"""``canonical_run_data_json`` (v0.7.0, slice 07; R14)."""

import json
from pathlib import Path

import pytest
from review_helpers import ENGINE, HOSTILE, put, stub_record

from eta_rxncat.review import (
    RunData,
    canonical_run_data_json,
    export_run_data,
    read_run_data,
)
from eta_rxncat.store import ArtifactStore

RAW = ("<", ">", "&", "\u2028", "\u2029")


@pytest.fixture
def hostile(tmp_path: Path) -> RunData:
    """A document with the hostile string as species label, entry id and provenance string."""
    path = tmp_path / "stub.sqlite"
    put(path, {})
    record = stub_record(label=HOSTILE, entry_id=HOSTILE)
    engine = ENGINE.model_copy(update={"version": HOSTILE})
    run = record.runs[0].model_copy(update={"engine": engine})
    selectivity = record.selectivity[0].model_copy(update={"engine": engine})
    gate = record.gates[0]
    gate = gate.model_copy(update={"unit_ref": gate.unit_ref.model_copy(update={"engine": engine})})
    record = record.model_copy(
        update={"runs": [run], "selectivity": [selectivity], "gates": [gate]}
    )
    with ArtifactStore(path) as store:
        return export_run_data(record, store)


def test_the_five_characters_appear_only_escaped(hostile: RunData) -> None:
    """Requirement 3: no raw character can end an HTML script element."""
    document = canonical_run_data_json(hostile)
    text = document.decode("utf-8")
    for char in RAW:
        assert char not in text
    for escape in ("\\u003c", "\\u003e", "\\u0026", "\\u2028", "\\u2029"):
        assert escape in text
    assert "</script>" not in text and "<!--" not in text
    assert "\\u003c/script\\u003e\\u003cimg src=x onerror=alert(1)\\u003e" in text


def test_the_strings_survive_parsing(hostile: RunData) -> None:
    """The JSON is valid and the data values are not HTML-escaped."""
    parsed = json.loads(canonical_run_data_json(hostile))
    assert HOSTILE in {s["label"] for s in parsed["species"]}
    assert parsed["candidates"][0]["entry_ids_by_site"] == {"r": HOSTILE}
    assert parsed["provenance"]["engines"][0]["version"] == HOSTILE


def test_it_is_compact_sorted_and_stable(hostile: RunData) -> None:
    """Sorted keys, compact separators, the same bytes twice."""
    document = canonical_run_data_json(hostile)
    assert document == canonical_run_data_json(hostile)
    parsed = json.loads(document)
    assert list(parsed) == sorted(parsed)
    assert b'": ' not in document and b"\n" not in document


def test_it_round_trips_to_the_same_bytes(hostile: RunData) -> None:
    """Reading the bytes and writing them again changes nothing."""
    document = canonical_run_data_json(hostile)
    assert canonical_run_data_json(read_run_data(document)) == document


def test_parsing_gives_the_dump_after_rounding(hostile: RunData) -> None:
    """Floats are rounded per unit family; everything else is the model dump."""
    parsed = json.loads(canonical_run_data_json(hostile))
    dump = hostile.model_dump(mode="json")
    assert parsed["candidates"] == dump["candidates"]
    assert parsed["gates"] == dump["gates"]
    # H2's second atom is at 1.2000012345 A: ten significant digits.
    species = {s["species_id"]: s for s in parsed["species"]}
    assert species["ts"]["coordinates_angstrom"][1][0] == 1.200001234
    (frequency,) = [f for f in parsed["frequencies"] if f["status"] == "completed"]
    (exact,) = [f for f in dump["frequencies"] if f["status"] == "completed"]
    assert frequency["frequencies_cm1"] == [float(f"{x:.8g}") for x in exact["frequencies_cm1"]]


def test_negative_zero_is_written_as_zero(hostile: RunData) -> None:
    """``-0.0`` and ``0.0`` give the same bytes."""
    species = hostile.species[0]
    negated = species.model_copy(
        update={"coordinates_angstrom": [[-0.0, -0.0, -0.0], species.coordinates_angstrom[1]]}
    )
    changed = hostile.model_copy(update={"species": [negated, *hostile.species[1:]]})
    assert canonical_run_data_json(changed) == canonical_run_data_json(hostile)
