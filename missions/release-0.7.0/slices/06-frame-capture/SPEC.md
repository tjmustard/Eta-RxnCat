---
id: OPR.0.7.0.6
slice: 06-frame-capture
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Store every optimization's path: P-RFO steps gain their geometry and geomeTRIC runs gain bridge frames in success and failure payloads, run in a per-run temp cwd, with stage keys unchanged."
depends_on: [OPR.0.7.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_optimize
parent: null
hacf_touches: ["src/eta_rxncat/optimize/**", "tests/unit/optimize/**", src/eta_rxncat/orchestrator/ts_ensemble.py, src/eta_rxncat/orchestrator/species.py, src/eta_rxncat/orchestrator/ts.py, "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/optimize, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 frame capture and the geomeTRIC temp cwd

## Intent

TJ's audit needs to see each optimization path (G10, G12 item 2). Frames are captured only at eta's
own boundaries and stored as additive payload fields; nothing changes a stage key or a result
(mission R8, R13, R22; US-008). geomeTRIC also stops writing files into the caller's cwd (L2).

Context the builder needs:
- **First task, M11 (stop-and-report):** on one GFN2 constrained pre-relax (ethyl/TS1a_n graft, from
  a scratch cwd, behind the host check), capture the bridge frames (below) and read geomeTRIC's
  `params.xyzout` **output file** (`optim.xyz` in the wrapper's temp dir, `geometric_impl.py:361`;
  reading an output is not reading internals). Record: frame count vs `n_steps` / `n_engine_calls`;
  whether the final frame equals `final_xyz` bitwise; which bridge frames match `xyzout` frames
  (accepted steps); how ladder steps appear. Decide the label: if every `xyzout` frame matches a
  bridge frame, mark `accepted_bool` per frame; otherwise label the list "engine evaluations
  requested by the optimizer (includes trial points)". If neither serves TJ's audit (the lead
  decides), stop: the lead files a TJ row before this slice merges.
- **P-RFO:** eta's own optimizer fills `TSStep.coordinates_angstrom` for every step (accepted and
  rejected), Å, product atom order. P-RFO's algorithm is unchanged.
- **geomeTRIC bridge (`optimize/geometric_impl.py`, eta's wrapper):** in `Bridge.calc_new`, after
  `engine.evaluate` returns, append `OptimizationFrame(coordinates_angstrom, energy_hartree,
  max_gradient_hartree_per_bohr, ladder_step)` to a per-run list owned by the existing run tally
  (the object that already counts engine calls across ladder steps); `ladder_step` comes from the
  caller (`tric`, `tric_tight_trust`, `cartesian`), not the bridge. Wrap the append so an async
  `PreRelaxTimeout` cannot leave a half-built frame (build the frame, then one `list.append`).
  `OptimizationResult.frames` carries the list on success.
- **Failure payloads (R13, F16):** `_PreRelax.run` (ts_ensemble.py) and the species-runner
  optimization paths store `frames` in **failure** rows too (timeout, `CoreDisplacementError`,
  `OptimizationFailedError`): the tally is read in `finally`. TJ wants to see stalls.
- **Payload writers:** `_opt_payload` (`orchestrator/species.py:464`) and the TS payload add
  `frames`/step coordinates only when present; a run without frames writes the same bytes as v0.6.0.
- **Keys (ADR-0016):** `build_stage_key` inputs are untouched; a test computes the keys of a v0.6.0
  stage set before and after and asserts equality. Stores are forward-only (stated in the module
  docstring and README in slice 14).
- **Temp cwd (R8):** `GeometricOptimizer.minimize` runs geomeTRIC inside
  `with _scratch_cwd():` — `tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))`, `os.chdir`
  into it under a module `threading.Lock`, restore the previous cwd in `finally`. The watchdog
  thread (HF-13 guard) never relies on the cwd.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (slices 11-13 write candidates; they never read them back as input).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.
- **Heavy runs (mission §5 "Heavy-run rule", normative):** before each engine/GPU command, a
  blocking host check in its own call or an exiting loop (never echo-then-run), output kept in the
  proof: `nvidia-smi` no compute process; `MemAvailable` >= 12 GiB; `ps`: no other eta
  E2E/pytest/xtb and no non-niced (nice < 10) process of any rig using >= 100 % CPU or >= 2 GiB RSS.
  One engine and one unit per command, `timeout 3600`, from a scratch cwd (never the repo root:
  geomeTRIC writes `HT.v_*.txt` into the cwd until slice 06 lands). Env asserted in the proof:
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`, `ETA_RXNCAT_ACCEPTANCE=1`,
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Honour any quiet-host hold the lead announces.

## 1. The Confidence Mandate

**Score: 9/10.** Capture is at eta's own hook, additive and optional; keys are pinned by a test. The
open point, the frame labelling, is M11 with a stop-and-report gate.

## Mini-requirements

1. M11 table and the labelling decision in the proof.
2. P-RFO: frame count == number of `TSStep`s on a fake-engine search; coordinates match.
3. geomeTRIC: frames on a fake-engine minimize; count as M11 measured; `ladder_step` per frame.
4. A fake timeout / `CoreDisplacementError` mid-run stores a failure row **with** frames.
5. A v0.6.0 row (no frames) loads and the exporter later sees `frames is None`.
6. Stage keys byte-equal to v0.6.0's for the same inputs; a no-frame payload byte-equal.
7. A real GFN2 pre-relax from a clean temp cwd leaves that cwd's listing unchanged; after the slice's
   own runs `git status --porcelain` shows no `HT.v_*`.
8. Concurrent-safety: the cwd is restored after an exception inside geomeTRIC (fake).

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] M11 (scratch instrument; host check); proof table; labelling decision.
- [ ] P-RFO step coordinates; bridge frames on the tally; failure payloads; payload writers.
- [ ] `_scratch_cwd` in `GeometricOptimizer`.
- [ ] Tests (`tests/unit/optimize/test_frames.py`, `test_scratch_cwd.py`,
      `tests/unit/orchestrator/test_prerelax_frames.py`, key-equality test).
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** open, read or patch geomeTRIC source; capture only in `calc_new`; read only its outputs.
- **DO NOT** change a stage key, a result value or P-RFO's algorithm.
- **DO NOT** run an engine from the repo root.

## Proof contract

- [ ] M11 table with the host check and env.
- [ ] `uv run pytest tests/unit/optimize tests/unit/orchestrator -q` passes (requirements 2-8).
- [ ] `git status --porcelain` after the slice's runs (no `HT.v_*`).
- [ ] Required checks exit 0.

## Source material

- Mission G10, R8, R13, R22, HF-6 (L2); ADR-0016, ADR-0024.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.2. Slice 07 depends on this one.
