---
slice: OPR.0.7.0.16
candidate_sha: 1f3ad54
artifact_type: guard
verdict: CLEAR
money_evidence: push chain reaches duplicate_after_push (fails without the
  drop); re-export reverted; pytest 2660 passed
---

# Execute evidence: 16-review-dispositions (OPR.0.7.0.16) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type.
Start `c0a8de1`. Code commit `49ee110`; ledger/progress commit `53b10e7`; fix commit `1f3ad54`
(audit FAIL iteration 1, base `d0dd57d`).

## Proof contract

- Disposition kinds (species, exporter), old record and old RunData loads, schema drift:
  `tests/unit/orchestrator/test_frequency_dispositions.py`, `tests/unit/review/test_dispositions.py`,
  `tests/unit/review/test_run_data.py`.
- Static summary grouping, headings, identity numbers, banner: `test_dispositions.py`.
- M12 stubs, Chrome and Playwright Firefox 159, headless, file://: `proof/m12/` (62 PASS, 0 failed each).
- Real data, read-only, 0 engine evaluations, store sha256 unchanged: `proof/known-answers.txt`
  (sample 6 excluded gate_failed:forming_overlap, overlap 0.131, 3.662/2.853 A, banner;
  071c077d750a superseded by ee86975197d1, itself dropped duplicate_after_push; 78c2c9876b89 kept).
- All 15 fixture records export, 0 missing rows: `proof/export-all-records.txt`.
- Checks: ruff check 0; ruff format --check (excluding spec/archive, spec/process) 0; mypy 0;
  full pytest 2660 passed, 196 deselected, exit 0 (rerun at `1f3ad54`).

## Deviations for the audit

1. A sample its chosen ensemble does not list, or whose template has no attempt, exports
   `excluded` / `not_recorded` (the TS kind enum has no not_recorded).
2. `not_recorded` rows (old records/documents) sit in the "Not used" group.
3. `Candidate` disposition lists are omitted from the serialised form when empty.
4. The lenient reader now keeps field defaults, so pre-slice documents load.
5. Dropped reason does not name the surviving row (the record carries no such field).
6. JS also lists samples without frequencies under the panel chooser; the index and candidate
   tables label each TS count with its kind.
7. Known answer 2 replays `run_species` on cached rows with `FairchemEngine._load` stubbed and
   `Engine.evaluate` refusing, in a throwaway venv (mlip-uma extra, offline; removed). The
   committed fixture record itself reads not_recorded.
8. RunData float test allow-list gained ratio, forming_overlap, active_core_ke_fraction (unitless).
9. M12 driver copied from slice 09 and extended; option count changed from 2 to 5.
10. Updater ran once after commit 49ee110: marked 8 nodes (cli, core, hw_probe, scaffold, store
    via spec/compiled/architecture.yml ownership); `unmapped` includes missions/ files and the
    untracked spec/active, spec/archive, spec/process paths it listed by name. No lore stale marks.
11. Descriptions compressed: review 1991 -> 1787; species_runner 1988 -> 1925.
    ensure-node --from-spec: no change to node files (globs and other nodes' paths skipped).

## Cross-node touches

- `src/eta_rxncat/orchestrator/species.py` -> eta_rxncat_species_runner.
- `tests/e2e/v070.py` -> eta_rxncat_species_runner.
- `tests/unit/orchestrator/test_frequency_dispositions.py` -> eta_rxncat_species_runner.

## Fix round 1 (lead ruling A)

- Push chain: `species._push` is patched to return anti's optimization shifted 0.01 A, unrelaxed,
  1e-4 Eh higher (so the lowest-G re-dedup keeps anti). The test asserts `dropped` /
  `duplicate_after_push` unconditionally. With the `_dedup_after_push` call removed from
  `run_species` it fails (`'mirror_partner' == 'duplicate_after_push'`, 1 failed); source restored.
- `orchestrator/__init__.py` is back to its c0a8de1 content (empty diff against Start).
- The updater was not rerun: the fix adds no change to mapped code beyond the flagged nodes.
  Deviation 10's selectivity mark came from the reverted file.
