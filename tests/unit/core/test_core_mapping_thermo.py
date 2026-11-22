"""Tests for AtomMappingSpec (self and template-level checks) and ThermoConfig."""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from eta_rxncat.core import (
    AtomMappingSpec,
    MolecularState,
    TemplateGeometry,
    ThermoConfig,
    dump_reaction_graph_json,
    load_reaction_graph,
)


def mapping(**overrides: Any) -> dict[str, Any]:
    """Return a valid mapping over 6 atoms, with overrides applied."""
    data: dict[str, Any] = {"keep": [0, 1, 2, 3, 4], "delete": [5], "alignment": [1, 0, 2]}
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"keep": [0, 1, 2, 3, 5]}, "overlap"),
        ({"keep": [0, 1, 1, 2]}, "keep has duplicate"),
        ({"delete": [5, 5]}, "delete has duplicate"),
        ({"alignment": [0, 1, 1]}, "alignment has duplicate"),
        ({"anchors": [3, 3]}, "anchors has duplicate"),
        ({"alignment": [0, 1, 5]}, "not in keep"),
        ({"alignment": [0, 1, 6]}, "not in keep"),
        ({"alignment": [0, 1]}, "at least 3"),
        ({"anchors": [5]}, "anchors"),
        ({"keep": [-1, 0, 1, 2]}, "negative"),
    ],
    ids=[
        "keep-delete-overlap",
        "duplicate-keep",
        "duplicate-delete",
        "duplicate-alignment",
        "duplicate-anchors",
        "alignment-in-delete",
        "alignment-not-in-keep",
        "two-alignment-atoms",
        "anchor-not-in-keep",
        "negative-index",
    ],
)
def test_mapping_invariants(overrides: dict[str, Any], message: str) -> None:
    """Each AtomMappingSpec invariant raises on its own violation."""
    with pytest.raises(ValidationError, match=message):
        AtomMappingSpec(**mapping(**overrides))


def six_atom_template(mapping_data: dict[str, Any]) -> dict[str, Any]:
    """Return a one-component, six-atom template dict using ``mapping_data``."""
    state = MolecularState(
        symbols=["C", "Cl", "Cl", "H", "H", "H"],
        coordinates=[[float(i), 0.0, 0.0] for i in range(6)],
        charge=-1,
        spin_multiplicity=1,
    )
    return {
        "id": "t1",
        "rank": 1,
        "components": [{"state": state.model_dump(), "count": 1}],
        "mapping": mapping_data,
    }


def test_template_rejects_index_beyond_atom_count() -> None:
    """A mapping index >= the template's atom count raises."""
    data = six_atom_template(mapping(delete=[5, 6]))
    with pytest.raises(ValidationError, match=r"template 't1'.*out of range"):
        TemplateGeometry.model_validate(data)


def test_template_requires_keep_and_delete_to_cover_all_atoms() -> None:
    """Keep ∪ delete must be every atom of the template."""
    data = six_atom_template(mapping(delete=[]))
    with pytest.raises(ValidationError, match=r"neither keep nor delete"):
        TemplateGeometry.model_validate(data)


def test_index_space_spans_components() -> None:
    """The index space is the components' atoms concatenated, each component once."""
    chloride = {
        "symbols": ["Cl"],
        "coordinates": [[0.0, 0.0, 0.0]],
        "charge": -1,
        "spin_multiplicity": 1,
    }
    methyl_chloride = {
        "symbols": ["C", "Cl", "H", "H", "H"],
        "coordinates": [[float(i), 0.0, 0.0] for i in range(5)],
        "charge": 0,
        "spin_multiplicity": 1,
    }
    template = TemplateGeometry.model_validate(
        {
            "id": "pair",
            "rank": 1,
            "components": [{"state": methyl_chloride, "count": 1}, {"state": chloride, "count": 2}],
            "mapping": {"keep": [0, 1, 2, 3, 5], "delete": [4], "alignment": [0, 1, 5]},
        }
    )
    assert template.atom_count == 6
    assert template.total_charge == -2


def test_mapping_order_survives_yaml_and_json(tmp_path: Path) -> None:
    """List order is preserved through YAML -> model -> JSON -> model."""
    order = {"keep": [4, 0, 3, 1, 2], "delete": [5], "alignment": [2, 0, 1], "anchors": [3, 4]}
    graph = {
        "schema_version": 1,
        "name": "order",
        "nodes": [
            {
                "id": "n1",
                "label": "n1",
                "kind": "intermediate",
                "priority": 1,
                "templates": [six_atom_template(order)],
            }
        ],
    }
    path = tmp_path / "order.yaml"
    path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    from_yaml = load_reaction_graph(path)
    json_path = tmp_path / "order.json"
    json_path.write_text(dump_reaction_graph_json(from_yaml), encoding="utf-8")
    from_json = load_reaction_graph(json_path)
    loaded = from_json.nodes[0].templates[0].mapping
    assert loaded is not None
    assert loaded.model_dump() == order
    assert (
        json.loads(json_path.read_text())["nodes"][0]["templates"][0]["mapping"]["keep"]
        == order["keep"]
    )


def test_thermo_defaults() -> None:
    """ThermoConfig() has exactly the Grimme quasi-RRHO / 1 M defaults."""
    assert ThermoConfig().model_dump() == {
        "entropy_model": "grimme_qrrho",
        "temperature_k": 298.15,
        "pressure_atm": 1.0,
        "standard_state_mol_l": 1.0,
        "qrrho_cutoff_cm1": 100.0,
        "qrrho_alpha": 4.0,
        "qrrho_rotor_moment_kg_m2": 1.0e-44,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"temperature_k": 0},
        {"standard_state_mol_l": None},
        {"qrrho_cutoff_cm1": -1},
        {"pressure_atm": float("inf")},
        {"entropy_model": "rrho"},
    ],
)
def test_thermo_rejects_bad_values(overrides: dict[str, Any]) -> None:
    """Non-positive, None, infinite or unknown thermo settings raise."""
    with pytest.raises(ValidationError):
        ThermoConfig(**overrides)
