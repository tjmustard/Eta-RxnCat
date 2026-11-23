"""Two-pass ETKDGv3 conformer pools from a SMILES, with stereo-checked seeds (R21, R24, R28).

Pass 1 is ETKDGv3 with experimental torsion preferences; pass 2 (``torsion_free_pass``) is
identical but without them, because pass 1 never samples the s-cis-side class of a conjugated
diene (F21). Seeds are user geometries that must be the same molecule with the same stereo. RDKit
is BSD-3-Clause.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from pydantic import ValidationError
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds, rdDistGeom
from rdkit.Geometry import Point3D

from eta_rxncat.conformers._rmsd import atom_subset, coords, graph_permutations, min_rmsds
from eta_rxncat.conformers.errors import ConformerInputError, EmbeddingFailedError
from eta_rxncat.conformers.options import ConformerOptions
from eta_rxncat.core import MolecularState

Origin = Literal["etkdg", "etkdg_free", "seed"]


@dataclass(frozen=True)
class PoolMember:
    """One starting geometry.

    Attributes:
        source_id: Pass-1 embeddings ``0..n-1``, pass 2 ``n..2n-1``, seeds ``2n..``.
        origin: ``etkdg``, ``etkdg_free`` or ``seed``.
        state: The geometry, atoms in ``AddHs(smiles)`` order.
    """

    source_id: int
    origin: Origin
    state: MolecularState


@dataclass(frozen=True)
class ConformerPool:
    """Everything ``generate`` produced, for the runner to store and key.

    Attributes:
        smiles: The input SMILES.
        canonical_smiles: RDKit's canonical isomeric SMILES of the input.
        members: Every embedding and seed, seeds first, then by ``source_id``.
        failure_counts: RDKit's ETKDG failure counts per pass (``pass1``, ``pass2``).
        pre_dedup_survivors: ``source_id`` of the members kept by pre-dedup, in visit order.
        seed_geometries_sha256: ``seed_geometries_sha256`` of the seeds (``""`` if none).
        options: The options used.
    """

    smiles: str
    canonical_smiles: str
    members: tuple[PoolMember, ...]
    failure_counts: dict[str, tuple[int, ...]]
    pre_dedup_survivors: tuple[int, ...]
    seed_geometries_sha256: str
    options: ConformerOptions

    def member(self, source_id: int) -> PoolMember:
        """Return the member with ``source_id``."""
        for m in self.members:
            if m.source_id == source_id:
                return m
        raise KeyError(source_id)

    def survivors(self) -> tuple[PoolMember, ...]:
        """Return the pre-dedup survivors, in visit order."""
        return tuple(self.member(i) for i in self.pre_dedup_survivors)


def _seed_text(state: MolecularState) -> str:
    """Return the R28 hash text of a (reordered) seed geometry."""
    rows = [
        f"{s} {x:.6f} {y:.6f} {z:.6f}\n"
        for s, (x, y, z) in zip(state.symbols, state.coordinates, strict=True)
    ]
    return f"{len(state.symbols)}\n\n" + "".join(rows)


def seed_geometries_sha256(seeds: Sequence[MolecularState]) -> str:
    """Return the seeds' sorted hex sha256 digests joined by ``,`` (``""`` if there are none)."""
    digests = sorted(hashlib.sha256(_seed_text(s).encode("utf-8")).hexdigest() for s in seeds)
    return ",".join(digests)


def _parse(smiles: str, charge: int, spin_multiplicity: int) -> tuple[Any, Any, str]:
    """Return (mol, mol with H, canonical isomeric SMILES) after the input checks."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ConformerInputError(f"SMILES does not parse: {smiles!r}")
    labelled = [a.GetIdx() for a in mol.GetAtoms() if a.GetIsotope() != 0]
    if labelled:
        raise ConformerInputError(
            f"SMILES {smiles!r} has isotope labels on atoms {labelled}; masses come from the "
            "element symbols, so isotopes are refused in v0.3.0 (R16)"
        )
    formal = Chem.GetFormalCharge(mol)
    if formal != charge:
        raise ConformerInputError(f"SMILES {smiles!r} has formal charge {formal}, not {charge}")
    mol_h = Chem.AddHs(mol)
    symbols = [a.GetSymbol() for a in mol_h.GetAtoms()]
    try:
        MolecularState(
            symbols=symbols,
            coordinates=[[0.0, 0.0, float(i)] for i in range(len(symbols))],
            charge=charge,
            spin_multiplicity=spin_multiplicity,
        )
    except ValidationError as exc:
        raise ConformerInputError(f"SMILES {smiles!r}: {exc.errors()[0]['msg']}") from exc
    return mol, mol_h, Chem.MolToSmiles(mol)


def _embed(
    mol_h: Any, options: ConformerOptions, free: bool
) -> tuple[list[list[list[float]]], tuple[int, ...]]:
    """Run one ETKDGv3 pass; return the embedded coordinates and RDKit's failure counts."""
    params: Any = rdDistGeom.ETKDGv3()  # RDKit stubs type the attributes wrongly
    params.randomSeed = options.seed
    params.pruneRmsThresh = -1.0
    params.numThreads = 1
    params.enforceChirality = True
    params.trackFailures = True
    if free:
        params.useExpTorsionAnglePrefs = False
    work = Chem.Mol(mol_h)
    ids = list(rdDistGeom.EmbedMultipleConfs(work, numConfs=options.n_embed, params=params))
    geometries = [work.GetConformer(cid).GetPositions().tolist() for cid in ids]
    return geometries, tuple(int(c) for c in params.GetFailureCounts())


def _check_seed(
    index: int, seed: MolecularState, mol_h: Any, canonical: str, charge: int, multiplicity: int
) -> MolecularState:
    """Return ``seed`` reordered into SMILES atom order, or raise ``ConformerInputError``."""
    name = f"seed {index}"
    if seed.charge != charge or seed.spin_multiplicity != multiplicity:
        raise ConformerInputError(
            f"{name}: charge {seed.charge}, multiplicity {seed.spin_multiplicity} differ from "
            f"the call's {charge}, {multiplicity}"
        )
    if sorted(seed.symbols) != sorted(a.GetSymbol() for a in mol_h.GetAtoms()):
        raise ConformerInputError(f"{name}: its elements differ from the SMILES's")
    rw = Chem.RWMol()
    for symbol in seed.symbols:
        rw.AddAtom(Chem.Atom(symbol))
    conformer = Chem.Conformer(len(seed.symbols))
    for i, (x, y, z) in enumerate(seed.coordinates):
        conformer.SetAtomPosition(i, Point3D(x, y, z))
    rw.AddConformer(conformer, assignId=True)
    seed_mol = rw.GetMol()
    try:
        rdDetermineBonds.DetermineBonds(seed_mol, charge=charge)
        Chem.SanitizeMol(seed_mol)
        Chem.AssignStereochemistryFrom3D(seed_mol)
    except ValueError as exc:
        raise ConformerInputError(f"{name}: bond perception failed: {exc}") from exc
    perceived = Chem.MolToSmiles(Chem.RemoveHs(seed_mol))
    if perceived != canonical:
        raise ConformerInputError(
            f"{name}: perceived as {perceived!r}, not the input {canonical!r} (connectivity or "
            "stereo differs)"
        )
    match = mol_h.GetSubstructMatch(seed_mol, useChirality=True)
    if len(match) != mol_h.GetNumAtoms():
        raise ConformerInputError(f"{name}: no stereo-respecting atom match onto the SMILES")
    ordered = [[0.0, 0.0, 0.0]] * len(match)
    for seed_index, smiles_index in enumerate(match):
        ordered[smiles_index] = list(seed.coordinates[seed_index])
    symbols = [a.GetSymbol() for a in mol_h.GetAtoms()]
    return MolecularState(
        symbols=symbols,
        coordinates=ordered,
        charge=charge,
        spin_multiplicity=multiplicity,
        metadata=dict(seed.metadata),
    )


def generate(
    smiles: str,
    *,
    charge: int,
    spin_multiplicity: int,
    options: ConformerOptions,
    seed_geometries: Sequence[MolecularState] = (),
) -> ConformerPool:
    """Return the two-pass ETKDGv3 pool of ``smiles`` plus any seeds, with pre-dedup applied.

    Pre-dedup visits seeds first, then embeddings by id, and keeps a member unless it is within
    ``pre_dedup_rmsd_angstrom`` (with H, min over automorphisms, proper rotation) of a kept one.
    A seed is never removed.

    Raises:
        ConformerInputError: Unparsable SMILES, an isotope label, a formal charge other than
            ``charge``, impossible electron parity, or any seed failure (charge or multiplicity,
            connectivity, stereo).
        EmbeddingFailedError: Neither pass produced an embedding.
    """
    _, mol_h, canonical = _parse(smiles, charge, spin_multiplicity)
    symbols = [a.GetSymbol() for a in mol_h.GetAtoms()]
    seeds = [
        _check_seed(i, s, mol_h, canonical, charge, spin_multiplicity)
        for i, s in enumerate(seed_geometries)
    ]
    n = options.n_embed
    pass1, fail1 = _embed(mol_h, options, free=False)
    counts: dict[str, tuple[int, ...]] = {"pass1": fail1}
    pass2: list[list[list[float]]] = []
    if options.torsion_free_pass:
        pass2, fail2 = _embed(mol_h, options, free=True)
        counts["pass2"] = fail2
    if not pass1 and not pass2:
        raise EmbeddingFailedError(counts)

    def state(xyz: list[list[float]]) -> MolecularState:
        return MolecularState(
            symbols=symbols, coordinates=xyz, charge=charge, spin_multiplicity=spin_multiplicity
        )

    members = [PoolMember(2 * n + i, "seed", s) for i, s in enumerate(seeds)]
    members += [PoolMember(i, "etkdg", state(xyz)) for i, xyz in enumerate(pass1)]
    members += [PoolMember(n + i, "etkdg_free", state(xyz)) for i, xyz in enumerate(pass2)]

    perms = graph_permutations(smiles, options.max_automorphisms)
    atoms = atom_subset(smiles, True, options.max_automorphisms)
    kept: list[PoolMember] = []
    kept_xyz: list[np.ndarray] = []
    for member in members:
        xyz = coords(member.state)
        if member.origin != "seed" and kept_xyz:
            nearest = float(min_rmsds(xyz, kept_xyz, perms, atoms).min())
            if nearest <= options.pre_dedup_rmsd_angstrom:
                continue
        kept.append(member)
        kept_xyz.append(xyz)
    return ConformerPool(
        smiles=smiles,
        canonical_smiles=canonical,
        members=tuple(members),
        failure_counts=counts,
        pre_dedup_survivors=tuple(m.source_id for m in kept),
        seed_geometries_sha256=seed_geometries_sha256(seeds),
        options=options,
    )
