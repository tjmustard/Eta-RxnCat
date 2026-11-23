---
id: OPR.0.4.0.1
slice: 01-starter
mission: release-0.4.0
status: done
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Unpack the v0.4.0 reference starter byte-identical into docs/prd/v0.4.0/, write the v0.4.0 discrepancy register (DV-01 to DV-10, CR-01 to CR-15) and mark PD-008 decided, changing no hash in PLAN_DISCREPANCIES.md."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["docs/prd/v0.4.0/**", docs/prd/PLAN_DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 starter unpack, discrepancy register and PD-008

## Intent

Unpack the v0.4.0 reference starter byte-identical into `docs/prd/v0.4.0/`, write the v0.4.0
discrepancy register (DV-01…DV-10, CR-01…CR-15), and mark PD-008 decided, without changing any
hash in `docs/prd/PLAN_DISCREPANCIES.md`.

Context the builder needs:
- **The starter is reference only** (TJ Q2 "B"; ADR-0007). No gate, lint or test scans
  `docs/prd/v0.4.0/`. Follow v0.3.0's layout: `docs/prd/v0.3.0/Eta-RxnCat-v0.3.0/…` beside
  `docs/prd/v0.3.0/DISCREPANCIES.md`.
- **Zip:** `PRDs/Eta-RxnCat-v0.4.0.zip`, sha256
  `6214b5e1a25f85a9efc6117f5d97ec7f7aa2db2c5a8a4098ea390fb5c48a0b62`, 32 files. Unzip it in
  scratch under TMPDIR and copy the tree to `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/`. Every file's
  sha256 must equal this list (resolve measured 2026-11-23):

    be9a8b1192d13313be459dfc026e2119d60ade8e0d708080a999509792d8401b  Eta-RxnCat-v0.4.0/AGENTS.md
    ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438  Eta-RxnCat-v0.4.0/Eta-RxnCat_Living_Master_Plan.md
    119c28fbea4c0ab6aa904a68b4bddf48861c000f7ebe2b769ddaa008174cde24  Eta-RxnCat-v0.4.0/pyproject.toml
    0142d01d180d7682bb00d458f7320ca256152a2d3db06da53d6bbc37e718806a  Eta-RxnCat-v0.4.0/README.md
    4c1f0353223fb5d1e5bc2bfe7c473a5d4ae7f7d95a5748311e290ade62eaf89c  Eta-RxnCat-v0.4.0/src/eta_rxncat/cli.py
    d3d5fb49e23d28a98d93a5b26c58f3b78186a339b0e3ee259e78b62e5263eb72  Eta-RxnCat-v0.4.0/src/eta_rxncat/conformers/ensemble.py
    463b53ab83c27dd23d0df67693a8968fba186d38a911e99007e69532e388bd08  Eta-RxnCat-v0.4.0/src/eta_rxncat/conformers/__init__.py
    71af842c0cc19380273a916c4e068ce23b7c48c83a7b86ebd1d5daaa709c4d93  Eta-RxnCat-v0.4.0/src/eta_rxncat/core/__init__.py
    13634dec4b731c9d85e1c6865b45d2310e1bff1c9ecdb29b24590f8d862f9fd0  Eta-RxnCat-v0.4.0/src/eta_rxncat/core/models.py
    6b2b85a536e58156e7e1bf005ebe86f52595d34d5b35f8fa1e463227924a25ae  Eta-RxnCat-v0.4.0/src/eta_rxncat/core/reaction_graph.py
    1a7faff35ed4f5a8487241ac2b18914b7d7be5807dd97e0988bd3a8c81beb1ed  Eta-RxnCat-v0.4.0/src/eta_rxncat/core/thermo.py
    23177208c1770212f3c4b74538cb230cf766ad2fa170f2ebab663cadf4e738df  Eta-RxnCat-v0.4.0/src/eta_rxncat/engines/base.py
    472fcbd4d8da15105307aa9aabc774c5d8b13afb8c8c6cd1daca98a02d1e5e54  Eta-RxnCat-v0.4.0/src/eta_rxncat/engines/__init__.py
    7651aec1a626da6abb4568833d97ad0c6836c7b22cff1801863afbb8ec320156  Eta-RxnCat-v0.4.0/src/eta_rxncat/engines/mlip.py
    2b214584bc6adfe6704a654b9045965bcf968f18985d28186b2d53d59076faa7  Eta-RxnCat-v0.4.0/src/eta_rxncat/engines/pyscf_engine.py
    fbd24e11b4c1269abddb2db9a378a32409e8c34c03cb8486592d6c2859d73a96  Eta-RxnCat-v0.4.0/src/eta_rxncat/engines/rdkit_xtb.py
    9d13ed3eceaecc36bf555e990adc9e72d39b78c642e6dc4d09503d98ac04fb46  Eta-RxnCat-v0.4.0/src/eta_rxncat/__init__.py
    9fd962372458dc60998b86fa5730a6dc1e53df4b837c3bcb1362267c99a101ec  Eta-RxnCat-v0.4.0/src/eta_rxncat/mapping/core_mapper.py
    8f7611a72f269f757fb8345851dd3357d51f857034ad3df36a54007994097071  Eta-RxnCat-v0.4.0/src/eta_rxncat/mapping/__init__.py
    6320acfa603878c6698bd931dfe706ae577c599320d30da5cad1d01a422f42e5  Eta-RxnCat-v0.4.0/src/eta_rxncat/optimize/gs_optimizer.py
    acae51005256dfe263067472a1388d44a63af9a10ba3f3173575bf1f95b67c86  Eta-RxnCat-v0.4.0/src/eta_rxncat/optimize/__init__.py
    00a569d23af4560266bf0366132139c0d441c58af6cd17e4b38be9f582713814  Eta-RxnCat-v0.4.0/src/eta_rxncat/orchestrator/__init__.py
    893c7654b6842912c3bd6fc9e528def8ffc64623f606f03aad02f94b9d018486  Eta-RxnCat-v0.4.0/src/eta_rxncat/store/artifact_store.py
    54c757b6364550b5f5cf70d4609640067abed565b898170b229a0b595e2fdfb4  Eta-RxnCat-v0.4.0/src/eta_rxncat/store/__init__.py
    c7ff3b3fac91b73a9e5243d122ef21a3343e2ccb3687adc220b8453fae50fb0e  Eta-RxnCat-v0.4.0/src/eta_rxncat/utils/hw_probe.py
    9d0cfcd002e95e69b35cb9dbbf828b18a05de0e963b7f6a22e3719d6a27ea14e  Eta-RxnCat-v0.4.0/src/eta_rxncat/utils/__init__.py
    4905299ad38147ce2fc29527cd2812bf707f11187bb76bd01ac1e2830872a319  Eta-RxnCat-v0.4.0/tests/e2e/fixtures/example_reaction_graph.yaml
    19daf6124b844070c4e6ad96a02dac7e17d5d89640b9b83a993708440aff02a7  Eta-RxnCat-v0.4.0/tests/unit/test_core_schemas.py
    ad17d0bd4c47e724df63ad88cd62c9a5451723cef379d4411d8105d73a56ec78  Eta-RxnCat-v0.4.0/tests/unit/test_engines_v020.py
    3a579cfbce91c86a4bb813ddd3a537b208d8fd77742a98e1f2c267256dcb8ca8  Eta-RxnCat-v0.4.0/tests/unit/test_hw_probe.py
    1496c28244a0f8374bef60ab81328aa08c5c36190658f44a2e2c754c6fa29ef0  Eta-RxnCat-v0.4.0/tests/unit/test_v030_thermo_conformers.py
    7091704036f57eb9705822095f4bbca8203d1c81c65bd6f764eb99bdd7c64107  Eta-RxnCat-v0.4.0/tests/unit/test_v040_core_mapper.py
- **`docs/prd/v0.4.0/DISCREPANCIES.md`.**
  - Header: the zip's sha256 (above), and the plan copy's sha256 inside it,
    `ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438`.
  - Then the table with columns `ID | Source | Behaviour there | v0.4.0 decision | Status`, with
    exactly these rows (copy the decisions as written; Status `decided` unless noted):
    - DV-01 starter plan, PR #9: adds enumeration, constrained-core pre-relaxation, "<0.1 Å core RMSD on Rh(I) (5+2)" → TJ Q2 "(b)": pre-relaxation in v0.4.0; enumeration and Rh(I) (5+2) in v1.x.
    - DV-02 `mapping/core_mapper.py` `kabsch_align`: SVD with determinant fix → Horn quaternion.
    - DV-03 `tests/unit/test_v040_core_mapper.py`: substituent alignment atoms all deleted, which its own validator rejects → the fragment side is its own ordered list (`fragment_alignment`), paired fragment atoms always dropped.
    - DV-04 `core/models.py` `AtomMappingSpec`: `keep_atoms`/`delete_atoms`/`alignment_atoms`/`attachment_anchors`, no partition → the ADR-0005 contract (`keep`, `delete`, `alignment`, `anchors`, partition) kept.
    - DV-05 `graft_substituent_onto_template`: `charge = template.charge + charge_delta`, multiplicity copied → explicit product charge and multiplicity (TJ Q5 "A").
    - DV-06 same: keep minus delete silently skipped → partition validated; an error, never a skip.
    - DV-07 same: `core_alignment_rmsd` rounded to 6 d.p. → unrounded `alignment_rmsd_angstrom`.
    - DV-08 same: `name` field on `MolecularState` → names go in metadata.
    - DV-09 `tests/e2e/fixtures/example_reaction_graph.yaml`: a mapping with `attachment_anchors` → reference only; the YAML/JSON format is undefined (TJ Q-E3); `GraftSpec` refuses non-empty `anchors`.
    - DV-10 `docs/prd/PLAN_DISCREPANCIES.md`: the v0.4.0 cell reads `ad092dff…` → **clarifying note, no change**: that column is the plan copy's sha256 inside the zip, which is correct; the zip's own sha256 is `6214b5e1…` (mission R3).
    - CR-01 … CR-15: the clean-room divergences, copied from the mission SPEC §5 "Discrepancy register" rows CR-01 to CR-15 verbatim. Source column: "nMAP behaviour spec §x" (`~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/NMAP_BEHAVIOUR_SPEC.md`, sha256 `a56c449b…7006`).
- **PD-008** in `docs/prd/PLAN_DISCREPANCIES.md` (currently `open`): set its Status cell to:
  `decided (TJ v0.4.0 Q2: "Q2. (b)", row qitem-20261123174816-79277143c4b9b81a: constrained-core pre-relaxation in v0.4.0; R-group/ligand enumeration and the Rh(I) (5+2) complexes in v1.x)`.
  Change **nothing else** in that file. No hash cell changes; the v0.4.0 hash `ad092dff…` is
  correct (N7, mission R3).
- **Roadmap note (not yours to act on):** the PRDs/ plan still lists enumeration at v0.7.0 (PR #14).
  Do not edit `PRDs/`.

**Seat rules for every v0.4.0 slice.** These are self-contained. The mission SPEC is
`missions/release-0.4.0/SPEC.md`; its R-rows are cited by number.

- **Clean room (TJ Q1, hard rule).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach".
  - No seat opens, clones, fetches or searches Eta_Scripts or nMap in any form (GitHub, a local
    or cached copy, a web search, a code search).
  - No seat asks the clean-room rig's seats about code.
  - Behaviour comes only from this SPEC, TJ's M1 spec and the approved documents in
    `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/`.
  - Never copy code from the starter (`docs/prd/v0.4.0/`).
  - A conflict between a clean-room document and this SPEC is a stop-and-report for a replan.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.4.0`, cut re-entrantly from Base, which is
  the mission commit on main (parent `c3506e6`). One code commit per slice, unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff.
- **Code graph first.** The first command of the slice is
  `python3 .agents/scripts/hyper_codegraph.py index`, and it must print `index: ok` (the red team
  saw `stale_index`). Anything else stops the slice. The audit treats
  `code_graph.status != ok` as a finding. The graph only widens a blast radius, never narrows it.
- **Ledger.** Write it only with `hyper_ledger.py` / `hypergraph_updater.py`, never by hand.
  - On existing nodes use `ensure-node --id <node>` with the **full** `--files` list (it
    replaces).
  - Count the node's globs before and after.
  - `eta_rxncat_engines` is not touched.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF.** HACF is v0.6.2. No `HACF-install.sh` (a plain run silently DOWNGRADES to 0.6.1 right
  now), no `HACF-uninstall.sh`, no `hyper_migrate.py apply`.
- **OpenRig 0.7.21.** `hyper_migrate.py verify` runs `rig scope audit` (HACF v0.6.2 on OpenRig
  0.7.21). If `hyper_spec.py` or `hyper_migrate.py` warn "outside the pinned contract", note it in
  the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git.
  Every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host memory (heavy runs).** Before any E2E, GPU, relaxation or full-suite run:
  - run `free -g` and list other rigs' heavy python/pytest/engine processes (`ps`);
  - if another heavy run is active, wait (poll at most every 5 minutes with Monitor or a
    background wait, not a foreground sleep);
  - record the check in the proof.

  Heavy runs are sequential. Never kill another rig's process.
- **v0.3.0 lessons (mission R23):**
  - **R54:** every numeric key in an output carries its unit suffix.
  - **R55:** no list in a compared output is in record or energy order; it is fixed by the fixture
    or sorted by an energy-independent key.
  - **R56:** a test records its real outcome through one `gated_outcome`, and `pending_*` fails
    under `ETA_RXNCAT_ACCEPTANCE=1`.
  - **R50:** any code that reads a store or runner payload checks `failed_reason` first (v0.4.0
    adds no such reader).
  - **Candidates (ADR-0027):** code commit C1 with a clean tree, run the E2E at C1, then commit
    only `tests/candidate_outputs/v0.4.0/*` as C2.
- **Required checks** (AGENTS.md), all exit 0 before each commit:
  - `uv sync --locked`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy`
  - `uv run pytest`
  - `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception.
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it, and never loosen a
  tolerance (TJ's or this SPEC's).
- **Never** push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 10/10.** Every byte and every row is specified.

## Mini-requirements

1. `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/` holds the 32 files, each with the sha256 listed above.
2. `docs/prd/v0.4.0/DISCREPANCIES.md` exists with the header hashes and rows DV-01…DV-10 and
   CR-01…CR-15.
3. PD-008's status cell reads exactly the decided text above.
4. `git diff Start -- docs/prd/PLAN_DISCREPANCIES.md` shows a change on the PD-008 line only.
5. The ledger: the updater marks `eta_rxncat_scaffold` (`docs/**`). No glob changes in this slice.

## 3. Implementation Plan (Task List)

- [ ] Task 1: `python3 .agents/scripts/hyper_codegraph.py index` → `index: ok`. Cut or check out the branch; record Start.
- [ ] Task 2: unzip in scratch; copy; verify all 32 sha256 against the list; remove scratch.
- [ ] Task 3: write `DISCREPANCIES.md`; edit the PD-008 cell.
- [ ] Task 4: required checks; commit; `hypergraph_updater.py` for the blast radius.

## 4. The Negative Space (Constraints)

- **DO NOT** edit any file under `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/` after copying it.
- **DO NOT** change any hash in `PLAN_DISCREPANCIES.md`, or any row other than PD-008's status.
- **DO NOT** touch `PRDs/`.
- **DO NOT** copy code from the starter into `src/` or `tests/`.

## Proof contract

- [ ] A script over `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/` prints 32 files and 32 sha256 matches.
- [ ] `DISCREPANCIES.md` contains every ID DV-01…DV-10 and CR-01…CR-15 (`grep -c`), and both header hashes.
- [ ] `git diff Start..HEAD -- docs/prd/PLAN_DISCREPANCIES.md` touches only the PD-008 line.
- [ ] The required checks exit 0.

## Source material

- Mission SPEC §3 item 1, §5 R3, R24, "Discrepancy register"; `docs/prd/v0.3.0/DISCREPANCIES.md`
  (format precedent); `docs/prd/PLAN_DISCREPANCIES.md`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- none (first slice)
