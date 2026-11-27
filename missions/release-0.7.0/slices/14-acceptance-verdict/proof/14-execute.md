---
slice: OPR.0.7.0.14
candidate_sha: f33113346054b4d37f716792d18782132f599b7d
artifact_type: guard
verdict: CLEAR
money_evidence: "verdict pass: 15 rerun commands, 0 engine calls, 0 skips, 30/30
  outputs match ef9225e fixtures; 0.7.0; full pytest 2690 passed"
---

# Execute evidence: 14-acceptance-verdict (OPR.0.7.0.14) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type;
this is builder evidence and the audit writes the QA verdict.

Start `9fdba68`. Slice 14's own commits: `e641ba1` (C1: verdict rule, rerun comparison, store reuse),
`d1596ad` (record with verdict, README, claim pins, 0.7.0), `f331133` (ledger flag, progress, task
boxes, field note), then this proof. Commits between `e641ba1` and `ef9225e` belong to the lead and
slices 15-18. Work gate: `ef9225e` (TJ's re-promotion, 30 `v070_*` fixtures). No push, no tag.

`E` = `~/.hacf/eta-rxncat-hacf/evidence`, `S` = `E/v070-replan7-runs` (the source root slice 18
set), `D` = `E/v070-slice14/rerun-r7`, `T` = `~/.cache/eta-rxncat-tmp/slice14r` (scratch, removed).

## Verdict rerun (at `ef9225e`, before any edit to `src/` or `tests/e2e/`)

- `D/all.sh` ran `D/run.sh` once per unit: one engine, one unit per command, `timeout 5400` for
  G7/G8 units and 3600 for scores, scratch cwd (empty after every command, no `HT*` in the repo).
- Stores: **copies** of the four replan-7 stores in `T/state`. `S/*.sqlite` and `S/records/*` are
  sha256-unchanged (`D/sources.sha256.before`); the copies' sha256 are equal before and after
  (`D/store-copies.sha256.{before,after}`). Candidates went to `T/candidates` and logs to `T/proof`,
  both then copied to `D` (the record derives from the copy). Nothing under
  `tests/candidate_outputs/` was read or written.
- Env (`D/proof/<tag>.env`): `ETA_RXNCAT_ACCEPTANCE=1`,
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`,
  `TMPDIR=~/.cache/eta-rxncat-tmp`, `ETA_RXNCAT_V070_REUSE_STORES=1`. UMA units used
  `.venv-accept-uma/bin/python`; the others `uv run --no-sync python`.
- Host check: blocking, floor **12 GiB for every command** (`D/hostcheck.sh`, slice 17's script).

| tag | exit, pytest | busy checks before start | final check (avail / GPU util / gpu_apps / heavy / eta) | wall | max RSS kB |
|---|---|---|---|---|---|
| ethyl-endo-xtb | 0, 1 passed | 0 | 14G / 2 % / 0 / 0 / 0 | 3.2 s | 158600 |
| ethyl-exo-xtb | 0, 1 passed | 0 | 14G / 12 % / 0 / 0 / 0 | 3.8 s | 160388 |
| npropyl-endo-xtb | 0, 1 passed | 0 | 14G / 7 % / 0 / 0 / 0 | 3.6 s | 167140 |
| npropyl-exo-xtb | 0, 1 passed | 0 | 14G / 7 % / 0 / 0 / 0 | 2.4 s | 167448 |
| score-ethyl-xtb | 0, 1 passed | 0 | 14G / 19 % / 0 / 0 / 0 | 1.0 s | 98880 |
| score-npropyl-xtb | 0, 1 passed | 3 | 14G / 0 % / 0 / 0 / 0 | 1.0 s | 100856 |
| ethyl-endo-uma | 0, 1 passed | 0 | 14G / 0 % / 0 / 0 / 0 | 142.5 s | 8585864 |
| ethyl-exo-uma | 0, 1 passed | 0 | 18G / 0 % / 0 / 0 / 0 | 116.9 s | 8941736 |
| npropyl-endo-uma | 0, 1 passed | 0 | 17G / 1 % / 0 / 0 / 0 | 124.5 s | 8953248 |
| npropyl-exo-uma | 0, 1 passed | 0 | 16G / 0 % / 0 / 0 / 0 | 96.0 s | 8924748 |
| score-ethyl-uma | 0, 1 passed | 1 | 17G / 1 % / 0 / 0 / 0 | 0.7 s | 109160 |
| score-npropyl-uma | 0, 1 passed | 0 | 17G / 1 % / 0 / 0 / 0 | 0.8 s | 110668 |
| graft-time-xtb | 0, 1 passed | 0 | 17G / 1 % / 0 / 0 / 0 | 2.8 s | 157972 |
| run-time-xtb | 0, 1 passed | 0 | 17G / 1 % / 0 / 0 / 0 | 2.2 s | 158604 |
| run-time-uma | 0, 1 passed | 3 | 17G / 0 % / 0 / 0 / 0 | 105.3 s | 8973072 |

- Busy checks were the script's GPU-utilisation limit (> 20 %, desktop processes). Desktop programs
  hold GPU memory on this host (about 2 GiB; e.g. gnome-remote-desktop, chrome, `handy`);
  `gpu_apps` counts only python/xtb/torch/uma/metis names, as in slices 11-18. The UMA warning is
  torch's `torch.jit.script` deprecation.
- **Engine calls: 0** in the first and second pass of all 11 units, 0 new rows (candidate
  `reported`), and the per-store row counts are unchanged around every command. The 4 score
  commands load no engine.
- Skips: 0 in all 15 commands.

## Comparison with `ef9225e`'s fixtures

`acceptance_record_v070.verdict_block`: **30/30 `pass`, `unexpected` empty for every file**. Run
records have no differing field; each unit candidate has 9 volatile differences, each score
candidate 1. `VOLATILE` and the fixtures are unchanged; no new wall-time entry was needed.

## Acceptance record

`uv run --no-sync python tests/e2e/acceptance_record_v070.py E
missions/release-0.7.0/slices/17-rerun-units/proof/17-execute.md D/full-pytest.log 0
docs/prd/v0.7.0/ACCEPTANCE_RESULT.json D tests/fixtures/v0.7.0` - exit 0, **verdict `pass`,
reasons `[]`**. `acceptance_record_v070.py` is unchanged from `4bd2cf0` (nothing needed extending).

- Before that, the no-rerun form with slice 18's full log reproduced the committed record
  byte for byte (`cmp` exit 0).
- Order (the claim test needs a verdict, the record needs the full log): a first record was derived
  with slice 18's log (uncommitted), the full pytest ran on the finished tree, and the committed
  record was re-derived from that run's log. Against slice 18's record the only removed values are
  the default suite's old pass count (2674 -> 2690); everything else is added. After the final
  derivation, `test_package.py`, `test_identity.py`, `test_acceptance_record_v070.py`: 182 passed.

## README and bump

- README: header pitch, badge, "What is" paragraph, `Features (v0.7.0)` with an enumeration /
  fallback / seed-check / verdict subsection, `review-bundle` in the CLI table, "Review a run" and
  "The run-data contract" sections, Roadmap (v0.7.0 under Built).
- `test_identity.py`: `V070_CLAIMS` (16) checked against the record and against code constants (CSP,
  schema and store versions, disposition literals, `SEED_CLASH_FACTOR`, bundle limit, 3Dmol
  version), with drift cases and the no-verdict refusals; the v0.6.0 test's exact-version assert is
  now "at least 0.6.0", as for v0.4.0/v0.5.0. Module docstring updated (it now imports eta).
- Prose that has no pin of its own beyond the claim it sits in (CLI behaviour, enumerator and
  fallback descriptions, decimation, banner rule, determinism) was written from the source and is
  covered by those modules' own tests; the auditor should rule whether that meets "every claim".
- Forward-only stores wording is narrower than ADR-0053 ("A v0.6.0 reader refuses v0.7.0 rows"):
  README says v0.6.0 refuses the new **transition-state search** rows. Probe: `git archive v0.6.0
  src` into scratch, `TSSearchResult.model_validate` on every successful `ts_opt` payload of a copy
  of `v070_enum.sqlite`: **87/87 refused** (`history.0.coordinates_angstrom` extra_forbidden).
  v0.6.0's `geometry_opt` rebuild selects keys from the payload, so refusal of that kind is not
  shown. No lore changed.
- Bump: `pyproject.toml`, `__init__.py`, `test_package.py`; `uv lock` (exit 0, one line:
  0.6.0 -> 0.7.0); `uv sync` (exit 0, reinstalled eta only).

## Commands and exit codes

| command | at | exit | result |
|---|---|---|---|
| `hyper_codegraph.py index` | `ef9225e` / after `d1596ad` | 0, 0 | `index: ok` |
| 15 verdict commands (`D/all.sh`) | `ef9225e` | 0 | above |
| `uv lock`; `uv sync` | tree of `d1596ad` | 0, 0 | |
| `uv run ruff check .` | tree of `d1596ad` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | same | 0 | 814 files already formatted |
| `uv run mypy` | same | 0 | no issues, 91 files |
| `uv run pytest -q -p no:cacheprovider` (`ETA_RXNCAT_XTB` set; `D/full-pytest.{log,exit}`) | same | 0 | **2690 passed, 196 deselected**, 699.38 s |
| `pytest test_package.py test_identity.py test_acceptance_record_v070.py` | final record | 0 | 182 passed |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | after `d1596ad` | 0 | skipped glob `tests/e2e/**` |
| `hypergraph_updater.py --from-diff 9fdba68 --apply --slice OPR.0.7.0.14 --json` (once) | after `d1596ad` | 0 | below |
| `hyper_spec.py progress --event executed` | after updater | 0 | executed |

Full-check host check: `avail=15G gpu=0% gpu_apps=0 heavy=0 eta=0 floor=12G` (`D/fullcheck.hostcheck`).
An earlier check was refused for a transient `codebase-memory-mcp` index worker; the run waited.
Another rig's pytest (`hakf-v0.2.0-live`) started about 90 s after ours and ran beside it, so the
wall time is 699 s against about 280 s before.

## Ledger

- `ensure-node`: `eta_rxncat_scaffold.files` kept all 22 entries and gained
  `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`. `tests/e2e/**` is covered by other nodes' globs.
- Updater (`D/updater.json`): dirty `cli, core, hw_probe, review, scaffold, selectivity,
  species_runner, store`; `needs_review` `conformers, engines, enumerator, mapping, optimize,
  thermo`. No lore stale candidates.
- **From slice 14's own files**: `scaffold` (README, record, pyproject, uv.lock, `__init__`, unit
  tests), `cli` (pyproject, uv.lock), `species_runner` (the three `tests/e2e` files of C1).
- **Re-flagged from slices 15-18** (already reconciled by their audits): `core`, `review`,
  `selectivity`; `hw_probe` and `store` (and part of `cli`/`scaffold`) as the known phantoms through
  `spec/compiled/architecture.yml`.
- `unmapped`: `.agents/**` (3 kit files), `lore/**` and `lore_hypergraph.yml` (cd2a91e),
  `missions/**`, `tests/fixtures/v0.7.0/**` (no owner node, known), the two untracked
  `.claude/settings.local.json.bak-*` files, and untracked names under `spec/active|archive|process`
  (the updater lists paths; no file under `spec/archive/` was opened).
- Not done here: `scaffold`'s description still says `eta-rxncat 0.6.0`; it is left for the audit's
  reconciliation (the node is near the 2000 cap).

## Deviations and disclosures

1. `hyper_spec.py progress --event executing` was not re-recorded for this resumed round (the slice
   was already `executing`, as the SPEC says it stays).
2. The record was derived twice, as above.
3. A first `hyper_lore.py note` call, chained after a heredoc, was denied whole by the gate hook
   (nothing ran); the parts were rerun separately and the note was reworded.
4. Scratch removed after this proof: `T`, and `~/.cache/eta-rxncat-tmp/slice14` (the superseded
   pre-replan rerun's `state/` and `outputs/`).
