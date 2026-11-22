"""Suite-wide test policy: offline unit tests and the acceptance skip-to-fail switch (ADR-0019)."""

import os
from collections.abc import Generator

import pytest

ACCEPTANCE_ENV = "ETA_RXNCAT_ACCEPTANCE"
OFFLINE_ENV = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")


@pytest.fixture(autouse=True, scope="session")
def _offline_hubs() -> Generator[None]:
    """Keep Hugging Face downloads off for the whole session, restoring the old values after."""
    saved = {name: os.environ.get(name) for name in OFFLINE_ENV}
    for name in OFFLINE_ENV:
        os.environ[name] = "1"
    yield
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Under ``ETA_RXNCAT_ACCEPTANCE=1``, report a skipped test (setup or call) as failed."""
    report = yield
    enabled = os.environ.get(ACCEPTANCE_ENV) == "1"
    if enabled and report.skipped and report.when in ("setup", "call"):
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        report.outcome = "failed"
        report.longrepr = f"{ACCEPTANCE_ENV}=1: a skip is a failure in an acceptance run: {reason}"
    return report
