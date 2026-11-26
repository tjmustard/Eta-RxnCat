"""The cross-node invariant and frozen-atom remap of enumeration (v0.7.0 slice 03; R3, R30.D)."""

from typing import Any

import pytest
from test_enumerator_support import (
    MAX_RMSD,
    TS_KEEP,
    default_maps,
    default_nodes,
    node,
    plan,
    reactant_map,
    record,
    template,
    ts_map,
    ts_template,
    xyz_state,
)

from eta_rxncat.core import (
    EnumeratedCandidate,
    EnumerationPlan,
    GraftResult,
    ReactionNode,
    StageConfig,
)
from eta_rxncat.mapping import enumerator as module
from eta_rxncat.mapping import graft
from eta_rxncat.mapping.enumerator import enumerate_candidates


def one(built: EnumerationPlan) -> EnumeratedCandidate:
    """Return the single candidate of a plan."""
    (candidate,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD).candidates
    return candidate


def test_partial_pathway_coverage() -> None:
    """A site on the endo TS alone is inconsistent, with its records kept."""
    candidate = one(plan(maps=[ts_map("ts_endo"), reactant_map()]))
    assert (candidate.status, candidate.detail) == ("inconsistent", "partial_pathway_coverage:r")
    assert candidate.graph is None
    assert [r.status for r in candidate.records] == ["ok", "ok"]


def exo(**overrides: Any) -> dict[str, ReactionNode]:
    """Return the default nodes with another exo TS state."""
    return default_nodes() | {"ts_exo": node("ts_exo", [ts_template("t1", "TS1a_x", **overrides)])}


@pytest.mark.parametrize(
    ("built", "detail"),
    [
        (
            plan(
                maps=[
                    ts_map("ts_endo"),
                    ts_map(
                        "ts_exo",
                        keep=[i for i in TS_KEEP if i not in (8, 9)],
                        delete=[8, 9, 16],
                    ),
                    reactant_map(),
                ]
            ),
            "ts_composition_mismatch:endo_exo",
        ),
        (plan(nodes=exo(charge=2)), "ts_charge_mismatch:endo_exo"),
        (plan(nodes=exo(spin_multiplicity=3)), "ts_multiplicity_mismatch:endo_exo"),
        (
            plan(maps=[ts_map("ts_endo"), ts_map("ts_exo")]),
            "reactant_composition_mismatch:endo_exo",
        ),
        (
            plan(
                nodes=default_nodes()
                | {
                    "cp": node(
                        "cp",
                        [template("t1", xyz_state("1_cyclopentadiene", charge=2))],
                        kind="reactant",
                    )
                }
            ),
            "reactant_charge_mismatch:endo_exo",
        ),
    ],
    ids=["ts_composition", "ts_charge", "ts_multiplicity", "reactant_composition", "charge"],
)
def test_cross_node_failures(built: EnumerationPlan, detail: str) -> None:
    """Each miss of the invariant names its check and leaves no graph."""
    candidate = one(built)
    assert (candidate.status, candidate.detail, candidate.graph) == ("inconsistent", detail, None)


def preopt(frozen: list[int]) -> StageConfig:
    """Return a toy constrained pre-optimisation stage."""
    return StageConfig(
        kind="constrained_preopt",
        engine="rdkit_ff",
        method="mmff94",
        frozen_atom_indices=frozen,
    )


SINGLE_POINT = StageConfig(kind="single_point", engine="rdkit_ff", method="mmff94")
REORDERED = [5, 4, 3, 2, 1, 0, *TS_KEEP[6:]]


def endo_with(
    stages: list[StageConfig] | None, *templates: str, **overrides: Any
) -> dict[str, ReactionNode]:
    """Return the default nodes with endo templates ``templates`` and node stages."""
    ranked = [ts_template(t, rank=k) for k, t in enumerate(templates or ("t1",), start=1)]
    return default_nodes() | {"ts_endo": node("ts_endo", ranked, stages=stages, **overrides)}


def out_node(candidate: EnumeratedCandidate, node_id: str) -> ReactionNode:
    """Return one node of the candidate graph."""
    assert candidate.graph is not None, candidate.detail
    (found,) = [n for n in candidate.graph.nodes if n.id == node_id]
    return found


def test_node_stage_frozen_atoms_become_product_indices() -> None:
    """Node-level frozen atoms map through the index map, list order kept; no fragment atoms."""
    cp_stage = [preopt([0])]
    nodes = endo_with([preopt([17, 0, 5]), SINGLE_POINT])
    nodes["cp"] = nodes["cp"].model_copy(update={"stages": cp_stage})
    built = plan(nodes=nodes, maps=[ts_map("ts_endo", keep=REORDERED)], sets=[], default_stages=[])
    candidate = one(built)
    stages = out_node(candidate, "ts_endo").stages
    assert stages is not None
    assert [s.frozen_atom_indices for s in stages] == [[16, 5, 0], []]
    assert out_node(candidate, "cp").stages == cp_stage


def test_default_stage_frozen_atoms_are_written_to_the_node() -> None:
    """Defaults with frozen atoms are copied to the covered node; the defaults stay unchanged."""
    defaults = [preopt([17, 1]), SINGLE_POINT]
    built = plan(maps=[ts_map("ts_endo", keep=REORDERED)], sets=[], default_stages=defaults)
    candidate = one(built)
    stages = out_node(candidate, "ts_endo").stages
    assert stages is not None
    assert [s.frozen_atom_indices for s in stages] == [[16, 4], []]
    assert candidate.graph is not None
    assert candidate.graph.default_stages == defaults
    assert out_node(candidate, "cp").stages is None
    assert out_node(candidate, "ts_exo").stages is None


def test_default_stages_without_frozen_atoms_leave_node_stages_unset() -> None:
    """Nothing to remap: ``stages`` stays ``None``."""
    candidate = one(plan(default_stages=[SINGLE_POINT]))
    assert out_node(candidate, "ts_endo").stages is None


@pytest.mark.parametrize("level", ["node", "default"])
def test_frozen_atom_without_image_is_refused_before_graft(
    level: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A frozen index in ``template.delete`` refuses the graft without calling it."""
    calls: list[Any] = []

    def spy(*args: Any) -> GraftResult:
        calls.append(args)
        return graft(*args)

    monkeypatch.setattr(module, "graft", spy)
    stages = [preopt([0, 16])]
    if level == "node":
        built = plan(nodes=endo_with(stages), maps=[ts_map("ts_endo")], sets=[])
    else:
        built = plan(maps=[ts_map("ts_endo")], sets=[], default_stages=stages)
    candidate = one(built)
    found = record(candidate, "ts_endo")
    assert (found.status, found.reason) == ("refused", "graft_input")
    assert found.order_rmsds_angstrom == []
    assert found.whole_input_charge_sum_holds_bool is None
    assert calls == []
    assert candidate.status == "unmappable"


def test_frozen_index_mismatch_between_templates() -> None:
    """Two eligible templates whose keep orders give different images are inconsistent."""
    built = plan(
        nodes=endo_with([preopt([0])], "t1", "t2"),
        maps=[*default_maps(), ts_map("ts_endo", "t2", keep=REORDERED)],
    )
    candidate = one(built)
    assert (candidate.status, candidate.detail) == (
        "inconsistent",
        "frozen_index_mismatch:ts_endo",
    )
    assert [r.status for r in candidate.records] == ["ok", "ok", "ok", "ok"]


def test_matching_frozen_images_are_accepted() -> None:
    """Equal images across templates are written once."""
    built = plan(
        nodes=endo_with([preopt([6])], "t1", "t2"),
        maps=[*default_maps(), ts_map("ts_endo", "t2", keep=REORDERED)],
    )
    candidate = one(built)
    stages = out_node(candidate, "ts_endo").stages
    assert stages is not None
    assert stages[0].frozen_atom_indices == [6]
