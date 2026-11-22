# Licence inventory: external components

Components Eta-RxnCat uses but never ships. None is vendored, copied, committed or imported by
the core. Each is downloaded by the user and used only through its engine. Python wheels are
judged by `tools/licence_gate.py` and are not listed here.

| Component | Version | Licence | Bundled third-party parts | How Eta-RxnCat uses it | Provenance | Decision |
|---|---|---|---|---|---|---|
| xtb (`xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz`) | 6.8.0 (`4b8c987066c7e9bd0c2b727ce026fb9a581c273a`) | LGPL-3.0 | Intel MKL and the Intel Fortran (ifx) runtime, statically linked (proprietary, redistributable) | `xtb_subprocess` engine: a separate process, file I/O in a fresh temporary directory, no shell, never in-process | GitHub release asset, 22,686,860 B, `sha256:db090333361749ae0d9ccf0ce7c0035c0000f2ebad0847f6d77191d1954f4d68` (release API digest). The asset's companion `.sha256` file lists the same digest under the name `xtb-bleed-linux-x86_64-ifx-mkl.tar.xz`. Provisioned to `~/.local/share/eta-rxncat/xtb/6.8.0/`, binary `stage/bin/xtb`; found via the engine's `binary` argument, `ETA_RXNCAT_XTB`, or `PATH`. | TJ v0.2.0 Q2 "A" (16:24Z, `qitem-20261122162111-26e232a707f003e2`): accept the xtb binary as a user-downloaded subprocess engine; ADR-0021 (PROPOSED) |
| MACE-MP-0 medium weights | (slice 09) | MIT | — | `mace` engine, local model file, content-pinned identity | (filled by slice 09) | (slice 09) |
| UMA `uma-s-1p2p1` weights | (slice 10) | `license: other` (gated) | — | `uma_direct` engine, HF cache or local checkpoint, content-pinned identity | (filled by slice 10) | (slice 10) |

Provisioning is a seat command recorded in each slice's handoff, never a test step.
