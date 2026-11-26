"""Tests for single-site enumeration: records, orders, refusals, graph output (v0.7.0 slice 03)."""

from typing import Any

import pytest
from test_enumerator_support import (
    ENDO_ORDER,
    EXO_ORDER,
    MAX_RMSD,
    TS_KEEP,
    default_maps,
    default_nodes,
    entry,
    node,
    plan,
    reactant_map,
    record,
    selectivity_set,
    template,
    ts_map,
    ts_template,
    xyz_state,
)

import eta_rxncat.mapping
from eta_rxncat.core import EnumerationPlan, EnumerationResult, GraftResult
from eta_rxncat.mapping import AlignmentError, graft
from eta_rxncat.mapping import enumerator as module
from eta_rxncat.mapping.enumerator import (
    EnumerationError,
    enumerate_candidates,
    map_template_indices,
    projected_ts_searches,
)


def run(built: EnumerationPlan, **kwargs: Any) -> EnumerationResult:
    """Enumerate at the fixture's RMSD ceiling."""
    return enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD, **kwargs)


def spy_graft(monkeypatch: pytest.MonkeyPatch) -> list[list[int]]:
    """Record the fragment alignment of every ``graft`` call."""
    calls: list[list[int]] = []

    def spy(*args: Any) -> GraftResult:
        calls.append(list(args[2].fragment_alignment))
        return graft(*args)

    monkeypatch.setattr(module, "graft", spy)
    return calls


def test_ok_records_and_chosen_orders_of_hf1() -> None:
    """Every (node, template) is ok; endo takes order [3, 4], exo [4, 3], all RMSDs recorded."""
    (candidate,) = run(plan()).candidates
    assert candidate.status == "ok"
    assert candidate.detail is None
    assert candidate.entry_ids_by_site == {"r": "ethyl"}
    assert [(r.node_id, r.status) for r in candidate.records] == [
        ("cyclopropene", "ok"),
        ("ts_endo", "ok"),
        ("ts_exo", "ok"),
    ]
    endo, exo = record(candidate, "ts_endo"), record(candidate, "ts_exo")
    assert (endo.chosen_order_index, exo.chosen_order_index) == (0, 1)
    assert endo.alignment_rmsd_angstrom == pytest.approx(0.0354, abs=1e-3)
    assert exo.alignment_rmsd_angstrom == pytest.approx(0.0486, abs=1e-3)
    mirror = endo.order_rmsds_angstrom[1]
    assert isinstance(mirror, float)
    assert mirror == pytest.approx(0.4940, abs=1e-3)
    assert exo.order_rmsds_angstrom[0] == "graft_clash"
    for r in (endo, exo):
        assert r.close_contact_count == 0
        assert r.min_interatomic_distance_angstrom == pytest.approx(1.078, abs=1e-3)
        assert r.index_map is not None and len(r.index_map) == 24
        assert (r.product_charge, r.product_multiplicity) == (0, 1)
        assert r.constrained_core_product_indices == [0, 1, 2, 3, 4, 5]


def test_npropyl_orders() -> None:
    """The lower-fit order differs per template for the same fragment (n-propyl)."""
    (candidate,) = run(plan(library=[entry("npropyl")])).candidates
    assert candidate.status == "ok"
    assert record(candidate, "ts_endo").chosen_order_index == 1  # sp2 order [5, 4]
    assert record(candidate, "ts_exo").chosen_order_index == 0


def test_tie_goes_to_the_first_listed_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Equal RMSDs choose the first listed order."""

    def tied(*args: Any) -> GraftResult:
        return graft(*args).model_copy(update={"alignment_rmsd_angstrom": 0.05})

    monkeypatch.setattr(module, "graft", tied)
    for orders in ([ENDO_ORDER, EXO_ORDER], [EXO_ORDER, ENDO_ORDER]):
        built = plan(
            library=[entry(fragment_orders=orders)],
            maps=[ts_map("ts_endo")],
            sets=[],
        )
        chosen = record(run(built).candidates[0], "ts_endo")
        assert chosen.chosen_order_index == 0
        assert chosen.order_rmsds_angstrom == [0.05, 0.05]


def only_endo(**overrides: Any) -> EnumerationPlan:
    """Return a plan that grafts the endo TS template alone, without selectivity sets."""
    overrides.setdefault("maps", [ts_map("ts_endo")])
    return plan(sets=[], **overrides)


def refused_endo(built: EnumerationPlan, reason: str) -> Any:
    """Assert the endo record is refused for ``reason`` and the candidate unmappable."""
    (candidate,) = run(built).candidates
    found = record(candidate, "ts_endo")
    assert (found.status, found.reason) == ("refused", reason)
    assert (candidate.status, candidate.detail, candidate.graph) == ("unmappable", "ts_endo", None)
    return found


def test_mirror_order_grafts_but_is_refused_by_rmsd() -> None:
    """HF-1: the endo mirror order grafts (17 contacts); only the RMSD gate refuses it."""
    found = refused_endo(only_endo(library=[entry(fragment_orders=[EXO_ORDER])]), "alignment_rmsd")
    assert found.close_contact_count == 17
    assert found.alignment_rmsd_angstrom == pytest.approx(0.4940, abs=1e-3)
    assert found.chosen_order_index == 0
    assert found.whole_input_charge_sum_holds_bool is not None


def test_refusal_graft_clash() -> None:
    """The exo mirror order clashes."""
    built = plan(maps=[ts_map("ts_exo")], sets=[], library=[entry(fragment_orders=[ENDO_ORDER])])
    found = record(run(built).candidates[0], "ts_exo")
    assert found.reason == "graft_clash"
    assert found.order_rmsds_angstrom == ["graft_clash"]
    assert found.chosen_order_index is None
    assert found.alignment_rmsd_angstrom is None
    assert found.whole_input_charge_sum_holds_bool is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"fragment_orders": [[2, 3, 11, 10]]},  # pairs template C3 with a fragment H
        {"fragment_orders": [[2, 3, 4, 99]]},  # out of range
        {"fragment_delete": [10, 11, 12]},  # deletes a paired atom
    ],
    ids=["element", "range", "paired_delete"],
)
def test_refusal_graft_input(overrides: dict[str, Any]) -> None:
    """A request graft cannot take is ``graft_input``."""
    library = [entry(**overrides)]
    found = refused_endo(only_endo(library=library), "graft_input")
    assert found.order_rmsds_angstrom == ["graft_input"] * len(library[0].fragment_orders)


def test_wrong_length_and_alignment_error_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    """R30.7: a short order (never grafted) and an ``AlignmentError`` order are ``graft_input``."""
    calls: list[list[int]] = []

    def failing(*args: Any) -> GraftResult:
        order = list(args[2].fragment_alignment)
        calls.append(order)
        if order == EXO_ORDER:
            raise AlignmentError("degenerate pair set")
        return graft(*args)

    monkeypatch.setattr(module, "graft", failing)
    built = only_endo(library=[entry(fragment_orders=[[2, 3, 4], EXO_ORDER, ENDO_ORDER])])
    found = record(run(built).candidates[0], "ts_endo")
    assert found.status == "ok"
    assert found.chosen_order_index == 2
    assert found.order_rmsds_angstrom[:2] == ["graft_input", "graft_input"]
    assert calls == [EXO_ORDER, ENDO_ORDER]


@pytest.mark.parametrize(
    ("orders", "reasons"),
    [
        ([[2, 3, 4], ENDO_ORDER], ["graft_input", "graft_clash"]),
        ([ENDO_ORDER, [2, 3, 4]], ["graft_clash", "graft_input"]),
    ],
)
def test_all_orders_raising_report_the_first_reason(
    orders: list[list[int]], reasons: list[str]
) -> None:
    """R30.7: with no order returning, the record takes the first listed order's reason."""
    built = plan(maps=[ts_map("ts_exo")], sets=[], library=[entry(fragment_orders=orders)])
    found = record(run(built).candidates[0], "ts_exo")
    assert found.reason == reasons[0]
    assert found.order_rmsds_angstrom == reasons


@pytest.mark.parametrize("components", ["count", "two"])
def test_refusal_multi_component_template(components: str) -> None:
    """A template with a count above 1 or several components is refused before graft."""
    state = xyz_state("5_cyclopropene")
    single = template("t1", state, count=2)
    if components == "two":
        single = single.model_copy(
            update={"components": [single.components[0].model_copy(update={"count": 1})] * 2}
        )
    nodes = default_nodes() | {"cyclopropene": node("cyclopropene", [single], kind="reactant")}
    built = plan(nodes=nodes, maps=[reactant_map()], sets=[])
    (candidate,) = run(built).candidates
    found = record(candidate, "cyclopropene")
    assert found.reason == "multi_component_template"
    assert found.order_rmsds_angstrom == []
    assert candidate.status == "unmappable"


def test_refusal_composition_mismatch_against_the_first_eligible_template() -> None:
    """A lower-ranked template giving another composition is refused; rank 1 sets it."""
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1"), ts_template("t2", rank=2)])
    }
    fewer = ts_map("ts_endo", "t2", keep=[i for i in TS_KEEP if i not in (8, 9)], delete=[8, 9, 16])
    built = only_endo(nodes=nodes, maps=[ts_map("ts_endo"), fewer])
    (candidate,) = run(built).candidates
    found = record(candidate, "ts_endo", "t2")
    assert found.reason == "composition_mismatch"
    assert found.index_map is not None and len(found.index_map) == 22
    assert candidate.graph is not None
    kept = {n.id: [t.id for t in n.templates] for n in candidate.graph.nodes}
    assert kept["ts_endo"] == ["t1__ethyl"]


def test_refusal_forming_bond_deleted() -> None:
    """A forming bond on a deleted atom refuses the graft after it returned."""
    built = only_endo(maps=[ts_map("ts_endo", forming_bonds=[(1, 2), (3, 16)])])
    found = refused_endo(built, "forming_bond_deleted")
    assert found.mapped_forming_bonds is None
    assert found.alignment_rmsd_angstrom is not None


def test_ranked_templates_are_renumbered_in_declared_rank_order() -> None:
    """Rank order wins over RMSD and listing order; a refused rank leaves no gap."""
    templates = [
        ts_template("third", rank=3),  # TS1a_n, RMSD 0.035
        ts_template("first", "TS1a_x", rank=1),  # RMSD 0.049: higher, but ranked first
        ts_template("second", rank=2),
    ]
    maps = [
        ts_map("ts_endo", "first"),
        ts_map("ts_endo", "second", forming_bonds=[(3, 16)]),
        ts_map("ts_endo", "third"),
    ]
    built = only_endo(nodes=default_nodes() | {"ts_endo": node("ts_endo", templates)}, maps=maps)
    (candidate,) = run(built).candidates
    assert [r.template_id for r in candidate.records] == ["first", "second", "third"]
    assert candidate.graph is not None
    (endo,) = [n for n in candidate.graph.nodes if n.id == "ts_endo"]
    assert [(t.id, t.rank) for t in endo.templates] == [
        ("first__ethyl", 1),
        ("third__ethyl", 2),
    ]
    first_rmsd = record(candidate, "ts_endo", "first").alignment_rmsd_angstrom
    third_rmsd = record(candidate, "ts_endo", "third").alignment_rmsd_angstrom
    assert first_rmsd is not None and third_rmsd is not None and first_rmsd > third_rmsd


def test_graph_output_names_and_copies_uncovered_nodes() -> None:
    """Graph and template ids carry the candidate id; uncovered nodes are copied unchanged."""
    built = plan()
    (candidate,) = run(built).candidates
    assert candidate.graph is not None
    assert candidate.graph.name == "toy__ethyl"
    nodes = {n.id: n for n in candidate.graph.nodes}
    reference = {n.id: n for n in built.reference_graph.nodes}
    assert list(nodes) == list(reference)
    assert nodes["cp"].model_dump_json() == reference["cp"].model_dump_json()
    (endo,) = nodes["ts_endo"].templates
    assert (endo.id, endo.rank, endo.mapping) == ("t1__ethyl", 1, None)
    assert endo.components[0].state.active_atom_indices == [0, 1, 2, 3, 4, 5]
    assert len(endo.components[0].state.symbols) == 24
    assert nodes["ts_endo"].stages is None


def test_unlisted_templates_of_a_covered_node_are_dropped_and_named() -> None:
    """R30.3: dropped templates leave no record and are named on the ok candidate."""
    spare = [ts_template("zz", rank=2), ts_template("aa", rank=3)]
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1"), *spare]),
        "cp": node(
            "cp",
            [
                template("t1", xyz_state("1_cyclopentadiene")),
                template("t9", xyz_state("1_cyclopentadiene"), rank=2),
            ],
            kind="reactant",
        ),
    }
    built = plan(nodes=nodes)
    (candidate,) = run(built).candidates
    assert candidate.status == "ok"
    assert candidate.detail == "dropped_unlisted:ts_endo/aa,ts_endo/zz"
    assert {r.template_id for r in candidate.records} == {"t1"}
    assert candidate.graph is not None
    out = {n.id: n for n in candidate.graph.nodes}
    assert [t.id for t in out["ts_endo"].templates] == ["t1__ethyl"]
    assert out["cp"].model_dump_json() == nodes["cp"].model_dump_json()


def test_map_template_indices_and_mapped_forming_bonds() -> None:
    """Indices go through the index map; a deleted atom raises."""
    (candidate,) = run(plan()).candidates
    endo = record(candidate, "ts_endo")
    assert endo.mapped_forming_bonds == [(1, 2), (3, 5)]
    assert map_template_indices(endo, [17, 0, 15]) == [16, 0, 15]
    with pytest.raises(EnumerationError, match=r"\[16\]"):
        map_template_indices(endo, [0, 16])
    reordered = ts_map("ts_endo", keep=[5, 4, 3, 2, 1, 0, *TS_KEEP[6:]])
    (candidate,) = run(only_endo(maps=[reordered])).candidates
    moved = record(candidate, "ts_endo")
    assert moved.mapped_forming_bonds == [(4, 3), (2, 0)]
    assert map_template_indices(moved, [1, 2, 3, 5]) == [4, 3, 2, 0]
    unmeasured = endo.model_copy(update={"index_map": None})
    with pytest.raises(EnumerationError, match="no graft product"):
        map_template_indices(unmeasured, [0])


def test_candidates_follow_library_order_and_plan_errors() -> None:
    """One candidate per entry, in declared order; no site or a repeated map is refused."""
    result = run(plan(library=[entry("npropyl"), entry("ethyl")]))
    assert [c.candidate_id for c in result.candidates] == ["npropyl", "ethyl"]
    assert result.max_alignment_rmsd_angstrom == MAX_RMSD
    with pytest.raises(EnumerationError, match="no site"):
        run(plan(sites=[], library=[]))
    with pytest.raises(EnumerationError, match="more than once"):
        run(plan(maps=[ts_map("ts_endo"), ts_map("ts_endo")], sets=[]))


def test_projected_ts_searches() -> None:
    """Ok candidates x distinct TS nodes x eligible templates x (1 + max_research)."""
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1"), ts_template("t2", rank=2)])
    }
    maps = [*default_maps(), ts_map("ts_endo", "t2")]
    bad = entry("bad", fragment_name="ethyl", fragment_orders=[[2, 3, 4]])
    sets = [selectivity_set("a"), selectivity_set("b")]
    built = plan(nodes=nodes, maps=maps, library=[entry(), entry("npropyl"), bad], sets=sets)
    result = run(built, max_research=3)
    assert [c.status for c in result.candidates] == ["ok", "ok", "unmappable"]
    # 2 ok candidates x (2 endo + 1 exo templates) x (1 + 3)
    assert result.projected_ts_searches == 24
    assert projected_ts_searches(result.candidates, sets, max_research=3) == 24
    assert run(built).projected_ts_searches == 2 * 3 * 11
    assert projected_ts_searches(result.candidates, sets) == 66


def test_two_runs_are_byte_equal() -> None:
    """Enumeration is deterministic."""
    built = plan(library=[entry(), entry("npropyl")])
    assert run(built).model_dump_json() == run(built).model_dump_json()


def test_mapping_package_does_not_export_the_enumerator() -> None:
    """R19: the enumerator is imported from its own module."""
    assert "enumerate_candidates" not in eta_rxncat.mapping.__all__
