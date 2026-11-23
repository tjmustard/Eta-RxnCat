"""Tests for the graft report helpers (v0.4.0 slice 04; mission G6, G7, R16)."""

import numpy as np
import pytest

from eta_rxncat.core import MolecularState
from eta_rxncat.mapping import (
    core_rmsd_angstrom,
    covalent_radius_angstrom,
    junction_volumes,
    perceive_bonds,
)


def water() -> MolecularState:
    """Return a water molecule (O first)."""
    return MolecularState(
        symbols=["H", "O", "H"],
        coordinates=[[0.757, 0.0, -0.467], [0.0, 0.0, 0.117], [-0.757, 0.0, -0.467]],
        charge=0,
        spin_multiplicity=1,
    )


def test_perceive_bonds_sorted_pairs() -> None:
    """Water has exactly the two O-H bonds, as sorted (i < j) pairs; H...H is not a bond."""
    assert perceive_bonds(water()) == [(0, 1), (1, 2)]


def test_covalent_radius_matches_rdkit() -> None:
    """Covalent radii come from RDKit's periodic table."""
    from rdkit import Chem

    table = Chem.GetPeriodicTable()
    for symbol in ("H", "C", "N", "O", "F", "Cl", "Rh"):
        assert covalent_radius_angstrom(symbol) == table.GetRcovalent(symbol)


def test_core_rmsd_superposes_selected_atoms() -> None:
    """core_rmsd_angstrom superposes b[indices_b] onto a[indices_a] (Horn, unweighted)."""
    rng = np.random.default_rng(1)
    a = rng.uniform(-2.0, 2.0, size=(6, 3))
    angle = 0.8
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0, 0, 1.0]]
    )
    b = a[[5, 4, 3, 2, 1, 0]] @ rotation.T + 3.0
    assert core_rmsd_angstrom(a, b, [0, 1, 2, 3], [5, 4, 3, 2]) <= 1e-10
    assert core_rmsd_angstrom(a, b, [0, 1, 2, 3], [4, 5, 3, 2]) > 0.1


# --- Mini-requirement 7: junction volumes ---------------------------------------------------

JUNCTION_COORDS = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def test_junction_sign_positive_and_reflected_negative() -> None:
    """A non-planar junction gives +1; reflecting the appended atom through the plane gives -1."""
    bonds = [(0, 1), (0, 2), (0, 3)]
    (record,) = junction_volumes(JUNCTION_COORDS, bonds, 3, 0.05)
    assert (record.template_atom, record.appended_atom) == (0, 3)
    assert (record.neighbour_a, record.neighbour_b) == (1, 2)
    assert record.signed_volume_angstrom3 == pytest.approx(1.0, abs=1e-12)
    assert record.sign == 1 and type(record.sign) is int
    assert type(record.signed_volume_angstrom3) is float
    reflected = [*JUNCTION_COORDS[:3], [0.0, 0.0, -1.0]]
    (mirror,) = junction_volumes(reflected, bonds, 3, 0.05)
    assert mirror.signed_volume_angstrom3 == pytest.approx(-1.0, abs=1e-12)
    assert mirror.sign == -1


def test_junction_within_tolerance_has_sign_zero() -> None:
    """|V| <= tolerance gives sign 0 (a junction atom in the reference plane)."""
    coords = [*JUNCTION_COORDS[:3], [-1.0, -1.0, 0.01]]
    (record,) = junction_volumes(coords, [(0, 1), (0, 2), (0, 3)], 3, 0.05)
    assert record.signed_volume_angstrom3 == pytest.approx(0.01, abs=1e-12)
    assert record.sign == 0


def test_junction_with_fewer_than_two_kept_neighbours_is_none() -> None:
    """With one kept neighbour, the neighbours, volume and sign are all None."""
    (record,) = junction_volumes(JUNCTION_COORDS, [(0, 1), (0, 3)], 3, 0.05)
    assert record.neighbour_a is None and record.neighbour_b is None
    assert record.signed_volume_angstrom3 is None and record.sign is None


def test_junction_neighbours_are_the_two_lowest_kept() -> None:
    """The reference neighbours are the two lowest kept indices, never the appended atom."""
    coords = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [-1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.0, -1.0],
    ]
    bonds = [(0, 3), (0, 2), (0, 1), (0, 4), (0, 5), (4, 5)]
    records = junction_volumes(coords, bonds, 4, 0.05)
    assert [(r.template_atom, r.appended_atom) for r in records] == [(0, 4), (0, 5)]
    assert all((r.neighbour_a, r.neighbour_b) == (1, 2) for r in records)
    assert [r.sign for r in records] == [1, -1]


def test_junctions_sorted_and_only_cross_bonds() -> None:
    """Only (kept, appended) bonds are junctions, sorted by (template_atom, appended_atom)."""
    coords = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [1.0, 1.0, 0.5],
        [0.0, 0.0, 1.0],
    ]
    bonds = [(1, 4), (0, 3), (3, 4), (0, 1), (0, 2), (1, 2)]
    records = junction_volumes(coords, bonds, 3, 0.05)
    assert [(r.template_atom, r.appended_atom) for r in records] == [(0, 3), (1, 4)]
