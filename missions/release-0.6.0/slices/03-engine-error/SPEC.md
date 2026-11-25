---
id: OPR.0.6.0.3
slice: 03-engine-error
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Make run_transition_state cache an EngineRuntimeError as failed_reason engine_error while EngineUnavailableError and EngineInputError still raise uncached."
depends_on: [OPR.0.6.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_ts_engine_error.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 engine runtime errors become cached TS failure rows

## Intent

Make `run_transition_state` record an `EngineRuntimeError` as a cached failure row
(`failed_reason="engine_error"`) instead of raising, while host and input errors
(`EngineUnavailableError`, `EngineInputError`) still raise and are never cached, so one engine crash
cannot void an ensemble and no host failure is frozen into the store.

Context the builder needs:
- Mission R3 (red team F3). `src/eta_rxncat/engines/errors.py`: `EngineError` (20) ←
  `EngineUnavailableError` (24), `EngineInputError` (28), `ScfConvergenceError` (32),
  `EngineRuntimeError` (41). `orchestrator/ts.py` already caches `TSSearchFailedError` and
  `ScfConvergenceError` in `_TSRun.search` and `_TSRun.frequency`; add `EngineRuntimeError` to both
  with payload `{"failed_reason": "engine_error", "message": str(exc), "error_type":
  type(exc).__name__}`; a cached row returns `"engine_error"` as `failed_reason`.
- Update the `run_transition_state` docstring's Raises section: `EngineUnavailableError`,
  `EngineInputError` raise; `EngineRuntimeError` is returned as `engine_error`.
- Test with a stub engine (the existing orchestrator unit tests' stub pattern) that raises each
  error class at the `ts_opt` stage and at the `frequency` stage; a `CountingEngine` proves the
  second run makes zero engine calls.
- **Seat rules (every slice):** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp); every
  framework script with `python3`; Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`
  (must print `index: ok`); run `hypergraph_updater.py --from-diff <Start> --apply` **once** after
  the commit (re-index first; a rerun needs `git restore spec/compiled/architecture.yml` first and a
  disclosure); never edit `spec/compiled/architecture.yml` by hand; never read `spec/archive/` or
  `tests/candidate_outputs/`; commits under this machine's git identity, ending with exactly
  `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)` (version from `.agents/hacf-manifest.json` at commit
  time), no co-author trailer, never `--no-verify`; stage named files only; no push, tag or promote.
- **Clean room (v0.4.0 Q1, v0.5.0 A1, hard rule):** never open, clone, fetch or search Eta_Scripts or
  nMAP; read no TS-optimizer or conformer-search source (installed `geometric` package internals,
  Sella, pysisyphus, the starter's code beyond naming it in a DV row); geomeTRIC runs only as a black
  box through eta's `GeometricOptimizer`. The mission SPEC is `missions/release-0.6.0/SPEC.md`; its
  R-, HF- and G-rows are cited by number.

## 1. The Confidence Mandate

**Score: 10/10.** Two `except` clauses, a docstring and tests, in a pattern the file already uses.

## Mini-requirements

1. US-003 / G3: `EngineRuntimeError` at `ts_opt` → `failed_reason == "engine_error"`, row cached;
   second run: `cache_hits == 1`, `engine_calls == 0`, same result.
2. G3: the same at `frequency` (search cached as success, frequency cached as failure).
3. G3: `EngineUnavailableError` and `EngineInputError` propagate from both stages and the store has
   no row for that key afterwards.
4. Existing `tests/unit/orchestrator/test_ts*.py` pass unchanged.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `orchestrator/ts.py`, `engines/errors.py`.
- [x] Task 2: the two `except EngineRuntimeError` clauses and the docstring.
- [x] Task 3: `tests/unit/orchestrator/test_ts_engine_error.py`; required checks.
- [x] Task 4: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** catch `EngineError` broadly; **DO NOT** cache `EngineUnavailableError` or
  `EngineInputError`.
- **DO NOT** change `run_transition_state`'s signature or any existing `failed_reason` value.

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_ts_engine_error.py -q` passes (all four cases).
- [ ] Existing orchestrator tests pass unchanged; required checks exit 0.

## Source material

- Mission R3; `src/eta_rxncat/orchestrator/ts.py`; `src/eta_rxncat/engines/errors.py`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

01.
