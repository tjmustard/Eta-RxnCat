---
id: OPR.0.7.0
mission: release-0.7.0
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope mission create)"
created: "2026-11-26"
intent: "Enumerate N candidate ReactionGraphs from a reference graph and an R-group/ligand library with explicit charge/multiplicity propagation, keep ranked TemplateGeometry fallbacks per node and run TS seeds through them, and export each run as versioned run-data JSON rendered by a static, serverless HTML review bundle of reusable view components (animated imaginary modes, optimization trajectories, per-candidate summaries): TJ's Phase 3 visual audit and the foundation of eta's future UI."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0005, ADR-0016, ADR-0023, ADR-0024, ADR-0027, ADR-0028, ADR-0029, ADR-0030, ADR-0031, ADR-0032, ADR-0042, ADR-0043, ADR-0044, ADR-0045, ADR-0046, ADR-0048, ADR-0049, ADR-0050, ADR-0051, ADR-0052, ADR-0053]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: eta v0.7.0 — Combinatorial Library Enumeration, Multi-Template Fallback & Phase 3 Review Bundle

## Intent

Release v0.7.0 of eta-rxncat (plan PR #14, `feat/graph-enumerator`, plus TJ's review-bundle feature).

- **`eta_rxncat.mapping.enumerator`** turns a reference `ReactionGraph`, declared graft sites and an
  R-group/ligand library into N candidate graphs.
  - Every mapped node's charge and multiplicity is declared by the library and checked; none is
    inferred.
  - Each enumerated node keeps every template that grafted cleanly, in declared rank order.
- **A TS seed runner** falls through those templates **only** on a TS-validation failure.
- **`eta-rxncat review-bundle`** exports each run as **versioned run-data JSON** (`schema_version` 1,
  a public contract). It then writes a static, serverless, offline HTML review bundle that only
  renders that JSON through reusable view components. TJ audits every enumerated TS (the imaginary
  mode animated) and every optimization (its frames) in it at Phase 3. It is the first piece of
  eta's UI track (TJ placement A).

A small E2E on the Tier 4 TSs with v0.6.0's alkyl series proves the mechanics.

- **Base:** v0.6.0 release, `main` = tag `v0.6.0` = `a8b8e71aff30ef0c9fb838b50e229fdf50effcd2`.
  Resolve re-verified every cited symbol at that sha (R1).
- **Scope source:** `PRDs/Eta-RxnCat_Living_Master_Plan.md` › v0.7.0 (authoritative, read-only), plus
  TJ's review-bundle decision. `PRDs/Eta-RxnCat-v0.7.0.zip` is reference only (sha256
  `ad7b7616…f0b25`).
- **Sources:**
  - Draft rev 3 sha256 `28af13417a3371403a31d1bd6cfd848525ce0bc2c940ecaf434f237d92d92a0f`.
  - Red Team report sha256 `f18bb087d548cf00727a55190c1c9d40b7bac8470511f2ed54730cc3915f1650`, with
    23 findings, all mediated in §5.
  - Resolve evidence in `~/.hacf/eta-rxncat-hacf/evidence/v070-resolve/` (`PHASE1.md`, the
    `offline*` files, `m9-3dmol-2.5.5/`, and the exo units `{et,pr}.{xtb,uma}.*`).

### TJ decisions (verbatim; binding)

| Id | Row | Text (verbatim) | Effect |
|---|---|---|---|
| Q-A1 | `qitem-20261125202245-84c25e2f8f645f5a` | "**Q-A1: B** (recommended). Graft every template in declared rank order and record each failure with its reason. At run time the TS ensemble runner falls through to the next template when a seed fails TS validation. An EngineError still propagates. The general scheduler stays at v0.8.0." | Graft-time ranking + run-time fall-through on the R4 allow-list only. |
| Q-A2 | same row | "**Q-A2: A** (recommended). Keep the 600 s guard and ADR-0024 unchanged, and size the E2E small. Report the stall rate and time lost. The out-of-process cure goes to v0.8.0." | ADR-0024 is unchanged. The stall cap reports (R6). The guard's budget source is R7. |
| Q-A3 | `qitem-20261125202813-4331bdd0fedc0322` (supersedes "Q-A3 B" and input request `…ac019f09ace2f15c`) | "I don't think there is a paper for that, but what we can do is you generate the output for these enumerated reactions, transition states, provide them to me with the files to me. I'm going to need a way to visualize them, visualize the frequencies to ensure that the transition state negative frequency is correct, that the optimization geometries are correct. I can manually audit them, and then we won't need to go to a paper because I've seen enough of these in my time to know when something is right or wrong" | Tier 4 + ethyl/n-propyl on TS1a_n and TS1a_x, both engines, the fallback constructs and the mechanics gates. ΔΔG‡ per R is report-only. No literature series. The human gate is TJ's visual audit of the review bundle (slice 13). |
| Review bundle | same row | "eta feature in v0.7.0"; format "HTML page only" | G10–G13, slices 06–09 and 13. |
| UI track | `qitem-20261125203022-a8e19bbeecc4e646` | "This actually fits in perfectly to some requirements later on for a user interface. Potentially setting ourselves up for being able to visualize and build the reaction networks as well as the selecting the swapping atoms, keep, remove, align, transition state active, all of those types of things in an HTML solution, also being able to visualize outputs with frequencies, multiple conformers, etc. So, yes, if we can start building out that user interface in HTML, that would be great. Longer term, the question is: should that be HTML or a different solution that is compatible with macOS, Linux, Windows, etc. Nice thing about HTML is it is compatible. But you have to load up a server for non-technical, non-savvy scientists, this may be difficult, so it would be better to have a more user-friendly solution" | Data/view split. Run-data JSON is the one public contract (R12); the HTML only renders it. Reusable components (R16). Static and serverless; it opens with a double-click. |
| Placement A | `qitem-20261125203315-64b10106c04fe484` | "Placement as proposed: the static review bundle in v0.7.0; a read-only network view in v0.8.0; conformer, frequency and topology views in v0.9.0; the interactive 'eta ui' as v1.1.0; desktop packaging (pywebview recommended; final choice later) as v1.2.0. PRDs/ is TJ's. Record this as a proposed master-plan change for his edit or approval, not as an edit you make." | v0.7.0 builds only the static bundle. The proposed plan changes are a PROPOSED ADR (§5) for TJ's edit; `PRDs/` is untouched. |
| Licence | standing | "I would prefer to keep ASE out as it would be a major core dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later. But the core remains." + "It's fine that the engine MACE pulls in ASE just not the core." | The enumerator is pure Python/numpy + eta's `graft`. 3Dmol.js 2.5.5 (BSD-3) is a vendored **output asset** that no Python module imports. geomeTRIC stays in the `opt-geometric` extra and is never vendored. |
| v0.3.0 Q2 | standing | "B use it as reference only. Keep a list of the discrepancies so that if needed, we can go through each of them and fix any issues that arise." | The zip unpacks to `docs/prd/v0.7.0/` with `Eta-RxnCat-v0.7.0/.ruff.toml` `exclude = ["*"]` (R29); DV rows below. |
| v0.4.0 Q5 | standing | "Q5. A" (explicit product charge and multiplicity; parity checked; the charge sum is reported, never used to infer) | Declared `charge_delta` and multiplicity per entry (R10). |
| v0.4.0 Q2 / roadmap | standing | "Q2. (b)"; roadmap "B: keep at v0.7.0" (PD-008) | This mission. |
| v0.6.0 Q-RES1 | `qitem-20261125135141-40dabb65dfb7a8a8` | "Can we r-group enumerate a new TS from with a alkyl chain" | Slice 14 of v0.6.0's fragments and graft recipe are the E2E's starting point. |
| Phase 3 / Push / Engines / Clean room | standing | culture; v0.6.0 Q3 amended "Build, install, and run these autonomously as to move on to the next step/question." | Only TJ promotes. Candidates and the bundle go to `tests/candidate_outputs/v0.7.0/`. Seats run engines, and a failed GPU run is a finding. The lead pushes. Never open Eta_Scripts/nMap. Read no TS-optimizer or conformer-search source; geomeTRIC is a black box, and only eta's own wrapper and geomeTRIC's **output files** are read. |
| Replan 7: fix | `qitem-20261126151741-216f0468b8ca13cd` | "Fix site + seed clash check" ("…plus a check that rejects or repairs seeds with atoms too close before optimization, so clashes like this one don't produce junk TSs"); TJ: "The initial structure was too close and the clashes led to a bad path and bad TS geometry. The ethyl group reacted with the diene due to a bad initial geometry clash." | Slices 15 (clash) and 16 (site) (R35). |
| Replan 7: bond check | `qitem-20261126151838-e190808aa4d1ce77` | Unintended-bond check: "Yes, add it in v0.7.0 (Recommended)" (A+, all inside v0.7.0) | Slice 15's `bond_changed:*`; reruns and re-review (slices 17-18). |
| Replan 7: promotion | same rows | "Yes, it stands (Recommended)". Keep 9fdba68; regenerated records come back as candidates to promote again. | Slice 14 waits for TJ's re-promotion. |

**TJ answers (R35): Q-R7a = A and Q-R7b = A** (relay `qitem-20261126153756-49f5d76005956ea5`, 11-26).
The question text is in `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7/TJ_QUESTION.md`.
- **Q-R7a, the clash cut: A.** 1.3 × Σ covalent radii, eta's bond rule. The other options were
  0.45 × Σ Bondi vdW radii (B) and an absolute Å (C).
- **Q-R7b, a clashing sample: A.** Reject it, record it, keep the slot, and draw no replacement.
  The other options were reject and replace (B) and repair (C).
- The M11 conditional row of slice 06 is not owed: M11 is measured, and the frames are labelled per
  frame (`accepted_bool`, R33).

## 1. Introduction & Goals

**Problem.**
- eta grafts one fragment onto one template (v0.4.0) and runs competing TS ensembles (v0.6.0). A
  library screen still means hand-building every graph, and a node's ranked `templates` are never
  read.
- TJ's Phase 3 audit is a judgement on structures and modes. Until now he has had JSON numbers and
  bare XYZ, with no way to see the imaginary mode or the optimization path.

**Solution.**
- A pure, deterministic enumerator with recorded refusals.
- Rank-ordered fallback templates, with run-time fall-through on TS-validation failures only.
- Optimization frames stored at eta's own boundaries.
- One run-data JSON contract, and an offline HTML bundle that renders it.

**Audience.** TJ, screening R-groups/ligands over a fixed mechanism and auditing by eye. v0.8.0's
scheduler and network view build on these contracts; TJ's planned v1.0 API freeze means
`EnumerationPlan` and `RunData` are designed to last (additive-only within a version).

### Goals (each gated in §8)

- **G1 Contracts.** Typed, `extra="forbid"`, unit-suffixed models for sites, library entries, graft
  records, candidates and fallback records (R9).
  - `ReactionGraph` schema 1 is unchanged.
  - `eta_rxncat.core` still imports no numpy/RDKit (an import-isolation test).
- **G2 Enumerator, single site.** Each entry × each declared (node, template) is grafted with eta's
  `graft`.
  - Every fragment order is tried; the lowest RMSD wins, ties go to declared order.
  - A refusal is recorded from the closed set.
  - The output is byte-equal across two runs.
- **G3 Charge/multiplicity, per template and across nodes.**
  - Per template: P3 (R10).
  - Across nodes: every node of a selectivity set carries the same entry multiset, and the competing
    TSs share element multiset, charge and multiplicity with each other and with Σ reactants.
    Otherwise `inconsistent_candidate:<detail>`.
  - `reactant_key` is derived from the candidate, never passed in.
- **G4 Multi-site product.**
  - Deterministic Cartesian order.
  - A required `max_candidates` refuses, never truncates.
  - Remapping is per template through `index_map`.
  - `site_atom_deleted` is a refusal.
  - `projected_ts_searches` is reported (R11).
- **G5 Ranked fallbacks (graft time).** Eligible templates keep declared order, renumbered 1..k.
  With k = 0 the candidate is `unmappable:<node>` (kept, no graph).
- **G6 TS seed fallback (run time).**
  - In rank order: a guarded, cached pre-relax; the pathway-face check; then
    `run_ts_ensemble_detailed`.
  - Fall through only on the R4 allow-list. Every other reason stops the node.
  - A live `EngineError` propagates. Charged/open-shell runs are refused.
  - Every attempt is recorded, and a rerun is all cache hits.
- **G7 Enumerated selectivity E2E.** ethyl and n-propyl on C7 (H16 replaced) of TS1a_n and TS1a_x,
  GFN2 and UMA, one (R × pathway × engine) unit per command.
  - Gated: N = 2 `ok`; charge 0 / multiplicity 1; graft RMSD ≤ 0.15 Å, 0 contacts; G3; Σw = 1;
    every member on the pathway's expected face; zero `engine_error`/`face_mismatch`; an all-hit
    rerun.
  - Reported: ΔΔG‡ per R, members, the stall count, time lost, `orientation_mismatch` count,
    CPU/wall.
- **G8 Fallback E2E (GFN2 gated, UMA reported once).**
  - **Graft-time:** rank 1's site map aligns on a Cp H, so it is refused `alignment_rmsd`.
  - **Run-time:** rank 1 of the endo node is the TS1a_x geometry, giving
    `seed:face_mismatch_pathway` before any TS search.
  - In both, rank 2 yields the ensemble, and the records name rank 1's reason.
- **G9 Graph hygiene.** The slice 01 split (R19) gives new nodes `eta_rxncat_selectivity`,
  `eta_rxncat_enumerator` and `eta_rxncat_review`.
  - Descriptions ≤ 1800 chars.
  - The graph is acyclic.
  - The union of owned files is preserved.
- **G10 Frames stored.**
  - P-RFO `TSStep` gains geometry, filled in `orchestrator/ts.py`; `prfo.py` is not edited (R33).
  - geomeTRIC runs gain bridge frames in success **and** failure payloads.
  - The key is unchanged; frames are payload-only (R13).
  - geomeTRIC runs in a per-run temp cwd (R8).
- **G11 Run-data contract and bundle writer (R12, R14–R17).**
- **G12 Review content (TJ's four items).**
  1. Each TS: 3D structure, frequencies with the imaginary mode highlighted and animated, and a loud
     banner when the count ≠ 1.
  2. Each optimization: a step player over the frames, an energy-vs-step plot, and convergence data.
  3. Each candidate: R, pathway, engine, rank used, fallbacks with reasons, charge/multiplicity,
     ΔG‡ | "not computed", ΔΔG‡, members/weights, graft RMSD.
  4. An index with the mechanics-gate pass/fail, linking to each.

  These are rendered by five reusable components, plus a JS-free static summary (R17).
- **G13 Bundle for v0.7.0.** Every v0.7.0 E2E run is bundled into
  `tests/candidate_outputs/v0.7.0/review/` before Phase 3. The real-bundle hygiene scans run, and
  TJ's visual audit is the Phase 3 gate.
- **G14 Seed geometry checks (R35, slice 15).**
  - A start geometry with a clash (pairs >= 3 bonds apart; the Q-R7a cut) never reaches an engine:
    it is `seed_clash`, recorded with the pair, the distance and the ratio.
  - A bond made or broken outside the forming bonds, at the pre-relax or at the TS, is
    `bond_changed:<stage>`, recorded with the bonds.
  - A graft with close contacts is never seeded.
- **G15 Review dispositions (R35, slices 16 and 18).**
  - Every frequency row on the site carries its disposition: member, merged or excluded with its
    reason, fell through, kept, superseded by push, or dropped with its reason.
  - Not-used rows are grouped apart from used rows.
  - Every TS shows its imaginary frequency, forming-bond overlap and forming distances, and a banner
    on any identity failure.
  - The rerun records and a fresh bundle go back to TJ for re-promotion.

## 2. Confidence Mandate

**Score: 9/10.** Every red-team finding has a decision. The exo graft, the eligibility gap, the face
separation and the fallback constructs are measured, the run-time strings are read at the release
sha, the 3Dmol pin is verified, and the exo engine units are measured (HF-3: all four clean on both engines). The residual risks
each have a stop-and-report gate in the slice that meets them: frame labelling (M11, slice 06), the
guard's budget source under load (M13, slice 05), and bundle size (M10, slice 08).

### Host facts measured by resolve (evidence `~/.hacf/eta-rxncat-hacf/evidence/v070-resolve/`)

- **HF-1 Exo graft (M1 geometry, F7; `offline.json`).**
  - Site rule: replace the C7 H with the **largest angle** between C7→H and C7→diene centroid
    (atoms 0, 1, 4, 5, 6). It picks H16 on both TSs: 179.9° on TS1a_n, 163.5° on TS1a_x (H17 is
    66.4° and 84.4°).
  - Lists, both TSs: keep all but 16, delete [16], alignment [7, 2, 3, 17], core [0..5], forming
    bonds [(1, 2), (3, 5)].
  - Correct order: endo 0.033–0.035 Å, exo 0.046–0.049 Å, with 0 contacts, min distance 1.078 Å and
    24/27 atoms.
  - Mirror order: exo 0.483–0.486 Å, refused `GraftClashError`. On endo (0.491–0.494 Å) it **grafts**
    with 17 contacts at a minimum of 0.64 Å.
  - The lower-fit order differs per template for the same fragment (ethyl: endo [3, 4], exo [4, 3]).
- **HF-2 Face and orientation (F2, F6, F13).**
  - `forming_bond_configuration` gives TS1a_n [1, 1] and TS1a_x [−1, −1]. The reflected TS1a_n stays
    [1, 1]; the descriptor is relative.
  - Every correct graft keeps its TS's face.
  - The signed volume at C7 over (C2, C3, X) flips sign between H16 and H17 on both TSs, and the
    grafted R takes H16's sign.
  - Graft-time construct: alignment [7, 2, 3, 8] has a best fit of 0.888 Å endo and 1.34 Å exo.
- **HF-3 Exo engine units (M1 engine half, M3, M5).** One command per unit, each behind its own
  blocking host check, from a scratch cwd, under `timeout 3600` with `/usr/bin/time -v`. The table
  is filled from the unit files.

| Unit (R, exo, engine) | Graft RMSD / contacts / atoms | Graft pre-relax | Core max disp. | Members (faces) | Σw | Exclusions | Max member pre-relax | Ensemble wall | Rerun | Command wall / CPU / peak RSS |
|---|---|---|---|---|---|---|---|---|---|---|
| ethyl, GFN2 | 0.0486 Å / 0 / 24 | 2.1 s | 4e-9 Å | 3 (all [−1, −1]) | 1 | 3 `outside_window` | 63.7 s | 230 s | 0 rows, 0 calls, equal | 234 s / 3333 s / 157 MB |
| n-propyl, GFN2 | 0.0457 Å / 0 / 27 | 10.0 s | 2e-8 Å | 3 (all [−1, −1]) | 1 | 3 `outside_window` | **408.5 s** | 1157 s | 0 rows, 0 calls, equal | 1170 s / 14 546 s / 160 MB |
| ethyl, UMA | 0.0486 Å / 0 / 24 | 31.5 s | 8e-9 Å | 3 (all [−1, −1]) | 1 | 3 `outside_window` | 205.3 s | 633 s | 0 rows, 0 calls, equal | 737 s / 9900 s / 7.85 GB |
| n-propyl, UMA | 0.0457 Å / 0 / 27 | 24.1 s | 2e-8 Å | 3 (all [−1, −1]) | 1 | 4 `outside_window` | 83.6 s | 390 s | 0 rows, 0 calls, equal | 476 s / 5687 s / 8.15 GB |

  - Every unit exited 0, with no `engine_error`, `face_mismatch` or `PreRelaxTimeout`, and every graft
    and start had face [−1, −1] (the exo expected face). Each host check passed first; a niced (10)
    hakf pytest at ~10 cores ran beside the GFN2 units (lead's ruling). The scratch cwd and the repo
    were clean of `HT.v_*` afterwards.
  - The first UMA attempt failed in 0.55 s, before any engine call: `EngineUnavailableError` (the main
    `.venv` lacks the `mlip-uma` extra). That was resolve's setup, not a product defect; it was rerun
    with `.venv-accept-uma` (eta imported from the repo at `a8b8e71`). The attempt is kept in
    `attempt1-uma-novenv/`.
  - **M5:** the UMA unit peak RSS is 8.15 GB at the command level, which keeps the 12 GiB floor.
  - **L1 evidence:** the n-propyl GFN2 member pre-relax took 408.5 s beside the niced load, 68 % of the
    600 s guard (the v0.6.0 endo n-propyl maximum was 282 s).

  - **M3:** endo healthy walls come from v0.6.0 HF-14: ethyl 192/223 s and n-propyl 482/206 s
    (GFN2/UMA).
  - **Worst case per command (HF3-BOUND):** the healthy maximum command wall is 1170 s (n-propyl
    GFN2). At the 600 s base that gives 1170 + 600 + 2 × 600 = 2970 s, inside `timeout 3600`. With
    R7's load-scaled cap of 1200 s it gives 1.5 × 1170 + 3 × 1200 = 5355 s, so the slice 11/12 E2E
    unit commands run under `timeout 5400` (R7). Every other command keeps 3600.
- **HF-4 Run-time strings (M7, read at `a8b8e71`).** A seed's `failed_reason` is `seed:` plus one
  of:
  - `ts_search_failed:<TSSearchFailureReason>` (`max_steps`, `too_many_rejections`, `mode_lost`,
    `no_reaction_mode`, `wall_time_exceeded`);
  - `scf_convergence`, `engine_error`, `ts_validation_failed`;
  - `gate_failed:<gate>`, `face_undetermined`.

  `TS_VALIDATION_REASONS` members never appear in `failed_reason`. They are in
  `record.validation.reasons`. (The draft said otherwise.)
- **HF-5 3Dmol.js (M9 licence/integrity; `m9-3dmol-2.5.5/`).**
  - Pin **2.5.5** (published 2026-05-22); 3.0.0 (2026-11-22) is under the two-week age rule.
  - npm `dist.integrity` `sha512-kqNHouGqq3YfW58174tdERvm0XYTmP0tavQKOqIw1ouc2OJ7epkXEFrtEkVXV0clBZT2Ze2xHRC/qxX0u0qCdw==`
    matches the tarball.
  - `build/3Dmol-min.js`: sha256 `f7cc78921ae72e7623e89cdd111434f58c2efddd2ffda1cd212644b406fb8016`,
    537 792 B.
  - LICENSE: BSD-3-Clause. It names the bundled GLmol (dual MIT/LGPL3; **eta elects MIT**),
    three.js (MIT) and jQuery (MIT). Runtime deps: iobuffer, netcdfjs, upng-js (MIT) and pako
    (MIT AND Zlib).
  - The min.js contains RCSB/PubChem download URLs, so CSP `connect-src 'none'` is required.
- **HF-6 Slice-12 audit findings (lead, 2026-11-26).**
  - **L1:** the 600 s guard is host-load sensitive. Deterministic GFN2 hit `PreRelaxTimeout` at
    1.8–3.7× slice 11's wall.
  - **L2:** geomeTRIC writes `HT.v_*.txt` into the process cwd; 14 landed in the repo root.
  - **Resolve's addition from HF-3 unit 1:** GFN2 xtb burns about 14 cores (3333 s CPU over 234 s
    wall), so a process-CPU budget must be thread-normalised.

### Measurements left to the build (each a stop-and-report gate)

- **M10 (slice 08):** dry-export bundle size against 25 MB.
- **M11 (slice 06, first task):** bridge frames vs geomeTRIC's `xyzout` output on one GFN2
  pre-relax. Measured: every `xyzout` frame matches a bridge frame; outcome `accepted_bool` (R33).
- **M12 (slices 09 and 13):** browser smoke on stubs, then on the real bundle with known answers.
- **M13 (slice 05, first task):** wall vs per-thread-normalised CPU per guarded pre-relax, idle and
  beside a loaded host.

## 3. Scope

### In scope

1. Starter + DISCREPANCIES + graph split + the v0.6.0 README "unit weights" wording fix (01).
2. Core contracts, frame fields, fallback records, additive exclusion reason (02).
3. Single-site enumerator + cross-node check (03).
4. Multi-site product (04).
5. TS seed fallback runner, ensemble guards (pathway face, orientation, stall cap, budget source)
   (05).
6. Frame capture + per-run temp cwd (06).
7. Run-data contract + exporter (07).
8. Bundle writer, CLI, vendored 3Dmol, static summary, CSP, scans (08).
9. View components + browser smoke (09).
10. E2E inputs (10).
11. Enumeration E2E (11).
12. Fallback E2E (12).
13. Review bundle + acceptance record → TJ Phase 3 (13).
14. Verdict + docs + 0.7.0 bump (14).

### Out of scope (each would otherwise grow sideways)

- The DAG scheduler, resume, and general non-TS fallback (v0.8.0).
- Candidate ranking and CSV/JSON summaries (v0.9.0).
- Topology audit (v0.9.0).
- `eta-rxncat enumerate` (v1.0.0).
- A literature series (Q-A3 revised).
- An out-of-process optimizer (Q-A2 A → v0.8.0).
- Charged/open-shell engine runs.
- Multi-component graft sites.
- IRC.
- Re-bundling v0.6.0.
- The rest of the UI track (v0.8.0 network view, v0.9.0 conformer/frequency/topology views, v1.1.0
  `eta ui`, v1.2.0 desktop).
- Any server, `fetch()`, ES module or editing in the bundle.
- Known limit: entry ids containing `+` can make joined candidate ids collide (slice 04 audit,
  observed item (a)); no fix or refusal in v0.7.0 (a core-model change; core is at 1973/2000).
- Any change to `ReactionGraph` schema 1, `graft`, `relax_constrained_core`, the P-RFO algorithm
  (only its step record gains geometry), the sampler or **`score_selectivity`** (R3).

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority |
|---|---|---|---|
| US-001 | As TJ, I want the v0.7.0 starter logged as reference. | 38 files byte-identical under `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/`, `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` `exclude = ["*"]` (hook-style ruff check and format check exit 0; R29), DV-01…DV-10, PLAN_DISCREPANCIES "Plan-vs-code (v0.7.0)" section. | P0 |
| US-002 | As the lead, I want the graph to keep room. | R19 sequence; three new nodes; owned-file union preserved; descriptions ≤ 1800; acyclic; updater once. | P0 |
| US-015 | As TJ, I want the README claim to say what was checked. | "unit weights" → "weights summing to 1" in README and the claims helper in `tests/unit/test_identity.py`, changed together; suite green. | P1 |
| US-003 | As a chemist, I want typed site/library/candidate/fallback models. | §5 Contracts; round-trip JSON; old graphs load; core import isolation. | P0 |
| US-004 | As a chemist, I want each declared graft done or refused with a reason. | Per (entry, node, template) `ok` with measures or `refused` from the closed set; byte-equal twice. | P0 |
| US-005 | As a chemist, I want charge/multiplicity explicit and consistent across a candidate. | P3; parity refusal; ±1 and doublet; mixed coverage refused `inconsistent_candidate`. | P0 |
| US-007 | As a chemist, I want multi-site libraries as a product, never truncated. | Order, cap refusal, two-site remap toy, `site_atom_deleted`, projected count. | P1 |
| US-006 | As a chemist, I want a TS node to fall back on a TS-validation failure, and only then. | R4 allow-list; real-class `EngineRuntimeError` through `run_transition_state` stops `stopped:seed:engine_error`; cached replay stops; graft timeout stops; `seed:face_mismatch_pathway` falls through; a test enumerates `TSSearchFailureReason`; rerun all hits; charged refusal. | P0 |
| US-016 | As a chemist, I want an ensemble that stalls to stay bounded and honest. | Stall cap k = 2 reports `stall_cap_reached`; budget source per R7 recorded per timeout row; orientation mismatch excluded. | P0 |
| US-008 | As TJ, I want each optimization's path stored. | P-RFO steps carry geometry; geomeTRIC frames in success and failure payloads; old rows load as "no trajectory stored"; keys byte-equal to v0.6.0's; cwd clean. | P0 |
| US-014 | As a future UI (and TJ's scripts), I want one versioned JSON. | Strict writer, lenient reader, committed schema + drift test, codes not messages, canonical serialisation, version rule documented. | P0 |
| US-009 | As TJ, I want a page per candidate showing the TS, its moving mode and every step. | G12 via components + static summary; bytes deterministic; no network; no host data; hostile strings inert; banner on ≠ 1 imaginary; CSP. | P0 |
| US-010 | As TJ, I want the enumeration proven end to end. | G7 per unit; candidates in `tests/candidate_outputs/v0.7.0/`; host checks in proof. | P0 |
| US-011 | As TJ, I want the fallback proven end to end. | G8; GFN2 gated; UMA reported once. | P0 |
| US-012 | As TJ, I want to audit every v0.7.0 TS and optimization by eye before promotion. | Bundle covers every E2E run; real-bundle scans; M12 on the real bundle; Phase 3 row names path and checks. | P0 |
| US-013 | As the lead, I want a record and a verdict that gate on real outcomes. | `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` derived from candidates; suite counts/skips; version 0.7.0. | P0 |

## 5. Technical Specifications

### Resolved trade-off log

| # | Item | Source | Decision | Detail |
|---|---|---|---|---|
| R1 | Base and symbols | F10 | resolved | Base `a8b8e71`. Verified there: `run_ts_ensemble_detailed` (ts_ensemble.py:230), `_PreRelax` (:150), `PRE_RELAX_BUDGET_S = 600.0` (:70), `deadline` (_deadline.py:39), `Bridge`/`calc_new` (geometric_impl.py:151/154), `params.xyzout` (:361), `TSStep` (core/ts_models.py:73), `TS_VALIDATION_REASONS` (:23), `_opt_payload` (orchestrator/species.py:464), `OptimizationResult` (core/optimization_models.py:28), `_EXCLUSION_REASON` (core/selectivity_models.py:29), `TSSearchFailureReason` (optimize/errors.py:39). |
| R2 | Pathway identity | F2, F13 | accept | Each `SiteTemplateMap` carries its own `forming_bonds` (template index space, mapped through `index_map`, validated: both atoms kept). Each selectivity-set pathway declares `expected_face: tuple[int, ...]`. The check runs on the pre-relaxed start **before** the TS search and on the seed after it (new optional `expected_face` keyword on `run_ts_ensemble_detailed`; `None` = v0.6.0). A mismatch is `seed:face_mismatch_pathway`, a template fault. HF-2: endo [1, 1], exo [−1, −1]. |
| R3 | Cross-node consistency | F3 | accept; scorer frozen | G3 invariant in the enumerator. The composition/charge/multiplicity refusal is in `enumerated_pathway_inputs` and `run_ts_with_fallback`, not in `score_selectivity`. The scorer is out of scope and pinned by v0.6.0's promoted fixtures. A direct scorer call with a hand-built `reactant_key` is a stated v0.6.0 limit. `reactant_key` = sorted (canonical SMILES, count) of the candidate's reactant nodes: RDKit `DetermineBonds` at the declared charge on each reactant node's rank-1 eligible template. |
| R4 | Fall-through allow-list | F1, HF-4 | accept, amended | **Falls through:** `seed:ts_search_failed:{max_steps,too_many_rejections,mode_lost,no_reaction_mode}`, `seed:ts_validation_failed`, `seed:gate_failed:<any>`, `seed:face_undetermined`, `seed:face_mismatch_pathway`. **Stops the node** with `stopped:<reason>`: everything else, including `seed:engine_error` (ADR-0045's cached crash), `seed:scf_convergence` (an engine fault, not TS validation: TJ's Q-A1 text), `seed:ts_search_failed:wall_time_exceeded` (a time fault), `graft_pre_relax_timeout` and any unknown string. A live `EngineError`/`EngineUnavailableError` propagates. A test enumerates `typing.get_args(TSSearchFailureReason)`, so a new reason fails until classified. |
| R5 | Charged runs | F8 | accept | `run_ts_with_fallback` and `enumerated_pathway_inputs` refuse any node at charge ≠ 0 or multiplicity ≠ 1: `charged_run_not_supported_v070`. The sampler perceives bonds at charge 0. Enumeration itself handles ±1 and doublets (unit tests). |
| R6 | Stall cap | F4, Q-A2 A | accept, red team's residual taken | New keyword `max_pre_relax_timeouts: int \| None = None` on `run_ts_ensemble_detailed`/`run_ts_ensemble` (not a `TSEnsembleOptions` field, so v0.6.0 records serialise unchanged). The fallback runner passes **2**. After k `pre_relax_failed:PreRelaxTimeout` exclusions the ensemble stops sampling and keeps its members. `TSEnsembleRun.stall_cap_reached_bool` and the run record report it. **Report, not stop:** the seed is always a member once sampling begins, so the node succeeds. `graft_pre_relax_timeout` (before any seed) still stops. Bound per unit command: healthy max + 600 + 2 × 600 (HF3-BOUND). |
| R7 | Guard budget source | L1, HF-6 | accept; measured in slice 05 | The guard bounds a **stall**, not slow progress under load. Default remedy: a **load-scaled wall budget**: `effective = 600 × max(1, load1 / n_cpu)` from `os.getloadavg()` and `os.cpu_count()`, read once at guard entry, capped at **1200 s** (HF3-BOUND: a higher cap breaks the per-command bound; 1200 s is about 3× the 408.5 s healthy pre-relax measured under load). It is recorded per timeout row (`budget_s`, `load1`, `budget_kind: "load_scaled_wall"`). A process-CPU budget is rejected: xtb runs ~14 threads (HF-6), and a thread-normalised CPU clock needs per-thread accounting eta does not have. M13 (slice 05, first task) runs one GFN2 ensemble idle and one beside a loaded host. If the load-scaled budget still times out a healthy pre-relax under load, stop and report. ADR-0024 is unchanged; ADR-0048's budget becomes load-scaled (PROPOSED amendment). The slice 11/12 E2E unit commands use `timeout 5400` (1.5 × 1170 s healthy + 3 × 1200 s; HF3-BOUND); every other command keeps 3600. |
| R8 | geomeTRIC cwd | L2 | accept | Slice 06: `GeometricOptimizer` runs each geomeTRIC call inside a per-run `tempfile.TemporaryDirectory(dir=TMPDIR)` as cwd. It goes through a context manager that saves the cwd and restores it in `finally`, with a module lock (chdir is process-wide). Test: a real GFN2 pre-relax from a clean temp cwd leaves the cwd listing unchanged. Proof: `git status --porcelain` shows no `HT.v_*`. Until slice 06 lands, every engine command runs from a scratch cwd (heavy-run rule). |
| R9 | Contract placement | draft | accept | Enumeration and fallback models live in `core/enumeration_models.py` (core, pydantic, no numpy), so review needs no selectivity edge. `RunRecord`/`RunData` live in `eta_rxncat.review.run_data`, on their own version rule. |
| R10 | P3 charge rule | Q5 A | accept | `product_charge = template.total_charge + Σ charge_delta`. Multiplicity: declared, else inherited; two different declared values → `multiplicity_conflict`. Parity by electron count before the graft → `parity`. The charge sum is reported, never used. |
| R11 | Engine-work bound | F11 | accept | `EnumerationResult.projected_ts_searches` = Σ over `ok` candidates × selectivity-set TS nodes × eligible templates × (1 + `max_research`), an upper bound. The E2E gates N = 2. A ceiling waits for v0.8.0. |
| R12 | Run-data contract | F21, P11 | accept, amended | Strict writer model (`schema_version: Literal[1]`, `extra="forbid"`) and lenient reader (`extra="ignore"`, `schema_version: int`, refuses > 1). A **new enum value is a version bump**. The committed `src/eta_rxncat/review/schema/run_data.v1.schema.json` equals `model_json_schema()`, with a drift test whose message names the pydantic major. Ids are deterministic strings, referenced by id. Content as in the draft P11. Missing rows export `{"status": "missing", "stage_key": …}`; the exporter runs no engine. |
| R13 | Frames and stores | F16, F20, ADR-0016 | accept | Frames are payload-only, additive, optional. Stage keys are byte-equal to v0.6.0's. **Stores are forward-only** (a v0.6.0 reader refuses v0.7.0 rows; stated). The bridge appends `OptimizationFrame` after `engine.evaluate` returns, on the per-run tally, inside `try/finally`, so failure payloads keep their frames: every failure row written around a geomeTRIC run (timeout, `CoreDisplacementError`, `OptimizationFailedError`, `scf_convergence`, `engine_error`), through a `ContextVar` frame sink in `optimize/base.py` read in the caller's `finally` (R33). `ladder_step` comes from the caller. |
| R14 | Serialisation and HTML safety | F14 | accept (lead guidance) | One `canonical_run_data_json(run_data) -> bytes` (sorted keys, fixed float format `repr` of the rounded value, `< > &    ` escaped) writes BOTH `run_data.json` and the embedded `<script type="application/json" id="run-data">`, byte-equal. Data values are never HTML-escaped. JS writes text with `textContent`/`setAttribute` only. A Python scan of `eta-view.js` forbids `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `Function(`, string-argument `setTimeout`/`setInterval`. CSP meta: `default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'`, plus only what M12 shows 3Dmol needs, recorded. Hostile strings (`</script><img src=x onerror=…>`, `<!--`, U+2028) in a species label, an entry id and a provenance string are a byte-level unit test and an M12 known-answer item. |
| R15 | Host data | F15 | accept | `RunData` carries reason **codes** and allow-listed fields, never a `message`. Slice 13 gates a scan of the **real** bundle for absolute paths, `$HOME`, the username and the hostname. |
| R16 | Components | P17 | accept | `assets/eta-view.js` (MIT, ES2017, classic script, no build) exposes `EtaView` with `moleculeViewer`, `modeAnimator`, `trajectoryPlayer`, `energyPlot` (SVG) and `candidateTable`. Each is `(element, runData, id) -> {update, destroy}`, reads only `RunData` and keeps no global state. |
| R17 | JS-free audit floor | F18 | accept | `index.html` contains a Python-rendered static summary: per TS `n_imaginary`, frequencies, gates and banners (computed in Python from `RunData`), so the audit never rests on JS alone. M12 runs on stubs (slice 09) and on the real bundle (slice 13) with known answers: a pure named-bond stretch mode and a 3-frame trajectory. |
| R18 | Bundle size | F17 | accept | Decimation lives in `RunData` (`decimation_stride`, `n_frames_total` per trajectory); the full frames stay in the store. Both copies ship. Ceiling 25 MB for the bundle; M10 runs on a dry export in slice 08 (stop-and-report). |
| R19 | Graph split | F9, G9 | accept, residuals fixed | See "Graph split (slice 01)". `orchestrator/__init__.py` moves to selectivity. The selectivity edges include mapping, engines and thermo. `mapping/__init__.py` does not re-export the enumerator. Acyclic by construction. |
| R20 | 3Dmol supply chain | F19, M9 | accept | Pin 2.5.5 (HF-5). Slice 08 re-downloads the tarball, verifies `dist.integrity`, vendors `build/3Dmol-min.js` + `LICENSE` as `LICENSE-3Dmol.txt` + a banner inventory in `SOURCES.md`, and tests the sha256. CSP blocks the download paths. |
| R21 | Slice 08 split | F23 | accept | 08 = Python side; 09 = `eta-view.js` + M12. 14 slices. Slice 04 stays. |
| R22 | Bridge clean room | F22 | accept as note | Capture only in `calc_new`; read only geomeTRIC's output files (`xyzout`). ADR-0024's existing use of geomeTRIC's API is unchanged. |
| R23 | Closed findings | F5, F8, F10, F12 | accept | `ps` rule below; R5; R1; G7/G8 zero `engine_error`/`face_mismatch`. |
| R24 | R syn/anti | F6 | accept | New optional `orientation_centers: Sequence[int] = ()` on the ensemble call. Per centre, the sign of the signed volume over its three lowest-index neighbours in the seed's bonds is compared with the seed. A mismatch is excluded as `orientation_mismatch` (additive `_EXCLUSION_REASON` member, slice 02). Reported, not gated. The E2E passes the C7 product index. |
| R25 | Exo site | F7 | accept, measured | HF-1's rule, which picks H16 on both TSs. The endo-only fallback (exo ΔΔG‡ "not computed", TJ told, slice 11 continues endo-only) applies only if an exo unit fails. |
| R26 | Fixture names | draft | resolved | `tests/e2e/data/e2e5/v070_enumeration.yaml` and `v070_fallback.yaml` (no `t5_` prefix, which would collide with Human Fixture Tier 5). |
| R27 | README wording | lead (v0.6.0 docs) | accept | Slice 01 changes "unit weights" to "weights summing to 1" in `README.md` and in the matching claim in `tests/unit/test_identity.py`, together (the claims helper compares them). |
| R28 | UI track ADR | Placement A | accept | A PROPOSED ADR records the UI track and run-data contract plus the six proposed master-plan edits for TJ's edit. `PRDs/` is untouched. |
| R29 | Replan 1: slice 01 stopped on three plan points (builder stop report `qitem-20261126021113-a7828cef`) | — | resolved (lead) | **1. Ruff gate path.** A gate at `docs/prd/v0.7.0/.ruff.toml` does not stop the hook (the starter's `pyproject.toml` `[tool.ruff]` is nearer its files): the hook's command (`.agents/scripts/pre-commit:54`) `find docs/prd/v0.7.0 -name '*.py' -print0 \| xargs -0 .venv/bin/ruff check --force-exclude --` gave 69 errors and `format --check` 13 files; with the gate at `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` both and `ruff check .` exit 0. v0.1.0–v0.6.0 all keep it at `docs/prd/vX/Eta-RxnCat-vX/.ruff.toml`. The gate lives there only; slice 01's done-when adds the two hook-style commands. **2. Import scan scope.** `tests/e2e/**` (species_runner) imports selectivity modules (`tests/e2e/t4_flexible.py:45,55-56`, `test_t4_helpers.py:22`, `test_t4_mapped_helpers.py:12`) and `tests/unit/orchestrator/**` holds selectivity tests: the edge rule and stop-and-report apply to `src/` imports; test-file imports are listed in the proof and add no edge; globs unchanged. **3. Plan-vs-code rows.** PLAN_DISCREPANCIES is one row per plan-vs-zip hunk and the v0.7.0 zip row already reads "identical to PRDs/": the four "Plan-vs-code rows" bullets are appended verbatim as a "Plan-vs-code (v0.7.0)" section under its table; table, hashes and PD ids unchanged. HACF-Replan-Of: OPR.0.7.0.1. |
| R30 | Replan 2: slice 03 halted before code on a record-field contradiction (builder halt report `qitem-20261126030623-2ded8910`) | R10, Q5 A | resolved (lead rulings A-D) | **A.** `GraftRecord` gains `whole_input_charge_sum_holds_bool: bool \| None = None` (additive, reported, never used); slice 03 touches `core/enumeration_models.py` and its unit test; the core ledger description (1973/2000) is not changed. **1.** `multiplicity_conflict` is unreachable with one site: a private helper over the declared values, tested directly; public reach in slice 04. **2.** `site_atom_deleted` is emitted from slice 04; no slice-03 test. **3.** "Templates no site lists are copied unchanged" means templates of uncovered nodes; an unlisted template of a covered node is dropped (equal-composition rule), with no record or reason, and named on the `ok` candidate's `detail` as `dropped_unlisted:<node>/<template>,…`; no new refusal reason. **4.** `max_research` is a keyword on `enumerate_candidates` and `projected_ts_searches` (default `TSEnsembleOptions().max_research`); a TS node in several selectivity sets counts once. **5.** `max_candidates` is enforced from slice 04. **7.** `AlignmentError` and a wrong-length fragment order → `graft_input`; every order raising → the first listed order's reason. **D.** Frozen atoms: on a covered node, every stage's `frozen_atom_indices` (node `stages`, else the graph's `default_stages`, then written to the node) is remapped per eligible template through `index_map`; a frozen index in `template.delete` (no image) refuses that graft `graft_input` before `graft` (graft's own rule for deleted active/core atoms); eligible templates with different images → `inconsistent`, `frozen_index_mismatch:<node>`; uncovered nodes and `default_stages` unchanged. HACF-Replan-Of: OPR.0.7.0.3. |
| R31 | Replan 3: slice 04 is silent on `frozen_atom_indices` (resolve's R30 note) | R30.D | resolved (lead rulings 1-3) | **1.** Frozen atoms compose through every site's graft per template, in site order, as later-site atoms do: before site k's graft on T a frozen index must be in site k's remapped `keep`, else that (node, T) is refused `graft_input` before `graft` (R30.D at every site; `site_atom_deleted` decided first); after it each index is remapped through that graft's own `index_map`; differing composed images across eligible templates → `inconsistent`, `frozen_index_mismatch:<node>`. No new reason or status; no contract change. **2.** Slice 03's audit carry-forward (reading 2): the full-entry-multiset branch of the cross-node invariant gets its code and test in slice 04. **3.** The enumerator ledger description (1989/2000) stays <= 2000 after slice 04, by `--description-file` / `apply-review`. **4.** Full entry multiset = the union reading: each set's TS/pathway entry multiset equals the union of its covered reactant nodes' entries; split reactants pass. **5.** After site k refuses (node, T), later sites skip it and record nothing; a template is eligible only if every site covering its node lists it, else dropped and named in `dropped_unlisted:<node>/<template>` (sorted, unique). No new reason or status. HACF-Replan-Of: OPR.0.7.0.4. |
| R32 | Replan 4: multi-site forming-bond seeding (slice 04 audit, observed item (b)) | R2 | resolved (lead ruling) | A later site can delete an earlier site's forming-bond or core atom: each `GraftRecord` checks only its own `forming_bonds`/`constrained_core`, and its `mapped_forming_bonds`/`constrained_core_product_indices` are in that graft's product space, so R2's "both atoms kept" held per graft, not for the final product. **Slice 05 owns it; slice 04's code and core are not reopened (core 1973/2000).** `enumerated_pathway_inputs` takes the node's `ok` records for the reference template (`template_id` minus `__<candidate_id>`) in `candidate.records` order (site order), maps each record's two lists into the final product through every later record with the public `map_template_indices`, and refuses with `FallbackInputError` `multi_site_seed_atom_deleted` (node, template, both site ids, the index) when one raises `EnumerationError`. One record: its lists verbatim (today's seed and stage keys, pinned). Several: forming bonds concatenated in site order, unordered duplicates dropped; core = sorted union. `run_ts_with_fallback` derives every eligible template's inputs before its first engine call, so the refusal costs 0 engine calls and is not on the R4 allow-list. The single-site E2E (slices 11-12) is unaffected. HACF-Replan-Of: OPR.0.7.0.5. |
| R33 | Replan 5: slice 06 halted before code (builder halt report `qitem-20261126043922-a61f5c38`): P-RFO step geometry vs the ts_opt key; M11 needs a missing field | G10, R13, M11 | resolved (lead rulings 1-4) | **1. Option B.** `prfo.py` is not edited: its sha256 is `opt.version` (`src-897c4e19cb4e738a`) in the ts_opt key, recorded in 13 promoted fixtures under `tests/fixtures/v0.5.0`/`v0.6.0` (no ACCEPTANCE_RESULT.json records it), so A would change TJ's promoted data. A recording engine in `orchestrator/ts.py` around the `CountingEngine` fills `TSStep.coordinates_angstrom`: in prfo.py at 897c4e19 the only `hessian=False` evaluation is the trial point, once per iteration, appended as `history[k]` with no engine call between, so the k-th `hessian=False` call is step k. Checked exactly (count, energy, max gradient) after the search, else a private code-fault error; `_source_identity().version` is pinned by a test. **2.** `OptimizationFrame.accepted_bool: bool \| None = None` (additive, omitted when None); slice 06 touches `core/optimization_models.py` and `tests/unit/core/test_frame_fields.py`; core ledger description (1973/2000) not changed. Each step's `optim.xyz` frames match bridge frames at <= 1e-6 Å max |Δ| (M11: 5.0e-11 matched, >= 5.3e-4 neighbours) → True, others False ("other engine evaluations (trial points, Hessian displacements)"), unreadable or unmatched → None. **3.** M11's second (forced-ladder) GFN2 command is part of M11; its table is the measured outcome. **4.** Frame sink per R13; ts_opt failure rows carry the recorder's frames too. HACF-Replan-Of: OPR.0.7.0.6. |
| R34 | Replan 6: slice 13 (not started) cannot bundle every run through one `--record`/`--store`, and its gates left M10, fresh output, engine-call count, browsers and the Phase 3 packet open (slice 11 execute `qitem-20261126122127-46a505c5` and audit `qitem-20261126124011-8a25256f`; slice 12 writes a fresh store) | G13, R15, R17, R18, M10, M12 | resolved (lead rulings 1-8) | **1. One bundle, no `src/` change.** The runs live in four stores (slice 11's and slice 12's three, one per unit) and share unit ids across them (`ethyl|endo|<xtb>`), so no single `RunData` holds them. Coverage is gated per store. The bundle is one root folder: one sub-bundle per bundled (record, store) pair written by the unchanged `eta-rxncat review-bundle`, a harness-written static root `index.html` (CSP, no script; links, gates, strides, sizes) and a root `MANIFEST.sha256`. No row is copied and no store merged. Slice 13 moves to node `eta_rxncat_species_runner` (owner of `tests/e2e/**`; 1979/2000). **2. M10.** `decimation_stride` > 2 on any `ts_search` trajectory, read from each sub-bundle's `run_data.json`, is a stop-and-report, tested. R18's 25 MB ceiling applies per sub-bundle; the total is reported (lead-accepted). **3.** Both output roots must be absent or empty; non-empty is refused, never wiped. Build and gate in scratch, then copy to `tests/candidate_outputs/v0.7.0/review/`. **4.** 0 `Engine.evaluate` calls, unchanged store row counts, no `missing` entry. **5. M12.** Gate: installed Chrome and Playwright Firefox; a Mozilla release Firefox run is optional (TJ's call). **6.** The Phase 3 row carries the slice 11 audit packet and slice 12's fallback results per construct (graft time per lead ruling A: rank-1 graft refused `alignment_rmsd`, a one-attempt `FallbackRecord`; run time: rank 1 `fell_through`, rank 2 `chosen`); the lead sends it to advisor-lead@kernel, tag `question-for-tj`. **7.** Builder proof `proof/13-execute.md`, never a QA verdict. The acceptance record derives from evidence records, never from candidates. **8.** Slice 13 runs no engine unit: `timeout 3600` throughout. Slice 14's seat rule now states 5400 for a G7/G8 unit command and 3600 otherwise (R7). Slice 12 is not edited. HACF-Replan-Of: OPR.0.7.0.13. |
| R35 | Replan 7: TJ's Phase 3 findings on the first bundle (TS1a_n__ethyl sample `1f64216a4471`; pre-push minimum `071c077d750a`). Diagnosis `~/.hacf/eta-rxncat-hacf/evidence/v070-diag/DIAGNOSIS.md`; TJ `qitem-20261126151741-216f0468b8ca13cd` + `qitem-20261126151838-e190808aa4d1ce77` (A+, all in v0.7.0) | G7, G8, G12, G13, R4, R6, R12, R17, R34 | resolved (TJ); Q-R7a/b answered A/A | **Measured** (read-only, `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7/MEASUREMENT.md`): sample 6's start puts ethyl H21 0.438 Å from diene C4; its pre-relax made C4–C17 and C0–H21 and broke C17–H21, kept at the TS (TJ's reading confirmed). Over all 121 starts (hashes verified), d < 1.3 × Σr_cov for a pair ≥ 3 bonds apart rejects 53, every one already excluded (the UMA stall included), and 0 of 68 seeds/members/merged (used ≥ 1.543, rejected ≤ 1.286). An absolute-Å cut cannot separate them. Topology changed at pre-relax/TS for sample 6 only. **Slices** (before the verdict): **15** (selectivity, core additive) `seed_checks` keyword: clash before any engine call → `seed_clash`; `bond_changed:pre_relax`/`:ts`; graft close contacts → `seed:seed_clash`; three new R4 fall-through reasons; `SeedCheckDetail` omitted when None. **16** (review; species.py; `unit_record`) dispositions on every row, used/not-used groups, `TSIdentity` with a banner on identity failure; `record_version` and RunData `schema_version` stay 1 (optional keys, unreleased, no enum value added). **17** reruns all 11 units + 4 scores on store copies in `v070-replan7-runs/`; under A/A 0 new rows and dG‡/ddG‡ equal to 9fdba68's; old candidates `git rm`'d, fresh ones candidate-only. **18** fresh bundle through slice 13's harness retargeted, the G15 gates, M12, the record re-derived, the Phase 3 re-review row. **14** re-pointed: after 18 and TJ's re-promotion; C1 `e641ba1` stands. Promotion 9fdba68 stood until TJ re-promoted (ef9225e, 2026-11-27). HACF-Replan-Of: OPR.0.7.0.14 (new OPR.0.7.0.15-18). |

### PROPOSED lore (this mission; TJ approves with `/hyper-lore-approve`)

- ADR-0049: run-data JSON v1 and the UI track, with placement A as proposed master-plan changes (R12, R14, R16-R18, R28).
- ADR-0050: the fallback allow-list (R4, R5); relates to ADR-0045.
- ADR-0051: the stall cap reports and the load-scaled budget (R6, R7); amends ADR-0048's budget, ADR-0024 unchanged.
- ADR-0052: the EnumerationPlan beside schema 1, rank over RMSD, the cross-node invariant (R2, R3, R10).
- ADR-0053: payload-only frames, forward-only stores, the geomeTRIC temp cwd (R8, R13).

### Seed deviations (from Draft rev 3)

- The P5 allow-list is replaced by R4 (HF-4). `TS_VALIDATION_REASONS` is not a `failed_reason`.
- P10 `stall_cap` stops → reports (R6); the cap is a keyword, not a `TSEnsembleOptions` field.
- §6/§7 "scorer-side refusal" → runner-side only (R3).
- Draft slice 08 → slices 08 + 09 (R21). The old 09–13 become 10–14.
- The `t5_` fixture names → `v070_` (R26).
- Draft M4's graft-time construct "element mismatch → `graft_input`" → wrong-H alignment →
  `alignment_rmsd` (HF-2). It exercises the new eligibility gate; `graft_input` stays a unit test.
- New: R7 (load-scaled guard), R8 (temp cwd), R24 (orientation), R27 (README wording).
- Replan 1 (R29): slice 01's ruff gate moves to `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` with
  hook-style checks; its import scan's edge rule covers `src/` imports only; the plan-vs-code
  bullets go in a section under the PLAN_DISCREPANCIES table.
- Replan 2 (R30): slice 03 also touches core for one additive `GraftRecord` field; its builder
  readings, the dropped-template detail and the frozen-index remap are written into the slice.
- Replan 3 (R31): slice 04 composes frozen atoms through every site's graft per template, carries
  slice 03's entry-multiset branch (union reading), rules site sequencing per template, and caps
  the enumerator description at 2000.
- Replan 4 (R32): slice 05 composes every covering site's forming bonds and core into the final
  product with `map_template_indices` and refuses `multi_site_seed_atom_deleted`; R2's "both atoms
  kept" now holds for the multi-site seed.
- Replan 5 (R33): slice 06 fills P-RFO step geometry outside `prfo.py` (keys unchanged), adds
  `OptimizationFrame.accepted_bool` in core, records M11 as measured, and keeps frames on every
  failure row through a frame sink.
- Replan 6 (R34): slice 13 bundles one sub-bundle per (record, store) pair over four stores under
  one root page and manifest (no `src/` change), gates M10 on the real `run_data.json`, refuses a non-empty output,
  counts 0 engine calls, gates M12 on Chrome + Playwright Firefox, and carries the Phase 3 packet.
- Replan 7 (R35):
  - new slices 15 (seed clash and unintended-bond checks), 16 (review dispositions and TS
    identity), 17 (rerun all 11 units on store copies) and 18 (fresh bundle, record, Phase 3
    re-review);
  - slice 14 now waits for slice 18 and TJ's re-promotion; its C1 `e641ba1` stands.

### Graph split (slice 01; after the base only; never hand-edit `architecture.yml`)

1. **Before:** run `python3 .agents/scripts/hyper_ledger.py show` and save it. Also write, per node,
   the glob list and the matched files (`git ls-files` matched by each glob), plus the **union**.
2. **Narrow species_runner:**
   - `ensure-node --id eta_rxncat_species_runner --files` with:
     - `src/eta_rxncat/orchestrator/species.py`, `ts.py`, `reaction.py`, `barrier.py`,
       `report.py`, `counting.py`;
     - `tests/unit/orchestrator/**`, `tests/e2e/**`;
     - `tests/candidate_outputs/v0.3.0/**`, `v0.5.0/**`, `v0.6.0/**`, `v0.7.0/**`.
   - `tests/e2e/**` stays the shared E2E harness glob; new nodes claim no E2E files.
3. **New selectivity node:**
   - `ensure-node --id eta_rxncat_selectivity --dimension Module --allow-shared --files` with:
     - `src/eta_rxncat/orchestrator/__init__.py`, `selectivity.py`, `ts_ensemble.py`,
       `_deadline.py`, `ts_fallback.py`;
     - `tests/unit/orchestrator/test_selectivity_*.py`, `test_ts_ensemble.py`,
       `test_deadline.py`, `test_ts_fallback*.py` (shared with species_runner's test glob; recorded).
   - `--associated-file src/eta_rxncat/orchestrator/selectivity.py`.
4. **New enumerator node:**
   - `ensure-node --id eta_rxncat_enumerator --dimension Module --allow-shared --files` with
     `src/eta_rxncat/mapping/enumerator.py` and `tests/unit/mapping/test_enumerator*.py`. These
     overlap mapping's `mapping/**` globs; the overlap is recorded, and mapping's globs are not
     narrowed.
5. **New review node:**
   - `ensure-node --id eta_rxncat_review --dimension Module --files` with
     `src/eta_rxncat/review/**` and `tests/unit/review/**`.
6. **Edges** (`set-edges`, cycle-checked):
   - selectivity → species_runner, core, conformers, optimize, store, mapping, engines, thermo;
   - enumerator → mapping, core;
   - review → core, thermo, store;
   - cli → review.

   species_runner keeps its edges and gains none into selectivity.
   **Before step 6,** run an import scan (`grep -rn "eta_rxncat\.\(orchestrator\|mapping\|review\)"`
   over each node's files) and attach it to the proof. Any import **in a `src/` file** that
   contradicts these edges is stop-and-report. Test-file imports (`tests/e2e/**` and
   `tests/unit/orchestrator/**` into selectivity modules) are listed in the scan and add no edge;
   globs unchanged (R29).
7. **Descriptions:** compress core and species_runner to ≤ 1800 chars, and write the three new ones
   (≤ 1800), each by `--description-file`.
8. **Review patch:** `apply-review` (2000-char cap; it stamps `audit:<slice>`).
9. **Index and updater:** `python3 .agents/scripts/hyper_codegraph.py index`, then
   `hypergraph_updater.py --from-diff <Start> --apply` **once**.
10. **After:** take the counts again. The union of matched files equals the before union, plus only
    the new files of this slice. No file is unowned. `hyper_ledger.py validate` passes. Record both
    count tables in the proof.

### Contracts (slice 02)

- **`core/enumeration_models.py`** (`CoreModel`, units in names, no numpy; exported from
  `eta_rxncat.core`):
  - `SiteTemplateMap(node_id, template_id, template: AtomMappingSpec, constrained_core,
    forming_bonds: list[tuple[int, int]])`.
  - `EnumerationSite(id, maps: list[SiteTemplateMap])`.
  - `LibraryEntry(id, site_id, fragment: MolecularState, fragment_orders: list[list[int]] (≥ 1),
    fragment_delete, charge_delta: int = 0, multiplicity: PositiveInt | None = None)`.
  - `SelectivitySet(id, pathways: list[PathwaySpec(pathway, node_id, expected_face)],
    reactant_node_ids)`.
  - `EnumerationPlan(reference_graph, sites, library, selectivity_sets, max_candidates:
    PositiveInt)`.
  - `GraftRecord`:
    - ids; `status` (`ok` | `refused`) and `reason`;
    - `order_rmsds_angstrom`, `chosen_order_index`, `alignment_rmsd_angstrom`;
    - `min_interatomic_distance_angstrom`, `close_contact_count`;
    - `index_map`, `product_charge`, `product_multiplicity`;
    - `mapped_forming_bonds`, `constrained_core_product_indices`;
    - `whole_input_charge_sum_holds_bool: bool | None = None` (added in slice 03 by R30; reported,
      never used, per R10).
  - `EnumeratedCandidate(candidate_id, entry_ids_by_site, status: Literal["ok", "unmappable",
    "inconsistent"], detail, graph | None, records)`.
  - `EnumerationResult(candidates, max_alignment_rmsd_angstrom, projected_ts_searches)`.
  - `FallbackAttempt(template_id, rank, outcome: Literal["chosen", "fell_through", "stopped"],
    reason, wall_time_s)` and `FallbackRecord(node_id, attempts, chosen_template_id, stop_reason)`.
- **Frame fields:**
  - `OptimizationFrame(coordinates_angstrom, energy_hartree, max_gradient_hartree_per_bohr,
    ladder_step, accepted_bool: bool | None = None)` (`accepted_bool` added in slice 06 by R33;
    omitted when `None`);
  - `OptimizationResult.frames: list[OptimizationFrame] | None = None`;
  - `TSStep.coordinates_angstrom: list[list[float]] | None = None`.
- **`_EXCLUSION_REASON`** gains `orientation_mismatch` (additive).
- **Closed refusal set:** `graft_input`, `graft_clash`, `alignment_rmsd`, `composition_mismatch`,
  `parity`, `multiplicity_conflict`, `multi_component_template`, `site_atom_deleted`,
  `forming_bond_deleted`.
- **Functions:**
  - `enumerate_candidates(plan, *, max_alignment_rmsd_angstrom)` and `map_template_indices` in
    `mapping/enumerator.py`;
  - `run_ts_with_fallback` and `enumerated_pathway_inputs` in `orchestrator/ts_fallback.py`;
  - `export_run_data` and `canonical_run_data_json` in `review/`;
  - `write_review_bundle(run_data, out_dir)` in `review/bundle.py`;
  - the `review-bundle` subcommand in `cli.py`.

### Heavy-run rule (normative for every engine slice)

- **A blocking host check before each GPU/engine command,** as a separate call or a loop that exits
  non-zero; never echo-then-run. The output is kept in the proof. It checks:
  1. `nvidia-smi`: no compute process (python/xtb/torch);
  2. `MemAvailable` ≥ **12 GiB** (UMA unit peak, HF-3);
  3. `ps`: no other eta E2E/pytest/xtb, and no process from any rig/user with nice < 10 using
     ≥ 100 % CPU or ≥ 2 GiB RSS. A niced (≥ 10) background job may run alongside, per the lead's
     2026-11-26 ruling, and is logged.
- **One engine and one (R × pathway) unit per command,** re-checked between units, under
  `timeout 3600`, except the slice 11/12 E2E units, which use `timeout 5400` (HF3-BOUND, R7). A
  timeout is stop-and-report.
- **Environment:** `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`,
  `ETA_RXNCAT_ACCEPTANCE=1`, `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`, all asserted in the
  proof.
- **Working directory:** every engine command runs from a scratch cwd (until R8 lands, and after,
  as defence).
- **Other rigs:** never run beside the lead's announced quiet-host holds (e.g. Metis timing).

### Starter discrepancies (DV rows for `docs/prd/v0.7.0/DISCREPANCIES.md`, slice 01)

The zip has 38 files; 5 differ from v0.6.0's (the plan copy, `pyproject.toml`, `__init__.py`, the new
`mapping/enumerator.py`, the new `tests/unit/test_v070_enumerator.py`).

| Row | Starter | Starter does | eta v0.7.0 |
|---|---|---|---|
| DV-01 | plan copy | equals the authoritative plan (sha256 `ea483e29…3cb6`) | PLAN_DISCREPANCIES: agrees; no new PD row |
| DV-02 | `SubstituentCandidate` | one fragment `AtomMappingSpec` | `LibraryEntry` + per-template `SiteTemplateMap` → `GraftSpec`, with `fragment_orders` |
| DV-03 | `charge_delta` | `charge = template.charge + delta`; multiplicity copied | declared delta/multiplicity, parity refused, cross-node check |
| DV-04 | `select_best_template` | reorders by lowest RMSD | declared rank; RMSD is a gate |
| DV-05 | after the graft | identity keep + alignment `[0, 1, 2]` | keeps `index_map` |
| DV-06 | models | `template_id` / `priority_rank` / `structure` / `stoichiometry_multipliers` | schema 1 `id` / `rank` / `components` |
| DV-07 | template loop | silent `continue` on a count mismatch | recorded refusal |
| DV-08 | `target_node_ids=None` | grafts every node | only declared (node, template) pairs |
| DV-09 | — | no multi-site | Cartesian product with a cap |
| DV-10 | `pyproject.toml` | `version = "0.7.0"`, `ruff>=0.7.0` | bump in slice 14; ruff pin not adopted |

Plan-vs-code rows (appended verbatim as a "Plan-vs-code (v0.7.0)" section under the
`docs/prd/PLAN_DISCREPANCIES.md` table; table, hashes and PD ids unchanged; R29):
- "propagating … deltas" is read as declared (Q5 A).
- "rank/select … fallbacks" is R4/G5 (Q-A1 B).
- v0.8.0 keeps general fallback.
- The review bundle and run-data JSON are TJ additions (rows `…4331bdd0`, `…a8e19bbe`), with the
  plan's item 18 re-placed by placement A (PROPOSED ADR).

### Proposed master-plan changes (PROPOSED ADR, R28; `PRDs/` untouched)

1. **v0.7.0:** add the static review bundle over run-data JSON v1, reusable components,
   `eta-rxncat review-bundle`, and vendored 3Dmol.js (BSD-3). Title "… & Phase 3 Review Bundle".
2. **v0.8.0:** a read-only reaction-network view over run-data JSON, reusing the v0.7.0 components
   (Cytoscape.js MIT is a candidate; licence re-verified then).
3. **v0.9.0:** conformer, frequency and topology views (static).
4. **v1.1.0:** interactive `eta ui`. A local backend opens the browser, with network
   view/editing, graft atom selection exporting `ReactionGraph` YAML/JSON, and conformer/frequency
   comparison.
5. **v1.2.0:** desktop packaging (pywebview BSD-3 recommended; final choice later), with
   notarization and signing.
6. **Known Constraints:** UI assets are vendored, pinned, licence-verified and permissive only;
   never a core runtime dependency.

### Blast radius

- **Touched nodes:**
  - core: models, frame fields, exclusion reason;
  - mapping: the enumerator, overlap recorded;
  - species_runner: narrowed; README claim test;
  - selectivity (new): fallback, guards, budget source;
  - optimize: P-RFO step geometry, bridge frames, temp cwd;
  - review (new);
  - cli: `review-bundle`;
  - scaffold: `pyproject.toml` package data for `review/assets` and `review/schema`, README.
- **Untouched:** engines, conformers, thermo, store.
- **Replan 7 (R35):**
  - selectivity: `ts_ensemble.py`, `ts_fallback.py`;
  - core: `selectivity_models.py`, `enumeration_models.py` (additive);
  - review: `run_data.py`, `export.py`, `bundle.py`, `eta-view.js`, the schema;
  - species_runner: `orchestrator/species.py`, `tests/e2e/**`, candidates;
  - scaffold: README and the record.
- The lead re-measures `hyper_ledger.py impact` after slice 01.

### Execution checklist (build order; the lead's work queue)

The slice table at the end of this document, in build order 01 → 13, then 15 → 18, then 14 (R35).
Slice 11 starts only if HF-3 is filled (it is: see §2). Slices 11–13 and 17 run engines only under
the heavy-run rule. Slice 17 waits for TJ's Q-R7a/b answer (or the lead's go on A + A), and slice 14
waits for TJ's re-promotion of slice 17's candidates.

Replan 7 time estimate (R35), as seat time per slice (build + audit) and GPU:

| slice | seat time | GPU |
|---|---|---|
| 15 | 2.5 h + 0.75 h | 0 |
| 16 | 3.5 h + 1 h | 0 |
| 17 | 1.5 h + 0.75 h; about 45 min of wall time for 15 commands, all store hits | about 10 min under A + A |
| 18 | 2.5 h + 1 h | 0 |

- About 13.5 h in sequence, plus TJ's re-review, then the rest of slice 14 (about 1.5 h).
- Under Q-R7b B, add about 1.5 h of wall time and about 1 h of GPU.

### Dependencies

- **No new Python dependency.** Validation is by pydantic; no `jsonschema`.
- **Vendored output assets:** 3Dmol.js 2.5.5 (BSD-3) and eta's `eta-view.js` (MIT). No JS
  toolchain.
- **geomeTRIC** stays in the `opt-geometric` extra (ADR-0023).

## 6. Negative Constraints

- **DO NOT** change `ReactionGraph` schema 1, any existing fixture, or `score_selectivity`.
- **DO NOT** infer a product charge or multiplicity (Q5 A), or reorder templates by RMSD over
  declared rank, or drop a refused template without a reason.
- **DO NOT** add a stage kind or cache-key field, or let frames change a key or a result.
- **DO NOT** fall through outside the R4 allow-list. Never let a live `EngineError` fall through.
- **DO NOT** run a charged/open-shell candidate on an engine in v0.7.0.
- **DO NOT** truncate above `max_candidates`.
- **DO NOT** run two engine commands at once, run beside another rig's non-niced heavy process, skip
  the blocking host check, or run an engine from the repo root.
- **DO NOT** re-compute anything or run an engine in the review writer.
- **DO NOT** load anything over the network, or use a server, `fetch()` or ES modules.
- **DO NOT** let a view read anything but `RunData`, or add a second data contract.
- **DO NOT** HTML-escape data values, or use `innerHTML`-class sinks.
- **DO NOT** put messages, timestamps, absolute paths, usernames, hostnames or secrets in any bundle
  file.
- **DO NOT** vendor copyleft, unpinned or unverified assets.
- **DO NOT** change a `RunData` key's meaning, unit or type, or add an enum value, without bumping
  `schema_version`.
- **DO NOT** import ASE or Sella, vendor geomeTRIC, or open/read/patch geomeTRIC source.
- **DO NOT** open Eta_Scripts/nMap or any TS-optimizer/conformer-search source.
- **DO NOT** copy starter code.
- **DO NOT** hand-edit `architecture.yml`. Run the updater once per slice.
- **DO NOT** promote a candidate, or read `tests/candidate_outputs/` or `spec/archive/` in stage work.
- **DO NOT** touch `missions/release-0.6.0/` or `PRDs/`.

## 7. Risks & Mitigation

| Risk | Mitigation |
|---|---|
| A crash presented as a template result (F1) | R4 allow-list; real-class and cached-replay tests; Literal enumeration test. |
| Wrong face in a fallback slot (F2) | R2 expected face, checked before and after the search; measured separation. |
| R/H swap at C7 (F6) | R24 orientation exclusion, reported. |
| Mixed-coverage candidate (F3) | G3 invariant; derived `reactant_key`; runner-side refusal. |
| Stalls (F4) and load-made timeouts (L1) | R6 cap reports; R7 load-scaled budget with M13 stop-and-report; per-unit commands; HF3-BOUND. |
| geomeTRIC files in the repo (L2) | R8 temp cwd + test; scratch cwd for every engine command. |
| Frames hard to read (M11) | Accepted-step labelling from `xyzout` if it matches; TJ row before slice 06 merges if neither labelling serves the audit. |
| Bundle too large (F17) | R18 decimation in the contract; M10 stop-and-report. |
| Hostile strings / host data in the bundle (F14, F15) | R14 canonical escaping, sink scan, CSP; R15 codes + real-bundle scan. |
| JS untested in CI (F18) | R17 static summary; M12 twice with known answers; TJ's Phase 3. |
| Contract drift (F21) | Strict writer + lenient reader; schema drift test; enum rule. |
| Vendored JS provenance (F19) | R20 integrity check, banner inventory, CSP. |
| Graph split corrupts node files (F9) | R19 sequence, import scan, union counts, updater once. |
| UI scope creep | Placement A; §3 and §6. |
| A clashing seed giving a junk saddle (TJ's Phase 3 finding) | R35: the clash check before any engine call, the bond check at the pre-relax and the TS, dispositions on the site, reruns and re-review. |

## 8. Success Metrics

- **G1–G4:** unit suites green.
  - Enumeration is byte-equal twice.
  - One test per refusal reason; ±1 and a doublet; mixed-coverage refused; core import isolation;
    projected count exact on a toy.
- **G5–G6:** exact attempt records.
  - `stopped:seed:engine_error` (live `EngineRuntimeError` through `run_transition_state`, and the
    cached replay).
  - `graft_pre_relax_timeout` stops.
  - `seed:face_mismatch_pathway` and validation failures fall through.
  - The Literal test; the charged refusal; the second run has 0 engine calls.
  - `stall_cap_reached_bool` on a fake staller, with members kept.
  - The load-scaled budget is recorded per timeout row.
- **G7 (per unit):** N = 2 `ok`; charge 0 / multiplicity 1; graft RMSD ≤ 0.15 Å, 0 contacts; G3;
  Σw = 1 within 1e-12; every member's face = the pathway's expected face; zero
  `engine_error`/`face_mismatch`; the rerun has 0 rows and 0 calls. Reported: ΔΔG‡ per R, members,
  stalls, time lost, `orientation_mismatch`, CPU/wall.
- **G8:** both constructs pick rank 2 with rank 1's reason (`alignment_rmsd`;
  `seed:face_mismatch_pathway`); zero `engine_error`; GFN2 gated.
- **G9:** new nodes; union preserved; ≤ 1800; acyclic; updater once.
- **G10:** frames on new rows (P-RFO count = `TSStep`s, `prfo.py` unedited; geomeTRIC count as M11
  measured, `accepted_bool` per frame); every failure payload keeps frames; keys equal to v0.6.0's; old rows load; cwd clean.
- **G11–G12:**
  - Schema drift test; lenient reader loads an unknown key; strict writer refuses it; version 2
    refused.
  - Embedded == file bytes; hostile strings inert at the byte level; sink scan clean; CSP present.
  - Only vendored assets referenced; deterministic bytes; no host data.
  - Banner on 2 imaginary modes (static summary); 3Dmol sha256 and licence pinned; M12 stub evidence.
- **G13:** the bundle covers every G7/G8 run; `MANIFEST.sha256` verifies; size ≤ 25 MB or
  decimation stated; real-bundle scans clean; every trajectory has frames; M12 on the real bundle;
  TJ's Phase 3 closed before slice 14.
- **G14:**
  - the sample-6 known answer: (4, 21), 0.438 Å, ratio 0.409;
  - fake-engine tests per check, with 0 engine calls for a rejected sample;
  - old fixtures re-serialise byte-equal; `seed_checks=False` is unchanged;
  - slice 17 under A + A: 0 new rows, every dG‡/ddG‡ equal to 9fdba68's, `seed_clash` exactly the
    measured set, 0 stalls.
- **G15:**
  - every row carries a disposition (none `not_recorded` in the fresh bundle) and sits in its group;
  - `TSIdentity` on every TS block, with the banner on an identity failure;
  - the known answers for `1f64216a4471` and `071c077d750a`;
  - M12 on stubs and on the real bundle;
  - TJ re-promotes before slice 14.
- **Release:** `uv run ruff check .`, `uv run ruff format --check .` (with the `spec/archive`,
  `spec/process` excludes), `uv run mypy` and `uv run pytest` exit 0. E2E skips = 0 under
  `ETA_RXNCAT_ACCEPTANCE=1`.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.7.0.1 | slices/01-starter-graph-split | Unpack the v0.7.0 starter as reference with its DV register, fix the v0.6.0 README 'unit weights' claim with its helper, and split the graph into selectivity, enumerator and review nodes by the mission's R19 sequence. |
| OPR.0.7.0.2 | slices/02-core-contracts | Add the enumeration, selectivity-set and fallback contracts, the optimization frame fields and the orientation_mismatch exclusion reason to core, all additive and numpy-free. |
| OPR.0.7.0.3 | slices/03-single-site-enumerator | Graft every library entry onto every declared (node, template) with eta's graft, choosing the lowest-RMSD fragment order, gating eligibility at the keyed RMSD, enforcing the charge rule and the cross-node invariant, and recording every refusal. |
| OPR.0.7.0.4 | slices/04-multi-site-product | Enumerate multi-site plans as a deterministic Cartesian product, refusing above max_candidates before any graft, remapping later sites per template through index_map, and refusing a site whose atoms an earlier graft deleted. |
| OPR.0.7.0.5 | slices/05-ts-seed-fallback | Add run_ts_with_fallback and enumerated_pathway_inputs, falling through only on the R4 allow-list, plus the ensemble guards: pathway expected face, orientation centres, a reporting stall cap and the measured load-scaled pre-relax budget. |
| OPR.0.7.0.6 | slices/06-frame-capture | Store every optimization's path: P-RFO steps gain their geometry and geomeTRIC runs gain bridge frames in success and failure payloads, run in a per-run temp cwd, with stage keys unchanged. |
| OPR.0.7.0.7 | slices/07-run-data-contract | Define RunRecord and the versioned RunData v1 contract with a strict writer, a lenient reader, a committed JSON Schema with a drift test and a canonical escaped serialisation, and export a run from the store without running an engine. |
| OPR.0.7.0.8 | slices/08-bundle-writer | Write the static offline review bundle from RunData with a JS-free static summary, a CSP, the canonical embedded JSON, vendored 3Dmol.js 2.5.5 verified against npm, and the eta-rxncat review-bundle command, with Python-side scans. |
| OPR.0.7.0.9 | slices/09-view-components | Write eta-view.js, five reusable framework-free components that render only RunData, and record the M12 browser smoke on stub run-data with known answers in Chrome and Firefox from file://. |
| OPR.0.7.0.10 | slices/10-e2e-inputs | Write the v0.7.0 E2E inputs: the Tier 4 endo/exo reference graph, the enumeration plan with the H16 site maps, expected faces and orientation centre, the two fallback constructs, and offline tests that pin the measured geometry. |
| OPR.0.7.0.11 | slices/11-enumeration-e2e | Prove the enumeration end to end: enumerate ethyl and n-propyl onto TS1a_n and TS1a_x and run each (R x pathway x engine) unit through run_ts_with_fallback on GFN2 then UMA, gating the mechanics and reporting dG dagger per R, stalls and time lost. |
| OPR.0.7.0.12 | slices/12-fallback-e2e | Prove the fallback end to end on GFN2: a rank-1 template refused at graft time and a rank-1 seed refused by the pathway face each fall through to rank 2, which yields the ensemble, with rank 1's reason recorded; UMA reported once. |
| OPR.0.7.0.13 | slices/13-review-bundle-and-record | Bundle every v0.7.0 E2E run for TJ's visual audit, gate the real bundle's hygiene and frames, repeat the M12 smoke on it, write the acceptance record from the evidence run records, and send TJ the Phase 3 row. |
| OPR.0.7.0.14 | slices/14-acceptance-verdict | After TJ's Phase 3 visual audit and promotion, run the verdict on both engines against the promoted outputs, document the review command and the run-data contract, and bump to 0.7.0. |
| OPR.0.7.0.15 | slices/15-seed-geometry-checks | Refuse a clashing start geometry before any engine call and exclude any TS whose pre-relax or search made or broke a bond outside the template's forming bonds, each with a recorded reason and detail, behind a seed_checks keyword the fallback runner turns on. |
| OPR.0.7.0.16 | slices/16-review-dispositions | Show on every review-site frequency row whether it fed the result and why not, group rejected rows apart from used ones, show each TS's identity numbers with a banner on any identity failure, and carry the endpoint disposition from the species runner into the run record. |
| OPR.0.7.0.17 | slices/17-rerun-units | Rerun all 11 v0.7.0 E2E units and the 4 score commands on copies of their stores with the seed checks and the new record fields, gate 0 new rows and unchanged dG dagger under the default rule, and land the fresh records as candidates after moving the old ones aside. |
| OPR.0.7.0.18 | slices/18-rereview-bundle | Bundle the rerun records with the fixed site through slice 13's harness retargeted to the replan-7 evidence, gate every row's disposition and TS identity, repeat M12, re-derive the acceptance record and draft TJ's Phase 3 re-review row. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
