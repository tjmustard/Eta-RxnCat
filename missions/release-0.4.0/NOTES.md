---
mission: OPR.0.4.0
name: release-0.4.0
created: "2026-11-23"
---

# Notes - release-0.4.0

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-23 - mission scaffolded.
- 2026-11-23 [field-note] (agent:hyper-execute, slice 01-starter) ruff given explicit starter paths (as a commit hook does) lints them under the starter's own pyproject [tool.ruff] (nested config wins; root extend-exclude/force-exclude do not reach it): 55 errors, 9 files unformatted. `ruff check .` from the root excludes docs/prd and passes. anchors: none
