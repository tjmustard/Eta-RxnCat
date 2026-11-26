# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.6.0 selectivity branching and competing TS screening (mission
  `missions/release-0.6.0`, OPR.0.6.0, 14 slices: 01–12 plus replan slices 13 and 14). Built,
  audited, promoted by TJ (Phase 3, `6fce509`), and accepted on this host on 2026-11-26
  (`docs/prd/v0.6.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run at `b67214b`).
- Eta is not paused. TJ lifted the pause on 2026-11-25 with an overnight go.

## Session State
Updated 2026-11-26.
- Branch `feature/eta-rxncat-v0.6.0`, Start `6dc735f` (the slice 12 verdict commit). Version
  0.6.0. The v0.6.0 docs commit is this feature's last commit. Nothing is pushed or tagged; the
  lead pushes on TJ's word.
- v0.6.0 adds:
  - selectivity in `orchestrator/selectivity.py`: Boltzmann-summed pathway free energies,
    ΔΔG‡ and % de (ee refused over multi-member ensembles, R8; ratio overflow gives +inf, R27);
  - `PathwayPruningRule` in `core`, beside the untouched `PruningRule` (DV-02, DV-05);
  - TS conformer ensembles in `conformers/`: per-fragment ETKDGv3 embedding, a seeded non-core
    perturbation, core-frozen sampling, P-RFO re-search and dedup (DV-07, DV-09);
  - the xtb `EngineError` now ends as a cached `failed_reason` (slice 03; closes the v0.5.0
    known issue);
  - the HF-13 pre-relax wall-time guard, 600 s, recorded as `PreRelaxTimeout` (ADR-0048,
    PROPOSED);
  - Tier 4 unmapped and mapped endo/exo on GFN2 and UMA, and TJ's ethyl/n-propyl/n-butyl series
    on TS1a_n (slice 14, mechanics only).
- Acceptance: all 13 acceptance commands exit 0 (see the record's `commands`); default suite
  2212 passed, 0 skipped, exit 0. Regression bounds are TJ's (R31): |ΔE_TS| ≤ 1e-5 Eh,
  heavy-atom RMSD ≤ 0.01 Å, |ΔΔG‡| ≤ 0.01 kcal/mol on GFN2 and ≤ 0.75 kcal/mol on UMA.
- The register `docs/prd/v0.6.0/DISCREPANCIES.md` closes DV-01, 02, 03, 05, 07, 08 and 09, each
  naming the audit that satisfied it. DV-04 and DV-06 stay `open`: their audits named the
  slice parts, not the row as satisfied. PD-010 is logged as DV-01.
- HACF is v0.6.6 (pinned `561f6b1`). Seats never run the installer.

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
- The lead decides the v0.6.0 push. The push needs TJ's word (standing "push when it passes").
- Open with TJ: ADR approvals (`/hyper-lore-approve`, now including ADR-0048 and the v0.6.0
  batch); geomeTRIC's "BSD 3-clause Non-AI" licence; DV-04 and DV-06 closure; DV-09a/b.
- v0.7.0 items named by v0.6.0: the HF-13 pre-relax stall and host-load sensitivity; geomeTRIC
  writing `HT.v_*.txt` into the working directory.
- Carried forward:
  - **v0.6.0**: the mapped pair's UMA margin is −0.09 against ADR-0040's 1.0 kcal/mol; the 1.5
    kcal/mol pruning rule falls on opposite sides of GFN2 and UMA; the Tier 4 Liu TSs converge to
    one member per pathway (HF-10).
  - **v0.5.0**: GFN2 TS4a has no reaction TS (report-only). UMA ΔG‡ spreads up to 0.074
    kcal/mol run to run on CUDA (TS3a); UMA TS4a ΔG‡ 14.600 is 0.10 inside its 14.7 window edge.
    `cartesian_basis` matches Gaussian only for d-only Pople bases at 6D. The record's GFN2
    `gated_on` text still reads "convergence, mode count" although R32 also gates the identity
    core (the tier gates are right).
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
