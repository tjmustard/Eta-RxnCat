## Context

The UMA TS1b_x(graft) ensemble pre-relaxation stalled in 3 of 13 runs at the same inputs (mission
HF-13). Six faulthandler dumps, filtered to eta frames plus a count of geomeTRIC frames, show a live
loop inside the injected geomeTRIC black box. The loop runs numpy eigh/svd between engine calls,
with no engine frame and an idle GPU. eta's `maxiter` does not bound it, and eta seeds geomeTRIC's
RNG, so the trigger is run-to-run engine noise. The optimizer runs in-process (ADR-0024).

## Decision

The ensemble pre-relaxation runs under an in-process wall-time budget (default 600 s, about 12× the
healthy maximum).
- A watchdog thread raises `PreRelaxTimeout`, a `BaseException`, into the calling thread with
  `PyThreadState_SetAsyncExc`. It re-sends every second until the guarded call exits and clears
  any pending exception on exit.
- The member is excluded as `pre_relax_failed:PreRelaxTimeout` with its wall time, the failure row
  is cached, and the ensemble continues.
- The optimizer stays in-process; ADR-0024 is unchanged. P-RFO is not guarded.

## Consequences

- A stall costs at most the budget and can no longer hang an E2E, acceptance or verdict run.
- The cause stays inside the black box. A cached timeout persists in that store; a fresh store
  retries.
- The mechanism is CPython-specific and stdlib-only, and it can only interrupt Python-level
  progress. A stall inside one native call would need an out-of-process optimizer, which is a new
  decision against ADR-0024.
