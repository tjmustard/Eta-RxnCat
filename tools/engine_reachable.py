"""Print the modules a dead-code pass must leave alone (v0.7.1 R31).

Run from any directory::

    python3 tools/engine_reachable.py

The default test suite never loads an engine binary, model or GPU, so 0 coverage there says nothing
about code that only an engine path or a deselected test reaches. This script lists every
``eta_rxncat`` module reachable by import from:

- the modules defining the classes in ``ENGINE_CLASSES`` (``orchestrator/species.py``);
- the modules of ``eta_rxncat.optimize`` that define an optimizer class;
- every file under ``tests/`` that carries an ``xtb``, ``gpu``, ``mlip_*``, ``slow``,
  ``acceptance`` or ``e2e`` marker, including the test helper modules it imports.

It only parses source with ``ast`` and imports nothing from the project. Function-level imports
count, and so do the parent packages of every imported module, so the set errs on the large side.

Exit status: 0 on success, 1 if ``ENGINE_CLASSES`` or an optimizer class cannot be found.
"""

import ast
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "eta_rxncat"
HEAVY_MARKERS = frozenset({"xtb", "gpu", "slow", "acceptance", "e2e"})
HEAVY_PREFIX = "mlip_"
UNREAD_TEST_DIRS = frozenset({"candidate_outputs", "fixtures", "data"})
SPECIES = f"{PACKAGE}.orchestrator.species"


def module_paths(source: Path) -> dict[str, Path]:
    """Map every module name of the package under ``source`` to its file."""
    modules: dict[str, Path] = {}
    for path in sorted((source / PACKAGE).rglob("*.py")):
        parts = path.relative_to(source).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modules[".".join(parts)] = path
    return modules


def parse(path: Path) -> ast.Module:
    """Parse one source file."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_names(tree: ast.Module, module: str, is_package: bool) -> Iterator[str]:
    """Yield the dotted names a module imports, at any depth in its source.

    A ``from a import b`` yields both ``a`` and ``a.b``; the caller keeps those that are modules.
    """
    package = module.split(".") if is_package else module.split(".")[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                prefix = package[: len(package) - node.level + 1]
                base = ".".join([*prefix, base] if base else prefix)
            yield base
            for alias in node.names:
                yield f"{base}.{alias.name}"


def with_parents(name: str, modules: dict[str, Path]) -> Iterator[str]:
    """Yield ``name`` and its parent packages, keeping those that are project modules."""
    parts = name.split(".")
    for end in range(1, len(parts) + 1):
        candidate = ".".join(parts[:end])
        if candidate in modules:
            yield candidate


def closure(seeds: Iterable[str], modules: dict[str, Path]) -> set[str]:
    """Return every project module reachable by import from the seed names."""
    seen: set[str] = set()
    queue = [m for seed in seeds for m in with_parents(seed, modules)]
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        seen.add(module)
        path = modules[module]
        for name in imported_names(parse(path), module, path.name == "__init__.py"):
            queue.extend(with_parents(name, modules))
    return seen


def defining_module(name: str, module: str, modules: dict[str, Path]) -> str | None:
    """Follow ``from x import name`` re-exports from ``module`` to the module defining ``name``."""
    path = modules[module]
    tree = parse(path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return module
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in modules:
            if any(alias.name == name for alias in node.names):
                return defining_module(name, node.module, modules)
    return None


def engine_seeds(modules: dict[str, Path]) -> set[str]:
    """Return the modules defining the classes named in ``ENGINE_CLASSES``."""
    for node in parse(modules[SPECIES]).body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "ENGINE_CLASSES"
            and isinstance(node.value, ast.Dict)
        ):
            names = [value.id for value in node.value.values if isinstance(value, ast.Name)]
            found = [defining_module(name, SPECIES, modules) for name in names]
            if names and len(names) == len(node.value.values) and None not in found:
                return {module for module in found if module is not None}
    raise LookupError(f"cannot resolve every class of ENGINE_CLASSES in {SPECIES}")


def optimizer_seeds(modules: dict[str, Path]) -> set[str]:
    """Return the ``eta_rxncat.optimize`` modules that define an ``*Optimizer`` class."""
    seeds = {
        module
        for module, path in modules.items()
        if module.startswith(f"{PACKAGE}.optimize.")
        and any(
            isinstance(node, ast.ClassDef) and node.name.endswith("Optimizer")
            for node in parse(path).body
        )
    }
    if not seeds:
        raise LookupError(f"no optimizer class found in {PACKAGE}.optimize")
    return seeds


def has_heavy_marker(tree: ast.Module) -> bool:
    """Whether the source refers to ``pytest.mark.<heavy marker>`` anywhere in its code."""
    return any(
        isinstance(node, ast.Attribute)
        and (node.attr in HEAVY_MARKERS or node.attr.startswith(HEAVY_PREFIX))
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
        for node in ast.walk(tree)
    )


def heavy_test_imports(tests: Path) -> tuple[list[Path], set[str]]:
    """Return the heavy-marked test files and every dotted name they or their helpers import.

    A helper is a test module imported by bare name from the importing file's own directory or
    from ``tests/e2e``, which pytest puts on ``sys.path``.
    """
    files = [
        path
        for path in sorted(tests.rglob("*.py"))
        if not UNREAD_TEST_DIRS & set(path.relative_to(tests).parts[:-1])
    ]
    marked = [path for path in files if has_heavy_marker(parse(path))]
    names: set[str] = set()
    seen: set[Path] = set()
    queue = list(marked)
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in imported_names(parse(path), path.stem, False):
            names.add(name)
            for folder in (path.parent, tests / "e2e"):
                helper = folder / f"{name.split('.')[0]}.py"
                if helper in files:
                    queue.append(helper)
    return marked, names


def main() -> int:
    """Print the seeds and the reachable modules."""
    modules = module_paths(ROOT / "src")
    try:
        engines = engine_seeds(modules)
        optimizers = optimizer_seeds(modules)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    marked, test_names = heavy_test_imports(ROOT / "tests")
    reachable = closure([*engines, *optimizers, *test_names], modules)
    print(f"engine seed modules: {', '.join(sorted(engines))}")
    print(f"optimizer seed modules: {', '.join(sorted(optimizers))}")
    print(f"heavy-marked test files: {len(marked)}")
    for path in marked:
        print(f"  {path.relative_to(ROOT).as_posix()}")
    print(f"excluded modules: {len(reachable)} of {len(modules)}")
    for module in sorted(reachable):
        print(f"  {module}")
    print("modules outside the exclusion set:")
    for module in sorted(set(modules) - reachable):
        print(f"  {module}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
