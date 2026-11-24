---
id: OPR.0.5.0.12
slice: 12-acceptance-record
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Assemble the v0.5.0 acceptance record from real per-check outcomes with pending states, measure run-to-run reproducibility to propose the regression bounds TJ sets at Phase 3, and derive the README claims."
depends_on: [OPR.0.5.0.11]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.5.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 acceptance record (pre-promotion), measured regression bounds, README derivation

## Intent

Assemble `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json` from real per-check outcomes of every v0.5.0
check (pending states for what waits on TJ), measure run-to-run reproducibility so TJ can set the
regression bounds at Phase 3, and derive the README v0.5.0 claims from the record. This slice's
PASS does not depend on TJ acting first.

Context the builder needs:
- **Pattern:** v0.4.0 slice 07 and v0.3.0 slices 09/10. Read `tests/e2e/acceptance.py`,
  `acceptance_record_v040.py`, `test_accept_v040.py`, `test_acceptance_record_v040.py`,
  `regression.py`, `test_gated_outcome.py`, `docs/prd/v0.4.0/ACCEPTANCE_RESULT.json`, and
  `missions/release-0.4.0/slices/07-acceptance-record/SPEC.md` (read-only precedent).
  Reuse `gated_outcome` (R56): `pending_*` fails under `ETA_RXNCAT_ACCEPTANCE=1`; a missing
  fragment is `missing`.
- **Driver:** `tests/e2e/test_accept_v050.py` (markers `e2e`, `acceptance`, plus `xtb` or
  `mlip_uma` per recipe), `tests/e2e/acceptance_record_v050.py` (record assembly + `check()` +
  `record_verdict(fixtures, default_suite, commands)` per v0.4.0 R27: `fail` on a default suite
  with a non-zero exit, failures or errors, or on any command with a non-zero exit or a skip).
- **Checks in the record** (state ∈ `pass` / `fail` / `pending_promotion` /
  `pending_confirmation` / `skipped` with reason / `missing`):
  - per case × recipe (ten): the slice 08–10 gates (both recipes: converged, mode count; UMA: KE,
    identity, window; UMA ordering TS4a < TS3a; GFN2: the identity core of mission R32, overlap
    ≥ 0.50, in phase, KE ≥ 0.60, from the validation fields, window reported), the second-run cache
    hits (stages that ran, G6/R32), conservation. GFN2 TS1a_n/TS1b_n (slice 08, which did not gate
    identity) get the GFN2 identity core here from their committed candidates;
  - **GFN2 TS4a is report-only** (TJ Q-TJ4 A, R32): its block is copied with `report_only: true`,
    `reported_outcome`, `failed_reason` and `failed_checks` as measured, and none of it is a gated
    check; a test asserts that a report-only `failed` entry leaves the record's gated checks
    unaffected, and that the same failure on any other pair fails;
  - the reported blocks (GFN2 extras, connectivity, G5 RMSDs) copied, never gated;
  - transcriptions: the six sha256s (HF-1) and the R9 energy differences (slice 07 proof values);
  - the cross-check fragment (slice 11): every record present (gate: attempted and recorded);
  - `regression`: `pending_promotion` (the candidates are not yet TJ's fixtures);
  - `transcription_confirmation`: `pending_confirmation` (TJ A3: TJ confirms at Phase 3);
  - `default_suite`, `commands` (each with exit code and skip count), `environment`.
- **Reproducibility measurement** (for the Phase 3 bounds; numeric bounds are TJ's, v0.3.0 R1
  "R1. A"): run each case × recipe twice more in **fresh** stores (host check; GPU one at a time;
  `timeout 3600`), and record per case × recipe the max \|ΔE_TS\| (Eh), \|ΔΔG‡\| (kcal/mol) and
  heavy-atom RMSD (Å, Horn) between the runs and against the C2 candidate's values (computed
  inside the test from the in-process result of slice 08–10 code, never by reading candidate
  files). Record them under `reproducibility` and a `proposed_regression_bounds` block: TJ's v0.4.0
  Q6 numbers (\|ΔE\| ≤ 1e-5 Eh, heavy RMSD ≤ 0.01 Å) and \|ΔΔG‡\| ≤ 0.01 kcal/mol, **only** if
  every measured difference is ≤ 1/10 of the bound; otherwise propose 10× the measured maximum
  and say so. The lead puts this block in TJ's Phase 3 row.
- **README:** "Features" and "Roadmap" lines for v0.5.0 derived from the record by the existing
  derivation helper pattern (a claim needs its check `pass`; pending checks give "pending TJ"
  wording). CHANGELOG is the scribe's.

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

**Score: 9/10.** The pattern exists twice; the only new part is the reproducibility block, whose
rule is fixed.

## Mini-requirements

1. `ACCEPTANCE_RESULT.json` with every check above and real states; `verdict` absent (slice 13 sets it).
2. The R27-style `record_verdict` and `check()` with tests: a failing suite, command, skip or any
   `fail`/`pending_*`/`missing` check each give `fail`; a stated `pass` that disagrees is refused.
3. `reproducibility` and `proposed_regression_bounds` blocks per the rule.
4. README v0.5.0 claims derived from the record, with derivation tests (a missing or `pending`
   check refuses the claim).
5. Acceptance runs on both recipes under `ETA_RXNCAT_ACCEPTANCE=1` with 0 skips except the states
   that are legitimately `pending_*`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read the precedent files.
- [ ] Task 2: record module, driver, verdict function, tests; required checks; C1.
- [ ] Task 3: host check → xtb acceptance → host check → UMA acceptance; reproducibility runs.
- [ ] Task 4: write the record and README; required checks; C2; updater (node
  `eta_rxncat_species_runner`; `docs/**` stays the scaffold's).

## 4. The Negative Space (Constraints)

- **DO NOT** read `tests/candidate_outputs/` by any route; **DO NOT** write `tests/fixtures/`.
- **DO NOT** set `verdict` or bump the version here.
- **DO NOT** turn a reported value into a gate, or a failure into a known limit; the only
  report-only pair is GFN2 TS4a, by TJ's Q-TJ4 A (R32).

## Proof contract

- [ ] Both acceptance commands with host checks, `timeout`, exit codes and skip counts.
- [ ] The record lists every check with its state; `regression` and `transcription_confirmation` are pending.
- [ ] `reproducibility` and `proposed_regression_bounds` are present with the rule applied.
- [ ] The verdict-function tests pass.
- [ ] The required checks exit 0.

## Source material

- Mission US-015, R4, R5, R9, R26; v0.4.0 slice 07 and R27; v0.3.0 slices 09/10.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.11 (build order; its code and contracts are used here)
