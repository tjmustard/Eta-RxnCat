# PROOF - OPR.0.7.0.17 Rerun the v0.7.0 E2E units with the seed checks and records

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

- Store copies, source and copy sha256, rows before and after: proof/17-execute.md "Store copies".
- Per unit host check, env, wall time, exit, rows added, gates: proof/17-execute.md "Runs"; dG‡/ddG‡ against 9fdba68: "Energies".
- `seed_clash` against `cov_margin.out` and the stall count: proof/17-execute.md "`seed_clash`".
- `git show --stat` of both candidate-only commits: proof/17-execute.md "Commits".
- Required checks exit 0: proof/17-execute.md "Commands".

## Artifacts

- proof/17-execute.md - guard CLEAR: 15/15 exit 0, 0 rows added, dG/ddG equal to fixtures, 53 seed_clash as measured, 0 bond_changed, 0 stalls; ruff/mypy exit 0; full pytest 2660 passed

## Residue / caveats

The fresh candidates are not promoted (TJ's re-review). The `review/` bundle is not rebuilt (slice 18). The harness fix has no unit test of its own (proof/17-execute.md, item 1).
