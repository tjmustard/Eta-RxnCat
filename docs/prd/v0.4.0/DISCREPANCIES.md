# v0.4.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.4.0.zip` (sha256
`6214b5e1a25f85a9efc6117f5d97ec7f7aa2db2c5a8a4098ea390fb5c48a0b62`) ships a starter implementation,
unpacked here under `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/` (32 files, byte-identical to the zip, plus the
gate file `.ruff.toml`, which is not part of the starter and keeps the pre-commit lint off it). The
plan copy inside it, `Eta-RxnCat-v0.4.0/Eta-RxnCat_Living_Master_Plan.md`, has sha256
`ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438`. The starter is reference only:
the code in `src/` and `tests/` is written fresh from the mission's slice specs, and no code is copied
from it. This register records every difference between the starter (and the clean-room nMAP
behaviour spec, for CR-01…CR-15) and the rewrite, so each one can be reviewed and fixed if needed.

TJ, Q2 (v0.3.0, standing): "B use it as reference only. Keep a list of the discrepancies so that if
needed, we can go through each of them and fix any issues that arise."

## Scope

The minimum rows of mission `missions/release-0.4.0/SPEC.md` §5 "Discrepancy register". Starter paths
are relative to `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/`. CR rows cite sections of the clean-room nMAP
behaviour spec, `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/NMAP_BEHAVIOUR_SPEC.md` (sha256
`a56c449b39e92eab23a766739e0bccce111619329ae4e066355876e35dee662d`), the only nMAP-derived input
(TJ Q1, clean room).

**Status.** `decided` means the v0.4.0 decision is fixed; the slice that implements it is named in the
mission SPEC. The auditor of that slice lists the row in its PASS handoff, and the scribe closes it at
v0.4.0 docs time. `closed (slice NN; audit <row>)` means the audit of that slice passed with the row
met. The slice 08 audit (`qitem-20261123230029-4838d875`) mapped every row to its implementing slices.
All 25 rows were closed at v0.4.0 docs time.

CR-11 is the one row that no per-slice audit lists by name. The slice 08 audit's map leaves it out,
and its closing line covers it ("every DV-01…DV-10 and CR-01…CR-15 row's implementing slice has passed
audit"). Slice 04's spec names CR-01…CR-11 in its scope. The scribe checked it against the code:
`GraftSpec` index fields are strict integer lists, a range string such as `"0-2"` raises
`ValidationError`, and nothing in `src/eta_rxncat/mapping/` reads or writes XYZ.

## Register

| ID | Source | Behaviour there | v0.4.0 decision | Status |
|---|---|---|---|---|
| DV-01 | starter plan, PR #9 | adds enumeration, constrained-core pre-relaxation, "<0.1 Å core RMSD on Rh(I) (5+2)" | TJ Q2 "(b)": pre-relaxation in v0.4.0; enumeration out of v0.4.0, kept at v0.7.0 (TJ roadmap B); Rh(I) (5+2) in v1.x. | closed (slices 05, 06, 08; audit `qitem-20261123205137-b02e9d41`, `qitem-20261123211443-d3cbec10`, `qitem-20261123230029-4838d875`; text corrected per R28) |
| DV-02 | `mapping/core_mapper.py` `kabsch_align` | SVD with determinant fix | Horn quaternion. | closed (slice 03; audit `qitem-20261123195455-678bc331`) |
| DV-03 | `tests/unit/test_v040_core_mapper.py` | substituent alignment atoms all deleted, which its own validator rejects | the fragment side is its own ordered list (`fragment_alignment`), paired fragment atoms always dropped. | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`) |
| DV-04 | `core/models.py` `AtomMappingSpec` | `keep_atoms`/`delete_atoms`/`alignment_atoms`/`attachment_anchors`, no partition | the ADR-0005 contract (`keep`, `delete`, `alignment`, `anchors`, partition) kept. | closed (slice 02; audit `qitem-20261123193947-cf5d5032`) |
| DV-05 | `graft_substituent_onto_template` | `charge = template.charge + charge_delta`, multiplicity copied | explicit product charge and multiplicity (TJ Q5 "A"). | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`) |
| DV-06 | same | keep minus delete silently skipped | partition validated; an error, never a skip. | closed (slice 04; audit `qitem-20261123203312-f875c673`) |
| DV-07 | same | `core_alignment_rmsd` rounded to 6 d.p. | unrounded `alignment_rmsd_angstrom`. | closed (slice 02; audit `qitem-20261123193947-cf5d5032`) |
| DV-08 | same | `name` field on `MolecularState` | names go in metadata. | closed (slice 02; audit `qitem-20261123193947-cf5d5032`) |
| DV-09 | `tests/e2e/fixtures/example_reaction_graph.yaml` | a mapping with `attachment_anchors` | reference only; the YAML/JSON format is undefined (TJ Q-E3); `GraftSpec` refuses non-empty `anchors`. | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`) |
| DV-10 | `docs/prd/PLAN_DISCREPANCIES.md` | the v0.4.0 cell reads `ad092dff…` | **clarifying note, no change**: that column is the plan copy's sha256 inside the zip, which is correct; the zip's own sha256 is `6214b5e1…` (mission R3). | closed (slice 01; audit `qitem-20261123191350-9f505a85`) |
| CR-01 | nMAP behaviour spec §3.1 | 1-based indices | 0-based (eta convention); vectors converted in the test loader | closed (slices 03, 04; audit `qitem-20261123195455-678bc331`, `qitem-20261123203312-f875c673`) |
| CR-02 | nMAP behaviour spec §5.2 (V2) | incoming-first product order | template-first (batch order, §5.1; Q4 "A") | closed (slice 04; audit `qitem-20261123203312-f875c673`) |
| CR-03 | nMAP behaviour spec §3.3, §10 Q1 | explicit incoming delete list; paired atoms not dropped | paired atoms always dropped, plus optional `fragment_delete` (TJ R1 "B") | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`) |
| CR-04 | nMAP behaviour spec §7 | no clash check | overlap floor 0.5 Å raises `GraftClashError`; close contacts recorded (TJ P1 "A") | closed (slices 04, 06; audit `qitem-20261123203312-f875c673`, `qitem-20261123211443-d3cbec10`) |
| CR-05 | nMAP behaviour spec §4.5 | 1 pair: crash; 2 / collinear: arbitrary spin or crash | `AlignmentError` (R12) | closed (slice 03; audit `qitem-20261123195455-678bc331`) |
| CR-06 | nMAP behaviour spec §4.3 | planar reversed sense undetected | planar flag + junction signed volumes (TJ R2 "A") | closed (slices 04, 06; audit `qitem-20261123203312-f875c673`, `qitem-20261123211443-d3cbec10`) |
| CR-07 | nMAP behaviour spec §3.1 | element mismatch accepted | `GraftInputError` (R17) | closed (slice 04; audit `qitem-20261123203312-f875c673`) |
| CR-08 | nMAP behaviour spec §3.2 | duplicate pairs act as weight 2; a template atom paired twice accepted | unique pair lists, else `ValidationError` | closed (slice 02; audit `qitem-20261123193947-cf5d5032`) |
| CR-09 | nMAP behaviour spec §3.2 | index 0 / negative wraps (V2) | `NonNegativeInt` and range checks; error | closed (slice 02; audit `qitem-20261123193947-cf5d5032`) |
| CR-10 | nMAP behaviour spec §3.4 | no charge or multiplicity | explicit product charge and multiplicity (TJ Q5 "A"); new behaviour | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`) |
| CR-11 | nMAP behaviour spec §3.3 | range syntax "a-b", reversed range silently empty, header-count defect | explicit integer lists only; no XYZ writer in v0.4.0 | closed (slices 02, 04; audit `qitem-20261123193947-cf5d5032`, `qitem-20261123203312-f875c673`; no audit names this row, see the Status note) |
| CR-12 | nMAP behaviour spec §4.1 | batch tool pre-aligns and overwrites template files in place | no input is ever modified | closed (slice 04; audit `qitem-20261123203312-f875c673`) |
| CR-13 | nMAP behaviour spec §4.4, §10 Q6 | RMSD informational, no threshold | same in the API; M1's bound is a fixture gate (R19) | closed (slices 03, 06, 07; audit `qitem-20261123195455-678bc331`, `qitem-20261123211443-d3cbec10`, `qitem-20261123214503-e4782517`) |
| CR-14 | nMAP behaviour spec §3.2 | weights handed to an external fitter (unverified) | `superpose` weights explicit (weighted centroid and RMS); `graft` unweighted (R19) | closed (slices 03, 04; audit `qitem-20261123195455-678bc331`, `qitem-20261123203312-f875c673`) |
| CR-15 | nMAP behaviour spec §7 | no relaxation | core-frozen pre-relaxation in `mapping.relax` (TJ Q2 "(b)") | closed (slices 05, 06; audit `qitem-20261123205137-b02e9d41`, `qitem-20261123211443-d3cbec10`) |
