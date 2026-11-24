"""Tier 3 E2E: the Diels-Alder pair, TS1a_n (unmapped) and TS1b_n (mapped from M1) (slice 08).

TJ A2 "Q2.  A", A4 "Q4. A" (windows TS1a_n [10.7, 24.7], TS1b_n [20, 34], 1 M, UMA-gated) and
Q-TJ3 (GFN2 gates convergence and the mode count only). A UMA miss is a finding for TJ (Q-E5),
never a widened window. The candidates are committed for TJ's Phase 3 review (ADR-0027).
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from candidates import environment
from checks import assert_checks_pass, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import t3
from t3 import (
    barrier_payload,
    cache_summary,
    candidate_dir,
    gates,
    reactant_summary,
    reported_block,
    run_case,
    ts_payload,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

CASES = {"ts1a_n": "t3_ts1a_n_unmapped.yaml", "ts1b_n": "t3_ts1b_n_mapped.yaml"}
FORMING_CORE = [1, 2, 3, 5]
"""The forming core of both Diels-Alder TSs (G5: reported RMSD to Liu's TS under the map)."""


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_t3_diels_alder(
    recipe_name: str,
    case: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    commit_sha: str,
) -> None:
    """Search, validate, barrier; second run all hits; gated per Q-TJ3; candidate written."""
    recipe = recipes(recipe_name)
    fixture = t3(CASES[case])
    store_path = tmp_path / "store.sqlite"
    first = run_case(fixture, recipe, recipe_name, store_path)
    second = run_case(fixture, recipe, recipe_name, store_path)
    tier = gates(recipe_name, first, second, fixture.window_dG_dagger_1M_kcal_mol)
    reported = reported_block(recipe_name, fixture, first, FORMING_CORE)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = {
        "fixture": fixture.name,
        "case": case,
        "recipe": recipe_name,
        "commit_sha": commit_sha,
        "environment": environment(identity, DEVICES[recipe_name]),
        "thermo_config": recipe.thermo_config.model_dump(mode="json"),
        "window_dG_dagger_1M_kcal_mol": list(fixture.window_dG_dagger_1M_kcal_mol),
        "ts": ts_payload(first.ts),
        "barrier": barrier_payload(first.barrier),
        "reactants": reactant_summary(first.reactants),
        "reported": reported,
        "second_run_cache": cache_summary(second),
        "checks": {"tier_gates": tier},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / f"t3_{case}.{recipe_name}.json", payload)
    print(
        f"\nT3 {case} {recipe_name}: failed_reason {first.ts.failed_reason}; "
        f"gates { {k: v['status'] for k, v in tier.items()} }; "
        f"dG_dagger_1M {tier['window_dG_dagger_1M']['value_kcal_mol']} window "
        f"{fixture.window_dG_dagger_1M_kcal_mol}; reported {reported}"
    )
    assert_checks_pass(payload["checks"])
