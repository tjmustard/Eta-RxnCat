---
id: OPR.0.5.0.13
slice: 13-acceptance-verdict
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "After TJ's Phase 3 promotion and regression bounds, run the verdict on both recipes against the promoted fixtures and bump the version to 0.5.0 only on pass."
depends_on: [OPR.0.5.0.12]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.5.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, tests/unit/test_package.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 acceptance verdict and the 0.5.0 bump (after TJ's Phase 3)

## Intent

After TJ promotes the v0.5.0 candidates and sets the regression bounds at Phase 3, run the verdict
on both recipes against the promoted fixtures, write `verdict` into the acceptance record, and
bump the version to 0.5.0 only on `pass`.

Context the builder needs:
- **Precondition (stop if not met):** TJ's Phase 3 answer is recorded by the lead as an R-row in
  the mission SPEC (the promotion commit, the promoted files with sha256 and blob id, TJ's
  verbatim answer, the regression bounds TJ set, and his confirmation of the six transcriptions).
  Only TJ writes `tests/fixtures/v0.5.0/`. Verify the precondition by file names and blob ids;
  never read `tests/candidate_outputs/`.
- **Pattern:** v0.4.0 slice 08 (`missions/release-0.4.0/slices/08-acceptance-verdict/SPEC.md`,
  read-only), including its R27 rules: the verdict is `fail` on a default suite with a non-zero
  exit, failures or errors, or on any command with a non-zero exit or a skip; `check()`
  recomputes it; a record without `verdict` refuses every README claim; the xtb run sets
  `ETA_RXNCAT_XTB`; `evidence.promotion` records TJ's verbatim answer, the promotion commit and
  each promoted file's sha256 and blob id.
- **Regression:** each case × recipe's verdict result against its promoted fixture with TJ's
  bounds (energy, ΔG‡, heavy-atom RMSD; `history` excluded, N11). The cache-hit, gate and
  cross-check checks re-run as in slice 12. `transcription_confirmation` becomes `confirmed` only
  from TJ's recorded answer.
- **Bump** (only on `pass`): `pyproject.toml`, `src/eta_rxncat/__init__.py`,
  `tests/unit/test_package.py`, `uv.lock` to 0.5.0. The P-RFO identity is the source hash of
  `prfo.py`, not the package version, so the bump changes no store key (R11).
- README final v0.5.0 claims from the record.

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  geomeTRIC may run only as a black box through `geometric-optimize` and its `--help` text.
- **Clean room, nMAP (v0.4.0 Q1).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach". Never open, clone, fetch or search Eta_Scripts or nMAP (GitHub,
  `~/PROJECTS/cleanroom-nmap`, a cache, a web or code search); only its `TRANSFER_LOG.md` may be
  read. Never message the clean-room seats.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.5.0`, cut re-entrantly from Base (the
  mission commit on main, parent `0d2a8d3`). One code commit per slice unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff. Every commit ends with exactly
  two footer lines, `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, `<version>` read from
  `.agents/hacf-manifest.json` at commit time; no co-author or session trailer. Author "Thomas J.
  L. Mustard Ph.D." (repo-local git config). Never `--no-verify`, never rewrite history.
- **Code graph first.** The first command is `python3 .agents/scripts/hyper_codegraph.py index`;
  it must print `index: ok` (the red team saw `stale_index`). Anything else stops the slice. The
  graph only widens a blast radius.
- **Ledger.** Only through `hyper_ledger.py` / `hypergraph_updater.py`, never by hand. On an
  existing node, `ensure-node --id <node>` takes the **full** `--files` list (it replaces); count
  the node's globs before and after. No slice creates a node.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF v0.6.3.** No `HACF-install.sh` (never without `--ref`), no `HACF-uninstall.sh`, no
  `hyper_migrate.py apply`. On OpenRig 0.7.21, `hyper_spec.py`/`hyper_migrate.py` warn "outside
  the pinned contract", `hyper_spec.py proof` writes the proof natively and `hyper_migrate.py
  verify` skips `rig scope audit`: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git:
  every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host (shared with the hacf and cleanroom rigs).** Before any E2E, GPU, engine or full-suite
  run: `free -g` and `ps` for other rigs' heavy python/pytest/engine processes; if one is active,
  wait (poll at most every 5 minutes with Monitor or a background wait, never a foreground sleep)
  for GPU/E2E work; the full CPU unit suite may run serially beside another rig's small batches
  only with ≥ 6 G available. Record the check in the proof. GPU/E2E runs one at a time. Never kill
  another rig's process. The check and the heavy command are separate calls (or the check exits
  non-zero), never echo-then-run.
- **Engines.** Every xtb command sets
  `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (without it the
  xtb E2E skips with exit 0). UMA runs in `.venv-accept-uma` on CUDA. Every E2E command runs
  under coreutils `timeout 3600`; an expiry is stop-and-report with the output.
- **Lessons (mission R26):** unit-suffixed numeric keys (R54); no energy- or record-ordered list
  in a compared output (R55); one `gated_outcome` per test, `pending_*` fails under
  `ETA_RXNCAT_ACCEPTANCE=1` (R56); any reader of a store or runner payload checks `failed_reason`
  first (R50); re-dedup after any geometry change (v0.3.0 path unchanged); tolerances are measured
  before they are written, never guessed; the candidate rule (code commit C1 with a clean tree,
  E2E at C1, then a commit of only `tests/candidate_outputs/v0.5.0/*` as C2).
- **Required checks** (AGENTS.md), all exit 0 before each commit: `uv sync --locked`;
  `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv run pytest`;
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception (N1).
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it; never loosen a tolerance
  (TJ's or this SPEC's). Never use `AskUserQuestion`.
- **Never** push, tag or open a PR.

## 1. The Confidence Mandate

**Score: 9/10.** The pattern is v0.4.0's; the bounds come from TJ at Phase 3 (the slice cannot
start without them).

## Mini-requirements

1. The verdict runs on both recipes, zero skips, under `ETA_RXNCAT_ACCEPTANCE=1`, each under
   `timeout 3600` after a host check.
2. `ACCEPTANCE_RESULT.json` rewritten with real outcomes and `verdict: pass`; on anything else,
   stop and report: no bump, no README claim.
3. Version 0.5.0 in the four places; `uv sync --locked` ok.
4. README final claims and their derivation tests.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; verify the precondition.
- [ ] Task 2: regression wiring with TJ's bounds; tests; required checks; C1.
- [ ] Task 3: host check → xtb verdict → host check → UMA verdict.
- [ ] Task 4: record; bump; `uv lock`; README; tests; required checks; C2; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** write or edit `tests/fixtures/`, or read `tests/candidate_outputs/`.
- **DO NOT** bump or claim on a non-`pass` verdict; **DO NOT** loosen TJ's bounds.
- **DO NOT** tag, push or edit the CHANGELOG.

## Proof contract

- [ ] Both verdict runs exit 0 with 0 skips (commands, host checks, wall times).
- [ ] The record's `verdict` is `pass`; regression `pass`; transcriptions `confirmed`; every command exit 0 with 0 skipped.
- [ ] `evidence.promotion` complete.
- [ ] `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` prints `0.5.0`.
- [ ] `git diff --stat Start..HEAD -- tests/fixtures tests/candidate_outputs` is empty; the required checks exit 0.

## Source material

- Mission US-015, R11, R20, R26; v0.4.0 slice 08 and R27/R28.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.12 (build order; its code and contracts are used here)
- TJ's Phase 3 promotion and regression bounds, recorded by the lead as a mission R-row
