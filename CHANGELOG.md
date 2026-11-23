# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-11-23

### Added
- **Core contracts** (`eta_rxncat.core`): `ThermoAnalysisOptions`, `ThermoResult`,
  `OptimizerIdentity`, `OptimizationResult`, `ConformerRecord` and `ConformerEnsemble`. They are
  frozen, strict and data-only. `eta_rxncat.core` still imports no numpy, RDKit or geomeTRIC.
- **Thermochemistry** (`eta_rxncat.thermo`): ideal-gas quasi-RRHO (Grimme 2012, ω₀ 100 cm⁻¹) at a
  1 M standard state from a Cartesian Hessian. It uses CODATA 2018 constants and Eckart-projected
  normal modes, in which every mode is kept and soft modes are listed. The rotational symmetry
  number comes from the geometry and capped graph automorphisms, and masses come from RDKit for
  Z 1–118. Boltzmann weights use log-sum-exp with degeneracies, without clipping.
  `check_ground_state` raises `NotAMinimumError` on an imaginary mode.
- **Optimizer interface** (`eta_rxncat.optimize`): `Optimizer`, `DihedralConstraint` and typed
  errors. `GeometricOptimizer` drives geomeTRIC 1.1.1's lower-level API, never `run_optimizer`.
  Each run uses a temporary directory and a sandboxed `geometric` logger. It records a recovery
  ladder: `tric`, then `tric_tight_trust`, then `cartesian`, or `hdlc` for a constrained run.
- **Conformers** (`eta_rxncat.conformers`): two-pass ETKDGv3 pools from a SMILES. The second pass
  runs without experimental torsion preferences, so the s-cis-side diene class is sampled.
  Stereo-checked seed geometries are accepted, and isotope labels are refused. Dedup is by
  proper-rotation RMSD over graph automorphisms, followed by an energy window, a per-conformer
  mirror degeneracy g and the ensemble build.
- **Single-species stage runner** (`eta_rxncat.orchestrator`): `run_species` caches each stage
  in the v0.1.0 artifact store: conformer search, optimisation, frequency and incremental single
  points. It counts engine calls and records per-stage metrics. It pushes along an imaginary mode
  at most once, then re-dedups the pushed conformer against the kept set.
  `run_constrained_point` gives a cached constrained optimisation. `reaction_free_energy` gives
  ΔE, ΔH, ΔG(1 atm) and ΔG(1 M), and the JSON report writer is deterministic.
- **End-to-end fixtures** (`tests/e2e/`, `e2e` marker): Human Fixture 1 (n-butane anti/gauche),
  Human Fixture 2 (butadiene + ethylene → cyclohexene, with incremental ALPB toluene and PCM
  single points), TJ's Tier 1 (2,3-dimethoxybutadiene) and Tier 2 (cyclopentadiene + cyclopropene
  → endo P1a_n, with incremental ALPB dioxane). Each runs on the xtb (GFN2) and UMA recipes. TJ's
  ωB97M-V/def2-TZVPD//B3LYP/6-31G** reference values are under
  `tests/e2e/data/reference/tj-reference-b3lyp-20261123/`. The fixtures TJ promoted are in
  `tests/fixtures/v0.3.0/`.
- **v0.3.0 acceptance** (`docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run
  2026-11-23 at `0a48204`). It ran on an NVIDIA GeForce RTX 5060 Ti, with UMA `uma-s-1p2p1`
  (fairchem 2.26.0) on CUDA and xtb 6.8.0 on the CPU. The xtb recipe passed 6 tests and the UMA
  recipe 5, with 0 skipped. Every fixture passed on both recipes and matched its promoted
  fixture, and TJ confirmed the derived SMILES. The UMA results compared with TJ's ωB97M-V
  reference, with these gated deltas:
  - n-butane gauche–anti ΔG: +0.009 kcal/mol (bound 0.5).
  - Diels–Alder ΔG_r: +0.056 kcal/mol (bound 2.0).
  - Tier 2 ΔG_r(1 M): −32.01 kcal/mol, inside TJ's −42 to −20 window.
  - Tier 1: all three gates pass on both recipes (both conformer classes kept, s-trans below
    s-cis-side, planar point within 0.1°).
- **Records**: proposed ADR-0023 to ADR-0027 (awaiting approval), and the v0.3.0 starter
  discrepancy register `docs/prd/v0.3.0/DISCREPANCIES.md` (23 rows, all closed at release).

### Changed
- **geomeTRIC is no longer a core dependency** (TJ Q3 A). It moved to the `opt-geometric` extra
  (`geometric==1.1.1`) and the dev group. The base licence profile has no exemption now. The
  BSD 3-clause Non-AI exemption moved to the new `opt-geometric` profile, which CI also gates. It
  stays in `gpu`, `mlip-mace` and `mlip-uma`, because `gpu4pyscf-cuda12x` pulls geomeTRIC in.
- **Test markers**: `e2e` is registered and deselected by default.
- **README**: v0.3.0 features. The v0.3.0 acceptance claims are derived from the record, and
  tests enforce them. The Acknowledgements section links the original
  [`Eta_Scripts`](https://github.com/tjmustard/Eta_Scripts) code and the author's Oregon State
  University dissertation (2015), where that code is also published.

### Known issues
- **GFN2 is reported, not gated, and it overbinds.** Its deltas against TJ's ωB97M-V reference
  are Diels–Alder ΔG_r −19.75 kcal/mol and n-butane gauche–anti ΔG −0.03 kcal/mol. Its Tier 2
  ΔG_r(1 M) is −52.36 kcal/mol, outside TJ's window. TJ's rule (Q-E5 "C"): "if it turns out MACE,
  UMA, or OMol25 are needed then they should become standard". The default recipe stays GFN2
  until TJ decides.
- **Cached failures (R50).** A non-deterministic engine failure stays cached as a completed
  failure row until `invalidate`, and is not retried under the same key.
- **UMA cyclohexene boats at the dedup threshold.** On UMA, HF2 cyclohexene keeps a Cs boat and a
  twist-boat 0.126 Å apart (threshold 0.125 Å), 0.31 kcal/mol apart and about 4 kcal/mol above
  the half-chair (weight ≈ 1e-3).
- **The UMA `dropped` list is not bit-reproducible.** GPU noise in the G order can swap which
  reason a dropped conformer gets (`duplicate_after_push` or `mirror_partner`) between runs. The
  kept records and counts are unchanged, and the regression does not compare the `dropped` list.
- **Per-conformer accuracy.** The accuracy check compares per-conformer quantities. Our G is
  quasi-RRHO and the reference uses pure RRHO (≤ 0.01 kcal/mol on these Δ values). The ensemble
  ΔG_r differs by `dG_r_ensemble_minus_lowest`, which is reported.
- **ADR-0023 to ADR-0027 are PROPOSED.** ADR-0024's body still names `CoordSysDict`, which is not
  importable; mission R44 corrected this, and the code builds its own coordinate-system table.
- **Carried forward from 0.2.0, still true:**
  - `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process. The fix is
    planned for when engines first share a process.
  - DFT Hessians use finite differences on the CPU, and the GPU analytic KS Hessian is used only
    for the supported classes.
  - `stability.py` pins private PySCF 2.15.1 / GPU4PySCF 1.9.2 internals.
  - fairchem engines run at `high-precision` only.
  - The GPU stability follow for fewer than three rotations is tested only with fakes.
  - The VRAM estimate does not cover GPU Hessians.
  - `PotentialResult` is frozen only shallowly (DV-23).

## [0.2.0] - 2026-11-23

### Added
- **`PotentialResult`** (`eta_rxncat.core.results`): a frozen core contract with energy (Eh),
  forces (Eh/Bohr), an optional Hessian (Eh/Bohr², `analytic` or `finite_difference`), the
  engine's identity (tag, version, content-pinned model), the device and its reason, the recovery
  steps taken and the wall time.
- **Engine interface** (`eta_rxncat.engines`): one abstract `Engine`, built from a stage with
  `from_stage`. Every result-changing option is keyed and filled into the resolved stage, so
  implicit and explicit defaults give the same cache key. Runtime arguments and the device are
  never keyed. Includes CODATA 2018 units, a finite-difference Hessian helper (step in Bohr,
  symmetrised, asymmetry recorded) and typed errors (`EngineInputError`,
  `EngineUnavailableError`, `ScfConvergenceError`, `EngineRuntimeError`). An engine that cannot
  represent a state's charge and spin refuses it and never computes something else.
- **Six engines**:
  - `rdkit_ff`: RDKit UFF and MMFF94, neutral singlets only.
  - `pyscf_gpu_cpu`: PySCF on the CPU and GPU4PySCF on CUDA from one resolved stage. It covers
    RKS/UKS/RHF/UHF, density fitting (keyed, on by default), the def2 ECP rule (`ecp="auto"`),
    ddCOSMO, C-PCM and IEF-PCM solvation (no ddCOSMO on GPU), an SCF escalation ladder and an
    internal stability analysis. On CUDA, a stage over the calibrated VRAM estimate or one that
    hits a listed out-of-memory error falls back to the CPU, with the reason recorded.
  - `xtb_subprocess`: GFN2-xTB 6.8.0 as a separate process with keyed ALPB solvation. The
    Hessian is a finite difference of xtb's gradients, because xtb's own `--hess` output is
    projected.
  - `mace`: MACE-MP-0 medium in float64, neutral singlets only, with the model file checked
    against its SHA-256 pin. `eta_rxncat` never imports `ase`.
  - `uma_direct` (`uma-s-1p2p1`) and `esen_omol25` (`esen-sm-conserving-all-omol`, TJ: "A - Ship
    it as a second model"): fairchem models on one clean-room bridge, with charge and spin passed
    through. Only the conserving OMol25 checkpoint is accepted.
- **Licence inventory** (`docs/licence-inventory.md`): external programs and weights used but
  never shipped, with licence, digest and decision. These are the xtb binary (LGPL-3.0 with
  bundled MKL/ifx, run as a subprocess; TJ F12 A), the MACE-MP-0 weights (MIT) and the UMA and
  OMol25 weights (FAIR Chemistry License v1, gated).
- **Engine test policy**: `xtb`, `mlip_mace`, `mlip_uma`, `slow` and `acceptance` markers (beside `gpu`), deselected by default, named
  acceptance environments, and `ETA_RXNCAT_ACCEPTANCE=1`, which turns every skip into a
  failure. Unit tests run offline.
- **v0.2.0 acceptance** (`docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`, run at `a879590`): passed on
  an NVIDIA GeForce RTX 5060 Ti (compute capability 12.0) with PyTorch 2.13.0+cu129 and
  GPU4PySCF 1.9.2. The smoke test matched GPU and CPU to |ΔE| 1.0e-12 Eh. All six engines ran
  their acceptance cases, with the expected refusals for states an engine cannot represent. GPU
  suite: 20 passed. Plain suite: 743 passed, with the one by-design skip.
- **Records**: proposed ADR-0016 to ADR-0022 (awaiting approval), the v0.2.0 starter discrepancy
  register `docs/prd/v0.2.0/DISCREPANCIES.md`, and the calibration and support evidence under
  `docs/prd/v0.2.0/`.

### Changed
- **GPU and MLIP stack**: PyTorch 2.13.0 from the CUDA 12.9 index (`cu129`, was `cu128`) and
  `fairchem-core>=2.22`, so UMA `uma-s-1p2p1` runs natively (TJ F1 A).
- **Licence gate**: `BSL-1.0` is on the allow-list (it is in torch 2.13.0's licence expression).
  A dist-info without `Name`, or two
  dist-infos for one name, now fails instead of being skipped or resolved first-wins.
- **README**: the version badge, the Features heading and the GPU claim are derived from
  `pyproject.toml` and the acceptance record, and tests enforce them. The Roadmap is split into
  Built and Planned.

### Known issues
- **Security: `import mace` disables safe `torch.load`.** The upstream `mace` package sets
  `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process, so any later `torch.load` in that
  process unpickles arbitrary objects. v0.2.0 is not exposed, because the `mlip-mace` and
  `mlip-uma` extras cannot share an environment. A fix is planned for when engines first share a
  process.
- **DFT Hessians.** On the CPU they are finite differences of analytic gradients. PySCF 2.15.1's
  analytic KS Hessian is wrong at the default grid, and CPU grid response is not implemented. On
  the GPU, GPU4PySCF's analytic KS Hessian is used only for the classes the committed support
  record covers (`docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`). UKS with IEF-PCM is about
  2e-4 Eh/Bohr² off and goes to finite differences.
- **SCF stability rule.** An instability counts only if λ_min < −1e-3 (keyed `stability_tol`),
  and a follow that lowers the energy by less than 1e-6 Eh (keyed `stability_noise_eh`) ends as
  stable. Shallower instabilities are no longer followed. The rule changed because threaded-CPU
  noise made PySCF's own −1e-5 verdict flaky.
- **fairchem precision.** `uma_direct` and `esen_omol25` run at `high-precision` only (keyed).
  A faster mode may be added later.
- **Private PySCF internals.** `engines/pyscf_gpu_cpu/stability.py` replays private PySCF
  2.15.1 and GPU4PySCF 1.9.2 code. A lock bump needs a re-pin, and a tripwire test fails until
  it is done.
- **From the acceptance record's `known_limits`:**
  - The GPU stability follow branch for fewer than three orbital rotations is tested only with
    fakes.
  - The VRAM estimate covers SCF and gradients only. A GPU Hessian over budget relies on the
    out-of-memory CPU fallback.
  - The plain suite in the GPU environment has one by-design skip
    (`tests/unit/cli/test_cli.py::test_console_script_smoke_skipped`).

## [0.1.0] - 2026-11-22

### Added
- **Scaffold and gates.** A `uv`-managed MIT package (`eta-rxncat`, src layout, committed
  `uv.lock`, Python 3.11–3.13) with strict `ruff`, `mypy` and `pytest` gates, CI, and the
  `v0.1.0` reference starter kept read-only under `docs/prd/v0.1.0/` with discrepancy registers.
- **Licence gates.** `tools/licence_gate.py` judges every package in a runtime environment from
  its exact licence metadata (SPDX expression, classifiers or licence field, no substring
  matching). There is one profile per install (`base`, `gpu`, `mlip-mace`, `mlip-uma`), each with
  version-pinned exemptions.
- **Core models and graph loader.** Strict Pydantic v2 contracts (`MolecularState`,
  `StageConfig`, `AtomMappingSpec`, `ThermoConfig`, `ReactionGraph` and the rest) and a YAML/JSON
  loader that rejects duplicate keys and reports every failure as one `GraphValidationError`.
- **Cache key and artifact store.** A canonical, versioned per-stage cache key and a WAL-mode
  SQLite artifact store whose completed artifacts are never silently overwritten
  (`ArtifactConflictError`; `invalidate` is the only way to replace one). Opening a store runs
  the version check, the WAL switch and schema creation within one `open_timeout_s` deadline
  (default 5 s). A file locked past it raises `StoreBusyError`, and an unknown schema version
  raises `StoreSchemaError` and leaves the file untouched.
- **Hardware probe and smoke.** `probe_hardware()` reports PyTorch/CUDA, the GPU, GPU4PySCF and a
  6.5 GiB VRAM budget, and flags broken installs. `run_smoke()` compares GPU4PySCF with PySCF, and
  a CUDA matmul with the CPU result, against numeric tolerances.
- **CLI.** `eta-rxncat validate <path>` and `eta-rxncat hardware-check [--smoke]`, with a fixed
  exit-code table and one-line errors.
- **Optional extras.** `gpu` (PyTorch from the CUDA 12.8 index, GPU4PySCF, CuPy), and
  `mlip-mace` and `mlip-uma`, which are mutually exclusive and declared as conflicting.
- **Copyleft boundary.** The core install and `src/eta_rxncat/` stay MIT/BSD or equivalent.
  Copyleft and off-list licences are allowed only as unmodified, downloaded, transitive
  dependencies of the optional engine extras (for example `ase` under `mlip-mace`), each pinned
  per profile. `tests/unit/test_package.py` fails if the package imports `ase` or any
  copyleft-exempted module, or depends on one directly.
- **GPU acceptance.** The smoke test passed on an NVIDIA GeForce RTX 5060 Ti (compute
  capability 12.0, PyTorch 2.8.0+cu128, GPU4PySCF 1.9.2) at commit `ff3991e`. The GPU SCF
  energy was −74.96302313846023 Eh against −74.96302313846122 Eh on the CPU (|ΔE| 9.95e-13 Eh,
  tolerance 1e-6), with the molecular orbitals on the device. The record is
  `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`.
- **README GPU claim tied to the record.** `tests/unit/test_identity.py` reads
  `docs/prd/v<version>/GPU_SMOKE_RESULT.json`. The README may say "GPU acceptance passed" only
  when the record's smoke status is `pass`, and then it must link the record and name its GPU.
- **README, CHANGELOG and media.** A README with logo, banner and badges. The media are a
  size-named WebP set under `media/` (`icon-<N>.webp`, `banner-<W>x<H>.webp`), and each document
  embeds the next size up from its displayed width. `tests/unit/test_media.py` checks the names
  against the pixel sizes and the embeds.
- **Author guard.** `tests/unit/test_identity.py` requires the author form
  "Thomas J. L. Mustard Ph.D." in `README.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml` and
  the project section of `AGENTS.md`, including forms split across line breaks.
- **Records.** Proposed ADR-0011 to ADR-0015 under `lore/ADRs/`, awaiting approval (licence-gate exceptions, exact SPDX
  evaluation, the copyleft rule and the store-open order), and the plan discrepancy registers
  `docs/prd/PLAN_DISCREPANCIES.md` and `docs/prd/v0.1.0/DISCREPANCIES.md`.

### Changed
- Author name standardised to Thomas J. L. Mustard Ph.D.
