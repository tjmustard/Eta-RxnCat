---
id: OPR.0.5.0.3
slice: 03-prfo
mission: release-0.5.0
status: done
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Implement the clean-room Cartesian P-RFO saddle search (TransitionStateOptimizer, PRFOOptimizer) with exact-Hessian seed and refresh, Bofill updates, trust radius and forming-bond mode following, proved on unequal-mass model surfaces."
depends_on: [OPR.0.5.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_optimize
parent: null
hacf_touches: ["src/eta_rxncat/optimize/**", "tests/unit/optimize/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/optimize]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 clean-room P-RFO saddle search (optimize)

## Intent

Implement `TransitionStateOptimizer` and `PRFOOptimizer`: a clean-room Cartesian partitioned-RFO
saddle search seeded and periodically refreshed with the engine's Hessian, Bofill-updated in
between, with a trust radius and mode following that starts from the forming-bond mode, proved on
analytic model surfaces with unequal masses.

Context the builder needs:
- **Clean room (TJ A1, verbatim "Q1. A").** Write this only from: Banerjee, Adams, Simons &
  Shepard, *J. Phys. Chem.* 1985, 89, 52 (partitioned RFO); Baker, *J. Comput. Chem.* 1986, 7, 385
  (P-RFO for transition states, mode following); Bofill, *J. Comput. Chem.* 1994, 15, 1 (the
  update); and the algorithm below. Never open geomeTRIC, Sella, pysisyphus, Eta_Scripts or the
  starter's `ts_optimizer.py`. MIT, numpy, base install.
- **Interfaces to read:** `src/eta_rxncat/optimize/base.py` (`Optimizer` — do **not** change it;
  `OptionSpec`, `resolved_options` logic and `_coerce`, which the new ABC reuses),
  `optimize/errors.py` (`OptimizerInputError`, `OptimizationFailedError(message, *, steps,
  last_energy_hartree)`), `engines/base.py` (`Engine.evaluate(state, *, forces, hessian) ->
  PotentialResult` with `energy_hartree`, `forces_hartree_per_bohr` (forces = −gradient),
  `hessian_hartree_per_bohr2`, `hessian_method`), `engines/units.py` (Å ↔ Bohr), and how
  `tests/unit/optimize/` and `tests/unit/mapping/test_relax.py` build fake engines.
- **New `optimize/ts_base.py`** (pure Python, no numpy): `TransitionStateOptimizer(abc.ABC)` with
  `OPTIONS: ClassVar[Mapping[str, OptionSpec]]`, abstract property `identity -> OptimizerIdentity`,
  `resolved_options(options)` (same rules and messages as `Optimizer.resolved_options`, plus: a
  key `"constraints"` is refused by name), and abstract
  `find_saddle(state, engine, *, forming_bonds: Sequence[tuple[int, int]] = (), options=None) -> TSSearchResult`.
  It has no frozen-atom or dihedral parameter (R21). Separate from `Optimizer` (R12).
- **New error** in `optimize/errors.py`: `TSSearchFailedError(OptimizationFailedError)` with
  attribute `reason: Literal["max_steps", "too_many_rejections", "mode_lost", "no_reaction_mode",
  "wall_time_exceeded"]`, constructed as `TSSearchFailedError(message, *, reason, steps,
  last_energy_hartree)`, the reason named in the message.
- **New `optimize/prfo.py`** (numpy): `PRFOOptimizer(TransitionStateOptimizer)`; export both
  classes and the error from `eta_rxncat.optimize`.
  - `identity`: `OptimizerIdentity(name="prfo", version="src-" + sha256(bytes of prfo.py)[:16])`,
    read from the module file at first use (R11). Never `eta_rxncat.__version__`.
  - `OPTIONS` (keyed, defaults): `max_steps` int 100; `hessian_refresh_steps` int 5;
    `trust_radius_bohr` 0.10; `trust_min_bohr` 0.001; `trust_max_bohr` 0.30;
    `max_consecutive_rejections` int 5; `min_initial_overlap` 0.60; `min_mode_overlap` 0.50;
    `max_gradient_hartree_per_bohr` 4.5e-4; `rms_gradient_hartree_per_bohr` 3.0e-4;
    `max_step_bohr` 1.8e-3; `rms_step_bohr` 1.2e-3; `max_wall_time_s` 1800.0;
    `ratio_floor_hartree` 1e-8. Refused before any engine call (`OptimizerInputError`): unknown key,
    wrong type, `constraints`, a non-positive number, `trust_min ≤ trust_radius ≤ trust_max`
    violated, fewer than 3 atoms, a linear state (rank of the rigid basis < 6), forming-bond
    indices out of range, duplicate pairs, or i == j.
  - **Coordinates (R7).** Cartesian, Bohr. Rigid basis: three unit translations and the three
    rotations `e_a × (r_k − centroid)` about the **unweighted geometric centroid**, orthonormalised
    by SVD; C = the 3N × (3N − 6) orthonormal complement. Projected gradient Cᵀg, Hessian CᵀHC
    (symmetrised). Never masses, never `thermo.modes`.
  - **Loop.** Step 0: `engine.evaluate(state, forces=True, hessian=True)` (an exact Hessian).
    Then repeat:
    1. Diagonalise CᵀHC (ascending eigenvalues b, eigenvectors V; Cartesian vectors C·V).
    2. **Followed mode.** At step 0, with `forming_bonds`: s = Σ over pairs (i, j) of (−u on atom i,
       +u on atom j), u the unit i→j vector, then s ← C Cᵀ s / ‖·‖; choose the Cartesian
       eigenvector with the largest \|⟨v, s⟩\|; if that is < `min_initial_overlap`, raise
       `TSSearchFailedError(reason="no_reaction_mode")`. Without `forming_bonds`: the lowest
       eigenvalue. Afterwards: the eigenvector with the largest \|overlap\| with the previous
       followed Cartesian vector, sign-aligned to it; if that is < `min_mode_overlap` and the
       current Hessian is a Bofill update, refresh exactly and choose again; if still below,
       `reason="mode_lost"`.
    3. **Step (Baker 1986)** in the eigenbasis, F_k = (CV)_kᵀ g, followed index f:
       λ_p = b_f/2 + ½√(b_f² + 4F_f²), Δ_f = −F_f/(b_f − λ_p); for the others, λ_n is the root of
       λ = Σ_{k≠f} F_k²/(λ − b_k) below min(0, min_{k≠f} b_k), by bracketed bisection/Newton to
       \|Δλ\| ≤ 1e-12 within 200 iterations (else `mode_lost`); Δ_k = −F_k/(b_k − λ_n).
       Δx = C V Δ; if ‖Δx‖ > trust, scale to trust. Predicted ΔE = gᵀΔx + ½ ΔxᵀHΔx.
    4. Evaluate energy and gradient at x + Δx (`forces=True, hessian=False`). ρ = ΔE_actual /
       ΔE_predicted, with ρ = 1 if \|ΔE_predicted\| < `ratio_floor_hartree`.
       - **Reject** if ρ < 0 or ρ > 3: revert, trust ← max(0.25·trust, trust_min), exact Hessian
         at the reverted geometry; more than `max_consecutive_rejections` in a row →
         `reason="too_many_rejections"`.
       - **Accept** otherwise: trust ← min(2·trust, trust_max) if 0.75 ≤ ρ ≤ 1.25 and ‖Δx‖ ≥
         0.9·trust; trust ← max(0.5·trust, trust_min) if ρ < 0.25 or ρ > 1.75. Every
         `hessian_refresh_steps`-th accepted step: exact Hessian; otherwise the **Bofill update**
         with s = Δx, y = g_new − g_old, r = y − Hs: H_MS = H + rrᵀ/(rᵀs); H_PSB = H + (rsᵀ +
         srᵀ)/(sᵀs) − (rᵀs)ssᵀ/(sᵀs)²; φ = (rᵀs)²/((rᵀr)(sᵀs)); H ← φH_MS + (1 − φ)H_PSB,
         symmetrised; if \|rᵀs\| < 1e-12‖r‖‖s‖, PSB alone.
    5. **Converged** after an accepted step when all hold on the **unprojected** gradient and that
       step: max\|g\| ≤ 4.5e-4, RMS g ≤ 3.0e-4 Eh/Bohr, max\|Δx\| ≤ 1.8e-3, RMS Δx ≤ 1.2e-3 Bohr
       (keyed). Return `TSSearchResult` (slice 02 contract) with the counts, `hessian_method` of
       the last exact Hessian, the final gradient norms and `final_rigid_gradient_norm` = ‖(I −
       CCᵀ)g‖, the sorted forming bonds, resolved options, identity and a `TSStep` per step.
    6. `max_steps` accepted+rejected steps → `reason="max_steps"`; `max_wall_time_s` exceeded
       (checked before each engine call) → `reason="wall_time_exceeded"`.
  - `EngineError` propagates unchanged; no other exception is caught. No `assert` in `src/`.
- **Model surfaces for tier D** (in `tests/unit/optimize/test_prfo.py`; analytic energy,
  gradient and Hessian in Hartree/Bohr, functions of interatomic distances only, so rigid-motion
  invariant; the fake engine returns `hessian_method="analytic"`):
  - **S1 (4 atoms, masses H, C, O, C — given to the state as symbols H, C, O, C):** pick a
    non-planar reference geometry; E = Σ_{pairs ≠ (0,3)} ½k_p(r_p − r_p⁰)² − ½k₁x² + ¼c x⁴ with
    x = r₀₃ − r₀₃⁰. The saddle is the reference geometry. Choose one soft pair constant so that at
    the start (x outside the inflection region, all pairs perturbed, the whole frame rotated by a
    random proper rotation) the **lowest** Hessian eigenvector has overlap < 0.60 with the (0, 3)
    forming stretch while another eigenvector has ≥ 0.60 (assert both). `forming_bonds=[(0, 3)]`.
  - **S2 (6 atoms, two forming bonds (0, 4) and (1, 5)):** harmonic terms on all other 13 pairs
    and E_rxn = −½k₁q₊² + ¼c q₊⁴ + ½k₂q₋² with q± = (x₁ ± x₂)/√2, x₁ = r₀₄ − d, x₂ = r₁₅ − d.
    Saddle at the reference geometry; a start where the reaction mode is the lowest.
  - **S3:** S2 started so close to the saddle that it converges in ≤ 3 steps (sanity).
- Measured facts this slice relies on (mission HF-5…7, HF-11): on real TSs and mapped starts the
  forming-stretch overlap of the reaction mode on the projected Cartesian Hessian is 0.841–0.953
  and every other mode's ≤ 0.389, on GFN2 and UMA; "largest active-core fraction" picked the
  wrong mode in 5 of 14 states (N5).

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

**Score: 9/10.** The algorithm, every number and the failure paths are fixed. Whether the model
surfaces' parameters produce the stated start conditions is checked by the tests themselves
(assert, then converge); choosing those parameters is the builder's.

## Mini-requirements

1. **G1:** on S1 (rotated start, reaction mode not the lowest) and S2, `find_saddle` converges;
   every atom within 1e-4 Bohr of the reference after Horn superposition (unweighted; a test-local
   SVD Kabsch is fine); the projected exact Hessian at the result (computed by the test) has
   exactly one negative eigenvalue; `final_rigid_gradient_norm_hartree_per_bohr ≤ 1e-10`.
2. **Mode choice:** on S1 a test asserts the chosen initial mode is the max-overlap one, not the
   lowest; with `forming_bonds=()` the lowest is chosen (recorded in `history[0]`).
3. **Cadence (US-004):** a counting fake asserts an exact Hessian at step 0, at every 5th accepted
   step and after each rejection, and Bofill otherwise (`hessian_source` per `TSStep`);
   `n_hessian_calls`, `n_gradient_calls`, `n_hessian_refreshes`, `n_rejected_steps` equal the
   fake's counts.
4. **Bofill:** a unit test of the update on random s, y against the formula written in the test;
   the PSB-only branch when rᵀs = 0.
5. **Failures, one test each:** `no_reaction_mode` (forming bond orthogonal to every low mode),
   `too_many_rejections` (a fake whose energy jumps so ρ > 3), `max_steps` (`max_steps=2` far from
   the saddle), `mode_lost` (a fake that swaps its Hessian eigenvectors after step 1),
   `wall_time_exceeded` (`max_wall_time_s` tiny with a slow fake). Each raises
   `TSSearchFailedError` with that `reason`, is an `OptimizationFailedError`, and carries steps and
   the last energy. An `EngineError` from the fake propagates as the same object (`is`).
6. **Refusals before any engine call:** every `OptimizerInputError` case listed above, with the
   fake recording zero calls.
7. **Identity:** `version` starts with `"src-"`, has 16 hex characters, and equals the sha256 of
   the module file's bytes computed in the test.
8. **G3:** importing `eta_rxncat.optimize`, `eta_rxncat.optimize.ts_base`, `eta_rxncat.optimize.prfo`
   loads no `geometric`, `torch`, `pyscf`, `fairchem`, `rdkit` (extend the import test).
9. Existing `Optimizer` subclasses (`GeometricOptimizer`, the test `Toy`, mapping's
   `RecordingOptimizer`) are untouched and their tests pass.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read the interfaces named above.
- [x] Task 2: `ts_base.py`, `TSSearchFailedError`.
- [x] Task 3: `prfo.py` (projector, mode choice, step, trust, Bofill, convergence, failures).
- [x] Task 4: model surfaces and the tests above; required checks.
- [x] Task 5: commit; updater for node `eta_rxncat_optimize` (no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** read any TS optimizer's source (N2); **DO NOT** import geomeTRIC in `prfo.py`.
- **DO NOT** change `Optimizer`, `GeometricOptimizer` or any existing test double.
- **DO NOT** use masses or `thermo` anywhere in `optimize/` (N6); **DO NOT** pick the initial mode by
  active-core fraction (N5).
- **DO NOT** accept frozen atoms, dihedrals or a `constraints` option (N12).
- **DO NOT** return a non-converged result; **DO NOT** compute a final Hessian after convergence
  (the runner does, R27).

## Proof contract

- [ ] `uv run pytest tests/unit/optimize -q` passes; the proof lists S1/S2 step counts and the
  final displacement from the reference.
- [ ] Each of the five failure reasons and the refusals has a passing test.
- [ ] The import test passes for the three modules.
- [ ] The required checks exit 0.

## Source material

- Mission §5 "P-RFO", R2, R7, R11, R12, R14, R15, R21, R24, R27, HF-5…HF-7, HF-11; the three papers.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.2 (build order; its code and contracts are used here)
