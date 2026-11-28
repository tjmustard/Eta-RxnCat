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
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.4) On GFN2 the seed need not stay a TS ensemble member: on the v0.7.0 ethyl candidate (1/1/1 options) it merges into the lower-G sample, so members[0] is fragment_embed:0; check seed identity through run.samples[0] or merges, not members. anchors: none
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.5) On a v0.7.0 candidate both pathways share one derived reactant_key and the plan has no pathway_pruning_rules, so a swapped-key or dropped-rules break is invisible without a variant: T-X4 uses distinct marker keys with all-rejecting member gates (no scoring, all cache hits) and a plan variant with a priority-1 rule. anchors: none
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.6) uv build with a warm cache succeeds with the network blocked even without --offline, so R39 is guarded by a test on the build command, not by a network-blocked run; the .venv-accept-gpu/mace/uma envs hold dev deps, so their licence gate already fails on pathspec MPL-2.0 before any change. anchors: none
- 2026-11-27 [field-note] (agent:hyper-execute, slice OPR.0.7.1.7) A record's pydantic ser_json_inf_nan does not reach a nested core model (the model's own config wins), so RunRecord writes ratio=inf through a wrap field serializer on RecordSelectivity.result; tests/e2e/v070.py checked_record_text still refuses a non-finite ratio. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.8) GPU KS analytic Hessian routing (gpu_ks_hessian_class) ignores cartesian_basis, while the v0.2.0 GPU support record was measured without it; cartesian_basis=True on CUDA can take the analytic path in a recorded class. README now says the class does not include cartesian_basis; no code change. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.8) R31 reachability (tools/engine_reachable.py) covers 87 of 90 eta_rxncat modules (parent packages count, and the marked tests import most of the package), so only __main__, review.schema.__main__ and utils._smoke_child are outside; no zero-coverage symbol met all four removal conditions. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.9) pytest junit has no deselected count, so tools/quality_record_v071.py also reads each verdict run's terminal log, and takes verdict_run_sha from a file written at the run so a rerun after the record commit gives the same bytes. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.9) A point release breaks every PLAN_VERSIONS.index(project_version()) lookup in test_identity.py (the GPU claim and the v0.4.0-v0.7.0 claim tests); they now go through roadmap_position. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.9) R19 wants a test id plus a record key per README/CHANGELOG claim, so a version record script needs known_issues constants for every CHANGELOG known issue before the verdict run; test-less known issues can cite only the key. anchors: none
- 2026-11-28 [field-note] (agent:hyper-execute, slice OPR.0.7.1.9) Fix round 2: R19 key-only citation holds only where no test exists; search tests for a known issue's claim before citing known_issues alone. anchors: none

## Lore capture

- replans: <filled by the lead at mission close>
- stories: <STORY ids proposed by the scribe, or none>
