---
slice: OPR.0.7.0.13
candidate_sha: e0a4988
artifact_type: guard
verdict: CLEAR
money_evidence: "Fix round: root page states no decimation; rebuilt bundle gates
  clean, 0 engine calls; M12 581/581 in Chrome and Playwright Firefox; full
  pytest 2593 passed"
---

# Execute evidence: 13-review-bundle-and-record (OPR.0.7.0.13) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type;
this is builder evidence and the audit writes the QA verdict.

Start `9b3101e`. First build: code `43de81b`, candidates `5b6bf1a`, record `d7a4e86`, ledger flag
and proof `33b9212`. **Audit FAIL, iteration 2** (U1, row qitem-20261126135941-d5138665, progress
`fb74dd0`). Fix round from `fb74dd0` (brief row qitem-20261126135956-06dfd8cf): code `ea76693`,
candidate removal `bcdad1d`, rebuilt candidates `e0a4988`; the record and this proof are in the
commit after it. No `src/` change. No engine ran. Nothing promoted, pushed or tagged. Everything
below describes the rebuilt bundle.

## Fix round: U1, the false decimation sentence

The root page's intro now comes from `decimation_statement` over the strides of the sub-bundles'
`run_data.json` files; a new gate, `intro_gate`, refuses a page that does not carry it. The page
now reads: "No trajectory is decimated: every trajectory is at decimation_stride 1, so a viewer
shows all of its n_frames_total frames." With any stride above 1 it names each kind and its
strides. Helper tests cover both cases, each with its failing case (the gate refusing the
sentence once the data no longer matches).

Rebuild, nothing edited by hand: `git rm -r tests/candidate_outputs/v0.7.0/review` in its own
commit `bcdad1d` (44 files, only that path); the old scratch tree was **moved aside**, per the
lead's ruling in the brief, to `E/v070-slice13/review-iter1` (its build report and M12 folder to
`review_report-iter1.json` and `m12-iter1`), so both roots were absent before the run. Against
`review-iter1`, only the root `index.html` and `MANIFEST.sha256` differ; the 42 sub-bundle files
are byte-identical.

`E` = `~/.hacf/eta-rxncat-hacf/evidence`, `P` = `E/v070-slice13/proof`.

## Lead ruling A on the network-reference scan (row qitem-20261126131940-8fe50cb7)

The SPEC's literal scan cannot pass on the shipped assets. Per ruling A: literal `http:`, `https:`,
`ws:`/`wss:` and `//host` scan on every eta-written file (root `index.html`, every
`MANIFEST.sha256`, each sub-bundle `index.html` and `run_data.json`, `eta-view.js` with only
`http://www.w3.org/2000/svg` exempt); `3Dmol-min.js` and `LICENSE-3Dmol.txt` byte-equal to
`src/eta_rxncat/review/assets` (not gated on counts); network `src=`/`href=` fails anywhere; CSP
meta with `connect-src 'none'` on every page; path, `$HOME`, username and hostname scans on every
file; sink scan excludes only `3Dmol-min.js`; M12 gates zero network requests.

Vendored literal hit counts (the same in all 7 sub-bundles): `3Dmol-min.js` http: 3, https: 12,
//host 1; `LICENSE-3Dmol.txt` http: 1, https: 1. The scan matches `ws:`/`wss:` at a word boundary:
the 4 plain `ws:` substrings in the 3Dmol file are the ends of the keys `rows:`/`esRows:`, not URLs.

## Coverage, per store

| store | records | bundled | covered (`==`) | runs | runs bundled | rows before/after |
|---|---|---|---|---|---|---|
| v070_enum.sqlite | 12 | 4 selectivity | 8 unit records | 8 | 8 | 368 / 368 |
| v070_fallback_graft_time_xtb.sqlite | 1 | 1 | 0 | 1 | 1 | 33 / 33 |
| v070_fallback_run_time_xtb.sqlite | 1 | 1 | 0 | 1 | 1 | 34 / 34 |
| v070_fallback_run_time_uma.sqlite | 1 | 1 | 0 | 1 | 1 | 34 / 34 |

Each store's file sha256 is also unchanged (`E/v070-slice13/review_report.json`). The covered
records are `v070_enum_{ethyl,npropyl}_{endo,exo}_{xtb,uma}.runrecord.json`.

## Engine calls, entries and gates

`Engine.evaluate` calls over the whole build: **0** (`counted_engine_calls()` around the in-process
`cli.main`). No `missing` trajectory, frequency or species in any sub-bundle; every trajectory has
frames. Cache hits are the store reads behind the entries below; the export has no stage metrics of
its own.

| sub-bundle (`.runrecord` suffix omitted) | candidate entries | trajectories | frequencies | build s | bytes | gates |
|---|---|---|---|---|---|---|
| v070_enum_ethyl_selectivity_uma | 2 | 61 | 25 | 1.21 | 2933562 | UMA reported 18/0 |
| v070_enum_ethyl_selectivity_xtb | 2 | 62 | 26 | 1.13 | 3087669 | GFN2 gated 18/0 |
| v070_enum_npropyl_selectivity_uma | 2 | 69 | 31 | 1.84 | 5687620 | UMA reported 18/0 |
| v070_enum_npropyl_selectivity_xtb | 2 | 67 | 29 | 1.29 | 5665151 | GFN2 gated 18/0 |
| v070_fallback_graft_time_xtb | 1 | 22 | 11 | 0.51 | 1491800 | GFN2 gated 9/0 |
| v070_fallback_run_time_xtb | 1 | 22 | 11 | 0.44 | 1491824 | GFN2 gated 9/0 |
| v070_fallback_run_time_uma | 1 | 22 | 11 | 0.43 | 1438321 | UMA reported 9/0 |

**Gate counts: GFN2 mechanics gates (gated) 54 pass / 0 fail. UMA gates (reported, not gated)
45 pass / 0 fail.** The UMA RunRecords carry plain `pass_bool` with no "reported" flag, and the UMA
candidate's `test_outcome` reads "passed" regardless (slice 12 audit); they are counted apart on
the root page and here, and never gate.

## Gates on the files as written (all pass)

- `sha256sum -c MANIFEST.sha256` exit 0 for the root and all 7 sub-bundles; each lists every other
  file (root 43, each sub-bundle 5). Root manifest sha256, scratch and copy:
  `aa923c9441b96f31282888b285b95173c3d5403e59fc2209993413c7fb3e7473`.
- Sizes: every sub-bundle <= 25 000 000 bytes (largest 5687620). Tree total **21839233** bytes,
  reported; the root page's footer figure 21795947 is the sum of the 7 sub-bundles (without the
  root index and manifest).
- 44 files scanned: host data none; network and sink scans as ruled; CSP meta on 8 of 8 HTML pages;
  embedded `run-data` bytes equal `run_data.json` in all 7.
- Fresh roots: both were absent before the run; the harness refuses a non-empty one and wipes
  nothing (helper tests). Copy: 44 files, each hashed against the scratch manifest as written,
  created exclusively, never read back. Also checked without reading candidate contents:
  `git ls-tree -r e0a4988` blob ids equal `git hash-object` of the 44 scratch files.

## M10: decimation strides (read from each `run_data.json` file)

**Every one of the 325 trajectories is at stride 1**; no `ts_search` above 2, no stop.
`kind: count (n_frames_total min-max)`, all stride 1:

| sub-bundle | pre_relax | ts_search | endpoint_opt |
|---|---|---|---|
| ethyl uma | 22 (9-85) | 21 (1-41) | 18 (10-23) |
| ethyl xtb | 22 (8-113) | 22 (1-33) | 18 (9-24) |
| npropyl uma | 22 (11-464) | 22 (2-13) | 25 (10-32) |
| npropyl xtb | 22 (12-674) | 22 (2-14) | 23 (9-32) |
| graft_time xtb | 11 (8-33) | 11 (1-33) | - |
| run_time xtb | 11 (8-33) | 11 (1-33) | - |
| run_time uma | 11 (9-51) | 11 (1-7) | - |

## Host check, environment, resources (bundle E2E)

`E/v070-slice13/run.sh bundle-iter2 3600`: blocking `hostcheck.sh` (slice 12's copy; loops, exits 3 if
never free), then `/usr/bin/time -v timeout 3600 uv run --no-sync python -m pytest
tests/e2e/test_review_v070.py::test_v070_review_bundle -m e2e` from
`~/.cache/eta-rxncat-tmp/slice13/cwd`. Env: `ETA_RXNCAT_ACCEPTANCE=1`,
`ETA_RXNCAT_V070_EVIDENCE=E`, `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`P/bundle-iter2.env`, HEAD
bcdad1d: the code of `ea76693` with the old candidates removed). Verdict immediately before:
`avail=13G gpu=0% gpu_apps=0 heavy=0 eta=0`, with no process at >=100 % CPU or >=2 GiB at any
nice. Exit 0, 1 passed, wall 8.5 s, user+sys 90 s, max RSS 148752 kB.
Scratch cwd empty and no `HT*` in the repo afterwards.

## M12 on the real scratch tree (`proof/m12/`)

Driver `proof/m12/m12_driver.py.txt`, throwaway Playwright 1.65.2 venv under TMPDIR,
`python -I m12_driver_v070.py <scratch tree> <evidence>`, rerun unchanged on the rebuilt tree
(new venv, same versions), host check first (`P/m12-iter2.hostcheck`), exit 0.
From `file://` at the root index, each link opened.

| browser | checks | TS modes animated | trajectory plays | pages | console errors | network |
|---|---|---|---|---|---|---|
| Chrome 158.0.8127.36 (installed, headless, SwiftShader) | 581 pass / 0 fail | 120 / 120 | 409 / 409 | 7 | none | `file:` only |
| Playwright Firefox 159.0 (headless, webgl.force-enabled) | 581 pass / 0 fail | 120 / 120 | 409 / 409 | 7 | none | no request event |

All 120 TS frequency entries (members and every other searched sample) have exactly one imaginary
mode. 409 plays cover the 325 trajectories: the 84 endpoint trajectories of the selectivity candidates
are listed once under each of the two pathways. "Plays" = Play advances the readout (skipped for a one-frame
trajectory), the slider reaches the last frame and the plot marker follows. Negative controls
(CSP block reported; console error and http request caught) pass. Playwright Firefox reports no
`file:` loads, so its network log is empty by design.
**Mozilla release Firefox: not run** (optional, TJ's call). Not proven: headed rendering, hardware
WebGL, Safari.

## Acceptance record

`docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`, written by
`uv run --no-sync python tests/e2e/acceptance_record_v070.py E
missions/release-0.7.0/slices/12-fallback-e2e/proof/12-execute.md P/full-pytest-iter2.log 0
docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` (exit 0). 8 G7 units, 4 selectivity scores, 3 G8
constructs; 15 engine commands exit 0 with 1 passed, 0 skipped each; default suite 2593 passed, 0
skipped (at e0a4988); 1 stall, 600.005 s; bundle path and root manifest sha256. It cross-checks
slice 11's `table.md` (members, stalls, time lost, cap, dG) and slice 12's proof table (merges,
G_pathway) against the records and refuses a disagreement, and refuses any input under
`tests/candidate_outputs`. No verdict (slice 14's). Test:
`tests/e2e/test_acceptance_record_v070.py`.

## `git show --stat e0a4988` (candidate-only)

`44 files changed, 7389 insertions(+)`, all under `tests/candidate_outputs/v0.7.0/review/`:
`MANIFEST.sha256`, `index.html`, and for each of the 7 sub-bundles `MANIFEST.sha256`,
`index.html`, `run_data.json`, `assets/{3Dmol-min.js,LICENSE-3Dmol.txt,eta-view.js}`. From the
command output; no candidate file was opened.

## Commands and exit codes (fix round; every one under `timeout 3600` except `git`, `mv`, `cp`)

| command | at | exit | result |
|---|---|---|---|
| `hyper_spec.py progress --event executing`; `hyper_codegraph.py index` | fb74dd0 | 0, 0 | `index: ok` |
| `ruff check .`, format check (with the excludes), `mypy` | pre-commit of ea76693 | 0, 0, 0 | 734 files; 91 sources |
| the two slice oracle test files (pre-commit) | pre-commit of ea76693 | 0 | 30 passed |
| `E/v070-slice13/run.sh bundle-iter2 3600` | bcdad1d | 0 | 1 passed |
| M12 driver (Chrome, Firefox) | e0a4988 | 0 | total failed 0 |
| `uv sync --locked` | e0a4988 | 0 | |
| `ruff check .`, format check, `mypy` | e0a4988 | 0, 0, 0 | |
| `pytest tests/e2e/test_v070_inputs.py` | e0a4988 | 0 | |
| `pytest tests/e2e/test_acceptance_record_v070.py`; `.../test_review_v070_helpers.py` | e0a4988 | 0, 0 | 5; 25 passed |
| `uv sync --locked --no-dev` (`.venv-runtime`) + base licence gate | e0a4988 | 0 | 13 packages, 0 failures |
| `uv run pytest` (full; `ETA_RXNCAT_XTB` exported) | e0a4988 | 0 | 2593 passed, 196 deselected, 560.7 s |
| record writer | e0a4988 | 0 | only suite count, root manifest sha and tree total changed |
| `hyper_spec.py progress --event executed` | | 0 | |

First-build commands are in the earlier version of this file (`33b9212`). Logs: `P/*-iter2*`.

## Ledger

`hyper_ledger.py ensure-node --from-spec <slice>/SPEC.md` exit 0, **no change** (globs skipped, the
node already holds `tests/e2e/**` and `tests/candidate_outputs/v0.7.0/**`; the record and ledger
paths are owned by other nodes). `eta_rxncat_species_runner` description stays at 2000/2000.
`hyper_codegraph.py index` `index: ok`, then `hypergraph_updater.py --from-diff 9b3101e --apply
--slice OPR.0.7.0.13 --json` **once**, exit 0: nodes `eta_rxncat_scaffold`,
`eta_rxncat_species_runner` dirty; radius adds `eta_rxncat_selectivity`;
`lore_stale_candidates: []`. `unmapped`: the mission NOTES/PROGRESS and slice 13
PROGRESS/SPEC, `proof/m12/**`, and the untracked `spec/active`, `spec/archive`, `spec/process`
paths (names only in the updater output; not opened).

Fix round: the updater was **not** rerun and the ledger not touched; the fix changes only
`tests/e2e/**` (node `eta_rxncat_species_runner`, already flagged dirty).

## Deviations and notes for the audit

1. Network-reference scan per lead ruling A (above).
2. `<sub>` is the record's Python file stem, so it ends in `.runrecord`.
3. The evidence root comes from `ETA_RXNCAT_V070_EVIDENCE` (no rig path in the repo); the E2E also
   carries the `acceptance` marker.
4. Beyond the row count, the harness also gates each store file's sha256 as unchanged.
5. Before the code commit, one engine-free **dry build** ran from the same harness into
   `$TMPDIR/slice13/dry/review` (host check free first; no candidate write; stores unchanged) to
   find gate failures before the one-shot official run. It passed with the same root manifest sha as the first official build.
6. Fixed (U1, above).
7. First build only: the pre-commit `ruff`, `mypy` and `uv sync` had no explicit `timeout`. The fix
   round used `timeout 3600`.
8. The writer exports only the record's samples, so a template that fell through has nothing in
   the bundle. Run-time rank 1 `TS1a_x__ethyl` (both run-time runs, GFN2 and
   UMA) **was pre-relaxed** (core-frozen; one `constrained_preopt` row per store, 8 frames GFN2, 10
   UMA, equal to its attributed engine calls) and then fell through on the face check of the relaxed
   seed (`ts_fallback.py:341-351`). **No TS search or frequency ran on it** (0 ts_opt/frequency
   calls; no such rows in the stores). That is the only store row outside the bundle in each
   run-time store; the graft-time store has none (rank 1 was refused at graft). The audit report
   cites `ts_ensemble.py:322-334` and a seed record; that later check did not fire here.
9. The rebuild ran at `bcdad1d`, whose code equals `ea76693`.

## Phase 3 row draft (the LEAD sends it: `advisor-lead@kernel`, tag `question-for-tj`)

**Summary:** eta v0.7.0 Phase 3: your visual audit of the review bundle (promote or findings)

**Open it:** double-click
`/home/tjmustard/PROJECTS/eta-rxncat/tests/candidate_outputs/v0.7.0/review/index.html`, then each
row's link (7 rows). Offline; no server.

**Check:**
- each TS has exactly one imaginary mode and it moves the forming bonds (the viewer draws bonds by
  distance, so a stretched bond can disappear at the far phase);
- each optimization path is sensible (Play / slider);
- R sits anti to the diene;
- the fallbacks read right (Fallbacks cell).

**Packet** (values from the run records):
- `orientation_mismatch` exclusions, 3-7 per unit (reported, not gated): GFN2 ethyl endo 4, exo 4,
  n-propyl endo 3, exo 7; UMA ethyl endo 5, exo 3, n-propyl endo 3, exo 7; fallbacks 4 (graft_time
  GFN2), 4 (run_time GFN2), 5 (run_time UMA).
- one `gate_failed:forming_overlap`: ethyl endo GFN2 (the two GFN2 fallback units compute the same
  ethyl endo ensemble and show the same exclusion).
- one UMA stall: ethyl exo, 600.0 s pre-relax timeout, cap not reached.
- dG‡ is the **ensemble** barrier (G_pathway − G_reactants), not the seed's. kcal/mol (1 M),
  GFN2 / UMA: ethyl endo 13.56 / 20.24, exo 17.49 / 24.81; n-propyl endo 13.86 / 20.44, exo
  18.09 / 25.41.
- ddG‡, endo major: ethyl 3.93 / 4.57, n-propyl 4.23 / 4.97 kcal/mol (GFN2 / UMA).
- fallback, **graft time** (GFN2; `v070_fallback_graft_time_xtb.runrecord.json`): the graft of
  declared rank-1 `TS1a_n_cp_h` is refused with exactly `alignment_rmsd`; declared rank-2 `TS1a_n`
  grafts `ok`; the fallback record holds one attempt (`TS1a_n__ethyl`, renumbered rank 1,
  `chosen`), so no fall-through appears in it. The view's "Rank used" shows **1** (renumbered), not
  the declared 2; the Fallbacks cell lists the graft refusal. Gates 9/9; 3 members.
- fallback, **run time** (`v070_fallback_run_time_{xtb,uma}.runrecord.json`; GFN2 gated, UMA
  reported): rank 1 `TS1a_x__ethyl` `fell_through`, `seed:face_mismatch_pathway`; rank 2
  `TS1a_n__ethyl` `chosen`. Chosen ensemble: GFN2 3 members, gates 9/9, G_pathway −28.2208485 Eh;
  UMA 3 members, 9/9 reported, G_pathway −389.1076145 Eh.
- **not in the bundle:** the run-time rank-1 seed `TS1a_x__ethyl` **was optimized** (a core-frozen
  pre-relaxation, 8 frames GFN2, 10 UMA) before it fell through on the face check; that trajectory
  is in the store but not in the bundle, because the bundle holds only the chosen template's
  samples. No TS search ran on it. The graft-time rank 1 has no trajectory (refused at graft).
- gates: GFN2 54/0 (gated); UMA 45/0 (reported, not gated). No trajectory is decimated. A Mozilla
  release Firefox was not run (optional, your call).

**Only you promote.** Nothing under `tests/candidate_outputs/v0.7.0/` has been promoted.

A. The audit holds; promote (you say which files). (Recommended if your visual check finds nothing.)
B. Findings: list them by row and TS or trajectory; nothing is promoted.
C. Hold: you want more before deciding (say what, e.g. the release-Firefox run).
