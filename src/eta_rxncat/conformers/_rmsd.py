"""RMSD over graph automorphisms with proper rotations only (shared by dedup and degeneracy).

Reuses ``eta_rxncat.thermo._geometry``: the batched Kabsch fit there never reflects, so a
conformer and its mirror image do not superimpose.
"""

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from numpy.typing import NDArray
from rdkit import Chem

from eta_rxncat.conformers.errors import ConformerInputError
from eta_rxncat.core import MolecularState
from eta_rxncat.thermo import ThermoInputError
from eta_rxncat.thermo._geometry import _proper_rotation_rmsd, automorphisms

FloatArray = NDArray[np.float64]


@lru_cache(maxsize=64)
def _graph(smiles: str, max_automorphisms: int) -> tuple[tuple[str, ...], NDArray[np.intp]]:
    """Return the AddHs element order and the automorphism permutations of ``smiles``."""
    parsed = Chem.MolFromSmiles(smiles)
    if parsed is None:
        raise ConformerInputError(f"SMILES does not parse: {smiles!r}")
    mol = Chem.AddHs(parsed)
    try:
        perms = automorphisms(mol, max_automorphisms)
    except ThermoInputError as exc:
        raise ConformerInputError(str(exc)) from exc
    symbols = tuple(atom.GetSymbol() for atom in mol.GetAtoms())
    return symbols, np.asarray(perms, dtype=np.intp)


def graph_permutations(smiles: str, max_automorphisms: int) -> NDArray[np.intp]:
    """Return the automorphisms of ``AddHs(smiles)`` as an M x N index array."""
    return _graph(smiles, max_automorphisms)[1]


def atom_subset(smiles: str, include_h: bool, max_automorphisms: int) -> NDArray[np.intp]:
    """Return the atom indices an RMSD uses: all atoms, or the heavy atoms only."""
    symbols = _graph(smiles, max_automorphisms)[0]
    return np.asarray([i for i, s in enumerate(symbols) if include_h or s != "H"], dtype=np.intp)


def check_order(state: MolecularState, smiles: str, max_automorphisms: int) -> None:
    """Raise ``ConformerInputError`` unless the state's atoms are in ``AddHs(smiles)`` order."""
    symbols = _graph(smiles, max_automorphisms)[0]
    if tuple(state.symbols) != symbols:
        raise ConformerInputError(
            f"state atoms {list(state.symbols)} are not in the AddHs order of {smiles!r}"
        )


def min_rmsds(
    reference: FloatArray,
    others: Sequence[FloatArray],
    perms: NDArray[np.intp],
    atoms: NDArray[np.intp],
) -> FloatArray:
    """Return, for each of ``others``, its least RMSD to ``reference`` over every automorphism.

    Each automorphism permutes ``other``; the subset ``atoms`` is then fitted onto the same subset
    of ``reference`` by the best proper rotation (both centred on their centroids).
    """
    if not others:
        return np.zeros(0, dtype=np.float64)
    ref = reference[atoms]
    ref = ref - ref.mean(axis=0)
    stacked = np.stack(others)  # K x N x 3
    permuted = stacked[:, perms][:, :, atoms]  # K x M x n x 3
    k, m = permuted.shape[:2]
    moved = permuted.reshape(k * m, len(atoms), 3)
    moved = moved - moved.mean(axis=1, keepdims=True)
    rmsd = _proper_rotation_rmsd(ref, moved).reshape(k, m)
    return np.asarray(rmsd.min(axis=1), dtype=np.float64)


def coords(state: MolecularState) -> FloatArray:
    """Return the state's coordinates as an N x 3 float array."""
    return np.asarray(state.coordinates, dtype=np.float64)
