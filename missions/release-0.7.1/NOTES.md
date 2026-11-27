---
mission: OPR.0.7.1
name: release-0.7.1
created: "2026-11-27"
---

# Notes - release-0.7.1

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-27 - mission scaffolded.
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.1) tests/integration is a package (__init__.py): import helpers as "from .conftest import ..."; tests.integration is not importable under "uv run pytest", and a bare "conftest" name is ambiguous. load_v070_plan() returns V070Plan(plan, max_alignment_rmsd_angstrom, orientation_centers). anchors: none

## Lore capture

- replans: <filled by the lead at mission close>
- stories: <STORY ids proposed by the scribe, or none>
