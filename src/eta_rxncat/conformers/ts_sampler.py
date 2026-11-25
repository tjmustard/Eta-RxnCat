"""The TS conformer sampler and the relative-configuration face descriptor (v0.6.0, slice 05).

Mission R1, R11, R16 and §5 "Face check". A sample never moves the reactive core and never crosses
to the other diastereomeric face:

* ``forming_bond_configuration`` is the relative configuration across each forming bond, a sign
  per bond, invariant under rigid motion and reflection and flipped between diastereomers.
* ``sample_ts_conformers`` embeds every connected fragment of the seed's perceived graph on its
  own (ETKDGv3 with a coordinate map on its anchor atoms; a map across disconnected fragments is
  ignored by RDKit, HF-4), places it on the seed by the anchor, and adds seeded perturbations of
  the non-core atoms. In every sample the core coordinates are then the seed's, exactly.

Pure: no engine, no geomeTRIC, no torch, no PySCF (G8).
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from rdkit import Chem, rdBase
from rdkit.Chem import rdDetermineBonds, rdDistGeom
from rdkit.Geometry import Point3D

from eta_rxncat.conformers._rmsd import min_rmsds
from eta_rxncat.conformers.errors import ConformerInputError, EmbeddingFailedError
from eta_rxncat.core import MolecularState, TSEnsembleOptions
from eta_rxncat.store.keys import geometry_payload
from eta_rxncat.thermo import ThermoInputError
from eta_rxncat.thermo._geometry import automorphisms

FloatArray = NDArray[np.float64]

_MIN_VOLUME_ANGSTROM3 = 1e-6
"""A face volume below this is degenerate (mission §5 "Face check")."""

_COLLINEAR_TOL = 1e-3
"""Largest sine of the angle for three anchor atoms to count as collinear."""


class FaceDescriptorError(ValueError):
    """The relative configuration cannot be judged (too few neighbours, or a zero volume)."""


@dataclass(frozen=True)
class TSSample:
    """One sampled start geometry for a TS re-search.

    Attributes:
        source: ``fragment_embed:<k>`` or ``perturb:<k>`` (``k`` counts from 0).
        state: The geometry; its core atoms equal the seed's exactly.
        face: ``forming_bond_configuration`` of ``state`` on the seed's perceived graph.
        start_sha256: Hex digest of the keyed geometry (``store.keys.geometry_payload``).
        bond_orders: For a ``fragment_embed`` sample, ``determined`` if every fragment's bond
            orders came from ``rdDetermineBonds.DetermineBonds`` (``charge=0``), else
            ``connectivity`` (the fallback: single bonds from the seed's perceived graph,
            recorded here); ``none`` for a ``perturb`` sample, which uses no bond orders.
    """

    source: str
    state: MolecularState
    face: tuple[int, ...]
    start_sha256: str
    bond_orders: str = "none"


def _sorted_forming_bonds(forming_bonds: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    return sorted((min(i, j), max(i, j)) for i, j in forming_bonds)


def _neighbours(bonds: Sequence[tuple[int, int]], n_atoms: int) -> list[list[int]]:
    result: list[list[int]] = [[] for _ in range(n_atoms)]
    for i, j in bonds:
        result[i].append(j)
        result[j].append(i)
    return [sorted(set(row)) for row in result]


def forming_bond_configuration(
    state: MolecularState,
    forming_bonds: Sequence[tuple[int, int]],
    bonds: Sequence[tuple[int, int]],
) -> tuple[int, ...]:
    """Return the relative configuration across each forming bond: ``+1`` or ``-1`` per bond.

    For a forming bond ``(i, j)`` and each end ``c`` with partner ``p``, ``V_c`` is the determinant
    of ``[x_a - x_c, x_b - x_c, x_p - x_c]`` where ``a`` and ``b`` are the two lowest-index
    neighbours of ``c`` in ``bonds`` other than ``p``. The sign of the bond is ``sign V_i * sign
    V_j``. ``bonds`` is the seed's perceived graph, for the seed and for every member.

    Args:
        state: The geometry.
        forming_bonds: Pairs of atoms whose bond forms; reported in sorted order.
        bonds: The perceived covalent bonds (forming bonds excluded).

    Returns:
        One sign per forming bond, in sorted forming-bond order.

    Raises:
        FaceDescriptorError: An end has fewer than two neighbours besides its partner, or a volume
            is below ``1e-6`` cubic Angstrom.
    """
    xyz = np.asarray(state.coordinates, dtype=np.float64)
    neighbours = _neighbours(bonds, len(state.symbols))

    def volume(c: int, p: int) -> float:
        others = [n for n in neighbours[c] if n != p]
        if len(others) < 2:
            raise FaceDescriptorError(
                f"forming bond end {c} (partner {p}) has {len(others)} other neighbours; need 2"
            )
        a, b = others[0], others[1]
        det = float(np.linalg.det(np.stack([xyz[a] - xyz[c], xyz[b] - xyz[c], xyz[p] - xyz[c]])))
        if abs(det) < _MIN_VOLUME_ANGSTROM3:
            raise FaceDescriptorError(f"forming bond end {c} (partner {p}) has volume {det:.3g}")
        return det

    signs = []
    for i, j in _sorted_forming_bonds(forming_bonds):
        signs.append(1 if (volume(i, j) > 0) == (volume(j, i) > 0) else -1)
    return tuple(signs)


def _components(bonds: Sequence[tuple[int, int]], n_atoms: int) -> list[list[int]]:
    """Return the connected components of the graph, each sorted, ordered by lowest atom."""
    neighbours = _neighbours(bonds, n_atoms)
    seen = [False] * n_atoms
    components: list[list[int]] = []
    for start in range(n_atoms):
        if seen[start]:
            continue
        stack, component = [start], []
        seen[start] = True
        while stack:
            atom = stack.pop()
            component.append(atom)
            for other in neighbours[atom]:
                if not seen[other]:
                    seen[other] = True
                    stack.append(other)
        components.append(sorted(component))
    return components


def _collinear(points: FloatArray) -> bool:
    """Return whether every point lies on the line through the first two distinct ones."""
    if len(points) < 3:
        return True
    direction = points[1] - points[0]
    norm = float(np.linalg.norm(direction))
    if norm == 0.0:
        return True
    direction = direction / norm
    off = points[2:] - points[0]
    cross = np.linalg.norm(np.cross(off, direction), axis=1)
    scale = np.maximum(np.linalg.norm(off, axis=1), 1e-12)
    return bool(np.all(cross / scale < _COLLINEAR_TOL))


def _anchor(
    fragment: list[int],
    core: set[int],
    xyz: FloatArray,
    symbols: Sequence[str],
    neighbours: list[list[int]],
) -> list[int]:
    """Return the fragment's anchor: its core atoms, plus their heavy neighbours if too few."""
    anchor = [a for a in fragment if a in core]
    if len(anchor) >= 3 and not _collinear(xyz[anchor]):
        return anchor
    members = set(fragment)
    extra = {
        n
        for a in anchor
        for n in neighbours[a]
        if n in members and n not in core and symbols[n] != "H"
    }
    anchor = sorted(set(anchor) | extra)
    if len(anchor) < 3 or _collinear(xyz[anchor]):
        raise ConformerInputError(
            f"fragment {fragment} has no usable anchor: core atoms {sorted(core & members)} "
            f"plus heavy neighbours give {anchor}, fewer than three or collinear"
        )
    return anchor


def _fragment_mol(
    fragment: list[int],
    symbols: Sequence[str],
    xyz: FloatArray,
    bonds: Sequence[tuple[int, int]],
) -> tuple["Chem.Mol", bool]:
    """Build the fragment as its own RDKit molecule; return it and whether bond orders were found.

    Bond orders come from ``rdDetermineBonds.DetermineBonds`` with ``charge=0``. If that fails, or
    perceives a different connectivity from the seed's, the molecule has the seed's connectivity
    with single bonds and the second value is ``False``.
    """
    local = {atom: k for k, atom in enumerate(fragment)}

    def build() -> Chem.RWMol:
        mol = Chem.RWMol()
        for atom in fragment:
            rd_atom = Chem.Atom(symbols[atom])
            rd_atom.SetNoImplicit(True)
            mol.AddAtom(rd_atom)
        conformer = Chem.Conformer(len(fragment))
        for atom in fragment:
            x, y, z = xyz[atom]
            conformer.SetAtomPosition(local[atom], Point3D(float(x), float(y), float(z)))
        mol.AddConformer(conformer, assignId=True)
        return mol

    wanted = sorted((local[i], local[j]) for i, j in bonds if i in local and j in local)
    mol = build()
    try:
        rdDetermineBonds.DetermineBonds(mol, charge=0)
        found = sorted(
            (b.GetBeginAtomIdx(), b.GetEndAtomIdx())
            if b.GetBeginAtomIdx() < b.GetEndAtomIdx()
            else (b.GetEndAtomIdx(), b.GetBeginAtomIdx())
            for b in mol.GetBonds()
        )
        if found == wanted:
            Chem.AssignStereochemistryFrom3D(mol)
            return mol.GetMol(), True
    except ValueError:
        pass
    mol = build()
    for i, j in wanted:
        mol.AddBond(i, j, Chem.BondType.SINGLE)
    mol.UpdatePropertyCache(strict=False)
    return mol.GetMol(), False


def _kabsch(mobile: FloatArray, target: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Return ``(rotation, translation)`` of the best proper fit: ``x -> x @ rotation + t``."""
    mobile_c, target_c = mobile.mean(axis=0), target.mean(axis=0)
    u, _, vt = np.linalg.svd((mobile - mobile_c).T @ (target - target_c))
    d = np.sign(np.linalg.det(u @ vt))
    rotation = u @ np.diag([1.0, 1.0, d if d != 0 else 1.0]) @ vt
    return rotation, target_c - mobile_c @ rotation


def _embed_fragment(
    fragment: list[int],
    anchor: list[int],
    symbols: Sequence[str],
    xyz: FloatArray,
    bonds: Sequence[tuple[int, int]],
    options: TSEnsembleOptions,
) -> tuple[list[FloatArray], bool]:
    """Return ``n_embed`` placed coordinate sets of the fragment (fragment-local order)."""
    mol, determined = _fragment_mol(fragment, symbols, xyz, bonds)
    local = {atom: k for k, atom in enumerate(fragment)}
    params: Any = rdDistGeom.ETKDGv3()
    params.randomSeed = options.random_seed
    params.numThreads = 1
    params.SetCoordMap(
        {local[a]: Point3D(float(xyz[a][0]), float(xyz[a][1]), float(xyz[a][2])) for a in anchor}
    )
    with rdBase.BlockLogs():
        ids = list(rdDistGeom.EmbedMultipleConfs(mol, options.n_embed, params))
    placed: list[FloatArray] = []
    anchor_local = [local[a] for a in anchor]
    for conformer_id in ids:
        coords = np.asarray(mol.GetConformer(conformer_id).GetPositions(), dtype=np.float64)
        rotation, translation = _kabsch(coords[anchor_local], xyz[anchor])
        placed.append(coords @ rotation + translation)
    return placed, determined


def _automorphism_permutations(
    symbols: Sequence[str], bonds: Sequence[tuple[int, int]], cap: int
) -> NDArray[np.intp]:
    mol = Chem.RWMol()
    for symbol in symbols:
        mol.AddAtom(Chem.Atom(symbol))
    for i, j in bonds:
        mol.AddBond(i, j, Chem.BondType.SINGLE)
    try:
        perms = automorphisms(mol.GetMol(), cap)
    except ThermoInputError as exc:
        raise ConformerInputError(str(exc)) from exc
    return np.asarray(perms, dtype=np.intp)


def _digest(state: MolecularState) -> str:
    text = json.dumps(geometry_payload(state), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sample_ts_conformers(
    seed: MolecularState,
    core_indices: Sequence[int],
    forming_bonds: Sequence[tuple[int, int]],
    bonds: Sequence[tuple[int, int]],
    options: TSEnsembleOptions,
) -> list[TSSample]:
    """Sample start geometries around a verified TS, core frozen, deterministic.

    Per connected fragment of ``bonds`` (forming bonds are not bonds): embed ``n_embed`` conformers
    with ETKDGv3 (``randomSeed``, one thread) and a coordinate map on the fragment's anchor, then
    place each on the seed by the anchor (proper Kabsch fit); sample ``k`` combines every
    fragment's ``k``-th embedding. Then ``n_perturb`` samples add ``N(0, sigma)`` noise to every
    non-core atom of the seed. In every sample the core coordinates are the seed's, exactly.
    Samples within ``pre_dedup_rmsd_angstrom`` of the seed or of a kept sample (proper-rotation
    RMSD over the seed graph's automorphisms, hydrogens included) are dropped. The seed is not
    returned.

    Args:
        seed: The verified TS.
        core_indices: Atoms that never move (the active core).
        forming_bonds: Pairs of atoms whose bond forms.
        bonds: The seed's perceived covalent bonds (forming bonds excluded).
        options: The keyed sampler options.

    Returns:
        The kept samples: ``fragment_embed:<k>`` by index, then ``perturb:<k>`` by index.

    Raises:
        ConformerInputError: A fragment has no usable anchor, or the automorphism cap is reached.
        EmbeddingFailedError: A fragment embedded no conformer.
        FaceDescriptorError: The seed's face cannot be judged.
    """
    symbols = list(seed.symbols)
    n_atoms = len(symbols)
    xyz = np.asarray(seed.coordinates, dtype=np.float64)
    core = {int(i) for i in core_indices}
    forming_bond_configuration(seed, forming_bonds, bonds)  # the seed itself must be judgeable
    neighbours = _neighbours(bonds, n_atoms)
    core_sorted = sorted(core)
    noncore = [a for a in range(n_atoms) if a not in core]

    candidates: list[tuple[str, FloatArray, bool | None]] = []
    embeddings: list[tuple[list[int], list[FloatArray]]] = []
    all_determined = True
    for fragment in _components(bonds, n_atoms):
        if not core & set(fragment):
            continue  # a spectator fragment keeps the seed's geometry in every embedding
        anchor = _anchor(fragment, core, xyz, symbols, neighbours)
        placed, fragment_determined = _embed_fragment(
            fragment, anchor, symbols, xyz, bonds, options
        )
        if not placed:
            raise EmbeddingFailedError({"fragment": (fragment[0],)})
        all_determined = all_determined and fragment_determined
        embeddings.append((fragment, placed))
    if embeddings:
        for k in range(min(len(placed) for _, placed in embeddings)):
            coords = xyz.copy()
            for fragment, placed in embeddings:
                coords[fragment] = placed[k]
            candidates.append((f"fragment_embed:{k}", coords, all_determined))
    rng = np.random.default_rng(options.random_seed)
    for k in range(options.n_perturb):
        noise = rng.normal(0.0, options.perturb_sigma_angstrom, size=(len(noncore), 3))
        coords = xyz.copy()
        coords[noncore] += noise
        candidates.append((f"perturb:{k}", coords, None))

    perms = _automorphism_permutations(symbols, bonds, options.max_automorphisms)
    everything = np.arange(n_atoms, dtype=np.intp)
    kept: list[FloatArray] = [xyz]
    samples: list[TSSample] = []
    for source, coords, determined in candidates:
        coords[core_sorted] = xyz[core_sorted]
        distance = min_rmsds(coords, kept, perms, everything)
        if kept and float(distance.min()) < options.pre_dedup_rmsd_angstrom:
            continue
        kept.append(coords)
        state = seed.model_copy(update={"coordinates": coords.tolist()})
        samples.append(
            TSSample(
                source=source,
                state=state,
                face=forming_bond_configuration(state, forming_bonds, bonds),
                start_sha256=_digest(state),
                bond_orders="none"
                if determined is None
                else ("determined" if determined else "connectivity"),
            )
        )
    return samples
