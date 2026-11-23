"""Idealised test geometries built from known parameters, and toy Hessians with chosen modes.

Every geometry's atom order equals ``Chem.AddHs(Chem.MolFromSmiles(smiles))`` for the SMILES
named beside it, so the symmetry-number code can pair them.
"""

import math

import numpy as np
from numpy.typing import NDArray

from eta_rxncat.core import MolecularState
from eta_rxncat.thermo import atomic_masses_amu

TETRA = math.degrees(math.acos(-1.0 / 3.0))
"""The ideal tetrahedral angle (degrees)."""

# CODATA 2018, written out here so the toy Hessians do not lean on eta_rxncat.thermo.constants.
_HARTREE_J = 4.3597447222071e-18
_BOHR_M = 0.529177210903e-10
_AMU_KG = 1.66053906660e-27
_C_CM = 299792458.0 * 100.0


def cm1_to_eigenvalue(wavenumber_cm1: float) -> float:
    """Return the mass-weighted Hessian eigenvalue (Eh/(Bohr^2 amu)) of a wavenumber."""
    omega = 2.0 * math.pi * _C_CM * abs(wavenumber_cm1)  # rad/s
    value = omega**2 * _BOHR_M**2 * _AMU_KG / _HARTREE_J
    return math.copysign(value, wavenumber_cm1)


def state(
    symbols: list[str], coords: NDArray[np.float64] | list[list[float]], mult: int = 1
) -> MolecularState:
    """Return a neutral state."""
    return MolecularState(
        symbols=symbols,
        coordinates=np.asarray(coords, dtype=np.float64).tolist(),
        charge=0,
        spin_multiplicity=mult,
    )


def place(
    a: NDArray[np.float64],
    b: NDArray[np.float64],
    c: NDArray[np.float64],
    bond: float,
    angle_deg: float,
    dihedral_deg: float,
) -> NDArray[np.float64]:
    """Return atom D with |CD| = bond, angle BCD and dihedral ABCD (NeRF)."""
    bc = c - b
    bc /= np.linalg.norm(bc)
    n = np.cross(b - a, bc)
    n /= np.linalg.norm(n)
    m = np.cross(n, bc)
    theta = math.radians(angle_deg)
    phi = math.radians(dihedral_deg)
    d2 = np.array(
        [
            -bond * math.cos(theta),
            bond * math.sin(theta) * math.cos(phi),
            bond * math.sin(theta) * math.sin(phi),
        ]
    )
    return np.asarray(c + d2[0] * bc + d2[1] * m + d2[2] * n, dtype=np.float64)


def water(h_shift: float = 0.0) -> MolecularState:
    """Return C2v water (SMILES ``O``), optionally moving H1 by ``h_shift`` Angstrom along x."""
    half = math.radians(104.5 / 2.0)
    r = 0.9572
    coords = [
        [0.0, 0.0, 0.0],
        [r * math.sin(half) + h_shift, 0.0, r * math.cos(half)],
        [-r * math.sin(half), 0.0, r * math.cos(half)],
    ]
    return state(["O", "H", "H"], coords)


def ammonia() -> MolecularState:
    """Return C3v ammonia (SMILES ``N``)."""
    r, h = 0.94, 0.38
    coords = [[0.0, 0.0, h]] + [
        [r * math.cos(2 * math.pi * k / 3), r * math.sin(2 * math.pi * k / 3), 0.0]
        for k in range(3)
    ]
    return state(["N", "H", "H", "H"], coords)


TET_DIRS = np.array(
    [[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=np.float64
) / math.sqrt(3)


def methane() -> MolecularState:
    """Return Td methane (SMILES ``C``)."""
    return state(["C"] + ["H"] * 4, np.vstack([np.zeros(3), 1.09 * TET_DIRS]))


def ethylene() -> MolecularState:
    """Return D2h ethylene (SMILES ``C=C``: C, C, H on C0 x 2, H on C1 x 2)."""
    coords = [
        [0.665, 0.0, 0.0],
        [-0.665, 0.0, 0.0],
        [1.23, 0.92, 0.0],
        [1.23, -0.92, 0.0],
        [-1.23, 0.92, 0.0],
        [-1.23, -0.92, 0.0],
    ]
    return state(["C", "C", "H", "H", "H", "H"], coords)


def benzene() -> MolecularState:
    """Return D6h benzene (SMILES ``c1ccccc1``: C0-C5, then H on C0-C5)."""
    angles = [2 * math.pi * k / 6 for k in range(6)]
    carbons = [[1.39 * math.cos(t), 1.39 * math.sin(t), 0.0] for t in angles]
    hydrogens = [[2.47 * math.cos(t), 2.47 * math.sin(t), 0.0] for t in angles]
    return state(["C"] * 6 + ["H"] * 6, carbons + hydrogens)


def co2(bend: float = 0.0) -> MolecularState:
    """Return CO2 (SMILES ``O=C=O``), with the first O moved ``bend`` Angstrom off the axis."""
    return state(["O", "C", "O"], [[-1.16, bend, 0.0], [0.0, 0.0, 0.0], [1.16, 0.0, 0.0]])


def hcn() -> MolecularState:
    """Return linear HCN (SMILES ``C#N``: C, N, H)."""
    return state(["C", "N", "H"], [[0.0, 0.0, 0.0], [1.156, 0.0, 0.0], [-1.066, 0.0, 0.0]])


def butane(dihedral_deg: float) -> MolecularState:
    """Return n-butane (SMILES ``CCCC``) with ideal tetrahedral angles and staggered methyls.

    Atom order: C0-C3, H on C0 x 3, H on C1 x 2, H on C2 x 2, H on C3 x 3. Each H is placed by the
    same rule on both halves, so the C0-C1-C2-C3 dihedral alone sets the point group (180: C2h,
    otherwise C2).
    """
    cc, ch = 1.53, 1.09
    c1 = np.array([0.0, 0.0, 0.0])
    c2 = np.array([cc, 0.0, 0.0])
    c0 = place(np.array([cc, 1.0, 0.0]), c2, c1, cc, TETRA, 0.0)
    c3 = place(c0, c1, c2, cc, TETRA, dihedral_deg)
    h_c0 = [place(c2, c1, c0, ch, TETRA, d) for d in (180.0, 60.0, -60.0)]
    h_c1 = [place(c3, c2, c1, ch, TETRA, dihedral_deg + d) for d in (120.0, -120.0)]
    h_c2 = [place(c0, c1, c2, ch, TETRA, dihedral_deg + d) for d in (120.0, -120.0)]
    h_c3 = [place(c1, c2, c3, ch, TETRA, d) for d in (180.0, 60.0, -60.0)]
    coords = np.vstack([c0, c1, c2, c3, *h_c0, *h_c1, *h_c2, *h_c3])
    return state(["C"] * 4 + ["H"] * 10, coords)


def neopentane() -> MolecularState:
    """Return staggered Td neopentane (SMILES ``CC(C)(C)C``: C0, C1 centre, C2-C4, then H by C)."""
    cc, ch = 1.53, 1.09
    centre = np.zeros(3)
    # C0, C2, C3, C4 along the four tetrahedral directions; methyl m's H point along -u_k, k != m.
    order = [0, 1, 2, 3]
    carbons = [cc * TET_DIRS[k] for k in order]
    hydrogens = []
    for m in order:
        for k in order:
            if k != m:
                hydrogens.append(carbons[m] - ch * TET_DIRS[k])
    coords = np.vstack([carbons[0], centre, carbons[1], carbons[2], carbons[3], *hydrogens])
    return state(["C"] * 5 + ["H"] * 12, coords)


def rigid_basis(
    coords: NDArray[np.float64], masses: NDArray[np.float64], linear: bool
) -> NDArray[np.float64]:
    """Return an orthonormal basis of the mass-weighted rigid motions (3N x 5 or 6)."""
    n = coords.shape[0]
    sqrt_m = np.sqrt(masses)
    r = coords - (masses[:, None] * coords).sum(axis=0) / masses.sum()
    vectors = []
    for axis in range(3):
        t = np.zeros((n, 3))
        t[:, axis] = sqrt_m
        vectors.append(t.reshape(-1))
        unit = np.zeros(3)
        unit[axis] = 1.0
        vectors.append((np.cross(unit, r) * sqrt_m[:, None]).reshape(-1))
    u, s, _ = np.linalg.svd(np.column_stack(vectors), full_matrices=True)
    rank = 5 if linear else 6
    return np.asarray(u[:, :rank], dtype=np.float64)


def hessian_with_modes(
    st: MolecularState, wavenumbers_cm1: list[float], *, linear: bool, seed: int = 7
) -> NDArray[np.float64]:
    """Return a Cartesian Hessian (Eh/Bohr^2) whose vibrations are exactly ``wavenumbers_cm1``.

    The rigid motions get eigenvalue 0; the vibrations get random orthonormal directions in their
    complement.
    """
    coords = np.asarray(st.coordinates, dtype=np.float64)
    masses = atomic_masses_amu(st.symbols)
    rigid = rigid_basis(coords, masses, linear)
    dim = 3 * len(st.symbols)
    rng = np.random.default_rng(seed)
    random = rng.standard_normal((dim, dim - rigid.shape[1]))
    random -= rigid @ (rigid.T @ random)
    q, _ = np.linalg.qr(random)
    lam = np.array([cm1_to_eigenvalue(f) for f in wavenumbers_cm1])
    mass_weighted = q @ np.diag(lam) @ q.T
    sqrt_m = np.repeat(np.sqrt(masses), 3)
    hessian = mass_weighted * np.outer(sqrt_m, sqrt_m)
    return np.asarray(0.5 * (hessian + hessian.T), dtype=np.float64)
