"""Regression and accuracy statuses for a fixture run, with the acceptance rule for pending_*."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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
    return {"regression": regression_status(fixture, recipe, payload), "accuracy": acc}


GATED_CHECKS = ("regression", "accuracy", "smiles_confirmation", "tier_gates")
"""The checks ``gated_outcome`` reads (R56); ``tier_gates`` is ``{name: {"status": ...}}``."""


def gated_outcome(result: Mapping[str, Any]) -> tuple[str, list[str]]:
    """A fixture run's outcome from its checks (R56): ``("passed", [])`` or ``("failed", names)``.

    Every gated check whose status is ``fail`` is named: regression, accuracy,
    ``smiles_confirmation`` (T1/T2) and any recorded tier gate. Under ``ETA_RXNCAT_ACCEPTANCE=1``
    a ``pending_*`` status fails too (R22: the verdict run settles every pending state). The
    fragment's ``test_outcome``/``failed_checks`` and ``assert_checks_pass`` both come from here,
    so they cannot disagree.
    """

    def status(value: Any) -> str:
        return str(value["status"]) if isinstance(value, Mapping) else str(value)

    statuses: list[tuple[str, str]] = []
    for name in ("regression", "accuracy", "smiles_confirmation"):
        if name in result:
            statuses.append((name, status(result[name])))
    for gate, value in sorted(result.get("tier_gates", {}).items()):
        statuses.append((f"tier_gates.{gate}", status(value)))
    failed = [
        name
        for name, status in statuses
        if status == "fail" or (acceptance() and status.startswith("pending_"))
    ]
    return ("failed", failed) if failed else ("passed", [])


def outcome_fields(result: Mapping[str, Any]) -> dict[str, Any]:
    """The fragment's ``test_outcome`` and ``failed_checks`` (from ``gated_outcome``)."""
    outcome, failed = gated_outcome(result)
    return {"test_outcome": outcome, "failed_checks": failed}


def assert_checks_pass(result: Mapping[str, Any]) -> None:
    """Fail the test when ``gated_outcome`` does (R26, R56)."""
    outcome, failed = gated_outcome(result)
    assert outcome == "passed", f"gated checks failed: {failed}; {dict(result)}"


def write(path: Path, payload: Mapping[str, Any]) -> None:
    """Write a candidate (never read back)."""
    from eta_rxncat.orchestrator import write_report

    write_report(path, payload)
