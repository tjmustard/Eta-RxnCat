# PROOF - OPR.0.7.1.3 Public per-sample stage keys on TSEnsembleRun and the defd982 unit test

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

All in `proof/03-execute.md` (builder evidence, not a QA verdict):

- targeted pytest (requirements 1, 3): "Requirement 1" and "Requirement 3";
- the private-import grep and listing (requirement 2): "Requirement 2";
- host check, command, `/usr/bin/time -v` and `cmp` exit 0 (requirement 4): "Requirement 4";
- required checks (requirement 5): "Requirement 5".

## Artifacts

- proof/03-execute.md - guard CLEAR: full pytest 2763 passed; parity runrecord cmp exit 0, 0 engine calls; ruff/format/mypy exit 0
- proof/03-qa.md - qa PASS: parity runrecord cmp exit 0 (0 engine calls); full pytest 2763 passed; ruff/format/mypy exit 0; clashed break exit 1

## Residue / caveats

The parity rerun reads cached rows from a copied store; no real-engine run covers the new
keys on a fresh store. See "For the auditor to rule on" in `proof/03-execute.md`.
