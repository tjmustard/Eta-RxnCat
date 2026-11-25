---
id: OPR.0.6.0.2
slice: 02-core-contracts
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Add ReactionNode.pathway, a typed evaluable PathwayPruningRule beside the inert PruningRule, and the TS-ensemble and selectivity result models, all additive."
depends_on: [OPR.0.6.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 core contracts — pathway label, typed pruning rule, ensemble and selectivity models

## Intent

Add the additive core contracts v0.6.0 needs: an optional `ReactionNode.pathway`, a typed and
evaluable `PathwayPruningRule` beside the inert free-form `PruningRule`, and the TS-ensemble and
selectivity result models, with every existing graph, cached row and fixture still loading.

Context the builder needs:
- **TJ, verbatim:** Q2 "A: evaluated per-pathway rule in core + optional pathway labels + small
  selectivity runner; 1.5 in the Tier 4 fixture, no library default (the recommendation)."
- Mission R7, R8, R23, R24 and §5 "Contracts" are normative. New module
  `src/eta_rxncat/core/selectivity_models.py`, exported from `eta_rxncat.core`.
- `ReactionNode.pathway: str | None = None` with the id pattern `^[A-Za-z][A-Za-z0-9_.-]*$`.
  `CoreModel` is `extra="forbid", frozen=True`: the default must be `None` so existing YAML loads.
- `PathwayPruningRule`: `id`, `metric: Literal["ddG_dagger_kcal_mol"]`, `pathways: tuple[str, str]`
  (distinct), `threshold_kcal_mol: PositiveFiniteFloat` (**required, no default**),
  `prune: Literal["minor_pathway_priority_ge_2"]`. `ReactionGraph.pathway_pruning_rules:
  list[PathwayPruningRule] = []`. Graph validation: rule ids unique across `pruning_rules` and
  `pathway_pruning_rules`; each named pathway is the `pathway` of at least one priority-1 node.
  The existing `PruningRule` and `tests/data/reaction_graphs/example_reaction_graph.yaml`
  (`barrier_gate`) are untouched and still load.
- `TSEnsembleOptions`: `n_embed` 10, `n_perturb` 10, `perturb_sigma_angstrom` 0.3,
  `pre_dedup_rmsd_angstrom` 0.125, `random_seed` 42, `max_research` 10, `rmsd_dedup_angstrom`
  0.125, `flag_dG_kcal_mol` 0.05, `energy_window_kcal_mol` 3.0, `max_automorphisms` 100000 (strict
  ints, positive finite floats).
- `TSEnsembleMember` (`index`, `source`, `start_sha256`, `G_hartree`, `degeneracy` ≥ 1,
  `rmsd_to_seed_angstrom`, `face: list[int]` of ±1, `validation_passed_bool`, `weight` in [0, 1], `pre_relax_wall_time_s | None` (mission R25)),
  `TSEnsembleExclusion` (`index`, `source`, `reason` from a closed set: mission R19 plus
  `face_undetermined`, `connectivity_changed`; `pre_relax_wall_time_s | None`), `TSEnsembleMerge` (`kept_index`, `merged_index`,
  `dG_kcal_mol`, `rmsd_angstrom`), `TSEnsemble` (mission §5 "Contracts"; weights sum to 1 within
  1e-12 when members exist; `G_pathway_hartree` and `failed_reason` mutually exclusive),
  `PruningDecision` (`rule_id`, `pathways`, `ddG_dagger_kcal_mol | None`,
  `signed_ddG_dagger_kcal_mol: dict[str, float]`, `threshold_kcal_mol`, `pruned_node_ids` sorted,
  `reason`), `SelectivityResult` (US-004 keys, `per_pathway`, `pruning`).
- Units in names; no numpy in core (G8: `import eta_rxncat.core` loads no numpy or RDKit).
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

**Score: 9/10.** Additive pydantic models in the house style (`core/ts_models.py` is the model).
The one judgment call — validators that are strict without breaking existing files — is covered
by the load-everything test.

## Mini-requirements

1. US-002: a graph with `pathway` labels and a `PathwayPruningRule` round-trips YAML/JSON; every
   file under `tests/data/` and every promoted fixture still validates (existing tests unchanged).
2. US-002: invalid rules are refused: missing threshold, threshold ≤ 0, equal pathways, unknown
   pathway, duplicate id across both rule lists, unknown `metric`/`prune`.
3. US-004/005: ensemble and result models validate weights (sum 1 within 1e-12), signs (face
   entries ±1), closed reason sets, and refuse extra fields.
4. G8: `python -c "import eta_rxncat.core, sys; assert 'numpy' not in sys.modules and 'rdkit' not in sys.modules"`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read `core/graph.py`, `core/ts_models.py`.
- [ ] Task 2: `ReactionNode.pathway`; `PathwayPruningRule`; graph validators.
- [ ] Task 3: `core/selectivity_models.py`; exports.
- [ ] Task 4: `tests/unit/core/test_selectivity_models.py`, `test_graph_pathway.py`; required checks.
- [ ] Task 5: commit; updater once (node `eta_rxncat_core`).

## 4. The Negative Space (Constraints)

- **DO NOT** change `PruningRule`, any existing field, or `StageKind` (no new stage kind, R24).
- **DO NOT** give `threshold_kcal_mol` a default.
- **DO NOT** import numpy or RDKit in `eta_rxncat.core`.

## Proof contract

- [ ] `uv run pytest tests/unit/core -q` passes, including the new tests.
- [ ] The G8 core import check prints nothing and exits 0.
- [ ] Required checks exit 0.

## Source material

- Mission §5 "Contracts", R7, R8, R19, R23, R24; `src/eta_rxncat/core/graph.py`,
  `src/eta_rxncat/core/ts_models.py`; `tests/data/reaction_graphs/`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

01 (starter, for the DV row references).
