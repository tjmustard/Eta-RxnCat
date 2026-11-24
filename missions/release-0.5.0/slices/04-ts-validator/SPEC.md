---
id: OPR.0.5.0.4
slice: 04-ts-validator
mission: release-0.5.0
status: done
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Add validate_transition_state (TJ's A2 numbers plus the measured TS identity check) and ts_thermochemistry (one imaginary mode excluded, sigma from the bond graph, no TS degeneracy), leaving the minimum path unchanged."
depends_on: [OPR.0.5.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_thermo
parent: null
hacf_touches: ["src/eta_rxncat/thermo/**", "tests/unit/thermo/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/thermo]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 TS validator, σ from a bond graph and TS thermochemistry (thermo)

## Intent

Add `thermo/ts.py` — `validate_transition_state` (TJ's A2 numbers plus the measured TS identity
check) and `ts_thermochemistry` (exactly one imaginary mode excluded, σ from the TS's perceived
bond graph, no TS degeneracy) — leaving the minimum path of `thermochemistry` bitwise unchanged.

Context the builder needs:
- **TJ A2, verbatim "Q2.  A":** exactly one mode below −20 cm⁻¹ (thermo's `imag_tol_cm1`), that
  mode below −50 cm⁻¹, mass-weighted active-core KE fraction ≥ 0.60, all keyed.
  **Q-TJ2, verbatim "A / A / A" (second answer):** σ from the geometry for reactants and the TS; no
  enantiomeric-TS degeneracy.
- **Read:** `thermo/modes.py` (`normal_modes` returns `NormalModes.frequencies_cm1` ascending and
  `modes_cartesian` 3N × n, each column a unit-length Cartesian displacement), `thermo/masses.py`
  (`atomic_masses_amu`), `thermo/rrho.py` (`thermochemistry`: σ at line ~157, imaginary modes
  `f < -imag_tol` excluded, soft modes as \|ν\|), `thermo/symmetry.py`
  (`rotational_symmetry_number`), `thermo/_geometry.py` (`automorphisms(mol, max)`,
  `permuted_rmsds`), `thermo/errors.py` (`ThermoInputError`), slice 02's `core/ts_models.py`.
- **`thermo/symmetry.py` (additive):** `rotational_symmetry_number_from_bonds(state, bonds, *,
  analysis) -> int`: build an RDKit mol of `state.symbols` in order, every atom `SetNoImplicit(True)`,
  the given bonds as single bonds; then exactly the existing algorithm (linear → 2/1 by
  centrosymmetry; else count automorphisms whose permutation is undone by a proper rotation within
  `sym_tol_angstrom`). Shares the algorithm with `rotational_symmetry_number` (factor out a private
  helper; the SMILES function's results are unchanged).
- **`thermo/rrho.py` refactor:** move the body of `thermochemistry` after the σ line into a private
  `_thermochemistry(state, hessian, electronic_energy_hartree, sigma, *, energy_source, config,
  analysis)`. `thermochemistry(smiles=…)` computes σ as now and calls it; its outputs are bitwise
  unchanged (the existing thermo tests and the v0.3.0 fixtures prove it).
- **New `thermo/ts.py`:**
  - `TSValidationInputError(ThermoInputError)`.
  - `validate_transition_state(state, hessian_hartree_per_bohr2, *, forming_bonds:
    Sequence[tuple[int, int]], options: TSValidationOptions | None = None, analysis:
    ThermoAnalysisOptions | None = None) -> TSValidation`.
    - Refuse (`TSValidationInputError`): `state.active_atom_indices` empty; `forming_bonds` empty;
      a pair with i == j, duplicates or out of range; `options.imag_tol_cm1 !=
      analysis.imag_tol_cm1` (the gate and thermo must agree; mission F-check "Imaginary count").
    - `normal_modes(...)`; n_imaginary = count of ν < −imag_tol. The reaction mode is index 0 (the
      lowest). If n_imaginary == 0: numbers `None`, reason `no_imaginary_mode`, all three passes false.
    - `mode_count_passed_bool` = n_imaginary == 1 and ν₀ < `cutoff_cm1`; reasons
      `multiple_imaginary_modes` (> 1), `imaginary_above_cutoff` (ν₀ ≥ cutoff).
    - KE fraction of mode 0: Σ_{a∈active} m_a‖d_a‖² / Σ_a m_a‖d_a‖² with d the unit Cartesian
      displacement and m from `atomic_masses_amu`; `active_core_passed_bool` = fraction ≥
      threshold, else reason `active_core_fraction_below_threshold`.
    - Identity (mission R3): unit forming-stretch vector s (for each pair (i, j): −u on i, +u on
      j, u = unit i→j vector in Å; summed; normalised); overlap = \|⟨s, d⟩\| ≥
      `min_forming_stretch_overlap` (else `forming_overlap_below_threshold`); in phase = all
      `(d_j − d_i)·u_ij` have the same sign (else `forming_bonds_out_of_phase`); every forming
      distance in [min, max] Å (else `forming_distance_out_of_window`); distances recorded under
      `"i-j"`. `identity_passed_bool` = all three.
    - Returns a `TSValidation` with every number, the options, the sorted active set and the
      sorted reasons.
  - `ts_thermochemistry(state, hessian, electronic_energy_hartree, *, validation, bonds,
    energy_source, config=None, analysis=None) -> ThermoResult`: raise `ThermoInputError` unless
    `validation.mode_count_passed_bool`; σ = `rotational_symmetry_number_from_bonds(state, bonds,
    …)`; call `_thermochemistry`; then raise `ThermoInputError` unless the result lists exactly one
    imaginary frequency equal to `validation.imaginary_frequency_cm1` within 1e-6 cm⁻¹.
- **Measured values this slice must not contradict** (mission HF-4, HF-6, HF-8): at the literature
  TSs on GFN2/UMA, one mode below −20, KE fractions 0.810–0.951, overlaps 0.723–0.833 with every
  other mode ≤ 0.281, forming distances 2.166–2.378 Å, every TS σ = 1, Cp σ = 2.
- Export `validate_transition_state`, `ts_thermochemistry`, `TSValidationInputError`,
  `rotational_symmetry_number_from_bonds` from `eta_rxncat.thermo`.

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

**Score: 10/10.** Formulae, refusals, reasons and the refactor boundary are fixed; the real-TS
numbers are already measured.

## Mini-requirements

1. **G2:** on a hand-built Hessian (a 4-atom system with unequal masses, one imaginary mode built
   in by construction), the KE fraction equals an independent computation in the test file within
   1e-12, and the overlap and distances equal hand-computed values within 1e-12.
2. **Reasons:** one test per reason and per refusal; `passed_bool` true only with no reason; a
   state with two imaginary modes gives `multiple_imaginary_modes` and `mode_count_passed_bool`
   false; an imaginary at −30 cm⁻¹ gives `imaginary_above_cutoff`.
3. **Real data (marker `xtb`, so the default suite deselects it by `addopts`; it is never a
   skip):** a test computes the GFN2 Hessian of TJ's committed
   `tests/e2e/data/e2e5/xyz/TS1a_n.xyz` with eta's xtb engine and asserts: one mode below −20, at
   −416 ± 5 cm⁻¹ (measured −416.2), KE fraction on `[0..5]` ≥ 0.60 (measured 0.930), overlap ≥ 0.50
   for bonds (1, 2), (3, 5) (measured 0.805), `passed_bool` true. The proof runs it with
   `ETA_RXNCAT_XTB=… uv run pytest -m xtb tests/unit/thermo/test_ts.py` and records the outcome.
4. **σ:** `rotational_symmetry_number_from_bonds` equals `rotational_symmetry_number` on every
   molecule the existing symmetry tests use (bonds from the SMILES mol in AddHs order), and gives
   1 for TS1a_n with its perceived bonds.
5. **TS thermo:** on a minimum's Hessian with a single imaginary mode injected, `ts_thermochemistry`
   equals `_thermochemistry` with the same σ to 1e-12 Eh; refuses when `mode_count_passed_bool` is
   false or the imaginary lists differ.
6. **Unchanged minimum path:** every existing thermo test passes unchanged; a test asserts
   `thermochemistry` on one v0.3.0 case returns the same `ThermoResult` JSON as before the refactor
   (record it from Start in the test as a literal, or compare with `_thermochemistry` called with
   the SMILES σ).
7. `import eta_rxncat.thermo.ts` loads no `geometric`, `torch`, `pyscf`, `fairchem`.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read the files named above.
- [x] Task 2: σ helper; `_thermochemistry` refactor (run the thermo suite before going on).
- [x] Task 3: `thermo/ts.py`; exports.
- [x] Task 4: `tests/unit/thermo/test_ts.py`; required checks (host check before an xtb test).
- [x] Task 5: commit; updater for node `eta_rxncat_thermo` (no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** change what `thermochemistry` or `check_ground_state` return for any input.
- **DO NOT** import `eta_rxncat.mapping` or `eta_rxncat.orchestrator` from `thermo/` (bonds are passed in).
- **DO NOT** treat a second mode below `imag_tol_cm1` as valid; **DO NOT** skip the fraction check
  (DV-05); **DO NOT** validate with an empty active set or no forming bonds (N14).
- **DO NOT** loosen any number of TJ's A2 or of R3.

## Proof contract

- [ ] `uv run pytest tests/unit/thermo -q` passes, and the `-m xtb` run of `test_ts.py` passes with `ETA_RXNCAT_XTB` set (0 skips).
- [ ] The independent KE-fraction comparison is ≤ 1e-12.
- [ ] Every existing thermo test passes unchanged.
- [ ] The required checks exit 0.

## Source material

- Mission §5 "Validator and TS thermo", R1, R3, R16, R17, HF-4, HF-6, HF-8; `src/eta_rxncat/thermo/`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.2 (build order; its code and contracts are used here)
