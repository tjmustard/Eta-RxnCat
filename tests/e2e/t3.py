"""Tier 3 TS E2E helpers (v0.5.0 slice 08 on): recipes, one case run, gates, reported block.

A case is a TS fixture (``fixtures.load_ts_fixture``) run on one recipe: the reactant species
through v0.3.0's ``run_species``, the TS through ``run_transition_state``, the barrier through
``activation_free_energy``, then the same again in the same store (G6). Gates follow TJ's Q-TJ3:
GFN2 gates convergence and the mode count only; UMA also gates the active core, the identity and
the ΔG‡ window. Everything else is reported. Candidates go to ``tests/candidate_outputs/v0.5.0/``
(``ETA_RXNCAT_CANDIDATE_DIR`` overrides it) and nothing reads them back.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from e2e_env import REPO
from fixtures import TSFixture

from eta_rxncat.core import MolecularState
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import core_rmsd_angstrom
from eta_rxncat.optimize import PRFOOptimizer
from eta_rxncat.orchestrator import (
    BarrierEnergies,
    Recipe,
    SpeciesResult,
    TSRecipe,
    TSRunResult,
    TSSpec,
    activation_free_energy,
    run_species,
    run_transition_state,
)
from eta_rxncat.store import ArtifactStore

CANDIDATES_V050 = REPO / "tests" / "candidate_outputs" / "v0.5.0"
ENERGY_SOURCE_BOUND_KCAL_MOL = 0.01
"""Lead's slice 08 rule: the TS's frequency-run and gradient-run energies at one geometry may
move ΔG‡ by at most this much, else stop and report (slice 06's energy-source note)."""
REACTANT_STAGES = ("conformer_search", "geometry_opt", "frequency")


def candidate_dir() -> Path:
    """``ETA_RXNCAT_CANDIDATE_DIR`` if set, else ``tests/candidate_outputs/v0.5.0`` (write only)."""
    override = os.environ.get("ETA_RXNCAT_CANDIDATE_DIR")
    path = Path(override) if override else CANDIDATES_V050
    path.mkdir(parents=True, exist_ok=True)
    return path


def ts_recipe(recipe: Recipe) -> TSRecipe:
    """The TS recipe of a species recipe: same engine stage and runtime, P-RFO defaults."""
    return TSRecipe(
        name=recipe.name,
        engine_stage=recipe.engine_stage,
        ts_optimizer=PRFOOptimizer(),
        thermo_config=recipe.thermo_config,
        analysis=recipe.analysis,
        engine_runtime=recipe.engine_runtime,
    )


def ts_spec(fixture: TSFixture, recipe_name: str) -> TSSpec:
    """The TS request of a fixture for one recipe (a mapped start reads that recipe's M1)."""
    return TSSpec(
        ts_id=fixture.ts_id,
        start=fixture.start_state(recipe_name),
        forming_bonds=fixture.forming_bonds,
        reference=fixture.reference,
        reference_map=fixture.start_to_reference_map,
    )


@dataclass(frozen=True)
class CaseRun:
    """One pass over a case: reactant results, the TS run, and the barrier (or its error)."""

    reactants: dict[str, SpeciesResult]
    ts: TSRunResult
    barrier: BarrierEnergies | None
    barrier_error: str | None


def run_case(fixture: TSFixture, recipe: Recipe, recipe_name: str, store_path: Path) -> CaseRun:
    """Run the reactants, the TS and the barrier once in the store at ``store_path``."""
    with ArtifactStore(store_path) as store:
        reactants = {s.species_id: run_species(s, recipe, store) for s in fixture.species}
        ts = run_transition_state(ts_spec(fixture, recipe_name), ts_recipe(recipe), store)
    barrier = error = None
    if ts.failed_reason is None and ts.record is not None:
        try:
            barrier = activation_free_energy(
                fixture.barrier,
                {k: v.ensemble for k, v in reactants.items()},
                ts.record,
                recipe.thermo_config,
            )
        except ValueError as exc:
            error = str(exc)
    return CaseRun(reactants, ts, barrier, error)


def all_hit(result: SpeciesResult, kind: str) -> bool:
    """Every row of ``kind`` was served from the store (R27)."""
    m = result.metrics.stages[kind]
    return m.rows_created == 0 and m.cache_hits == len(result.keys[kind]) > 0


def ts_all_hit(ts: TSRunResult) -> bool:
    """Both TS stages were served from the store with no row created."""
    return all(
        ts.metrics[k].cache_hits == 1 and ts.metrics[k].rows_created == 0
        for k in ("ts_opt", "frequency")
    )


def comparable_ts(ts: TSRunResult) -> dict[str, Any]:
    """The TS payload without metrics and without the search history (N11)."""
    payload = ts.as_payload()
    payload.pop("metrics")
    if payload["search"] is not None:
        payload["search"] = {k: v for k, v in payload["search"].items() if k != "history"}
    return payload


def energy_source(ts: TSRunResult) -> dict[str, Any] | None:
    """The TS's frequency-run E vs its optimizer (gradient-run) E at the same final geometry."""
    if ts.record is None:
        return None
    frequency_e = ts.record.thermo.electronic_energy_hartree
    gradient_e = ts.record.search.final_energy_hartree
    delta = frequency_e - gradient_e
    return {
        "frequency_run_energy_hartree": frequency_e,
        "gradient_run_energy_hartree": gradient_e,
        "delta_hartree": delta,
        "delta_kcal_mol": delta * HARTREE_KCAL_MOL,
        "bound_kcal_mol": ENERGY_SOURCE_BOUND_KCAL_MOL,
        "within_bound_bool": abs(delta * HARTREE_KCAL_MOL) <= ENERGY_SOURCE_BOUND_KCAL_MOL,
    }


def rmsds_to_reference(
    state: MolecularState, fixture: TSFixture, forming_core: list[int]
) -> dict[str, float]:
    """Full, active and forming-core RMSDs (Angstrom, Horn) of ``state`` to Liu's TS, mapped."""
    mapping = list(fixture.start_to_reference_map)
    n = len(mapping)
    active = list(fixture.active_atom_indices)
    ref = fixture.reference.coordinates

    def rmsd(indices: list[int]) -> float:
        return core_rmsd_angstrom(ref, state.coordinates, [mapping[k] for k in indices], indices)

    return {
        "full_rmsd_angstrom": rmsd(list(range(n))),
        "active_rmsd_angstrom": rmsd(active),
        "forming_core_rmsd_angstrom": rmsd(forming_core),
    }


def gates(
    recipe_name: str,
    first: CaseRun,
    second: CaseRun,
    window: tuple[float, float],
) -> dict[str, dict[str, Any]]:
    """The per-recipe tier gates (Q-TJ3): status ``pass``, ``fail`` or ``reported``."""
    ts = first.ts
    validation = ts.validation
    converged = ts.search is not None  # a failed search or SCF leaves no search result
    uma = recipe_name == "uma"

    def status(ok: bool, gated: bool = True) -> dict[str, Any]:
        return {"status": ("pass" if ok else "fail") if gated else "reported"}

    dg = None if first.barrier is None else first.barrier.dG_dagger_1M_kcal_mol
    source = energy_source(ts)
    inside = dg is not None and window[0] <= dg <= window[1]
    return {
        "search_converged": status(converged),
        "mode_count": status(validation is not None and validation.mode_count_passed_bool),
        "active_core": status(validation is not None and validation.active_core_passed_bool, uma),
        "identity": status(validation is not None and validation.identity_passed_bool, uma),
        "window_dG_dagger_1M": {**status(inside, uma), "value_kcal_mol": dg},
        "barrier_conservation": status(first.barrier is not None and first.barrier_error is None),
        "energy_source_consistent": status(source is not None and source["within_bound_bool"]),
        "second_run_ts_all_hits": status(ts_all_hit(second.ts)),
        "second_run_reactants_all_hits": status(
            all(all_hit(r, k) for r in second.reactants.values() for k in REACTANT_STAGES)
        ),
        "second_run_equal_payload": status(
            comparable_ts(first.ts) == comparable_ts(second.ts) and first.barrier == second.barrier
        ),
    }


def reported_block(
    recipe_name: str,
    fixture: TSFixture,
    first: CaseRun,
    forming_core: list[int],
) -> dict[str, Any]:
    """Everything reported and never gated for one case and recipe."""
    ts = first.ts
    search = ts.search
    validation = ts.validation
    literature = fixture.literature
    block: dict[str, Any] = {
        "connectivity_equal_bool": ts.connectivity_equal_bool,
        "failed_reason": ts.failed_reason,
        "energy_source": energy_source(ts),
        "literature_dG_dagger_1M_kcal_mol": literature["dG_dagger_1M_kcal_mol"],
        "literature_dG_dagger_1atm_kcal_mol": literature["dG_dagger_1atm_kcal_mol"],
        "literature_source": literature["source"],
    }
    if search is not None:
        block["search_counts"] = {
            "n_steps": search.n_steps,
            "n_gradient_calls": search.n_gradient_calls,
            "n_hessian_calls": search.n_hessian_calls,
            "n_hessian_refreshes": search.n_hessian_refreshes,
            "n_rejected_steps": search.n_rejected_steps,
        }
        block["hessian_method"] = search.hessian_method
        block["rmsd_to_literature_ts"] = rmsds_to_reference(
            search.final_state, fixture, forming_core
        )
    if validation is not None:
        block["validation_numbers"] = {
            "imaginary_frequency_cm1": validation.imaginary_frequency_cm1,
            "active_core_ke_fraction": validation.active_core_ke_fraction,
            "forming_stretch_overlap": validation.forming_stretch_overlap,
            "forming_bonds_in_phase_bool": validation.forming_bonds_in_phase_bool,
            "forming_distances_angstrom": validation.forming_distances_angstrom,
        }
    if first.barrier is not None:
        block["dG_dagger_1atm_kcal_mol"] = first.barrier.dG_dagger_1atm_kcal_mol
        block["delta_dG_dagger_1M_vs_literature_kcal_mol"] = (
            first.barrier.dG_dagger_1M_kcal_mol - literature["dG_dagger_1M_kcal_mol"]
        )
    if first.barrier_error is not None:
        block["barrier_error"] = first.barrier_error
    block["gated_on"] = "convergence, mode count" if recipe_name == "xtb" else "all (UMA, Q-TJ3)"
    return block


def ts_payload(ts: TSRunResult) -> dict[str, Any]:
    """The TS part of a candidate; ``search_history`` sits apart and is never compared (N11)."""
    payload = ts.as_payload()
    history = None
    if payload["search"] is not None:
        history = payload["search"].pop("history")
    state = None if ts.search is None else ts.search.final_state.model_dump(mode="json")
    return {"state": state, **payload, "search_history": history}


def barrier_payload(barrier: BarrierEnergies | None) -> dict[str, Any] | None:
    """The barrier energies as JSON."""
    return None if barrier is None else barrier.model_dump(mode="json")


def cache_summary(second: CaseRun) -> dict[str, Any]:
    """Hits and rows of the second run, per reactant stage and TS stage."""
    return {
        "reactants": {
            k: {
                kind: {
                    "cache_hits": r.metrics.stages[kind].cache_hits,
                    "rows_created": r.metrics.stages[kind].rows_created,
                }
                for kind in REACTANT_STAGES
            }
            for k, r in sorted(second.reactants.items())
        },
        "ts": {
            kind: {
                "cache_hits": second.ts.metrics[kind].cache_hits,
                "rows_created": second.ts.metrics[kind].rows_created,
                "engine_calls": second.ts.metrics[kind].engine_calls,
            }
            for kind in ("ts_opt", "frequency")
        },
    }


def reactant_summary(results: Mapping[str, SpeciesResult]) -> dict[str, Any]:
    """Per reactant: kept records, dropped reasons, ensemble G and the lowest record's G."""
    out: dict[str, Any] = {}
    for species_id, result in sorted(results.items()):
        ensemble = result.ensemble
        out[species_id] = {
            "n_kept": len(ensemble.records),
            "dropped": [{"source_id": s, "reason": r} for s, r in result.dropped],
            "ensemble_gibbs_hartree": ensemble.ensemble_gibbs_hartree,
            "lowest_gibbs_hartree": ensemble.records[
                ensemble.lowest_index
            ].thermo.gibbs_free_energy_hartree,
        }
    return out
