"""Offline tests of the mapped Tier 4 helpers (slice 10): the exo graft, the graph, G6 pruning."""

from types import SimpleNamespace
from typing import Any

import pytest
from fixtures import t4
from t4 import PairRun, exo_graft, mapped_graph, pruning_gate, seed_payload
from test_t3_inputs import formula

from eta_rxncat.core import PruningDecision
from eta_rxncat.orchestrator import NodeOutcome, SelectivityRun

FIXTURE = t4("t4_mapped_selectivity_pruned.yaml")
NODE = "downstream_exo_minor"


def test_exo_graft_derives_the_map_the_fixture_holds() -> None:
    """The R2 rule applied to the graft and Liu's TS1b_x equals the YAML map (slice 08)."""
    result, mapping = exo_graft(FIXTURE)
    assert mapping == list(FIXTURE.pathway("exo").start_to_reference_map)
    assert formula(result.product.symbols) == "C9H12" and result.close_contacts == []
    assert result.constrained_core_product_indices == [1, 2, 3, 5]


def test_exo_graft_refuses_a_map_that_disagrees(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the derived map differed from the fixture's, the run stops instead of mislabelling."""
    import t4 as module

    monkeypatch.setattr(
        module, "derive_map", lambda *_: SimpleNamespace(graft_to_ts1b_n_map=[0, 1, 2])
    )
    with pytest.raises(ValueError, match="differs"):
        exo_graft(FIXTURE)


def test_mapped_graph_has_the_rule_and_the_downstream_node() -> None:
    """Two priority-1 TS nodes carrying the pathway labels, the 1.5 rule, P1b_x at priority 2."""
    starts = {p.pathway: p.start_state("xtb") for p in FIXTURE.pathways if p.pathway == "endo"}
    exo_result, _ = exo_graft(FIXTURE)
    starts["exo"] = exo_result.product.model_copy(
        update={"active_atom_indices": [0, 1, 2, 3, 4, 5]}
    )
    graph = mapped_graph(FIXTURE, starts)
    by_id = {n.id: n for n in graph.nodes}
    assert by_id["TS1b_n"].pathway == "endo" and by_id["TS1b_n"].priority == 1
    assert by_id["TS1b_x"].pathway == "exo" and by_id["TS1b_x"].priority == 1
    assert by_id[NODE].pathway == "exo" and by_id[NODE].priority == 2
    (rule,) = graph.pathway_pruning_rules
    assert rule.threshold_kcal_mol == 1.5 and rule.pathways == ("endo", "exo")


# --- G6 ----------------------------------------------------------------------------------------


def decision(ddg: float | None, pruned: list[str]) -> PruningDecision:
    """A decision of the 1.5 rule."""
    return PruningDecision(
        rule_id="endo_exo_ddG",
        pathways=("endo", "exo"),
        ddG_dagger_kcal_mol=ddg,
        signed_ddG_dagger_kcal_mol={} if ddg is None else {"exo_vs_endo": ddg},
        threshold_kcal_mol=1.5,
        pruned_node_ids=pruned,
        reason="stub",
    )


def run(
    ddg: float | None,
    status: str,
    *,
    species_rows: int,
    decided: PruningDecision | None = None,
) -> PairRun:
    """A pair run with one decision and one downstream outcome (two reactant species)."""
    pruned = [NODE] if status == "pruned" else []
    result = None
    if status == "computed":
        stage = SimpleNamespace(rows_created=0, cache_hits=1)
        result = SimpleNamespace(
            ensemble=SimpleNamespace(records=[object()]),
            metrics=SimpleNamespace(
                stages={k: stage for k in ("conformer_search", "geometry_opt", "frequency")}
            ),
            keys={k: ("k",) for k in ("conformer_search", "geometry_opt", "frequency")},
        )
    node = NodeOutcome(NODE, "exo", status, tuple(["endo_exo_ddG"] if pruned else []), result)  # type: ignore[arg-type]
    selectivity = SelectivityRun({}, None, (decided or decision(ddg, pruned),), {NODE: node})
    return PairRun(
        reactants={"cp": None, "cb": None},  # type: ignore[dict-item]
        runs={},
        score=None,
        barriers={},
        barrier_errors={},
        selectivity=selectivity,
        store_rows={"conformer_search": 2 + species_rows},
    )


def gate(first: PairRun, second: PairRun | None = None) -> dict[str, Any]:
    """The G6 gate of a first and second run."""
    return pruning_gate(FIXTURE, first, second or first)


def test_above_the_threshold_prunes_with_no_species_work() -> None:
    """GFN2-like +1.753: pruned, no result, no downstream rows."""
    got = gate(run(1.753, "pruned", species_rows=0))
    assert got["status"] == "pass" and got["branch"] == "pruned"
    assert got["margin_to_threshold_kcal_mol"] == pytest.approx(0.253)
    assert got["pruned_node_ids"] == [NODE]


def test_below_the_threshold_computes_the_downstream_node() -> None:
    """UMA-like +1.410: computed, with its result and one species' rows."""
    got = gate(run(1.410, "computed", species_rows=1))
    assert got["status"] == "pass" and got["branch"] == "computed"
    assert got["margin_to_threshold_kcal_mol"] == pytest.approx(-0.09)


def test_exactly_the_threshold_computes() -> None:
    """At 1.5 nothing is pruned (strict), so the node is computed."""
    assert gate(run(1.5, "computed", species_rows=1))["expected_branch"] == "computed"
    assert gate(run(1.5, "pruned", species_rows=0))["status"] == "fail"


def test_a_branch_that_contradicts_the_measured_value_fails() -> None:
    """Pruned below the threshold, or computed above it, fails G6."""
    assert gate(run(1.410, "pruned", species_rows=0))["status"] == "fail"
    assert gate(run(1.753, "computed", species_rows=1))["status"] == "fail"


def test_a_pruned_node_that_left_rows_fails() -> None:
    """Pruned but the store has downstream rows: the node was not really skipped."""
    assert gate(run(1.753, "pruned", species_rows=1))["status"] == "fail"


def test_second_run_must_repeat_the_decision() -> None:
    """A different decision (or outcome) in the second run fails the gate."""
    first = run(1.753, "pruned", species_rows=0)
    assert gate(first, run(1.753, "pruned", species_rows=0))["status"] == "pass"
    assert gate(first, run(1.760, "pruned", species_rows=0))["status"] == "fail"
    assert gate(first, run(1.410, "computed", species_rows=1))["status"] == "fail"


def test_no_decision_fails() -> None:
    """A run without a selectivity decision cannot pass."""
    empty = PairRun({}, {}, None, {}, {}, selectivity=SelectivityRun({}, None, (), {}))
    assert gate(empty)["status"] == "fail"


def test_seed_payload_names_the_case() -> None:
    """The regression compares with ``t3_<case>``: the mapped endo seed is ts1b_n."""
    run_ = SimpleNamespace(
        runs={"endo": SimpleNamespace(seed_result=SimpleNamespace())}, barriers={"endo": None}
    )
    from unittest import mock

    with mock.patch("t4.ts_payload", return_value={}):
        assert seed_payload(run_, "endo", FIXTURE, case="ts1b_n")["case"] == "ts1b_n"  # type: ignore[arg-type]
        assert seed_payload(run_, "endo", FIXTURE)["case"] == "ts1a_n"  # type: ignore[arg-type]
