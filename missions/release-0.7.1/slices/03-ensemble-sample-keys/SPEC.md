---
id: OPR.0.7.1.3
slice: 03-ensemble-sample-keys
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Expose each TS ensemble sample's stage keys on TSEnsembleRun, switch the v0.7.0 E2E off private helpers with a byte-equal record, and unit-test the clashed-sample rule."
depends_on: [OPR.0.7.1.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_selectivity
parent: null
hacf_touches: [src/eta_rxncat/orchestrator/ts_ensemble.py, src/eta_rxncat/orchestrator/__init__.py, "tests/unit/orchestrator/test_ts_ensemble*.py", tests/e2e/v070.py, tests/e2e/test_v070_samples.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator, tests/e2e/test_v070_samples.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Public per-sample stage keys on TSEnsembleRun and the defd982 unit test

## Intent

Expose each TS ensemble sample's stage keys on `TSEnsembleRun`, so the E2E and the review export
stop re-deriving them from private helpers, and pin v0.7.0's clashed-sample rule with a unit test
(mission R37; TJ Q-71a = A, relay `qitem-20261127193135-56e30a8bf6ae383a`; carry-forwards 1 and 2;
US-004).

Context the builder needs:
- **API (Contract `SampleKeys`):** in `src/eta_rxncat/orchestrator/ts_ensemble.py` add a frozen
  dataclass `SampleKeys(index: int, source: str, pre_relax_key: str | None, ts_opt_key: str | None,
  frequency_key: str | None)` and the field `samples: tuple[SampleKeys, ...] = ()` on
  `TSEnsembleRun` (:101, a frozen runtime dataclass; it is not cached). Export `SampleKeys` from
  `eta_rxncat.orchestrator` (`__init__.py`: the lazy table :80 and `__all__` :134). Index 0 is the
  seed (`source="seed"`); samples follow in draw order up to where sampling stopped. The runner
  fills each key from the `StageKey` it already builds for that row (pre-relax `build_stage_key`,
  and the `run_transition_state` result's `keys["ts_opt"]` / `keys["frequency"]`). A `seed_clash`
  sample has all three keys None; a pre-relax failure has only `pre_relax_key`. No stage key,
  payload, `TSEnsemble` field or RunData field changes: an existing store gives the same results.
- **Unit tests** (fakes are allowed in unit tests): extend
  `tests/unit/orchestrator/test_ts_ensemble*.py` with the keys of the seed, a searched sample, a
  pre-relax-failed sample and a clashed sample, and assert every non-None key is a row in the store.
- **E2E switch:** `tests/e2e/v070.py` `derive_samples` (:376) maps `run.samples` to `RecordSample`s
  and drops `_digest`, `_PreRelax` and `_sorted_pairs` (:67-68) and any now-unused private import.
  The timeout rows (`note_timeout`) are read from the rows of `samples[i].pre_relax_key`. The
  coverage assertions the function makes stay. List every private eta import left in `v070.py`
  with its reason (target: none).
- **defd982 test (carry-forward 2):** a new offline `tests/e2e/test_v070_samples.py` (no marker, no
  engine): for a `TSEnsembleRun` whose ensemble excludes index k as `seed_clash`, `derive_samples`
  gives index k a `RecordSample` with only `template_id`, `sample_index`, `source` and `species_id`,
  **even when the store holds rows for that start** from an earlier run (plant one with
  `store.put`). It fails on `bf7b949`'s logic with the `clashed` branch removed (state that break in
  the docstring).
- **Parity (stop-and-report):** in a throwaway worktree at the slice commit
  (`git worktree add <literal path>`; R22's interpreter; never `uv` in it), rerun the v0.7.0 E2E unit
  `ethyl-endo-xtb` (`tests/e2e/test_v070_enumeration.py::test_v070_unit` with that id) under the
  heavy-run rule (mission §5: blocking host check as a separate call, `timeout 5400`,
  `/usr/bin/time -v`, thread pins, scratch cwd, `ETA_RXNCAT_XTB`, `ETA_RXNCAT_ACCEPTANCE=1`). `cmp`
  its runrecord against `tests/fixtures/v0.7.0/v070_enum_ethyl_endo_xtb.runrecord.json`. Byte-equal
  is the pass; any difference is a stop-and-report to the lead with the diff of keys (never a
  re-promotion). Then remove the worktree by literal path. Nothing from the worktree is committed.
- **Ledger:** selectivity description 1455 (room); species_runner 1991 (compress first if a word is
  needed).
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/`.
  - The ruff format oracle is only
    `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`.
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.7.0/`, older
    missions or `PRDs/`. Plain literal `rm -f` only, and never `rm -rf` on a computed path.
  - Ledger caps (mission §5 carry-forward 7): any description word in a node at or above 1978 chars
    is compressed for first, with the before and after counts in the proof. Core gets no words.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.
- **Licence:** no new Python or JS dependency; the core stays MIT/BSD.

## 1. The Confidence Mandate

**Score: 9/10.** `TSEnsembleRun`, the private imports and `derive_samples` were re-read at `bf7b949`;
the field is additive on a runtime dataclass. Residual: the parity rerun's wall (v0.7.0 ran it under
the same 5400 s bound) and any record field the switch changes, which the byte compare catches.

## Mini-requirements

1. `SampleKeys` and `TSEnsembleRun.samples` exist and are exported; the unit tests pass.
2. `tests/e2e/v070.py` imports no `_`-prefixed eta name (or each left one is listed with a reason).
3. `tests/e2e/test_v070_samples.py` pins the clashed-sample rule.
4. The parity runrecord is byte-equal to the promoted fixture.
5. The default suite is green.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] `SampleKeys`, the field, the runner fill, the export.
- [ ] Unit tests.
- [ ] E2E switch and `test_v070_samples.py`.
- [ ] Required checks; commit.
- [ ] Parity rerun in a worktree (host check first); remove the worktree; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change a stage key, a cache payload, `TSEnsemble`, `RunRecord` or a RunData field.
- **DO NOT** write to `tests/fixtures/` or `tests/candidate_outputs/` in the main checkout; the parity
  run's outputs stay in the worktree and are discarded.
- **DO NOT** run UMA, GPU or MLIP; the parity unit is the xtb one only.

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator tests/e2e/test_v070_samples.py -q` passes
  (requirements 1, 3).
- [ ] `grep -n "import _\|, _[a-zA-Z]" tests/e2e/v070.py` output with the listing (requirement 2).
- [ ] Host check, command, `/usr/bin/time -v` and the `cmp` exit 0 for the parity record
  (requirement 4).
- [ ] Required checks exit 0 (requirement 5).

## Source material

- Mission R37, heavy-run rule; v0.7.0 slices 11, 15 and 17 (record and clash rule).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.2.
