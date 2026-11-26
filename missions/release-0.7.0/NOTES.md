---
mission: OPR.0.7.0
name: release-0.7.0
created: "2026-11-26"
---

# Notes - release-0.7.0

Context and observations that help the mission but do not change its `SPEC.md` contract or its
`PROGRESS.md` acceptance checklist belong here. `hyper_lore.py note --mission <dir>` appends them.

## Notes

- 2026-11-26 - mission scaffolded.
- 2026-11-26 [field-note] (agent:hyper-execute, slice 01-starter-graph-split) A ruff gate under docs/prd/vX/ does not stop the hook: ruff uses the config nearest each file (here the starter pyproject.toml), and only a --force-exclude check on explicit paths shows it; a whole-tree ruff check passes either way. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.2) GraftRecord.order_rmsds_angstrom is list[float | GraftRefusalReason] (one item per declared order), so slice 03 records a raised order by its reason; measures are None on refusal. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.2) Optional frame fields are omitted from serialised bytes by a wrap model_serializer (not exclude_if, which needs pydantic>=2.12; pyproject allows >=2). anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.3) ensure-node --from-spec skips touches owned by another node (core files, ledger) and the test glob, so it was a no-op here; the enumerator node already held both entries from slice 01. anchors: none

## Lore capture

- replans: <filled by the lead at mission close>
- stories: <STORY ids proposed by the scribe, or none>
