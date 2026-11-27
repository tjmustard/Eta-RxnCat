"""Tests for the test policy: markers, offline hubs, acceptance skip-to-fail (slices 01, 04)."""

import ast
import os
import tomllib
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

ROOT = Path(__file__).resolve().parents[2]
CONFTEST = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
DESELECTED_MARKERS = ("gpu", "xtb", "mlip_mace", "mlip_uma", "slow", "acceptance", "e2e")
DEFAULT_SELECTED_MARKERS = ("integration",)

SKIPPING_TEST = """
import pytest

def test_skips():
    pytest.skip("x-reason-for-skip")
"""

SETUP_SKIP_TEST = """
import pytest

@pytest.fixture
def needs_tool():
    pytest.skip("tool-missing-in-setup")

def test_uses_tool(needs_tool):
    pass
"""


def run_inner(pytester: pytest.Pytester, source: str) -> pytest.RunResult:
    """Run ``source`` as an inner session that loads the project's real conftest."""
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(source)
    return pytester.runpytest_inprocess("-rA")


def test_skip_stays_skip_without_variable(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without ETA_RXNCAT_ACCEPTANCE a skipping test is a skip and the run exits 0."""
    monkeypatch.delenv("ETA_RXNCAT_ACCEPTANCE", raising=False)
    result = run_inner(pytester, SKIPPING_TEST)
    assert result.ret == 0
    result.assert_outcomes(skipped=1)


@pytest.mark.parametrize("value", ["0", "", "true", "yes"])
def test_only_exact_one_enables_switch(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Only the exact value "1" turns skips into failures."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", value)
    result = run_inner(pytester, SKIPPING_TEST)
    assert result.ret == 0
    result.assert_outcomes(skipped=1)


def test_call_skip_fails_under_acceptance(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under ETA_RXNCAT_ACCEPTANCE=1 a skip in the call phase fails, showing the reason."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    result = run_inner(pytester, SKIPPING_TEST)
    assert result.ret == 1
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*ETA_RXNCAT_ACCEPTANCE=1*x-reason-for-skip*"])


def test_setup_skip_fails_under_acceptance(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Under ETA_RXNCAT_ACCEPTANCE=1 a skip raised in a fixture (setup) also fails."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    result = run_inner(pytester, SETUP_SKIP_TEST)
    assert result.ret == 1
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*tool-missing-in-setup*"])


def test_hub_offline_inside_test() -> None:
    """The autouse session fixture sets both Hugging Face offline variables."""
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_markers_and_default_deselection() -> None:
    """The addopts deselect exactly the deselected set, never the default-selected one (R24)."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ini = config["tool"]["pytest"]["ini_options"]
    declared = {entry.split(":", 1)[0] for entry in ini["markers"]}
    assert declared == set(DESELECTED_MARKERS) | set(DEFAULT_SELECTED_MARKERS)
    assert all(entry.split(":", 1)[1].strip() for entry in ini["markers"])
    expected = " and ".join(f"not {marker}" for marker in DESELECTED_MARKERS)
    assert ini["addopts"] == f"-m '{expected}'"
    assert not any(marker in ini["addopts"] for marker in DEFAULT_SELECTED_MARKERS)


def test_acceptance_envs_gitignored() -> None:
    """The acceptance env directories are ignored."""
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".venv-accept-*/" in lines


IMPORTORSKIP_MODULE = """
import pytest

mace = pytest.importorskip("no_such_mace_xyz")

def test_m():
    pass
"""

MODULE_SKIP = """
import pytest

pytest.skip("no engine here", allow_module_level=True)

def test_m():
    pass
"""

XFAIL_FAILING = """
import pytest

@pytest.mark.xfail(reason="known-gap-xyz")
def test_x():
    assert False
"""

XFAIL_PASSING = """
import pytest

@pytest.mark.xfail(reason="known-gap-xyz")
def test_x():
    pass
"""


def run_modules(pytester: pytest.Pytester, **modules: str) -> pytest.RunResult:
    """Run the given test modules in an inner session that loads the project's real conftest."""
    pytester.makeconftest(CONFTEST)
    pytester.makepyfile(**modules)
    return pytester.runpytest_inprocess("-rA", "-p", "no:cacheprovider")


def test_collection_skip_fails_under_acceptance(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A module-level importorskip next to a passing module fails the run under =1 (R32)."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    result = run_modules(
        pytester, test_mlip_inner=IMPORTORSKIP_MODULE, test_rdkit="def test_r():\n    pass\n"
    )
    assert result.ret != 0
    outcomes = result.parseoutcomes()
    assert "skipped" not in outcomes and outcomes.get("errors", 0) >= 1, outcomes
    result.stdout.fnmatch_lines(["*test_mlip_inner.py*skipped at collection*no_such_mace_xyz*"])


def test_collection_skip_stays_skip_without_variable(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the variable the same two modules give exit 0 and 1 passed, 1 skipped."""
    monkeypatch.delenv("ETA_RXNCAT_ACCEPTANCE", raising=False)
    result = run_modules(
        pytester, test_mlip_inner=IMPORTORSKIP_MODULE, test_rdkit="def test_r():\n    pass\n"
    )
    assert result.ret == 0
    result.assert_outcomes(passed=1, skipped=1)


def test_module_level_skip_fails_under_acceptance(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pytest.skip(..., allow_module_level=True) fails the run under =1, naming the reason."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    result = run_modules(pytester, test_skipmod=MODULE_SKIP)
    assert result.ret != 0
    assert "skipped" not in result.parseoutcomes()
    result.stdout.fnmatch_lines(["*test_skipmod.py*no engine here*"])


@pytest.mark.parametrize("source", [XFAIL_FAILING, XFAIL_PASSING], ids=["xfailed", "xpassed"])
def test_xfail_fails_under_acceptance(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """An xfail test is a failure under =1 whether it xfails or xpasses, with the reason shown."""
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    result = run_modules(pytester, test_x=source)
    assert result.ret == 1
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*an xfail test is a failure*known-gap-xyz*"])


def test_xfail_unchanged_without_variable(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the variable a failing xfail test is 1 xfailed and the run exits 0."""
    monkeypatch.delenv("ETA_RXNCAT_ACCEPTANCE", raising=False)
    result = run_modules(pytester, test_x=XFAIL_FAILING)
    assert result.ret == 0
    result.assert_outcomes(xfailed=1)


SKIP_CALLS = frozenset({"importorskip", "skip"})
GUARDED_DIRS = ("tests/unit/engines", "tests/acceptance", "tests/integration")


def module_level_skips(path: Path) -> list[str]:
    """Return ``path:line`` for each module-level ``pytest.skip``/``pytest.importorskip`` call.

    Module level means anything that runs at import: top-level statements and class bodies,
    including inside top-level ``if``/``try``/``with``. Calls inside functions and lambdas run
    at test time and are allowed. ``from pytest import skip`` style names are caught too.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "pytest"
        for alias in node.names
        if alias.name in SKIP_CALLS
    }
    hits: list[str] = []
    stack: list[ast.AST] = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in SKIP_CALLS
                and isinstance(func.value, ast.Name)
                and func.value.id == "pytest"
            ) or (isinstance(func, ast.Name) and func.id in aliases):
                hits.append(f"{path}:{node.lineno}")
        stack.extend(ast.iter_child_nodes(node))
    return sorted(hits)


def test_no_module_level_skips_in_engine_tests() -> None:
    """No engine, acceptance or integration module skips at import (R32, R25)."""
    files = [
        p for d in GUARDED_DIRS for p in sorted((ROOT / d).rglob("*.py")) if (ROOT / d).is_dir()
    ]
    assert (ROOT / "tests/unit/engines").is_dir() and files
    assert [hit for path in files for hit in module_level_skips(path)] == []


@pytest.mark.parametrize(
    ("source", "flagged"),
    [
        ("import pytest\nx = pytest.importorskip('x')\n", True),
        ("import pytest\npytest.skip('x', allow_module_level=True)\n", True),
        ("import pytest\nif True:\n    pytest.importorskip('x')\n", True),
        ("import pytest\nclass TestA:\n    m = pytest.importorskip('x')\n", True),
        ("from pytest import importorskip\nm = importorskip('x')\n", True),
        ("import pytest\ndef test_a():\n    pytest.importorskip('x')\n", False),
        ("import pytest\n@pytest.fixture\ndef m():\n    return pytest.importorskip('x')\n", False),
        ("import pytest\nf = lambda: pytest.skip('x')\n", False),
        ("import pytest\npytestmark = pytest.mark.xtb\n", False),
    ],
    ids=[
        "top-level-importorskip",
        "top-level-skip",
        "inside-top-level-if",
        "class-body",
        "from-import-alias",
        "inside-test-function",
        "inside-fixture",
        "inside-lambda",
        "marker-only",
    ],
)
def test_module_level_skip_scanner(tmp_path: Path, source: str, flagged: bool) -> None:
    """The scanner flags import-time skips and allows function-, fixture- and marker-level ones."""
    path = tmp_path / "test_case.py"
    path.write_text(source, encoding="utf-8")
    assert bool(module_level_skips(path)) is flagged
