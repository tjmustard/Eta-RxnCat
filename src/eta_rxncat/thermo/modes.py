"""Eckart-projected harmonic normal modes from a Cartesian Hessian (DV-06, DV-07)."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from eta_rxncat.core import ThermoAnalysisOptions
from eta_rxncat.thermo._geometry import center_of_mass, is_linear
from eta_rxncat.thermo.constants import EIGENVALUE_TO_CM1
from eta_rxncat.thermo.errors import ThermoInputError
from eta_rxncat.thermo.masses import atomic_masses_amu

ZERO_FREQUENCY_CM1 = 1e-3
"""A mode with |nu| below this (cm^-1) is degenerate with a rigid motion: an error (R15)."""


@dataclass(frozen=True)
class NormalModes:
    """Harmonic frequencies and mode vectors of one geometry.

    Attributes:
        frequencies_cm1: The 0 / 3N-5 / 3N-6 frequencies (cm^-1), ascending, imaginary negative.
        modes_cartesian: 3N x n_modes; column ``k`` is the Cartesian displacement of mode ``k``
            (``3 * atom + axis``), normalised to unit length.
        is_linear: Whether the molecule was analysed as linear.
        n_atoms: Number of atoms.
    """

    frequencies_cm1: tuple[float, ...]
    modes_cartesian: NDArray[np.float64]
    is_linear: bool
    n_atoms: int


def _rigid_basis(coords: NDArray[np.float64], masses: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the 3N x 6 mass-weighted translation and rotation vectors about the COM."""
    n = coords.shape[0]
    sqrt_m = np.sqrt(masses)
    r = coords - center_of_mass(coords, masses)
    vectors = []
    for axis in range(3):
        t = np.zeros((n, 3))
        t[:, axis] = sqrt_m
        vectors.append(t.reshape(-1))
    for axis in range(3):
        unit = np.zeros(3)
        unit[axis] = 1.0
        vectors.append((np.cross(unit, r) * sqrt_m[:, None]).reshape(-1))
    return np.column_stack(vectors)


def normal_modes(
    symbols: Sequence[str],
    coords_angstrom: ArrayLike,
    hessian_hartree_per_bohr2: ArrayLike,
    *,
    analysis: ThermoAnalysisOptions,
) -> NormalModes:
    """Return the harmonic normal modes of a geometry.

    The Hessian is copied into a fresh float64 array (the input is never modified), symmetrised
    and mass-weighted. Translations and rotations about the centre of mass are orthonormalised by
    SVD (rank 3 for N = 1, 5 if linear, else 6) and the Hessian is diagonalised in their orthogonal
    complement, so exactly 0 / 3N-5 / 3N-6 eigenvalues result; nothing is dropped by magnitude.

    Args:
        symbols: Element symbols, one per atom.
        coords_angstrom: Cartesian coordinates (Angstrom), N x 3.
        hessian_hartree_per_bohr2: Cartesian Hessian (Eh/Bohr^2), 3N x 3N, unprojected.
        analysis: Tolerances (``linear_tol_angstrom`` decides linearity).

    Raises:
        ThermoInputError: On a shape mismatch, a non-finite Hessian, a rank-deficient rigid-body
            basis, or a mode with |nu| < 1e-3 cm^-1.
    """
    coords = np.array(coords_angstrom, dtype=np.float64)
    n = len(symbols)
    if coords.shape != (n, 3):
        raise ThermoInputError(f"coordinates shape {coords.shape} != ({n}, 3)")
    hessian = np.array(hessian_hartree_per_bohr2, dtype=np.float64)
    if hessian.shape != (3 * n, 3 * n):
        raise ThermoInputError(f"Hessian shape {hessian.shape} != ({3 * n}, {3 * n})")
    if not np.all(np.isfinite(hessian)):
        raise ThermoInputError("Hessian has non-finite entries")
    masses = atomic_masses_amu(symbols)
    linear = is_linear(coords, masses, analysis.linear_tol_angstrom)
    if n == 1:
        return NormalModes((), np.zeros((3, 0)), False, 1)

    hessian = 0.5 * (hessian + hessian.T)
    inv_sqrt_m = np.repeat(1.0 / np.sqrt(masses), 3)
    mass_weighted = hessian * np.outer(inv_sqrt_m, inv_sqrt_m)

    rank = 5 if linear else 6
    # The rigid-body span does not depend on the length unit, so Angstrom is used as given.
    u, s, _ = np.linalg.svd(_rigid_basis(coords, masses), full_matrices=True)
    if s[rank - 1] <= 1e-8 * s[0]:
        raise ThermoInputError(
            f"rigid-body basis has rank < {rank} (singular values {s.tolist()}); "
            "check linearity and coordinates"
        )
    complement = u[:, rank:]
    projected = complement.T @ mass_weighted @ complement
    eigenvalues, vectors = np.linalg.eigh(0.5 * (projected + projected.T))
    frequencies = np.sign(eigenvalues) * np.sqrt(np.abs(eigenvalues)) * EIGENVALUE_TO_CM1
    small = [float(f) for f in frequencies if abs(f) < ZERO_FREQUENCY_CM1]
    if small:
        raise ThermoInputError(
            f"mode(s) with |nu| < {ZERO_FREQUENCY_CM1} cm^-1: {small} (degenerate with a rigid "
            "motion)"
        )
    order = np.argsort(frequencies, kind="stable")
    displacements = (complement @ vectors[:, order]) * inv_sqrt_m[:, None]
    displacements /= np.linalg.norm(displacements, axis=0)
    return NormalModes(
        frequencies_cm1=tuple(float(f) for f in frequencies[order]),
        modes_cartesian=np.asarray(displacements, dtype=np.float64),
        is_linear=linear,
        n_atoms=n,
    )
