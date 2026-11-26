---
slice: OPR.0.7.0.12
candidate_sha: 243b619
artifact_type: guard
verdict: CLEAR
money_evidence: 3/3 fallback units pass 9 gates (GFN2 gated, UMA reported);
  rank-1 TS-search calls 0; second passes 0 calls; full pytest 2563 passed
---

# Execute evidence: 12-fallback-e2e (OPR.0.7.0.12) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type;
this is builder evidence and the audit writes the QA verdict.

Start `3db44db`. Code commit `24668b3`; every engine command ran at that HEAD. Candidate-only
commit `243b619`.

## Lead ruling on the graft-time gate (row qitem-20261126124248-0826c9cd, ruling A)

The SPEC's "`FallbackRecord` has rank 1 `fell_through` ... and rank 2 `chosen`" cannot hold for
graft_time: mission G5 renumbers the eligible templates 1..k, so a refused template never reaches the
runner. Per ruling A the graft_time gates are: (1) GraftRecord of `TS1a_n_cp_h` is `refused` with
exactly `alignment_rmsd`; (2) the declared rank-2 template `TS1a_n` is graft `ok`; (3) the
FallbackRecord is exactly one attempt, `TS1a_n__ethyl`, renumbered rank 1, `chosen`; (4) 0 engine
calls attributable to the refused template; (5) the G7 ensemble gates and the all-hit second pass.
The worded gate applies to run_time only. No `src/` change.

## Per unit (all 9 gates pass in all three units)

Gates: candidate_ok, graft_records, fallback_record, rank_1_no_ts_search_calls,
engine_calls_attributed, weights_sum_to_one, every_member_face_expected,
no_engine_error_or_face_mismatch, second_pass_all_hits. UMA is reported, not gated (its gates are
recorded under `reported_gates` in the candidate; all pass).

| unit | FallbackRecord (template, rank, outcome, reason, attempt wall s) |
|---|---|
| run_time GFN2 | (TS1a_x__ethyl, 1, fell_through, seed:face_mismatch_pathway, 1.45); (TS1a_n__ethyl, 2, chosen, -, 102.50) |
| graft_time GFN2 | (TS1a_n__ethyl, 1, chosen, -, 74.82) |
| run_time UMA | (TS1a_x__ethyl, 1, fell_through, seed:face_mismatch_pathway, 13.69); (TS1a_n__ethyl, 2, chosen, -, 48.93) |

Graft records (template: status, alignment RMSD A, close contacts): run_time TS1a_x ok 0.0486 0,
TS1a_n ok 0.0354 0, cyclopropene ok 0.0525 0. graft_time TS1a_n_cp_h **refused alignment_rmsd**
0.8884 (2 contacts), TS1a_n ok 0.0354 0, cyclopropene ok 0.0525 0.

### First-pass engine calls by template and stage (CountingEngine; sum equals Engine.evaluate count)

| unit | rank-1 pre-relax | rank-1 TS search (ts_opt + frequency) | chosen: pre-relax / ts_opt / frequency | first pass total | rows | second pass calls / rows | derivation calls / rows |
|---|---|---|---|---|---|---|---|
| run_time GFN2 | 8 | **0** | 273 / 99 / 11 | 391 | 34 | 0 / 0 | 0 / 0 |
| graft_time GFN2 | 0 (refused template not in graph) | **0** | 273 / 99 / 11 | 383 | 33 | 0 / 0 | 0 / 0 |
| run_time UMA | 10 | **0** | 282 / 59 / 11 | 362 | 34 | 0 / 0 | 0 / 0 |

Separation method: `attributed_engine_calls` (tests/e2e/v070.py) wraps `CountingEngine.evaluate`
(stage kind) and `_PreRelax.run`; the pre-relaxation of a template's grafted seed (digest) opens
that template's attempt. Rank-1 TS search = its ts_opt + frequency calls. Second pass: all hits,
`FallbackRecord` and ensemble equal to the first pass.

### Ensemble gates and values (reported values never gated)

| unit | members (index, weight, face) | exclusions | merges | samples | stall cap | G_pathway Eh | first / second pass wall s |
|---|---|---|---|---|---|---|---|
| run_time GFN2 | 1 0.16647, 2 0.41676, 5 0.41676 (all [1,1]); sum 1.0 | orientation_mismatch 4, gate_failed:forming_overlap 1 | 3 | 11 | no | -28.2208485 | 202 / 0.8 |
| graft_time GFN2 | same as run_time GFN2 | orientation_mismatch 4, gate_failed:forming_overlap 1 | 3 | 11 | no | -28.2208485 | 165 / 0.6 |
| run_time UMA | 0 0.16459, 2 0.42052, 5 0.41489 (all [1,1]); sum 1.0 | orientation_mismatch 5 | 3 | 11 | no | -389.1076145 | 159 / 57.6 (model load) |

Zero stalls and zero `engine_error`/`face_mismatch` in all units. The two GFN2 units computed the
same chosen ensemble independently (separate fresh stores) and agree to the printed digits.
No reactant species are run in a fallback unit, so no barrier is computed (`not_computed`).

Run records exported from each store: 1 candidate, 22 trajectories (0 missing), 11 frequencies
(0 missing).

## Stores (a deviation from "a fresh store for this slice"; lead did not object)

One fresh store per unit: `~/.hacf/eta-rxncat-hacf/evidence/v070-slice12/v070_fallback_<construct>_<engine>.sqlite`
(the test refuses an existing one). graft_time's chosen template is run_time's rank 2, so a shared
store would have made one unit's first pass all cache hits. Slice 13 bundles three stores here.

## Commands

Per unit: `~/.hacf/eta-rxncat-hacf/evidence/v070-slice12/run.sh <tag> <xtb|uma> 5400 'test_v070_fallback[<construct>-<engine>]'`:
blocking host check (loop; exits if never free), then `/usr/bin/time -v timeout 5400 <python> -m pytest
tests/e2e/test_v070_fallback.py::<node> -c pyproject.toml --rootdir . -m e2e -s -rs -p no:cacheprovider`
from scratch cwd `~/.cache/eta-rxncat-tmp/slice12/cwd`; xtb: `uv run --no-sync python`; UMA:
`.venv-accept-uma/bin/python` (not re-synced in this slice). Order: run_time xtb, run_time uma,
graft_time xtb. One at a time; all exit 0.

| tag | exit | wall | user + sys CPU s | max RSS kB | host check verdict immediately before |
|---|---|---|---|---|---|
| run-time-xtb | 0 | 3:24.30 | 2234 | 171876 | 12:47:24Z avail=15G gpu=0% gpu_apps=0 heavy=0 eta=0 |
| run-time-uma | 0 | 4:35.29 | 1946 | 10591056 (10.59 GB; floor 12 GiB) | 12:50:54Z avail=14G gpu=0% gpu_apps=0 heavy=0 eta=0 |
| graft-time-xtb | 0 | 2:46.88 | 1662 | 170260 | 12:55:34Z avail=14G gpu=0% gpu_apps=0 heavy=0 eta=0 |

Env in every command (`proof/<tag>.env`): ETA_RXNCAT_XTB (stage xtb 6.8.0), ETA_RXNCAT_ACCEPTANCE=1,
TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp, ETA_RXNCAT_V070_STATE (the slice-12 dir). After each:
scratch cwd empty, no HT.v_* in the repo. Logs, host checks and time files:
`~/.hacf/eta-rxncat-hacf/evidence/v070-slice12/proof/`.

Host check (`hostcheck.sh` in that dir, slice 11 audit finding fixed): no user or rig process is
excluded from the heavy filter; only the check's own `ps` is left out and is logged with CPU/RSS.
Heavy and eta lists were empty in every check; GPU compute list held only desktop clients (about
1.9 GB), 0 % utilisation. The check runs before a unit only; it says nothing about load during one.

## `git show --stat 243b619`

```
 tests/candidate_outputs/v0.7.0/v070_fallback_graft_time_xtb.json            | 659 +
 tests/candidate_outputs/v0.7.0/v070_fallback_graft_time_xtb.runrecord.json  | 962 +
 tests/candidate_outputs/v0.7.0/v070_fallback_run_time_uma.json              | 685 +
 tests/candidate_outputs/v0.7.0/v070_fallback_run_time_uma.runrecord.json    | 969 +
 tests/candidate_outputs/v0.7.0/v070_fallback_run_time_xtb.json              | 686 +
 tests/candidate_outputs/v0.7.0/v070_fallback_run_time_xtb.runrecord.json    | 969 +
 6 files changed, 4930 insertions(+)
```
(from the command output; no candidate file was opened. `git status` printed the six new untracked paths before this commit.)

## Required checks (at 243b619; TMPDIR on disk, ETA_RXNCAT_XTB exported)

`uv sync --locked` 0; `ruff check .` 0; `ruff format --check . --extend-exclude spec/archive
--extend-exclude spec/process` 0 (726 files); `mypy` 0 (91 files);
`pytest tests/e2e/test_v070_inputs.py` 0 (18 passed); full `pytest` 0 (2563 passed, 195
deselected, 174.4 s); base licence gate 0 (13 packages, 0 failures). The same set also passed
before the code commit (2563 passed).
