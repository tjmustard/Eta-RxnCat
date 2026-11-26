## Context

TJ's v0.7.0 Q-A1 B: "At run time the TS ensemble runner falls through to the next template when a
seed fails TS validation. An EngineError still propagates." But ADR-0045 caches an engine crash
(`EngineRuntimeError`) as the completed row `failed_reason="engine_error"`, which the ensemble runner
returns as `seed:engine_error`. A rule of "fall through on any failed seed" would therefore present
a host fault as a template result. At the v0.6.0 release sha the seed strings are `seed:` plus
`ts_search_failed:<reason>`, `scf_convergence`, `engine_error`, `ts_validation_failed`,
`gate_failed:<gate>` or `face_undetermined`. `TS_VALIDATION_REASONS` appear only inside
`record.validation.reasons`.

## Decision

- A TS node of an enumerated candidate falls through to its next eligible template **only** on an
  allow-list of template faults:
  - `seed:ts_search_failed:{max_steps, too_many_rejections, mode_lost, no_reaction_mode}`;
  - `seed:ts_validation_failed`;
  - `seed:gate_failed:<any>`;
  - `seed:face_undetermined`;
  - `seed:face_mismatch_pathway` (the seed is not on the pathway's declared face, checked before and
    after the TS search).
- Every other reason **stops** the node as `stopped:<reason>`. That includes `seed:engine_error`,
  `seed:scf_convergence`, `seed:ts_search_failed:wall_time_exceeded`, `graft_pre_relax_timeout` and
  any unknown string. A live `EngineError` / `EngineUnavailableError` propagates.
- A test enumerates `TSSearchFailureReason`, so a new search reason fails until it is classified.
- Charged or open-shell candidates are refused before any engine run in v0.7.0
  (`charged_run_not_supported_v070`).

## Consequences

- A crash, an SCF failure or a stall is never relabelled as a fallback. The record shows where and
  why the node stopped.
- Some template-specific SCF failures stop where they could have fallen through. That is
  conservative by design, and TJ's text names TS validation only.
- The fallback adds no cache rows: its record is re-derived from the cached pre-relax, TS and
  frequency rows, so a rerun is all hits.
