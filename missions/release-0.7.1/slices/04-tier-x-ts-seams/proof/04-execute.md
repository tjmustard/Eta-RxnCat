---
slice: OPR.0.7.1.4
candidate_sha: 5487d36d66f71b23752a7981b07557f774c8af55
artifact_type: guard
verdict: CLEAR
money_evidence: Tier X 4 passed 0 skipped; full pytest 2763 passed;
  ruff/format/mypy exit 0; 7 seam breaks fail
---

# Execute evidence: 04-tier-x-ts-seams (OPR.0.7.1.4) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `bf287aa`. C1 `3eb5e3e` (the test file). C2 `5487d36` (updater flags, progress, task boxes,
field note). Then this proof. No push, no tag.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-04`.

## Lead ruling used: 4 GiB floor

Dispatch row `qitem-20261127211807-3e66d4631f6cbcca`: "if 12 GiB isn't free, a 4 GiB floor is
allowed for these CPU GFN2 commands, on the v0.7.0 basis qitem-20261126195109-0246e7d8", with peak
RSS recorded and a stop above 2 GiB.

The first check (21:20:38Z, the 12 GiB `v071-resolve/hostcheck.sh`) exited 1 with
`verdict: avail=11G gpu=0% gpu_apps=0 heavy=1 eta=0` (the heavy process was a momentary `rig ps`).
Its output file was then overwritten by the floor check. Every GFN2 and pytest command after it used
`E/hostcheck-floor4.sh`, which differs from the 12 GiB script only in `-ge 4`. MemAvailable was
11-12 GiB throughout. Highest peak RSS: GFN2 commands 154948 kB, full pytest 358388 kB. Neither is
near 2 GiB.

## Measured run (requirements 1-2)

Host check, separate call (`E/run2.hostcheck`, 21:21:30Z):

```
Mem:              30          18           4           0           7          11
== heavy processes (any user/rig; >=100% CPU or >=2 GiB RSS)
    PID USER      NI %CPU   RSS     ELAPSED COMMAND
verdict: avail=11G gpu=0% gpu_apps=0 heavy=0 eta=0
HOST FREE
```

Command, from the scratch cwd `~/.cache/eta-rxncat-tmp/v071-04-cwd` (empty afterwards), `P` = the
project root:

```
TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp \
ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb \
ETA_RXNCAT_ACCEPTANCE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/time -v -o E/run2.time timeout 600 P/.venv/bin/python -m pytest -c P/pyproject.toml \
  --rootdir P -p no:cacheprovider -m "integration and xtb" \
  P/tests/integration/test_seams_ts_gfn2.py --junitxml=E/run2.junit.xml -v --durations=0
```

Exit 0. `/usr/bin/time -v`: wall 0:31.93, maximum resident set size 154276 kB. Junit
(`E/run2.junit.xml`): tests 4, failures 0, errors 0, **skipped 0**.

| test | junit | wall s | limit s (2x R33) |
|---|---|---|---|
| `test_tx1_prfo_validation_thermo_and_replay` | passed | 5.84 | 16 |
| `test_tx2_ensemble_sampler_relax_and_store` | passed | 9.71 | 82 |
| `test_tx3_fallback_rank1_chosen_and_replayed` | passed | 15.37 | 160 for both T-X3 tests (16.00) |
| `test_tx3_rank1_face_mismatch` | passed | 0.63 (shared store); 16.41 s alone on a fresh store | |

### The first run failed (my test's error)

`E/run1.*`, same command, 21:20:45Z check: exit 1, 3 passed, 1 failed (wall 0:31.63, RSS
154132 kB). T-X3 asserted `run.ensemble.members[0].source == "seed"` and saw `fragment_embed:0`: on
the ethyl candidate the seed merges into the lower-G sample. The slice does not require T-X3's seed
to be a member (that gate is T-X2's), so I replaced the line with `assert run.ensemble.members` and
`assert run.samples[0].source == "seed"`. T-X3's slice gates ("names rank 1 with no fall-through",
no seed fault, replay all hits) are unchanged. No product code changed.

## `git status --porcelain`

After both runs: the slice's own files and the pre-existing untracked `.claude/*.bak-*`,
`spec/archive/`, `spec/process/`. **No `HT.v_*`**, in the repo or in the scratch cwd.

## Seam breaks (requirement 3; builder's pre-check, not the audit's `seam_breaks.json`)

Throwaway worktree `~/.cache/eta-rxncat-tmp/wt0704` at `3eb5e3e` (removed afterwards),
`PYTHONPATH=<wt>/src`, main venv python; the driver asserts the imported path
(`<wt>/src/eta_rxncat/__init__.py`). Driver `E/breaks.py` (exit 0), output `E/breaks.out`, per case
`E/break-<name>.{diff,log,time,hostcheck}`; one named test per case under `timeout 600`.

| case | test | exit | failed on |
|---|---|---|---|
| control, no edit | mismatch (alone, fresh store) | 0 | passed |
| final `frequency` row not stored | T-X1 | 1 | `row_count` 1 != 2 |
| validator given swapped forming-bond pairs | T-X1 | 1 | forming overlap and in-phase gates False |
| `minimize` freezes the non-core atoms | T-X2 | 1 | sample excluded `pre_relax_failed:CoreDisplacementError`, no `ts_opt` key |
| `core` itself replaced by the non-core atoms | T-X2 | 1 | `KeyError: 0` at `members[0]` (seed no longer a member), before the core-coordinate assert |
| face comparison inverted | T-X3 | 1 | `stop_reason` `all_templates_failed` |
| pre-check skipped (`if False`) | mismatch | 1 | store holds a rank-1 `ts_opt` row |
| pre-check skipped and ensemble gets `expected_face=None` | mismatch | 1 | rank 1 `chosen` |

Note on "pre-check skipped": the ensemble still reports `seed:face_mismatch_pathway` for rank 1, so
only the no-search-rows gate catches it.

Host check before these: the first driver run waited 10 minutes and ran **no** test, because the
check counted the driver itself as an eta process (its path contains `eta-rxncat`); a niced pytest of
another rig was also running. `E/hostcheck-floor4-self.sh` (the per-case check) differs from
`hostcheck-floor4.sh` only in excluding `v071-04/breaks.py`. A separate-call check with the
unmodified floor-4 script passed at 21:39:30Z before the second driver run, and every per-case check
read `heavy=0 eta=0`.

## Required checks (requirements 3-4)

| command | exit | seen |
|---|---|---|
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 868 files already formatted |
| `uv run mypy` | 0 | no issues, 91 source files |
| `timeout 3600 uv run pytest -q -rs` (`ETA_RXNCAT_XTB`, `TMPDIR` set; host check `E/pytest.hostcheck`) | 0 | **2763 passed, 200 deselected**, 362.95 s (`E/full-pytest.log`) |

The new module is not in the default junit (`E/full.junit.xml`): `xtb` deselects it. The full run is
on the tree that became C1; ruff, format and mypy were rerun at C2.

## Other commands

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and before the updater) | 0 | `index: ok` |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | no change; glob touch skipped (already listed); ledger path owned by other nodes. Node files `tests/integration/**` before and after |
| `hypergraph_updater.py --from-diff bf287aa --apply --slice OPR.0.7.1.4 --json` (once) | 0 | node and radius `eta_rxncat_integration` (dirty); `lore_stale_candidates` empty |
| `hyper_ledger.py validate` | 0 | ok |
| `hyper_lore.py note` | 0 | one field note |

`unmapped` (updater): the `.claude` settings backups, the mission and slice files, and untracked
`spec/` files listed by name (none opened). Full JSON: `E/updater.json`.

The integration node's description (1581 chars) is unchanged and does not yet describe
`test_seams_ts_gfn2.py`; no description was compressed or grown.

## For the auditor to rule on

1. T-X3 does not require the seed to be a member (see "The first run failed").
2. The two T-X3 tests share a module-scoped store, not the per-test `store` fixture (R43 allows it;
   stated in `fallback_store`'s docstring and the mismatch test's).
3. The variant plan names the new template `TS1a_x_rank1`.
4. The mismatch gate "no `ts_opt` or `frequency` row for rank 1" is asserted as: the store's rows of
   those kinds are exactly the keys in rank 2's `run.samples`.
5. T-X3's docstring names an extra break (face comparison inverted), because dropping
   `expected_face` fails only the mismatch test.
6. The "core replaced" T-X2 break fails incidentally (table above); the break the slice names
   (frozen list swapped) fails on the intended assert.
7. T-X2 also asserts the sample was searched and that its relaxed core matches the seed's within
   `CORE_FREEZE_TOLERANCE_ANGSTROM`.
8. The test imports `_read_xyz` from the integration `conftest.py`.
9. 4 GiB floor and the driver's self-excluding host check, above.
