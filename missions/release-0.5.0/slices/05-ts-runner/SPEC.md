---
id: OPR.0.5.0.5
slice: 05-ts-runner
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Add run_transition_state: P-RFO search, final Hessian in the frequency stage, validation and TS thermochemistry, every stage cached under ts_opt with failures, never through the minimum path."
depends_on: [OPR.0.5.0.3, OPR.0.5.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_ts_runner.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 TS runner — search, frequency, validate, TS thermo, cache (orchestrator)

## Intent

Add `orchestrator/ts.py` with `run_transition_state`, which runs the P-RFO search, computes the
final Hessian in the `frequency` stage, validates, runs TS thermochemistry and caches every stage
— failures included — under the new `ts_opt` stage kind, without ever touching the species
runner's minimum path.

Context the builder needs:
- **Read:** `orchestrator/species.py` — `_Runner._lookup/_save` (a failure is a `COMPLETED` row
  carrying `failed_reason`), `opt_stage` (how `opt.<key>`, `opt.name`, `opt.version` enter the
  key), `frequency` (payload `energy_hartree`, `hessian_hartree_per_bohr2`, `hessian_method`,
  `geometry`; key = `build_stage_key(state, _with_kind(engine.stage, "frequency",
  engine.stage.options), engine.identity)`), `build_engine`, `CountingEngine`
  (`orchestrator/counting.py`), `geometry_payload`, `StageMetrics`; `store/keys.py`
  (`build_stage_key`); `mapping/report.py` (`perceive_bonds(state) -> list[tuple[int, int]]`);
  slices 02–04 (contracts, `PRFOOptimizer`, `validate_transition_state`, `ts_thermochemistry`).
- **Contract (mission §5 "TS runner"):**
  - `TSSpec` (frozen dataclass): `ts_id: str`, `start: MolecularState` (with
    `active_atom_indices`), `forming_bonds: tuple[tuple[int, int], ...]`, `reference:
    MolecularState | None = None`, `reference_map: tuple[int, ...] | None = None` (start index →
    reference index; `None` means identity).
  - `TSRecipe` (frozen dataclass): `name`, `engine_stage: StageConfig`, `ts_optimizer:
    TransitionStateOptimizer`, `ts_options: Mapping[str, ScalarValue] = {}`, `thermo_config`,
    `analysis`, `validation_options: TSValidationOptions`, `engine_runtime: Mapping[str, Any] = {}`.
  - `run_transition_state(spec, recipe, store) -> TSRunResult`:
    1. **`ts_opt` stage.** Stage = `_with_kind(engine.stage, "ts_opt", options)` where options =
       engine options + `opt.<k>` for every resolved TS option + `opt.name`, `opt.version` (the
       identity) + `opt.forming_bonds` = `";".join(f"{i}-{j}")` over the sorted pairs. Key =
       `build_stage_key(spec.start, stage, engine.identity)`. Hit with `failed_reason` → return a
       failed `TSRunResult` (no engine call); hit → rebuild `TSSearchResult` from the payload with
       `model_validate`; miss → `find_saddle(spec.start, engine, forming_bonds=…,
       options=recipe.ts_options)`; save `result.model_dump(mode="json")`. On
       `TSSearchFailedError` save `{"failed_reason": "ts_search_failed:<reason>", "message":
       str(exc)}`; on `ScfConvergenceError` `{"failed_reason": "scf_convergence", …}`; any other
       error propagates.
    2. **`frequency` stage** on `result.final_state`, same key rule and payload as the species
       runner (a TS frequency row is indistinguishable from any other frequency row of that
       geometry; that is intended, R10). A cached `failed_reason` is returned as the failure.
    3. **Bonds** of the final TS: `perceive_bonds(final_state)`; `connectivity_equal_bool` =
       (bonds mapped through `reference_map` == `perceive_bonds(reference)`) when a reference is
       given, else `None` (reported only; mission R3).
    4. **Validate** with the frequency Hessian, `spec.forming_bonds`, `recipe.validation_options`,
       `recipe.analysis`.
    5. If `mode_count_passed_bool`: `ts_thermochemistry(final_state, hessian, energy, validation=…,
       bonds=…, energy_source="optimization", config=recipe.thermo_config,
       analysis=recipe.analysis)` → `TransitionStateRecord(ts_id, state, search, validation,
       thermo, degeneracy=1)`. Else `failed_reason="ts_validation_failed"`, validation kept.
    6. `TSRunResult` (frozen dataclass): `ts_id`, `record: TransitionStateRecord | None`,
       `search: TSSearchResult | None`, `validation: TSValidation | None`, `failed_reason: str |
       None`, `connectivity_equal_bool: bool | None`, `metrics` (per stage `ts_opt` and
       `frequency`: `cache_hits`, `rows_created`, `engine_calls`, `wall_time_s`), `keys`
       (`{"ts_opt": key, "frequency": key}`), and `as_payload()` returning a JSON-ready dict with
       unit-suffixed keys and `history` included under `search` (callers exclude it from
       comparisons, N11).
- **Readers check `failed_reason` first** (R50): the `ts_opt` and `frequency` readers here, and
  `as_payload`.
- **Never** call `check_ground_state`, `_frequency_and_thermo`, `_push`, `_dedup_after_push` or
  `run_species` (N3, mission R13).

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  geomeTRIC may run only as a black box through `geometric-optimize` and its `--help` text.
- **Clean room, nMAP (v0.4.0 Q1).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach". Never open, clone, fetch or search Eta_Scripts or nMAP (GitHub,
  `~/PROJECTS/cleanroom-nmap`, a cache, a web or code search); only its `TRANSFER_LOG.md` may be
  read. Never message the clean-room seats.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.5.0`, cut re-entrantly from Base (the
  mission commit on main, parent `0d2a8d3`). One code commit per slice unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff. Every commit ends with exactly
  two footer lines, `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, `<version>` read from
  `.agents/hacf-manifest.json` at commit time; no co-author or session trailer. Author "Thomas J.
  L. Mustard Ph.D." (repo-local git config). Never `--no-verify`, never rewrite history.
- **Code graph first.** The first command is `python3 .agents/scripts/hyper_codegraph.py index`;
  it must print `index: ok` (the red team saw `stale_index`). Anything else stops the slice. The
  graph only widens a blast radius.
- **Ledger.** Only through `hyper_ledger.py` / `hypergraph_updater.py`, never by hand. On an
  existing node, `ensure-node --id <node>` takes the **full** `--files` list (it replaces); count
  the node's globs before and after. No slice creates a node.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF v0.6.3.** No `HACF-install.sh` (never without `--ref`), no `HACF-uninstall.sh`, no
  `hyper_migrate.py apply`. On OpenRig 0.7.21, `hyper_spec.py`/`hyper_migrate.py` warn "outside
  the pinned contract", `hyper_spec.py proof` writes the proof natively and `hyper_migrate.py
  verify` skips `rig scope audit`: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git:
  every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host (shared with the hacf and cleanroom rigs).** Before any E2E, GPU, engine or full-suite
  run: `free -g` and `ps` for other rigs' heavy python/pytest/engine processes; if one is active,
  wait (poll at most every 5 minutes with Monitor or a background wait, never a foreground sleep)
  for GPU/E2E work; the full CPU unit suite may run serially beside another rig's small batches
  only with ≥ 6 G available. Record the check in the proof. GPU/E2E runs one at a time. Never kill
  another rig's process. The check and the heavy command are separate calls (or the check exits
  non-zero), never echo-then-run.
- **Engines.** Every xtb command sets
  `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (without it the
  xtb E2E skips with exit 0). UMA runs in `.venv-accept-uma` on CUDA. Every E2E command runs
  under coreutils `timeout 3600`; an expiry is stop-and-report with the output.
- **Lessons (mission R26):** unit-suffixed numeric keys (R54); no energy- or record-ordered list
  in a compared output (R55); one `gated_outcome` per test, `pending_*` fails under
  `ETA_RXNCAT_ACCEPTANCE=1` (R56); any reader of a store or runner payload checks `failed_reason`
  first (R50); re-dedup after any geometry change (v0.3.0 path unchanged); tolerances are measured
  before they are written, never guessed; the candidate rule (code commit C1 with a clean tree,
  E2E at C1, then a commit of only `tests/candidate_outputs/v0.5.0/*` as C2).
- **Required checks** (AGENTS.md), all exit 0 before each commit: `uv sync --locked`;
  `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv run pytest`;
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception (N1).
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it; never loosen a tolerance
  (TJ's or this SPEC's). Never use `AskUserQuestion`.
- **Never** push, tag or open a PR.

## 1. The Confidence Mandate

**Score: 9/10.** Every step, key part and payload is fixed. The engine-free tests use a fake TS
optimizer and a fake engine, so no measurement is open here.

## Mini-requirements

1. **Happy path (fakes):** a fake `TransitionStateOptimizer` returning a fixed `TSSearchResult` and
   a fake engine with a Hessian that has one imaginary mode on the active set → a record with
   `degeneracy == 1`, one imaginary in `thermo`, `failed_reason is None`.
2. **Cache (G6):** a second `run_transition_state` with the same store: `ts_opt` and `frequency`
   `cache_hits == 1` each, `rows_created == 0`, zero optimizer and engine calls, and an equal
   payload (excluding `metrics` and timing).
3. **Keys:** changing any TS option, the forming bonds, the optimizer `version`, or the start
   geometry changes the `ts_opt` key; the `frequency` key equals the species runner's for the same
   geometry and engine stage (computed in the test with the species runner's helper).
4. **Failures cached:** a fake raising `TSSearchFailedError(reason="max_steps")` → row with
   `failed_reason == "ts_search_failed:max_steps"`; the rerun returns the same failure with zero
   optimizer calls. Same for `ScfConvergenceError`. A Hessian with two imaginary modes →
   `failed_reason == "ts_validation_failed"`, no thermo, validation kept.
5. **N3 spy:** patching the four species-runner helpers and `run_species` to raise shows zero
   calls on the happy and the failure paths.
6. **Connectivity:** with a reference equal to the start and the identity map,
   `connectivity_equal_bool` is true; with a reference missing one bond it is false; the result is
   recorded only.
7. `as_payload()` has only unit-suffixed numeric keys (a test walks it) and no list in
   energy order.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read the code named above.
- [ ] Task 2: `orchestrator/ts.py`; export from `eta_rxncat.orchestrator`.
- [ ] Task 3: `tests/unit/orchestrator/test_ts_runner.py`; required checks.
- [ ] Task 4: commit; updater for node `eta_rxncat_species_runner` (no glob change; the updater
  should now see `species_runner → mapping`).

## 4. The Negative Space (Constraints)

- **DO NOT** change `orchestrator/species.py` behaviour (importing its helpers is fine).
- **DO NOT** pass a TS through the minimum path (N3).
- **DO NOT** gate anything on `connectivity_equal_bool` (N7).
- **DO NOT** change the store schema or `KEY_SCHEMA`.

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_ts_runner.py -q` passes.
- [ ] The cache-hit and failure-cache tests pass (listed by name in the proof).
- [ ] The N3 spy test passes.
- [ ] The required checks exit 0.

## Source material

- Mission §5 "TS runner", R10, R11, R13, R17, R20, R27; `src/eta_rxncat/orchestrator/species.py`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.3 (build order; its code and contracts are used here)
- OPR.0.5.0.4 (build order; its code and contracts are used here)
