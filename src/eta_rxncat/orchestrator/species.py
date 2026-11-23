"""Single-species stage runner with per-stage caching (v0.3.0; TJ Q4 "C"; R7, R15, R18, R35, R42).

Stages, each cached in the v0.1.0 ``ArtifactStore`` under ``build_stage_key``:

- ``conformer_search`` (0 engine calls): the two-pass ETKDG pool, keyed on pass-1 embedding 0.
- ``geometry_opt`` per pre-dedup survivor (and per imaginary-mode push, and per constrained point).
- ``frequency`` per kept conformer: energy and Hessian. Thermochemistry is recomputed from the
  stored Hessian every time and never stored.
- ``single_point`` stages added incrementally on the kept conformers.

The optimizer options enter the ``geometry_opt`` key with an ``opt.`` prefix (plus ``opt.name``,
``opt.version`` and, for a constrained run only, ``opt.constraints``); the engine itself is
always built from the stage without them. Keys use the *requested* optimizer options, the same
ones ``OptimizationResult.options`` records.
"""

import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import rdkit

from eta_rxncat.conformers import (
    ConformerOptions,
    ConformerPool,
    EnsembleEmptyError,
    PoolMember,
    assign_degeneracy,
    build_ensemble,
    dedup,
    drop_mirror_partners,
    energy_window,
    generate,
)
from eta_rxncat.core import (
    ConformerEnsemble,
    ConformerRecord,
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    StageConfig,
    ThermoAnalysisOptions,
    ThermoConfig,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import (
    Engine,
    ESENOMol25Engine,
    MACEEngine,
    PySCFEngine,
    RDKitFFEngine,
    ScfConvergenceError,
    UMADirectEngine,
    XTBSubprocessEngine,
)
from eta_rxncat.optimize import (
    DihedralConstraint,
    OptimizationFailedError,
    Optimizer,
    OptimizerInputError,
    constraints_text,
)
from eta_rxncat.orchestrator.counting import CountingEngine
from eta_rxncat.store import (
    ArtifactStatus,
    ArtifactStore,
    StageKey,
    build_stage_key,
    geometry_payload,
)
from eta_rxncat.thermo import (
    NotAMinimumError,
    ThermoInputError,
    check_ground_state,
    normal_modes,
    thermochemistry,
)

ENGINE_CLASSES: dict[str, type[Engine]] = {
    "rdkit_ff": RDKitFFEngine,
    "mace": MACEEngine,
    "uma_direct": UMADirectEngine,
    "pyscf_gpu_cpu": PySCFEngine,
    "xtb_subprocess": XTBSubprocessEngine,
    "esen_omol25": ESENOMol25Engine,
}
"""Engine class per tag (tests replace entries with fakes)."""

PUSH_MAX_DISPLACEMENT_ANGSTROM = 0.1
"""Largest atomic displacement of the imaginary-mode push (R15)."""

STAGE_KINDS = ("conformer_search", "geometry_opt", "frequency", "single_point")


@dataclass(frozen=True)
class SpeciesSpec:
    """One species to run.

    Attributes:
        species_id: Identifier used in reports and reactions.
        smiles: SMILES (atom order of every state is ``AddHs(smiles)``).
        charge: Total charge.
        spin_multiplicity: ``2S + 1``.
        conformer_options: Conformer generation settings.
        seed_geometries: Optional seed geometries.
    """

    species_id: str
    smiles: str
    charge: int
    spin_multiplicity: int
    conformer_options: ConformerOptions = field(default_factory=ConformerOptions)
    seed_geometries: tuple[MolecularState, ...] = ()


@dataclass(frozen=True)
class Recipe:
    """An engine stage, an optimizer and thermochemistry settings.

    Attributes:
        name: Recipe name.
        engine_stage: The engine stage (its kind is ignored; the runner sets each stage's kind).
        optimizer: The optimizer.
        optimizer_options: Requested optimizer options (resolved by the optimizer).
        thermo_config: Thermochemistry settings.
        analysis: Normal-mode and symmetry tolerances.
        engine_runtime: Runtime keyword arguments for the engine constructor.
    """

    name: str
    engine_stage: StageConfig
    optimizer: Optimizer
    optimizer_options: Mapping[str, ScalarValue] = field(default_factory=dict)
    thermo_config: ThermoConfig = field(default_factory=ThermoConfig)
    analysis: ThermoAnalysisOptions = field(default_factory=ThermoAnalysisOptions)
    engine_runtime: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SinglePoint:
    """An incremental single-point stage.

    Attributes:
        stage: The single-point stage (kind is set to ``single_point``).
        only_lowest: Run it only on the lowest-G kept conformer.
        engine_runtime: Runtime keyword arguments for its engine.
    """

    stage: StageConfig
    only_lowest: bool = False
    engine_runtime: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class StageMetrics:
    """Per-stage-kind metrics.

    Attributes:
        wall_time_s: Wall time spent in the stage (s).
        engine_calls: Engine evaluations counted by ``CountingEngine``.
        cache_hits: Rows served from the store.
        rows_created: Rows written (completed or failed) because of a miss.
    """

    wall_time_s: float = 0.0
    engine_calls: int = 0
    cache_hits: int = 0
    rows_created: int = 0


@dataclass
class RunMetrics:
    """Metrics of one ``run_species`` (or ``run_constrained_point``) call."""

    stages: dict[str, StageMetrics] = field(
        default_factory=lambda: {k: StageMetrics() for k in STAGE_KINDS}
    )
    optimizer_steps_total: int = 0
    recovery_steps: Counter[str] = field(default_factory=Counter)

    @property
    def engine_calls(self) -> int:
        """All engine evaluations."""
        return sum(m.engine_calls for m in self.stages.values())

    def as_payload(self) -> dict[str, Any]:
        """Return the metrics as a JSON-ready mapping (sorted recovery-step counts)."""
        return {
            "stages": {
                k: {
                    "wall_time_s": m.wall_time_s,
                    "engine_calls": m.engine_calls,
                    "cache_hits": m.cache_hits,
                    "rows_created": m.rows_created,
                }
                for k, m in self.stages.items()
            },
            "optimizer_steps_total": self.optimizer_steps_total,
            "recovery_steps": dict(sorted(self.recovery_steps.items())),
        }


@dataclass(frozen=True)
class SpeciesResult:
    """The result of ``run_species``.

    Attributes:
        ensemble: The Boltzmann ensemble of the kept conformers.
        dropped: ``(source_id, reason)`` for every conformer not in the ensemble.
        single_point_energies: Per single-point stage (index into ``single_points``), the energy
            (Eh) per ensemble record index.
        metrics: Per-stage metrics.
        keys: Every stage key the run used, by kind, in visit order.
    """

    ensemble: ConformerEnsemble
    dropped: tuple[tuple[int, str], ...]
    single_point_energies: dict[int, dict[int, float]]
    metrics: RunMetrics
    keys: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ConstrainedPoint:
    """A constrained optimization (R42): stationary only within the constraint.

    Attributes:
        state: The optimized geometry.
        energy_hartree: Its energy (Eh).
        optimization: The optimizer result (``options["constraints"]`` set).
        cache_hit: Whether the row came from the store.
        key: The ``geometry_opt`` stage key.
        metrics: Per-stage metrics.
    """

    state: MolecularState
    energy_hartree: float
    optimization: OptimizationResult
    cache_hit: bool
    key: str
    metrics: RunMetrics


def build_engine(stage: StageConfig, runtime: Mapping[str, Any]) -> Engine:
    """Build the engine for ``stage`` from ``ENGINE_CLASSES``."""
    return ENGINE_CLASSES[stage.engine].from_stage(stage, **dict(runtime))


def _with_kind(stage: StageConfig, kind: str, options: Mapping[str, ScalarValue]) -> StageConfig:
    """Return ``stage`` with another kind and options (validated)."""
    data = stage.model_dump()
    data["kind"] = kind
    data["options"] = dict(options)
    return StageConfig.model_validate(data)


def _state(template: MolecularState, xyz: Sequence[Sequence[float]]) -> MolecularState:
    """Return ``template`` at new coordinates."""
    return MolecularState.model_validate(
        {**template.model_dump(), "coordinates": [list(r) for r in xyz]}
    )


class _Runner:
    """Shared state of one run: engine, counting, store and metrics."""

    def __init__(self, spec: SpeciesSpec, recipe: Recipe, store: ArtifactStore) -> None:
        self.spec = spec
        self.recipe = recipe
        self.store = store
        self.engine = CountingEngine(build_engine(recipe.engine_stage, recipe.engine_runtime))
        self.metrics = RunMetrics()
        self.keys: dict[str, list[str]] = {k: [] for k in STAGE_KINDS}

    # stage plumbing -------------------------------------------------------------------------

    def _lookup(self, kind: str, key: StageKey) -> dict[str, Any] | None:
        """Return the completed payload of ``key`` (a hit) or ``None`` (a miss)."""
        self.keys[kind].append(key.key)
        payload = self.store.get(key)
        if payload is not None:
            self.metrics.stages[kind].cache_hits += 1
        return payload

    def _save(self, kind: str, key: StageKey, payload: Mapping[str, Any]) -> None:
        """Write a completed row; a failure is a completed row carrying ``failed_reason``."""
        self.store.put(key, ArtifactStatus.COMPLETED, payload)
        self.metrics.stages[kind].rows_created += 1

    def _timed(self, kind: str) -> "_Timer":
        self.engine.kind = kind
        return _Timer(self, kind)

    # stage definitions ----------------------------------------------------------------------

    def opt_stage(self, constraints: str = "") -> StageConfig:
        """The ``geometry_opt`` key stage: engine options plus ``opt.`` optimizer options."""
        optimizer = self.recipe.optimizer
        resolved = optimizer.resolved_options(self.recipe.optimizer_options)
        identity = optimizer.identity
        options: dict[str, ScalarValue] = dict(self.engine.stage.options)
        options.update({f"opt.{k}": v for k, v in resolved.items()})
        options["opt.name"] = identity.name
        options["opt.version"] = identity.version
        if constraints:
            options["opt.constraints"] = constraints
        return _with_kind(self.engine.stage, "geometry_opt", options)

    def conformer_search(self) -> ConformerPool:
        """Generate the pool (always; RDKit runs before the lookup) and cache its payload."""
        spec = self.spec
        with self._timed("conformer_search"):
            pool = generate(
                spec.smiles,
                charge=spec.charge,
                spin_multiplicity=spec.spin_multiplicity,
                options=spec.conformer_options,
                seed_geometries=spec.seed_geometries,
            )
            options: dict[str, ScalarValue] = dict(spec.conformer_options.as_stage_options())
            options.update(
                {
                    "smiles": pool.canonical_smiles,
                    "rdkit_version": rdkit.__version__,
                    "seed_geometries_sha256": pool.seed_geometries_sha256,
                }
            )
            stage = _with_kind(self.engine.stage, "conformer_search", options)
            first = next((m for m in pool.members if m.origin == "etkdg"), pool.members[0])
            key = build_stage_key(first.state, stage, self.engine.identity)
            if self._lookup("conformer_search", key) is None:
                self._save("conformer_search", key, _pool_payload(pool))
        return pool

    def optimize(
        self,
        state: MolecularState,
        *,
        frozen: Sequence[int] = (),
        dihedrals: Sequence[DihedralConstraint] = (),
    ) -> tuple[OptimizationResult | None, str | None, bool, str]:
        """Return (result or None, failure reason or None, cache_hit, key) of one optimization."""
        text = constraints_text(frozen, dihedrals)
        key = build_stage_key(state, self.opt_stage(text), self.engine.identity)
        with self._timed("geometry_opt"):
            payload = self._lookup("geometry_opt", key)
            if payload is not None and "failed_reason" in payload:
                return None, str(payload["failed_reason"]), True, key.key
            if payload is not None:
                return _opt_from_payload(state, payload), None, True, key.key
            try:
                result = self.recipe.optimizer.minimize(
                    state,
                    self.engine,
                    frozen_atom_indices=frozen,
                    dihedral_constraints=dihedrals,
                    options=self.recipe.optimizer_options,
                )
            except (OptimizationFailedError, ScfConvergenceError) as exc:
                reason = (
                    "optimization_failed"
                    if isinstance(exc, OptimizationFailedError)
                    else "scf_convergence"
                )
                self._save("geometry_opt", key, {"failed_reason": reason, "message": str(exc)})
                return None, reason, False, key.key
            self._save("geometry_opt", key, _opt_payload(result))
        self.metrics.optimizer_steps_total += result.n_steps
        self.metrics.recovery_steps.update(result.recovery_steps)
        return result, None, False, key.key

    def frequency(
        self, state: MolecularState
    ) -> tuple[float, list[list[float]], dict[str, Any]] | str:
        """Return (energy, Hessian, stored geometry payload) of ``state``, or a failure reason."""
        stage = _with_kind(self.engine.stage, "frequency", self.engine.stage.options)
        key = build_stage_key(state, stage, self.engine.identity)
        with self._timed("frequency"):
            payload = self._lookup("frequency", key)
            if payload is not None and "failed_reason" in payload:
                return str(payload["failed_reason"])
            if payload is not None:
                return (
                    float(payload["energy_hartree"]),
                    payload["hessian_hartree_per_bohr2"],
                    payload["geometry"],
                )
            try:
                result = self.engine.evaluate(state, forces=False, hessian=True)
            except ScfConvergenceError as exc:
                failure = {"failed_reason": "scf_convergence", "message": str(exc)}
                self._save("frequency", key, failure)
                return "scf_convergence"
            hessian = result.hessian_hartree_per_bohr2
            assert hessian is not None  # evaluate(hessian=True) guarantees it
            matrix = [list(row) for row in hessian]
            geometry = geometry_payload(state)
            payload = {
                "energy_hartree": result.energy_hartree,
                "hessian_hartree_per_bohr2": matrix,
                "hessian_method": result.hessian_method,
                "geometry": geometry,
            }
            self._save("frequency", key, payload)
        return result.energy_hartree, matrix, geometry

    def single_point(self, sp: SinglePoint, state: MolecularState) -> tuple[float, dict[str, Any]]:
        """Return (energy, stored geometry payload) of a single point on ``state``."""
        engine = CountingEngine(build_engine(sp.stage, sp.engine_runtime))
        engine.kind = "single_point"
        stage = _with_kind(engine.stage, "single_point", engine.stage.options)
        key = build_stage_key(state, stage, engine.identity)
        start = time.perf_counter()
        try:
            payload = self._lookup("single_point", key)
            if payload is not None:
                return float(payload["energy_hartree"]), payload["geometry"]
            result = engine.evaluate(state, forces=False, hessian=False)
            geometry = geometry_payload(state)
            self._save(
                "single_point", key, {"energy_hartree": result.energy_hartree, "geometry": geometry}
            )
            return result.energy_hartree, geometry
        finally:
            self.metrics.stages["single_point"].wall_time_s += time.perf_counter() - start
            self.metrics.stages["single_point"].engine_calls += engine.total


class _Timer:
    """Context manager adding wall time and counted calls to a stage's metrics."""

    def __init__(self, runner: _Runner, kind: str) -> None:
        self.runner = runner
        self.kind = kind

    def __enter__(self) -> None:
        self.start = time.perf_counter()
        self.calls = self.runner.engine.total

    def __exit__(self, *exc: object) -> None:
        metrics = self.runner.metrics.stages[self.kind]
        metrics.wall_time_s += time.perf_counter() - self.start
        metrics.engine_calls += self.runner.engine.total - self.calls


def _pool_payload(pool: ConformerPool) -> dict[str, Any]:
    """The stored form of a conformer pool."""
    return {
        "members": [
            {"id": m.source_id, "origin": m.origin, "xyz": [list(r) for r in m.state.coordinates]}
            for m in pool.members
        ],
        "failure_counts": {k: list(v) for k, v in sorted(pool.failure_counts.items())},
        "pre_dedup_survivors": list(pool.pre_dedup_survivors),
        "options": pool.options.as_stage_options(),
        "canonical_smiles": pool.canonical_smiles,
        "seed_geometries_sha256": pool.seed_geometries_sha256,
    }


def _opt_payload(result: OptimizationResult) -> dict[str, Any]:
    """The stored form of an optimization result."""
    return {
        "final_xyz": [list(r) for r in result.final_state.coordinates],
        "final_energy_hartree": result.final_energy_hartree,
        "n_steps": result.n_steps,
        "n_engine_calls": result.n_engine_calls,
        "recovery_steps": list(result.recovery_steps),
        "optimizer": result.optimizer.model_dump(),
        "options": dict(result.options),
    }


def _opt_from_payload(start: MolecularState, payload: Mapping[str, Any]) -> OptimizationResult:
    """Rebuild an ``OptimizationResult`` from its stored form."""
    return OptimizationResult(
        final_state=_state(start, payload["final_xyz"]),
        final_energy_hartree=payload["final_energy_hartree"],
        converged=True,
        n_steps=payload["n_steps"],
        n_engine_calls=payload["n_engine_calls"],
        recovery_steps=list(payload["recovery_steps"]),
        optimizer=OptimizerIdentity.model_validate(payload["optimizer"]),
        options=dict(payload["options"]),
    )


def _push_directions(
    state: MolecularState, hessian: Sequence[Sequence[float]], analysis: ThermoAnalysisOptions
) -> tuple[MolecularState, MolecularState]:
    """Return the state displaced both ways along its lowest mode (largest atom move 0.1 A)."""
    modes = normal_modes(state.symbols, state.coordinates, hessian, analysis=analysis)
    vector = modes.modes_cartesian[:, 0].reshape(-1, 3)
    vector = vector * (PUSH_MAX_DISPLACEMENT_ANGSTROM / float(np.linalg.norm(vector, axis=1).max()))
    xyz = np.asarray(state.coordinates, dtype=np.float64)
    return _state(state, (xyz + vector).tolist()), _state(state, (xyz - vector).tolist())


def run_species(
    spec: SpeciesSpec,
    recipe: Recipe,
    store: ArtifactStore,
    *,
    single_points: Sequence[SinglePoint | StageConfig] = (),
    energy_source: Literal["optimization", "single_point"] = "optimization",
) -> SpeciesResult:
    """Run every stage of one species and return its Boltzmann ensemble.

    A conformer is dropped (with its reason) on ``OptimizationFailedError``,
    ``ScfConvergenceError`` or a persistent imaginary mode after one push (``not_a_minimum``).
    ``EngineUnavailableError``, ``EngineInputError``, ``EngineRuntimeError`` and
    ``OptimizerInputError`` propagate.

    Args:
        spec: The species.
        recipe: Engine, optimizer and thermochemistry settings.
        store: The artifact store.
        single_points: Incremental single-point stages on the kept conformers.
        energy_source: ``single_point`` takes E from the first single point (its geometry must be
            the frequency stage's, R35).

    Raises:
        EnsembleEmptyError: Every conformer was dropped; it carries each reason.
        ThermoInputError: ``energy_source="single_point"`` without a matching single point.
    """
    runner = _Runner(spec, recipe, store)
    sps = [s if isinstance(s, SinglePoint) else SinglePoint(stage=s) for s in single_points]
    if energy_source == "single_point" and not sps:
        raise ThermoInputError('energy_source="single_point" needs at least one single point')
    pool = runner.conformer_search()

    # geometry_opt per survivor
    survivors: list[PoolMember] = list(pool.survivors())
    optimized: list[tuple[PoolMember, OptimizationResult]] = []
    dropped: list[tuple[int, str]] = []
    for member in survivors:
        result, reason, _, _ = runner.optimize(member.state)
        if result is None:
            dropped.append((member.source_id, str(reason)))
        else:
            optimized.append((member, result))

    # dedup and window
    states = [r.final_state for _, r in optimized]
    energies = [r.final_energy_hartree for _, r in optimized]
    kept = dedup(states, energies, spec.conformer_options, smiles=spec.smiles) if optimized else []
    inside, outside = energy_window(kept, energies, spec.conformer_options)
    for k in outside:
        dropped.append((optimized[k.index][0].source_id, "energy_window"))

    # frequency, push, thermo, degeneracy
    records: list[ConformerRecord] = []
    freq_geometry: dict[tuple[int, ...], dict[str, Any]] = {}
    for k in inside:
        member, result = optimized[k.index]
        source_ids = sorted(optimized[i][0].source_id for i in k.source_ids)
        done = _frequency_and_thermo(runner, spec, recipe, result, source_ids, dropped)
        if done is not None:
            freq_geometry[tuple(done[0].source_ids)] = done[1]
            records.append(done[0])

    records = _dedup_after_push(records, spec, dropped)
    kept_records, mirrored = drop_mirror_partners(records, spec.smiles, spec.conformer_options)
    for index, reason in mirrored:
        dropped.append((records[index].source_ids[0], reason))
    if not kept_records:
        raise EnsembleEmptyError(sorted(dropped))
    records = kept_records

    # incremental single points
    sp_energies: dict[int, dict[int, float]] = {}
    lowest = min(
        range(len(records)), key=lambda i: (records[i].thermo.gibbs_free_energy_hartree, i)
    )
    for s_index, sp in enumerate(sps):
        targets = [lowest] if sp.only_lowest else list(range(len(records)))
        sp_energies[s_index] = {}
        for r_index in targets:
            energy, geometry = runner.single_point(sp, records[r_index].state)
            sp_energies[s_index][r_index] = energy
            if energy_source == "single_point" and s_index == 0:
                if geometry != freq_geometry[tuple(records[r_index].source_ids)]:
                    raise ThermoInputError(
                        "single-point geometry differs from the frequency stage's (R35)"
                    )
                records[r_index] = _with_energy(records[r_index], energy)
    if energy_source == "single_point":
        missing = [i for i in range(len(records)) if i not in sp_energies.get(0, {})]
        if missing:
            raise ThermoInputError(f"records {missing} have no single point for energy_source")

    ensemble = build_ensemble(
        spec.species_id, spec.smiles, records, recipe.thermo_config.temperature_k
    )
    return SpeciesResult(
        ensemble=ensemble,
        dropped=tuple(sorted(dropped)),
        single_point_energies=sp_energies,
        metrics=runner.metrics,
        keys={k: tuple(v) for k, v in runner.keys.items()},
    )


def _dedup_after_push(
    records: list[ConformerRecord], spec: SpeciesSpec, dropped: list[tuple[int, str]]
) -> list[ConformerRecord]:
    """Drop a record whose final geometry duplicates an earlier kept record (R53).

    The imaginary-mode push re-optimizes a conformer after the first dedup, so it can land on
    another kept conformer. The existing ``dedup`` rule (R3: proper-rotation RMSD over graph
    automorphisms at ``rmsd_dedup_angstrom``) runs again over the final geometries, visited by
    record G (ties to the lower index). A match is dropped as ``duplicate_after_push`` under its
    first source id; the survivor is unchanged and keeps its own source ids. Without a push no pair
    can match (the geometries were deduplicated already), so the record set is then unchanged.
    """
    if len(records) < 2:
        return records
    kept = dedup(
        [r.state for r in records],
        [r.thermo.gibbs_free_energy_hartree for r in records],
        spec.conformer_options,
        smiles=spec.smiles,
    )
    survivors = sorted(k.index for k in kept)
    for k in kept:
        for i in k.source_ids:
            if i != k.index:
                dropped.append((records[i].source_ids[0], "duplicate_after_push"))
    return [records[i] for i in survivors]


def _thermo(
    spec: SpeciesSpec, recipe: Recipe, state: MolecularState, energy: float, hessian: Any
) -> Any:
    return thermochemistry(
        state,
        hessian,
        energy,
        smiles=spec.smiles,
        energy_source="optimization",
        config=recipe.thermo_config,
        analysis=recipe.analysis,
    )


def _frequency_and_thermo(
    runner: _Runner,
    spec: SpeciesSpec,
    recipe: Recipe,
    result: OptimizationResult,
    source_ids: list[int],
    dropped: list[tuple[int, str]],
) -> tuple[ConformerRecord, dict[str, Any]] | None:
    """Frequency, one imaginary-mode push at most, thermo and degeneracy of one kept conformer.

    Returns the record and the frequency row's stored geometry payload.
    """
    freq = runner.frequency(result.final_state)
    if isinstance(freq, str):
        dropped.append((source_ids[0], freq))
        return None
    thermo = _thermo(spec, recipe, result.final_state, result.final_energy_hartree, freq[1])
    try:
        check_ground_state(thermo)
    except NotAMinimumError:
        pushed = _push(runner, spec, recipe, result, freq[1])
        if pushed is None:
            dropped.append((source_ids[0], "optimization_failed"))
            return None
        result = pushed
        freq = runner.frequency(result.final_state)
        if isinstance(freq, str):
            dropped.append((source_ids[0], freq))
            return None
        thermo = _thermo(spec, recipe, result.final_state, result.final_energy_hartree, freq[1])
        try:
            check_ground_state(thermo)
        except NotAMinimumError:
            dropped.append((source_ids[0], "not_a_minimum"))
            return None
    record = ConformerRecord(
        state=result.final_state,
        optimization=result,
        thermo=thermo,
        degeneracy=assign_degeneracy(result.final_state, spec.smiles, spec.conformer_options),
        source_ids=source_ids,
    )
    return record, freq[2]


def _push(
    runner: _Runner,
    spec: SpeciesSpec,
    recipe: Recipe,
    result: OptimizationResult,
    hessian: Any,
) -> OptimizationResult | None:
    """Optimize both displacements along the lowest imaginary mode; keep the lower energy."""
    plus, minus = _push_directions(result.final_state, hessian, recipe.analysis)
    candidates = []
    for displaced in (plus, minus):
        pushed, _, _, _ = runner.optimize(displaced)
        if pushed is not None:
            candidates.append(pushed)
    if not candidates:
        return None
    best = min(candidates, key=lambda r: r.final_energy_hartree)
    runner.metrics.recovery_steps["imag_mode_push"] += 1
    return best.model_copy(
        update={"recovery_steps": [*result.recovery_steps, "imag_mode_push", *best.recovery_steps]}
    )


def _with_energy(record: ConformerRecord, energy: float) -> ConformerRecord:
    """Return ``record`` with its thermochemistry rebased on a single-point energy (R35)."""
    thermo = record.thermo
    data = thermo.model_dump()
    data["electronic_energy_hartree"] = energy
    data["energy_source"] = "single_point"
    data["gibbs_free_energy_hartree"] = energy + thermo.thermal_correction_gibbs_hartree
    return record.model_copy(update={"thermo": type(thermo).model_validate(data)})


def run_constrained_point(
    spec: SpeciesSpec,
    recipe: Recipe,
    store: ArtifactStore,
    start_state: MolecularState,
    *,
    frozen_atom_indices: Sequence[int] = (),
    dihedral_constraints: Sequence[DihedralConstraint] = (),
) -> ConstrainedPoint:
    """Run one cached constrained ``geometry_opt`` (R42): no frequency, thermo or ensemble.

    The key adds ``opt.constraints`` to the usual ``geometry_opt`` options, so it differs from the
    unconstrained key of the same start, and unconstrained keys are unchanged.

    Raises:
        OptimizerInputError: No constraint given, or frozen atoms combined with dihedrals (that
            geomeTRIC path is untested and has hung, slice 04), or the optimizer's own input
            errors.
        OptimizationFailedError: The constrained optimization failed (also when cached as failed).
    """
    if not frozen_atom_indices and not dihedral_constraints:
        raise OptimizerInputError("run_constrained_point needs at least one constraint")
    if frozen_atom_indices and dihedral_constraints:
        raise OptimizerInputError(
            "frozen atoms together with dihedral constraints are refused: untested in geomeTRIC "
            "(enforce applies to frozen atoms only, slice 04) and seen to hang"
        )
    runner = _Runner(spec, recipe, store)
    result, reason, hit, key = runner.optimize(
        start_state, frozen=frozen_atom_indices, dihedrals=dihedral_constraints
    )
    if result is None:
        raise OptimizationFailedError(
            f"constrained optimization failed ({reason})", steps=(), last_energy_hartree=None
        )
    return ConstrainedPoint(
        state=result.final_state,
        energy_hartree=result.final_energy_hartree,
        optimization=result,
        cache_hit=hit,
        key=key,
        metrics=runner.metrics,
    )


__all__ = [
    "ENGINE_CLASSES",
    "ConstrainedPoint",
    "Recipe",
    "RunMetrics",
    "SinglePoint",
    "SpeciesResult",
    "SpeciesSpec",
    "StageMetrics",
    "build_engine",
    "run_constrained_point",
    "run_species",
]
