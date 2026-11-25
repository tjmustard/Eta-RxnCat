"""Tier 4 E2E: the unmapped endo/exo pair, TS1a_n vs TS1a_x, with TS ensembles (slice 09).

TJ Q3 "A" (GFN2 gated per pair as measured, UMA window [2.3, 6.3], both > 0.5 strict), Q1 "B"
(ensembles) and Q-TJ4 "A" (member gates). A miss is a finding for TJ, never a widened gate. The
candidate is committed for TJ's Phase 3 review (nothing reads it back).
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
    regression_endo_seed,
    reported_block,
    run_pair,
    seed_payload,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_t4_unmapped(
    recipe_name: str, recipes: Callable[[str], Recipe], tmp_path: Path, commit_sha: str
) -> None:
    """Ensembles, selectivity and gates; second run all hits; candidate written."""
    recipe = recipes(recipe_name)
    fixture = t4("t4_endo_exo_unmapped.yaml")
    store_path = tmp_path / "store.sqlite"
    first = run_pair(fixture, recipe, recipe_name, store_path)
    second = run_pair(fixture, recipe, recipe_name, store_path)
    regression = regression_endo_seed(seed_payload(first, "endo", fixture), recipe_name)
    tier = gates(recipe_name, fixture, first, second, regression)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
        "fixture": fixture.name,
        "case": "t4_unmapped",
        "recipe": recipe_name,
        "commit_sha": commit_sha,
        "environment": environment(identity, DEVICES[recipe_name]),
        "thermo_config": recipe.thermo_config.model_dump(mode="json"),
        "ensemble_options": first.runs["endo"].ensemble.options.model_dump(mode="json"),
        "pathways": {k: ensemble_payload(r) for k, r in first.runs.items()},
        "score": None if first.score is None else first.score.model_dump(mode="json"),
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
    write(candidate_dir() / f"t4_unmapped.{recipe_name}.json", payload)
    write_fragment("t4_unmapped", recipe_name, payload)
    print(
        f"\nT4 unmapped {recipe_name}: gates { {k: v['status'] for k, v in tier.items()} }; "
        f"ddG_dagger {tier['window_ddG_dagger']['value_kcal_mol']} window "
        f"[{fixture.uma_window.low}, {fixture.uma_window.high}]; reported {payload['reported']}"
    )
    assert_checks_pass(payload["checks"])
