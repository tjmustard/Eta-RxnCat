"""Regression and accuracy statuses for a fixture run, with the acceptance rule for pending_*."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from derived import accuracy
from e2e_env import PROMOTED, acceptance
from reference_values import load_reference_file
from regression import compare


def regression_status(fixture: str, recipe: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compare with ``tests/fixtures/v0.3.0/<fixture>.<recipe>.json`` if promoted, else pending."""
    promoted = PROMOTED / f"{fixture}.{recipe}.json"
    if not promoted.exists():
        return {"status": "pending_promotion"}
    return compare(payload, json.loads(promoted.read_text(encoding="utf-8")))


def reference() -> dict[str, Any] | None:
    """The promoted reference values (fixtures mode), or ``None`` before promotion."""
    path = PROMOTED / "reference_values.json"
    return load_reference_file(path, fixtures_mode=True) if path.exists() else None


def checks(
    fixture: str,
    recipe: str,
    payload: Mapping[str, Any],
    observed: Mapping[str, float] | None,
    sigmas: Mapping[str, int],
) -> dict[str, Any]:
    """Regression and accuracy; under ETA_RXNCAT_ACCEPTANCE=1 any pending_* fails the test.

    ``observed=None``: the fixture has no reference-values entries (T1/T2 compare with literature
    values in their own derived block), so accuracy is ``reported``.
    """
    acc = (
        {"status": "reported", "deltas": [], "note": "no reference_values entries for this fixture"}
        if observed is None
        else accuracy(observed, sigmas, reference(), recipe=recipe)
    )
    result = {"regression": regression_status(fixture, recipe, payload), "accuracy": acc}
    pending = [k for k, v in result.items() if str(v["status"]).startswith("pending_")]
    if pending and acceptance():
        pytest.fail(f"{fixture}.{recipe}: {pending} pending in an acceptance run")
    return result


def assert_checks_pass(result: Mapping[str, Any]) -> None:
    """A regression or gated accuracy failure fails the test (R26)."""
    assert result["regression"]["status"] != "fail", result["regression"]
    assert result["accuracy"]["status"] != "fail", result["accuracy"]


def write(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a candidate (never read back)."""
    from eta_rxncat.orchestrator import write_report

    write_report(path, payload)
