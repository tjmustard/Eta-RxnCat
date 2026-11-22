# Progress - 09-store-first-open

> Current state and retained outcomes for this slice. `hyper_spec.py progress` regenerates
> "Current state" and appends to "Outcomes"; never rewrite an Outcomes line.

## Current state

<!-- BEGIN HACF GENERATED: current-state -->
- hacf_status: blocked
- status: active
- last event: 2026-11-22T15:18:20+00:00 blocked
<!-- END HACF GENERATED: current-state -->

## Outcomes

- 2026-11-22T13:24:17+00:00 compiled - created by hyper_scope.py slice create
- 2026-11-22T15:15:35+00:00 executing
- 2026-11-22T15:18:20+00:00 blocked - Deadline proof bullet is contradictory (lead -> resolve). Under a BEGIN EXCLUSIVE holder the step-4 user_version read blocks for busy_timeout and fails at 5.007 s with a raw OperationalError before the WAL retry runs. Under BEGIN IMMEDIATE the read succeeds at 0.000 s and journal_mode=WAL fails at once with SQLITE_BUSY. The retry/deadline proofs and the final open order wait on resolve.
