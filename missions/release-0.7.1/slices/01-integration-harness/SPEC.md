---
id: OPR.0.7.1.1
slice: 01-integration-harness
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Give tests/integration a default-selected integration marker, real-module helpers, a no-mock no-skip policy test, the eta_rxncat_integration node, and ownership of every promoted fixture."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_integration
parent: null
hacf_touches: ["tests/integration/**", pyproject.toml, tests/unit/test_test_policy.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/integration, tests/unit/test_test_policy.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Integration harness, marker split, mock policy, node and fixture ownership

## Intent

Give `tests/integration/` a default-selected `integration` marker, shared real-module helpers, a
policy test that forbids mocks across seams and every skip form, the `eta_rxncat_integration` node,
and ownership of every promoted fixture (mission R2, R3, R5, R21, R24-R27; US-001, US-002).

Context the builder needs:
- **Marker (R2, R24):** register `integration` in `pyproject.toml` `markers` (:89-97) with the
  Marker contract text. Do **not** add it to `addopts` (:98). In `tests/unit/test_test_policy.py`
  split `MARKERS` (:14) into `DESELECTED_MARKERS` (the seven) and
  `DEFAULT_SELECTED_MARKERS = ("integration",)`; `test_markers_and_default_deselection` (:91)
  asserts addopts deselects exactly the first set, never names the second, and declared markers ==
  the union.
- **Guarded dir (R25):** add `tests/integration` to `GUARDED_DIRS` (:210).
- **Policy test (R26 + R25):** `tests/integration/test_integration_policy.py`, an AST scan of every
  `tests/integration/**/*.py`. It fails on: `unittest.mock` (import or from); any attribute of a
  `monkeypatch` parameter (tracked by name and by alias) outside {`setenv`, `delenv`, `chdir`};
  assignment / augassign / `del` to an `Attribute` or `Subscript` rooted at an imported `eta_rxncat`
  module name or `sys.modules`; builtin `setattr` / `delattr`; any import from `tests.*` other than
  `tests.integration`; `pytest.skip`, `importorskip`, `skipif`, `xfail` as call or marker; the
  markers `gpu`, `mlip_mace`, `mlip_uma`, `slow`. The scanner is a function the test parametrises
  over source snippets: one negative case per form (it must report the form) and positive cases
  (`monkeypatch.setenv`, a subprocess call, a plain local assignment) that pass. Then it scans the
  real directory and asserts zero findings. Every test in the directory carries `integration`
  (checked by the same scan: a module-level `pytestmark` containing `pytest.mark.integration`).
- **Conftest helpers (R3, R21):** `tests/integration/conftest.py` with:
  - `uff_recipe()` and `gfn2_stage()`, the latter rebuilt literally from `tests/e2e/e2e_env.py:28-34`
    (`StageConfig(kind="geometry_opt", engine="xtb_subprocess", method="gfn2",
    options={"alpb_state": "gsolv"})`, runtime `{}`); no import of `e2e_env`.
  - a `store` fixture, `ArtifactStore(tmp_path / "store.db")`, and `row_count(store)`.
  - a `scratch_cwd` fixture (`monkeypatch.chdir(tmp_path)`).
  - `load_v070_plan()`: the copied rules of `tests/e2e/v070.py:109` `load_enumeration` (`_read`
    :135, `_inputs`, `_state`, `_template`): schema 1; exact top-level keys = the plan keys ∪
    {`max_alignment_rmsd_angstrom`, `orientation_centers`} ∪ {`schema`, `fixture`}; every `xyz`
    resolved against the YAML's directory; each block read with its declared `charge` and
    `spin_multiplicity`; then `EnumerationPlan.model_validate`. It returns the plan plus
    `max_alignment_rmsd_angstrom` and `orientation_centers`. Read the loader's code to copy the rules;
    write no new format. Its parity test is slice 02's.
- **Node (R5):** `python3 .agents/scripts/hyper_ledger.py ensure-node --id eta_rxncat_integration
  --dimension Module --files 'tests/integration/**'`, description ≤ 1200 chars; `depends_on` = the
  import scan of `tests/integration/**` (at this slice: core, store, engines, orchestrator nodes the
  conftest imports) **plus** `eta_rxncat_species_runner` and `eta_rxncat_core` (data owners). Print
  the scan in the proof.
- **Fixture ownership (R27):** recount with `git ls-files tests/fixtures` (at `bf7b949`: v0.3.0 10,
  v0.4.0 3, v0.5.0 11, v0.6.0 10, v0.7.0 30, `.gitkeep` 1 = 65). Add `tests/fixtures/v0.3.0/**`,
  `v0.5.0/**`, `v0.6.0/**`, `v0.7.0/**` to `eta_rxncat_species_runner`; `tests/fixtures/v0.4.0/**`
  to `eta_rxncat_mapping`; `tests/fixtures/.gitkeep` and `tests/candidate_outputs/.gitkeep` to
  `eta_rxncat_scaffold`. `ensure-node --files` **replaces** the list: pass each node's full list and
  print its glob count before and after (memory guard). Graph stays acyclic (`hyper_ledger.py
  validate`).
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

**Score: 9/10.** Every line cited was re-read at `bf7b949`. Residual: the exact list form
`ensure-node` takes for each existing node, which the builder reads from `hyper_ledger.py --help`
before running it.

## Mini-requirements

1. `integration` is registered and default-selected; the R24 split test passes.
2. `tests/integration` is guarded (R25).
3. The policy test reports every R26/R25 form in its negative cases and finds none in the directory.
4. The conftest helpers exist, import nothing from `tests.unit` or `tests.e2e`, and `load_v070_plan()`
   returns an `EnumerationPlan`.
5. `eta_rxncat_integration` owns `tests/integration/**` with the R5 `depends_on`; the R27 globs are
   added; 65 fixture files are owned; the ledger validates.
6. The default suite is green.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] Marker, R24 split, R25 guarded dir.
- [x] Policy scanner and its cases.
- [x] Conftest helpers including `load_v070_plan()`.
- [x] Ledger: node, fixture globs (counts before/after), validate.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** add `integration` to `addopts`.
- **DO NOT** import from `tests/unit/` or `tests/e2e/` in `tests/integration/**`.
- **DO NOT** edit `tests/e2e/v070.py` or `v070_enumeration.yaml`.
- **DO NOT** own `lore/`, `missions/`, `.agents/`, `.claude/`, `PRDs/` or `spec/`.

## Proof contract

- [x] `uv run pytest tests/integration tests/unit/test_test_policy.py -q` passes (requirements 1-4).
- [x] `hyper_ledger.py validate` ok; `impact --files tests/integration/conftest.py` names
  `eta_rxncat_integration`; the fixture counts before and after (requirement 5).
- [x] Required checks exit 0 (requirement 6).

## Source material

- Mission R2, R3, R5, R21, R24-R27; Red Team RT-01, RT-04, RT-05, RT-06, RT-08, RT-14.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- None inside this mission. Base `bf7b949` (v0.7.0 shipped).
