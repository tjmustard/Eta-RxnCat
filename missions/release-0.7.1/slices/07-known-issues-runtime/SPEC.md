---
id: OPR.0.7.1.7
slice: 07-known-issues-runtime
mission: release-0.7.1
status: done
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Make open_timeout_s=inf mean no deadline under a typed contract, stop the MACE import leaking an environment variable, and round-trip run records with an infinite ratio as \"Infinity\"."
depends_on: [OPR.0.7.1.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_store
parent: null
hacf_touches: [src/eta_rxncat/store/artifact_store.py, "tests/unit/store/**", src/eta_rxncat/engines/mace.py, "tests/unit/engines/**", src/eta_rxncat/review/run_data.py, "tests/unit/review/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/store, tests/unit/engines, tests/unit/review, tests/integration]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Known issues in runtime source (R13/R29 store inf, R14 MACE env, R38 ratio inf)

## Intent

Make `ArtifactStore(open_timeout_s=inf)` mean no deadline under a typed contract, stop eta's MACE
import from leaking a process-wide environment variable, and make a run record with an infinite
selectivity ratio survive a JSON round trip (mission R13, R14, R29, R38; TJ Q-71b = A, relay
`qitem-20261127193135-56e30a8bf6ae383a`; US-007).

Context the builder needs:
- **R29 (store):** `store/artifact_store.py`.
  - :101 `not open_timeout_s > 0` lets `inf` through, and then :143 `int(remaining * 1000)` raises
    `OverflowError`.
  - **Contract:** `inf` means no deadline. `bool` and non-real values raise `TypeError`, so `True`
    is newly refused. NaN and ≤ 0 raise `ValueError`.
  - Clamp to `2**31 - 1` ms at both `sqlite3.connect(timeout=…)` (:109-110) and every
    `PRAGMA busy_timeout` (:143). Update the docstring.
  - **Tests:**
    - `inf` opens a fresh store.
    - `inf` against a held lock keeps retrying and then opens. The open runs in a daemon worker
      thread joined with a 30 s bound, and the releaser thread drops the lock after about 0.5 s and
      is joined with a timeout. If either thread is still alive, the test fails.
    - `True`, `"5"` and `None` raise `TypeError`.
    - NaN, 0 and -1 raise `ValueError`.
    - A test reads back `busy_timeout` after a connect with `inf`.
  - ADR-0015 is otherwise unchanged.
- **R14 (engines):** wrap `engines/mace.py:123` `importlib.import_module("mace")` in a small context
  manager. It saves the prior state of `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD` (absent or a value) and
  restores it in `finally`. eta's own load passes `weights_only=False` (:133), so eta's path is
  unaffected.
  - **Test** (offline, default suite): put a stub package `mace` on `sys.path` via `tmp_path`; its
    `__init__` sets the variable. Afterwards the variable is absent if it was absent before, and
    keeps its value if it was set before.
  - The test evicts and restores `sys.modules["mace"]` and `sys.path`.
  - The docstring states the limit: the guard restores nothing if `mace` was already imported earlier
    in the process. No MACE extra, no engine run.
- **R38 (review):** `RunRecord` (`review/run_data.py:263`), `_Record` config (:84,
  `allow_inf_nan=False`), nests `SelectivityResult.ratio` (`core/selectivity_models.py:350`,
  `allow_inf_nan=True`).
  - **Contract:** an infinite ratio is written as the JSON string `"Infinity"` and read back as
    `inf`. Finite values are unchanged.
  - Measure `ser_json_inf_nan="strings"` on the record config first. Use the smallest mechanism that
    makes `RunRecord.model_validate_json(r.model_dump_json()) == r` true for a record with
    `ratio=inf`.
  - Make no change to `SelectivityResult` or anywhere in core.
  - **Tests:**
    - the inf round trip;
    - a NaN anywhere in a record is still refused;
    - every committed `tests/fixtures/v0.7.0/*.runrecord.json` re-serialises to its exact bytes, so
      finite records stay byte-identical. Read the fixtures in place and do not write them.
  - Remove the CHANGELOG 0.7.0 known issue in slice 09, not here.
- **Ledger:** store 1804, engines **1991** and review 1983. No description words are expected; if one
  is needed, compress first. Core gets none.
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

**Score: 9/10.** Each defect was re-read at `bf7b949`, and the R13 crash path was traced in code.
Residual: whether pydantic's `ser_json_inf_nan` applies to the nested core model from the record's
config. It is measured first; if it does not apply, choose the smallest field-level serializer on
the record side and state it.

## Mini-requirements

1. R29: each contract case is tested, and the held-lock test cannot hang.
2. R14: the variable is restored in both prior states.
3. R38: the inf round trip holds, NaN is refused, and the v0.7.0 runrecord fixtures re-serialise
   byte-identically.
4. Each new test fails at `bf7b949` and passes after.
5. The default suite is green, and the integration suite (Tier O, plus a Tier X rerun under the
   heavy-run rule) stays green, which shows no seam broke.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] R29 and its tests.
- [x] R14 and its test.
- [x] R38: measure the mechanism, then the fix and its tests.
- [x] Required checks; Tier X rerun (host check first); commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change ADR-0015's open order or its error class.
- **DO NOT** change `SelectivityResult`, `CoreModel` or any core file.
- **DO NOT** import a real MACE or run an engine for R14.

## Proof contract

- [ ] The new test ids, each failing at `bf7b949` (from a worktree run with R22's interpreter) and
  passing after (requirements 1-4).
- [ ] The R38 mechanism measurement and the fixture byte-compare list (requirement 3).
- [ ] The required checks exit 0, and the Tier X junit shows 0 failed and 0 skipped (requirement 5).

## Source material

- Mission R13, R14, R29 and R38; ADR-0015; TJ Q-71b = A.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.6.
