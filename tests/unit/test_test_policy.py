"""Tests for the engine test policy: markers, offline hubs, acceptance skip-to-fail (slice 01)."""

import os
import tomllib
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

ROOT = Path(__file__).resolve().parents[2]
CONFTEST = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
MARKERS = ("gpu", "xtb", "mlip_mace", "mlip_uma", "slow", "acceptance")

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
    """All six markers are declared, and the default addopts deselects every one of them."""
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ini = config["tool"]["pytest"]["ini_options"]
    declared = {entry.split(":", 1)[0] for entry in ini["markers"]}
    assert declared == set(MARKERS)
    assert all(entry.split(":", 1)[1].strip() for entry in ini["markers"])
    expected = " and ".join(f"not {marker}" for marker in MARKERS)
    assert ini["addopts"] == f"-m '{expected}'"


def test_acceptance_envs_gitignored() -> None:
    """The acceptance env directories are ignored."""
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".venv-accept-*/" in lines
