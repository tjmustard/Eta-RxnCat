---
id: OPR.0.7.1.9
slice: 09-verdict
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Set version 0.7.1 under a point-release identity rule, write the CHANGELOG entry, and generate QUALITY_RESULT.json from the real suite runs and committed seam-break files, gating on real outcomes."
depends_on: [OPR.0.7.1.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, README.md, CHANGELOG.md, tests/unit/test_identity.py, tools/quality_record_v071.py, "tests/unit/tools/test_quality_record*.py", docs/prd/v0.7.1/QUALITY_RESULT.json, docs/prd/v0.7.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Verdict, version 0.7.1, point-release identity, CHANGELOG and QUALITY_RESULT.json

## Intent

Set version 0.7.1 everywhere under a point-release identity rule, write the CHANGELOG entry, and
generate `docs/prd/v0.7.1/QUALITY_RESULT.json` from the real suite runs and the committed seam-break
files, gating on real outcomes. It also brings the README to TJ's 11-27 standard at 0.7.1 and
closes v0.7.0's DV-10 row on TJ's choice (mission R19, R20, R23, R25, R30, R46, R47; US-009).

Context the builder needs:
- **R23 (scaffold test):** `tests/unit/test_identity.py`.
  - `PLAN_VERSIONS` (:257) and `check_version_identity` (:291) get the point-release rule: a version
    `X.Y.Z` with `Z > 0` takes `X.Y.0`'s roadmap position. Built lists up to `X.Y.0`, and Planned
    lists the rest.
  - The README badge must read `release-v0.7.1` (:300-302).
  - Add a positive case (0.7.1) and a negative case (0.7.1 with 0.8.0 under Built).
  - With R47: at 0.7.1 the Roadmap's `### Built` also lists `**v0.7.1**` after `**v0.7.0**`. Since
    0.7.1 is not in `PLAN_VERSIONS`, the rule must not count that line as a later plan version, and
    `listing_problems` (Features subsections = Built, pitch = Built minus v0.1.0) must pass on the
    real README. The positive synthetic case includes that Built line.
- **Version 0.7.1** goes in:
  - `pyproject.toml`;
  - `src/eta_rxncat/__init__.py`;
  - the README badge `release-v0.7.1`, and the README shape of R47 (below);
  - `uv.lock`, via `uv lock` in the main checkout only.
- **README standard (R47; TJ's docs-only pushes on main, `7b65537` and `8753164`, merged at
  `030322a`).** The tests are `pitch_problems`, `check_version_identity` (R50) and
  `listing_problems` in `tests/unit/test_identity.py`. Read them before writing.
  - The pitch is the centred bold intro plus one bullet per released version. Add a v0.7.1 bullet,
    last, ending `(v0.7.1).`, and change the previous last bullet's ending to `(v0.7.0);` if the
    list's punctuation needs it.
  - `## ✨ Features` has no version in its title. Add one `### … (v0.7.1)` subsection, last, after
    `### Library enumeration, template fallback and review (v0.7.0)`. Its claims are cited per R19.
  - Roadmap: add `- **v0.7.1**: …` under `### Built` after v0.7.0, and drop the `**v0.7.1** (in
    progress)` line from `### Planned, not yet built`.
  - Keep `readme_sections`, the TOC and the header tests green.
  - If a point release cannot be a pitch bullet or a Features subsection under the R50/R23 checks,
    stop. Ask TJ through `advisor-lead@kernel`, tagged `question-for-tj`, with options A/B/C and a
    recommendation. Do not loosen the checks to fit.
- **DV-10 (R46; TJ "Close it (Recommended)", advisor relay
  `qitem-20261127204642-06c18509e72ce4bb`):** in `docs/prd/v0.7.0/DISCREPANCIES.md`, change only
  row DV-10's last cell from `open` to `done (v0.7.0 slice 14 set version 0.7.0; closed on TJ's
  choice, relay qitem-20261127204642-06c18509e72ce4bb)`. Touch no other row or file under
  `docs/prd/v0.7.0/`.
- **CHANGELOG `## [0.7.1] - <date>`** has four parts:
  - **Added:** the integration suite (Tier O and Tier X), `SampleKeys` / `TSEnsembleRun.samples`,
    `tools/engine_reachable.py` and `tools/quality_record_v071.py`.
  - **Fixed:** R10, R11, R13/R29, R14, R28, R38, R39 and R40.
  - **Removed:** the R17 removals.
  - **Known issues:**
    - R15 kept;
    - the deferred carry-forwards, each with its reason (multi-site forming bonds; `+` in entry ids;
      `run_selectivity` priority 1 against the plan's priority-2 TS nodes, R35; the geomeTRIC
      temp-dir and partial-mark edge cases, R41; HF-13 still carried);
    - R14's import-order limit.
  - Remove the 0.7.0 `ratio = inf` known issue from the new entry only. Do not edit older entries.
  - Under **Fixed** or a docs line: ADR-0053's reader claim is narrowed by the PROPOSED node slice
    08 registered (R45; name its id), pending TJ's approval.
- **Verdict runs:**
  1. The default suite: `uv run pytest --junitxml=~/.hacf/eta-rxncat-hacf/evidence/v071-verdict/default.xml`.
  2. Tier X: run the blocking host check as a separate call, then the mission R2 command with
     `--junitxml=~/.hacf/eta-rxncat-hacf/evidence/v071-verdict/integration_x.xml`, under
     `timeout 600` and `/usr/bin/time -v`.
- **R20/R30 record:** `tools/quality_record_v071.py` (scaffold, stdlib only) writes the JSON.
  - It reads the two junit files and `missions/release-0.7.1/slices/{02-tier-o-seams,
    04-tier-x-ts-seams,05-tier-x-selectivity-review}/seam_breaks.json`.
  - It exits non-zero if any expected test id, file or list is missing or empty.
  - **Keys:** `version`, `base_sha` (the full sha of `bf7b949`), `verdict_run_sha` (HEAD at the
    verdict run), `suites.{default,integration_x}.{passed,failed,skipped,deselected,errors,wall_s}`,
    `integration_tests[]`, `known_issues[]` and `dead_code.{removed,kept}`.
  - **Gates:**
    - the default suite has 0 failed and 0 errors, and every T-O id plus the parity test is `passed`
      by id, with 0 skipped among `integration` ids;
    - Tier X has 0 failed, 0 errors and 0 skipped;
    - every seam break has `failed: true`;
    - every known-issue test is present and passing.
  - Commit the record from this run. Rerun the script after the commit to confirm it reproduces
    bytes-equal against the same evidence.
- **R19:** fill each README/CHANGELOG claim's `QUALITY_RESULT.json` key.
- **Ledger:** scaffold 1998 (1978 at compile; slice 01's audit added 20) and cli 1550. Compress
  scaffold first if it needs a word.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/`.
  - The ruff format oracle is only
    `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`.
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.7.0/`, older
    missions or `PRDs/`. Plain literal `rm -f` only, and never `rm -rf` on a computed path.
  - Ledger caps (mission §5 carry-forward 7): any description word in a node at or above 1978 chars
    is compressed for first, with the before and after counts in the proof. Core gets no words.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.
- **Licence:** no new Python or JS dependency; the core stays MIT/BSD.

## 1. The Confidence Mandate

**Score: 9/10.** RT-03's failure mode was re-read at `bf7b949` and has an explicit rule. The record's
inputs are named and fail closed. Residual: the R23 rule's exact roadmap parsing, which is pinned by
the positive and negative cases.

## Mini-requirements

1. `test_identity` is green at 0.7.1, and its R23 cases pass.
2. 0.7.1 appears in every R20 place, including the badge and `uv.lock`.
3. The CHANGELOG `[0.7.1]` entry is complete, with each claim cited.
4. `QUALITY_RESULT.json` is generated from the named sources, every gate passes, and the script
   fails on a missing source (shown by a unit test or by a run against a missing file in scratch).
5. The default suite and Tier X are green, with the host check in the proof.
6. R47: `pitch_problems`, `check_version_identity` and `listing_problems` pass on the real README
   at 0.7.1, with the v0.7.1 pitch bullet, Features subsection and Built line present.
7. R46: DV-10 reads done with its citation, and `git diff --stat docs/prd/v0.7.0` shows only
   `DISCREPANCIES.md`, one line.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] R23 rule and cases; version bump; `uv lock`.
- [x] README to the R47 standard; DV-10 (R46).
- [x] CHANGELOG.
- [x] Record script and its fail-closed test.
- [x] Verdict runs (host check before Tier X); generate the record.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** hand-edit `QUALITY_RESULT.json`.
- **DO NOT** push, tag or promote; the lead pushes on the verdict.
- **DO NOT** edit `PRDs/` or any CHANGELOG entry older than 0.7.1.

## Proof contract

- [ ] `uv run pytest tests/unit/test_identity.py -q` passes (requirement 1).
- [ ] `git grep -n "0\.7\.1"` over the version files (requirement 2).
- [ ] The README pitch bullet, Features subsection and Built line, with `test_identity` green
  (requirement 6); the DV-10 diff (requirement 7).
- [ ] Both junit files, the host check, the script's exit 0, and its exit ≠ 0 on a missing source
  (requirements 4-5).
- [ ] The required checks exit 0 (requirement 3).

## Source material

- Mission R19, R20, R23, R25, R30, R46 and R47; Red Team RT-03 and RT-11.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.8.
