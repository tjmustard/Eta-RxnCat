"""``tools/quality_record_v071.py`` fails closed on missing sources and failed gates (R20, R30)."""

import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any
from xml.sax.saxutils import quoteattr

import pytest

REPO = Path(__file__).parents[3]
SCRIPT = REPO / "tools" / "quality_record_v071.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("quality_record_v071", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = _load()


def write_suite(evidence: Path, name: str, outcomes: dict[str, str], deselected: int = 3) -> None:
    """A junit file and a run log for ``outcomes`` (id to passed, failed, error or skipped)."""
    cases = []
    for test_id, outcome in outcomes.items():
        module, test = test_id.split("::", 1)
        classname = module.removesuffix(".py").replace("/", ".")
        tag = {"passed": "", "failed": "<failure/>", "error": "<error/>", "skipped": "<skipped/>"}
        cases.append(
            f"<testcase classname={quoteattr(classname)} name={quoteattr(test)}>"
            f"{tag[outcome]}</testcase>"
        )
    found = list(outcomes.values())
    (evidence / f"{name}.xml").write_text(
        f'<testsuites><testsuite tests="{len(found)}" failures="{found.count("failed")}" '
        f'errors="{found.count("error")}" skipped="{found.count("skipped")}" time="1.5">'
        f"{''.join(cases)}</testsuite></testsuites>",
        encoding="utf-8",
    )
    (evidence / f"{name}.log").write_text(
        f"{found.count('passed')} passed, {deselected} deselected in 1.50s\n", encoding="utf-8"
    )


def default_outcomes() -> dict[str, str]:
    """Every id the default-suite gates need, all passing."""
    ids = list(TOOL.PARITY_AND_TIER_O)
    ids += [name for _, _, names in TOOL.KNOWN_ISSUES for name in names]
    return dict.fromkeys(ids, "passed")


@pytest.fixture
def sources(tmp_path: Path) -> tuple[Path, Path]:
    """A complete synthetic ``(root, evidence)`` whose gates all pass."""
    root, evidence = tmp_path / "root", tmp_path / "evidence"
    evidence.mkdir(parents=True)
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nversion = "0.7.1"\n', encoding="utf-8")
    (evidence / "verdict_run_sha").write_text("a" * 40 + "\n", encoding="utf-8")
    write_suite(evidence, "default", default_outcomes())
    write_suite(evidence, "integration_x", dict.fromkeys(TOOL.TIER_X, "passed"))
    by_slice = {
        TOOL.SEAM_BREAK_SLICES[0]: TOOL.PARITY_AND_TIER_O,
        TOOL.SEAM_BREAK_SLICES[1]: [i for i in TOOL.TIER_X if "_ts_gfn2" in i],
        TOOL.SEAM_BREAK_SLICES[2]: [i for i in TOOL.TIER_X if "_selectivity_" in i],
    }
    for name, ids in by_slice.items():
        folder = root / TOOL.SLICES / name
        folder.mkdir(parents=True)
        rows = [
            {"test_id": i.split("[")[0], "break_description": f"break {i}", "failed": True}
            for i in ids
        ]
        (folder / "seam_breaks.json").write_text(json.dumps({"breaks": rows}), encoding="utf-8")
    proof = root / TOOL.DEAD_CODE_PROOF
    proof.parent.mkdir(parents=True)
    proof.write_text(
        "| symbol | verdict |\n|---|---|\n| `kept_one` | keep: referenced |\n", encoding="utf-8"
    )
    return root, evidence


def run(root: Path, evidence: Path) -> subprocess.CompletedProcess[str]:
    """Run the script on the synthetic sources."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--evidence", str(evidence)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_sources_write_the_same_bytes_twice(sources: tuple[Path, Path]) -> None:
    """All gates pass: exit 0, the R20 keys, and equal bytes from equal sources."""
    root, evidence = sources
    output = root / TOOL.OUTPUT
    first = run(root, evidence)
    assert first.returncode == 0, first.stderr
    written = output.read_bytes()
    assert run(root, evidence).returncode == 0
    assert output.read_bytes() == written
    record: dict[str, Any] = json.loads(written)
    assert list(record) == [
        "version",
        "base_sha",
        "verdict_run_sha",
        "suites",
        "integration_tests",
        "known_issues",
        "dead_code",
    ]
    assert record["suites"]["default"]["deselected"] == 3
    assert [t["id"] for t in record["integration_tests"]] == [t[0] for t in TOOL.SEAM_TESTS]
    assert record["dead_code"] == {
        "removed": [],
        "kept": [{"symbol": "kept_one", "reason": "referenced"}],
    }


MISSING = [
    "evidence/default.xml",
    "evidence/default.log",
    "evidence/integration_x.xml",
    "evidence/integration_x.log",
    "evidence/verdict_run_sha",
    "root/pyproject.toml",
    *[f"root/{TOOL.SLICES}/{name}/seam_breaks.json" for name in TOOL.SEAM_BREAK_SLICES],
    f"root/{TOOL.DEAD_CODE_PROOF}",
]


@pytest.mark.parametrize("empty", [False, True], ids=["missing", "empty"])
@pytest.mark.parametrize("relative", MISSING)
def test_a_missing_or_empty_source_fails(
    sources: tuple[Path, Path], relative: str, empty: bool
) -> None:
    """Each source, removed or blanked, gives exit 1 and writes no record."""
    root, evidence = sources
    path = root.parent / relative
    if empty:
        path.write_text("", encoding="utf-8")
    else:
        path.unlink()
    result = run(root, evidence)
    assert result.returncode == 1 and path.name in result.stderr, result.stderr
    assert not (root / TOOL.OUTPUT).exists()


def _suite_edit(name: str, change: Callable[[dict[str, str]], None]) -> Callable[..., None]:
    def edit(root: Path, evidence: Path) -> None:
        outcomes = default_outcomes() if name == "default" else dict.fromkeys(TOOL.TIER_X, "passed")
        change(outcomes)
        write_suite(evidence, name, outcomes)

    return edit


def _breaks_edit(change: Callable[[list[dict[str, Any]]], None]) -> Callable[..., None]:
    def edit(root: Path, evidence: Path) -> None:
        path = root / TOOL.SLICES / TOOL.SEAM_BREAK_SLICES[0] / "seam_breaks.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data["breaks"])
        path.write_text(json.dumps(data), encoding="utf-8")

    return edit


TIER_O_ID = TOOL.PARITY_AND_TIER_O[0]
ISSUE_ID = TOOL.KNOWN_ISSUES[0][2][0]

GATES: dict[str, Callable[..., None]] = {
    "default-failure": _suite_edit("default", lambda o: o.update({"t/x.py::t": "failed"})),
    "default-error": _suite_edit("default", lambda o: o.update({"t/x.py::t": "error"})),
    "tier-o-missing": _suite_edit("default", lambda o: o.pop(TIER_O_ID)),
    "integration-skip": _suite_edit(
        "default", lambda o: o.update({"tests/integration/test_x.py::t": "skipped"})
    ),
    "tier-x-skip": _suite_edit("integration_x", lambda o: o.update({TOOL.TIER_X[0]: "skipped"})),
    "tier-x-missing": _suite_edit("integration_x", lambda o: o.pop(TOOL.TIER_X[0])),
    "known-issue-missing": _suite_edit("default", lambda o: o.pop(ISSUE_ID)),
    "known-issue-skipped": _suite_edit("default", lambda o: o.update({ISSUE_ID: "skipped"})),
    "break-did-not-fail": _breaks_edit(lambda rows: rows[0].update(failed=False)),
    "test-without-break": _breaks_edit(lambda rows: rows.pop(0)),
    "empty-break-list": _breaks_edit(lambda rows: rows.clear()),
}


@pytest.mark.parametrize("gate", list(GATES))
def test_a_failed_gate_writes_nothing(sources: tuple[Path, Path], gate: str) -> None:
    """Each failed gate gives exit 1 and writes no record."""
    root, evidence = sources
    GATES[gate](root, evidence)
    result = run(root, evidence)
    assert result.returncode == 1 and result.stderr.startswith("error: "), result.stderr
    assert not (root / TOOL.OUTPUT).exists()
