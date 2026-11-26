"""The species runner, reactions and reports (v0.3.0); the TS runner and barrier (v0.5.0).

The v0.8.0 DAG comes later.

TJ Q4 "C": the incremental-solvation test runs on this small runner.

Exports load on first use (PEP 562, mission R26, slice 04), so
``eta_rxncat.orchestrator.selectivity`` imports without RDKit, torch, PySCF or geomeTRIC (G8).
``__all__`` and every ``from eta_rxncat.orchestrator import X`` are unchanged.
"""

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eta_rxncat.orchestrator.barrier import BarrierEnergies, BarrierSpec, activation_free_energy
    from eta_rxncat.orchestrator.counting import CountingEngine
    from eta_rxncat.orchestrator.reaction import (
        ReactionEnergies,
        ReactionSpec,
        reaction_free_energy,
        standard_state_shift_kcal_mol,
    )
    from eta_rxncat.orchestrator.report import ensemble_to_payload, report_text, write_report
    from eta_rxncat.orchestrator.selectivity import (
        DownstreamNode,
        NodeOutcome,
        PathwayInputs,
        SelectivityInputError,
        SelectivityRun,
        evaluate_pathway_pruning,
        run_selectivity,
        score_selectivity,
    )
    from eta_rxncat.orchestrator.species import (
        ENGINE_CLASSES,
        ConstrainedPoint,
        Recipe,
        RunMetrics,
        SinglePoint,
        SpeciesResult,
        SpeciesSpec,
        StageMetrics,
        build_engine,
        run_constrained_point,
        run_species,
    )
    from eta_rxncat.orchestrator.ts import TSRecipe, TSRunResult, TSSpec, run_transition_state
    from eta_rxncat.orchestrator.ts_ensemble import (
        TSEnsembleRun,
        run_ts_ensemble,
        run_ts_ensemble_detailed,
    )
    from eta_rxncat.orchestrator.ts_fallback import (
        enumerated_pathway_inputs,
        run_ts_with_fallback,
    )

_LAZY: dict[str, str] = {
    "DownstreamNode": "selectivity",
    "NodeOutcome": "selectivity",
    "PathwayInputs": "selectivity",
    "SelectivityRun": "selectivity",
    "evaluate_pathway_pruning": "selectivity",
    "run_selectivity": "selectivity",
    "BarrierEnergies": "barrier",
    "BarrierSpec": "barrier",
    "ConstrainedPoint": "species",
    "CountingEngine": "counting",
    "ENGINE_CLASSES": "species",
    "ReactionEnergies": "reaction",
    "ReactionSpec": "reaction",
    "Recipe": "species",
    "RunMetrics": "species",
    "SelectivityInputError": "selectivity",
    "SinglePoint": "species",
    "SpeciesResult": "species",
    "SpeciesSpec": "species",
    "StageMetrics": "species",
    "TSEnsembleRun": "ts_ensemble",
    "TSRecipe": "ts",
    "TSRunResult": "ts",
    "TSSpec": "ts",
    "activation_free_energy": "barrier",
    "build_engine": "species",
    "ensemble_to_payload": "report",
    "enumerated_pathway_inputs": "ts_fallback",
    "reaction_free_energy": "reaction",
    "report_text": "report",
    "run_constrained_point": "species",
    "run_species": "species",
    "run_transition_state": "ts",
    "run_ts_ensemble": "ts_ensemble",
    "run_ts_ensemble_detailed": "ts_ensemble",
    "run_ts_with_fallback": "ts_fallback",
    "score_selectivity": "selectivity",
    "standard_state_shift_kcal_mol": "reaction",
    "write_report": "report",
}
"""Public name -> the submodule that defines it."""


def __getattr__(name: str) -> Any:
    """Load a lazily exported name from its submodule and cache it on the package."""
    submodule = _LAZY.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{submodule}"), name)
    globals()[name] = value
    return value


__all__ = [
    "DownstreamNode",
    "NodeOutcome",
    "PathwayInputs",
    "SelectivityRun",
    "evaluate_pathway_pruning",
    "run_selectivity",
    "ENGINE_CLASSES",
    "BarrierEnergies",
    "BarrierSpec",
    "ConstrainedPoint",
    "CountingEngine",
    "ReactionEnergies",
    "ReactionSpec",
    "Recipe",
    "RunMetrics",
    "SelectivityInputError",
    "SinglePoint",
    "SpeciesResult",
    "SpeciesSpec",
    "StageMetrics",
    "TSEnsembleRun",
    "TSRecipe",
    "TSRunResult",
    "TSSpec",
    "activation_free_energy",
    "build_engine",
    "ensemble_to_payload",
    "enumerated_pathway_inputs",
    "reaction_free_energy",
    "report_text",
    "run_constrained_point",
    "run_species",
    "run_transition_state",
    "run_ts_ensemble",
    "run_ts_ensemble_detailed",
    "run_ts_with_fallback",
    "score_selectivity",
    "standard_state_shift_kcal_mol",
    "write_report",
]
