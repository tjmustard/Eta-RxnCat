"""The v0.5.0 acceptance record: merge, schema check, verdict and bounds rules (slices 12-13)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from acceptance_record_v050 import (
    CASES,
    HF1_SHA256,
    KNOWN_LIMITS,
    PROMOTED_FILES,
    RECIPES,
    REPORT_ONLY,
    TJ_BOUNDS,
    check,
    command_entry,
    git_blob_id,
    merge_runs,
    promotion_evidence,
    proposed_bounds,
    record_verdict,
    reproducibility_entry,
)
from t3 import PROMOTED_V050, REGRESSION_BOUNDS

STATE = {
    "symbols": ["C", "C", "N", "O", "H"],
    "coordinates": [[0, 0, 0], [1.5, 0, 0], [0, 1.4, 0], [0, 0, 1.2], [2, 1, 0]],
}


def moved(dx: float) -> dict[str, Any]:
    """STATE with the second carbon moved by ``dx`` Angstrom along y."""
    state = copy.deepcopy(STATE)
    state["coordinates"][1][1] = dx
    return state


def gates(status: str = "pass", uma: bool = False) -> dict[str, Any]:
    """Tier gates as t3.gates writes them (GFN2 reports identity and window)."""
    names = ("search_converged", "mode_count", "active_core", "barrier_conservation")
    out: dict[str, Any] = {g: {"status": status} for g in names}
    out["forming_overlap"] = {"status": "reported" if uma else status, "value": 0.7}
    out["forming_in_phase"] = {"status": "reported" if uma else status}
    out["identity"] = {"status": status if uma else "reported"}
    out["window_dG_dagger_1M"] = {"status": status if uma else "reported", "value_kcal_mol": 18}
    return out


def case_fragment(case: str, recipe: str, status: str = "pass") -> dict[str, Any]:
    """A Tier 3 fragment as the slice 08-10 tests write it."""
    if (recipe, case) in REPORT_ONLY:
        return {
            "case": case,
            "recipe": recipe,
            "report_only": True,
            "reported_outcome": "failed",
            "failed_reason": "ts_search_failed:max_steps",
            "failed_checks": ["search_converged"],
            "checks": {"tier_gates": {"search_converged": {"status": "reported"}}},
            "test_outcome": "report_only",
            "ts": {"failed_reason": "ts_search_failed:max_steps", "thermo": None, "state": None},
            "barrier": None,
        }
    tier = gates(status, uma=recipe == "uma")
    failed = sorted(f"tier_gates.{k}" for k, v in tier.items() if v["status"] == "fail")
    return {
        "case": case,
        "recipe": recipe,
        "checks": {"tier_gates": tier},
        "test_outcome": "failed" if failed else "passed",
        "failed_checks": failed,
        "ts": {
            "failed_reason": None,
            "thermo": {"electronic_energy_hartree": -100.0},
            "state": STATE,
        },
        "barrier": {"dG_dagger_1M_kcal_mol": 18.0},
        "reported": {"connectivity_equal_bool": True},
        "second_run_cache": {},
        "window_dG_dagger_1M_kcal_mol": [10, 24],
    }


def repro_fragment(de: float = 1e-7, dg: float = 1e-4, dx: float = 0.0) -> dict[str, Any]:
    """Two fresh-store runs as test_t3_reproducibility writes them."""
    return {
        "runs": [
            {"ts_energy_hartree": -100.0, "dG_dagger_1M_kcal_mol": 18.0, "ts_state": STATE},
            {
                "ts_energy_hartree": -100.0 + de,
                "dG_dagger_1M_kcal_mol": 18.0 + dg,
                "ts_state": moved(dx),
            },
        ]
    }


def runs(**cases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Two per-recipe acceptance files; ``cases`` overrides ``<case>_<recipe>`` fragments."""
    out = {}
    for recipe in RECIPES:
        frags = {c: case_fragment(c, recipe) for c in CASES}
        frags.update({k.split("__")[0]: v for k, v in cases.items() if k.endswith(f"__{recipe}")})
        out[recipe] = {
            "recipe": recipe,
            "commit_sha": "c1",
            "tree_clean": True,
            "run_at_utc": "2026-11-24T20:00:00+00:00",
            "device": "cpu" if recipe == "xtb" else "cuda",
            "engine": {"name": recipe},
            "python": "3.12.0",
            "hardware": {"gpu": "test"},
            "cases": frags,
            "reproducibility": {
                c: repro_fragment() for c in CASES if (recipe, c) not in REPORT_ONLY
            },
        }
    out["uma"]["cross_check"] = {
        "records": {
            f"{c}.{r}": {"status": "converged", "exit_code": 0} for c in CASES for r in RECIPES
        },
        "geometric_version": "1.1.1",
    }
    return out


COMMANDS = [
    {
        "argv": ["pytest"],
        "env": {},
        "exit_code": 0,
        "wall_s": 4.0,
        "log": "a.log",
        "summary": "1 passed",
    }
]
SUITE = {"command": "uv run pytest", "exit_code": 0, "passed": 10, "failed": 0, "errors": 0}


NO_PROMOTION = Path(__file__).resolve().parent / "no_promoted_fixtures_here"
"""A directory that does not exist: the pre-promotion state (slice 12)."""


def merged(**cases: dict[str, Any]) -> dict[str, Any]:
    """A pre-promotion record merged from synthetic fragments."""
    return merge_runs(runs(**cases), COMMANDS, SUITE, promoted_dir=NO_PROMOTION)


def settled(record: dict[str, Any]) -> dict[str, Any]:
    """The record's fixtures with every pending state settled to ``pass`` (TJ acted)."""
    fixtures = copy.deepcopy(record["fixtures"])
    for by in fixtures["t3"].values():
        for entry in by.values():
            if entry.get("regression", {}).get("status") == "pending_promotion":
                entry["regression"]["status"] = "pass"
    fixtures["transcription_confirmation"]["status"] = "pass"
    return fixtures


def test_pre_promotion_record_is_valid_without_verdict() -> None:
    """Gates pass; regression and confirmation pending; no verdict key; the rule says fail."""
    record = merged()
    assert check(record) == [] and "verdict" not in record
    assert record["known_limits"] == list(KNOWN_LIMITS)
    for case in CASES:
        for recipe in RECIPES:
            entry = record["fixtures"]["t3"][case][recipe]
            want = "reported" if (recipe, case) in REPORT_ONLY else "pending_promotion"
            assert entry["regression"]["status"] == want
    assert record["fixtures"]["transcription_confirmation"]["status"] == "pending_confirmation"
    assert record["fixtures"]["transcriptions"]["sha256"]["status"] == "pass"
    assert record["fixtures"]["transcriptions"]["r9"]["status"] == "pass"
    assert record["fixtures"]["cross_check"]["status"] == "pass"
    verdict = record_verdict(record["fixtures"], SUITE, COMMANDS)
    assert verdict["verdict"] == "fail"
    assert all("pending_" in r for r in verdict["verdict_reasons"])


def test_settled_record_is_pass() -> None:
    """With every pending state settled, the verdict is pass."""
    fixtures = settled(merged())
    assert record_verdict(fixtures, SUITE, COMMANDS) == {"verdict": "pass", "verdict_reasons": []}


def test_gfn2_identity_core_is_gated_on_every_case_but_ts4a() -> None:
    """R32: GFN2 TS1a_n/TS1b_n/TS3a/N4 carry identity_core; a failed overlap fails the record."""
    record = merged()
    for case in CASES:
        entry = record["fixtures"]["t3"][case]["xtb"]
        if case == "ts4a":
            assert "identity_core" not in entry and entry["report_only"] is True
        else:
            assert entry["identity_core"]["status"] == "pass"
    fixtures = settled(record)
    fixtures["t3"]["ts1a_n"]["xtb"]["tier_gates"]["forming_overlap"]["status"] = "fail"
    reasons = record_verdict(fixtures, SUITE, COMMANDS)["verdict_reasons"]
    assert "t3.ts1a_n.xtb.tier_gates.forming_overlap: fail" in reasons


def test_report_only_failure_never_fails_the_record() -> None:
    """R32: GFN2 TS4a failed (report-only) leaves the gated checks unaffected."""
    fixtures = settled(merged())
    entry = fixtures["t3"]["ts4a"]["xtb"]
    assert entry["report_only"] is True and entry["reported_outcome"] == "failed"
    assert record_verdict(fixtures, SUITE, COMMANDS)["verdict"] == "pass"


@pytest.mark.parametrize(("case", "recipe"), [("ts4a", "uma"), ("ts3a", "xtb"), ("n4", "uma")])
def test_same_failure_on_any_other_pair_fails(case: str, recipe: str) -> None:
    """The report-only exemption is GFN2 TS4a's alone: the same failure elsewhere fails."""
    fail = case_fragment(case, recipe, status="fail")
    fail["checks"]["tier_gates"]["search_converged"] = {"status": "fail"}
    record = merged(**{f"{case}__{recipe}": fail})
    fixtures = settled(record)
    verdict = record_verdict(fixtures, SUITE, COMMANDS)
    assert verdict["verdict"] == "fail"
    assert f"t3.{case}.{recipe}.test_outcome: fail" in verdict["verdict_reasons"]


def test_report_only_flag_on_another_pair_is_refused() -> None:
    """Only GFN2 TS4a may be report-only; a forged flag elsewhere is a schema problem."""
    record = merged()
    record["fixtures"]["t3"]["ts3a"]["uma"]["report_only"] = True
    assert any("only GFN2 TS4a" in p for p in check(record))


def test_missing_fragment_is_missing_and_fails() -> None:
    """R56: a fragment never written is ``missing`` and fails the verdict."""
    fixtures = settled(merged(n4__uma={"test_outcome": "missing"}))
    reasons = record_verdict(fixtures, SUITE, COMMANDS)["verdict_reasons"]
    assert "t3.n4.uma.test_outcome: missing" in reasons


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda s, c: (None, c), "default_suite: missing"),
        (lambda s, c: ({**s, "failed": 1}, c), "default_suite: exit_code 0, failed 1"),
        (lambda s, c: ({**s, "exit_code": 1}, c), "default_suite: exit_code 1"),
        (lambda s, c: ({**s, "errors": 2}, c), "errors 2"),
        (lambda s, c: (s, [{**c[0], "exit_code": 1}]), "exit_code 1"),
        (lambda s, c: (s, [{**c[0], "summary": "1 passed, 1 skipped in 3.0s"}]), "1 skipped"),
        (lambda s, c: (s, []), "commands: none recorded"),
    ],
)
def test_suite_command_or_skip_fails(change: Any, reason: str) -> None:
    """v0.4.0 R27: a failing suite, a failing command or a skip fails a settled record."""
    fixtures = settled(merged())
    suite, commands = change(SUITE, COMMANDS)
    verdict = record_verdict(fixtures, suite, commands)
    assert verdict["verdict"] == "fail"
    assert any(reason in r for r in verdict["verdict_reasons"]), verdict


@pytest.mark.parametrize("state", ["fail", "pending_promotion", "pending_confirmation", "skipped"])
def test_any_non_pass_state_fails(state: str) -> None:
    """fail, pending_*, skipped each fail the verdict (R56)."""
    fixtures = settled(merged())
    fixtures["cross_check"]["status"] = state
    assert record_verdict(fixtures, SUITE, COMMANDS)["verdict_reasons"] == [f"cross_check: {state}"]


def test_stated_pass_that_disagrees_is_refused() -> None:
    """A hand-written ``pass`` on a record whose rule says fail is refused by ``check``."""
    record = merged()
    record.update(verdict="pass", verdict_reasons=[])
    assert any("is not the record's verdict" in p for p in check(record))
    record = merge_runs(promoted_runs(ts3a__uma=regressed("fail", "ts3a")), COMMANDS, SUITE)
    assert record["verdict"] == "fail" and check(record) == []
    record.update(verdict="pass", verdict_reasons=[])
    assert any("is not the record's verdict" in p for p in check(record))


def test_incomplete_cross_check_fails() -> None:
    """The cross-check gate: every case x recipe attempted and recorded."""
    r = runs()
    del r["uma"]["cross_check"]["records"]["n4.xtb"]
    record = merge_runs(r, COMMANDS, SUITE, promoted_dir=NO_PROMOTION)
    assert record["fixtures"]["cross_check"]["status"] == "fail"
    r = runs()
    del r["uma"]["cross_check"]
    record = merge_runs(r, COMMANDS, SUITE, promoted_dir=NO_PROMOTION)
    assert record["fixtures"]["cross_check"]["status"] == "missing"


def test_transcription_sha_mismatch_fails(tmp_path: Path) -> None:
    """A transcription that no longer equals HF-1 fails its check."""
    for name in HF1_SHA256:
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    record = merge_runs(runs(), COMMANDS, SUITE, xyz_dir=tmp_path, promoted_dir=NO_PROMOTION)
    assert record["fixtures"]["transcriptions"]["sha256"]["status"] == "fail"


def test_merge_refuses_unclean_or_split_commits() -> None:
    """Both recipes must run at one clean commit."""
    r = runs()
    r["uma"]["tree_clean"] = False
    with pytest.raises(ValueError, match="unclean"):
        merge_runs(r, COMMANDS, SUITE, promoted_dir=NO_PROMOTION)
    r = runs()
    r["uma"]["commit_sha"] = "c2"
    with pytest.raises(ValueError, match="different"):
        merge_runs(r, COMMANDS, SUITE, promoted_dir=NO_PROMOTION)


def test_reproducibility_measures_all_pairs() -> None:
    """Three runs, three pairs: the maxima include the acceptance run; GFN2 TS4a is n/a."""
    entry = reproducibility_entry(
        "ts3a", "uma", case_fragment("ts3a", "uma"), repro_fragment(2e-6, 0.03, 0.1)
    )
    assert entry["status"] == "measured" and entry["n_runs"] == 3
    assert entry["max_abs_delta_ts_energy_hartree"] == pytest.approx(2e-6)
    assert entry["max_abs_delta_dG_dagger_1M_kcal_mol"] == pytest.approx(0.03)
    assert entry["max_heavy_rmsd_angstrom"] > 0.0
    ts4a = reproducibility_entry("ts4a", "xtb", case_fragment("ts4a", "xtb"), {})
    assert ts4a["status"] == "n/a" and "report-only" in ts4a["reason"]
    missing = reproducibility_entry(
        "n4", "uma", case_fragment("n4", "uma"), {"test_outcome": "missing"}
    )
    assert missing["status"] == "missing"


def _measured(**values: float) -> dict[str, Any]:
    return {
        "status": "measured",
        "max_abs_delta_ts_energy_hartree": values.get("de", 0.0),
        "max_heavy_rmsd_angstrom": values.get("rmsd", 0.0),
        "max_abs_delta_dG_dagger_1M_kcal_mol": values.get("dg", 0.0),
    }


def test_bounds_rule_tj_bound_only_within_a_tenth() -> None:
    """TJ's bound when every measurement is <= 1/10 of it; else 10x the measured maximum."""
    repro = {
        "xtb": {"ts1a_n": _measured(de=1e-7, rmsd=1e-4, dg=1e-4)},
        "uma": {
            "ts1a_n": _measured(de=1e-7, rmsd=1e-4, dg=1e-4),
            "ts3a": _measured(de=8e-5, rmsd=0.004, dg=0.047),
        },
    }
    bounds = proposed_bounds(repro)["recipes"]
    for quantity, bound in TJ_BOUNDS.items():
        assert bounds["xtb"][quantity]["proposed"] == bound
        assert bounds["xtb"][quantity]["basis"] == "tj_bound"
    dg = bounds["uma"]["abs_delta_dG_dagger_1M_kcal_mol"]
    assert dg["basis"] == "ten_times_measured_max" and dg["proposed"] == pytest.approx(0.47)
    assert dg["measured_max_case"] == "ts3a" and "10x the measured maximum" in dg["statement"]
    assert bounds["uma"]["heavy_rmsd_angstrom"]["proposed"] == pytest.approx(0.04)
    assert bounds["uma"]["abs_delta_ts_energy_hartree"]["proposed"] == pytest.approx(8e-4)


def test_bounds_rule_edge_and_missing() -> None:
    """Exactly 1/10 keeps TJ's bound; a missing measurement proposes nothing."""
    repro = {
        "xtb": {"n4": _measured(de=1e-6, rmsd=0.001, dg=0.001)},
        "uma": {"n4": {"status": "missing"}},
    }
    bounds = proposed_bounds(repro)["recipes"]
    assert all(bounds["xtb"][q]["basis"] == "tj_bound" for q in TJ_BOUNDS)
    assert all(bounds["uma"][q]["status"] == "missing" for q in TJ_BOUNDS)


def test_command_entry_reads_summary_and_rss(tmp_path: Path) -> None:
    """The command block comes from the log: summary line and /usr/bin/time's max RSS."""
    log = tmp_path / "run.log"
    log.write_text(
        "x\n====== 1 passed, 3 deselected in 12.50s ======\n"
        "\tMaximum resident set size (kbytes): 6912345\n",
        encoding="utf-8",
    )
    entry = command_entry(log, 0, 13.0, {"A": "1"}, ["pytest", "-k", "x"])
    assert entry["summary"] == "1 passed, 3 deselected in 12.50s"
    assert entry["max_rss_kbytes"] == 6912345 and entry["log"] == "run.log"


# --- the verdict run (slice 13): TJ's promotion, regression, confirmation, verdict -----------


def regressed(status: str = "pass", case: str = "ts1a_n", recipe: str = "uma") -> dict[str, Any]:
    """A fragment carrying the in-process regression result ``t3.regression_ts`` writes."""
    fragment = case_fragment(case, recipe)
    fragment["checks"]["regression"] = {
        "status": status,
        "abs_delta_ts_energy_hartree": 0.0,
        "abs_delta_dG_dagger_1M_kcal_mol": 0.0,
        "heavy_rmsd_angstrom": 0.0,
        "bounds": dict(REGRESSION_BOUNDS[recipe]),
        "mismatches": [] if status == "pass" else ["abs_delta_dG_dagger_1M_kcal_mol"],
    }
    return fragment


def promoted_runs(**cases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Two acceptance files whose every gated fragment passed its regression."""
    r = runs()
    for recipe in RECIPES:
        for case in CASES:
            if (recipe, case) in REPORT_ONLY:
                r[recipe]["cases"][case]["checks"]["regression"] = {"status": "reported"}
            else:
                r[recipe]["cases"][case] = regressed("pass", case, recipe)
        for key, value in cases.items():
            if key.endswith(f"__{recipe}"):
                r[recipe]["cases"][key.split("__")[0]] = value
    return r


PRIOR = {
    "commit_sha": "c12",
    "reproducibility": {"uma": {"ts3a": {"status": "measured"}}},
    "proposed_regression_bounds": {"rule": "slice 12"},
}


def test_promotion_evidence_verifies_r33() -> None:
    """The committed fixtures equal R33's sha256s and blob ids; absent before the promotion."""
    evidence = promotion_evidence(PROMOTED_V050)
    assert evidence["status"] == "verified" and evidence["commit"] == "ccacac5"
    assert evidence["tj_answer_verbatim"] == "A: 0.75 all (Recommended)"
    assert sorted(evidence["files"]) == sorted(PROMOTED_FILES)
    assert promotion_evidence(NO_PROMOTION)["status"] == "absent"
    assert git_blob_id(b"") == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def test_promotion_evidence_refuses_a_changed_or_missing_file(tmp_path: Path) -> None:
    """A fixture that is not TJ's byte for byte, or a missing one, never feeds a verdict."""
    for name in PROMOTED_FILES:
        (tmp_path / name).write_bytes((PROMOTED_V050 / name).read_bytes())
    assert promotion_evidence(tmp_path)["status"] == "verified"
    first = sorted(PROMOTED_FILES)[0]
    (tmp_path / first).write_bytes((PROMOTED_V050 / first).read_bytes() + b" ")
    with pytest.raises(ValueError, match="not R33's"):
        promotion_evidence(tmp_path)
    (tmp_path / first).unlink()
    with pytest.raises(ValueError, match="not R33's"):
        promotion_evidence(tmp_path)


def test_verdict_run_passes_with_regression_and_confirmation() -> None:
    """Promoted: regression from the fragments, transcriptions confirmed, bounds, verdict pass."""
    record = merge_runs(promoted_runs(), COMMANDS, SUITE, prior=PRIOR)
    assert check(record) == []
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert record["fixtures"]["transcription_confirmation"]["status"] == "confirmed"
    assert record["evidence"]["promotion"]["status"] == "verified"
    assert record["regression_bounds"]["recipes"]["uma"]["abs_delta_dG_dagger_1M_kcal_mol"] == 0.75
    assert record["regression_bounds"]["recipes"]["xtb"]["abs_delta_dG_dagger_1M_kcal_mol"] == 0.01
    assert record["reproducibility"] == PRIOR["reproducibility"]
    assert "c12" in record["evidence"]["reproducibility_source"]
    for case in CASES:
        for recipe in RECIPES:
            want = "reported" if (recipe, case) in REPORT_ONLY else "pass"
            assert record["fixtures"]["t3"][case][recipe]["regression"]["status"] == want


@pytest.mark.parametrize(
    ("fragment", "reason"),
    [
        (regressed("fail", "ts3a", "uma"), "t3.ts3a.uma.regression: fail"),
        (case_fragment("ts3a", "uma"), "t3.ts3a.uma.regression: missing"),
    ],
)
def test_verdict_run_regression_miss_fails(fragment: dict[str, Any], reason: str) -> None:
    """A regression outside TJ's bounds, or none recorded, fails the verdict."""
    record = merge_runs(promoted_runs(ts3a__uma=fragment), COMMANDS, SUITE, prior=PRIOR)
    assert record["verdict"] == "fail" and reason in record["verdict_reasons"]


def test_report_only_regression_miss_never_fails() -> None:
    """R32: GFN2 TS4a's regression is compared and recorded, never gated."""
    ts4a = case_fragment("ts4a", "xtb")
    ts4a["checks"]["regression"] = {"status": "reported", "mismatches": ["ts_energy: missing"]}
    record = merge_runs(promoted_runs(ts4a__xtb=ts4a), COMMANDS, SUITE, prior=PRIOR)
    entry = record["fixtures"]["t3"]["ts4a"]["xtb"]["regression"]
    assert entry["status"] == "reported" and entry["mismatches"] == ["ts_energy: missing"]
    assert record["verdict"] == "pass"


def test_verdict_needs_verified_promotion_and_bounds() -> None:
    """``check`` refuses a stated verdict without TJ's bounds or a verified promotion."""
    record = merge_runs(promoted_runs(), COMMANDS, SUITE, prior=PRIOR)
    broken = copy.deepcopy(record)
    del broken["regression_bounds"]
    assert "missing regression_bounds" in check(broken)
    broken = copy.deepcopy(record)
    broken["evidence"]["promotion"]["status"] = "absent"
    assert "a verdict needs evidence.promotion verified" in check(broken)


# --- the committed record ------------------------------------------------------------------

RECORD = Path(__file__).resolve().parents[2] / "docs" / "prd" / "v0.5.0" / "ACCEPTANCE_RESULT.json"


def test_committed_record_is_the_passing_verdict() -> None:
    """The committed record is valid and passes against TJ's promotion (R56, v0.4.0 R27)."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["record_schema"] == 1
    assert check(record) == []
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert record["known_limits"] == list(KNOWN_LIMITS)
    assert record["default_suite"]["exit_code"] == 0 and record["default_suite"]["failed"] == 0
    assert record["commands"] and all(c["exit_code"] == 0 for c in record["commands"])
    assert record["evidence"]["promotion"]["status"] == "verified"
    assert record["evidence"]["promotion"]["commit"] == "ccacac5"
    assert record["fixtures"]["transcription_confirmation"]["status"] == "confirmed"
    assert record["regression_bounds"]["recipes"] == REGRESSION_BOUNDS
    t3 = record["fixtures"]["t3"]
    for case in CASES:
        for recipe in RECIPES:
            want = "reported" if (recipe, case) in REPORT_ONLY else "pass"
            assert t3[case][recipe]["regression"]["status"] == want
    assert t3["ts4a"]["xtb"]["report_only"] is True
