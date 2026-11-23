"""The v0.4.0 acceptance record: merge, schema check and verdict rule (slice 07; R56)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from acceptance_record_v040 import (
    KNOWN_LIMITS,
    VERDICTS,
    check,
    merge_runs,
    pytest_counts,
    record_verdict,
)

GATES = ("g1_core_frozen", "g2_connectivity_equals_ts1b_n", "g3_junction_signs_equal_ts1b_n")


def graft_fragment(
    regression: str = "pending_promotion", mapping: str = "pending_confirmation"
) -> dict[str, Any]:
    """A graft fragment as test_m1_relax writes it."""
    return {
        "fixture": "m1",
        "recipe": "graft",
        "schema": 1,
        "forming_core_rmsd": {"status": "pass", "value_angstrom": 0.0498, "bound_angstrom": 0.1},
        "tier_d": {"d3_forming_core_rmsd": {"status": "pass"}},
        "regression_graft": {"status": regression},
        "map_confirmation": mapping,
        "reported": {"full_rmsd_angstrom": 0.7794},
        "test_outcome": "passed",
        "failed_checks": [],
    }


def recipe_fragment(
    recipe: str, gate: str = "pass", regression: str = "pending_promotion"
) -> dict[str, Any]:
    """A relaxed-recipe fragment as test_m1_relax writes it."""
    return {
        "fixture": "m1",
        "recipe": recipe,
        "schema": 1,
        "relaxed_gates": {"status": gate, **{g: {"status": gate} for g in GATES}},
        "regression_relaxed": {"status": regression},
        "reported": {"full_rmsd_angstrom": 0.55},
        "metrics": {
            "wall_time_s": 3.0,
            "n_steps": 17,
            "n_engine_calls": 18,
            "recovery_steps": ["tric"],
            "device": "cpu" if recipe == "xtb" else "cuda",
        },
        "core_max_displacement_angstrom": 4e-8,
        "test_outcome": "passed" if gate == "pass" else "failed",
        "failed_checks": [] if gate == "pass" else ["tier_gates.g1_core_frozen"],
    }


def runs(**overrides: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Two per-recipe acceptance files (xtb carries the graft fragment)."""
    common = {
        "commit_sha": "c1",
        "tree_clean": True,
        "run_at_utc": "2026-11-23T21:30:00+00:00",
        "hardware": {"gpu": "test"},
        "fixture_sha256": {},
    }
    m1_xtb = {"graft": graft_fragment(), "xtb": recipe_fragment("xtb")}
    m1_uma = {"uma": recipe_fragment("uma")}
    m1_xtb.update({k: v for k, v in overrides.items() if k in ("graft", "xtb")})
    m1_uma.update({k: v for k, v in overrides.items() if k == "uma"})
    return {
        "xtb": {**common, "engine": {"name": "xtb"}, "device": "cpu", "fixtures": {"m1": m1_xtb}},
        "uma": {**common, "engine": {"name": "uma"}, "device": "cuda", "fixtures": {"m1": m1_uma}},
    }


COMMANDS = [
    {
        "argv": ["pytest"],
        "env": {},
        "exit_code": 0,
        "wall_s": 4.0,
        "log": "xtb.log",
        "summary": "1 passed",
    }
]
SUITE = {
    "command": "uv run pytest",
    "exit_code": 0,
    "passed": 10,
    "failed": 0,
    "cleanroom_vectors": {
        "command": "uv run pytest tests/unit/mapping",
        "exit_code": 0,
        "passed": 5,
        "failed": 0,
    },
}
PROMOTION = {
    "tj_answer": {"verbatim": "1. PROMOTED: …"},
    "promotion_commit": "174a783",
    "files": {
        name: {
            "sha256": "0" * 64,
            "blob_id": "b",
            "candidate_blob_id": "b",
            "equals_candidate": True,
        }
        for name in ("m1_graft.json", "m1_relaxed.uma.json", "m1_relaxed.xtb.json")
    },
}


def test_pre_promotion_record_is_pending_and_valid() -> None:
    """Gates pass, regression pending_promotion, map pending_confirmation: verdict pending."""
    record = merge_runs(runs(), COMMANDS, SUITE)
    assert check(record) == []
    assert record["verdict"] == "pending"
    assert sorted(record["fixtures"]["m1"]) == ["graft", "uma", "xtb"]
    assert record["known_limits"] == list(KNOWN_LIMITS)
    assert "fixture" not in record["fixtures"]["m1"]["xtb"]
    assert any("map_confirmation pending_confirmation" in r for r in record["verdict_reasons"])


def test_everything_settled_is_pass() -> None:
    """Promoted and confirmed everywhere: verdict pass with no reasons."""
    record = merge_runs(
        runs(
            graft=graft_fragment("pass", "confirmed"),
            xtb=recipe_fragment("xtb", regression="pass"),
            uma=recipe_fragment("uma", regression="pass"),
        ),
        COMMANDS,
        SUITE,
        PROMOTION,
    )
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert check(record) == []
    no_evidence = copy.deepcopy(record)
    del no_evidence["evidence"]["promotion"]
    assert any("evidence.promotion" in p for p in check(no_evidence))


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"uma": recipe_fragment("uma", gate="fail")}, "m1.uma: relaxed_gates fail"),
        ({"xtb": recipe_fragment("xtb", regression="fail")}, "m1.xtb: regression_relaxed fail"),
        ({"graft": graft_fragment(mapping="fail")}, "m1.graft: map_confirmation fail"),
    ],
)
def test_any_failure_is_fail(overrides: dict[str, Any], reason: str) -> None:
    """A failed gate, regression or map confirmation makes the verdict fail, with the reason."""
    record = merge_runs(runs(**overrides), COMMANDS, SUITE)
    assert record["verdict"] == "fail"
    assert reason in record["verdict_reasons"]


def test_missing_fragment_is_fail() -> None:
    """A test that raised before writing its fragment is recorded as missing, and fails."""
    data = runs()
    del data["uma"]["fixtures"]["m1"]["uma"]
    record = merge_runs(data, COMMANDS, SUITE)
    assert record["fixtures"]["m1"]["uma"] == {"test_outcome": "missing"}
    assert record["verdict"] == "fail"
    assert "m1.uma: test_outcome missing" in record["verdict_reasons"]


def test_record_verdict_never_pass_with_pending() -> None:
    """record_verdict reads pass only when nothing is fail, pending_* or missing (R56)."""
    fixtures = {"m1": {"graft": graft_fragment(), "xtb": recipe_fragment("xtb")}}
    assert record_verdict(fixtures, SUITE, COMMANDS)["verdict"] == "fail"  # uma missing
    fixtures["m1"]["uma"] = recipe_fragment("uma")
    assert record_verdict(fixtures, SUITE, COMMANDS)["verdict"] == "pending"
    assert record_verdict(fixtures)["verdict"] == "fail"  # no default suite


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda r: r["fixtures"]["m1"].pop("uma"), "missing fixtures.m1.uma"),
        (
            lambda r: r["fixtures"]["m1"]["xtb"]["regression_relaxed"].update(status="ok"),
            "regression_relaxed status",
        ),
        (lambda r: r["fixtures"]["m1"]["graft"].update(map_confirmation="yes"), "map_confirmation"),
        (lambda r: r["fixtures"]["m1"]["uma"]["metrics"].pop("device"), "metrics"),
        (lambda r: r["known_limits"].append("a gated failure"), "known_limits"),
        (lambda r: r.update(verdict="pass"), "is not the fixtures' verdict"),
        (lambda r: r.pop("default_suite"), "missing default_suite"),
    ],
)
def test_check_rejects(mutate: Any, fragment: str) -> None:
    """The schema check catches a missing entry, a bad value, a missing block or a wrong verdict."""
    record = copy.deepcopy(merge_runs(runs(), COMMANDS, SUITE))
    mutate(record)
    assert any(fragment in p for p in check(record)), check(record)


def test_merge_refuses_unclean_or_split_commits() -> None:
    """Both recipes must run at one clean commit."""
    data = runs()
    data["uma"]["commit_sha"] = "other"
    with pytest.raises(ValueError, match="different or unclean"):
        merge_runs(data, COMMANDS, SUITE)
    data = runs()
    data["xtb"]["tree_clean"] = False
    with pytest.raises(ValueError, match="different or unclean"):
        merge_runs(data, COMMANDS, SUITE)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "==== 1386 passed, 119 deselected, 2 warnings in 307.42s (0:05:07) ====",
            {"passed": 1386, "deselected": 119, "failed": 0},
        ),
        ("==== 1 passed, 1 deselected in 3.53s ====", {"passed": 1, "deselected": 1}),
        ("1380 passed, 117 deselected, 2 warnings in 143.30s (0:02:23)", {"passed": 1380}),
        (
            "== 2 failed, 5 passed, 1 skipped, 1 error in 1.0s ==",
            {"failed": 2, "skipped": 1, "errors": 1},
        ),
    ],
)
def test_pytest_counts(line: str, expected: dict[str, int]) -> None:
    """The default_suite counts come from pytest's own summary line."""
    counts = pytest_counts("some output\n" + line + "\n")
    assert {k: counts[k] for k in expected} == expected


# --- the committed record ------------------------------------------------------------------

RECORD = Path(__file__).resolve().parents[2] / "docs" / "prd" / "v0.4.0" / "ACCEPTANCE_RESULT.json"


def test_committed_record_parses_and_is_pre_promotion() -> None:
    """The committed record is valid; gates pass; regressions and the map are pending (R22)."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["record_schema"] == 1
    assert check(record) == []
    m1 = record["fixtures"]["m1"]
    assert sorted(m1) == ["graft", "uma", "xtb"]
    assert m1["graft"]["forming_core_rmsd"]["status"] == "pass"
    assert m1["graft"]["regression_graft"]["status"] in VERDICTS["regression"]
    assert m1["graft"]["map_confirmation"] in VERDICTS["map_confirmation"]
    for recipe in ("xtb", "uma"):
        assert m1[recipe]["test_outcome"] == "passed"
        assert m1[recipe]["relaxed_gates"]["status"] == "pass"
        assert m1[recipe]["regression_relaxed"]["status"] in VERDICTS["regression"]
    assert record["verdict"] in VERDICTS["record"]
    assert record["known_limits"] == list(KNOWN_LIMITS)
    assert record["default_suite"]["exit_code"] == 0
    assert record["default_suite"]["cleanroom_vectors"]["failed"] == 0


# --- replan 2 (mission R27): the default suite, vectors, commands and skips gate the verdict -----


def settled_runs() -> dict[str, dict[str, Any]]:
    """Runs whose every fixture check passed (promoted and confirmed)."""
    return runs(
        graft=graft_fragment("pass", "confirmed"),
        xtb=recipe_fragment("xtb", regression="pass"),
        uma=recipe_fragment("uma", regression="pass"),
    )


def failing_suite() -> dict[str, Any]:
    """SUITE with one failed test."""
    suite = copy.deepcopy(SUITE)
    suite["failed"] = 1
    return suite


def failing_vectors() -> dict[str, Any]:
    """SUITE with a failing clean-room vector run."""
    suite = copy.deepcopy(SUITE)
    suite["cleanroom_vectors"]["exit_code"] = 1
    return suite


def command_with(**change: Any) -> list[dict[str, Any]]:
    """COMMANDS with one field changed."""
    return [{**COMMANDS[0], **change}]


@pytest.mark.parametrize(
    ("suite", "commands", "reason"),
    [
        (failing_suite, lambda: COMMANDS, "default_suite: exit_code 0, failed 1"),
        (
            failing_vectors,
            lambda: COMMANDS,
            "default_suite.cleanroom_vectors: exit_code 1, failed 0",
        ),
        (lambda: SUITE, lambda: command_with(exit_code=2), "commands[0] pytest: exit_code 2"),
        (
            lambda: SUITE,
            lambda: command_with(summary="1 passed, 1 skipped, 1 deselected in 4.0s"),
            "commands[0] pytest: 1 skipped",
        ),
    ],
)
def test_all_pass_fixtures_still_fail_on_suite_vectors_commands_or_skips(
    suite: Any, commands: Any, reason: str
) -> None:
    """R27 (a), (c): a failing default suite, vector run, command or a skip gives fail."""
    record = merge_runs(settled_runs(), commands(), suite(), PROMOTION)
    assert record["verdict"] == "fail"
    assert reason in record["verdict_reasons"]
    assert check(record) == []


def test_hand_edited_pass_is_refused() -> None:
    """check() recomputes the verdict from fixtures, suite and commands."""
    record = merge_runs(settled_runs(), COMMANDS, failing_suite(), PROMOTION)
    record["verdict"], record["verdict_reasons"] = "pass", []
    assert any("is not the fixtures' verdict" in p for p in check(record))


def test_record_without_verdict_is_refused() -> None:
    """R27 (b): a record without the verdict key is refused by check()."""
    record = merge_runs(settled_runs(), COMMANDS, SUITE, PROMOTION)
    del record["verdict"]
    assert "missing verdict" in check(record)
