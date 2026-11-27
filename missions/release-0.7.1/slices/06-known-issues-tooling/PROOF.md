# PROOF - OPR.0.7.1.6 Known issues in tooling and test text (R10, R11, R28, R39, R40)

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

All in `proof/06-execute.md` (builder evidence, not a QA verdict):

- R10, R11, R39, R40 test ids, failing output at `bf7b949`, passing after (requirements 1, 2, 4,
  5): "Failing at the base, passing after" and "R39 measurement";
- R44 case ids failing on the scanner at `1d26110`, passing after (requirement 2): same section;
- R28 profile verdict sets before and after, equal (requirement 3): "R28 profile verdicts";
- required checks (requirement 6): "Required checks".

## Artifacts

- proof/06-execute.md - guard CLEAR: 21 new tests fail at bf7b949 and 31 at 1d26110, then pass; full pytest 2848 passed; R28 verdict sets equal

## Residue / caveats

Listed under "For the auditor to rule on" in `proof/06-execute.md`: forms the R44 scan still
misses (item 2) and the `_ts_recipe` / `_member_gates` helper home (item 8, carry-forward).
