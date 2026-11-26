---
slice: OPR.0.7.0.11
candidate_sha: 9ce26c6c3cf9c5dbd41eaf478a2dda513e454646
artifact_type: qa
verdict: PASS
money_evidence: 8/8 units 9/9 G7 gates; ethyl endo GFN2 rerun identical (13.5602
  kcal/mol, 694/0 calls); full pytest 2563 passed
---

# QA: 11-enumeration-e2e (OPR.0.7.0.11) — PASS, iteration 1

Range judged: 475894b..b38ada1 (3af1e95 code: tests/e2e/v070.py, tests/e2e/test_v070_enumeration.py; dd99d1c candidate-only; b38ada1 progress/proof/ledger flag). Auditor: build-audit. No src/ change in the range.

## Verdicts
- MR1 HF-3 start gate: met (mission HF-3 exo table filled; lead pre-check).
- MR2 8 units x 9 G7 gates: pass. All 12 logs end "1 passed", /usr/bin/time exit 0, walls 4:17-16:27 (units, < 5400) and < 3 s (scores). 13 host checks (12 + preflight) each "HOST FREE": avail 13-16 G, gpu_apps 0, heavy 0, eta 0; run.sh loops hostcheck.sh and exits 3 if never free (blocking, not echo-then-run). Env per command in evidence proof/<tag>.env (ETA_RXNCAT_XTB, ETA_RXNCAT_ACCEPTANCE=1, TMPDIR on disk, HEAD 3af1e95; scratch cwd empty, 0 HT.v_* after).
- MR3 second pass: gate requires 0 new rows (whole store), 0 Engine.evaluate calls, 0 rows/calls in sample-stage metrics, reactants all-hit, equal FallbackRecord and ensemble; derivation also 0/0. Engine.evaluate is the only caller of _evaluate in src/ (concrete engines define only _evaluate; CountingEngine and ts._RecordingEngine delegate to .evaluate), so the patch counts graft pre-relax, re-search, frequencies and species runner.
- MR4 reported values: present per unit (stalls, time lost, cap, orientation_mismatch, walls, CPU, RSS, load1 per timeout row).
- MR5 candidate-only commit: `git show --name-only dd99d1c` = 24 paths, all under tests/candidate_outputs/v0.7.0/ (names only; no candidate opened).
- Negative space: units ran one per command, scratch cwd; ddG-dagger never gated. No new dependency; no src change; nothing outside tests/e2e, the candidate dir, mission files and the ledger.
- Binding lore: 0 binding nodes; lore_refs [].

## Reproducibility (auditor rerun)
Throwaway worktree at 3af1e95, PYTHONPATH=<wt>/src (eta_rxncat imported from the worktree), fresh store + candidate dir under TMPDIR scratch, behind a blocking host check (avail 15G, gpu_apps 0, heavy 0, eta 0). `test_v070_unit[ethyl-endo-xtb]` exit 0 in 3:21.7, RSS 174 MB. Identical to the builder: 9/9 gates, 3 members, exclusions forming_overlap 1 / orientation_mismatch 4, seed dG 14.622747460513642, ensemble dG 13.560206712557633 kcal/mol, 694/0 calls, 57/0 rows, export 40 trajectories/15 frequencies, 0 missing. Run record vs builder's state copy: only wall-time fields differ. UMA not rerun (GFN2 sufficient for reproducibility of the harness; UMA evidence judged from logs).

## Oracle (auditor, at b38ada1)
ruff check . 0; ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process 0 (724 files); mypy 0 (91 files); full pytest 0 (2563 passed, 192 deselected, 235.8 s). test_v070_inputs is inside the full run.

## Rulings on the builder's 13 items
1 shared store: accepted; second-pass gate measures the store-wide delta and the global call count, so sharing cannot hide a hit; first-pass reactant hits in the second pathway unit are a cost, not a gate (no G7 gate requires first-pass computation). 2 dual record write: accepted. 3 extra names: accepted. 4 commit order: accepted (candidates carry commit_sha 3af1e95). 5 private names: acceptable test-side use (self-checking: full coverage + start digests + 0/0); contract gap → v0.7.1. 6 call counting: verified. 7 reactant conformers: accepted. 8 dG-dagger = dG_seed + (G_pathway - G_seed) = G_pathway - G_reactants on the same thermo basis; mission gates nothing on it. 9-10 accepted. 11 UMA RSS 10.6 GB: report. 12 denied ls: nothing read. 13 proof boxes: noted.
