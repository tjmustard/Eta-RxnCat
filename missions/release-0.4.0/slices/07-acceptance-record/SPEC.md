---
id: OPR.0.4.0.7
slice: 07-acceptance-record
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Add the M1 regression and map-confirmation checks, run M1 on both recipes into docs/prd/v0.4.0/ACCEPTANCE_RESULT.json with real outcomes and pending states, and derive the README v0.4.0 claims, with no dependence on TJ acting first."
depends_on: [OPR.0.4.0.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.4.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 acceptance record (pre-promotion) and README derivation

## Intent

Write the M1 regression and map-confirmation checks (pending until TJ promotes). Run M1 on both
recipes into `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json` with real per-check outcomes and pending
states, and derive the README v0.4.0 claims from that record. This slice's PASS does not depend on
TJ acting first.

Context the builder needs:
- The pattern is v0.3.0's slices 09/10. Read `tests/e2e/acceptance.py`, `acceptance_record.py`,
  `regression.py`, `test_accept_v030.py`, `test_acceptance_record.py`, `test_gated_outcome.py` and
  `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`.
  - Reuse `gated_outcome` (R56): one function decides the fragment's `test_outcome` /
    `failed_checks` and the assertion; `pending_*` fails under `ETA_RXNCAT_ACCEPTANCE=1`; a
    missing fragment is `missing`.
  - Reuse the regression machinery where it fits. Add an M1 comparison only where it does not.
- **The driver is `tests/e2e/test_accept_v040.py`** (markers `e2e`, `acceptance`, plus `xtb` or
  `mlip_uma`). It is **not** under `tests/acceptance/**`, which belongs to the engines node
  (mission R8). Add it to `eta_rxncat_mapping`'s files (full `--files` list).
- **The record run must not rewrite the committed candidates.** Set `ETA_RXNCAT_CANDIDATE_DIR`
  and `ETA_RXNCAT_ACCEPTANCE_OUT` to scratch under TMPDIR.
- **Checks per recipe** (`fixtures.m1.<recipe>`), each with a real outcome:
  - `forming_core_rmsd`:
    - value `forming_core_rmsd_angstrom`;
    - bound 0.10 (TJ Q6 "A");
    - `pass`/`fail` (recipe-independent; recorded under `fixtures.m1.graft`).
  - `relaxed_gates`: g1 core displacement ≤ 1e-6 Å (mission R26), g2 connectivity equal, g3 junction signs
    equal and nonzero (TJ P1 "A", R2 "A"), each with values; `pass`/`fail`.
  - `regression_graft` (recipe-independent): against `tests/fixtures/v0.4.0/m1_graft.json`.
    - Coordinate RMSD with **no** superposition ≤ 1e-10 Å.
    - `index_map`, `graft_to_ts1b_n_map`, `close_contacts` pairs and junction signs exact.
    - `pending_promotion` when the fixture is absent.
  - `regression_relaxed`: against `tests/fixtures/v0.4.0/m1_relaxed.<recipe>.json`.
    - |ΔE| ≤ 1e-5 Eh.
    - Heavy-atom RMSD ≤ 0.01 Å **after** Horn superposition over heavy atoms (mission R20(d)).
    - `pending_promotion` when absent.
  - `map_confirmation`: `confirmed` when `tests/fixtures/v0.4.0/m1_graft.json` exists and its
    `graft_to_ts1b_n_map` equals the YAML's. Otherwise `pending_confirmation`; `fail` if it exists
    and differs. Promotion is TJ's confirmation (TJ P2 "A", mission R2, R25). Nothing reads the
    promoted file's own status field.
  - Metrics: `wall_time_s`, `n_steps`, `n_engine_calls`, `recovery_steps`, device, the reported
    RMSDs.
- **The record** (`record_schema: 1`):
  - `commit_sha`, `run_at_utc`, `hardware`, `commands`, `logs`, `fixtures.m1.{graft,xtb,uma}`;
  - `default_suite` (the `uv run pytest` command, exit code, and the passed/failed counts
    including the clean-room vectors);
  - `known_limits`;
  - `verdict` (`pass` only when nothing is `fail`, `pending_*` or `missing`; here it is expected
    to be `pending`).

  `known_limits` holds exactly these lines:
  - "the pure M1 graft keeps four close contacts (two C…H at 1.12 Å, two C…C at 1.96 Å); they are
    recorded, not refused, and the pre-relaxation is gated on TS1b_n's connectivity (TJ P1 A)";
  - "on M1 the pure-graft junction signs are undetermined (planar pair set); the handedness check
    is decided on the relaxed structures (TJ R2 A)";
  - "the pre-relaxed structure is a TS guess, not a minimum; it is never ground-state checked";
  - "the M1 YAML is provisional until the YAML/JSON graph format is defined (TJ Q-E3)";
  - "GraftSpec is self-contained; from v0.8.0 the graph loader builds it from
    TemplateGeometry.mapping, the single source (mission R11)";
  - "R-group/ligand enumeration and the Rh(I) (5+2) complexes are v1.x (TJ Q2 (b))".
- **A record-schema test** (default suite): the committed record parses, has `graft`, `xtb` and
  `uma`, every required key, and only allowed outcome values.
- **README:** "Features" and "Roadmap" v0.4.0 lines contain only what the record shows, e.g.
  "conserved-core mapper: quaternion alignment, ordered graft surgery with explicit charge/spin,
  core-frozen pre-relaxation; M1 regression pending TJ promotion".
  `tests/unit/test_identity.py` asserts each README claim against the record. The version stays
  0.3.0 (the bump is slice 08).

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

**Score: 9/10.** The record schema follows v0.3.0. The runtime numbers are whatever the run
measures.

## Mini-requirements

1. M1 regression and map-confirmation helpers, with unit tests:
   - a fake promoted fixture → `pass`;
   - a perturbed one (1e-9 Å coordinate shift, or a changed map entry) → `fail`;
   - absent → `pending_*`.
2. `tests/e2e/test_accept_v040.py` and the merge into `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json`.
3. The record-schema test.
4. README v0.4.0 claims and `test_identity.py` derivation tests.
5. The ledger: the driver path is added to `eta_rxncat_mapping`; validate ok.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read the v0.3.0 acceptance code.
- [ ] Task 2: helpers, driver, merge, schema test; required checks; commit C1 (code).
- [ ] Task 3: host check → xtb acceptance → host check → UMA acceptance, at C1, with scratch candidate and out dirs, under `timeout 3600` each; merge into the record.
- [ ] Task 4: README and derivation tests; commit C2 (record + README + tests); updater; remove scratch.

## 4. The Negative Space (Constraints)

- **DO NOT** set `ETA_RXNCAT_ACCEPTANCE=1` here, or treat `pending_*` as a failure in this slice.
- **DO NOT** write the repo's `tests/candidate_outputs/` or `tests/fixtures/`, or read them.
- **DO NOT** list a gated failure under `known_limits`; a failed gate fails the run (stop and report).
- **DO NOT** claim in the README anything the record does not show; **DO NOT** bump the version.

## Proof contract

- [ ] The two acceptance runs exit 0 with 0 skips (scratch dirs; commands and host checks in the proof).
- [ ] `git diff --stat Start..HEAD -- tests/candidate_outputs tests/fixtures` is empty.
- [ ] The record has `graft`, `xtb` and `uma`; the gates `pass`; regression `pending_promotion`; map `pending_confirmation`; the schema test passes.
- [ ] The README derivation tests pass; the required checks exit 0.

## Source material

- Mission SPEC §4 US-009, §5 R2, R11, R20(d), R23, R25, "Test tiers"; ADR-0027; `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`; `missions/release-0.3.0/slices/09-acceptance-record/SPEC.md` and `10-acceptance-verdict/SPEC.md` (format precedent, read-only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.6 (M1 fixture, E2E and candidates)
