"""The transition-state runner: search, frequency, validation, TS thermochemistry (v0.5.0).

Mission §5 "TS runner". ``run_transition_state`` caches the P-RFO search under the ``ts_opt``
stage kind (ADR-0038) and the final Hessian under ``frequency`` with the species runner's key rule,
failures included as completed rows carrying ``failed_reason`` (v0.3.0 R50). A TS never enters
the species runner's minimum path (R13, N3): this module calls none of ``run_species``,
``check_ground_state``, ``_frequency_and_thermo``, ``_push`` or ``_dedup_after_push``.
Connectivity is reported, never gated (R3, N7).
"""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from eta_rxncat.core import (
    MolecularState,
    StageConfig,
    ThermoAnalysisOptions,
    ThermoConfig,
    TransitionStateRecord,
    TSSearchResult,
    TSValidation,
    TSValidationOptions,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import EngineRuntimeError, ScfConvergenceError
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.optimize import TransitionStateOptimizer, TSSearchFailedError
from eta_rxncat.orchestrator.counting import CountingEngine
from eta_rxncat.orchestrator.species import StageMetrics, _with_kind, build_engine
from eta_rxncat.store import (
    ArtifactStatus,
    ArtifactStore,
    StageKey,
    build_stage_key,
    geometry_payload,
)
from eta_rxncat.thermo import ts_thermochemistry, validate_transition_state

TS_STAGE_KINDS = ("ts_opt", "frequency")
"""The stage kinds a TS run caches, in visit order."""


@dataclass(frozen=True)
class TSSpec:
    """One transition state to search for.

    Attributes:
        ts_id: Identifier of the TS (a TS record has no SMILES, R1).
        start: The start geometry, with the active core in ``active_atom_indices``.
        forming_bonds: Pairs of atoms whose bond forms or breaks.
        reference: A reference TS for the reported connectivity, if any.
        reference_map: Start index -> reference index; ``None`` means the identity.
    """

    ts_id: str
    start: MolecularState
    forming_bonds: tuple[tuple[int, int], ...]
    reference: MolecularState | None = None
    reference_map: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        """Refuse a reference map that does not cover every start atom."""
        if self.reference_map is not None and len(self.reference_map) != len(self.start.symbols):
            raise ValueError(
                f"reference_map has {len(self.reference_map)} entries for "
                f"{len(self.start.symbols)} atoms"
            )


@dataclass(frozen=True)
class TSRecipe:
    """How to run a TS: engine, TS optimizer and the validator and thermochemistry settings.

    Attributes:
        name: Recipe name.
        engine_stage: The engine's stage (its options key every stage).
        ts_optimizer: The TS search.
        ts_options: Requested TS-optimizer options (keyed as given, resolved).
        thermo_config: Thermochemistry settings.
        analysis: Normal-mode and symmetry tolerances.
        validation_options: The validator's thresholds.
        engine_runtime: Engine runtime arguments (never keyed).
    """

    name: str
    engine_stage: StageConfig
    ts_optimizer: TransitionStateOptimizer
    ts_options: Mapping[str, ScalarValue] = field(default_factory=dict)
    thermo_config: ThermoConfig = field(default_factory=ThermoConfig)
    analysis: ThermoAnalysisOptions = field(default_factory=ThermoAnalysisOptions)
    validation_options: TSValidationOptions = field(default_factory=TSValidationOptions)
    engine_runtime: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TSRunResult:
    """The result of ``run_transition_state``; check ``failed_reason`` first (R50).

    Attributes:
        ts_id: The TS identifier.
        record: The TS record (search, validation, thermochemistry), if the mode count passed.
        search: The converged search, if any.
        validation: The validator's verdict, if the frequency stage completed.
        failed_reason: Why no record exists, or ``None``.
        connectivity_equal_bool: Perceived bonds equal the reference's (mapped); ``None``
            without a reference or a final geometry. Reported only.
        metrics: Per stage kind (``ts_opt``, ``frequency``).
        keys: The stage key per kind.
    """

    ts_id: str
    record: TransitionStateRecord | None
    search: TSSearchResult | None
    validation: TSValidation | None
    failed_reason: str | None
    connectivity_equal_bool: bool | None
    metrics: dict[str, StageMetrics]
    keys: dict[str, str]

    def as_payload(self) -> dict[str, Any]:
        """Return a JSON-ready mapping; ``search.history`` is included but never compared (N11)."""
        return {
            "ts_id": self.ts_id,
            "failed_reason": self.failed_reason,
            "connectivity_equal_bool": self.connectivity_equal_bool,
            "search": None if self.search is None else self.search.model_dump(mode="json"),
            "validation": (
                None if self.validation is None else self.validation.model_dump(mode="json")
            ),
            "thermo": (None if self.record is None else self.record.thermo.model_dump(mode="json")),
            "degeneracy": None if self.record is None else self.record.degeneracy,
            "keys": dict(sorted(self.keys.items())),
            "metrics": {
                kind: {
                    "wall_time_s": m.wall_time_s,
                    "engine_calls": m.engine_calls,
                    "cache_hits": m.cache_hits,
                    "rows_created": m.rows_created,
                }
                for kind, m in self.metrics.items()
            },
        }


def _sorted_pairs(pairs: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Return the pairs as sorted ``(min, max)`` tuples."""
    return sorted((min(i, j), max(i, j)) for i, j in pairs)


def _runtime_failure(exc: EngineRuntimeError) -> dict[str, str]:
    """Return the cached payload of an engine crash (mission R3): a completed failure row."""
    return {
        "failed_reason": "engine_error",
        "message": str(exc),
        "error_type": type(exc).__name__,
    }


class _TSRun:
    """One TS run: counted engine, store, metrics and keys."""

    def __init__(self, spec: TSSpec, recipe: TSRecipe, store: ArtifactStore) -> None:
        self.spec = spec
        self.recipe = recipe
        self.store = store
        self.engine = CountingEngine(build_engine(recipe.engine_stage, recipe.engine_runtime))
        self.metrics = {kind: StageMetrics() for kind in TS_STAGE_KINDS}
        self.keys: dict[str, str] = {}
        self.pairs = _sorted_pairs(spec.forming_bonds)

    def _lookup(self, kind: str, key: StageKey) -> dict[str, Any] | None:
        self.keys[kind] = key.key
        payload = self.store.get(key)
        if payload is not None:
            self.metrics[kind].cache_hits += 1
        return payload

    def _save(self, kind: str, key: StageKey, payload: Mapping[str, Any]) -> None:
        self.store.put(key, ArtifactStatus.COMPLETED, payload)
        self.metrics[kind].rows_created += 1

    def ts_stage(self) -> StageConfig:
        """The ``ts_opt`` key stage: engine options plus resolved ``opt.`` TS options."""
        optimizer = self.recipe.ts_optimizer
        resolved = optimizer.resolved_options(self.recipe.ts_options)
        identity = optimizer.identity
        options: dict[str, ScalarValue] = dict(self.engine.stage.options)
        options.update({f"opt.{k}": v for k, v in resolved.items()})
        options["opt.name"] = identity.name
        options["opt.version"] = identity.version
        options["opt.forming_bonds"] = ";".join(f"{i}-{j}" for i, j in self.pairs)
        return _with_kind(self.engine.stage, "ts_opt", options)

    def search(self) -> TSSearchResult | str:
        """Return the cached or new search, or a failure reason."""
        key = build_stage_key(self.spec.start, self.ts_stage(), self.engine.identity)
        with _Timed(self, "ts_opt"):
            payload = self._lookup("ts_opt", key)
            if payload is not None and "failed_reason" in payload:
                return str(payload["failed_reason"])
            if payload is not None:
                return TSSearchResult.model_validate(payload)
            try:
                result = self.recipe.ts_optimizer.find_saddle(
                    self.spec.start,
                    self.engine,
                    forming_bonds=self.pairs,
                    options=self.recipe.ts_options,
                )
            except TSSearchFailedError as exc:
                reason = f"ts_search_failed:{exc.reason}"
                self._save("ts_opt", key, {"failed_reason": reason, "message": str(exc)})
                return reason
            except ScfConvergenceError as exc:
                failure = {"failed_reason": "scf_convergence", "message": str(exc)}
                self._save("ts_opt", key, failure)
                return "scf_convergence"
            except EngineRuntimeError as exc:
                self._save("ts_opt", key, _runtime_failure(exc))
                return "engine_error"
            self._save("ts_opt", key, result.model_dump(mode="json"))
        return result

    def frequency(self, state: MolecularState) -> tuple[float, list[list[float]]] | str:
        """Return (energy, Hessian) at ``state`` with the species runner's key and payload."""
        stage = _with_kind(self.engine.stage, "frequency", self.engine.stage.options)
        key = build_stage_key(state, stage, self.engine.identity)
        with _Timed(self, "frequency"):
            payload = self._lookup("frequency", key)
            if payload is not None and "failed_reason" in payload:
                return str(payload["failed_reason"])
            if payload is not None:
                return float(payload["energy_hartree"]), payload["hessian_hartree_per_bohr2"]
            try:
                result = self.engine.evaluate(state, forces=False, hessian=True)
            except ScfConvergenceError as exc:
                failure = {"failed_reason": "scf_convergence", "message": str(exc)}
                self._save("frequency", key, failure)
                return "scf_convergence"
            except EngineRuntimeError as exc:
                self._save("frequency", key, _runtime_failure(exc))
                return "engine_error"
            hessian = result.hessian_hartree_per_bohr2
            if hessian is None:
                raise TypeError("engine.evaluate(hessian=True) returned no Hessian")
            matrix = [list(row) for row in hessian]
            self._save(
                "frequency",
                key,
                {
                    "energy_hartree": result.energy_hartree,
                    "hessian_hartree_per_bohr2": matrix,
                    "hessian_method": result.hessian_method,
                    "geometry": geometry_payload(state),
                },
            )
        return result.energy_hartree, matrix

    def connectivity(self, bonds: Sequence[tuple[int, int]]) -> bool | None:
        """Return whether ``bonds`` (mapped to the reference) equal the reference's bonds."""
        reference = self.spec.reference
        if reference is None:
            return None
        mapping = self.spec.reference_map or tuple(range(len(self.spec.start.symbols)))
        mapped = _sorted_pairs([(mapping[i], mapping[j]) for i, j in bonds])
        return mapped == _sorted_pairs(perceive_bonds(reference))

    def result(self, **fields: Any) -> TSRunResult:
        values: dict[str, Any] = {
            "record": None,
            "search": None,
            "validation": None,
            "failed_reason": None,
            "connectivity_equal_bool": None,
        }
        values.update(fields)
        return TSRunResult(
            ts_id=self.spec.ts_id, metrics=self.metrics, keys=dict(self.keys), **values
        )


class _Timed:
    """Context manager adding wall time and counted engine calls to a TS stage's metrics."""

    def __init__(self, run: _TSRun, kind: str) -> None:
        self.run = run
        self.kind = kind

    def __enter__(self) -> None:
        self.run.engine.kind = self.kind
        self.start = time.perf_counter()
        self.calls = self.run.engine.total

    def __exit__(self, *exc: object) -> None:
        metrics = self.run.metrics[self.kind]
        metrics.wall_time_s += time.perf_counter() - self.start
        metrics.engine_calls += self.run.engine.total - self.calls


def run_transition_state(spec: TSSpec, recipe: TSRecipe, store: ArtifactStore) -> TSRunResult:
    """Search, compute the final Hessian, validate and run TS thermochemistry, caching each stage.

    Steps (mission §5 "TS runner"): ``ts_opt`` (P-RFO search, keyed by the start geometry, the
    engine stage, every resolved TS option, the optimizer identity and the sorted forming bonds);
    ``frequency`` at the final geometry (the species runner's key and payload); bonds perceived
    from the final geometry; ``validate_transition_state``; and, if the mode count passed,
    ``ts_thermochemistry`` and a ``TransitionStateRecord``. Otherwise ``failed_reason`` is
    ``ts_validation_failed`` and the validation is kept.

    Raises:
        eta_rxncat.optimize.OptimizerInputError: Bad TS options or forming bonds.
        eta_rxncat.thermo.TSValidationInputError: A validator input that cannot be judged.
        eta_rxncat.engines.EngineUnavailableError: The engine cannot run on this host; never
            cached.
        eta_rxncat.engines.EngineInputError: The engine refuses the input; never cached.

    An ``EngineRuntimeError`` (the engine crashed) and an SCF failure do not raise: each is cached
    as a completed row and returned as ``failed_reason`` ``"engine_error"`` or
    ``"scf_convergence"`` (mission R3).
    """
    run = _TSRun(spec, recipe, store)
    search = run.search()
    if isinstance(search, str):
        return run.result(failed_reason=search)
    state = search.final_state
    bonds = perceive_bonds(state)
    connectivity = run.connectivity(bonds)
    frequency = run.frequency(state)
    if isinstance(frequency, str):
        return run.result(
            search=search, failed_reason=frequency, connectivity_equal_bool=connectivity
        )
    energy, hessian = frequency
    validation = validate_transition_state(
        state,
        hessian,
        forming_bonds=run.pairs,
        options=recipe.validation_options,
        analysis=recipe.analysis,
    )
    if not validation.mode_count_passed_bool:
        return run.result(
            search=search,
            validation=validation,
            failed_reason="ts_validation_failed",
            connectivity_equal_bool=connectivity,
        )
    thermo = ts_thermochemistry(
        state,
        hessian,
        energy,
        validation=validation,
        bonds=bonds,
        energy_source="optimization",
        config=recipe.thermo_config,
        analysis=recipe.analysis,
    )
    record = TransitionStateRecord(
        ts_id=spec.ts_id,
        state=state,
        search=search,
        validation=validation,
        thermo=thermo,
        degeneracy=1,
    )
    return run.result(
        record=record, search=search, validation=validation, connectivity_equal_bool=connectivity
    )
