r"""Merge the v0.4.0 M1 acceptance files into docs/prd/v0.4.0/ACCEPTANCE_RESULT.json (slice 07).

Usage::

    python3 tests/e2e/acceptance_record_v040.py suite <default_suite.log> <mapping.log> \\
        <default_suite.json>
    python3 tests/e2e/acceptance_record_v040.py merge <acceptance_xtb.json> \\
        <acceptance_uma.json> <commands.json> <default_suite.json> <out.json>

``commands.json`` lists ``{"argv", "env", "exit_code", "wall_s", "log", "summary"}`` per run;
``suite`` derives the ``default_suite`` block from the pytest output logs (never typed by hand).
The record follows v0.3.0's conventions (``record_schema`` 1). Its ``verdict`` is ``pass`` only
when nothing is ``fail``, ``pending_*`` or ``missing`` (R56); before TJ's promotion it is
``pending``.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

ENTRIES = ("graft", "xtb", "uma")
RECIPES = ("xtb", "uma")
VERDICTS = {
    "check": {"pass", "fail"},
    "regression": {"pass", "fail", "pending_promotion"},
    "map_confirmation": {"confirmed", "pending_confirmation", "fail"},
    "test_outcome": {"passed", "failed", "missing"},
    "record": {"pass", "pending", "fail"},
}
KNOWN_LIMITS = (
    "the pure M1 graft keeps four close contacts (two C…H at 1.12 Å, two C…C at 1.96 Å); they are "
    "recorded, not refused, and the pre-relaxation is gated on TS1b_n's connectivity (TJ P1 A)",
    "on M1 the pure-graft junction signs are undetermined (planar pair set); the handedness check "
    "is decided on the relaxed structures (TJ R2 A)",
    "the pre-relaxed structure is a TS guess, not a minimum; it is never ground-state checked",
    "the M1 YAML is provisional until the YAML/JSON graph format is defined (TJ Q-E3)",
    "GraftSpec is self-contained; from v0.8.0 the graph loader builds it from "
    "TemplateGeometry.mapping, the single source (mission R11)",
    "R-group/ligand enumeration stays at v0.7.0 (TJ roadmap B); the Rh(I) (5+2) complexes are v1.x "
    "(TJ Q2 (b))",
)
TOP_KEYS = (
    "record_schema",
    "commit_sha",
    "run_at_utc",
    "hardware",
    "engines",
    "devices",
    "fixture_sha256",
    "commands",
    "logs",
    "default_suite",
    "known_limits",
    "evidence",
    "fixtures",
    "verdict",
    "verdict_reasons",
)
GRAFT_KEYS = ("forming_core_rmsd", "regression_graft", "map_confirmation", "reported")
RECIPE_KEYS = (
    "relaxed_gates",
    "regression_relaxed",
    "metrics",
    "reported",
    "core_max_displacement_angstrom",
)
METRIC_KEYS = {"wall_time_s", "n_steps", "n_engine_calls", "recovery_steps", "device"}


def _states(name: str, entry: dict[str, Any]) -> dict[str, Any]:
    """The verdict-bearing states of one entry."""
    if name == "graft":
        states = {
            "forming_core_rmsd": entry.get("forming_core_rmsd", {}).get("status"),
            "regression_graft": entry.get("regression_graft", {}).get("status"),
            "map_confirmation": entry.get("map_confirmation"),
        }
        for gate, value in sorted(entry.get("tier_d", {}).items()):
            states[f"tier_d.{gate}"] = value.get("status")
        return states
    gates = entry.get("relaxed_gates", {})
    states = {"relaxed_gates": gates.get("status")}
    for gate, value in sorted(gates.items()):
        if isinstance(value, dict):
            states[f"relaxed_gates.{gate}"] = value.get("status")
    states["regression_relaxed"] = entry.get("regression_relaxed", {}).get("status")
    return states


def _suite_failures(name: str, block: dict[str, Any]) -> list[str]:
    """A failing pytest block: non-zero exit code, failed or errors (mission R27 a)."""
    code, failed, errors = block.get("exit_code"), block.get("failed", 0), block.get("errors", 0)
    if code != 0 or failed or errors:
        return [
            f"{name}: exit_code {code}, failed {failed}" + (f", errors {errors}" if errors else "")
        ]
    return []


def _command_failures(commands: list[dict[str, Any]]) -> list[str]:
    """Commands with a non-zero exit code or a reported skip (mission R27 a, c)."""
    reasons = []
    for i, command in enumerate(commands):
        where = f"commands[{i}] {' '.join(command.get('argv', [])[:3])}"
        if command.get("exit_code") != 0:
            reasons.append(f"{where}: exit_code {command.get('exit_code')}")
        skipped = pytest_counts(str(command.get("summary", "")))["skipped"]
        if skipped:
            reasons.append(f"{where}: {skipped} skipped")
    return reasons


def record_verdict(
    fixtures: dict[str, Any],
    default_suite: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The record's verdict (R56, R27).

    ``fail`` on any failed or missing entry or check, a failing default suite or clean-room vector
    run, a command with a non-zero exit code or a skip, or a missing default suite; else
    ``pending`` on any ``pending_*``; else ``pass``.
    """
    failures: list[str] = []
    pending: list[str] = []
    if default_suite is None:
        failures.append("default_suite: missing")
    else:
        failures += _suite_failures("default_suite", default_suite)
        failures += _suite_failures(
            "default_suite.cleanroom_vectors", default_suite.get("cleanroom_vectors", {})
        )
    failures += _command_failures(commands or [])
    m1 = fixtures.get("m1", {})
    for name in ENTRIES:
        entry = m1.get(name, {"test_outcome": "missing"})
        outcome = entry.get("test_outcome")
        if outcome != "passed":
            failed = entry.get("failed_checks", [])
            failures.append(f"m1.{name}: test_outcome {outcome}" + (f" {failed}" if failed else ""))
        if outcome == "missing":
            continue
        for check_name, state in _states(name, entry).items():
            if state == "fail":
                failures.append(f"m1.{name}: {check_name} fail")
            elif str(state).startswith("pending_"):
                pending.append(f"m1.{name}: {check_name} {state}")
    if failures:
        return {"verdict": "fail", "verdict_reasons": failures + pending}
    return {"verdict": "pending" if pending else "pass", "verdict_reasons": pending}


def check(record: dict[str, Any]) -> list[str]:
    """Schema problems of a merged record (empty when valid)."""
    problems = [f"missing {key}" for key in TOP_KEYS if key not in record]
    if record.get("record_schema") != 1:
        problems.append("record_schema is not 1")
    m1 = record.get("fixtures", {}).get("m1", {})
    if set(record.get("fixtures", {})) != {"m1"} or set(m1) != set(ENTRIES):
        problems.append(f"fixtures must be exactly m1.{{graft,xtb,uma}}, got {sorted(m1)}")
    for name in ENTRIES:
        entry = m1.get(name)
        if entry is None:
            problems.append(f"missing fixtures.m1.{name}")
            continue
        if entry.get("test_outcome") not in VERDICTS["test_outcome"]:
            problems.append(f"fixtures.m1.{name}: test_outcome")
        if entry.get("test_outcome") == "missing":
            continue
        for key in GRAFT_KEYS if name == "graft" else RECIPE_KEYS:
            if key not in entry:
                problems.append(f"fixtures.m1.{name}: missing {key}")
        if name == "graft":
            if entry.get("forming_core_rmsd", {}).get("status") not in VERDICTS["check"]:
                problems.append("fixtures.m1.graft: forming_core_rmsd status")
            if entry.get("regression_graft", {}).get("status") not in VERDICTS["regression"]:
                problems.append("fixtures.m1.graft: regression_graft status")
            if entry.get("map_confirmation") not in VERDICTS["map_confirmation"]:
                problems.append("fixtures.m1.graft: map_confirmation")
        else:
            gates = entry.get("relaxed_gates", {})
            if gates.get("status") not in VERDICTS["check"]:
                problems.append(f"fixtures.m1.{name}: relaxed_gates status")
            for gate in (
                "g1_core_frozen",
                "g2_connectivity_equals_ts1b_n",
                "g3_junction_signs_equal_ts1b_n",
            ):
                if gates.get(gate, {}).get("status") not in VERDICTS["check"]:
                    problems.append(f"fixtures.m1.{name}: relaxed_gates.{gate}")
            status = entry.get("regression_relaxed", {}).get("status")
            if status not in VERDICTS["regression"]:
                problems.append(f"fixtures.m1.{name}: regression_relaxed status")
            if not METRIC_KEYS <= set(entry.get("metrics", {})):
                problems.append(f"fixtures.m1.{name}: metrics {sorted(entry.get('metrics', {}))}")
    if list(record.get("known_limits", [])) != list(KNOWN_LIMITS):
        problems.append("known_limits are not the fixed lines")
    suite = record.get("default_suite", {})
    for key in ("command", "exit_code", "passed", "failed", "cleanroom_vectors"):
        if key not in suite:
            problems.append(f"default_suite: missing {key}")
    if record.get("verdict") not in VERDICTS["record"]:
        problems.append("verdict value")
    if record.get("verdict") == "pass":
        files = record.get("evidence", {}).get("promotion", {}).get("files", {})
        if set(files) != set(PROMOTED_FILES) or not all(
            f.get("equals_candidate") for f in files.values()
        ):
            problems.append("a pass verdict needs evidence.promotion for all three promoted files")
    expected = record_verdict(
        record.get("fixtures", {}), record.get("default_suite"), record.get("commands", [])
    )
    stated = {k: record.get(k) for k in expected}
    if stated != expected:
        problems.append(f"verdict {stated} is not the fixtures' verdict {expected}")
    return problems


SUMMARY = re.compile(r"=+ (?P<body>.*?) in [\d.]+s(?: \([\d:]+\))? =+\s*$", re.MULTILINE)


def pytest_counts(log_text: str) -> dict[str, int]:
    """The counts of pytest's final summary line (``passed``, ``failed``, ...)."""
    matches = list(SUMMARY.finditer(log_text))
    if not matches:
        tail = log_text.strip().splitlines()[-1] if log_text.strip() else ""
        body = re.sub(r" in [\d.]+s.*$", "", tail)
    else:
        body = matches[-1].group("body")
    counts = {"passed": 0, "failed": 0, "skipped": 0, "deselected": 0, "errors": 0}
    for number, word in re.findall(r"(\d+) (passed|failed|skipped|deselected|errors?)", body):
        counts["errors" if word.startswith("error") else word] = int(number)
    return counts


def suite_block(suite_log: Path, mapping_log: Path) -> dict[str, Any]:
    """The ``default_suite`` block from the two pytest logs (first line: ``exit_code=<n>``)."""

    def read(path: Path) -> tuple[int, dict[str, int]]:
        text = path.read_text(encoding="utf-8")
        exit_code = int(re.search(r"exit_code=(\d+)", text).group(1))  # type: ignore[union-attr]
        return exit_code, pytest_counts(text)

    code, counts = read(suite_log)
    mapping_code, mapping_counts = read(mapping_log)
    return {
        "command": "uv run pytest",
        "exit_code": code,
        **counts,
        "cleanroom_vectors": {
            "command": "uv run pytest tests/unit/mapping",
            "exit_code": mapping_code,
            **mapping_counts,
        },
    }


def merge_runs(
    runs: dict[str, dict[str, Any]],
    commands: list[dict[str, Any]],
    default_suite: dict[str, Any],
    promotion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the record from the per-recipe acceptance files (already parsed)."""
    shas = {r["commit_sha"] for r in runs.values()}
    if len(shas) != 1 or not all(r["tree_clean"] for r in runs.values()):
        raise ValueError(f"recipes ran at different or unclean commits: {shas}")
    hashes = [json.dumps(r.get("fixture_sha256"), sort_keys=True) for r in runs.values()]
    if len(set(hashes)) != 1:
        raise ValueError("the recipes compared against different promoted fixtures")
    m1: dict[str, Any] = {}
    for name, source in (("graft", "xtb"), ("xtb", "xtb"), ("uma", "uma")):
        entry = dict(runs[source]["fixtures"]["m1"].get(name, {"test_outcome": "missing"}))
        for key in ("fixture", "recipe", "schema"):
            entry.pop(key, None)
        m1[name] = entry
    fixtures = {"m1": m1}
    record = {
        "record_schema": 1,
        "commit_sha": shas.pop(),
        "run_at_utc": max(r["run_at_utc"] for r in runs.values()),
        "hardware": runs["uma"]["hardware"],
        "engines": {recipe: run["engine"] for recipe, run in sorted(runs.items())},
        "devices": {recipe: run["device"] for recipe, run in sorted(runs.items())},
        "fixture_sha256": runs["uma"].get("fixture_sha256", {}),
        "commands": [
            {
                "argv": c["argv"],
                "env": c["env"],
                "exit_code": c["exit_code"],
                "wall_s": c["wall_s"],
                "summary": c["summary"],
            }
            for c in commands
        ],
        "logs": {
            c["log"]: {"exit_code": c["exit_code"], "summary": c["summary"]} for c in commands
        },
        "default_suite": default_suite,
        "known_limits": list(KNOWN_LIMITS),
        "evidence": {
            "candidates_phase3_set": (
                "tests/candidate_outputs/v0.4.0/m1_graft.json, m1_relaxed.xtb.json and "
                "m1_relaxed.uma.json at 035e289 (produced at C1 b872079)"
            ),
            "record_run_candidates": "written to a scratch ETA_RXNCAT_CANDIDATE_DIR, not committed",
            "verdict_run": "slice 08, ETA_RXNCAT_ACCEPTANCE=1, after TJ's Phase 3 promotion (R22)",
            **({"promotion": promotion} if promotion is not None else {}),
        },
        "fixtures": fixtures,
        **record_verdict(fixtures, default_suite, commands),
    }
    problems = check(record)
    if problems:
        raise ValueError(f"record invalid: {problems}")
    return record


PROMOTION_COMMIT = "174a783"
CANDIDATES_COMMIT = "035e289"
PROMOTED_FILES = ("m1_graft.json", "m1_relaxed.uma.json", "m1_relaxed.xtb.json")
TJ_PROMOTION = {
    "queue_row": "qitem-20261123222552-7f2f3da801c4ec2c",
    "answering": "qitem-20261123214530-98591a612a38f5db",
    "relayed_by": "advisor",
    "verbatim": (
        "1. PROMOTED: TJ copied m1_graft.json, m1_relaxed.xtb.json and m1_relaxed.uma.json from "
        "tests/candidate_outputs/v0.4.0/ into tests/fixtures/v0.4.0/ himself … That CONFIRMS THE "
        "ATOM MAP (his P2 A)."
    ),
    "mission_row": "R28",
}
"""TJ's Phase 3 answer as mission R28 quotes it (R27 e)."""


def promotion_evidence(repo: Path) -> dict[str, Any]:
    """R27 (e): TJ's answer, the promotion commit, and per file sha256 and git blob ids.

    The candidates are compared by blob id (``git ls-tree``) only, never read.
    """
    import hashlib
    import subprocess

    def blobs(commit: str, directory: str) -> dict[str, str]:
        out = subprocess.run(
            ["git", "ls-tree", commit, directory + "/"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return {line.split("\t")[1].rsplit("/", 1)[1]: line.split()[2] for line in out.splitlines()}

    promoted = blobs(PROMOTION_COMMIT, "tests/fixtures/v0.4.0")
    candidates = blobs(CANDIDATES_COMMIT, "tests/candidate_outputs/v0.4.0")
    files = {}
    for name in PROMOTED_FILES:
        path = repo / "tests" / "fixtures" / "v0.4.0" / name
        files[name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "blob_id": promoted.get(name),
            "candidate_blob_id": candidates.get(name),
            "equals_candidate": promoted.get(name) is not None
            and promoted.get(name) == candidates.get(name),
        }
    return {
        "tj_answer": TJ_PROMOTION,
        "promotion_commit": PROMOTION_COMMIT,
        "candidates_commit": CANDIDATES_COMMIT,
        "files": files,
    }


def _dump(path: Path, data: Any) -> None:
    text = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    """``suite <log> <mapping-log> <out>`` or ``merge <xtb> <uma> <commands> <suite> <out>``."""
    if len(argv) == 4 and argv[0] == "suite":
        _dump(Path(argv[3]), suite_block(Path(argv[1]), Path(argv[2])))
        print(f"wrote {argv[3]}")
        return 0
    if len(argv) == 6 and argv[0] == "merge":
        runs = {
            "xtb": json.loads(Path(argv[1]).read_text(encoding="utf-8")),
            "uma": json.loads(Path(argv[2]).read_text(encoding="utf-8")),
        }
        record = merge_runs(
            runs,
            json.loads(Path(argv[3]).read_text(encoding="utf-8")),
            json.loads(Path(argv[4]).read_text(encoding="utf-8")),
            promotion_evidence(Path(__file__).resolve().parents[2]),
        )
        _dump(Path(argv[5]), record)
        print(f"wrote {argv[5]}: verdict {record['verdict']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
