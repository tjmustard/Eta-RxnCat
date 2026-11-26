"""Tests for the TS seed fallback and the enumerated inputs (v0.7.0, slice 05; R2-R7, R32).

The fallback loop runs on the stub surface of ``test_ts_ensemble`` with a hand-built candidate
whose TS templates are TS1a_n shifted by a few mÅ (distinct cache keys, same chemistry). The
R32 composition tests run the real enumerator on the e2e5 XYZ files.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, get_args

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mapping"))

from test_enumerator_multisite import M_KEEP, m_map, methyl, two_sites
from test_enumerator_support import (
    MAX_RMSD,
    default_nodes,
    entry,
    plan,
    ts_map,
    xyz_state,
)
from test_ts_ensemble import (
    CORE,
    FORMING,
    SEED_STATE,
    TagEngine,
    TagRelax,
    TagTS,
    gates,
    tag_engine,
    tag_of,
)

import eta_rxncat.orchestrator.ts_ensemble as ensemble_module
import eta_rxncat.orchestrator.ts_fallback as module
from eta_rxncat.core import (
    Component,
    EnumeratedCandidate,
    GraftRecord,
    MolecularState,
    PathwaySpec,
    ReactionGraph,
    ReactionNode,
    TemplateGeometry,
    TSEnsembleOptions,
)
from eta_rxncat.engines import EngineUnavailableError
from eta_rxncat.mapping.enumerator import enumerate_candidates, map_template_indices
from eta_rxncat.optimize import TSSearchFailedError
from eta_rxncat.optimize.errors import TSSearchFailureReason
from eta_rxncat.orchestrator import (
    TSRecipe,
    TSSpec,
    enumerated_pathway_inputs,
    run_ts_with_fallback,
)
from eta_rxncat.orchestrator._deadline import PreRelaxTimeout
from eta_rxncat.orchestrator.ts import _TSRun
from eta_rxncat.store import ArtifactStore, build_stage_key

__all__ = ["tag_engine"]  # the autouse fixture that routes xtb_subprocess to the tag engine

OPTIONS = TSEnsembleOptions(n_perturb=2, max_research=2)
CID = "c"


class ReasonTS(TagTS):
    """``TagTS`` plus a ``ts:<reason>`` tag that fails the search with that reason."""

    def find_saddle(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Fail with the tagged reason, else behave as ``TagTS``."""
        tag = tag_of(state)
        if tag.startswith("ts:"):
            engine.evaluate(state, forces=True)
            raise TSSearchFailedError(
                "stub", reason=tag.removeprefix("ts:"), steps=("0",), last_energy_hartree=-1.0
            )
        return super().find_saddle(state, engine, **kwargs)


class SpyTS(ReasonTS):
    """Counts the TS searches."""

    calls = 0

    def find_saddle(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Count, then search."""
        type(self).calls += 1
        return super().find_saddle(state, engine, **kwargs)


class TimeoutRelax(TagRelax):
    """A minimizer that raises the deadline signal for a ``pre_timeout`` tag."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Raise ``PreRelaxTimeout`` or behave as ``TagRelax``."""
        if self.calls < len(self.script) and self.script[self.calls] == "pre_timeout":
            self.calls += 1
            raise PreRelaxTimeout
        return super().minimize(state, engine, **kwargs)


def stub_recipe(ts: type[TagTS] = ReasonTS) -> TSRecipe:
    """The TS recipe on the stub surface."""
    from test_ts_ensemble import STAGE as ENGINE_STAGE

    return TSRecipe(name="stub", engine_stage=ENGINE_STAGE, ts_optimizer=ts())


def ts_geometry(shift: int) -> MolecularState:
    """TS1a_n moved ``shift`` mÅ along x: the same surface, a distinct cache key."""
    coords = [[x + 1.0e-3 * shift, y, z] for x, y, z in SEED_STATE.coordinates]
    return SEED_STATE.model_copy(update={"coordinates": coords, "metadata": {}})


def template(tid: str, rank: int, state: MolecularState) -> TemplateGeometry:
    """A one-species template."""
    return TemplateGeometry(id=tid, rank=rank, components=[Component(state=state, count=1)])


def graft_record(ref: str, node_id: str = "ts") -> GraftRecord:
    """An ok record whose product indices are the template's."""
    return GraftRecord(
        entry_id="e",
        site_id="r",
        node_id=node_id,
        template_id=ref,
        status="ok",
        mapped_forming_bonds=[list(p) for p in FORMING],
        constrained_core_product_indices=CORE,
    )


def reactant_nodes(**overrides: MolecularState) -> list[ReactionNode]:
    """Cyclopentadiene and cyclopropene reactant nodes."""
    states = {
        "cp": xyz_state("1_cyclopentadiene"),
        "cyclopropene": xyz_state("5_cyclopropene"),
        **overrides,
    }
    return [
        ReactionNode(
            id=name,
            label=name,
            kind="reactant",
            priority=1,
            templates=[template("t1", 1, state)],
        )
        for name, state in states.items()
    ]


def candidate(
    n_templates: int = 2,
    *,
    reactants: list[ReactionNode] | None = None,
    extra_nodes: Sequence[ReactionNode] = (),
    status: str = "ok",
) -> EnumeratedCandidate:
    """A hand-built candidate whose ``ts`` node has ``n_templates`` ranked templates."""
    ts_node = ReactionNode(
        id="ts",
        label="ts",
        kind="transition_state",
        priority=1,
        templates=[template(f"t{k}__{CID}", k, ts_geometry(k)) for k in range(1, n_templates + 1)],
    )
    graph = ReactionGraph(
        schema_version=1,
        name="g",
        nodes=[*(reactant_nodes() if reactants is None else reactants), ts_node, *extra_nodes],
    )
    data: dict[str, Any] = {
        "candidate_id": CID,
        "entry_ids_by_site": {"r": "e"},
        "status": status,
        "graph": graph,
        "records": [graft_record(f"t{k}") for k in range(1, n_templates + 1)],
    }
    if status != "ok":
        data.update(graph=None, detail="inconsistent_candidate:x")
    return EnumeratedCandidate.model_validate(data)


def pathway(face: tuple[int, ...] = (1, 1)) -> PathwaySpec:
    """The endo pathway on the ``ts`` node."""
    return PathwaySpec(pathway="endo", node_id="ts", expected_face=face)


def fallback(
    path: Path,
    relax: TagRelax,
    built: EnumeratedCandidate | None = None,
    *,
    face: tuple[int, ...] = (1, 1),
    ts: type[TagTS] = ReasonTS,
) -> Any:
    """Run the fallback once in the store at ``path``."""
    with ArtifactStore(path) as store:
        return run_ts_with_fallback(
            candidate() if built is None else built,
            "ts",
            pathway(face),
            stub_recipe(ts),
            store,
            optimizer=relax,
            options=OPTIONS,
            member_gates=gates,
        )


def outcomes(record: Any) -> list[tuple[int, str, str | None]]:
    """The attempts as ``(rank, outcome, reason)``."""
    return [(a.rank, a.outcome, a.reason) for a in record.attempts]


# --- The chosen template and the stops ---


def test_rank_one_is_chosen(tmp_path: Path) -> None:
    """A good rank 1 gives its ensemble; no other template runs."""
    record, run = fallback(tmp_path / "s.sqlite", TagRelax())
    assert record.chosen_template_id == "t1__c" and record.stop_reason is None
    assert outcomes(record) == [(1, "chosen", None)]
    assert run is not None and run.ensemble.members
    assert run.ensemble.pathway == "endo"
    assert run.ensemble.reactant_key == (("C1=CC1", 1), ("C1=CCC=C1", 1))


def test_an_engine_error_stops_the_node_and_so_does_the_cached_row(tmp_path: Path) -> None:
    """US-006: a real ``EngineRuntimeError`` through ``run_transition_state`` stops the node."""
    path = tmp_path / "s.sqlite"
    first, run = fallback(path, TagRelax(["engine"]))
    assert first.stop_reason == "stopped:seed:engine_error" and run is None
    assert outcomes(first) == [(1, "stopped", "seed:engine_error")]
    calls = TagEngine.calls
    relax = TagRelax(["A"])
    second, _ = fallback(path, relax)
    assert second == first
    assert (TagEngine.calls, relax.calls) == (calls, 0)


def test_a_graft_pre_relax_timeout_stops(tmp_path: Path) -> None:
    """A stalled graft pre-relaxation stops the node, never falling through."""
    record, run = fallback(tmp_path / "s.sqlite", TimeoutRelax(["pre_timeout"]))
    assert record.stop_reason == "stopped:graft_pre_relax_timeout" and run is None
    assert outcomes(record) == [(1, "stopped", "graft_pre_relax_timeout")]


@pytest.mark.parametrize(
    "tag, reason",
    [
        ("pre_core", "pre_relax_failed:CoreDisplacementError"),
        ("pre_fail", "pre_relax_failed:OptimizationFailedError"),
        ("pre_scf", "scf_convergence"),
        ("pre_engine", "engine_error"),
    ],
)
def test_other_graft_pre_relax_failures_stop(tmp_path: Path, tag: str, reason: str) -> None:
    """None of the pre-relaxation failures is on the allow-list."""
    record, _ = fallback(tmp_path / "s.sqlite", TagRelax([tag]))
    assert record.stop_reason == f"stopped:{reason}"


@pytest.mark.parametrize(
    "tag, reason",
    [
        ("ts:max_steps", "seed:ts_search_failed:max_steps"),
        ("ts:too_many_rejections", "seed:ts_search_failed:too_many_rejections"),
        ("ts:mode_lost", "seed:ts_search_failed:mode_lost"),
        ("ts:no_reaction_mode", "seed:ts_search_failed:no_reaction_mode"),
        ("two_imag", "seed:ts_validation_failed"),
        ("gate", "seed:gate_failed:active_core"),
        ("X", "seed:face_mismatch_pathway"),
    ],
)
def test_allow_listed_reasons_fall_through(tmp_path: Path, tag: str, reason: str) -> None:
    """Each template fault falls through to rank 2, which is chosen."""
    record, run = fallback(tmp_path / "s.sqlite", TagRelax([tag]))
    assert record.chosen_template_id == "t2__c"
    assert outcomes(record) == [(1, "fell_through", reason), (2, "chosen", None)]
    assert run is not None


def test_an_undetermined_seed_face_falls_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``seed:face_undetermined`` is a template fault."""
    real = ensemble_module.forming_bond_configuration

    def judge(state: MolecularState, forming: Any, bonds: Any) -> tuple[int, ...]:
        if tag_of(state) == "undet":
            raise ensemble_module.FaceDescriptorError("stub: zero volume")
        return real(state, forming, bonds)

    monkeypatch.setattr(ensemble_module, "forming_bond_configuration", judge)
    record, _ = fallback(tmp_path / "s.sqlite", TagRelax(["undet"]))
    assert outcomes(record)[0] == (1, "fell_through", "seed:face_undetermined")
    assert record.chosen_template_id == "t2__c"


@pytest.mark.parametrize(
    "tag, reason",
    [
        ("scf", "seed:scf_convergence"),
        ("ts:wall_time_exceeded", "seed:ts_search_failed:wall_time_exceeded"),
    ],
)
def test_engine_and_time_faults_stop(tmp_path: Path, tag: str, reason: str) -> None:
    """Not TS validation: the node stops."""
    record, _ = fallback(tmp_path / "s.sqlite", TagRelax([tag]))
    assert record.stop_reason == f"stopped:{reason}"
    assert outcomes(record) == [(1, "stopped", reason)]


def test_an_unknown_reason_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A string the allow-list does not know stops the node."""
    real = module.run_ts_ensemble_detailed

    def renamed(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        ensemble = result.ensemble.model_copy(
            update={"failed_reason": "seed:something_new", "members": []}
        )
        return ensemble_module.TSEnsembleRun(ensemble, result.metrics, result.seed_result)

    monkeypatch.setattr(module, "run_ts_ensemble_detailed", renamed)
    record, _ = fallback(tmp_path / "s.sqlite", TagRelax())
    assert record.stop_reason == "stopped:seed:something_new"
    assert not module.falls_through("seed:something_new")
    assert not module.falls_through("seed:gate_failed:")


def test_every_search_failure_reason_is_classified() -> None:
    """A new ``TSSearchFailureReason`` must be put on one side of R4."""
    declared = set(get_args(TSSearchFailureReason))
    assert declared == module.FALL_THROUGH_TS_SEARCH | module.STOP_TS_SEARCH
    assert not module.FALL_THROUGH_TS_SEARCH & module.STOP_TS_SEARCH
    for reason in declared:
        assert module.falls_through(f"seed:ts_search_failed:{reason}") == (
            reason in module.FALL_THROUGH_TS_SEARCH
        )


def test_the_face_mismatch_precedes_the_search(tmp_path: Path) -> None:
    """The pre-relaxed start's face is checked first: no TS search runs at all."""
    SpyTS.calls = 0
    record, run = fallback(tmp_path / "s.sqlite", TagRelax(), face=(-1, -1), ts=SpyTS)
    assert SpyTS.calls == 0 and run is None
    assert outcomes(record) == [
        (1, "fell_through", "seed:face_mismatch_pathway"),
        (2, "fell_through", "seed:face_mismatch_pathway"),
    ]
    assert record.stop_reason == "all_templates_failed"


def test_all_templates_failing(tmp_path: Path) -> None:
    """Every template a template fault: ``all_templates_failed``, without the ``stopped:`` word."""
    record, run = fallback(tmp_path / "s.sqlite", TagRelax(["two_imag", "two_imag"]))
    assert record.stop_reason == "all_templates_failed" and run is None
    assert [a.rank for a in record.attempts] == [1, 2]


def test_a_live_engine_error_propagates(tmp_path: Path) -> None:
    """``EngineUnavailableError`` is not turned into a record."""
    with pytest.raises(EngineUnavailableError):
        fallback(tmp_path / "s.sqlite", TagRelax(["unavail"]))


def test_a_rerun_repeats_the_record_without_engine_calls(tmp_path: Path) -> None:
    """The record is re-derived from the cached rows: equal, no call, no row."""
    path = tmp_path / "s.sqlite"
    script = ["two_imag", "A", "B", "A"]
    first, first_run = fallback(path, TagRelax(script))
    calls = TagEngine.calls
    relax = TagRelax(script)
    second, second_run = fallback(path, relax)
    assert second == first
    assert first.attempts[1].wall_time_s > 0
    assert (TagEngine.calls, relax.calls) == (calls, 0)
    assert first_run is not None and second_run is not None
    assert second_run.ensemble == first_run.ensemble
    assert all(m.rows_created == 0 and m.engine_calls == 0 for m in second_run.metrics.values())


def test_the_fallback_passes_the_stall_cap(tmp_path: Path) -> None:
    """R6: the fallback stops sampling after two member timeouts, keeping the seed."""
    options = TSEnsembleOptions(n_perturb=4, max_research=4)
    relax = TimeoutRelax(["A", "pre_timeout", "pre_timeout", "A", "A"])
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        record, run = run_ts_with_fallback(
            candidate(1),
            "ts",
            pathway(),
            stub_recipe(),
            store,
            optimizer=relax,
            options=options,
            member_gates=gates,
        )
    assert record.chosen_template_id == "t1__c"
    assert run is not None and run.stall_cap_reached_bool
    assert relax.calls == 3


# --- Refusals (R3, R5) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        xyz_state("5_cyclopropene", charge=1, spin_multiplicity=2),
        xyz_state("5_cyclopropene", spin_multiplicity=3),
    ],
    ids=["charged", "triplet"],
)
def test_charged_and_open_shell_runs_are_refused(tmp_path: Path, state: MolecularState) -> None:
    """R5: refused on any node, before any engine call."""
    built = candidate(reactants=reactant_nodes(cyclopropene=state))
    relax = TagRelax()
    calls = TagEngine.calls
    with pytest.raises(module.FallbackInputError, match="charged_run_not_supported_v070"):
        fallback(tmp_path / "s.sqlite", relax, built)
    assert (TagEngine.calls, relax.calls) == (calls, 0)


def test_a_candidate_that_is_not_ok_is_refused(tmp_path: Path) -> None:
    """An ``inconsistent`` candidate has nothing to run."""
    with pytest.raises(module.FallbackInputError, match="not 'ok'"):
        fallback(tmp_path / "s.sqlite", TagRelax(), candidate(status="inconsistent"))


def test_competing_ts_nodes_must_agree(tmp_path: Path) -> None:
    """R3: a competing TS with another composition is refused."""
    other = ReactionNode(
        id="ts2",
        label="ts2",
        kind="transition_state",
        priority=1,
        templates=[template("x", 1, xyz_state("5_cyclopropene"))],
    )
    with pytest.raises(module.FallbackInputError, match="differ in composition"):
        fallback(tmp_path / "s.sqlite", TagRelax(), candidate(extra_nodes=[other]))


def test_a_pathway_of_another_node_is_refused(tmp_path: Path) -> None:
    """The pathway must be the node's."""
    with (
        ArtifactStore(tmp_path / "s.sqlite") as store,
        pytest.raises(module.FallbackInputError, match="not 'cp'"),
    ):
        run_ts_with_fallback(
            candidate(),
            "cp",
            pathway(),
            stub_recipe(),
            store,
            optimizer=TagRelax(),
            options=OPTIONS,
            member_gates=gates,
        )


def test_reactant_key_is_derived() -> None:
    """R3: canonical SMILES of the reactant nodes with counts; the function takes no key."""
    built = enumerate_candidates(plan(), max_alignment_rmsd_angstrom=MAX_RMSD).candidates[0]
    inputs = enumerated_pathway_inputs(built, "ts_endo", "t1__ethyl", stub_recipe(), lambda _: {})
    assert inputs.reactant_key == (("C1=CCC=C1", 1), ("CCC1C=C1", 1))


# --- R32: one site verbatim, several composed ---


def enumerate_one(built: Any) -> EnumeratedCandidate:
    """The plan's single candidate, which must be ``ok``."""
    (found,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD).candidates
    assert found.status == "ok", found.detail
    return found


def ts_key(spec: TSSpec, recipe: TSRecipe, path: Path) -> str:
    """The ``ts_opt`` stage key of a seed."""
    with ArtifactStore(path) as store:
        run = _TSRun(spec, recipe, store)
        return build_stage_key(spec.start, run.ts_stage(), run.engine.identity).key


def endo_nodes() -> dict[str, ReactionNode]:
    """The reactants and the endo TS alone."""
    nodes = default_nodes()
    del nodes["ts_exo"]
    return nodes


def two_site_candidate(r_map: Any, m: Any) -> EnumeratedCandidate:
    """The endo-only two-site candidate with the given maps."""
    return enumerate_one(
        plan(
            nodes=endo_nodes(),
            sites=two_sites([r_map], [m]),
            library=[entry(), methyl()],
            sets=[],
        )
    )


def test_one_site_seeds_the_record_verbatim(tmp_path: Path) -> None:
    """Requirement 12: today's seed and its TS stage key."""
    built = enumerate_one(plan())
    (record,) = [r for r in built.records if r.node_id == "ts_endo"]
    inputs = enumerated_pathway_inputs(built, "ts_endo", "t1__ethyl", stub_recipe(), lambda _: {})
    assert record.mapped_forming_bonds is not None
    assert inputs.seed.forming_bonds == tuple(tuple(p) for p in record.mapped_forming_bonds)
    assert inputs.seed.forming_bonds == ((1, 2), (3, 5))
    assert inputs.core_indices == record.constrained_core_product_indices == [0, 1, 2, 3, 4, 5]
    assert inputs.seed.start.active_atom_indices == [0, 1, 2, 3, 4, 5]
    assert built.graph is not None
    product = next(n for n in built.graph.nodes if n.id == "ts_endo").templates[0]
    today = TSSpec(
        ts_id="today",
        start=MolecularState.model_validate(
            {
                **product.components[0].state.model_dump(),
                "active_atom_indices": record.constrained_core_product_indices,
            }
        ),
        forming_bonds=tuple(tuple(p) for p in record.mapped_forming_bonds),
    )
    recipe = stub_recipe()
    assert ts_key(inputs.seed, recipe, tmp_path / "a.sqlite") == ts_key(
        today, recipe, tmp_path / "b.sqlite"
    )


def test_a_seed_atom_deleted_by_a_later_site_is_refused(tmp_path: Path) -> None:
    """Requirement 13: site ``m`` deletes H14, which site ``r`` declares in a forming bond."""
    built = two_site_candidate(
        ts_map("ts_endo", forming_bonds=[(1, 2), (3, 5), (3, 14)]), m_map("ts_endo")
    )
    template_id = f"t1__{built.candidate_id}"
    with pytest.raises(module.FallbackInputError) as caught:
        enumerated_pathway_inputs(built, "ts_endo", template_id, stub_recipe(), lambda _: {})
    message = str(caught.value)
    assert message.startswith("multi_site_seed_atom_deleted")
    for word in ("ts_endo", "'t1'", "site 'r'", "site 'm'", "atom 14"):
        assert word in message
    relax = TagRelax()
    calls = TagEngine.calls
    with (
        ArtifactStore(tmp_path / "s.sqlite") as store,
        pytest.raises(module.FallbackInputError, match="^multi_site_seed_atom_deleted"),
    ):
        run_ts_with_fallback(
            built,
            "ts_endo",
            PathwaySpec(pathway="endo", node_id="ts_endo", expected_face=(1, 1)),
            stub_recipe(),
            store,
            optimizer=relax,
            options=OPTIONS,
            member_gates=gates,
        )
    assert (TagEngine.calls, relax.calls) == (calls, 0)


def test_two_sites_compose_bonds_and_core() -> None:
    """Requirement 14: site ``r``'s pair is carried through site ``m``; the core is the union."""
    r_map = ts_map("ts_endo", forming_bonds=[(1, 2)], constrained_core=[0, 1, 2])
    m = m_map("ts_endo", forming_bonds=[(3, 5)], constrained_core=[3, 4, 5], keep=M_KEEP)
    built = two_site_candidate(r_map, m)
    first, second = [r for r in built.records if r.node_id == "ts_endo"]
    inputs = enumerated_pathway_inputs(
        built, "ts_endo", f"t1__{built.candidate_id}", stub_recipe(), lambda _: {}
    )
    assert first.mapped_forming_bonds is not None and second.mapped_forming_bonds is not None
    ((i, j),) = first.mapped_forming_bonds
    carried = tuple(map_template_indices(second, [i, j]))
    (own,) = second.mapped_forming_bonds
    assert inputs.seed.forming_bonds == (carried, tuple(own))
    assert first.constrained_core_product_indices is not None
    assert second.constrained_core_product_indices is not None
    expected = sorted(
        set(map_template_indices(second, first.constrained_core_product_indices))
        | set(second.constrained_core_product_indices)
    )
    assert inputs.core_indices == expected
    template_symbols = xyz_state("TS1a_n").symbols
    symbols = inputs.seed.start.symbols
    originals = [(1, 2), (3, 5)]
    for pair, original in zip(inputs.seed.forming_bonds, originals, strict=True):
        assert [symbols[k] for k in pair] == [template_symbols[k] for k in original]
    assert [symbols[k] for k in inputs.core_indices] == [template_symbols[k] for k in range(6)]


def test_duplicate_pairs_across_sites_are_dropped() -> None:
    """Both sites declaring the same bonds give each once, unordered, in site order."""
    built = two_site_candidate(ts_map("ts_endo"), m_map("ts_endo"))
    inputs = enumerated_pathway_inputs(
        built, "ts_endo", f"t1__{built.candidate_id}", stub_recipe(), lambda _: {}
    )
    assert len(inputs.seed.forming_bonds) == 2
    assert inputs.core_indices == [0, 1, 2, 3, 4, 5]


def test_an_unknown_template_is_refused() -> None:
    """A template id outside the node is refused."""
    with pytest.raises(module.FallbackInputError, match="has no template"):
        enumerated_pathway_inputs(candidate(), "ts", "nope__c", stub_recipe(), lambda _: {})


def test_a_gate_mapping_is_passed_through() -> None:
    """The inputs carry the recipe and the member gates given."""
    recipe = stub_recipe()

    def mine(_: Any) -> Mapping[str, bool]:
        return {"ok": True}

    inputs = enumerated_pathway_inputs(candidate(), "ts", "t1__c", recipe, mine)
    assert inputs.recipe is recipe and inputs.member_gates is mine
