"""Shared real-module helpers for the integration tests (mission R3, R21).

Everything here is a real eta object or a literal copy of a committed rule. Nothing imports from
``tests.unit`` or ``tests.e2e``; ``test_integration_policy.py`` enforces that, and forbids mocks.
"""

import sqlite3
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, NamedTuple

import pytest
import yaml

from eta_rxncat.core import EnumerationPlan, MolecularState, StageConfig
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import Recipe
from eta_rxncat.store import ArtifactStore

ROOT = Path(__file__).resolve().parents[2]
V070_ENUMERATION_YAML = ROOT / "tests" / "e2e" / "data" / "e2e5" / "v070_enumeration.yaml"

_PLAN_KEYS = {"reference_graph", "sites", "library", "selectivity_sets", "max_candidates"}
_RUN_KEYS = {"max_alignment_rmsd_angstrom", "orientation_centers"}
_MAP_KEYS = ("keep", "delete", "alignment")


def uff_recipe() -> Recipe:
    """``rdkit_ff`` UFF with ``GeometricOptimizer`` defaults (offline, tier O)."""
    stage = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
    return Recipe("uff", stage, GeometricOptimizer())


def gfn2_stage() -> StageConfig:
    """GFN2 xtb with the ALPB ``gsolv`` state, the v0.3.0 E2E stage (runtime ``{}``)."""
    return StageConfig(
        kind="geometry_opt",
        engine="xtb_subprocess",
        method="gfn2",
        options={"alpb_state": "gsolv"},
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[ArtifactStore]:
    """A fresh per-test artifact store."""
    artifact_store = ArtifactStore(tmp_path / "store.db")
    yield artifact_store
    artifact_store.close()


def row_count(store: ArtifactStore) -> int:
    """Count the rows read straight from the store file."""
    connection = sqlite3.connect(store.path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM stage_artifacts").fetchone()[0])
    finally:
        connection.close()


@pytest.fixture
def scratch_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run the test with its working directory in ``tmp_path``."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class V070Plan(NamedTuple):
    """One enumeration plan and the run settings its YAML declares beside it."""

    plan: EnumerationPlan
    max_alignment_rmsd_angstrom: float
    orientation_centers: tuple[int, ...]


def load_v070_plan(path: Path = V070_ENUMERATION_YAML) -> V070Plan:
    """Load v0.7.0's ``v070_enumeration.yaml`` (the rules of ``tests/e2e/v070.py``, copied).

    Schema 1; the top-level keys are exactly the plan keys, the two run settings, ``schema`` and
    ``fixture``; every ``xyz`` path is relative to the YAML's directory and is read with its
    declared charge and spin multiplicity; ``EnumerationPlan`` validates the rest.

    Raises:
        ValueError: On a wrong schema, a missing or unknown key, or a plan the contracts refuse.
    """
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    expected = _PLAN_KEYS | _RUN_KEYS | {"schema", "fixture"}
    missing, extra = sorted(expected - set(data)), sorted(set(data) - expected)
    if missing or extra:
        raise ValueError(f"{path}: top-level keys: missing {missing}, unknown {extra}")
    base = path.parent
    graph = dict(data["reference_graph"])
    graph["nodes"] = [
        {**node, "templates": [_template(base, t) for t in node["templates"]]}
        for node in graph["nodes"]
    ]
    sites = [{**site, "maps": [_site_map(m) for m in site["maps"]]} for site in data["sites"]]
    library = []
    for raw in data["library"]:
        entry = dict(raw)
        entry["fragment"] = _state(base, entry)
        library.append(entry)
    plan = {key: data[key] for key in _PLAN_KEYS}
    plan.update(reference_graph=graph, sites=sites, library=library)
    return V070Plan(
        plan=EnumerationPlan.model_validate(plan),
        max_alignment_rmsd_angstrom=float(data["max_alignment_rmsd_angstrom"]),
        orientation_centers=tuple(int(i) for i in data["orientation_centers"]),
    )


def _read_xyz(path: Path, charge: int, multiplicity: int) -> MolecularState:
    """Read an XYZ file (count line, comment, then ``symbol x y z`` rows) as a state."""
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    rows = [line.split() for line in lines[2 : 2 + n]]
    return MolecularState(
        symbols=[r[0] for r in rows],
        coordinates=[[float(x) for x in r[1:4]] for r in rows],
        charge=charge,
        spin_multiplicity=multiplicity,
    )


def _state(base: Path, block: dict[str, Any]) -> MolecularState:
    """Pop ``xyz``, ``charge``, ``spin_multiplicity`` and active atoms out of a block."""
    state = _read_xyz(base / block.pop("xyz"), block.pop("charge"), block.pop("spin_multiplicity"))
    return MolecularState.model_validate(
        {**state.model_dump(), "active_atom_indices": block.pop("active_atom_indices", [])}
    )


def _template(base: Path, raw: Mapping[str, Any]) -> dict[str, Any]:
    block = dict(raw)
    state = _state(base, block)
    return {**block, "components": [{"state": state, "count": 1}]}


def _site_map(raw: Mapping[str, Any]) -> dict[str, Any]:
    block = dict(raw)
    block["template"] = {key: block.pop(key) for key in _MAP_KEYS}
    return block
