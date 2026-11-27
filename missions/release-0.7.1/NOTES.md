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
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.2) The v0.7.0 enumeration plan names only unmoved atoms (0-5) on its TS nodes and freezes none, so index-remap breaks in the enumerator or enumerated_pathway_inputs are invisible on it; T-O4/T-O6 add a variant plan naming template atom 17 (product index 16). anchors: none
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.3) A fresh-store rerun of a v0.7.0 unit cannot cmp equal (pre_relax_wall_time_s of members and exclusions is a stored row value outside VOLATILE); the byte-equal parity run reads a sqlite backup of the store that made the fixture (v070-replan7-runs), as v0.7.0 slice 17 did. anchors: none

## Lore capture

- replans: <filled by the lead at mission close>
- stories: <STORY ids proposed by the scribe, or none>
