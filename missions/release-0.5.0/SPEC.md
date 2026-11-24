---
id: OPR.0.5.0
mission: release-0.5.0
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope mission create)"
created: "2026-11-24"
intent: "Add a clean-room P-RFO transition-state optimizer and an active-core imaginary-mode validator, and prove them with an activation-barrier E2E on TJ's Tier 3 cases (Human Fixture 3)."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0011, ADR-0019, ADR-0020, ADR-0021, ADR-0023, ADR-0026, ADR-0027, ADR-0028, ADR-0031, ADR-0032, ADR-0033, ADR-0034, ADR-0035, ADR-0036, ADR-0037, ADR-0038, ADR-0039, ADR-0040]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.5.0 — TS P-RFO Optimizer & Active-Core Frequency Validator (Human Fixture Tier 3)

## Intent

v0.5.0 is the fifth of ten versions. It turns v0.4.0's mapped TS *guess* into a verified
first-order saddle point and a free-energy barrier:
- a clean-room **partitioned-RFO (P-RFO) saddle search** in Cartesian coordinates
  (`eta_rxncat.optimize`), seeded with the engine's exact Hessian, refreshed with exact Hessians
  on a fixed cadence and Bofill-updated in between, with a trust radius and mode following;
- an **active-core TS validator** (`eta_rxncat.thermo`): exactly one imaginary mode, below a
  cutoff, localised on the active core, and moving the forming bonds;
- **TS thermochemistry** with that one mode excluded, and an **activation barrier** ΔG‡ at 1 M and
  1 atm (`eta_rxncat.orchestrator`);
- **Human Fixture 3 / TJ's Tier 3**: five TS searches (TS1a_n and N4 unmapped; TS1b_n mapped from
  v0.4.0's M1; TS3a unmapped and TS4a mapped from TS3a by two single grafts) on GFN2 (reported)
  and UMA (gated), committed as candidates for TJ's Phase 3.

Plan (`PRDs/Eta-RxnCat_Living_Master_Plan.md` l.45–47, authoritative per TJ Q1 "A"):
> `PR #10 (feat/ts-optimizer)`: Implement clean-room P-RFO saddle-point optimizer (seeded with
> MLIP/xTB Hessian + periodic exact Hessian refreshes) and active-core imaginary mode projection
> filter (1 negative frequency, >=50-60% active-atom kinetic energy contribution).
>
> `PR #11 (test/e2e-gs-ts-fixture)`: Run E2E validation against **Human Fixture 3** (GS + TS
> reaction map -> activation barrier with mapped substituent).

- **Base:** the mission commit on main (parent `0d2a8d3`). `0d2a8d3` is the v0.4.0 release
  `03ee452` (pushed, tagged `v0.4.0`) plus the local HACF v0.6.3 upgrade. The lead commits this
  mission on main, and that commit is Base. The builder cuts `feature/eta-rxncat-v0.5.0` from it.
- **Inputs compiled:**
  - `Draft_PRD.md`, sha256 `01338683927349e96952d48480fcb7946689ff765485777145a63d80de101337`;
  - `RedTeam_Report.md`, sha256 `2af6e18f1d5d091dcf602f716cc9c2925bc479b347c94b013b7c7adc6415a730`
    (F1–F22, Parts A–C);
  - resolve's pre-build measurement (TJ A4), §2 "Host facts" and `~/.hacf/eta-rxncat-hacf/evidence/v050-resolve-f6/`.

  The draft and the red-team report are archived, and a restore copy of both is in
  `spec/process/eta-rxncat-v0.5.0-drafts/`. This SPEC is self-contained.
- **Author:** the decisions are TJ's (Thomas J. L. Mustard Ph.D.), quoted verbatim. The design
  resolutions are spec-resolve's, each logged in §5 "Resolved trade-off log".

### TJ decisions (verbatim; binding)

| # | Question (row) | TJ, verbatim | Meaning here |
|---|---|---|---|
| A1 | How the TS search is built (`qitem-20261124022519-fc0c0dfa7516da8a`) | "Q1. A" | Own clean-room P-RFO in **Cartesian** coordinates (rigid motions projected out), written only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52; Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1. MIT, numpy, base install, mode following. **No seat reads the source of any TS optimizer** (geomeTRIC, Sella, pysisyphus, Eta_Scripts). geomeTRIC's `--transition` is used **only as a black-box cross-check in acceptance**, never in the product path (mechanism: R5). No TRIC (PD-009). |
| A2 | Active-core filter numbers (`qitem-20261124022519-e5ab60e19dea4068`) | "Q2.  A" | Exactly **one** mode below **−20 cm⁻¹** (thermo's `imag_tol_cm1`); that mode below **−50 cm⁻¹**; mass-weighted active-core KE fraction **≥ 0.60**. All keyed. |
| A3 | Which T3 cases, who transcribes (`qitem-20261124022519-4551a749dbc997df`) | "Q3. A" | **All four** T3 fixtures (five TS searches). The team transcribes TS3a, TS4a, cyclobutenone and TS N4 from the attached SIs (Liu 2013, Paton 2011), with checks and `SOURCES.md`; TJ confirms them at Phase 3 with the candidates. Dual −CF₃ = two single grafts. |
| A4 | ΔG‡ windows (`qitem-20261124022519-cca036eafbb291c2`) | "Q4. A" | UMA-gated windows on eta's **1 M** ΔG‡: TS1b_n **[20, 34]** (TJ's, read at 1 M as relayed); TS1a_n **[10.7, 24.7]**; N4 **[15.6, 29.6]**; TS4a **[0.7, 14.7]**; TS3a **[10.0, 24.0]**. Resolve measures UMA at the literature geometries **before the build**; a case headed outside goes to TJ first (rule R6; result: all five go). GFN2 reported only. |
| Q-TJ1 | A literature TS misses A2 at the pre-build check (operator row `qitem-20261124031648-7ab9cad4f3d919ba`) | "A / A / A" (first) | **A:** the case goes back to TJ before the build, with the measured numbers (as A4). Measured: no case misses (R6). |
| Q-TJ2 | ΔG‡ symmetry convention (same row) | "A / A / A" (second) | **A:** σ from the geometry for reactants and the TS; **no** enantiomeric-TS degeneracy (TS g = 1). Matches how the Gaussian references were computed (R1). |
| Q-TJ3 | What is pass/fail on GFN2 (same row) | "A / A / A" (third) | **A:** on GFN2, convergence plus exactly one imaginary mode below the cutoff are **gated**; KE fraction, TS identity (R3, which replaces connectivity) and ΔG‡ are **reported** (R4). |

TJ's answer to Q-TJ1–3 was relayed by the advisor at 03:22Z as `'A / A / A'` (resolution of row
`qitem-20261124031648-7ab9cad4f3d919ba`; lead relay to resolve at 03:23Z).

Standing TJ decisions that apply:
- **Licence** (11-22 14:57Z, verbatim): "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." (14:59Z): "It's fine that the engine MACE pulls in ASE just not the
  core." P1 (11-23): "As long as the license does not taint the license of the entire repo."
- Q1 "A" (`PRDs/` plan authoritative); Q2 "B" (starter reference only, per-version
  `DISCREPANCIES.md`); Q3 amended: "Build, install, and run these autonomously as to move on to the
  next step/question."
- v0.3.0 R1 "R1. A": candidates are committed on the branch; only TJ promotes them (ADR-0027).
- **Clean room** (v0.4.0 Q1, excerpt): "There is some ownership by the university, my advisor and
  co-authors. They are copyrighted in the code, and that is why I'd like to build this clean room
  approach". No seat opens, clones, fetches or searches Eta_Scripts or nMAP (GitHub or
  `~/PROJECTS/cleanroom-nmap`; only its `TRANSFER_LOG.md` may be read).
- Q-E1 "Q1. A" (T3 → v0.5.0); Q-E3 "Q3. B, but these may need updating as we define the YAML/JSON
  format." (every fixture YAML is provisional); Q-E4 "Q4. A but the files attached can be used as
  reference." (forming carbons of TS1a_n `[1, 2, 3, 5]`); Q-E5 "Q5. C, if it turns out MACE, UMA,
  or OMol25 are needed then they should become standard." (windows gate UMA only).
- v0.4.0 settled: "A double graft is two single grafts"; core frozen via `frozen_atom_indices`,
  never a dihedral constraint (ADR-0032; R26 bound 1e-6 Å).
- Author "Thomas J. L. Mustard Ph.D." everywhere. Never push. `PRDs/` untouched. Commits end with
  the two footer lines `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
  `.agents/hacf-manifest.json` at commit time.

## 1. Introduction & Goals

**Problem.** v0.4.0 builds a mapped TS guess (M1: cyclobutene grafted onto Liu's endo TS1a_n,
core-frozen pre-relaxed on xtb and UMA), but nothing turns a guess into a saddle point. The repo
has only a minimiser (`GeometricOptimizer` behind `Optimizer.minimize`), and the species path
treats any imaginary mode as a failure (`check_ground_state` → `NotAMinimumError`, then a push
and a re-minimisation). There is no activation barrier anywhere in eta, so the plan's Hypothesis 1
("reliable TS initial guesses via quaternion/Kabsch alignment + constrained-core MLIP/xTB
relaxation prior to saddle-point optimization") cannot be tested.

**Solution.**
1. `optimize/ts_base.py`: a `TransitionStateOptimizer` ABC, separate from `Optimizer` (R12).
   `optimize/prfo.py`: `PRFOOptimizer`, Cartesian P-RFO with an unweighted rigid-motion
   projector (R7), exact-Hessian seed and refresh, Bofill updates, trust radius (R14), mode
   following with the initial mode chosen by overlap with the forming bonds (R2).
2. `thermo/ts.py`: `validate_transition_state` (A2 plus the TS identity check, R3) and
   `ts_thermochemistry` (one mode excluded; σ from the perceived graph of the geometry; R1).
3. `orchestrator/ts.py`: `run_transition_state`, which searches, computes the final Hessian in the
   frequency stage, validates, runs TS thermo and caches every stage under the new stage kind
   `ts_opt` (R10), failures included. `orchestrator/barrier.py`: `BarrierSpec` and
   `activation_free_energy` (R1).
4. Tier 3 inputs, five E2E searches per recipe, a black-box geomeTRIC cross-check (R5), the
   acceptance record, TJ's Phase 3, the verdict and the 0.5.0 bump.

**Audience.** TJ, as user and Phase 3 reviewer. The build seats. v0.6.0 (selectivity ΔΔG‡ from two
TSs on this path), v0.8.0 (orchestrator `optimize_ts` stages, multi-level Hessian seeding), v0.9.0
(topology audit as a library feature; the YAML suite re-run).

**Goals (measurable):**
- **G1.** On analytic model surfaces with a known first-order saddle (tier D: non-diagonal,
  rotated-frame Hessians, **unequal masses** H/C/O, starts where the lowest Hessian mode is not
  the reaction mode), `PRFOOptimizer.find_saddle` converges under §5 "P-RFO" criteria to the
  known saddle within 1e-4 Bohr and ends with exactly one negative eigenvalue of the projected
  exact Hessian.
- **G2.** `validate_transition_state` returns every number it used under unit-suffixed keys; the
  active-core KE fraction equals an independent mass-weighted computation in the test file within
  1e-12; every refusal and reason in §5 "Validator" has a test.
- **G3.** Importing `eta_rxncat.optimize`, `eta_rxncat.optimize.prfo`, `eta_rxncat.optimize.ts_base`
  loads no `geometric`, `torch`, `pyscf`, `fairchem` or `rdkit`; `eta_rxncat.core` still loads no
  numpy or RDKit.
- **G4.** Per Tier 3 search (TS1a_n, TS1b_n, TS3a, TS4a, N4) and recipe (xtb GFN2 CPU; UMA
  `uma-s-1p2p1` CUDA): the search converges and the TS has exactly one mode below −20 cm⁻¹, below
  −50 cm⁻¹ (**gated on both recipes**, Q-TJ3 A). On **UMA** also gated: active-core KE fraction
  ≥ 0.60, the TS identity check (R3) and ΔG‡(1 M) inside the A4 window; the ordering
  ΔG‡(TS4a) < ΔG‡(TS3a). On **GFN2** those are reported.
- **G5.** Mapped cases (TS1b_n, TS4a): forming-core RMSD to the literature TS under the stated-rule
  map is **reported** (not gated; v0.4.0 gates the guess).
- **G6.** A second run of every TS E2E in the same store: 100% cache hits on `ts_opt` and
  `frequency`.

## 2. Confidence Mandate

**Score: 9/10.** Every red-team finding has a decision (§5), TJ answered A1–A4 and Q-TJ1–3, and
resolve ran the pre-build measurement TJ asked for (A4) on both engines: every case is inside its
window and passes A2 at the literature geometry, with the selection and identity rules measured
rather than guessed (host facts below). The questions that would reach 10 cannot be answered on
paper; each is a stop-and-report, never a loosened bound:
- whether P-RFO on **GFN2** keeps a saddle for TS4a and TS3a, where GFN2 puts the literature TS
  **below** the reactants (ΔE‡ −16.4 and −5.9 kcal/mol, HF-3). Convergence plus one imaginary
  mode is gated on GFN2 (Q-TJ3 A), so a GFN2 miss there fails the verdict and goes to TJ with its
  output;
- where the UMA **stationary** TS lands against the window. The tightest margin is TS4a: 12.38
  (UMA thermo at Liu's geometry) or 13.38 (literature offset) against the upper bound 14.7;
- whether PySCF reproduces Liu's electronic energies for the four transcribed Liu structures
  (R9; slice 07).

### Host facts measured by resolve (2026-11-24, before the build; TJ A4)

Scratch under `TMPDIR`; scripts, logs and JSON are kept in
`~/.hacf/eta-rxncat-hacf/evidence/v050-resolve-f6/`. Literature geometries: TJ's committed XYZ
(TS1a_n, TS1b_n, Cp, cyclopropene, cyclobutene), tetrazines 3/4 from the builder's `XYZ_FILES`
(`ast.literal_eval`; never executed), and resolve's scratch transcription of TS3a, TS4a,
cyclobutenone and N4 (HF-1). Engines: eta's `XTBSubprocessEngine` (xtb 6.8.0, GFN2,
`ETA_RXNCAT_XTB` set) and `UMADirectEngine` (fairchem 2.26.0,
`uma-s-1p2p1@sha256:b2673b85…d5ce`, high precision, CUDA) with their finite-difference Hessians
(`fd_step_bohr` 0.005); modes from `thermo.modes.normal_modes`, masses from `thermo.masses`; G from
eta's quasi-RRHO `thermochemistry` at 298.15 K, 1 M, with σ from the perceived graph of each
geometry. Host checks before each run: ≥ 9 G available, no other rig's GPU or engine job; the
first mapped-start xtb run overlapped one HACF-rig `pytest -n 10` batch (single-threaded xtb, 9 G
available; recorded); every UMA run had a clear host.

| # | Fact | Value |
|---|---|---|
| HF-1 | Scratch transcriptions (sha256; formula; RDKit connectivity: two fragments, every H/F degree 1, no C below degree 3) | `TS3a.xyz` `6bf308b6…a1b4` C7H10N4 (Liu SI S15, 17 atoms left column + 4 atoms top of the right column); `TS4a.xyz` `b00f6a87…008c` C7H4F6N4 (S17); `cyclobutenone.xyz` `c489e512…f30c` C4H4O (Paton SI S3); `TS_N4.xyz` `cf7e4501…c46f` C9H10O (Paton S6; signs from the "-­‐" sequence); `3_dimethyltetrazine.xyz` `e42ed53a…662d` C4H6N4 and `4_bis_cf3_tetrazine.xyz` `174c23d2…2f74` C4N4F6 (builder). All pass. |
| HF-2 | Forming bonds at the literature TSs (inter-fragment heavy pairs, 1.9–2.7 Å) | TS1a_n (1,2) (3,5) 2.336/2.336; TS1b_n (1,2) (3,5) 2.241/2.241; TS3a (0,6) (3,7) 2.274/2.274; TS4a (0,6) (3,7) 2.378/2.378; N4 (1,9) (2,10) 2.166/2.309 Å. RDKit's C–C perception threshold is 1.976 Å, so each TS perceives as the reactants' graph (F3 confirmed). |
| HF-3 | ΔE‡ and ΔG‡(1 M) at the literature geometries (kcal/mol): GFN2 / UMA; "alt" = engine ΔE‡ + literature (ΔG‡ − ΔE‡) | TS1a_n ΔE 1.84 / 7.56, ΔG 13.02 / **19.38** (alt 20.23), window [10.7, 24.7]; TS1b_n 5.97 / 16.92, 18.24 / **29.05** (alt 29.88), [20, 34]; TS3a −5.87 / 7.47, 5.96 / **19.76** (alt 21.13), [10.0, 24.0]; TS4a −16.38 / 0.63, −5.60 / **12.38** (alt 13.38), [0.7, 14.7]; N4 0.35 / 13.92, 12.91 / **26.50** (no alt: Paton gives no electronic E), [15.6, 29.6]. **UMA inside every window, margin ≥ 1.32.** UMA ordering TS4a < TS3a holds (12.38 < 19.76); GFN2 too (−5.60 < 5.96). |
| HF-4 | A2 at the literature TSs: lowest ν (cm⁻¹), modes below −20, KE fraction on the R16 active set; GFN2 / UMA | TS1a_n −416.2 / −376.3, 1 / 1, 0.930 / 0.901; TS1b_n −509.2 / −527.0, 1 / 1, 0.950 / 0.947; TS3a −360.9 / −349.0, 1 / 1, 0.928 / 0.908; TS4a −232.8 / −238.2, 1 / 1, 0.839 / 0.810; N4 −471.4 / −517.9, 1 / 1, 0.951 / 0.951. Lowest real mode ≥ 36.7 cm⁻¹ (TS4a UMA). **Every case passes A2 on both engines.** Max \|F\| at the TS 0.006–0.021 Eh/Bohr. |
| HF-5 | F2 on the validator's normal modes: the highest active-core KE fraction among the *other* modes (GFN2 / UMA) | TS1a_n 0.887 (1511 cm⁻¹) / 0.827; TS1b_n 0.860 / 0.798; **TS3a 0.996 (472 cm⁻¹) / 0.991 (466)**; **TS4a 0.986 (652) / 0.982 (675)**; N4 0.860 / 0.792. At the mapped starts: M1 xtb **0.922 (1639 cm⁻¹)** beats the reaction mode's 0.906; TS4a start xtb **0.987 (672)** / UMA **0.986 (678)** beat 0.904 / 0.885. **"Largest active-core fraction" picks the wrong mode in 5 of 14 measured states.** |
| HF-6 | Overlap of the unit forming-bond stretch vector with modes (normal modes; GFN2 / UMA): reaction mode, best other mode | TS1a_n 0.805 / 0.723, ≤ 0.087; TS1b_n 0.810 / 0.786, ≤ 0.066; TS3a 0.833 / 0.792, ≤ 0.077; TS4a 0.801 / 0.812, ≤ **0.281**; N4 0.822 / 0.802, ≤ 0.056. Mapped starts: M1 0.759 / 0.745 vs ≤ 0.076; TS4a start 0.842 / 0.810 vs ≤ 0.194. Both forming bonds move in phase in every reaction mode. |
| HF-7 | Same overlap on the eigenvectors of the **unweighted projected Cartesian Hessian** (what P-RFO selects from), GFN2 | reaction mode 0.927, 0.953, 0.903, 0.844, 0.949 (TS1a_n, TS1b_n, TS3a, TS4a, N4); M1 start 0.883; TS4a start 0.889; best other mode ≤ **0.389** (TS4a). The reaction mode is also the lowest eigenvalue in all 7. |
| HF-8 | σ by the geometry route (graph automorphisms that a proper rotation undoes within 0.05 Å) | every TS σ = 1; Cp 2, cyclopropene 2, cyclobutene 2, tetrazine 3 2, tetrazine 4 2, cyclobutenone 1. |
| HF-9 | Literature references by header G arithmetic (kcal/mol; Liu and Paton are Gaussian, 1 atm; Paton's SI states no concentration correction) | TS1a_n 19.637 (1 M 17.742); TS1b_n 27.793 (25.899); TS3a 18.877 (16.983); TS4a 9.591 (7.697); N4 24.463 (22.569). Each equals TJ's quoted 19.6 / 27.8 / 18.9 / 9.6 / 24.5 to 0.05. The A4 windows are these 1 M values ± 7 (TS1b_n: TJ's [20, 34]). Paton's Cp G −193.937243 equals Liu's −193.937241 (2e-6 Eh), so the two SIs share a level and a standard state. |
| HF-10 | TS4a mapped guess by two single grafts on TS3a (R22 lists) | alignment RMSD 0.1462 / 0.1463 Å; no close contacts; min distance 1.079 Å; stated-rule map onto Liu's TS4a (576 isomorphisms, all distinct heavy maps give the same core RMSD) `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 17, 18, 19, 20, 14, 15, 16, 10, 11, 12]`; **forming-core [0, 3, 6, 7] RMSD 0.0599 Å**. Core-frozen pre-relaxation (`GeometricOptimizer`, maxiter 200): xtb 17 steps / 5.2 s, UMA 14 steps / 8.6 s; at the relaxed start xtb has two modes below −20 (−322.1 reaction, −72.5 a CF₃ rotor), UMA one (−377.6). |
| HF-11 | Same overlap on the projected Cartesian Hessian, **UMA** | reaction mode 0.897, 0.953, 0.888, 0.850, 0.951 (TS1a_n, TS1b_n, TS3a, TS4a, N4); M1 start 0.841; TS4a start 0.898; best other mode ≤ **0.338** (M1 start). The reaction mode is the lowest eigenvalue in all 7 (`cart_uma.json`). |
| HF-12 | Engine cost | GFN2 FD Hessian + energies for one TS and its two reactants 3.0–4.3 s; UMA 5.4–6.3 s (first case 19.9 s with model load). |

## 3. Scope

### In scope
1. **Starter (slice 01).** Unpack `PRDs/Eta-RxnCat-v0.5.0.zip` (sha256
   `ecfd9aa35b218b5def341fab83f477538f0b9719269fc30f1d9d53860072eda6`, 34 files) into
   `docs/prd/v0.5.0/` byte-identical (ADR-0007) with `.ruff.toml` `exclude = ["*"]`;
   `docs/prd/v0.5.0/DISCREPANCIES.md` (DV rows, §5); PD-009 `decided` in
   `docs/prd/PLAN_DISCREPANCIES.md`, no other hash changes.
2. **Core contracts (slice 02)**: `OptimizerIdentity.name` widened to `Literal["geometric",
   "prfo"]`; `StageKind` gains `"ts_opt"`; new `core/ts_models.py` (`FormingBond`, `TSStep`,
   `TSSearchResult`, `TSValidationOptions`, `TSValidation`, `TransitionStateRecord`).
   `OptimizationResult`, `ConformerRecord`, `ConformerEnsemble` unchanged.
3. **P-RFO (slice 03)**: `optimize/ts_base.py`, `optimize/prfo.py`, `TSSearchFailedError`.
4. **Validator and TS thermo (slice 04)**: `thermo/ts.py`; σ from a bond graph in
   `thermo/symmetry.py` (additive); `thermochemistry`'s minimum path unchanged.
5. **TS runner (slice 05)** and **barrier (slice 06)** in `orchestrator/`.
6. **Tier 3 inputs (slice 07)**: six transcribed/extracted XYZ files, `SOURCES.md` rows,
   five provisional YAMLs, tier-D checks, the PySCF energy-reproduction check of the Liu files.
7. **Tier 3 E2E (slices 08–10)**, per recipe, candidates committed: 08 the Diels–Alder pair
   (TS1a_n unmapped, TS1b_n mapped), 09 the tetrazine pair (TS3a unmapped, TS4a mapped by two
   grafts), 10 the cyclobutenone N4 (unmapped).
8. **geomeTRIC black-box cross-check (slice 11)**, acceptance only (R5).
9. **Acceptance record (slice 12)**, the **Phase 3 gate** (TJ), the **verdict and the 0.5.0 bump
   (slice 13)**, following v0.4.0's 07/08 pattern (R27 verdict gating).
10. Docs: README Features/Roadmap derived from the acceptance record. CHANGELOG is the scribe's.

### Out of scope (each would otherwise grow sideways)
- **TS conformer search**: one TS per case from one start; reactants get ensembles.
- **IRC**: TS identity is the validator's mode and identity checks (R3), not IRC.
- **Multi-level seeding** (xTB Hessian seeding DFT) and MLIP/xTB → DFT refinement: v0.8.0 (PR #15).
  In v0.5.0 the seed Hessian comes from the engine that runs the search; both v0.5.0 recipes are
  MLIP/xTB, which meets PR #10's "seeded with MLIP/xTB Hessian" (R24).
- **DFT TS searches** in acceptance. The optimizer works with any `Engine`; PySCF is used only for
  the energy-reproduction check (R9).
- **Covalent topology audit** as a library feature: v0.9.0 (PR #16). The zip's "covalent-graph
  topology guard" is a DV row.
- **`run_from_yaml`, `ReactionGraph` execution, YAML graph loading**: v0.8.0. The E2E calls the
  runners directly; the YAMLs are provisional (Q-E3).
- **Selectivity** (ΔΔG‡, endo/exo, pruning; Tier 4): v0.6.0. **Enumeration** / multi-site grafts
  in one call: v0.7.0.
- **TRIC** (TJ A1 "A": Cartesian; PD-009); geomeTRIC in the product path (A1).
- **Recovery ladder** beyond trust-radius reduction plus an exact-Hessian refresh on a rejected
  step (the plan's "damped/Cartesian/Lanczos fallback" line): a later sub-point release if a run
  shows the need (R14, R24).
- Promoting anything into `tests/fixtures/` (TJ only); editing `PRDs/` or the plan.
- Tier 4's `P1b_x`/`TS1b_x`; the Tier 5 / Cheong & Houk geometries.

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority | Slice |
|---|---|---|---|---|
| US-001 | As the builder, I want the v0.5.0 starter unpacked as reference with its discrepancies listed. | 34 files byte-identical with their sha256 list; `DISCREPANCIES.md` has DV-01…DV-09 (§5); PD-009 `decided` with A1/A2 text; `git diff Base -- docs/prd/PLAN_DISCREPANCIES.md` changes only PD-009's status/decision cells. | P0 | 01 |
| US-002 | As a library user, I want strict frozen TS contracts. | §5 "Contracts"; every validator has a passing and a rejecting test; `OptimizationResult` and v0.3.0/v0.4.0 cached payloads and promoted fixtures still validate; `"sella"` still rejected; `import eta_rxncat.core` loads no numpy or RDKit. | P0 | 02 |
| US-003 | As a library user, I want a converged first-order saddle from a guess, an engine and keyed options. | `PRFOOptimizer.find_saddle` per §5 "P-RFO"; G1 on every model surface; bad input raises `OptimizerInputError` before any engine call. | P0 | 03 |
| US-004 | As a library user, I want the search seeded with an exact Hessian and refreshed on a cadence. | Exact Hessian at step 0, every `hessian_refresh_steps` (5) accepted steps and after every rejected step; Bofill in between; `n_gradient_calls`, `n_hessian_calls`, `n_hessian_refreshes` recorded; a counting fake engine asserts the cadence exactly. | P0 | 03 |
| US-005 | As a library user, I want the reaction mode followed, not the lowest mode. | Initial mode = maximum overlap with the forming-bond stretch (R2), refused below 0.60; then maximum overlap with the previous followed mode; a model surface where the reaction mode is not the lowest converges to the right saddle; a case where it is the lowest also passes. | P0 | 03 |
| US-006 | As a reviewer, I want every TS checked for one active-core imaginary mode that moves the forming bonds. | `validate_transition_state` per §5 "Validator": count, cutoff, KE fraction, identity; fixed reason vocabulary; refusals for empty active set or forming bonds. | P0 | 04 |
| US-007 | As a library user, I want TS thermochemistry with the one mode excluded. | `ts_thermochemistry` refuses unless `mode_count_passed_bool`; ZPE/E_vib/S exclude exactly that mode; σ from the bond graph; equals `thermochemistry` on a minimum with the same σ (to 1e-12 Eh). | P0 | 04 |
| US-008 | As an operator, I want every TS stage cached and resumable, failures included. | `run_transition_state` per §5 "TS runner"; second run 100% hits on `ts_opt` and `frequency`; failures cached `COMPLETED` with `failed_reason`; every reader checks it. | P1 | 05 |
| US-009 | As a chemist, I want ΔG‡ at 1 M and 1 atm from a TS and its reactants. | `activation_free_energy` per §5 "Barrier"; formula and charge conservation from symbols/SMILES; `dG_dagger_1M_kcal_mol − dG_dagger_1atm_kcal_mol = Δn·RT ln(cRT/p)` with Δn = 1 − Σ coeff. | P0 | 06 |
| US-010 | As TJ, I want the Tier 3 structures transcribed and checked before any E2E uses them. | Six XYZ files byte-equal to HF-1's sha256s (or a stop-and-report); `SOURCES.md` rows with DOI, SI page, E/H/G as printed, standard state; formula/connectivity/forming-bond checks; PySCF reproduces Liu's E for the four Liu files (R9); five provisional YAMLs. | P0 | 07 |
| US-011 | As TJ, I want the Diels–Alder barriers (TS1a_n unmapped; TS1b_n mapped from M1). | Per recipe: G4 gates; ΔG‡ windows (UMA) [10.7, 24.7] and [20, 34]; G5 reported; candidates committed. | P0 | 08 |
| US-012 | As TJ, I want the tetrazine barriers (TS3a unmapped; TS4a mapped by two grafts). | Per recipe: G4 gates; windows (UMA) [10.0, 24.0] and [0.7, 14.7]; ordering TS4a < TS3a (UMA gated, GFN2 reported); G5 for TS4a; candidates committed. | P0 | 09 |
| US-013 | As TJ, I want the cyclobutenone N4 barrier (unmapped). | Per recipe: G4 gates; window (UMA) [15.6, 29.6]; candidates committed. | P0 | 10 |
| US-014 | As a reviewer, I want each acceptance TS cross-checked against geomeTRIC's own TS search, run as a black box. | §5 "Cross-check" (R5): documented CLI only, subprocess, same start, same eta engine, same seed Hessian; per case × recipe ΔE, heavy-atom RMSD, ν and eta's validator verdict on geomeTRIC's TS recorded; reported, never gated except that each run was attempted and recorded. | P1 | 11 |
| US-015 | As TJ, I want an acceptance record and a verdict that gates on real outcomes. | `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json`; verdict `pass` only with zero `fail`/`pending_*`/missing checks, a clean default suite and commands with zero skips (R27 pattern); runs after TJ's promotion; bump to 0.5.0 only on `pass`. | P0 | 12, 13 |

## 5. Technical Specifications

### Resolved trade-off log

Vocabulary: **resolved** (the design changes so the risk is gone; the slice that carries it is
named), **resolved (TJ)** (TJ decided), **out of scope** (excluded, with the owner). No finding is
`accepted`, so no new human row is owed. "Fn" is the red-team id (Part A ledger; Part B items are
in R23). Every Part A finding F1–F22 has exactly one row.

Lore (all PROPOSED, `origin: agent`; TJ approves through `/hyper-lore-approve`): R1 → ADR-0036; R2 → ADR-0034; R3 → ADR-0035; R4 → ADR-0037; R5 → ADR-0039; R6 → ADR-0040; R7, R11, R12, R14, R24, R27 → ADR-0033; R10 → ADR-0038.

| ID | Finding | Sev | Disposition | Decision |
|---|---|---|---|---|
| R1 | F1: a TS has no SMILES, but σ, `ConformerRecord`, `ConformerEnsemble` and `ReactionSpec` need one | high | resolved (TJ Q-TJ2 A) | **Separate TS path; no v0.3.0 contract changes.** (a) σ of a TS (and only a TS) comes from its **perceived bond graph**: `thermo.symmetry.rotational_symmetry_number_from_bonds(state, bonds, analysis=…)` builds an RDKit graph from the state's symbols and the given bonds (all single, no implicit H; atom order = the state's), and counts automorphisms a proper rotation undoes within `sym_tol_angstrom` (the existing `automorphisms` + `permuted_rmsds`). It is the SMILES route's algorithm on a graph whose atom order is the geometry's, so for a minimum it gives the same σ (test). The runner perceives the bonds with `mapping.report.perceive_bonds` (HF-8: every TS σ = 1). (b) **TS degeneracy is 1** (TJ Q-TJ2, verbatim "A / A / A": "σ from the geometry for both reactants and the TS; no enantiomeric-TS degeneracy"); reactant ensembles keep v0.3.0's conformer degeneracy unchanged. (c) **New records**: `TSSearchResult` and `TransitionStateRecord` (core, slice 02); `BarrierSpec` + `activation_free_energy` (orchestrator, slice 06) with conservation from reactant SMILES vs the TS's symbols and charge. `OptimizationResult`, `ConformerRecord`, `ConformerEnsemble`, `ReactionSpec` and `reaction_free_energy` are untouched, so every v0.3.0/v0.4.0 cached row and promoted fixture still validates. Slices 02, 04, 05, 06. |
| R2 | F2: the "largest active-core fraction" initial-mode rule can pick a stiff mode | high | resolved | **Measured, and the architect's rule is rejected**: it picks the wrong mode in 5 of 14 states (HF-5), including both mapped starts. **Rule:** the TS search takes `forming_bonds` (pairs of atoms whose bond forms or breaks). Its unit forming-stretch vector s (Cartesian, Bohr: for each pair (i, j), −u on i and +u on j with u the unit i→j vector; summed; normalised) is projected into the rigid-motion complement (R7). The **initial followed mode** is the eigenvector of the projected Cartesian Hessian with the largest \|⟨v, s⟩\|. If that overlap is < `min_initial_overlap` **0.60**, the search stops with `TSSearchFailedError(reason="no_reaction_mode")` after the first Hessian. Measured on the projected Cartesian Hessian: reaction mode 0.841–0.953, best other ≤ 0.389 on both engines (HF-7, HF-11); on normal modes 0.723–0.842 vs ≤ 0.281 (HF-6), so 0.60 separates the populations on both. With `forming_bonds` empty (tier-D only), the initial mode is the lowest eigenvalue. Afterwards the followed mode is the eigenvector with the largest \|overlap\| with the previous followed mode (R14). Negative constraint N5. Slice 03. |
| R3 | F3: perceived connectivity cannot tell the right saddle from a wrong one | high | resolved | **Connectivity is reported, never the identity gate.** TS identity (`identity_passed_bool`) is three measured checks on the validator's imaginary mode and the TS geometry: (1) forming-stretch overlap of the imaginary normal mode ≥ `min_forming_stretch_overlap` **0.50** (measured reaction modes 0.723–0.842, best other 0.281; HF-6); (2) the two forming-bond stretch components `(d_j − d_i)·u_ij` have the **same sign** (both bonds shorten together; measured in every case); (3) each forming distance in [`forming_distance_min_angstrom` **1.90**, `forming_distance_max_angstrom` **2.90**] Å (measured 2.166–2.378, HF-2; the window is loose on purpose: a wrong saddle of the van der Waals complex fails (1), a product-side bond fails the lower bound). Perceived connectivity of the TS and of the reference TS (under the stated-rule map for mapped cases) is recorded per case as `connectivity_equal_bool`, never gated. The cross-check (R5) applies the same validator to geomeTRIC's TS. Gated on UMA, reported on GFN2 (R4). Slices 04, 08–11. |
| R4 | F4: GFN2 gating ambiguous | high | resolved (TJ Q-TJ3 A) | TJ, verbatim: "A / A / A". On **GFN2**: `converged` and `mode_count_passed_bool` (exactly one mode below −20 cm⁻¹ and it is below −50 cm⁻¹) are **gated**; `active_core_passed_bool`, `identity_passed_bool`, `connectivity_equal_bool`, ΔG‡ and the ordering are **reported**. On **UMA** all of them plus the A4 window and the TS4a < TS3a ordering are gated. Slices 08–10, 12. |
| R5 | F5: the geomeTRIC black-box cross-check has no workable mechanism | high | resolved | **Black box via the documented CLI only.** `geometric-optimize --help` (geomeTRIC 1.1.1, read as documentation; no source read) documents `--engine ase` with `--ase-class`/`--ase-kwargs`, `--transition yes`, and `--hessian file+last:<path>`. The cross-check runs **in a subprocess** (R2 isolation; never in the eta process) in `.venv-accept-uma` (geometric 1.1.1, ase 3.29.0, fairchem 2.26.0 present; measured): `geometric-optimize <start>.xyz --engine ase --ase-class eta_geometric_shim.EtaCalculator --ase-kwargs '<json: recipe>' --transition yes --hessian file+last:<seed>.txt --prefix <dir>/<case>`, where the seed is **eta's own exact Hessian at the same start** (the P-RFO seed) and the shim (`tests/e2e/eta_geometric_shim.py`, acceptance only) is an ASE `Calculator` that evaluates eta's engine for the recipe (xtb subprocess or UMA) and converts Eh/Bohr → eV/Å. Coordinate system: geomeTRIC's default. Recorded per case × recipe: exit code, wall time, ΔE (geomeTRIC TS − eta TS, kcal/mol), heavy-atom RMSD after Horn superposition (identity map: same start, same atom order), eta's `validate_transition_state` on geomeTRIC's final geometry with eta's frequency-stage Hessian. **Reported only**; the verdict needs every run attempted and recorded (a geomeTRIC non-convergence is recorded as `geometric_not_converged`, not a verdict failure). ASE is imported only in the shim under `tests/e2e/`, in an acceptance env, never in `src/` (licence policy: core stays MIT). The open "BSD 3-clause Non-AI" licence look stays with TJ (handoff). Slice 11. |
| R6 | F6: the pre-build UMA measurement has no decision rule and omits A2 | high | resolved (TJ Q-TJ1 A) | **Rule (go/no-go per case):** at the literature geometries on UMA, (a) the projected ΔG‡(1 M) = UMA ΔE‡ + UMA quasi-RRHO thermal correction (TS: imaginary mode excluded; σ from the geometry; 1 M) lies inside the A4 window with ≥ 1.0 kcal/mol margin, and for the Liu cases the alternative ΔE‡_UMA + (ΔG‡ − ΔE‡)_literature does too (Paton gives no electronic E, so N4 uses (a) only); and (b) the UMA FD Hessian at the literature TS satisfies A2 on the R16 active set. A miss on (a) or (b) sends the case to TJ before the build (A4; Q-TJ1 A). **Result: all five go** (HF-3, HF-4); GFN2 measured and reported only. Tightest: TS4a, 12.38 / 13.38 against 14.7. Nothing goes to TJ. Slice 07's byte-equal re-transcription (HF-1 sha256s) makes HF-3/HF-4 apply to the committed files. |
| R7 | F7: Cartesian projection with the mass-weighted rigid basis | medium | resolved | P-RFO works in **unweighted Cartesian** coordinates (Bohr). Its rigid basis is the three unit translations and the three infinitesimal rotations about the **geometric centroid** (`e_a × r_k`), orthonormalised by SVD (rank 6; 5 if linear, which the TS search refuses), and the complement C (3N × (3N−6)). Gradient and Hessian are projected as Cᵀg and CᵀHC; steps are C·(complement step). **Convergence is tested on the unprojected gradient** (the true residual) and the rigid-gradient norm is recorded. `thermo.modes._rigid_basis` and `normal_modes` are never called inside the loop (N6). The followed mode and its overlaps live in this Cartesian space; the validator's KE fraction and overlap use the mass-weighted normal modes of `normal_modes` (different objects, both stated). Tier-D model surfaces carry unequal masses (H 1.008, C 12.011, O 15.999). Slice 03. |
| R8 | F8: references quoted, not re-derived; Paton's standard state unverified | medium | resolved | Every reference is derived by header G arithmetic from the transcribed SI energies and recorded with its standard state in `SOURCES.md` (HF-9): Liu and Paton are Gaussian 1 atm (Paton's SI states free energies at 298 K with no concentration correction; its Cp G equals Liu's to 2e-6 Eh). All five equal TJ's quoted numbers to 0.05 kcal/mol, so the A4 windows stand unchanged. A tier-D test recomputes each reference from the YAML/SOURCES energies and checks the window centre (± 7, TS1b_n excepted). Slice 07. |
| R9 | F9: the transcription check is weaker than an energy reproduction | medium | resolved | Slice 07 adds a PySCF single point (eta's `pyscf_gpu_cpu` engine, M06-2X/6-31G(d) with `cartesian_basis=True` per R30, `.venv-accept-gpu`, heavy-run gate) on the four Liu files (TS3a, TS4a, tetrazine 3, tetrazine 4) **and** on two of TJ's committed Liu files (TS1a_n, cyclopropene) as the measured control. **Bound:** \|E_pyscf − E_Liu\| ≤ 1e-4 Eh on every file; if a control misses it, that is stop-and-report (the bound is never raised; it is TJ's call). The Paton files (cyclobutenone, N4) have no electronic E; they rely on formula + connectivity + forming-bond + HF-4 stationarity (one imaginary mode on both engines, max \|F\| ≤ 0.011 Eh/Bohr) and TJ's Phase 3 confirmation. Reported and gated in slice 07 (a miss stops the build before any E2E). |
| R10 | F10: no stage kind for a TS search | medium | resolved | New `StageKind` value **`"ts_opt"`** (additive `Literal`; slice 02). TS search rows never use `geometry_opt`, so no reader that filters by kind mixes saddles with minima. The final Hessian reuses the existing `frequency` kind (keyed by geometry and engine only). `eta_rxncat_cli`'s graph validation accepts the new value by construction; no CLI change (the full suite proves it). Slices 02, 05. |
| R11 | F11: `OptimizerIdentity.version` for an in-repo P-RFO | medium | resolved | `PRFOOptimizer.identity = OptimizerIdentity(name="prfo", version="src-" + sha256(prfo.py source bytes)[:16])`, computed from `importlib.resources`/`__file__` bytes at first use. Any edit to `prfo.py` changes the key (a fixed build never reads an earlier build's cached failures); the 0.5.0 bump does not touch `prfo.py`, so the verdict's store keys equal the acceptance run's. Never `eta_rxncat.__version__` (N8). Every E2E uses a fresh store per run, then a second run in the same store for G6. Slices 03, 05, 08–13. |
| R12 | F12: a TS method on `Optimizer` would break mapping's tests | medium | resolved | **Separate ABC** `TransitionStateOptimizer` in `optimize/ts_base.py` (pure Python). `Optimizer` is unchanged, so `RecordingOptimizer`, `Toy` and `GeometricOptimizer` stay instantiable and `eta_rxncat_mapping` is untouched. A minimiser can never be passed as a TS search (typed). Slice 03. |
| R13 | F13: the TS path must never pass through the minimum handling | medium | resolved | Negative constraint N3: no TS ever goes through `check_ground_state`, `_frequency_and_thermo`, `_push`, `_dedup_after_push` or `run_species`. The TS runner reuses only `build_stage_key`, `_with_kind`, `CountingEngine`, `geometry_payload` and the `frequency`-stage payload shape. A test feeds a valid TS through `run_transition_state` with a spy on those four helpers and asserts zero calls. Slice 05. |
| R14 | F14: trust radius and step acceptance under-specified | medium | resolved | §5 "P-RFO" fixes every number, each keyed: trust start 0.10 Bohr, bounds [0.001, 0.30]; ratio ρ = ΔE_actual/ΔE_predicted with a floor guard (\|ΔE_pred\| < 1e-8 Eh counts as ρ = 1); grow ×2 when 0.75 ≤ ρ ≤ 1.25 and the step was ≥ 0.9·trust; shrink ×0.5 when ρ < 0.25 or ρ > 1.75; **reject** when ρ < 0 or ρ > 3: revert, trust ×0.25, exact Hessian refresh; `max_consecutive_rejections` 5 → `TSSearchFailedError("too_many_rejections")`; `max_steps` 100 → `"max_steps"`; mode lost after a refresh → `"mode_lost"`. Each failure is a tested path. Slice 03. |
| R15 | F15: timeouts have no mechanism | medium | resolved | Two layers, no new dependency: (1) a keyed `max_wall_time_s` on P-RFO (default 1800.0) checked before every engine call → `TSSearchFailedError("wall_time_exceeded")`; (2) every E2E command in a proof runs under coreutils `timeout 3600` (v0.4.0 R6); an expiry is stop-and-report with the output. Per-case cost measured (HF-12: one Hessian plus reactants 3–6 s), so a 100-step search with ≤ 25 Hessians fits well inside. Slices 03, 08–13. |
| R16 | F16: validator edge cases and per-case active sets | medium | resolved | `validate_transition_state` raises `TSValidationInputError` (a `ThermoInputError`) on an empty `active_atom_indices`, empty `forming_bonds`, an index out of range, or `options.imag_tol_cm1 != analysis.imag_tol_cm1`. `n_imaginary == 0` → reason `no_imaginary_mode`; `> 1` → `multiple_imaginary_modes`. **Active-set rule** (per case, fixed in the YAML): the forming-bond atoms plus every heavy atom on a 4-atom path between the two forming atoms of the diene fragment (both paths for a symmetric ring). TS1a_n, TS1b_n, M1 start `[0, 1, 2, 3, 4, 5]` (TJ's); TS3a and Liu's TS4a `[0, 1, 2, 3, 4, 5, 6, 7]` (tetrazine ring + the two dienophile carbons); the TS4a mapped start `[0..7]` (graft numbering, HF-10); N4 `[1, 2, 9, 10, 12, 13]`. Substituent carbons are **not** in the set (Q-TJ1 C not chosen). Measured KE fractions: HF-4. Slices 04, 07. |
| R17 | F17: FD Hessians called "exact"; UMA float32 noise unmeasured | medium | resolved | Records carry `hessian_method` (from `PotentialResult`) in `TSSearchResult` and in the `frequency` payload (already stored). UMA at the five literature TSs: exactly one mode below −20 cm⁻¹, lowest real mode ≥ 36.7 cm⁻¹ (HF-4). A spurious second mode at the converged UMA TS fails `mode_count_passed_bool` and is stop-and-report to TJ (Q-E5 "should become standard"), never a loosened count (N10). "Exact Hessian" in this SPEC means "the engine's own Hessian (analytic or its FD)", as opposed to a Bofill update. Slices 02, 03, 05. |
| R18 | F18: US-011 bundles three behaviours | low | resolved | Split into US-011 (DA pair), US-012 (tetrazine pair), US-013 (N4), each in its own slice (08, 09, 10), so one case's miss does not block the others' evidence. US order fixed. |
| R19 | F19: the copyleft constraint contradicts the MACE engine | low | resolved | N1 is scoped: no `ase`, `sella`, in-process `tblite`, `psi4` or other copyleft import in `src/eta_rxncat/{core,optimize,thermo,orchestrator,mapping}/`; engines behind the `Engine` interface are excepted as TJ allowed. ASE appears only in the acceptance shim under `tests/e2e/` (R5). |
| R20 | F20: step histories in compared payloads | low | resolved | `TSSearchResult.history` (one `TSStep` per accepted or rejected step) is stored and written to candidates under `history`, but every regression and candidate comparison excludes it (N11); compared: end-state quantities and counts inside measured bounds only. |
| R21 | F21: TS search constraint handling unstated | low | resolved | `find_saddle` has no frozen-atom or dihedral parameter, refuses an options key `constraints` with `OptimizerInputError`, and the mapped cases' core-frozen pre-relaxation (ADR-0032) happens before, through `relax_constrained_core`, never inside the search (N12). |
| R22 | F22: the TS4a graft's fragment source is not pinned | low | resolved | The fragment is `tests/e2e/data/e2e5/xyz/4_bis_cf3_tetrazine.xyz` (TJ's builder file, C4N4F6). **Graft 1** on TS3a: keep all but `[15, 16, 17]` (the H of methyl C10), delete `[15, 16, 17]`, pairs `[[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[10,10]]` ([template, fragment]), `fragment_delete [6, 7, 8, 9]`, `constrained_core [0, 3, 6, 7]`. **Graft 2** on graft 1's product: keep all but `[15, 16, 17]` (now the H of methyl C9), delete `[15, 16, 17]`, pairs `[[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[9,6]]`, `fragment_delete [10, 11, 12, 13]`, `constrained_core [0, 3, 6, 7]`. Then `relax_constrained_core` (core `[0, 3, 6, 7]`, `maxiter` 200). Measured: HF-10. Liu's TS4a is the reference only, never a donor (N13). |
| R23 | Red-team Part B items | — | resolved | (a) TS1b_n's [20, 34] is read **at 1 M, as TJ A4 "A" was relayed**. (b) G1's model atoms carry unequal masses (R7). (c) Risk rows added for σ/degeneracy, false convergence, FD noise and the wrong initial mode (§7). (d) US order fixed (R18). (e) "Another rig's heavy run is active" is observable only through `free -g` + `ps`; the seat rules name both. (f) Part B §6's eleven proposed constraints are adopted as N3–N13. (g) Each story has a timeout (R15). (h) Blast radius adds `mapping` as a dependency of the runner (bond perception; no change to mapping), `cli` by the `StageKind` widening (no change), and core's new module (§5 "Blast radius"). |
| R24 | Architect's choices the red team left standing | — | resolved | Kept: convergence on max\|g\| ≤ 4.5e-4, RMS g ≤ 3.0e-4 Eh/Bohr, max step ≤ 1.8e-3, RMS step ≤ 1.2e-3 Bohr, all four required, on the unprojected gradient (R7); `max_steps` 100; refresh every 5; G5 reported only; recovery = trust tightening + exact refresh only; same-engine seed meets "seeded with MLIP/xTB Hessian"; the ordering TS4a < TS3a gated on UMA, reported on GFN2 (measured on both, HF-3). Changed: the final Hessian is the `frequency` stage's, not returned by P-RFO (R27). |
| R25 | Draft "DO NOT start from lowest eigenvalue alone when active atoms are set" | — | resolved | Replaced by R2: with `forming_bonds` given, the overlap rule chooses; the lowest eigenvalue is used only without forming bonds (tier D). HF-7: the lowest eigenvalue would also have been right in all 7 measured states, but it is not the stated rule. |
| R26 | v0.3.0/v0.4.0 lessons carried | — | resolved | In every slice's seat rules: unit-suffixed keys (R54); no energy- or record-ordered lists in compared outputs (R55); one `gated_outcome` per test, `pending_*` fails under acceptance (R56); readers check `failed_reason` first (R50); re-dedup after a geometry change (reactant ensembles unchanged; one TS needs none); the candidate rule incl. `git show`; measured tolerances (R26 of v0.4.0); `ETA_RXNCAT_XTB` on every xtb command; timeouts (R15); heavy-run gate; the verdict gates on suite, commands and skips (v0.4.0 R27). |
| R27 | US-002 (draft) has P-RFO return the final exact Hessian | — | resolved | P-RFO returns no Hessian. The runner computes the final Hessian in the `frequency` stage (cached, keyed by geometry and engine) and validates with it, so the search and the validator are independent and a rerun of validation never re-runs the search. |
| R28 | Regression bounds for the verdict (not raised by the red team; needed by slice 13) | — | resolved (TJ at Phase 3) | Numeric bounds are TJ's (v0.3.0 R1 "R1. A"). Slice 12 measures run-to-run reproducibility per case × recipe and proposes TJ's v0.4.0 Q6 numbers (\|ΔE\| ≤ 1e-5 Eh, heavy-atom RMSD ≤ 0.01 Å) plus \|ΔΔG‡\| ≤ 0.01 kcal/mol if every measured difference is ≤ 1/10 of them, else 10× the measured maximum. The lead puts that block in TJ's Phase 3 row; slice 13 uses TJ's answer and cannot start without it. |
| R29 | Replan 1 (audit 03 handback `qitem-20261124051212-668b769f`): `bofill_update` raises a bare `ZeroDivisionError` when r = y − Hs = 0 (reproduced with H = diag(1, 2, 3), y = Hs), because the PSB-only test \|rᵀs\| < 1e-12‖r‖‖s‖ is false at 0 < 0; the same at s = 0; and the "mode lost on a Bofill Hessian → exact refresh → recover" path has no test | medium | resolved | From Bofill 1994: the update is the correction that makes H_new satisfy the secant condition H_new s = y; at r = 0 H already does and both correction terms vanish, so the update is the identity. If rᵀr == 0 or sᵀs == 0 (computed floats), `bofill_update` returns ½(H + Hᵀ) before any division; that step stays `hessian_source = "bofill"`. No tolerance changes, no exception is caught. Rejected: raising `TSSearchFailedError` (a satisfied secant condition is not a failure; it would fail good searches on near-quadratic surfaces). A new slice `14-bofill-guard` (node `eta_rxncat_optimize`, depends on .3 only) carries the guard, unit tests at r = 0 and s = 0, and a recovery test that forces the lost-mode branch with a patched update; it was placed as a new slice because no unfinished slice touches `eta_rxncat_optimize`. Slice 05 depends on .14, so it runs after 04 and before 05; it neither depends on nor blocks 04. |
| R30 | Replan 2 (slice 07 stop report `qitem-20261124064156-cb552525`): R9's control `TS1a_n` through eta's `pyscf_gpu_cpu` misses Liu by +3.385e-3 Eh (spherical 5D, 132 AOs); raw PySCF with Cartesian d (`mol.cart`, 140 AOs = +1 per d shell on 8 C) gives −6.3e-5 Eh, inside 1e-4 | medium | resolved | **Why Cartesian d is right here:** Liu's M06-2X/6-31G(d) energies are Gaussian's, and Gaussian's default for the Pople 6-31G family (6-31G(d), 6-31G(d,p), 6-31+G(d)) is 6D (Cartesian d), while 6-311G-family, Dunning and def2 bases default to 5D (spherical); a `6D`/`5D` keyword in the route overrides either. The difference is the basis definition (a different variational space), not numerical noise, so the fix belongs to the engine and R9's bound (TJ's) stays. **Limits for later tiers:** `cartesian_basis` is Cartesian for every l (PySCF `mol.cart`), so it reproduces Gaussian only where Gaussian also used Cartesian functions for every shell present: d-only Pople bases at 6D. Gaussian's default 6D **7F** (pure f) has no PySCF equivalent; a reference with f functions or with `5D` is compared spherical. Read the reference's route or AO count before choosing. **Design (lead's option A):** a keyed `cartesian_basis: bool` on `pyscf_gpu_cpu`, default False, written into the resolved stage **only when True** (removed when False, like the `ladder_small_basis` rewrite), so every existing PySCF resolved stage and key stays byte-identical; absent means spherical, permanently; `ENGINE_IMPL` stays 2. A narrow exception to ADR-0016's "every option always carries its value", proposed as ADR-0041. `init_guess="atom"` with it is refused on both devices (GPU4PySCF 1.9.2 asserts on it). Rejected: a plain always-keyed option (changes every PySCF key; old rows orphaned); an `ENGINE_IMPL` bump (the same invalidation for no gain); raw PySCF in slice 07 (R9 says eta's engine); widening the bound (TJ's; 2.1 kcal/mol is a definition). New slice `15-pyscf-cartesian-basis` (node `eta_rxncat_engines`, depends on .1) proves the keys unchanged against literals computed before the edit, GPU−CPU parity ≤ 1e-6 Eh, and re-measures the TS1a_n control; slice 07 depends on .15 and sets `cartesian_basis=True` in its R9 stage only. |
| R31 | Replan 3 (builder diagnostic `qitem-20261124100836-2bbff382`): with `cartesian_basis=True` (R30) at the default `grids_level=3`, TS4a misses R9 (ΔE = −1.080e-4 Eh) | medium | resolved | Measured through eta's `pyscf_gpu_cpu` (M06-2X, 6-31g*, `cartesian_basis=True`, `density_fit=False`, `conv_tol=1e-10`, cuda), ΔE = E_pyscf − E_Liu (Eh), TS1a_n / cyclopropene / TS3a / TS4a / tetrazine 3 / tetrazine 4: **level 3** −6.25e-5 / −8.5e-6 / −8.15e-5 / **−1.080e-4** / −7.48e-5 / −3.20e-5; **level 4** −2.49e-5 / −5.7e-6 / −2.68e-5 / −2.21e-5 / −8.25e-5 / −6.18e-5 (all ≤ 1e-4); level 5 (TS4a only) −2.78e-5. Reading: reproducing Gaussian references on the larger TSs needs a finer integration grid than eta's default; beyond level 4 the residual (a few 1e-5 Eh, every value negative) is not grid-limited (TS4a gains nothing at 5; the tetrazines move slightly the other way), so it is a residual method or implementation difference, not something to tune. **Decision:** slice 07's R9 stage sets `grids_level=4` (an existing keyed option; no code change) beside `cartesian_basis=True`. TJ's 1e-4 Eh bound is unchanged. **Known limit:** the tightest margin is tetrazine 3 at level 4 (−8.25e-5, margin 1.75e-5). A later tier checked against Gaussian M06-2X/6-31G(d) references uses R30 + R31's stage (`cartesian_basis=True`, `grids_level=4`) and measures before asserting. |

### Seed deviations

None yet (first compile). Replans add rows here.

### P-RFO (normative; slice 03)

`PRFOOptimizer(TransitionStateOptimizer)`, `find_saddle(state, engine, *, forming_bonds=(), options=None) -> TSSearchResult`.
- **Coordinates:** Cartesian, Bohr internally; the state's Å converted with `engines.units`.
  Rigid basis and complement per R7. Linear molecules and N < 3 are refused (`OptimizerInputError`).
- **Options** (`OPTIONS`, keyed through `resolved_options`, every one in the store key as
  `opt.<key>`): `max_steps` int 100; `hessian_refresh_steps` int 5; `trust_radius_bohr` float
  0.10; `trust_min_bohr` 0.001; `trust_max_bohr` 0.30; `max_consecutive_rejections` int 5;
  `min_initial_overlap` 0.60; `min_mode_overlap` 0.50; `max_gradient_hartree_per_bohr` 4.5e-4;
  `rms_gradient_hartree_per_bohr` 3.0e-4; `max_step_bohr` 1.8e-3; `rms_step_bohr` 1.2e-3;
  `max_wall_time_s` 1800.0; `ratio_floor_hartree` 1e-8. Unknown key, wrong type, a `constraints`
  key, `trust_min > trust_radius > trust_max` violated, or a non-positive number →
  `OptimizerInputError` before any engine call. `forming_bonds` indices out of range, duplicates
  or i == j → `OptimizerInputError`.
- **Loop.** Step 0: energy + gradient + exact Hessian (`engine.evaluate(state, forces=True,
  hessian=True)`). Each iteration: project; diagonalise CᵀHC (ascending); choose the followed
  mode (R2 at step 0; afterwards max \|overlap\| with the previous followed vector, mapped back to
  Cartesian); if that overlap < `min_mode_overlap` and the Hessian was a Bofill update, refresh
  exactly and choose again; if still below, fail `mode_lost`.
- **Step (Baker 1986).** In the complement eigenbasis (eigenvalues b_k, gradient components
  F_k = v_kᵀ(Cᵀg)), followed mode k = 1: λ_p = b_1/2 + ½·√(b_1² + 4F_1²); step_1 = −F_1/(b_1 −
  λ_p). Other modes: λ_n is the root of λ = Σ_{k≠1} F_k²/(λ − b_k) below min(0, b_2) (b_2 the
  lowest of the others), found by bracketed bisection/Newton to \|Δλ\| ≤ 1e-12 within 200
  iterations, else `mode_lost`; step_k = −F_k/(b_k − λ_n). Step Δx = C·V·step. If ‖Δx‖ > trust,
  scale to trust. Predicted ΔE = gᵀΔx + ½ΔxᵀHΔx (Cartesian, projected H).
- **Accept/reject, trust** per R14. **Bofill update** (Bofill 1994) between exact refreshes:
  with s = Δx, y = Δg, r = y − Hs: H_MS = H + rrᵀ/(rᵀs); H_PSB = H + (rsᵀ + srᵀ)/(sᵀs) −
  (rᵀs)ssᵀ/(sᵀs)²; φ = (rᵀs)²/((rᵀr)(sᵀs)); H_new = φ·H_MS + (1 − φ)·H_PSB, symmetrised; if
  \|rᵀs\| < 1e-12·‖r‖‖s‖ use PSB only; if rᵀr = 0 or sᵀs = 0, return H unchanged before any division (R29, slice 14). Refresh exactly at every `hessian_refresh_steps`-th accepted
  step and after every rejection.
- **Convergence:** all four criteria (R24) on the unprojected Cartesian gradient and the last
  accepted step, checked after each accepted step. Then return `TSSearchResult` (§5 "Contracts").
- **Failures:** `TSSearchFailedError(OptimizationFailedError)` with `reason ∈ {"max_steps",
  "too_many_rejections", "mode_lost", "no_reaction_mode", "wall_time_exceeded"}`, `steps` = the
  history's step labels, `last_energy_hartree`. `EngineError` propagates unchanged.
- **Clean room:** written from the three papers only (A1). No `assert` in `src/`.

### Validator and TS thermo (normative; slice 04)

`thermo/ts.py`:
- `validate_transition_state(state, hessian_hartree_per_bohr2, *, forming_bonds, options:
  TSValidationOptions | None = None, analysis: ThermoAnalysisOptions | None = None) -> TSValidation`.
  `active_atom_indices` come from `state`. Uses `normal_modes`. Imaginary modes: ν < −imag_tol.
  The **reaction mode** is the lowest-frequency mode. KE fraction of mode d (unit Cartesian
  displacement from `normal_modes`): Σ_{a∈active} m_a‖d_a‖² / Σ_a m_a‖d_a‖² (masses from
  `thermo.masses`). Overlap, in-phase and distances per R3 (Å for distances).
  - `mode_count_passed_bool` = (n_imaginary == 1 and ν_1 < `cutoff_cm1`);
  - `active_core_passed_bool` = (fraction ≥ `min_active_core_ke_fraction`), false if n_imaginary == 0;
  - `identity_passed_bool` = overlap, in-phase and distance checks all hold, false if n_imaginary == 0;
  - `passed_bool` = all three; `reasons` sorted, from the fixed vocabulary
    `{"active_core_fraction_below_threshold", "forming_bonds_out_of_phase",
    "forming_distance_out_of_window", "forming_overlap_below_threshold",
    "imaginary_above_cutoff", "multiple_imaginary_modes", "no_imaginary_mode"}`; empty iff `passed_bool`.
  - Refusals per R16.
- `ts_thermochemistry(state, hessian, electronic_energy_hartree, *, validation, bonds,
  energy_source, config=None, analysis=None) -> ThermoResult`: raises `ThermoInputError` unless
  `validation.mode_count_passed_bool` and the recomputed imaginary list has exactly one entry
  equal to `validation.imaginary_frequency_cm1` within 1e-6 cm⁻¹; σ from
  `rotational_symmetry_number_from_bonds`. Implementation: extract the body of `thermochemistry`
  into a private `_thermochemistry(state, hessian, e, sigma, …)`; `thermochemistry(smiles=…)`
  computes σ as today and calls it (its output is bitwise unchanged; the existing tests prove it).

### TS runner (normative; slice 05)

`orchestrator/ts.py`:
- `TSSpec` (frozen dataclass): `ts_id`, `start: MolecularState` (with `active_atom_indices`),
  `forming_bonds: tuple[tuple[int, int], ...]`, `reference: MolecularState | None` (for the
  reported connectivity), `reference_map: tuple[int, ...] | None` (start → reference indices).
- `TSRecipe`: `name`, `engine_stage`, `ts_optimizer: TransitionStateOptimizer`, `ts_options`,
  `thermo_config`, `analysis`, `validation_options`, `engine_runtime`.
- `run_transition_state(spec, recipe, store) -> TSRunResult`:
  1. `ts_opt` key = `build_stage_key(spec.start, stage(kind "ts_opt"; engine options + `opt.<k>`
     resolved + `opt.name`, `opt.version` + `opt.forming_bonds` as "i-j;…" sorted), engine identity)`.
     Hit with `failed_reason` → return the failure; hit → rebuild `TSSearchResult` from the
     payload; miss → `find_saddle`; `TSSearchFailedError` → save `{"failed_reason":
     "ts_search_failed:<reason>", "message": …}`; `ScfConvergenceError` → `"scf_convergence"`.
  2. `frequency` stage on the final geometry, same payload shape and key rule as the species runner.
  3. Bonds of the final TS by `mapping.report.perceive_bonds`; `validate_transition_state`.
  4. If `mode_count_passed_bool`: `ts_thermochemistry` with σ from those bonds → a
     `TransitionStateRecord`; else no thermo and `failed_reason = "ts_validation_failed"` with the
     validation kept.
  5. `TSRunResult`: `record | None`, `validation | None`, `failed_reason | None`,
     `connectivity_equal_bool | None`, per-stage metrics (`cache_hits`, `rows_created`,
     `engine_calls`, `wall_time_s`), keys.
- No call into the species runner's minimum path (R13, N3).

### Barrier (normative; slice 06)

`orchestrator/barrier.py`:
- `BarrierSpec` (pydantic, frozen, `extra="forbid"`): `reactants: tuple[tuple[str, PositiveInt],
  …]` (min 1), `ts_id: str`, `smiles: dict[str, str]` (reactants). Conservation against a TS
  state is checked by `activation_free_energy` (element counts of AddHs(SMILES) × coeff vs the TS
  symbols; Σ formal charge × coeff vs the TS charge; mismatch → `ValueError` naming both).
- `activation_free_energy(spec, ensembles, ts_record, config) -> BarrierEnergies`
  (`dE_dagger_kcal_mol`, `dH_dagger_kcal_mol`, `dG_dagger_1atm_kcal_mol`,
  `dG_dagger_1M_kcal_mol`, `delta_n`): reactants by v0.3.0's ensemble conventions (Boltzmann E
  and H; `ensemble_gibbs_hartree`); the TS by its single `ThermoResult` (degeneracy 1, Q-TJ2 A);
  Δn = 1 − Σ coeff; `dG_1atm = dG_1M − Δn·standard_state_shift_kcal_mol(config)` (the existing
  function). Temperatures must all equal `config.temperature_k`.

### Cross-check (slice 11)

Per R5. The shim is acceptance-only test code. `.venv-accept-uma` serves both recipes (eta's xtb
subprocess engine runs there too, with `ETA_RXNCAT_XTB`). Results go into the acceptance record
under `cross_check`, keyed by case and recipe.

### Contracts (slice 02; `core/ts_models.py`, exported from `eta_rxncat.core`; `CoreModel`, units in names, no numpy)

- `OptimizerIdentity.name: Literal["geometric", "prfo"]` (additive; `"sella"` still rejected).
- `StageKind` gains `"ts_opt"`.
- `FormingBond`: `i`, `j: NonNegativeInt`, `i < j`.
- `TSStep`: `step: NonNegativeInt`, `accepted_bool`, `energy_hartree`, `max_gradient_hartree_per_bohr`,
  `trust_radius_bohr`, `followed_eigenvalue_hartree_per_bohr2`, `mode_overlap: float | None`,
  `hessian_source: Literal["exact", "bofill"]`, `ratio: float | None`.
- `TSSearchResult`: `final_state`, `final_energy_hartree`, `converged: Literal[True]` (strict),
  `n_steps`, `n_gradient_calls`, `n_hessian_calls`, `n_hessian_refreshes`, `n_rejected_steps`,
  `hessian_method: HessianMethod`, `followed_eigenvalue_hartree_per_bohr2: float` (< 0 at the end
  is **not** required; the validator decides), `final_max_gradient_hartree_per_bohr`,
  `final_rms_gradient_hartree_per_bohr`, `final_rigid_gradient_norm_hartree_per_bohr`,
  `forming_bonds: list[FormingBond]` (sorted), `optimizer: OptimizerIdentity`,
  `options: dict[str, ScalarValue]`, `history: list[TSStep]` (step order; never compared, R20).
- `TSValidationOptions`: `imag_tol_cm1` 20.0, `cutoff_cm1` −50.0, `min_active_core_ke_fraction`
  0.60, `min_forming_stretch_overlap` 0.50, `forming_distance_min_angstrom` 1.90,
  `forming_distance_max_angstrom` 2.90 (validators: positive tolerances; cutoff < −imag_tol;
  fractions in (0, 1]; min < max).
- `TSValidation`: `n_imaginary`, `imaginary_frequency_cm1: float | None`,
  `active_core_ke_fraction: float | None`, `forming_stretch_overlap: float | None`,
  `forming_bonds_in_phase_bool: bool | None`, `forming_distances_angstrom: dict[str, float]`
  (key `"i-j"`), `options: TSValidationOptions`, `active_atom_indices: list[int]` (sorted),
  `mode_count_passed_bool`, `active_core_passed_bool`, `identity_passed_bool`, `passed_bool`,
  `reasons: list[str]` (sorted, vocabulary above). Validators: `passed_bool` == all three;
  `reasons` empty iff `passed_bool`; reasons ⊆ vocabulary.
- `TransitionStateRecord`: `ts_id`, `state`, `search: TSSearchResult`, `validation: TSValidation`
  (with `mode_count_passed_bool` true), `thermo: ThermoResult` (exactly one imaginary listed),
  `degeneracy: Literal[1]`.

### Starter discrepancies (DV rows for `docs/prd/v0.5.0/DISCREPANCIES.md`)

- **DV-01 / PD-009** (plan vs zip): plan "P-RFO … >=50-60%"; zip "TRIC P-RFO … soft-mode
  Hessian-refresh / damped fallback recovery … >=60% … covalent-graph topology guard". Decided by
  TJ A1/A2 (Cartesian P-RFO, ≥ 0.60, topology guard v0.9.0).
- **DV-02** `optimize/ts_optimizer.py` imports `MolecularState`/`VibrationalMode`/`PotentialEngine`/
  `compute_frequencies_from_hessian`/`_ATOMIC_MASSES_AMU` from modules eta does not have, and uses
  `coords_array()`/`.coordinates` shapes eta does not expose.
- **DV-03** `_prfo_step`: always maximises along the lowest eigenvector; filters eigenvalues by
  `|λ| > 1e-6` instead of projecting rigid motions; fixed 25-step Newton without a convergence
  check; `1e-8` added to a denominator.
- **DV-04** `optimize_transition_state`: single RMS-gradient test (3e-4); no step acceptance or
  trust update; energy and final Hessian unvalidated; no failure path.
- **DV-05** `validate_transition_state_modes`: counts modes below −40 cm⁻¹ (TJ: −20 count, −50
  cutoff); default fraction 0.50 (TJ: 0.60); skips the fraction check when it is `None`.
- **DV-06** default mass 12.0 for unknown elements (eta's `thermo.masses` raises).
- **DV-07** `tests/unit/test_v050_ts_prfo.py`: diagonal model Hessian; mode following never exercised.
- **DV-08** no TS identity check beyond counting (eta: R3); no barrier or standard-state handling.
- **DV-09** the slice 01 builder lists any further starter file whose behaviour differs from this
  SPEC (one row each) or writes "none".

### Blast radius

Read from `spec/compiled/architecture.yml` (11 nodes, all `clean`; delta mode), red-team Part B
§5 re-checked by resolve:
- **Touched:** `eta_rxncat_scaffold` (01, 12, 13: `docs/prd/v0.5.0/**`, PD-009, README, version);
  `eta_rxncat_core` (02); `eta_rxncat_optimize` (03); `eta_rxncat_thermo` (04, additive);
  `eta_rxncat_species_runner` (05–13: `orchestrator/ts.py`, `orchestrator/barrier.py`,
  `tests/unit/orchestrator/**`, `tests/e2e/**`, and **`tests/candidate_outputs/v0.5.0/**`** added
  to its `files` in slice 08).
- **Read only / unchanged:** `eta_rxncat_mapping` (graft, relax, perceive_bonds are called;
  nothing changes), `eta_rxncat_engines`, `eta_rxncat_store` (`KEY_SCHEMA` unchanged; keys go
  through `StageConfig`), `eta_rxncat_conformers`, `eta_rxncat_cli` (accepts the wider
  `StageKind`; no change), `eta_rxncat_hw_probe`.
- New edges the updater should see: `species_runner → mapping` (bond perception), `species_runner
  → thermo` (exists), `optimize → engines` (exists). No new node.
- Every core change is additive, so no consumer breaks; core is upstream of everything, so the
  updater lists a wide radius.

### Execution checklist (build order; the lead's work queue)

| # | Slice | Id | Depends on | Node |
|---|---|---|---|---|
| 1 | `slices/01-starter` | OPR.0.5.0.1 | — | `eta_rxncat_scaffold` |
| 2 | `slices/02-ts-contracts` | OPR.0.5.0.2 | .1 | `eta_rxncat_core` |
| 3 | `slices/03-prfo` | OPR.0.5.0.3 | .2 | `eta_rxncat_optimize` |
| 4 | `slices/04-ts-validator` | OPR.0.5.0.4 | .2 | `eta_rxncat_thermo` |
| 4b | `slices/14-bofill-guard` (replan 1, R29) | OPR.0.5.0.14 | .3 | `eta_rxncat_optimize` |
| 5 | `slices/05-ts-runner` | OPR.0.5.0.5 | .3, .4, .14 | `eta_rxncat_species_runner` |
| 6 | `slices/06-barrier` | OPR.0.5.0.6 | .5 | `eta_rxncat_species_runner` |
| 6b | `slices/15-pyscf-cartesian-basis` (replan 2, R30) | OPR.0.5.0.15 | .1 | `eta_rxncat_engines` |
| 7 | `slices/07-tier3-inputs` | OPR.0.5.0.7 | .6, .15 | `eta_rxncat_species_runner` |
| 8 | `slices/08-e2e-diels-alder` | OPR.0.5.0.8 | .7 | `eta_rxncat_species_runner` |
| 9 | `slices/09-e2e-tetrazine` | OPR.0.5.0.9 | .8 | `eta_rxncat_species_runner` |
| 10 | `slices/10-e2e-cyclobutenone` | OPR.0.5.0.10 | .8 | `eta_rxncat_species_runner` |
| 11 | `slices/11-geometric-crosscheck` | OPR.0.5.0.11 | .9, .10 | `eta_rxncat_species_runner` |
| 12 | `slices/12-acceptance-record` | OPR.0.5.0.12 | .11 | `eta_rxncat_species_runner` |
| — | **PHASE 3 GATE**: TJ reviews the candidates (five TSs × two recipes, the cross-check, the six transcriptions, the TS4a graft), promotes what he accepts into `tests/fixtures/v0.5.0/`, confirms the transcriptions, and sets the verdict's regression bounds from slice 12's `proposed_regression_bounds` (R28) | — | .12 | — |
| 13 | `slices/13-acceptance-verdict` | OPR.0.5.0.13 | .12 + TJ promotion | `eta_rxncat_species_runner` |

One slice at a time (the ledger takes no parallel writes). Every node id above exists in the
ledger; no slice creates a node. The feature is done when 13 is audited PASS with verdict `pass`.

### Dependencies

- No new runtime dependency (numpy is a base dependency). No new extra.
- geomeTRIC 1.1.1 + ASE 3.29.0: acceptance cross-check only, in `.venv-accept-uma`, subprocess, CLI
  (R5). xtb 6.8.0 (ADR-0021), UMA `uma-s-1p2p1` (ADR-0017/0020), PySCF GPU env
  (`.venv-accept-gpu`) for R9 — all already provisioned.

## 6. Negative Constraints

- **N1. DO NOT** import `ase`, `sella`, in-process `tblite`, `psi4` or any copyleft package in
  `src/eta_rxncat/{core,optimize,thermo,orchestrator,mapping}/` (engines behind `Engine` are
  excepted, as TJ allowed). ASE only in `tests/e2e/eta_geometric_shim.py` (R19, R5).
- **N2. DO NOT** open, clone, fetch or search Eta_Scripts or nMAP (GitHub or
  `~/PROJECTS/cleanroom-nmap`; only its `TRANSFER_LOG.md` may be read), or message the
  clean-room seats. **DO NOT** read the source of any TS optimizer (geomeTRIC, Sella,
  pysisyphus, Eta_Scripts, the starter's `_prfo_step` beyond a DV row) (TJ A1). geomeTRIC may run
  only as a black box through its documented CLI.
- **N3. DO NOT** pass a TS through `check_ground_state`, `_frequency_and_thermo`, `_push`,
  `_dedup_after_push` or `run_species` (R13).
- **N4. DO NOT** run geomeTRIC's `run_optimizer` or any geomeTRIC function in the eta process, and
  **DO NOT** drive its TS mode through `optimize/geometric_impl.py` (R5).
- **N5. DO NOT** choose the initial mode by active-core fraction (measured wrong, R2).
- **N6. DO NOT** project a Cartesian gradient or Hessian with the mass-weighted rigid basis, and
  **DO NOT** call `thermo.modes.normal_modes` or `_rigid_basis` inside the P-RFO loop (R7).
- **N7. DO NOT** gate TS identity on perceived connectivity (R3).
- **N8. DO NOT** use `eta_rxncat.__version__` as the P-RFO `OptimizerIdentity.version` (R11).
- **N9. DO NOT** take a literature reference from a quoted number; derive it from the SI
  energies and record its standard state (R8). **DO NOT** compare a 1 atm literature value with
  eta's 1 M without Δn·RT ln(cRT/p).
- **N10. DO NOT** loosen a UMA window, the A2 numbers, R3's bounds or R9's bound to make a run
  pass; a miss is a finding with its output to TJ. **DO NOT** gate GFN2 numbers except
  convergence and the mode count (R4).
- **N11. DO NOT** compare `history` or any step-ordered list in a regression or candidate gate (R20).
- **N12. DO NOT** accept frozen atoms, dihedrals or an options key `constraints` in a TS search
  (R21); **DO NOT** add a dihedral constraint to any relaxation (ADR-0032).
- **N13. DO NOT** let a reference TS donate fragment atoms to a graft (R22).
- **N14. DO NOT** validate a TS with empty `active_atom_indices` or empty forming bonds (R16).
- **N15. DO NOT** call a finite-difference Hessian "exact" in a record; record `hessian_method` (R17).
- **N16. DO NOT** execute TJ's bundle builder; extract with `ast.literal_eval`. **DO NOT** commit
  the SI PDFs.
- **N17. DO NOT** write `tests/fixtures/` or promote a candidate; **DO NOT** read
  `tests/candidate_outputs/` or `spec/archive/`, including through `git show`/`git diff`.
- **N18. DO NOT** edit `PRDs/`, `spec/compiled/architecture.yml` by hand, or install/upgrade HACF
  (no `HACF-install.sh` without `--ref`, no `hyper_migrate.py apply`).
- **N19. DO NOT** start a GPU/E2E run while `free -g` + `ps` show another rig's heavy run.

## 7. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A home-written P-RFO has a sign/shift bug that still converges on model surfaces | Medium | High | Non-diagonal, rotated, unequal-mass surfaces with a non-lowest reaction mode (G1); validator independent of the optimizer; R3 identity check; black-box geomeTRIC comparison on every case (R5, reported). |
| GFN2 has no saddle near Liu's TS4a/TS3a (GFN2 ΔE‡ −16.4 / −5.9 at the literature geometries, HF-3), so the gated GFN2 convergence or mode count fails | Medium | Medium | Q-TJ3 A gates it; a miss is stop-and-report to TJ with the output (Q-E5: "should become standard"), never a waived gate. |
| UMA stationary ΔG‡ outside a window (TS4a margin 1.3–2.3 kcal/mol at the literature geometry) | Low–Medium | High | Measured before the build (R6); a miss is a finding to TJ, never a loosened window. |
| Wrong initial mode at a mapped start | Low (measured) | High | R2 overlap rule with the 0.60 refusal (HF-5…7). |
| False convergence from a wrong projector | Low | High | R7 unweighted projector; convergence on the unprojected gradient; unequal-mass tier D. |
| σ or TS degeneracy off by RT ln 2 (0.41 kcal/mol) | Low | Medium | Q-TJ2 A; σ by the graph route equals the SMILES route on minima (test); HF-8. |
| UMA float32 FD noise adds a spurious imaginary mode at a TS | Low (HF-4 clean) | Medium | `hessian_method` recorded; stop-and-report (R17). |
| SI transcription error | Low (HF-1 checks) | High | Byte-equal re-transcription, formula/connectivity, PySCF energy reproduction for Liu (R9), stationarity (HF-4), TJ at Phase 3. |
| P-RFO cycles and hangs the shared host | Low | Medium | `max_wall_time_s`, `max_steps`, rejection budget, `timeout 3600` (R15). |
| Shared host: other rigs' heavy runs | High | Medium | Heavy-run gate; one GPU/E2E at a time; recorded in the proof. |
| `hyper_spec`/`hyper_migrate` warn "outside the pinned contract" on rig 0.7.21 | Certain | Low | Expected; noted in proofs, not a finding. |

## 8. Success Metrics

- Default suite (`uv run pytest`), ruff, format, mypy and the base licence gate exit 0 with **no
  skips** in the gated set.
- Tier D: G1 on every model surface; the cadence and every failure reason tested; G2 at 1e-12; G3.
- Per Tier 3 search and recipe: G4 gates hold (both recipes: converged + mode count; UMA also KE,
  identity, window, ordering), GFN2 extras reported; G5 reported; G6 100% cache hits.
- Transcriptions: byte-equal to HF-1, PySCF within 1e-4 Eh on the Liu files (R9).
- Cross-check attempted and recorded for every case × recipe (R5).
- TJ promotes the candidates at Phase 3; the verdict run passes on the promoted fixtures; version 0.5.0.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.5.0.1 | slices/01-starter | Unpack the v0.5.0 starter byte-identical as reference with its discrepancy register (DV-01..DV-09) and set PD-009 to decided with TJ's A1/A2 answers. |
| OPR.0.5.0.2 | slices/02-ts-contracts | Add the frozen TS contracts to eta_rxncat.core (prfo optimizer name, ts_opt stage kind, core/ts_models.py) without changing any existing field. |
| OPR.0.5.0.3 | slices/03-prfo | Implement the clean-room Cartesian P-RFO saddle search (TransitionStateOptimizer, PRFOOptimizer) with exact-Hessian seed and refresh, Bofill updates, trust radius and forming-bond mode following, proved on unequal-mass model surfaces. |
| OPR.0.5.0.4 | slices/04-ts-validator | Add validate_transition_state (TJ's A2 numbers plus the measured TS identity check) and ts_thermochemistry (one imaginary mode excluded, sigma from the bond graph, no TS degeneracy), leaving the minimum path unchanged. |
| OPR.0.5.0.5 | slices/05-ts-runner | Add run_transition_state: P-RFO search, final Hessian in the frequency stage, validation and TS thermochemistry, every stage cached under ts_opt with failures, never through the minimum path. |
| OPR.0.5.0.6 | slices/06-barrier | Add BarrierSpec and activation_free_energy: dE, dH and dG dagger at 1 M and 1 atm from a TS record and reactant ensembles, conservation checked without a TS SMILES. |
| OPR.0.5.0.7 | slices/07-tier3-inputs | Land the Tier 3 inputs: six XYZ files re-transcribed byte-equal to resolve's checked copies, SOURCES.md provenance with derived references, five provisional TS-fixture YAMLs and a loader, tier-D checks and the PySCF energy reproduction of the Liu files. |
| OPR.0.5.0.8 | slices/08-e2e-diels-alder | Run the TS1a_n (unmapped) and TS1b_n (mapped from M1) TS searches and barriers on GFN2 and UMA, gated per TJ's Q-TJ3, and commit the candidates. |
| OPR.0.5.0.9 | slices/09-e2e-tetrazine | Run the TS3a (unmapped) and TS4a (two single CF3 grafts plus core-frozen pre-relaxation) TS searches and barriers on GFN2 and UMA with the TS4a<TS3a ordering, and commit the candidates. |
| OPR.0.5.0.10 | slices/10-e2e-cyclobutenone | Run the Paton N4 cyclopentadiene + cyclobutenone TS search and barrier on GFN2 and UMA from Paton's geometry and commit the candidates. |
| OPR.0.5.0.11 | slices/11-geometric-crosscheck | Cross-check every Tier 3 TS against geomeTRIC's TS search run as a black box (documented CLI, subprocess, same start, engine and seed Hessian) and record the comparison, reported only. |
| OPR.0.5.0.12 | slices/12-acceptance-record | Assemble the v0.5.0 acceptance record from real per-check outcomes with pending states, measure run-to-run reproducibility to propose the regression bounds TJ sets at Phase 3, and derive the README claims. |
| OPR.0.5.0.13 | slices/13-acceptance-verdict | After TJ's Phase 3 promotion and regression bounds, run the verdict on both recipes against the promoted fixtures and bump the version to 0.5.0 only on pass. |
| OPR.0.5.0.14 | slices/14-bofill-guard | Make bofill_update return the Hessian unchanged when the residual or the step is exactly zero, so no bare ZeroDivisionError escapes the TS search, and test the lost-mode-on-Bofill exact-refresh recovery path. |
| OPR.0.5.0.15 | slices/15-pyscf-cartesian-basis | Add a keyed cartesian_basis option to the pyscf_gpu_cpu engine (default False, written into the resolved stage only when True so every existing PySCF key stays byte-identical) so R9 can reproduce Gaussian 6D 6-31G(d) references. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
