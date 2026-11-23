---
id: OPR.0.4.0.8
slice: 08-acceptance-verdict
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "After TJ's Phase 3 promotion, rerun M1 on both recipes with ETA_RXNCAT_ACCEPTANCE=1 and zero skips, record the regression and map-confirmation verdicts, bump the version to 0.4.0 only on a pass verdict and derive the final README claims."
depends_on: [OPR.0.4.0.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.4.0/ACCEPTANCE_RESULT.json, docs/prd/PLAN_DISCREPANCIES.md, docs/prd/v0.4.0/DISCREPANCIES.md, README.md, tests/unit/test_identity.py, tests/unit/test_package.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 acceptance verdict after TJ's promotion, and the 0.4.0 bump

## Intent

After TJ's Phase 3 promotion, rerun M1 on both recipes with `ETA_RXNCAT_ACCEPTANCE=1` and zero
skips, and record the regression and map-confirmation verdicts. Bump the version to 0.4.0 only on
a `pass` verdict, and derive the final README claims.

Context the builder needs:
- **Precondition (stop if not met). TJ promoted all three files in commit `174a783` (mission R28):**
  - `tests/fixtures/v0.4.0/` holds exactly `m1_graft.json`, `m1_relaxed.xtb.json` and
    `m1_relaxed.uma.json`, with these sha256 (recompute them):
    - `m1_graft.json` `2e01ebf600eadabad47c9b66ffe368c756506fdcad3da3cd65df5bb5af117031`
    - `m1_relaxed.uma.json` `ff3eb5b5ba61ef538c5d9681af619b7ee6f746d47f71bea0de42b140f417ccab`
    - `m1_relaxed.xtb.json` `b3ed5680612ac0d8fb4157312ec257bfb1ac1d854d8b6889306958d9756adf73`
  - Their blob ids at `174a783` equal those of `tests/candidate_outputs/v0.4.0/` at `035e289`.
    Compare by `git ls-tree` ids only.
  - TJ's answer (relayed by the advisor, `qitem-20261123222552-7f2f3da801c4ec2c`) is quoted in
    mission R28. Copy R28's quote and these facts into `evidence.promotion` (R27 e).
  - Check by file names and git blob ids against the candidates commit; never by reading the
    candidates. A missing promoted file leaves its check `pending_promotion`, which fails under
    acceptance. That is a stop-and-report, never a skip.
- Pattern: v0.3.0 slice 10. Commits:
  - C1: any code fix this slice needs (often none; then C1 is Start).
  - The verdict run at C1 with `ETA_RXNCAT_ACCEPTANCE=1`, scratch candidate and out dirs, a
    fresh store.
  - C2: the record, the version bump and the README.

  Two commits are a stated exception, as v0.3.0 R56.
- **Version bump (mission R13), only with `verdict: pass`:** `pyproject.toml` `version = "0.4.0"`,
  `src/eta_rxncat/__init__.py` `__version__ = "0.4.0"`, `tests/unit/test_package.py` asserts
  `"0.4.0"`, and `uv lock` refreshes `uv.lock`'s own entry (`uv sync --locked` must then pass).
- The verdict is `pass` only with zero `fail`, `pending_*` or `missing` checks (R56). The map check
  reads `confirmed` when the promoted `m1_graft.json`'s map equals the YAML's.
- The README's final v0.4.0 lines are derived from the verdict record, and
  `tests/unit/test_identity.py` enforces them. CHANGELOG is the scribe's, not this slice's.
- **Replan 2 (mission R27), binding. Do these before the verdict run, in C1:**
  - **(a) The default suite gates the verdict.** Audit 07 found that `record_verdict` in
    `tests/e2e/acceptance_record_v040.py` reads only the fixture checks, so a failing default suite
    still gave `pass`. Change it to `record_verdict(fixtures, default_suite, commands)`.
    - It returns `fail` when any of these holds:
      - `default_suite.exit_code != 0`, or `default_suite.failed > 0`, or `default_suite.errors > 0`;
      - the same for `default_suite.cleanroom_vectors`;
      - any entry of `commands` has `exit_code != 0`.
    - Each failure adds a reason to `verdict_reasons`: `default_suite: exit_code 1, failed 2`,
      `default_suite.cleanroom_vectors: …`, `commands[<i>] <argv[0..2]>: exit_code <n>`.
    - `check()` recomputes the verdict with the same three inputs, so a hand-edited `pass` is
      refused. `merge_runs` passes them.
  - **(b) A record without `verdict` is refused.** `check()` already flags a bad verdict value.
    `check_v040_claims` in `tests/unit/test_identity.py` must also refuse every claim, with the
    message "has no verdict", when the key is absent. It must never raise `KeyError`; this is
    v0.3.0 slice 10 req 4.
  - **(c) Zero skips.** The acceptance runs must show `skipped == 0` in their logs.
    - The xtb command sets `ETA_RXNCAT_XTB=$HOME/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`.
      Without it the xtb test SKIPS (audit 06 gap).
    - `record_verdict` also fails when any `commands[*].summary` reports a skip. Read
      `commands[*].summary` as `merge_runs` stores it; if a summary has no skip count, derive one
      with `pytest_counts`.
  - **(d) Map confirmation is the promotion itself** (TJ "P2 A", mission R2).
    `map_confirmation` reads `graft_to_ts1b_n_map` from the promoted
    `tests/fixtures/v0.4.0/m1_graft.json` and compares it with the M1 YAML. It never reads a
    status field the candidate carried over (same rule as v0.3.0 R58).
  - **(e) Promotion evidence** (as v0.3.0 R57). The record's `evidence.promotion` holds:
    - TJ's verbatim answer and its queue row (both from the lead's dispatch);
    - the promotion commit;
    - per promoted file, its sha256 and git blob id, with the candidates-commit blob id it equals
      (compared by blob id, never by reading the candidate).

    The proof repeats it. The lead writes the matching mission R-row when the promotion lands.
  - **Tests (default suite, `tests/e2e/test_acceptance_record_v040.py` and `tests/unit/test_identity.py`):**
    - a record that is all-pass except `default_suite.failed = 1` gives `verdict: fail`, with the
      reason, and `check_v040_claims` then refuses (the v0.3.0 R56 family);
    - the same for a non-zero `cleanroom_vectors.exit_code`, a non-zero command exit code, and a
      reported skip;
    - a record without `verdict` is refused by `check()` and by `check_v040_claims` ("has no
      verdict");
    - a promoted `m1_graft.json` whose map differs from the YAML gives `map_confirmation: fail`.
- **Roadmap correction (mission R28; TJ "B: keep at v0.7.0"), in C1.** Group enumeration stays at
  v0.7.0; only the Rh(I) (5+2) complexes are v1.x. Correct three committed texts:
  - (1) the `KNOWN_LIMITS` line in `tests/e2e/acceptance_record_v040.py` becomes
    `"R-group/ligand enumeration stays at v0.7.0 (TJ roadmap B); the Rh(I) (5+2) complexes are v1.x (TJ Q2 (b))"`;
  - (2) PD-008's status cell in `docs/prd/PLAN_DISCREPANCIES.md` becomes
    `decided (TJ v0.4.0 Q2: "Q2. (b)", row qitem-20261123174816-79277143c4b9b81a: constrained-core pre-relaxation in v0.4.0; R-group/ligand enumeration not in v0.4.0 and kept at v0.7.0 (TJ roadmap "B: keep at v0.7.0", row qitem-20261123222552-7f2f3da801c4ec2c); the Rh(I) (5+2) complexes in v1.x)`
    (that cell only; no hash changes);
  - (3) DV-01's decision cell in `docs/prd/v0.4.0/DISCREPANCIES.md` becomes
    `TJ Q2 "(b)": pre-relaxation in v0.4.0; enumeration out of v0.4.0, kept at v0.7.0 (TJ roadmap B); Rh(I) (5+2) in v1.x.`
- **What the promotion must contain:** exactly the three Phase 3 candidates, promoted to
  `tests/fixtures/v0.4.0/m1_graft.json`, `m1_relaxed.xtb.json` and `m1_relaxed.uma.json`.
  Nothing else is expected: no reference-values file and no SMILES file. A `pass` needs all
  three. If TJ promotes fewer, a regression check stays `pending_promotion`, which fails under
  acceptance. That is a stop-and-report to the lead (a TJ or replan question), never a skip.
- **The README after a pass:** replace the slice 07 "pending TJ promotion" claims with claims
  derived from the verdict record. `check_v040_claims` gets the matching predicates
  (verdict `pass`, regressions `pass`, map `confirmed`). `test_readme_v040_claims_match_record`
  then asserts `project_version() == "0.4.0"`.

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

**Score: 9/10.** Everything is mechanical once TJ has promoted. The open input is which relaxed
candidates TJ promotes; the dispatch states it.

## Mini-requirements

0. Replan 2 (R27) items (a)–(e) and their tests, committed in C1, before any verdict run.
1. The verdict run on both recipes, zero skips, under `ETA_RXNCAT_ACCEPTANCE=1` (each under
   `timeout 3600`, after a host check).
2. `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json` is rewritten with the real outcomes and `verdict: pass`.
   If anything fails, stop and report: no bump, no README claim.
3. Version 0.4.0 in the four places; `uv sync --locked` ok.
4. README final claims and the derivation tests.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; verify the precondition by names and blob ids.
- [ ] Task 1b: R27 (a)–(e) code and tests; required checks; commit C1 (clean tree).
- [ ] Task 2: host check → the xtb verdict run → host check → the UMA verdict run.
- [ ] Task 3: record; version bump; `uv lock`; README; tests; required checks; commit C2; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** write or edit `tests/fixtures/` (TJ's), or read `tests/candidate_outputs/`.
- **DO NOT** bump the version or write claims on a non-`pass` verdict.
- **DO NOT** loosen a regression bound (TJ Q6 "A") or relabel a failure as a known limit.
- **DO NOT** tag, push or edit the CHANGELOG.
- **DO NOT** derive the verdict from the fixture checks alone; **DO NOT** run the xtb acceptance without `ETA_RXNCAT_XTB`.

## Proof contract

- [ ] Both verdict runs exit 0 with 0 skips under `ETA_RXNCAT_ACCEPTANCE=1` (commands, host checks, wall times).
- [ ] The record's `verdict` is `pass`; regression `pass`; map `confirmed`; the gates `pass`; `default_suite` exit 0 with 0 failed and 0 errors (clean-room vectors too); every command exit 0 with 0 skipped.
- [ ] The R27 tests pass: a failing default suite, vector run, command or skip each give `verdict: fail`, and the README claims are refused; a record without `verdict` is refused.
- [ ] `evidence.promotion` lists TJ's verbatim answer, the promotion commit and each promoted file's sha256 and blob id.
- [ ] `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` prints `0.4.0`; `uv sync --locked` exits 0.
- [ ] `git diff --stat Start..HEAD -- tests/fixtures tests/candidate_outputs` is empty; the required checks exit 0.

## Source material

- Mission SPEC §4 US-009, §5 R2, R13, R25, R27, "Test tiers"; audit 07 handback `qitem-20261123214503-e4782517`; ADR-0027; `missions/release-0.3.0/slices/10-acceptance-verdict/SPEC.md` (precedent, read-only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.7 (record, helpers) and TJ's Phase 3 promotion (named by the lead at dispatch)
