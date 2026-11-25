"""Tier 4 E2E: the mapped endo/exo pair, TS1b_n vs grafted TS1b_x, and TJ's pruning (slice 10).

TJ Q3 "A" (gates), Q2 "A" (threshold 1.5 kcal/mol in the fixture, no library default) and Q-E4
(P1b_x is ``downstream_exo_minor``). The pair runs through the shipped selectivity runner, so G6
tests the pruning path as it will be used: above 1.5 the P1b_x node is ``pruned`` with no engine
work, else it is computed. Both outcomes pass (G6) and the branch is recorded with its margin.
A miss on a gate is a finding for TJ, never a widened gate. The candidate is committed for
Phase 3 (nothing reads it back).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from acceptance import write_fragment
from candidates import environment
from checks import assert_checks_pass, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import t4
from t3 import reactant_summary
from t4 import (
    cache_summary,
    candidate_dir,
    ensemble_payload,
    gates,
    grafted_exo_start,
    pruning_gate,
    pruning_payload,
    regression_endo_seed,
    reported_block,
    run_mapped_pair,
    seed_payload,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_t4_mapped(
    recipe_name: str, recipes: Callable[[str], Recipe], tmp_path: Path, commit_sha: str
) -> None:
    """Graft, ensembles, selectivity, pruning and gates; second run all hits; candidate written."""
    recipe = recipes(recipe_name)
    fixture = t4("t4_mapped_selectivity_pruned.yaml")
    exo_start, graft_summary = grafted_exo_start(fixture, recipe)
    starts = {"endo": fixture.pathway("endo").start_state(recipe_name), "exo": exo_start}
    store_path = tmp_path / "store.sqlite"
    first = run_mapped_pair(fixture, recipe, recipe_name, store_path, starts)
    second = run_mapped_pair(fixture, recipe, recipe_name, store_path, starts)
    regression = regression_endo_seed(
        seed_payload(first, "endo", fixture, case="ts1b_n"), recipe_name
    )
    tier = gates(recipe_name, fixture, first, second, regression)
    tier["pruning_g6"] = pruning_gate(fixture, first, second)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
        "fixture": fixture.name,
        "case": "t4_mapped",
        "recipe": recipe_name,
        "commit_sha": commit_sha,
        "environment": environment(identity, DEVICES[recipe_name]),
        "thermo_config": recipe.thermo_config.model_dump(mode="json"),
        "ensemble_options": first.runs["endo"].ensemble.options.model_dump(mode="json"),
        "exo_graft": graft_summary,
        "pathways": {k: ensemble_payload(r) for k, r in first.runs.items()},
        "score": None if first.score is None else first.score.model_dump(mode="json"),
        "pruning": pruning_payload(first),
        "barriers": {
            k: None if b is None else b.model_dump(mode="json") for k, b in first.barriers.items()
        },
        "ensemble_barriers": first.ensemble_barriers,
        "reactants": reactant_summary(first.reactants),
        "reported": reported_block(fixture, first),
        "second_run_cache": cache_summary(second),
        "checks": {"tier_gates": tier, "regression": regression},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / f"t4_mapped.{recipe_name}.json", payload)
    write_fragment("t4_mapped", recipe_name, payload)
    print(
        f"\nT4 mapped {recipe_name}: gates { {k: v['status'] for k, v in tier.items()} }; "
        f"ddG_dagger {tier['window_ddG_dagger']['value_kcal_mol']} window "
        f"({fixture.uma_window.low}, {fixture.uma_window.high}]; pruning {tier['pruning_g6']}; "
        f"reported {payload['reported']}"
    )
    assert_checks_pass(payload["checks"])
