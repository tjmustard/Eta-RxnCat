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
hacf_status: executed
node_id: eta_rxncat_optimize
parent: null
hacf_touches: ["src/eta_rxncat/optimize/**", "tests/unit/optimize/**", src/eta_rxncat/orchestrator/ts_ensemble.py, src/eta_rxncat/orchestrator/species.py, src/eta_rxncat/orchestrator/ts.py, "tests/unit/orchestrator/**", src/eta_rxncat/core/optimization_models.py, tests/unit/core/test_frame_fields.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/optimize, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 frame capture and the geomeTRIC temp cwd

## Intent

TJ's audit needs to see each optimization path (G10, G12 item 2). Frames are captured only at eta's
own boundaries and stored as additive payload fields; nothing changes a stage key or a result
(mission R8, R13, R22, R33; US-008). geomeTRIC also stops writing files into the caller's cwd (L2).

Context the builder needs:
- **M11 is measured (R33; builder halt report `qitem-20261126043922-a61f5c38`, evidence
  `~/.hacf/eta-rxncat-hacf/evidence/v070-slice06/`).** Two GFN2 commands (ethyl/TS1a_n graft, ENDO
  order [2,3,4,10], 24 atoms, core frozen): the planned run and a disclosed forced-ladder run
  (`maxiter 3`), both accepted as M11's measurement. Copy this table into the proof as measured:

  | run | ladder step | bridge frames | `optim.xyz` frames | outcome |
  |---|---|---|---|---|
  | maxiter 200 (`m11.json`) | tric | 8 (= `n_engine_calls` 8; `n_steps` 7) | 8 (bridge 0-7) | converged |
  | maxiter 3 forced (`m11-ladder.json`) | tric | 4 | 4 (0-3) | not converged |
  | | tric_tight_trust | 148 | 4 (0, 145, 146, 147) | not converged |
  | | hdlc | 4 | 4 (0-3) | not converged |

  Every `optim.xyz` frame matches a bridge frame (max deviation 5.0e-11 Å; next-nearest bridge
  frame >= 5.3e-4 Å); the final frame equals `final_xyz` bitwise; each ladder step writes its own
  `optim.xyz` from Iteration 0. Tight-trust's 144 unmatched frames are, by count (24 x 3 x 2) and
  spacing (0.001 Bohr), finite-difference Hessian displacements from `hessian="first"`.
  **Decision (lead ruling, R33): `accepted_bool` per frame.** No further engine run is owed for M11.
- **Core field (R33):** `OptimizationFrame` gains `accepted_bool: bool | None = None`, additive and
  left out of the serialised form when `None` (as `OptimizationResult.frames` is); a frame without
  it serialises byte-equal to slice 02's. Test in `tests/unit/core/test_frame_fields.py`. The core
  ledger description (1973/2000) is not changed.
- **P-RFO (R33, option B): `optimize/prfo.py` is not edited** (its bytes are the ts_opt key's
  `opt.version`, `src-897c4e19cb4e738a`, recorded in TJ's promoted v0.5.0/v0.6.0 fixtures).
  `TSStep.coordinates_angstrom` (Å, product atom order) is filled in `orchestrator/ts.py` by a
  private recording engine that `_TSRun.search` passes to `find_saddle` around its `CountingEngine`
  (stage and identity delegated, so the key and the counts are unchanged).
  - **Mapping rule (read from prfo.py at 897c4e19):** `_Search` reaches the engine only through
    `_evaluate`. `hessian=True` comes only from `_exact` (start, mode-lost refresh, after a
    rejection, every `hessian_refresh_steps` accepted steps). `hessian=False` comes exactly once per
    loop iteration, at the trial point `x + dx`, followed with no engine call in between by
    `history.append(TSStep(energy_hartree=trial.energy_hartree, max_gradient_hartree_per_bohr=
    float(np.max(np.abs(trial_gradient))), ...))`; the wall-time check raises before the call. So
    **the k-th `hessian=False` evaluation (0-based) is `history[k]`'s geometry**, for accepted and
    rejected steps alike, and on success their counts are equal.
  - **Exactness check:** after `find_saddle` returns, the recorder requires
    `len(records) == len(history)` and, per k, the record's energy and max |gradient| (computed
    the same way from the same `PotentialResult`) `==` the step's fields. Any mismatch raises a
    private `RuntimeError` subclass (a code fault: not caught, never cached). Then `history` is
    replaced by `model_copy(update={"coordinates_angstrom": ...})` per step. P-RFO's algorithm is
    unchanged.
- **geomeTRIC bridge (`optimize/geometric_impl.py`, eta's wrapper):** in `Bridge.calc_new`, after
  `engine.evaluate` returns, append `OptimizationFrame(coordinates_angstrom, energy_hartree,
  max_gradient_hartree_per_bohr, ladder_step)` to the frame list owned by the run tally (`_Tally`,
  which already counts engine calls across ladder steps); `ladder_step` comes from the caller
  (`tric`, `tric_tight_trust`, then `hdlc` when constrained or `cartesian`), not the bridge. Build
  the frame, then one `list.append`, so an async `PreRelaxTimeout` cannot leave a half-built frame.
  `OptimizationResult.frames` carries the list on success.
- **Accepted marking (R33):** in `_run`, in a `finally` inside the `_sandbox()` block (so failed and
  retried steps are read too), parse that step's `optim.xyz` (standard multi-frame XYZ) and walk its
  frames in order against that step's bridge frames: each matches the first later unmatched bridge
  frame whose max |coordinate difference| is <= **1e-6 Å** (M11: matches 5.0e-11 Å, neighbours
  >= 5.3e-4 Å, so 1e-6 sits four orders clear of both). Matched frames get `accepted_bool=True`, the
  step's others `False` (the review labels them "other engine evaluations (trial points, Hessian
  displacements)"). If the file is missing or unparseable, or any of its frames finds no match, that
  step's frames keep `None`; marking never raises and never changes a result. Replace a frame by
  index with `model_copy` (one item assignment).
- **Frame sink (R13, R33):** `optimize/base.py` adds a `ContextVar` sink and a context manager
  (e.g. `capture_frames()`) yielding a fresh list and resetting the var in `finally`. When a sink is
  active, `minimize` uses that list as the tally's frame list (else a fresh one), so the caller holds
  every frame even when `minimize` raises or `relax_constrained_core` raises
  `CoreDisplacementError` after it returns. The deadline watchdog raises into the calling thread,
  so the context var is visible there.
- **Failure payloads (R13, F16, R33): every failure row written around a geomeTRIC run carries its
  frames.** `_PreRelax.run` (ts_ensemble.py) opens the sink around its `try` and writes `frames` on
  every failure: `PreRelaxTimeout`, `CoreDisplacementError`, `OptimizationFailedError`,
  `scf_convergence`, `engine_error`. `_Runner.optimize` (species.py) does the same for
  `optimization_failed` and `scf_convergence`. `_TSRun.search` writes the recorder's records as
  `frames` (`ladder_step` and `accepted_bool` `None`) on its `ts_search_failed:*`,
  `scf_convergence` and `engine_error` rows. An empty list is left out. TJ wants to see stalls.
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

**Score: 9/10.** Capture is at eta's own hooks, additive and optional; prfo.py is untouched and keys
are pinned by a test. M11 is measured and the labelling decided (R33). The P-RFO mapping rests on
prfo.py's call order, held by the exactness check and the source-identity pin (requirement 2).

## Mini-requirements

1. M11's table (above) and the `accepted_bool` decision copied into the proof as measured.
2. P-RFO, fake engine, a search with at least one rejection and one exact refresh: step count ==
   `TSStep`s; each step's coordinates equal the geometry of the matching `hessian=False` call seen
   by an independent spy engine. A records list shifted by one or with an extra record raises the
   mapping error. `prfo._source_identity().version == "src-897c4e19cb4e738a"` is pinned (an edit
   to prfo.py fails it and reopens both the key and the mapping).
3. geomeTRIC: frames on a fake-engine minimize; count as M11 measured; `ladder_step` per frame;
   `accepted_bool` from a written `optim.xyz` (match, non-match, missing file → `None`).
4. Fake timeout, `CoreDisplacementError`, `OptimizationFailedError`, `scf_convergence` and
   `engine_error` mid-run each store a failure row **with** frames; a TS search failure too.
5. A v0.6.0 row (no frames) loads and the exporter later sees `frames is None`.
6. Stage keys byte-equal to v0.6.0's for the same inputs (ts_opt included); a no-frame payload and
   an `accepted_bool=None` frame byte-equal.
7. A real GFN2 pre-relax from a clean temp cwd leaves that cwd's listing unchanged; after the slice's
   own runs `git status --porcelain` shows no `HT.v_*`.
8. Concurrent-safety: the cwd is restored after an exception inside geomeTRIC (fake).

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] M11 proof table and decision (measured; R33).
- [x] `OptimizationFrame.accepted_bool` (core) and its test.
- [x] P-RFO recorder in ts.py; bridge frames on the tally; accepted marking; frame sink; failure
      payloads; payload writers.
- [x] `_scratch_cwd` in `GeometricOptimizer`.
- [x] Tests (`tests/unit/optimize/test_frames.py`, `test_scratch_cwd.py`,
      `tests/unit/orchestrator/test_prerelax_frames.py`, key-equality test).
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** open, read or patch geomeTRIC source; capture only in `calc_new`; read only its outputs.
- **DO NOT** change a stage key, a result value or P-RFO's algorithm; **DO NOT** edit `optimize/prfo.py`.
- **DO NOT** run an engine from the repo root.

## Proof contract

- [ ] M11 table with the host checks and env (both commands, from the evidence dir).
- [ ] `uv run pytest tests/unit/optimize tests/unit/orchestrator -q` passes (requirements 2-8).
- [ ] `git status --porcelain` after the slice's runs (no `HT.v_*`).
- [ ] Required checks exit 0.

## Source material

- Mission G10, R8, R13, R22, R33, HF-6 (L2); ADR-0016, ADR-0024.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.2. Slice 07 depends on this one.
