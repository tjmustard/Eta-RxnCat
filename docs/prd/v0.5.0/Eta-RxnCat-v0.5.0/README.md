# Eta-RxnCat

**Eta-RxnCat** is a clean-room, permissively licensed (MIT) computational chemistry library and adaptive workflow engine for **homogeneous organometallic and organocatalytic reaction mechanisms**.

It combines classical force fields (RDKit UFF/MMFF94), isolated semi-empirical tight-binding (`GFN2-xTB` / `g-xTB` via subprocess), reactive machine-learned interatomic potentials (`MACE` and Meta's `UMA`), and density functional theory (`PySCF` / `GPU4PySCF`) inside a **priority-gated Reaction Graph** orchestrator.

## Scientific Heritage & Homage

Eta-RxnCat is a modern, clean-room architectural rewrite inspired by two foundational bodies of work:

1. **The Induced-Fit / Conserved-Core Transition State Model & `nMap` (~2014–2015):**
   Demonstrated in Mustard, Wender, & Cheong (*ACS Catal.* 2015, *5*, 1758–1763; DOI: `10.1021/cs501828e`), the geometry of bond-forming and bond-breaking atoms in catalytic transition states remains remarkably invariant ($< 0.1\text{ \AA}$ RMSD) across structurally and electronically diverse catalysts. `nMap` and `Eta_Scripts` pioneered quaternion/Kabsch subgraph alignment and ordered atom surgery (`keep`, `delete`, and `alignment` atom lists) to map new catalysts and substrates onto conserved ground-state and transition-state cores.
2. **Automated Reaction Network Profiling (`AutoRW` / `RxnEnumProfiler`):**
   Building on lessons from automated multi-level reaction network enumeration, Eta-RxnCat introduces a **priority-gated DAG scheduler** and **stage-decomposed content-addressed caching** so high-importance steps (such as selectivity-determining transition states) execute first and prune unpromising candidates before full catalytic cycles are computed.

## Licensing Philosophy

Every in-process dependency in `Eta-RxnCat` is strictly permissive (**MIT**, **BSD-3-Clause**, or **Apache-2.0**). Copyleft libraries (such as `ASE`, `Sella`, `tblite`, or `Psi4`) are intentionally excluded from in-process imports; external LGPL command-line binaries like `xtb` are isolated behind subprocess JSON/XYZ worker boundaries.

## Quickstart (`v0.1.0`)

```bash
# Create virtual environment with uv
uv venv --python 3.11
source .venv/bin/activate

# Install core package + dev tooling
uv pip install -e ".[dev]"

# Verify RTX 5060 / CUDA / GPU4PySCF hardware capabilities
python -m eta_rxncat.utils.hw_probe

# Run unit tests and permissive license audit
pytest tests/unit
pip-licenses --fail-on="GPL;LGPL;AGPL"
```

## Project Roadmap

See `Eta-RxnCat_Living_Master_Plan.md` for the full semantic versioning roadmap from `v0.1.0` through `v1.0.0` and beyond.
