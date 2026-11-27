---
slice: OPR.0.7.1.3
candidate_sha: 845b841
artifact_type: guard
verdict: CLEAR
money_evidence: full pytest 2763 passed; parity runrecord cmp exit 0, 0 engine
  calls; ruff/format/mypy exit 0
---

# Execute evidence: 03-ensemble-sample-keys (OPR.0.7.1.3) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `4d58042`. C1 `2365953` (source and tests). C2 `845b841` (updater flags, progress, task boxes,
touches, field note). Then this proof. No push, no tag.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-slice03`.

## Lead rulings used

**A (`qitem-20261127205634-18d154060088d162`, answering `qitem-20261127205615-51483dd7d778ea29`):**
touches extended by one file, `src/eta_rxncat/orchestrator/ts_fallback.py`, only to set
`samples[0].pre_relax_key` by `dataclasses.replace` from the key it already builds. Two SPEC
sentences failed against `4d58042`:

1. "The runner fills each key from the `StageKey` it already builds for that row" (with "Index 0 is
   the seed" and "The timeout rows (`note_timeout`) are read from the rows of
   `samples[i].pre_relax_key`"): `run_ts_ensemble_detailed` receives the seed already relaxed and
   builds no pre-relax key for it; `run_ts_with_fallback` does. The promoted record has
   `samples[0].pre_relax_key`.
2. "`derive_samples` (:376) maps `run.samples` to `RecordSample`s and drops `_digest`, `_PreRelax`
   and `_sorted_pairs`": `attributed_engine_calls` and `run_fallback_unit` (v0.7.0 slice 12 call
   attribution) also use `_digest` and `_PreRelax`.

The `ts_fallback.py` diff is: the `replace` import, `seed_pre_relax_key = pre_relax.last_key`, and
the `replace` on the chosen return.

**Memory floor (lead message 11-27 21:05Z, relayed into the builder's pane; basis
`qitem-20261126195109-0246e7d8`):** MemAvailable floor 4 GiB for this GFN2 run on a copy of the
replan-7 store; stop if any engine call. Every other host check unchanged. Engine calls were 0.

## Requirement 1: `SampleKeys`, `samples`, export

`uv run pytest tests/unit/orchestrator tests/e2e/test_v070_samples.py -q` at C2: exit 0,
**287 passed, 1 deselected** (`E/proof/targeted.log`).

New tests: `test_sample_keys_name_every_samples_rows` (seed, searched, pre-relax-failed, clashed;
non-None keys are store rows), `test_a_cached_run_records_the_same_sample_keys`,
`test_a_failed_seed_records_only_the_seed`, two added assertions in the stall-cap guard test,
`test_the_seed_sample_names_the_graft_pre_relax_row` (ruling A), and
`test_a_clashed_sample_has_no_keys_even_with_rows_in_the_store`.

## Requirement 2: private eta imports left in `tests/e2e/v070.py`

`grep -n "import _\|, _[a-zA-Z]" tests/e2e/v070.py`:

```
32:from fixtures import DATA, _exact_keys, read_xyz
65:from eta_rxncat.orchestrator.ts_ensemble import PRE_RELAX_KIND, _digest, _PreRelax
112:    data = _read(path, _PLAN_KEYS | _RUN_KEYS)
127:        _exact_keys(path, name, constructs[name], _PLAN_KEYS)
315:    from eta_rxncat.orchestrator.ts_fallback import _canonical_smiles
535:        derivation_calls, derivation_rows = calls["evaluate"], _rows(store) - rows
```

| private eta name left | reason |
|---|---|
| `_PreRelax` | `attributed_engine_calls` patches `_PreRelax.run` to attribute calls per template (v0.7.0 slice 12) |
| `_digest` | the same attribution: `attributed_engine_calls` and `run_fallback_unit` match seed starts to templates |
| `_canonical_smiles` (lazy, :315) | `reactant_specs` matches reactant nodes to `reactant_key` with the runner's own canonicalisation; outside R37, unchanged by this slice |

`_sorted_pairs`, `TSSpec`, `run_transition_state` and `build_stage_key` imports are gone.
`_exact_keys` is a test-module helper, not eta. Lines 112, 127 and 535 are not imports.

## Requirement 3: the clashed-sample rule

Checked in the C1 worktree (`PYTHONPATH=<wt>/src`, main venv python, import path in
`E/proof/import-path.txt`):

| `v070.py` used | exit | log |
|---|---|---|
| C1 | 0 | `E/proof/samples-head.log` |
| `bf7b949` as it was | 0 | `E/proof/samples-bf7b949.log` |
| `bf7b949` minus the `clashed` branch (`E/proof/bf7b949-no-clashed.diff`, against C1) | 1: sample 1 gained `pre_relax_key` | `E/proof/samples-bf7b949-no-clashed.log` |

The file was restored with `git checkout` in the worktree before the parity run.

## Requirement 4: parity

Method: as v0.7.0 slice 17 (which the SPEC cites), the unit ran on a `sqlite3 .backup` copy of
`v070-replan7-runs/v070_enum.sqlite` (source opened `mode=ro`). That store's
`v070_enum_ethyl_endo_xtb.runrecord.json` is byte-equal to the promoted fixture (`cmp` exit 0). So
the run reads cached rows through the new code; it does not recompute any row. A fresh store could
not compare byte-equal (stored `pre_relax_wall_time_s` values).

Host check (separate call, `E/hostcheck-floor.sh`; it differs from the v0.7.0 script only in the
floor argument, which the verdict line now prints). Earlier at the 12 GiB floor it exited 1 on
memory alone; polls in `E/proof/parity.hostcheck.polls`. The passing check
(`E/proof/parity.hostcheck`):

```
verdict: floor=4G avail=11G gpu=0% gpu_apps=0 heavy=0 eta=0
HOST FREE
```

Command, from a scratch cwd (empty afterwards), env in `E/proof/parity.env` (xtb path,
`ETA_RXNCAT_ACCEPTANCE=1`, thread pins 1, `ETA_RXNCAT_V070_STATE=E/state`, TMPDIR on disk,
`PYTHONPATH=<wt>/src`):

```
/usr/bin/time -v timeout 5400 <main .venv python> -m pytest
  "<wt>/tests/e2e/test_v070_enumeration.py::test_v070_unit[ethyl-endo-xtb]"
  -c <wt>/pyproject.toml --rootdir <wt> -m e2e -s -rs -p no:cacheprovider
```

`<wt>` = `/home/tjmustard/.cache/eta-rxncat-tmp/wt0703` (detached at `2365953`, no `uv` in it,
removed afterwards by that literal path with `--force`, discarding its outputs).

- exit 0, 1 passed; wall 0:01.05; peak RSS 160048 kB; 9/9 gates pass;
- engine calls 0/0, new rows 0/0;
- store copy sha256 `665cdfd8...a5d18` before and after, 368 rows; source sha256 check OK after;
- `cmp E/state/records/v070_enum_ethyl_endo_xtb.runrecord.json <wt>/tests/fixtures/v0.7.0/...`
  **exit 0** (both sha256 `cfc1b9a6...1fcf6`); the worktree fixture equals the main checkout's.
  Byte-equal, so no VOLATILE path list is needed.

## Requirement 5: required checks (on the tree that became C1)

| command | exit | seen |
|---|---|---|
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 865 files already formatted |
| `uv run mypy` | 0 | no issues, 91 source files |
| `timeout 3600 uv run pytest -q` (`ETA_RXNCAT_XTB` set) | 0 | 2763 passed, 196 deselected (`E/proof/full-pytest.log`) |

Before the full run a host check (`free`, `ps`) showed no other pytest or xtb process.

## Other commands

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and before the updater) | 0 | `index: ok` |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `hyper_spec.py lint <SPEC>` (after the touches edit) | 0 | ok |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | no change; glob touch skipped (node already lists the unit tests); `tests/e2e/*` and the ledger owned by other nodes |
| `hypergraph_updater.py --from-diff 4d58042 --apply --slice OPR.0.7.1.3 --json` (once) | 0 | dirty: selectivity, species_runner; needs_review: integration; `lore_stale_candidates` empty |
| `hyper_ledger.py validate` | 0 | ok |
| `hyper_lore.py note` | 0 | one field note |

During iteration one `ruff check` failed (a long line, an import order) and one targeted pytest
stopped at collection (`OptionSpec` imported from the wrong module in the new test); both fixed
before the runs above. One combined shell command with a heredoc and `hyper_lore.py note` was
refused by the gate hook (nothing in it ran); the parts were then run separately.

`unmapped` (updater): the `.claude` settings backups, the mission and slice files, and untracked
`spec/` files listed by name (none opened). Full JSON: `E/proof/updater.json`.

Ledger descriptions unchanged: selectivity 1455, species_runner 1991.

## For the auditor to rule on

1. `ts_fallback.py` and the `hacf_touches` entry: lead ruling A.
2. Private names left in `v070.py` (table above), including `_canonical_smiles`, which ruling A's
   text does not name.
3. Parity on a copied store (all cache hits) at a 4 GiB floor. The fresh-compute path of the new
   `last_key` fill is exercised by the fake-engine unit tests only, not by a real-engine run.
4. A run whose seed fails records `samples` = the seed entry only (the SPEC says nothing on failed
   runs). `run_ts_ensemble_detailed` called directly leaves `samples[0].pre_relax_key` None.
5. `derive_samples` keeps its signature, redraws the samples (no engine) only for the member digest
   assertion, and reads rows by hex key through a `StageKey` (new helper `stored_row`, as
   `review/export.py` does).
6. `test_v070_samples.py` uses `_PreRelax.stage()` to plant rows under the keys the old logic looked
   up, and a stub engine for its identity.
7. The format oracle ran only in the excluding form.
