# Eta-RxnCat Living Master Plan

## Project Objectives
* Build **Eta-RxnCat**, a permissively licensed (MIT / BSD / Apache-2.0) computational chemistry library and adaptive workflow engine for **homogeneous organometallic and organocatalytic reaction mechanisms**.
* Maintain a strict **clean-room codebase** (zero copyleft/LGPL in-process dependencies; zero `ase` or `Sella` imports; direct PyTorch tensor adapters for `MACE` and `FAIRChem UMA`; subprocess isolation for `xtb` / `g-xTB`) while crediting `Eta_Scripts` and `nMap` (Mustard, Wender, & Cheong, *ACS Catal.* 2015) in the repository README.
* Execute reaction networks defined in YAML/JSON **priority-gated Reaction Graphs** supporting multi-template 3D geometries, ordered `keep` / `delete` / `alignment` atom lists, explicit per-step `(charge, multiplicity)`, conformer ensemble Boltzmann averaging, and adaptive pruning/skip logic.
* Support **stage-decomposed content-addressed caching** so interrupted workflows resume from exact checkpoints and incremental post-processing stages (such as adding `ddCOSMO`/`PCM` solvation or high-level single-point refinements onto completed gas-phase runs) execute without recomputing upstream optimizations or frequencies.
* Follow strict scientific software engineering practices: trunk-based PR workflow (`main` protected; isolated `feat/*` and `fix/*` branches enabling parallel development across non-overlapping modules), `pytest` unit/integration/E2E test tiers driven by human-authored reaction map fixtures, and semantic versioning from `v0.1.0` to `v1.0.0` (with `v0.x.y` sub-point releases) and post-`v1.0` GUI/visualization extensions.

## Current Hypotheses & Architecture
* **Hypothesis 1 (Conserved Reactive Core):** Across ligand/catalyst perturbations within a fixed mechanism, bond-forming/breaking core atoms remain conserved within ~0.1 Angstrom RMSD (Mustard et al., *ACS Catal.* 2015), enabling reliable TS initial guesses via quaternion/Kabsch alignment + constrained-core MLIP/xTB relaxation prior to saddle-point optimization. *(High confidence)*
* **Hypothesis 2 (Priority-Gated Adaptive Graph Execution):** Evaluating `priority == 1` nodes (selectivity-determining TS pairs or primary RDS) before expanding secondary catalytic-cycle intermediates cuts compute by >5-10x without sacrificing hit discovery, provided covalent-topology diffing flags mechanism-switching outliers. *(High confidence)*
* **Hypothesis 3 (RTX 5060 `sm_120` Hybrid Execution & Direct Tensor Bridge):** Running `MACE` and `UMA-S-1.2.1` (`omol` task) directly via PyTorch `>=2.7+cu128` (bypassing `ASE` calculators via clean-room graph tensor builders) and routing small/medium DFT jobs to `GPU4PySCF` (`1.8.0+` CUDA 12 JIT / CUDA 13 path) with an automatic 6.5 GB VRAM ceiling fallback to CPU density-fitted `PySCF` maximizes local workstation throughput. *(High confidence)*
* **Hypothesis 4 (Condensed-Phase Thermochemistry, Solver Escalation & Stage-Decomposed Caching):** Using Grimme quasi-RRHO vibrational entropy damping plus a 1 M standard-state concentration correction eliminates low-frequency rotor artifacts and artificial bimolecular entropy penalties; multi-stage SCF basis-projection and soft-mode optimizer fallbacks recover convergence failures; and stage-decomposed SQLite/JSON caching enables crash-safe restart and incremental solvation additions. *(High confidence)*
* **Repository & Module Boundary Architecture (Parallel-PR Safe):**
  * `src/eta_rxncat/core/`: Zero-external-chemistry-engine data contracts (`MolecularState` with mandatory `charge` and `spin_multiplicity` per node/step, `ConformerEnsemble`, `AtomMappingSpec` with ordered `keep`/`delete`/`align` indices, `ReactionNode`, `ReactionEdge`, `ReactionGraph`, `StageConfig`, `PotentialResult`, `ThermoResult` with Grimme `qRRHO` + 1 M standard state, `VibrationalMode`), YAML/JSON I/O, and covalent connectivity graph validation.
  * `src/eta_rxncat/store/`: Stage-decomposed, content-addressed SQLite artifact store supporting crash recovery (skipping completed nodes/stages on resubmission) and incremental stage addition (e.g., appending `ddCOSMO`/`PCM` single-point corrections onto completed gas-phase graphs).
  * `src/eta_rxncat/engines/`: Pluggable `Potential` implementations (`rdkit_ff`, `mace`, `uma_direct`, `pyscf_gpu_cpu`, `xtb_subprocess`) + solvation presets (`ddCOSMO`/`PCM` for PySCF, `ALPB` for xTB) + automated SCF escalation ladder (DIIS -> level-shift/SOSCF -> smaller-basis `project_dm_nr2nr` projection).
  * `src/eta_rxncat/conformers/`: 3D conformer generation (`RDKit` ETKDGv3 + torsional/distance-geometry sampling, optional `CREST` subprocess), RMSD/energy deduplication, and Boltzmann ensemble thermodynamics.
  * `src/eta_rxncat/mapping/`: Clean-room quaternion/Kabsch alignment, ordered `keep`/`delete`/`alignment` atom surgery, charge/spin-aware R-group/ligand enumeration, and constrained-core relaxation.
  * `src/eta_rxncat/optimize/`: `geomeTRIC` (BSD-3) wrapper for GS minimization; clean-room TRIC Partitioned Rational Function Optimization (P-RFO) for TS search; soft-mode recovery ladder (trust-radius tightening + exact Hessian refresh + fallback to robust damped/Cartesian/Lanczos optimizer); active-core imaginary-mode projection filter (>=60% kinetic energy overlap on active atoms, single negative frequency < -50 cm^-1).
  * `src/eta_rxncat/orchestrator/`: Priority-ordered DAG scheduler executing `ReactionGraph` nodes stage-by-stage, querying the artifact store before launching compute, evaluating gating rules, and computing reaction barriers, `% ee`, and Energetic Span Model TOF.

## Actionable Steps

### Version Roadmap (`v0.1.0` -> `v1.0.0` -> `v1.x+`)

* **`v0.1.0` — Repo Scaffold, Hardware Gate & Core Schemas**
  1. `PR #1 (feat/repo-scaffold)`: Initialize `pyproject.toml` (MIT, `uv`-managed), `src/eta_rxncat/` layout, README with homage to `nMap` (2015) and `Eta_Scripts`, `AGENTS.md` contributor/PR rules, and GitHub Actions CI (`ruff`, `mypy`, `pytest`, `pip-licenses` blocking GPL/LGPL). *(Starter files generated; ready to commit via PR.)*
  2. `PR #2 (feat/hw-probe)`: Implement `eta_rxncat.utils.hw_probe` verifying PyTorch CUDA `12.8+` (`sm_120`), `GPU4PySCF` (`1.8.0+`) JIT/native kernel execution, and 8 GB VRAM ceiling detection on a ~60-atom organometallic test molecule. *(Starter probe generated; ready to verify on RTX 5060.)*
  3. `PR #3 (feat/core-schemas)`: Implement Pydantic v2 models (`MolecularState` enforcing per-step `charge` & `spin_multiplicity`, `AtomMappingSpec`, `StageConfig`, `ReactionGraph`, Grimme `qRRHO` + 1 M `ThermoConfig`), YAML/JSON loader/validator, and stage-decomposed SQLite artifact store (`eta_rxncat.store`). *(Starter schemas, store, and unit tests generated.)*

* **`v0.2.0` — Clean-Room Potentials (`RDKit FF`, `MACE`, `UMA Direct`, `PySCF/GPU4PySCF`, `xtb` Subprocess)** *(Parallelizable PRs)*
  4. `PR #4 (feat/engine-rdkit-xtb)`: Implement `RDKitFFEngine` (UFF/MMFF94) and process-isolated `XTBSubprocessEngine` (`GFN2-xTB` + `ALPB` solvation). *(Done when unit tests verify energies/gradients and license audit confirms zero LGPL imports.)*
  5. `PR #5 (feat/engine-mlip)`: Implement `MACEEngine` and clean-room `UMADirectEngine` (`uma-s-1.2.1` / `omol` task with charge & spin multiplicity, bypassing `ASE`). *(Done when single-point energies/forces match reference outputs on charged/open-shell organometallic test cases.)*
  6. `PR #6 (feat/engine-pyscf)`: Implement `PySCFEngine` with `GPU4PySCF` dispatch, `ddCOSMO`/`PCM` solvation, SCF escalation ladder (DIIS -> level-shift/SOSCF -> small-basis `project_dm_nr2nr` projection), and automatic CPU DF-KS fallback above VRAM threshold. *(Done when analytical gradients, Hessians, and SCF recovery tests pass.)*

* **`v0.3.0` — Conformer Generation, GS Optimization & Boltzmann Ensemble Gate (Human Fixture Tier 1 & Tier 2)**
  7. `PR #7 (feat/conformers-gs)`: Implement conformer generator (`RDKit` ETKDGv3 + RMSD/energy pruning), `geomeTRIC` GS optimizer wrapper with soft-mode fallback, Grimme `qRRHO` + 1 M thermochemistry, and Boltzmann ensemble averaging. *(Done when unit tests pass on flexible organic/organometallic test molecules.)*
  8. `PR #8 (test/e2e-gs-fixtures)`: Run E2E validation against **Human Fixture 1** (single species conformer search -> optimization -> lowest conformer + Boltzmann distribution) and **Human Fixture 2** (two ground states -> reaction free energy, plus incremental solvation stage test). *(Done when E2E tests pass and benchmark metrics are recorded.)*

* **`v0.4.0` — Conserved-Core Structure Mapper (`nMap` Clean-Room Rewrite)** *(Can run in parallel with `v0.3.0`)*
  9. `PR #9 (feat/core-mapper)`: Implement quaternion Kabsch alignment, ordered `keep`/`delete`/`alignment` atom surgery, charge/spin-aware R-group/ligand enumeration, and constrained-core pre-relaxation. *(Done when unit tests verify exact atom ordering and <0.1 Angstrom core RMSD on Rh(I) (5+2) reference complexes.)*

* **`v0.5.0` — Transition State P-RFO Optimizer & Active-Core Frequency Validator (Human Fixture Tier 3)**
  10. `PR #10 (feat/ts-optimizer)`: Implement clean-room TRIC P-RFO saddle-point optimizer (seeded with MLIP/xTB Hessian + soft-mode Hessian-refresh / damped fallback recovery), active-core imaginary mode projection filter (1 negative frequency, >=60% active-atom kinetic energy contribution), and covalent-graph topology guard. *(Done when unit tests converge model analytic/MLIP saddle points.)*
  11. `PR #11 (test/e2e-gs-ts-fixture)`: Run E2E validation against **Human Fixture 3** (GS + TS reaction map -> activation barrier with mapped substituent). *(Done when E2E test passes.)*

* **`v0.6.0` — Selectivity Branching & Competing TS Screening (Human Fixture Tier 4)**
  12. `PR #12 (feat/selectivity-scorer)`: Implement multi-pathway TS comparison, Boltzmann-weighted selectivity barriers, `% ee` / regioselectivity calculation, and priority-gate pruning rules. *(Done when unit tests verify selectivity math and branch pruning.)*
  13. `PR #13 (test/e2e-ddg-fixture)`: Run E2E validation against **Human Fixture 4** (competing TS1 vs. TS2 reaction map -> differential barrier and `% ee`). *(Done when E2E test passes.)*

* **`v0.8.0` — Full Catalytic Cycle Orchestrator & Energetic Span Model (Human Fixture Tier 5)**
  14. `PR #14 (feat/graph-orchestrator)`: Implement priority-ordered DAG scheduler, stage-decomposed crash recovery & incremental stage execution, multi-stage refinement (`MLIP/xTB` -> `DFT`), and Energetic Span Model (TOF / TDI / TDTS) + sum-over-states analyzer. *(Done when integration tests verify skip-gating, mid-run crash resume, and post-hoc solvation addition.)*
  15. `PR #15 (test/e2e-catalytic-cycle)`: Run E2E validation against **Human Fixture 5** (full multi-step catalytic cycle with priority-gated pruning and TOF output). *(Done when E2E test passes.)*

* **`v1.0.0` — Production CLI, Multi-Template Enumeration & Documentation Release**
  16. `PR #16 (feat/cli-release)`: Finalize CLI entrypoints (`eta-rxncat run`, `eta-rxncat validate`, `eta-rxncat hardware-check`, `eta-rxncat cache-status`), multi-template node fallback selection, comprehensive API docs, and `v1.0.0` release tag. *(Done when full unit + integration + E2E test matrix passes on clean install.)*

* **`v1.1.0+` — Post-V1.0 Interactive GUI & Visual Analytics**
  17. Interactive 3D structure/reaction-graph builder (graphical selection of `keep`, `delete`, and `alignment` atoms exporting directly to `ReactionGraph` YAML/JSON) and interactive web/notebook visualizer for completed reaction networks, conformer Boltzmann distributions, and imaginary mode animations.

## Known Constraints & Open Questions
* **License Constraint:** Strictly MIT / BSD / Apache-2.0 for all in-process dependencies (`no ase`, `no sella`, `no in-process tblite/psi4`).
* **Hardware Constraint:** NVIDIA RTX 5060 (8 GB VRAM, Blackwell `sm_120`); PyTorch `>=2.7.0+cu128` and `GPU4PySCF >=1.8.0` required; auto-fallback to CPU `PySCF` above ~6.5 GB VRAM budget.
* **Sub-Point Release Policy:** Use `v0.x.y` tags (`v0.2.1`, `v0.5.1`, etc.) whenever hardware quirks, convergence edge cases, or schema refinements require intermediate patches before advancing to the next minor milestone.

## The Graveyard
* *None yet.*

## Custom Commands
* *None registered yet.*

## Change Log
* **2026-11-21:** Initialized Living Master Plan with scope, license firewall architecture, induced-fit conserved-core TS mapping hypothesis, and V1 roadmap.
* **2026-11-21:** Set project name to **Eta-RxnCat**, locked V1 DFT engine to **PySCF / GPU4PySCF** (with RTX 5060 8 GB VRAM guardrails), committed to clean-room best-practices rewrite with README homage to `nMap` / `Eta_Scripts`, and added **priority-gated Reaction Graph** architecture with ordered `keep`/`delete`/`align` atom mapping.
* **2026-11-21:** Verified RTX 5060 (`sm_120`) compatibility with PyTorch `2.7+cu128`, `GPU4PySCF 1.8.0+`, and `FAIRChem UMA-S-1.2.1` (`omol`); locked YAML/JSON graph format and `ddCOSMO`/`PCM`/`ALPB` solvation for `v1.0.0`; established semantic version roadmap (`v0.1.0` -> `v1.0.0` -> `v1.1.0+`), parallel PR workflow, and 5-tier human-authored E2E reaction-map test fixtures.
* **2026-11-21:** Added quasi-RRHO + 1 M standard-state thermochemistry defaults, explicit charge/spin propagation across R-group/ligand substitutions, solver failure recovery hooks, and content-addressed SQLite/Parquet artifact caching.
* **2026-11-21:** Confirmed Grimme `qRRHO` thermochemistry, per-step mandatory `(charge, multiplicity)`, multi-stage SCF basis-projection & soft-mode optimizer escalation ladders, and stage-decomposed content-addressed caching.
* **2026-11-21:** Packaged `v0.1.0` repository starter archive (`Eta-RxnCat-v0.1.0.zip`) for Claude Code handoff.
