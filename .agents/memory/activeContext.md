# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.5.0 TS P-RFO Optimizer & Active-Core Frequency Validator (mission
  `missions/release-0.5.0`, OPR.0.5.0, 15 slices: 01–13 plus replan slices 14 and 15), proved on
  TJ's Tier 3 (five literature TSs × GFN2 and UMA): built, audited, promoted by TJ (Phase 3,
  `ccacac5`) and accepted on this host on 2026-11-24.
- **Eta pauses after the v0.5.0 push (TJ)** until TJ's weekly usage reset, Sat 2026-11-28 6 PM PT
  (2026-11-29T02:00Z). No v0.6.0 mission until TJ restarts it.

## Session State
Updated 2026-11-24.
- Branch `feature/eta-rxncat-v0.5.0`, cut from `272b1b4` (the v0.5.0 mission commit on `main`;
  its parent `0d2a8d3` is v0.4.0 plus the HACF v0.6.3 upgrade). Version 0.5.0. The lead pushes,
  under TJ's standing "A: yes, push when it passes".
- v0.1.0 to v0.4.0 are described in their `CHANGELOG.md` entries.
- v0.5.0 adds:
  - core TS contracts in `core/ts_models.py` (`FormingBond`, `TSStep`, `TSSearchResult`,
    `TSValidationOptions`, `TSValidation`, `TransitionStateRecord`), the `ts_opt` stage kind and
    `prfo` as an optimizer name;
  - `optimize/prfo.py`: `PRFOOptimizer`, a clean-room Cartesian P-RFO (Banerjee 1985, Baker 1986,
    Bofill 1994) behind `TransitionStateOptimizer` (`optimize/ts_base.py`); failures raise
    `TSSearchFailedError` with a named reason; the Bofill r = 0 / s = 0 guard (R29);
  - `thermo/ts.py`: `validate_transition_state` (TJ A2 plus the R3 identity checks) and
    `ts_thermochemistry` (sigma from the TS bond graph, Q-TJ2 A);
  - `orchestrator/ts.py` `run_transition_state` (cached `ts_opt`, then the `frequency` stage's
    Hessian validates) and `orchestrator/barrier.py` `activation_free_energy` (ΔG‡ at 1 M and
    1 atm);
  - `cartesian_basis` on `pyscf_gpu_cpu`, keyed only when true (ADR-0041).
- Tier 3: inputs in `tests/e2e/data/e2e5/` (`SOURCES.md`, `t3_*.yaml`, XYZ files), tests
  `tests/e2e/test_t3_*.py`, promoted fixtures in `tests/fixtures/v0.5.0/` (11 files). The xtb E2E
  needs `ETA_RXNCAT_XTB` set, or it skips.
- Acceptance: `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json`, verdict `pass` (run at `b2046ca`, xtb
  on the CPU, UMA `uma-s-1p2p1` on CUDA), with its `known_limits` and `reported_notes`.
- The register `docs/prd/v0.5.0/DISCREPANCIES.md` has DV-01…DV-08 closed. DV-09a/b (the
  version bump) stay `decided`: no audit handoff named them. PD-009 is decided.
- HACF is v0.6.3 (`b7dcb44`, installed as `0d2a8d3`). Seats never run the installer. Upgrade to
  v0.6.5 (pinned `a215447`) is the operator's, after the v0.5.0 push. On rig 0.7.21,
  `hyper_spec.py proof` writes proofs natively and `hyper_migrate.py verify` skips
  `rig scope audit`; both are expected.

## Recent Decisions
- Licence policy (TJ, 2026-11-22 14:57Z, governs all versions): the core (`src/eta_rxncat/` and
  the core install) is MIT/BSD or equivalent only and never imports `ase`. Copyleft engines (DFT,
  MLIP, conformer search) are allowed only behind the engine interface, as optional extras or
  subprocesses, because they can be replaced. `ase` coming in through the MACE extra is fine
  (14:59Z).
- TJ v0.5.0:
  - A1 "Q1. A": clean-room Cartesian P-RFO, no TRIC; geomeTRIC `--transition` only as a
    black-box cross-check through its CLI.
  - A2 "Q2.  A": one mode below −20 cm⁻¹, below −50 cm⁻¹, active-core KE fraction ≥ 0.60.
  - Q-TJ2 A: TS sigma from the perceived bond graph, no TS degeneracy.
  - Q-TJ3 A, amended by Q-TJ4 A (R32): UMA gates everything; GFN2 gates convergence, mode count
    and the identity core (overlap, in phase, KE) except TS4a, which is report-only.
  - ADR-0041 "A: key only when on" (`cartesian_basis`).
  - Phase 3 (R33) "A: 0.75 all (Recommended)": bounds |ΔE_TS| ≤ 1e-5 Eh, heavy RMSD ≤ 0.01 Å,
    |ΔΔG‡(1 M)| ≤ 0.75 kcal/mol on UMA, ≤ 0.01 on GFN2; transcriptions confirmed.
- TJ v0.4.0:
  - Q1: clean room, because the original code's copyright is shared with the university, his
    advisor and his co-authors.
  - Q2 (b): core-frozen pre-relaxation is in v0.4.0. Roadmap B: R-group/ligand enumeration stays
    at v0.7.0. The Rh(I) (5+2) complexes go to v1.x.
  - Q3 B: M1 is the only v0.4.0 fixture.
  - Q4 A + R1 B: the template keeps keep/delete, pairs are ordered, and `fragment_delete` is
    optional.
  - Q5 A: charge and multiplicity are explicit.
  - Q6 A: bounds are core RMSD ≤ 0.10 Å, graft regression 1e-10 Å, and relaxed regression
    1e-5 Eh / 0.01 Å.
  - P1 A: contacts are recorded and the relaxed structures are gated on connectivity.
  - P2 A: the atom map comes from a stated rule, and TJ confirmed it by promoting the graft.
  - R2 A: planar flag plus junction handedness.
- R26: the core-freeze bound is 1e-6 Å, by measurement. ADR-0032 still says 1e-8 Å and is
  queued for TJ's next `/hyper-lore-approve`.
- Author form everywhere: "Thomas J. L. Mustard Ph.D.". `PRDs/` is read-only.
- ADR-0001 to ADR-0041 are all PROPOSED, not approved. ADR-0033 to ADR-0041 are v0.5.0's (the
  TS optimizer interface, the initial mode, the identity gate, TS sigma, GFN2 gating, the
  `ts_opt` stage, the geomeTRIC CLI cross-check, the pre-build window check and
  `cartesian_basis`).

## Next Steps
- The lead pushes v0.5.0 (`main` and the tag; it carries `0d2a8d3`, the HACF v0.6.3 upgrade),
  reports to TJ, and parks eta until TJ's reset (2026-11-29T02:00Z). The operator may then
  upgrade HACF to v0.6.5.
- Open with TJ: ADR approvals (`/hyper-lore-approve`, including ADR-0032's bound); geomeTRIC's
  "BSD 3-clause Non-AI" licence; whether GFN2 stays the default recipe (Q-E5); closing DV-09a/b.
- v0.6.0, when restarted: selectivity branching and competing TS screening (plan
  `PRDs/Eta-RxnCat_Living_Master_Plan.md`).
- Carried forward:
  - **v0.5.0**: an xtb `EngineError` (exit 128) propagates out of `run_transition_state` instead
    of a cached `failed_reason` (R32; v0.6.0+ robustness item). GFN2 TS4a has no reaction TS
    (report-only). UMA ΔG‡ spreads up to 0.074 kcal/mol run to run on CUDA (TS3a); UMA TS4a
    ΔG‡ 14.600 is 0.10 inside its 14.7 window edge. `cartesian_basis` matches Gaussian only for
    d-only Pople bases at 6D; the tightest R9 margin is 3-dimethyltetrazine (−8.25e-5 Eh,
    `grids_level=4`). The record's GFN2 `gated_on` text still reads "convergence, mode count"
    although R32 also gates the identity core (the tier gates are right).
  - **v0.4.0**: `JunctionVolume.sign` accepts `True` and `1.0`, and `signed_volume_angstrom3`
    accepts `True` (Pydantic laxness). Clean-room vector 07 is odd-electron, so the test uses
    multiplicity 2. Pure-graft junction handedness is undetermined on planar pair sets. UMA
    regressions vary by GPU noise (about 1e-8 Eh). `GraftSpec` duplicates
    `TemplateGeometry.mapping` until the v0.8.0 loader builds it from there.
  - **Security**: `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` process-wide. Save and
    restore the variable around the import when engines first share a process.
  - R50: a non-deterministic engine failure stays cached until `invalidate`.
  - UMA HF2 cyclohexene boat and twist-boat sit 0.126 Å apart (dedup threshold 0.125 Å). UMA
    `dropped` reasons can swap between runs.
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
