# PROOF - OPR.0.7.0.12 v0.7.0 fallback E2E (G8)

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

- Per unit host check, env, `FallbackRecord`, gates, second-pass counts: proof/12-execute.md "Per unit", "Commands" (graft_time gates per lead ruling A, row qitem-20261126124248-0826c9cd).
- `git show --stat` of the candidate-only commit (243b619): proof/12-execute.md.
- Required checks exit 0: proof/12-execute.md "Required checks".

## Artifacts

- proof/12-execute.md - guard CLEAR: 3/3 fallback units pass 9 gates (GFN2 gated, UMA reported); rank-1 TS-search calls 0; second passes 0 calls; full pytest 2563 passed
- proof/12-qa.md - qa PASS: G8 on GFN2: both constructs pick rank 2 with rank 1 reason; rank-1 TS-search 0; audit reruns identical (slice 11 dG 13.560206712557633; slice 12 run_time 391 calls); pytest 2563

## Residue / caveats

Chemistry is reported only; no barrier in fallback units; TJ's Phase 3 follows slice 13. Host load during a unit was not monitored.
