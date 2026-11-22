# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  SQLite artifact store whose completed artifacts are never silently overwritten.
- **Hardware probe and smoke.** `probe_hardware()` reports PyTorch/CUDA, the GPU, GPU4PySCF and a
  6.5 GiB VRAM budget, and flags broken installs. `run_smoke()` compares GPU4PySCF with PySCF, and
  a CUDA matmul with the CPU result, against numeric tolerances.
- **CLI.** `eta-rxncat validate <path>` and `eta-rxncat hardware-check [--smoke]`, with a fixed
  exit-code table and one-line errors.
- **Optional extras.** `gpu` (PyTorch from the CUDA 12.8 index, GPU4PySCF, CuPy), and
  `mlip-mace` and `mlip-uma`, which are mutually exclusive and declared as conflicting.

### Changed
- Author name standardised to Thomas J. L. Mustard Ph.D.
