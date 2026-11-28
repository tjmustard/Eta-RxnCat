"""Stale-reference scan of docs and docstrings (v0.7.1 R18). No git, no network, no engine.

Every backticked dotted name that begins ``eta_rxncat.`` must resolve, in ``README.md``, the
``CHANGELOG.md`` sections from ``[Unreleased]`` and ``[0.7.1]`` upwards (older entries are
history), ``docs/*.md`` (not ``docs/prd``) and the docstrings under ``src``.

A module that needs only the base dependencies is imported when a name refers to it. A module in
``ENGINE_EXTRA_MODULES`` is found with ``importlib.util.find_spec`` and never imported by this
scan; its attributes are resolved from the module source.
"""

import ast
import importlib
import importlib.util
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
PACKAGE = "eta_rxncat"
# A code span (single or double backticks, optionally with Sphinx's "~") starting with the package.
REFERENCE = re.compile(rf"`~?({PACKAGE}(?:\.[A-Za-z_]\w*)+)")
CHANGELOG_HEADING = re.compile(r"^## \[(?P<label>[^\]]+)\]")
FIRST_SCANNED_VERSION = (0, 7, 1)
# The modules that drive an optional extra (gpu, mlip-mace, mlip-uma, opt-geometric).
ENGINE_EXTRA_MODULES = (
    f"{PACKAGE}.engines._fairchem_bridge",
    f"{PACKAGE}.engines.esen_omol25",
    f"{PACKAGE}.engines.mace",
    f"{PACKAGE}.engines.pyscf_gpu_cpu.gpu",
    f"{PACKAGE}.engines.uma_direct",
    f"{PACKAGE}.optimize.geometric_impl",
    f"{PACKAGE}.utils._smoke_child",
)

Reference = tuple[str, int, str]


def text_references(text: str, first_line: int = 1) -> Iterator[tuple[int, str]]:
    """Yield ``(line number, dotted name)`` for each reference in a block of text."""
    for offset, line in enumerate(text.splitlines()):
        for match in REFERENCE.finditer(line):
            yield first_line + offset, match.group(1)


def changelog_references(text: str) -> Iterator[tuple[int, str]]:
    """Yield the references in the ``[Unreleased]`` section and in versions from 0.7.1 up."""
    scanned = False
    for number, line in enumerate(text.splitlines(), start=1):
        heading = CHANGELOG_HEADING.match(line)
        if heading:
            label = heading["label"]
            scanned = label == "Unreleased" or (
                tuple(int(part) for part in label.split(".")) >= FIRST_SCANNED_VERSION
            )
        if scanned:
            yield from text_references(line, number)


def docstring_references(source: str) -> Iterator[tuple[int, str]]:
    """Yield the references in every docstring, including attribute docstrings."""
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            yield from text_references(node.value.value, node.lineno)


def collect_references(root: Path) -> list[Reference]:
    """Return ``(repo-relative path, line, name)`` for every reference in scope under ``root``."""
    found: list[Reference] = []

    def add(path: Path, references: Iterator[tuple[int, str]]) -> None:
        relative = path.relative_to(root).as_posix()
        found.extend((relative, line, name) for line, name in references)

    for path in [root / "README.md", *sorted((root / "docs").glob("*.md"))]:
        if path.is_file():
            add(path, text_references(path.read_text(encoding="utf-8")))
    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        add(changelog, changelog_references(changelog.read_text(encoding="utf-8")))
    for path in sorted((root / "src").rglob("*.py")):
        add(path, docstring_references(path.read_text(encoding="utf-8")))
    return found


def bound_names(body: list[ast.stmt]) -> dict[str, list[ast.stmt]]:
    """Map the names a module or class body defines to the body each one opens (classes only).

    Covers ``def``, ``class``, assignments (annotated ones too) and the entries of ``__all__``.
    """
    names: dict[str, list[ast.stmt]] = {}
    for node in body:
        if isinstance(node, ast.ClassDef):
            names[node.name] = node.body
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names[node.name] = []
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for leaf in ast.walk(target):
                    if isinstance(leaf, ast.Name):
                        names.setdefault(leaf.id, [])
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                if isinstance(node.value, ast.List | ast.Tuple):
                    for element in node.value.elts:
                        if isinstance(element, ast.Constant) and isinstance(element.value, str):
                            names.setdefault(element.value, [])
    return names


def resolves_in_source(source: str, attributes: list[str]) -> bool:
    """Whether the attribute chain is defined in a module's source, without importing it."""
    body = ast.parse(source).body
    for attribute in attributes:
        names = bound_names(body)
        if attribute not in names:
            return False
        body = names[attribute]
    return True


def resolves_on_import(module: str, attributes: list[str]) -> bool:
    """Import a base-dependency module and walk the attribute chain on it.

    A dataclass or pydantic field without a class-level value counts when it ends the chain.
    """
    value: object = importlib.import_module(module)
    for position, attribute in enumerate(attributes):
        if hasattr(value, attribute):
            value = getattr(value, attribute)
            continue
        fields = {*getattr(value, "model_fields", {}), *getattr(value, "__annotations__", {})}
        return attribute in fields and position == len(attributes) - 1
    return True


def resolves(name: str) -> bool:
    """Whether a dotted name beginning with the package names a module or something in one."""
    parts = name.split(".")
    module, used = parts[0], 1
    spec = importlib.util.find_spec(module)
    while spec is not None and used < len(parts) and spec.submodule_search_locations is not None:
        child = importlib.util.find_spec(f"{module}.{parts[used]}")
        if child is None:
            break
        module, spec, used = f"{module}.{parts[used]}", child, used + 1
    if spec is None:
        return False
    attributes = parts[used:]
    if not attributes:
        return True
    if module in ENGINE_EXTRA_MODULES:
        assert spec.origin is not None
        return resolves_in_source(Path(spec.origin).read_text(encoding="utf-8"), attributes)
    return resolves_on_import(module, attributes)


def stale_references(root: Path) -> list[str]:
    """Return ``path:line name`` for every reference under ``root`` that does not resolve."""
    return [
        f"{path}:{line} {name}"
        for path, line, name in collect_references(root)
        if not resolves(name)
    ]


def test_no_stale_references() -> None:
    """Every backticked ``eta_rxncat`` name in the docs and docstrings resolves."""
    assert stale_references(REPO) == []


def test_scan_reads_every_source() -> None:
    """The scan finds references in the README and in source docstrings."""
    paths = {path for path, _line, _name in collect_references(REPO)}
    assert "README.md" in paths
    assert any(path.startswith("src/eta_rxncat/") for path in paths)


def test_engine_extra_modules_exist() -> None:
    """The never-imported list names real modules."""
    assert [m for m in ENGINE_EXTRA_MODULES if importlib.util.find_spec(m) is None] == []


@pytest.mark.parametrize(
    "name",
    [
        "eta_rxncat.core",
        "eta_rxncat.thermo.constants",
        "eta_rxncat.orchestrator.run_ts_with_fallback",
        "eta_rxncat.mapping.enumerator.enumerate_candidates",
        "eta_rxncat.review.RunRecord",
        "eta_rxncat.review.run_data.RunData.schema_version",
        "eta_rxncat.engines.mace",
        "eta_rxncat.engines.mace.MACEEngine",
        "eta_rxncat.engines.mace.MACEEngine._load_model",
        "eta_rxncat.optimize.geometric_impl.GeometricOptimizer",
    ],
)
def test_resolves(name: str) -> None:
    """A module, a lazy export, a class member and an engine-extra attribute all resolve."""
    assert resolves(name)


@pytest.mark.parametrize(
    "name",
    [
        "eta_rxncat.nosuch",
        "eta_rxncat.nosuch.module",
        "eta_rxncat.thermo.constants.NOT_A_CONSTANT",
        "eta_rxncat.orchestrator.run_nothing",
        "eta_rxncat.review.run_data.RunData.no_field",
        "eta_rxncat.engines.mace.NoSuchEngine",
        "eta_rxncat.engines.mace.MACEEngine.no_method",
    ],
)
def test_does_not_resolve(name: str) -> None:
    """A missing module, export, field or member is stale."""
    assert not resolves(name)


def test_engine_extra_modules_are_never_imported(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolving a name in an engine-extra module does not call ``import_module``."""

    def refuse(name: str, package: str | None = None) -> None:
        raise AssertionError(f"imported {name}")

    monkeypatch.setattr(importlib, "import_module", refuse)
    for module in ENGINE_EXTRA_MODULES:
        assert not resolves(f"{module}.not_a_name")


PLANTED = {
    "README.md": "Use `eta_rxncat.core` and `eta_rxncat.planted_readme`.\n",
    "docs/note.md": "See `eta_rxncat.mapping.planted_docs()`.\n",
    "docs/prd/old.md": "`eta_rxncat.planted_prd` is out of scope.\n",
    "CHANGELOG.md": (
        "## [Unreleased]\n`eta_rxncat.planted_unreleased`\n"
        "## [0.7.1] - 2026-01-01\n`eta_rxncat.planted_current`\n"
        "## [0.7.0] - 2026-01-01\n`eta_rxncat.planted_history`\n"
    ),
    "src/mod.py": (
        '"""Module: ``eta_rxncat.planted_module``."""\n\n'
        "VALUE = 1\n"
        '""":class:`~eta_rxncat.core.PlantedAttribute`."""\n\n'
        "# `eta_rxncat.planted_comment` is not a docstring\n"
    ),
}


def test_planted_stale_names_fail(tmp_path: Path) -> None:
    """A planted stale name fails from every source in scope, and nothing out of scope does."""
    for relative, text in PLANTED.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    assert stale_references(tmp_path) == [
        "README.md:1 eta_rxncat.planted_readme",
        "docs/note.md:1 eta_rxncat.mapping.planted_docs",
        "CHANGELOG.md:2 eta_rxncat.planted_unreleased",
        "CHANGELOG.md:4 eta_rxncat.planted_current",
        "src/mod.py:1 eta_rxncat.planted_module",
        "src/mod.py:4 eta_rxncat.core.PlantedAttribute",
    ]
