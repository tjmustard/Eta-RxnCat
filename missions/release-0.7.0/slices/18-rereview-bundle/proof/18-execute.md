---
slice: OPR.0.7.0.18
candidate_sha: 5af5105
artifact_type: guard
verdict: CLEAR
money_evidence: bundle 7 sub-bundles, 0 engine calls, G15 and 3 known answers
  pass; M12 759/0 both browsers; record re-derived, values unchanged; full
  pytest 2674 passed
---

# Execute evidence: 18-rereview-bundle (OPR.0.7.0.18) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type;
this is builder evidence and the audit writes the QA verdict.

Start `cd2a91e`. Commits: `fb32253` code (`tests/e2e/**` only); `1abbe17` candidate-only (the
bundle); `79b66a5` M12 evidence and a checkpoint note (usage limit; the note is removed with this
proof); `4bd2cf0` acceptance record; `5af5105` ledger flag, progress, field note. No `src/` change,
no engine run, nothing promoted, pushed or tagged.

`E` = `~/.hacf/eta-rxncat-hacf/evidence`, `S` = `E/v070-replan7-runs` (the named source root,
`review_v070.SOURCE_ROOT`), `D` = `E/v070-slice18`.

## What changed

- `review_v070.py`: sources are the records and four stores of `S`; `SLICE11`/`SLICE12` removed;
  `Source.slice_name` is now `group` (`G7 enumeration` / `G8 fallback`; root index column "Source").
  Every slice 13 gate is unchanged. `build_review` runs the G15 gates before the copy.
- `review_g15.py` (new): the G15 gates and both known answers, read from each scratch
  `run_data.json` and static `index.html` and compared with the record.
- `test_review_v070.py`: report and scratch root under `S`.
- `acceptance_record_v070.py`: reads `S`; cross-checks every dG‡, ddG‡, `G_pathway`, `seed_clash`
  index list, `bond_changed` and stall count against slice 17's proof tables (the slice 11/12 table
  checks are removed); adds the per-unit clash and bond counts and the `replan_7` block. Argument
  count unchanged; the second argument is now slice 17's proof. Slice 13's record is read from
  `S/proof/acceptance-slice13.json`, the bytes of
  `git show cd2a91e:docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` (sha256
  `11d2408ac3252a6c118c6011ca0aa155f48848c9dc02260650919cb411894bcb`).
- Both helper test files updated, with a failing case for each new gate.

## Bundle E2E (`D/run.sh bundle 3600`, at `fb32253`)

Blocking host check first (`D/proof/bundle.hostcheck`): `avail=13G gpu=0% gpu_apps=0 heavy=0
eta=0`, floor 4 GiB (**lead ruling in this slice's brief, `qitem-20261126211155-c9f544cc688d1c35`:
4 GiB suffices since no engine loads**; the SPEC says 12, and 13 were free). Env:
`ETA_RXNCAT_ACCEPTANCE=1`, `ETA_RXNCAT_V070_EVIDENCE=E`,
`TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`; scratch cwd, empty afterwards, no `HT*` in the
repo. Exit 0, 1 passed, wall 6.0 s, max RSS 127920 kB. Report: `S/review_report.json`.

### Coverage and rows, per store

| store | records | bundled | runs | rows before/after | file sha256 (unchanged) |
|---|---|---|---|---|---|
| v070_enum.sqlite | 12 | 4 selectivity | 8/8 | 368/368 | `665cdfd8…` |
| v070_fallback_graft_time_xtb.sqlite | 1 | 1 | 1/1 | 33/33 | `0c03402b…` |
| v070_fallback_run_time_xtb.sqlite | 1 | 1 | 1/1 | 34/34 | `2c04785e…` |
| v070_fallback_run_time_uma.sqlite | 1 | 1 | 1/1 | 34/34 | `634fef6c…` |

`Engine.evaluate` calls: **0**.

### R34 gates (all pass)

- Manifests: root lists 43 files, each of 7 sub-bundles 5; `sha256sum -c` clean. Root manifest
  sha256 `5ad4aa3b9a8dc8cfbb42ea07c73b5311c27826ef276b52d3130de1a4378332ec`.
- Sizes (bytes): ethyl uma 1935463, ethyl xtb 1972761, npropyl uma 2461061, npropyl xtb 2580682,
  graft_time 1005264, run_time xtb 1005288, run_time uma 983606; total 11977758.
- No `missing` entry; every trajectory has frames; embedded bytes equal `run_data.json`.
- M10: all 220 trajectories (84 endpoint_opt, 68 pre_relax, 68 ts_search) at stride 1.
- 44 files scanned: host data, network (lead ruling A of slice 13; vendored literal counts reported)
  and sink scans clean; CSP on 8 of 8 pages.
- Mechanics gates: GFN2 54 pass / 0 fail (gated); UMA 45 / 0 (reported, not gated).
- Fresh roots: `S/review` was absent before the run; the harness refuses a non-empty root.

### G15 gates (all pass)

Every sample and endpoint row has a disposition as the record lists it; none is `not_recorded`;
every row with a frequency has a `TSIdentity` (TS) and sits in its group under a heading naming it.

| sub-bundle | TS used / not | rowless samples | minima used / not |
|---|---|---|---|
| ethyl uma | 6 / 7 | 9 | 6 / 2 |
| ethyl xtb | 6 / 7 | 9 | 6 / 2 |
| npropyl uma | 7 / 5 | 10 | 10 / 8 |
| npropyl xtb | 7 / 5 | 10 | 10 / 4 |
| graft_time xtb | 3 / 3 | 5 | none |
| run_time xtb | 3 / 3 | 5 | none |
| run_time uma | 3 / 3 | 5 | none |

**No TS block fails its identity (68 of 68 pass), so no identity banner is on the real page.** The
gate requires a banner exactly when an identity fails; a stub test removes it and the gate fails.

Known answers:

1. Ethyl endo GFN2 sample 6 (ethyl xtb, graft_time, run_time xtb): "Sample 6 (fragment_embed:6,
   template TS1a_n__ethyl): excluded: seed_clash C4–H21 0.438 Å", in Not used, no frequency row,
   distance 0.438032688 Å, ratio 0.409376343902.
2. `071c077d750a` (npropyl uma, endo and exo): in Not used, "superseded by push →
   …ee86975197d1…"; successor `ee86975197d1` is "dropped: duplicate_after_push", equal to the
   record's species-runner kind and reason.

### Candidate commit

`git show --stat 1abbe17`: 44 files, 8796 insertions, all under
`tests/candidate_outputs/v0.7.0/review/`. The 44 index blob ids equalled
`git hash-object` of the 44 scratch files before the commit. No candidate file was opened.

## M12 on the real scratch tree (`proof/m12/`)

Driver `proof/m12/m12_driver.py.txt` (slice 13's, plus dispositions, grouping, banners and the known
answers), throwaway Playwright 1.65.2 venv under TMPDIR (removed afterwards), `python -I`, from
`file://` at the root index. Host check `D/proof/m12.hostcheck`. Exit 0.

| browser | checks | TS modes animated | plays | pages | disposition options | console errors | network |
|---|---|---|---|---|---|---|---|
| Chrome 158.0.8127.36 (installed, headless) | 759 / 0 | 68 / 68 | 304 / 304 | 7 | 116 | none | `file:` only |
| Playwright Firefox 159.0 (headless) | 759 / 0 | 68 / 68 | 304 / 304 | 7 | 116 | none | no request event |

Negative controls pass. Screenshots of the three known answers (static and JS) are in both browser
folders; I viewed three Chrome ones (sample 6 static, `071c` static, successor JS). Not proven:
headed rendering, hardware WebGL, release Firefox, Safari.

## Acceptance record

`uv run --no-sync python tests/e2e/acceptance_record_v070.py E
missions/release-0.7.0/slices/17-rerun-units/proof/17-execute.md D/proof/full-pytest.log 0
docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`, exit 0, no verdict. 8 G7 units, 4 scores, 3 G8
constructs; 15 engine commands exit 0, 1 passed, 0 skipped; suite 2674 passed. `replan_7`: Q-R7a A,
Q-R7b A, cut 1.3 x covalent sum, rejected ratios 0.409 to 1.286; reasons changed on all 11 units to
`seed_clash`; stalls 1 (600.005 s) to 0; **no dG‡, ddG‡, `G_pathway`, member or merge count
changed**; root manifest `aa923c94…` to `5ad4aa3b…`. Writer test:
`tests/e2e/test_acceptance_record_v070.py`.

## Commands and exit codes

Every uv command under `timeout 3600`.

| command | at | exit | result |
|---|---|---|---|
| `hyper_spec.py progress --event executing`; `hyper_codegraph.py index` | cd2a91e | 0, 0 | `index: ok` |
| ruff check, format (excluding form), mypy | pre-commit of fb32253 | 0, 0, 0 | 812 files; 91 sources |
| the two oracle test files | pre-commit of fb32253 | 0 | 59 passed |
| `uv sync --locked` | fb32253 | 0 | |
| `D/hostcheck.sh … 4`; dry build (`D/dry.py` into TMPDIR) | before fb32253 | 0, 0 | all gates, same manifest sha |
| `D/run.sh bundle 3600` | fb32253 | 0 | 1 passed |
| M12 driver | 1abbe17 | 0 | 0 failed |
| host check; `uv sync --locked` | 79b66a5 | 0, 0 | |
| `ruff check .`; `ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`; `mypy` | 79b66a5 | 0, 0, 0 | 813 files; 91 sources |
| `uv run pytest` (full, `ETA_RXNCAT_XTB` exported) | 79b66a5 | 0 | 2674 passed, 196 deselected, 278.04 s |
| `pytest test_acceptance_record_v070.py`; `test_review_v070_helpers.py` | 79b66a5 | 0, 0 | 25; 34 passed |
| record writer | 79b66a5 | 0 | |
| `ensure-node --from-spec`; `hyper_ledger.py validate` | 4bd2cf0 | 0, 0 | no change; `validate: ok` |
| `hyper_codegraph.py index`; `hypergraph_updater.py --from-diff cd2a91e --apply --slice OPR.0.7.0.18 --json` (once) | 4bd2cf0 | 0, 0 | below |
| `hyper_spec.py progress --event executed`; `hyper_lore.py note` | 4bd2cf0 | 0, 0 | |

Logs: `D/proof/`.

## Ledger

`ensure-node`: no change (both globs skipped; the record and ledger paths are other nodes'); the
node's files are as before, description untouched (1997/2000). Updater: dirty
`eta_rxncat_scaffold`, `eta_rxncat_species_runner`; radius adds `eta_rxncat_selectivity`;
`lore_stale_candidates` empty. `unmapped`: mission and slice files, `proof/**`, a `.claude`
settings backup and untracked `spec/` paths listed by name (none opened). Full JSON:
`D/proof/updater.json`.

## For the auditor to rule on

1. One command of mine included a listing of `tests/candidate_outputs/v0.7.0` and was refused by the
   permission layer; nothing in it ran. I reran it without that part.
2. A dry build into TMPDIR ran before the official one-shot run, after its own host check.
3. M12's host check refused three times with one heavy process (the one I inspected: another
   project's python fuzzer, `oin-v1-w7-a`); a loop waited until the host was free. Slice 18's host check is slice 17's script, floor 4.
4. A usage limit paused the seat between M12 and the full check. No command was interrupted.
5. `S/proof/acceptance-slice13.json` is a new file in the source root (see "What changed").
6. The format oracle ran only in the excluding form (seat rule).
7. `.claude/settings.local.json.bak-pretreg-20261126` and `spec/` untracked paths are not mine and
   were not staged.

## Phase 3 re-review row draft (the LEAD sends it: `advisor-lead@kernel`, tag `question-for-tj`)

**Summary:** eta v0.7.0 Phase 3 re-review: the fixed bundle (re-promote, findings or hold)

**Open it:** double-click
`/home/tjmustard/PROJECTS/eta-rxncat/tests/candidate_outputs/v0.7.0/review/index.html`, then each
row's link (7 rows). Offline; no server.

**Since your first review:** a seed clash check (a start with a pair at least 3 bonds apart closer
than 1.3 x the covalent radii sum is rejected, recorded and keeps its slot: your A + A) and a bond
change check; a site that labels every row used or not used and why, with each TS's identity
numbers; all units rerun.

**Your two findings:**
- TS1a_n__ethyl sample 6 (the clash). Open `v070_enum_ethyl_selectivity_xtb`, candidate ethyl,
  pathway endo, "Not used": "Sample 6 … excluded: seed_clash C4–H21 0.438 Å". It now has no TS
  search and no frequencies. The two GFN2 fallback rows show the same line.
- The pre-push minimum `071c077d750a`. Open `v070_enum_npropyl_selectivity_uma`, candidate
  npropyl, "Not used": headed "superseded by push → ee86975197d1…", with its warning "Minimum has 1
  imaginary mode(s); expected 0." Its successor `ee86975197d1` is also not used, "dropped:
  duplicate_after_push" (the pushed minimum duplicates one already kept).

**What to know:**
- Rejected, merged and superseded rows are grouped apart under "Not used" and labelled.
- Every TS shown passes its identity check, so no identity-failure banner appears on this bundle.
- `seed_clash` per unit (GFN2 / UMA): ethyl endo 5 / 5, exo 4 / 4; n-propyl endo 3 / 3, exo 7 / 7;
  fallbacks: graft_time 5 (GFN2), run_time 5 / 5. These replace the earlier `orientation_mismatch`,
  `forming_overlap` and stall exclusions. The 600 s UMA ethyl exo stall was a clashing sample; there
  are now 0 stalls. No `bond_changed`.
- **Numbers are unchanged** from what you promoted (9fdba68). dG‡, kcal/mol, GFN2 / UMA: ethyl endo
  13.56 / 20.24, exo 17.49 / 24.81; n-propyl endo 13.86 / 20.44, exo 18.09 / 25.41. ddG‡ (endo
  major): ethyl 3.93 / 4.57, n-propyl 4.23 / 4.97.
- Fallback, graft time (GFN2): declared rank-1 `TS1a_n_cp_h` is refused `alignment_rmsd`; "Rank
  used" shows the renumbered **1** (not the declared 2) and the Fallbacks cell lists the refusal.
- Fallback, run time (GFN2, UMA): rank 1 `TS1a_x__ethyl` fell through
  `seed:face_mismatch_pathway`, rank 2 `TS1a_n__ethyl` chosen. The bundle holds only the chosen
  template's samples.
- Gates: GFN2 54 / 0 (gated); UMA 45 / 0 (reported, not gated).
- Checked in headless Chrome and Playwright Firefox; no release Firefox, no headed run.

**Re-promotion** replaces the 30 files of 9fdba68 in `tests/fixtures/v0.7.0/` with the 30 new
`v070_*` candidates (commit `45c52d4`). **Only you promote.** Slice 14 (the verdict) waits for it.

A. Re-promote all 30. (Recommended if your visual check finds nothing.)
B. Findings: list them by row and TS or minimum; nothing is promoted.
C. Hold: you want more first (say what).
