---
id: OPR.0.7.1.6
slice: 06-known-issues-tooling
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Fix the tooling and test-text known issues (t3 gated_on text, test-policy skip blind spots, bare-BSD licence label, offline wheel test, host-data scan false positive), each with a test that fails at the base."
depends_on: [OPR.0.7.1.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [tests/e2e/t3.py, "tests/e2e/test_t3_*.py", tests/conftest.py, tests/unit/test_test_policy.py, tools/licence_gate.py, pyproject.toml, tests/unit/tools/test_licence_gate.py, docs/licence-inventory.md, tests/unit/review/test_assets.py, tests/unit/review/test_bundle_scans.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_test_policy.py, tests/unit/tools/test_licence_gate.py, tests/unit/review]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Known issues in tooling and test text (R10, R11, R28, R39, R40)

## Intent

Fix the verified tooling and test-text known issues: t3's xtb `gated_on` text, the test-policy
skip blind spots, the bare-BSD licence label, the online-only wheel test and the host-data scan's
false positive. Each fix comes with a test that fails at `bf7b949` (mission R10, R11, R28, R39,
R40; US-007).

Context the builder needs:
- **R10 (species_runner):** `tests/e2e/t3.py:291` writes `"convergence, mode count"` for xtb. Make
  t3 emit exactly the per-case text of `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json`:
  `"convergence, mode count, identity core (forming overlap, in phase, KE)"` for n4, ts1a_n, ts1b_n
  and ts3a, and `"none (report-only, R32)"` for ts4a. Add an offline test (in `tests/e2e/`) that,
  for each v0.5.0 case, compares the text t3 would write with the record's. Text only.
- **R11 (scaffold):**
  - (a) `module_level_skips` (`tests/unit/test_test_policy.py:213`): collect `import pytest as X`
    aliases; visit `decorator_list`, `args.defaults` / `kw_defaults` and class `bases` / `keywords`,
    while still skipping function bodies. Add parametrised cases for each.
  - (b) `tests/conftest.py:80`: add `"teardown"` to `when in (...)`. A pytester test shows that a
    teardown skip fails under `ETA_RXNCAT_ACCEPTANCE=1` and stays a skip without it.
- **R28 (scaffold; TJ Q1 B, Q-RT1 A):**
  - In `pyproject.toml`, map `[tool.eta-rxncat.licence-gate.classifiers]` `"BSD License"` (:113)
    and `[…names]` `"BSD"` and `"BSD License"` (:126-127) to `LicenseRef-BSD-classifier`, and add
    that id to `allowed`. `"3-Clause BSD License"` (:128) stays BSD-3-Clause.
  - Add a new table `[tool.eta-rxncat.licence-gate.labels]` holding
    `"LicenseRef-BSD-classifier" = "BSD (variant not stated)"`.
  - In `tools/licence_gate.py:375`, the row's licence column prints
    `<raw> [BSD (variant not stated)]` when the resolved id has a label.
  - Tests in `tests/unit/tools/test_licence_gate.py`: the classifier path, both names paths, the
    exact row text, and a `License-Expression: BSD-3-Clause` package that stays BSD-3-Clause
    unlabelled.
  - **Proof:** run each profile (`base`, `gpu`, `mlip-mace`, `mlip-uma`; the existing gate commands
    with `uv run --no-sync` in the named envs) before and after. The PASS/FAIL sets must be equal,
    and `antlr4-python3-runtime` passes in `mlip-uma`.
  - Update `docs/licence-inventory.md` if it names the mapping.
- **R39 (review, tests only):** `tests/unit/review/test_assets.py:59` builds with `uv build --wheel`
  (:66). Add `--offline`.
  - Measure first: `UV_OFFLINE=1 uv build --wheel --offline --out-dir <scratch>` on this host. If no
    cached build backend is available, stop and report.
  - The no-`uv` skip (:61-63) stays, so it fails under `=1` (ADR-0019).
- **R40 (review, tests only):** `tests/unit/review/test_bundle_scans.py:63` matches the user and host
  names as substrings (:78).
  - Exclude only the files that are byte-pinned by the bundle's vendored-asset sha256, and name the
    pin source in the test.
  - New cases: the user name planted in a non-vendored file fails, and the pinned 3Dmol file is not
    scanned.
  - `tests/unit/review/test_export.py:63-64` stays unchanged.
- **Ledger:** scaffold 1978 and review 1983. No description words are expected. If the auditor needs
  one, compress first.
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

**Score: 9/10.** Every line cited here was re-read at `bf7b949`, and R28's affected packages were
measured on 2026-11-26. Residual: the wheel backend's presence in uv's cache. It is measured first,
and its absence is a stop-and-report.

## Mini-requirements

1. R10: the t3 text equals the v0.5.0 record per case. The test fails on the old line.
2. R11: each new AST case and the teardown pytester case fail on `bf7b949`'s code and pass after.
3. R28: the label mechanism and its tests work, and the profile PASS/FAIL sets are equal before and
   after.
4. R39: the wheel test builds with `--offline`, with the measurement recorded.
5. R40: the scan skips only pinned vendored files, and its cases pass.
6. The default suite is green.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] R10 and its test.
- [ ] R11 (a) and (b) and their tests.
- [ ] R28: config, label, tests, then the before and after profile runs.
- [ ] R39 measurement, then the fix.
- [ ] R40.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change any gate verdict (R28 is a label, not a policy change).
- **DO NOT** edit `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json` or any committed record.
- **DO NOT** touch `src/`.

## Proof contract

- [ ] For each of R10, R11, R39 and R40: the new test id, its failing output at `bf7b949` (from a
  worktree run with R22's interpreter), and passed after (requirements 1, 2, 4, 5).
- [ ] The R28 profile verdict sets before and after, which must be equal (requirement 3).
- [ ] The required checks exit 0 (requirement 6).

## Source material

- Mission R10, R11, R28, R39 and R40; TJ Q1 B and Q-RT1 A.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.5.
