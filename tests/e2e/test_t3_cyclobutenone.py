"""Tier 3 E2E: cyclopentadiene + cyclobutenone, Paton's endo N4 TS (unmapped) (slice 10).

TJ A3 "Q3. A", A4 "Q4. A" (window [15.6, 29.6], 1 M, UMA-gated), Q-TJ3 amended by Q-TJ4 A (mission
R32): GFN2 gates convergence, the mode count and the identity core; UMA as before. Paton's
"E(M06-2X)" column is thermally corrected, so the reference is G only and no literature ΔE‡ is
reported anywhere.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from acceptance import write_fragment
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

FORMING_CORE = [1, 2, 9, 10]
"""N4's forming atoms (the reported forming-core RMSD to Paton's N4, identity map)."""


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_t3_cyclobutenone(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    commit_sha: str,
) -> None:
    """Search, validate, barrier; second run all hits; gated per R32; candidate written."""
    recipe = recipes(recipe_name)
    fixture = t3("t3_n4_unmapped.yaml")
    store_path = tmp_path / "store.sqlite"
    first = run_case(fixture, recipe, recipe_name, store_path)
    second = run_case(fixture, recipe, recipe_name, store_path)
    tier = gates(recipe_name, first, second, fixture.window_dG_dagger_1M_kcal_mol)
    reported = reported_block(recipe_name, fixture, first, FORMING_CORE)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = {
        "fixture": fixture.name,
        "case": "n4",
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
    # Paton prints no electronic energy: no literature dE dagger may appear (mission R8, HF-9).
    assert "dE_dagger" not in json.dumps(payload["reported"])
    write(candidate_dir() / f"t3_n4.{recipe_name}.json", payload)
    write_fragment("t3_n4", recipe_name, payload)
    print(
        f"\nT3 n4 {recipe_name}: failed_reason {first.ts.failed_reason}; "
        f"gates { {k: v['status'] for k, v in tier.items()} }; "
        f"dG_dagger_1M {tier['window_dG_dagger_1M']['value_kcal_mol']} window "
        f"{fixture.window_dG_dagger_1M_kcal_mol}; reported {reported}"
    )
    assert_checks_pass(payload["checks"])
