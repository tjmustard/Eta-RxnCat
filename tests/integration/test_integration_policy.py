"""No mock across a seam and no silent skip in ``tests/integration`` (mission R25, R26).

``scan`` reads one module's AST and returns a ``<name>:<line>: <form>`` finding for each rule it
breaks. The cases below pin every form; the last test runs the scanner over the real directory.

Seam break: remove one rule from ``scan`` and its negative case fails.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

DIRECTORY = Path(__file__).resolve().parent
ALLOWED_MONKEYPATCH = frozenset({"setenv", "delenv", "chdir"})
SKIP_NAMES = frozenset({"skip", "importorskip", "skipif", "xfail"})
FORBIDDEN_MARKERS = frozenset({"gpu", "mlip_mace", "mlip_uma", "slow"})


def _chain(node: ast.expr) -> list[str]:
    """Return the dotted names of an attribute/subscript chain from its root, else ``[]``."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute | ast.Subscript):
        parts.append(node.attr if isinstance(node, ast.Attribute) else "[]")
        node = node.value
    if not isinstance(node, ast.Name):
        return []
    return [node.id, *reversed(parts)]


def _imports(tree: ast.Module) -> Iterator[tuple[ast.stmt, str, str, str]]:
    """Yield ``(statement, bound name, bound path, imported path)`` for every import.

    ``import a.b`` binds ``a`` (bound path ``a``) but imports ``a.b``. A relative import that
    climbs out of this directory is reported as ``tests.<module>``.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                bound = alias.asname or root
                yield node, bound, alias.name if alias.asname else root, alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level >= 2:
                module = f"tests.{module}".rstrip(".")
            elif node.level == 1:
                module = f"tests.integration.{module}".rstrip(".")
            for alias in node.names:
                path = f"{module}.{alias.name}"
                yield node, alias.asname or alias.name, path, path


def _within(path: str, package: str) -> bool:
    return path == package or path.startswith(f"{package}.")


def _monkeypatch_names(tree: ast.Module) -> set[str]:
    """``monkeypatch`` and every name it is assigned to, directly or through another alias."""
    names = {"monkeypatch"}
    assignments: list[tuple[list[ast.expr], ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assignments.append((node.targets, node.value))
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr) and node.value is not None:
            assignments.append(([node.target], node.value))
    grew = True
    while grew:
        grew = False
        for targets, value in assignments:
            if isinstance(value, ast.Name) and value.id in names:
                new = {t.id for t in targets if isinstance(t, ast.Name)} - names
                names |= new
                grew = grew or bool(new)
    return names


def _marks_integration(tree: ast.Module) -> bool:
    """Whether the module-level ``pytestmark`` contains ``pytest.mark.integration``."""
    value: ast.expr | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in node.targets):
                value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "pytestmark":
                value = node.value
    if value is None:
        return False
    marks = value.elts if isinstance(value, ast.List | ast.Tuple) else [value]
    return any(
        _chain(m.func if isinstance(m, ast.Call) else m) == ["pytest", "mark", "integration"]
        for m in marks
    )


def scan(source: str, name: str) -> list[str]:
    """Return each policy finding in ``source``; ``name`` is the module's file name."""
    tree = ast.parse(source, filename=name)
    findings: set[tuple[int, str]] = set()

    def report(node: ast.AST, form: str) -> None:
        findings.add((getattr(node, "lineno", 0), form))

    eta_names: set[str] = set()
    pytest_paths: dict[str, list[str]] = {"pytest": ["pytest"]}
    sys_paths: dict[str, list[str]] = {"sys": ["sys"]}
    for statement, bound, bound_path, path in _imports(tree):
        if _within(path, "unittest.mock"):
            report(statement, "unittest.mock")
        if _within(path, "tests") and not _within(path, "tests.integration"):
            report(statement, "tests-import")
        if _within(path, "eta_rxncat"):
            eta_names.add(bound)
        if _within(path, "pytest"):
            pytest_paths[bound] = bound_path.split(".")
            if path.split(".")[-1] in SKIP_NAMES:
                report(statement, path.split(".")[-1])
        if _within(path, "sys"):
            sys_paths[bound] = bound_path.split(".")
    patches = _monkeypatch_names(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute | ast.Subscript):
            chain = _chain(node)
            if not chain:
                continue
            if isinstance(node.ctx, ast.Store | ast.Del):
                if chain[0] in eta_names:
                    report(node, "eta-assignment")
                if (sys_paths.get(chain[0], []) + chain[1:])[:2] == ["sys", "modules"]:
                    report(node, "sys.modules-assignment")
            if not isinstance(node, ast.Attribute):
                continue
            if chain[:2] == ["unittest", "mock"]:
                report(node, "unittest.mock")
            if len(chain) == 2 and chain[0] in patches and node.attr not in ALLOWED_MONKEYPATCH:
                report(node, f"monkeypatch.{node.attr}")
            full = pytest_paths.get(chain[0], []) + chain[1:]
            if full[:1] == ["pytest"]:
                if "MonkeyPatch" in full[:-1]:
                    report(node, f"monkeypatch.{node.attr}")
                if node.attr in SKIP_NAMES:
                    report(node, node.attr)
                if full[1:-1] == ["mark"] and node.attr in FORBIDDEN_MARKERS:
                    report(node, f"mark.{node.attr}")
        elif isinstance(node, ast.Name):
            if node.id in ("setattr", "delattr"):
                report(node, node.id)
        elif isinstance(node, ast.Call):
            called = _chain(node.func)
            if called[-1:] in (["add_marker"], ["applymarker"]):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and arg.value in SKIP_NAMES:
                        report(node, str(arg.value))
                    elif isinstance(arg, ast.Constant) and arg.value in FORBIDDEN_MARKERS:
                        report(node, f"mark.{arg.value}")

    if Path(name).match("test_*.py") or Path(name).match("*_test.py"):
        if not _marks_integration(tree):
            findings.add((1, "no-integration-mark"))
    return [f"{name}:{line}: {form}" for line, form in sorted(findings)]


MARK = "import pytest\npytestmark = pytest.mark.integration\n"
ETA = "import eta_rxncat.store as artifact\n"

NEGATIVE_CASES = {
    "import-mock": ("import unittest.mock\n", "unittest.mock"),
    "import-mock-as": ("import unittest.mock as m\n", "unittest.mock"),
    "from-unittest-import-mock": ("from unittest import mock\n", "unittest.mock"),
    "from-mock-import": ("from unittest.mock import patch\n", "unittest.mock"),
    "mock-attribute": ("import unittest\nunittest.mock.patch('x')\n", "unittest.mock"),
    "monkeypatch-setattr": (
        "def test_a(monkeypatch):\n    monkeypatch.setattr(a, 'b', 1)\n",
        "monkeypatch.setattr",
    ),
    "monkeypatch-setitem": (
        "def test_a(monkeypatch):\n    monkeypatch.setitem(d, 'b', 1)\n",
        "monkeypatch.setitem",
    ),
    "monkeypatch-context": (
        "def test_a(monkeypatch):\n    with monkeypatch.context() as m:\n        pass\n",
        "monkeypatch.context",
    ),
    "monkeypatch-alias": (
        "def test_a(monkeypatch):\n    mp = monkeypatch\n    again = mp\n"
        "    again.syspath_prepend('x')\n",
        "monkeypatch.syspath_prepend",
    ),
    "monkeypatch-class": (
        "import pytest\nwith pytest.MonkeyPatch.context() as m:\n    pass\n",
        "monkeypatch.context",
    ),
    "eta-assign": (ETA + "artifact.ArtifactStore.get = None\n", "eta-assignment"),
    "eta-assign-from": (
        "from eta_rxncat.store import ArtifactStore\nArtifactStore.get = None\n",
        "eta-assignment",
    ),
    "eta-assign-dotted": (
        "import eta_rxncat.store\neta_rxncat.store.ArtifactStore = None\n",
        "eta-assignment",
    ),
    "eta-subscript": (ETA + "artifact.TABLE['x'] = 1\n", "eta-assignment"),
    "eta-augassign": (ETA + "artifact.SCHEMA_VERSION += 1\n", "eta-assignment"),
    "eta-delete": (ETA + "del artifact.ArtifactStore\n", "eta-assignment"),
    "eta-unpack": (ETA + "artifact.a, b = 1, 2\n", "eta-assignment"),
    "sys-modules-assign": ("import sys\nsys.modules['x'] = None\n", "sys.modules-assignment"),
    "sys-modules-delete": (
        "from sys import modules\ndel modules['x']\n",
        "sys.modules-assignment",
    ),
    "setattr": ("setattr(a, 'b', 1)\n", "setattr"),
    "delattr": ("delattr(a, 'b')\n", "delattr"),
    "setattr-alias": ("s = setattr\n", "setattr"),
    "tests-import": ("import tests.unit.core\n", "tests-import"),
    "tests-from-import": ("from tests.e2e import v070\n", "tests-import"),
    "tests-from-package": ("from tests import unit\n", "tests-import"),
    "relative-escape": ("from ..unit import helpers\n", "tests-import"),
    "skip-call": ("import pytest\npytest.skip('x')\n", "skip"),
    "skip-marker": ("import pytest\n@pytest.mark.skip\ndef test_a():\n    pass\n", "skip"),
    "importorskip": ("import pytest\npytest.importorskip('x')\n", "importorskip"),
    "skipif": (
        "import pytest\n@pytest.mark.skipif(True, reason='x')\ndef f():\n    pass\n",
        "skipif",
    ),
    "xfail-call": ("import pytest\ndef f():\n    pytest.xfail('x')\n", "xfail"),
    "xfail-marker": ("import pytest\npytestmark = [pytest.mark.xfail]\n", "xfail"),
    "skip-from-import": ("from pytest import skip\n", "skip"),
    "skip-mark-alias": ("from pytest import mark\n@mark.skipif(1)\ndef f():\n    pass\n", "skipif"),
    "skip-pytest-alias": ("import pytest as pt\npt.skip('x')\n", "skip"),
    "skip-param-mark": (
        "import pytest\nP = pytest.param(1, marks=pytest.mark.skip)\n",
        "skip",
    ),
    "skip-add-marker": ("def test_a(request):\n    request.node.add_marker('skip')\n", "skip"),
    "gpu": ("import pytest\n@pytest.mark.gpu\ndef f():\n    pass\n", "mark.gpu"),
    "mlip_mace": ("import pytest\nM = pytest.mark.mlip_mace\n", "mark.mlip_mace"),
    "mlip_uma": ("import pytest\nM = pytest.mark.mlip_uma\n", "mark.mlip_uma"),
    "slow": ("import pytest\nM = pytest.mark.slow\n", "mark.slow"),
}


@pytest.mark.parametrize(
    ("source", "form"), list(NEGATIVE_CASES.values()), ids=list(NEGATIVE_CASES)
)
def test_scanner_reports_form(source: str, form: str) -> None:
    """Each forbidden form is reported under its name."""
    found = {finding.rsplit(": ", 1)[1] for finding in scan(source, "helper.py")}
    assert form in found


@pytest.mark.parametrize(
    "source",
    [
        "def test_a(monkeypatch, tmp_path):\n    monkeypatch.setenv('A', '1')\n"
        "    monkeypatch.delenv('A')\n    monkeypatch.chdir(tmp_path)\n",
        "import subprocess, sys\nsubprocess.run([sys.executable, '-c', 'pass'], check=True)\n",
        "x = {}\nx['a'] = 1\ny = 2\ny += 1\ndel y\n",
        "from eta_rxncat.core import StageConfig\nvalue = StageConfig.model_fields\n",
        "from tests.integration.conftest import uff_recipe\n",
        "import tests.integration.conftest\n",
        "from .conftest import uff_recipe\n",
        "import sys\nfound = sys.modules['os']\n",
        "import pytest\nM = pytest.mark.xtb\n",
    ],
    ids=[
        "allowed-monkeypatch",
        "subprocess",
        "local-assignment",
        "eta-read",
        "integration-import",
        "integration-module-import",
        "relative-import",
        "sys-modules-read",
        "xtb-marker",
    ],
)
def test_scanner_allows(source: str) -> None:
    """Environment patches, subprocesses, local assignments and reads pass."""
    assert scan(source, "helper.py") == []


@pytest.mark.parametrize(
    ("source", "marked"),
    [
        (MARK, True),
        ("import pytest\npytestmark = [pytest.mark.xtb, pytest.mark.integration]\n", True),
        ("import pytest\npytestmark: list[object] = [pytest.mark.integration]\n", True),
        ("import pytest\n", False),
        ("import pytest\npytestmark = pytest.mark.xtb\n", False),
        ("import pytest\ndef test_a():\n    pytestmark = pytest.mark.integration\n", False),
    ],
    ids=["single", "list", "annotated", "missing", "other-mark", "not-module-level"],
)
def test_scanner_requires_the_integration_mark(source: str, marked: bool) -> None:
    """A test module needs a module-level ``pytestmark`` holding the integration mark."""
    assert (scan(source, "test_case.py") == []) is marked


def test_integration_directory_is_clean() -> None:
    """No module under ``tests/integration`` breaks a rule."""
    files = sorted(DIRECTORY.rglob("*.py"))
    assert {"conftest.py", Path(__file__).name} <= {path.name for path in files}
    findings = [
        finding
        for path in files
        for finding in scan(path.read_text(encoding="utf-8"), str(path.relative_to(DIRECTORY)))
    ]
    assert findings == []
