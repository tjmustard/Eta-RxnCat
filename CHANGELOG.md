# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
