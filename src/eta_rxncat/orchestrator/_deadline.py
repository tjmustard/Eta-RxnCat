"""A wall-time deadline for a stalled pre-relaxation (v0.6.0, slice 13; mission R28, HF-13).

geomeTRIC can spin in a live numpy loop that no ``maxiter`` bounds. ``deadline`` interrupts the
calling thread after a budget by raising ``PreRelaxTimeout`` into it (CPython, stdlib only).
"""

import ctypes
import math
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager

_RESEND_INTERVAL_S = 1.0
MAX_EFFECTIVE_BUDGET_S = 1200.0
"""The ceiling of a load-scaled budget, in seconds (v0.7.0, R7; the per-command bound)."""
BUDGET_KIND = "load_scaled_wall"
"""What a recorded budget means (v0.7.0, R7)."""


class PreRelaxTimeout(BaseException):  # noqa: N818 - a deadline signal, not an error
    """The pre-relaxation exceeded its wall budget.

    It derives from ``BaseException`` so a broad ``except Exception`` inside the guarded code
    cannot swallow it.
    """


def validate_budget(budget_s: float | None) -> None:
    """Raise ``ValueError`` unless ``budget_s`` is ``None`` or a finite positive number."""
    if budget_s is None:
        return
    if not math.isfinite(budget_s) or budget_s <= 0:
        raise ValueError(f"pre-relax budget must be a finite number > 0 or None, got {budget_s!r}")


def effective_budget_s(base_s: float) -> tuple[float, float]:
    """Scale a wall budget by the host load, read once (v0.7.0, R7).

    The guard bounds a stall, not slow progress on a busy host. A process-CPU budget is not used,
    because xtb runs many threads.

    Args:
        base_s: The budget on an idle host, in seconds.

    Returns:
        ``(min(1200, base_s * max(1, load1 / n_cpu)), load1)``.
    """
    load1 = os.getloadavg()[0]
    scale = max(1.0, load1 / (os.cpu_count() or 1))
    return min(MAX_EFFECTIVE_BUDGET_S, base_s * scale), load1


def _send(thread_id: int, exception: type[BaseException] | None) -> None:
    # ``None`` must reach C as NULL (which clears), so it is not wrapped in ``py_object``.
    payload = None if exception is None else ctypes.py_object(exception)
    ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), payload)


@contextmanager
def deadline(budget_s: float | None) -> Iterator[None]:
    """Raise ``PreRelaxTimeout`` into the calling thread if the block outlives ``budget_s``.

    A watchdog thread waits ``budget_s``, then re-sends the exception every second until the
    block exits, which covers a loop that swallows one. On exit (normal or not) the watchdog is
    stopped and joined and any undelivered exception is cleared, so none arrives after the block.

    Args:
        budget_s: The wall budget in seconds; ``None`` means no guard and no thread.

    Raises:
        ValueError: ``budget_s`` is not ``None`` and not a finite number greater than zero.
        PreRelaxTimeout: The block ran past the budget.
    """
    validate_budget(budget_s)
    if budget_s is None:
        yield
        return
    thread_id = threading.get_ident()
    done = threading.Event()

    def watch() -> None:
        if done.wait(budget_s):
            return
        while not done.is_set():
            _send(thread_id, PreRelaxTimeout)
            done.wait(_RESEND_INTERVAL_S)

    watchdog = threading.Thread(target=watch, name="pre-relax-deadline", daemon=True)
    watchdog.start()
    try:
        yield
    finally:
        # Stop the sender first, join it (no send can follow), then clear what is pending. An
        # exception that lands inside this cleanup is absorbed and the steps repeat; they are
        # idempotent.
        while True:
            try:
                done.set()
                watchdog.join()
                _send(thread_id, None)
                break
            except PreRelaxTimeout:
                continue
