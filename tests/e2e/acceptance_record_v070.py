r"""Derive docs/prd/v0.7.0/ACCEPTANCE_RESULT.json from the v0.7.0 evidence (slice 13, R34).

Usage::

    uv run python tests/e2e/acceptance_record_v070.py <evidence_dir> <slice12_proof.md> \
        <full_pytest.log> <full_pytest_exit_code> <out.json> [<rerun_dir> <fixtures_dir>]

Every value comes from the evidence run records of slices 11 and 12, their proof tables and logs,
the final default-suite log, and the scratch bundle (``<evidence_dir>/v070-slice13/review`` with
``review_report.json`` beside it). Nothing is typed by hand and no candidate output is ever read: a
path below ``tests/candidate_outputs`` is refused. Without ``<rerun_dir>`` the record holds no
verdict (slice 13's record).

With ``<rerun_dir>`` (slice 14: ``candidates/`` holds the rerun's outputs, ``proof/`` its command
logs and time files) and ``<fixtures_dir>`` (TJ's promoted ``tests/fixtures/v0.7.0/``), each rerun
output is compared field by field with its fixture, only the fields in ``VOLATILE`` may differ, and
the record states ``verdict`` from ``record_verdict``.
"""

import json
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from acceptance_record_v040 import pytest_counts
from review_v070 import SLICE11, SLICE12, Source, sha256_of, sources

from eta_rxncat.review import RunRecord
from eta_rxncat.review.run_data import RecordRun

TIMEOUT_REASON = "pre_relax_failed:PreRelaxTimeout"
GRAFT_TIMEOUT_REASON = "graft_pre_relax_timeout"
BUNDLE_PATH = "tests/candidate_outputs/v0.7.0/review/"
ENGINE_NAMES = {"xtb_subprocess": "GFN2", "uma_direct": "UMA"}


RUN_WALL = "a wall time measured by this run"
CACHE_HIT = "the rerun reads the earlier run's rows, so its first pass computes less"
VOLATILE: tuple[tuple[str, str], ...] = (
    (r"commit_sha", "HEAD of the rerun"),
    (r"environment\.run\.eta_rxncat", "installed package metadata version of the venv"),
    (r"reported\.resources\.\w+", "CPU, wall time and peak memory of this run"),
    (r"reported\.(first|second)_pass_wall_time_s", RUN_WALL),
    (r"reported\.stage_metrics\.\w+\.wall_time_s", RUN_WALL),
    (r"(second_pass_)?fallback\.attempts\[\d+\]\.wall_time_s", RUN_WALL),
    (r"runs\[\d+\]\.fallback\.attempts\[\d+\]\.wall_time_s", RUN_WALL),
    (r"reported\.first_pass_(engine_calls|new_rows)", CACHE_HIT),
    (r"reported\.stage_metrics\.\w+\.(engine_calls|cache_hits|rows_created)", CACHE_HIT),
    (r"first_pass_engine_calls_by_template_stage(\.\w+)+", CACHE_HIT),
    (r"checks\.\w+\.engine_calls_attributed\.(attributed|first_pass)", CACHE_HIT),
    (r"checks\.\w+\.rank_1_no_ts_search_calls\.all_calls", CACHE_HIT),
)
"""The only fields of a rerun output that may differ from its fixture, each with the reason."""


class RecordError(ValueError):
    """An input is missing, forbidden, or two sources disagree."""


def refuse_candidates(*paths: Path) -> None:
    """Refuse any input below ``tests/candidate_outputs`` (a candidate is never read back).

    Raises:
        RecordError: Naming the path.
    """
    for path in paths:
        if "candidate_outputs" in path.resolve().parts:
            raise RecordError(f"a candidate output is never an input: {path}")


def _time_exit(path: Path) -> int:
    found = re.search(r"Exit status: (\d+)", path.read_text(encoding="utf-8"))
    if not found:
        raise RecordError(f"no exit status in {path.name}")
    return int(found.group(1))


def command_block(proof: Path, tag: str) -> dict[str, Any]:
    """One slice 11/12 command: its exit code and pytest counts (from the evidence logs).

    Raises:
        RecordError: A log or time file is missing.
    """
    log = proof / f"{tag}.log"
    time_file = proof / f"{tag}.time"
    if not log.is_file() or not time_file.is_file():
        raise RecordError(f"no log or time file for {tag}")
    counts = pytest_counts(log.read_text(encoding="utf-8", errors="replace"))
    return {"tag": tag, "exit_code": _time_exit(time_file), "counts": counts}


def run_values(run: RecordRun) -> dict[str, Any]:
    """The reported values of one run, from its record."""
    ensemble = run.ensemble
    excluded = [] if ensemble is None else list(ensemble.excluded)
    stalls = [e for e in excluded if e.reason == TIMEOUT_REASON]
    graft = [a for a in run.fallback.attempts if a.reason == GRAFT_TIMEOUT_REASON]
    return {
        "n_members": 0 if ensemble is None else len(ensemble.members),
        "exclusions_by_reason": dict(sorted(Counter(e.reason for e in excluded).items())),
        "n_merges": 0 if ensemble is None else len(ensemble.merges),
        "G_pathway_hartree": None if ensemble is None else ensemble.G_pathway_hartree,
        "dG_dagger_kcal_mol": run.dG_dagger_kcal_mol,
        "stall_count": len(stalls),
        "graft_pre_relax_timeouts": len(graft),
        "time_lost_to_stalls_s": sum(e.pre_relax_wall_time_s or 0.0 for e in stalls),
        "stall_cap_reached_bool": run.stall_cap_reached_bool,
        "fallback": [
            {
                "template_id": a.template_id,
                "rank": a.rank,
                "outcome": a.outcome,
                "reason": a.reason,
            }
            for a in run.fallback.attempts
        ],
        "chosen_template_id": run.fallback.chosen_template_id,
    }


def unit_block(name: str, record: RunRecord) -> dict[str, Any]:
    """One single-unit record: its engine, gates and reported values.

    Raises:
        RecordError: The record does not hold exactly one run.
    """
    if len(record.runs) != 1:
        raise RecordError(f"{name} holds {len(record.runs)} runs, expected one")
    (run,) = record.runs
    engine = ENGINE_NAMES[run.engine.name]
    return {
        "record": name,
        "candidate_id": run.candidate_id,
        "pathway": run.pathway,
        "engine": engine,
        "gated": engine == "GFN2",
        "gates": {g.gate_id: "pass" if g.pass_bool else "fail" for g in record.gates},
        "values": run_values(run),
    }


def table_rows(markdown: str) -> dict[str, list[str]]:
    """Markdown table rows keyed by their first cell."""
    rows = {}
    for line in markdown.splitlines():
        if line.startswith("|") and not set(line) <= set("|-: "):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.setdefault(cells[0], cells[1:])
    return rows


def check_slice11_table(units: list[dict[str, Any]], table: str) -> None:
    """Members, stalls, time lost, cap and dG-dagger agree with slice 11's proof table.

    Raises:
        RecordError: A unit is missing from the table or disagrees with it.
    """
    rows = table_rows(table)
    for unit in units:
        key = f"{unit['candidate_id']} {unit['pathway']} {_tag(unit['engine'])}"
        if key not in rows:
            raise RecordError(f"{key} is not in slice 11's proof table")
        cells, values = rows[key], unit["values"]
        stalls = [s.strip() for s in cells[3].split("/")]
        found = (int(cells[1]), int(stalls[0]), round(float(stalls[1])), stalls[2], float(cells[4]))
        expected = (
            values["n_members"],
            values["stall_count"],
            round(values["time_lost_to_stalls_s"]),
            str(values["stall_cap_reached_bool"]),
            round(values["dG_dagger_kcal_mol"], 3),
        )
        if found != expected:
            raise RecordError(f"{key}: proof table {found} differs from the record {expected}")


def check_slice12_proof(units: list[dict[str, Any]], proof: str) -> None:
    """Merges and ``G_pathway`` agree with slice 12's proof ensemble table.

    Raises:
        RecordError: A unit is missing from the table or disagrees with it.
    """
    section = proof.split("### Ensemble gates and values", 1)
    if len(section) != 2:
        raise RecordError("slice 12's proof has no ensemble table")
    rows = table_rows(section[1].split("\n## ", 1)[0])
    for unit in units:
        key = f"{unit['construct']} {unit['engine']}"
        if key not in rows:
            raise RecordError(f"{key} is not in slice 12's proof table")
        cells, values = rows[key], unit["values"]
        found = (int(cells[2]), float(cells[5]))
        expected = (values["n_merges"], round(values["G_pathway_hartree"], 7))
        if found != expected:
            raise RecordError(f"{key}: proof table {found} differs from the record {expected}")


def score_block(name: str, record: RunRecord) -> dict[str, Any]:
    """One selectivity record's ΔΔG‡, ratio and major pathway (reported, never gated)."""
    (scored,) = record.selectivity
    return {
        "record": name,
        "candidate_id": scored.candidate_id,
        "engine": ENGINE_NAMES[scored.engine.name],
        "ddG_dagger_kcal_mol": scored.result.ddG_dagger_kcal_mol,
        "major_pathway": scored.result.major_pathway,
        "ratio": scored.result.ratio,
        "selectivity_percent": scored.result.selectivity_percent,
    }


def bundle_block(evidence: Path) -> dict[str, Any]:
    """The bundle path, its root manifest's sha256 and the build report's counts.

    Raises:
        RecordError: No scratch bundle, or its manifest differs from the report.
    """
    out = evidence / "v070-slice13"
    manifest = out / "review" / "MANIFEST.sha256"
    report_path = out / "review_report.json"
    if not manifest.is_file() or not report_path.is_file():
        raise RecordError("no scratch bundle or build report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    digest = sha256_of(manifest)
    gates = report["gates"]
    if digest != gates["root_manifest_sha256"]:
        raise RecordError("the scratch manifest differs from the build report")
    return {
        "path": BUNDLE_PATH,
        "root_manifest_sha256": digest,
        "files_listed": len(manifest.read_text(encoding="utf-8").splitlines()),
        "engine_calls": report["engine_calls"],
        "sub_bundle_bytes": gates["sub_bundle_bytes"],
        "total_bytes": gates["total_bytes"],
        "gate_counts": report["gate_counts"],
        "rows_per_store": {
            name: {"before": s["rows_before"], "after": s["rows_after"]}
            for name, s in report["stores"].items()
        },
    }


def differing_paths(rerun: Any, fixture: Any, path: str = "") -> list[str]:
    """The dotted paths where two JSON documents differ (a missing key or item is a difference).

    Values must also have the same type, so ``1`` differs from ``1.0`` and from ``True``.
    """
    if isinstance(rerun, dict) and isinstance(fixture, dict):
        found = []
        for key in sorted(set(rerun) | set(fixture)):
            child = f"{path}.{key}" if path else key
            if key not in rerun or key not in fixture:
                found.extend(_leaves(rerun.get(key, fixture.get(key)), child))
            else:
                found.extend(differing_paths(rerun[key], fixture[key], child))
        return found
    if isinstance(rerun, list) and isinstance(fixture, list) and len(rerun) == len(fixture):
        return [
            p
            for i, (a, b) in enumerate(zip(rerun, fixture, strict=True))
            for p in differing_paths(a, b, f"{path}[{i}]")
        ]
    return [] if type(rerun) is type(fixture) and rerun == fixture else [path]


def _leaves(value: Any, path: str) -> list[str]:
    """Every leaf path below a value present on one side only (an empty mapping is a leaf)."""
    if isinstance(value, dict) and value:
        return [p for k, v in sorted(value.items()) for p in _leaves(v, f"{path}.{k}")]
    return [path]


def volatile_reason(path: str) -> str | None:
    """The reason ``path`` may differ from its fixture, or ``None`` when it must be equal."""
    return next((why for pattern, why in VOLATILE if re.fullmatch(pattern, path)), None)


def compare_fixture(rerun: Path, fixture: Path) -> dict[str, Any]:
    """One rerun output against its fixture: ``pass`` only if every difference is volatile."""
    paths = differing_paths(json.loads(rerun.read_bytes()), json.loads(fixture.read_bytes()))
    unexpected = [p for p in paths if volatile_reason(p) is None]
    return {
        "status": "fail" if unexpected else "pass",
        "fixture_sha256": sha256_of(fixture),
        "unexpected": unexpected,
        "volatile": [p for p in paths if p not in unexpected],
    }


def regression_block(rerun: Path, fixtures: Path, expected: list[str]) -> dict[str, Any]:
    """Every fixture compared with the rerun output of the same name.

    Raises:
        RecordError: The fixtures or the rerun outputs are not exactly the expected files.
    """
    for what, folder in (("fixtures", fixtures), ("rerun outputs", rerun / "candidates")):
        found = {p.name for p in folder.glob("*.json")}
        if found != set(expected):
            raise RecordError(f"{what} are not the expected files: {sorted(found ^ set(expected))}")
    return {n: compare_fixture(rerun / "candidates" / n, fixtures / n) for n in expected}


def command_tag(stem: str) -> str:
    """The command tag of a fixture stem (a ``selectivity`` stem is a score command)."""
    if stem.startswith("v070_fallback_"):
        construct, engine = stem.removeprefix("v070_fallback_").rsplit("_", 1)
        return f"{construct.replace('_', '-')}-{engine}"
    r_group, pathway, engine = stem.removeprefix("v070_enum_").split("_")
    if pathway == "selectivity":
        return f"score-{r_group}-{engine}"
    return f"{r_group}-{pathway}-{engine}"


def rerun_unit(path: Path) -> dict[str, Any]:
    """What one rerun unit gated, and what it computed (cache use is reported, not gated)."""
    payload = json.loads(path.read_bytes())
    reported = payload["reported"]
    gates = payload["checks"].get("tier_gates") or payload["checks"]["reported_gates"]
    return {
        "case": payload["case"],
        "engine": {"xtb": "GFN2", "uma": "UMA"}[payload["recipe"]],
        "gated": payload["recipe"] == "xtb",
        "commit_sha": payload["commit_sha"],
        "gates": {name: g["status"] for name, g in sorted(gates.items())},
        "first_pass_engine_calls": reported["first_pass_engine_calls"],
        "first_pass_new_rows": reported["first_pass_new_rows"],
        "second_pass_engine_calls": reported["second_pass_engine_calls"],
        "second_pass_new_rows": reported["second_pass_new_rows"],
    }


def verdict_block(
    rerun: Path, fixtures: Path, units: list[str], scores: list[str]
) -> dict[str, Any]:
    """The verdict rerun: its commands, unit gates, cache use and fixture comparison.

    ``units`` are the fixture stems of the G7 and G8 units, ``scores`` those of the scores.

    Raises:
        RecordError: A missing log or output, or a file that has no counterpart.
    """
    stems = [*units, *scores]
    expected = sorted(f"{s}{suffix}" for s in stems for suffix in (".json", ".runrecord.json"))
    regression = regression_block(rerun, fixtures, expected)
    return {
        "commands": [command_block(rerun / "proof", command_tag(s)) for s in stems],
        "units": [rerun_unit(rerun / "candidates" / f"{s}.json") for s in units],
        "volatile_fields": [{"pattern": p, "reason": r} for p, r in VOLATILE],
        "regression": regression,
    }


def record_verdict(record: Mapping[str, Any]) -> dict[str, Any]:
    """The verdict rule, from the record alone: ``pass`` or ``fail`` with the reasons.

    ``fail`` on: a default suite with a non-zero exit, a failure, an error or no pass; no rerun
    command, or one with a non-zero exit, a failure, an error, a skip or no pass; no gated (GFN2)
    unit, or a gated unit with a gate that is not ``pass``; no fixture comparison, or one that is
    not ``pass``. UMA gates are reported, never gated.
    """
    reasons = []
    suite = record["suites"]["default_suite"]
    counts = suite["counts"]
    if suite["exit_code"] or counts["failed"] or counts["errors"] or not counts["passed"]:
        reasons.append(f"default_suite: exit {suite['exit_code']}, {counts}")
    run = record.get("verdict_run", {})
    commands = run.get("commands", [])
    if not commands:
        reasons.append("commands: none recorded")
    for command in commands:
        found = command["counts"]
        bad = command["exit_code"] or found["failed"] or found["errors"] or found["skipped"]
        if bad or not found["passed"]:
            reasons.append(f"command {command['tag']}: exit {command['exit_code']}, {found}")
    gated = [u for u in run.get("units", []) if u["gated"]]
    if not gated:
        reasons.append("units: no gated unit")
    reasons.extend(
        f"{unit['case']}.{name}: {status}"
        for unit in gated
        for name, status in unit["gates"].items()
        if status != "pass"
    )
    regression = run.get("regression", {})
    if not regression:
        reasons.append("regression: none recorded")
    reasons.extend(
        f"regression {name}: {entry['status']}"
        for name, entry in regression.items()
        if entry["status"] != "pass"
    )
    return {"verdict": "fail" if reasons else "pass", "verdict_reasons": reasons}


def _records(source: Source) -> Mapping[str, RunRecord]:
    return {n: RunRecord.model_validate_json(p.read_bytes()) for n, p in source.records.items()}


def build_record(
    evidence: Path,
    slice12_proof: Path,
    full_log: Path,
    full_exit: int,
    rerun: Path | None = None,
    fixtures: Path | None = None,
) -> dict[str, Any]:
    """Derive the whole record; ``rerun`` and ``fixtures`` together add the verdict.

    Raises:
        RecordError: A missing, forbidden or disagreeing input.
    """
    if (rerun is None) != (fixtures is None):
        raise RecordError("the verdict needs both a rerun directory and a fixtures directory")
    verdict_inputs = [p for p in (rerun, fixtures) if p is not None]
    refuse_candidates(evidence, slice12_proof, full_log, *verdict_inputs)
    found = sources(evidence)
    (first,) = [s for s in found if s.slice_name == SLICE11]
    g7, scores = [], []
    for name, record in sorted(_records(first).items()):
        if record.selectivity:
            scores.append(score_block(name, record))
        else:
            g7.append(unit_block(name, record))
    g8 = []
    for source in (s for s in found if s.slice_name == SLICE12):
        ((name, record),) = _records(source).items()
        construct = source.store.stem.removeprefix("v070_fallback_").rsplit("_", 1)[0]
        block = unit_block(name, record)
        block["construct"] = construct
        block["graft_records"] = [
            {"template_id": r.template_id, "status": r.status, "reason": r.reason}
            for c in record.candidates
            for r in c.records
        ]
        g8.append(block)
    first_proof = evidence / "v070-slice11" / "proof"
    check_slice11_table(g7, (first_proof / "table.md").read_text(encoding="utf-8"))
    check_slice12_proof(g8, slice12_proof.read_text(encoding="utf-8"))
    commands = [
        command_block(first_proof, f"{u['candidate_id']}-{u['pathway']}-{_tag(u['engine'])}")
        for u in g7
    ] + [
        command_block(first_proof, f"score-{s['candidate_id']}-{_tag(s['engine'])}") for s in scores
    ]
    commands += [
        command_block(
            evidence / "v070-slice12" / "proof",
            f"{u['construct'].replace('_', '-')}-{_tag(u['engine'])}",
        )
        for u in g8
    ]
    suite = pytest_counts(full_log.read_text(encoding="utf-8", errors="replace"))
    units = [*g7, *g8]
    record: dict[str, Any] = {
        "version": "0.7.0",
        "derived_by": "tests/e2e/acceptance_record_v070.py",
        "g7_units": g7,
        "g7_selectivity": scores,
        "g8_constructs": g8,
        "stalls": {
            "count": sum(u["values"]["stall_count"] for u in units),
            "time_lost_s": sum(u["values"]["time_lost_to_stalls_s"] for u in units),
            "graft_pre_relax_timeouts": sum(u["values"]["graft_pre_relax_timeouts"] for u in units),
        },
        "suites": {
            "engine_commands": commands,
            "default_suite": {"command": "uv run pytest", "exit_code": full_exit, "counts": suite},
        },
        "bundle": bundle_block(evidence),
    }
    if rerun is None or fixtures is None:
        return record
    record["verdict_run"] = verdict_block(
        rerun,
        fixtures,
        [u["record"].removesuffix(".runrecord.json") for u in units],
        [s["record"].removesuffix(".runrecord.json") for s in scores],
    )
    record.update(record_verdict(record))
    return record


def _tag(engine: str) -> str:
    return {"GFN2": "xtb", "UMA": "uma"}[engine]


def main(argv: list[str]) -> int:
    """Write the record; return 0, or 2 on a usage error."""
    if len(argv) not in (5, 7):
        print(__doc__, file=sys.stderr)
        return 2
    evidence, proof, log, exit_code, out = argv[:5]
    verdict_inputs = [Path(a) for a in argv[5:]]
    record = build_record(Path(evidence), Path(proof), Path(log), int(exit_code), *verdict_inputs)
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    stated = record.get("verdict", "none (no rerun)")
    print(f"wrote {target}; verdict {stated}; reasons {record.get('verdict_reasons')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
