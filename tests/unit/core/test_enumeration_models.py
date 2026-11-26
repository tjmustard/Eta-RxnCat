"""Tests for the v0.7.0 enumeration, selectivity-set and fallback contracts."""

from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from eta_rxncat.core import (
    AtomMappingSpec,
    Component,
    EnumeratedCandidate,
    EnumerationPlan,
    EnumerationResult,
    EnumerationSite,
    FallbackAttempt,
    FallbackRecord,
    GraftRecord,
    GraftRefusalReason,
    LibraryEntry,
    MolecularState,
    PathwaySpec,
    ReactionGraph,
    ReactionNode,
    SelectivitySet,
    SiteTemplateMap,
    TemplateGeometry,
)


def methane() -> MolecularState:
    """Return a neutral singlet methane (atom 0 is carbon)."""
    return MolecularState(
        symbols=["C", "H", "H", "H", "H"],
        coordinates=[
            [0.0, 0.0, 0.0],
            [0.63, 0.63, 0.63],
            [-0.63, -0.63, 0.63],
            [-0.63, 0.63, -0.63],
            [0.63, -0.63, -0.63],
        ],
        charge=0,
        spin_multiplicity=1,
    )


def reference_graph() -> ReactionGraph:
    """Return a two-node graph, ``reactant`` and ``ts``, each with template ``t1``."""
    nodes = [
        ReactionNode(
            id=node_id,
            label=node_id,
            kind=kind,
            priority=1,
            templates=[
                TemplateGeometry(id="t1", rank=1, components=[Component(state=methane(), count=1)])
            ],
        )
        for node_id, kind in (("reactant", "reactant"), ("ts", "transition_state"))
    ]
    return ReactionGraph(schema_version=1, name="toy", nodes=nodes)


def mapping(**overrides: Any) -> AtomMappingSpec:
    """Return a mapping over methane's atoms."""
    data: dict[str, Any] = {"keep": [0, 1, 2, 3], "delete": [4], "alignment": [0, 1, 2]}
    data.update(overrides)
    return AtomMappingSpec(**data)


def site_map(**overrides: Any) -> SiteTemplateMap:
    """Return a valid SiteTemplateMap on node ``ts``."""
    data: dict[str, Any] = {
        "node_id": "ts",
        "template_id": "t1",
        "template": mapping(),
        "constrained_core": [0],
        "forming_bonds": [(0, 1), (2, 3)],
    }
    data.update(overrides)
    return SiteTemplateMap(**data)


def site(**overrides: Any) -> EnumerationSite:
    """Return a valid site ``s1``."""
    data: dict[str, Any] = {"id": "s1", "maps": [site_map()]}
    data.update(overrides)
    return EnumerationSite(**data)


def entry(**overrides: Any) -> LibraryEntry:
    """Return a valid library entry ``e1`` for site ``s1``."""
    data: dict[str, Any] = {
        "id": "e1",
        "site_id": "s1",
        "fragment": methane(),
        "fragment_orders": [[0, 1, 2], [0, 2, 1]],
        "fragment_delete": [],
    }
    data.update(overrides)
    return LibraryEntry(**data)


def selectivity_set(**overrides: Any) -> SelectivitySet:
    """Return a valid one-pathway selectivity set."""
    data: dict[str, Any] = {
        "id": "set1",
        "pathways": [PathwaySpec(pathway="endo", node_id="ts", expected_face=(1, 1))],
        "reactant_node_ids": ["reactant"],
    }
    data.update(overrides)
    return SelectivitySet(**data)


def plan(**overrides: Any) -> EnumerationPlan:
    """Return a valid plan, with overrides applied."""
    data: dict[str, Any] = {
        "reference_graph": reference_graph(),
        "sites": [site()],
        "library": [entry()],
        "selectivity_sets": [selectivity_set()],
        "max_candidates": 4,
    }
    data.update(overrides)
    return EnumerationPlan(**data)


def graft_record(**overrides: Any) -> GraftRecord:
    """Return a valid ``ok`` graft record."""
    data: dict[str, Any] = {
        "entry_id": "e1",
        "site_id": "s1",
        "node_id": "ts",
        "template_id": "t1",
        "status": "ok",
        "order_rmsds_angstrom": [0.04, "graft_clash"],
        "chosen_order_index": 0,
        "alignment_rmsd_angstrom": 0.04,
        "min_interatomic_distance_angstrom": 1.08,
        "close_contact_count": 0,
        "index_map": [("template", 0), ("fragment", 3)],
        "product_charge": 0,
        "product_multiplicity": 1,
        "mapped_forming_bonds": [(0, 1)],
        "constrained_core_product_indices": [0],
    }
    data.update(overrides)
    return GraftRecord(**data)


def candidate(**overrides: Any) -> EnumeratedCandidate:
    """Return a valid ``ok`` candidate."""
    data: dict[str, Any] = {
        "candidate_id": "e1",
        "entry_ids_by_site": {"s1": "e1"},
        "status": "ok",
        "graph": reference_graph(),
        "records": [graft_record()],
    }
    data.update(overrides)
    return EnumeratedCandidate(**data)


def attempt(rank: int = 1, **overrides: Any) -> FallbackAttempt:
    """Return a fallback attempt at ``rank``."""
    data: dict[str, Any] = {
        "template_id": f"t{rank}",
        "rank": rank,
        "outcome": "fell_through",
        "reason": "seed:face_mismatch_pathway",
        "wall_time_s": 1.5,
    }
    data.update(overrides)
    return FallbackAttempt(**data)


def fallback(**overrides: Any) -> FallbackRecord:
    """Return a record whose second attempt was chosen."""
    data: dict[str, Any] = {
        "node_id": "ts",
        "attempts": [attempt(1), attempt(2, outcome="chosen", reason=None)],
        "chosen_template_id": "t2",
    }
    data.update(overrides)
    return FallbackRecord(**data)


ROUND_TRIP: list[BaseModel] = [
    site_map(),
    site(),
    entry(charge_delta=-1, multiplicity=2),
    PathwaySpec(pathway="exo", node_id="ts", expected_face=(-1, -1)),
    selectivity_set(),
    plan(),
    graft_record(),
    graft_record(
        status="refused",
        reason="parity",
        order_rmsds_angstrom=[],
        chosen_order_index=None,
        alignment_rmsd_angstrom=None,
        min_interatomic_distance_angstrom=None,
        close_contact_count=None,
        index_map=None,
        product_charge=None,
        product_multiplicity=None,
        mapped_forming_bonds=None,
        constrained_core_product_indices=None,
    ),
    candidate(),
    candidate(status="unmappable", detail="ts", graph=None),
    EnumerationResult(
        candidates=[candidate()], max_alignment_rmsd_angstrom=0.15, projected_ts_searches=11
    ),
    attempt(),
    fallback(),
    fallback(attempts=[], chosen_template_id=None, stop_reason="all_templates_failed"),
]


@pytest.mark.parametrize("model", ROUND_TRIP, ids=lambda m: type(m).__name__)
def test_json_round_trip(model: BaseModel) -> None:
    """Every contract survives a JSON round trip unchanged."""
    assert type(model).model_validate_json(model.model_dump_json()) == model


def test_models_are_strict_and_frozen() -> None:
    """Unknown keys are refused and instances cannot be mutated."""
    with pytest.raises(ValidationError, match="extra"):
        EnumerationSite.model_validate({"id": "s1", "maps": [], "note": "x"})
    with pytest.raises(ValidationError, match="frozen"):
        site().id = "other"  # type: ignore[misc]


def test_refusal_reasons_are_the_closed_set() -> None:
    """The refusal reasons are exactly the mission's closed set, and nothing else validates."""
    assert get_args(GraftRefusalReason) == (
        "graft_input",
        "graft_clash",
        "alignment_rmsd",
        "composition_mismatch",
        "parity",
        "multiplicity_conflict",
        "multi_component_template",
        "site_atom_deleted",
        "forming_bond_deleted",
    )
    with pytest.raises(ValidationError):
        graft_record(status="refused", reason="something_else")
    with pytest.raises(ValidationError):
        graft_record(order_rmsds_angstrom=["something_else"])
    with pytest.raises(ValidationError):
        graft_record(order_rmsds_angstrom=[float("inf")])


@pytest.mark.parametrize("bonds", [[], [(0, 1)], [(0, 1), (0, 2), (2, 3)]])
def test_forming_bonds_accepted(bonds: list[tuple[int, int]]) -> None:
    """Sorted distinct non-negative pairs are accepted."""
    assert site_map(forming_bonds=bonds).forming_bonds == bonds


@pytest.mark.parametrize(
    "bonds",
    [[(1, 0)], [(1, 1)], [(-1, 2)], [(2, 3), (0, 1)], [(0, 1), (0, 1)]],
    ids=["reversed", "self", "negative", "unsorted", "duplicate"],
)
def test_forming_bonds_refused(bonds: list[tuple[int, int]]) -> None:
    """Reversed, self, negative, unsorted and repeated pairs are refused."""
    with pytest.raises(ValidationError):
        site_map(forming_bonds=bonds)


def test_template_anchors_refused() -> None:
    """The site's mapping may not carry anchors."""
    with pytest.raises(ValidationError, match="anchors"):
        site_map(template=mapping(anchors=[1]))
    assert site_map().template.anchors == []


@pytest.mark.parametrize(
    "orders", [[], [[0, 1, 2], [0, 1, 2]], [[0, -1, 2]]], ids=["none", "repeated", "negative"]
)
def test_fragment_orders_refused(orders: list[list[int]]) -> None:
    """At least one order, no repeats, no negative atom."""
    with pytest.raises(ValidationError):
        entry(fragment_orders=orders)


def test_fragment_orders_accepted() -> None:
    """One order, or several distinct ones, are accepted."""
    assert entry(fragment_orders=[[2, 1, 0]]).fragment_orders == [[2, 1, 0]]
    assert len(entry().fragment_orders) == 2
    assert entry().charge_delta == 0
    assert entry().multiplicity is None


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"sites": [site(), site()]}, "duplicate site ids"),
        ({"library": [entry(), entry()]}, "duplicate library entry ids"),
        ({"library": [entry(site_id="s9")]}, "unknown site id"),
        ({"sites": [site(maps=[site_map(node_id="nope")])]}, "unknown node id"),
        ({"sites": [site(maps=[site_map(template_id="t9")])]}, "has no template"),
        (
            {
                "selectivity_sets": [
                    selectivity_set(
                        pathways=[PathwaySpec(pathway="a", node_id="x", expected_face=(1,))]
                    )
                ]
            },
            "unknown node ids",
        ),
        ({"selectivity_sets": [selectivity_set(reactant_node_ids=["x"])]}, "unknown node ids"),
        ({"max_candidates": 0}, "greater than or equal to 1"),
    ],
    ids=["site", "entry", "site_ref", "node", "template", "set_node", "set_reactant", "cap"],
)
def test_plan_refused(overrides: dict[str, Any], match: str) -> None:
    """Each cross-reference of a plan is checked."""
    with pytest.raises(ValidationError, match=match):
        plan(**overrides)


def test_plan_accepted() -> None:
    """A consistent plan with two sites and two entries is accepted."""
    two = plan(
        sites=[site(), site(id="s2")],
        library=[entry(), entry(id="e2", site_id="s2")],
        max_candidates=1,
    )
    assert [s.id for s in two.sites] == ["s1", "s2"]


@pytest.mark.parametrize("face", [(), (0,), (1, 2)])
def test_expected_face_refused(face: tuple[int, ...]) -> None:
    """The expected face is a non-empty tuple of +1/-1."""
    with pytest.raises(ValidationError):
        PathwaySpec(pathway="endo", node_id="ts", expected_face=face)


def test_expected_face_accepted() -> None:
    """Both signs are accepted."""
    assert PathwaySpec(pathway="p", node_id="ts", expected_face=(1, -1)).expected_face == (1, -1)


def test_candidate_refused() -> None:
    """The graph goes with ``ok``, and a non-``ok`` candidate needs a detail."""
    with pytest.raises(ValidationError, match="graph must be present"):
        candidate(graph=None)
    for status in ("unmappable", "inconsistent"):
        with pytest.raises(ValidationError, match="graph must be present"):
            candidate(status=status, detail="d")
        with pytest.raises(ValidationError, match="detail is required"):
            candidate(status=status, graph=None)


def test_candidate_accepted() -> None:
    """An ``ok`` candidate has a graph; the others carry a detail and none."""
    assert candidate().graph is not None
    for status in ("unmappable", "inconsistent"):
        assert candidate(status=status, graph=None, detail="d").detail == "d"


@pytest.mark.parametrize(
    "overrides",
    [
        {"chosen_template_id": None},
        {"stop_reason": "x"},
        {"attempts": [], "chosen_template_id": None},
        {"attempts": []},
        {"attempts": [attempt(2), attempt(1)]},
        {"attempts": [attempt(1), attempt(1)]},
    ],
    ids=["neither", "both", "empty_neither", "empty_chosen", "descending", "tied"],
)
def test_fallback_record_refused(overrides: dict[str, Any]) -> None:
    """Exactly one ending, a stop reason without attempts, and increasing ranks."""
    with pytest.raises(ValidationError):
        fallback(**overrides)


def test_fallback_record_accepted() -> None:
    """A chosen record, a stopped one and an empty one with a stop reason are accepted."""
    assert fallback().chosen_template_id == "t2"
    stopped = fallback(attempts=[attempt(1)], chosen_template_id=None, stop_reason="stopped:x")
    assert stopped.stop_reason == "stopped:x"
    empty = fallback(attempts=[], chosen_template_id=None, stop_reason="all_templates_failed")
    assert empty.attempts == []


def test_graft_record_whole_input_charge_sum() -> None:
    """R30.A: the reported charge-sum bool defaults to None, takes a bool and stays strict."""
    assert graft_record().whole_input_charge_sum_holds_bool is None
    for value in (True, False):
        record = graft_record(whole_input_charge_sum_holds_bool=value)
        assert record.whole_input_charge_sum_holds_bool is value
        assert GraftRecord.model_validate_json(record.model_dump_json()) == record
    with pytest.raises(ValidationError):
        graft_record(whole_input_charge_sum_bool=True)
