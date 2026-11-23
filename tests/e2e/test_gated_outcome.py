"""R56: one gated_outcome decides the fragment's test_outcome and assert_checks_pass (slice 10)."""

from typing import Any

import pytest
from acceptance_record import record_verdict
from checks import assert_checks_pass, gated_outcome, outcome_fields

PASSING: dict[str, Any] = {
    "regression": {"status": "pass"},
    "accuracy": {"status": "pass"},
}


@pytest.fixture(autouse=True)
def _not_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ETA_RXNCAT_ACCEPTANCE", raising=False)


@pytest.mark.parametrize(
    ("checks", "named"),
    [
        ({**PASSING, "regression": {"status": "fail"}}, "regression"),
        ({**PASSING, "accuracy": {"status": "fail", "deltas": []}}, "accuracy"),
        ({**PASSING, "smiles_confirmation": {"status": "fail"}}, "smiles_confirmation"),
        ({**PASSING, "smiles_confirmation": "fail"}, "smiles_confirmation"),
        ({**PASSING, "tier_gates": {"window": {"status": "fail"}}}, "tier_gates.window"),
    ],
)
def test_failing_check_fails_and_is_named(checks: dict[str, Any], named: str) -> None:
    """Each gated failure gives "failed" naming it; the assertion raises from the same decision."""
    assert gated_outcome(checks) == ("failed", [named])
    assert outcome_fields(checks) == {"test_outcome": "failed", "failed_checks": [named]}
    with pytest.raises(AssertionError, match=named):
        assert_checks_pass(checks)


def test_passing_and_reported_checks_pass() -> None:
    """pass, reported and confirmed are not failures."""
    checks = {**PASSING, "accuracy": {"status": "reported"}, "smiles_confirmation": "confirmed"}
    assert gated_outcome(checks) == ("passed", [])
    assert_checks_pass(checks)


def test_pending_fails_only_under_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    """R22: pending_* is allowed before the gate and fails in the verdict run."""
    checks = {
        "regression": {"status": "pending_promotion"},
        "accuracy": {"status": "pending_reference"},
        "smiles_confirmation": "pending_confirmation",
    }
    assert gated_outcome(checks) == ("passed", [])
    monkeypatch.setenv("ETA_RXNCAT_ACCEPTANCE", "1")
    assert gated_outcome(checks) == (
        "failed",
        ["regression", "accuracy", "smiles_confirmation"],
    )
    with pytest.raises(AssertionError):
        assert_checks_pass(checks)


def _entry(**over: Any) -> dict[str, Any]:
    entry = {
        "test_outcome": "passed",
        "failed_checks": [],
        "regression": {"status": "pass"},
        "accuracy": {"verdict": "pass"},
    }
    return {**entry, **over}


def _fixtures(**over: dict[str, Any]) -> dict[str, dict[str, Any]]:
    names = ("hf1_butane", "hf2_diels_alder", "e2e5_t1", "e2e5_t2")
    fixtures = {
        n: {
            r: _entry(**({"smiles_confirmation": "confirmed"} if n.startswith("e2e5") else {}))
            for r in ("xtb", "uma")
        }
        for n in names
    }
    for key, entry in over.items():
        name, recipe = key.rsplit("__", 1)
        fixtures[name][recipe] = entry
    return fixtures


def test_record_verdict_pass_only_when_everything_passed() -> None:
    """All passed, nothing pending or missing: pass."""
    assert record_verdict(_fixtures()) == {"verdict": "pass", "verdict_reasons": []}


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        (
            {
                "hf1_butane__uma": _entry(
                    test_outcome="failed",
                    failed_checks=["regression"],
                    regression={"status": "fail"},
                )
            },
            "hf1_butane.uma: test_outcome failed ['regression']",
        ),
        ({"e2e5_t2__xtb": {"test_outcome": "missing"}}, "e2e5_t2.xtb: test_outcome missing"),
        (
            {"hf2_diels_alder__xtb": _entry(accuracy={"verdict": "pending_reference"})},
            "hf2_diels_alder.xtb: accuracy pending_reference",
        ),
        (
            {"e2e5_t1__uma": _entry(smiles_confirmation="fail")},
            "e2e5_t1.uma: smiles_confirmation fail",
        ),
        (
            {
                "e2e5_t2__uma": _entry(
                    smiles_confirmation="confirmed",
                    tier_gates={"window_dG_r_1M": {"status": "fail"}},
                )
            },
            "e2e5_t2.uma: tier_gates.window_dG_r_1M fail",
        ),
    ],
)
def test_record_verdict_fail_with_reasons(over: dict[str, Any], reason: str) -> None:
    """A failed, missing or pending fixture x recipe makes the record fail, with the reason."""
    verdict = record_verdict(_fixtures(**over))
    assert verdict["verdict"] == "fail"
    assert reason in verdict["verdict_reasons"]


def test_failed_tier_gate_fails_fragment_and_record() -> None:
    """A recorded T1/T2 tier gate at fail: outcome failed, named, and the record verdict fail."""
    tier = {"ordering_strans_below_scis": {"status": "fail"}, "planar": {"status": "pass"}}
    checks = {**PASSING, "smiles_confirmation": "confirmed", "tier_gates": tier}
    fields = outcome_fields(checks)
    assert fields == {
        "test_outcome": "failed",
        "failed_checks": ["tier_gates.ordering_strans_below_scis"],
    }
    entry = _entry(smiles_confirmation="confirmed", tier_gates=tier, **fields)
    verdict = record_verdict(_fixtures(e2e5_t1__xtb=entry))
    assert verdict["verdict"] == "fail"
    assert (
        "e2e5_t1.xtb: test_outcome failed ['tier_gates.ordering_strans_below_scis']"
        in verdict["verdict_reasons"]
    )
    assert "e2e5_t1.xtb: tier_gates.ordering_strans_below_scis fail" in verdict["verdict_reasons"]


def test_reported_tier_gate_passes() -> None:
    """The GFN2 T2 window is reported, not gated (TJ Q-E5): it does not fail anything."""
    tier = {"window_dG_r_1M": {"status": "reported"}}
    checks = {**PASSING, "smiles_confirmation": "confirmed", "tier_gates": tier}
    assert gated_outcome(checks) == ("passed", [])
    entry = _entry(smiles_confirmation="confirmed", tier_gates=tier)
    assert record_verdict(_fixtures(e2e5_t2__xtb=entry))["verdict"] == "pass"
