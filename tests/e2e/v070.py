"""v0.7.0 E2E helpers: the YAML inputs (slice 10) and the enumeration units (slice 11).

Inputs: ``load_enumeration``, ``load_fallback`` and the ``V070Inputs`` they return. Each YAML
block mirrors the ``EnumerationPlan`` fields, with every structure given as an ``xyz`` path
(relative to the YAML) plus its explicit charge and spin multiplicity. The contracts validate the
rest and refuse unknown keys.

Units (mission G7): ``run_unit`` runs one (R x pathway) unit of one recipe through
``run_ts_with_fallback`` and the species runner twice in one store, derives the per-sample stage
keys ``TSEnsembleRun`` does not expose, and ``unit_gates``/``unit_record`` judge it and build its
``RunRecord``. ``score_pair`` scores the two pathways of one (R, engine). Loading the inputs runs
no engine; nothing here changes ``src/``.
"""

import math
import os
import resource
import time
from collections import Counter
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from e2e_env import REPO
from fixtures import DATA, _exact_keys, read_xyz
from t3 import REACTANT_STAGES, all_hit, ts_recipe
from t4 import exclusions_by_reason, member_gates

from eta_rxncat.conformers import ConformerOptions, sample_ts_conformers
from eta_rxncat.core import (
    EnumeratedCandidate,
    EnumerationPlan,
    FallbackRecord,
    MolecularState,
    PathwaySpec,
    SelectivityResult,
    TSEnsemble,
    TSEnsembleOptions,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL, Engine
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.enumerator import enumerate_candidates
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer
from eta_rxncat.orchestrator import (
    BarrierSpec,
    Recipe,
    SpeciesResult,
    SpeciesSpec,
    TSEnsembleRun,
    TSSpec,
    activation_free_energy,
    build_engine,
    enumerated_pathway_inputs,
    run_species,
    run_transition_state,
    run_ts_with_fallback,
    score_selectivity,
)
from eta_rxncat.orchestrator.counting import CountingEngine
from eta_rxncat.orchestrator.ts import _sorted_pairs
from eta_rxncat.orchestrator.ts_ensemble import PRE_RELAX_KIND, _digest, _PreRelax
from eta_rxncat.review import export_run_data
from eta_rxncat.review.run_data import (
    RecordCandidate,
    RecordEndpoint,
    RecordGate,
    RecordRun,
    RecordSample,
    RecordSelectivity,
    RecordSpecies,
    RecordUnitRef,
    RunRecord,
)
from eta_rxncat.store import ArtifactStore, build_stage_key

E2E5 = DATA / "e2e5"
ENUMERATION_YAML = E2E5 / "v070_enumeration.yaml"
FALLBACK_YAML = E2E5 / "v070_fallback.yaml"
CONSTRUCTS = ("graft_time", "run_time")

_PLAN_KEYS = {"reference_graph", "sites", "library", "selectivity_sets", "max_candidates"}
_RUN_KEYS = {"max_alignment_rmsd_angstrom", "orientation_centers"}
_MAP_KEYS = ("keep", "delete", "alignment")


@dataclass(frozen=True)
class V070Inputs:
    """One enumeration plan and the run settings its YAML declares beside it.

    Attributes:
        plan: The validated plan.
        max_alignment_rmsd_angstrom: For ``enumerate_candidates``.
        orientation_centers: Product atom indices for the ensemble's orientation guard.
    """

    plan: EnumerationPlan
    max_alignment_rmsd_angstrom: float
    orientation_centers: tuple[int, ...]


def load_enumeration(path: Path = ENUMERATION_YAML) -> V070Inputs:
    """Load ``v070_enumeration.yaml``.

    Raises:
        ValueError: On a wrong schema, a missing or unknown key, or a plan the contracts refuse.
    """
    data = _read(path, _PLAN_KEYS | _RUN_KEYS)
    return _inputs(path, {k: data[k] for k in _PLAN_KEYS}, data)


def load_fallback(path: Path = FALLBACK_YAML) -> dict[str, V070Inputs]:
    """Load ``v070_fallback.yaml`` as ``{"graft_time": ..., "run_time": ...}``.

    Raises:
        ValueError: On a wrong schema, a missing or unknown key, or a plan the contracts refuse.
    """
    data = _read(path, {"constructs"} | _RUN_KEYS)
    constructs = data["constructs"]
    _exact_keys(path, "constructs", constructs, set(CONSTRUCTS))
    out = {}
    for name in CONSTRUCTS:
        _exact_keys(path, name, constructs[name], _PLAN_KEYS)
        out[name] = _inputs(path, constructs[name], data)
    return out


def _read(path: Path, keys: set[str]) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    _exact_keys(path, "top-level", data, keys | {"schema", "fixture"})
    return data


def _inputs(path: Path, plan: Mapping[str, Any], settings: Mapping[str, Any]) -> V070Inputs:
    base = Path(path).parent
    graph = dict(plan["reference_graph"])
    graph["nodes"] = [
        {**node, "templates": [_template(base, t) for t in node["templates"]]}
        for node in graph["nodes"]
    ]
    sites = [{**site, "maps": [_site_map(m) for m in site["maps"]]} for site in plan["sites"]]
    library = []
    for raw in plan["library"]:
        entry = dict(raw)
        entry["fragment"] = _state(base, entry)
        library.append(entry)
    return V070Inputs(
        plan=EnumerationPlan.model_validate(
            {**plan, "reference_graph": graph, "sites": sites, "library": library}
        ),
        max_alignment_rmsd_angstrom=float(settings["max_alignment_rmsd_angstrom"]),
        orientation_centers=tuple(int(i) for i in settings["orientation_centers"]),
    )


def _state(base: Path, block: dict[str, Any]) -> MolecularState:
    """Pop ``xyz``, ``charge``, ``spin_multiplicity`` and active atoms out of a block."""
    state = read_xyz(base / block.pop("xyz"), block.pop("charge"), block.pop("spin_multiplicity"))
    return MolecularState.model_validate(
        {**state.model_dump(), "active_atom_indices": block.pop("active_atom_indices", [])}
    )


def _template(base: Path, raw: Mapping[str, Any]) -> dict[str, Any]:
    block = dict(raw)
    state = _state(base, block)
    return {**block, "components": [{"state": state, "count": 1}]}


def _site_map(raw: Mapping[str, Any]) -> dict[str, Any]:
    block = dict(raw)
    block["template"] = {key: block.pop(key) for key in _MAP_KEYS}
    return block


# --- Slice 11: one (R x pathway x engine) unit --------------------------------------------------

CANDIDATES_V070 = REPO / "tests" / "candidate_outputs" / "v0.7.0"
R_GROUPS = ("ethyl", "npropyl")
PATHWAYS = ("endo", "exo")
SELECTIVITY_ID = "endo_exo"
WEIGHT_TOLERANCE = 1e-12
TIMEOUT_REASONS = ("pre_relax_failed:PreRelaxTimeout", "graft_pre_relax_timeout")
SAMPLE_STAGES = (PRE_RELAX_KIND, "ts_opt", "frequency")
REACTANT_CONFORMERS = ConformerOptions(n_embed=10, seed=42)
"""The reactants' conformer settings (v0.6.0's, ``t4_flexible_alkyl.yaml``)."""


def candidate_dir() -> Path:
    """``ETA_RXNCAT_CANDIDATE_DIR`` if set, else ``tests/candidate_outputs/v0.7.0`` (write only)."""
    override = os.environ.get("ETA_RXNCAT_CANDIDATE_DIR")
    path = Path(override) if override else CANDIDATES_V070
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_dir() -> Path | None:
    """``ETA_RXNCAT_V070_STATE``: the durable store and run records, outside the repository."""
    base = os.environ.get("ETA_RXNCAT_V070_STATE")
    if not base:
        return None
    path = Path(base)
    (path / "records").mkdir(parents=True, exist_ok=True)
    return path


def unit_name(r_group: str, pathway: str, recipe_name: str) -> str:
    """``v070_enum_<R>_<pathway>_<engine>``."""
    return f"v070_enum_{r_group}_{pathway}_{recipe_name}"


def score_name(r_group: str, recipe_name: str) -> str:
    """``v070_enum_<R>_selectivity_<engine>``."""
    return f"v070_enum_{r_group}_selectivity_{recipe_name}"


@contextmanager
def counted_engine_calls(*recipes: Recipe) -> Iterator[Counter[str]]:
    """Count every real engine evaluation, graft pre-relax and species runner included.

    The concrete engine inherits ``Engine.evaluate``; the runners' ``CountingEngine`` wraps it and
    delegates here, so each evaluation is counted exactly once.
    """
    for recipe in recipes:
        engine = build_engine(recipe.engine_stage, recipe.engine_runtime)
        assert type(engine).evaluate is Engine.evaluate, "the engine overrides evaluate"
    assert CountingEngine.evaluate is not Engine.evaluate
    calls: Counter[str] = Counter()
    original = Engine.evaluate

    def counting(self: Engine, state: MolecularState, **kwargs: Any) -> Any:
        calls["evaluate"] += 1
        return original(self, state, **kwargs)

    Engine.evaluate = counting  # type: ignore[method-assign]
    try:
        yield calls
    finally:
        Engine.evaluate = original  # type: ignore[method-assign]


def _usage() -> dict[str, float]:
    own = resource.getrusage(resource.RUSAGE_SELF)
    kids = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "cpu_s": own.ru_utime + own.ru_stime + kids.ru_utime + kids.ru_stime,
        "peak_rss_self_kb": own.ru_maxrss,
        "peak_rss_child_kb": kids.ru_maxrss,
    }


@dataclass(frozen=True)
class UnitPass:
    """One pass of a unit: the fallback record, the ensemble run and the reactants."""

    record: FallbackRecord
    run: TSEnsembleRun | None
    reactants: dict[str, SpeciesResult]
    wall_time_s: float
    engine_calls: int
    new_rows: int


@dataclass(frozen=True)
class Unit:
    """Everything one (R x pathway x engine) unit measured."""

    r_group: str
    recipe_name: str
    inputs: V070Inputs
    candidate: EnumeratedCandidate
    pathway: PathwaySpec
    first: UnitPass
    second: UnitPass
    samples: list[RecordSample]
    timeouts: list[dict[str, Any]]
    derivation_engine_calls: int
    derivation_new_rows: int
    barrier: dict[str, float] | None
    barrier_error: str | None
    resources: dict[str, float]


def enumerate_one(r_group: str) -> tuple[V070Inputs, EnumeratedCandidate]:
    """Enumerate the plan (pure) and take the R's candidate."""
    inputs = load_enumeration()
    result = enumerate_candidates(
        inputs.plan, max_alignment_rmsd_angstrom=inputs.max_alignment_rmsd_angstrom
    )
    (candidate,) = [c for c in result.candidates if c.candidate_id == r_group]
    return inputs, candidate


def pathway_spec(inputs: V070Inputs, pathway: str) -> PathwaySpec:
    """The ``endo_exo`` set's pathway."""
    (selectivity,) = [s for s in inputs.plan.selectivity_sets if s.id == SELECTIVITY_ID]
    (found,) = [p for p in selectivity.pathways if p.pathway == pathway]
    return found


def reactant_specs(
    candidate: EnumeratedCandidate, reactant_key: tuple[tuple[str, int], ...]
) -> dict[str, SpeciesSpec]:
    """One ``SpeciesSpec`` per reactant node, with the SMILES of the derived ``reactant_key``.

    Species ids are ``<node>__<candidate>``. Each node's SMILES is matched to the key through the
    runner's own canonicalisation of the node's rank-1 template.
    """
    from eta_rxncat.orchestrator.ts_fallback import _canonical_smiles

    assert candidate.graph is not None
    counts = dict(reactant_key)
    specs: dict[str, SpeciesSpec] = {}
    for node in candidate.graph.nodes:
        if node.kind != "reactant":
            continue
        template = min(node.templates, key=lambda t: t.rank)
        (component,) = template.components
        assert component.count == 1
        smiles = _canonical_smiles(component.state, node.id)
        assert counts[smiles] == 1, f"reactant {node.id}: {smiles} not once in {reactant_key}"
        species_id = f"{node.id}__{candidate.candidate_id}"
        specs[species_id] = SpeciesSpec(
            species_id=species_id,
            smiles=smiles,
            charge=component.state.charge,
            spin_multiplicity=component.state.spin_multiplicity,
            conformer_options=REACTANT_CONFORMERS,
        )
    assert len(specs) == len(reactant_key)
    return specs


def _rows(store: ArtifactStore) -> int:
    return len(store.query())


def _one_pass(
    candidate: EnumeratedCandidate,
    pathway: PathwaySpec,
    recipe: Recipe,
    recipe_name: str,
    centers: tuple[int, ...],
    specs: Mapping[str, SpeciesSpec],
    store_path: Path,
) -> UnitPass:
    start = time.perf_counter()
    with counted_engine_calls(recipe) as calls, ArtifactStore(store_path) as store:
        before = _rows(store)
        record, run = run_ts_with_fallback(
            candidate,
            pathway.node_id,
            pathway,
            ts_recipe(recipe),
            store,
            optimizer=GeometricOptimizer(),
            options=TSEnsembleOptions(),
            member_gates=member_gates(recipe_name),
            orientation_centers=centers,
        )
        reactants = {k: run_species(s, recipe, store) for k, s in specs.items()}
        new_rows = _rows(store) - before
        engine_calls = calls["evaluate"]
    return UnitPass(record, run, reactants, time.perf_counter() - start, engine_calls, new_rows)


def derive_samples(
    candidate: EnumeratedCandidate,
    pathway: PathwaySpec,
    run: TSEnsembleRun,
    template_id: str,
    recipe: Recipe,
    recipe_name: str,
    store: ArtifactStore,
) -> tuple[list[RecordSample], list[dict[str, Any]]]:
    """The stage keys of every sample of the chosen ensemble, and its timeout rows.

    ``TSEnsembleRun`` exposes no per-sample keys, so they are re-derived the way the runner builds
    them (same sampler, same pre-relax key, a cached ``run_transition_state``). Only rows already
    in the store are read back through the runners, so nothing is computed.

    Raises:
        AssertionError: The derived samples do not cover the ensemble's members, exclusions and
            merges, or a member's start digest differs.
    """
    options = TSEnsembleOptions()
    tsr = ts_recipe(recipe)
    inputs = enumerated_pathway_inputs(
        candidate, pathway.node_id, template_id, tsr, member_gates(recipe_name)
    )
    pre = _PreRelax(tsr, store, GeometricOptimizer(), inputs.core_indices)

    def key_of(state: MolecularState) -> str:
        return build_stage_key(state, pre.stage(), pre.engine.identity).key

    def row_of(state: MolecularState) -> dict[str, Any] | None:
        return store.get(build_stage_key(state, pre.stage(), pre.engine.identity))

    timeouts: list[dict[str, Any]] = []

    def note_timeout(index: int, row: Mapping[str, Any]) -> None:
        if str(row.get("failed_reason")) == TIMEOUT_REASONS[0]:
            fields = ("wall_time_s", "budget_s", "load1", "budget_kind")
            timeouts.append({"sample_index": index, **{k: row.get(k) for k in fields}})

    graft_row = row_of(inputs.seed.start)
    assert graft_row is not None, "no graft pre-relax row"
    note_timeout(0, graft_row)
    species_id = template_id
    samples = [
        RecordSample(
            template_id=template_id,
            sample_index=0,
            source="seed",
            species_id=species_id,
            pre_relax_key=key_of(inputs.seed.start),
            ts_opt_key=run.seed_result.keys.get("ts_opt"),
            frequency_key=run.seed_result.keys.get("frequency"),
        )
    ]
    assert run.seed_result.record is not None
    seed_final = run.seed_result.record.state
    bonds = perceive_bonds(seed_final)
    drawn = sample_ts_conformers(
        seed_final, inputs.core_indices, _sorted_pairs(inputs.seed.forming_bonds), bonds, options
    )
    digests: dict[int, str] = {}
    for index, sample in enumerate(drawn[: options.max_research], start=1):
        row = row_of(sample.state)
        if row is None:
            break  # sampling stopped at the stall cap
        note_timeout(index, row)
        digests[index] = _digest(sample.state)
        ts_opt_key = frequency_key = None
        if "failed_reason" not in row:
            relaxed, _, _ = pre.run(sample.state)
            assert relaxed is not None
            result = run_transition_state(
                TSSpec(
                    ts_id=f"{inputs.seed.ts_id}:{sample.source}",
                    start=relaxed,
                    forming_bonds=inputs.seed.forming_bonds,
                ),
                tsr,
                store,
            )
            ts_opt_key = result.keys.get("ts_opt")
            frequency_key = result.keys.get("frequency")
        samples.append(
            RecordSample(
                template_id=template_id,
                sample_index=index,
                source=sample.source,
                species_id=species_id,
                pre_relax_key=key_of(sample.state),
                ts_opt_key=ts_opt_key,
                frequency_key=frequency_key,
            )
        )
    ensemble = run.ensemble
    judged = (
        {m.index for m in ensemble.members}
        | {e.index for e in ensemble.excluded}
        | {m.merged_index for m in ensemble.merges}
    )
    assert judged == {s.sample_index for s in samples}, (judged, samples)
    for member in ensemble.members:
        if member.index:
            assert member.start_sha256 == digests[member.index]
    return samples, timeouts


def _barrier(
    specs: Mapping[str, SpeciesSpec],
    reactants: Mapping[str, SpeciesResult],
    run: TSEnsembleRun | None,
    recipe: Recipe,
) -> tuple[dict[str, float] | None, str | None]:
    """The ensemble dG-dagger (1 M): the seed barrier shifted to ``G_pathway``."""
    if run is None or run.seed_result.record is None:
        return None, "no_ts_record"
    record = run.seed_result.record
    spec = BarrierSpec(
        reactants=tuple((k, 1) for k in specs),
        ts_id=record.ts_id,
        smiles={k: s.smiles for k, s in specs.items()},
    )
    try:
        seed = activation_free_energy(
            spec, {k: v.ensemble for k, v in reactants.items()}, record, recipe.thermo_config
        )
    except ValueError as exc:
        return None, str(exc)
    g_pathway = run.ensemble.G_pathway_hartree
    if g_pathway is None:
        return None, "no_pathway_free_energy"
    shift = (g_pathway - record.thermo.gibbs_free_energy_hartree) * HARTREE_KCAL_MOL
    return {
        "seed_dG_dagger_1M_kcal_mol": seed.dG_dagger_1M_kcal_mol,
        "ensemble_dG_dagger_1M_kcal_mol": seed.dG_dagger_1M_kcal_mol + shift,
        "ensemble_correction_kcal_mol": shift,
    }, None


def run_unit(
    r_group: str, pathway: str, recipe: Recipe, recipe_name: str, store_path: Path
) -> Unit:
    """Enumerate, then run the unit twice in ``store_path`` and derive its sample keys."""
    before = _usage()
    start = time.perf_counter()
    inputs, candidate = enumerate_one(r_group)
    spec = pathway_spec(inputs, pathway)
    assert candidate.graph is not None
    (node,) = [n for n in candidate.graph.nodes if n.id == spec.node_id]
    (template,) = node.templates
    seed_inputs = enumerated_pathway_inputs(
        candidate, spec.node_id, template.id, ts_recipe(recipe), member_gates(recipe_name)
    )
    specs = reactant_specs(candidate, tuple(seed_inputs.reactant_key))
    args = (candidate, spec, recipe, recipe_name, inputs.orientation_centers, specs, store_path)
    first = _one_pass(*args)
    second = _one_pass(*args)
    samples: list[RecordSample] = []
    timeouts: list[dict[str, Any]] = []
    with counted_engine_calls(recipe) as calls, ArtifactStore(store_path) as store:
        rows = _rows(store)
        chosen = first.record.chosen_template_id
        if chosen is not None and first.run is not None:
            samples, timeouts = derive_samples(
                candidate, spec, first.run, chosen, recipe, recipe_name, store
            )
        derivation_calls, derivation_rows = calls["evaluate"], _rows(store) - rows
    barrier, barrier_error = _barrier(specs, first.reactants, first.run, recipe)
    after = _usage()
    resources = {
        "wall_time_s": time.perf_counter() - start,
        "cpu_user_plus_sys_s": after["cpu_s"] - before["cpu_s"],
        "peak_rss_self_kb": after["peak_rss_self_kb"],
        "peak_rss_child_kb": after["peak_rss_child_kb"],
    }
    return Unit(
        r_group,
        recipe_name,
        inputs,
        candidate,
        spec,
        first,
        second,
        samples,
        timeouts,
        derivation_calls,
        derivation_rows,
        barrier,
        barrier_error,
        resources,
    )


# --- Gates ---------------------------------------------------------------------------------------


def g3_invariant(candidate: EnumeratedCandidate) -> bool:
    """The competing TSs and the sum of the reactants share composition, charge, multiplicity."""
    assert candidate.graph is not None
    nodes = {n.id: n for n in candidate.graph.nodes}
    reactants: Counter[str] = Counter()
    charge = 0
    for node in nodes.values():
        if node.kind == "reactant":
            template = min(node.templates, key=lambda t: t.rank)
            reactants += template.element_counts
            charge += template.total_charge
    for node_id in ("TS1a_n", "TS1a_x"):
        for template in nodes[node_id].templates:
            if template.element_counts != reactants or template.total_charge != charge:
                return False
            if [c.state.spin_multiplicity for c in template.components] != [1]:
                return False
    return True


def second_pass_hits(unit: Unit) -> bool:
    """0 rows and 0 engine calls on the second pass and derivation, with equal records."""
    first, second = unit.first, unit.second
    if first.run is None or second.run is None:
        return False
    if second.new_rows or second.engine_calls or unit.derivation_new_rows:
        return False
    if unit.derivation_engine_calls:
        return False
    metrics = second.run.metrics
    if any(metrics[k].rows_created or metrics[k].engine_calls for k in SAMPLE_STAGES):
        return False
    if not all(all_hit(r, k) for r in second.reactants.values() for k in REACTANT_STAGES):
        return False
    return first.record == second.record and first.run.ensemble == second.run.ensemble


def unit_gates(unit: Unit) -> dict[str, dict[str, Any]]:
    """The G7 gates of one unit, each ``pass`` or ``fail``."""

    def gate(ok: bool, **extra: Any) -> dict[str, Any]:
        return {"status": "pass" if ok else "fail", **extra}

    candidate, record, run = unit.candidate, unit.first.record, unit.first.run
    ensemble = None if run is None else run.ensemble
    members = [] if ensemble is None else ensemble.members
    reasons = {} if ensemble is None else exclusions_by_reason(ensemble)
    assert candidate.graph is not None
    charges = sorted(
        {
            (c.state.charge, c.state.spin_multiplicity)
            for n in candidate.graph.nodes
            for t in n.templates
            for c in t.components
        }
        | {(r.product_charge, r.product_multiplicity) for r in candidate.records}
    )
    rmsds = [r.alignment_rmsd_angstrom for r in candidate.records]
    max_rmsd = max((x for x in rmsds if x is not None), default=math.inf)
    contacts = [r.close_contact_count for r in candidate.records]
    weights = sum(m.weight for m in members)
    expected = list(unit.pathway.expected_face)
    chosen = [a for a in record.attempts if a.outcome == "chosen"]
    return {
        "candidate_ok": gate(candidate.status == "ok", candidate_status=candidate.status),
        "charge_0_multiplicity_1": gate(charges == [(0, 1)], found=[list(c) for c in charges]),
        "graft_rmsd_and_contacts": gate(
            all(r.status == "ok" for r in candidate.records)
            and None not in rmsds
            and max_rmsd <= unit.inputs.max_alignment_rmsd_angstrom
            and contacts == [0] * len(contacts),
            max_alignment_rmsd_angstrom=max_rmsd,
            close_contact_counts=contacts,
        ),
        "g3_invariant": gate(g3_invariant(candidate)),
        "chosen_at_rank_1": gate(
            len(chosen) == 1 and chosen[0].rank == 1 and len(record.attempts) == 1,
            stop_reason=record.stop_reason,
        ),
        "weights_sum_to_one": gate(
            bool(members) and abs(weights - 1.0) <= WEIGHT_TOLERANCE, weights_sum=weights
        ),
        "every_member_face_expected": gate(
            bool(members) and all(m.face == expected for m in members), expected_face=expected
        ),
        "no_engine_error_or_face_mismatch": gate(
            ensemble is not None
            and "engine_error" not in reasons
            and "face_mismatch" not in reasons,
            exclusions_by_reason=reasons,
        ),
        "second_pass_all_hits": gate(
            second_pass_hits(unit),
            new_rows=unit.second.new_rows,
            engine_calls=unit.second.engine_calls,
        ),
    }


def reported_unit(unit: Unit) -> dict[str, Any]:
    """Everything reported and never gated."""
    run = unit.first.run
    reasons = {} if run is None else exclusions_by_reason(run.ensemble)
    attempts = unit.first.record.attempts
    graft_stalls = [a for a in attempts if a.reason == TIMEOUT_REASONS[1]]
    block: dict[str, Any] = {
        "barrier": unit.barrier,
        "barrier_error": unit.barrier_error,
        "stall_count": len(unit.timeouts),
        "graft_pre_relax_timeouts": len(graft_stalls),
        "timeouts": unit.timeouts,
        "time_lost_to_stalls_s": math.fsum(t["wall_time_s"] for t in unit.timeouts),
        "stall_cap_reached_bool": False if run is None else run.stall_cap_reached_bool,
        "orientation_mismatch_count": reasons.get("orientation_mismatch", 0),
        "n_samples_run": len(unit.samples),
        "first_pass_wall_time_s": unit.first.wall_time_s,
        "second_pass_wall_time_s": unit.second.wall_time_s,
        "first_pass_engine_calls": unit.first.engine_calls,
        "first_pass_new_rows": unit.first.new_rows,
        "second_pass_new_rows": unit.second.new_rows,
        "second_pass_engine_calls": unit.second.engine_calls,
        "derivation_new_rows": unit.derivation_new_rows,
        "derivation_engine_calls": unit.derivation_engine_calls,
        "resources": unit.resources,
        "reactants": {
            k: {
                "n_kept": len(v.ensemble.records),
                "ensemble_gibbs_hartree": v.ensemble.ensemble_gibbs_hartree,
            }
            for k, v in sorted(unit.first.reactants.items())
        },
    }
    if run is None:
        return block
    ensemble = run.ensemble
    block.update(
        reactant_key=[list(x) for x in ensemble.reactant_key],
        n_members=len(ensemble.members),
        members=[m.model_dump(mode="json") for m in ensemble.members],
        excluded=[e.model_dump(mode="json") for e in ensemble.excluded],
        exclusions_by_reason=reasons,
        n_merges=len(ensemble.merges),
        n_flagged_merges=len(ensemble.flagged_merges),
        G_pathway_hartree=ensemble.G_pathway_hartree,
        max_pre_relax_wall_time_s=run.max_pre_relax_wall_time_s,
        stage_metrics={
            k: {
                "wall_time_s": m.wall_time_s,
                "engine_calls": m.engine_calls,
                "cache_hits": m.cache_hits,
                "rows_created": m.rows_created,
            }
            for k, m in run.metrics.items()
        },
    )
    return block


# --- Run records ---------------------------------------------------------------------------------


def unit_record(unit: Unit, recipe: Recipe, gates: Mapping[str, Mapping[str, Any]]) -> RunRecord:
    """The unit's ``RunRecord``: one run, its candidate, species and gates (no selectivity)."""
    candidate, run = unit.candidate, unit.first.run
    assert candidate.graph is not None
    (node,) = [n for n in candidate.graph.nodes if n.id == unit.pathway.node_id]
    chosen = unit.first.record.chosen_template_id or node.templates[0].id
    (template,) = [t for t in node.templates if t.id == chosen]
    ts_state = template.components[0].state
    species = [RecordSpecies(species_id=chosen, label=chosen, state=ts_state)]
    endpoints = []
    for species_id, result in sorted(unit.first.reactants.items()):
        state = result.ensemble.records[0].state
        species.append(RecordSpecies(species_id=species_id, label=species_id, state=state))
        endpoints.append(
            RecordEndpoint(
                species_id=species_id,
                opt_keys=list(result.keys["geometry_opt"]),
                frequency_keys=list(result.keys["frequency"]),
            )
        )
    engine = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    record_run = RecordRun(
        candidate_id=candidate.candidate_id,
        pathway=unit.pathway.pathway,
        engine=engine,
        optimizers=[GeometricOptimizer().identity, PRFOOptimizer().identity],
        species_id=chosen,
        analysis=recipe.analysis,
        fallback=unit.first.record,
        ensemble=None if run is None else run.ensemble,
        stall_cap_reached_bool=False if run is None else run.stall_cap_reached_bool,
        dG_dagger_kcal_mol=(
            None if unit.barrier is None else unit.barrier["ensemble_dG_dagger_1M_kcal_mol"]
        ),
        samples=unit.samples,
        endpoints=endpoints,
    )
    ref = RecordUnitRef(
        candidate_id=candidate.candidate_id, pathway=unit.pathway.pathway, engine=engine
    )
    return RunRecord(
        species=species,
        candidates=[
            RecordCandidate(
                candidate_id=candidate.candidate_id,
                entry_ids_by_site=candidate.entry_ids_by_site,
                records=candidate.records,
            )
        ],
        runs=[record_run],
        gates=[
            RecordGate(gate_id=f"G7.{name}", unit_ref=ref, pass_bool=g["status"] == "pass")
            for name, g in sorted(gates.items())
        ],
    )


def export_report(record: RunRecord, store_path: Path) -> dict[str, int]:
    """Export the record from the store (engine-free) and count what the exporter found."""
    with ArtifactStore(store_path) as store:
        data = export_run_data(record, store)
    return {
        "candidates": len(data.candidates),
        "trajectories": len(data.trajectories),
        "trajectories_missing": sum(t.status == "missing" for t in data.trajectories),
        "frequencies": len(data.frequencies),
        "frequencies_missing": sum(f.status == "missing" for f in data.frequencies),
    }


def checked_record_text(record: RunRecord) -> str:
    """The record's JSON, refused unless it has finite ratios and reads back equal.

    Raises:
        ValueError: A selectivity ratio is not finite (it would be written as ``null``; mission
            slice 07 audit carry-forward: stop and report).
    """
    for scored in record.selectivity:
        if not math.isfinite(scored.result.ratio):
            raise ValueError(
                f"STOP AND REPORT: selectivity ratio of {scored.candidate_id} on "
                f"{scored.engine.name} is {scored.result.ratio}"
            )
    text = record.model_dump_json(indent=1)
    assert RunRecord.model_validate_json(text) == record
    return text + "\n"


def write_record(name: str, record: RunRecord, state: Path) -> None:
    """Write the record to the state directory and the candidate directory."""
    text = checked_record_text(record)
    for folder in (state / "records", candidate_dir()):
        (folder / f"{name}.runrecord.json").write_text(text, encoding="utf-8", newline="\n")


# --- One (R, engine): score the two pathways -----------------------------------------------------


def read_unit_record(state: Path, name: str) -> RunRecord:
    """A unit's record from the state directory (never from the candidate directory)."""
    path = state / "records" / f"{name}.runrecord.json"
    return RunRecord.model_validate_json(path.read_text(encoding="utf-8"))


def score_pair(
    records: Mapping[str, RunRecord],
) -> tuple[SelectivityResult, dict[str, TSEnsemble], RunRecord]:
    """Score the endo and exo ensembles of one (R, engine) and merge the two unit records."""
    assert sorted(records) == sorted(PATHWAYS)
    runs = {}
    for pathway, record in records.items():
        (run,) = record.runs
        assert run.pathway == pathway and run.ensemble is not None, pathway
        runs[pathway] = run
    assert len({r.candidate_id for r in runs.values()}) == 1
    assert runs["endo"].engine == runs["exo"].engine
    ensembles = {p: r.ensemble for p, r in runs.items() if r.ensemble is not None}
    temperature_k = ensembles["endo"].temperature_k
    result = score_selectivity(ensembles, kind="de", temperature_k=temperature_k)
    species: dict[str, RecordSpecies] = {}
    for pathway in PATHWAYS:
        for entry in records[pathway].species:
            assert species.setdefault(entry.species_id, entry) == entry
    engine = runs["endo"].engine
    candidate_id = runs["endo"].candidate_id
    assert records["endo"].candidates == records["exo"].candidates
    merged = RunRecord(
        species=list(species.values()),
        candidates=records["endo"].candidates,
        runs=[runs[p] for p in PATHWAYS],
        selectivity=[RecordSelectivity(candidate_id=candidate_id, engine=engine, result=result)],
        gates=[g for p in PATHWAYS for g in records[p].gates],
    )
    return result, ensembles, merged
