# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.2.0 Clean-Room Potentials (mission `missions/release-0.2.0`, OPR.0.2.0, 11 slices):
  built, audited and accepted on this host on 2026-11-23. Next: v0.3.0 (conformers, ground-state
  optimisation, Boltzmann ensembles), from `PRDs/Eta-RxnCat_Living_Master_Plan.md`.

## Session State
Updated 2026-11-23.
- Branch `feature/eta-rxncat-v0.2.0`, cut from `e6b1d31` on local `main` (which carries v0.1.0).
  Version 0.2.0. Not pushed, tagged or released.
- v0.1.0 (foundation) is described in the `CHANGELOG.md` [0.1.0] entry.
- v0.2.0 adds `PotentialResult` (`eta_rxncat.core.results`) and the engine interface
  (`eta_rxncat.engines`: `Engine`, `from_stage`, keyed options, typed errors, CODATA 2018 units,
  FD Hessian). It also adds six engines: `rdkit_ff`, `pyscf_gpu_cpu` (CPU and GPU), `xtb_subprocess`,
  `mace`, `uma_direct` and `esen_omol25`. `conformers/`, `mapping/`, `optimize/` and
  `orchestrator/` still hold only a docstring.
- Stack: torch 2.13.0+cu129, GPU4PySCF 1.9.2, PySCF 2.15.1, fairchem-core 2.26.0, mace-torch
  0.3.17, xtb 6.8.0 (an external binary).
- Acceptance: `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json` (run at `a879590`, all pass, with its
  `known_limits`). External files and their licences: `docs/licence-inventory.md`.
- Acceptance envs `.venv-accept-gpu`, `.venv-accept-mace` and `.venv-accept-uma` are gitignored
  (`AGENTS.md`, "Engine tests"). `.venv` is the base dev env.
- HACF hold (TJ, 2026-11-22): no HACF-install.sh, HACF-uninstall.sh or migrate apply until TJ's
  go after v0.2.0. Installed HACF is v0.6.0 (`e4da6ef`).

## Recent Decisions
- Licence policy (TJ, 2026-11-22 14:57Z, governs all versions): the core (`src/eta_rxncat/` and
  the core install) is MIT/BSD or equivalent only and never imports `ase`. Copyleft engines (DFT,
  MLIP, conformer search) are allowed only behind the engine interface, as optional extras or
  subprocesses, because they can be replaced. `ase` coming in through the MACE extra is fine
  (14:59Z).
- TJ v0.2.0: F1 A, the cu129 stack for native UMA. F12 A, the xtb binary accepted as a
  user-downloaded subprocess engine. "A - Ship it as a second model": OMol25 eSEN as
  `esen_omol25`. Q3 A, UMA weights from fairchem's HF cache.
- Lead decision within that policy: BSL-1.0 is an allowed (permissive) licence.
- DFT Hessians are FD of analytic gradients on the CPU. On the GPU the analytic KS Hessian is
  used only for classes the support record covers, and UKS IEF-PCM goes to FD.
- SCF stability: unstable only if λ_min < −1e-3 (`stability_tol`), and a follow gaining under
  1e-6 Eh (`stability_noise_eh`) ends as stable.
- fairchem engines are keyed to `high-precision` inference only.
- Author form everywhere: "Thomas J. L. Mustard Ph.D.". `PRDs/` is read-only.
- ADR-0001 to ADR-0022 are all PROPOSED, not approved. ADR-0016 to ADR-0022 are this cycle's
  (cache key from the resolved stage, MLIP identity by sha256, PySCF keyed stage, engine test
  policy, cu129 stack, the xtb binary, `esen_omol25`).

## Next Steps
- Tell TJ v0.2.0 is complete. Ask about fast-forwarding local `main`, approving the ADRs and the
  HACF v0.6.1 upgrade. Then the v0.3.0 architect stage.
- Carried forward:
  - **Security**: `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` process-wide. Save and
    restore the variable around the import when engines first share a process.
  - `stability.py` pins private PySCF 2.15.1 / GPU4PySCF 1.9.2 internals. A lock bump needs a
    re-pin, and the tripwire test enforces it.
  - The GPU R43 CPU-copy stability follow is fake-tested only.
  - GPU Hessian memory is outside the VRAM estimate, and relies on the OOM fallback.
  - The test-policy AST rule misses `import pytest as pt` aliases and decorator or default-arg
    skips. The runtime hook still catches them.
  - `PotentialResult` float fields are lax, and frozen is shallow. Tighten them when the core is
    next touched.
  - The store accepts `open_timeout_s=inf`, which raises `OverflowError`. Opening an existing
    store waits behind an active writer, which matters for v0.8.0.
  - CI runner disk for the CUDA wheels; cuTENSOR is absent (performance only).
  - Doc claims about acceptance must be derived from the record.
  - A faster fairchem inference mode, if wanted later.

## Field Notes (legacy)
`hyper_lore.py note --legacy` appends field notes below this line.
