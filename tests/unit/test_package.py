"""Tests for the top-level ``eta_rxncat`` package."""

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import eta_rxncat

HEAVY_MODULES = ("torch", "pyscf", "rdkit")


def test_version() -> None:
    """The package reports the v0.1.0 version string."""
    assert eta_rxncat.__version__ == "0.1.0"


def test_import_loads_no_heavy_modules() -> None:
    """Importing the package in a fresh interpreter loads none of the heavy backends."""
    code = (
        "import json, sys\n"
        "import eta_rxncat\n"
        f"heavy = {HEAVY_MODULES!r}\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in heavy)\n"
        "print(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


SRC = Path(__file__).parents[2] / "src" / "eta_rxncat"
PYPROJECT = Path(__file__).parents[2] / "pyproject.toml"
FORBIDDEN_IMPORTS = frozenset({"ase", "matscipy", "sella", "tblite", "psi4"})
FORBIDDEN_DIRECT_DEPENDENCIES = frozenset({"ase", "matscipy"})


def forbidden_imports(root: Path) -> list[str]:
    """Return ``path:line: module`` for each import of a forbidden package under ``root``.

    Covers ``import x``, ``import x.y``, ``from x import y`` and ``from x.y import z`` anywhere in a
    module (including function bodies); relative imports are ignored.
    """
    hits = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                if name.split(".")[0] in FORBIDDEN_IMPORTS:
                    hits.append(f"{path}:{node.lineno}: {name}")
    return hits


def requirement_name(requirement: str) -> str:
    """Return the normalised distribution name of a PEP 508 requirement string."""
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", requirement)
    assert match, requirement
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def test_no_copyleft_imports_in_package() -> None:
    """No module under src/eta_rxncat imports ase, matscipy, sella, tblite or psi4."""
    assert forbidden_imports(SRC) == []


@pytest.mark.parametrize(
    ("source", "module"),
    [
        ("import ase\n", "ase"),
        ("import ase.io as aio\n", "ase.io"),
        ("from matscipy.neighbours import neighbour_list\n", "matscipy.neighbours"),
        ("def f():\n    import sella\n", "sella"),
        ("import os, psi4\n", "psi4"),
        ("from tblite import interface\n", "tblite"),
    ],
)
def test_scanner_reports_forbidden_import(tmp_path: Path, source: str, module: str) -> None:
    """The scanner reports a forbidden import with its file and line."""
    path = tmp_path / "pkg" / "mod.py"
    path.parent.mkdir()
    path.write_text(source, encoding="utf-8")
    hits = forbidden_imports(tmp_path)
    assert len(hits) == 1 and hits[0].startswith(f"{path}:") and hits[0].endswith(f": {module}")


def test_scanner_ignores_lookalikes(tmp_path: Path) -> None:
    """Names that merely start with a forbidden name, and relative imports, are not reported."""
    path = tmp_path / "mod.py"
    path.write_text("import asedb\nfrom . import ase\nimport phase\n", encoding="utf-8")
    assert forbidden_imports(tmp_path) == []


def test_no_direct_copyleft_dependencies() -> None:
    """Neither ase nor matscipy is declared directly in the dependencies or any extra."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    declared = {"dependencies": project.get("dependencies", [])}
    declared |= {f"extra {k}": v for k, v in project.get("optional-dependencies", {}).items()}
    offenders = [
        f"{where}: {req}"
        for where, reqs in declared.items()
        for req in reqs
        if requirement_name(req) in FORBIDDEN_DIRECT_DEPENDENCIES
    ]
    assert offenders == []
    assert set(declared) == {"dependencies", "extra gpu", "extra mlip-mace", "extra mlip-uma"}


@pytest.mark.parametrize(
    "requirement", ["ase>=3.22", "ASE", "matscipy[extra]", "MatSciPy ; python_version>'3'"]
)
def test_direct_dependency_check_catches(requirement: str) -> None:
    """The requirement-name normaliser recognises forbidden names in any spelling."""
    assert requirement_name(requirement) in FORBIDDEN_DIRECT_DEPENDENCIES
