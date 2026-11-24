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
