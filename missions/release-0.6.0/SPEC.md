---
id: OPR.0.6.0
mission: release-0.6.0
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope mission create)"
created: "2026-11-25"
intent: "Add a selectivity scorer (multi-pathway TS comparison over core-frozen TS conformer ensembles, Boltzmann-summed pathway barriers, \u0394\u0394G\u2021 with % ee / % de / regioselectivity, evaluated per-pathway priority-gate pruning) and prove it on TJ's Tier 4 endo/exo cases (Human Fixture 4)."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0007, ADR-0008, ADR-0014, ADR-0019, ADR-0021, ADR-0023, ADR-0024, ADR-0025, ADR-0026, ADR-0027, ADR-0028, ADR-0031, ADR-0032, ADR-0033, ADR-0035, ADR-0036, ADR-0038, ADR-0040, ADR-0042, ADR-0043, ADR-0044, ADR-0045, ADR-0046, ADR-0047, ADR-0048]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.6.0 — Selectivity Branching, TS Conformer Ensembles & Human Fixture Tier 4

## Intent

v0.6.0 is the sixth of ten versions. v0.5.0 turns one guess into one verified TS and one barrier.
v0.6.0 compares **competing pathways, each an ensemble of TSs**:
- a **TS conformer search** (TJ Q1 B): conformers sampled around a verified TS with the reactive
  core frozen, each pre-relaxed with the core frozen, re-searched with P-RFO, validated, checked
  for the **same diastereomeric face as its seed**, deduplicated and Boltzmann-summed;
- a **selectivity scorer** (`eta_rxncat.orchestrator.selectivity.score_selectivity`, pure): per
  pathway Boltzmann-summed G, ΔΔG‡, the product ratio and the selectivity percentage, labelled ee,
  de or regio by the caller;
- an **evaluated per-pathway pruning rule** and a small selectivity runner (TJ Q2 A);
- **Human Fixture 4 / TJ's Tier 4**: endo vs exo for Cp + cyclopropene (unmapped: TS1a_n vs TS1a_x)
  and Cp + cyclobutene (mapped: TS1b_n vs TS1b_x, the exo TS grafted from TS1a_x), on GFN2 and UMA,
  gated per TJ Q3 A, candidates committed for TJ's Phase 3.

Plan (`PRDs/Eta-RxnCat_Living_Master_Plan.md` l.49–51, authoritative per TJ Q1 "A"):
> `PR #12 (feat/selectivity-scorer)`: Implement multi-pathway TS comparison, Boltzmann-weighted
> selectivity barriers, `% ee` / regioselectivity calculation, and priority-gate pruning rules.
>
> `PR #13 (test/e2e-ddg-fixture)`: Run E2E validation against **Human Fixture 4** (competing TS1
> vs. TS2 reaction map -> differential barrier and `% ee`).

- **Base:** main `d94b9c9` (HACF v0.6.6 install) ← `34de2b4` (HACF v0.6.5) ← `21ece4e` (v0.5.0,
  tagged). The HACF commits go out with v0.6.0. Branch `feature/eta-rxncat-v0.6.0`, cut by the
  builder from the mission commit.
- **Mode:** delta. `spec/compiled/architecture.yml` has 11 nodes (`hyper_ledger.py validate: ok`).
- **Compiled by** spec-resolve@eta-rxncat-hacf (2026-11-25) from `Draft_PRD.md` rev 2 (sha256
  `cbf01312…5fd63440`) and `RedTeam_Report.md` (sha256 `fcfc61ff…0f56e6c`, F1–F15), with resolve's
  pre-build measurement (§2 "Host facts", HF-1…HF-13). Author of every decision quoted as TJ's:
  Thomas J. L. Mustard Ph.D.

### TJ decisions (verbatim; binding)

**v0.6.0 answers** (relayed by advisor-lead@kernel on 2026-11-25; TJ chose through the advisor):

| # | Question (row) | TJ, verbatim | Meaning here |
|---|---|---|---|
| Q1 | Where the competing TSs come from (`qitem-20261125054847-b2c5081af2850ddf`; answer `qitem-20261125055335-ca097cacf39333ff`) | "B: add a TS conformer search in v0.6.0 (core-frozen conformer sampling around each TS, each re-searched with P-RFO, deduplicated and Boltzmann-summed; about 2-3 more slices) — NOT the recommendation. Mind the memory rule for GPU TS searches." | The TS conformer search is in scope (slices 05, 06). Every pathway's G is a Boltzmann sum over its validated, face-consistent, deduplicated ensemble. "The memory rule" is quoted in R10. |
| Q2 | How pruning works before the v0.8.0 scheduler (`qitem-20261125054847-3f3bd573f97e69bd`; answer `qitem-20261125055336-b525985719cff106`) | "A: evaluated per-pathway rule in core + optional pathway labels + small selectivity runner; 1.5 in the Tier 4 fixture, no library default (the recommendation)." | US-002, US-006, R7, slices 02 and 07. |
| Q3 | Tier 4 pass/fail (`qitem-20261125054847-14b7ddf17c0d4428`; answer `qitem-20261125055336-dcb056d88dc68cc3`) | "A: assertions on both engines (GFN2 gated per pair only if measured to reproduce, else report-only) + UMA within reference +/-2.0 floored at 0.5; pre-build misses come back to TJ (the recommendation)." | G5, R12, R21. Windows apply to the **Boltzmann-summed** ΔΔG‡. GFN2 measured to reproduce on both pairs (HF-7), so GFN2's sign and > 0.5 are gated on both. No pre-build miss (HF-7). |

**Standing decisions that bind:**
- **Licence** (11-22, verbatim): "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." and "It's fine that the engine MACE pulls in ASE just not the core."
  geomeTRIC stays out of vendored code and the core runtime dependencies (ADR-0014, ADR-0023); it
  reaches the ensemble runner only through the injected `Optimizer` (`opt-geometric` extra, R5).
- **Q1 "A"**: the `PRDs/` plan is authoritative and `PRDs/` is read-only. **Q2 "B"**: the starter
  zip is reference only; it unpacks byte-identical under `docs/prd/v0.6.0/` with a `.ruff.toml`
  `exclude = ["*"]` gate file (ADR-0007), and every plan-vs-zip or plan-vs-code mismatch is a DV
  row in `docs/prd/v0.6.0/DISCREPANCIES.md` (+ `docs/prd/PLAN_DISCREPANCIES.md` across zips).
- **Q-E1 "Q1. A"**: Tier 4 physics runs in v0.6.0 through v0.6.0's own API; the YAML 5-tier harness
  re-runs all tiers at v0.9.0.
- **Q-E3 "Q3. B, but these may need updating as we define the YAML/JSON format."**: the team drafts
  the Tier 4 YAMLs (schema 1) for TJ's review; every fixture YAML stays provisional.
- **Q-E4 "Q4. A but the files attached can be used as reference."**: forming-bond carbons
  `[1, 2, 3, 5]`; geometries from TJ's SIs (`~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/si/`);
  mismatch 4 settled: **P1b_x** and **TS1b_x** are transcribed from Liu 2013's SI (HF-1) and TJ
  confirms them at Phase 3.
- **Q-E5 "Q5. C, if it turns out MACE, UMA, or OMol25 are needed then they should become
  standard."**: numeric windows gate UMA only; sign/ordering that GFN2 reproduces is gated on both.
- **Q3 (amended)**: "Build, install, and run these autonomously as to move on to the next
  step/question." A failed GPU run is a finding with its output.
- **Phase 3 is TJ's** (v0.3.0 R1 "R1. A", ADR-0027): novel outputs land in
  `tests/candidate_outputs/v0.6.0/`, only TJ promotes; the Phase 3 gate sits before slice 12.
- **v0.5.0 Phase 3** (`qitem-20261124221114-efeccb6d9876cb00`): "A: 0.75 all (Recommended)" — read
  per quantity in R6.
- **v0.5.0 Q-TJ4 "A (Recommended)"**: on GFN2 the identity core (forming overlap ≥ 0.50, in phase,
  active-core KE ≥ 0.60) is gated with convergence and the mode count. **v0.5.0 A2 "Q2.  A"**:
  exactly one mode below −20 cm⁻¹, that mode below −50 cm⁻¹, KE ≥ 0.60. Every ensemble member
  passes its recipe's gates.
- **Clean room** (v0.4.0 Q1, v0.5.0 A1): no seat opens Eta_Scripts or nMap source; no TS-optimizer
  or conformer-search source is read. v0.6.0 needs no nMap behaviour.
- **Push**: TJ's standing go covers verdict pass + checks only, and the lead does it. Author
  "Thomas J. L. Mustard Ph.D." everywhere. Commits end with exactly the two footer lines
  `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
  `.agents/hacf-manifest.json` at commit time. No co-author trailer.

## 1. Introduction & Goals

**Problem.** Eta finds and validates one TS from one start and computes its barrier
(`run_transition_state`, `activation_free_energy`). Nothing samples the conformations around a TS,
nothing compares two TSs, `PruningRule` (`core/graph.py:143`) is "validated as a schema and by
reference, never evaluated", and `ReactionNode` has no pathway label. An xtb `EngineError`
(v0.5.0: exit 128 on GFN2 TS4a) propagates out of `run_transition_state`
(`orchestrator/ts.py:300`), so one crash would lose an ensemble.

**Solution.**
1. `core` (slice 02): optional `ReactionNode.pathway`; a typed, evaluated `PathwayPruningRule`
   beside the free-form `PruningRule`; `TSEnsembleOptions`, `TSEnsemble`, `TSEnsembleMember`,
   `TSEnsembleExclusion`, `SelectivityResult` models. No new stage kind (R24).
2. `run_transition_state` (slice 03): an `EngineRuntimeError` becomes a cached failure row
   `failed_reason="engine_error"`; `EngineUnavailableError`/`EngineInputError` re-raise, uncached (R3).
3. `score_selectivity` (slice 04): pure, closed-form, log-sum-exp, constants from `eta_rxncat.thermo`.
4. `sample_ts_conformers` + `forming_bond_configuration` (slice 05, `eta_rxncat.conformers`):
   per-fragment ETKDGv3 anchored on the seed plus a seeded non-core perturbation (R16), and the
   face descriptor (R1).
5. `run_ts_ensemble` (slice 06, `orchestrator/ts_ensemble.py`): pre-relax (`relax_constrained_core`,
   cached as `constrained_preopt`), `run_transition_state`, gates, face check, dedup, energy window,
   weights, exclusions (R1, R2, R8, R11, R17, R20).
6. `run_selectivity` (slice 07): per priority-1 pathway, seed TS → ensemble → score → pruning →
   unpruned priority ≥ 2 nodes through the species runner; every decision recorded (R7).
7. Tier 4 inputs (08), E2E per pair (09, 10), acceptance record (11), TJ's Phase 3, verdict and
   the 0.6.0 bump (12).

**Audience.** TJ (user, Phase 3 reviewer); the build seats. Later: v0.7.0 (multi-template seeds),
v0.8.0 (the scheduler adopts the pruning rule and the ensemble), v0.9.0 (the YAML harness).

**Goals (measurable):**
- **G1.** `score_selectivity` reproduces closed-form values within 1e-12 for: two single-member
  pathways; multi-member pathways (weights sum to 1 within 1e-12); degeneracy g = 2 on a member
  (G_i − RT ln g_i); ties (50:50); ΔΔG‡ = 200 kcal/mol with no overflow and no clamp; T = 350 K;
  permuted pathways and members give the same result. The starter's check holds: 1.7 kcal/mol at
  298.15 K → 89.2 ± 0.5 % (de/ee). Refusals: mixed reactant sets, temperatures, recipe identities
  (engine name, model, engine version), an empty pathway, fewer than two pathways, and `kind="ee"`
  with any pathway of more than one member (R8).
- **G2.** Pruning (R7): with ΔΔG‡ > threshold (strict) exactly the computed minor pathway's nodes
  with `priority ≥ 2` and `pathway == minor` are pruned; at ΔΔG‡ == threshold and below, none. Never
  a `pathway=None` node. Either pathway with no valid member → no pruning, reason recorded. The
  computed major differs from a caller's expectation → pruning still targets the computed minor and
  the signed ΔΔG‡ is recorded. Pruned nodes: status `pruned`, zero engine calls (counting wrapper).
- **G3.** `run_transition_state` with a stub engine raising `EngineRuntimeError` returns
  `failed_reason == "engine_error"` (message kept) and caches it; a second run hits the row with zero
  engine calls. `EngineUnavailableError` and `EngineInputError` propagate and leave no row (R3).
- **G4.** Sampler and ensemble, offline (analytic/stub surfaces and the Tier 4 seed geometries, no
  engine): sampler deterministic (byte-equal coordinates for a fixed seed); core coordinates equal
  the seed's exactly in every sample; every sample keeps the seed's face; a constructed
  face-crossed sample (dienophile CH₂ reflected through the C2–C3–ring plane) is excluded as
  `face_mismatch`; re-converged copies of one saddle merge regardless of ΔG noise and are summed
  once; two distinct saddles stay distinct; the core moves ≤ the ADR-0032 bound in pre-relaxation;
  `forming_bond_configuration` gives endo (+1, +1) and exo (−1, −1) on Liu's four TSs and is
  invariant under reflection (HF-3).
- **G5.** Tier 4 per recipe (GFN2 CPU; UMA `uma-s-1p2p1` CUDA) and per pair (unmapped TS1a_n/TS1a_x;
  mapped TS1b_n/TS1b_x), every summed member passing its recipe's v0.5.0 gates and the face check:
  - **both engines, both pairs (gated):** endo is the major pathway and the Boltzmann-summed
    ΔΔG‡ > 0.5 kcal/mol (GFN2 gated on both pairs: HF-7);
  - **UMA only (gated):** unmapped ΔΔG‡ ∈ [2.3, 6.3]; mapped ΔΔG‡ ∈ (0.5, 3.8] (R12);
  - **both (gated):** no `engine_error` exclusion and no `face_mismatch` exclusion in any ensemble;
    the endo seed reproduces the promoted v0.5.0 fixture within R6's table.
- **G6.** Mapped pruning against TJ's 1.5 kcal/mol, using the measured Boltzmann-summed ΔΔG‡: if
  > 1.5, `downstream_exo_minor` (P1b_x) is `pruned` with zero engine calls; otherwise it is computed.
  Both outcomes are acceptable and recorded with the number. (Measured single-TS values: GFN2 1.753
  → prune; UMA 1.410 → compute; HF-7.)
- **G7.** A second run of every Tier 4 E2E in the same store: every cached stage the first run
  visited (`constrained_preopt`, `ts_opt`, `frequency`, reactant stages) is 100 % hits, zero new
  rows, failure rows included; the sampler re-generates byte-equal samples; the ensemble, score and
  pruning record are equal (history fields excluded, N11).
- **G8.** Importing `eta_rxncat.orchestrator.selectivity` loads no `torch`, `pyscf`, `fairchem`,
  `geometric` or `rdkit`; importing `eta_rxncat.conformers.ts_sampler` and
  `eta_rxncat.orchestrator.ts_ensemble` loads no `torch`, `pyscf`, `fairchem` or `geometric`;
  `eta_rxncat.core` still loads no numpy or RDKit.

## 2. Confidence Mandate

**Score: 9/10.** Every red-team finding has a decision (R1–R15) and every architect OPEN item is
decided by measurement (R16–R25). The blocker F1 is closed in the specs by a measured, general face
check and a sampler that cannot cross faces by construction. The remaining point of uncertainty is
question Q-RES1 to TJ (Tier 4 ensembles measured at one member each, HF-10). It is now CLOSED:
TJ chose B, amended to an alkyl R-group series, which is slice 14 (R29, HF-14).

### Host facts measured by resolve (2026-11-25, before the build; TJ Q3 A "pre-build misses come back to TJ")

Scripts and raw output: `~/.hacf/eta-rxncat-hacf/evidence/v060-resolve/` (README there). Engines:
`.venv` (xtb 6.8.0 via `ETA_RXNCAT_XTB`) and `.venv-accept-uma` (UMA `uma-s-1p2p1`, CUDA). Every
engine run sat behind a blocking host check (`hostcheck_*.txt`), one heavy run at a time.

- **HF-1 Transcriptions.** TS1a_x from TJ's builder (`XYZ_FILES`, `ast.literal_eval`, never
  executed) is coordinate-identical to Liu SI S9 (sha256 `ec319a52…0f684d60`). TS1b_x = SI S9 right
  column (1 atom after the "TS1b_x" label) + SI S10 left column (first 20 atoms), sha256
  `2a0b8362…ff365fd82`. P1b_x = SI S20 right column (21 atoms after "P1b_x"), sha256
  `ca870643…c9699b5eec`. Checks: TS1a_x C8H10/18, TS1b_x C9H12/21 two fragments each; P1b_x C9H12/21
  one fragment; every H degree 1, no C below degree 3; forming pairs (1,2),(3,5) at 2.353 Å
  (TS1a_x) and 2.266 Å (TS1b_x).
- **HF-2 References (M3, closed).** Liu header G: TS1a_x − TS1a_n = **+4.273**; TS1b_x − TS1b_n =
  **+1.849** kcal/mol (red team Part C; arithmetic re-checked). TJ's +4.3/+1.8 stand as the window
  centres; 1.849 is recorded beside 1.8.
- **HF-3 Face descriptor.** The red team's plane test (dienophile CH₂ side of the C0/C1/C4/C5
  plane) does **not** separate endo from exo: C7 is on the same side in TS1a_n (+2.86 Å) and TS1a_x
  (+2.60 Å). The relative-configuration descriptor (R1) gives endo (+1, +1) and exo (−1, −1) on all
  four Liu TSs, and is mirror-invariant by construction.
- **HF-4 The draft's sampler fails.** ETKDGv3 with a `coordMap` on the two-fragment TS graph (RDKit
  2026.09.2, `SetCoordMap` and the legacy keyword alike): after core alignment the core is off by
  up to **1.91–2.15 Å**; only 2/20 TS1a_n samples keep the seed's face (mixed (−1, +1) faces
  appear); pinning 14 atoms gives identical output (the map is ignored across fragments);
  `useRandomCoords` embeds 0/20. The draft's fallback (rotor scan) has nothing to rotate on Tier 4.
- **HF-5 Per-fragment sampler works.** Each fragment embedded alone (ETKDGv3, coordMap on its
  anchor atoms), Kabsch-placed on the seed by the anchor: core ≤ 0.011 Å before reset, **50/50
  faces preserved** on all four TSs; all 50 embeddings collapse to one geometry 0.22–0.26 Å from
  the seed.
- **HF-6 M1 cost (one P-RFO search + frequency).** GFN2 CPU 4.1–5.3 s (5–8 engine calls); UMA CUDA
  6.2–8.5 s (5–11 calls, model load included). Graft core-frozen relax: GFN2 1.7 s, UMA 25.8 s.
  Ensemble member (pre-relax + search + frequency): GFN2 3.4–46 s, 70–101 s per 11-member ensemble;
  UMA 5.1–49 s per member, 100–145 s per 11-member ensemble, plus one unexplained pre-relax stall (HF-13).
- **HF-7 Single-TS ΔΔG‡ (G_x − G_n, engine TSs from Liu's starts; M4/M6).**

  | Pair | GFN2 | UMA | Liu (header G) | UMA window | UMA margin to edge |
  |---|---|---|---|---|---|
  | unmapped TS1a_x − TS1a_n | **+3.977** | **+4.602** | +4.273 | [2.3, 6.3] | 1.70 |
  | mapped TS1b_x − TS1b_n | **+1.753** (graft +1.754) | **+1.410** | +1.849 | (0.5, 3.8] | 0.91 |

  GFN2 reproduces the sign and > 0.5 on both pairs → gated on both (Q3 A). UMA is inside both
  windows → no pre-build miss. ADR-0040's 1.0 kcal/mol margin was written for absolute barrier
  windows; applied here the mapped UMA margin (0.91) falls short of it, which is recorded, not a
  miss (R4). The mapped values straddle TJ's 1.5 pruning threshold: GFN2 prunes P1b_x, UMA computes
  it (G6).
- **HF-8 M5 graft.** Cyclobutene grafted onto TS1a_x with the M1 YAML's keep/delete/alignment lists
  unchanged: pure-graft forming-core `[1,2,3,5]` RMSD to Liu's TS1b_x **0.046 Å** (v0.4.0 bound
  0.10); after core-frozen relax and P-RFO the TS reaches TS1b_x: forming-core RMSD 0.027 (GFN2) /
  0.022 Å (UMA), G equal to the search from Liu's own geometry within 1.2e-6 Eh. The full-atom
  RMSD under TS1b_n's map is 0.55 Å because Liu's TS1b_x atom order differs; slice 10 derives the
  graft→TS1b_x map by the ADR-0031 rule.
- **HF-9 Endo seeds reproduce v0.5.0.** Re-searching TS1a_n (Liu start) and TS1b_n (M1 start) in a
  fresh store: TS G vs the promoted fixture — GFN2 2e-12 kcal/mol (both), UMA 8.6e-5 and 2.9e-4
  kcal/mol (4.6e-7 Eh).
- **HF-10 M2 ensembles: one distinct member per TS.** Per-fragment ETKDGv3 (20) + Cartesian
  perturbation of non-core atoms (σ 0.3 Å, 20) → pre-dedup → seed + 10 re-searched per TS. GFN2:
  TS1a_n, TS1a_x, TS1b_n, TS1b_x(graft) each **1 distinct member**; 43/44 searches converged to the
  seed's saddle with the seed's face; one perturbed sample failed the pre-relax core bound
  (`CoreDisplacementError`, 8.4e-4 Å). UMA: TS1a_n, TS1a_x, TS1b_n each **1 distinct member** (10/11, 11/11, 11/11 converged to the seed's saddle with the seed's face; one `ts_search_failed:no_reaction_mode` on TS1a_n's perturbed sample 23 — the same sample that failed the GFN2 core bound); TS1b_x(graft) 6/6 to the seed before the run was stopped at its 7th member (HF-13).
- **HF-11 Duplicate noise floor (F2).** Re-converged copies of one saddle: |ΔG| ≤ 0.0021 kcal/mol,
  RMSD ≤ 4e-5 Å (GFN2); |ΔG| ≤ 0.00046 kcal/mol, RMSD ≤ 3.3e-5 Å (UMA). Two copies kept as distinct would have lowered G_p by
  RT ln 2 = 0.41 kcal/mol (red team F2), so the merge rule is decisive here.
- **HF-12 Faces at the starts.** Atom order decides the sign, so a member is always compared with
  its own seed (same atom order), never with Liu's file: in the graft layout TS1b_n is (−1, −1) and
  the grafted TS1b_x is (+1, +1).
- **HF-13 Pre-relax stall (UMA).** TS1b_x(graft) perturbed sample 24 ran > 14 min at ~15 CPU cores,
  0 % GPU, no output, and was stopped by resolve. Re-run alone with an eta-frames-only stack sampler
  it completed: pre-relax 42.2 s, all inside `GeometricOptimizer._run` (the injected geomeTRIC black
  box), then P-RFO 5.4 s. eta's `maxiter` (200 passed, 300 default) did not bound the stall. Not
  reproduced; cause unknown. Mitigation: every E2E command runs under `timeout 3600` and per-member
  wall time is recorded (R25).
  **Replan 3 (measured, `~/.hacf/eta-rxncat-hacf/evidence/v060-replan3/`):** now 3 stalls in 13 known
  UMA TS1b_x(graft) runs at the same inputs (resolve; audit #1 of slice 10, exit 124 at 3600 s; resolve's
  replan-3 run 7 of 9). Run 7's six faulthandler dumps (filtered to eta frames + a geomeTRIC frame
  count) all sit in an ensemble member's pre-relax: `_PreRelax.run` → `relax_constrained_core` →
  `GeometricOptimizer._run` → geomeTRIC (10–16 frames) → numpy `eigh`/`svd`/`max`, with the leaf
  changing between dumps. The black box is looping, live, between engine calls: no engine frame, GPU
  0–1 %, ~17 cores of OpenBLAS threads (20 by default, torch also 20). Thread count multiplies the burn
  but is not the cause. The trigger is UMA run-to-run noise, since eta seeds geomeTRIC's RNG. The fix
  inside the black box is not cheap, so slice 13 bounds it (R28).

- **HF-14 Flexible alkyl series (replan 4; evidence `~/.hacf/eta-rxncat-hacf/evidence/v060-replan4/`).** The graft of R onto TS1a_n at H16 is clean: alignment 0.033–0.035 Å, no contacts, 24/27/30 atoms. It needs the all-anti chain (the ETKDG n-propyl conformer clashes, 0.28 Å) and the lower-fit sp2 order (the mirror order fits at 0.49 Å). Ensemble with the R18 defaults, distinct members ethyl / n-propyl / n-butyl: GFN2 3/4/5 (wall 192/482/694 s), UMA 3/4/5 (223/206/819 s, RSS 8.1 GB). Every run: Σw = 1, all faces [1, 1], second pass 0 rows / 0 calls / equal ensemble, no `PreRelaxTimeout`. The gauche rotamers come as mirror-image pairs at equal G (ΔG ≤ 0.05 kcal/mol, equal RMSD to the seed), so they are genuinely distinct saddles. Longest member pre-relax: GFN2 282 s (n-propyl), UMA 387 s (n-butyl), inside the 600 s guard. n-Butyl loses one member to `connectivity_changed` and one to `ts_search_failed:no_reaction_mode` on both engines.

### OPEN for TJ (row ids in the handoff; the build does not wait unless noted)
- **Q-RES1 (M2 → TJ, as the draft required; row `qitem-20261125064639-149cf207118abaab` to advisor-lead@kernel) — CLOSED 2026-11-25: B, amended (R29).** TJ, verbatim (row `qitem-20261125134835-b68359c8b88aa4f6`): "B (the recommendation). Add one mechanics-only flexible-ensemble E2E as slice 13, before the acceptance record. Graft a rotor-bearing substituent (e.g. methoxymethyl) onto TS1a_n and run it on GFN2 and UMA. Gates: >= 2 distinct members, weights summing to 1, consistent faces, and a second run that is all cache hits. ddG dagger is reported only. Replan the details as needed." Amended (row `qitem-20261125135141-40dabb65dfb7a8a8`), verbatim: "Can we r-group enumerate a new TS from with a alkyl chain"; he chose R = ethyl, n-propyl, n-butyl on TS1a_n's cyclopropene CH2, with the HF-13 guard on the grafts. That is slice 14, because 13 was already the HF-13 guard. Original text follows. Every Tier 4 ensemble is one member on GFN2
  and on UMA (HF-10), so Tier 4 exercises the Boltzmann sum only as the identity. Options: A accept
  unit-level proof (G1, G4), B add one mechanics-only flexible E2E (slice 13), C drop the TS
  conformer search from v0.6.0. Recommendation B. **Gates:** nothing in slices 01–04, 07–12; slices
  05–06 proceed unless TJ picks C (then resolve replans them); B adds slice 13 by replan before
  slice 11.

## 3. Scope

### In scope
1. **Starter (slice 01).** `PRDs/Eta-RxnCat-v0.6.0.zip` (36 files, sha256 `0c1b1f6e…a78a88b7`)
   unpacked byte-identical to `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/` plus the `.ruff.toml`
   gate file; `docs/prd/v0.6.0/DISCREPANCIES.md` with DV-01…DV-09; `PLAN_DISCREPANCIES.md` hashes
   unchanged, PD-010 status updated.
2. **Core contracts (slice 02).** `ReactionNode.pathway`; `PathwayPruningRule` and
   `ReactionGraph.pathway_pruning_rules`; ensemble and selectivity models. Additive; existing
   YAML/JSON and cached rows load unchanged.
3. **Engine-error fix (slice 03)** in `run_transition_state` (R3).
4. **Scorer (slice 04).**
5. **TS conformer sampler + face descriptor (slice 05).**
6. **TS ensemble runner (slice 06).**
7. **Selectivity runner + pruning (slice 07).**
8. **Tier 4 inputs (slice 08):** TS1a_x, TS1b_x, P1b_x xyz files with `SOURCES.md` rows; provisional
   `t4_endo_exo_unmapped.yaml`, `t4_mapped_selectivity_pruned.yaml`; input checks. The pre-build
   measurement is done (HF-1…HF-12); the slice re-runs the transcription procedure and must produce
   byte-equal files.
9. **Tier 4 E2E (slices 09–10)** per recipe, candidates committed.
10. **Acceptance record (slice 11)** → **TJ Phase 3** → **verdict and 0.6.0 bump (slice 12)**.
11. Docs: README Features/Roadmap derived from the acceptance record. CHANGELOG is the scribe's (its
    `[0.6.0]` entry should say the EngineError issue is fixed).

### Out of scope (each would otherwise grow sideways)
- Ground-state conformer search changes (v0.3.0's search is used as is).
- Sampling the reactive core itself (other forming-bond geometries are other TSs).
- The DAG scheduler, graph-wide crash resume, multi-level refinement, energetic span/TOF: v0.8.0.
  Topology audit: v0.9.0.
- TJ's YAML schema (`schema_version: "0.1.0"`, hyperedges, `gating:`): converted to schema 1,
  provisional (Q-E3).
- Tier 5; Dataset A/C pathways; PySCF/DFT and solvation for Tier 4.
- `kind="ee"` over multi-member ensembles (R8, DV-08); chirality assignment of mirror-image TS
  conformers.
- Carry-forward (b): the v0.5.0 `reported.gated_on` text nit — TJ's call, outside this diff.
- (Moved in scope by replan 4, R29:) the flexible alkyl-series E2E, slice 14.

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority |
|---|---|---|---|
| US-001 | As a builder, I want the v0.6.0 starter unpacked as reference so that plan-vs-zip mismatches are logged, not followed. | Per-file sha256 equal to the zip; `.ruff.toml` `exclude = ["*"]`; DV-01…DV-09 open; no `PRDs/` change. | P0 |
| US-002 | As a graph author, I want to label nodes with a pathway and declare a typed pruning rule so that competing branches can be compared and pruned. | `ReactionNode.pathway: str \| None = None`; `PathwayPruningRule`; every existing YAML/JSON loads; round-trip; strict models; rule references validated. | P0 |
| US-003 | As a user, I want an engine crash in one TS search recorded, not raised, so that an ensemble reports everything else. | G3. | P0 |
| US-004 | As a chemist, I want ΔΔG‡, the ratio and the selectivity % from competing pathways. | G1. Keys `ddG_dagger_kcal_mol`, `signed_ddG_dagger_kcal_mol`, `ratio`, `selectivity_percent`, `kind`, `major_pathway`, `temperature_k`, `per_pathway`. | P0 |
| US-005 | As a chemist, I want each pathway's TS conformers Boltzmann-summed (TJ Q1 B). | G_p = −RT ln Σ g_i exp(−G_i/RT) over the summed members (log-sum-exp); weights sum to 1 within 1e-12; order-free; members outside the 3.0 kcal/mol window recorded, not summed. | P0 |
| US-006 | As a user, I want minor-pathway downstream nodes pruned when ΔΔG‡ exceeds my threshold (TJ Q2 A). | G2. Decision record: rule id, pathways, signed and unsigned ΔΔG‡, threshold, pruned ids (sorted), reason. No library default. | P0 |
| US-007 | As a chemist, I want conformers sampled around a verified TS with its reactive core frozen and its face kept. | G4 sampler parts; every sample recorded with its source (`fragment_embed:<k>` / `perturb:<k>`), sha256 and face. | P0 |
| US-008 | As a chemist, I want each sample re-searched, validated, face-checked and deduplicated so that the ensemble holds only distinct verified TSs of the same reaction and diastereomer. | G4 runner parts; per-member recipe gates; face check (R1); dedup (R2); exclusions with reasons; pathway fails only if no member is valid; G7. | P0 |
| US-009 | As TJ, I want Tier 4's inputs transcribed and checked. | HF-1 checks as tests; header-G arithmetic +4.273 / +1.849 within 0.005; `SOURCES.md` rows with sha256 and SI page; byte-equal to resolve's transcription. | P0 |
| US-010 | As TJ, I want the unmapped endo/exo pair run per recipe with ensembles. | Seeds from Liu's TS1a_n/TS1a_x; G5; candidate lists every member, weight and exclusion; G7. | P0 |
| US-011 | As TJ, I want the mapped pair and the pruning check run per recipe. | TS1b_x seed grafted from TS1a_x (M1 lists, core `[1,2,3,5]`) then pre-relaxed; TS1b_n from the M1 fixture; G5, G6; forming-core RMSDs to Liu's TS1b_x/TS1b_n reported (ADR-0031 maps); G7. | P0 |
| US-012 | As TJ, I want an acceptance record and a Phase 3 gate before the verdict. | `ACCEPTANCE_RESULT.json` derived from the candidates and real test outcomes (suite counts and skips gated, `ETA_RXNCAT_ACCEPTANCE=1` recorded); Phase 3 row to TJ before slice 12; bump to 0.6.0 only on a pass. | P0 |

## 5. Technical Specifications

### Resolved trade-off log

| R | Finding / item | Sev | Decision | Resolution |
|---|---|---|---|---|
| R1 | F1: pinned core `[0..5]` omits C7 (C7/C8); endo and exo share forming bonds, so a sample can cross faces and enter the wrong sum | blocker | resolved | **Face check, gated on both engines, plus a sampler that cannot cross by construction.** `forming_bond_configuration(state, forming_bonds, bonds)` → one sign per forming bond (i, j): s(i, j) = sign V_i · sign V_j, where V_c = det[x_a − x_c, x_b − x_c, x_p − x_c], (a, b) the two lowest-index perceived-graph neighbours of c other than its partner p. It is the relative configuration across the forming bond: invariant under reflection and rigid motion, flipped between diastereomers. A member is summed only if its tuple equals its seed's (same atom order); otherwise it is excluded `face_mismatch`. Measured (HF-3): endo (+1, +1), exo (−1, −1) on Liu's four TSs; the red team's plane test fails (same side for endo and exo). The sampler anchors each fragment by its core atoms plus, when those are fewer than three or collinear, their heavy neighbours in that fragment — for Tier 4 the dienophile anchor is its whole ring — so ETKDG can never place the CH₂ on the other face (HF-5: 50/50). Any `face_mismatch` in a Tier 4 ensemble fails G5. Slices 05, 06; ADR-0042. |
| R2 | F2: "flagged, both kept" double-counts re-converged copies (RT ln k) | high | resolved | **Merge on shape and face only.** Two valid members are one if proper-rotation RMSD with H (perceived-graph automorphisms of the seed, `thermo._geometry.automorphisms` + `permuted_rmsds`, cap `max_automorphisms`) < `rmsd_dedup_angstrom` 0.125 **and** their face tuples are equal. The lower-G member is kept; each merge records `dG_kcal_mol` and `rmsd_angstrom`. A merge with \|ΔG\| > `flag_dG_kcal_mol` 0.05 (~24× the measured floor, HF-11) is flagged in `flagged_merges` but still merged. Never sum two members that share a shape. Dedup runs after P-RFO (the re-dedup lesson); pre-dedup runs on samples. Slice 06; ADR-0044. |
| R3 | F3: caching all `EngineError` freezes host failures and degrades ensembles silently | high | resolved | **Cache only `EngineRuntimeError`** (`engines/errors.py:41`) as `{"failed_reason": "engine_error", "message", "error_type"}` in the stage being run (`ts_opt` or `frequency`); `ScfConvergenceError` keeps its own row. **`EngineUnavailableError` and `EngineInputError` re-raise with no row** (host/input problems, never cached). In an ensemble an `engine_error` member is excluded with that reason; **any `engine_error` exclusion in a Tier 4 ensemble fails G5** (visible to TJ). Determinism of xtb crashes is unknown (v0.5.0 TS4a, one data point): caching keeps G7 honest, and the gate keeps a cached crash from passing. Docstring updated. Slice 03; ADR-0045. |
| R4 | F4: no pre-build UMA ΔΔG‡ measurement; ADR-0040 margin uncited | high | resolved (measured) | **Measured now (HF-7):** UMA unmapped +4.602 ∈ [2.3, 6.3], mapped +1.410 ∈ (0.5, 3.8]. **Rule:** Q3 A's window is the gate; a pre-build value outside it goes to TJ. ADR-0040's 1.0 kcal/mol margin is a v0.5.0 rule for absolute barriers; the mapped margin (0.91) is recorded and reported in the handoff, not treated as a miss. GFN2 (M4) +3.977 / +1.753 reproduces sign and > 0.5. No pre-build miss. |
| R5 | F5: pre-relaxation needs geomeTRIC; mapping/optimize marked read-only; no cache for pre-relax | medium | resolved | `run_ts_ensemble` takes an injected `Optimizer` (the E2E passes `GeometricOptimizer()`, `opt-geometric` extra, ADR-0023/0011); no module of the core, scorer, sampler or ensemble runner imports geomeTRIC (G8). The pre-relax cache wrapper lives in `orchestrator/ts_ensemble.py` (species_runner node): key = `build_stage_key(sample, StageConfig(kind="constrained_preopt", frozen_atom_indices=core, options=engine options + opt.* resolved + opt.name/version), engine identity)`. `mapping` and `optimize` stay read-only. Failures (`CoreDisplacementError`, `OptimizerError`, `engine_error`) are cached as failure rows. Slice 06. |
| R6 | F6: regression tolerances unassigned to quantities | medium | resolved | Endo seed vs promoted `tests/fixtures/v0.5.0/t3_ts1{a,b}_n.{xtb,uma}.json`, reading TJ's "A: 0.75 all" per quantity: **TS E** \|Δ\| ≤ 1e-5 Eh (both); **TS geometry** Horn RMSD ≤ 0.01 Å (both, identity map); **TS G** \|Δ\| ≤ 0.01 kcal/mol (GFN2) / 0.75 kcal/mol (UMA); **ΔG‡(1 M)** \|Δ\| ≤ 0.01 (GFN2) / 0.75 (UMA). All four gated. Measured (HF-9): 2e-12 / 2.9e-4 kcal/mol, so the E row binds first and the G rows guard the reactant side. Slices 09, 10. |
| R7 | F7: pruning semantics ambiguous | medium | resolved | `PathwayPruningRule(id, metric="ddG_dagger_kcal_mol", pathways=(a, b), threshold_kcal_mol > 0 required, prune="minor_pathway_priority_ge_2")`, listed in `ReactionGraph.pathway_pruning_rules`; `pathways` must name labels used by priority-1 TS nodes. Evaluated once after both pathways have ensembles. Prune the **computed** minor's nodes with `priority ≥ 2` **and** `pathway == minor`, iff ΔΔG‡ > threshold (strict). Never prune `pathway=None`. If either pathway has no summed member: no pruning, reason `no_valid_member:<pathway>`. Record `signed_ddG_dagger_kcal_mol` keyed `"<b>_vs_<a>"` = G_b − G_a with (a, b) in rule order. The free-form `PruningRule` is untouched. Slices 02, 07; ADR-0046. |
| R8 | F8: mirror-image TS conformers and degeneracy | medium | resolved | `score_selectivity` refuses `kind="ee"` when any pathway has more than one summed member (`SelectivityInputError`), DV-08; Tier 4 is `de`. Each `TSEnsembleMember` carries `degeneracy` (from `TransitionStateRecord.degeneracy`, 1 per ADR-0036) and the sum uses G_i − RT ln g_i (G1 tests g = 2). |
| R9 | F9: `ETA_RXNCAT_ACCEPTANCE=1` unnamed | medium | resolved | Every Tier 4 E2E and the verdict run with `ETA_RXNCAT_ACCEPTANCE=1` and (xtb) `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`, recorded in each proof; slice 11's record stores the environment and slice 12 refuses a record without `ETA_RXNCAT_ACCEPTANCE=1`. |
| R10 | F10: memory rule glossed | medium | resolved | Verbatim (run record, TJ's selection): "(3) Memory rule: swap full, both rigs build at once, NO overlapping heavy runs host-wide; clear seats between runs; recover stalled seats." Each (pair × recipe) is its own command behind its own blocking host check (`free -g` ≥ 9 G available and no other rig's pytest/eta python; the check exits non-zero and the run is a separate call; never echo-then-run), recorded with output. Wait rather than overlap (background wait, no foreground sleep). UMA runs one seat at a time (ADR-0008). Slices 09–12. |
| R11 | F11: which samples are re-searched | low | resolved | Order: seed first, then `fragment_embed:<k>` by embed index, then `perturb:<k>` by index, after pre-dedup (seed kept first; a sample within 0.125 Å of a kept one is dropped). The first `max_research` (default 10) non-seed samples are re-searched. Every option is keyed into the ensemble options and recorded. Slices 05, 06. |
| R12 | F12: window bounds and the mapped centre | low | resolved | Unmapped UMA [2.3, 6.3] inclusive; mapped UMA (0.5, 3.8] (> 0.5 strict, ≤ 3.8); both engines > 0.5 strict. Centres are TJ's +4.3 and +1.8; Liu's +4.273 / +1.849 recorded beside them. M3 closed (HF-2). |
| R13 | F13: "GFN2 4.86 vs M06-2X 4.79" mislabelled | low | resolved | It is ΔE at Liu's geometries. ΔΔG‡ at GFN2 TSs is +3.977 / +1.753 (HF-7); the mission quotes those. |
| R14 | F14: ADR-0037 stale and contradicted by Q-TJ4 A; ADR-0040/0036 uncited | low | resolved | Propose ADR-0047 superseding ADR-0037 with Q-TJ4 A's rule (GFN2 gates convergence, mode count and the identity core: overlap ≥ 0.50, in phase, KE ≥ 0.60; full identity incl. distance window reported). Cite ADR-0036, ADR-0040. |
| R15 | F15: `tests/fixtures/**` and `tests/candidate_outputs/v0.6.0/**` unowned; stale code-graph index | low | resolved | `tests/candidate_outputs/v0.6.0/**` enters `eta_rxncat_species_runner` through slice 09's `hacf_touches` (ensure-node). `tests/fixtures/**` stays unowned on purpose: no node writes it and TJ's promotions must not mark a node dirty; slices read it only. Every builder runs `hyper_codegraph.py index` (must print `index: ok`) as Task 1. |
| R16 | Draft P2 sampler (ETKDG + coordMap on the two-fragment TS) | — | rejected by measurement | HF-4. **Sampler:** per connected fragment of the seed's perceived graph, ETKDGv3 (`randomSeed`, `numThreads=1`) on the fragment alone with a coordMap on its anchor atoms (R1), Kabsch-placed on the seed by the anchor; plus `n_perturb` Cartesian perturbations of the non-core atoms (numpy `default_rng(seed)`, σ `perturb_sigma_angstrom`). In every sample the core coordinates are then set to the seed's exactly. Defaults (keyed): `n_embed` 10, `n_perturb` 10, `perturb_sigma_angstrom` 0.3, `pre_dedup_rmsd_angstrom` 0.125, `random_seed` 42. Slice 05; ADR-0043. |
| R17 | Draft P6 energy window | — | resolved | 3.0 kcal/mol, keyed `energy_window_kcal_mol`; members above are recorded `outside_window`, not summed (weight at 3.0 is 0.63 %, ≤ 0.004 kcal/mol on G_p). |
| R18 | Draft P7 ensemble size | — | resolved (M1/M2) | Tier 4: `n_embed` 10, `n_perturb` 10, `max_research` 10 per seed (seed + ≤ 10). Cost per ensemble GFN2 ~70–100 s; UMA ~100–145 s (one stall seen, HF-13); 4 ensembles × 2 recipes per full Tier 4 pass. Library defaults equal these. |
| R19 | Draft P8 failed members | — | resolved | Excluded and recorded (`ts_search_failed:<reason>`, `scf_convergence`, `engine_error`, `ts_validation_failed`, `gate_failed:<check>`, `face_mismatch`, `pre_relax_failed:<error>`, `outside_window`); the seed is always tried; a pathway fails only if no member is summed. In Tier 4 the acceptance record gates zero `engine_error` and zero `face_mismatch` (R1, R3); other exclusions are reported with counts by reason. |
| R20 | Draft "Reuse of v0.5.0" | — | resolved | Endo seeds re-searched in the Tier 4 store from v0.5.0's starts; gated regression per R6 (HF-9). Promoted fixtures are read, never written. |
| R21 | Draft M4 / G5 GFN2 gating | — | resolved (measured) | GFN2 gates endo-major and ΔΔG‡ > 0.5 on **both** pairs (HF-7); never a numeric window on GFN2. |
| R22 | Draft module homes | — | resolved | Sampler + face descriptor: `src/eta_rxncat/conformers/ts_sampler.py` (node `eta_rxncat_conformers`). Ensemble runner: `src/eta_rxncat/orchestrator/ts_ensemble.py`; scorer: `orchestrator/selectivity.py` (`score_selectivity`, `run_selectivity`) (node `eta_rxncat_species_runner`). Models: `src/eta_rxncat/core/selectivity_models.py` (node `eta_rxncat_core`). |
| R23 | Draft "Pruning: extend `PruningRule` or a new model" | — | resolved | New model beside it (R7). Reason: `PruningRule.parameters` is free-form and existing graphs (e.g. `tests/data/reaction_graphs/example_reaction_graph.yaml` `barrier_gate`) must keep loading unchanged; a typed model is evaluated, the free-form one stays inert. |
| R24 | Draft P9 "new stage kind or reuse" | — | resolved | **No new stage kind.** Pre-relaxation is keyed as the existing `constrained_preopt` (R5, its `frozen_atom_indices` = the core); search and frequency are `run_transition_state`'s `ts_opt`/`frequency`. Sampling is pure and deterministic (≤ 0.02 s per seed, HF-5) and is not cached: G7 checks byte-equal resampling instead. |
| R25 | HF-13: an injected pre-relax can stall past `maxiter` | — | resolved | Every Tier 4 E2E / acceptance / verdict command runs under `timeout 3600`; a timeout is a stop-and-report with the output (TJ Q3 amended: a failed run is a finding). `TSEnsembleMember`/`TSEnsembleExclusion` record `pre_relax_wall_time_s`; the candidate reports the maximum. No in-process watchdog in v0.6.0 (geomeTRIC runs in-process, ADR-0024). *Superseded in part by R28 (replan 3): slice 13 adds an in-process wall-time budget; `timeout 3600` stays.* |
| R26 | Replan 1 (slice 04, builder block at `808e50c`): G8 vs DV-03 — `import eta_rxncat.thermo.constants` loads RDKit because `thermo/__init__.py` imports `symmetry.py`/`masses.py` eagerly | — | resolved (lead ruling A) | Slice 04 makes `src/eta_rxncat/thermo/__init__.py`'s exports lazy (PEP 562 `__getattr__` + `TYPE_CHECKING` imports, `__all__` and every `from eta_rxncat.thermo import X` unchanged); the scorer uses the real `eta_rxncat.thermo.constants`. Not B (moving constants), never C/D. Blast radius of slice 04 gains `eta_rxncat_thermo` (already owns `src/eta_rxncat/thermo/**`; no ledger change). No thermo behaviour or constant changes. |
| R27 | Replan 2 (slice 04): slice 04 requires `ratio = inf` on float overflow, but slice 02's `SelectivityResult.ratio` is `Field(ge=1.0, allow_inf_nan=False)` and refuses it | — | resolved (lead ruling) | Slice 04 changes that one field to accept `+inf` (`allow_inf_nan=True`, `ge=1.0` kept, so NaN, `-inf` and < 1 are still refused; tested), plus its docstring line and a core model test. Slice 04's touches gain `src/eta_rxncat/core/selectivity_models.py` and `tests/unit/core/test_selectivity_models.py`; its blast radius gains `eta_rxncat_core` (ratio field only; no ledger change). No other core change. |
| R28 | Replan 3: HF-13 is recurrent (3 of 13 UMA TS1b_x(graft) runs; a stall would make the slice 11/12 verdict runs a coin flip). Measured as a live geomeTRIC-internal numpy loop between engine calls inside the ensemble pre-relax | — | resolved (lead ruling: measure, then bound or fix) | New slice 13 (OPR.0.6.0.13, before 11): `orchestrator/_deadline.py`, a watchdog thread raising `PreRelaxTimeout(BaseException)` into the calling thread via `PyThreadState_SetAsyncExc` after `pre_relax_budget_s` (default `PRE_RELAX_BUDGET_S = 600.0`, ~12× the healthy 49 s max), re-sent every 1 s, cleared on exit. `_PreRelax.run` excludes the member as `pre_relax_failed:PreRelaxTimeout` (fits the existing reason regex; no core change), records the wall time, caches the row with `budget_s`, and the ensemble continues. Budget not in the stage key. Not a cure: the cause is inside the black box. Optimizer stays in-process (ADR-0024 unchanged); new ADR-0048 PROPOSED. P-RFO and the E2E graft pre-relax are unguarded (no stall seen). Not N-consecutive-runs proof: the oracle is unit tests of the interrupt plus one UMA mapped run < 1300 s. Tier 4 G is unchanged by a timeout, since every member re-converges to the seed (HF-10). Blast radius: `eta_rxncat_species_runner` only (description 1967/2000; compress, no split). |
| R29 | Replan 4: TJ Q-RES1 = B, amended to an alkyl R-group series (verbatim in §2) | — | resolved (TJ) | New slice 14 (OPR.0.6.0.14, order 106: after 13, before 11). R = ethyl, n-propyl, n-butyl replaces H16 (the cyclopropene CH2 H anti to Cp) of TS1a_n through eta's `graft`. Fragments: 3-R-cyclopropene, ETKDGv3 seed 42 + MMFF, chain all-anti (the plain ETKDG n-propyl conformer clashes). The sp2 pair order is the lower-RMSD fit. Core-frozen pre-relax under `deadline(PRE_RELAX_BUDGET_S)` (TJ: the guard applies to the grafts too). Ensemble with the library defaults (R18) on GFN2 and UMA. Gates per R × recipe: no `failed_reason`, ≥ 2 distinct members (ethyl too: anti + a mirror-image gauche pair, measured 3), \|Σw − 1\| ≤ 1e-12, every face the seed's, zero `face_mismatch`/`engine_error`, a second pass with 0 rows / 0 calls / equal ensemble, and no `graft_pre_relax_timeout`. Reported only: members per R (non-decreasing expected, measured 3/4/5 on both engines), ΔG‡, the ensemble correction, ΔΔG‡ vs ethyl, and max pre-relax wall. Tests and inputs only, no `src/` change. Six candidates go to `tests/candidate_outputs/v0.6.0/`. One slice, about 25 min per recipe (within TJ's 1–2 slices and ~3× GPU TS searches). Blast radius: `eta_rxncat_species_runner` (tests/e2e only; no ledger change). |
| R30 | Replan 4: slice 11 was paused mid-build (C1 `1273070`) for slice 14 (lead sequencing option a) | — | resolved (lead) | Slice 11 resumes as a continuation with Start `ca983a8`; its range will contain slices 13–14's commits. Its repro runs at `1273070` stay valid because 14 changes no `src/` (14's requirement 5); a non-empty `src` diff voids them. Audit judges 11 on its own commits listed by sha in its PROOF (range minus 14's files). The record gains 14's six `flexible_ensemble` entries (gated as slice 14; regression `pending_promotion`; no repro bounds for 14). |

### Seed deviations (from the draft)
- Sampler: per-fragment ETKDGv3 + perturbation (R16), not ETKDG coordMap on the whole TS.
- Dedup: RMSD + face only; the 0.05 kcal/mol figure is a flag, not a keep-both rule (R2).
- `EngineError` → only `EngineRuntimeError` is cached (R3).
- Face check added (R1); `kind="ee"` refused on multi-member ensembles (R8); degeneracy in the sum.
- No new stage kind (R24); pre-relax keyed as `constrained_preopt`.
- Slice 08 lands resolve's measured inputs instead of measuring.
- Replan 1 (R26): slice 04 also makes `thermo/__init__.py` exports lazy.
- Replan 2 (R27): slice 04 also lets `SelectivityResult.ratio` hold `+inf`.
- Replan 3 (R28): new slice 13 (before 11) bounds the ensemble pre-relax by a wall-time budget; slice 11 depends on it.
- Replan 4 (R29, R30): new slice 14 (after 13, before 11) is the flexible alkyl-series E2E (TJ Q-RES1 B, amended); slice 11 depends on it and records its checks.

### Face check (normative; slices 05, 06)
- Input: a state, its forming bonds, its perceived bonds (`mapping.perceive_bonds`, which excludes
  forming bonds at TS distances). For each forming bond (i, j), each end c ∈ {i, j} with partner p
  must have ≥ 2 perceived neighbours other than p, else `FaceDescriptorError` (the check cannot be
  judged; the member is excluded `face_undetermined`). a, b = the two lowest-index such neighbours.
- Output: `tuple[int, ...]` of ±1 per forming bond in sorted forming-bond order; a zero volume
  (\|V\| < 1e-6 Å³) is `FaceDescriptorError`.
- Neighbours are taken from the **seed's** perceived graph for both seed and member (the member's
  covalent graph must equal the seed's, else `connectivity_changed` exclusion).

### Ensemble runner (normative; slice 06)
`run_ts_ensemble(seed: TSSpec, recipe: TSRecipe, store, *, optimizer: Optimizer, core_indices,
options: TSEnsembleOptions, gates: Callable[[TSRunResult], dict[str, bool]]) -> TSEnsemble`:
1. Seed: `run_transition_state(seed)`. If the seed fails its search or its gates, nothing is
   sampled and the pathway fails with the seed's reason: the seed anchors every face.
2. Sample (slice 05) from the seed's final TS; pre-dedup; take the first `max_research`.
3. Per sample: core-frozen pre-relax (cached `constrained_preopt`), then `run_transition_state`
   with the same forming bonds and recipe; apply `gates` (the recipe's member gates: GFN2 = A2 +
   identity core per Q-TJ4 A; UMA = A2 + full identity); connectivity equal to the seed's; face.
4. Dedup (R2), energy window (R17), Boltzmann weights with degeneracy over summed members,
   `G_pathway_hartree` by log-sum-exp.
5. Return members (index, source, sha256 of start, G, degeneracy, rmsd_to_seed, face, validation
   summary, weight), exclusions (index, source, reason), merges, flagged_merges, options, the
   per-stage metrics (calls, hits, rows).
No exception escapes for a member; `OptimizerInputError` / `TSValidationInputError` /
`EngineUnavailableError` / `EngineInputError` still raise (bad inputs, host problems).

### Selectivity (normative; slices 04, 07)
- `score_selectivity(pathways: Mapping[str, TSEnsemble], *, kind: Literal["ee","de","regio"],
  temperature_k: float) -> SelectivityResult`, pure; RT from `eta_rxncat.thermo` constants
  (ADR-0026). G_p in Eh → kcal/mol by `HARTREE_KCAL_MOL`. Two pathways: ΔΔG‡ = G_minor − G_major ≥ 0,
  r = exp(ΔΔG‡/RT), % = 100 (r − 1)/(r + 1). N > 2: each pathway's fraction (softmax of −G_p/RT),
  `ddG_dagger_kcal_mol` relative to the major. Refusals per G1. Every ensemble carries its
  `temperature_k`, `reactant_key` (sorted (SMILES, count) of the reactants) and recipe identity;
  mismatches are refused.
- `run_selectivity(graph, recipes, store, …)` evaluates each `PathwayPruningRule` once after every
  priority-1 pathway has its ensemble, then runs the unpruned priority ≥ 2 nodes through the species
  runner; pruned nodes get status `pruned` and zero engine calls. The decision record is part of the
  result and the candidate. The DAG scheduler stays at v0.8.0.

### Contracts (slice 02; `core/selectivity_models.py`, exported from `eta_rxncat.core`; `CoreModel`, units in names, no numpy)
- `ReactionNode.pathway: str | None = None` (pattern `^[A-Za-z][A-Za-z0-9_.-]*$`).
- `PathwayPruningRule` (R7); `ReactionGraph.pathway_pruning_rules: list[PathwayPruningRule] = []`
  (ids unique across both rule lists; `pathways` must be labels present on priority-1 nodes).
- `TSEnsembleOptions` (R16–R18 defaults, plus `rmsd_dedup_angstrom` 0.125, `flag_dG_kcal_mol` 0.05,
  `max_automorphisms` 100000; all keyed and recorded).
- `TSEnsembleMember`, `TSEnsembleExclusion`, `TSEnsembleMerge`, `TSEnsemble` (`pathway`,
  `temperature_k`, `reactant_key`, `recipe_identity`, `members`, `excluded`, `merges`,
  `flagged_merges`, `options`, `G_pathway_hartree | None`, `failed_reason | None`). Weights sum to 1
  within 1e-12 when members exist (validator).
- `SelectivityResult` (US-004 keys, `per_pathway{G_pathway_hartree, n_members, n_excluded,
  fraction}`, `pruning: PruningDecision | None`).
- `run_transition_state`: signature unchanged; new `failed_reason` value `"engine_error"`.

### Starter discrepancies (DV rows for `docs/prd/v0.6.0/DISCREPANCIES.md`, slice 01)
- DV-01 / PD-010: plan "% ee / regioselectivity"; zip adds "*(Done when unit tests verify
  selectivity math and branch pruning.)*".
- DV-02: starter `core.reaction_graph.PruningRule(rule_id, metric, reference_node_id,
  target_node_id, operator, threshold, on_fail)` vs eta `core.graph.PruningRule(id, description,
  parameters)` + new `PathwayPruningRule` (R7, R23).
- DV-03: starter's own constants and exponent clamp at 500 vs `eta_rxncat.thermo` constants and
  log-sum-exp, no clamp.
- DV-04: starter compares two TSs; plan "Boltzmann-weighted"; TJ Q1 B ensembles.
- DV-05: starter's global `skip_remaining_nodes` vs per-pathway pruning (TJ Q2 A).
- DV-06: TJ's Tier 4 YAMLs vs schema 1; `[0,2,3,4]` → `[1,2,3,5]`; `P1a_n` → `P1b_x` (Q-E4);
  "% ee" reported as % de.
- DV-07: starter has no TS conformer search (added per TJ Q1 B).
- DV-08: `kind="ee"` refused over multi-member ensembles (R8).
- DV-09: draft sampler (ETKDG coordMap over the two-fragment TS) replaced by per-fragment
  embedding + perturbation (R16, HF-4).

### Blast radius
`python3 .agents/scripts/hyper_ledger.py impact --nodes eta_rxncat_species_runner,eta_rxncat_core,eta_rxncat_conformers`
→ the draft's nine nodes (cli, conformers, core, engines, mapping, optimize, species_runner, store,
thermo). **Written:** `eta_rxncat_core` (02), `eta_rxncat_species_runner` (03, 04, 06, 07, 08–11),
`eta_rxncat_conformers` (05), `eta_rxncat_scaffold` (01, 12), `eta_rxncat_thermo` (04, `thermo/__init__.py` import mechanics only, R26), `eta_rxncat_core` also in 04 (`SelectivityResult.ratio` accepts `+inf`, R27), `eta_rxncat_species_runner` also in 13 (`orchestrator/_deadline.py` + `ts_ensemble.py` pre-relax budget, R28) and 14 (tests/e2e flexible E2E + inputs only, R29). **Read only:** thermo (otherwise), mapping
(graft, `relax_constrained_core`, `perceive_bonds`, `core_rmsd_angstrom`), optimize (P-RFO,
`GeometricOptimizer` via injection), engines, store. No new node.

### Execution checklist (build order; the lead's work queue)
01 starter + DV rows · 02 core contracts · 03 EngineError · 04 scorer · 05 TS sampler + face ·
06 TS ensemble runner · 07 selectivity runner + pruning · 08 Tier 4 inputs · 09 unmapped E2E ·
10 mapped E2E + pruning · 13 HF-13 pre-relax guard (R28) · 11 acceptance record → **TJ Phase 3** →
12 verdict + 0.6.0 bump. Replan 4 (R29) inserts 14 flexible-ensemble E2E after 13, before 11.

### Dependencies
No new runtime dependency. RDKit (already the conformer engine) and numpy for the sampler; the
`opt-geometric` extra for the ensemble's pre-relaxation, injected, as in v0.4.0/v0.5.0 E2E.

## 6. Negative Constraints
- **DO NOT** edit `PRDs/`, `spec/compiled/architecture.yml` (scripts only), `spec/archive/` or
  `tests/fixtures/` (TJ promotes); never read `spec/archive/` or `tests/candidate_outputs/`.
- **DO NOT** rewrite the v0.5.0 promoted fixtures; compare against them only.
- **DO NOT** move core atoms during sampling or pre-relaxation; **DO NOT** hold the core with a
  dihedral constraint (ADR-0032).
- **DO NOT** sum a member that fails its recipe's gates, changes connectivity, or differs from its
  seed's face; **DO NOT** drop an excluded member silently.
- **DO NOT** sum two members that share a shape (R2), whatever their ΔG.
- **DO NOT** cache `EngineUnavailableError` or `EngineInputError`.
- **DO NOT** use RDKit `coordMap` across disconnected fragments (HF-4).
- **DO NOT** import or vendor `ase`, `sella` or geomeTRIC in core, the scorer, the sampler or the
  ensemble runner; geomeTRIC arrives only as an injected `Optimizer`. **DO NOT** read any
  TS-optimizer or conformer-search source (clean room). **DO NOT** use the starter's code.
- **DO NOT** put a default pruning threshold in the library; **DO NOT** prune `pathway=None` nodes.
- **DO NOT** gate GFN2 on a numeric ΔΔG‡ window. **DO NOT** loosen a window after a run; a miss is a
  stop-and-report to TJ.
- **DO NOT** run a GPU or E2E command without the blocking host check in a separate call; never
  echo-then-run; never overlap heavy runs (R10).
- **DO NOT** compare TSs across recipes, model hashes, temperatures or reactant sets.
- **DO NOT** open Eta_Scripts or nMap source. **DO NOT** push, tag or promote. **DO NOT** add a
  co-author trailer.

## 7. Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Tier 4 ensembles are one member (measured, HF-10), so the sum is the identity in the E2E | Slice 14's alkyl series (3/4/5 members, HF-14) exercises the sum end to end; G1/G4 prove the sum, weights, degeneracy and dedup on multi-member stubs; Q-RES1 to TJ (recommend a mechanics-only flexible E2E) |
| Diastereomer contamination (F1) | Face check gated on both engines; anchored sampler cannot cross (HF-5); unit test with a constructed crossover |
| Duplicate double count (F2) | Merge on RMSD + face; noise floor 0.0021 kcal/mol (HF-11); flags at 0.05 |
| Asymmetric exclusions from host failures (F3) | Unavailable/Input never cached; any `engine_error` exclusion fails G5 |
| Mapped ΔΔG‡ near the 1.5 pruning threshold (GFN2 1.753, UMA 1.410) | G6 accepts either branch against the measured value; both branches unit-tested |
| UMA mapped ΔΔG‡ 0.91 above the 0.5 floor | Inside TJ's window; recorded (R4); a run below 0.5 is a stop-and-report |
| Injected pre-relax stalls (HF-13: 3 of 13 UMA TS1b_x runs; a live geomeTRIC-internal loop) | Slice 13 bounds each pre-relax at 600 s and excludes it as `pre_relax_failed:PreRelaxTimeout` (R28); `timeout 3600` per command stays; per-member wall time recorded |
| Pre-relax core bound fails on a perturbed sample (1/44, HF-10) | Excluded `pre_relax_failed:CoreDisplacementError`, reported, not gated |
| ETKDG nondeterminism breaks G7 | `numThreads=1`, fixed seeds; byte-equal resampling test |
| Exo graft drifts from TS1b_x | Measured 0.046 Å pure graft, 0.022–0.027 Å final (HF-8); forming-core RMSD reported |
| SI transcription errors | HF-1 checks as tests; byte-equal re-transcription; TJ confirms at Phase 3 |

## 8. Success Metrics
- Unit: G1–G4 and G8 pass offline.
- E2E per recipe: both pairs pass G5 and G6; endo seeds reproduce v0.5.0 within R6; G7 all hits;
  no `engine_error` or `face_mismatch` exclusion; suite counts and skips match the record;
  `ETA_RXNCAT_ACCEPTANCE=1` in every proof.
- Phase 3: TJ promotes the Tier 4 candidates (ensembles, weights, exclusions) and confirms the
  TS1a_x, TS1b_x and P1b_x transcriptions.
- Verdict pass → version 0.6.0; README derived from the record; DV rows closed by audits.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.6.0.1 | slices/01-starter | Unpack the v0.6.0 starter zip byte-identical under docs/prd/v0.6.0/ as reference only, gate it off from ruff, and open the DV register with DV-01..DV-09. |
| OPR.0.6.0.2 | slices/02-core-contracts | Add ReactionNode.pathway, a typed evaluable PathwayPruningRule beside the inert PruningRule, and the TS-ensemble and selectivity result models, all additive. |
| OPR.0.6.0.3 | slices/03-engine-error | Make run_transition_state cache an EngineRuntimeError as failed_reason engine_error while EngineUnavailableError and EngineInputError still raise uncached. |
| OPR.0.6.0.4 | slices/04-scorer | Add score_selectivity, a pure function giving Boltzmann-summed pathway G, ddG dagger, ratio and selectivity percent (ee, de or regio) in closed form with no heavy imports. |
| OPR.0.6.0.5 | slices/05-ts-sampler | Add a deterministic core-frozen TS conformer sampler (per-fragment ETKDGv3 anchored on the seed plus seeded non-core perturbation) and the relative-configuration face descriptor. |
| OPR.0.6.0.6 | slices/06-ts-ensemble | Add run_ts_ensemble: sample, cached core-frozen pre-relax, P-RFO re-search and validation, face and connectivity checks, dedup on shape and face, energy window and Boltzmann weights, with every exclusion recorded. |
| OPR.0.6.0.7 | slices/07-selectivity-runner | Add run_selectivity and evaluate_pathway_pruning: ensembles per priority-1 pathway, the score, each PathwayPruningRule evaluated once, and only unpruned priority-2 nodes run, every decision recorded. |
| OPR.0.6.0.8 | slices/08-tier4-inputs | Land TS1a_x, TS1b_x and P1b_x byte-equal to resolve's checked transcription, with SOURCES.md rows, the two provisional Tier 4 fixture YAMLs and offline input tests. |
| OPR.0.6.0.9 | slices/09-e2e-unmapped | Run the unmapped Cp + cyclopropene endo/exo pair with TS ensembles on GFN2 and UMA, gated per TJ Q3 A, and commit the candidates. |
| OPR.0.6.0.10 | slices/10-e2e-mapped-pruning | Run the mapped Cp + cyclobutene endo/exo pair (TS1b_x grafted from TS1a_x) with TS ensembles on GFN2 and UMA, check TJ's 1.5 kcal/mol pruning against the measured ddG dagger, and commit the candidates. |
| OPR.0.6.0.11 | slices/11-acceptance-record | Assemble the v0.6.0 acceptance record from real per-check outcomes with pending states for TJ, measure run-to-run reproducibility for the Phase 3 bounds, and derive the README claims. |
| OPR.0.6.0.12 | slices/12-acceptance-verdict | After TJ's Phase 3 promotion and bounds, run the verdict on both recipes against the promoted fixtures and bump the version to 0.6.0 only on pass. |
| OPR.0.6.0.13 | slices/13-hf13-pre-relax-guard | Bound each ensemble pre-relaxation by a wall-time budget so a stalled geomeTRIC pre-relax (HF-13) becomes a cached, recorded pre_relax_failed:PreRelaxTimeout exclusion and the ensemble continues. |
| OPR.0.6.0.14 | slices/14-flexible-ensemble-e2e | Graft an alkyl series (ethyl, n-propyl, n-butyl) onto TS1a_n, run guarded core-frozen pre-relax and the TS ensemble on GFN2 and UMA, and gate per R at least two distinct members, unit weights, the seed's face and an all-hit rerun, with ddG dagger reported only. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
