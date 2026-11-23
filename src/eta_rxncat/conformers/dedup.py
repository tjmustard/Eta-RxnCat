"""Post-optimization dedup and the energy window (DV-11; R3).

Two optimized conformers are one when their least RMSD over graph automorphisms, after the best
proper rotation, is within ``rmsd_dedup_angstrom``. Mirror images are never merged here (no
reflection); ``degeneracy.drop_mirror_partners`` handles them.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from eta_rxncat.conformers._rmsd import (
    atom_subset,
    check_order,
    coords,
    graph_permutations,
    min_rmsds,
)
from eta_rxncat.conformers.errors import ConformerInputError
from eta_rxncat.conformers.options import ConformerOptions
from eta_rxncat.core import MolecularState
from eta_rxncat.engines import kcal_mol_to_hartree


@dataclass(frozen=True)
class Kept:
    """One distinct conformer after dedup.

    Attributes:
        index: Index (into the input) of the representative, the lowest-energy member.
        source_ids: Indices of every input merged into it, ascending (the representative included).
    """

    index: int
    source_ids: tuple[int, ...]


def dedup(
    states: Sequence[MolecularState],
    energies: Sequence[float],
    options: ConformerOptions,
    *,
    smiles: str,
) -> list[Kept]:
    """Merge optimized conformers within ``rmsd_dedup_angstrom`` into the lower-energy one.

    States are visited by energy (ties go to the lower index); each joins the first kept
    representative it matches, else becomes one. The result is ordered by energy.

    Args:
        states: Optimized geometries, atoms in ``AddHs(smiles)`` order.
        energies: Their electronic energies (Eh).
        options: ``rmsd_dedup_angstrom``, ``include_h_in_rmsd``, ``max_automorphisms``.
        smiles: The molecule (for its automorphisms).

    Raises:
        ConformerInputError: On a length mismatch or a state not in SMILES atom order.
    """
    if len(states) != len(energies):
        raise ConformerInputError(f"{len(states)} states but {len(energies)} energies")
    for state in states:
        check_order(state, smiles, options.max_automorphisms)
    perms = graph_permutations(smiles, options.max_automorphisms)
    atoms = atom_subset(smiles, options.include_h_in_rmsd, options.max_automorphisms)
    order = sorted(range(len(states)), key=lambda i: (energies[i], i))
    reps: list[int] = []
    groups: dict[int, list[int]] = {}
    for i in order:
        xyz = coords(states[i])
        if reps:
            rmsd = min_rmsds(xyz, [coords(states[r]) for r in reps], perms, atoms)
            hits = [
                r
                for r, value in zip(reps, rmsd, strict=True)
                if value <= options.rmsd_dedup_angstrom
            ]
            if hits:
                groups[hits[0]].append(i)
                continue
        reps.append(i)
        groups[i] = [i]
    return [Kept(index=r, source_ids=tuple(sorted(groups[r]))) for r in reps]


def energy_window(
    kept: Sequence[Kept], energies: Sequence[float], options: ConformerOptions
) -> tuple[list[Kept], list[Kept]]:
    """Split ``kept`` into (inside, outside) the window E - E_min <= ``energy_window_kcal_mol``."""
    if not kept:
        return [], []
    e_min = min(energies[k.index] for k in kept)
    limit = kcal_mol_to_hartree(options.energy_window_kcal_mol)
    inside = [k for k in kept if energies[k.index] - e_min <= limit]
    outside = [k for k in kept if energies[k.index] - e_min > limit]
    return inside, outside
