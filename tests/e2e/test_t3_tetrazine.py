"""Tier 3 E2E: the tetrazine pair, TS3a (unmapped) and TS4a (two CF3 grafts on TS3a) (slice 09).

TJ A3 "Q3. A" (dual -CF3 = two single grafts), A4 "Q4. A" (windows TS3a [10.0, 24.0], TS4a
[0.7, 14.7], 1 M, UMA-gated) and Q-TJ3 (GFN2 gates convergence and the mode count only). TJ's
ordering, dG dagger(TS4a) < dG dagger(TS3a) at 1 M, is gated on UMA and reported on GFN2. The
TS4a start is built once per recipe (grafts + core-frozen pre-relaxation) and both passes use it.
Q-TJ4 A (mission R32): GFN2 TS4a is report-only (recorded, never gated; an EngineError on that
pair is caught here and recorded), and GFN2 gates the identity core on TS3a.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from candidates import environment
from checks import assert_checks_pass, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import t3
from t3 import (
    CaseRun,
    barrier_payload,
    cache_summary,
    candidate_dir,
    gates,
    grafted_start,
    reactant_summary,
    reported_block,
    reported_outcome,
    run_case,
    ts_payload,
)

from eta_rxncat.engines import EngineError
from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

FORMING_CORE = [0, 3, 6, 7]
"""The forming core of both tetrazine TSs (G5: reported RMSD to Liu's TS under the map)."""


def candidate(
    case: str,
    recipe_name: str,
    recipe: Recipe,
    commit_sha: str,
    fixture: Any,
    first: CaseRun,
    second: CaseRun,
    tier: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    """The candidate payload of one case (slice 08's form, plus ``extra``)."""
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
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
        "reported": reported_block(recipe_name, fixture, first, FORMING_CORE),
        "second_run_cache": cache_summary(second),
        **extra,
        "checks": {"tier_gates": tier},
    }
    payload.update(outcome_fields(payload["checks"]))
    return payload


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_t3_tetrazine(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    commit_sha: str,
) -> None:
    """TS3a and TS4a: search, validate, barrier, second run, ordering; candidates written."""
    recipe = recipes(recipe_name)
    ts3a = t3("t3_ts3a_unmapped.yaml")
    ts4a = t3("t3_ts4a_mapped.yaml")
    start, graft_summary = grafted_start(ts4a, recipe, FORMING_CORE)

    report_only = {"ts3a": False, "ts4a": recipe_name == "xtb"}  # R32: GFN2 TS4a
    runs = {}
    engine_errors: dict[str, EngineError] = {}
    for case, fixture, fixed in (("ts3a", ts3a, None), ("ts4a", ts4a, start)):
        store_path = tmp_path / f"{case}.sqlite"
        try:
            first = run_case(fixture, recipe, recipe_name, store_path, fixed)
            second = run_case(fixture, recipe, recipe_name, store_path, fixed)
        except EngineError as exc:
            if not report_only[case]:
                raise
            engine_errors[case] = exc
            continue
        runs[case] = (fixture, first, second)

    dg: dict[str, float | None] = {"ts3a": None, "ts4a": None}
    for case, (_, first, _) in runs.items():
        dg[case] = None if first.barrier is None else first.barrier.dG_dagger_1M_kcal_mol
    ordered = dg["ts3a"] is not None and dg["ts4a"] is not None and dg["ts4a"] < dg["ts3a"]
    ordering = {
        "status": ("pass" if ordered else "fail") if recipe_name == "uma" else "reported",
        "dG_dagger_1M_ts4a_kcal_mol": dg["ts4a"],
        "dG_dagger_1M_ts3a_kcal_mol": dg["ts3a"],
    }

    payloads = {}
    for case, exc in engine_errors.items():
        payload = {
            "fixture": ts4a.name,
            "case": case,
            "recipe": recipe_name,
            "commit_sha": commit_sha,
            "report_only": True,
            "reported_outcome": "failed",
            "failed_reason": f"engine_error:{type(exc).__name__}",
            "engine_error_message": str(exc),
            "failed_checks": ["engine_error"],
            "graft_summary": graft_summary,
            "ordering_ts4a_below_ts3a": ordering,
            "checks": {"tier_gates": {}},
            "test_outcome": "report_only",
        }
        write(candidate_dir() / f"t3_{case}.{recipe_name}.json", payload)
        payloads[case] = payload
        print(f"\nT3 {case} {recipe_name}: REPORT-ONLY engine_error {type(exc).__name__}: {exc}")
    for case, (fixture, first, second) in runs.items():
        tier = gates(
            recipe_name,
            first,
            second,
            fixture.window_dG_dagger_1M_kcal_mol,
            report_only=report_only[case],
        )
        extra: dict[str, Any] = {}
        if case == "ts4a":
            tier["ordering_ts4a_below_ts3a"] = ordering
            extra["graft_summary"] = graft_summary
        else:
            extra["ordering_ts4a_below_ts3a"] = ordering
        payload = candidate(
            case, recipe_name, recipe, commit_sha, fixture, first, second, tier, extra
        )
        if report_only[case]:
            outcome, failed = reported_outcome(tier)
            payload.update(
                report_only=True,
                reported_outcome=outcome,
                failed_reason=first.ts.failed_reason,
                failed_checks=failed,
                test_outcome="report_only",
            )
        write(candidate_dir() / f"t3_{case}.{recipe_name}.json", payload)
        payloads[case] = payload
        print(
            f"\nT3 {case} {recipe_name}: failed_reason {first.ts.failed_reason}; "
            f"gates { {k: v['status'] for k, v in tier.items()} }; dG_dagger_1M {dg[case]} "
            f"window {fixture.window_dG_dagger_1M_kcal_mol}; reported {payload['reported']}"
        )
    print(f"\nT3 tetrazine {recipe_name}: ordering {ordering}; graft {graft_summary['pre_relax']}")
    for payload in payloads.values():
        if payload.get("report_only"):
            # R32: GFN2 TS4a is report-only: marked so, and none of its checks is gated.
            statuses = {v["status"] for v in payload["checks"]["tier_gates"].values()}
            assert payload["report_only"] is True and statuses <= {"reported"}
        else:
            assert_checks_pass(payload["checks"])
