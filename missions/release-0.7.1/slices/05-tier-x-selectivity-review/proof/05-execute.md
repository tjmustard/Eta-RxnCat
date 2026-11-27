---
slice: OPR.0.7.1.5
candidate_sha: cd83053
artifact_type: guard
verdict: CLEAR
money_evidence: Tier X 2 passed 0 skipped; full pytest 2763 passed;
  ruff/format/mypy exit 0; 5 seam breaks fail
---

# Execute evidence: 05-tier-x-selectivity-review (OPR.0.7.1.5) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `3da4284`. C1 `0e8253f` (the test file). C2 `cd83053` (updater flags, progress, task boxes,
field note). Then this proof. No push, no tag.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-05`.

## Lead ruling used: 4 GiB floor

Dispatch row `qitem-20261127220616-f4d42ebfeb8e9510`: "if 12 GiB isn't free, a 4 GiB floor for these
CPU GFN2 commands (v0.7.0 basis qitem-20261126195109-0246e7d8), valid while measured peak RSS stays
<= 2 GiB".

The first check (22:09:05Z, `E/hostcheck.sh`, 12 GiB, output `E/run1.hostcheck12`) exited 1:
`avail=11G gpu=0% gpu_apps=0 heavy=0 eta=0`. Every GFN2 and pytest command used
`E/hostcheck-floor4-self.sh` as a separate blocking step. It is slice 04's script with only the
excluded driver path changed to `v071-05/breaks.py`; it differs from `hostcheck.sh` only in `-ge 4`.
MemAvailable was 10-11 GiB. Highest peak RSS: GFN2 commands 162608 kB, full pytest 356728 kB.

## Measured run (requirements 1-2)

Host check `E/run1.hostcheck` (`HOST FREE`), then from the scratch cwd
`~/.cache/eta-rxncat-tmp/v071-05-cwd` (empty afterwards), `P` = the project root:

```
TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp \
ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb \
ETA_RXNCAT_ACCEPTANCE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/time -v -o E/run1.time timeout 600 P/.venv/bin/python -m pytest -c P/pyproject.toml \
  --rootdir P -p no:cacheprovider -m "integration and xtb" \
  P/tests/integration/test_seams_selectivity_gfn2.py --junitxml=E/run1.junit.xml -v --durations=0
```

Exit 0. Wall 1:27.46, maximum resident set size 161248 kB. Junit: tests 2, failures 0, errors 0,
**skipped 0**.

| test | outcome | call (s) | limit |
|---|---|---|---|
| `test_tx4_graph_file_to_selectivity_and_replay` | passed | 86.94 | estimate 90, stop above 180 |
| `test_tx5_review_export_round_trip` | passed | 0.17 (replays T-X4's rows) | about 0 added |

Alone on a fresh store T-X5 computes the chain itself: 85.40 s (`control-x5-alone`).

`git status --porcelain` afterwards: the slice's own files and the pre-existing untracked
`.claude/*.bak-*`, `spec/archive/`, `spec/process/`. No `HT.v_*` in the repo or the scratch cwd.

## Seam breaks (requirement 4; builder's pre-check, not the audit's `seam_breaks.json`)

Throwaway worktree `~/.cache/eta-rxncat-tmp/wt0705` at `0e8253f` (removed afterwards),
`PYTHONPATH=<wt>/src`, main venv python; the driver asserts the imported path
(`<wt>/src/eta_rxncat/__init__.py`). Driver `E/breaks.py` (exit 0), output `E/breaks.out`, per case
`E/break-<name>.{diff,log,time,hostcheck}`; one named test per case under `timeout 600`.

| case | test | exit | failed on |
|---|---|---|---|
| control, no edit | T-X4 | 0 | passed, 84.96 s |
| control, no edit | T-X5 | 0 | passed, 85.40 s |
| `run_selectivity` passes the other pathway's `reactant_key` | T-X4 | 1 | `(('[exo]', 1),) == (('[endo]', 1),)` |
| loader drops `pathway_pruning_rules` | T-X4 | 1 | variant graph round trip unequal |
| loader drops every node's `pathway` | T-X4 | 1 | `SelectivityInputError`, 0.29 s (raised by `run_selectivity`, not an assert) |
| serialiser `sort_keys=False` | T-X5 | 1 | unsorted objects in `run_data.json` |
| `export_run_data` skips the `ts_opt` row | T-X5 | 1 | exported trajectory set differs from the samples' keys |

## Required checks (requirements 3-4)

| command | exit | seen |
|---|---|---|
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 871 files already formatted |
| `uv run mypy` | 0 | no issues, 91 source files |
| `timeout 3600 uv run pytest` (`ETA_RXNCAT_XTB`, `TMPDIR` set; host check `E/pytest.hostcheck`) | 0 | **2763 passed, 202 deselected**, 315.39 s (`E/full-pytest.log`) |

Both new tests are deselected by default (`xtb`). The full run is on the tree that became C1; ruff,
format and mypy were rerun at C2.

## Other commands

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and before the updater) | 0 | `index: ok` |
| `hyper_gates.py mode`; `hyper_spec.py resolve <slice dir> --json` | 0 | interactive; no errors |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `ruff check`, `ruff format --check`, `mypy` on the draft | 0 | |
| `pytest tests/integration/test_integration_policy.py` | 1, then 0 | first draft used `monkeypatch.context` (banned); changed to `contextlib.chdir`; 57 passed |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | no change; glob touch skipped (already listed); ledger path owned by other nodes. Node files `tests/integration/**` before and after |
| `hypergraph_updater.py --from-diff 3da4284 --apply --slice OPR.0.7.1.5 --json` (once) | 0 | node and radius `eta_rxncat_integration` (dirty); `lore_stale_candidates` empty |
| `hyper_ledger.py validate` | 0 | ok |
| `hyper_lore.py note` | 0 | one field note |

`unmapped` (updater): the `.claude` settings backups, the mission and slice files, and untracked
`spec/` files listed by name (none opened). Full JSON: `E/updater.json`.

Slips with no effect: one early `cat >` to an unset `$TMPDIR` path was refused, and two
`hyper_ledger.py show` calls with a node argument exited 2 (it takes none).

## For the auditor to rule on

1. **`RunRecord.fallback`.** `RecordRun` requires a `FallbackRecord`, and `run_selectivity` runs no
   fallback. The test states what did happen: the node's one template, its real rank, outcome
   `chosen` (it seeded the ensemble), and `wall_time_s` = the run's
   `total_pre_relax_wall_time_s`. The exporter needs `chosen_template_id` to resolve members. I
   judged these honest values, not the slice's stop-and-report case. No barrier, endpoint or gate
   is claimed.
2. **Reactant-key variant is not a plan variant.** Both pathways derive the same key from the shared
   reactant nodes, so no R42 plan variant can separate them, and different keys cannot be scored.
   T-X4 reruns with `dataclasses.replace`d `PathwayInputs` (marker keys, member gates that reject
   every seed): no score, all cache hits, each ensemble must carry its own key.
3. **Rules variant** (R42): the plan with the TS nodes at priority 1 and one rule (a rule is only
   valid on priority-1 pathways). It is enumerated and round-tripped through a file, engine-free.
4. **Schema check.** The project has no JSON Schema validator and v0.7.0 forbids adding
   `jsonschema`. The test has a small checker for the keywords the committed schema uses; an unknown
   keyword raises.
5. **Reader equality** uses `export.model_dump_json()`. The bundle's canonical bytes round floats, so
   they are checked against the schema and read, not compared for equality with the export.
6. **Extra gate:** every object in `run_data.json` has sorted keys. Equal bytes across two writes
   cannot fail on the key-order break.
7. T-X5 calls the same chain helper on the shared store (a replay after T-X4), so it can run alone
   (R22); it does not receive T-X4's Python object.
8. The test imports `_assert_all_hits`, `_member_gates` and `_ts_recipe` from
   `test_seams_ts_gfn2.py`.
9. The integration node's description (1939 chars) is unchanged and does not describe the new
   module; its `depends_on` has no `eta_rxncat_review`, which T-X5 now imports.
10. 4 GiB floor and the driver's self-excluding host check, above.
