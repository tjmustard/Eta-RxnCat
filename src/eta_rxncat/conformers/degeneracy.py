"""Per-conformer mirror degeneracy (R3) and mirror-partner removal.

g = 2 when the molecule is graph-achiral and the conformer itself is chiral (its mirror image is a
distinct conformer of the same energy); otherwise g = 1. It is decided from the conformer, never
from finding a partner, so removing one enantiomer before dedup cannot change it.
"""

from collections.abc import Sequence
from typing import Literal

import numpy as np
from rdkit import Chem

from eta_rxncat.conformers._rmsd import (
    atom_subset,
    check_order,
    coords,
    graph_permutations,
    min_rmsds,
)
from eta_rxncat.conformers.errors import ConformerInputError
from eta_rxncat.conformers.options import ConformerOptions
from eta_rxncat.core import ConformerRecord, MolecularState

_MIRROR = np.array([-1.0, 1.0, 1.0])


def graph_achiral(smiles: str) -> bool:
    """Return whether the molecule equals its mirror image as a graph.

    True when the canonical isomeric SMILES is unchanged by inverting every tetrahedral tag.
    Double-bond (E/Z) stereo is mirror-invariant and left as is; atropisomer and other
    non-tetrahedral stereo is not considered (known limit, R37).

    Raises:
        ConformerInputError: If the SMILES does not parse.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ConformerInputError(f"SMILES does not parse: {smiles!r}")
    mirror = Chem.Mol(mol)
    for atom in mirror.GetAtoms():
        if atom.GetChiralTag() in (
            Chem.ChiralType.CHI_TETRAHEDRAL_CW,
            Chem.ChiralType.CHI_TETRAHEDRAL_CCW,
        ):
            atom.InvertChirality()
    return bool(Chem.MolToSmiles(mol) == Chem.MolToSmiles(mirror))


def _mirror_rmsd(
    a: MolecularState, b: MolecularState, smiles: str, options: ConformerOptions
) -> float:
    """Return the least proper-rotation RMSD between ``a`` and the mirror image of ``b``."""
    perms = graph_permutations(smiles, options.max_automorphisms)
    atoms = atom_subset(smiles, options.include_h_in_rmsd, options.max_automorphisms)
    return float(min_rmsds(coords(a), [coords(b) * _MIRROR], perms, atoms)[0])


def conformer_chiral(state: MolecularState, smiles: str, options: ConformerOptions) -> bool:
    """Return whether the conformer is chiral.

    It is chiral when its x-inverted geometry is more than ``rmsd_dedup_angstrom`` from itself
    under every automorphism with a proper rotation.
    """
    check_order(state, smiles, options.max_automorphisms)
    return _mirror_rmsd(state, state, smiles, options) > options.rmsd_dedup_angstrom


def assign_degeneracy(
    state: MolecularState, smiles: str, options: ConformerOptions
) -> Literal[1, 2]:
    """Return 2 if the molecule is graph-achiral and the conformer chiral, else 1."""
    return 2 if graph_achiral(smiles) and conformer_chiral(state, smiles, options) else 1


def drop_mirror_partners(
    records: Sequence[ConformerRecord], smiles: str, options: ConformerOptions
) -> tuple[list[ConformerRecord], list[tuple[int, str]]]:
    """Remove each record whose mirror image matches a kept lower-G record.

    Records are visited by G (ties go to the lower index); the lower-G one stays. Returns the
    kept records in input order and ``(index, "mirror_partner")`` for each dropped one.
    """
    for record in records:
        check_order(record.state, smiles, options.max_automorphisms)
    order = sorted(
        range(len(records)), key=lambda i: (records[i].thermo.gibbs_free_energy_hartree, i)
    )
    kept: list[int] = []
    dropped: list[tuple[int, str]] = []
    for i in order:
        partner = any(
            _mirror_rmsd(records[k].state, records[i].state, smiles, options)
            <= options.rmsd_dedup_angstrom
            for k in kept
        )
        if partner:
            dropped.append((i, "mirror_partner"))
        else:
            kept.append(i)
    return [records[i] for i in sorted(kept)], sorted(dropped)
