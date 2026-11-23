# v0.3.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.3.0.zip` (sha256
`eaa9638d7d77ad0dc8c51fb4ef749b7a1d08b28dd106ca5ae7312ab6a1ddb401`) ships a starter implementation,
unpacked here under `docs/prd/v0.3.0/Eta-RxnCat-v0.3.0/` (30 files, byte-identical to the zip, plus the
gate file `.ruff.toml`, which is not part of the starter). It is reference only: the code in `src/`
and `tests/` is written fresh from the mission's slice specs. This register records every difference
between the starter (and TJ's 5-tier bundle, for DV-19/DV-20) and the rewrite, so each one can be
reviewed and fixed if needed.

TJ, Q2: "B use it as reference only. Keep a list of the discrepancies so that if needed, we can go
through each of them and fix any issues that arise."

## Scope

The minimum rows of mission `missions/release-0.3.0/SPEC.md` §5 "Discrepancy register". Starter paths
are relative to `docs/prd/v0.3.0/Eta-RxnCat-v0.3.0/`; line numbers are the starter's as unpacked.
DV-19/DV-20 point into TJ's bundle builder,
`~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py`
(abbreviated `builder.py`). DV-23 points at this repository's own v0.2.0 contract.

**Status.** `open (slice NN)` means the named v0.3.0 slice implements the decision; the auditor of that
slice closes the row. `decided` means no code change is owed.
`closed (slice NN; audit <row>)` means the audit of that slice passed with the row met; the audit
listed it in its PASS handoff and the scribe closed it at v0.3.0 docs time (the audit seat does not
edit project docs).

## Register

| ID | Starter file:line | Starter behaviour | v0.3.0 decision | Source | Status |
|---|---|---|---|---|---|
| DV-01 | `src/eta_rxncat/core/thermo.py:6` | Thermochemistry math (numpy) lives in `eta_rxncat.core`. | Math moves to the new `eta_rxncat.thermo` package; `eta_rxncat.core` keeps only the data contracts and stays free of numpy/RDKit/geomeTRIC. | Mission §5 "Contracts"; R1 | closed (slices 02, 03; audit `qitem-20261123041808-195d68c6`) |
| DV-02 | `src/eta_rxncat/core/thermo.py:121-131` | Rotational partition function has no rotational symmetry number σ. | σ derived from the geometry and capped graph automorphisms (proper rotations only), exact in regression. | R8, R9 | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-03 | `src/eta_rxncat/core/thermo.py:115` | Grimme damping moment B_av = mean of the principal moments. | B_av = `qrrho_rotor_moment_kg_m2`, default 1e-44 kg·m² (Grimme 2012). | Mission §5 "Algorithms"; R15 | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-04 | `src/eta_rxncat/core/thermo.py:160` | E_trans + E_rot = 3 RT for every polyatomic, linear included. | Linear molecules: E_trans + E_rot = 5/2 RT; nonlinear 3 RT; N = 1 → 3/2 RT. | R15, R34 | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-05 | `src/eta_rxncat/core/thermo.py:23-29`, `:38`, `:106` | 21-element mass table; any other element silently gets 12.0 amu. | Masses from RDKit for Z 1–118 (most abundant isotope); a missing mass raises, never defaults. | Mission §5 "Algorithms"; R16 | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-06 | `src/eta_rxncat/core/thermo.py:75-78` | Drops the `rank` eigenvalues nearest zero after projection (can drop a real soft mode). | Diagonalise the Hessian in the complement of the Eckart translation/rotation space; nothing is dropped by magnitude. | Mission §5 "Algorithms" | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-07 | `src/eta_rxncat/core/thermo.py:102-103` | Modes in (−10, 10) cm⁻¹ silently dropped from ZPE and entropy. | Every mode kept; soft modes use \|ν̃\| and are listed in `ThermoResult.soft_modes_cm1`; \|ν̃\| < 1e-3 cm⁻¹ → `ThermoInputError`. | R15, R36 | closed (slices 02, 03; audit `qitem-20261123041808-195d68c6`) |
| DV-08 | `src/eta_rxncat/core/models.py:80`; `src/eta_rxncat/core/thermo.py:156-157` | `head_gordon` mode offered but silently computed as plain RRHO. | Not offered: the entropy model is `Literal["grimme_qrrho"]`. | Mission §6 | closed (slices 02, 03; audit `qitem-20261123041808-195d68c6`) |
| DV-09 | `src/eta_rxncat/core/models.py:198`; `src/eta_rxncat/core/thermo.py:174-191` | `is_valid_stationary_point` flag; result still returned for a non-minimum. | Ground-state check raises `NotAMinimumError`; the species runner does one imaginary-mode push (R15, R18). | R15, R18 | closed (slices 03, 06; audit `qitem-20261123041808-195d68c6`, `qitem-20261123064423-65aa7510`) |
| DV-10 | `src/eta_rxncat/conformers/ensemble.py:16-33` | XYZ input with bond perception; returns the input state on any failure. | SMILES input (optional stereo-checked seeds); typed `ConformerInputError`. | R24, R28 | closed (slice 05; audit `qitem-20261123062150-a049e9d2`) |
| DV-11 | `src/eta_rxncat/conformers/ensemble.py:37-52` | RDKit `pruneRmsThresh` + `GetBestRMS` pruning (merges mirror images), no energy window. | Own dedup over automorphisms with proper rotations; per-conformer mirror degeneracy g; energy window. | R3 | closed (slice 05; audit `qitem-20261123062150-a049e9d2`) |
| DV-12 | `src/eta_rxncat/conformers/ensemble.py:85`; `src/eta_rxncat/core/thermo.py:146` | Boltzmann and vibrational exponents clipped at 500. | Log-sum-exp with degeneracies; no clipping. | Mission §5 "Algorithms" | closed (slice 03; audit `qitem-20261123041808-195d68c6`) |
| DV-13 | `src/eta_rxncat/optimize/gs_optimizer.py:6-8`, `:51` | geomeTRIC imported at module level; `run_optimizer` writes `eta_opt.xyz` etc. in the cwd and reconfigures logging. | Lazy import behind the `opt-geometric` extra; lower-level API (`OptParams`, `Molecule`, `CoordSysDict`, `Optimizer`); temp-dir and logger sandbox. | R2, R5 | closed (slice 04; audit `qitem-20261123055639-d7637a1a`) |
| DV-14 | `src/eta_rxncat/optimize/gs_optimizer.py:41-59` | Bare `except Exception`: TRIC → Cartesian, failure reasons lost. | Recorded three-step typed ladder. | Mission §5 "Algorithms" | closed (slice 04; audit `qitem-20261123055639-d7637a1a`) |
| DV-15 | `src/eta_rxncat/engines/base.py:18-29`, `:33-54`; `src/eta_rxncat/optimize/gs_optimizer.py:25-30` | Starter `PotentialEngine.evaluate(state, compute_forces=…, compute_hessian=…)` API. | v0.2.0 `Engine.evaluate` / `PotentialResult` (already on `main`). | Mission §5 "Contracts" | closed (slices 04, 06; audit `qitem-20261123055639-d7637a1a`, `qitem-20261123064423-65aa7510`) |
| DV-16 | `tests/unit/test_v030_thermo_conformers.py:40` | Hard-coded fake energies `[-158.4500, -158.4485]` drive the Boltzmann test. | Tier-D (analytic) tests and real engine runs. | Mission §5 "Test tiers and tolerances" | closed (slices 03–08; audit `qitem-20261123092430-aefe9820`) |
| DV-17 | `src/eta_rxncat/core/models.py:88-116` | Starter `MolecularState` (mutable, unchecked names, `metadata`, numpy in core). | The v0.1.0 `MolecularState` contract already on `main`, unchanged. | Mission §5 "Contracts" | closed (slice 02; audit `qitem-20261123040452-da899eda`) |
| DV-18 | `Eta-RxnCat_Living_Master_Plan.md:40` (PR #8) | The zip's plan copy adds "plus incremental solvation stage test" and the done criteria (PD-007). | TJ Q4 "C": plan scope plus the zip's done criteria; the incremental-solvation test runs on the species runner. | TJ Q4 `qitem-20261123010134-cd43c1fb3e761e27`; PD-007 | closed (slices 06, 07; audit `qitem-20261123064423-65aa7510`, `qitem-20261123080306-05682a70`) |
| DV-19 | `builder.py:323-352`, `:353-396`, `:397-444` (`tier1_*`, `tier2_*` YAMLs) | Tier YAMLs use a graph `nodes:` schema, `engine: "rdkit_ff"` conformer ranking and RMSD 0.35 / 0.25 Å. | Provisional v0.3.0 fixture format under `tests/e2e/data/`, the mission's recipes and dedup thresholds. | TJ Q-E3 "B" | closed (slices 07, 08; audit `qitem-20261123080306-05682a70`, `qitem-20261123092430-aefe9820`) |
| DV-20 | `builder.py:704` | Asserts per-node `hits_by_stage["gs_opt_freq"] == 3`. | Per-species `species_stage_cache` (a species hits only when every kept conformer's row was served). | R27 | closed (slice 08; audit `qitem-20261123092430-aefe9820`) |
| DV-21 | `src/eta_rxncat/core/thermo.py:23-29` (masses by symbol) | No isotope handling; any label would be ignored. | A SMILES with any isotope label → `ConformerInputError`. | R16 | closed (slice 05; audit `qitem-20261123062150-a049e9d2`) |
| DV-22 | `src/eta_rxncat/conformers/ensemble.py:35-38` | One ETKDGv3 pass, which never samples the s-cis-side diene class. | Second pass with `useExpTorsionAnglePrefs=False` (`torsion_free_pass`, default `true`). | R21, R25 | closed (slice 05; audit `qitem-20261123062150-a049e9d2`) |
| DV-23 | `src/eta_rxncat/core/results.py:22` (this repo, v0.2.0) | `PotentialResult` is frozen only shallowly (its lists are mutable). | Carried forward unchanged; consumers copy matrices; docstring note (slice 02), unchanged-Hessian test (slice 03). | Mission §5 "Discrepancy register" | closed (slices 02, 03; audit `qitem-20261123041808-195d68c6`) |
