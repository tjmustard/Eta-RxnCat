---
id: OPR.0.5.0.14
slice: 14-bofill-guard
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Make bofill_update return the Hessian unchanged when the residual or the step is exactly zero, so no bare ZeroDivisionError escapes the TS search, and test the lost-mode-on-Bofill exact-refresh recovery path."
depends_on: [OPR.0.5.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_optimize
parent: null
hacf_touches: [src/eta_rxncat/optimize/prfo.py, "tests/unit/optimize/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/optimize]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 Bofill zero-residual guard and the lost-mode recovery test (optimize)

## Intent

Make `bofill_update` return the Hessian unchanged when the residual r = y − Hs or the step s is
exactly zero (instead of letting a `ZeroDivisionError` escape the search), and add the missing test
of the path "mode lost on a Bofill-updated Hessian → exact refresh → the search recovers and
converges". Mission R29. Replan 1, from audit 03's handback (`qitem-20261124051212-668b769f`).

Context the builder needs:
- **The defect (audit 03, reproduced).** In `src/eta_rxncat/optimize/prfo.py`, `bofill_update`
  with `H = diag(1, 2, 3)` and `y = H s` gives r = 0: the PSB-only test
  `|rᵀs| < 1e-12·‖r‖‖s‖` reads `0 < 0`, is false, and the Murtagh–Sargent branch divides by
  rᵀs = 0. A bare `ZeroDivisionError` then escapes `find_saddle`. That breaks the failure
  contract (only `TSSearchFailedError` or `EngineError` may leave it) and R50's named-failure
  caching in slice 05. With s = 0, sᵀs = 0 divides in PSB the same way.
- **The rule (Bofill 1994; mission §5 "P-RFO", amended by R29).** Every update in the Bofill family
  is H plus a correction built from r, chosen so that the new Hessian satisfies the secant
  condition H_new s = y. At r = 0 the current H already satisfies it, and both the MS and the PSB
  correction terms vanish as r → 0, so the update is the identity. With s = 0 there is no step to
  learn from. So, **before any division**: if rᵀr == 0.0 or sᵀs == 0.0 (the computed floats,
  which also catches underflow), return `0.5·(H + Hᵀ)` unchanged in value. That step's
  `TSStep.hessian_source` stays `"bofill"`, because it is the update's value, not a new exact
  Hessian. Every other input keeps the existing formula and branch exactly. No tolerance is
  added or changed, and no `try/except ZeroDivisionError` is used.
- **Optimizer identity.** Editing `prfo.py` changes `OptimizerIdentity.version` (sha of the file,
  R11), which is what R11 is for. No stored TS record exists yet (slice 05 writes the first ones),
  so nothing has to be migrated.
- **The recovery path (`prfo.py`, the `followed < 0` branch of the loop).** When the followed
  mode's overlap drops below `min_mode_overlap` on a Bofill Hessian, the search computes an exact
  Hessian at the current geometry and chooses again. Only if the exact Hessian also fails does it
  raise `mode_lost`. The existing `mode_lost` test covers only the second outcome.
- **Interfaces to read:** `src/eta_rxncat/optimize/prfo.py` (`bofill_update`, the loop,
  `_choose_mode`, `_exact`), `tests/unit/optimize/test_prfo.py` (surfaces S1–S3, `SurfaceEngine`,
  `run`, `expected_calls`, the existing Bofill and `mode_lost` tests). Nothing outside
  `optimize/` changes.

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  The guard here comes from the Bofill 1994 update and R29, never from any implementation.
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

**Score: 10/10.** It is a two-condition guard with a fixed return value, two unit tests on
fixed inputs and one recovery test. That test forces the path by replacing the update, so it
needs no tuned surface parameter.

## Mini-requirements

1. **Guard:** in `bofill_update`, `if rr == 0.0 or ss == 0.0: return 0.5 * (hessian + hessian.T)`
   before any division (names as in the current code). The docstring states the rule and cites
   R29. Everything else in the function is unchanged.
2. **r = 0 test:** `H = diag(1.0, 2.0, 3.0)`, a fixed nonzero s, `y = H @ s`. Under
   `np.errstate(all="raise")`, `bofill_update(H, s, y)` returns an array equal to H
   (`np.array_equal`), and the secant condition `H_new @ s == y` holds within 1e-12.
3. **s = 0 test:** the same H, `s = zeros(3)`, any finite y: returns H, raises nothing (under
   `np.errstate(all="raise")`).
4. **Unchanged elsewhere:** the existing `test_bofill_update_matches_the_formula` and
   `test_bofill_psb_only_when_r_orthogonal_to_s` pass unmodified.
5. **Recovery test (lost on Bofill → exact refresh → recover):** run S2 (or S1) with
   `monkeypatch` replacing `eta_rxncat.optimize.prfo.bofill_update` by a test-local function. On
   its first call it returns the exact Hessian with its projected eigenvectors rotated, so the
   followed vector's best overlap is < `min_mode_overlap`; for example, swap the eigenvalues of the
   followed mode and of a mode orthogonal to it, keeping the matrix symmetric. On later calls it
   delegates to the real function. Assert all of these:
   - the search converges to the reference saddle (same criterion as G1);
   - no `TSSearchFailedError` is raised;
   - the counting fake records one extra exact-Hessian call at the step after the first Bofill
     update, beyond the regular schedule (`expected_calls` plus one), and `n_hessian_refreshes`
     matches the fake's count;
   - that step's `TSStep.hessian_source` is `"exact"`.

   The existing `mode_lost` test still passes; it is the other outcome (exact refresh also lost).
## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read the interfaces named above.
- [x] Task 2: the guard and docstring in `bofill_update`.
- [x] Task 3: tests 2, 3 and 5 in `tests/unit/optimize/test_prfo.py`; required checks.
- [x] Task 4: commit; updater for node `eta_rxncat_optimize` (no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** read any TS optimizer's source (N2). The guard comes from the Bofill 1994 update
  and R29 only.
- **DO NOT** change the Bofill formula, the PSB-only threshold (1e-12), the refresh cadence, the
  mode-following rule, `min_mode_overlap` or any other option or tolerance.
- **DO NOT** catch `ZeroDivisionError` (or any exception) to hide the defect; **DO NOT** add an
  `assert` to `src/`.
- **DO NOT** touch any file outside `src/eta_rxncat/optimize/prfo.py` and
  `tests/unit/optimize/test_prfo.py` (plus the ledger through the updater); in particular nothing
  in `thermo/` (slice 04 is being built concurrently on that node).

## Proof contract

- [ ] `uv run pytest tests/unit/optimize -q` passes; the proof lists the three new test names.
- [ ] The proof states the reproduction before the fix: the r = 0 call raised
  `ZeroDivisionError`. Run it against the parent commit or before editing, and quote the
  one-line traceback tail.
- [ ] The required checks exit 0.

## Source material

- Mission R29 (new), §5 "P-RFO" (Bofill bullet, amended), R11, R50; Bofill, *J. Comput. Chem.*
  1994, 15, 1; audit 03 handback `qitem-20261124051212-668b769f`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.3 (build order; its code is amended here)
