---
slice: OPR.0.7.1.7
candidate_sha: 225cfbd
artifact_type: guard
verdict: CLEAR
money_evidence: 12 new tests fail at bf7b949 then pass; full pytest 2878 passed;
  Tier X 6 passed 0 skipped; 15 v0.7.0 records byte-identical
---

# Execute evidence: 07-known-issues-runtime (OPR.0.7.1.7) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `7b15de5`. C1 `bc7e8da` (code and tests). C2 `225cfbd` (ledger flags, progress, task boxes,
field note). Then this proof. No push, no tag, no package install or sync.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-07`.

## Changes

- R29 `store/artifact_store.py`: `_refuse_non_real` (TypeError for bool and non-`numbers.Real`),
  then the unchanged `> 0` ValueError; `_BUSY_TIMEOUT_MAX_MS = 2**31 - 1` clamps
  `sqlite3.connect(timeout=)` and every open-time `PRAGMA busy_timeout`; docstring. The open order,
  the single deadline and `StoreBusyError` are unchanged (ADR-0015); `inf` as no deadline matches
  PROPOSED ADR-0059.
- R14 `engines/mace.py`: `_restored_env` around `import_module("mace")` only; docstring states the
  already-imported limit.
- R38 `review/run_data.py`: a wrap `field_serializer("result", when_used="json")` on
  `RecordSelectivity`. No core file and no `SelectivityResult` change.

## Failing at the base, passing after (requirements 1-4)

Worktree at `bf7b949` with only the three changed test files copied in (they and the three source
files are identical at `bf7b949` and Start), R22 interpreter (`PYTHONPATH=<worktree>/src`,
`.venv/bin/python -m pytest -p no:cacheprovider`; `eta_rxncat.__file__` under the worktree).
Exit 1, **12 failed, 22 passed** (`E/fail-base.txt`). Worktree removed. All pass on C1.

| R | test id (file) | seen at `bf7b949` |
|---|---|---|
| 29 | `store/test_first_open.py::test_infinite_open_timeout_opens_a_fresh_store` | `OverflowError: cannot convert float infinity to integer` |
| 29 | `...::test_infinite_open_timeout_waits_for_a_held_lock` | the same OverflowError, recorded by the worker |
| 29 | `...::test_infinite_open_timeout_is_clamped_in_sqlite` | the same OverflowError |
| 29 | `...::test_open_timeout_must_be_a_real_number[True]` | `DID NOT RAISE TypeError` |
| 29 | `...::test_open_timeout_must_be_a_real_number[{5,None}]` | TypeError from `>`, message lacks `open_timeout_s` |
| 14 | `engines/test_mace.py::test_importing_mace_leaves_the_torch_env_as_it_was[{absent,set}-{imports,import-error}]` | `'1' == None` / `'1' == '0'` |
| 38 | `review/test_export.py::test_an_infinite_ratio_round_trips_as_the_string_infinity[{None,1}]` | `None == 'Infinity'` |

New tests that **pass at the base too**, because they guard behaviour that must not change:
`test_a_nan_anywhere_in_a_record_is_refused[{literal,string}]`, `test_the_committed_records_are_found`
and the 15 `test_a_finite_v070_record_reserialises_to_its_bytes[...]`. R29's NaN, 0 and -1 case is
the existing `test_open_timeout_must_be_positive` (not duplicated; passes at the base).

Held-lock test alone under `timeout 120`, on C2: exit 0, 1 passed in 0.70 s
(`E/held-lock-alone.txt`). Releaser joined with 5 s, daemon worker with 30 s.

## R38 measurement and byte compare (requirement 3)

`E/measure-ser-inf-nan.py` / `.txt`: a record-like model over a nested core-like model, with
`ser_json_inf_nan` = `null`, `strings` and `constants` on the **outer** config: all three write
`{"result":{"ratio":null}}`, which fails to read back. So the config route does not reach the nested
model. `E/measure-serializer.py` / `.txt` (rerun on the shipped classes): the inf record round-trips
with and without `indent`; `"NaN"`, `NaN` and `"-Infinity"` as the ratio are refused.

Byte compare: `(model_dump_json(indent=1) + "\n")` (the v0.7.0 writer's format,
`tests/e2e/v070.py::checked_record_text`) equals the committed bytes for all 15:
`v070_enum_{ethyl,npropyl}_{endo,exo,selectivity}_{uma,xtb}` (12),
`v070_fallback_graft_time_xtb`, `v070_fallback_run_time_{uma,xtb}`. Fixtures read only;
`git diff --quiet 7b15de5 HEAD -- tests/fixtures` exit 0.

## Required checks (requirement 5)

On the tree that became C1 (only SPEC task boxes changed afterwards), `uv run --no-sync`, `TMPDIR`
and `ETA_RXNCAT_XTB` set:

| command | exit | seen |
|---|---|---|
| `ruff check .` | 0 | All checks passed |
| `ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 876 files already formatted |
| `mypy` | 0 | no issues, 91 source files |
| `timeout 3600 ... pytest` | 0 | **2878 passed, 202 deselected**, 2 pyscf basis-set-exchange UserWarnings, 619.86 s (2848 at slice 06, +30) |
| `timeout 3600 ... pytest tests/unit/store tests/unit/engines tests/unit/review tests/integration` | 0 | 615 passed, 85 deselected, 52.62 s |

The full run took 619.86 s against 219 s at slice 06, and passed the tool's 600 s foreground limit
(it finished in the background). Other rigs' pytest and git processes were running around then; load
average read 19 to 24 on 20 cores just after. I did not establish the cause. The new tests are
short (the 34 selected base-run tests took 0.75 s).

Tier X rerun: host check first, as its own command (11 GiB available, no heavy process in `ps`,
load 19.09/24.41/21.15). Then, `ETA_RXNCAT_ACCEPTANCE=1`, one thread per BLAS,
`timeout 3600 .venv/bin/python -m pytest -p no:cacheprovider -m "integration and xtb"
tests/integration --junitxml=E/tierx.junit.xml`: exit 0, junit **tests 6, errors 0, failures 0,
skipped 0**, wall 1:55.68, max RSS 162544 kB. No GPU, UMA, MACE or PySCF engine run was selected.

Iteration failures, mine, fixed before C1: `mypy` exit 1 twice (an inline
`isinstance(..., numbers.Real)` on a `float` parameter made the rest of `__init__` unreachable to
mypy; then `numbers.Real` has no `>` in the stubs). The first run of the prototype serializer script
after the change exited 1 (it declared a second serializer on the shipped class); fixed in the saved
copy and rerun.

## Ledger and other commands

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and before the updater) | 0 | `index: ok` |
| `hyper_gates.py mode`; `hyper_spec.py resolve <slice dir> --json` | 0 | interactive; no errors |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | see below |
| `hypergraph_updater.py --from-diff 7b15de5 --apply --slice OPR.0.7.1.7 --json` (once, after C1) | 0 | see below |
| `hyper_ledger.py validate` | 0 | ok |
| one field note (mission `NOTES.md`) | 0 | |

`ensure-node` on `eta_rxncat_store`: skipped the three globs and the two paths owned by `engines` and
`review`; appended `src/eta_rxncat/store/artifact_store.py` (4 files to 5; all 4 kept; already
covered by the node's own glob).

Updater: dirty `cli`, `core`, `engines`, `hw_probe`, `review`, `scaffold`, `store`; blast radius also
`conformers`, `enumerator`, `integration`, `mapping`, `optimize`, `selectivity`, `species_runner`,
`thermo`. `core`, `hw_probe`, `cli` and `scaffold` come from `spec/compiled/architecture.yml` being
in the diff (ensure-node had changed it): `impact --files` on that path alone names `cli`, `core`,
`hw_probe`, `scaffold`, `store`. `lore_stale_candidates` empty, no stale line on stderr. `unmapped`:
104 paths (the `.claude` backups, mission and slice files, untracked `spec/` files listed by name,
none opened). Full JSON `E/updater.json`. No ledger description changed.

## For the auditor to rule on

1. **R38 knock-on, not changed (outside touches).** `tests/e2e/v070.py::checked_record_text` still
   raises on a non-finite ratio, and its docstring says it "would be written as `null`", which is no
   longer true. The README / CHANGELOG known issue is slice 09's.
2. **R38 scope.** `model_dump(mode="json")` also yields `"Infinity"`; python-mode `model_dump` keeps
   `inf`. The NaN test replaces every float in the stub record (and the ratio) one at a time.
3. **R29 edges, unchanged or newly worded.** `Decimal` is not `numbers.Real`, so it raises the new
   TypeError (at the base it also raised TypeError, from `float + Decimal`; read from the code, not
   run). An integer too large for a float (`10**400`) is not handled: I expect `OverflowError` as at
   the base (not run).
4. **R14.** The guard covers the `import mace` line only. `torch` import and `torch.load` are outside
   it. The test stubs `torch` in `sys.modules` and calls `_load_model` on an uninitialised instance,
   so it needs no weights; it adds the import-error case.
5. Checks ran as `uv run --no-sync` (round notes: no install). AGENTS.md's sync, `.venv-runtime` and
   licence-gate steps were not run; this slice changes no dependency.
