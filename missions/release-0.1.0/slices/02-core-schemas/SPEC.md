---
id: OPR.0.1.0.2
slice: 02-core-schemas
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the strict Pydantic v2 core data contracts and a duplicate-key-rejecting YAML/JSON ReactionGraph loader and validator, with a test for every invariant."
depends_on: [OPR.0.1.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", "tests/data/**", docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Core schemas, ReactionGraph loader and validator

## Intent

Implement the strict Pydantic v2 data contracts in `eta_rxncat.core` (molecular state, mapping
spec, stage, engine identity, thermo, template, node, edge, pruning rule, graph) and a YAML/JSON
loader that rejects duplicate keys, with unit tests for every invariant.

Context the builder needs (self-contained): every later Eta-RxnCat version (engines v0.2.0,
conformers v0.3.0, mapper v0.4.0, orchestrator v0.8.0) imports these models, so every invariant
here is a contract. The plan's core promise: explicit per-step `charge` and `spin_multiplicity`,
never silently defaulted or coerced. The v0.1.0 starter under
`docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/` is **reference only**: write fresh code,
record every difference in `docs/prd/v0.1.0/DISCREPANCIES.md`. Node `eta_rxncat_core` is **not yet
in the graph**: register it with `python3 .agents/scripts/hyper_ledger.py ensure-node --from-spec
<this SPEC.md> --dimension Module`.

## 1. The Confidence Mandate

**Score: 9/10.** Every field, default and invariant is fixed below. Residual: the mapping
partition rule (Mini-requirement 3, keep ∪ delete = all atoms) is a deliberate strict-first choice
that TJ may relax later; implement it as written.

## Mini-requirements

1. US-005 `MolecularState` (`core/molecule.py` or similar; all models `ConfigDict(extra="forbid",
   frozen=True)`): `symbols: list[str]` (≥ 1, each exactly a canonical element symbol Z 1–118 —
   `Fe` ok; `fe`, `FE`, `Xx` raise); `coordinates: list[list[float]]` Å, N×3 with N =
   `len(symbols)`, every value finite; `charge: StrictInt` (required); `spin_multiplicity:
   StrictInt ≥ 1` (required); `active_atom_indices: list[StrictInt] = []` (unique, 0 ≤ i < N);
   `metadata: dict[str, str | int | float | bool] = {}`. Electron check with
   n_e = Σ Z(symbol) − charge: n_e ≥ 0, `spin_multiplicity − 1 ≤ n_e`,
   `(n_e − (spin_multiplicity − 1)) % 2 == 0`. StrictInt must reject `True`, `"1"` and `1.0`.
2. `StageConfig`: `kind ∈ {conformer_search, constrained_preopt, geometry_opt, frequency,
   single_point}`; `engine ∈ {rdkit_ff, mace, uma_direct, pyscf_gpu_cpu, xtb_subprocess}`;
   `method: str` (non-empty; `default` in any case raises); `basis: str | None` (non-empty
   required iff engine is `pyscf_gpu_cpu`, else must be `None`); `solvation: Solvation =
   Solvation()`; `frozen_atom_indices: list[StrictInt] = []` (unique, ≥ 0; non-empty required when
   kind is `constrained_preopt`); `options: dict[str, str | int | float | bool] = {}` (finite
   floats). `Solvation`: `model ∈ {none, ddcosmo, pcm, alpb}` (default `none`), `solvent: str |
   None = None`, `dielectric: float | None = None` (> 0, finite); `none` requires both `None`;
   other models require at least one; `ddcosmo`/`pcm` only with `pyscf_gpu_cpu`, `alpb` only with
   `xtb_subprocess` (checked on `StageConfig`). `EngineIdentity`: `name` (an engine tag),
   `version: str` (non-empty), `model: str | None = None`.
3. US-006 `AtomMappingSpec`: ordered `keep`, `delete`, `alignment: list[StrictInt]`,
   `anchors: list[StrictInt] = []`. Raises when: any index < 0; a duplicate inside any list;
   keep ∩ delete ≠ ∅; alignment ⊄ keep; `len(alignment) < 3`; anchors ⊄ keep. At
   `TemplateGeometry` level with N template atoms: any index ≥ N raises; keep ∪ delete ≠
   {0 … N−1} raises. Order of every list survives YAML → model → JSON → model.
4. US-008 `ThermoConfig`: `entropy_model: Literal["grimme_qrrho"] = "grimme_qrrho"`,
   `temperature_k = 298.15`, `pressure_atm = 1.0`, `standard_state_mol_l = 1.0`,
   `qrrho_cutoff_cm1 = 100.0`, `qrrho_alpha = 4.0`, `qrrho_rotor_moment_kg_m2 = 1.0e-44`; every
   numeric field a finite float > 0; `None` for any of them raises.
5. Graph models: `Component(state: MolecularState, count: StrictInt ≥ 1, label: str | None =
   None)`; `TemplateGeometry(id: str, rank: StrictInt ≥ 1, components: list[Component] ≥ 1,
   mapping: AtomMappingSpec | None = None)` — atom index space = concatenation of the components'
   atoms in listed order, each component once; `ReactionNode(id matching
   ^[A-Za-z][A-Za-z0-9_.-]*$, label: str, kind ∈ {reactant, intermediate, transition_state,
   product, off_cycle_sink}, priority: StrictInt ≥ 1, templates ≥ 1 with unique id and unique
   rank, stages: list[StageConfig] | None = None, pruning_rules: list[str] = [])` — all templates
   of a node have equal Σ(count × charge) and equal element multiset Σ(count × symbols);
   `ReactionEdge(source, target, label: str | None = None)`; `PruningRule(id, description: str,
   parameters: dict[str, str | int | float | bool] = {})`; `ReactionGraph(schema_version:
   Literal[1] (required), name: str, nodes ≥ 1, edges = [], default_stages = [], thermo =
   ThermoConfig(), pruning_rules = [])`. Graph raises on: duplicate node id, duplicate rule id,
   edge endpoint not a node id, self-loop, duplicate (source, target), node rule ref not defined.
   Cycles are valid. `priority_order() -> list[str]` sorts node ids by `(priority, id)`.
6. US-007 loader (`core/io.py` or similar): `load_reaction_graph(path: Path) -> ReactionGraph`
   — `.yaml`/`.yml` via a `yaml.SafeLoader` subclass that raises on a duplicate mapping key with
   the key and line; `.json` via `json.loads(..., object_pairs_hook=…)` that raises on a duplicate
   key; any other suffix raises naming it. Every failure (I/O, YAML/JSON syntax, duplicate key,
   pydantic validation) is re-raised as `GraphValidationError(message)` whose message names the
   offender (node id, key, path or field location). `dump_reaction_graph_json(graph) -> str`.
7. Example graph `tests/data/reaction_graphs/example_reaction_graph.yaml`: `schema_version: 1`,
   ≥ 3 nodes (one a `transition_state`, two priority tiers), ≥ 2 edges, one template with a valid
   `mapping`, one node with a two-component template (e.g. separated A + B, `count` 1 each), one
   `pruning_rules` entry referenced by a node, default stages, chemically valid charge/
   multiplicity for every state. It must load with no error.
8. US-011 (core + fixture areas): `docs/prd/v0.1.0/DISCREPANCIES.md` sections `## Core`,
   `## Fixture`, `## Tests` gain one row per starter item (every public top-level name, public
   field and public method of `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/*.py`; every
   top-level and node/edge/template key of the starter fixture; every test function in the starter
   `tests/unit/test_core_schemas.py`) and `added` rows for rewrite items absent from the starter.
   Starter models outside v0.1.0 scope — `ConformerEnsemble`, `PotentialResult`, `ThermoResult`,
   `VibrationalMode`, any connectivity validation — are `dropped` rows, reason "mission R8: defined
   by its consuming version". Status `open`.

## 3. Implementation Plan (Task List)

- [ ] Task 1 — Element table (Z 1–118 symbols, canonical case) as an immutable module constant
  (tuple/`MappingProxyType`), not a mutable global.
- [ ] Task 2 — `MolecularState` with field and model validators (Mini-requirement 1).
- [ ] Task 3 — `Solvation`, `StageConfig`, `EngineIdentity` (Mini-requirement 2).
- [ ] Task 4 — `AtomMappingSpec` self-checks (Mini-requirement 3, first half).
- [ ] Task 5 — `ThermoConfig` (Mini-requirement 4).
- [ ] Task 6 — `Component`, `TemplateGeometry` (index-space checks), `ReactionNode`,
  `ReactionEdge`, `PruningRule`, `ReactionGraph`, `priority_order()` (Mini-requirement 5).
- [ ] Task 7 — Duplicate-key YAML loader and JSON hook, `load_reaction_graph`,
  `dump_reaction_graph_json`, `GraphValidationError` (Mini-requirement 6).
- [ ] Task 8 — Example graph (Mini-requirement 7).
- [ ] Task 9 — Tests under `tests/unit/core/` (one test per bullet of the Proof contract).
- [ ] Task 10 — `core/__init__.py` re-exports the public names; register rows (Mini-requirement 8).
- [ ] Task 11 — Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`; all exit 0.

## 4. The Negative Space (Constraints)

- **DO NOT** import anything in `eta_rxncat.core` except the stdlib, `numpy`, `pydantic`, `yaml`
  (no `eta_rxncat.store`, `eta_rxncat.utils`, `torch`, `pyscf`, `rdkit`, `gpu4pyscf`, `cupy`,
  `mace`, `fairchem`).
- **DO NOT** give `charge` or `spin_multiplicity` a default, or use a coercing `int` for them.
- **DO NOT** use `yaml.load`, `yaml.full_load`, `yaml.unsafe_load` or `pickle`.
- **DO NOT** implement hashing or cache keys here (the store slice owns them), any engine,
  mapper, connectivity validation or pruning evaluation.
- **DO NOT** add models outside Mini-requirements 1–5.
- **DO NOT** copy starter code; **DO NOT** write to `tests/fixtures/`.
- **DO NOT** let any model accept unknown keys (`extra="forbid"`).

## Proof contract

- [ ] Missing `charge` → `ValidationError`; missing `spin_multiplicity` → `ValidationError`.
- [ ] `charge` given as `"1"`, `1.0` or `True` → `ValidationError` (three cases); same for `spin_multiplicity`.
- [ ] `spin_multiplicity=0` → error; symbols `["fe"]`, `["Xx"]` → error; 2 symbols with 3 coordinate rows → error; a coordinate row of length 2 → error; `float("nan")` / `float("inf")` coordinate → error.
- [ ] Active index `-1`, `N`, or duplicated → error; unknown key `chrage` → error.
- [ ] Neutral H₂O with multiplicity 2 → error; neutral H₂O multiplicity 1 → ok; H₂O⁺ (charge 1) multiplicity 2 → ok; H atom charge 2 → error (n_e < 0).
- [ ] StageConfig: `method="default"` / `"Default"` → error; pyscf without basis → error; xtb with basis → error; `ddcosmo` with `xtb_subprocess` → error; `alpb` with `pyscf_gpu_cpu` → error; `pcm` with neither solvent nor dielectric → error; `constrained_preopt` with empty frozen atoms → error; unknown engine tag `xtb` → error.
- [ ] AtomMappingSpec: overlapping keep/delete, duplicate in keep/delete/alignment/anchors, alignment index in delete, alignment not in keep, 2 alignment atoms, anchor not in keep, negative index → error (one test each); at template level index ≥ N and keep ∪ delete ≠ all atoms → error; list order preserved after YAML→model→JSON→model.
- [ ] `ThermoConfig()` has exactly the defaults of Mini-requirement 4; `temperature_k=0`, `standard_state_mol_l=None`, `qrrho_cutoff_cm1=-1` → error.
- [ ] Graph: duplicate node id, unknown edge endpoint, self-loop, duplicate edge, undefined pruning-rule ref, two templates with different total charge, duplicate template rank → `GraphValidationError` whose message contains the offending id.
- [ ] A 3-node cycle A→B→C→A validates; `priority_order()` on tiers {B:1, A:1, C:2} → `["A","B","C"]`.
- [ ] YAML with `charge:` twice in one mapping → `GraphValidationError` naming `charge`; JSON with a duplicate key → error; `graph.toml` → error naming `.toml`.
- [ ] `load_reaction_graph(example)` succeeds; YAML → model → `dump_reaction_graph_json` → model is equal (`==`).
- [ ] `python -c "import eta_rxncat.core, sys; assert not {'torch','pyscf','rdkit','gpu4pyscf','cupy'} & set(sys.modules)"` (as a subprocess test) → exit 0.
- [ ] `grep -rnE 'yaml\.(load|full_load|unsafe_load)\(|pickle' src/eta_rxncat/core` → no match.
- [ ] Four gates exit 0; DISCREPANCIES.md has a row for every core/fixture/test starter item.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (v0.1.0 PR #3; Module Boundary `core/`).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/{models,reaction_graph,__init__}.py`, `tests/e2e/fixtures/example_reaction_graph.yaml`, `tests/unit/test_core_schemas.py` (reference only).
- Mission `missions/release-0.1.0/SPEC.md` §5 Contracts and trade-off log R6, R8, R9, R18, R19, R22, R23.

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.1 (scaffold: package, gates, register file)
