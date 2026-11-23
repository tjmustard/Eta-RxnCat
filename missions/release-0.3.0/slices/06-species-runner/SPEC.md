---
id: OPR.0.3.0.6
slice: 06-species-runner
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Create eta_rxncat.orchestrator: the single-species stage runner with store caching per stage, counted engine calls, one imaginary-mode push, incremental single points, per-stage metrics, ReactionSpec free energies at 1 atm and 1 M, and a deterministic JSON report writer."
depends_on: [OPR.0.3.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Single-species stage runner with store caching, counted engine calls, reactions and report writer

## Intent

Create `eta_rxncat.orchestrator` (new ledger node `eta_rxncat_species_runner`): a single-species
runner that executes conformer search → optimization → dedup/window → frequency (with one
imaginary-mode push) → thermo → ensemble, caching every stage in the v0.1.0 `ArtifactStore`, adding
single-point stages incrementally, counting engine calls, recording per-stage metrics, computing
reaction ΔG from species ensembles, and writing deterministic JSON reports.

Context the builder needs:
- TJ Q4 "C": the incremental-solvation test runs on this small runner, not the v0.8.0 orchestrator.
- Store: `ArtifactStore(path, *, open_timeout_s=5.0)`; `put(key, status, payload)`, `get(key)`,
  `status(key)`, `query(...)`; completed rows are immutable, an identical re-put is a no-op, a
  different payload on a completed row raises `ArtifactConflictError`; the row timestamp column is
  `created_at_utc`. Keys: `store.keys.build_stage_key(state, stage, engine.identity)` (geometry
  gridded to 1e-5 Å, includes charge and multiplicity); `geometry_payload(state)`.
- Engines: `Engine.from_stage(stage, **runtime)`, `engine.stage` (resolved), `engine.identity`,
  `engine.evaluate(state, *, forces, hessian) -> PotentialResult`. Every engine returns an FD or
  analytic Hessian on `hessian=True`. Errors: `EngineError` → `EngineUnavailableError`,
  `EngineInputError`, `ScfConvergenceError`, `EngineRuntimeError`. `StageConfig(kind, engine,
  method, basis, solvation, frozen_atom_indices, options)`; kinds include `conformer_search`,
  `geometry_opt`, `frequency`, `single_point`. Engine option tables reject unknown keys.
- New node: `ensure-node --id eta_rxncat_species_runner --dimension Module --depends-on
  eta_rxncat_core,eta_rxncat_thermo,eta_rxncat_optimize,eta_rxncat_conformers,eta_rxncat_engines,eta_rxncat_store
  --files 'src/eta_rxncat/orchestrator/**,tests/unit/orchestrator/**,tests/e2e/**,tests/candidate_outputs/v0.3.0/**'
  --associated-file src/eta_rxncat/orchestrator/species.py --description-file <file>`; scaffold loses
  `src/eta_rxncat/orchestrator/**` (full `--files` list).

**Seat rules for every v0.3.0 slice (self-contained; the mission SPEC is `missions/release-0.3.0/SPEC.md`):**
- Branch `feature/eta-rxncat-v0.3.0`, cut re-entrantly from Base `7993284`. One code commit per
  slice; record `Start` (HEAD when you begin) in your handoff.
- First command of the slice: `python3 .agents/scripts/hyper_codegraph.py index`. It must print
  `index: ok`; anything else stops the slice. The audit treats `code_graph.status != ok` as a
  finding. The code graph only widens the blast radius; it never narrows it.
- Ledger: only `hyper_ledger.py` / `hypergraph_updater.py`. Use `ensure-node --id <node>` on
  existing nodes and pass the **full** `--files` list (it replaces). `ensure-node --from-spec` no
  longer drops other slices' files (HACF v0.6.1 E5), but count the node's globs before and after
  anyway. Never edit `spec/compiled/architecture.yml` by hand. `eta_rxncat_engines` is not touched.
- Scratch: `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs). Remove
  temp clones, venvs and scratch directories at the end of each step.
- No `HACF-install.sh`, `HACF-uninstall.sh` or `hyper_migrate.py apply`. Ignore any "review it with
  hyper_migrate.py plan" line (known false positive). On OpenRig 0.7.21, `hyper_spec.py` and
  `hyper_migrate.py` warn "outside the pinned contract" and `hyper_spec.py proof` writes the proof
  natively: expected, note it in the proof, not a finding.
- Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git: every `git diff`,
  `git show`, `git log -p` over a range that contains a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`. Never write `tests/fixtures/`. `PRDs/` is read-only.
- Required checks (AGENTS.md), all exit 0 before the commit: `uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, and
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- Licence (TJ, verbatim): "I would prefer to keep ASE out as it would be a major core dependency.
  The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP,
  conf search can be copy left. Because they can be replaced with a new engine later. But the core
  remains." / "It's fine that the engine MACE pulls in ASE just not the core." No agent-made
  licence exception.
- A host fact that does not hold, a failed engine run, or a bound that measured noise breaks is
  stop-and-report to the lead with the output — never worked around, never a loosened tolerance.
- Never push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 9/10.** Keys, payloads, counting and drop rules are fixed; the tests use the fast
`rdkit_ff`/`uff` engine and an in-memory fake.

## Mini-requirements

1. `orchestrator/counting.py` `CountingEngine(engine)`: delegates `stage`, `identity`,
   `evaluate`; counts `evaluate` calls per runner stage kind (the runner sets the current kind).
2. `orchestrator/species.py`:
   - `SpeciesSpec(species_id, smiles, charge, spin_multiplicity, conformer_options,
     seed_geometries=())`; `Recipe(name, engine_stage: StageConfig, optimizer: Optimizer,
     optimizer_options, thermo_config=ThermoConfig(), analysis=ThermoAnalysisOptions(),
     engine_runtime={})`.
   - `run_species(spec, recipe, store, *, single_points=(), energy_source="optimization") ->
     SpeciesResult(ensemble, dropped, single_point_energies, metrics)`.
   - **conformer_search** (0 engine calls): `StageConfig(kind="conformer_search", engine=recipe
     engine tag, method=recipe method, options=conformer options ∪ {smiles: canonical isomeric,
     rdkit_version, seed_geometries_sha256})`; key geometry = pass-1 embedding 0 (RDKit runs before
     the lookup, intended). Payload: pool members (id, origin, xyz), failure counts, pre-dedup
     survivors, resolved options.
   - **geometry_opt** per survivor: options = resolved engine options ∪ resolved optimizer options
     with `opt.` prefix ∪ `opt.name`, `opt.version`; the engine is built from the stage **without**
     the `opt.` keys. Key geometry = the member's input geometry. Payload: final xyz, final energy,
     n_steps, n_engine_calls, recovery_steps, optimizer identity, options.
   - dedup and window (conformers), then **frequency** per kept: `hessian=True` on the optimized
     state; payload energy + Hessian (full matrix). Thermo recomputed from it, never stored.
   - Imaginary-mode push (once per conformer): displace along the lowest imaginary mode (Cartesian
     displacement scaled so the largest atomic displacement is 0.1 Å) in both directions, optimize
     each as a **new** `geometry_opt` row keyed on the displaced geometry, keep the lower energy,
     append `imag_mode_push` to `recovery_steps`, new frequency row; still imaginary → drop
     `not_a_minimum`.
   - Degeneracy, mirror-partner drop, `build_ensemble`.
   - `run_constrained_point(spec, recipe, store, start_state, *, frozen_atom_indices=(),
     dihedral_constraints=()) -> ConstrainedPoint(state, energy_hartree, optimization, cache_hit)`
     (R42; used by slice 08 for T1's planar s-cis point): one `geometry_opt` row keyed on
     `start_state` with the usual engine and `opt.` options **plus `opt.constraints`** = the
     optimizer's `constraints_text(...)` (present only when constrained, so unconstrained keys are
     unchanged); payload as other `geometry_opt` rows. No frequency, no thermo, no G, never an
     ensemble record (a constrained geometry is stationary only within the constraint). Counted and
     metered like any stage (`engine_calls`, `cache_hits` under `geometry_opt`).
   - Drop rule: drop a conformer (with reason) on `OptimizationFailedError`, `ScfConvergenceError`
     or `NotAMinimumError` after the push; `EngineUnavailableError`, `EngineInputError`,
     `EngineRuntimeError`, `OptimizerInputError` propagate. All dropped → `EnsembleEmptyError`.
   - **single_point** stages (`single_points`: `StageConfig`s, optional `only_lowest: bool`) per
     kept record on its optimized state; stored like v0.2.0 stages. `energy_source="single_point"`
     requires the SP geometry payload to equal the frequency stage's, else `ThermoInputError` (R35).
   - Metrics per stage kind: `wall_time_s`, `engine_calls` (CountingEngine), `cache_hits`,
     `rows_created`; plus `optimizer_steps_total`, `recovery_steps`.
3. `orchestrator/reaction.py` `ReactionSpec(reactants, products)` (frozen pydantic; `(species_id,
   coeff: PositiveInt)`; validator: atoms by element and total charge conserved given each species'
   formula and charge) and `reaction_free_energy(spec, ensembles, config) -> ReactionEnergies(dE,
   dH, dG_1atm, dG_1M, delta_n)` with ΔG(1 M) − ΔG(1 atm) = Δn·RT ln(c°RT/p°).
4. `orchestrator/report.py` `write_report(path, payload: Mapping)`: JSON `schema: 1`, floats via
   `repr` (round-trip exact), sorted keys, LF, trailing newline; `ensemble_to_payload(...)` with
   per-record E, G, ZPE, S components, σ, g, weight, lowest 6 frequencies, xyz.

## 3. Implementation Plan (Task List)

- [x] Task 1: ledger node; `counting.py` + tests.
- [x] Task 2: `species.py` stages and keys + tests with `rdkit_ff`/`uff` on butane (small
  `n_embed`) and a fake engine for the push and drop paths.
- [x] Task 3: `reaction.py`, `report.py` + tests.
- [x] Task 4: incremental test `tests/unit/orchestrator/test_incremental_stage.py`.
- [x] Task 5: `hypergraph_updater.py --from-diff`; required checks; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** store `ThermoResult` or overwrite a gas-phase G with a solvated value.
- **DO NOT** pass `opt.` keys to an engine; **DO NOT** reuse a key with a different payload.
- **DO NOT** catch `EngineUnavailableError`, `EngineInputError`, `EngineRuntimeError`.
- **DO NOT** change `store/` or any engine.

## Proof contract

- [ ] Two runs of the same species/recipe into fresh stores → byte-identical keys for every stage.
- [ ] Rerun into the same store → `CountingEngine` total 0; every stage `cache_hits` = its row
  count; `rows_created` 0.
- [ ] Adding one gas single point (`rdkit_ff`, uff) on the rerun → exactly `n_kept` engine calls;
  every conformer_search/geometry_opt/frequency row has the same key and the same `created_at_utc`
  as before (read via the store); rows created == counted misses.
- [ ] Fake engine with one imaginary mode at the first frequency → `imag_mode_push` recorded, a
  new `geometry_opt` row with a different key; persistent imaginary mode → dropped
  `not_a_minimum`; all dropped → `EnsembleEmptyError` carrying each reason.
- [ ] `EngineInputError` from the fake engine propagates out of `run_species`.
- [ ] `energy_source="single_point"` with an SP on a different geometry → `ThermoInputError`.
- [ ] `run_constrained_point` on butane (`rdkit_ff`/uff) with `DihedralConstraint((0, 1, 2, 3),
  0.0)`: |φ| ≤ 0.1°; its key differs from the unconstrained `geometry_opt` key of the same start;
  a rerun is a cache hit with 0 engine calls; no frequency row is created for it.
- [ ] `ReactionSpec` rejects a non-conserving reaction; Δn = −1 gives ΔG(1 M) − ΔG(1 atm) =
  −1.8943 kcal/mol ± 1e-4 at 298.15 K.
- [ ] `write_report` output re-parses to equal floats exactly and is byte-identical across two
  writes (`tmp_path`).
- [ ] Required checks exit 0.

## Source material

- Mission §5 R7, R15, R18, R35, R42, "Contracts" (stage keys, `ReactionSpec`, candidate output);
  ADR-0001, ADR-0002, ADR-0016; `src/eta_rxncat/store/`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.3, OPR.0.3.0.4, OPR.0.3.0.5
