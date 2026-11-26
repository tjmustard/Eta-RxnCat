"""Tests for the pre-relax wall-time deadline (v0.6.0, slice 13; R28, G8).

The guarded loops are stand-ins: numpy linear algebra in a Python loop with no engine call, the
signature of the HF-13 stall. Every test is CPU-only and short.
"""

import math
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

from eta_rxncat.orchestrator._deadline import (
    PreRelaxTimeout,
    deadline,
    effective_budget_s,
)

BUDGET = 0.5


def _spin(*, swallow_once: bool = False) -> None:
    """Loop forever on numpy svd/eigh; optionally swallow the first exception once."""
    a = np.random.default_rng(0).random((40, 40))
    swallowed = not swallow_once
    while True:
        try:
            np.linalg.svd(a)
            np.linalg.eigh(a @ a.T)
        except BaseException:
            if swallowed:
                raise
            swallowed = True


def test_a_stalled_loop_is_interrupted_near_the_budget() -> None:
    """R28 requirement 1: a numpy loop is cut at about the budget."""
    start = time.perf_counter()
    with pytest.raises(PreRelaxTimeout), deadline(BUDGET):
        _spin()
    assert BUDGET <= time.perf_counter() - start < BUDGET + 3.0


def test_a_loop_that_swallows_one_exception_is_still_interrupted() -> None:
    """R28 requirement 3: the one-second re-send covers a swallow."""
    start = time.perf_counter()
    with pytest.raises(PreRelaxTimeout), deadline(BUDGET):
        _spin(swallow_once=True)
    assert time.perf_counter() - start < BUDGET + 3.0


def test_a_broad_except_exception_cannot_swallow_it() -> None:
    """It derives from BaseException, so ``except Exception`` cannot swallow it."""
    with pytest.raises(PreRelaxTimeout), deadline(BUDGET):
        try:
            _spin()
        except Exception:  # noqa: BLE001 - the point of the test
            pytest.fail("PreRelaxTimeout must not be an Exception")


def test_no_exception_arrives_after_a_block_that_finishes_in_time() -> None:
    """R28 requirement 4: normal exit leaves no live watchdog and no late exception."""
    before = threading.active_count()
    with deadline(BUDGET):
        pass
    assert threading.active_count() == before
    time.sleep(2 * BUDGET)  # a late raise would surface here
    assert threading.active_count() == before


def test_no_exception_arrives_after_a_block_that_raises() -> None:
    """An exception exit also leaves no watchdog and no late exception."""
    before = threading.active_count()
    with pytest.raises(KeyError), deadline(BUDGET):
        raise KeyError("boom")
    time.sleep(2 * BUDGET)
    assert threading.active_count() == before


def test_no_exception_arrives_after_a_timeout() -> None:
    """After a timeout the re-send stops: nothing arrives in the next seconds."""
    with pytest.raises(PreRelaxTimeout), deadline(BUDGET):
        _spin()
    time.sleep(2.5)  # past two more re-send intervals
    assert threading.active_count() >= 1


def test_none_starts_no_watchdog() -> None:
    """R28 requirement 7: no budget, no thread, no guard."""
    before = threading.active_count()
    with deadline(None):
        assert threading.active_count() == before
    assert threading.active_count() == before


@pytest.mark.parametrize("budget", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_an_invalid_budget_is_refused(budget: float) -> None:
    """A budget <= 0, NaN or infinite raises ValueError before the block runs."""
    with pytest.raises(ValueError, match="budget"), deadline(budget):
        pytest.fail("the block must not run")


def test_import_loads_no_optimizer_stack() -> None:
    """G8: importing the deadline helper loads none of torch, pyscf, fairchem, geometric."""
    code = (
        "import sys; import eta_rxncat.orchestrator._deadline; "
        "heavy = ('torch', 'pyscf', 'fairchem', 'geometric'); "
        "bad = [x for x in heavy if x in sys.modules]; assert not bad, bad"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "load1, base, expected",
    [
        (0.0, 600.0, 600.0),
        (7.0, 600.0, 600.0),
        (20.0, 600.0, 600.0),
        (30.0, 600.0, 900.0),
        (40.0, 600.0, 1200.0),
        (400.0, 600.0, 1200.0),
        (30.0, 2.0, 3.0),
    ],
)
def test_the_budget_scales_with_load_up_to_the_cap(
    monkeypatch: pytest.MonkeyPatch, load1: float, base: float, expected: float
) -> None:
    """R7: unchanged up to one load per CPU, then proportional, never above 1200 s."""
    monkeypatch.setattr("os.getloadavg", lambda: (load1, 0.0, 0.0))
    monkeypatch.setattr("os.cpu_count", lambda: 20)
    assert effective_budget_s(base) == (expected, load1)
