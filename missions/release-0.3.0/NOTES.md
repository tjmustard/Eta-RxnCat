---
mission: OPR.0.3.0
name: release-0.3.0
created: "2026-11-23"
---

# Notes - release-0.3.0

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-23 - mission scaffolded.
- 2026-11-23 [field-note] (agent:hyper-execute, slice 01-starter) The starter ships its own pyproject.toml with [tool.ruff], so ruff uses it as the nearest config for files under docs/prd/v0.3.0/Eta-RxnCat-v0.3.0/ and the root extend-exclude does not apply there (explicit paths from the pre-commit hook included); a gate file .ruff.toml with exclude = ["*"] at the starter root keeps ruff off it, as for v0.1.0 and v0.2.0. anchors: none
- 2026-11-23 [field-note] (agent:hyper-execute, slice 01-starter) hypergraph_updater.py --from-diff without --apply still runs the lore post-impact hook and writes stale marks to lore_hypergraph.yml and lore/MAP.md (documented: "in both forms"); a preview is not read-only. Every node lists spec/compiled/architecture.yml, so any ledger write maps the diff to cli, core, hw_probe, scaffold and store. anchors: none
