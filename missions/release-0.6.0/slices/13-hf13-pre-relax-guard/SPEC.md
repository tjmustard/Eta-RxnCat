---
id: OPR.0.6.0.13
slice: 13-hf13-pre-relax-guard
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Bound each ensemble pre-relaxation by a wall-time budget so a stalled geomeTRIC pre-relax (HF-13) becomes a cached, recorded pre_relax_failed:PreRelaxTimeout exclusion and the ensemble continues."
depends_on: [OPR.0.6.0.10]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_deadline.py, tests/unit/orchestrator/test_ts_ensemble.py]]
lore_refs: [ADR-0024, ADR-0045, ADR-0048]
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 HF-13 guard — bound the ensemble pre-relaxation by a wall-time budget

## Intent

Make a stalled ensemble pre-relaxation a bounded, recorded per-member exclusion, so no Tier 4 E2E,
acceptance or verdict run can hang on HF-13. A pre-relax that exceeds its wall budget is interrupted,
excluded as `pre_relax_failed:PreRelaxTimeout` with its wall time, cached like every other pre-relax
failure, and the ensemble continues with the next sample.

Context the builder needs:
- **Why (measured, mission HF-13 / R28; evidence `~/.hacf/eta-rxncat-hacf/evidence/v060-replan3/`):**
  the UMA TS1b_x(graft) ensemble stalls in 3 of 13 known runs at the same commit and inputs. Run 7
  of resolve's replan-3 series stalled and gave six `faulthandler` dumps. The main thread's eta frames were the same in all six:
  `ts_ensemble.py` `run_ts_ensemble_detailed` → `_PreRelax.run` → `mapping/relax.py`
  `relax_constrained_core` → `optimize/geometric_impl.py` `minimize` → `_run` (geomeTRIC's loop).
  Below that is geomeTRIC code calling numpy `eigh`/`svd`/`max`, and the leaf changes from dump to dump.
  So the loop is live, not deadlocked. It makes no engine call (no `Bridge.calc_new` frame, GPU 0–1 %), and
  it burns ~17 cores on OpenBLAS threads. eta's `maxiter` does not bound it. The trigger is
  run-to-run UMA (CUDA) noise: eta seeds geomeTRIC's RNG. The cause is inside the black box and is not
  cheap to fix from eta. So this slice **bounds** the stall and does not cure it.
- **Mechanism (normative):** a new private helper `src/eta_rxncat/orchestrator/_deadline.py`:
  - `class PreRelaxTimeout(BaseException)`. It derives from `BaseException`, so a broad `except
    Exception` inside the black box cannot swallow it.
  - A context manager `deadline(budget_s: float | None)`, used on the calling thread.
  - With a finite `budget_s > 0`, it starts a daemon watchdog thread that waits on an `Event` for
    `budget_s`. If the event is not set by then, the watchdog raises `PreRelaxTimeout` into the
    calling thread with `ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid),
    ctypes.py_object(PreRelaxTimeout))`, every 1.0 s until the guarded block exits. Re-sending
    covers a loop that swallows one exception.
  - On exit, normal or not, the manager sets the event under a lock shared with the watchdog,
    clears any undelivered exception with `PyThreadState_SetAsyncExc(tid, None)`, and joins the
    watchdog. No exception can land after the block.
  - `budget_s=None` means no thread and no guard. A budget that is not finite, or is ≤ 0, raises
    `ValueError`.
  - Resolve checked the mechanism on this interpreter (`asyncexc.py`): a numpy svd/eigh loop was
    interrupted at budget + 1 s, even with one swallow, and no exception arrived late.
  - CPython-only, stdlib-only (`ctypes`, `threading`), no new dependency.
- **Wiring (normative), `orchestrator/ts_ensemble.py`:**
  - `PRE_RELAX_BUDGET_S: float = 600.0`, a module constant with a docstring. The healthy maximum
    measured is 49 s on UMA (HF-12/HF-13 rows), so the margin is about 12×. One stall costs ≤ 601 s,
    well inside the `timeout 3600` per command of R25.
  - `run_ts_ensemble` and `run_ts_ensemble_detailed` gain a keyword `pre_relax_budget_s: float |
    None = PRE_RELAX_BUDGET_S`, passed to `_PreRelax`.
  - `_PreRelax.run` wraps only the `relax_constrained_core` call in `deadline(...)`. It catches
    `PreRelaxTimeout` as failure `pre_relax_failed:PreRelaxTimeout`, with a message naming the
    budget. It stores the usual failure row `{failed_reason, message, wall_time_s}` plus
    `"budget_s"`, and returns the failure with the wall time.
  - That reason already matches core's `_EXCLUSION_REASON` (`pre_relax_failed:\S.*`), so **no core
    change** is needed. The exclusion carries `pre_relax_wall_time_s`.
  - The budget is not an optimizer option and does **not** enter the stage key.
  - A cached timeout is a cache hit like any other failure row. A run in a fresh store retries the
    member. This keeps the two-run store check of the E2E deterministic.
  - `run_selectivity` and the E2E helpers are unchanged: they get the default.
- **Where it does not apply:** P-RFO (`run_transition_state`, eta's own optimizer) and the E2E's
  graft pre-relax in `tests/e2e/t4.py`. No stall was observed in either. Do not guard them.
- **Effect on Tier 4 numbers:** every UMA TS1b_x member re-converges to the seed (HF-10/HF-11, one
  distinct member). An excluded member therefore drops a duplicate, and pathway G and ΔΔG‡ are
  unchanged. The only visible effect is one more `pre_relax_failed:PreRelaxTimeout` row in the
  candidate's exclusions, plus `max_pre_relax_wall_time_s` ≈ 600. Slice 11 records that as run-to-run
  variation of the excluded list, not of G.
- **Ledger:** node `eta_rxncat_species_runner` owns `src/eta_rxncat/orchestrator/**`. Its description is at
  1967/2000 chars. If the updater or apply-review needs a sentence for `_deadline.py`, compress
  existing text to fit. **No node split.**
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp).
  - Run every framework script with `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand.
  - Never read `spec/archive/` or `tests/candidate_outputs/`.
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, with the version read from
    `.agents/hacf-manifest.json` at commit time.
  - No co-author trailer, and never `--no-verify`.
  - Stage named files only. No push, tag or promote.
- **Heavy runs:** any GPU or E2E command sits behind a blocking host check in its own call: `free -g`
  ≥ 9 G available, no other pytest/xtb/eta python on the host (any rig), GPU idle. Never overlap. Use
  `timeout 3600`.
- **Clean room (v0.4.0 Q1, v0.5.0 A1, hard rule):**
  - Never open, clone, fetch or search Eta_Scripts or nMAP.
  - Read no TS-optimizer or conformer-search source: the installed `geometric` package internals,
    Sella, pysisyphus.
  - geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.
  - Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.

## 1. The Confidence Mandate

**Score: 9/10.** Small additive guard at one call site, with a mechanism resolve exercised on this
interpreter, and an exclusion reason the core contract already accepts. Residual risk: an async
exception delivered inside the engine's own Python code (fairchem/torch) mid-evaluation. The stall
signature shows no engine frames, and the engine object is reused only for the next member's fresh
call. Requirement 6 tests that the engine still evaluates after a timeout.

## Mini-requirements

1. R28: an injected stub optimizer whose `minimize` loops forever in Python on numpy linear algebra
   (no engine call), with `pre_relax_budget_s=2.0`, gives that sample the exclusion
   `pre_relax_failed:PreRelaxTimeout`. Its `pre_relax_wall_time_s` is in [2.0, 6.0], and
   the call returns; it does not hang. Run the test under a pytest-level time limit or an explicit
   assertion on elapsed time.
2. R28: the ensemble continues: a later sample on a well-behaved path is pre-relaxed, re-searched and
   summed. The ensemble does not fail because of the timed-out member alone.
3. R28: a stub loop that catches `BaseException` once and keeps looping is still interrupted (by the
   re-send) within budget + 3 s.
4. R28: after a guarded block that finishes before its budget, no `PreRelaxTimeout` arrives later.
   Sleep 2 × budget after the call and assert nothing was raised. The watchdog thread has exited.
5. G7/R28: a second call on the same store hits the cached timeout row (zero new rows, zero engine
   calls for that sample). The equal `TSEnsemble` carries the same exclusion and the row holds `budget_s`.
6. R28: after a timeout, the same pre-relax engine evaluates the next sample correctly (stub energy
   equal to a fresh engine's).
7. R28: `pre_relax_budget_s=None` starts no watchdog thread (`threading.active_count()` unchanged),
   and a budget ≤ 0, NaN or inf raises `ValueError` before any engine call. The default equals
   `PRE_RELAX_BUDGET_S == 600.0`.
8. G8: importing `eta_rxncat.orchestrator.ts_ensemble` and `eta_rxncat.orchestrator._deadline` loads
   no `torch`, `pyscf`, `fairchem`, `geometric`.
9. The existing `tests/unit/orchestrator/test_ts_ensemble.py` requirements still pass unchanged:
   the default budget never fires on stubs.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `orchestrator/ts_ensemble.py`,
      `mapping/relax.py`, `core/selectivity_models.py` (`_EXCLUSION_REASON`), this SPEC's evidence
      README.
- [x] Task 2: `orchestrator/_deadline.py` (`PreRelaxTimeout`, `deadline`) and
      `tests/unit/orchestrator/test_deadline.py` (requirements 3, 4, 7, 8).
- [x] Task 3: wire `pre_relax_budget_s` / `PRE_RELAX_BUDGET_S` through `run_ts_ensemble(_detailed)`
      and `_PreRelax`. Add requirements 1, 2, 5, 6 to `tests/unit/orchestrator/test_ts_ensemble.py`.
- [x] Task 4: required checks; then one UMA run of `tests/e2e/test_t4_mapped.py::test_t4_mapped[uma]`
      (behind a host check, `timeout 3600`, ACCEPTANCE=1, XTB set, `ETA_RXNCAT_CANDIDATE_DIR` under
      TMPDIR so no committed candidate changes). It must pass in < 1300 s (2 × the healthy ~400 s
      + one budget). Record wall time, exit and any `PreRelaxTimeout` exclusion.
- [x] Task 5: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** change any core model or the exclusion-reason regex. The reason fits
  `pre_relax_failed:<error>`.
- **DO NOT** move the optimizer out of process, add a subprocess or worker, or change ADR-0024. Any
  such change would be a new PROPOSED ADR for TJ.
- **DO NOT** import geomeTRIC in the orchestrator, vendor it, or add it to core deps. **DO NOT** edit
  `optimize/` or `mapping/` (read only).
- **DO NOT** guard P-RFO or the E2E graft pre-relax, and do not change `run_selectivity`, the E2E
  helpers or any committed candidate.
- **DO NOT** add a stage kind (R24), and do not put the budget in the stage key.
- **DO NOT** set thread counts (OMP/OpenBLAS/torch) in library code. Thread capping is out of scope.
- **DO NOT** split the `eta_rxncat_species_runner` node.

## Proof contract

- [x] `uv run pytest tests/unit/orchestrator/test_deadline.py tests/unit/orchestrator/test_ts_ensemble.py -q`
      passes (requirements 1–9).
- [x] Required checks exit 0.
- [x] One UMA `test_t4_mapped[uma]` run passes under `timeout 3600` in < 1300 s, with wall and exit
      recorded.

## Source material

- Mission HF-13, R25, R28; evidence `~/.hacf/eta-rxncat-hacf/evidence/v060-replan3/README.md`
  (run7.filtered.txt, summary.txt, asyncexc.py); ADR-0048 (PROPOSED).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.6.0.10 (audited). Slice 11 depends on this slice.
