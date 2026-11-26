---
slice: OPR.0.7.0.13
candidate_sha: 5b6bf1a
artifact_type: guard
verdict: CLEAR
money_evidence: 7 sub-bundles gate clean with 0 engine calls; M12 581/581 in
  Chrome and Playwright Firefox; M10 all stride 1; full pytest 2591 passed
---

# Execute evidence: 13-review-bundle-and-record (OPR.0.7.0.13) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type;
this is builder evidence and the audit writes the QA verdict.

Start `9b3101e`. Code commit `43de81b` (the bundle E2E, the full suite the record reads, and the
record derivation ran at it). Candidate-only commit `5b6bf1a`. Record and progress commit
`d7a4e86`. The ledger flag and this proof are in the commit after it. No `src/` change. No engine
ran. Nothing promoted, pushed or tagged.

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
| v070_enum_ethyl_selectivity_uma | 2 | 61 | 25 | 0.64 | 2933562 | UMA reported 18/0 |
| v070_enum_ethyl_selectivity_xtb | 2 | 62 | 26 | 0.27 | 3087669 | GFN2 gated 18/0 |
| v070_enum_npropyl_selectivity_uma | 2 | 69 | 31 | 1.04 | 5687620 | UMA reported 18/0 |
| v070_enum_npropyl_selectivity_xtb | 2 | 67 | 29 | 0.90 | 5665151 | GFN2 gated 18/0 |
| v070_fallback_graft_time_xtb | 1 | 22 | 11 | 0.18 | 1491800 | GFN2 gated 9/0 |
| v070_fallback_run_time_xtb | 1 | 22 | 11 | 0.09 | 1491824 | GFN2 gated 9/0 |
| v070_fallback_run_time_uma | 1 | 22 | 11 | 0.08 | 1438321 | UMA reported 9/0 |

**Gate counts: GFN2 mechanics gates (gated) 54 pass / 0 fail. UMA gates (reported, not gated)
45 pass / 0 fail.** The UMA RunRecords carry plain `pass_bool` with no "reported" flag, and the UMA
candidate's `test_outcome` reads "passed" regardless (slice 12 audit); they are counted apart on
the root page and here, and never gate.

## Gates on the files as written (all pass)

- `sha256sum -c MANIFEST.sha256` exit 0 for the root and all 7 sub-bundles; each lists every other
  file (root 43, each sub-bundle 5). Root manifest sha256, scratch and copy:
  `fb307c7daeb58594a0a0f18fa9b84475dae8757c3e2ec8f923885e6c2e483147`.
- Sizes: every sub-bundle <= 25 000 000 bytes (largest 5687620). Tree total **21839280** bytes,
  reported; the root page's footer figure 21795947 is the sum of the 7 sub-bundles (without the
  root index and manifest).
- 44 files scanned: host data none; network and sink scans as ruled; CSP meta on 8 of 8 HTML pages;
  embedded `run-data` bytes equal `run_data.json` in all 7.
- Fresh roots: both were absent before the run; the harness refuses a non-empty one and wipes
  nothing (helper tests). Copy: 44 files, each hashed against the scratch manifest as written,
  created exclusively, never read back. Also checked without reading candidate contents:
  `git ls-tree -r 5b6bf1a` blob ids equal `git hash-object` of the 44 scratch files.

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

`E/v070-slice13/run.sh bundle 3600`: blocking `hostcheck.sh` (slice 12's copy; loops, exits 3 if
never free), then `/usr/bin/time -v timeout 3600 uv run --no-sync python -m pytest
tests/e2e/test_review_v070.py::test_v070_review_bundle -m e2e` from
`~/.cache/eta-rxncat-tmp/slice13/cwd`. Env: `ETA_RXNCAT_ACCEPTANCE=1`,
`ETA_RXNCAT_V070_EVIDENCE=E`, `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`P/bundle.env`, HEAD
43de81b). Verdict immediately before: `avail=14G gpu=0% gpu_apps=0 heavy=0 eta=0`. The check's
all-nice listing shows one hakf-rig `pytest` at nice 10, 113 % CPU: listed, not counted by the
inherited heavy filter (nice < 10). Exit 0, 1 passed, wall 4.6 s, user+sys 53 s, max RSS 143780 kB.
Scratch cwd empty and no `HT*` in the repo afterwards.

## M12 on the real scratch tree (`proof/m12/`)

Driver `proof/m12/m12_driver.py.txt`, throwaway Playwright 1.65.2 venv under TMPDIR,
`python -I m12_driver_v070.py <scratch tree> <evidence>`, host check first, exit 0.
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
missions/release-0.7.0/slices/12-fallback-e2e/proof/12-execute.md P/full-pytest.log 0
docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` (exit 0). 8 G7 units, 4 selectivity scores, 3 G8
constructs; 15 engine commands exit 0 with 1 passed, 0 skipped each; default suite 2591 passed, 0
skipped (at 43de81b); 1 stall, 600.005 s; bundle path and root manifest sha256. It cross-checks
slice 11's `table.md` (members, stalls, time lost, cap, dG) and slice 12's proof table (merges,
G_pathway) against the records and refuses a disagreement, and refuses any input under
`tests/candidate_outputs`. No verdict (slice 14's). Test:
`tests/e2e/test_acceptance_record_v070.py`.

## `git show --stat 5b6bf1a` (candidate-only)

`44 files changed, 7389 insertions(+)`, all under `tests/candidate_outputs/v0.7.0/review/`:
`MANIFEST.sha256`, `index.html`, and for each of the 7 sub-bundles `MANIFEST.sha256`,
`index.html`, `run_data.json`, `assets/{3Dmol-min.js,LICENSE-3Dmol.txt,eta-view.js}`. From the
command output; no candidate file was opened.

## Commands and exit codes

| command | at | exit | result |
|---|---|---|---|
| `hyper_codegraph.py index` | Start | 0 | `index: ok` |
| `hyper_spec.py progress --event executing` (detail: Start, `escape_tracking: v1`) | Start | 0 | |
| `uv run pytest tests/e2e/test_review_v070_helpers.py` / `test_acceptance_record_v070.py` (iterating) | work tree | 1, then 0 | one wrong `match=` string fixed; 28 passed |
| `uv run ruff check .`, `ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`, `mypy` | pre-commit | 0, 0, 0 | 733 files; 91 sources |
| `uv sync --locked` | 43de81b | 0 | |
| `uv run pytest tests/e2e/test_v070_inputs.py -q` | 43de81b | 0 | 18 passed |
| `uv run pytest` the two new test files | 43de81b | 0 | 28 passed |
| `uv run pytest` (full; `ETA_RXNCAT_XTB` exported) | 43de81b | 0 | 2591 passed, 196 deselected |
| `uv sync --locked --no-dev` into `.venv-runtime`, then `tools/licence_gate.py --profile base` | 43de81b | 0 | 13 packages, 0 failures |
| `E/v070-slice13/run.sh bundle 3600` | 43de81b | 0 | 1 passed |
| M12 driver (Chrome, Firefox) | 43de81b | 0 | total failed 0 |
| record writer | 43de81b | 0 | |
| `ruff check`, format check, `mypy` | d7a4e86 | 0, 0, 0 | |
| the slice's two oracle pytest files | d7a4e86 | 0, 0 | 5 and 23 passed |
| `uv run pytest` (full, final) | d7a4e86 + the ledger flag uncommitted | 0 | 2591 passed, 196 deselected, 730.8 s (host load ~26) |
| `hyper_spec.py progress --event executed`; `hyper_spec.py lint <slice>` | | 0, 0 | `lint: ok` |

Logs: `P/` (`uv-sync`, `inputs`, `helpers`, `full-pytest`, `licence`, `bundle.*`, `m12.*`,
`oracle-*`, `final-pytest`, `dry.hostcheck`).

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

## Deviations and notes for the audit

1. Network-reference scan per lead ruling A (above).
2. `<sub>` is the record's Python file stem, so it ends in `.runrecord`.
3. The evidence root comes from `ETA_RXNCAT_V070_EVIDENCE` (no rig path in the repo); the E2E also
   carries the `acceptance` marker.
4. Beyond the row count, the harness also gates each store file's sha256 as unchanged.
5. Before the code commit, one engine-free **dry build** ran from the same harness into
   `$TMPDIR/slice13/dry/review` (host check free first; no candidate write; stores unchanged) to
   find gate failures before the one-shot official run. It passed with the same root manifest sha.
6. The root page's intro says trajectories are decimated to fit the budget; here none is (all
   stride 1, as each row states). Not rebuilt: the candidate root must not be wiped.
7. The pre-commit runs of `ruff`, `mypy` and `uv sync` had no explicit `timeout`; the pytest runs,
   the bundle E2E, M12 and the final checks used `timeout 3600`.
8. Fallback rank-1 attempts have no trajectory in the bundle (the records' samples are the chosen
   template's); they show in the view's Fallbacks cell.

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
- gates: GFN2 54/0 (gated); UMA 45/0 (reported, not gated). No trajectory is decimated. A Mozilla
  release Firefox was not run (optional, your call).

**Only you promote.** Nothing under `tests/candidate_outputs/v0.7.0/` has been promoted.

A. The audit holds; promote (you say which files). (Recommended if your visual check finds nothing.)
B. Findings: list them by row and TS or trajectory; nothing is promoted.
C. Hold: you want more before deciding (say what, e.g. the release-Firefox run).
