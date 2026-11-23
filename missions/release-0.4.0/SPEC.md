---
id: OPR.0.4.0
mission: release-0.4.0
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope mission create)"
created: "2026-11-23"
intent: "Eta-RxnCat v0.4.0: a clean-room conserved-core structure mapper (quaternion alignment, ordered keep/delete/alignment atom surgery and charge/spin-aware single-substituent grafting) that turns a reference TS plus a fragment into a mapped TS guess, proved on TJ's TS1a_n to TS1b_n mapping."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0003, ADR-0004, ADR-0005, ADR-0007, ADR-0019, ADR-0023, ADR-0027, ADR-0028, ADR-0029, ADR-0030, ADR-0031, ADR-0032]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.4.0 — Conserved-Core Structure Mapper (nMap Clean-Room Rewrite)

## Intent

v0.4.0 is the fourth of ten versions. It adds `eta_rxncat.mapping`, a clean-room conserved-core
structure mapper:
- quaternion (Horn) superposition of ordered atom pairs;
- ordered keep/delete/alignment atom surgery;
- charge/spin-explicit single-substituent grafting, with close contacts and junction handedness
  recorded;
- a core-frozen pre-relaxation through v0.3.0's `Optimizer`.

From a reference transition state (the template) and a fragment, it builds a mapped TS guess.
v0.5.0 seeds its TS search from that guess.

The mapper is proved by tier-D tests and by:
- the checker-approved clean-room nMAP test vectors;
- TJ's M1 mapping: graft cyclobutene onto Liu's endo TS1a_n to make a TS1b_n guess, compared with
  Liu's own TS1b_n.

M1's outputs are committed as candidates for TJ's Phase 3 review. A verdict run after TJ's
promotion accepts v0.4.0.

- **Base:** the mission commit on main (parent `c3506e6`). `c3506e6` is the v0.3.0 release
  `18c1d1c` (pushed, tagged `v0.3.0`) plus the HACF v0.6.2 upgrade. The lead commits this mission
  on main, and that commit is Base. The builder cuts `feature/eta-rxncat-v0.4.0` from it.
- **Inputs compiled:**
  - `Draft_PRD.md`, sha256 `b148db22e5984f24d15b2c1bafecae0ab4ef91061c742b0238ef1a2bda248995`;
  - `RedTeam_Report.md`, sha256 `69dcea5dee3f3f988aeaabcb6808dee7cbb7953ab689023de54d4642a0198a02`
    (F1–F15, Parts A–C);
  - the clean-room nMAP behaviour spec, `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/NMAP_BEHAVIOUR_SPEC.md`,
    sha256 `a56c449b39e92eab23a766739e0bccce111619329ae4e066355876e35dee662d`, checker-approved
    (`CHECKER_REPORT.md` sha256 `be1de23c076a775bdbbd8ecf6a2400edada07a41ad0c99e347f3d597ad5e7006`),
    carried by the operator per `TRANSFER_LOG.md` (transfer 1, 2026-11-23T18:44:06Z);
  - the architect's comparison of that spec with the draft (row `qitem-20261123184521-43809941`).

  The draft and the red-team report are archived, and a restore copy of both is in
  `spec/process/eta-rxncat-v0.4.0-drafts/`. This SPEC is self-contained.
- **Author:** the decisions are TJ's (Thomas J. L. Mustard Ph.D.), quoted verbatim. The design
  resolutions are spec-resolve's, each logged in §5 "Resolved trade-off log".

### TJ decisions (verbatim; binding)

| # | Question | TJ, verbatim | Meaning here |
|---|---|---|---|
| Q1 | Clean room vs TJ's own Eta_Scripts/nMap code (row `qitem-20261123174816-79277143c4b9b81a`) | "Q1. I feel like this should spawn out into its own project a clean room rig and agents, skills, etc. But for now, let's implement this as you've specced. I will research and plan externally and come back to the auditor or the advisor with a fully fledged plan on a long-term clean room rig. There is some ownership by the university, my advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this clean room approach" | No eta seat opens, clones, fetches or searches Eta_Scripts or nMap, or asks the clean-room seats about code. Behaviour comes only from this SPEC, TJ's M1 spec and the approved documents in `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/`. |
| Q2 | PD-008: enumeration, constrained-core pre-relaxation, Rh(I) (5+2) | "Q2. (b)" | Core-frozen pre-relaxation is in v0.4.0. R-group/ligand enumeration and the Rh(I) (5+2) complexes move to v1.x. |
| Q3 | The v0.4.0 human fixture | "Q3. B" | TJ's M1 only. The barrier stays in v0.5.0. |
| Q4 | Graft input format | "Q4. A" | Template keep/delete. Alignment as ordered `[template, incoming]` pairs. Unaligned incoming atoms appended in their own order. Extended by R1 "B" below. |
| Q5 | Product charge and spin | "Q5. A" | Explicit product charge and multiplicity. Parity checked. The charge sum is reported, never used to infer. |
| Q6 | Numeric bounds | "Q6. A" | M1 forming-core RMSD to Liu's TS1b_n ≤ 0.10 Å. Graft regression 1e-10 Å. Relaxed graft regression \|ΔE\| ≤ 1e-5 Eh and heavy-atom RMSD ≤ 0.01 Å. |
| P1 / P2 | Red-team P1 (what M1 proves) and P2 (who fixes the atom map); TJ 18:44Z via the operator on `qitem-20261123184100-04bbd81fa6e1b2f1` | "P1 A / P2 A" | P1 A: the pure graft records its close contacts (it may clash; no error). The pre-relaxed candidate is gated on perceived bonded connectivity equal to Liu's TS1b_n's. Full-molecule RMSDs are reported. No new numeric bound. P2 A: the team derives the graft → TS1b_n atom map by a stated rule that never minimises the gated RMSD, and TJ confirms the map at Phase 3 with the candidates. |
| R1 / R2 (clean room) | nMAP spec §10 Q1 and Q3; TJ via the operator on `qitem-20261123184537-83b70f71682cfcd4` | "R1 B, R2 A" | R1 B: Q4 "A" plus an optional incoming delete list, empty by default. Paired incoming atoms are always dropped. R2 A: report a planar-pair flag, plus a handedness check across the junction (signed volume), checked against TS1b_n in M1. |

Standing TJ decisions that apply:
- Licence (11-22 14:57Z, verbatim): "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." Also (14:59Z): "It's fine that the engine MACE pulls in ASE just not the
  core." And P1 (11-23): "As long as the license does not taint the license of the entire repo."
- Q1 "A": the `PRDs/` plan is authoritative.
- Q2 "B": the starter is reference only, with a per-version `DISCREPANCIES.md`.
- Q3 amended: "Build, install, and run these autonomously as to move on to the next step/question."
- v0.3.0 R1 "R1. A": candidates are committed on the branch, and only TJ promotes them
  (ADR-0027).
- Q-E3: "Q3. B, but these may need updating as we define the YAML/JSON format."
- Q-E4: "Q4. A but the files attached can be used as reference." Index fix 1 (forming carbons
  `[1, 2, 3, 5]`) is approved.
- Q-E1 "A": T3 → v0.5.0.
- The author is "Thomas J. L. Mustard Ph.D.". Never push. `PRDs/` stays untouched.

## 1. Introduction & Goals

**Problem.** The plan's Hypothesis 1 (`PRDs/Eta-RxnCat_Living_Master_Plan.md` l.11): the forming
and breaking core of a TS barely moves when substituents change, "within ~0.1 Angstrom RMSD". So
a known TS can seed a new one by aligning a fragment onto the conserved core and swapping atoms.
Nothing in the repo builds such a structure yet, and v0.5.0 (Human Fixture 3, "with mapped
substituent") needs one. Plan l.42–43: "`PR #9 (feat/core-mapper)`: Implement quaternion Kabsch
alignment, ordered `keep`/`delete`/`alignment` atom surgery, and charge/spin-aware
single-substituent grafting."

**Solution.** A new package, `eta_rxncat.mapping`: MIT, numpy, with RDKit imported lazily and
only for bond perception.
1. `align`: Horn quaternion superposition. It is a proper rotation by construction. It refuses
   degenerate pair sets and reports planarity.
2. `graft`: ordered surgery.
   - Product order: template keep (keep order), then the fragment atoms that are neither paired
     nor in `fragment_delete`, in ascending fragment order.
   - Kept template coordinates are bitwise unchanged.
   - Charge and multiplicity are explicit.
   - Active and core indices are re-indexed.
   - It refuses an overlap floor (0.5 Å) and records close contacts, junction signed volumes and
     the planar-pair flag.
3. `relax`: core-frozen pre-relaxation through `Optimizer.minimize(frozen_atom_indices=…)`, with
   a named error if the core moves.
4. `report`: perceived bonds, core RMSD and junction volumes, used by the fixture.

**Audience.** TJ, as user and reviewer. The build seats. v0.5.0, which seeds P-RFO from the mapped
TS. v1.x, which enumerates by repeated single grafts.

**Goals (measurable):**
- **G1.** `graft()` returns a `GraftResult`:
  - the product order follows §5 "Algorithms" exactly;
  - kept template coordinates are bitwise the template's;
  - charge and multiplicity are the spec's;
  - `index_map` names every product atom's source.
- **G2.** `superpose()` returns det(R) = +1. Its RMSD matches an independent residual-based SVD
  Kabsch in the test file within 1e-10 Å on 1000 random non-degenerate sets.
- **G3.** On M1, the pure graft's forming-core `[1, 2, 3, 5]` RMSD to Liu's TS1b_n, under the
  stated map, is ≤ 0.10 Å (TJ Q6 "A"; measured 0.0498 Å).
- **G4.** Per recipe (xtb, UMA), the M1 pre-relaxation:
  - converges with the frozen core moved ≤ 1e-6 Å (max per-atom displacement, no superposition; R26);
  - gives a product whose perceived connectivity equals TS1b_n's under the map (TJ P1 "A");
  - has junction signed-volume signs that equal TS1b_n's, nonzero (TJ R2 "A").
- **G5.** Importing `eta_rxncat.mapping` or any of its submodules loads no `geometric`, `torch`,
  `pyscf`, `fairchem` or `rdkit` (F10). `eta_rxncat.core` still loads no numpy or RDKit.
- **G6.** The clean-room vectors 01–05 and 07 (07 eta-adapted, R18) reproduce at 1e-6 Å. Vector
  06 is refused with `AlignmentError`.

## 2. Confidence Mandate

**Score: 9/10.** Every red-team finding and every clean-room difference has a decision. TJ
answered every question the red team and the clean-room comparison raised (P1 A, P2 A, R1 B,
R2 A). The questions needed to reach 10 cannot be answered on paper. They are outcomes a run must
show, and each is a stop-and-report:
- whether the M1 pre-relaxation keeps TS1b_n's connectivity and junction signs (H-M5);
- whether xtb and UMA hold the frozen core to 1e-6 Å (H-M3; R26: xtb measured 4.19e-8 Å on M1).

A miss is a finding with its output, never a loosened bound.

### Host facts measured by resolve (2026-11-23)

Measured in scratch under `TMPDIR`. The XYZ files were taken from the builder's `XYZ_FILES`
literal with `ast.literal_eval`; the builder was never executed. Repo `.venv`, RDKit
`DetermineConnectivity` defaults.

| # | Fact | Value |
|---|---|---|
| HF-1 | sha256 of TJ's three M1 files | equal to the draft's: `TS1a_n.xyz` `c437537…f267`, `6_cyclobutene.xyz` `8b25312…e990`, `TS1b_n.xyz` `677d570…a457` |
| HF-2 | M1 alignment over the 4 pairs | RMSD 0.11573 Å, det(R) = 1. Pair elements match (C/C, C/C, H/H, H/H). |
| HF-3 | Pair-set shape (singular values of the centred set) | template C2, C3, H10, H11: 2.3735, 0.6312, 2.3e-16. Fragment: 2.2168, 0.7850, 1.0e-4. So the pair set is **planar** (RMS out-of-plane 1.2e-16 / 5.1e-5 Å) and far from collinear (RMS off-line 0.316 Å). |
| HF-4 | Perceived bonds | TS1a_n 18, cyclobutene 10, TS1b_n 21, pure graft 23, graft source graph 21 (§5 "Algorithms") |
| HF-5 | Close contacts in the pure graft | Perceived graft bonds absent from the source graph: exactly (0, 15) and (4, 16), both C…C, **1.9598 / 1.9611 Å**. This is the draft's 23-vs-21 (H-M2 closed). RDKit gives each H only one partner, so perception misses F1's H contacts: (0, 17) C…H **1.1218 Å** and (4, 20) C…H **1.1251 Å**. Under the R1 radius rule (1.3 × sum of RDKit covalent radii, over kept-template × appended pairs not in the source graph) the contacts are exactly those four. In TS1b_n the mapped C0…C15 is 3.0792 Å. The minimum interatomic distance 1.0782 Å is a real C–H bond. Junction bonds (2, 15) and (3, 16) are 1.5908 Å. |
| HF-6 | Element-preserving isomorphisms, source graph → TS1b_n graph | 32 maps; 4 distinct heavy-atom maps; forming-core RMSD is 0.0498 Å under two of them and 0.9637 Å under the other two. |
| HF-7 | The stated-rule map (lexicographically smallest, R2) | `[0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 7, 8, 17, 18, 19, 20]`. Under it: forming core 0.04976 Å, active `[0..5]` 0.04220 Å, full 0.7794 Å. The draft's full 0.5966 Å was the "best of 32" (RMSD-minimised, F3). |
| HF-8 | Junction signed volumes (R16 rule) | pure graft −0.0006 / −0.0006 Å³: **undetermined** (\|V\| ≤ 0.05), because the junction neighbours are pair atoms and the pair set is planar. The reversed-sense graft gives +0.0006 / +0.0006. TS1b_n under the R2 map: +0.8505 / −0.8505 Å³. |
| HF-9 | Horn quaternion vs residual-based SVD Kabsch, numpy, 1000 random sets of 3–29 points | \|ΔRMSD\| ≤ 4.4e-15 Å, \|ΔR\| ≤ 2.0e-14. Rigid copies give RMSD ≤ 6.3e-15 Å. (The red team measured thermo's `kabsch_rmsd` cancellation floor at 1.69e-7 Å, which is why it is not the reference.) |

## 3. Scope

### In scope
1. **Starter (slice 01).** Unpack `PRDs/Eta-RxnCat-v0.4.0.zip` (sha256 `6214b5e1a25f85a9efc6117f5d97ec7f7aa2db2c5a8a4098ea390fb5c48a0b62`,
   32 files) into `docs/prd/v0.4.0/` byte-identical (ADR-0007). Write
   `docs/prd/v0.4.0/DISCREPANCIES.md` with the DV and CR rows. Set PD-008 to `decided`. **No**
   change to any `PLAN_DISCREPANCIES.md` hash (R3).
2. **Core contracts (slice 02):** `GraftSpec`, `GraftResult`, `CloseContact`, `JunctionVolume`
   in `core/mapping_models.py`.
3. **`mapping.align` (slice 03):** superposition, pair-set shape, errors, the new
   `eta_rxncat_mapping` node, and clean-room vectors 01–03 and 06.
4. **`mapping.graft` and `mapping.report` (slice 04):** surgery, contacts, junctions, the planar
   flag, bond perception, core RMSD, and vectors 04, 05 and 07.
5. **`mapping.relax` (slice 05):** core-frozen pre-relaxation with `CoreDisplacementError`.
6. **Fixture M1 (slice 06):** TJ's three XYZ files and their provenance, the provisional M1
   YAML with the stated-rule map, tier-D checks, the xtb and UMA pre-relaxations, and committed
   candidates.
7. **Acceptance record (slice 07)**, then the **Phase 3 gate** (TJ), then the **verdict and the
   0.4.0 bump (slice 08)**.
8. Docs: README Features/Roadmap derived from the record. CHANGELOG is the scribe's.

### Out of scope
- R-group/ligand library enumeration and multi-site grafting in one call: v1.x (TJ Q2 "(b)").
  The PRDs/ plan still lists enumeration at v0.7.0 (PR #14). That is a roadmap note for the lead
  and TJ; this mission does not touch the plan (R24). A double graft is two single grafts.
- The Rh(I) (5+2) reference complexes: v1.x (TJ Q2 "(b)").
- TS optimisation, P-RFO, the barrier, the active-core mode filter, and Tier 3 as a ΔG‡ test:
  v0.5.0 (TJ Q-E1 "A").
- Store caching of grafts or relaxations; `ReactionGraph` execution; YAML graph loading.
  `TemplateGeometry.mapping` stays the v0.8.0 loader's single source, and it will build a
  `GraftSpec` from it (R11).
- The covalent topology audit as a library feature (v0.9.0). v0.4.0 perceives bonds only in
  `mapping.report` and in the M1 fixture gate.
- Automatic atom-map or core detection (MCS); GUI selection (v1.1.0+); the nMAP XYZ range syntax
  (`"2-3 5"`); nMAP's template pre-alignment (CR rows).
- Any change to `thermo/`, `conformers/`, `engines/`, `store/`, `optimize/` or `orchestrator/`,
  and to ADR-0005's `AtomMappingSpec`.

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority | Slice |
|---|---|---|---|---|
| US-001 | As the builder, I want the starter unpacked as reference with its discrepancies listed, so that every later question traces to a row. | 32 files byte-identical, with their sha256 list. `DISCREPANCIES.md` has DV-01…DV-10 and CR-01…CR-15 (§5 "Discrepancy register"). PD-008 is `decided`. `git diff Base -- docs/prd/PLAN_DISCREPANCIES.md` changes only the PD-008 status cell. | P0 | 01 |
| US-002 | As a library user, I want strict frozen contracts for a graft request and its result, so that a graft is validated before any geometry is touched. | §5 "Contracts". Every validator has a passing and a rejecting test. `import eta_rxncat.core` loads no numpy or RDKit. | P0 | 02 |
| US-003 | As a chemist, I want quaternion superposition of ordered pairs, so that alignment is exact and reflection-free. | §5 "Algorithms" A1–A4. The rotation and translation of a known motion are recovered (RMSD ≤ 1e-10 Å). det(R) = +1 on 1000 random sets. RMSD agrees with the test-local SVD within 1e-10 Å. Non-coplanar mirror sets give RMSD > 0, and vector 03 gives 0.75 Å ± 1e-6. Fewer than 3 pairs, collinear sets (vector 06) and a non-unique top eigenvalue raise `AlignmentError`. Identical inputs give a bitwise-identical result (H-M4). | P0 | 03 |
| US-004 | As a chemist, I want ordered surgery with an optional fragment delete list, so that product indices are predictable and aryl-style grafts are expressible (TJ Q4 "A", R1 "B"). | §5 "Algorithms" G1–G8. Exact product order and `index_map`. Kept template coordinates are bitwise unchanged. Vectors 01, 02, 04, 05 and 07-adapted match at 1e-6 Å. A hand-built CH3Cl → CH3F graft is exact. | P0 | 04 |
| US-005 | As a chemist, I want product charge and multiplicity explicit and checked (TJ Q5 "A"). | Product charge and multiplicity come from the spec. Parity is checked by `MolecularState`. `whole_input_charge_sum_holds_bool` is reported only (R10). | P0 | 04 |
| US-006 | As a chemist, I want active atoms, the constrained core, overlaps, contacts, junctions and planarity handled explicitly, so that nothing about the graft is silent (TJ P1 "A", R2 "A"). | Active atoms and the core are re-indexed; deleting one raises `GraftInputError`. A pair closer than `min_distance_angstrom` raises `GraftClashError(i, j, d)`. Close contacts, junction signed volumes and the planar flag are recorded and sorted. Element mismatch in a pair, non-empty `anchors`, non-empty fragment active indices and out-of-range indices raise `GraftInputError`. | P0 | 04 |
| US-007 | As a chemist, I want the graft pre-relaxed with its conserved core frozen (TJ Q2 "(b)"). | `relax_constrained_core` per §5 "Algorithms" X1–X4. Core max displacement ≤ 1e-6 Å (R26), else `CoreDisplacementError`. No dihedral constraints are ever passed. Engine and optimizer errors propagate unchanged. Tests: fake engine/optimizer (tier D), then UFF with `GeometricOptimizer`. | P0 | 05 |
| US-008 | As TJ, I want my M1 mapping run end to end, with the atom map derived by a stated rule, so that I can review the mapped TS1b_n guess (TJ Q3 "B", P1 "A", P2 "A", R2 "A"). | §5 "Fixture M1". Tier D: the stated-rule map is re-derived and equals the YAML's; forming-core RMSD ≤ 0.10 Å; contacts, junctions, planarity and other-map RMSDs are reported. E2E per recipe: connectivity equals TS1b_n's and junction signs match. Candidates `m1_graft.json`, `m1_relaxed.xtb.json` and `m1_relaxed.uma.json` are committed in a candidates-only commit. | P0 | 06 |
| US-009 | As TJ, I want an acceptance record and a split verdict, so that v0.4.0's claims come from a record and cannot pass on a pending check (ADR-0027, R56). | `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json`: real outcomes per check (`pass`/`fail`/`pending_promotion`/`pending_confirmation`/`skipped` with reason). The verdict is `pass` only with zero `fail`, `pending_*` or missing checks. The version is bumped to 0.4.0 only at the verdict. | P0 | 07, 08 |

## 5. Technical Specifications

### Resolved trade-off log

Vocabulary:
- **resolved**: the design changes so the risk is gone; the slice that carries it is named.
- **out of scope**: excluded, with the owner.

No finding is `accepted`, so no human row is owed for one. "Fn" is the red-team id. "nMAP §x" and
"arch-n" are the clean-room spec and the architect's comparison.

| ID | Finding | Sev | Disposition | Decision |
|---|---|---|---|---|
| R1 | F1 (blocker) M1 puts two H 1.12 Å from Cp carbons, and no check sees it; F2 (high) the M1 gate cannot fail because of the mapper | blocker / high | resolved (TJ) | TJ, verbatim: "P1 A / P2 A". (1) **Overlap floor:** any product pair closer than `min_distance_angstrom` (0.5 Å, keyed) raises `GraftClashError` (atoms on top of each other are never a starting geometry). (2) **Close contacts:** the pure graft *records* its contacts (§5 "Algorithms" G6). A contact is a pair (kept template atom, appended atom) that is not a source-graph bond and is closer than 1.3 × (r_cov,i + r_cov,j). r_cov is RDKit `GetRcovalent`, and 1.3 is `DetermineConnectivity`'s own default `covFactor`. Contacts are never an error. M1 records exactly (0, 15) 1.9598, (0, 17) 1.1218, (4, 16) 1.9611 and (4, 20) 1.1251 Å (HF-5). Perception alone was rejected because it gives each H one partner and misses the 1.12 Å H contacts (measured). (3) **Gate on the relaxed candidates (P1 A):** per recipe, the perceived connectivity of the pre-relaxed product, mapped through the stated map, equals TS1b_n's perceived connectivity (edge sets equal). (4) Full-molecule RMSDs are reported, never gated. No new numeric bound. F2's what-if (R applied as Rᵀ) is caught by the clean-room vectors 01–05 at 1e-6 Å (slices 03/04). Slices 02, 04, 06. |
| R2 | F3 (high) the map derivation cannot work as written, and as measured it was chosen by the gated quantity | high | resolved (TJ) | TJ, verbatim: "P1 A / P2 A". **Stated rule:** (a) perceive connectivity of TS1a_n, cyclobutene and TS1b_n separately (`DetermineConnectivity`, defaults); (b) build the graft's source graph (G6); (c) enumerate every element-preserving graph isomorphism source → TS1b_n (equal bond counts; RDKit substructure matching with all bonds single, `uniquify=False`); (d) choose the **lexicographically smallest** map tuple (TS1b_n index per product atom, in product order). No coordinate enters the choice. Zero isomorphisms, or unequal bond counts, is stop-and-report. The derived map is written into the provisional M1 YAML. A tier-D test re-derives it by the same rule and asserts equality. The candidate also reports the isomorphism count (32), the distinct heavy maps (4) and the forming-core RMSD under each distinct heavy map (0.0498 ×2, 0.9637 ×2), so TJ sees the choice was not tuned. TJ confirms the map at Phase 3 by promoting `m1_graft.json`, which carries it: the promotion is the confirmation, as v0.3.0 R58. Negative constraint N2. Slice 06. |
| R3 | F4 (high) US-001/DV-10 would corrupt a correct register | high | resolved | `PLAN_DISCREPANCIES.md`'s column is the plan copy's sha256 inside the zip (`ad092dff…`, red team measured), so it is right. **No** hash in it changes (N7). DV-10 becomes a clarifying note: "the register's v0.4.0 cell is the plan copy's sha256 (`ad092dff…`); the zip's own sha256 is `6214b5e1…`; both are correct". The zip sha256 is recorded in `docs/prd/v0.4.0/DISCREPANCIES.md`'s header. The only `PLAN_DISCREPANCIES.md` change is PD-008's status cell. Slice 01. |
| R4 | F5 (medium) fixture path collides with v0.3.0's e2e5 data; false ownership claim | medium | resolved | One fixture tree and one provenance register. TJ's three files go to `tests/e2e/data/e2e5/xyz/` (`TS1a_n.xyz`, `6_cyclobutene.xyz`, `TS1b_n.xyz`), byte-identical. Three rows are added to the existing `tests/e2e/data/e2e5/SOURCES.md` (SI page from each file's header, DOI 10.1021/ja408437u, transcriber TJ, sha256). They are extracted the v0.3.0 way: `ast.parse` + `ast.literal_eval` of `XYZ_FILES`; the builder is never executed, anywhere (N3). The M1 YAML is `tests/e2e/data/e2e5/m1_ts1a_n_to_ts1b_n.yaml`. No `tests/data/human_fixtures/` directory is created. Ownership is in R8. Slice 06. |
| R5 | F6 (medium) 1e-10 cross-check fails near zero; test reaches into thermo's private module | medium | resolved | The cross-check reference is an **independent SVD Kabsch written in the test file** that computes RMSD from residual coordinates. `thermo._geometry` is never imported from `src/eta_rxncat/mapping/` or `tests/unit/mapping/` (N4), so there is no mapping → thermo edge. Its precision is measured (HF-9: ≤ 4.4e-15 Å), so the G2 tolerance of 1e-10 Å on RMSD is honest. Rotations are compared too (max element difference ≤ 1e-9) on sets whose pair-set shape is non-degenerate. The random generator rejects sets with an RMS off-line deviation < 0.1 Å, or a top-eigenvalue gap < 1e-6. Thermo's `kabsch_rmsd` has a measured cancellation floor of 1.69e-7 Å and is not used as a reference. **TJ's Q6 1e-10 Å is a different comparison** (the graft against its promoted fixture) and is untouched. Mirror tests use non-coplanar sets (and vector 03). Slice 03. |
| R6 | F7 (medium) pre-relaxation unbounded in runtime and resources; audit 04's frozen + dihedral hang | medium | resolved | (1) M1's pre-relaxation passes `options={"maxiter": 200}` to `GeometricOptimizer` explicitly. (2) The harness-level bound: every M1 E2E command in a proof runs under coreutils `timeout 3600`. An expiry is a stop-and-report with the output; the test itself records `wall_time_s`. `optimize/` stays frozen (§6). (3) **No v0.4.0 path combines frozen atoms with a dihedral constraint.** `relax_constrained_core` has no dihedral parameter and calls `minimize(..., frozen_atom_indices=core, options=...)` with `dihedral_constraints` left at its default `()`. A recording fake optimizer test asserts `dihedral_constraints == ()`, and an `options` key named `constraints` is refused up front with `MappingError`. (4) The heavy-run rule is in every slice's seat rules. Slices 05, 06. |
| R7 | F8 (medium) core-displacement guard underspecified, maybe a bare `assert` | medium | resolved | Named error `CoreDisplacementError(MappingError)` carrying (atom, displacement). The metric is the **max per-atom Euclidean displacement of the core atoms, final vs input, with no superposition** (D4: the frame is the template's). Bound 1e-8 Å (architect-set), **superseded by R26 (replan 1): 1e-6 Å, measured**. A miss on xtb or UMA is stop-and-report (H-M3), never a widened bound. No `assert` statement anywhere in `src/eta_rxncat/mapping/`; a test greps for it. Slice 05. |
| R8 | F9 (medium) ledger: new node has no edges; test files land in the wrong nodes | medium | resolved | Slice 03 creates node `eta_rxncat_mapping` (Module) with `depends_on: eta_rxncat_core, eta_rxncat_engines, eta_rxncat_optimize` (relax uses the `Engine` and `Optimizer` interfaces) and files `src/eta_rxncat/mapping/**, tests/unit/mapping/**`. Slice 06 adds `tests/e2e/test_m1_*.py, tests/e2e/data/e2e5/m1_*.yaml, tests/candidate_outputs/v0.4.0/**` (F9c), and slice 07 adds `tests/e2e/test_accept_v040.py`. The full list is passed each time. `eta_rxncat_scaffold` loses `src/eta_rxncat/mapping/**` (description unchanged). The acceptance driver is `tests/e2e/test_accept_v040.py`, **not** `tests/acceptance/**` (the engines node's; F9b). `tests/e2e/**` stays in `eta_rxncat_species_runner` too. That overlap is stated and accepted (the e2e harness is the runner's), so the M1 files mark both nodes. TJ's XYZ files under `tests/e2e/data/e2e5/xyz/` are the runner's, like v0.3.0's. No thermo edge (R5). `eta_rxncat_engines` is not touched. Slices 03, 06, 07. |
| R9 | F10 (low) G5 contradicts relax.py | low | resolved | G5 now reads as §5 "Dependencies": no `geometric`, `torch`, `pyscf`, `fairchem` or `rdkit` at import of `eta_rxncat.mapping` or any submodule. `eta_rxncat.optimize` imports only numpy among heavy modules (red team measured). Slice 03 (test), extended in 04/05. |
| R10 | F11 (low) the charge sum measures the wrong sum | low | resolved | Renamed `whole_input_charge_sum_holds_bool`: product charge == template charge + fragment charge, over the **whole inputs**, deleted atoms included. Its docstring says so, and that it is false for a correct graft with a charged leaving group. Report only (TJ Q5 "A"). Slice 02. |
| R11 | F12 (low) `anchors` unused; `GraftSpec.template` duplicates `TemplateGeometry.mapping` | low | resolved / out of scope | A non-empty `template.anchors` is refused by `GraftSpec` (nothing silently ignored). The duplication is out of scope for v0.4.0: when the graph runs (v0.8.0), `TemplateGeometry.mapping` is the single source and the loader builds a `GraftSpec` from it. Recorded as a `known_limits` line. Slices 02, 07. |
| R12 | F13 (low) degeneracy rule ill-posed; arch-2 / nMAP §4.5, §10 Q2 | low | resolved | Shape test on each centred pair set: singular values s1 ≥ s2 ≥ s3, k points. RMS off-line deviation = √((s2² + s3²)/k). **< 3 pairs, or an RMS off-line deviation ≤ `degenerate_tolerance_angstrom` (1e-3 Å, keyed) on either side, raises `AlignmentError`.** A second guard: λ1 − λ2 ≤ 1e-10·max(1, \|λ1\|) of the 4×4 key matrix raises `AlignmentError("rotation not unique")`. M1 passes (0.316 Å). Vector 06's 1-, 2- and 3-collinear-pair cases are refused. Slice 03. |
| R13 | F14 (low) no slice owns the version bump | low | resolved | Slice 08 bumps `pyproject.toml`, `src/eta_rxncat/__init__.py`, `tests/unit/test_package.py` and `uv.lock` to 0.4.0, only after a `pass` verdict. Slice 08. |
| R14 | F15 (low) inconsistent error family | low | resolved | `graft()` calls `spec.template.check_atom_count(n)` and re-raises its `ValueError` as `GraftInputError(...) from err`. A test pins the type and the `__cause__`. Model-level violations stay pydantic `ValidationError` at construction. Slice 04. |
| R15 | arch-1 / nMAP §10 Q1: "unpaired" vs "non-deleted" incoming atoms | — | resolved (TJ) | TJ, verbatim: "R1 B, R2 A". `GraftSpec.fragment_delete: list[NonNegativeInt] = []`. **Paired fragment atoms are always dropped.** The appended atoms are the fragment atoms neither paired nor in `fragment_delete`, ascending. `fragment_delete` must be unique, in range and disjoint from `fragment_alignment`. A paired atom listed there is refused, because it is already dropped. M1 is unchanged (`fragment_delete: []`). Vectors 04/05 become expressible (fragment_delete = the ring H). Slices 02, 04. |
| R16 | arch-3 / nMAP §4.3, §10 Q3: reversed sense on a planar pair set | — | resolved (TJ) | TJ, verbatim: "R1 B, R2 A". (1) **Planar flag:** the RMS out-of-plane deviation s3/√k of each centred pair set is reported (`template_pair_planarity_rms_angstrom`, `fragment_pair_planarity_rms_angstrom`). `planar_pair_set_bool` is true if either is ≤ `planar_tolerance_angstrom` (0.05 Å, keyed). M1 is planar (HF-3). (2) **Junction handedness:** a junction is a source-graph bond (t, a) between a kept template atom t and an appended atom a. Its reference neighbours n1 < n2 are the two lowest product indices among t's source-graph neighbours that are kept template atoms other than a. V = (p_a − p_t) · [(p_n1 − p_t) × (p_n2 − p_t)] in Å³. sign = 0 if \|V\| ≤ `junction_volume_tolerance_angstrom3` (0.05, keyed), else ±1. With fewer than 2 such neighbours, V and sign are `None`. All are recorded in `GraftResult.junctions`, sorted by (t, a). (3) **Checked against TS1b_n in M1:** the same V is computed on TS1b_n at the mapped indices. On each relaxed candidate, every junction's sign is nonzero and equals TS1b_n's (a sign gate, not a numeric bound). On the pure graft the signs are reported: M1's are 0 (undetermined, HF-8), which is recorded, not failed. Slices 02, 04, 06. |
| R17 | arch-4 / nMAP §3.1, §10 Q4: element mismatch in a pair | — | resolved | `graft()` raises `GraftInputError` naming the pair and both symbols when `template.symbols[t] != fragment.symbols[f]` (ADR-0003 strictness). `superpose()` takes coordinates only and does not check. Slice 04. |
| R18 | arch-7, arch-8: clean-room test vectors and deliberate divergences | — | resolved | The vector files are copied byte-identical into `tests/unit/mapping/data/cleanroom_nmap/<NN_name>/` with `PROVENANCE.md`: TRANSFER_LOG transfer 1, its per-file sha256, `CHECKER_REPORT.md` "Approved for transfer", TJ Q1. They go under the **mapping node's** test tree, not `tests/data/**` (the core node's), so core is not marked dirty (F9 spirit). Indices are converted 1-based → 0-based in a test loader. Coordinates and RMSD are compared at 1e-6 Å (the vectors' 6-decimal precision). Use: 01, 02, 03 (alignment level: moved incoming rows 5–8 and RMSD 0.75), 06 (refusals) in slice 03; 04, 05, 07 in slice 04. **Vector 07, eta-adapted:** the literal request pairs template atom 5, which it also deletes. ADR-0005's alignment ⊆ keep refuses that (`ValidationError`, asserted). The eta request keeps template 5: template delete {2,3} (1-based), pairs (1,1), (4,2), (5,3), `fragment_delete` []. The product is template 1, 4, 5, 6 then incoming N, Cl, with the expected coordinates taken from the vector's files at 1e-6. The lead's addendum line "vector 07 expects GraftClashError" assumed nMAP's keep-a-paired-atom request, which R15 (paired atoms always dropped) makes inexpressible. Overlap is tested by a hand-built clash case instead. The range syntax `"2-3 5 4-3 5"` is not an eta input (CR-11). Slices 03, 04. |
| R19 | arch-5, arch-6 / nMAP §10 Q5–Q6 | — | resolved (informational) | No RMSD threshold in the API: the alignment RMSD is reported, and M1's bound is a fixture gate (TJ Q6). `superpose()` keeps optional positive finite weights (weighted centroids, weighted correlation, weighted RMS). `graft()` never passes weights. |
| R20 | Red-team Part B items | — | resolved | (a) US-004 and US-008 overlap: every M1 check lives in slice 06 only; slice 04 tests use vectors and hand-built cases. (b) `NonNegativeFiniteFloat` is defined in `core/mapping_models.py` (`Annotated[float, Field(ge=0, allow_inf_nan=False)]`). (c) `GraftResult` lives in `core/mapping_models.py`. (d) The relaxed-candidate regression's heavy-atom RMSD superposes (Horn, heavy atoms, unweighted) before comparing. The pure-graft regression compares coordinates directly (same template frame, no superposition): coordinate RMSD ≤ 1e-10 Å, `index_map` exact. (e) Risks re-rated in §7. |
| R21 | Red-team N1–N7 | — | resolved | All seven are adopted in §6. N1's "contact check result" is `GraftResult.close_contacts` (R1), which every M1 candidate carries. N4 is extended to `tests/unit/mapping/`. |
| R22 | Draft H-M2 (23 vs 21 perceived bonds) | — | resolved | Closed by HF-4/HF-5. The two extra perceived bonds are C0…C15 and C4…C16 at 1.96 Å, the carbons of the CH2 groups whose H the red team found at 1.12 Å (F1's "two extra C–H bonds" reading was close but not exact). The source graph has 21 bonds and is isomorphic to TS1b_n's (HF-6). |
| R23 | v0.3.0 lessons carried | — | resolved | In every slice's seat rules: R54 (unit-suffixed numeric keys); R55 (no energy- or record-ordered lists in compared outputs; lists are fixed by the fixture or sorted by an energy-independent key); R56 (fragments record the real outcome via one `gated_outcome`; `pending_*` fails under acceptance; missing is `missing`); R50 (reader rule, applied to any store or runner payload, although v0.4.0 adds none); R53 (no new dedup; not applicable). The candidate rule (C1 code, E2E at C1, C2 candidates only; every diff, show or log -p uses `':(exclude)tests/candidate_outputs'`). Heavy runs sequential, after the host check. |
| R24 | Roadmap: TJ Q2 "(b)" moves enumeration to v1.x while the plan lists it at v0.7.0 (PR #14) | — | out of scope | The plan is not touched (`PRDs/` read-only, Q1 "A"). PD-008's decided text names v1.x. The roadmap reconciliation belongs to the lead and TJ. |
| R25 | Phase 3 gate content | — | resolved | TJ reviews three candidates: `m1_graft.json` (with the stated-rule map, its alternatives, the contacts and the junctions), `m1_relaxed.xtb.json` and `m1_relaxed.uma.json`. Promoting `m1_graft.json` confirms the map (R2). Only TJ writes `tests/fixtures/v0.4.0/`. The lead's Phase 3 row also states HF-5 (the two 1.12 Å contacts) and HF-8 (pure-graft junctions undetermined). |
| R26 | Replan 1: the 1e-8 Å core-freeze bound (R7) fails on the unchanged v0.3.0 `GeometricOptimizer` (slice 05 stop, row `qitem-20261123203623-5f1b4bc3`; evidence `~/.hacf/eta-rxncat-hacf/evidence-v040-05-uff-core-drift.md`; lead row `qitem-20261123203651-6af28ab1`) | — | resolved | **Measured.** geomeTRIC `$freeze` with `enforce` 0.1 holds frozen atoms to about 1e-8–1e-7 Å, not to 1e-8 Å. (a) Builder, UFF n-butane, 8 runs: 2.3e-9 to **1.19e-7 Å**; 6 of 8 above 1e-8; deterministic across hash seeds. (b) Resolve, UFF, 40 runs (7 molecules: butane, pentane, cyclohexane, toluene, ethanol, methyl acetate, butadiene; random 2–4-heavy-atom cores; 2 embeds each): max 4.53e-8, median 1.22e-8; 23 of 40 above 1e-8; none above 1e-7. All converged on `tric`. (c) Resolve, **xtb (GFN2, the slice 06 recipe) on the actual M1 graft**, core [1, 2, 3, 5], `maxiter` 200: **4.19e-8 Å**, 17 steps, `tric`, 24 s. Snapping the core back to its input changes the xtb energy by **3.9e-10 Eh**. (d) UFF cannot evaluate the pure M1 graft at all (RDKit bond perception fails on the clashed TS geometry), so UFF stays a unit-test engine only. UMA was not measured (GPU; the host was shared). (v0.3.0's ≤ 4e-9 Å was water only.) **Decision: option A, a measured bound, `CORE_FREEZE_TOLERANCE_ANGSTROM = 1e-6`** (max per-atom displacement, no superposition; the metric is unchanged). Why 1e-6 Å: (1) it is 8× the worst drift measured on any engine (1.19e-7); (2) it equals the six-decimal precision of the XYZ inputs and of the clean-room vector comparisons, so the core is unchanged at the precision the inputs carry; (3) it is 4 orders below TJ's relaxed regression heavy-atom bound (0.01 Å, Q6 "A"), and the energy effect is about 1e-9 Eh against TJ's 1e-5 Eh, so **TJ's Q6 bounds are untouched**; (4) it is far tighter than TJ's own M1 text ("held within 0.15 Å RMSD"), so "frozen" keeps its meaning and no TJ question is owed. **Rejected: B** (make the freeze exact in `optimize/`). It changes the audited v0.3.0 `optimize` node and every frozen-atom caller (the species runner's constrained point, and v0.3.0's H15 tests) for a gain below every downstream tolerance, and a written-back geometry is no longer the optimizer's converged point. A tighter `enforce` has v0.3.0's hang history and is unmeasured. **Rejected: C** (snap the core back in `relax.py`): a workaround that hides drift instead of bounding it. **H-M3** (xtb/UMA in slice 06) is judged against 1e-6 Å. A miss there is stop-and-report, and the bound is never widened again. **ADR-0032** (PROPOSED) still says 1e-8 Å; R26 supersedes it, and the lead raises this at TJ's lore approval. Slices 05, 06, 07; seed deviations replan 1. |
| R27 | Replan 2: the slice 08 verdict ignores the default suite (audit 07, row `qitem-20261123214503-e4782517`, verbatim: "record_verdict ignores default_suite.exit_code and failed; the SPEC's verdict rule names only check states. A failing default suite would not turn the verdict to fail."; lead row `qitem-20261123214543-c9406896`) | — | resolved | Slice 08 C1, before the verdict run: (a) `record_verdict(fixtures, default_suite, commands)` returns `fail` on a default-suite or clean-room-vector run with a non-zero exit code, failures or errors, or on any command with a non-zero exit code or a skip. `check()` recomputes it the same way, so a stated `pass` cannot disagree with the record. (b) A record without `verdict` refuses every README claim (v0.3.0 slice 10 req 4). (c) The xtb acceptance command sets `ETA_RXNCAT_XTB` (audit 06: without it the test skips), and the run needs zero skips. (d) Map confirmation reads the promoted `m1_graft.json` map, never a carried-over status (R2, as v0.3.0 R58). (e) `evidence.promotion` records TJ's verbatim answer, the promotion commit and each promoted file's sha256 and blob id (as v0.3.0 R57); the lead writes the promotion R-row when it lands. The promotion is exactly the three Phase 3 files; promoting fewer is a stop-and-report, not a skip. The version still goes to 0.4.0 only on `pass` (R13). Tests: a failing suite, vector run, command or skip each give `fail`, and the README check refuses. Slice 08; seed deviations replan 2. |

### Seed deviations

Changes to slice specs after their first compile (replan mode; finished slices are never edited).

| Replan | Slice | Change | Rows |
|---|---|---|---|
| 1 | 01–04 | none (audited PASS; context only) | — |
| 1 | 05-constrained-relax | core bound 1e-8 → 1e-6 Å as `CORE_FREEZE_TOLERANCE_ANGSTROM`; displacement fixtures rescaled; UFF expectation; negative space | R26 |
| 1 | 06-m1-fixture | g1 judged at 1e-6 Å; the measured core drift recorded | R26 |
| 1 | 07-acceptance-record | g1 at 1e-6 Å | R26 |
| 1 | 08-acceptance-verdict | none | — |
| 2 | 01–07 | none (audited PASS; context only) | — |
| 2 | 08-acceptance-verdict | R27 (a)–(e) in C1: the default suite, commands and skips gate the verdict; a record without `verdict` is refused; xtb run with `ETA_RXNCAT_XTB`; map confirmation from the promoted file; `evidence.promotion`; exactly three promoted files expected | R27 |

### Host facts and stop-and-report steps

| # | Fact | How | Status |
|---|---|---|---|
| HF-1…HF-9 | §2 | resolve scratch run | measured 2026-11-23 |
| H-M3 | `minimize` with `frozen_atom_indices` holds the core ≤ 1e-6 Å on xtb and UMA (R26) | slice 06 E2E (`CoreDisplacementError` otherwise) | xtb measured 4.19e-8 Å on M1 (resolve, replan 1); UMA open |
| H-M4 | `numpy.linalg.eigh` on the 4×4 key matrix is bitwise deterministic run to run on this host | slice 03 test | open |
| H-M5 | The M1 pre-relaxed product keeps TS1b_n's connectivity and junction signs on each recipe | slice 06 E2E | open; a miss is the finding TJ's P1 A exists to catch: stop and report, with the candidate still written |
| H-M6 | M1 pre-relaxation finishes within `timeout 3600` per recipe at `maxiter` 200 | slice 06 | open |

### Blast radius

Read from `spec/compiled/architecture.yml` (red-team C2, re-checked by resolve):
- **Touched:**
  - `eta_rxncat_core` (new `core/mapping_models.py`, `core/__init__.py` exports);
  - `eta_rxncat_scaffold` (`mapping/**` glob moved out, `test_package.py`, `docs/**`, README, the
    version);
  - new `eta_rxncat_mapping`;
  - `eta_rxncat_species_runner` (`tests/e2e/**`: M1 data, tests, acceptance driver).
- **Not touched:** engines, thermo, optimize, conformers, store, cli, hw_probe.
- Core is upstream of everything, so the updater lists a wide radius. Every contract change is
  additive (no existing field changes), so no consumer breaks.

### Execution checklist (build order; the lead's work queue)

| # | Slice | Id | Depends on | Node |
|---|---|---|---|---|
| 1 | `slices/01-starter` | OPR.0.4.0.1 | — | `eta_rxncat_scaffold` |
| 2 | `slices/02-graft-contracts` | OPR.0.4.0.2 | .1 | `eta_rxncat_core` |
| 3 | `slices/03-align` | OPR.0.4.0.3 | .2 | `eta_rxncat_mapping` (**new**: slice 03 creates it) |
| 4 | `slices/04-graft` | OPR.0.4.0.4 | .3 | `eta_rxncat_mapping` |
| 5 | `slices/05-constrained-relax` | OPR.0.4.0.5 | .4 | `eta_rxncat_mapping` |
| 6 | `slices/06-m1-fixture` | OPR.0.4.0.6 | .5 | `eta_rxncat_mapping` |
| 7 | `slices/07-acceptance-record` | OPR.0.4.0.7 | .6 | `eta_rxncat_mapping` |
| — | **PHASE 3 GATE**: TJ reviews the three candidates and promotes what he accepts into `tests/fixtures/v0.4.0/` | — | .7 | — |
| 8 | `slices/08-acceptance-verdict` | OPR.0.4.0.8 | .7 + TJ promotion | `eta_rxncat_mapping` |

One slice at a time (the ledger takes no parallel writes). The feature is done when 08 is audited
PASS with verdict `pass`.

### Contracts

All in `src/eta_rxncat/core/mapping_models.py`, exported from `eta_rxncat.core`. They subclass
`CoreModel`: `extra="forbid"`, frozen, ADR-0003 strict, units in names. The module imports no
numpy.

**`GraftSpec`**
- `template: AtomMappingSpec` (ADR-0005, unchanged). `alignment` is the ordered template side of
  the pairs. `anchors` must be empty (R11).
- `fragment_alignment: list[NonNegativeInt]`: the ordered fragment side. It is unique and has
  the same length as `template.alignment`.
- `fragment_delete: list[NonNegativeInt] = []`: unique, disjoint from `fragment_alignment` (R15).
- `constrained_core: list[NonNegativeInt] = []`: unique, ⊆ `template.keep`.
- `product_charge: StrictInt`, `product_multiplicity: PositiveInt` (Q5 "A").
- `min_distance_angstrom: PositiveFiniteFloat = 0.5`.
- `degenerate_tolerance_angstrom: PositiveFiniteFloat = 1e-3`.
- `planar_tolerance_angstrom: PositiveFiniteFloat = 0.05`.
- `junction_volume_tolerance_angstrom3: PositiveFiniteFloat = 0.05`.
- Validators (`ValueError` → `ValidationError`):
  - the lengths match;
  - `template.alignment` and `fragment_alignment` are each unique;
  - `fragment_delete` is unique and disjoint from `fragment_alignment`;
  - the core is unique and ⊆ keep;
  - `anchors` is empty.

  Ranges against real atom counts are checked by `graft()`.

**`CloseContact`:** `i: NonNegativeInt`, `j: NonNegativeInt` (product indices, i < j),
`distance_angstrom: PositiveFiniteFloat`.

**`JunctionVolume`:** `template_atom`, `appended_atom`, `neighbour_a`, `neighbour_b`:
`NonNegativeInt | None` (neighbours `None` when fewer than 2); `signed_volume_angstrom3:
FiniteFloat | None`; `sign: Literal[-1, 0, 1] | None`.

**`GraftResult`**
- `product: MolecularState`.
- `index_map: list[tuple[Literal["template", "fragment"], NonNegativeInt]]` (product order).
- `alignment_rmsd_angstrom: NonNegativeFiniteFloat`.
- `template_charge`, `fragment_charge`, `product_charge: StrictInt`;
  `whole_input_charge_sum_holds_bool: bool` (R10).
- `constrained_core_product_indices`, `active_product_indices: list[NonNegativeInt]`, both sorted.
- `min_interatomic_distance_angstrom: PositiveFiniteFloat`.
- `template_pair_planarity_rms_angstrom`, `fragment_pair_planarity_rms_angstrom:
  NonNegativeFiniteFloat`; `planar_pair_set_bool: bool`.
- `source_bonds: list[tuple[NonNegativeInt, NonNegativeInt]]` (i < j, sorted).
- `close_contacts: list[CloseContact]`, sorted by (i, j).
- `junctions: list[JunctionVolume]`, sorted by (template_atom, appended_atom).
- Validators:
  - `len(index_map)` equals the product atom count;
  - every listed index is < the product atom count;
  - the lists are sorted and unique where stated.

**Errors (`src/eta_rxncat/mapping/errors.py`):** `MappingError(Exception)`, with subclasses:
- `AlignmentError`;
- `GraftInputError`;
- `GraftClashError(i, j, distance_angstrom)` (attributes);
- `CoreDisplacementError(atom, displacement_angstrom)`.

No function returns its input, or a partial result, in place of an error.

### Algorithms (normative where a test depends on them)

**Alignment (`mapping/align.py`).**
- **A1. Signature:** `superpose(mobile, reference, weights=None, *, degenerate_tolerance_angstrom=1e-3) -> Superposition`.
  - Arrays are (k, 3) float64 and must have equal shape; otherwise `AlignmentError`.
  - Weights must be positive and finite, of length k.
  - `Superposition` is a frozen dataclass with `rotation` (3×3), `mobile_centroid`,
    `reference_centroid`, `rmsd_angstrom` and `apply(coords)`: x′ = R (x − c_m) + c_r.
- **A2. Shape guard:** `pair_set_shape(points) -> (rms_off_line_angstrom, rms_off_plane_angstrom)`
  from the singular values of the centred set (R12, R16). k < 3, or off-line ≤ tolerance on
  either side, raises `AlignmentError`.
- **A3. Rotation:** Horn 1987. Build the 4×4 symmetric key matrix from the 3×3 correlation
  matrix Σ w (m − c_m)(r − c_r)ᵀ. `numpy.linalg.eigh` gives the unit quaternion of the largest
  eigenvalue. The λ1 − λ2 guard raises `AlignmentError` (R12). det(R) = +1 by construction; no
  reflection fix-up exists.
- **A4. RMSD:** computed from residual coordinates, √(Σ w‖R(m − c_m) + c_r − r‖² / Σ w), never
  from the eigenvalue formula.

**Graft (`mapping/graft.py`):** `graft(template: MolecularState, fragment: MolecularState, spec: GraftSpec) -> GraftResult`.
- **G1. Ranges.** Check `spec.template.check_atom_count(n_template)`; a `ValueError` becomes
  `GraftInputError` (R14). Fragment indices (`fragment_alignment`, `fragment_delete`) must be
  < n_fragment. The template's `active_atom_indices` and `spec.constrained_core` must not
  intersect `delete`. A non-empty `fragment.active_atom_indices` is refused. All of these raise
  `GraftInputError`.
- **G2. Elements.** For each pair, the template and fragment symbols are equal, else
  `GraftInputError` (R17).
- **G3. Superpose** `fragment[fragment_alignment]` onto `template[template.alignment]`
  (unweighted, A1–A4), with `spec.degenerate_tolerance_angstrom`.
- **G4. Assemble.**
  - First, `template.keep` in keep order. Coordinates are copied from the template array, never
    recomputed.
  - Then the appended atoms: fragment indices not in `fragment_alignment` and not in
    `fragment_delete`, ascending, transformed by `apply`.
  - `index_map` records each atom's source.
- **G5. Overlap floor.** Over all product pairs, the minimum distance is computed. Any pair
  < `min_distance_angstrom` raises `GraftClashError` for the first such pair in (i, j) order.
- **G6. Source graph and contacts.**
  - Perceive the template's and the fragment's connectivity separately with
    `mapping.report.perceive_bonds` (RDKit `rdDetermineBonds.DetermineConnectivity`, defaults,
    lazy import).
  - The source graph, in product indices, contains:
    - template bonds between two kept atoms;
    - fragment bonds between two appended atoms;
    - **junction bonds**: (t, a) for every fragment bond (f, a) where f is paired with template
      atom t and a is appended.
  - Bonds touching a deleted or dropped atom are omitted.
  - `close_contacts` are the pairs (i kept template, j appended) that are not source bonds, with
    distance < 1.3 × (r_cov,i + r_cov,j). r_cov is RDKit `Chem.GetPeriodicTable().GetRcovalent`,
    lazy, inside `report`. They are recorded with their distances, never raised (R1).
- **G7. Junctions and planarity** per R16.
- **G8. Product state.** `MolecularState` with the spec's charge and multiplicity (parity checked
  there), and active atoms re-indexed. `metadata` gets `alignment_rmsd_angstrom` and the template
  and fragment names, if they carry one.

**Report helpers (`mapping/report.py`):**
- `perceive_bonds(state) -> list[tuple[int, int]]` (sorted, RDKit lazy).
- `covalent_radius_angstrom(symbol) -> float` (RDKit `GetRcovalent`, lazy).
- `core_rmsd_angstrom(a, b, indices_a, indices_b)`: superposes (A1–A4) and returns the RMSD over
  the listed atoms.
- `junction_volumes(coords, source_bonds, n_template_kept, tolerance)`: the R16 rule, reused on
  TS1b_n coordinates under the map.

**Relaxation (`mapping/relax.py`):**
- **X1. Signature:** `relax_constrained_core(state, engine, optimizer, core_indices, options=None) -> OptimizationResult`.
- **X2. Up-front refusals:** `core_indices` empty, non-unique or out of range, or an `options`
  key `constraints`, raises `MappingError` before any engine call (R6).
- **X3. Call:** `optimizer.minimize(state, engine, frozen_atom_indices=core_indices, options=options)`.
  No dihedral constraints, ever. `EngineError` and `OptimizerError` propagate unchanged.
- **X4. Displacement check:** the max per-atom displacement of the core atoms (final vs input, no
  superposition) > `CORE_FREEZE_TOLERANCE_ANGSTROM` (1e-6 Å, R26) raises `CoreDisplacementError` (R7). The result is a pre-relaxation,
  **not a minimum**, and is never passed to `check_ground_state`.

### Dependencies and licence

- No new dependency.
- numpy (base) in `align`, `graft` and `report`. RDKit (base) is imported lazily inside
  `report.perceive_bonds`.
- `relax` imports only the `Optimizer` and `Engine` interfaces. geomeTRIC stays in the
  `opt-geometric` extra and the dev group (ADR-0023, v0.3.0 P1).
- `tests/unit/test_package.py` asserts that importing `eta_rxncat.mapping` and each of
  `.align`, `.graft`, `.report`, `.relax`, `.errors` in a fresh interpreter loads none of
  `geometric`, `torch`, `pyscf`, `fairchem`, `rdkit`.
- Licence-gate profiles are unchanged. MIT throughout. Nothing from nMap, Eta_Scripts or the
  starter's code is copied.

### Test tiers and tolerances (TJ Q6 "A")

- **Tier D** (default suite, `.venv`, offline):
  - alignment: 1e-10 Å vs the test-local SVD; det = +1;
  - clean-room vectors: 1e-6 Å;
  - surgery, order, index maps, charges, contacts, junction signs: exact;
  - M1: forming-core RMSD ≤ 0.10 Å; map re-derivation exact.
- **E2E** (`e2e`, `slow`, plus `xtb` or `mlip_uma`; the v0.3.0 named envs `.venv-accept-opt` and
  `.venv-accept-uma`): the M1 pre-relaxation per recipe. Gates: the core ≤ 1e-6 Å (R26), connectivity
  equal to TS1b_n's, junction signs equal and nonzero.
- **Regression after promotion:**
  - `m1_graft.json`: coordinate RMSD ≤ 1e-10 Å, no superposition, `index_map` and the map exact.
  - `m1_relaxed.<recipe>.json`: |ΔE| ≤ 1e-5 Eh, and heavy-atom RMSD ≤ 0.01 Å after heavy-atom
    superposition.
  - Every numeric key is unit-suffixed (R54); every list is order-fixed by the fixture or sorted
    (R55).

### Fixture M1 (TJ Q3 "B"; provisional per Q-E3, Q4 "A", R1 "B")

- **Files.** `tests/e2e/data/e2e5/xyz/{TS1a_n.xyz, 6_cyclobutene.xyz, TS1b_n.xyz}`, byte-identical
  (HF-1), plus three rows in `tests/e2e/data/e2e5/SOURCES.md` (R4).
- **`tests/e2e/data/e2e5/m1_ts1a_n_to_ts1b_n.yaml`** (team-drafted, provisional) with TJ's lists
  verbatim:
  - keep `[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15]`, delete `[7, 16, 17]`;
  - alignment pairs `[[2, 0], [3, 3], [10, 4], [11, 9]]`; `fragment_delete: []`;
  - active `[0, 1, 2, 3, 4, 5]`; `constrained_core: [1, 2, 3, 5]` (fix 1, TJ Q-E4 "A", noted);
  - charge 0, multiplicity 1;
  - `graft_to_ts1b_n_map` (the R2 stated-rule map; HF-7), and `map_rule` (one line naming R2).
- **Tier-D checks** (`tests/e2e/test_m1_graft.py`, default suite, writes nothing):
  - the graft builds (21 atoms, TS1b_n's formula);
  - the map is re-derived and equals the YAML's;
  - forming-core `[1, 2, 3, 5]` RMSD ≤ 0.10 Å;
  - `close_contacts` pairs = {(0, 15), (0, 17), (4, 16), (4, 20)} (HF-5, exact pairs);
  - `planar_pair_set_bool` is true;
  - the junctions are (2, 15) and (3, 16).
- **E2E** (`tests/e2e/test_m1_relax.py`): for each recipe (xtb `xtb_subprocess`/gfn2, UMA
  `uma_direct`/uma-s-1p2p1, the v0.3.0 recipes from `tests/e2e/e2e_env.py`), the run calls
  `relax_constrained_core(graft.product, engine, GeometricOptimizer(), core=[1, 2, 3, 5] re-indexed, options={"maxiter": 200})`.
  - Gates (R1, R16): perceived connectivity equal to TS1b_n's under the map; junction signs
    equal and nonzero.
  - Reported: full, active and forming-core RMSD to TS1b_n; appended heavy-atom RMSD after
    forming-core superposition; `n_steps`, `recovery_steps`, `wall_time_s`.
- **Candidates** (`tests/candidate_outputs/v0.4.0/`), committed in a candidates-only commit C2
  (ADR-0027): `m1_graft.json` (written by the xtb E2E run), `m1_relaxed.xtb.json` and
  `m1_relaxed.uma.json`. Each candidate carries:
  - `commit_sha` (= C1), environment, inputs' sha256, the spec, the map, the map rule;
  - the isomorphism count, the per-heavy-map forming-core RMSDs;
  - the contacts, junctions, gate outcomes and the real `test_outcome` (R56).

### Discrepancy register (`docs/prd/v0.4.0/DISCREPANCIES.md`, minimum rows)

Header: the zip's sha256 `6214b5e1…0b62` and the plan copy's `ad092dff…` (R3).

| ID | Source | Behaviour there | v0.4.0 decision |
|---|---|---|---|
| DV-01 | starter plan, PR #9 | adds enumeration, constrained-core pre-relaxation, "<0.1 Å core RMSD on Rh(I) (5+2)" | TJ Q2 "(b)": pre-relaxation in v0.4.0; enumeration and Rh(I) in v1.x (PD-008 decided) |
| DV-02 | starter `mapping/core_mapper.py` `kabsch_align` | SVD with determinant fix | Horn quaternion (A3) |
| DV-03 | starter `tests/unit/test_v040_core_mapper.py` | substituent alignment atoms all deleted, which its own validator rejects | the fragment side is its own ordered list (R15) |
| DV-04 | starter `core/models.py` `AtomMappingSpec` | `keep_atoms`/`delete_atoms`/`alignment_atoms`/`attachment_anchors`; no partition | ADR-0005 contract kept |
| DV-05 | starter `graft_substituent_onto_template` | `charge = template.charge + charge_delta`; multiplicity copied | explicit (Q5 "A") |
| DV-06 | same | keep minus delete silently skipped | partition validated; error |
| DV-07 | same | `core_alignment_rmsd` rounded to 6 d.p. | unrounded `alignment_rmsd_angstrom` |
| DV-08 | same | `name` field on `MolecularState` | names in metadata |
| DV-09 | starter `tests/e2e/fixtures/example_reaction_graph.yaml` | a mapping with `attachment_anchors` | reference only; format undefined (Q-E3) |
| DV-10 | `docs/prd/PLAN_DISCREPANCIES.md` | the v0.4.0 cell is `ad092dff…` | clarifying note only: that is the plan copy's sha256 (correct); the zip's is `6214b5e1…` (R3) |
| CR-01 | nMAP §3.1 | 1-based indices | 0-based (eta convention); vectors converted in the test loader |
| CR-02 | nMAP §5.2 (V2) | incoming-first product order | template-first (batch order, §5.1; Q4 "A") |
| CR-03 | nMAP §3.3, §10 Q1 | explicit incoming delete list; paired atoms not dropped | paired atoms always dropped, plus optional `fragment_delete` (TJ R1 "B") |
| CR-04 | nMAP §7 | no clash check | overlap floor 0.5 Å raises `GraftClashError`; close contacts recorded (TJ P1 "A") |
| CR-05 | nMAP §4.5 | 1 pair: crash; 2 / collinear: arbitrary spin or crash | `AlignmentError` (R12) |
| CR-06 | nMAP §4.3 | planar reversed sense undetected | planar flag + junction signed volumes (TJ R2 "A") |
| CR-07 | nMAP §3.1 | element mismatch accepted | `GraftInputError` (R17) |
| CR-08 | nMAP §3.2 | duplicate pairs act as weight 2; a template atom paired twice accepted | unique pair lists, else `ValidationError` |
| CR-09 | nMAP §3.2 | index 0 / negative wraps (V2) | `NonNegativeInt` and range checks; error |
| CR-10 | nMAP §3.4 | no charge or multiplicity | explicit product charge and multiplicity (TJ Q5 "A"); new behaviour |
| CR-11 | nMAP §3.3 | range syntax "a-b", reversed range silently empty, header-count defect | explicit integer lists only; no XYZ writer in v0.4.0 |
| CR-12 | nMAP §4.1 | batch tool pre-aligns and overwrites template files in place | no input is ever modified |
| CR-13 | nMAP §4.4, §10 Q6 | RMSD informational, no threshold | same in the API; M1's bound is a fixture gate (R19) |
| CR-14 | nMAP §3.2 | weights handed to an external fitter (unverified) | `superpose` weights explicit (weighted centroid and RMS); `graft` unweighted (R19) |
| CR-15 | nMAP §7 | no relaxation | core-frozen pre-relaxation in `mapping.relax` (TJ Q2 "(b)") |

## 6. Negative Constraints

- **DO NOT** open, clone, fetch or search Eta_Scripts or nMap (GitHub, any local or cached copy),
  or ask the clean-room rig's seats about its code (TJ Q1). Read only the approved documents in
  `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/`. Never copy code from the starter.
- **DO NOT** treat a later clean-room document as binding without resolve: a conflict with this
  SPEC is a replan.
- **DO NOT** move, round or recompute kept template coordinates during a graft.
- **DO NOT** infer a product charge or multiplicity.
- **DO NOT** allow a reflection in any alignment.
- **DO NOT** implement enumeration, multi-site grafting, TS optimisation, MCS mapping or YAML graph
  loading.
- **DO NOT** change `thermo/`, `conformers/`, `engines/`, `store/`, `optimize/`, `orchestrator/`
  or `AtomMappingSpec`. Stop and report if a slice needs to.
- **DO NOT** pass a dihedral constraint together with frozen atoms on any v0.4.0 path (R6).
- **DO NOT** run `check_ground_state` on a pre-relaxed TS guess, or call it a minimum.
- **DO NOT** write `tests/fixtures/`, promote a candidate, or read `tests/candidate_outputs/` or
  `spec/archive/` (including through `git show`, `git diff`, `git log -p`).
- **DO NOT** edit TJ's XYZ files.
- **DO NOT** loosen a TJ bound, or an architect bound in this SPEC, to make a run pass. A miss is
  stop-and-report.
- **DO NOT** edit `architecture.yml` by hand; run `HACF-install.sh`, `HACF-uninstall.sh` or
  `hyper_migrate.py apply`; push, tag or open a PR; or modify `PRDs/`.
- **N1** DO NOT commit or report a graft or relaxed candidate without its `close_contacts` and
  `junctions` in it.
- **N2** DO NOT choose an atom map by minimising any RMSD (R2).
- **N3** DO NOT execute TJ's 5-tier builder script anywhere. Extract with `ast.literal_eval`.
- **N4** DO NOT import `eta_rxncat.thermo._geometry` (or any `thermo` module) from
  `src/eta_rxncat/mapping/` or `tests/unit/mapping/`.
- **N5** DO NOT start an E2E, GPU or relaxation run without the host heavy-run check, recorded in
  the proof.
- **N6** DO NOT write a second e2e5 `SOURCES.md`.
- **N7** DO NOT edit `PLAN_DISCREPANCIES.md` hashes.

## 7. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The M1 pre-relaxation loses TS1b_n's connectivity (F1's contacts pull an H onto Cp) or flips a junction | Medium | High for v0.5.0's seed | Gated per recipe (R1, R16). A miss is H-M5 stop-and-report with the candidate written for TJ. |
| The stated-rule map is the wrong one of two symmetry-equivalent heavy maps | Low (rule measured to pick the 0.0498 Å family) | Medium | TJ confirms at Phase 3 (P2 "A"). Alternatives are reported (R2). |
| Pre-relaxation is slow or hangs on UMA/xtb | Medium | Medium | `maxiter` 200, `timeout 3600`, no dihedral constraints, heavy-run check (R6). |
| xtb/UMA move the frozen core > 1e-6 Å (R26) | Low | Medium | `CoreDisplacementError`, then stop-and-report (H-M3). |
| A later clean-room document disagrees with these conventions | Low | Medium | Replan through resolve, with both documents cited. |
| A seat touches nMap code | Low | High (TJ's copyright concern) | Hard rule in §6 and in every slice's seat rules. The operator logs every crossing. |
| The draft's "minimum distance 1.078 Å" is read as "no clash" | — | — | Closed: contacts are defined by perception, not by a distance floor (R1). |

## 8. Success Metrics

- Every user story passes. Every AGENTS.md required check exits 0 in every slice.
- Alignment agrees with the test-local SVD within 1e-10 Å on 1000 random sets, with det(R) = +1
  every time. Clean-room vectors 01–05 and 07-adapted match at 1e-6 Å; vector 06 is refused.
- M1:
  - forming-core RMSD ≤ 0.10 Å (TJ Q6 "A");
  - per recipe, connectivity and junction signs match TS1b_n's (TJ P1 "A", R2 "A");
  - the core is frozen to 1e-6 Å (R26);
  - all recorded in `ACCEPTANCE_RESULT.json` with the commit sha.
- Candidates are committed in candidates-only commits. `tests/fixtures/v0.4.0/` is written only
  by TJ. The verdict is `pass` with zero `fail`, `pending_*` or missing checks. The version is
  0.4.0.
- `import eta_rxncat.mapping` loads no heavy module.
- `DISCREPANCIES.md` has DV-01…DV-10 and CR-01…CR-15. PD-008 is decided.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.4.0.1 | slices/01-starter | Unpack the v0.4.0 reference starter byte-identical into docs/prd/v0.4.0/, write the v0.4.0 discrepancy register (DV-01 to DV-10, CR-01 to CR-15) and mark PD-008 decided, changing no hash in PLAN_DISCREPANCIES.md. |
| OPR.0.4.0.2 | slices/02-graft-contracts | Add frozen strict core contracts GraftSpec, GraftResult, CloseContact and JunctionVolume in core/mapping_models.py with pass/reject tests for every validator, keeping eta_rxncat.core free of numpy and RDKit. |
| OPR.0.4.0.3 | slices/03-align | Create eta_rxncat.mapping with its errors and Horn-quaternion superpose that refuses degenerate pair sets and reports planarity, create the eta_rxncat_mapping ledger node, and prove alignment against a test-local SVD and clean-room vectors 01-03 and 06. |
| OPR.0.4.0.4 | slices/04-graft | Implement ordered graft surgery (paired fragment atoms dropped, optional fragment_delete, explicit charge/spin, re-indexed active atoms and core, overlap floor) with recorded close contacts, junction signed volumes and the planar flag, proved on hand-built cases and clean-room vectors 04, 05 and 07. |
| OPR.0.4.0.5 | slices/05-constrained-relax | Implement relax_constrained_core: core-frozen pre-relaxation through Optimizer.minimize with frozen_atom_indices and never a dihedral constraint, raising CoreDisplacementError above 1e-6 A (replan 1, R26), proved with a recording fake and UFF. |
| OPR.0.4.0.6 | slices/06-m1-fixture | Land TJ's three M1 structures with provenance and the provisional M1 YAML with the stated-rule atom map, prove the pure graft by tier-D checks, pre-relax on xtb and UMA gated on TS1b_n connectivity and junction signs, and commit the three candidates for Phase 3. |
| OPR.0.4.0.7 | slices/07-acceptance-record | Add the M1 regression and map-confirmation checks, run M1 on both recipes into docs/prd/v0.4.0/ACCEPTANCE_RESULT.json with real outcomes and pending states, and derive the README v0.4.0 claims, with no dependence on TJ acting first. |
| OPR.0.4.0.8 | slices/08-acceptance-verdict | After TJ's Phase 3 promotion, rerun M1 on both recipes with ETA_RXNCAT_ACCEPTANCE=1 and zero skips, record the regression and map-confirmation verdicts, bump the version to 0.4.0 only on a pass verdict and derive the final README claims. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
