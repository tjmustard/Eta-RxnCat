r"""Merge the per-recipe acceptance files into docs/prd/v0.3.0/ACCEPTANCE_RESULT.json (slice 09).

Usage::

    python -m tests.e2e.acceptance_record merge <acceptance_xtb.json> <acceptance_uma.json> \\
        <commands.json> <out.json>

``commands.json`` lists ``{"argv", "env", "exit_code", "wall_s", "log"}`` per acceptance run.
The record follows the v0.2.0 GPU_SMOKE_RESULT.json conventions (record_schema 1).
"""

import json
import sys
from pathlib import Path
from typing import Any

FIXTURES = ("hf1_butane", "hf2_diels_alder", "e2e5_t1", "e2e5_t2")
RECIPES = ("xtb", "uma")
VERDICTS = {
    "regression": {"pass", "fail", "pending_promotion"},
    "accuracy": {"pass", "fail", "reported", "pending_reference"},
    "smiles_confirmation": {"confirmed", "pending_confirmation", "fail"},
}

FIXED_LIMITS = (
    "accuracy compares per-conformer quantities; our G is Grimme quasi-RRHO (ω₀ 100 cm⁻¹), the "
    "reference pure RRHO (≤ 0.01 kcal/mol on these Δ values per its README); the ensemble ΔG_r "
    "differs from the per-conformer ΔG_r by `dG_r_ensemble_minus_lowest` (reported).",
    "a non-deterministic engine failure stays cached as a completed failure row until "
    "`invalidate`; it is not retried under the same key (R50)",
)


OUTCOMES = {"passed", "failed", "missing"}


def missing(entry: dict[str, Any]) -> bool:
    """A fixture x recipe whose test raised before writing its fragment (R56)."""
    return entry.get("test_outcome") == "missing"


def record_verdict(fixtures: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """R56: ``pass`` only if every fixture x recipe passed; nothing failed, pending or missing."""
    reasons = []
    for name in FIXTURES:
        for recipe in RECIPES:
            entry = fixtures.get(name, {}).get(recipe, {"test_outcome": "missing"})
            where = f"{name}.{recipe}"
            outcome = entry.get("test_outcome")
            if outcome != "passed":
                failed = entry.get("failed_checks", [])
                reasons.append(
                    f"{where}: test_outcome {outcome}" + (f" {failed}" if failed else "")
                )
            if missing(entry):
                continue
            states = {
                "regression": entry.get("regression", {}).get("status"),
                "accuracy": entry.get("accuracy", {}).get("verdict"),
            }
            if "smiles_confirmation" in entry:
                states["smiles_confirmation"] = entry["smiles_confirmation"]
            for check_name, state in states.items():
                if state == "fail" or str(state).startswith("pending_"):
                    reasons.append(f"{where}: {check_name} {state}")
    return {"verdict": "fail" if reasons else "pass", "verdict_reasons": reasons}


def known_limits(fixtures: dict[str, dict[str, Any]]) -> list[str]:
    """R26: reported deviations only (never a gated failure), plus the fixed lines."""
    limits = list(FIXED_LIMITS)
    t2 = fixtures["e2e5_t2"]
    xtb, uma = t2["xtb"], t2["uma"]
    if missing(xtb) or missing(uma):
        return limits
    if not xtb["window"]["inside"]:
        low, high = xtb["window"]["bounds_kcal_mol"]
        limits.append(
            f"GFN2 (xtb recipe) T2 ΔG_r(1 M) = {xtb['dG_r_1M_kcal_mol']:.2f} kcal/mol lies outside "
            f'TJ\'s window ({low}, {high}); reported, not gated (TJ Q-E5 "C"); UMA gives '
            f"{uma['dG_r_1M_kcal_mol']:.2f}, inside and gated. TJ's escalation rule, verbatim: "
            '"Q5. C, if it turns out MACE, UMA, or OMol25 are needed then they should become '
            'standard." The default recipe stays GFN2 until TJ decides.'
        )
    for name in ("hf1_butane", "hf2_diels_alder"):
        deltas = fixtures[name]["xtb"].get("accuracy", {}).get("deltas", [])
        gating = [d for d in deltas if d["level"].startswith("wb97mv")]
        if gating:
            parts = ", ".join(f"{d['quantity']} {d['delta']:+.2f}" for d in gating)
            limits.append(
                f"GFN2 (xtb recipe) {name} vs TJ's ωB97M-V reference values (deltas, kcal/mol or "
                f"percent; reported, xtb is never gated): {parts}"
            )
    return limits


def check(record: dict[str, Any]) -> list[str]:
    """Schema problems of a merged record (empty when valid)."""
    problems = []
    for key in (
        "record_schema",
        "commit_sha",
        "run_at_utc",
        "hardware",
        "commands",
        "logs",
        "known_limits",
        "evidence",
        "fixtures",
    ):
        if key not in record:
            problems.append(f"missing {key}")
    for name in FIXTURES:
        for recipe in RECIPES:
            entry = record.get("fixtures", {}).get(name, {}).get(recipe)
            if entry is None:
                problems.append(f"missing fixtures.{name}.{recipe}")
                continue
            if entry.get("test_outcome", "passed") not in OUTCOMES:
                problems.append(f"fixtures.{name}.{recipe}: test_outcome")
            if missing(entry):
                continue
            for key in (
                "stages",
                "species",
                "optimizer_steps_total",
                "recovery_steps",
                "device",
                "regression",
                "accuracy",
                "failures",
            ):
                if key not in entry:
                    problems.append(f"fixtures.{name}.{recipe}: missing {key}")
            for stage in ("conformer_search", "geometry_opt", "frequency", "single_point"):
                metrics = entry.get("stages", {}).get(stage, {})
                if set(metrics) != {"wall_time_s", "engine_calls", "cache_hits"}:
                    problems.append(
                        f"fixtures.{name}.{recipe}: stage {stage} metrics {sorted(metrics)}"
                    )
            if entry.get("regression", {}).get("status") not in VERDICTS["regression"]:
                problems.append(f"fixtures.{name}.{recipe}: regression verdict")
            if entry.get("accuracy", {}).get("verdict") not in VERDICTS["accuracy"]:
                problems.append(f"fixtures.{name}.{recipe}: accuracy verdict")
            if (
                name.startswith("e2e5")
                and entry.get("smiles_confirmation") not in VERDICTS["smiles_confirmation"]
            ):
                problems.append(f"fixtures.{name}.{recipe}: smiles_confirmation")
            if name in ("hf2_diels_alder", "e2e5_t2"):
                for key in ("incremental_solvation", "species_stage_cache"):
                    if key not in entry:
                        problems.append(f"fixtures.{name}.{recipe}: missing {key}")
            if name == "hf2_diels_alder" and "dG_r_ensemble_minus_lowest_kcal_mol" not in entry:
                problems.append(f"fixtures.{name}.{recipe}: missing dG_r_ensemble_minus_lowest")
    if "verdict" in record:
        expected = record_verdict(record.get("fixtures", {}))
        stated = {k: record.get(k) for k in expected}
        if stated != expected:
            problems.append(f"verdict {stated} is not the fixtures' verdict {expected}")
    return problems


def merge(xtb_path: Path, uma_path: Path, commands_path: Path) -> dict[str, Any]:
    """Build the record from both recipe files and the command list."""
    runs = {"xtb": json.loads(xtb_path.read_text()), "uma": json.loads(uma_path.read_text())}
    return merge_runs(runs, json.loads(commands_path.read_text()))


def merge_runs(runs: dict[str, dict[str, Any]], commands: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the record from the per-recipe acceptance files (already parsed)."""
    shas = {r["commit_sha"] for r in runs.values()}
    if len(shas) != 1 or not all(r["tree_clean"] for r in runs.values()):
        raise ValueError(f"recipes ran at different or unclean commits: {shas}")
    fixtures: dict[str, dict[str, Any]] = {name: {} for name in FIXTURES}
    for recipe, run in runs.items():
        for name in FIXTURES:
            entry = dict(run["fixtures"].get(name, {"test_outcome": "missing"}))
            entry.pop("fixture", None)
            entry.pop("recipe", None)
            entry.pop("schema", None)
            fixtures[name][recipe] = entry
    record = {
        "record_schema": 1,
        "commit_sha": shas.pop(),
        "run_at_utc": max(r["run_at_utc"] for r in runs.values()),
        "hardware": runs["uma"]["hardware"],
        "engines": {recipe: run["engine"] for recipe, run in runs.items()},
        "devices": {recipe: run["device"] for recipe, run in runs.items()},
        "commands": [
            {"argv": c["argv"], "env": c["env"], "exit_code": c["exit_code"], "wall_s": c["wall_s"]}
            for c in commands
        ],
        "logs": {
            c["log"]: {"exit_code": c["exit_code"], "summary": c["summary"]} for c in commands
        },
        "known_limits": known_limits(fixtures),
        "evidence": {
            "candidates_phase3_set": {
                "hf": "tests/candidate_outputs/v0.3.0/hf1_butane.{xtb,uma}.json and "
                "hf2_diels_alder.{xtb,uma}.json at e24777d",
                "reference_values": (
                    "tests/candidate_outputs/v0.3.0/reference_values.json at 32ee699"
                ),
                "t2_and_smiles": "e2e5_t2.{xtb,uma}.json and e2e5_smiles.json at 1c06fc6",
                "t1": "e2e5_t1.{xtb,uma}.json at 1e3d4e9",
            },
            "record_run_candidates": "written to a scratch ETA_RXNCAT_CANDIDATE_DIR, not committed",
            "verdict_run": "slice 10, ETA_RXNCAT_ACCEPTANCE=1, after TJ's Phase 3 promotion (R22)",
        },
        "fixtures": fixtures,
        **record_verdict(fixtures),
    }
    problems = check(record)
    if problems:
        raise ValueError(f"record invalid: {problems}")
    return record


def main(argv: list[str]) -> int:
    """``merge <xtb> <uma> <commands> <out>``."""
    if len(argv) != 5 or argv[0] != "merge":
        print(__doc__)
        return 2
    record = merge(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    text = json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    Path(argv[4]).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {argv[4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
