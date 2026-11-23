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
hacf_touches: ["tests/e2e/**", docs/prd/v0.4.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, tests/unit/test_package.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, spec/compiled/architecture.yml]
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
- **Precondition (stop if not met):** the lead's dispatch names TJ's promotion commit.
  - `tests/fixtures/v0.4.0/` holds `m1_graft.json`, and the relaxed files TJ chose to promote.
  - The lead's dispatch records TJ's verbatim answer.
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
- **OpenRig 0.7.21.** `hyper_spec.py` and `hyper_migrate.py` warn "outside the pinned contract",
  `hyper_spec.py proof` writes the proof natively, and `verify` skips `rig scope audit`. All of
  this is expected: note it in the proof, not as a finding.
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

1. The verdict run on both recipes, zero skips, under `ETA_RXNCAT_ACCEPTANCE=1` (each under
   `timeout 3600`, after a host check).
2. `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json` is rewritten with the real outcomes and `verdict: pass`.
   If anything fails, stop and report: no bump, no README claim.
3. Version 0.4.0 in the four places; `uv sync --locked` ok.
4. README final claims and the derivation tests.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; verify the precondition by names and blob ids.
- [ ] Task 2: host check → the xtb verdict run → host check → the UMA verdict run.
- [ ] Task 3: record; version bump; `uv lock`; README; tests; required checks; commit C2; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** write or edit `tests/fixtures/` (TJ's), or read `tests/candidate_outputs/`.
- **DO NOT** bump the version or write claims on a non-`pass` verdict.
- **DO NOT** loosen a regression bound (TJ Q6 "A") or relabel a failure as a known limit.
- **DO NOT** tag, push or edit the CHANGELOG.

## Proof contract

- [ ] Both verdict runs exit 0 with 0 skips under `ETA_RXNCAT_ACCEPTANCE=1` (commands, host checks, wall times).
- [ ] The record's `verdict` is `pass`; regression `pass`; map `confirmed`; the gates `pass`.
- [ ] `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` prints `0.4.0`; `uv sync --locked` exits 0.
- [ ] `git diff --stat Start..HEAD -- tests/fixtures tests/candidate_outputs` is empty; the required checks exit 0.

## Source material

- Mission SPEC §4 US-009, §5 R2, R13, R25, "Test tiers"; ADR-0027; `missions/release-0.3.0/slices/10-acceptance-verdict/SPEC.md` (precedent, read-only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.7 (record, helpers) and TJ's Phase 3 promotion (named by the lead at dispatch)
