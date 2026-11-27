# PROOF - OPR.0.7.1.4 Tier X TS seams on CPU GFN2 (T-X1…T-X3)

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

All in `proof/04-execute.md` (builder evidence, not a QA verdict):

- host check, command, `/usr/bin/time -v` and junit, 4 `passed`, 0 skipped (requirements 1-2):
  "Measured run";
- no `HT.v_*` in `git status --porcelain`: "git status --porcelain";
- the `expected_face` break fails `test_tx3_rank1_face_mismatch` (requirement 3): "Seam breaks";
- required checks, the new module deselected by default (requirements 3-4): "Required checks".

## Artifacts

- proof/04-execute.md - guard CLEAR: Tier X 4 passed 0 skipped; full pytest 2763 passed; ruff/format/mypy exit 0; 7 seam breaks fail

## Residue / caveats

The seam-break runs are the builder's pre-check; the audit owns `seam_breaks.json`. All GFN2 runs
used the lead's 4 GiB memory floor. See "For the auditor to rule on" in `proof/04-execute.md`.
