# Eta-RxnCat Engineering & Agent Collaboration Guidelines

This repository follows strict scientific software engineering standards and trunk-based Pull Request workflows.

## 1. Branching & Pull Request Protocol
* **Never commit directly to `main`.** All changes must enter via focused Pull Requests from `feat/<topic>`, `fix/<topic>`, or `test/<topic>` branches.
* **Parallel Development Boundaries:** Keep PRs scoped to a single subpackage (`core/`, `store/`, `engines/`, `conformers/`, `mapping/`, `optimize/`, `orchestrator/`) so multiple agents or developers can work in parallel without merge conflicts.
* **Living Master Plan Sync:** Whenever a milestone, architectural decision, or sub-point version (`v0.x.y`) changes, update `Eta-RxnCat_Living_Master_Plan.md` in the same PR and append a dated entry to `Change Log`.

## 2. Clean-Room & Permissive License Guardrails
* **Zero Copyleft Imports:** Do NOT import `ase`, `sella`, `tblite`, or `psi4` anywhere inside `src/eta_rxncat/`. All in-process dependencies must be MIT, BSD, Apache-2.0, ISC, or PSF licensed.
* **Subprocess Isolation:** External binaries with LGPL or proprietary licenses (`xtb`, `crest`, `orca`) must be invoked strictly via `subprocess` using serialized `.xyz` / JSON I/O.
* **Clean-Room Algorithms:** Implement quaternion/Kabsch alignment, internal-coordinate P-RFO saddle-point optimization, Grimme quasi-RRHO thermochemistry, and Energetic Span Model equations directly from published mathematical formulations.

## 3. Scientific & Numerical Standards
* **Mandatory Charge & Spin Multiplicity:** Every `MolecularState` and reaction step must explicitly declare integer `charge` and `spin_multiplicity` ($2S + 1$).
* **Hardware Guardrails (NVIDIA RTX 5060, 8 GB VRAM):** GPU-accelerated DFT (`GPU4PySCF`) must check estimated VRAM footprint against `6.5 GB` active budget and automatically fall back to density-fitted CPU `PySCF` when exceeded.
* **Stage-Decomposed Caching:** Never bundle conformer search, geometry optimization, frequency calculation, and solvation single-point energy into a single opaque cache key. Hash each stage independently so crashed workflows resume cleanly and post-hoc solvation stages reuse completed gas-phase geometries and Hessians.

## 4. Required Checks Before Opening a PR
1. `ruff check src tests`
2. `mypy src`
3. `pytest tests/unit`
4. `pip-licenses --fail-on="GPL;LGPL;AGPL"`
