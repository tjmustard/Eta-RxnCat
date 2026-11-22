---
mission: OPR.0.1.0
name: release-0.1.0
created: "2026-11-22"
---

# Notes - release-0.1.0

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-22 - mission scaffolded.
- 2026-11-22 [field-note] (agent:hyper-execute, slice 01-scaffold) geometric >=1.1 ships a "BSD 3-clause Non-AI" LICENSE (clause 4 bans ML-training use) and declares no licence metadata, so pip-licenses reports UNKNOWN; 1.0.2 is plain BSD-3 but also UNKNOWN. anchors: none
- 2026-11-22 [field-note] (agent:hyper-execute, slice 01-scaffold) ruff over "." also lints the HACF .agents/ scripts (120 lint, 12 format failures); they must be excluded via extend-exclude since agents may not edit them. anchors: none
