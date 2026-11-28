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

HEAVY_MODULES = ("torch", "pyscf", "rdkit", "numpy", "geometric")


def test_version() -> None:
    """The package reports the v0.7.1 version string."""
    assert eta_rxncat.__version__ == "0.7.1"


def test_import_loads_no_heavy_modules() -> None:
    """Importing the package and its data-only core loads none of the heavy backends or numpy."""
    code = (
        "import json, sys\n"
        "import eta_rxncat\n"
        "import eta_rxncat.core\n"
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
# sella, tblite, psi4: never imported (slice 01 rule). The rest are the top-level modules of the
# GPL/LGPL/MPL distributions exempted in the MLIP profiles (R48, ADR-0014), read from each
# distribution's top_level.txt in the gpu+mlip-mace and gpu+mlip-uma envs.
FORBIDDEN_IMPORTS = frozenset(
    {
        "sella",
        "tblite",
        "psi4",
        "ase",  # ase 3.29.0, LGPL-2.1-or-later
        "matscipy",  # matscipy 1.3.1, LGPL-2.1
        "hostlist",  # python-hostlist 2.3.0, GPL-2.0-or-later
        "psycopg2",  # psycopg2-binary 2.9.13, LGPL
        "ase_db_backends",  # ase_db_backends 0.11.0, LGPL-2.1-or-later
        "ray_haproxy",  # ray-haproxy 2.8.25, GPLv2
        "tqdm",  # tqdm 4.70.1, MPL-2.0 AND MIT
        "orjson",  # orjson 3.13.0, MPL-2.0 AND (Apache-2.0 OR MIT)
        "certifi",  # certifi 2026.11.20, MPL-2.0
    }
)
# Copyleft-exempt distributions (R48) must never be declared directly, in core or in any extra.
FORBIDDEN_DIRECT_DEPENDENCIES = frozenset(
    {
        "ase",
        "matscipy",
        "python-hostlist",
        "psycopg2-binary",
        "ase-db-backends",
        "ray-haproxy",
        "tqdm",
        "orjson",
        "certifi",
    }
)


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


ENGINE_HEAVY = ("ase", "torch", "mace", "fairchem", "gpu4pyscf", "cupy", "pyscf", "rdkit")


def test_engines_import_loads_no_heavy_modules() -> None:
    """Importing eta_rxncat.engines on the base install loads no engine library (lazy imports)."""
    code = (
        "import eta_rxncat, eta_rxncat.engines, sys; "
        f"print(sorted(set({ENGINE_HEAVY!r}) & set(sys.modules)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


V030_PACKAGES = (
    "eta_rxncat.core",
    "eta_rxncat.thermo",
    "eta_rxncat.conformers",
    "eta_rxncat.optimize",
)
V030_HEAVY = ("geometric", "torch", "pyscf", "fairchem")


@pytest.mark.parametrize("package", V030_PACKAGES)
def test_v030_packages_load_no_optimizer_or_engine_library(package: str) -> None:
    """Importing a v0.3.0 package loads no geomeTRIC, torch, PySCF or fairchem (TJ Q3 A)."""
    code = (
        f"import {package}, sys; "
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {V030_HEAVY!r}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


GEOMETRIC_HOME = SRC / "optimize" / "geometric_impl.py"


def geometric_imports_outside_functions(root: Path, allowed: Path) -> list[str]:
    """Return ``path:line`` for each ``geometric`` import not inside a function of ``allowed``."""
    hits = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        inside: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                inside |= {id(child) for child in ast.walk(node) if child is not node}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            if not any(name.split(".")[0] == "geometric" for name in names):
                continue
            if path != allowed or id(node) not in inside:
                hits.append(f"{path}:{node.lineno}")
    return hits


def test_geometric_imported_only_inside_geometric_impl_functions() -> None:
    """The geometric package is imported only inside functions of optimize/geometric_impl.py."""
    assert geometric_imports_outside_functions(SRC, GEOMETRIC_HOME) == []


@pytest.mark.parametrize(
    ("relative", "source", "hit"),
    [
        ("optimize/geometric_impl.py", "import geometric\n", True),
        ("optimize/geometric_impl.py", "def f():\n    import geometric.params\n", False),
        ("optimize/other.py", "def f():\n    from geometric import optimize\n", True),
        ("core/x.py", "import geometricx\n", False),
    ],
)
def test_geometric_rule_scanner(tmp_path: Path, relative: str, source: str, hit: bool) -> None:
    """The AST rule flags module-level imports and any import outside geometric_impl.py."""
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    allowed = tmp_path / "optimize" / "geometric_impl.py"
    assert bool(geometric_imports_outside_functions(tmp_path, allowed)) is hit


def test_import_ban_scans_engines_directory() -> None:
    """The AST import ban walks src/eta_rxncat/engines/ (every engine module is checked)."""
    engines_dir = SRC / "engines"
    scanned = set(SRC.rglob("*.py"))
    modules = sorted(engines_dir.glob("*.py"))
    assert {"__init__.py", "base.py", "errors.py", "fd.py", "identity.py", "options.py"} <= {
        p.name for p in modules
    }
    assert set(modules) <= scanned
    assert forbidden_imports(engines_dir) == []


def test_import_ban_catches_engine_module(tmp_path: Path) -> None:
    """A banned import inside an engines/ module (even function-local) is reported."""
    engines_dir = tmp_path / "engines"
    engines_dir.mkdir()
    (engines_dir / "mace_engine.py").write_text("def load():\n    import ase\n", encoding="utf-8")
    assert forbidden_imports(tmp_path) == [f"{engines_dir / 'mace_engine.py'}:2: ase"]


def test_no_copyleft_imports_in_package() -> None:
    """No module under src/eta_rxncat imports a banned or copyleft-exempted package."""
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


@pytest.mark.parametrize("module", sorted(FORBIDDEN_IMPORTS))
def test_scanner_covers_every_banned_module(tmp_path: Path, module: str) -> None:
    """Every banned module name, imported directly, is reported."""
    (tmp_path / "mod.py").write_text(f"import {module}\n", encoding="utf-8")
    assert len(forbidden_imports(tmp_path)) == 1


def test_permissive_off_list_packages_are_not_banned() -> None:
    """lmdb, torch_ema and clusterscope are exempt for metadata reasons only, not import-banned."""
    assert not {"lmdb", "torch_ema", "clusterscope"} & FORBIDDEN_IMPORTS


@pytest.mark.parametrize(
    "requirement",
    ["python_hostlist>=2", "psycopg2-binary", "ase_db_backends", "Ray.HAProxy", "certifi", "TQDM"],
)
def test_direct_dependency_check_covers_r48(requirement: str) -> None:
    """The direct-dependency check recognises every R48 copyleft distribution, in any spelling."""
    assert requirement_name(requirement) in FORBIDDEN_DIRECT_DEPENDENCIES


def test_scanner_ignores_lookalikes(tmp_path: Path) -> None:
    """Names that merely start with a forbidden name, and relative imports, are not reported."""
    path = tmp_path / "mod.py"
    path.write_text("import asedb\nfrom . import ase\nimport phase\n", encoding="utf-8")
    assert forbidden_imports(tmp_path) == []


def test_no_direct_copyleft_dependencies() -> None:
    """No copyleft-exempted distribution is declared directly in the dependencies or any extra."""
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
    assert set(declared) == {
        "dependencies",
        "extra gpu",
        "extra mlip-mace",
        "extra mlip-uma",
        "extra opt-geometric",
    }


@pytest.mark.parametrize(
    "requirement", ["ase>=3.22", "ASE", "matscipy[extra]", "MatSciPy ; python_version>'3'"]
)
def test_direct_dependency_check_catches(requirement: str) -> None:
    """The requirement-name normaliser recognises forbidden names in any spelling."""
    assert requirement_name(requirement) in FORBIDDEN_DIRECT_DEPENDENCIES


MAPPING_MODULES = (
    "eta_rxncat.mapping",
    "eta_rxncat.mapping.align",
    "eta_rxncat.mapping.errors",
    "eta_rxncat.mapping.graft",
    "eta_rxncat.mapping.relax",
    "eta_rxncat.mapping.report",
)
MAPPING_HEAVY = ("geometric", "torch", "pyscf", "fairchem", "rdkit")


def test_mapping_import_loads_no_heavy_modules() -> None:
    """Importing the mapping modules in a fresh interpreter loads none of MAPPING_HEAVY (R9)."""
    imports = "; ".join(f"import {module}" for module in MAPPING_MODULES)
    code = (
        f"{imports}; import sys; "
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {MAPPING_HEAVY!r}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"
