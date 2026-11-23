"""Report helpers for grafts: bond perception, covalent radii, core RMSD and junction volumes.

RDKit is imported inside the functions that need it, never at module level, so importing
``eta_rxncat.mapping`` loads no RDKit.
"""

from collections.abc import Sequence
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from eta_rxncat.core import JunctionVolume, MolecularState
from eta_rxncat.mapping.align import superpose


def perceive_bonds(state: MolecularState) -> list[tuple[int, int]]:
    """Perceive the bonds of a structure from its coordinates alone.

    Builds an RDKit molecule with one atom per symbol and a conformer from the coordinates, then
    runs ``rdDetermineBonds.DetermineConnectivity`` with its defaults (connect-the-dots with
    ``covFactor`` 1.3).

    Args:
        state: The structure.

    Returns:
        The bonds as sorted ``(i, j)`` pairs with ``i < j``.
    """
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds
    from rdkit.Geometry import Point3D

    mol = Chem.RWMol()
    for symbol in state.symbols:
        mol.AddAtom(Chem.Atom(symbol))
    conformer = Chem.Conformer(len(state.symbols))
    for index, (x, y, z) in enumerate(state.coordinates):
        conformer.SetAtomPosition(index, Point3D(x, y, z))
    mol.AddConformer(conformer, assignId=True)
    rdDetermineBonds.DetermineConnectivity(mol)
    bonds = []
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bonds.append((min(i, j), max(i, j)))
    return sorted(bonds)


def covalent_radius_angstrom(symbol: str) -> float:
    """Return RDKit's covalent radius of an element (``GetPeriodicTable().GetRcovalent``)."""
    from rdkit import Chem

    return float(Chem.GetPeriodicTable().GetRcovalent(symbol))


def core_rmsd_angstrom(
    a_coords: ArrayLike,
    b_coords: ArrayLike,
    indices_a: Sequence[int],
    indices_b: Sequence[int],
) -> float:
    """Superpose ``b[indices_b]`` onto ``a[indices_a]`` (Horn, unweighted) and return the RMSD.

    Raises:
        AlignmentError: If the selected pair sets cannot be superposed.
    """
    a = np.asarray(a_coords, dtype=np.float64)
    b = np.asarray(b_coords, dtype=np.float64)
    return superpose(b[list(indices_b)], a[list(indices_a)]).rmsd_angstrom


def junction_volumes(
    coords: ArrayLike,
    source_bonds: Sequence[tuple[int, int]],
    n_kept: int,
    tolerance: float,
) -> list[JunctionVolume]:
    """Measure the handedness of every junction bond of a graft product.

    A junction is a source bond ``(t, a)`` with ``t < n_kept <= a`` (kept template atom, appended
    atom). Its reference neighbours ``n1 < n2`` are the two lowest indices among ``t``'s
    source-graph neighbours that are ``< n_kept`` and not ``a``. The signed volume is
    ``V = (p_a - p_t) . [(p_n1 - p_t) x (p_n2 - p_t)]`` in cubic Angstrom; its sign is 0 when
    ``|V| <= tolerance``. With fewer than two such neighbours, the neighbours, ``V`` and the sign
    are all ``None``.

    Args:
        coords: Product coordinates, (n, 3), Angstrom.
        source_bonds: The graft's source graph in product indices.
        n_kept: Number of kept template atoms (they come first in the product).
        tolerance: Volume magnitude at or below which the sign is 0, cubic Angstrom.

    Returns:
        One record per junction, sorted by ``(template_atom, appended_atom)``.
    """
    points = np.asarray(coords, dtype=np.float64)
    neighbours: dict[int, set[int]] = {}
    for i, j in source_bonds:
        neighbours.setdefault(i, set()).add(j)
        neighbours.setdefault(j, set()).add(i)
    records = []
    for i, j in sorted({(min(b), max(b)) for b in source_bonds}):
        if not i < n_kept <= j:
            continue
        t, a = i, j
        reference = sorted(n for n in neighbours[t] if n < n_kept and n != a)[:2]
        if len(reference) < 2:
            records.append(
                JunctionVolume(
                    template_atom=t,
                    appended_atom=a,
                    neighbour_a=None,
                    neighbour_b=None,
                    signed_volume_angstrom3=None,
                    sign=None,
                )
            )
            continue
        n1, n2 = reference
        volume = float(
            np.dot(points[a] - points[t], np.cross(points[n1] - points[t], points[n2] - points[t]))
        )
        sign: Literal[-1, 0, 1] = 0 if abs(volume) <= tolerance else (1 if volume > 0 else -1)
        records.append(
            JunctionVolume(
                template_atom=t,
                appended_atom=a,
                neighbour_a=n1,
                neighbour_b=n2,
                signed_volume_angstrom3=volume,
                sign=sign,
            )
        )
    return records
