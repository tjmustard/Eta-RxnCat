---
slice: OPR.0.7.0.17
candidate_sha: 45c52d47fd3bc6843f701a78246cc710cff2517b
artifact_type: guard
verdict: CLEAR
money_evidence: 15/15 exit 0, 0 rows added, dG/ddG equal to fixtures, 53
  seed_clash as measured, 0 bond_changed, 0 stalls; ruff/mypy exit 0; full
  pytest 2660 passed
---

# Execute evidence: 17-rerun-units (OPR.0.7.0.17) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type.
This is builder evidence; the audit writes the QA verdict.

Start `f8fcd9b`. Code commit `defd982` (harness fix), old-candidate removal `e798c92`, fresh
candidates `45c52d4`. All 15 runs executed at HEAD `e798c92`.

## Gate and rulings

- Start gate: slices 15 and 16 audited; TJ Q-R7a = A and Q-R7b = A, advisor relay
  `qitem-20261126153756-49f5d76005956ea5` (as stated in the lead's brief). The Q-R7b B branch
  does not apply.
- Lead ruling `qitem-20261126195109-0246e7d8` (answers my row `qitem-20261126195041-2439d7a73d16682d`):
  MemAvailable floor 4 GiB for GFN2 and score commands, 12 GiB strict for UMA, GFN2 first, stop if a
  GFN2 command makes an engine call or its peak RSS exceeds 1 GiB. Neither happened.

## Store copies

State directory `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7-runs/` (new). Copies made with
`sqlite3 "file:<src>?mode=ro" ".backup '<dst>'"`.

- `v070-slice11/v070_enum.sqlite` -> `v070_enum.sqlite`
  - source sha256 `613751808b048e5c69b3388ea0adda46067b9e5b701ca1f8f066dcf98eba8ced` (after backup: same)
  - copy sha256 before runs `665cdfd85367483ba9cd2ca14e5868516978fc2cbd90da32b9a838abf70d5a18`
  - copy sha256 after runs `665cdfd85367483ba9cd2ca14e5868516978fc2cbd90da32b9a838abf70d5a18`
  - rows: source 368, copy before 368, after 368
- `v070-slice12/v070_fallback_graft_time_xtb.sqlite` -> `v070_fallback_graft_time_xtb.sqlite`
  - source sha256 `4ca1456c9a559f40535ce396105baa5b6877fd642e9572a410608852161c827a` (after backup: same)
  - copy sha256 before runs `0c03402bcaf6cf1f8a10eb8c7a41f8f69865018435c1687798aac15d502c71c0`
  - copy sha256 after runs `0c03402bcaf6cf1f8a10eb8c7a41f8f69865018435c1687798aac15d502c71c0`
  - rows: source 33, copy before 33, after 33
- `v070-slice12/v070_fallback_run_time_xtb.sqlite` -> `v070_fallback_run_time_xtb.sqlite`
  - source sha256 `c5fe92b0e58439d87ccdddd46593eabad9903c1e497d683d8391a8b07c185217` (after backup: same)
  - copy sha256 before runs `2c04785e308f87467733709f098505b74a0bb357291a98ca6bc3b81c6ffaeda0`
  - copy sha256 after runs `2c04785e308f87467733709f098505b74a0bb357291a98ca6bc3b81c6ffaeda0`
  - rows: source 34, copy before 34, after 34
- `v070-slice12/v070_fallback_run_time_uma.sqlite` -> `v070_fallback_run_time_uma.sqlite`
  - source sha256 `41ac713c65a9f9102e1a0f7d7b83339deba5c96e91ee777a2fa9a43a97917cd8` (after backup: same)
  - copy sha256 before runs `634fef6c64c3d6148dfc27c38335a29d34e659217c725c6362807a5fb2af2bc7`
  - copy sha256 after runs `634fef6c64c3d6148dfc27c38335a29d34e659217c725c6362807a5fb2af2bc7`
  - rows: source 34, copy before 34, after 34

Old evidence after all runs: `sha256sum -c proof/sources.sha256.before` from the evidence
directory, 12 of 12 OK (db, shm and wal of the four sources), exit 0.

## Runs

One pytest node per command through `run.sh` (scratch cwd, `/usr/bin/time -v`). Env in every
`proof/<tag>.env`: `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`,
`ETA_RXNCAT_ACCEPTANCE=1`, `ETA_RXNCAT_V070_REUSE_STORES=1`, `ETA_RXNCAT_V070_STATE=<state dir>`,
`TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`; every run left 0 files in the cwd. Timeouts: 5400
units, 3600 scores. UMA used `.venv-accept-uma` (editable on this tree's `src/`; its package
metadata reads 0.5.0). "checks" = host-check outputs kept; "blockers" = GPU apps / heavy / eta
processes in the passing check. "rows added" compares per-store row counts before and after.

| tag | checks | MemAvailable / floor | blockers | wall | peak RSS kB | exit | rows added | engine calls, new rows | gates |
|---|---|---|---|---|---|---|---|---|---|
| ethyl-endo-xtb | 4 | 10G / 4G | 0/0/0 | 0:03.22 | 158880 | 0 | 0 | 0/0, 0/0 | 9/9 |
| ethyl-exo-xtb | 1 | 10G / 4G | 0/0/0 | 0:02.44 | 159908 | 0 | 0 | 0/0, 0/0 | 9/9 |
| score-ethyl-xtb | 1 | 11G / 4G | 0/0/0 | 0:00.98 | 98828 | 0 | 0 | no engine | 3/3 |
| npropyl-endo-xtb | 2 | 9G / 4G | 0/0/0 | 0:04.13 | 166772 | 0 | 0 | 0/0, 0/0 | 9/9 |
| npropyl-exo-xtb | 2 | 9G / 4G | 0/0/0 | 0:02.50 | 167304 | 0 | 0 | 0/0, 0/0 | 9/9 |
| score-npropyl-xtb | 2 | 9G / 4G | 0/0/0 | 0:01.05 | 100696 | 0 | 0 | no engine | 3/3 |
| run-time-xtb | 2 | 9G / 4G | 0/0/0 | 0:02.74 | 158804 | 0 | 0 | 0/0, 0/0 | 9/9 |
| graft-time-xtb | 3 | 9G / 4G | 0/0/0 | 0:03.06 | 158992 | 0 | 0 | 0/0, 0/0 | 9/9 |
| ethyl-endo-uma | 51 | 12G / 12G | 0/0/0 | 2:43.61 | 8694180 | 0 | 0 | 0/0, 0/0 | 9/9 |
| ethyl-exo-uma | 3 | 15G / 12G | 0/0/0 | 2:46.48 | 8945148 | 0 | 0 | 0/0, 0/0 | 9/9 |
| score-ethyl-uma | 1 | 16G / 4G | 0/0/0 | 0:01.25 | 108144 | 0 | 0 | no engine | 3/3 |
| npropyl-endo-uma | 1 | 16G / 12G | 0/0/0 | 2:36.39 | 8759712 | 0 | 0 | 0/0, 0/0 | 9/9 |
| npropyl-exo-uma | 2 | 16G / 12G | 0/0/0 | 1:48.08 | 8985368 | 0 | 0 | 0/0, 0/0 | 9/9 |
| score-npropyl-uma | 1 | 18G / 4G | 0/0/0 | 0:00.79 | 109352 | 0 | 0 | no engine | 3/3 |
| run-time-uma | 3 | 16G / 12G | 0/0/0 | 1:59.67 | 8944504 | 0 | 0 | 0/0, 0/0 | 9/9 |

## Energies against `tests/fixtures/v0.7.0/` (exact float equality)

| record | pathway | quantity | new | fixture (9fdba68) | equal |
|---|---|---|---|---|---|
| v070_enum_ethyl_endo_xtb | endo | dG‡ | 13.560206712557633 | 13.560206712557633 | True |
| v070_enum_ethyl_exo_xtb | exo | dG‡ | 17.48896324308849 | 17.48896324308849 | True |
| v070_enum_ethyl_selectivity_xtb | endo | dG‡ | 13.560206712557633 | 13.560206712557633 | True |
| v070_enum_ethyl_selectivity_xtb | exo | dG‡ | 17.48896324308849 | 17.48896324308849 | True |
| v070_enum_ethyl_selectivity_xtb | endo/exo | ddG‡ | 3.9287565305308614 | 3.9287565305308614 | True |
| v070_enum_npropyl_endo_xtb | endo | dG‡ | 13.86081776428437 | 13.86081776428437 | True |
| v070_enum_npropyl_exo_xtb | exo | dG‡ | 18.086049482990774 | 18.086049482990774 | True |
| v070_enum_npropyl_selectivity_xtb | endo | dG‡ | 13.86081776428437 | 13.86081776428437 | True |
| v070_enum_npropyl_selectivity_xtb | exo | dG‡ | 18.086049482990774 | 18.086049482990774 | True |
| v070_enum_npropyl_selectivity_xtb | endo/exo | ddG‡ | 4.225231718706405 | 4.225231718706405 | True |
| v070_fallback_run_time_xtb | endo | G_pathway (Eh); record has no dG‡ | -28.22084847429305 | -28.22084847429305 | True |
| v070_fallback_graft_time_xtb | endo | G_pathway (Eh); record has no dG‡ | -28.22084847429305 | -28.22084847429305 | True |
| v070_enum_ethyl_endo_uma | endo | dG‡ | 20.235660364919468 | 20.235660364919468 | True |
| v070_enum_ethyl_exo_uma | exo | dG‡ | 24.808196296814334 | 24.808196296814334 | True |
| v070_enum_ethyl_selectivity_uma | endo | dG‡ | 20.235660364919468 | 20.235660364919468 | True |
| v070_enum_ethyl_selectivity_uma | exo | dG‡ | 24.808196296814334 | 24.808196296814334 | True |
| v070_enum_ethyl_selectivity_uma | endo/exo | ddG‡ | 4.5725359318948655 | 4.5725359318948655 | True |
| v070_enum_npropyl_endo_uma | endo | dG‡ | 20.444047621736306 | 20.444047621736306 | True |
| v070_enum_npropyl_exo_uma | exo | dG‡ | 25.410415988871044 | 25.410415988871044 | True |
| v070_enum_npropyl_selectivity_uma | endo | dG‡ | 20.444047621736306 | 20.444047621736306 | True |
| v070_enum_npropyl_selectivity_uma | exo | dG‡ | 25.410415988871044 | 25.410415988871044 | True |
| v070_enum_npropyl_selectivity_uma | endo/exo | ddG‡ | 4.966368367134739 | 4.966368367134739 | True |
| v070_fallback_run_time_uma | endo | G_pathway (Eh); record has no dG‡ | -389.10761445505483 | -389.10761445505483 | True |

## `seed_clash` against `v070-replan7/cov_margin.out`

| unit | seed_clash indices | measured | bond_changed | stalls |
|---|---|---|---|---|
| v070_enum_ethyl_endo_uma | [3, 4, 6, 7, 8] | [3, 4, 6, 7, 8] | 0 | 0 |
| v070_enum_ethyl_endo_xtb | [3, 4, 6, 7, 8] | [3, 4, 6, 7, 8] | 0 | 0 |
| v070_enum_ethyl_exo_uma | [1, 2, 5, 9] | [1, 2, 5, 9] | 0 | 0 |
| v070_enum_ethyl_exo_xtb | [1, 2, 5, 9] | [1, 2, 5, 9] | 0 | 0 |
| v070_enum_npropyl_endo_uma | [7, 8, 10] | [7, 8, 10] | 0 | 0 |
| v070_enum_npropyl_endo_xtb | [7, 8, 9] | [7, 8, 9] | 0 | 0 |
| v070_enum_npropyl_exo_uma | [1, 2, 3, 4, 5, 6, 9] | [1, 2, 3, 4, 5, 6, 9] | 0 | 0 |
| v070_enum_npropyl_exo_xtb | [1, 2, 3, 4, 5, 6, 9] | [1, 2, 3, 4, 5, 6, 9] | 0 | 0 |
| v070_fallback_graft_time_xtb | [3, 4, 6, 7, 8] | [3, 4, 6, 7, 8] | 0 | 0 |
| v070_fallback_run_time_uma | [3, 4, 6, 7, 8] | [3, 4, 6, 7, 8] | 0 | 0 |
| v070_fallback_run_time_xtb | [3, 4, 6, 7, 8] | [3, 4, 6, 7, 8] | 0 | 0 |

Total 53 = 53 measured; `bond_changed:*` 0; stalls 0; no unit reached the stall cap. The excluded
index set of every unit equals the fixture's, every non-clash reason and sample key is unchanged,
and a clashed sample has no stage keys. Reasons that changed to `seed_clash` (old reason shown):

- v070_enum_ethyl_endo_uma: [(3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (6, 'orientation_mismatch', 'seed_clash'), (7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash')]
- v070_enum_ethyl_endo_xtb: [(3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (6, 'gate_failed:forming_overlap', 'seed_clash'), (7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash')]
- v070_enum_ethyl_exo_uma: [(1, 'pre_relax_failed:PreRelaxTimeout', 'seed_clash'), (2, 'orientation_mismatch', 'seed_clash'), (5, 'orientation_mismatch', 'seed_clash'), (9, 'orientation_mismatch', 'seed_clash')]
- v070_enum_ethyl_exo_xtb: [(1, 'orientation_mismatch', 'seed_clash'), (2, 'orientation_mismatch', 'seed_clash'), (5, 'orientation_mismatch', 'seed_clash'), (9, 'orientation_mismatch', 'seed_clash')]
- v070_enum_npropyl_endo_uma: [(7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash'), (10, 'orientation_mismatch', 'seed_clash')]
- v070_enum_npropyl_endo_xtb: [(7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash'), (9, 'orientation_mismatch', 'seed_clash')]
- v070_enum_npropyl_exo_uma: [(1, 'orientation_mismatch', 'seed_clash'), (2, 'orientation_mismatch', 'seed_clash'), (3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (5, 'orientation_mismatch', 'seed_clash'), (6, 'orientation_mismatch', 'seed_clash'), (9, 'orientation_mismatch', 'seed_clash')]
- v070_enum_npropyl_exo_xtb: [(1, 'orientation_mismatch', 'seed_clash'), (2, 'orientation_mismatch', 'seed_clash'), (3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (5, 'orientation_mismatch', 'seed_clash'), (6, 'orientation_mismatch', 'seed_clash'), (9, 'orientation_mismatch', 'seed_clash')]
- v070_fallback_graft_time_xtb: [(3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (6, 'gate_failed:forming_overlap', 'seed_clash'), (7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash')]
- v070_fallback_run_time_uma: [(3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (6, 'orientation_mismatch', 'seed_clash'), (7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash')]
- v070_fallback_run_time_xtb: [(3, 'orientation_mismatch', 'seed_clash'), (4, 'orientation_mismatch', 'seed_clash'), (6, 'gate_failed:forming_overlap', 'seed_clash'), (7, 'orientation_mismatch', 'seed_clash'), (8, 'orientation_mismatch', 'seed_clash')]

## n-propyl UMA cyclopropene dispositions (records just written, state directory)

```
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl 78c2c9876b89 kept None ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl edea8d156eca dropped mirror_partner ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl eff482560785 kept None ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl 5ebb886afc5e kept None ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl fe6df08746a6 kept None ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl 62caef43e33f dropped mirror_partner ->
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl 071c077d750a superseded_by_push None -> ee86975197d1
disposition v070_enum_npropyl_endo_uma cyclopropene__npropyl ee86975197d1 dropped duplicate_after_push ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl 78c2c9876b89 kept None ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl edea8d156eca dropped mirror_partner ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl eff482560785 kept None ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl 5ebb886afc5e kept None ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl fe6df08746a6 kept None ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl 62caef43e33f dropped mirror_partner ->
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl 071c077d750a superseded_by_push None -> ee86975197d1
disposition v070_enum_npropyl_exo_uma cyclopropene__npropyl ee86975197d1 dropped duplicate_after_push ->
```

Every endpoint of every unit has `frequency_dispositions` covering exactly its frequency rows, and
every unit records `validation`.

## Checker

`check.py` (state directory, standard library; reads `records/` and the fixtures only) ran before
the candidate commit: exit 0, `ALL CHECKS PASS` (`proof/check.out`).

## Commits (`git show --stat`)

- `e798c92` "Remove the first v0.7.0 candidates before the reruns (slice 17)": 74 files changed,
  35169 deletions; all under `tests/candidate_outputs/v0.7.0/` (30 records, 44 `review/` files).
- `45c52d4` "Add the rerun v0.7.0 candidates (slice 17)": 30 files changed, 30268 insertions;
  `tests/candidate_outputs/v0.7.0/v070_enum_{ethyl,npropyl}_{endo,exo,selectivity}_{xtb,uma}` and
  `v070_fallback_{graft_time_xtb,run_time_uma,run_time_xtb}`, each `.json` and `.runrecord.json`.
  No `review/` tree (slice 18).

No candidate file was opened.

## Commands

From the repo root, `TMPDIR` and `ETA_RXNCAT_XTB` set.

| command | at | exit | seen |
|---|---|---|---|
| `python3 .agents/scripts/hyper_codegraph.py index` | f8fcd9b | 0 | `index: ok` |
| `uv run ruff check .`; format (excluding form) | defd982 tree | 0, 0 | pass; 756 formatted |
| `pytest test_v070_inputs, test_review_v070_helpers, test_acceptance_record_v070` | defd982 tree | 0 | 63 passed |
| `uv sync --locked` (before the runs) | defd982 tree | 0 | |
| 15 x `run.sh` (table above) | e798c92 | 0 | |
| `python3 <state>/check.py <repo>` | e798c92 | 0 | ALL CHECKS PASS |
| `uv sync --locked` | 45c52d4 | 0 | |
| `uv run ruff check .` | 45c52d4 | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 45c52d4 | 0 | 809 files formatted |
| `uv run mypy` | 45c52d4 | 0 | 91 source files |
| `uv run pytest` | 45c52d4 | 0 | 2660 passed, 196 deselected, 207.63 s |
| `uv run pytest tests/e2e/test_v070_inputs.py` | 45c52d4 | 0 | 18 passed |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 45c52d4 | 0 | no change; skipped both globs and `architecture.yml` |
| `hyper_ledger.py validate` | 45c52d4 | 0 | `validate: ok` |
| `hyper_codegraph.py index` (re-index) | 45c52d4 | 0 | `index: ok` |
| `hypergraph_updater.py --from-diff f8fcd9b --apply --slice OPR.0.7.0.17 --json` (once) | 45c52d4 | 0 | below |

The full check's host check passed first (17 GiB, no blockers; `proof/fullcheck.hostcheck`,
output `proof/fullcheck.log`).

## Ledger

- `eta_rxncat_species_runner` files and description (1999/2000) unchanged.
- Updater: nodes `eta_rxncat_species_runner` (dirty); blast radius adds `eta_rxncat_selectivity`
  (needs_review); `lore_stale_candidates` empty. `unmapped`: the slice and mission files, `lore/`,
  `lore_hypergraph.yml`, a `.claude` settings backup, and untracked `spec/` files listed by name
  (none opened). Full JSON: `proof/updater.json`.

## For the auditor to rule on

1. Harness fix `defd982` (`tests/e2e/v070.py` `derive_samples`): a clashed sample made no engine
   call, but a copied store still holds its old rows, so the record would have claimed their keys
   and reported the old ethyl exo UMA `PreRelaxTimeout` as a stall. Found by reading, before any
   run. No unit test was added; the check is `check.py` on the 11 unit records.
2. Host check: attempt 1 of `ethyl-endo-xtb` waited 60 min at 12 GiB and exited 3 without
   starting; I stopped attempt 2 while it was still polling, to apply the ruling. Neither made an
   engine call. `run.sh` then overwrote its output on each poll, so only the last output of each
   of those two attempts survives (`.attempt1`, `.attempt2`). After the ruling every output is
   appended to `proof/<tag>.hostcheck`.
3. `run.sh` and `hostcheck.sh` were edited for the ruling (floor argument, appended outputs, RSS
   stop line); no other host-check condition changed. `hostcheck.sh` was byte-identical to slice
   12's before.
4. Score commands for UMA ran at the 4 GiB floor (the ruling covers all 4 scores), each after its
   two UMA units.
5. The fallback records carry no dG‡ (new and fixture alike); their energy comparison is
   `G_pathway_hartree`, with ensemble members and merges also equal.
6. The format oracle ran only in the excluding form, not the SPEC's bare form (seat rule).
7. `lore/`, `lore_hypergraph.yml` and `.claude/settings.local.json.bak-pretreg-20261126` show as
   changed or untracked in the tree; this slice did not write or stage them.
