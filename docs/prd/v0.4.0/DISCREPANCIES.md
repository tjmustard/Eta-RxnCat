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
v0.4.0 docs time.

## Register

| ID | Source | Behaviour there | v0.4.0 decision | Status |
|---|---|---|---|---|
| DV-01 | starter plan, PR #9 | adds enumeration, constrained-core pre-relaxation, "<0.1 Å core RMSD on Rh(I) (5+2)" | TJ Q2 "(b)": pre-relaxation in v0.4.0; enumeration out of v0.4.0, kept at v0.7.0 (TJ roadmap B); Rh(I) (5+2) in v1.x. | decided |
| DV-02 | `mapping/core_mapper.py` `kabsch_align` | SVD with determinant fix | Horn quaternion. | decided |
| DV-03 | `tests/unit/test_v040_core_mapper.py` | substituent alignment atoms all deleted, which its own validator rejects | the fragment side is its own ordered list (`fragment_alignment`), paired fragment atoms always dropped. | decided |
| DV-04 | `core/models.py` `AtomMappingSpec` | `keep_atoms`/`delete_atoms`/`alignment_atoms`/`attachment_anchors`, no partition | the ADR-0005 contract (`keep`, `delete`, `alignment`, `anchors`, partition) kept. | decided |
| DV-05 | `graft_substituent_onto_template` | `charge = template.charge + charge_delta`, multiplicity copied | explicit product charge and multiplicity (TJ Q5 "A"). | decided |
| DV-06 | same | keep minus delete silently skipped | partition validated; an error, never a skip. | decided |
| DV-07 | same | `core_alignment_rmsd` rounded to 6 d.p. | unrounded `alignment_rmsd_angstrom`. | decided |
| DV-08 | same | `name` field on `MolecularState` | names go in metadata. | decided |
| DV-09 | `tests/e2e/fixtures/example_reaction_graph.yaml` | a mapping with `attachment_anchors` | reference only; the YAML/JSON format is undefined (TJ Q-E3); `GraftSpec` refuses non-empty `anchors`. | decided |
| DV-10 | `docs/prd/PLAN_DISCREPANCIES.md` | the v0.4.0 cell reads `ad092dff…` | **clarifying note, no change**: that column is the plan copy's sha256 inside the zip, which is correct; the zip's own sha256 is `6214b5e1…` (mission R3). | decided |
| CR-01 | nMAP behaviour spec §3.1 | 1-based indices | 0-based (eta convention); vectors converted in the test loader | decided |
| CR-02 | nMAP behaviour spec §5.2 (V2) | incoming-first product order | template-first (batch order, §5.1; Q4 "A") | decided |
| CR-03 | nMAP behaviour spec §3.3, §10 Q1 | explicit incoming delete list; paired atoms not dropped | paired atoms always dropped, plus optional `fragment_delete` (TJ R1 "B") | decided |
| CR-04 | nMAP behaviour spec §7 | no clash check | overlap floor 0.5 Å raises `GraftClashError`; close contacts recorded (TJ P1 "A") | decided |
| CR-05 | nMAP behaviour spec §4.5 | 1 pair: crash; 2 / collinear: arbitrary spin or crash | `AlignmentError` (R12) | decided |
| CR-06 | nMAP behaviour spec §4.3 | planar reversed sense undetected | planar flag + junction signed volumes (TJ R2 "A") | decided |
| CR-07 | nMAP behaviour spec §3.1 | element mismatch accepted | `GraftInputError` (R17) | decided |
| CR-08 | nMAP behaviour spec §3.2 | duplicate pairs act as weight 2; a template atom paired twice accepted | unique pair lists, else `ValidationError` | decided |
| CR-09 | nMAP behaviour spec §3.2 | index 0 / negative wraps (V2) | `NonNegativeInt` and range checks; error | decided |
| CR-10 | nMAP behaviour spec §3.4 | no charge or multiplicity | explicit product charge and multiplicity (TJ Q5 "A"); new behaviour | decided |
| CR-11 | nMAP behaviour spec §3.3 | range syntax "a-b", reversed range silently empty, header-count defect | explicit integer lists only; no XYZ writer in v0.4.0 | decided |
| CR-12 | nMAP behaviour spec §4.1 | batch tool pre-aligns and overwrites template files in place | no input is ever modified | decided |
| CR-13 | nMAP behaviour spec §4.4, §10 Q6 | RMSD informational, no threshold | same in the API; M1's bound is a fixture gate (R19) | decided |
| CR-14 | nMAP behaviour spec §3.2 | weights handed to an external fitter (unverified) | `superpose` weights explicit (weighted centroid and RMS); `graft` unweighted (R19) | decided |
| CR-15 | nMAP behaviour spec §7 | no relaxation | core-frozen pre-relaxation in `mapping.relax` (TJ Q2 "(b)") | decided |
