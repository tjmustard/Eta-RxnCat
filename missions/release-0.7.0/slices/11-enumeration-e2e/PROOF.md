# PROOF - OPR.0.7.0.11 v0.7.0 enumeration E2E (G7)

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

- Per unit host check, env, wall/CPU/RSS, gates, second-pass counts: proof/11-qa.md "Per unit", "Commands", "Host".
- `git show --stat` of the candidate-only commit (dd99d1c): proof/11-qa.md.
- Required checks exit 0: proof/11-qa.md "Required checks".

## Artifacts

- proof/11-qa.md - qa PASS: 8/8 units pass 9 G7 gates on GFN2 and UMA; 4 scores finite; 0-call second passes; full pytest 2563 passed
- proof/11-audit-qa.md - qa PASS: 8/8 units 9/9 G7 gates; ethyl endo GFN2 rerun identical (13.5602 kcal/mol, 694/0 calls); full pytest 2563 passed

## Residue / caveats

Chemistry is reported only (Q-A3); TJ's Phase 3 follows slice 13. Host load during a unit was not monitored.
