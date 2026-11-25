---
id: OPR.0.6.0.4
slice: 04-scorer
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Add score_selectivity, a pure function giving Boltzmann-summed pathway G, ddG dagger, ratio and selectivity percent (ee, de or regio) in closed form with no heavy imports."
depends_on: [OPR.0.6.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", src/eta_rxncat/thermo/__init__.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_selectivity_score.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 selectivity scorer (pure)

## Intent

Add `score_selectivity`, a pure function that turns competing pathways' TS ensembles into
Boltzmann-summed pathway free energies, ΔΔG‡, the product ratio and the selectivity percentage
(ee, de or regio), with closed-form accuracy and no engine, RDKit or geomeTRIC import.

Context the builder needs:
- Mission §5 "Selectivity", R8, R12, G1, G8. Module `src/eta_rxncat/orchestrator/selectivity.py`.
- G_p = −RT ln Σ_i g_i exp(−G_i/RT) over **summed** members, computed as log-sum-exp in kcal/mol
  (`HARTREE_KCAL_MOL`; R from `eta_rxncat.thermo` constants, ADR-0026). Two pathways: ΔΔG‡ =
  G_minor − G_major ≥ 0, r = exp(ΔΔG‡/RT), % = 100 (r − 1)/(r + 1); `signed_ddG_dagger_kcal_mol` keyed
  `"<b>_vs_<a>"` for pathways in sorted-name order (slice 07 re-keys by rule order). N > 2: fractions
  by softmax of −G_p/RT, `ddG_dagger_kcal_mol` = G_second − G_major, `selectivity_percent` = the
  major's fraction × 100.
- Refuse (`SelectivityInputError`, a `ValueError`): fewer than two pathways; a pathway with no summed
  member (`failed_reason` set); mixed `temperature_k`, `reactant_key` or `recipe_identity`
  (engine name, model, version); `temperature_k` ≠ the call's; `kind="ee"` when any pathway has > 1
  member (DV-08).
- G1 cases (closed form within 1e-12): two single-member; multi-member (weights sum to 1); g = 2;
  tie (50 %); ΔΔG‡ = 200 kcal/mol (no overflow, no clamp; ratio may be `inf` only if the float
  overflows — then report `ratio = inf` and `selectivity_percent = 100.0` exactly, tested); T = 350 K;
  permutation invariance (pathways and members). Starter check: 1.7 kcal/mol, 298.15 K → 89.2 ±
  0.5 %. Red team's check: +1.849 → 91.5 % de, +4.273 → 99.85 % de (to 0.05).
- G8: a subprocess test imports `eta_rxncat.orchestrator.selectivity` and asserts none of `torch`,
  `pyscf`, `fairchem`, `geometric`, `rdkit` is in `sys.modules`. If `eta_rxncat.orchestrator`'s
  package `__init__` pulls in heavy modules, import the selectivity module so that it does not (lazy
  exports in `orchestrator/__init__.py` are acceptable; record what changed).
- **Replan 1 (mission R26, lead ruling A):** `import eta_rxncat.thermo.constants` loads RDKit today,
  because `thermo/__init__.py` eagerly imports `symmetry.py` and `masses.py` (`from rdkit import
  Chem`); measured at `808e50c`. Make `src/eta_rxncat/thermo/__init__.py`'s exports lazy (PEP 562
  module `__getattr__` mapping each public name to its submodule, the same imports under
  `TYPE_CHECKING` for mypy, `__all__` unchanged), so every existing `from eta_rxncat.thermo import X`
  still works and the scorer imports the real constants from `eta_rxncat.thermo.constants`. Blast
  radius gains node `eta_rxncat_thermo` (it already owns `src/eta_rxncat/thermo/**`; no ledger
  write).
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

**Score: 9/10.** Closed-form math. The one risk is the orchestrator package's import graph for G8,
which the subprocess test settles.

## Mini-requirements

1. US-004/G1: every G1 case within 1e-12; the three literature checks.
2. US-005: weights per member, summing to 1 within 1e-12, order-free.
3. US-004: every refusal raises `SelectivityInputError` with the offending field named.
4. G8: the import test passes.
5. R26: every name in `eta_rxncat.thermo.__all__` still imports (`from eta_rxncat.thermo import X`
   for each, test), the existing thermo tests pass unchanged, and a subprocess test shows
   `import eta_rxncat.thermo.constants` leaves `rdkit` out of `sys.modules`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read `thermo` constants, slice 02 models.
- [ ] Task 2a: lazy `thermo/__init__.py` (R26) + its tests (requirement 5).
- [ ] Task 2: `orchestrator/selectivity.py` (`score_selectivity`, `SelectivityInputError`); export.
- [ ] Task 3: `tests/unit/orchestrator/test_selectivity_score.py` (G1, refusals, G8); required checks.
- [ ] Task 4: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** clamp exponents or define local physical constants (DV-03).
- **DO NOT** call an engine, RDKit or geomeTRIC from the scorer.
- **DO NOT** read or copy the starter's `selectivity.py`.
- **DO NOT** change thermo behaviour, any thermo constant or value, or any thermo submodule; R26
  touches only `thermo/__init__.py`'s import mechanics. **DO NOT** move the constants (lead ruling:
  not option B).

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_selectivity_score.py -q` passes.
- [ ] The G8 subprocess test passes; the R26 thermo import tests pass; required checks exit 0.

## Source material

- Mission §5 "Selectivity", G1, G8, R8, R12; slice 02 models; `src/eta_rxncat/thermo/`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

02.
