"""Tier 4 E2E helpers (v0.6.0 slice 09 on): one endo/exo pair run, its gates and the candidate.

A pair is a Tier 4 fixture (``fixtures.load_t4_fixture``) run on one recipe: the reactants through
``run_species``, each pathway's seed TS and TS ensemble through ``run_ts_ensemble_detailed`` (the
core-frozen pre-relaxation optimizer is ``GeometricOptimizer()``, injected), the Boltzmann-summed
selectivity through ``score_selectivity``, then the same again in the same store (G7).

Gates follow TJ's Q3 "A" with the member gates of Q-TJ4 "A": both recipes gate that the seeds
converge and pass the member gates, that endo is the major pathway, that the summed ddG-dagger is
above 0.5 kcal/mol (strict), that no ensemble excluded a sample as ``engine_error`` or
``face_mismatch``, the endo seed's regression against TJ's promoted v0.5.0 fixture, and the second
run; UMA also gates the window [2.3, 6.3]. GFN2 reports its window and never gates a numeric one
(R21). A miss is a finding for TJ, never a widened gate. Candidates go to
``tests/candidate_outputs/v0.6.0/`` (``ETA_RXNCAT_CANDIDATE_DIR`` overrides it); nothing reads
them back.
"""

import json
import os
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from e2e_env import REPO
from fixtures import T4Fixture
from t3 import REACTANT_STAGES, all_hit, regression_ts, ts_payload, ts_recipe

from eta_rxncat.core import SelectivityResult, TSEnsemble, TSEnsembleOptions
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import core_rmsd_angstrom
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import (
    BarrierEnergies,
    BarrierSpec,
    Recipe,
    SpeciesResult,
    StageMetrics,
    TSEnsembleRun,
    TSRunResult,
    TSSpec,
    activation_free_energy,
    run_species,
    run_ts_ensemble_detailed,
    score_selectivity,
)
from eta_rxncat.store import ArtifactStore

CANDIDATES_V060 = REPO / "tests" / "candidate_outputs" / "v0.6.0"
PROMOTED_V050 = REPO / "tests" / "fixtures" / "v0.5.0"
STAGE_KINDS = ("constrained_preopt", "ts_opt", "frequency")
MIN_DDG_KCAL_MOL = 0.5
"""Both engines: the Boltzmann-summed ddG-dagger is strictly above this (TJ Q3 A, HF-7, R21)."""
FORMING_CORE = [1, 2, 3, 5]
REGRESSION_G_BOUND_KCAL_MOL = {"xtb": 0.01, "uma": 0.75}
"""R6: the endo seed's TS G may move by at most this much from the promoted v0.5.0 fixture."""

MemberGates = Callable[[TSRunResult], dict[str, bool]]


def candidate_dir() -> Path:
    """``ETA_RXNCAT_CANDIDATE_DIR`` if set, else ``tests/candidate_outputs/v0.6.0`` (write only)."""
    override = os.environ.get("ETA_RXNCAT_CANDIDATE_DIR")
    path = Path(override) if override else CANDIDATES_V060
    path.mkdir(parents=True, exist_ok=True)
    return path


def member_gates(recipe_name: str) -> MemberGates:
    """The recipe's member gates (Q-TJ4 A): GFN2 = mode count + active core + identity core.

    The identity core is the forming-stretch overlap at the validator's threshold and the forming
    bonds in phase. UMA = mode count + active core + the full identity (which also holds the
    forming-distance window).
    """

    def gates(result: TSRunResult) -> dict[str, bool]:
        validation = result.validation
        if validation is None:
            return {"validation": False}
        checks = {
            "mode_count": validation.mode_count_passed_bool,
            "active_core": validation.active_core_passed_bool,
        }
        if recipe_name == "uma":
            checks["identity"] = validation.identity_passed_bool
        else:
            overlap = validation.forming_stretch_overlap
            threshold = validation.options.min_forming_stretch_overlap
            checks["forming_overlap"] = overlap is not None and overlap >= threshold
            checks["forming_in_phase"] = validation.forming_bonds_in_phase_bool is True
        return checks

    return gates


def reactant_key(fixture: T4Fixture) -> tuple[tuple[str, int], ...]:
    """The sorted ``(SMILES, count)`` pairs of the fixture's reactants (one of each)."""
    return tuple(sorted((s.smiles, 1) for s in fixture.species))


@dataclass(frozen=True)
class PairRun:
    """One pass over a pair: reactants, each pathway's ensemble run, the score and the barriers."""

    reactants: dict[str, SpeciesResult]
    runs: dict[str, TSEnsembleRun]
    score: SelectivityResult | None
    barriers: dict[str, BarrierEnergies | None]
    barrier_errors: dict[str, str]
    ensemble_barriers: dict[str, dict[str, float] | None] = field(default_factory=dict)

    @property
    def ensembles(self) -> dict[str, TSEnsemble]:
        """Each pathway's ensemble."""
        return {k: r.ensemble for k, r in self.runs.items()}


def run_pair(
    fixture: T4Fixture,
    recipe: Recipe,
    recipe_name: str,
    store_path: Path,
    options: TSEnsembleOptions | None = None,
) -> PairRun:
    """Run reactants, both ensembles, the score and the seed barriers once in ``store_path``."""
    options = options or TSEnsembleOptions()
    ts = ts_recipe(recipe)
    runs: dict[str, TSEnsembleRun] = {}
    with ArtifactStore(store_path) as store:
        reactants = {s.species_id: run_species(s, recipe, store) for s in fixture.species}
        for p in fixture.pathways:
            seed = TSSpec(
                ts_id=p.ts_id,
                start=p.start_state(recipe_name),
                forming_bonds=p.forming_bonds,
                reference=p.reference,
                reference_map=p.start_to_reference_map,
            )
            runs[p.pathway] = run_ts_ensemble_detailed(
                seed,
                ts,
                store,
                optimizer=GeometricOptimizer(),
                core_indices=p.active_atom_indices,
                pathway=p.pathway,
                reactant_key=reactant_key(fixture),
                options=options,
                member_gates=member_gates(recipe_name),
            )
    valid = {k: r.ensemble for k, r in runs.items() if r.ensemble.failed_reason is None}
    score = (
        score_selectivity(valid, kind="de", temperature_k=fixture.temperature_k)
        if len(valid) == len(fixture.pathways)
        else None
    )
    smiles = {s.species_id: s.smiles for s in fixture.species}
    barriers: dict[str, BarrierEnergies | None] = {}
    errors: dict[str, str] = {}
    for p in fixture.pathways:
        record = runs[p.pathway].seed_result.record
        barriers[p.pathway] = None
        if record is None:
            continue
        spec = BarrierSpec(
            reactants=tuple((s.species_id, 1) for s in fixture.species),
            ts_id=p.ts_id,
            smiles=smiles,
        )
        try:
            barriers[p.pathway] = activation_free_energy(
                spec,
                {k: v.ensemble for k, v in reactants.items()},
                record,
                recipe.thermo_config,
            )
        except ValueError as exc:
            errors[p.pathway] = str(exc)
    return PairRun(reactants, runs, score, barriers, errors, ensemble_barriers(runs, barriers))


def ensemble_barriers(
    runs: Mapping[str, TSEnsembleRun], barriers: Mapping[str, BarrierEnergies | None]
) -> dict[str, dict[str, float] | None]:
    """Each pathway's barriers from its ensemble's G (the Boltzmann-summed TS free energy).

    The seed barrier (``activation_free_energy`` on the seed's record, which checks atom and
    charge conservation) moved by ``G_pathway - G_seed``: the reactants cancel, so the difference
    between two pathways is the ddG-dagger of the score. The ensemble's lowest member need not be
    the seed (it is whichever merged copy has the lowest G), so the seed barrier alone is not that.
    """
    out: dict[str, dict[str, float] | None] = {}
    for label, run in runs.items():
        barrier, record = barriers[label], run.seed_result.record
        g_path = run.ensemble.G_pathway_hartree
        if barrier is None or record is None or g_path is None:
            out[label] = None
            continue
        shift = (g_path - record.thermo.gibbs_free_energy_hartree) * HARTREE_KCAL_MOL
        out[label] = {
            "dG_dagger_1M_kcal_mol": barrier.dG_dagger_1M_kcal_mol + shift,
            "dG_dagger_1atm_kcal_mol": barrier.dG_dagger_1atm_kcal_mol + shift,
            "seed_to_ensemble_shift_kcal_mol": shift,
        }
    return out


# --- Gates -------------------------------------------------------------------------------------


def exclusions_by_reason(ensemble: TSEnsemble) -> dict[str, int]:
    """Count an ensemble's exclusions by reason (the parametrised ones by their stem)."""
    return dict(sorted(Counter(e.reason for e in ensemble.excluded).items()))


def _status(ok: bool, gated: bool = True) -> dict[str, Any]:
    return {"status": ("pass" if ok else "fail") if gated else "reported"}


def stage_totals(run: TSEnsembleRun) -> dict[str, dict[str, float]]:
    """Per stage kind: wall time, engine calls, cache hits and rows created, as JSON numbers."""
    return {
        kind: {
            "wall_time_s": run.metrics[kind].wall_time_s,
            "engine_calls": run.metrics[kind].engine_calls,
            "cache_hits": run.metrics[kind].cache_hits,
            "rows_created": run.metrics[kind].rows_created,
        }
        for kind in STAGE_KINDS
    }


def second_run_all_hits(second: PairRun) -> bool:
    """G7: every ensemble stage hit and wrote nothing, and made no engine call."""
    for run in second.runs.values():
        for kind in STAGE_KINDS:
            m: StageMetrics = run.metrics[kind]
            if m.rows_created != 0 or m.engine_calls != 0:
                return False
        if run.metrics["ts_opt"].cache_hits == 0 or run.metrics["frequency"].cache_hits == 0:
            return False
    return True


def gates(
    recipe_name: str,
    fixture: T4Fixture,
    first: PairRun,
    second: PairRun,
    regression: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """The per-recipe gates, each ``pass``, ``fail`` or ``reported`` (``regression`` as built)."""
    uma = recipe_name == "uma"
    score = first.score
    ddg = None if score is None else score.ddG_dagger_kcal_mol
    reasons = {k: exclusions_by_reason(e) for k, e in first.ensembles.items()}
    single = all(len(e.members) == 1 for e in first.ensembles.values())
    pathway_ddg = None
    per_pathway = [first.ensemble_barriers.get(p.pathway) for p in fixture.pathways]
    if len(per_pathway) == 2 and all(b is not None for b in per_pathway):
        endo, exo = per_pathway
        assert endo is not None and exo is not None
        pathway_ddg = abs(exo["dG_dagger_1M_kcal_mol"] - endo["dG_dagger_1M_kcal_mol"])
    return {
        "seeds_converge_and_pass_member_gates": _status(
            all(e.failed_reason is None for e in first.ensembles.values())
            and len(first.ensembles) == len(fixture.pathways)
        ),
        "endo_is_major": {
            **_status(score is not None and score.major_pathway == "endo"),
            "major_pathway": None if score is None else score.major_pathway,
        },
        "ddG_dagger_above_0_5": {
            **_status(ddg is not None and ddg > MIN_DDG_KCAL_MOL),
            "value_kcal_mol": ddg,
        },
        "window_ddG_dagger": {
            **_status(ddg is not None and fixture.uma_window.contains(ddg), uma),
            "value_kcal_mol": ddg,
            "window": {
                "low": fixture.uma_window.low,
                "high": fixture.uma_window.high,
                "low_inclusive": fixture.uma_window.low_inclusive,
                "high_inclusive": fixture.uma_window.high_inclusive,
            },
        },
        "no_engine_error_exclusions": _status(
            all("engine_error" not in r for r in reasons.values())
        ),
        "no_face_mismatch_exclusions": _status(
            all("face_mismatch" not in r for r in reasons.values())
        ),
        "regression_endo_seed": {"status": regression["status"]},
        "per_pathway_dG_difference_equals_ddG": {
            **_status(
                pathway_ddg is not None
                and ddg is not None
                and abs(pathway_ddg - ddg) <= 1e-9
                and single,
                single,
            ),
            "per_pathway_difference_kcal_mol": pathway_ddg,
            "ddG_dagger_kcal_mol": ddg,
        },
        "second_run_ensembles_all_hits": _status(second_run_all_hits(second)),
        "second_run_reactants_all_hits": _status(
            all(all_hit(r, k) for r in second.reactants.values() for k in REACTANT_STAGES)
        ),
        "second_run_equal_ensembles_and_score": _status(
            first.ensembles == second.ensembles and first.score == second.score
        ),
    }


# --- The endo seed's regression against TJ's promoted v0.5.0 fixture (mission R6) -------------


def seed_payload(run: PairRun, pathway: str, fixture: T4Fixture) -> dict[str, Any]:
    """The seed of one pathway in the v0.5.0 candidate shape (``ts`` and ``barrier`` blocks)."""
    barrier = run.barriers[pathway]
    return {
        "case": "ts1a_n",
        "ts": ts_payload(run.runs[pathway].seed_result),
        "barrier": None if barrier is None else barrier.model_dump(mode="json"),
        "fixture": fixture.name,
    }


def regression_endo_seed(
    payload: Mapping[str, Any], recipe_name: str, promoted_dir: Path = PROMOTED_V050
) -> dict[str, Any]:
    """Compare the endo seed with ``t3_ts1a_n.<recipe>.json`` (TJ's v0.5.0 Phase 3 bounds, R6).

    ``regression_ts`` checks E, the heavy-atom RMSD and ΔG‡(1 M); this adds the TS free energy,
    bounded like ΔG‡. ``pending_promotion`` when the fixture is absent.
    """
    result = regression_ts(payload, recipe_name, promoted_dir=promoted_dir)
    path = promoted_dir / f"t3_{payload['case']}.{recipe_name}.json"
    if result["status"] == "pending_promotion" or not path.is_file():
        return result
    old = json.loads(path.read_text(encoding="utf-8"))["ts"]["thermo"]["gibbs_free_energy_hartree"]
    new = payload["ts"]["thermo"]["gibbs_free_energy_hartree"]
    delta = abs(float(new) - float(old)) * HARTREE_KCAL_MOL
    bound = REGRESSION_G_BOUND_KCAL_MOL[recipe_name]
    result = dict(result)
    result["abs_delta_ts_gibbs_kcal_mol"] = delta
    result["bounds"] = {**result["bounds"], "abs_delta_ts_gibbs_kcal_mol": bound}
    if delta > bound:
        result["mismatches"] = [*result["mismatches"], "abs_delta_ts_gibbs_kcal_mol"]
        result["status"] = "fail"
    return result


# --- Reported block and candidate ---------------------------------------------------------------


def seed_core_rmsd_to_liu(run: TSEnsembleRun, fixture: T4Fixture, pathway: str) -> float | None:
    """Forming-core RMSD (Angstrom, Horn) of the seed's TS to Liu's, identity map."""
    search = run.seed_result.search
    if search is None:
        return None
    p = fixture.pathway(pathway)
    mapping = list(p.start_to_reference_map)
    return core_rmsd_angstrom(
        p.reference.coordinates,
        search.final_state.coordinates,
        [mapping[k] for k in FORMING_CORE],
        FORMING_CORE,
    )


def reported_block(fixture: T4Fixture, first: PairRun) -> dict[str, Any]:
    """Everything reported and never gated for one pair and recipe."""
    score = first.score
    block: dict[str, Any] = {
        "liu_header_ddG_dagger_kcal_mol": fixture.liu_header_ddG_dagger_kcal_mol,
        "tj_reference_ddG_dagger_kcal_mol": fixture.reference_ddG_dagger_kcal_mol,
        "selectivity_percent": None if score is None else score.selectivity_percent,
        "ratio": None if score is None else score.ratio,
        "kind": fixture.kind,
        "temperature_k": fixture.temperature_k,
        "pathways": {},
        "gfn2_gate_definition": fixture.gfn2_gate,
    }
    for p in fixture.pathways:
        run = first.runs[p.pathway]
        ensemble = run.ensemble
        barrier = first.barriers[p.pathway]
        summed = first.ensemble_barriers.get(p.pathway)
        block["pathways"][p.pathway] = {
            "ts_id": p.ts_id,
            "failed_reason": ensemble.failed_reason,
            "members": [
                {
                    "index": m.index,
                    "source": m.source,
                    "weight": m.weight,
                    "G_hartree": m.G_hartree,
                    "rmsd_to_seed_angstrom": m.rmsd_to_seed_angstrom,
                    "pre_relax_wall_time_s": m.pre_relax_wall_time_s,
                }
                for m in ensemble.members
            ],
            "exclusions_by_reason": exclusions_by_reason(ensemble),
            "n_merges": len(ensemble.merges),
            "n_flagged_merges": len(ensemble.flagged_merges),
            "G_pathway_hartree": ensemble.G_pathway_hartree,
            "seed_forming_core_rmsd_to_liu_angstrom": seed_core_rmsd_to_liu(
                run, fixture, p.pathway
            ),
            "seed_dG_dagger_1M_kcal_mol": None
            if barrier is None
            else barrier.dG_dagger_1M_kcal_mol,
            "seed_dG_dagger_1atm_kcal_mol": (
                None if barrier is None else barrier.dG_dagger_1atm_kcal_mol
            ),
            "ensemble_dG_dagger": summed,
            "stage_metrics": stage_totals(run),
            "max_pre_relax_wall_time_s": run.max_pre_relax_wall_time_s,
        }
    if first.barrier_errors:
        block["barrier_errors"] = dict(first.barrier_errors)
    return block


def ensemble_payload(run: TSEnsembleRun) -> dict[str, Any]:
    """An ensemble (members, weights, exclusions, merges, options) and the seed's own TS."""
    return {
        "ensemble": run.ensemble.model_dump(mode="json"),
        "seed_ts": ts_payload(run.seed_result),
    }


def cache_summary(second: PairRun) -> dict[str, Any]:
    """Hits, rows and engine calls of the second run, per pathway and stage."""
    return {p: stage_totals(r) for p, r in sorted(second.runs.items())} | {
        "reactants": {
            k: {
                kind: {
                    "cache_hits": r.metrics.stages[kind].cache_hits,
                    "rows_created": r.metrics.stages[kind].rows_created,
                }
                for kind in REACTANT_STAGES
            }
            for k, r in sorted(second.reactants.items())
        }
    }
