# PROOF - OPR.0.7.0.15 Seed clash check and unintended-bond check

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

- Known-answer clash numbers and provenance: proof/15-execute.md "Known-answer clash numbers".
- Fake-engine tests (reason, detail, engine calls): proof/15-execute.md "Fake-engine tests".
- Old-fixture byte equality, `seed_checks=False` unchanged: proof/15-execute.md "Core and old records".
- Required checks exit 0: proof/15-execute.md "Commands".

## Artifacts

- proof/15-execute.md - guard CLEAR: sample 6 clash (4,21) 0.438 A ratio 0.409, member None; old fixtures byte-equal; ruff/mypy exit 0; full pytest 2642 passed
- proof/15-qa.md - qa PASS: sample 6 seed_clash (4,21) 0.438 A; 53/121 starts flagged, 0/68 used; 0 engine calls; pytest 2642 passed

## Residue / caveats

No engine run: the effect on the real units is measured by slice 17's reruns. Slice 16 renders the new reasons and details. TJ's Q-R7a/Q-R7b: this builds the defaults (A, A).
