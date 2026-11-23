"""Geometry helpers shared by ``eta_rxncat.thermo`` and ``eta_rxncat.conformers``.

Every rigid fit is a proper rotation (determinant +1): a reflection is never allowed, so a
molecule and its mirror image are not superimposed.
"""

from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from eta_rxncat.thermo.errors import ThermoInputError

FloatArray = NDArray[np.float64]


def center_of_mass(coords: ArrayLike, masses: ArrayLike) -> FloatArray:
    """Return the mass-weighted centre of ``coords`` (N x 3)."""
    xyz = np.asarray(coords, dtype=np.float64)
    m = np.asarray(masses, dtype=np.float64)
    return np.asarray((m[:, None] * xyz).sum(axis=0) / m.sum(), dtype=np.float64)


def inertia_tensor(coords: ArrayLike, masses: ArrayLike) -> FloatArray:
    """Return the 3 x 3 inertia tensor about the centre of mass, in mass x length^2 units."""
    xyz = np.asarray(coords, dtype=np.float64)
    m = np.asarray(masses, dtype=np.float64)
    r = xyz - center_of_mass(xyz, m)
    r2 = (r * r).sum(axis=1)
    tensor = np.eye(3) * float((m * r2).sum()) - np.einsum("i,ij,ik->jk", m, r, r)
    return np.asarray(tensor, dtype=np.float64)


def principal_axes(coords: ArrayLike, masses: ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Return the ascending principal moments and their axes (columns)."""
    moments, axes = np.linalg.eigh(inertia_tensor(coords, masses))
    return np.asarray(moments, dtype=np.float64), np.asarray(axes, dtype=np.float64)


def is_linear(coords: ArrayLike, masses: ArrayLike, linear_tol_angstrom: float) -> bool:
    """Return whether a molecule is linear.

    N = 1 is never linear and N = 2 always is. Otherwise the molecule is linear when every atom
    lies within ``linear_tol_angstrom`` of the line through the centre of mass along the principal
    axis with the smallest moment.

    Args:
        coords: Cartesian coordinates (Angstrom), N x 3.
        masses: Atomic masses, N.
        linear_tol_angstrom: Largest allowed distance from the axis (Angstrom).
    """
    xyz = np.asarray(coords, dtype=np.float64)
    n = xyz.shape[0]
    if n == 1:
        return False
    if n == 2:
        return True
    _, axes = principal_axes(xyz, masses)
    axis = axes[:, 0]
    r = xyz - center_of_mass(xyz, masses)
    off_axis = r - np.outer(r @ axis, axis)
    return bool(np.all(np.linalg.norm(off_axis, axis=1) <= linear_tol_angstrom))


def _proper_rotation_rmsd(reference: FloatArray, moved: FloatArray) -> FloatArray:
    """Return the proper-rotation RMSD of each ``moved[k]`` onto ``reference`` (both centred).

    ``reference`` is N x 3 and ``moved`` is M x N x 3. Kabsch: H = moved^T reference, SVD, flip the
    smallest singular direction when det < 0 so the rotation is proper.
    """
    n = reference.shape[0]
    cov = np.einsum("kni,nj->kij", moved, reference)
    u, s, vt = np.linalg.svd(cov)
    det = np.linalg.det(u) * np.linalg.det(vt)
    s_signed = s.copy()
    s_signed[:, 2] *= np.sign(det)
    s_signed[det == 0.0, 2] = s[det == 0.0, 2]
    e0 = (moved**2).sum(axis=(1, 2)) + float((reference**2).sum())
    msd = np.maximum(e0 - 2.0 * s_signed.sum(axis=1), 0.0) / n
    return np.asarray(np.sqrt(msd), dtype=np.float64)


def kabsch_rmsd(reference: ArrayLike, moved: ArrayLike) -> float:
    """Return the RMSD after the best proper rotation of ``moved`` onto ``reference``.

    Both are N x 3 and are centred on their (unweighted) centroids first.
    """
    ref = np.asarray(reference, dtype=np.float64)
    mov = np.asarray(moved, dtype=np.float64)
    if ref.shape != mov.shape:
        raise ThermoInputError(f"shape {mov.shape} != reference shape {ref.shape}")
    ref = ref - ref.mean(axis=0)
    mov = mov - mov.mean(axis=0)
    return float(_proper_rotation_rmsd(ref, mov[None, :, :])[0])


def permuted_rmsds(coords: ArrayLike, permutations: ArrayLike) -> FloatArray:
    """Return the proper-rotation RMSD between ``coords`` and each atom permutation of itself.

    Args:
        coords: N x 3 coordinates.
        permutations: M x N; row ``k`` maps position ``i`` to atom ``permutations[k][i]``.

    Returns:
        M RMSDs, in the units of ``coords``.
    """
    xyz = np.asarray(coords, dtype=np.float64)
    perms = np.asarray(permutations, dtype=np.intp)
    if perms.size == 0:
        return np.zeros(0, dtype=np.float64)
    centred = xyz - xyz.mean(axis=0)
    return _proper_rotation_rmsd(centred, centred[perms])


def automorphisms(mol: Any, max_automorphisms: int) -> list[tuple[int, ...]]:
    """Return every graph automorphism of an RDKit molecule (hydrogens as given).

    ``GetSubstructMatches`` truncates at 1000 matches unless told otherwise, so the cap is always
    explicit: ``max_automorphisms + 1`` matches are requested, and reaching that many is an error.

    Args:
        mol: An RDKit ``Mol``.
        max_automorphisms: The largest number of automorphisms accepted.

    Raises:
        ThermoInputError: If the molecule has more than ``max_automorphisms`` automorphisms.
    """
    matches = mol.GetSubstructMatches(
        mol, uniquify=False, useChirality=False, maxMatches=max_automorphisms + 1
    )
    if len(matches) > max_automorphisms:
        raise ThermoInputError(
            f"automorphism cap reached: more than {max_automorphisms} graph automorphisms "
            "(raise ThermoAnalysisOptions.max_automorphisms)"
        )
    return [tuple(int(i) for i in match) for match in matches]
