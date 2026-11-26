r"""Derive docs/prd/v0.7.0/ACCEPTANCE_RESULT.json from the v0.7.0 evidence (slice 13, R34).

Usage::

    uv run python tests/e2e/acceptance_record_v070.py <evidence_dir> <slice12_proof.md> \
        <full_pytest.log> <full_pytest_exit_code> <out.json>

Every value comes from the evidence run records of slices 11 and 12, their proof tables and logs,
the final default-suite log, and the scratch bundle (``<evidence_dir>/v070-slice13/review`` with
``review_report.json`` beside it). Nothing is typed by hand and no candidate output is ever read: a
path below ``tests/candidate_outputs`` is refused. The record holds no verdict (slice 14's).
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


def _records(source: Source) -> Mapping[str, RunRecord]:
    return {n: RunRecord.model_validate_json(p.read_bytes()) for n, p in source.records.items()}


def build_record(
    evidence: Path, slice12_proof: Path, full_log: Path, full_exit: int
) -> dict[str, Any]:
    """Derive the whole record.

    Raises:
        RecordError: A missing, forbidden or disagreeing input.
    """
    refuse_candidates(evidence, slice12_proof, full_log)
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
    return {
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


def _tag(engine: str) -> str:
    return {"GFN2": "xtb", "UMA": "uma"}[engine]


def main(argv: list[str]) -> int:
    """Write the record; return 0, or 2 on a usage error."""
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    evidence, proof, log, exit_code, out = argv
    record = build_record(Path(evidence), Path(proof), Path(log), int(exit_code))
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
