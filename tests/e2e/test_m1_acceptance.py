"""M1 regression and map-confirmation helpers against fake promoted fixtures (v0.4.0 slice 07).

Default suite; every promoted fixture here is a fake written to ``tmp_path`` (the repository's
``tests/fixtures/`` is never read or written).
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from m1 import (
    derive_map,
    load_m1,
    map_confirmation,
    product_payload,
    regression_graft,
    regression_relaxed,
)

from eta_rxncat.mapping import graft


@pytest.fixture(scope="module")
def graft_payload() -> dict[str, Any]:
    """The M1 pure graft in candidate form (the fields the graft regression compares)."""
    m1 = load_m1()
    result = graft(m1.template, m1.fragment, m1.spec)
    return {
        "product": product_payload(result.product),
        "index_map": [list(entry) for entry in result.index_map],
        "graft_to_ts1b_n_map": derive_map(result, m1.reference).graft_to_ts1b_n_map,
        "close_contacts": [c.model_dump() for c in result.close_contacts],
        "junctions": [j.model_dump() for j in result.junctions],
    }


@pytest.fixture(scope="module")
def relaxed_payload(graft_payload: dict[str, Any]) -> dict[str, Any]:
    """A relaxed-candidate stand-in: the graft geometry with an energy."""
    return {"relaxed_product": graft_payload["product"], "final_energy_hartree": -349.5}


def promote(directory: Path, name: str, payload: dict[str, Any]) -> Path:
    """Write a fake promoted fixture."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")
    return directory


def shifted(
    payload: dict[str, Any], key: str, atom: int, axis: int, delta: float
) -> dict[str, Any]:
    """A deep copy with one coordinate of ``payload[key]`` moved by ``delta`` Angstrom."""
    out = copy.deepcopy(payload)
    out[key]["coordinates_angstrom"][atom][axis] += delta
    return out


# --- regression_graft -----------------------------------------------------------------------


def test_regression_graft_pending_when_absent(
    graft_payload: dict[str, Any], tmp_path: Path
) -> None:
    """No promoted m1_graft.json: pending_promotion."""
    assert regression_graft(graft_payload, tmp_path) == {"status": "pending_promotion"}


def test_regression_graft_pass_on_identical(graft_payload: dict[str, Any], tmp_path: Path) -> None:
    """An identical promoted graft passes with coordinate RMSD 0."""
    result = regression_graft(graft_payload, promote(tmp_path, "m1_graft.json", graft_payload))
    assert result["status"] == "pass" and result["coordinate_rmsd_angstrom"] == 0.0


def test_regression_graft_fails_on_1e_9_shift(
    graft_payload: dict[str, Any], tmp_path: Path
) -> None:
    """A 1e-9 Angstrom shift of one atom exceeds the 1e-10 Angstrom bound (no superposition)."""
    promoted = shifted(graft_payload, "product", 7, 0, 1e-9)
    result = regression_graft(graft_payload, promote(tmp_path, "m1_graft.json", promoted))
    assert result["status"] == "fail" and result["mismatches"] == ["coordinates"]


@pytest.mark.parametrize(
    ("key", "mismatch"),
    [
        ("graft_to_ts1b_n_map", "graft_to_ts1b_n_map"),
        ("index_map", "index_map"),
        ("close_contacts", "close_contacts"),
        ("junctions", "junction_signs"),
    ],
)
def test_regression_graft_fails_on_changed_entry(
    graft_payload: dict[str, Any], tmp_path: Path, key: str, mismatch: str
) -> None:
    """A changed map entry, index_map entry, contact pair or junction sign fails exactly."""
    promoted = copy.deepcopy(graft_payload)
    if key == "graft_to_ts1b_n_map":
        promoted[key][7], promoted[key][8] = promoted[key][8], promoted[key][7]
    elif key == "index_map":
        promoted[key][15] = ["fragment", 9]
    elif key == "close_contacts":
        promoted[key][0]["j"] = 16
    else:
        promoted[key][0]["sign"] = 1
    result = regression_graft(graft_payload, promote(tmp_path, "m1_graft.json", promoted))
    assert result["status"] == "fail" and result["mismatches"] == [mismatch]


# --- regression_relaxed ---------------------------------------------------------------------


def test_regression_relaxed_pending_when_absent(
    relaxed_payload: dict[str, Any], tmp_path: Path
) -> None:
    """No promoted m1_relaxed.<recipe>.json: pending_promotion."""
    assert regression_relaxed(relaxed_payload, "xtb", tmp_path) == {"status": "pending_promotion"}


def test_regression_relaxed_pass_within_bounds(
    relaxed_payload: dict[str, Any], tmp_path: Path
) -> None:
    """A rigid motion plus 5e-6 Eh and a 1e-3 A heavy-atom shift pass (Horn over heavy atoms)."""
    promoted = copy.deepcopy(relaxed_payload)
    coords = promoted["relaxed_product"]["coordinates_angstrom"]
    promoted["relaxed_product"]["coordinates_angstrom"] = [[-y, x, z + 3.0] for x, y, z in coords]
    promoted = shifted(promoted, "relaxed_product", 0, 2, 1e-3)
    promoted["final_energy_hartree"] += 5e-6
    result = regression_relaxed(
        relaxed_payload, "uma", promote(tmp_path, "m1_relaxed.uma.json", promoted)
    )
    assert result["status"] == "pass", result
    assert result["heavy_atom_rmsd_angstrom"] < 1e-3


@pytest.mark.parametrize(
    ("energy", "shift", "mismatches"),
    [
        (2e-5, 0.0, ["energy"]),
        (0.0, 0.1, ["heavy_atom_rmsd"]),
        (2e-5, 0.1, ["energy", "heavy_atom_rmsd"]),
    ],
)
def test_regression_relaxed_fails_beyond_bounds(
    relaxed_payload: dict[str, Any],
    tmp_path: Path,
    energy: float,
    shift: float,
    mismatches: list[str],
) -> None:
    """|dE| > 1e-5 Eh or heavy-atom RMSD > 0.01 A fails, each named."""
    promoted = shifted(relaxed_payload, "relaxed_product", 0, 0, shift)
    promoted["final_energy_hartree"] += energy
    result = regression_relaxed(
        relaxed_payload, "xtb", promote(tmp_path, "m1_relaxed.xtb.json", promoted)
    )
    assert result["status"] == "fail" and result["mismatches"] == mismatches


# --- map_confirmation -----------------------------------------------------------------------


def test_map_confirmation_states(graft_payload: dict[str, Any], tmp_path: Path) -> None:
    """Pending when absent; confirmed when equal; fail when the promoted map differs."""
    yaml_map = load_m1().config["graft_to_ts1b_n_map"]
    assert map_confirmation(yaml_map, tmp_path) == "pending_confirmation"
    promote(tmp_path, "m1_graft.json", graft_payload)
    assert map_confirmation(yaml_map, tmp_path) == "confirmed"
    changed = copy.deepcopy(graft_payload)
    changed["graft_to_ts1b_n_map"][0], changed["graft_to_ts1b_n_map"][4] = 4, 0
    promote(tmp_path, "m1_graft.json", changed)
    assert map_confirmation(yaml_map, tmp_path) == "fail"


def test_map_confirmation_ignores_status_fields(
    graft_payload: dict[str, Any], tmp_path: Path
) -> None:
    """The promoted file's own status fields are never read (R25)."""
    yaml_map = load_m1().config["graft_to_ts1b_n_map"]
    promoted = {**graft_payload, "test_outcome": "failed", "status": "fail"}
    promote(tmp_path, "m1_graft.json", promoted)
    assert map_confirmation(yaml_map, tmp_path) == "confirmed"
