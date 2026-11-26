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
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.4) A later-site map is in template indices and cannot name atoms an earlier graft appended; the enumerator keeps them after the remapped keep. A selectivity-set entry-multiset miss is reachable on its own only with a composition-preserving entry, because the composition checks run first. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.6) M11: geomeTRIC calls Bridge.calc_new also for tight-trust (hessian=first) displacements: 148 evaluations vs 4 xyzout frames on 24 atoms; the PRFO identity hashes prfo.py, so any edit there changes ts_opt keys. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.5) M13: a GFN2 TS1a_n ensemble used about 18 CPU-seconds per wall-second (process plus children) and pushed load1 to about 23 on 20 CPUs by itself, so the R7 budget scales above 600 s even on an otherwise idle host; an EnumeratedCandidate carries no selectivity sets, so ts_fallback compares TS nodes of the same priority. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.6) The P-RFO step recorder (orchestrator/ts.py) requires one hessian=False evaluation per history step, so a fake TS optimizer must follow that call contract or the run raises; _scratch_cwd changes the process-wide cwd, so a caller using relative paths from another thread during a geomeTRIC run would resolve them in the temp dir. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.7) run-data: TSEnsembleRun exposes no per-sample stage keys (only seed_result.keys), so slice 11 must derive pre-relax, ts_opt and frequency keys for RecordSample itself; export_run_data refuses an ensemble member without a sample. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.8) M10: slice 06's smoke.py writes no store and one pre-relaxation is no ensemble, so bundle size was extrapolated from resolve's HF-3 stores (about 440-560 frames per ensemble, 47 bytes per frame per atom); endpoint rows are an allowance, so slice 13 must measure the real bundle against 25 MB. The bundle writer refuses a non-empty output directory. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.9) M12: 3Dmol 2.5.5 draws all viewers on one shared offscreen WebGL canvas and has no destroy; a removed viewer redrawn at size zero raises an OffscreenCanvas page error in Firefox, so disconnect divwatcher/intwatcher and stub show(). The slice 08 CSP needed no addition (no surfaces, so no blob worker). /usr/bin/firefox on this host is a snap shim with no snap installed. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.10) Slice 10: the cyclopropene reactant map keeps H3, deletes mirror H4 (fits 0.0525/0.0496 A); v070 inputs load via tests/e2e/v070.py load_enumeration()/load_fallback(), which return the plan plus max_alignment_rmsd_angstrom and orientation_centers (not EnumerationPlan fields); the graft-time rank 1 (align on Cp H8) grafts one order at 0.888 A with 2 contacts and clashes on the other. anchors: none
- 2026-11-26 [field-note] (agent:hyper-execute, slice OPR.0.7.0.11) Slice 11: units share one store (ETA_RXNCAT_V070_STATE/v070_enum.sqlite, evidence/v070-slice11, 24 run records beside it) for slice 13's bundle; engine calls are counted by patching Engine.evaluate; UMA unit peak RSS reached 10.6 GB (HF-3: 8.15 GB) and a UMA all-hit second pass still takes 57-69 s. anchors: none

## Lore capture

- replans: <filled by the lead at mission close>
- stories: <STORY ids proposed by the scribe, or none>
