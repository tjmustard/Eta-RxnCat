"""Write ``docs/prd/v0.7.1/QUALITY_RESULT.json`` from the v0.7.1 verdict runs (R20, R30).

Standard library only. The record is generated from these sources and never edited by hand:

- the evidence directory of the verdict run: ``default.xml`` and ``integration_x.xml`` (pytest
  junit), ``default.log`` and ``integration_x.log`` (the same runs' terminal output, the only place
  pytest reports the deselected count), and ``verdict_run_sha`` (``git rev-parse HEAD`` at the run);
- the committed ``seam_breaks.json`` of slices 02, 04 and 05;
- the R17 table in slice 08's execute proof (the dead-code verdicts);
- ``pyproject.toml`` (the version).

It exits 1, writing nothing, when a source, an expected test id or a list is missing or empty, or
when a gate fails. The same sources always give the same bytes.
"""

import argparse
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.7.1"
BASE_SHA = "bf7b9497b6d76caaabd2d6544d2e3f704d117919"
OUTPUT = "docs/prd/v0.7.1/QUALITY_RESULT.json"
SLICES = "missions/release-0.7.1/slices"
SEAM_BREAK_SLICES = ("02-tier-o-seams", "04-tier-x-ts-seams", "05-tier-x-selectivity-review")
DEAD_CODE_PROOF = f"{SLICES}/08-dead-code-and-doc-refs/proof/08-execute.md"

OFFLINE = "tests/integration/test_seams_offline.py"
TS = "tests/integration/test_seams_ts_gfn2.py"
SELECTIVITY = "tests/integration/test_seams_selectivity_gfn2.py"

SEAM_TESTS: tuple[tuple[str, str, str], ...] = (
    (f"{OFFLINE}::test_to1_species_runner_store_roundtrip", "O", "species runner, store, thermo"),
    (
        f"{OFFLINE}::test_to2_reaction_energies_replay_from_reopened_store",
        "O",
        "reaction free energy from real runner output",
    ),
    (f"{OFFLINE}::test_to3_conformer_stage_stores_members", "O", "conformers, engine, store"),
    (f"{OFFLINE}::test_to4_enumerator_runs_the_real_graft", "O", "enumerator, graft"),
    (f"{OFFLINE}::test_to5_candidate_graph_file_roundtrip", "O", "candidate graph file, loader"),
    (f"{OFFLINE}::test_to6_enumerated_seed_inputs[TS1a_n]", "O", "enumerated seed inputs"),
    (f"{OFFLINE}::test_to6_enumerated_seed_inputs[TS1a_x]", "O", "enumerated seed inputs"),
    (f"{OFFLINE}::test_plan_loader_parity", "O", "plan loader parity with the E2E loader"),
    (f"{TS}::test_tx1_prfo_validation_thermo_and_replay", "X", "TS runner, P-RFO, GFN2"),
    (f"{TS}::test_tx2_ensemble_sampler_relax_and_store", "X", "TS ensemble, optimizer, store"),
    (f"{TS}::test_tx3_fallback_rank1_chosen_and_replayed", "X", "TS template fallback"),
    (f"{TS}::test_tx3_rank1_face_mismatch", "X", "TS fallback face check"),
    (
        f"{SELECTIVITY}::test_tx4_graph_file_to_selectivity_and_replay",
        "X",
        "graph file, loader, selectivity",
    ),
    (f"{SELECTIVITY}::test_tx5_review_export_round_trip", "X", "review export, reader, bundle"),
)
"""Every seam test: id, tier (O offline, X CPU GFN2) and the seam it guards."""

PARITY_AND_TIER_O = tuple(test_id for test_id, tier, _ in SEAM_TESTS if tier == "O")
TIER_X = tuple(test_id for test_id, tier, _ in SEAM_TESTS if tier == "X")

KNOWN_ISSUES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("R10", "fixed", ("tests/e2e/test_t3_gated_on.py::test_gated_on_text_equals_the_record",)),
    (
        "R11",
        "fixed",
        (
            "tests/unit/test_test_policy.py::test_module_level_skip_scanner",
            "tests/unit/test_test_policy.py::test_teardown_skip_fails_under_acceptance",
        ),
    ),
    (
        "R13/R29",
        "fixed",
        (
            "tests/unit/store/test_first_open.py::test_infinite_open_timeout_opens_a_fresh_store",
            "tests/unit/store/test_first_open.py::test_infinite_open_timeout_waits_for_a_held_lock",
            "tests/unit/store/test_first_open.py::test_infinite_open_timeout_is_clamped_in_sqlite",
            "tests/unit/store/test_first_open.py::test_open_timeout_must_be_a_real_number",
        ),
    ),
    (
        "R14",
        "fixed",
        ("tests/unit/engines/test_mace.py::test_importing_mace_leaves_the_torch_env_as_it_was",),
    ),
    (
        "R28",
        "fixed",
        (
            "tests/unit/tools/test_licence_gate.py::test_bare_bsd_passes_with_the_label",
            "tests/unit/tools/test_licence_gate.py::test_the_repo_maps_bare_bsd_to_the_labelled_id",
        ),
    ),
    (
        "R38",
        "fixed",
        (
            "tests/unit/review/test_export.py::"
            "test_an_infinite_ratio_round_trips_as_the_string_infinity",
        ),
    ),
    ("R39", "fixed", ("tests/unit/review/test_assets.py::test_the_wheel_build_is_offline",)),
    (
        "R40",
        "fixed",
        (
            "tests/unit/review/test_bundle_scans.py::"
            "test_the_host_data_scan_skips_the_pinned_3dmol_file",
        ),
    ),
    ("R15: PotentialResult floats and shallow freeze", "kept", ()),
    ("R12: licence gate unnamed and ambiguous distribution cases", "dropped", ()),
    ("multi-site forming bonds", "deferred", ()),
    ("'+' in library entry ids", "deferred", ()),
    ("run_selectivity priority 1 against priority-2 TS nodes (R35)", "deferred", ()),
    ("geomeTRIC temp-dir and partial-mark edge cases (R41)", "deferred", ()),
    ("HF-13 geomeTRIC pre-relax stall", "deferred", ()),
    ("review page red frequency-failure box", "deferred", ()),
    (
        "R14 limit: the guard wraps only the import of mace; an already-imported mace "
        "is not covered",
        "open",
        ("tests/unit/engines/test_mace.py::test_importing_mace_leaves_the_torch_env_as_it_was",),
    ),
    (
        "GPU analytic Hessian routing: gpu_ks_hessian_class has no cartesian_basis, and the "
        "support record does not cover it",
        "open",
        (),
    ),
    (
        "tests/e2e/v070.py checked_record_text still raises on a non-finite ratio, and its "
        "docstring is stale",
        "open",
        (),
    ),
    (
        "tests/e2e/t3.py: the ENERGY_SOURCE_BOUND_KCAL_MOL docstring follows the wrong constant",
        "open",
        (),
    ),
    (
        "R44 scanner misses: builtins.getattr, objects returned by eta calls, non-constant "
        "module names, patchers passed by other routes",
        "open",
        (),
    ),
)
"""Every known issue of the release: id, verdict and the default-suite tests that prove a fix or
bound an open limit."""


class RecordError(Exception):
    """A source is missing or empty, or a gate failed."""


def read_text(path: Path) -> str:
    """The text of ``path``, refused when it is missing or blank."""
    if not path.is_file():
        raise RecordError(f"missing source: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RecordError(f"empty source: {path}")
    return text


def junit_outcomes(path: Path) -> tuple[dict[str, str], dict[str, int], float]:
    """``(outcome by test id, suite counts, wall seconds)`` of one junit file.

    The outcome is ``passed``, ``failed``, ``error`` or ``skipped``. A test id is
    ``path/to/module.py::name``.
    """
    try:
        root = ET.fromstring(read_text(path))
    except ET.ParseError as error:
        raise RecordError(f"unreadable junit: {path}: {error}") from error
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    outcomes: dict[str, str] = {}
    wall = 0.0
    for suite in suites:
        wall += float(suite.get("time", "0"))
        for case in suite.findall("testcase"):
            test_id = f"{case.get('classname', '').replace('.', '/')}.py::{case.get('name', '')}"
            found = "passed"
            for tag, outcome in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
                if case.find(tag) is not None:
                    found = outcome
                    break
            # a case with a failure and a teardown error is listed twice: keep the bad outcome
            if outcomes.get(test_id, "passed") == "passed":
                outcomes[test_id] = found
    if not outcomes:
        raise RecordError(f"no test cases in {path}")
    counts = {
        key: sum(int(suite.get(attribute, "0")) for suite in suites)
        for key, attribute in (
            ("tests", "tests"),
            ("failed", "failures"),
            ("errors", "errors"),
            ("skipped", "skipped"),
        )
    }
    return outcomes, counts, round(wall, 3)


def summary_count(log: str, word: str) -> int:
    """The ``N <word>`` count of pytest's final summary line (0 when the line omits it)."""
    lines = [line for line in log.splitlines() if re.search(r"\d+ passed.* in [\d.]+s", line)]
    if not lines:
        raise RecordError("no pytest summary line in a run log")
    match = re.search(rf"(\d+) {word}\b", lines[-1])
    return int(match[1]) if match else 0


def suite(evidence: Path, name: str) -> tuple[dict[str, str], dict[str, Any]]:
    """The outcomes and the record block of the suite ``name`` (junit file and run log)."""
    outcomes, counts, wall = junit_outcomes(evidence / f"{name}.xml")
    log = read_text(evidence / f"{name}.log")
    passed = counts["tests"] - counts["failed"] - counts["errors"] - counts["skipped"]
    if summary_count(log, "passed") != passed:
        raise RecordError(f"{name}.log and {name}.xml disagree on the passed count")
    block = {
        "passed": passed,
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "deselected": summary_count(log, "deselected"),
        "errors": counts["errors"],
        "wall_s": wall,
    }
    return outcomes, block


def seam_breaks(root: Path) -> list[dict[str, Any]]:
    """Every row of the three committed ``seam_breaks.json`` files."""
    rows: list[dict[str, Any]] = []
    for name in SEAM_BREAK_SLICES:
        path = root / SLICES / name / "seam_breaks.json"
        breaks = json.loads(read_text(path)).get("breaks")
        if not breaks:
            raise RecordError(f"no breaks in {path}")
        rows.extend(breaks)
    return rows


def dead_code(root: Path) -> dict[str, list[dict[str, str]]]:
    """The removed and kept candidates of slice 08's R17 tables."""
    removed: list[dict[str, str]] = []
    kept: list[dict[str, str]] = []
    for line in read_text(root / DEAD_CODE_PROOF).splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.startswith("|") or not re.fullmatch(r"`[^`]+`", cells[0]):
            continue
        verdict, _, reason = cells[-1].partition(": ")
        if verdict not in ("keep", "remove"):
            continue
        row = {"symbol": cells[0].strip("`"), "reason": reason}
        (kept if verdict == "keep" else removed).append(row)
    if not kept and not removed:
        raise RecordError(f"no R17 rows in {DEAD_CODE_PROOF}")
    return {"removed": removed, "kept": kept}


def matching(outcomes: dict[str, str], test: str) -> dict[str, str]:
    """The outcomes of ``test``: itself, or every parametrised id of it."""
    return {i: o for i, o in outcomes.items() if i == test or i.startswith(f"{test}[")}


def build_record(root: Path, evidence: Path) -> dict[str, Any]:
    """The record from the sources under ``root`` and ``evidence``.

    Raises:
        RecordError: A source is missing or empty, or a gate failed; the message lists every
            failed gate.
    """
    version = tomllib.loads(read_text(root / "pyproject.toml"))["project"]["version"]
    sha = read_text(evidence / "verdict_run_sha").strip()
    default, default_block = suite(evidence, "default")
    tier_x, tier_x_block = suite(evidence, "integration_x")
    breaks = seam_breaks(root)
    dead = dead_code(root)

    problems: list[str] = []
    if version != VERSION:
        problems.append(f"version is {version}, not {VERSION}")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        problems.append(f"verdict_run_sha is not a full sha: {sha!r}")
    for key in ("failed", "errors"):
        if default_block[key]:
            problems.append(f"default suite: {default_block[key]} {key}")
    for key in ("failed", "errors", "skipped"):
        if tier_x_block[key]:
            problems.append(f"Tier X: {tier_x_block[key]} {key}")
    for test_id in PARITY_AND_TIER_O:
        if default.get(test_id) != "passed":
            problems.append(f"default suite: {test_id} is {default.get(test_id, 'missing')}")
    problems.extend(
        f"default suite: integration test {test_id} skipped"
        for test_id, outcome in sorted(default.items())
        if test_id.startswith("tests/integration/") and outcome == "skipped"
    )
    for test_id in TIER_X:
        if tier_x.get(test_id) != "passed":
            problems.append(f"Tier X: {test_id} is {tier_x.get(test_id, 'missing')}")
    for row in breaks:
        if row.get("failed") is not True:
            problems.append(f"seam break did not fail: {row.get('test_id')}")

    tests: list[dict[str, Any]] = []
    for test_id, tier, seam in SEAM_TESTS:
        bare = test_id.split("[", 1)[0]
        rows = [
            {"break": row["break_description"], "failed_test": row["test_id"]}
            for row in breaks
            if row.get("test_id") in (test_id, bare) and row.get("failed") is True
        ]
        if not rows:
            problems.append(f"no failing seam break for {test_id}")
        tests.append({"id": test_id, "tier": tier, "seam": seam, "seam_breaks": rows})

    issues: list[dict[str, Any]] = []
    for issue, verdict, names in KNOWN_ISSUES:
        for name in names:
            found = matching(default, name)
            if not found:
                problems.append(f"known issue {issue}: test missing: {name}")
            problems.extend(
                f"known issue {issue}: {i} is {o}" for i, o in found.items() if o != "passed"
            )
        issues.append({"id": issue, "verdict": verdict, "test": list(names) or None})

    if problems:
        raise RecordError("\n".join(problems))
    return {
        "version": version,
        "base_sha": BASE_SHA,
        "verdict_run_sha": sha,
        "suites": {"default": default_block, "integration_x": tier_x_block},
        "integration_tests": tests,
        "known_issues": issues,
        "dead_code": dead,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Write the record and return 0; print the reasons and return 1 when it cannot be written."""
    parser = argparse.ArgumentParser(description="Write the v0.7.1 QUALITY_RESULT.json.")
    parser.add_argument("--evidence", type=Path, required=True, help="the verdict run directory")
    parser.add_argument("--root", type=Path, default=REPO, help="the repository root")
    parser.add_argument("--output", type=Path, help=f"default: <root>/{OUTPUT}")
    args = parser.parse_args(argv)
    try:
        record = build_record(args.root, args.evidence)
    except RecordError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    output = args.output or args.root / OUTPUT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
