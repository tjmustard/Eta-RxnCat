"""Tests for the eta-rxncat CLI: outputs, the exit-code table and one-line errors."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from eta_rxncat import cli
from eta_rxncat.utils import hw_probe

REPO = Path(__file__).parents[3]
EXAMPLE = REPO / "tests" / "data" / "reaction_graphs" / "example_reaction_graph.yaml"
EXAMPLE_REL = "tests/data/reaction_graphs/example_reaction_graph.yaml"
HYDROGEN = {"symbols": ["H"], "coordinates": [[0.0, 0.0, 0.0]], "charge": 0, "spin_multiplicity": 2}


def script() -> str:
    """Return the installed ``eta-rxncat`` console script."""
    path = Path(sys.executable).parent / "eta-rxncat"
    found = str(path) if path.exists() else shutil.which("eta-rxncat")
    assert found, "eta-rxncat console script is not installed"
    return found


def run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the installed console script from the repo root."""
    return subprocess.run([script(), *args], capture_output=True, text=True, cwd=REPO)


def node(node_id: str, **overrides: Any) -> dict[str, Any]:
    """Return a one-template hydrogen-atom node."""
    data: dict[str, Any] = {
        "id": node_id,
        "label": node_id,
        "kind": "intermediate",
        "priority": 1,
        "templates": [{"id": "t1", "rank": 1, "components": [{"state": HYDROGEN, "count": 1}]}],
    }
    data.update(overrides)
    return data


def graph(**overrides: Any) -> dict[str, Any]:
    """Return a valid two-node graph A -> B, with overrides applied."""
    data: dict[str, Any] = {
        "schema_version": 1,
        "name": "g",
        "nodes": [node("A"), node("B")],
        "edges": [{"source": "A", "target": "B"}],
    }
    data.update(overrides)
    return data


def test_validate_example(capsys: pytest.CaptureFixture[str]) -> None:
    """The example graph validates with exactly the four summary lines."""
    assert cli.main(["validate", EXAMPLE_REL]) == 0
    out, err = capsys.readouterr()
    assert out.splitlines() == [
        f"OK {EXAMPLE_REL}",
        "nodes: 3",
        "edges: 2",
        "priority_order: ts_sn2,products,reactants",
    ]
    assert err == ""


INVALID_JSON = {
    "duplicate-node": (graph(nodes=[node("A"), node("A")], edges=[]), "'A'"),
    "unknown-endpoint": (graph(edges=[{"source": "A", "target": "Z"}]), "'Z'"),
    "self-loop": (graph(edges=[{"source": "A", "target": "A"}]), "A -> A"),
    "duplicate-edge": (
        graph(edges=[{"source": "A", "target": "B"}, {"source": "A", "target": "B"}]),
        "A -> B",
    ),
    "unknown-rule": (graph(nodes=[node("A", pruning_rules=["gate"]), node("B")]), "'gate'"),
}


@pytest.mark.parametrize("case", sorted(INVALID_JSON))
def test_validate_invalid_graphs(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each invalid graph exits 1 with one stderr line naming the offender and empty stdout."""
    data, offender = INVALID_JSON[case]
    path = tmp_path / f"{case}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert cli.main(["validate", str(path)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 1 and err.startswith("error: ") and offender in err
    assert "Traceback" not in err


def test_validate_duplicate_yaml_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A YAML mapping with a duplicate key exits 1, naming the key."""
    path = tmp_path / "dup.yaml"
    path.write_text("schema_version: 1\nname: a\nname: b\nnodes: []\n", encoding="utf-8")
    assert cli.main(["validate", str(path)]) == 1
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("error: ") and "duplicate key 'name'" in err
    assert len(err.splitlines()) == 1


@pytest.mark.parametrize(
    ("name", "content", "offender"),
    [
        ("graph.toml", b"name = 'x'\n", ".toml"),
        ("missing.yaml", None, "missing.yaml"),
        ("bad.yaml", b"\xff\xfe\x00bad", "UTF-8"),
        ("syntax.yaml", b"name: [unclosed\n", "syntax error"),
    ],
    ids=["toml", "missing", "non-utf8", "yaml-syntax"],
)
def test_validate_unreadable(
    name: str,
    content: bytes | None,
    offender: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported, missing, undecodable or unparsable files exit 1 with one error line."""
    path = tmp_path / name
    if content is not None:
        path.write_bytes(content)
    assert cli.main(["validate", str(path)]) == 1
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("error: ") and offender in err
    assert len(err.splitlines()) == 1 and "Traceback" not in err


def test_multiline_error_is_one_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A YAML syntax error (multi-line in PyYAML) is still printed as one line."""
    path = tmp_path / "bad.yaml"
    path.write_text("a: b: c\n", encoding="utf-8")
    assert cli.main(["validate", str(path)]) == 1
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 1 and err.endswith("\n")


def test_hardware_check(capsys: pytest.CaptureFixture[str]) -> None:
    """hardware-check prints the JSON report and exits 0."""
    assert cli.main(["hardware-check"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["report_schema"] == 1 and "flags" in report


def absent_gpu_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake a host where torch and gpu4pyscf are not installed (imports fail, no metadata)."""

    def missing(name: str) -> ModuleType | None:
        raise ModuleNotFoundError(f"No module named '{name}'")

    monkeypatch.setattr(hw_probe, "_import", missing)
    monkeypatch.setattr(hw_probe, "_dist_version", lambda distributions: None)


def test_hardware_check_smoke_skipped_without_torch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """On a host without torch, --smoke exits 3 with status skipped."""
    absent_gpu_stack(monkeypatch)
    assert cli.main(["hardware-check", "--smoke"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "skipped"


@pytest.mark.parametrize(("status", "code"), [("pass", 0), ("fail", 1), ("skipped", 3)])
def test_hardware_check_smoke_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
    code: int,
) -> None:
    """--smoke exits with smoke_exit_code: pass 0, fail 1, skipped 3."""
    absent_gpu_stack(monkeypatch)
    skipped = hw_probe.run_smoke()  # a fake host: no torch, so no child process
    fake = skipped.model_copy(
        update={"status": status, "reason": None if status == "pass" else "x"}
    )
    monkeypatch.setattr(hw_probe, "run_smoke", lambda timeout_s=600.0: fake)
    assert cli.main(["hardware-check", "--smoke"]) == code
    assert json.loads(capsys.readouterr().out)["status"] == status


@pytest.mark.parametrize(
    "argv",
    [[], ["frobnicate"], ["validate"], ["hardware-check", "--bogus"], ["validate", "a", "b"]],
    ids=["no-command", "unknown-command", "missing-path", "unknown-flag", "extra-arg"],
)
def test_usage_errors(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    """Usage errors return 2 (main never raises SystemExit) with argparse's message."""
    assert cli.main(argv) == 2
    assert "usage: eta-rxncat" in capsys.readouterr().err


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """--help prints usage and returns 0."""
    assert cli.main(["--help"]) == 0
    assert "hardware-check" in capsys.readouterr().out


def test_console_script_validate() -> None:
    """The installed console script validates the example graph."""
    result = run("validate", EXAMPLE_REL)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == f"OK {EXAMPLE_REL}"


def test_console_script_invalid_has_no_traceback(tmp_path: Path) -> None:
    """The installed script reports a missing file in one line with exit 1."""
    result = run("validate", str(tmp_path / "missing.yaml"))
    assert result.returncode == 1 and result.stdout == ""
    assert result.stderr.startswith("error: ") and "Traceback" not in result.stderr
    assert len(result.stderr.splitlines()) == 1


def test_console_script_hardware_check() -> None:
    """The installed script's hardware-check exits 0 with a JSON report."""
    result = run("hardware-check")
    assert result.returncode == 0 and json.loads(result.stdout)["report_schema"] == 1


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is not None,
    reason="torch is installed in this environment; the real skip path cannot be observed",
)
def test_console_script_smoke_skipped() -> None:
    """On a real environment without torch, the installed script's --smoke exits 3 (skipped)."""
    result = run("hardware-check", "--smoke")
    assert result.returncode == 3 and json.loads(result.stdout)["status"] == "skipped"


@pytest.mark.parametrize("argv", [[], ["frobnicate"]], ids=["no-command", "unknown-command"])
def test_console_script_usage_errors(argv: list[str]) -> None:
    """The installed script exits 2 on usage errors."""
    assert run(*argv).returncode == 2


def test_python_dash_m() -> None:
    """``python -m eta_rxncat validate <fixture>`` exits 0."""
    result = subprocess.run(
        [sys.executable, "-m", "eta_rxncat", "validate", EXAMPLE_REL],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr


def test_validate_imports_no_heavy_modules() -> None:
    """Validating a graph loads none of torch, pyscf, gpu4pyscf, cupy, rdkit."""
    code = (
        "import sys\n"
        "from eta_rxncat.cli import main\n"
        f"assert main(['validate', {str(EXAMPLE)!r}]) == 0\n"
        "heavy = {'torch', 'pyscf', 'gpu4pyscf', 'cupy', 'rdkit', 'mace', 'fairchem'}\n"
        "loaded = heavy & {m.split('.')[0] for m in sys.modules}\n"
        "assert not loaded, loaded\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
