# Eta-RxnCat

Eta-RxnCat is a permissively licensed (MIT) computational-chemistry library and workflow engine
for homogeneous organometallic and organocatalytic reaction mechanisms. It is planned to combine
classical force fields, subprocess-isolated tight-binding, machine-learned interatomic potentials
and density functional theory (PySCF / GPU4PySCF) under a priority-gated reaction-graph
orchestrator. `v0.1.0` provides the package scaffold, the core schemas, the artifact store and
the hardware probe.

## Scientific heritage

Eta-RxnCat is a clean-room rewrite inspired by:

- **The conserved-core transition-state model and `nMap`.** Mustard, T. J. L.; Wender, P. A.;
  Cheong, P. H.-Y. *ACS Catal.* **2015**, *5*, 1758–1763. DOI:
  [`10.1021/cs501828e`](https://doi.org/10.1021/cs501828e). The geometry of the bond-forming and
  bond-breaking atoms in catalytic transition states stays nearly invariant across diverse
  catalysts, so new catalysts and substrates can be mapped onto conserved cores.
- **`Eta_Scripts`**, which with `nMap` pioneered Kabsch/quaternion subgraph alignment and ordered
  atom surgery (`keep`, `delete` and `alignment` atom lists).

## Licensing

Eta-RxnCat is released under the MIT licence (see `LICENSE`).

- Every runtime dependency must report a licence on the allow-list
  `MIT;BSD;Apache;ISC;PSF;Python Software Foundation`. CI enforces this with `pip-licenses` over
  a runtime-only environment; a package reporting anything else (including `UNKNOWN`) fails.
- `ase`, `sella`, in-process `tblite` and `psi4` are never imported by `eta_rxncat`.
- External copyleft or proprietary programs (such as `xtb`) are only ever run as subprocesses
  with serialised file I/O.

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync          # create .venv from the committed uv.lock
uv run pytest    # run the test suite
```

The other required checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Roadmap

The roadmap from `v0.1.0` to `v1.0.0` is in `PRDs/Eta-RxnCat_Living_Master_Plan.md`.
