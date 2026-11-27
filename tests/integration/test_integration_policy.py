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
SIBLING_DIRECTORIES = (DIRECTORY.parent / "e2e", DIRECTORY.parent / "unit")
ALLOWED_MONKEYPATCH = frozenset({"setenv", "delenv", "chdir"})
MUTATORS = frozenset(
    {"setattr", "delattr", "setitem", "delitem", "syspath_prepend", "context", "undo"}
)
SYS_MODULES_MUTATORS = frozenset({"pop", "update", "setdefault", "__setitem__"})
SKIP_NAMES = frozenset({"skip", "importorskip", "skipif", "xfail"})
FORBIDDEN_MARKERS = frozenset({"gpu", "mlip_mace", "mlip_uma", "slow"})
SYS_MODULES = ["sys", "modules"]


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


def _sibling_stems() -> frozenset[str]:
    """Module names that ``tests/e2e`` and ``tests/unit`` offer as bare imports (R44).

    ``conftest`` is left out: this directory imports its own helpers relatively.
    """
    stems = {path.stem for folder in SIBLING_DIRECTORIES for path in folder.glob("*.py")}
    return frozenset(stems - {"conftest"})


def _monkeypatch_names(tree: ast.AST, seeds: frozenset[str] = frozenset()) -> set[str]:
    """``monkeypatch``, ``seeds`` and every name one of them is assigned to, through any alias."""
    names = {"monkeypatch", *seeds}
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


def _own_nodes(function: ast.AST) -> Iterator[ast.AST]:
    """The nodes of a function's own body, leaving nested functions and lambdas out."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def _bare_names(value: ast.expr) -> set[str]:
    """Names used as values in ``value``, not merely as the object of an attribute."""
    bases = {id(n.value) for n in ast.walk(value) if isinstance(n, ast.Attribute)}
    return {n.id for n in ast.walk(value) if isinstance(n, ast.Name) and id(n) not in bases}


def _wrapper_fixtures(tree: ast.Module, known: dict[str, bool]) -> dict[str, bool]:
    """Functions that hand their ``monkeypatch`` on, as ``{name: handed on as itself}`` (R44).

    A function that takes ``monkeypatch`` (or a name in ``known``) and returns or yields it is
    reported under its own name and under a ``@pytest.fixture(name=...)``. ``False`` means it
    travels inside a tuple, a call's result or an attribute of the returned object.
    """
    found: dict[str, bool] = {}
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        args = function.args
        taken = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
        taken &= {"monkeypatch", *known}
        if not taken:
            continue
        own = list(_own_nodes(function))
        itself = frozenset(n for n in taken if n == "monkeypatch" or known[n])
        held = _monkeypatch_names(function, itself) - ({"monkeypatch"} - itself)
        holders = taken - itself
        for node in own:
            if isinstance(node, ast.Assign) and _bare_names(node.value) & held:
                holders |= {
                    chain[0]
                    for target in node.targets
                    if isinstance(target, ast.Attribute | ast.Subscript)
                    if (chain := _chain(target))
                }
        for node in own:
            if not isinstance(node, ast.Return | ast.Yield | ast.YieldFrom) or node.value is None:
                continue
            names = _bare_names(node.value)
            if not names & (held | holders):
                continue
            direct = isinstance(node.value, ast.Name) and node.value.id in held
            aliases = {function.name}
            for decorator in function.decorator_list:
                if isinstance(decorator, ast.Call):
                    aliases |= {
                        str(k.value.value)
                        for k in decorator.keywords
                        if k.arg == "name" and isinstance(k.value, ast.Constant)
                    }
            for alias in aliases:
                found[alias] = found.get(alias, False) or direct
    return found


def _collect_wrappers(
    trees: list[ast.Module], seed: dict[str, bool] | None = None
) -> dict[str, bool]:
    """Wrapper fixtures across modules, including wrappers of wrappers."""
    found = dict(seed or {})
    while True:
        grown = dict(found)
        for tree in trees:
            for name, direct in _wrapper_fixtures(tree, found).items():
                grown[name] = grown.get(name, False) or direct
        if grown == found:
            return found
        found = grown


def _dynamic_mock_import(node: ast.Call, called: list[str]) -> bool:
    """Whether a call imports ``unittest.mock`` by name (``import_module`` or ``__import__``)."""
    keywords = {k.arg: k.value for k in node.keywords}
    first = node.args[0] if node.args else keywords.get("name")
    if not isinstance(first, ast.Constant):
        return False
    if called == ["importlib", "import_module"]:
        return first.value in ("unittest.mock", "mock")
    if called != ["__import__"]:
        return False
    if first.value in ("unittest.mock", "mock"):
        return True
    fromlist = node.args[3] if len(node.args) > 3 else keywords.get("fromlist")
    return (
        first.value == "unittest"
        and isinstance(fromlist, ast.List | ast.Tuple)
        and any(isinstance(e, ast.Constant) and e.value == "mock" for e in fromlist.elts)
    )


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


def scan(source: str, name: str, wrappers: dict[str, bool] | None = None) -> list[str]:
    """Return each policy finding in ``source``; ``name`` is the module's file name.

    ``wrappers`` are the monkeypatch wrapper fixtures of the other modules (``_collect_wrappers``).
    """
    tree = ast.parse(source, filename=name)
    findings: set[tuple[int, str]] = set()

    def report(node: ast.AST, form: str) -> None:
        findings.add((getattr(node, "lineno", 0), form))

    eta_names: set[str] = set()
    pytest_paths: dict[str, list[str]] = {"pytest": ["pytest"]}
    sys_paths: dict[str, list[str]] = {"sys": ["sys"]}
    importlib_paths: dict[str, list[str]] = {"importlib": ["importlib"]}
    siblings = _sibling_stems()
    for statement, bound, bound_path, path in _imports(tree):
        if _within(path, "unittest.mock"):
            report(statement, "unittest.mock")
        if _within(path, "tests") and not _within(path, "tests.integration"):
            report(statement, "tests-import")
        if path.split(".", 1)[0] in siblings:
            report(statement, "sibling-import")
        if _within(path, "importlib"):
            importlib_paths[bound] = bound_path.split(".")
        if _within(path, "eta_rxncat"):
            eta_names.add(bound)
        if _within(path, "pytest"):
            pytest_paths[bound] = bound_path.split(".")
            if path.split(".")[-1] in SKIP_NAMES:
                report(statement, path.split(".")[-1])
        if _within(path, "sys"):
            sys_paths[bound] = bound_path.split(".")
    known = _collect_wrappers([tree], wrappers)
    parameters = {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}
    used = {n: direct for n, direct in known.items() if n in parameters}
    patches = _monkeypatch_names(tree, frozenset(n for n, direct in used.items() if direct))
    containers = {n for n, direct in used.items() if not direct}
    # Unpacking or reading a container yields names that may hold the patcher.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if set(_chain(node.value)[:1]) & containers:
                containers |= {
                    n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)
                }

    def modules_chain(chain: list[str]) -> list[str]:
        """``chain`` with a ``sys`` import alias resolved."""
        return sys_paths.get(chain[0], []) + chain[1:] if chain else []

    def indirect(target: ast.expr) -> bool:
        """Whether ``target`` is rooted at an eta name or at ``sys.modules``."""
        chain = _chain(target)
        return bool(chain) and (chain[0] in eta_names or modules_chain(chain)[:2] == SYS_MODULES)

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute | ast.Subscript):
            chain = _chain(node)
            if not chain:
                continue
            if isinstance(node.ctx, ast.Store | ast.Del):
                if chain[0] in eta_names:
                    report(node, "eta-assignment")
                if modules_chain(chain)[:2] == SYS_MODULES:
                    report(node, "sys.modules-assignment")
            if not isinstance(node, ast.Attribute):
                continue
            if chain[:2] == ["unittest", "mock"]:
                report(node, "unittest.mock")
            if len(chain) == 2 and chain[0] in patches and node.attr not in ALLOWED_MONKEYPATCH:
                report(node, f"monkeypatch.{node.attr}")
            if chain[0] in patches | containers and node.attr in MUTATORS:
                report(node, f"monkeypatch.{node.attr}")
            if node.attr == "__dict__" and indirect(node.value):
                report(node, "dict-indirection")
            resolved = modules_chain(chain)
            if resolved[:2] == SYS_MODULES and resolved[2:] == [node.attr]:
                if node.attr in SYS_MODULES_MUTATORS:
                    report(node, f"sys.modules.{node.attr}")
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
            if called in (["getattr"], ["vars"]) and node.args and indirect(node.args[0]):
                report(node, f"{called[0]}-indirection")
            imported = importlib_paths.get(called[0], called[:1]) + called[1:] if called else []
            if _dynamic_mock_import(node, imported):
                report(node, "dynamic-mock-import")
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
    "sibling-e2e": ("import fixtures\n", "sibling-import"),
    "sibling-e2e-from": ("from e2e_env import REPO\n", "sibling-import"),
    "sibling-t3": ("import t3 as tier3\n", "sibling-import"),
    "sibling-t4": ("from t4 import gates\n", "sibling-import"),
    "sibling-v070": ("def f():\n    import v070\n", "sibling-import"),
    "sibling-unit": ("import test_package\n", "sibling-import"),
    "wrapper-return": (
        "def patcher(monkeypatch):\n    return monkeypatch\n"
        "def test_a(patcher):\n    patcher.setattr(a, 'b', 1)\n",
        "monkeypatch.setattr",
    ),
    "wrapper-yield": (
        "def patcher(monkeypatch):\n    mp = monkeypatch\n    yield mp\n"
        "def test_a(patcher):\n    patcher.syspath_prepend('x')\n",
        "monkeypatch.syspath_prepend",
    ),
    "wrapper-named-fixture": (
        "import pytest\n@pytest.fixture(name='patcher')\n"
        "def _patcher(monkeypatch):\n    return monkeypatch\n"
        "def test_a(patcher):\n    patcher.setitem(d, 'b', 1)\n",
        "monkeypatch.setitem",
    ),
    "wrapper-of-wrapper": (
        "def inner(monkeypatch):\n    return monkeypatch\n"
        "def outer(inner):\n    return inner\n"
        "def test_a(outer):\n    outer.delattr(a, 'b')\n",
        "monkeypatch.delattr",
    ),
    "wrapper-tuple": (
        "def patched(monkeypatch, tmp_path):\n    return monkeypatch, tmp_path\n"
        "def test_a(patched):\n    mp, _ = patched\n    mp.setattr(a, 'b', 1)\n",
        "monkeypatch.setattr",
    ),
    "wrapper-tuple-index": (
        "def patched(monkeypatch):\n    yield (monkeypatch, 1)\n"
        "def test_a(patched):\n    patched[0].setattr(a, 'b', 1)\n",
        "monkeypatch.setattr",
    ),
    "wrapper-attribute": (
        "def holder(monkeypatch, thing):\n    thing.patch = monkeypatch\n    return thing\n"
        "def test_a(holder):\n    holder.patch.setattr(a, 'b', 1)\n",
        "monkeypatch.setattr",
    ),
    "getattr-eta": (ETA + "getattr(artifact, 'ArtifactStore')\n", "getattr-indirection"),
    "getattr-sys-modules": (
        "import sys\ngetattr(sys.modules['os'], 'sep')\n",
        "getattr-indirection",
    ),
    "vars-eta": (ETA + "vars(artifact)['ArtifactStore'] = None\n", "vars-indirection"),
    "vars-sys-modules": ("from sys import modules\nvars(modules['os'])\n", "vars-indirection"),
    "dict-eta": (ETA + "artifact.__dict__.update(x=1)\n", "dict-indirection"),
    "dict-sys-modules": ("import sys\nsys.modules['os'].__dict__\n", "dict-indirection"),
    "sys-modules-pop": ("import sys\nsys.modules.pop('x')\n", "sys.modules.pop"),
    "sys-modules-update": ("import sys as s\ns.modules.update({})\n", "sys.modules.update"),
    "sys-modules-setdefault": (
        "from sys import modules\nmodules.setdefault('x', None)\n",
        "sys.modules.setdefault",
    ),
    "sys-modules-setitem": (
        "import sys\nsys.modules.__setitem__('x', None)\n",
        "sys.modules.__setitem__",
    ),
    "import-module-mock": (
        "import importlib\nimportlib.import_module('unittest.mock')\n",
        "dynamic-mock-import",
    ),
    "import-module-alias": (
        "from importlib import import_module as load\nload(name='mock')\n",
        "dynamic-mock-import",
    ),
    "dunder-import-mock": ("__import__('unittest.mock')\n", "dynamic-mock-import"),
    "dunder-import-fromlist": (
        "__import__('unittest', fromlist=['mock'])\n",
        "dynamic-mock-import",
    ),
    "dunder-import-positional": (
        "__import__('unittest', None, None, ('mock',))\n",
        "dynamic-mock-import",
    ),
    "dunder-import-bare-mock": ("__import__('mock')\n", "dynamic-mock-import"),
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
        "from .conftest import V070Plan, load_v070_plan\n",
        "def f(sample):\n    return getattr(sample, 'key'), vars(sample), sample.__dict__\n",
        "def scratch(monkeypatch, tmp_path):\n    monkeypatch.chdir(tmp_path)\n"
        "    return tmp_path\n"
        "def test_a(scratch):\n    scratch.joinpath('a')\n",
        "import importlib\nimportlib.import_module('json')\n__import__('unittest')\n",
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
        "conftest-relative-import",
        "getattr-non-eta",
        "monkeypatch-user-not-wrapper",
        "dynamic-import-not-mock",
    ],
)
def test_scanner_allows(source: str) -> None:
    """Environment patches, subprocesses, local assignments and reads pass."""
    assert scan(source, "helper.py") == []


def test_sibling_names_come_from_the_directories() -> None:
    """The set holds the e2e and unit module stems and leaves ``conftest`` out."""
    stems = _sibling_stems()
    assert {"fixtures", "e2e_env", "t3", "t4", "v070", "test_test_policy"} <= stems
    assert "conftest" not in stems
    assert scan("from conftest import x\n", "helper.py") == []


def test_wrapper_alias_crosses_modules() -> None:
    """A wrapper fixture in one module is tracked where another module takes it (R44)."""
    helper = "def patcher(monkeypatch):\n    return monkeypatch\n"
    user = "def test_a(patcher):\n    patcher.setattr(a, 'b', 1)\n"
    wrappers = _collect_wrappers([ast.parse(helper), ast.parse(user)])
    found = scan(user, "helper.py", wrappers)
    assert found == ["helper.py:2: monkeypatch.setattr"]
    assert scan(user, "helper.py") == []


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
    sources = {path: path.read_text(encoding="utf-8") for path in files}
    wrappers = _collect_wrappers([ast.parse(source) for source in sources.values()])
    findings = [
        finding
        for path, source in sources.items()
        for finding in scan(source, str(path.relative_to(DIRECTORY)), wrappers)
    ]
    assert findings == []
