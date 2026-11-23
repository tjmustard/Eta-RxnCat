# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.3.0 Conformer Generation, GS Optimization & Boltzmann Ensemble Gate (mission
  `missions/release-0.3.0`, OPR.0.3.0, 12 slices), with Human Fixtures 1 and 2 and TJ's 5-tier
  Tiers 1 and 2: built, audited, promoted by TJ (Phase 3) and accepted on this host on
  2026-11-23. Next: v0.4.0 (the conserved-core structure mapper, a clean-room `nMap`), from
  `PRDs/Eta-RxnCat_Living_Master_Plan.md`.

## Session State
Updated 2026-11-23.
- Branch `feature/eta-rxncat-v0.3.0`, cut from `24f1af5` (local `main`, which carries v0.2.0 and
  the HACF v0.6.1 upgrade). Version 0.3.0. Pushing is the person's call.
- v0.1.0 and v0.2.0 are described in their `CHANGELOG.md` entries.
- v0.3.0 adds the core contracts `ThermoResult`, `OptimizationResult`, `ConformerRecord` and
  `ConformerEnsemble`, and four packages: `eta_rxncat.thermo` (quasi-RRHO at 1 M from Hessians),
  `eta_rxncat.optimize` (`GeometricOptimizer`, geomeTRIC in the `opt-geometric` extra),
  `eta_rxncat.conformers` (two-pass ETKDGv3, dedup, degeneracy, ensembles) and
  `eta_rxncat.orchestrator` (the cached single-species runner, reaction free energies, reports).
  `mapping/` still holds only a docstring.
- Acceptance: `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`, verdict `pass` (run at `0a48204`, xtb
  recipe on the CPU, UMA `uma-s-1p2p1` on CUDA), with its `known_limits`. Promoted fixtures are in
  `tests/fixtures/v0.3.0/`, and TJ's ωB97M-V reference is in
  `tests/e2e/data/reference/tj-reference-b3lyp-20261123/`.
- Acceptance envs: `.venv-accept-opt` (xtb recipe) and `.venv-accept-uma` (`gpu`, `mlip-uma`,
  `opt-geometric`), beside `.venv-accept-gpu` and `.venv-accept-mace` (`AGENTS.md`, "Engine
  tests"). `.venv` is the base dev env. E2E runs are behind the `e2e` marker.
- The discrepancy register `docs/prd/v0.3.0/DISCREPANCIES.md` has all 23 rows closed.
- HACF is v0.6.1 (`b01d41b`) with the codebase-memory-mcp code graph. Still no HACF install,
  uninstall or migrate apply without TJ's go.

## Recent Decisions
- Licence policy (TJ, 2026-11-22 14:57Z, governs all versions): the core (`src/eta_rxncat/` and
  the core install) is MIT/BSD or equivalent only and never imports `ase`. Copyleft engines (DFT,
  MLIP, conformer search) are allowed only behind the engine interface, as optional extras or
  subprocesses, because they can be replaced. `ase` coming in through the MACE extra is fine
  (14:59Z).
- TJ v0.3.0:
  - Q1 C: the team drafts HF1/HF2, and TJ promotes them and supplies the reference values.
  - Q2 B: the starter is reference only, with a discrepancy register.
  - Q3 A: geomeTRIC goes behind an `Optimizer` interface in the `opt-geometric` extra.
  - Q4 C: the incremental-solvation test runs on the species runner.
  - Q5 A: the regression bounds by kind are not widened.
  - Q-E1 A: tier map T1/T2 in v0.3.0, T3 in v0.5.0, T4 in v0.6.0, T5 in v0.9.0.
  - Q-E5 C: GFN2 windows are reported; "if it turns out MACE, UMA, or OMol25 are needed then
    they should become standard".
  - TJ confirmed the four Tier 1/2 SMILES and promoted the candidates (Phase 3).
- The accuracy gate is UMA against TJ's ωB97M-V/def2-TZVPD//B3LYP/6-31G** per-conformer values;
  xtb is never gated.
- Author form everywhere: "Thomas J. L. Mustard Ph.D.". `PRDs/` is read-only.
- ADR-0001 to ADR-0027 are all PROPOSED, not approved. ADR-0023 to ADR-0027 are this cycle's
  (the `opt-geometric` extra, geomeTRIC's lower-level API, two-pass ETKDGv3 and dedup,
  thermochemistry from stored Hessians, candidates-only commits). ADR-0024's body still names
  `CoordSysDict`, which R44 corrected.

## Next Steps
- Lead reports v0.3.0 to TJ, and the push waits on TJ's word. Then the v0.4.0 architect stage
  (the conserved-core mapper; TJ's Tier 3 comes in v0.5.0).
- Open with TJ: ADR approvals (`/hyper-lore-approve`); whether GFN2 stays the default recipe
  (Q-E5 escalation).
- Carried forward:
  - **Security**: `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` process-wide. Save and
    restore the variable around the import when engines first share a process.
  - R50: a non-deterministic engine failure stays cached until `invalidate`.
  - UMA HF2 cyclohexene boat and twist-boat sit 0.126 Å apart (dedup threshold 0.125 Å).
  - UMA `dropped` reasons can swap between runs (GPU noise in the G order); the kept records do
    not change.
  - `stability.py` pins private PySCF 2.15.1 / GPU4PySCF 1.9.2 internals. A lock bump needs a
    re-pin, and the tripwire test enforces it.
  - The GPU R43 CPU-copy stability follow is tested only with fakes. GPU Hessian memory is
    outside the VRAM estimate, which relies on the OOM fallback.
  - The test-policy AST rule misses `import pytest as pt` aliases and decorator or default-arg
    skips. The runtime hook still catches them.
  - `PotentialResult` float fields are lax, and frozen is shallow (DV-23). Tighten them when the
    core is next touched.
  - The store accepts `open_timeout_s=inf`, which raises `OverflowError`. Opening an existing
    store waits behind an active writer (v0.8.0).
  - CI runner disk for the CUDA wheels; cuTENSOR is absent (performance only).
  - Doc claims about acceptance must be derived from the record.

## Field Notes (legacy)
`hyper_lore.py note --legacy` appends field notes below this line.
