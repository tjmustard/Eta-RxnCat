# PROOF - OPR.0.7.1.5 Tier X selectivity chain and the review export round trip (T-X4, T-X5)

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

All in `proof/05-execute.md` (builder evidence, not a QA verdict):

- host check, command, `/usr/bin/time -v` and junit, T-X4 and T-X5 `passed`, 0 skipped
  (requirements 1-2): "Measured run";
- each named seam break fails its test (requirement 4): "Seam breaks";
- required checks, both tests deselected by default (requirements 3-4): "Required checks".

## Artifacts

- proof/05-execute.md - guard CLEAR: Tier X 2 passed 0 skipped; full pytest 2763 passed; ruff/format/mypy exit 0; 5 seam breaks fail

## Residue / caveats

The seam-break runs are the builder's pre-check; the audit owns `seam_breaks.json`. All GFN2 runs
used the lead's 4 GiB memory floor. See "For the auditor to rule on" in `proof/05-execute.md`.
