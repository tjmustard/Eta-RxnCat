---
id: OPR.0.5.0.2
slice: 02-ts-contracts
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Add the frozen TS contracts to eta_rxncat.core (prfo optimizer name, ts_opt stage kind, core/ts_models.py) without changing any existing field."
depends_on: [OPR.0.5.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 TS contracts (core)

## Intent

Add the frozen, strict TS contracts to `eta_rxncat.core` — the `"prfo"` optimizer name, the
`"ts_opt"` stage kind and `core/ts_models.py` — without changing any existing field, so every
v0.3.0/v0.4.0 cached row and promoted fixture still validates.

Context the builder needs:
- **Existing code (read it):** `src/eta_rxncat/core/optimization_models.py` (`OptimizerIdentity`
  with `name: Literal["geometric"]`, whose docstring already says "v0.5.0 widens `name`";
  `OptimizationResult` with a strict `converged` validator), `core/models.py` (`CoreModel`:
  `extra="forbid"`, frozen; `StageKind` at line 16; `MolecularState`, `ScalarValue`,
  `NonNegativeInt`), `core/results.py` (`HessianMethod`), `core/thermo_models.py` (`ThermoResult`),
  `core/__init__.py` (exports). v0.3.0's `tests/unit/core/` has `test_identity_rejected` with a
  `"sella"` case; it must still be rejected.
- **Changes (mission §5 "Contracts", R1, R10, R17, R20):**
  1. `OptimizerIdentity.name: Literal["geometric", "prfo"]`; docstring updated.
  2. `StageKind` gains `"ts_opt"` (additive; R10). Nothing else in `models.py` changes.
  3. New `src/eta_rxncat/core/ts_models.py`, exported from `eta_rxncat.core`, every class a
     `CoreModel`, pydantic and the standard library only (no numpy):
     - `FormingBond`: `i: NonNegativeInt`, `j: NonNegativeInt`; validator `i < j`.
     - `TSStep`: `step: NonNegativeInt`, `accepted_bool: bool`, `energy_hartree: FiniteFloat`,
       `max_gradient_hartree_per_bohr: NonNegativeFiniteFloat`, `trust_radius_bohr:
       PositiveFiniteFloat`, `followed_eigenvalue_hartree_per_bohr2: FiniteFloat`,
       `mode_overlap: FiniteFloat | None` (in [0, 1] when set), `hessian_source:
       Literal["exact", "bofill"]`, `ratio: FiniteFloat | None`.
     - `TSSearchResult`: `final_state: MolecularState`, `final_energy_hartree: FiniteFloat`,
       `converged: Literal[True]` (strict, same `mode="before"` validator as
       `OptimizationResult`), `n_steps`, `n_gradient_calls`, `n_hessian_calls`,
       `n_hessian_refreshes`, `n_rejected_steps: NonNegativeInt`, `hessian_method:
       HessianMethod`, `followed_eigenvalue_hartree_per_bohr2: FiniteFloat`,
       `final_max_gradient_hartree_per_bohr`, `final_rms_gradient_hartree_per_bohr`,
       `final_rigid_gradient_norm_hartree_per_bohr: NonNegativeFiniteFloat`, `forming_bonds:
       list[FormingBond]` (sorted by (i, j), unique, every index < atom count), `optimizer:
       OptimizerIdentity`, `options: dict[str, ScalarValue]`, `history: list[TSStep]` (step
       order; `history[k].step == k`). The docstring says `history` is never compared (R20).
     - `TSValidationOptions`: `imag_tol_cm1: PositiveFiniteFloat = 20.0`, `cutoff_cm1:
       FiniteFloat = -50.0`, `min_active_core_ke_fraction = 0.60`, `min_forming_stretch_overlap
       = 0.50`, `forming_distance_min_angstrom = 1.90`, `forming_distance_max_angstrom = 2.90`.
       Validators: `cutoff_cm1 < -imag_tol_cm1`; both fractions in (0, 1]; distances positive and
       min < max. Docstring: TJ A2 "Q2.  A"; mission R3.
     - `TSValidation`: `n_imaginary: NonNegativeInt`, `imaginary_frequency_cm1: FiniteFloat |
       None`, `active_core_ke_fraction: FiniteFloat | None`, `forming_stretch_overlap:
       FiniteFloat | None`, `forming_bonds_in_phase_bool: bool | None`,
       `forming_distances_angstrom: dict[str, PositiveFiniteFloat]` (keys `"i-j"`, i < j),
       `options: TSValidationOptions`, `active_atom_indices: list[NonNegativeInt]` (sorted,
       unique, non-empty), `mode_count_passed_bool`, `active_core_passed_bool`,
       `identity_passed_bool`, `passed_bool: bool`, `reasons: list[str]`. Validators:
       `passed_bool == (mode_count and active_core and identity)`; `reasons` sorted, unique,
       ⊆ `TS_VALIDATION_REASONS`; `reasons == []` iff `passed_bool`; `n_imaginary == 0` implies
       the three optional numbers are `None`.
     - `TS_VALIDATION_REASONS: frozenset[str]` = `{"active_core_fraction_below_threshold",
       "forming_bonds_out_of_phase", "forming_distance_out_of_window",
       "forming_overlap_below_threshold", "imaginary_above_cutoff", "multiple_imaginary_modes",
       "no_imaginary_mode"}`.
     - `TransitionStateRecord`: `ts_id: str` (min length 1), `state: MolecularState`, `search:
       TSSearchResult`, `validation: TSValidation`, `thermo: ThermoResult`, `degeneracy:
       Literal[1]` (TJ Q-TJ2 "A": no enantiomeric-TS degeneracy). Validators:
       `validation.mode_count_passed_bool` is true; `len(thermo.imaginary_frequencies_cm1) == 1`;
       `state` equals `search.final_state` (symbols, charge, multiplicity, coordinates).
- `OptimizationResult`, `ConformerRecord`, `ConformerEnsemble` and every other existing model are
  **unchanged** (R1). Existing JSON round-trips stay byte-identical.

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

**Score: 10/10.** Every field, type and validator is listed; the changes are additive.

## Mini-requirements

1. `OptimizerIdentity(name="prfo", version="src-0123456789abcdef")` validates; `"sella"` is still
   rejected; every existing identity test passes unchanged.
2. `StageConfig(kind="ts_opt", …)` validates; every existing `StageKind` value still validates.
3. Each new model: one passing construction and one rejecting test per validator (bad order of
   `FormingBond`, an unknown reason, `passed_bool` inconsistent, `reasons` unsorted, a
   `converged` of `1`, a `TransitionStateRecord` with two imaginary modes or a failed mode count,
   `history[k].step != k`, a forming bond out of range, `cutoff_cm1 = -10`).
4. Every new model round-trips through `model_dump(mode="json")` / `model_validate` exactly.
5. A test loads `tests/fixtures/v0.4.0/m1_relaxed.xtb.json`'s `optimizer` block and a v0.3.0
   fixture's (read `tests/fixtures/v0.3.0/` for one that carries an `optimizer`) into
   `OptimizerIdentity` unchanged.
6. `import eta_rxncat.core` loads no numpy or RDKit (extend the existing import test).

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read the files named above.
- [ ] Task 2: widen `name`, add `"ts_opt"`; write `ts_models.py`; export.
- [ ] Task 3: tests under `tests/unit/core/test_ts_models.py`; required checks.
- [ ] Task 4: commit; updater for node `eta_rxncat_core` (no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** change any existing field, default or validator of an existing model.
- **DO NOT** import numpy, RDKit or any engine/optimizer module in `core/`.
- **DO NOT** add a TS field to `OptimizationResult` or `ConformerRecord` (R1).

## Proof contract

- [ ] `uv run pytest tests/unit/core -q` passes, including the new file and the unchanged identity tests.
- [ ] The import test shows no numpy/RDKit after `import eta_rxncat.core`.
- [ ] The v0.3.0 and v0.4.0 fixture `optimizer` blocks validate unchanged.
- [ ] The required checks exit 0.

## Source material

- Mission §5 "Contracts", R1, R10, R11, R17, R20; `src/eta_rxncat/core/`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.1 (build order; its code and contracts are used here)
