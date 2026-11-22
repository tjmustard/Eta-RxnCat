Decision (TJ, 08:19Z, verbatim "Q1 A, Q2 A", row qitem-20261122075815-4c32a48f2e42363c; Red Team F1, F2; resolve R1, R2, R30). Optional extras are `gpu`, `mlip-mace` and `mlip-uma`. The two MLIP extras are mutually exclusive, declared under `[tool.uv] conflicts` so that `uv lock` resolves both, and an environment uses one MLIP at a time (mace-torch pins e3nn==0.4.4 while fairchem-core needs e3nn>=0.5). The licence gate runs per extra:
- The base install has no exemptions.
- NVIDIA CUDA runtime wheels are exempt.
- LGPL packages (ase, matscipy) are allowed only as transitive dependencies of the MLIP extras: never declared directly, never vendored, never imported by eta_rxncat (enforced by an AST test).
Revisit if a later version needs MACE and UMA in one process.
