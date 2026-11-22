---
id: OPR.0.2.0.5
slice: 05-rdkit-ff
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the rdkit_ff engine: UFF/MMFF94 energies, analytic forces and FD Hessians for neutral closed-shell states only (charge 0, multiplicity 1; R35), with perception and round-trip checks, refusing everything else."
depends_on: [OPR.0.2.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/engines/test_rdkit_ff.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: RDKit UFF / MMFF94 engine (`rdkit_ff`)

## Intent

Implement `RDKitFFEngine` (tag `rdkit_ff`): UFF and MMFF94 single-point energies and analytic
forces, plus an FD Hessian, for states RDKit can represent. Anything it cannot represent is
refused with `EngineInputError`.

Context the builder needs (self-contained).

TJ v0.2.0 Q2 "A": engines that cannot represent a state's charge or spin refuse it. Replan R35
(lead decision A; mission US-003 governs) sets the rule:
- `rdkit_ff` accepts **only charge 0 and multiplicity 1**. UFF has no electrostatics by default,
  so ion energies are not meaningful, even though RDKit 2026.09.2 perceives `[H][O-]` and
  `[H][O+]([H])[H]` and has parameters for them (builder's measurement).
- For neutral molecules, the perception and round-trip check (R14) stays:
  `rdDetermineBonds.DetermineBonds(mol, charge=0)`, the perceived element multiset equals
  `state.symbols`, and the total formal charge is 0.

The starter (`docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py`, reference
only) swallows perception errors and falls back to coordinates-only terms. That is a defect, and
a register entry.

The base engine framework (`eta_rxncat.engines.base`, `options`, `units`, `fd`, `identity`) comes
from slice 04. `rdkit` is in the base install (BSD-3-Clause), imported inside the engine only.

Keyed options: `fd_step_bohr` (float, 0.005), `engine_impl` (1). `StageConfig.method` is `uff` or
`mmff94`; anything else → `EngineInputError`. No runtime arguments.

## 1. The Confidence Mandate

**Score: 10/10.** The API, refusal rules, references and tolerances are fixed and testable on the
base install.

## Mini-requirements

1. `engines/rdkit_ff.py`, `RDKitFFEngine(Engine)` with `tag = "rdkit_ff"` and `ENGINE_IMPL = 1`.
   `identity = EngineIdentity(name="rdkit_ff", version=library_version("rdkit"), model=None)`.
2. Evaluate:
   - build an RDKit mol from symbols and coordinates (Å);
   - `DetermineBonds(mol, charge=state.charge)`;
   - run the round-trip check;
   - set up the force field: UFF (`UFFHasAllMoleculeParams`, `UFFGetMoleculeForceField`) or MMFF
     (`MMFFHasAllMoleculeParams`, `MMFFGetMoleculeProperties`, `MMFFGetMoleculeForceField`);
   - energy kcal/mol → Hartree; gradient kcal/mol/Å → forces Hartree/Bohr, negated (units
     module);
   - Hessian, when requested: `fd_hessian` on the engine's own forces, with `hessian_method =
     "finite_difference"`.
   - `device = "cpu"`.
3. Refusals with `EngineInputError`, checked in this order:
   - (a) **charge ≠ 0 or multiplicity ≠ 1** (R35), before any RDKit call, with exactly the message
     `rdkit_ff: charge <q>, multiplicity <m>: only neutral closed-shell states (charge 0, multiplicity 1) are supported`;
   - (b) perception raises;
   - (c) round-trip mismatch (element multiset, or a non-zero total formal charge);
   - (d) missing UFF or MMFF parameters.
   
   The (b)–(d) messages also name the engine, charge and multiplicity.
   
   Catch only RDKit's specific exception types. Name them after checking what `DetermineBonds`
   raises on this RDKit version; no bare `Exception`.
4. Register rows (status `open`) vs the starter: engine name `rdkit_uff` → `rdkit_ff`; swallowed
   errors → refusal; coordinates-only fallback dropped; units.

## 3. Implementation Plan (Task List)

- [ ] Task 1: engine and refusals.
- [ ] Task 2: tests in `tests/unit/engines/test_rdkit_ff.py` (default suite; tiny molecules),
  using the shared test set in `tests/unit/engines/data/`. Create that directory with the five `.xyz`
  files of mission §5 "Test set": water, hydroxide, hydroxyl, hydronium, Pd anion. Each file
  holds a comment line with `charge=<q> multiplicity=<m>`, and the loader lives in
  `tests/unit/engines/conftest.py`.
- [ ] Task 3: register rows; four gates.

## 4. The Negative Space (Constraints)

- **DO NOT** fall back to coordinates-only or connectivity-free terms.
- **DO NOT** import rdkit at module level.
- **DO NOT** accept a multiplicity other than 1, or a state whose perceived charge differs.

## Proof contract

- [ ] Water, UFF and MMFF94 each:
  - energy equals RDKit's own `ff.CalcEnergy()` on the same perceived mol, converted with
    `engines.units` (≤1e-10 relative);
  - forces equal `−ff.CalcGrad()` converted (≤1e-10 relative);
  - forces match central FD of the engine energy at step 1e-4 Å (≤1e-5 Eh/Bohr).
- [ ] Each case gives `EngineInputError` with the message naming `rdkit_ff`, the charge and the
  multiplicity:
  - hydroxide (charge −1);
  - hydronium (+1);
  - hydroxyl (multiplicity 2);
  - a deliberate round-trip mismatch (water geometry with `charge=-2`).
- [ ] Behavioural check (R4): the same water geometry at charge 0 vs multiplicity 2 → the second
  is refused, so no silent pass.
- [ ] `hessian=True` on water → 9×9 `finite_difference`, exactly symmetric, `hessian_max_asymmetry`
  recorded.
- [ ] `engine.stage.options == {"fd_step_bohr": 0.005, "engine_impl": 1}` for a stage with no
  options. An unknown option → `EngineInputError`.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0. The base-install no-heavy-import test still prints `[]`.

## Source material

- Mission §5 Contracts and Test set, R4, R14, R16; TJ v0.2.0 Q2; the starter `rdkit_xtb.py`
  (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base)
