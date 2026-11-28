---
slice: OPR.0.7.1.9
candidate_sha: "2e52588"
artifact_type: guard
verdict: CLEAR
money_evidence: full pytest 2940 passed; Tier X 6 passed 0 skipped; record
  generated at acb7e7c, rerun bytes-equal, exit 1 on a missing source
---

# Execute evidence: 09-verdict (OPR.0.7.1.09) - builder (not a QA verdict)

The artifact type is `guard` only because the proof writer has no `execute` type; the audit writes
the QA verdict.

Start `2fcc8be`. C1 `acb7e7c` (version, R23 rule, README, DV-10, CHANGELOG, record script and
tests). C2 `11426e0` (`QUALITY_RESULT.json`). C3 `2e52588` (ledger flags, lore stale marks,
progress, task boxes, field notes). Then this proof. No push, no tag. `E` =
`~/.hacf/eta-rxncat-hacf/evidence/v071-verdict`.

## Verdict runs (at `acb7e7c`, `E/verdict_run_sha`)

The working tree then held only this slice's uncommitted progress files (SPEC status and
PROGRESS.md rows) and the two untracked `.claude` backups; no code differed from `acb7e7c`.

| run | command | exit | seen |
|---|---|---|---|
| default | `TMPDIR=... ETA_RXNCAT_XTB=... /usr/bin/time -v timeout 3600 uv run pytest --junitxml=E/default.xml > E/default.log` | 0 | 2940 passed, 202 deselected, 2 warnings, 428.12 s, max RSS 359676 kB |
| host check (own call) | `bash ~/.hacf/eta-rxncat-hacf/evidence/v071-05-audit/hostcheck-floor4.sh E/integration_x.hostcheck` | 0 | avail 13G, gpu 0%, gpu_apps 0, heavy 0, eta 0, HOST FREE |
| Tier X | scratch cwd; `ETA_RXNCAT_ACCEPTANCE=1`, `ETA_RXNCAT_XTB`, three thread pins 1; `/usr/bin/time -v timeout 600 .venv/bin/python -m pytest -c pyproject.toml --rootdir . -m "integration and xtb" tests/integration --junitxml=E/integration_x.xml -p no:cacheprovider > E/integration_x.log` (absolute paths) | 0 | 6 passed, 100 deselected, 114.52 s, max RSS 162636 kB; scratch cwd empty after (removed); `git status --porcelain` shows no `HT.v_*` |
| record | `python3 tools/quality_record_v071.py --evidence E` | 0 | wrote the record |
| record rerun after C2 | same, then `git diff --exit-code --stat docs/prd/v0.7.1` | 0 / 0 | bytes equal |
| missing source | evidence copy in scratch without `integration_x.xml`, `--output` in scratch | 1 | `error: missing source: .../integration_x.xml`; no file written; scratch removed |

## Required checks

| command | exit | seen |
|---|---|---|
| `uv lock` | 0 | `Updated eta-rxncat v0.7.0 -> v0.7.1`; the lock diff is that one line |
| `uv run ruff check .` | 0 | passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 885 files already formatted (after C2) |
| `uv run mypy` | 0 | no issues in 93 source files |
| `uv run pytest` | 0 | the default verdict run above, at `acb7e7c`; C2 adds only the record |
| `uv run pytest tests/unit/test_identity.py -q -p no:cacheprovider` (after C2) | 0 | 121 passed |
| `uv run pytest tests/unit/test_identity.py tests/unit/test_doc_refs.py tests/unit/tools -q` (after C2) | 0 | 223 passed |

The first `ruff format --check` (before C1) exited 1 on two of this slice's test files; `uv run
ruff format` on those two fixed it.

## Proof contract

- Requirement 1 (identity, R23): `roadmap_position`; positive case
  `test_version_identity_point_release_readme_passes`, negative
  `test_version_identity_point_release_with_next_minor_built_fails`, `test_roadmap_position`.
- Requirement 2: `git grep -n "0\.7\.1"` hits `pyproject.toml:7`,
  `src/eta_rxncat/__init__.py:3`, `uv.lock:731`, `tests/unit/test_package.py:20`, `README.md:22`
  (badge) and `README.md:19`, `:264`, `:474`.
- Requirement 6 (R47): pitch bullet "a quality point release: integration tests at the module seams
  and known-issue fixes (v0.7.1)." (the v0.7.0 bullet now ends `;`); Features subsection
  `### Integration tests and quality fixes (v0.7.1)`, last; `- **v0.7.1**` under Built; the Planned
  line removed. `pitch_problems`, `check_version_identity` and `listing_problems` pass on the real
  README (in `test_identity.py`). No other existing README words changed.
- Requirement 7 (R46): `git diff --stat bf7b949 HEAD -- docs/prd/v0.7.0` = `DISCREPANCIES.md`, one
  line: DV-10's last cell `open` -> `done (v0.7.0 slice 14 set version 0.7.0; closed on TJ's
  choice, relay qitem-20261127204642-06c18509e72ce4bb)`.
- Requirements 4-5: the table above.
- Requirement 3: CHANGELOG `[0.7.1]`; older entries untouched.

## For the audit to rule on

1. The record script has more sources than the SPEC names: each run's terminal log (junit holds no
   deselected count; the script cross-checks the log's passed count with the junit), the
   `verdict_run_sha` file (so a rerun after the commit gives the same bytes), `pyproject.toml`
   (version) and slice 08's execute proof (the R17 table, for `dead_code`; 44 kept, 0 removed).
2. `dead_code.removed` is empty because slice 08 removed nothing; the script requires a non-empty
   R17 table, not a non-empty `removed`.
3. `known_issues` ids, verdicts and test names, and `integration_tests` seam labels, are constants
   in the script. `known_issues[].test` is a list (several tests per issue) or null. R12's edge
   cases are `dropped`; the red frequency-failure box is listed as `deferred` (mission §3).
4. `integration_tests` lists the 14 seam tests, not the integration policy tests. The skip gate
   covers every `tests/integration/` id.
5. `check_version_identity` has one added check: a later plan version under `### Built` is a
   problem. It tightens R50; no existing check was loosened. Four claim tests and the GPU-claim test
   now use `roadmap_position` (they raised `ValueError` at 0.7.1). `tests/unit/test_package.py`
   (version string) is outside `hacf_touches`; R20 says "and tests".
6. Tier X ran as one command over `tests/integration` (the slice's wording), not one module per
   command (mission heavy-run rule); 114.52 s under `timeout 600`. Host floor 4 GiB per the lead's
   ruling (13 GiB were free). The default suite ran without a host check (R32 exempts Tier O).
7. CHANGELOG date is 2026-11-27. It names no counts; claims point to tests and record keys.
8. The README subsection names three of the eight fixed issues and points to `known_issues`.

## Ledger and lore

- `ensure-node --from-spec`: exit 0; skipped the glob `tests/unit/tools/test_quality_record*.py`
  (already covered by `tests/unit/tools/**`). `eta_rxncat_scaffold` files 31 -> 34, none dropped:
  added `tools/quality_record_v071.py`, `docs/prd/v0.7.1/QUALITY_RESULT.json`,
  `docs/prd/v0.7.0/DISCREPANCIES.md` (each already under `tools/**` or `docs/**`).
- No description changed: scaffold 1998, core 1973, cli 1550.
- `hypergraph_updater.py --from-diff 2fcc8be --apply --slice OPR.0.7.1.9 --json`: exit 0, run once.
  Dirty: cli, core, hw_probe, scaffold, store (their files include paths this slice or the ledger
  write touched). Radius (15): cli, conformers, core, engines, enumerator, hw_probe, integration,
  mapping, optimize, review, scaffold, selectivity, species_runner, store, thermo. `unmapped` 104:
  the two `.claude` backups, three mission progress/SPEC files, the rest untracked `spec/` workbench
  names (not opened). Code graph `ok`.
- Lore marked stale by the updater (left as written, nothing approved): ADR-0010, ADR-0011,
  ADR-0013, ADR-0014, ADR-0019, ADR-0020.
- `hyper_ledger.py validate`: ok.
- `hyper_codegraph.py index`: `index: ok` at the start and before the updater.

## Fix round 1 (audit FAIL iteration 1: U1, U2; R19 citations)

Governed by the lead ruling `~/.cache/eta-rxncat-tmp/lead-ruling-071-09-r19.md` (exceptions
(a) lore node id, (b) added file path; fixes 1-4; note 5). Start stays `2fcc8be`. Fix commit
`4f24c1c`, on top of `dddfb56`.

- U1: the README "Per-sample stage keys" bullet now cites
  `test_tx2_ensemble_sampler_relax_and_store` (every non-None `run.samples` key is a store row)
  and `integration_tests`, beside the unit test. All 3 README bullets carry a record key.
- U2: CHANGELOG `[0.7.1]` header says test and record key; `version`, `known_issues`,
  `integration_tests`, `suites.default` and `dead_code` added as ruled; ADR-0066 stays cited by
  node id. A script over the entry: 26 bullets, 0 without a record key or lore id.
- Fix 3: five `open` entries added to the script's `known_issues` (R14 import limit, with the R14
  test as its bound; `cartesian_basis` GPU Hessian routing; `v070.py` `checked_record_text` and
  its docstring; the `t3.py` constant docstring; the R44 scanner misses; `test` null for the last
  four), worded from the slice 06, 07 and 08 QA proofs.
- Record: regenerated from the same `E` (`~/.hacf/eta-rxncat-hacf/evidence/v071-verdict`). The
  diff is the five added entries only; `verdict_run_sha` stays `acb7e7c`. No fresh verdict run.

| command | exit | seen |
|---|---|---|
| `timeout 3600 python3 tools/quality_record_v071.py --evidence E` | 0 | wrote the record |
| same after `4f24c1c`, `--output` in scratch; `cmp` | 0 / 0 | bytes equal (scratch removed) |
| `git diff --stat acb7e7c..4f24c1c -- src tests` | 0 | empty |
| `git diff --stat acb7e7c..4f24c1c` | 0 | the 4 fix files except tests, plus mission, proof, lore and ledger bookkeeping from `11426e0`..`dddfb56` |
| `uv run --no-sync pytest tests/unit/tools/test_quality_record_v071.py tests/unit/test_identity.py tests/unit/test_package.py tests/unit/test_doc_refs.py -q -p no:cacheprovider` | 0 | 222 passed (before and after the commit) |
| `uv run --no-sync ruff check .` | 0 | passed |
| `uv run --no-sync ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 886 files already formatted |
| `uv run --no-sync mypy` | 0 | 93 source files |
| `hyper_codegraph.py index` | 0 | `index: ok` |
| `hypergraph_updater.py --from-diff dddfb56 --json` (dry), then `--apply --slice OPR.0.7.1.9`, once | 0 / 0 | scaffold only; "no change" (already flagged); `lore_stale_candidates` empty; 101 unmapped = the 2 `.claude` backups and the untracked `spec/` workbench names |
| `hyper_spec.py progress --event executed` | 4 | refused: `audit_failed -> executed` not allowed |
| `progress --event executing` (detail `escape_tracking: v1`), then `--event executed` | 0 / 0 | status executed |
| `hyper_ledger.py validate` | 0 | ok |

Deviations for the audit:
1. The CHANGELOG header adds what is named where only a test or only a key exists: test-less known
   issues and the "Removed" result cite the key alone (no test exists for them), beside
   exceptions (a) and (b).
2. Citations are per bullet: the `v070.py` private-import sentences sit under the Per-sample
   bullet's citations.
3. The integration-suite line also names `test_integration_policy.py` for its policy claim.
4. The script's `KNOWN_ISSUES` docstring now says a test may bound an open limit. Its unit test
   file is unchanged.
5. The full `pytest` and the verdict runs were not repeated (no `src/` or `tests/` change, per the
   ruling). `ensure-node` was not rerun (no new file).
6. `executing` was recorded at the end of the round, not before the edits.

For the version end (ruling note 5): `PLAN_VERSIONS` in `tests/unit/test_identity.py` lacks
v0.10.x, so 0.10.1 would be "not a plan version". Fix before v0.10.x; unchanged now.
