---
id: OPR.0.2.0.6
slice: 06-pyscf-cpu
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the PySCF engine's CPU path: keyed DF and auxbasis, the def2 ECP rule, explicit charge/spin RKS/UKS, ddCOSMO and C-PCM from a solvent table, the SCF escalation ladder with mandatory stability analysis, and analytic gradients/Hessians checked against FD."
depends_on: [OPR.0.2.0.4, OPR.0.2.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/prd/v0.2.0/DISCREPANCIES.md, "docs/prd/v0.2.0/evidence/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, "-m", slow, tests/unit/engines/test_pyscf_cpu.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: PySCF engine, CPU path (`pyscf_gpu_cpu`): DF, ECP, solvation, SCF ladder with stability, analytic derivatives

## Intent

Implement the CPU path of `PySCFEngine` (tag `pyscf_gpu_cpu`). It runs density-fitted
RKS/UKS/RHF/UHF with explicit charge and spin, with the def2 ECP rule, ddCOSMO and C-PCM
solvation from a solvent name or dielectric, and the plan's SCF escalation ladder with a mandatory
stability analysis. It returns analytic gradients and Hessians, checked against finite
differences. Slice 07 adds the GPU dispatch on top of the same resolved stage.

Context the builder needs (self-contained).

Plan PR #6: "PySCFEngine with GPU4PySCF dispatch, ddCOSMO/PCM solvation, SCF escalation ladder
(DIIS -> level-shift/SOSCF -> small-basis `project_dm_nr2nr` projection) and automatic CPU DF-KS
fallback above VRAM threshold."

Resolve measured on this host, with PySCF 2.15.1 at B3LYP/def2-SVP and `conv_tol` 1e-10:
- water DF minus non-DF is 1.0e-5 Eh, so DF is keyed;
- linear PdCl₂ converges to **different SCF solutions depending on the initial guess**, 7.9 mEh
  apart. The higher state is internally unstable, and following it lands lower and still
  unstable;
- `[PdCl₄]²⁻` and `[PdCl₃(C₂H₄)]⁻` are guess-independent and internally stable;
- a def2 basis without `ecp=` runs Rh/Pd all-electron with no error. With `ecp="def2-svp"`,
  PdCl₂ has 52 electrons.

Hence mission R2, R3, R9 and ADR-0018 (PROPOSED).

TJ v0.2.0 Q1 "C both": reference = plain PySCF on the same input, plus analytic-vs-FD checks and
ladder recovery. The engine base comes from slice 04, and the shared test set (`.xyz` with charge
and multiplicity) is in `tests/unit/engines/data/` (slice 05). `pyscf` is in the base install
(Apache-2.0), imported inside the engine only. The starter
(`docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py`) is reference only;
it ignores the solvent name.

## 1. The Confidence Mandate

**Score: 9/10.** The options, rules, ladder and tolerances are fixed and grounded in resolve's
measurements. The residual is PySCF's analytic Hessian coverage for each solvation and DF
combination, which this slice determines and records. FD of analytic gradients is the labelled
fallback.

## Mini-requirements

1. `engines/pyscf_gpu_cpu/` (package):
   - `PySCFEngine(Engine)`, with `tag = "pyscf_gpu_cpu"` and `ENGINE_IMPL = 1`;
   - `identity = EngineIdentity(name="pyscf_gpu_cpu", version=library_version("pyscf"), model=None)`.
     Slice 07 keeps this identity: the device is not keyed, and the gpu4pyscf version goes into
     the result's `device_reason`/notes, never the identity.
   - `StageConfig.method` is an xc name accepted by `pyscf.dft.libxc`, or `hf`.
   - `StageConfig.basis` is required (core already enforces this).
2. Keyed options, filled into `engine.stage`:

   | Option | Type | Default |
   |---|---|---|
   | `density_fit` | bool | `True` |
   | `auxbasis` | str | `def2-universal-jkfit` |
   | `ecp` | str | `auto` (resolved per state, rule 3, R36) |
   | `grids_level` | int | 3 |
   | `conv_tol` | float | 1e-10 |
   | `init_guess` | `minao` \| `atom` \| `huckel` | `minao` |
   | `pcm_method` | `C-PCM` \| `IEF-PCM` | `C-PCM` |
   | `ladder_small_basis` | str | per rule 5: `minao` for def2-* bases, else `sto-3g` (R37) |
   | `stability` | `internal` | `internal` |
   | `fd_step_bohr` | float | 0.005 |
   | `hessian_mode` | `auto` \| `fd_gradients` \| `analytic` | `auto` (rule 7, R41) |
   | `engine_impl` | int | 1 |

   Runtime arguments: `device` (`auto`|`cpu`|`cuda`; this slice implements `cpu` only, and `auto`
   = `cpu` until slice 07), `max_memory_mb` (int), `ladder_max_cycle` (int, default 100; tests
   inject small values).
3. ECP rule (R3, as amended by R36; lead decision A). `engine.stage`, the stage the cache key
   hashes (slice 04, ADR-0016), keeps `ecp = "auto"` as a keyed literal unless the caller gives an
   explicit value. The key stays exact, because the rule below is a pure function of
   `(basis, symbols)`, and both are already keyed.

   The engine adds `resolved_stage_for(state) -> StageConfig`: `engine.stage` with `ecp` replaced
   by the concrete value. `evaluate` builds the mol from it, and the per-state proofs read it.
   - `auto`: if the basis starts with `def2-` (case-insensitive) and any atom has Z > 36 → the
     basis name; with Z ≤ 36 everywhere → `"none"`; a non-def2 basis with any Z > 36 →
     `EngineInputError`;
   - an explicit `ecp` value (anything but `auto`) is used as given and validated against PySCF.
     It must exist for every element with Z > 36, else `EngineInputError`. `"none"` with any
     Z > 36 under a def2 basis → `EngineInputError` (R3: never all-electron def2 for Z > 36);
   - PySCF must have the resolved ECP for every Z > 36 element, else `EngineInputError`.

   Known cost: explicit `ecp="def2-svp"` and implicit `auto` give different keys for the same
   physics. That is a harmless cache miss, never a wrong hit.
4. Charge and spin: `mol.charge = state.charge`, `mol.spin = multiplicity − 1`. Multiplicity 1
   uses RKS (RHF for `hf`); above that, UKS (UHF). Coordinates go in Å with `unit="Angstrom"`.
5. SCF ladder (R9). Run in order, stopping at the first converged step:
   1. `diis`: a plain SCF with `init_guess`, `max_cycle = ladder_max_cycle`;
   2. `level_shift`: `level_shift = 0.25`, `damp = 0.5`, starting from the last density;
   3. `soscf`: `mf.newton()`;
   4. `small_basis_projection`: converge the same functional in `ladder_small_basis` (`minao` for
      def2-* bases, else `sto-3g`, R37; keyed; an explicit option overrides it), with the **same
      resolved ECP** as the target. Project it with
      `pyscf.scf.addons.project_dm_nr2nr(mol_small, dm_small, mol)`, then run a DIIS SCF from that
      guess.

      Measured (PySCF 2.15.1): `def2-sv(p)` does not exist (`BasisNotFoundError`), and
      `def2-sv_p`/`def2svp` normalise to def2-SVP itself. `minao` covers Rh, Pd, Ru, Ir, Pt, Au, Os
      and W; `sto-3g` stops at Xe. On the Pd anion, the `minao` and `sto-3g` projections both
      converge to E = −1586.87553329 Eh.
   
   Each attempted step is appended to `recovery_steps` (e.g. `["diis", "level_shift"]`). If every
   step fails → `ScfConvergenceError(steps=…)`.
   
   Then, **always**, internal stability analysis (`mf.stability(internal=True, external=False,
   return_status=True)`):
   - if stable, append `"stability:stable"`;
   - if unstable, rebuild the density from the returned orbitals, re-run the SCF, append
     `"stability:followed"`, and re-check, up to 2 follows;
   - still unstable → `ScfConvergenceError`.
6. Solvation (R2, US-009):
   - `ddcosmo` → `mf.ddCOSMO()` with ε;
   - `pcm` → `mf.PCM()` with `method = pcm_method` and ε;
   - `alpb` is refused (core already pairs it with xtb only).
   
   ε comes from the explicit `dielectric` (which wins) or the solvent-name table in
   `engines/pyscf_gpu_cpu/solvents.py`. That table is a dict of lowercase name → ε from the
   Minnesota Solvent Descriptor Database. It must include at least water 78.3553, toluene 2.3741,
   acetonitrile, methanol, ethanol, dichloromethane, tetrahydrofuran, dimethylsulfoxide, benzene,
   chloroform, acetone and n,n-dimethylformamide. Record the source and version in the module
   docstring; check the values against the copy shipped in GPU4PySCF's `solvent/_solvent_data` or
   PySCF if present, and say which. An unknown name → `EngineInputError`.
7. Derivatives (R41; the builder's measured finding: `~/.hacf/eta-rxncat-hacf/evidence/v020-ks-hessian-finding.md`):
   - gradient: `mf.nuc_grad_method().kernel()` → forces = −grad. Analytic gradients are correct
     everywhere measured (≤6.5e-6 Eh/Bohr vs FD of energy, including the Pd anion and HI with an
     ECP).
   - Hessian, by the keyed `hessian_mode` (default `auto`). It depends only on keyed stage fields
     (method, basis/ECP, solvation, grid) and the state's elements, so the key stays exact:
     - **HF** (RHF/UHF) without ddCOSMO → `mf.Hessian().kernel()`, (N,N,3,3) → 3N×3N,
       symmetrised, `hessian_method="analytic"`. Measured correct, 1.1e-5 to 2.8e-5.
     - **Every KS functional**, and HF with ddCOSMO (ddCOSMO has no analytic Hessian:
       `AttributeError 'surface'`) → `fd_hessian` on the engine's analytic gradients (6N SCF plus
       gradient calls, step `fd_step_bohr`), symmetrised, `hessian_max_asymmetry` recorded,
       `hessian_method="finite_difference"`.
       PySCF 2.15.1's default analytic KS Hessian (grid response off) is wrong at the default grid.
       Measured: water B3LYP 3.2e-4 (grid 3); HCl 3.3e-3; HBr B3LYP 0.24 (H_zz 84% off); HI +
       def2 ECP 3.9e-2 (grid 3) and 1.7e-2 (8%) at grid 9.
     - Explicit `hessian_mode="fd_gradients"` forces FD for any method. Explicit
       `hessian_mode="analytic"` with a KS functional or ddCOSMO → `EngineInputError` ("analytic KS
       Hessian is unreliable in PySCF 2.15.1 (R41)").
   - If the rule depends on the state (Aprime envelope by element), resolve it per state through
     `resolved_stage_for(state)` (R36's mechanism); `engine.stage` keeps `auto`.

   Record the measured support matrix and these errors in
   `docs/prd/v0.2.0/evidence/pyscf-cpu-support.json`, generated by a seat command, not by
   product code.
8. Errors:
   - PySCF exceptions are caught by named type and re-raised as `EngineRuntimeError` (tail) or
     `EngineInputError` (e.g. an unknown xc or basis), `from` the cause;
   - no bare `Exception`;
   - `device = "cpu"`, `device_reason = None`.
9. Register rows (status `open`) vs the starter: the solvent name now used; engine name
   `pyscf_<xc>_<basis>` → the tag; ladder steps; ECP rule; DF keyed; stability added; the
   `< −75.0` test replaced by a reference comparison.

## 3. Implementation Plan (Task List)

- [ ] Task 1: options, ECP rule, mol build, RKS/UKS (Mini-requirements 1–4).
- [ ] Task 2: the ladder and stability (Mini-requirement 5).
- [ ] Task 3: solvation and the table (Mini-requirement 6).
- [ ] Task 4: derivatives, the support matrix, errors (Mini-requirements 7–8).
- [ ] Task 5: tests in `tests/unit/engines/test_pyscf_cpu.py`:
  - default suite: sto-3g/HF water tests (fast);
  - `slow` marker: B3LYP/def2-SVP, the Pd anion and the FD checks.
- [ ] Task 6: register rows; four gates; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** run a def2 basis for Z > 36 without its ECP.
- **DO NOT** accept a converged SCF without the stability analysis, or hide a stability follow.
- **DO NOT** leave `density_fit`, `auxbasis`, `ecp`, `grids_level`, `conv_tol`, `init_guess`,
  `pcm_method` or `ladder_small_basis` unkeyed.
- **DO NOT** import pyscf at module level, or import gpu4pyscf or torch anywhere in this slice.
- **DO NOT** catch bare `Exception`, or return a partial result.

## Proof contract

- [ ] Reference (default suite, HF/sto-3g water): energy, gradient and Hessian equal plain PySCF
  built the same way (`density_fit` true, same auxbasis), ≤1e-10 Eh (energy), ≤1e-8 Eh/Bohr
  (gradient).
- [ ] `slow` (B3LYP/def2-SVP):
  - water and `[PdCl₃(C₂H₄)]⁻` energies equal plain PySCF (≤1e-8 Eh);
  - analytic gradient vs central FD of energy (step 1e-3 Bohr) ≤1e-5 Eh/Bohr, on water (all
    coordinates) and on the Pd anion (the 3 Pd coordinates and the 3 of the first C);
  - R41 (i): HF/def2-SVP water: analytic Hessian vs FD of analytic gradients ≤1e-4 Eh/Bohr²;
  - R41 (ii): B3LYP/def2-SVP water: the engine's Hessian (`hessian_method == "finite_difference"`)
    vs energy second differences (gradient-free; central, step 0.005 Bohr, 4-point formulas for
    off-diagonals) ≤1e-4 Eh/Bohr²;
  - R41 (iii) canary: PySCF's own default analytic B3LYP Hessian (grid response **off**) for HBr
    (def2-SVP, grid 3) differs from FD of analytic gradients by more than 1e-2 Eh/Bohr² (measured
    0.24). The test asserts the defect and records the value. If a future PySCF fixes it, the
    test fails with "default analytic KS Hessian now agrees; revisit R41" (slice 05's canary
    pattern);
  - `hessian_mode` resolution as specified in Mini-req 7. `fd_gradients` forces FD for HF. The
    disallowed `analytic` cases raise `EngineInputError`.
- [ ] Literal mapping (R4):
  - hydroxide → `mol.charge == -1`, `mol.spin == 0`, RKS;
  - hydroxyl → `mol.spin == 1`, UKS;
  - the Pd anion → `mol.nelectron == 86` (Pd def2 ECP replaces 28 core electrons; all-electron
    would be 114);
  - behavioural: the hydroxyl geometry at multiplicity 2 vs hydroxide at charge −1 give
    different energies.
- [ ] ECP rule (R36):
  - `engine.stage.options["ecp"] == "auto"` for a stage with no `ecp` option;
  - for the Pd anion with `def2-svp`, `engine.resolved_stage_for(state).options["ecp"] == "def2-svp"`;
  - for water, `== "none"`;
  - the Pd anion with `cc-pvdz` and no `ecp` → `EngineInputError` (from `resolved_stage_for` and
    from `evaluate`);
  - explicit `ecp="def2-svp"` on the Pd anion → used as given, with the same energy as `auto` to
    ≤1e-10 Eh, but a different `build_stage_key` (the recorded known cost);
  - explicit `ecp="none"` on the Pd anion with `def2-svp` → `EngineInputError`;
  - `build_stage_key(state, engine.stage, identity)` is identical for two `auto` stages, and the
    concrete ECP is never written back into `engine.stage`.
- [ ] Ladder (deterministic, injected; default suite on HF/sto-3g water):
  - `ladder_max_cycle=1` makes DIIS fail and records `["diis", "level_shift", …]`, up to the
    step that converges;
  - an injected failure of every step (monkeypatch each step's kernel to report not converged)
    → `ScfConvergenceError` with all four steps;
  - the energy after recovery equals the plain converged energy ≤1e-8 Eh;
  - `recovery_steps` ends with `stability:stable`.
- [ ] Small-basis rung (R37): for a `def2-svp` stage, `engine.stage.options["ladder_small_basis"] == "minao"`;
  for `cc-pvdz`, `"sto-3g"`. A ladder run forced to step 4 (inject `ladder_max_cycle=1` into
  steps 1–3 only) on the Pd anion records `small_basis_projection` and converges to the plain
  energy ≤1e-8 Eh.
- [ ] Stability: a monkeypatched `stability()` that reports unstable once and then stable →
  `"stability:followed"` and then `"stability:stable"`. Always unstable → `ScfConvergenceError`
  after 2 follows.
- [ ] Solvation (`slow` for B3LYP):
  - water C-PCM with `solvent="water"` equals the energy with `dielectric=78.3553` (≤1e-10);
  - it differs from gas phase by more than 1e-4 Eh;
  - ddCOSMO runs;
  - `solvent="Water"` resolves to `water` in `engine.stage`;
  - an unknown solvent → `EngineInputError`.
- [ ] `docs/prd/v0.2.0/evidence/pyscf-cpu-support.json` exists, and each analytic/FD choice in the
  engine matches it.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0. The `slow` tests pass with `uv run pytest -m slow
  tests/unit/engines/test_pyscf_cpu.py`; paste the summary.

## Source material

- Plan PR #6; mission R2, R3, R4, R9, R16, "Resolve's host measurements", Test set; ADR-0018
  (PROPOSED); the starter `pyscf_engine.py` (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base), OPR.0.2.0.5 (the shared test data in `tests/unit/engines/data/`)
