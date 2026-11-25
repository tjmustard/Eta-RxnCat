"""The TS ensemble runner: sample, pre-relax, re-search, vet, merge, weight (v0.6.0, slice 06).

Mission §5 "Ensemble runner", R1-R3, R5, R8, R11, R17, R19, R24. From a verified seed TS the runner
samples core-frozen conformers (slice 05), pre-relaxes each with the core frozen (cached under the
existing ``constrained_preopt`` stage kind, no new kind), re-searches and validates each with
``run_transition_state``, keeps only members of the seed's reaction and face, merges re-converged
copies, applies the energy window and Boltzmann-weights the rest, so a pathway's free energy counts
each distinct accessible TS once. Every sample that is not summed is recorded with its reason.

The pre-relaxation optimizer is injected: this module never imports geomeTRIC (G8).
"""

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from eta_rxncat.conformers._rmsd import min_rmsds
from eta_rxncat.conformers.ts_sampler import (
    FaceDescriptorError,
    _automorphism_permutations,
    _digest,
    forming_bond_configuration,
    sample_ts_conformers,
)
from eta_rxncat.core import (
    EngineIdentity,
    MolecularState,
    StageConfig,
    TSEnsemble,
    TSEnsembleExclusion,
    TSEnsembleMember,
    TSEnsembleMerge,
    TSEnsembleOptions,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import (
    HARTREE_KCAL_MOL,
    EngineRuntimeError,
    ScfConvergenceError,
)
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.errors import CoreDisplacementError
from eta_rxncat.mapping.relax import relax_constrained_core
from eta_rxncat.optimize import OptimizationFailedError, Optimizer
from eta_rxncat.orchestrator.counting import CountingEngine
from eta_rxncat.orchestrator.species import (
    StageMetrics,
    _opt_payload,
    _state,
    build_engine,
)
from eta_rxncat.orchestrator.ts import (
    TSRecipe,
    TSRunResult,
    TSSpec,
    _sorted_pairs,
    run_transition_state,
)
from eta_rxncat.store import ArtifactStatus, ArtifactStore, build_stage_key
from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS

PRE_RELAX_OPTIONS: Mapping[str, ScalarValue] = {"maxiter": 200}
"""The pre-relaxation's optimizer options (mission R24); keyed."""

PRE_RELAX_KIND = "constrained_preopt"
STAGE_KINDS = (PRE_RELAX_KIND, "ts_opt", "frequency")

FloatArray = NDArray[np.float64]
MemberGates = Callable[[TSRunResult], Mapping[str, bool]]


@dataclass(frozen=True)
class TSEnsembleRun:
    """An ensemble with the per-stage metrics and the seed's own run.

    Attributes:
        ensemble: The ensemble.
        metrics: Per stage kind (``constrained_preopt``, ``ts_opt``, ``frequency``).
        seed_result: The seed's ``run_transition_state`` result.
    """

    ensemble: TSEnsemble
    metrics: dict[str, StageMetrics]
    seed_result: TSRunResult
    max_pre_relax_wall_time_s: float | None = field(default=None)


@dataclass
class _Candidate:
    """A re-searched sample that passed every check."""

    index: int
    source: str
    start_sha256: str
    g_hartree: float
    degeneracy: int
    rmsd_to_seed: float
    face: tuple[int, ...]
    validation_passed: bool
    wall_time: float | None
    coords: FloatArray


def _failed(
    *,
    pathway: str,
    temperature_k: float,
    reactant_key: Sequence[tuple[str, int]],
    identity: EngineIdentity,
    options: TSEnsembleOptions,
    reason: str,
) -> TSEnsemble:
    return TSEnsemble(
        pathway=pathway,
        temperature_k=temperature_k,
        reactant_key=tuple((s, c) for s, c in reactant_key),
        recipe_identity=identity,
        options=options,
        failed_reason=reason,
    )


def _first_failed_gate(gates: Mapping[str, bool]) -> str | None:
    for name, passed in gates.items():
        if not passed:
            return name
    return None


def _add(total: StageMetrics, part: StageMetrics) -> None:
    total.wall_time_s += part.wall_time_s
    total.engine_calls += part.engine_calls
    total.cache_hits += part.cache_hits
    total.rows_created += part.rows_created


class _PreRelax:
    """The cached core-frozen pre-relaxation of one ensemble (mission R5, R24)."""

    def __init__(
        self,
        recipe: TSRecipe,
        store: ArtifactStore,
        optimizer: Optimizer,
        core: Sequence[int],
    ) -> None:
        self.store = store
        self.optimizer = optimizer
        self.core = sorted(core)
        self.engine = CountingEngine(build_engine(recipe.engine_stage, recipe.engine_runtime))
        self.engine.kind = PRE_RELAX_KIND
        self.metrics = StageMetrics()

    def stage(self) -> StageConfig:
        """The keyed stage: engine options, resolved ``opt.`` minimize options, frozen core."""
        resolved = self.optimizer.resolved_options(PRE_RELAX_OPTIONS)
        identity = self.optimizer.identity
        options: dict[str, ScalarValue] = dict(self.engine.stage.options)
        options.update({f"opt.{k}": v for k, v in resolved.items()})
        options["opt.name"] = identity.name
        options["opt.version"] = identity.version
        data = self.engine.stage.model_dump()
        data.update(kind=PRE_RELAX_KIND, options=options, frozen_atom_indices=self.core)
        return StageConfig.model_validate(data)

    def run(self, state: MolecularState) -> tuple[MolecularState | None, str | None, float]:
        """Return (relaxed state or None, failure reason or None, wall time of the relaxation)."""
        key = build_stage_key(state, self.stage(), self.engine.identity)
        stored = self.store.get(key)
        if stored is not None:
            self.metrics.cache_hits += 1
            if "failed_reason" in stored:
                return None, str(stored["failed_reason"]), float(stored["wall_time_s"])
            return _state(state, stored["final_xyz"]), None, float(stored["wall_time_s"])
        calls = self.engine.total
        start = time.perf_counter()
        failure: str | None = None
        message = ""
        result = None
        try:
            result = relax_constrained_core(
                state, self.engine, self.optimizer, self.core, options=PRE_RELAX_OPTIONS
            )
        except (CoreDisplacementError, OptimizationFailedError) as exc:
            failure, message = f"pre_relax_failed:{type(exc).__name__}", str(exc)
        except ScfConvergenceError as exc:
            failure, message = "scf_convergence", str(exc)
        except EngineRuntimeError as exc:
            failure, message = "engine_error", str(exc)
        wall = time.perf_counter() - start
        self.metrics.wall_time_s += wall
        self.metrics.engine_calls += self.engine.total - calls
        if result is None:
            self.store.put(
                key,
                ArtifactStatus.COMPLETED,
                {"failed_reason": failure, "message": message, "wall_time_s": wall},
            )
            self.metrics.rows_created += 1
            return None, failure, wall
        self.store.put(key, ArtifactStatus.COMPLETED, {**_opt_payload(result), "wall_time_s": wall})
        self.metrics.rows_created += 1
        return result.final_state, None, wall


def run_ts_ensemble_detailed(
    seed: TSSpec,
    recipe: TSRecipe,
    store: ArtifactStore,
    *,
    optimizer: Optimizer,
    core_indices: Sequence[int],
    pathway: str,
    reactant_key: Sequence[tuple[str, int]],
    options: TSEnsembleOptions,
    member_gates: MemberGates,
) -> TSEnsembleRun:
    """Run ``run_ts_ensemble`` and also return the per-stage metrics and the seed's run.

    See ``run_ts_ensemble``.
    """
    engine_identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    temperature_k = recipe.thermo_config.temperature_k
    rt = R_GAS * temperature_k * J_PER_MOL_TO_HARTREE
    metrics = {kind: StageMetrics() for kind in STAGE_KINDS}

    def fail(reason: str, seed_result: TSRunResult) -> TSEnsembleRun:
        ensemble = _failed(
            pathway=pathway,
            temperature_k=temperature_k,
            reactant_key=reactant_key,
            identity=engine_identity,
            options=options,
            reason=reason,
        )
        return TSEnsembleRun(ensemble, metrics, seed_result)

    seed_result = run_transition_state(seed, recipe, store)
    for kind in ("ts_opt", "frequency"):
        _add(metrics[kind], seed_result.metrics[kind])
    if seed_result.record is None:
        return fail(f"seed:{seed_result.failed_reason}", seed_result)
    failed_gate = _first_failed_gate(member_gates(seed_result))
    if failed_gate is not None:
        return fail(f"seed:gate_failed:{failed_gate}", seed_result)
    seed_final = seed_result.record.state
    seed_bonds = perceive_bonds(seed_final)
    pairs = _sorted_pairs(seed.forming_bonds)
    try:
        seed_face = forming_bond_configuration(seed_final, pairs, seed_bonds)
    except FaceDescriptorError:
        return fail("seed:face_undetermined", seed_result)

    seed_xyz = np.asarray(seed_final.coordinates, dtype=np.float64)
    perms = _automorphism_permutations(seed_final.symbols, seed_bonds, options.max_automorphisms)
    everything = np.arange(len(seed_final.symbols), dtype=np.intp)

    def rmsd(a: FloatArray, b: FloatArray) -> float:
        return float(min_rmsds(a, [b], perms, everything)[0])

    seed_gibbs = seed_result.record.thermo.gibbs_free_energy_hartree
    candidates = [
        _Candidate(
            index=0,
            source="seed",
            start_sha256=_digest(seed.start),
            g_hartree=seed_gibbs,
            degeneracy=seed_result.record.degeneracy,
            rmsd_to_seed=0.0,
            face=seed_face,
            validation_passed=seed_result.record.validation.passed_bool,
            wall_time=None,
            coords=seed_xyz,
        )
    ]
    excluded: list[TSEnsembleExclusion] = []

    def exclude(index: int, source: str, reason: str, wall: float | None) -> None:
        excluded.append(
            TSEnsembleExclusion(
                index=index, source=source, reason=reason, pre_relax_wall_time_s=wall
            )
        )

    samples = sample_ts_conformers(seed_final, core_indices, pairs, seed_bonds, options)
    pre_relax = _PreRelax(recipe, store, optimizer, core_indices)
    wall_times: list[float] = []
    for index, sample in enumerate(samples[: options.max_research], start=1):
        relaxed, reason, wall = pre_relax.run(sample.state)
        wall_times.append(wall)
        if relaxed is None:
            exclude(index, sample.source, str(reason), wall)
            continue
        result = run_transition_state(
            TSSpec(
                ts_id=f"{seed.ts_id}:{sample.source}",
                start=relaxed,
                forming_bonds=seed.forming_bonds,
            ),
            recipe,
            store,
        )
        for kind in ("ts_opt", "frequency"):
            _add(metrics[kind], result.metrics[kind])
        if result.record is None:
            exclude(index, sample.source, str(result.failed_reason), wall)
            continue
        failed_gate = _first_failed_gate(member_gates(result))
        if failed_gate is not None:
            exclude(index, sample.source, f"gate_failed:{failed_gate}", wall)
            continue
        final = result.record.state
        if sorted(perceive_bonds(final)) != sorted(seed_bonds):
            exclude(index, sample.source, "connectivity_changed", wall)
            continue
        try:
            face = forming_bond_configuration(final, pairs, seed_bonds)
        except FaceDescriptorError:
            exclude(index, sample.source, "face_undetermined", wall)
            continue
        if face != seed_face:
            exclude(index, sample.source, "face_mismatch", wall)
            continue
        coords = np.asarray(final.coordinates, dtype=np.float64)
        candidates.append(
            _Candidate(
                index=index,
                source=sample.source,
                start_sha256=sample.start_sha256,
                g_hartree=result.record.thermo.gibbs_free_energy_hartree,
                degeneracy=result.record.degeneracy,
                rmsd_to_seed=rmsd(seed_xyz, coords),
                face=face,
                validation_passed=result.record.validation.passed_bool,
                wall_time=wall,
                coords=coords,
            )
        )
    _add(metrics[PRE_RELAX_KIND], pre_relax.metrics)

    # R2: merge on shape and face, lowest G first; record every merge, flag a large |dG|.
    kept: list[_Candidate] = []
    merges: list[TSEnsembleMerge] = []
    flagged: list[TSEnsembleMerge] = []
    for candidate in sorted(candidates, key=lambda c: (c.g_hartree, c.index)):
        target = None
        for member in kept:
            distance = rmsd(member.coords, candidate.coords)
            if distance < options.rmsd_dedup_angstrom and member.face == candidate.face:
                target = (member, distance)
                break
        if target is None:
            kept.append(candidate)
            continue
        member, distance = target
        merge = TSEnsembleMerge(
            kept_index=member.index,
            merged_index=candidate.index,
            dG_kcal_mol=(candidate.g_hartree - member.g_hartree) * HARTREE_KCAL_MOL,
            rmsd_angstrom=distance,
        )
        merges.append(merge)
        if abs(merge.dG_kcal_mol) > options.flag_dG_kcal_mol:
            flagged.append(merge)

    # R17: the energy window; members above it are recorded, not summed.
    lowest = min(c.g_hartree for c in kept)
    summed: list[_Candidate] = []
    for candidate in sorted(kept, key=lambda c: c.index):
        if (candidate.g_hartree - lowest) * HARTREE_KCAL_MOL > options.energy_window_kcal_mol:
            exclude(candidate.index, candidate.source, "outside_window", candidate.wall_time)
        else:
            summed.append(candidate)

    terms = [c.degeneracy * math.exp(-(c.g_hartree - lowest) / rt) for c in summed]
    total = math.fsum(terms)
    members = [
        TSEnsembleMember(
            index=c.index,
            source=c.source,
            start_sha256=c.start_sha256,
            G_hartree=c.g_hartree,
            degeneracy=c.degeneracy,
            rmsd_to_seed_angstrom=c.rmsd_to_seed,
            face=list(c.face),
            validation_passed_bool=c.validation_passed,
            weight=term / total,
            pre_relax_wall_time_s=c.wall_time,
        )
        for c, term in zip(summed, terms, strict=True)
    ]
    ensemble = TSEnsemble(
        pathway=pathway,
        temperature_k=temperature_k,
        reactant_key=tuple((s, c) for s, c in reactant_key),
        recipe_identity=engine_identity,
        members=members,
        excluded=sorted(excluded, key=lambda e: e.index),
        merges=merges,
        flagged_merges=flagged,
        options=options,
        G_pathway_hartree=lowest - rt * math.log(total),
    )
    return TSEnsembleRun(
        ensemble,
        metrics,
        seed_result,
        max_pre_relax_wall_time_s=max(wall_times) if wall_times else None,
    )


def run_ts_ensemble(
    seed: TSSpec,
    recipe: TSRecipe,
    store: ArtifactStore,
    *,
    optimizer: Optimizer,
    core_indices: Sequence[int],
    pathway: str,
    reactant_key: Sequence[tuple[str, int]],
    options: TSEnsembleOptions,
    member_gates: MemberGates,
) -> TSEnsemble:
    """Build one pathway's TS ensemble from a seed TS.

    The seed runs first (``run_transition_state``); if its search fails or a gate fails, nothing is
    sampled and ``failed_reason`` is ``seed:<reason>``. Otherwise the first ``max_research`` samples
    of ``sample_ts_conformers`` are each pre-relaxed with ``core_indices`` frozen (cached as
    ``constrained_preopt``; ``optimizer`` is injected), re-searched, gated, and checked against the
    seed's perceived bonds and face. A member that fails is excluded with its reason (R19), never
    raised. Valid members (the seed included) merge into the lowest-G member within
    ``rmsd_dedup_angstrom`` that has the same face (every merge recorded, flagged above
    ``flag_dG_kcal_mol``), members above ``energy_window_kcal_mol`` are ``outside_window``, and the
    rest are Boltzmann-weighted with degeneracy; ``G_pathway_hartree`` is the log-sum-exp.

    Args:
        seed: The verified TS spec (its start geometry carries the active core).
        recipe: The TS recipe, shared by the seed and every member.
        store: The artifact store.
        optimizer: The core-frozen minimizer for the pre-relaxation.
        core_indices: Atoms that never move.
        pathway: The pathway label.
        reactant_key: Sorted ``(SMILES, count)`` pairs of the reactants.
        options: The keyed ensemble options.
        member_gates: The recipe's member gates, ``{check name: passed}`` per result.

    Returns:
        The ensemble.

    Raises:
        eta_rxncat.optimize.OptimizerInputError: Bad optimizer options or forming bonds.
        eta_rxncat.thermo.TSValidationInputError: A validator input that cannot be judged.
        eta_rxncat.engines.EngineUnavailableError: A host problem; never cached.
        eta_rxncat.engines.EngineInputError: A bad engine input; never cached.
        eta_rxncat.mapping.MappingError: An empty, duplicated or out-of-range core.
        eta_rxncat.conformers.ConformerInputError: A fragment without an anchor, or the
            automorphism cap reached.
    """
    return run_ts_ensemble_detailed(
        seed,
        recipe,
        store,
        optimizer=optimizer,
        core_indices=core_indices,
        pathway=pathway,
        reactant_key=reactant_key,
        options=options,
        member_gates=member_gates,
    ).ensemble


__all__ = [
    "PRE_RELAX_OPTIONS",
    "TSEnsembleRun",
    "run_ts_ensemble",
    "run_ts_ensemble_detailed",
]
