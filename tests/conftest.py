"""Suite-wide test policy: offline unit tests and the acceptance skip-to-fail switch (ADR-0019).

Under ``ETA_RXNCAT_ACCEPTANCE=1`` no test can pass by not running: setup and call skips, xfail
(either outcome) and collection-phase skips all fail the run (R8, R32).
"""

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


def _acceptance() -> bool:
    """Whether this is an acceptance run (``ETA_RXNCAT_ACCEPTANCE=1`` exactly)."""
    return os.environ.get(ACCEPTANCE_ENV) == "1"


def _skip_reason(longrepr: object) -> str:
    """Return the reason text of a skipped report's ``longrepr``."""
    return str(longrepr[2]) if isinstance(longrepr, tuple) else str(longrepr)


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(
    collector: pytest.Collector,
) -> Generator[None, pytest.CollectReport, pytest.CollectReport]:
    """Under ``ETA_RXNCAT_ACCEPTANCE=1``, report a skipped collector as a collection failure.

    A module-level ``pytest.skip(..., allow_module_level=True)`` or ``pytest.importorskip`` skips
    the module's collector; here it fails, naming the module, so the run exits non-zero (R32).
    """
    report = yield
    if _acceptance() and report.skipped:
        reason = _skip_reason(report.longrepr)
        report.outcome = "failed"
        report.longrepr = (
            f"{ACCEPTANCE_ENV}=1: {collector.nodeid or collector.name} was skipped at "
            f"collection, which is a failure in an acceptance run: {reason}"
        )
    return report


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Under ``ETA_RXNCAT_ACCEPTANCE=1``, report a skipped (setup or call) or xfail test as failed.

    An ``xfail`` test fails whether it xfailed or xpassed (R32); ``wasxfail`` is removed so the
    terminal and exit code count it as a failure.
    """
    report = yield
    if not _acceptance():
        return report
    if hasattr(report, "wasxfail"):
        reason = report.wasxfail
        del report.wasxfail
        report.outcome = "failed"
        report.longrepr = (
            f"{ACCEPTANCE_ENV}=1: an xfail test is a failure in an acceptance run "
            f"({report.when}): {reason}"
        )
    elif report.skipped and report.when in ("setup", "call"):
        reason = _skip_reason(report.longrepr)
        report.outcome = "failed"
        report.longrepr = f"{ACCEPTANCE_ENV}=1: a skip is a failure in an acceptance run: {reason}"
    return report
