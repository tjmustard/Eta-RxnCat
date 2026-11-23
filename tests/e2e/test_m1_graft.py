"""Fixture M1, tier D: the pure graft of cyclobutene onto TS1a_n against TS1b_n (v0.4.0 slice 06).

No markers: it runs in the default suite and writes nothing. Expected values were measured by
resolve (mission HF-2…HF-8); TJ "Q6. A" sets the forming-core bound (0.10 Angstrom).
"""

from collections import Counter

import pytest
from m1 import (
    FORMING_CORE_BOUND_ANGSTROM,
    derive_map,
    heavy_map_rmsds,
    load_m1,
    reference_junction_signs,
    rmsds_to_reference,
)

from eta_rxncat.core import GraftResult
from eta_rxncat.mapping import graft


@pytest.fixture(scope="module")
def graft_and_map() -> tuple[GraftResult, list[int]]:
    """The M1 pure graft and its stated-rule map."""
    m1 = load_m1()
    result = graft(m1.template, m1.fragment, m1.spec)
    return result, derive_map(result, m1.reference).graft_to_ts1b_n_map


def test_m1_graft_formula_and_alignment(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 1: 21 atoms with TS1b_n's formula; alignment RMSD 0.11573 +- 1e-4 Angstrom."""
    result, _ = graft_and_map
    reference = load_m1().reference
    assert len(result.product.symbols) == 21
    assert Counter(result.product.symbols) == Counter(reference.symbols)
    assert result.alignment_rmsd_angstrom == pytest.approx(0.11573, abs=1e-4)
    assert result.constrained_core_product_indices == [1, 2, 3, 5]
    assert result.active_product_indices == [0, 1, 2, 3, 4, 5]
    assert (result.product.charge, result.product.spin_multiplicity) == (0, 1)


def test_m1_map_rederived_equals_yaml(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 2: the stated rule (no coordinates) gives the YAML's map; 32 isomorphisms."""
    result, mapping = graft_and_map
    m1 = load_m1()
    assert mapping == m1.config["graft_to_ts1b_n_map"]
    atom_map = derive_map(result, m1.reference)
    assert atom_map.n_isomorphisms == 32
    rows = heavy_map_rmsds(result, m1.reference, atom_map)
    print("heavy-map forming-core RMSD:", rows)
    assert [r["heavy_map"] for r in rows] == sorted(r["heavy_map"] for r in rows)
    assert len(rows) == 4


def test_m1_forming_core_rmsd(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 3: forming-core RMSD <= 0.10 Angstrom (TJ Q6 "A"); active and full are reported."""
    result, mapping = graft_and_map
    rmsds = rmsds_to_reference(result.product.coordinates, load_m1().reference, result, mapping)
    print("pure-graft RMSDs to TS1b_n:", rmsds)
    assert rmsds["forming_core_rmsd_angstrom"] <= FORMING_CORE_BOUND_ANGSTROM
    assert rmsds["forming_core_rmsd_angstrom"] == pytest.approx(0.04976, abs=1e-4)
    assert rmsds["active_rmsd_angstrom"] == pytest.approx(0.04220, abs=1e-4)
    assert rmsds["full_rmsd_angstrom"] == pytest.approx(0.7794, abs=1e-4)


def test_m1_close_contacts(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 4: exactly the four recorded contacts (1.3 x covalent radii; never raised)."""
    result, _ = graft_and_map
    contacts = {(c.i, c.j): c.distance_angstrom for c in result.close_contacts}
    print("close contacts:", contacts)
    assert set(contacts) == {(0, 15), (0, 17), (4, 16), (4, 20)}
    expected = {(0, 15): 1.9598, (0, 17): 1.1218, (4, 16): 1.9611, (4, 20): 1.1251}
    for pair, distance in expected.items():
        assert contacts[pair] == pytest.approx(distance, abs=1e-4)


def test_m1_planarity_and_junctions(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 5: planar flag True; junctions (2, 15) and (3, 16), signs reported (not gated)."""
    result, _ = graft_and_map
    assert result.planar_pair_set_bool is True
    junctions = [(j.template_atom, j.appended_atom) for j in result.junctions]
    print("pure-graft junctions:", [j.model_dump() for j in result.junctions])
    assert junctions == [(2, 15), (3, 16)]
    for junction in result.junctions:
        assert junction.signed_volume_angstrom3 == pytest.approx(-0.0006, abs=1e-4)


def test_m1_reference_junctions_nonzero(graft_and_map: tuple[GraftResult, list[int]]) -> None:
    """Check 6: TS1b_n's junction volumes under the map are nonzero (+-0.8505 A^3)."""
    result, mapping = graft_and_map
    rows = reference_junction_signs(result, load_m1().reference, mapping, 0.05)
    print("TS1b_n junctions under the map:", rows)
    assert [(r["template_atom"], r["appended_atom"]) for r in rows] == [(2, 15), (3, 16)]
    assert [r["sign"] for r in rows] == [1, -1]
    for row, volume in zip(rows, (0.8505, -0.8505), strict=True):
        assert row["signed_volume_angstrom3"] == pytest.approx(volume, abs=1e-4)
