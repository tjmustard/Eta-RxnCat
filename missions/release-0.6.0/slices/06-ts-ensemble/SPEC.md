---
id: OPR.0.6.0.6
slice: 06-ts-ensemble
mission: release-0.6.0
status: done
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Add run_ts_ensemble: sample, cached core-frozen pre-relax, P-RFO re-search and validation, face and connectivity checks, dedup on shape and face, energy window and Boltzmann weights, with every exclusion recorded."
depends_on: [OPR.0.6.0.3, OPR.0.6.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_ts_ensemble.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 TS ensemble runner

## Intent

Add `run_ts_ensemble`: from a verified seed TS, sample core-frozen conformers, pre-relax each with
the core frozen (cached), re-search and validate each with P-RFO, keep only members of the seed's
reaction and face, merge re-converged copies, apply the energy window and Boltzmann-weight the rest,
recording every exclusion, so a pathway's G counts each distinct accessible TS exactly once.

Context the builder needs:
- Mission §5 "Ensemble runner" (normative), R1, R2, R3, R5, R8, R11, R17, R19, R24; G4 (runner parts),
  G7, G8. Module `src/eta_rxncat/orchestrator/ts_ensemble.py`, node `eta_rxncat_species_runner`.
- Signature: `run_ts_ensemble(seed: TSSpec, recipe: TSRecipe, store: ArtifactStore, *, optimizer:
  Optimizer, core_indices: Sequence[int], pathway: str, reactant_key, options: TSEnsembleOptions,
  member_gates: Callable[[TSRunResult], Mapping[str, bool]]) -> TSEnsemble`. The optimizer is
  injected (the E2E passes `GeometricOptimizer()`; unit tests a stub `Optimizer`); this module never
  imports geomeTRIC (G8).
- Pre-relax cache (R5/R24): key = `build_stage_key(sample.state, StageConfig(kind=
  "constrained_preopt", engine=…, method=…, frozen_atom_indices=sorted(core), options=engine options
  + "opt.*" resolved minimize options + opt.name/opt.version), engine identity)`; call
  `relax_constrained_core(sample.state, engine, optimizer, core, options={"maxiter": 200})`; cache
  the final geometry (and energy) or a failure row (`pre_relax_failed:<ErrorClass>` for
  `CoreDisplacementError`/`OptimizerError`, `engine_error` for `EngineRuntimeError`). The engine for
  the pre-relax is built once per ensemble from the recipe (`build_engine`) and wrapped in
  `CountingEngine` for metrics.
- Per member after pre-relax: `run_transition_state(TSSpec(ts_id=f"{seed.ts_id}:{source}",
  start=relaxed, forming_bonds=seed.forming_bonds), recipe, store)`; then, in order: failure →
  exclusion with its `failed_reason`; `member_gates` false → `gate_failed:<first failing check>`;
  perceived bonds ≠ seed's → `connectivity_changed`; face (slice 05, seed's graph) ≠ seed's →
  `face_mismatch` (`FaceDescriptorError` → `face_undetermined`).
- Dedup (R2) over valid members sorted by G: merge into the first kept member with RMSD <
  `rmsd_dedup_angstrom` (seed-graph automorphisms, with H) **and** equal face; record every merge;
  `flagged_merges` where |ΔG| > `flag_dG_kcal_mol`. Then the energy window (R17) → `outside_window`
  exclusions. Weights: g_i exp(−(G_i − G_min)/RT) normalised; `G_pathway_hartree` by log-sum-exp;
  `degeneracy` from each `TransitionStateRecord`.
- Seed rule: the seed runs first; if it fails its search or gates, nothing is sampled and the
  ensemble's `failed_reason` is `seed:<reason>`.
- Member gates for Tier 4 come from the E2E (slice 09), not from this module: GFN2 = mode count +
  identity core (overlap ≥ 0.50, in phase) + active core (KE ≥ 0.60) per Q-TJ4 A; UMA = mode count +
  active core + full `identity_passed_bool`.
- Metrics per stage kind (`constrained_preopt`, `ts_opt`, `frequency`): engine calls, cache hits,
  rows created, wall time — G7 checks them. Each member and exclusion records
  `pre_relax_wall_time_s` (mission R25, HF-13: one UMA pre-relax stalled > 14 min in resolve's run).
- **Measured (HF-10, HF-11):** on Tier 4 every member re-converges to the seed's saddle (RMSD ≤ 4e-5 Å,
  |ΔG| ≤ 0.0021 kcal/mol on GFN2) and keeps the seed's face; one perturbed sample in 44 failed the
  pre-relax core bound. Your E2E-free unit tests use stub surfaces; Tier 4 runs are slices 09–10.
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

**Score: 9/10.** Composition of tested pieces (`relax_constrained_core`, `run_transition_state`,
slice 05) with a cache wrapper in an existing pattern; resolve ran the same flow end to end on both
engines (HF-10). Residual risk: stub surfaces with two saddles of the same forming bonds take care to
build; the spec names the cases.

## Mini-requirements

1. US-008/G4: on a stub engine with two known saddles (different non-core geometry, same face) and
   re-converging samples, the ensemble holds exactly the two saddles; re-converged copies merge even
   with |ΔG| up to 0.04 kcal/mol (and are flagged above 0.05); merged copies are summed once.
2. US-008/G4/R1: a stub that converges a sample onto the opposite-face saddle excludes it as
   `face_mismatch`; a connectivity change → `connectivity_changed`.
3. US-008/R19: every exclusion reason in mission R19 is produced by a test and recorded with source
   and index; the pathway fails only with no summed member; a failing seed stops sampling.
4. US-005: weights sum to 1 within 1e-12; `G_pathway_hartree` equals the closed form; g = 2 respected.
5. G7: a second call in the same store: `constrained_preopt`, `ts_opt`, `frequency` all hits, zero
   rows, equal `TSEnsemble` (history excluded).
6. G4: pre-relaxation moves the core ≤ the ADR-0032 bound (`CORE_FREEZE_TOLERANCE_ANGSTROM`).
7. G8: importing the module loads no `torch`, `pyscf`, `fairchem`, `geometric`.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `orchestrator/ts.py`,
      `mapping/relax.py`, `store/keys.py`, slice 05's module.
- [x] Task 2: the pre-relax cache wrapper and its tests.
- [x] Task 3: `run_ts_ensemble` (seed, sample, members, exclusions, dedup, window, weights).
- [x] Task 4: `tests/unit/orchestrator/test_ts_ensemble.py` (requirements 1–7); required checks.
- [x] Task 5: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** sum a member that fails gates, connectivity or face; **DO NOT** drop an exclusion.
- **DO NOT** keep two members that share a shape and face, whatever their ΔG.
- **DO NOT** import geomeTRIC; **DO NOT** edit `mapping/` or `optimize/` (read only).
- **DO NOT** add a stage kind (R24).

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_ts_ensemble.py -q` passes (requirements 1–7).
- [ ] Required checks exit 0.

## Source material

- Mission §5 "Ensemble runner", R1–R3, R5, R8, R11, R17, R19, R24, HF-10, HF-11.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

03, 05 (and 02).
