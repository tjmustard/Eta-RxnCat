---
id: OPR.0.6.0.7
slice: 07-selectivity-runner
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Add run_selectivity and evaluate_pathway_pruning: ensembles per priority-1 pathway, the score, each PathwayPruningRule evaluated once, and only unpruned priority-2 nodes run, every decision recorded."
depends_on: [OPR.0.6.0.4, OPR.0.6.0.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_selectivity_runner.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 selectivity runner and per-pathway pruning

## Intent

Add `run_selectivity`, which runs each priority-1 pathway's seed TS and ensemble, scores them,
evaluates each `PathwayPruningRule` once, and runs only the unpruned priority ≥ 2 nodes through the
species runner, recording every decision with its numbers — the evaluated pruning TJ chose in Q2 A.

Context the builder needs:
- **TJ, verbatim (Q2):** "A: evaluated per-pathway rule in core + optional pathway labels + small
  selectivity runner; 1.5 in the Tier 4 fixture, no library default (the recommendation)."
- Mission R7 (normative), §5 "Selectivity", G2, G6. Module `orchestrator/selectivity.py`
  (`run_selectivity`, `evaluate_pathway_pruning`), node `eta_rxncat_species_runner`.
- `evaluate_pathway_pruning(rule, result: SelectivityResult, nodes) -> PruningDecision` is pure:
  computed minor = the pathway with the larger G_p among `rule.pathways`; prune iff ΔΔG‡ >
  `threshold_kcal_mol` (strict) the nodes with `priority ≥ 2` and `pathway == minor`; never
  `pathway=None`; either pathway without a summed member → no pruning, reason
  `no_valid_member:<pathway>`; `signed_ddG_dagger_kcal_mol` keyed `"<b>_vs_<a>"` in rule order;
  `pruned_node_ids` sorted.
- `run_selectivity(...)`: the inputs are the graph's nodes and rules plus, per priority-1 TS node, the
  `TSSpec`, core indices and member gates (the E2E builds them; v0.6.0 has no graph→TS-spec loader;
  keep the inputs explicit). Order: every priority-1 pathway's ensemble (slice 06) → `score_selectivity`
  (slice 04) → each rule → each unpruned priority ≥ 2 node through `run_species`; a pruned node gets
  status `pruned`, no engine call. The result holds the ensembles, the score, the decisions and the
  per-node outcomes; it is what slice 10's candidate serialises.
- Unit tests: a stub graph with two pathways and three priority-2 nodes (minor, major, `None`), stub
  ensembles with ΔΔG‡ at threshold − 0.01, == threshold, threshold + 0.01; the computed major being
  the pathway a test author "expected" to be minor; a pathway with zero members. A
  `CountingEngine` proves zero engine calls for pruned nodes.
- **Seat rules (every slice):** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp); every
  framework script with `python3`; Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`
  (must print `index: ok`); run `hypergraph_updater.py --from-diff <Start> --apply` **once** after
  the commit (re-index first; a rerun needs `git restore spec/compiled/architecture.yml` first and a
  disclosure); never edit `spec/compiled/architecture.yml` by hand; never read `spec/archive/` or
  `tests/candidate_outputs/`; commits under this machine's git identity, ending with exactly
  `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)` (version from `.agents/hacf-manifest.json` at commit
  time), no co-author trailer, never `--no-verify`; stage named files only; no push, tag or promote.
- **Clean room (v0.4.0 Q1, v0.5.0 A1, hard rule):** never open, clone, fetch or search Eta_Scripts or
  nMAP; read no TS-optimizer or conformer-search source (installed `geometric` package internals,
  Sella, pysisyphus, the starter's code beyond naming it in a DV row); geomeTRIC runs only as a black
  box through eta's `GeometricOptimizer`. The mission SPEC is `missions/release-0.6.0/SPEC.md`; its
  R-, HF- and G-rows are cited by number.

## 1. The Confidence Mandate

**Score: 9/10.** R7 removes the ambiguity the red team found; the runner is glue over slices 04/06
and `run_species`.

## Mini-requirements

1. US-006/G2: prune exactly the computed minor's priority ≥ 2, same-pathway nodes iff ΔΔG‡ > threshold;
   none at or below; never `pathway=None`.
2. G2: no pruning with reason when a pathway has no summed member.
3. US-006: the decision record carries rule id, pathways, signed and unsigned ΔΔG‡, threshold, pruned
   ids, reason; pruned nodes have status `pruned` and zero engine calls.
4. No library default threshold (a rule without one is refused at load, slice 02).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read slices 02/04/06 code, `run_species`.
- [x] Task 2: `evaluate_pathway_pruning` + tests.
- [x] Task 3: `run_selectivity` + tests with stub engines.
- [x] Task 4: required checks; commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** add a scheduler, crash resume or graph-wide orchestration (v0.8.0).
- **DO NOT** prune `pathway=None` nodes or use a default threshold.
- **DO NOT** read or copy the starter's pruning code (DV-02, DV-05).

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_selectivity_runner.py -q` passes (G2 cases,
      zero engine calls for pruned nodes).
- [ ] Required checks exit 0.

## Source material

- Mission R7, §5 "Selectivity", G2, G6; slices 02, 04, 06.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

04, 06.
