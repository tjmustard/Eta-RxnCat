"""Tier X: the transition-state seams on CPU GFN2 xtb (mission R7, R9, R32, R33, R36, R43).

Real P-RFO, sampler, constrained relax, geomeTRIC, validator, thermochemistry and store, with the
``xtb_subprocess`` engine on both sides. No stored reference number: values are compared only
between a fresh result and its cache replay, or between two values of one run. Each test names the
smallest source edits (seam breaks, R4) that make it fail.

Deselected by default (``xtb``); run with the mission R2 Tier X command.
"""

import json
import math
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import yaml

from eta_rxncat.conformers import forming_bond_configuration
from eta_rxncat.core import (
    EnumeratedCandidate,
    EnumerationPlan,
    MolecularState,
    PathwaySpec,
    TransitionStateRecord,
    TSEnsembleOptions,
)
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.enumerator import enumerate_candidates
from eta_rxncat.mapping.relax import CORE_FREEZE_TOLERANCE_ANGSTROM
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer
from eta_rxncat.orchestrator import (
    TSEnsembleRun,
    TSRecipe,
    TSRunResult,
    TSSpec,
    run_transition_state,
    run_ts_ensemble_detailed,
    run_ts_with_fallback,
)
from eta_rxncat.store import ArtifactStore

from .conftest import ROOT, V070Plan, _read_xyz, gfn2_stage, load_v070_plan, row_count

pytestmark = [pytest.mark.integration, pytest.mark.xtb]

TS1A_N_YAML = ROOT / "tests" / "e2e" / "data" / "e2e5" / "t3_ts1a_n_unmapped.yaml"
WEIGHT_TOLERANCE = 1e-12
"""``weights_sum_tolerance`` of ``t4_flexible_alkyl.yaml`` (mission R7)."""

ENSEMBLE_OPTIONS = TSEnsembleOptions(n_embed=1, n_perturb=1, max_research=1)
"""The smallest sampler (the ``PositiveInt`` minimum, mission R9): one sample besides the seed."""

ENDO_NODE = "TS1a_n"
EXO_NODE = "TS1a_x"


class Seed(NamedTuple):
    """The M1a TS1a_n seed and its reactant key."""

    spec: TSSpec
    core: list[int]
    reactant_key: tuple[tuple[str, int], ...]


def _ts1a_n_seed() -> Seed:
    """The TS request of ``t3_ts1a_n_unmapped.yaml``, read in place (no reference, identity map)."""
    data = yaml.safe_load(TS1A_N_YAML.read_text(encoding="utf-8"))
    block = data["ts"]
    state = _read_xyz(
        TS1A_N_YAML.parent / block["start_xyz"], block["charge"], block["spin_multiplicity"]
    )
    core = [int(i) for i in block["active_atom_indices"]]
    start = MolecularState.model_validate({**state.model_dump(), "active_atom_indices": core})
    spec = TSSpec(
        ts_id=block["ts_id"],
        start=start,
        forming_bonds=tuple((int(i), int(j)) for i, j in block["forming_bonds"]),
    )
    reactant_key = tuple(sorted((s["smiles"], 1) for s in data["species"]))
    return Seed(spec, core, reactant_key)


def _ts_recipe() -> TSRecipe:
    """GFN2 with P-RFO defaults, built as ``tests/e2e/t3.py``'s ``ts_recipe`` builds it."""
    return TSRecipe(name="xtb", engine_stage=gfn2_stage(), ts_optimizer=PRFOOptimizer())


def _member_gates(result: TSRunResult) -> dict[str, bool]:
    """The GFN2 member gates of ADR-0047: mode count, active core and the identity core."""
    validation = result.validation
    if validation is None:
        return {"validation": False}
    overlap = validation.forming_stretch_overlap
    threshold = validation.options.min_forming_stretch_overlap
    return {
        "mode_count": validation.mode_count_passed_bool,
        "active_core": validation.active_core_passed_bool,
        "forming_overlap": overlap is not None and overlap >= threshold,
        "forming_in_phase": validation.forming_bonds_in_phase_bool is True,
    }


def _rows(store: ArtifactStore) -> dict[str, tuple[str, dict[str, Any]]]:
    """Every row of the store file: key -> (stage kind, payload)."""
    connection = sqlite3.connect(store.path)
    try:
        rows = connection.execute(
            "SELECT key, stage_kind, payload_json FROM stage_artifacts"
        ).fetchall()
    finally:
        connection.close()
    return {key: (kind, json.loads(payload)) for key, kind, payload in rows}


def _sample_keys(run: TSEnsembleRun, field: str) -> set[str]:
    return {key for sample in run.samples if (key := getattr(sample, field)) is not None}


def _assert_all_hits(run: TSEnsembleRun) -> None:
    for kind, metrics in run.metrics.items():
        assert metrics.engine_calls == 0, kind
        assert metrics.rows_created == 0, kind
        assert metrics.cache_hits > 0, kind


def test_tx1_prfo_validation_thermo_and_replay(store: ArtifactStore, scratch_cwd: Path) -> None:
    """T-X1: ``run_transition_state`` with P-RFO on TS1a_n, GFN2 and the store.

    Seam breaks: ``run_transition_state`` skips storing the ``frequency`` row; the identity gate
    reads the wrong forming-bond order.
    """
    spec = _ts1a_n_seed().spec
    recipe = _ts_recipe()
    first = run_transition_state(spec, recipe, store)

    assert first.failed_reason is None
    assert first.search is not None and first.search.converged
    validation = first.validation
    assert validation is not None
    assert validation.n_imaginary == 1
    # The identity core of ADR-0047 (forming overlap, in phase, active-core KE) and mode count.
    assert all(_member_gates(first).values()), _member_gates(first)

    record = first.record
    assert record is not None
    assert TransitionStateRecord.model_validate(record.model_dump(mode="json")) == record
    assert sum(m.rows_created for m in first.metrics.values()) == row_count(store) == 2
    assert set(first.keys.values()) == set(_rows(store))

    again = run_transition_state(spec, recipe, store)
    for kind, metrics in again.metrics.items():
        assert metrics.engine_calls == 0, kind
        assert metrics.rows_created == 0, kind
        assert metrics.cache_hits == 1, kind
    assert row_count(store) == 2
    payloads = [run.as_payload() for run in (first, again)]
    for payload in payloads:
        payload.pop("metrics")
    assert payloads[0] == payloads[1]


def test_tx2_ensemble_sampler_relax_and_store(store: ArtifactStore, scratch_cwd: Path) -> None:
    """T-X2: the ensemble with its sampler, ``relax_constrained_core``, geomeTRIC and the store.

    Seam break: ``relax_constrained_core`` swaps the frozen-atom list for the non-core atoms.
    """
    seed = _ts1a_n_seed()
    recipe = _ts_recipe()

    def run_once() -> TSEnsembleRun:
        return run_ts_ensemble_detailed(
            seed.spec,
            recipe,
            store,
            optimizer=GeometricOptimizer(),
            core_indices=seed.core,
            pathway="endo",
            reactant_key=seed.reactant_key,
            options=ENSEMBLE_OPTIONS,
            member_gates=_member_gates,
        )

    run = run_once()
    ensemble = run.ensemble
    assert ensemble.failed_reason is None
    seed_record = run.seed_result.record
    assert seed_record is not None

    members = {m.index: m for m in ensemble.members}
    assert members[0].source == "seed"
    assert abs(sum(m.weight for m in ensemble.members) - 1) <= WEIGHT_TOLERANCE
    pairs = sorted((min(i, j), max(i, j)) for i, j in seed.spec.forming_bonds)
    seed_face = forming_bond_configuration(
        seed_record.state, pairs, perceive_bonds(seed_record.state)
    )
    for member in ensemble.members:
        assert tuple(member.face) == seed_face, member.index

    # The sample went through the pre-relaxation, the search and the Hessian.
    assert [s.index for s in run.samples] == [0, 1]
    sample = run.samples[1]
    assert sample.pre_relax_key is not None
    assert sample.ts_opt_key is not None, ensemble.excluded
    assert sample.frequency_key is not None, ensemble.excluded

    # Slice 03: every key the runner names is a row in this fresh store, of the matching kind.
    rows = _rows(store)
    for field, kind in (
        ("pre_relax_key", "constrained_preopt"),
        ("ts_opt_key", "ts_opt"),
        ("frequency_key", "frequency"),
    ):
        for key in _sample_keys(run, field):
            assert rows[key][0] == kind, (field, key)

    # The pre-relaxation froze the core: the sampler keeps the seed's core coordinates, and the
    # relaxed row still has them.
    relaxed = rows[sample.pre_relax_key][1]["final_xyz"]
    for atom in seed.core:
        moved = math.dist(relaxed[atom], seed_record.state.coordinates[atom])
        assert moved <= CORE_FREEZE_TOLERANCE_ANGSTROM, (atom, moved)

    again = run_once()
    _assert_all_hits(again)
    assert row_count(store) == len(rows)
    assert again.ensemble == ensemble
    assert again.samples == run.samples


@pytest.fixture(scope="module")
def fallback_store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ArtifactStore]:
    """One store for the two T-X3 tests, so rank 2 can replay T-X3's rows (either order works)."""
    artifact_store = ArtifactStore(tmp_path_factory.mktemp("tx3") / "store.db")
    yield artifact_store
    artifact_store.close()


def _ethyl(loaded: V070Plan, plan: EnumerationPlan) -> EnumeratedCandidate:
    result = enumerate_candidates(
        plan, max_alignment_rmsd_angstrom=loaded.max_alignment_rmsd_angstrom
    )
    (ethyl,) = [c for c in result.candidates if c.candidate_id == "ethyl"]
    assert ethyl.status == "ok", ethyl.detail
    return ethyl


def _endo_pathway(plan: EnumerationPlan) -> PathwaySpec:
    (pathway,) = [p for s in plan.selectivity_sets for p in s.pathways if p.node_id == ENDO_NODE]
    return pathway


def _fall_back(
    loaded: V070Plan, candidate: EnumeratedCandidate, store: ArtifactStore
) -> tuple[Any, TSEnsembleRun | None]:
    return run_ts_with_fallback(
        candidate,
        ENDO_NODE,
        _endo_pathway(loaded.plan),
        _ts_recipe(),
        store,
        optimizer=GeometricOptimizer(),
        options=ENSEMBLE_OPTIONS,
        member_gates=_member_gates,
        orientation_centers=loaded.orientation_centers,
    )


def test_tx3_fallback_rank1_chosen_and_replayed(
    fallback_store: ArtifactStore, scratch_cwd: Path
) -> None:
    """T-X3: ``run_ts_with_fallback`` on the enumerated ethyl candidate, endo node.

    The unmodified v0.7.0 plan has one template on the node, which passes the seed checks and
    seeds the ensemble.

    Seam breaks: the runner inverts the face comparison (rank 1 then falls through). Dropping
    ``expected_face`` is caught by ``test_tx3_rank1_face_mismatch``.
    """
    loaded = load_v070_plan()
    candidate = _ethyl(loaded, loaded.plan)
    record, run = _fall_back(loaded, candidate, fallback_store)

    template_id = f"{ENDO_NODE}__ethyl"
    assert record.stop_reason is None
    assert record.chosen_template_id == template_id
    assert [(a.template_id, a.rank, a.outcome, a.reason) for a in record.attempts] == [
        (template_id, 1, "chosen", None)
    ]
    assert run is not None
    assert run.ensemble.failed_reason is None
    assert run.ensemble.members
    assert run.samples[0].source == "seed"
    face = _endo_pathway(loaded.plan).expected_face
    for member in run.ensemble.members:
        assert tuple(member.face) == face, member.index
    rows = _rows(fallback_store)
    for field in ("pre_relax_key", "ts_opt_key", "frequency_key"):
        assert _sample_keys(run, field) <= set(rows), field
    assert run.samples[0].pre_relax_key is not None

    count = row_count(fallback_store)
    again_record, again = _fall_back(loaded, candidate, fallback_store)
    assert again is not None
    _assert_all_hits(again)
    assert row_count(fallback_store) == count
    assert again_record == record
    assert again.ensemble == run.ensemble


def _rank1_exo_plan(plan: EnumerationPlan) -> EnumerationPlan:
    """The R42 variant: the endo node tries the exo geometry before the endo one."""
    data = plan.model_dump()
    nodes = {node["id"]: node for node in data["reference_graph"]["nodes"]}
    (endo,) = nodes[ENDO_NODE]["templates"]
    (exo,) = nodes[EXO_NODE]["templates"]
    nodes[ENDO_NODE]["templates"] = [
        {**exo, "id": "TS1a_x_rank1", "rank": 1},
        {**endo, "rank": 2},
    ]
    (site,) = [s for s in data["sites"] if s["id"] == "c7"]
    (exo_map,) = [m for m in site["maps"] if m["node_id"] == EXO_NODE]
    site["maps"] = [
        *site["maps"],
        {**exo_map, "node_id": ENDO_NODE, "template_id": "TS1a_x_rank1"},
    ]
    return EnumerationPlan.model_validate(data)


def test_tx3_rank1_face_mismatch(fallback_store: ArtifactStore, scratch_cwd: Path) -> None:
    """T-X3 rank-1 face mismatch (mission R36, R43): the face check runs before any search.

    Changes to the v0.7.0 plan (R42, built here, no file):

    1. Node ``TS1a_n`` gets two templates: rank 1 is node ``TS1a_x``'s template geometry under the
       id ``TS1a_x_rank1``; rank 2 is the plan's ``TS1a_n`` template.
    2. Site ``c7`` gets one more map, a copy of its ``TS1a_x`` map for the pair
       (``TS1a_n``, ``TS1a_x_rank1``).

    The pathway (``expected_face`` ``[1, 1]``) and the options are the unmodified plan's. The store
    is shared with T-X3, so rank 2 replays T-X3's rows when that test ran first.

    Seam break: the fallback runner drops ``expected_face`` (its face check is skipped or compares
    against no face), so rank 1 goes to the ensemble instead of falling through.
    """
    loaded = load_v070_plan()
    candidate = _ethyl(loaded, _rank1_exo_plan(loaded.plan))
    record, run = _fall_back(loaded, candidate, fallback_store)

    first = record.attempts[0]
    assert (first.template_id, first.rank) == ("TS1a_x_rank1__ethyl", 1)
    assert (first.outcome, first.reason) == ("fell_through", "seed:face_mismatch_pathway")
    assert record.chosen_template_id == f"{ENDO_NODE}__ethyl"
    assert run is not None

    # Only rank 2 was ever searched: the store's searches and Hessians are exactly the ones its
    # ensemble names, so ``run_ts_ensemble_detailed`` never ran on rank 1.
    rows = _rows(fallback_store)
    for field, kind in (("ts_opt_key", "ts_opt"), ("frequency_key", "frequency")):
        stored = {key for key, (stage, _) in rows.items() if stage == kind}
        assert stored == _sample_keys(run, field), kind
