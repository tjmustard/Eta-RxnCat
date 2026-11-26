"""v0.7.0 E2E inputs (slice 10): the enumeration and fallback YAMLs as ``EnumerationPlan``s.

Public surface: ``load_enumeration``, ``load_fallback`` and the ``V070Inputs`` they return. Each
YAML block mirrors the ``EnumerationPlan`` fields, with every structure given as an ``xyz`` path
(relative to the YAML) plus its explicit charge and spin multiplicity. The contracts validate the
rest and refuse unknown keys. Engine-free; nothing here changes ``src/``.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from fixtures import DATA, _exact_keys, read_xyz

from eta_rxncat.core import EnumerationPlan, MolecularState

E2E5 = DATA / "e2e5"
ENUMERATION_YAML = E2E5 / "v070_enumeration.yaml"
FALLBACK_YAML = E2E5 / "v070_fallback.yaml"
CONSTRUCTS = ("graft_time", "run_time")

_PLAN_KEYS = {"reference_graph", "sites", "library", "selectivity_sets", "max_candidates"}
_RUN_KEYS = {"max_alignment_rmsd_angstrom", "orientation_centers"}
_MAP_KEYS = ("keep", "delete", "alignment")


@dataclass(frozen=True)
class V070Inputs:
    """One enumeration plan and the run settings its YAML declares beside it.

    Attributes:
        plan: The validated plan.
        max_alignment_rmsd_angstrom: For ``enumerate_candidates``.
        orientation_centers: Product atom indices for the ensemble's orientation guard.
    """

    plan: EnumerationPlan
    max_alignment_rmsd_angstrom: float
    orientation_centers: tuple[int, ...]


def load_enumeration(path: Path = ENUMERATION_YAML) -> V070Inputs:
    """Load ``v070_enumeration.yaml``.

    Raises:
        ValueError: On a wrong schema, a missing or unknown key, or a plan the contracts refuse.
    """
    data = _read(path, _PLAN_KEYS | _RUN_KEYS)
    return _inputs(path, {k: data[k] for k in _PLAN_KEYS}, data)


def load_fallback(path: Path = FALLBACK_YAML) -> dict[str, V070Inputs]:
    """Load ``v070_fallback.yaml`` as ``{"graft_time": ..., "run_time": ...}``.

    Raises:
        ValueError: On a wrong schema, a missing or unknown key, or a plan the contracts refuse.
    """
    data = _read(path, {"constructs"} | _RUN_KEYS)
    constructs = data["constructs"]
    _exact_keys(path, "constructs", constructs, set(CONSTRUCTS))
    out = {}
    for name in CONSTRUCTS:
        _exact_keys(path, name, constructs[name], _PLAN_KEYS)
        out[name] = _inputs(path, constructs[name], data)
    return out


def _read(path: Path, keys: set[str]) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    _exact_keys(path, "top-level", data, keys | {"schema", "fixture"})
    return data


def _inputs(path: Path, plan: Mapping[str, Any], settings: Mapping[str, Any]) -> V070Inputs:
    base = Path(path).parent
    graph = dict(plan["reference_graph"])
    graph["nodes"] = [
        {**node, "templates": [_template(base, t) for t in node["templates"]]}
        for node in graph["nodes"]
    ]
    sites = [{**site, "maps": [_site_map(m) for m in site["maps"]]} for site in plan["sites"]]
    library = []
    for raw in plan["library"]:
        entry = dict(raw)
        entry["fragment"] = _state(base, entry)
        library.append(entry)
    return V070Inputs(
        plan=EnumerationPlan.model_validate(
            {**plan, "reference_graph": graph, "sites": sites, "library": library}
        ),
        max_alignment_rmsd_angstrom=float(settings["max_alignment_rmsd_angstrom"]),
        orientation_centers=tuple(int(i) for i in settings["orientation_centers"]),
    )


def _state(base: Path, block: dict[str, Any]) -> MolecularState:
    """Pop ``xyz``, ``charge``, ``spin_multiplicity`` and active atoms out of a block."""
    state = read_xyz(base / block.pop("xyz"), block.pop("charge"), block.pop("spin_multiplicity"))
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
