"""The ``RunData`` writer, reader and committed schema (v0.7.0, slice 07; R12)."""

import json
from typing import Any

import pydantic
import pytest
from review_helpers import put, stub_record

from eta_rxncat.review import (
    CHANGES,
    SCHEMA_VERSION,
    RunData,
    UnsupportedRunDataVersion,
    canonical_run_data_json,
    export_run_data,
    read_run_data,
)
from eta_rxncat.review.schema import SCHEMA_PATH, render_schema
from eta_rxncat.store import ArtifactStore

UNIT_SUFFIXES = (
    "_angstrom",
    "_cm1",
    "_hartree",
    "_hartree_per_bohr",
    "_kcal_mol",
)
UNITLESS_FLOATS = {
    "weight_fraction",
    "value",
    "threshold",
    "ratio",
    "forming_overlap",
    "active_core_ke_fraction",
}
"""A weight is a fraction by name; a gate's value and threshold carry ``unit``; a clash ratio,
a mode overlap and a kinetic-energy fraction are dimensionless."""


@pytest.fixture(scope="module")
def document(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """A full v1 document exported from the stub store."""
    path = tmp_path_factory.mktemp("run_data") / "stub.sqlite"
    put(path, {})
    with ArtifactStore(path) as store:
        data = export_run_data(stub_record(), store)
    return json.loads(canonical_run_data_json(data))


def encoded(document: dict[str, Any]) -> bytes:
    """The document as bytes."""
    return json.dumps(document).encode()


def test_the_strict_writer_refuses_an_unknown_key(document: dict[str, Any]) -> None:
    """Requirement 1: the writer refuses unknown keys at any depth."""
    RunData.model_validate(document)
    with pytest.raises(pydantic.ValidationError, match="Extra inputs"):
        RunData.model_validate({**document, "new_key": 1})
    deep = json.loads(json.dumps(document))
    deep["candidates"][0]["members"][0]["new_key"] = 1
    with pytest.raises(pydantic.ValidationError, match="Extra inputs"):
        RunData.model_validate(deep)


def test_the_lenient_reader_loads_unknown_keys_at_any_depth(document: dict[str, Any]) -> None:
    """Requirement 1: a v1 document with unknown keys loads, without them."""
    newer = json.loads(json.dumps(document))
    newer["new_key"] = {"a": 1}
    newer["provenance"]["new_key"] = 1
    newer["candidates"][0]["members"][0]["new_key"] = 1
    for entry in [*newer["trajectories"], *newer["frequencies"]]:
        entry["new_key"] = 1
    stored = next(t for t in newer["trajectories"] if t.get("frames"))
    stored["frames"][0]["new_key"] = 1
    stored["convergence"]["new_key"] = 1
    assert read_run_data(encoded(newer)) == RunData.model_validate(document)


@pytest.mark.parametrize("version", [2, 99])
def test_a_later_version_is_refused(document: dict[str, Any], version: int) -> None:
    """Requirement 1: version 2 is refused before its shape is looked at."""
    with pytest.raises(UnsupportedRunDataVersion):
        read_run_data(encoded({**document, "schema_version": version}))
    with pytest.raises(UnsupportedRunDataVersion):
        read_run_data(encoded({"schema_version": version}))


@pytest.mark.parametrize("version", [0, True, 1.0, "1"])
def test_only_the_integer_one_is_written(document: dict[str, Any], version: object) -> None:
    """The writer takes the integer 1 only."""
    with pytest.raises(pydantic.ValidationError):
        RunData.model_validate({**document, "schema_version": version})


def test_the_reader_refuses_a_missing_required_key(document: dict[str, Any]) -> None:
    """Leniency covers unknown keys only."""
    broken = {k: v for k, v in document.items() if k != "species"}
    with pytest.raises(pydantic.ValidationError):
        read_run_data(encoded(broken))


def test_a_dangling_reference_is_refused(document: dict[str, Any]) -> None:
    """References are by id and must resolve."""
    broken = json.loads(json.dumps(document))
    broken["candidates"][0]["trajectory_ids"].append("nothing")
    with pytest.raises(pydantic.ValidationError, match="unknown trajectory"):
        RunData.model_validate(broken)


def test_the_committed_schema_matches_the_model() -> None:
    """Requirement 2: the drift test."""
    assert SCHEMA_PATH.read_text(encoding="utf-8") == render_schema(), (
        f"{SCHEMA_PATH.name} differs from RunData.model_json_schema() under pydantic "
        f"{pydantic.VERSION.split('.')[0]} ({pydantic.VERSION}); if the contract change is meant, "
        "apply the version rule, then run `python3 -m eta_rxncat.review.schema`"
    )
    assert json.loads(render_schema()) == RunData.model_json_schema()
    assert SCHEMA_PATH.name == f"run_data.v{SCHEMA_VERSION}.schema.json"


def test_the_schema_states_the_version_rule() -> None:
    """The rule is in the schema description, and CHANGES ends at the current version."""
    description = RunData.model_json_schema()["description"]
    assert "enum value bumps it" in " ".join(description.split())
    assert CHANGES[-1][0] == SCHEMA_VERSION


def _numbers(schema: dict[str, Any]) -> bool:
    """Whether a property's schema holds a float anywhere (not through a ``$ref``)."""
    if schema.get("type") == "number":
        return True
    parts = [*schema.get("anyOf", []), schema.get("items", {})]
    return any(_numbers(p) for p in parts if p)


def test_every_physical_quantity_carries_its_unit() -> None:
    """Requirement 7: a walk of every float-valued key of the schema."""
    schema = RunData.model_json_schema()
    keys = {
        name
        for model in [schema, *schema["$defs"].values()]
        for name, sub in model.get("properties", {}).items()
        if _numbers(sub)
    }
    assert {"coordinates_angstrom", "energy_hartree", "dG_dagger_kcal_mol"} <= keys
    unitless = {k for k in keys if not k.endswith(UNIT_SUFFIXES)}
    assert unitless == UNITLESS_FLOATS
    gate = schema["$defs"]["Gate"]["properties"]
    assert "unit" in gate
