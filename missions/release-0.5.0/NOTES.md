---
mission: OPR.0.5.0
name: release-0.5.0
created: "2026-11-24"
---

# Notes - release-0.5.0

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-24 - mission scaffolded.
- 2026-11-24 [field-note] (agent:hyper-execute, slice 01-starter) Working-tree `uv run ruff format --check .` exits 1 on the untracked spec/archive and spec/process Draft_PRD.md files (ruff formats python blocks in .md); a clean checkout of the commit passes. The pre-commit hook checks staged .py only. anchors: none
- 2026-11-24 [field-note] (agent:hyper-execute, slice 02-ts-contracts) No tests/fixtures/v0.3.0 JSON carries an optimizer block (only environment.versions.geometric); the fixture-identity test asserts per-version counts (v0.3.0: 0, v0.4.0: 2) so a new fixture cannot slip past (lead ruling 04:16Z). anchors: none
- 2026-11-24 [field-note] (agent:hyper-execute, slice 03-prfo) Tier-D surfaces: an all-pairs harmonic network over-stiffens the forming motion (S2 reference was a minimum, all 12 projected eigenvalues > 0); soft inter-fragment pairs (0.1 vs 0.6) restore one negative mode. G1 1e-4 Bohr needs the lowest positive mode >~0.03 Eh/Bohr2 at these convergence thresholds. anchors: none
- 2026-11-24 [field-note] (agent:hyper-execute, slice 04-ts-validator) Never rerun hypergraph_updater.py --from-diff <rev> --apply after an apply: the working-tree diff then includes the first write to architecture.yml, which five nodes list in files:, so it marks cli/core/hw_probe/scaffold/store dirty. git restore the ledger, then run once. Edits after the slice-start index make the code graph stale_index; re-index before the updater. anchors: none
- 2026-11-24 [field-note] (agent:hyper-execute, slice 14-bofill-guard) Forcing a lost mode needs the actual followed vector: mixing fixed eigenvectors left overlaps 0.50-0.58 (no loss). Built around the spied followed vector, overlap is 0.408. S2 (softest mode 0.03 Eh/Bohr2) lands at 1.07e-4 Bohr on a perturbed path vs 6.6e-7 normally; S1 (0.21) gives 2.7e-6. G1 1e-4 is trajectory-sensitive on soft surfaces. anchors: none
