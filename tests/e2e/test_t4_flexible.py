"""Tier 4 flexible-ensemble E2E: an alkyl R-group series on TS1a_n (slice 14).

TJ's amended Q-RES1 B. R = ethyl, n-propyl, n-butyl on the cyclopropene CH2 of TS1a_n, grafted with
eta's graft, pre-relaxed with the core frozen inside ``deadline(PRE_RELAX_BUDGET_S)`` (TJ's HF-13
guard on the grafts), then the v0.6.0 TS ensemble twice in one store. Gated per R: no failed
reason, at least two distinct members, unit weights, the seed's face (no ``face_mismatch`` or
``engine_error``), a second pass of all hits, and no graft pre-relax timeout. Member counts,
energies, exclusions and ΔG‡ are reported only. The candidate is written for TJ's Phase 3 look; it
makes no regression claim (no promoted fixture exists).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from acceptance import write_fragment
from candidates import environment
from checks import assert_checks_pass, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS
from t4 import candidate_dir
from t4_flexible import (
    SERIES,
    candidate_name,
    flex,
    gates,
    graft_block,
    inputs_block,
    non_decreasing_report,
    reported_block,
    run_environment,
    run_flexible,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


def params() -> list[Any]:
    """Every recipe x R, each under its engine marker (one R x recipe per command with -k)."""
    out = []
    for param in RECIPE_PARAMS:
        for r_group in SERIES:
            out.append(
                pytest.param(
                    param.values[0], r_group, marks=param.marks, id=f"{param.values[0]}-{r_group}"
                )
            )
    return out


@pytest.mark.parametrize(("recipe_name", "r_group"), params())
def test_t4_flexible(
    recipe_name: str,
    r_group: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    commit_sha: str,
) -> None:
    """Graft, guarded pre-relax, ensemble twice, gates; the candidate is written first."""
    recipe = recipes(recipe_name)
    fixture = flex()
    series = fixture.get(r_group)
    run = run_flexible(fixture, series, recipe, recipe_name, tmp_path / "store.sqlite")
    tier = gates(run)
    reported = reported_block(fixture, run)
    if run.runs[0] is not None:
        reported["chain_length_order"] = non_decreasing_report(
            recipe_name, r_group, len(run.runs[0].ensemble.members)
        )
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
        "fixture": fixture.name,
        "case": f"t4_flexible_{r_group}",
        "recipe": recipe_name,
        "r_group": r_group,
        "commit_sha": commit_sha,
        "environment": {
            **environment(identity, DEVICES[recipe_name]),
            "run": run_environment(recipe_name),
        },
        "inputs_sha256": inputs_block(fixture, series),
        "graft": graft_block(fixture, run),
        "reported": reported,
        "regression": {
            "status": "pending_promotion",
            "note": "no promoted fixture exists for this case (slice 14; Phase 3)",
        },
        "checks": {"tier_gates": tier},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / candidate_name(r_group, recipe_name), payload)
    write_fragment(f"t4_flexible_{r_group}", recipe_name, payload)
    print(
        f"\nT4 flexible {r_group} {recipe_name}: "
        f"gates { {k: v['status'] for k, v in tier.items()} }; "
        f"members {reported.get('n_members')} (expected {series.expected_members}); "
        f"exclusions {reported.get('exclusions_by_reason')}; "
        f"max pre-relax {reported.get('max_pre_relax_wall_time_s')}; barrier {reported['barrier']}"
    )
    assert_checks_pass(payload["checks"])
