---
id: OPR.0.7.1.5
slice: 05-tier-x-selectivity-review
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Check the enumerated graph file to selectivity score chain on CPU GFN2 and the review export from that store through the schema, lenient reader and bundle writer."
depends_on: [OPR.0.7.1.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_integration
parent: null
hacf_touches: ["tests/integration/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Tier X selectivity chain and the review export round trip (T-X4, T-X5)

## Intent

Check the whole chain from an enumerated graph file to a selectivity score on GFN2, and the review
export from that real store through the schema, the lenient reader and the bundle writer (mission
R9, R35, R37; US-006).

Context the builder needs:
- **File:** `tests/integration/test_seams_selectivity_gfn2.py`, `pytestmark =
  [pytest.mark.integration, pytest.mark.xtb]`, one **module-scoped** store shared by T-X4 and T-X5.
- **Task 2 is the measurement (stop-and-report):** T-X4 > 180 s (2× R33's 90 s) is a stop-and-report.
- **T-X4 (R35):** `load_v070_plan()` → `enumerate_candidates` → the ethyl candidate's graph →
  `dump_reaction_graph_json` → `tmp_path` file → `load_reaction_graph`. Build the run graph with
  `model_copy`, setting **only** the two TS nodes (`TS1a_n`, `TS1a_x`) to priority 1; the docstring
  states why (`run_selectivity` runs priority-1 pathways, `selectivity.py:371`; the plan's TS nodes
  are priority 2 for the fallback runner, `v070_enumeration.yaml:28,40`). Pathway inputs per
  pathway (`endo`, `exo`) from `enumerated_pathway_inputs` on the **unmodified** candidate.
  `run_selectivity(graph, store, pathways=..., downstream={}, optimizer=GeometricOptimizer(),
  options=TSEnsembleOptions(n_embed=1, n_perturb=1, max_research=1), kind="de")`. Gates: each
  pathway ≥ 1 member, Σw within `1e-12` per set, a score present, and a rerun all hits with an
  equal score.
- **T-X5:** a `RunRecord` built from T-X4's result (the `RecordCandidate` / `RecordSample` /
  `RecordSelectivity` models in `review/run_data.py`; samples from `TSEnsembleRun.samples`, R37)
  → `export_run_data` (`review/export.py:699`) → validate against
  `src/eta_rxncat/review/schema/run_data.v1.schema.json` → `read_run_data` (`run_data.py:739`)
  equals the export → `write_review_bundle` (`bundle.py:405`) into two fresh directories gives equal
  bytes file by file. If building a valid `RunRecord` needs a field T-X4 cannot honestly supply,
  stop and report (never invent values).
- **Run command:** as slice 04 (separate blocking host check, `timeout 600`, `/usr/bin/time -v`,
  thread pins, scratch cwd, no `HT.v_*` afterwards).
- **Seam breaks (R4; the audit commits
  `missions/release-0.7.1/slices/05-tier-x-selectivity-review/seam_breaks.json`):**
  - T-X4 ⇐ `run_selectivity` passes the wrong pathway's `reactant_key`; and ⇐ `load_reaction_graph`
    drops `pathway_pruning_rules` or a node's `pathway`.
  - T-X5 ⇐ the RunData serialiser reorders sorted keys; and ⇐ `export_run_data` skips a sample's
    `ts_opt` row.
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

**Score: 9/10.** The APIs and the priority mismatch were re-read at `bf7b949`; M1c measured the
same chain shape (43 s, replay equal) on the t4 pair. Residual: the ethyl pair's wall (measured first)
and the `RunRecord` fields a non-E2E run can supply (stop-and-report if one is missing).

## Mini-requirements

1. The measurement is in the proof; T-X4 within 2× its estimate.
2. T-X4 and T-X5 pass under the Tier X command with `ETA_RXNCAT_ACCEPTANCE=1`, 0 skipped.
3. The priority copy is stated in T-X4's docstring and touches only the two TS nodes.
4. Each test names its seam break(s); the default suite stays green.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] T-X4.
- [ ] T-X5.
- [ ] Host check; measured run; required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change `run_selectivity`, the plan YAML or any node's priority outside the test's copy.
- **DO NOT** write a bundle or record outside `tmp_path`.
- **DO NOT** run GPU or MLIP; CPU GFN2 only.

## Proof contract

- [ ] Host check, command, `/usr/bin/time -v`, junit with T-X4 and T-X5 `passed`, 0 skipped
  (requirements 1-2).
- [ ] Required checks exit 0 (requirements 3-4).

## Source material

- Mission R9, R33, R35, R37; resolve evidence `m1c*`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.4.
