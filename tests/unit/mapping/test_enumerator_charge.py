"""Charge, multiplicity and parity of enumeration (v0.7.0 slice 03; R10, R30.1, R30.A)."""

from typing import Any

import pytest
from test_enumerator_support import (
    ENDO_ORDER,
    MAX_RMSD,
    default_nodes,
    entry,
    node,
    plan,
    record,
    ts_map,
    ts_template,
    xyz_state,
)

from eta_rxncat.core import GraftResult, GraftSpec
from eta_rxncat.mapping import enumerator as module
from eta_rxncat.mapping import graft
from eta_rxncat.mapping.enumerator import _product_multiplicity, enumerate_candidates


@pytest.mark.parametrize("delta", [-1, 1])
def test_charge_delta_and_declared_doublet(delta: int) -> None:
    """The product takes template charge + delta and the declared multiplicity on every node."""
    built = plan(library=[entry(charge_delta=delta, multiplicity=2)])
    (candidate,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD).candidates
    assert candidate.status == "ok"
    for found in candidate.records:
        assert (found.product_charge, found.product_multiplicity) == (delta, 2)
    assert candidate.graph is not None
    state = candidate.graph.nodes[2].templates[0].components[0].state
    assert (state.charge, state.spin_multiplicity) == (delta, 2)


def test_multiplicity_is_inherited_and_charge_adds_to_the_template() -> None:
    """Without a declaration the template's triplet and charge carry through."""
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1", charge=2, spin_multiplicity=3)])
    }
    built = plan(nodes=nodes, maps=[ts_map("ts_endo")], sets=[], library=[entry(charge_delta=-2)])
    (candidate,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD).candidates
    found = record(candidate, "ts_endo")
    assert (found.product_charge, found.product_multiplicity) == (0, 3)


@pytest.mark.parametrize(
    "overrides",
    [{"charge_delta": 1}, {"charge_delta": -1, "multiplicity": 1}, {"multiplicity": 2}],
)
def test_parity_is_refused_before_graft(
    overrides: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An impossible charge and multiplicity never reaches graft."""
    calls: list[GraftSpec] = []

    def spy(*args: Any) -> GraftResult:
        calls.append(args[2])
        return graft(*args)

    monkeypatch.setattr(module, "graft", spy)
    built = plan(maps=[ts_map("ts_endo")], sets=[], library=[entry(**overrides)])
    (candidate,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD).candidates
    found = record(candidate, "ts_endo")
    assert (found.status, found.reason) == ("refused", "parity")
    assert found.order_rmsds_angstrom == ["parity", "parity"]
    assert found.whole_input_charge_sum_holds_bool is None
    assert calls == []


def test_whole_input_charge_sum_is_copied_from_the_chosen_graft() -> None:
    """R30.A: the record reports the graft's bool, true or false."""
    plain = plan(maps=[ts_map("ts_endo")], sets=[])
    charged = plan(
        maps=[ts_map("ts_endo")], sets=[], library=[entry(charge_delta=1, multiplicity=2)]
    )
    for built, expected in ((plain, True), (charged, False)):
        result = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD)
        found = record(result.candidates[0], "ts_endo")
        direct = graft(
            xyz_state("TS1a_n", active_atom_indices=[0, 1, 2, 3, 4, 5]),
            built.library[0].fragment,
            GraftSpec(
                template=built.sites[0].maps[0].template,
                fragment_alignment=ENDO_ORDER,
                fragment_delete=[11, 12],
                constrained_core=[0, 1, 2, 3, 4, 5],
                product_charge=found.product_charge,
                product_multiplicity=found.product_multiplicity,
            ),
        )
        assert found.whole_input_charge_sum_holds_bool is expected
        assert direct.whole_input_charge_sum_holds_bool is expected


def test_multiplicity_conflict_helper() -> None:
    """R30.1: declared else inherited; two different declarations conflict."""
    assert _product_multiplicity([None], 1) == 1
    assert _product_multiplicity([2], 1) == 2
    assert _product_multiplicity([None, 3, 3], 1) == 3
    assert _product_multiplicity([2, 4], 2) is None
