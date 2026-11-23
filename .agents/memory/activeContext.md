# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.4.0 Conserved-Core Structure Mapper, a clean-room rewrite of `nMap` (mission
  `missions/release-0.4.0`, OPR.0.4.0, 8 slices), proved on TJ's Fixture M1: built, audited,
  promoted by TJ (Phase 3) and accepted on this host on 2026-11-23.
- **Eta is PAUSED after v0.4.0 (TJ).** Do not start v0.5.0 until TJ restarts it after the HACF
  efficiency release.

## Session State
Updated 2026-11-23.
- Branch `feature/eta-rxncat-v0.4.0`, cut from `baef0b3` (the v0.4.0 mission commit on `main`;
  its parent `c3506e6` is v0.3.0 plus the HACF v0.6.2 upgrade). Version 0.4.0. The lead pushes,
  on TJ's word only.
- v0.1.0 to v0.3.0 are described in their `CHANGELOG.md` entries.
- v0.4.0 adds the core contracts `GraftSpec`, `GraftResult`, `CloseContact` and
  `JunctionVolume` (`core/mapping_models.py`), and the package `eta_rxncat.mapping`:
  - `align`: Horn quaternion `superpose`, with a pair-set shape guard;
  - `graft`: ordered surgery, explicit charge and multiplicity, contacts, junction signed
    volumes and the planar flag;
  - `relax`: `relax_constrained_core`, with the core frozen to 1e-6 Å;
  - `report`: bond perception, core RMSD and junction volumes;
  - `errors`: `MappingError` and its subclasses.
  Importing it loads numpy only.
- Clean room (TJ Q1): no seat opens, clones, fetches or searches Eta_Scripts or nMap. Behaviour
  comes only from the operator-approved clean-room documents named in the mission SPEC.
  The vectors are in `tests/unit/mapping/data/cleanroom_nmap/` with `PROVENANCE.md`.
- Fixture M1: TJ's XYZ files are in `tests/e2e/data/e2e5/xyz/`, the provisional YAML is
  `tests/e2e/data/e2e5/m1_ts1a_n_to_ts1b_n.yaml`, the tests are `tests/e2e/test_m1_*.py`, and the
  promoted fixtures are in `tests/fixtures/v0.4.0/`. The xtb E2E needs `ETA_RXNCAT_XTB` set, or it
  skips.
- Acceptance: `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json`, verdict `pass` (run at `2dbc3ec`, xtb
  recipe on the CPU, UMA `uma-s-1p2p1` on CUDA), with its `known_limits`.
- The discrepancy register `docs/prd/v0.4.0/DISCREPANCIES.md` has all 25 rows (DV-01…DV-10,
  CR-01…CR-15) closed. PD-008 is decided.
- HACF is v0.6.2 (`5028b9f`, installed as `c3506e6`). Seats never run the installer. It pins rig
  {0.6.13, 0.7.16}, so on rig 0.7.21 `hyper_spec.py proof` writes proofs natively and
  `hyper_migrate.py verify` skips `rig scope audit`. Both are expected.

## Recent Decisions
- Licence policy (TJ, 2026-11-22 14:57Z, governs all versions): the core (`src/eta_rxncat/` and
  the core install) is MIT/BSD or equivalent only and never imports `ase`. Copyleft engines (DFT,
  MLIP, conformer search) are allowed only behind the engine interface, as optional extras or
  subprocesses, because they can be replaced. `ase` coming in through the MACE extra is fine
  (14:59Z).
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
- ADR-0001 to ADR-0032 are all PROPOSED, not approved. ADR-0028 to ADR-0032 are this cycle's
  (the graft input, Horn alignment, contacts and the overlap floor, the stated-rule atom map, and
  the core-frozen pre-relaxation).

## Next Steps
- The lead pushes v0.4.0 (`main` and the tag) under TJ's "A: yes, push when it passes", then
  reports to TJ. Eta then waits for TJ's restart after the HACF efficiency release.
- Open with TJ: ADR approvals (`/hyper-lore-approve`, including ADR-0032's bound); whether GFN2
  stays the default recipe (Q-E5); a licence look at geomeTRIC's "Non-AI" clause.
- v0.5.0, when restarted: TS optimisation (P-RFO) seeded from the mapper's guess, the active-core
  mode filter, and TJ's Tier 3.
- Carried forward:
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
