## Context

ADR-0048 bounds one ensemble pre-relax at 600 s of wall time and lets the ensemble continue. In
v0.7.0 two things changed:
- **Worst case.** An ensemble guards up to one graft pre-relax plus `max_research` (10) sample
  pre-relaxes, so its worst-case stall is about 6600 s, beyond the 3600 s command timeout (red team
  F4).
- **Load.** The v0.6.0 slice-12 audit found the guard host-load sensitive: deterministic GFN2
  pre-relaxes timed out at 1.8–3.7× their healthy wall time on a loaded host.

Resolve measured GFN2 xtb using about 14 cores (3333 s CPU in 234 s wall), so a process-CPU budget
would fire about 14× early. TJ's Q-A2 A keeps the 600 s guard and ADR-0024 unchanged, keeps the E2E
small, and reports the stall rate and time lost.

## Decision

- **Stall cap.** `max_pre_relax_timeouts` (k) is a keyword on `run_ts_ensemble_detailed`. It is not
  an options field, so v0.6.0 records are unchanged. `None` keeps v0.6.0 behaviour; the v0.7.0
  fallback runner passes 2. After k timeouts the ensemble stops sampling and keeps its members, and
  `stall_cap_reached_bool` is recorded. That **reports, not stops**: the seed is already a member.
  A timeout of the graft pre-relax, before any seed exists, still stops the node.
- **Load-scaled budget (amends ADR-0048's budget).**
  - The effective budget is `min(1200, 600 × max(1, load1 / n_cpu))`, read once at guard entry.
  - Each timeout row records `budget_s`, `load1` and `budget_kind`.
  - The 600 s base, the in-process watchdog and ADR-0024 are unchanged.
- **Measure first.** The slice that implements this measures healthy pre-relax wall against
  `load1` first, idle and loaded, and stops if the scaled budget still cuts a healthy run.

## Consequences

- The worst case per (R × pathway × engine) command is bounded: healthy maximum + one graft budget
  + k × budget. Measured (v0.7.0 HF-3): the healthy maximum command is 1170 s, so the bound is
  2970 s at the 600 s base, inside `timeout 3600`, and 5355 s at the 1200 s cap. The E2E unit
  commands therefore run under `timeout 5400`.
- A loaded host gets proportionally more time. The guard still catches a true stall, which makes no
  progress at any load.
- A capped ensemble can have fewer members than an uncapped one. The record says so, and ΔΔG‡ is
  reported only.
