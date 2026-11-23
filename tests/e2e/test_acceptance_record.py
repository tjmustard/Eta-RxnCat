"""The committed v0.3.0 acceptance record parses and follows its schema (slice 09)."""

import json
from pathlib import Path

import pytest
from acceptance_record import FIXTURES, RECIPES, VERDICTS, check, known_limits

RECORD = Path(__file__).resolve().parents[2] / "docs" / "prd" / "v0.3.0" / "ACCEPTANCE_RESULT.json"


def record() -> dict:  # type: ignore[type-arg]
    """The committed record."""
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_record_parses_and_is_complete() -> None:
    """Every fixture x recipe, every required key, only allowed verdict values."""
    data = record()
    assert data["record_schema"] == 1
    assert check(data) == []
    assert sorted(data["fixtures"]) == sorted(FIXTURES)
    for name in FIXTURES:
        assert sorted(data["fixtures"][name]) == sorted(RECIPES)


def test_record_verdicts_are_allowed_and_pre_promotion() -> None:
    """Before TJ's Phase 3 gate (R22) the TJ-dependent verdicts are pending."""
    data = record()
    for name in FIXTURES:
        for recipe in RECIPES:
            entry = data["fixtures"][name][recipe]
            assert entry["regression"]["status"] in VERDICTS["regression"]
            assert entry["accuracy"]["verdict"] in VERDICTS["accuracy"]
            assert entry["accuracy"]["gating_level"] == "wb97mv_def2tzvpd//b3lyp_631gss"
            if name.startswith("e2e5"):
                assert entry["smiles_confirmation"] in VERDICTS["smiles_confirmation"]


def test_record_known_limits_carry_the_fixed_lines() -> None:
    """R47 and R50 lines are present; no gated failure is listed as a limit (R26)."""
    data = record()
    limits = data["known_limits"]
    assert any(line.startswith("accuracy compares per-conformer quantities") for line in limits)
    assert any("(R50)" in line for line in limits)
    assert limits == known_limits(data["fixtures"])
    assert data["fixtures"]["e2e5_t2"]["uma"]["window"]["inside"] is True


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda d: d["fixtures"]["e2e5_t1"].pop("uma"), "missing fixtures.e2e5_t1.uma"),
        (
            lambda d: d["fixtures"]["hf1_butane"]["xtb"]["regression"].update(status="ok"),
            "regression",
        ),
        (
            lambda d: d["fixtures"]["hf2_diels_alder"]["uma"].pop("species_stage_cache"),
            "species_stage_cache",
        ),
        (lambda d: d.pop("known_limits"), "missing known_limits"),
    ],
)
def test_check_rejects(mutate: object, fragment: str) -> None:
    """The schema check catches a missing recipe, a bad verdict, a missing block or key."""
    data = record()
    mutate(data)  # type: ignore[operator]
    assert any(fragment in p for p in check(data)), check(data)
