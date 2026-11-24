"""``t3.regression_ts``: a case against its promoted fixture under TJ's R33 bounds (slice 13)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from t3 import REGRESSION_BOUNDS, regression_ts

STATE = {
    "symbols": ["C", "C", "N", "O", "H"],
    "coordinates": [[0, 0, 0], [1.5, 0, 0], [0, 1.4, 0], [0, 0, 1.2], [2, 1, 0]],
}


def payload(
    de: float = 0.0, dg: float = 0.0, dy: float = 0.0, case: str = "ts3a"
) -> dict[str, Any]:
    """A candidate payload's compared parts, shifted by ``de`` Eh, ``dg`` kcal/mol, ``dy`` Å."""
    state = copy.deepcopy(STATE)
    state["coordinates"][1][1] += dy
    return {
        "case": case,
        "ts": {
            "state": state,
            "thermo": {"electronic_energy_hartree": -491.5 + de},
            "search_history": [{"step": len(str(dy))}],
        },
        "barrier": {"dG_dagger_1M_kcal_mol": 22.19 + dg},
    }


def promote(tmp_path: Path, recipe: str, data: dict[str, Any]) -> Path:
    """Write ``data`` as the promoted ``t3_<case>.<recipe>.json`` under ``tmp_path``."""
    (tmp_path / f"t3_{data['case']}.{recipe}.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def test_bounds_are_tj_r33() -> None:
    """|ΔE| 1e-5 Eh and RMSD 0.01 Å on both; ΔΔG‡ 0.75 on UMA, 0.01 on xtb."""
    for recipe in ("xtb", "uma"):
        assert REGRESSION_BOUNDS[recipe]["abs_delta_ts_energy_hartree"] == 1e-5
        assert REGRESSION_BOUNDS[recipe]["heavy_rmsd_angstrom"] == 0.01
    assert REGRESSION_BOUNDS["uma"]["abs_delta_dG_dagger_1M_kcal_mol"] == 0.75
    assert REGRESSION_BOUNDS["xtb"]["abs_delta_dG_dagger_1M_kcal_mol"] == 0.01


def test_pending_without_fixture(tmp_path: Path) -> None:
    """No promoted file: ``pending_promotion``."""
    assert regression_ts(payload(), "uma", promoted_dir=tmp_path) == {"status": "pending_promotion"}


def test_identical_passes_and_history_is_ignored(tmp_path: Path) -> None:
    """Equal values pass; a different ``search_history`` is never compared (N11)."""
    old = payload()
    old["ts"]["search_history"] = [{"step": 99}]
    result = regression_ts(payload(), "xtb", promoted_dir=promote(tmp_path, "xtb", old))
    assert result["status"] == "pass" and result["mismatches"] == []
    assert result["heavy_rmsd_angstrom"] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize(
    ("recipe", "shift", "status", "mismatch"),
    [
        ("uma", {"dg": 0.5}, "pass", None),
        ("uma", {"dg": 0.8}, "fail", "abs_delta_dG_dagger_1M_kcal_mol"),
        ("xtb", {"dg": 0.005}, "pass", None),
        ("xtb", {"dg": 0.05}, "fail", "abs_delta_dG_dagger_1M_kcal_mol"),
        ("uma", {"de": 2e-5}, "fail", "abs_delta_ts_energy_hartree"),
        ("xtb", {"de": 5e-6}, "pass", None),
        ("uma", {"dy": 0.2}, "fail", "heavy_rmsd_angstrom"),
    ],
)
def test_bounds_per_recipe(
    tmp_path: Path, recipe: str, shift: dict[str, float], status: str, mismatch: str | None
) -> None:
    """Each quantity against its R33 bound on its recipe."""
    result = regression_ts(
        payload(**shift), recipe, promoted_dir=promote(tmp_path, recipe, payload())
    )
    assert result["status"] == status
    assert result["mismatches"] == ([] if mismatch is None else [mismatch])


def test_missing_value_fails(tmp_path: Path) -> None:
    """A value one side lacks (no barrier) is a mismatch, never a pass."""
    new = payload()
    new["barrier"] = None
    result = regression_ts(new, "uma", promoted_dir=promote(tmp_path, "uma", payload()))
    assert result["status"] == "fail"
    assert result["mismatches"] == ["abs_delta_dG_dagger_1M_kcal_mol: missing"]


def test_report_only_is_reported(tmp_path: Path) -> None:
    """GFN2 TS4a (R32): compared and recorded, status ``reported`` whatever the values."""
    new = payload(dg=5.0, case="ts4a")
    result = regression_ts(
        new, "xtb", report_only=True, promoted_dir=promote(tmp_path, "xtb", payload(case="ts4a"))
    )
    assert result["status"] == "reported"
    assert result["mismatches"] == ["abs_delta_dG_dagger_1M_kcal_mol"]
