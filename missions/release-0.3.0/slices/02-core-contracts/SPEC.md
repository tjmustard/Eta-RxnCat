---
id: OPR.0.3.0.2
slice: 02-core-contracts
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Add frozen, strict core contracts (ThermoAnalysisOptions, ThermoResult, OptimizerIdentity, OptimizationResult, ConformerRecord, ConformerEnsemble) with pass/reject tests, keep eta_rxncat.core free of numpy/RDKit/geomeTRIC, and trim the core ledger description."
depends_on: [OPR.0.3.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", tests/unit/test_package.py, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Core contracts for thermochemistry, optimization and conformer ensembles

## Intent

Add the frozen, strict core data contracts v0.3.0 exchanges — `ThermoAnalysisOptions`,
`ThermoResult`, `OptimizerIdentity`, `OptimizationResult`, `ConformerRecord`, `ConformerEnsemble` —
with pass/reject tests, keep `eta_rxncat.core` free of numpy/RDKit/geomeTRIC, and trim the core
ledger description.

Context the builder needs:
- Core is data-only (pydantic + stdlib, no numpy): `core/results.py` says "Data only: plain lists,
  no numpy", and `tests/unit/test_package.py::test_import_loads_no_heavy_modules` holds it. All
  models subclass the existing `CoreModel` (`extra="forbid"`, frozen) with ADR-0003 strictness:
  chemistry ints `StrictInt`, floats finite (reuse the existing `FiniteFloat`,
  `PositiveFiniteFloat`, `NonNegativeInt`, `PositiveInt`, `ScalarValue` aliases in `core/models.py`).
- `ThermoConfig` (`core/models.py:271`) is reused **unchanged**.
- Existing core test files: `test_core_graph_io.py`, `test_core_mapping_thermo.py`,
  `test_core_molecule.py`, `test_core_potential_result.py`, `test_core_stage.py`. New names below do
  not collide.
- `eta_rxncat_core`'s description is 1977/2000. Rewrite it to ≤ 1800 characters including the new
  models, via `hyper_ledger.py ensure-node --id eta_rxncat_core --description-file <file>`; files
  unchanged (`core/**` already covers the new modules).

**Seat rules for every v0.3.0 slice (self-contained; the mission SPEC is `missions/release-0.3.0/SPEC.md`):**
- Branch `feature/eta-rxncat-v0.3.0`, cut re-entrantly from Base `7993284`. One code commit per
  slice; record `Start` (HEAD when you begin) in your handoff.
- First command of the slice: `python3 .agents/scripts/hyper_codegraph.py index`. It must print
  `index: ok`; anything else stops the slice. The audit treats `code_graph.status != ok` as a
  finding. The code graph only widens the blast radius; it never narrows it.
- Ledger: only `hyper_ledger.py` / `hypergraph_updater.py`. Use `ensure-node --id <node>` on
  existing nodes and pass the **full** `--files` list (it replaces). `ensure-node --from-spec` no
  longer drops other slices' files (HACF v0.6.1 E5), but count the node's globs before and after
  anyway. Never edit `spec/compiled/architecture.yml` by hand. `eta_rxncat_engines` is not touched.
- Scratch: `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs). Remove
  temp clones, venvs and scratch directories at the end of each step.
- No `HACF-install.sh`, `HACF-uninstall.sh` or `hyper_migrate.py apply`. Ignore any "review it with
  hyper_migrate.py plan" line (known false positive). On OpenRig 0.7.21, `hyper_spec.py` and
  `hyper_migrate.py` warn "outside the pinned contract" and `hyper_spec.py proof` writes the proof
  natively: expected, note it in the proof, not a finding.
- Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git: every `git diff`,
  `git show`, `git log -p` over a range that contains a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`. Never write `tests/fixtures/`. `PRDs/` is read-only.
- Required checks (AGENTS.md), all exit 0 before the commit: `uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, and
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- Licence (TJ, verbatim): "I would prefer to keep ASE out as it would be a major core dependency.
  The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP,
  conf search can be copy left. Because they can be replaced with a new engine later. But the core
  remains." / "It's fine that the engine MACE pulls in ASE just not the core." No agent-made
  licence exception.
- A host fact that does not hold, a failed engine run, or a bound that measured noise breaks is
  stop-and-report to the lead with the output — never worked around, never a loosened tolerance.
- Never push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 10/10.** Field lists and validators are fully specified below.

## Mini-requirements

1. `src/eta_rxncat/core/thermo_models.py`:
   - `ThermoAnalysisOptions`: `imag_tol_cm1: PositiveFiniteFloat = 20.0`, `sym_tol_angstrom:
     PositiveFiniteFloat = 0.05`, `linear_tol_angstrom: PositiveFiniteFloat = 1e-3`,
     `max_automorphisms: PositiveInt = 100000`.
   - `ThermoResult`: `n_atoms: PositiveInt`; `electronic_energy_hartree: FiniteFloat`;
     `energy_source: Literal["optimization", "single_point"]`; `zpe_hartree`,
     `thermal_correction_enthalpy_hartree`, `thermal_correction_gibbs_hartree`,
     `entropy_hartree_per_k`, `gibbs_free_energy_hartree`, `standard_state_correction_hartree`:
     `FiniteFloat`; `entropy_components_hartree_per_k: dict[Literal["translational", "rotational",
     "vibrational", "electronic"], FiniteFloat]`; `frequencies_cm1`, `imaginary_frequencies_cm1`,
     `soft_modes_cm1: list[FiniteFloat]`; `rotational_symmetry_number: PositiveInt`; `is_linear:
     bool`; `config: ThermoConfig`; `analysis: ThermoAnalysisOptions`; `masses_source: str`
     (min_length 1).
   - Validators: all four entropy keys present, summing to the total within 1e-12 relative (abs
     1e-30 floor); frequency count = 0 if `n_atoms == 1` (then `is_linear` must be False), else
     3N−5 if linear, else 3N−6; `n_atoms == 2` requires `is_linear`; `frequencies_cm1` ascending;
     `imaginary_frequencies_cm1` = exactly the frequencies < −`analysis.imag_tol_cm1`;
     `soft_modes_cm1` = exactly those in [−imag_tol, 0); `gibbs_free_energy_hartree ==
     electronic_energy_hartree + thermal_correction_gibbs_hartree` within 1e-12 Eh.
2. `src/eta_rxncat/core/optimization_models.py`: `OptimizerIdentity(name: Literal["geometric"],
   version: str min_length 1)` (docstring: v0.5.0 widens the Literal for P-RFO);
   `OptimizationResult(final_state: MolecularState, final_energy_hartree: FiniteFloat, converged:
   Literal[True], n_steps: NonNegativeInt, n_engine_calls: NonNegativeInt, recovery_steps:
   list[str], optimizer: OptimizerIdentity, options: dict[str, ScalarValue])`.
3. `src/eta_rxncat/core/ensemble_models.py`: `ConformerRecord(state: MolecularState, optimization:
   OptimizationResult, thermo: ThermoResult, degeneracy: Literal[1, 2], source_ids:
   list[NonNegativeInt])` — `source_ids` ≥ 1 and unique; `thermo.n_atoms == len(state.symbols)`.
   `ConformerEnsemble(species_id: str min_length 1, smiles: str min_length 1, records:
   list[ConformerRecord] min_length 1, boltzmann_weights: list[FiniteFloat], lowest_index:
   NonNegativeInt, ensemble_gibbs_hartree: FiniteFloat, temperature_k: PositiveFiniteFloat)` —
   lengths match; weights ≥ 0 and sum to 1 within 1e-12; `lowest_index` is the argmin of
   `thermo.gibbs_free_energy_hartree` with ties to the lowest index; all records share symbols,
   charge and multiplicity; every `record.thermo.config.temperature_k == temperature_k`.
4. Re-export all six from `eta_rxncat.core` (`__init__.py`, `__all__`).
5. Carry-forward (DV-23): a docstring note on `PotentialResult` consumers; the test that a
   `PotentialResult` is unchanged after a consumer copies its matrices lands in slice 03.
6. `import eta_rxncat.core` still loads no `numpy`, `rdkit`, `geometric` (extend the existing
   subprocess test's module list).

## 3. Implementation Plan (Task List)

- [x] Task 1: `thermo_models.py` + tests `tests/unit/core/test_core_thermo_models.py`.
- [x] Task 2: `optimization_models.py` + `tests/unit/core/test_core_optimization_models.py`.
- [x] Task 3: `ensemble_models.py` + `tests/unit/core/test_core_ensemble_models.py`.
- [x] Task 4: re-exports; extend `test_package.py` heavy-module list.
- [x] Task 5: core description trim; `hyper_ledger.py validate`; required checks; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** import numpy, RDKit or geomeTRIC in `eta_rxncat.core`.
- **DO NOT** change `ThermoConfig`, `PotentialResult` or any existing model.
- **DO NOT** add a ground-state boolean to `ThermoResult`.

## Proof contract

- [ ] For each validator in Mini-requirements 1–3, one passing and one rejecting test (e.g. entropy
  keys missing → rejected; 3N−6 vs 3N−5 count; N = 1 with 1 frequency → rejected; N = 2 non-linear →
  rejected; weights summing to 1 + 1e-9 → rejected; ties pick the lowest index; mixed charge across
  records → rejected; `converged=False` → rejected; `degeneracy=3` → rejected; duplicate
  `source_ids` → rejected).
- [ ] Every model is frozen (assignment raises) and rejects an extra field.
- [ ] `uv run pytest tests/unit/core tests/unit/test_package.py` exit 0; the no-heavy-import test
  lists `numpy`, `rdkit`, `geometric` and prints `[]`.
- [ ] Core description ≤ 1800 characters; `hyper_ledger.py validate` exit 0; required checks exit 0.

## Source material

- Mission §5 "Contracts"; R36; ADR-0003; `src/eta_rxncat/core/models.py`, `results.py`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.1 (starter, register)
