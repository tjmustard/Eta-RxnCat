"""Tier-D: t3 writes the v0.5.0 acceptance record's ``gated_on`` text for every case (R10)."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from e2e_env import REPO
from fixtures import t3
from t3 import reported_block

RECORD = REPO / "docs" / "prd" / "v0.5.0" / "ACCEPTANCE_RESULT.json"
CASES = {
    "n4": "t3_n4_unmapped.yaml",
    "ts1a_n": "t3_ts1a_n_unmapped.yaml",
    "ts1b_n": "t3_ts1b_n_mapped.yaml",
    "ts3a": "t3_ts3a_unmapped.yaml",
    "ts4a": "t3_ts4a_mapped.yaml",
}


def unconverged_run() -> Any:
    """A stand-in CaseRun with no search, validation or barrier: ``gated_on`` needs none."""
    ts = SimpleNamespace(
        search=None,
        validation=None,
        record=None,
        connectivity_equal_bool=None,
        failed_reason="ts_search_failed:max_steps",
    )
    return SimpleNamespace(ts=ts, barrier=None, barrier_error=None)


def test_the_record_holds_exactly_these_cases() -> None:
    """The case list is the record's own, so no case goes unchecked."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert set(record["fixtures"]["t3"]) == set(CASES)


@pytest.mark.parametrize("recipe_name", ["xtb", "uma"])
@pytest.mark.parametrize("case", list(CASES))
def test_gated_on_text_equals_the_record(case: str, recipe_name: str) -> None:
    """The text ``reported_block`` writes equals the committed record's, per case and recipe."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    expected = record["fixtures"]["t3"][case][recipe_name]["reported"]["gated_on"]
    block = reported_block(recipe_name, t3(CASES[case]), unconverged_run(), [])
    assert block["gated_on"] == expected
