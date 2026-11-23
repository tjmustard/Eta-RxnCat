---
id: OPR.0.3.0
mission: release-0.3.0
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope mission create)"
created: "2026-11-23"
intent: "Eta-RxnCat v0.3.0: generate, optimize and Boltzmann-average conformer ensembles with Grimme quasi-RRHO 1 M thermochemistry behind a replaceable optimizer interface, proved end to end on Human Fixtures 1 and 2."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0001, ADR-0003, ADR-0007, ADR-0010, ADR-0011, ADR-0013, ADR-0014, ADR-0016, ADR-0019, ADR-0020, ADR-0021, ADR-0022]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.3.0 — Conformers, GS Optimization & Boltzmann Ensemble Gate (Human Fixtures 1–2, 5-Tier T1–T2)

## Intent

v0.3.0 is the third of ten versions. For one species given as a SMILES with an explicit charge and
multiplicity, it generates conformers, optimizes them behind a replaceable `Optimizer` interface,
computes harmonic frequencies and Grimme quasi-RRHO thermochemistry at the 1 M standard state, and
Boltzmann-averages the ensemble with mirror degeneracy. A small single-species stage runner caches
every stage in the v0.1.0 store, so a rerun or an added solvation single point recomputes nothing
upstream. Reactions are small species/stoichiometry specs, not `ReactionGraph`s.

The pipeline is proved end to end with two recipes (GFN2-xTB default, UMA second) on Human
Fixture 1 (n-butane), Human Fixture 2 (butadiene + ethylene → cyclohexene) and Tiers 1–2 of TJ's
5-tier suite (1,3-dimethoxybutadiene; cyclopentadiene + cyclopropene → endo P1a_n). Outputs go to
`tests/candidate_outputs/v0.3.0/` for TJ to review and promote (Phase 3), and v0.3.0 is accepted
only by a verdict run after TJ's promotion.

- **Base:** `7993284` (main: v0.2.0 `6523be1` + the HACF v0.6.1 upgrade commit; lead decision,
  2026-11-23 03:2xZ). The builder cuts `feature/eta-rxncat-v0.3.0` from it.
- **Inputs compiled:** `Draft_PRD.md` rev 2 (sha256 `271a711f7594022794ad3c1ecde9e74b2fbdee2b407e4f9adce7f6a38580bd8d`)
  and `RedTeam_Report.md` Parts A–D (sha256 `850c776b4e84ac2e385c29ec4c98aaea3b4ad132ec665ee8858813f29bb74c44`,
  F1–F32). Both are archived; a restore copy is in `spec/process/eta-rxncat-v0.3.0-drafts/`. This
  SPEC is self-contained: nothing below needs the draft to be read.
- **Author:** the decisions are TJ's (Thomas J. L. Mustard Ph.D.), quoted verbatim; the design
  resolutions are spec-resolve's, each logged in §5 "Resolved trade-off log".

### TJ decisions (verbatim; binding)

| # | TJ | Row | Meaning |
|---|---|---|---|
| Q1 | "Q1. C" | `qitem-20261123010133-eec9e1571c70ac8d` | The team drafts HF1 (n-butane anti/gauche) and HF2 (1,3-butadiene + ethylene → cyclohexene, 1 M) and runs them into `tests/candidate_outputs/v0.3.0/` for TJ to promote. TJ supplies the reference values (request `qitem-20261123015428-cc83f02a1853ab80`, open). |
| Q2 | "Q2. A" | `qitem-20261123010134-8e2f9ac01e3e1394` | Default recipe GFN2-xTB end to end (`xtb_subprocess`/`gfn2`). Second recipe UMA end to end (`uma_direct`/`uma-s-1p2p1`). Both run every fixture at acceptance. |
| Q3 | "Q3. A" | `qitem-20261123010134-70adc3a1bbc6ff7b` | An `Optimizer` interface. geomeTRIC is one optimizer in the optional extra `opt-geometric`, which carries its licence exemption. Core and the base runtime install never import it. |
| Q4 | "Q4. C" | `qitem-20261123010134-cd43c1fb3e761e27` | Plan scope plus the zip's done criteria. The incremental-solvation test runs on the small species runner (not the v0.8.0 orchestrator); benchmark metrics go in the acceptance record. |
| Q5 | "Q5 tolerance, I agreed on recommendation of A" | `qitem-20261123015428-9acc6f78ed4b8b62` | Regression (both recipes): lowest conformer class exact, \|ΔE\| ≤ 1e-5 Eh, G/ΔG ≤ 0.05 kcal/mol, weights ±0.02 absolute. Accuracy gated for UMA only: butane gauche − anti within 0.5 kcal/mol, Diels–Alder ΔG within 2.0 kcal/mol of TJ's values; xtb deviation reported. |
| Q-E1 | "Q1. A" | `qitem-20261123025042-6791e53b48284218` | 5-tier map: T1/T2 v0.3.0, T3 v0.5.0, T4 v0.6.0, T5 v0.9.0; all five re-run via YAML at v0.9.0. |
| Q-E2 | "Q2. A" | `qitem-20261123025043-bc5dc899e15dee2c` | T1 and T2 join v0.3.0 beside HF1/HF2 (unchanged). |
| Q-E3 | "Q3. B, but these may need updating as we define the YAML/JSON format." | `qitem-20261123025043-e8fdeed0bdd0a6db` | Every fixture input here is provisional until the YAML/JSON format is defined. |
| Q-E4 | "Q4. A but the files attached can be used as reference." | `qitem-20261123025044-47984a131bce3de9` | The index fixes concern T3/T5 (later versions). T1/T2 use TJ's XYZ as given. The SIs are reference sources. |
| Q-E5 | "Q5. C, if it turns out MACE, UMA, or OMol25 are needed then they should become standard." | `qitem-20261123025044-8c14515db45c326a` | Numeric literature windows gate UMA only; GFN2 values are reported. Sign/ordering checks GFN2 reproduces stay gated on both. If data show GFN2 is insufficient, the proposal that MACE/UMA/OMol25 becomes standard is raised to TJ. |
| R1 | "R1. A" | (relayed by the lead) | Candidate outputs are committed on the feature branch. |
| R2 | "R2. A" | (relayed by the lead) | Butane ΔG(gauche − anti) is per conformer, no RT ln 2; the class population is reported separately. |

Standing: Q1 A (`PRDs/` plan authoritative; zip copies reference only); Q2 B (starter reference only,
per-version `DISCREPANCIES.md`); Q3 amended "Build, install, and run these autonomously as to move on
to the next step/question." (a failed engine run is a finding with output); author "Thomas J. L.
Mustard Ph.D."; never push; `PRDs/` read-only. Never run TJ's bundle builder script in the repo.

LICENCE POLICY (TJ, 14:57Z): "I would prefer to keep ASE out as it would be a major core dependency.
The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP, conf
search can be copy left. Because they can be replaced with a new engine later. But the core
remains." (14:59Z) "It's fine that the engine MACE pulls in ASE just not the core."

Open with TJ (not decided here): the reference values (`qitem-20261123015428-cc83f02a1853ab80`,
needed before slice 10); confirmation of the four derived SMILES (at Phase 3 promotion); F32, which
s-cis TJ's T1 2.2 kcal/mol means (`qitem-20261123032327-833f8c98768fa58f`, unanswered at compile:
default C, "class comparison, geometry unspecified", reported only).

## 1. Introduction & Goals

**Problem.** v0.2.0 gives six engines that return energy, forces and a Hessian for one fixed
geometry. Nothing yet generates conformers, optimizes a geometry, computes frequencies or
thermochemistry, or averages an ensemble, so the repo cannot answer "what is the free energy of
this molecule, or of this reaction?". The plan's Hypothesis 4 (Grimme quasi-RRHO + 1 M) and its
stage-decomposed caching are untested.

**Solution.**
1. `eta_rxncat.conformers`: ETKDGv3 from a SMILES in two passes (experimental torsion preferences
   on, then off; R21), optional stereo-checked seed geometries, proper-rotation dedup over graph
   automorphisms, energy window, and mirror degeneracy from each conformer's own chirality.
2. `eta_rxncat.optimize`: the `Optimizer` interface; `GeometricOptimizer` (geomeTRIC 1.1.1 driven
   through its lower-level API, never `run_optimizer`) in the extra `opt-geometric`; a recorded
   three-step recovery ladder.
3. `eta_rxncat.thermo`: CODATA 2018 constants, normal modes with Eckart projection, rotational
   symmetry number, Grimme quasi-RRHO at 1 M, log-sum-exp Boltzmann with degeneracies.
4. `eta_rxncat.orchestrator.species`: the single-species stage runner with store caching,
   counted engine calls, incremental single points, per-stage metrics, reaction ΔG, and the
   deterministic JSON report writer.
5. HF1, HF2, T1 and T2 end to end on both recipes into committed candidate outputs.
6. An acceptance record (slice 09) and, after TJ's Phase 3 gate, the verdict run (slice 10).

**Audience.** TJ (user, reviewer, promoter); the build seats; v0.4.0 (constrained pre-opt reuses
`frozen_atom_indices`), v0.5.0 (P-RFO behind the same `Optimizer` interface; widens
`OptimizerIdentity.name`) and v0.6.0 (Boltzmann-weighted selectivity).

**Goals.**
- G1: a SMILES with explicit charge and multiplicity → a `ConformerEnsemble` whose records each
  carry the optimized geometry, a validated `ThermoResult`, a degeneracy and a Boltzmann weight,
  plus the ensemble free energy.
- G2: every thermochemistry formula is proved by tier-D tests against hand-derivable values.
- G3: a rerun of a finished species makes 0 engine calls; adding a solvation single point makes
  exactly one engine call per kept conformer. Counted by the counting engine wrapper, cross-checked
  against store rows (R7).
- G4: HF1 and HF2 reproduce TJ's promoted outputs within the Q5 bounds on a fresh store (cache
  disabled) for both recipes — a reproducibility gate (R10); UMA meets the Q5 accuracy bounds.
- G5: the base runtime install and `eta_rxncat.core` never import geomeTRIC; the `base` licence
  profile passes without the geomeTRIC exemption. (In the `gpu`/`mlip-*` envs geomeTRIC is present
  transitively through `gpu4pyscf-cuda12x`, so `GeometricOptimizer()` works there without the extra;
  no test asserts unavailability in those envs.)
- G6: T1 and T2 pass their structural, caching, sign and ordering gates on both recipes; T2's
  ΔG_rxn(1 M) is inside TJ's window on UMA; GFN2's deviation is reported.

## 2. Confidence Mandate

**Score: 9/10.** Every red-team finding F1–F32 has a disposition (§5 log): 31 resolved, 1 out of
scope (F8's scaling for large molecules, with its v0.4.0+ owner), none accepted-and-pending. F21,
the blocker, is resolved by a second ETKDG pass, proved on the real recipe by resolve's own
measurement (R21) and re-proved in slice 05 by an independent route.

What keeps it from 10, and the questions that would make it 10:
1. **TJ's reference values** (`cc83f02a…`, open). Needed before slice 10, not before the build.
   Question for TJ: the per-conformer values per R2 "A" for HF1 (ΔE/ΔH/ΔG gauche − anti) and ΔG_r,
   ΔH_r for HF2, with standard state and source.
2. **UMA on T2's window and on T1's s-cis-side survival is unmeasured** (needs the uma env and the
   pipeline). Both are stop-and-report host facts (H14, and the T2 UMA run in slice 08): a miss is a
   finding to the lead, never a widened bound. No spec text changes on either outcome.
3. **F32** (open; default C applied). Changing the answer changes one data field, not code.

## 3. Scope

### In scope
1. Starter unpack into `docs/prd/v0.3.0/` (reference only, ADR-0007), `DISCREPANCIES.md` (≥ the rows
   in §5 "Discrepancy register"), PD-007 → decided.
2. Core contracts in `eta_rxncat.core`: `ThermoResult`, `ThermoAnalysisOptions`, `ConformerRecord`,
   `ConformerEnsemble`, `OptimizationResult`, `OptimizerIdentity`. `ThermoConfig` reused unchanged.
3. `eta_rxncat.thermo`: constants, normal modes, symmetry number, quasi-RRHO, Boltzmann, ground-state
   check.
4. `eta_rxncat.optimize`: interface, errors, `GeometricOptimizer` in `opt-geometric`, ladder.
5. `eta_rxncat.conformers`: two-pass ETKDGv3, seeds, dedup, window, degeneracy, ensemble build.
6. `eta_rxncat.orchestrator`: species runner, counting wrapper, metrics, `ReactionSpec`, report
   writer.
7. Packaging and licence: `opt-geometric` extra; geomeTRIC in the dev group (R5); base drops it; new
   `opt-geometric` licence profile; CI; AGENTS.md rules.
8. HF1/HF2 and T1/T2: inputs under `tests/e2e/data/`, E2E tests, committed candidates.
9. Acceptance record (slice 09) and verdict run after the Phase 3 gate (slice 10).
10. README Features/Roadmap derived from the record; CHANGELOG is the scribe's.

### Out of scope
- CREST (later version). Tiers 3–5 (v0.5.0, v0.6.0, v0.9.0 per Q-E1) and the YAML suite runner
  (v0.8.0/v0.9.0). TJ's graph-schema YAMLs (provisional, Q-E3).
- Transition states, P-RFO, imaginary-mode filters beyond "a ground state has none" (v0.5.0).
- Selectivity (v0.6.0). DAG orchestrator, priority gating, crash-resume across a graph (v0.8.0).
  `ReactionGraph` execution.
- Head-Gordon quasi-RRHO; `entropy_model` stays `Literal["grimme_qrrho"]`.
- Automatic charge/multiplicity perception; conformer generation from a bare XYZ (an XYZ is only a
  seed). Isotope-labelled SMILES (refused, R16).
- The mace `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD` carry-forward (no recipe runs mace; v0.2.0 known
  issue). The store `open_timeout_s=inf` carry-forward (the runner uses the finite default 5.0 s).
- Tightening `PotentialResult` itself (changes the v0.2.0 contract and the engines node).
- A smarter point-group finder for molecules whose H-automorphism count exceeds the cap (v0.4.0+,
  R8).

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority |
|---|---|---|---|
| US-001 | As the builder, I want the v0.3.0 starter unpacked as reference with its discrepancies listed. | `docs/prd/v0.3.0/` holds the 30 zip files byte-identical; the zip's sha256 is `eaa9638d7d77ad0dc8c51fb4ef749b7a1d08b28dd106ca5ae7312ab6a1ddb401`; no gate scans the directory; `DISCREPANCIES.md` has ≥ the register rows; PD-007 reads `decided (TJ v0.3.0 Q4: "C", row qitem-20261123010134-cd43c1fb3e761e27)`. Slice 01. | P0 |
| US-002 | As a library user, I want frozen, strict core contracts for thermochemistry, ensembles and optimization results. | §5 Contracts models exist, frozen, `extra="forbid"`, ADR-0003 strict; each validator has a pass and a reject test; `import eta_rxncat.core` loads no numpy, RDKit or geomeTRIC. Slice 02. | P0 |
| US-003 | As a chemist, I want harmonic frequencies from any engine's Cartesian Hessian with translation/rotation projected out. | Diatomic: exactly one mode, frequency from k and μ to 1e-6 relative; linear triatomic 3N−5; a rigid rotation changes no frequency by > 1e-6 cm⁻¹; CO₂ bent by 1e-4 Å is linear; N = 1 gives 0 modes. Slice 03. | P0 |
| US-004 | As a chemist, I want the rotational symmetry number from the geometry. | H₂O 2, NH₃ 3, CH₄ 12, ethylene 4, benzene 12, CO₂ 2, HCN 1, butane anti 2, gauche 2; one atom moved 0.2 Å drops to the subgroup value; hexamethylethane (H-automorphisms over the cap) raises `ThermoInputError`; σ on optimizer-converged water/ethylene/benzene equals the idealized value (slice 05). Slice 03. | P0 |
| US-005 | As a chemist, I want Grimme quasi-RRHO thermochemistry at 1 M. | Each term matches its closed form at 298.15 K; the 1 M term is RT ln(24.4654) = 1.8943 kcal/mol ± 1e-4; Grimme weight 0.5 at ω = ω₀; for a linear molecule E_trans + E_rot = 5/2 RT; S_elec = R ln(2S+1); a total-H tier-D test sums the terms independently; every Z 1–118 has a mass. Slice 03. | P0 |
| US-006 | As a chemist, I want ensembles Boltzmann-averaged with degeneracies. | Equal G, g = (1, 2) → weights (1/3, 2/3); G_ens hand-checked; ΔG = 1000 kcal/mol does not overflow. Slice 03. | P0 |
| US-007 | As a chemist, I want an optimizer interface with geomeTRIC as an optional extra. | Without geomeTRIC, `GeometricOptimizer()` raises `OptimizerUnavailableError` naming `uv sync --extra opt-geometric`; base runtime lock has no `geometric`; UFF water converges to RDKit's own tight UFF minimum within 1e-5 Eh; no file outside the temp dir; a host `FileHandler` and `caplog` still receive a post-run message, and stderr carries no geomeTRIC output. Slice 04. | P0 |
| US-008 | As a chemist, I want a recorded recovery ladder. | `tric` → `tric_tight_trust` → `cartesian`, each recorded in order; exhaustion → `OptimizationFailedError` with the steps; `EngineError` stops the ladder and propagates. Fake engine. Slice 04. | P0 |
| US-009 | As a chemist, I want ETKDGv3 conformers from a SMILES, deduplicated without merging mirror images, with every relevant torsion class sampled. | Formal-charge mismatch, isotope labels, or a seed whose stereo differs → `ConformerInputError`. Butane (seed 42, UFF): exactly one anti record (g = 1) and exactly one gauche record (g = 2), both when g⁺ and g⁻ survive optimization and when only one does. Butadiene and T1: pass 2 yields s-cis-side embeddings (≥ 1). Slice 05. | P0 |
| US-010 | As a chemist, I want a single-species runner that caches every stage. | Rerun → 0 engine calls (counting wrapper); added ALPB single point → exactly `n_kept` calls; upstream rows unchanged (same keys, same `created_at_utc`); store rows created == counted misses; keys byte-identical across runs. Slice 06. | P0 |
| US-011 | As TJ, I want HF1 (n-butane) on both recipes in committed candidates. | `hf1_butane.<recipe>.json` for `xtb` and `uma`; ΔG/ΔH/ΔE(gauche − anti) per conformer (R2 "A"); gauche population and `class_dG_gauche_anti` reported; committed in a candidates-only commit. Slice 07. | P0 |
| US-012 | As TJ, I want HF2 (Diels–Alder, 1 M) on both recipes with an incremental-solvation stage. | ΔE_r, ΔH_r, ΔG_r at 1 atm and 1 M; xtb: ALPB(toluene, `alpb_state: gsolv`) single point per kept record, ΔG_solv per species and the solvated ΔG_r(1 M); both recipes: one PySCF PCM(toluene, C-PCM) single point on ethylene's lowest record as a mechanism check (1 call, 0 upstream, no ΔG_solv); UMA ΔG_solv `n/a`. Slice 07. | P0 |
| US-013 | As TJ, I want an acceptance record with benchmark metrics. | `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json` per fixture and recipe: per-stage wall time, engine calls, cache hits; conformer counts; optimizer and recovery steps; regression/accuracy verdicts (`pending_*` allowed in slice 09); device; commit; environment. README claims derived from it (tested). Slices 09, 10. | P0 |
| US-014 | As the licence owner, I want the gate to follow geomeTRIC's new place. | `--profile base` passes with no geomeTRIC exemption; new `--profile opt-geometric` passes with the pinned exemption; `gpu`, `mlip-mace`, `mlip-uma` keep it (pulled in by `gpu4pyscf-cuda12x` because CI syncs those profiles with `--extra gpu`); a stale exemption still fails; CI gains the profile. Slice 04. | P0 |
| US-015 | As TJ, I want Tier 1 (1,3-dimethoxybutadiene) on both recipes. | `e2e5_t1.<recipe>.json`. Gated on both: ≥ 2 kept records; lowest record 0 imaginary modes; weights sum to 1 within 1e-12; G_BA ≤ G_lowest; ≥ 1 kept s-trans and ≥ 1 kept s-cis-side record; lowest s-trans G below lowest s-cis-side G. Reported: ΔE(s-cis-side − s-trans) vs 2.2 kcal/mol, labelled per F32. Slice 08. | P0 |
| US-016 | As TJ, I want Tier 2 (Cp + cyclopropene → endo P1a_n) on both recipes with an incremental ALPB(dioxane) stage. | `e2e5_t2.<recipe>.json`. Gated on both: atoms and charge conserved; ΔG_rxn(1 M) < 0; every species' lowest record 0 imaginary modes; P1a_n σ = 1, g = 1. UMA only: −42 < ΔG_rxn(1 M) < −20. xtb: rerun with ALPB(dioxane, gsolv) → 0 upstream calls, upstream stages served for 3 of 3 species, solvation stage missing for 3 of 3 with exactly Σ n_kept calls, every species has a finite ΔG_solv, solvated ΔG_rxn(1 M) ≠ gas ΔG_rxn(1 M). UMA: plain rerun → 0 calls. Slice 08. | P0 |
| US-017 | As TJ, I want the SMILES derived from my XYZ shown to me before they count. | A tier-D test re-derives each SMILES from TJ's XYZ and asserts molecule equality with the input (both canonicalised by the running RDKit); derived SMILES go to `e2e5_smiles.json`; once TJ's promoted `tests/fixtures/v0.3.0/e2e5_smiles.json` exists, input equals it as molecules; under `ETA_RXNCAT_ACCEPTANCE=1` an absent confirmation fails (`pending_confirmation`). Slices 08, 10. | P0 |

## 5. Technical Specifications

### Resolved trade-off log

Vocabulary: **resolved** (the design changes so the risk is gone; the slice that carries it is
named), **out of scope** (excluded, with the owner). No finding is `accepted`, so no human row is
owed for one. Part A/B are red-team rev 1 (F1–F20); Part D is the rev-2 delta (F21–F32).

| ID | Finding | Sev | Disposition | Decision |
|---|---|---|---|---|
| R1 | F1 `engines.units` lacks h, k_B, c, N_A, amu, R; adding them touches engines | high | resolved | New `eta_rxncat/thermo/constants.py`: CODATA 2018 exact h, k_B, c, N_A, e, plus amu (1.66053906660e-27 kg), E_h (4.3597447222071e-18 J), a₀ (0.529177210903e-10 m), cal = 4.184 J, atm = 101325 Pa, R = N_A·k_B. A tier-D test derives `engines.units.HARTREE_KCAL_MOL` (E_h·N_A/4184) and `BOHR_ANGSTROM` from them within 1e-12 relative. No engine file changes. Slice 03. |
| R2 | F2 `run_optimizer`'s `fileConfig` closes host handlers | high | resolved | Never call `geometric.optimize.run_optimizer`. Drive the lower-level API: `geometric.params.OptParams`, `geometric.molecule.Molecule`, `geometric.optimize.CoordSysDict`, `geometric.optimize.Optimizer(...).optimizeGeometry()`. During a call the `geometric` logger gets `propagate=False` and one handler writing into the temp dir; its prior handlers/level/propagate are restored after. Test: a root `FileHandler(mode="w")` plus `caplog` both receive a message logged after the run, and `capfd` stderr has no geomeTRIC lines. Slice 04. PROPOSED decision (lore). |
| R3 | F3 the 0.5 Å heavy-atom pre-dedup merges g⁺/g⁻, so a found-pair rule gives g = 1 | high | resolved | Degeneracy is a property of the conformer: g = 2 iff the molecule is graph-achiral **and** the conformer is chiral (its inverted geometry is > `rmsd_dedup_angstrom` from itself under every automorphism with a proper rotation); else 1. A kept record whose inversion matches another kept record is a mirror partner and is dropped (the lower-G one stays; ties → lower index), recorded in `dropped` with reason `mirror_partner`. Pre-dedup runs **with H** at `pre_dedup_rmsd_angstrom` (default 0.125). Tests: g⁺ present and g⁺ absent each give one gauche record with g = 2. Slice 05. |
| R4 | F4 slice 08 could not pass before TJ acts | high | resolved | Split: slice 09 (acceptance record, `pending_*` allowed; PASS = record complete + derivation tests) → Phase 3 gate (TJ) → slice 10 (verdict). See R22. |
| R5 | F5 P0 optimizer/conformer tests never run in the required checks | high | resolved | `geometric==1.1.1` goes in the **dev** dependency group as well as the `opt-geometric` extra, so `uv sync --locked` (required check 1) installs it in `.venv` and `uv run pytest` runs every optimizer and conformer test in the default suite, with no deselected marker. The runtime licence gate uses `--no-dev`, so `base` stays geomeTRIC-free (TJ's policy is about the shipped core; dev tools are not shipped). The "extra absent" path is tested by making `import geometric` fail (`monkeypatch.setitem(sys.modules, "geometric", None)`). No `opt_geometric` marker. Slice 04. PROPOSED decision. |
| R6 | F6 HF1 accuracy quantity undefined w.r.t. degeneracy | high | resolved (TJ R2 "A") | ΔE/ΔH/ΔG(gauche − anti) per conformer: lowest gauche record − lowest anti record, no RT ln 2. Reported beside: gauche population (summed weights, degeneracy included) and `class_dG_gauche_anti` = −RT ln(P_gauche/P_anti). `hf1.gauche_population` has no bound; when TJ supplies it, it is `reported`, stated explicitly. Slices 07, 10. |
| R7 | F7 `conformer_search` payload/engine/counting undefined | medium | resolved | `conformer_search` makes **0 engine calls**. Payload: the pool (each member's id, origin `etkdg`/`etkdg_free`/`seed`, xyz), RDKit failure counts per pass, the pre-dedup survivors, the resolved conformer options. Its `StageConfig` uses the recipe's engine tag and method so each recipe has its own pool row; its key geometry is pass-1 embedding id 0, so RDKit runs before the lookup (intended; deterministic per H4). Counting instrument: `CountingEngine` (wraps `evaluate`, counts per stage kind); cross-check: store rows created == counted misses. Slice 06. |
| R8 | F8 RDKit truncates automorphisms at 1000 silently; the cap raises on ordinary molecules | medium | resolved + out of scope | Every `GetSubstructMatches` passes `maxMatches = max_automorphisms + 1` and `uniquify=False`; reaching the cap raises `ThermoInputError` (test: hexamethylethane `CC(C)(C)C(C)(C)C` with H). Default cap 100 000 kept: every v0.3.0 species is far below it. A point-group finder for large molecules is **out of scope**, owned by v0.4.0+ (known limit in the record). Slice 03. |
| R9 | F9 σ/g flip under tolerance; 1e-8 linearity misclassifies | medium | resolved | σ and g of every record are **exact** in regression. Linearity: N = 2, or every atom within `linear_tol_angstrom` (default 1e-3 Å) of the line through the COM along the smallest-moment principal axis. Tests: CO₂ bent 1e-4 Å → linear; σ on optimizer-converged water/ethylene/benzene (slice 05). Slices 03, 05, 10. |
| R10 | F10 H5 "3 reruns" is vacuous on deterministic engines and cache hits | medium | resolved | H5 redefined: cache disabled; butane gauche re-optimized from 3 different pass-1 embeddings that converge to it (and from 3 displacements of 0.01 Å); record the spread of the lowest 3 frequencies and of G; UMA on cuda. Spread of G > 0.05/3 kcal/mol → stop and report, never loosen. Regression compares like with like: same device, recorded; the verdict run uses a fresh store. G4 restated as a reproducibility gate. Slice 07. |
| R11 | F11 blast radius measured on starter names; engines reached via `tests/acceptance/**`; description limits | medium | resolved | Acceptance test moves to `tests/e2e/test_accept_v030.py` (species-runner node), so `eta_rxncat_engines` is not touched. Fixture inputs live under `tests/e2e/data/` (no double map with core's `tests/data/**`). The incremental test lives in `tests/unit/orchestrator/`. Slice 01 trims the scaffold description (1991 → ≤ 1800) and slice 02 the core one (1977 → ≤ 1800), via `hyper_ledger.py ensure-node --id <node> --description-file`. Re-measured blast radius below. |
| R12 | F12 zip sha256 wrong in draft | medium | resolved | `eaa9638d7d77ad0dc8c51fb4ef749b7a1d08b28dd106ca5ae7312ab6a1ddb401` (resolve: `sha256sum PRDs/Eta-RxnCat-v0.3.0.zip`), 30 files. Slice 01. |
| R13 | F13 HF2 ΔG_solv undefined for UMA; PySCF can't give ΔG_solv in one call; ALPB state unnamed | medium | resolved | xtb: ΔG_solv per conformer = E(ALPB SP) − E(gas opt), both GFN2 at the same geometry, `alpb_state: gsolv` named in the stage options (1 M gas → 1 M solution, consistent with the 1 M gas G). UMA: `n/a`. PySCF PCM check is **mechanism only**: 1 call, 0 upstream, no ΔG_solv. Slice 07. |
| R14 | F14 lock diff is more than the marker | low | resolved | Expected `uv lock` diff: `geometric`, `networkx`, `six` leave the base runtime closure and appear under the `opt-geometric` extra and the dev group (still under `gpu4pyscf-cuda12x`); **no version changes** anywhere. Any other diff → stop and report. Slice 04. |
| R15 | F15 thermochemistry definition gaps; D4's 1.06 | low | resolved | Written in §5 Algorithms: E_vib is the thermal excess **excluding** ZPE; H = E + ZPE + E_trans + E_rot + E_vib + k_BT·N_A (per mole); free-rotor S_r = R[½ + ln((8π³μ′k_BT/h²)^{1/2})] with μ = h/(8π²cν̃), μ′ = μB_av/(μ+B_av); \|ν̃\| < 1e-3 cm⁻¹ → `ThermoInputError`; N = 1 → 0 modes, S_rot = E_rot = 0; N = 2 always linear. Imag-mode push: the Cartesian displacement along the mode, scaled so the largest atomic displacement is 0.1 Å. RT ln 4 = 0.821 kcal/mol (ethylene). Slices 03, 06. |
| R16 | F16 isotope labels silently dropped | low | resolved | A SMILES with any isotope label → `ConformerInputError` in v0.3.0 (masses come from symbols). Register row DV-21. Slice 05. |
| R17 | F17 candidate commit policy undefined | low | resolved (TJ R1 "A") | Committed on the feature branch; commit order and audit evidence per R23. Slices 07, 08. |
| R18 | F18 `created_at` vs `created_at_utc`; imag-push key; weight-regression matching | low | resolved | The column is `created_at_utc`. The imag-push re-optimization is a **new** `geometry_opt` row keyed on the displaced geometry. Regression matches records by class (HF1 torsion class / T1 diene class) and RMSD ≤ 0.125 Å with H over automorphisms (proper rotation) to the promoted record; an unmatched record on either side is a regression **fail**. Slices 06, 10. |
| R19 | F19 stale Base | low | resolved | Base `7993284` (lead). |
| R20 | F20 "C-PCM(toluene)" | low | resolved | `Solvation(model="pcm", solvent="toluene")`, `options={"pcm_method": "C-PCM"}` (the engine's default, written explicitly). Slice 07. |
| R21 | **F21 (blocker)** ETKDGv3 never samples the s-cis-side diene class | blocker | resolved | **Remedy (b): a second ETKDG pass with `useExpTorsionAnglePrefs=False`**, merged into the pool (keyed `torsion_free_pass: bool`, default `true`; same `n_embed` and `seed`, ids `n_embed…2·n_embed−1`, origin `etkdg_free`). Why (b): it is general (no hand-picked bond list, which (a) needs and v0.4.0+ would inherit), deterministic, one keyed flag; (c) would drop a real minimum the v0.5.0 Diels–Alder TS search needs and leave HF2's butadiene ensemble incomplete. Resolve measured on RDKit 2026.09.2, seed 42, `numThreads=1`: pass 1 gives s-cis-side 0/40 (T1) and 0/50 (butadiene); pass 2 gives 24/40 and 26/50, bit-reproducible across runs. On the real default recipe (xtb 6.8.0 `--gfn 2 --opt tight`, run directly, not through pipeline code): the s-cis-side class survives (T1 φ 48.7° → 2.1°; butadiene −65.6° → −18.3°) and lies above s-trans (T1 +1.69, butadiene +2.13 kcal/mol, ΔE). So US-015's "both classes present" gate stays and can pass. HF2's butadiene ensemble is expected to hold an s-trans and an s-cis-side (gauche) record; HF2's expected content and the §7 risk are corrected. Nothing TJ decided is weakened (TJ's Tier 1 asks ≥ 2 conformers; this adds conformers). Slice 05 carries it and re-proves it (H12, H14). PROPOSED decision. |
| R22 | F22 no owner for the post-Phase-3 verdict run or the SMILES-correction redo | high | resolved | Sequence: slice 09 (record; PASS without TJ) → **Phase 3 gate** (TJ reviews the committed candidates, promotes into `tests/fixtures/v0.3.0/`, confirms the SMILES, writes `reference_values.json`) → the lead routes to **resolve**, which records the promotion as a new R-row (file names + sha256 of `tests/fixtures/v0.3.0/*`) → slice 10 (builder: verdict run, `ETA_RXNCAT_ACCEPTANCE=1`, fresh store) → audit. If TJ corrects a SMILES, resolve compiles a rework slice (replan mode, a fresh MiniPRD before slice 10) that changes the input file and re-runs the affected E2E cases; accepted slices are never edited. Slice 09's PASS never depends on TJ. The v0.3.0 release waits on the gate. |
| R23 | F23 committed candidates are readable through git; H13 checks the wrong permission; commit order | medium | resolved | Order per E2E slice: (1) code commit C1 on a clean tree (`git status --porcelain --untracked-files=no` empty); (2) E2E run at C1 writes candidates with `commit_sha = C1`; (3) commit C2 containing **only** `tests/candidate_outputs/v0.3.0/*`, message `candidates produced at <C1>`. Every `git diff`, `git show` and `git log -p` by any seat over a range containing C2 uses the pathspec `-- . ':(exclude)tests/candidate_outputs'`; C2 is verified by `git show --name-only --format=%s <C2>` (names only). The writer function is unit-tested on `tmp_path`, so behaviour is audited without reading candidates. H13 is redefined: the builder confirms the pathspec form excludes the files (`git diff --stat C1..C2 -- . ':(exclude)tests/candidate_outputs'` prints nothing) and that `git add`/`commit` of the path succeeds; a denial stops and reports. PROPOSED decision. Slices 07, 08 (and 09, 10). |
| R24 | F24 seed match ignores stereo | medium | resolved | A seed (`MolecularState`) is bond-perceived (`rdDetermineBonds.DetermineBonds(mol, charge=charge)`), `AssignStereochemistryFrom3D`, and must satisfy both: its canonical isomeric SMILES equals the input SMILES's (running RDKit), and `GetSubstructMatch(seed_mol, useChirality=True)` over all atoms including H succeeds; else `ConformerInputError`. The match reorders seed atoms into SMILES order. Test: a Z-diene seed for the E SMILES and an exo seed for endo P1a_n are both refused. Slice 05. |
| R25 | F25 H12 gate decided from the code it gates | medium | resolved | The ordering gate is decided **now**, from resolve's independent xtb CLI measurement (R21): GFN2 reproduces s-trans < s-cis-side, so the T1 ordering check is **gated on both recipes**. Slice 05 re-measures H12 by the same independent route (xtb CLI from TJ's seed and from every pass-2 s-cis-side embedding) before any pipeline code is used; a contradiction is stop-and-report, never a re-decision. DO NOT decide a gate from the output of the code it gates. |
| R26 | F26 escalation reads as allowing acceptance with a gated failure | medium | resolved | A gated check that fails, fails acceptance; the release waits on TJ. `known_limits` lists only reported deviations (GFN2 windows) and the Q-E5 escalation proposal. |
| R27 | F27 T2 solvated ΔG_rxn underdefined | medium | resolved | Per conformer: G_solv,i = G_gas,i + (E_ALPB,i − E_gas,i); per species ΔG_solv = G_ens,solv − G_ens,gas (re-Boltzmann over the solvated G, same degeneracies); solvated ΔG_rxn(1 M) = gas ΔG_rxn(1 M) + Σν ΔG_solv (1 M base, because `gsolv` is 1 M → 1 M). Gates: every species has a finite ΔG_solv (3 of 3), solvated ≠ gas by > 1e-6 kcal/mol; the signs are reported. `species_stage_cache`: a species is a hit only when every kept conformer's row was served; one miss makes the species a miss. Slice 08. |
| R28 | F28 seed contract gaps | low | resolved | `seed_geometries: Sequence[MolecularState]` (same charge and multiplicity as the call, else `ConformerInputError`). Hashed text after reordering: `f"{n}\n\n"` then per atom `f"{symbol} {x:.6f} {y:.6f} {z:.6f}\n"` (Å, symbol as in the state); `seed_geometries_sha256` = sorted hex digests joined by `,` (or `""`). `ConformerInputError`'s definition includes every seed failure. Pre-dedup visits seeds first, so a seed is never removed by pre-dedup; "the SI conformer is always in the pool" is then true. Slice 05. |
| R29 | F29 ledger double-maps; H13 placement | low | resolved | Inputs under `tests/e2e/data/**` (species runner). The species-runner node owns `tests/candidate_outputs/v0.3.0/**` (path mapping only; no seat reads them). H13 runs in slice 07, the first slice that commits candidates. |
| R30 | F30 SMILES compared as strings | low | resolved | Compare molecules: `Chem.MolToSmiles(Chem.MolFromSmiles(s))` of both sides with the running RDKit must be equal. Slices 08, 10. |
| R31 | F31 running TJ's builder is unnecessary | low | resolved | Extract the `XYZ_FILES` literal from `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py` with `ast.parse` + `ast.literal_eval` (no execution), write the four files UTF-8, check each full sha256 against the prefixes below, and record that the builder's sha256 matches TJ's `MANIFEST.sha256` in the same directory. Slice 08. |
| R32 | F32 T1 dihedral atoms unnamed; which s-cis the 2.2 kcal/mol means | low | resolved (atoms) / TJ open (meaning) | Dihedral = SMILES atoms 0-1-2-3 of `C=C(/C=C/OC)OC` (H added after, so the indices hold). Meaning: TJ row `833f8c98…` unanswered at compile → option C: `literature.label: "class comparison, geometry unspecified"`, reported only. The label is a field in `tests/e2e/data/e2e5/t1_dimethoxybutadiene.yaml`, read by the test, so a TJ answer changes data, not code. |
| R33 | Part B §1: G5 holds only in base (geomeTRIC transitive in gpu/mlip) | — | resolved | Stated in G5; no test asserts `OptimizerUnavailableError` outside base. |
| R34 | Part B §4: US-005 "5/2 RT" ambiguous | — | resolved | Means E_trans + E_rot for a linear molecule. |
| R35 | Part B §5.1: D7 single-point geometry not validated | — | resolved | `energy_source: "single_point"` requires the SP's input geometry hash (store `geometry_payload`) to equal the frequency stage's; else `ThermoInputError`. Slice 06. |
| R36 | Part B §5.4: `soft_modes_cm1` not a field; weights parenthesis; N = 1/2; `OptimizerIdentity` Literal | — | resolved | `ThermoResult.soft_modes_cm1` added; "exact arithmetic" dropped (1e-12 stays); N = 1/2 per R15; `OptimizerIdentity.name: Literal["geometric"]` is recorded as widened by v0.5.0. Slice 02. |
| R37 | Part B §5.5: graph-achirality ignores double-bond/atropisomer stereo | — | resolved | Recorded as a known limit (tetrahedral tags only); no v0.3.0 species is affected (E/Z is mirror-invariant). |
| R38 | Part B §5.6/§6: GAU gmax hard-coded; exemption citation; acceptance env profiles | — | resolved | Tests read convergence thresholds from geomeTRIC's `params.py` at runtime. The gpu/mlip exemption's `pulled-in-by` cites `gpu4pyscf-cuda12x` **and** the CI profile definition (`--extra gpu`). The acceptance envs are not gate profiles; `opt-geometric` is. |
| R39 | Part B §5.7: UMA device nondeterminism | — | resolved | `device` recorded per run; regression only compares runs on the same device; the record states it. |
| R40 | Part B §7/§8: named envs and commands; tier-D time command | — | resolved | §8 names them. |
| R41 | Lead: code graph | — | resolved | Every slice starts with `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`; the audit treats `code_graph.status != ok` as a finding. The graph only widens the blast radius. |

### Host facts and stop-and-report steps

Each is checked by the named command in its slice before code depends on it. A mismatch stops the
slice and is reported with the output; it is never worked around.

| # | Fact | Status at compile | Slice |
|---|---|---|---|
| H1 | `gpu4pyscf-cuda12x` depends on `geometric` (`uv.lock`) | verified (draft, red team) | 04 |
| H2 | Dative-bond SMILES embed (`N->[Pd](Cl)(Cl)<-N`, status 0) | verified (draft) | — |
| H3 | RDKit `pruneRmsThresh` 0.5 merges butane g⁺/g⁻ (the threshold, not reflection) | verified | 05 |
| H4 | ETKDGv3, fixed seed, `numThreads=1`: bit-reproducible, both passes | verified (red team pass 1; resolve pass 2 dihedrals) | 05 |
| H5 | Low-frequency/G noise across distinct converged geometries (R10) | to measure | 07 |
| H6 | geomeTRIC 1.1.1 lower-level API: `OptParams` kwargs, `CoordSysDict`, `Optimizer`, convergence sets exactly `GAU`, `NWCHEM_LOOSE`, `GAU_LOOSE`, `TURBOMOLE`, `INTERFRAG_TIGHT`, `GAU_TIGHT`, `GAU_VERYTIGHT`; failure types `GeomOptNotConvergedError`, `GeomOptStructureError`; what maxiter raises; `$freeze` via `parse_constraints`; `hessian` values | partly verified | 04 |
| H7 | xtb 6.8.0 deterministic energies | verified (red team) | — |
| H8 | `pbe0` (libxc, PySCF 2.15.1) and `def2-svp` accepted; `--alpb toluene` | toluene verified; rest to run | 07 |
| H9 | RDKit masses Z 1–118 | verified (red team) | 03 |
| H10 | DetermineBonds + AssignStereochemistryFrom3D on TJ's four XYZ give the table SMILES | verified (draft, red team) | 08 |
| H11 | `--alpb dioxane` accepted | verified | — |
| H12 | GFN2 lowest s-trans T1 below lowest s-cis-side | **verified by resolve** (+1.69 kcal/mol ΔE, xtb CLI); re-measure independently | 05 |
| H13 | pathspec exclusion hides candidates; `git add`/`commit` allowed (R23) | to verify | 07 |
| H14 | The s-cis-side class survives optimization on UMA for butadiene and T1 (a pass-2 embedding optimized by `GeometricOptimizer` on `uma_direct`) | to measure | 05 (uma env) |

### Blast radius

Measured by resolve (read-only): `python3 .agents/scripts/hyper_ledger.py impact --files
src/eta_rxncat/core/thermo_models.py,src/eta_rxncat/core/ensemble_models.py,src/eta_rxncat/core/optimization_models.py,pyproject.toml,uv.lock,tools/licence_gate.py,AGENTS.md,tests/unit/test_package.py,tests/unit/test_identity.py,README.md,docs/prd/v0.3.0/DISCREPANCIES.md`
→ existing nodes `eta_rxncat_core`, `eta_rxncat_scaffold`, `eta_rxncat_cli` (via `pyproject.toml`,
`uv.lock`); blast radius adds `eta_rxncat_store`, `eta_rxncat_engines`, `eta_rxncat_hw_probe` as
reverse `depends_on` of core (needs_review only). New files under `thermo/`, `optimize/`,
`conformers/`, `orchestrator/`, `tests/e2e/` map to the new nodes below. The builder re-runs
`hypergraph_updater.py --from-diff` per slice as `execute.md` requires; that output governs.

Ledger changes (only via `hyper_ledger.py` / `hypergraph_updater.py`; `--id` on existing nodes,
`--files` always the full list; count the globs before and after):
- New nodes, created by the slice that first adds their files (not yet in the graph):
  - `eta_rxncat_thermo` (Module; depends_on `eta_rxncat_core`): `src/eta_rxncat/thermo/**`,
    `tests/unit/thermo/**` — slice 03.
  - `eta_rxncat_optimize` (Module; depends_on `eta_rxncat_core`, `eta_rxncat_engines`):
    `src/eta_rxncat/optimize/**`, `tests/unit/optimize/**` — slice 04.
  - `eta_rxncat_conformers` (Module; depends_on `eta_rxncat_core`, `eta_rxncat_thermo`):
    `src/eta_rxncat/conformers/**`, `tests/unit/conformers/**` — slice 05.
  - `eta_rxncat_species_runner` (Module; depends_on core, thermo, optimize, conformers, engines,
    store): `src/eta_rxncat/orchestrator/**`, `tests/unit/orchestrator/**`, `tests/e2e/**`,
    `tests/candidate_outputs/v0.3.0/**` — slice 06.
- `eta_rxncat_scaffold` loses `src/eta_rxncat/optimize/**` (slice 04), `src/eta_rxncat/conformers/**`
  (slice 05), `src/eta_rxncat/orchestrator/**` (slice 06); its description is trimmed to ≤ 1800
  characters in slice 01.
- `eta_rxncat_core`: no new globs; description trimmed to ≤ 1800 in slice 02.
- `eta_rxncat_engines`: **not touched** (1953/2000). A slice that finds it must change an engine
  file stops and reports.
- `eta_rxncat_store`: API unchanged; the runner is a new consumer.

### Execution checklist (build order; the lead's work queue)

1. `01-starter` — US-001; scaffold description trim.
2. `02-core-contracts` — US-002; core description trim; `PotentialResult` carry-forward test.
3. `03-thermo` — US-003…US-006; constants; new node `eta_rxncat_thermo`.
4. `04-optimizer` — US-007, US-008, US-014; extra, dev group, lock, licence profile, CI, AGENTS.md;
   new node `eta_rxncat_optimize`.
5. `05-conformers` — US-009; two-pass ETKDG (R21), seeds (R24, R28), degeneracy (R3); H12, H14;
   new node `eta_rxncat_conformers`.
6. `06-species-runner` — US-010; runner, counting, metrics, `ReactionSpec`, report writer; new node
   `eta_rxncat_species_runner`.
7. `07-human-fixtures` — US-011, US-012; H5, H8, H13; HF1/HF2 on both recipes; candidates commit.
8. `08-e2e5-tiers` — US-015…US-017; TJ's XYZ; T1/T2 on both recipes; candidates commit.
9. `09-acceptance-record` — US-013; record with `pending_*`; README derivation.
10. **Phase 3 gate (TJ; not a slice):** TJ reviews and promotes the candidates, confirms the SMILES,
    writes `tests/fixtures/v0.3.0/reference_values.json`. Then resolve records the promotion (R22),
    and compiles a rework slice first if TJ corrected a SMILES.
11. `10-acceptance-verdict` — US-011/012/015–017 verdicts; `ETA_RXNCAT_ACCEPTANCE=1`, zero skips.

Strictly one slice at a time (the ledger takes no parallel writes). **The feature is done when slice
10 audits PASS.** Each slice is one code commit on `feature/eta-rxncat-v0.3.0` (plus, for 07 and 08,
the candidates-only commit of R23), and every AGENTS.md required check exits 0.

### Contracts

All core models are `CoreModel` (`extra="forbid"`, frozen), ADR-0003 strict (chemistry ints
`StrictInt`, floats finite). Units are in field names.

**`ThermoAnalysisOptions` (core/thermo_models.py):** `imag_tol_cm1: PositiveFiniteFloat = 20.0`,
`sym_tol_angstrom: PositiveFiniteFloat = 0.05`, `linear_tol_angstrom: PositiveFiniteFloat = 1e-3`,
`max_automorphisms: PositiveInt = 100000`. Not stored (thermo is derived, R-D6), recorded in each
`ThermoResult`.

**`ThermoResult` (core/thermo_models.py):** `n_atoms: PositiveInt`; `electronic_energy_hartree`;
`energy_source: Literal["optimization", "single_point"]`; `zpe_hartree`,
`thermal_correction_enthalpy_hartree`, `thermal_correction_gibbs_hartree` (ZPE included in both);
`entropy_hartree_per_k` and `entropy_components_hartree_per_k` (exactly the keys `translational`,
`rotational`, `vibrational`, `electronic`, summing to the total within 1e-12 relative);
`gibbs_free_energy_hartree` = E + thermal_correction_gibbs; `standard_state_correction_hartree`
(inside G); `frequencies_cm1` (all 3N−6 or 3N−5, ascending, imaginary negative; 0 for N = 1);
`imaginary_frequencies_cm1` (those < −imag_tol, ⊆ frequencies); `soft_modes_cm1` (those in
[−imag_tol, 0), ⊆ frequencies); `rotational_symmetry_number: PositiveInt`; `is_linear: bool`;
`config: ThermoConfig`; `analysis: ThermoAnalysisOptions`; `masses_source: str`. Validators:
frequency count per `n_atoms`/`is_linear` (N = 1 → 0 and not linear; N = 2 → linear); subset
rules; component sum. No ground-state flag: `thermo.check_ground_state(result)` raises
`NotAMinimumError` listing the imaginary modes.

**`OptimizerIdentity`, `OptimizationResult` (core/optimization_models.py):**
`OptimizerIdentity(name: Literal["geometric"], version: str)` (v0.5.0 widens the Literal).
`OptimizationResult`: `final_state: MolecularState`, `final_energy_hartree`, `converged:
Literal[True]`, `n_steps: NonNegativeInt`, `n_engine_calls: NonNegativeInt`, `recovery_steps:
list[str]`, `optimizer: OptimizerIdentity`, `options: dict[str, ScalarValue]` (resolved).

**`ConformerRecord`, `ConformerEnsemble` (core/ensemble_models.py):** record: `state`
(optimized), `optimization: OptimizationResult`, `thermo: ThermoResult`, `degeneracy:
Literal[1, 2]`, `source_ids: list[NonNegativeInt]` (≥ 1, unique). Ensemble: `species_id`
(min_length 1), `smiles`, `records` (≥ 1), `boltzmann_weights`, `lowest_index`,
`ensemble_gibbs_hartree`, `temperature_k`. Validators: lengths match; weights ≥ 0 summing to 1
within 1e-12; `lowest_index` = argmin G (ties → lowest index); all records share symbols, charge,
multiplicity; every `thermo.config.temperature_k == temperature_k`.

**`Optimizer` interface (optimize/base.py):** `identity` property; `OPTIONS: ClassVar[Mapping[str,
OptionSpec]]` (reuse `engines.options.OptionSpec`, ADR-0016 resolution); `minimize(state, engine,
*, frozen_atom_indices=(), options=None) -> OptimizationResult`. Errors: `OptimizerError` →
`OptimizerUnavailableError` (names `uv sync --extra opt-geometric`), `OptimizerInputError`
(unknown/mistyped option, frozen indices out of range, empty/mismatched state),
`OptimizationFailedError` (`steps: tuple[str, ...]`, `last_energy_hartree`). `EngineError` raised
inside `minimize` propagates unchanged; library exceptions are caught by named type and re-raised
`from` the cause. Options (keyed, `opt.` prefix in the stage key): `coordsys` ∈ {tric, cart, dlc,
hdlc} = tric; `convergence_set` ∈ the seven H6 names = GAU; `maxiter` = 300; `trust` = 0.1;
`hessian` ∈ {never, first} = never.

**Conformer API (conformers/):** `generate(smiles, *, charge, spin_multiplicity, options:
ConformerOptions, seed_geometries=()) -> ConformerPool`; `dedup`, `energy_window`,
`assign_degeneracy`, `build_ensemble`. Keyed `ConformerOptions`: `n_embed` (50), `seed` (42),
`torsion_free_pass` (true), `pre_dedup_rmsd_angstrom` (0.125), `rmsd_dedup_angstrom` (0.125),
`energy_window_kcal_mol` (6.0), `include_h_in_rmsd` (true), `max_automorphisms` (100000). Errors:
`ConformerError` → `ConformerInputError` (SMILES unparsable; formal charge ≠ charge; impossible
electron parity; isotope labels; any seed failure per R24/R28), `EmbeddingFailedError` (zero
embeddings across both passes; RDKit failure counts), `EnsembleEmptyError` (every conformer
dropped; each reason). No function returns its input as a fallback.

**Stage keys (ADR-0001, ADR-0016):** `build_stage_key(state, stage, engine.identity)`.
`conformer_search`: recipe engine tag/method; `options` = resolved conformer options ∪ `{smiles:
canonical isomeric, rdkit_version, seed_geometries_sha256}`; geometry = pass-1 embedding 0.
`geometry_opt`: resolved engine options ∪ resolved optimizer options prefixed `opt.` ∪ `opt.name`,
`opt.version`; the engine is built from the stage without the `opt.` keys. `frequency`,
`single_point`: the engine stage, geometry = the optimized state. Byte-identical across runs
(tested).

**`ReactionSpec` (orchestrator/species.py, not core):** reactants/products as `(species_id,
coeff: PositiveInt)`; validator: atoms by element and charge conserved. ΔG_r = Σν G_ens(products) −
Σν G_ens(reactants) at one `ThermoConfig`; 1 atm and 1 M both reported, difference Δn·RT
ln(c°RT/p°) (Δn = −1 for HF2 and T2: ΔG_r(1 M) = ΔG_r(1 atm) − 1.8943 kcal/mol at 298.15 K).

**Candidate output (`tests/candidate_outputs/v0.3.0/<fixture>.<recipe>.json`, `schema: 1`):**
`fixture`, `recipe`, `commit_sha` (= C1 of R23), `environment` (python, rdkit, geometric, xtb or
fairchem versions, model id, device), `thermo_config`; per species: `smiles`, `charge`,
`multiplicity`, `n_pool`, `n_kept`, `dropped` (each with reason), per record: class label where
defined, E, G, ZPE, S components, σ, g, weight, lowest 6 frequencies, xyz; `ensemble_gibbs_hartree`;
fixture-derived quantities (slices 07, 08). Floats via `repr`. Deterministic except `commit_sha`;
metrics live in the acceptance record.

**Acceptance record (`docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`, `record_schema: 1`):** the v0.2.0
`GPU_SMOKE_RESULT.json` conventions (`commit_sha`, `run_at_utc`, `hardware`, `commands`, `logs`,
`known_limits`, `evidence`), plus `fixtures.<fixture>.<recipe>`: per-stage `wall_time_s`,
`engine_calls`, `cache_hits`; `optimizer_steps_total`, `recovery_steps`; `device`; `regression`
(`pass`|`fail`|`pending_promotion`) with deltas; `accuracy` (`pass`|`fail`|`reported`|
`pending_reference`); `smiles_confirmation` (T1/T2: `confirmed`|`pending_confirmation`|`fail`);
`incremental_solvation` (observed vs expected calls); `species_stage_cache` (T2, HF2). `pending_*`
are allowed in slice 09; slice 10 runs with `ETA_RXNCAT_ACCEPTANCE=1`, where they fail.

**Reference values (`tests/fixtures/v0.3.0/reference_values.json`, TJ only):** the team writes the
format and `tests/e2e/data/reference_values.example.json`. Entries: `quantity` ∈
{`hf1.dE_gauche_anti`, `hf1.dH_gauche_anti`, `hf1.dG_gauche_anti` (per conformer), 
`hf1.gauche_population` (reported only), `hf2.dG_r`, `hf2.dH_r`}, `value`, `unit` (`kcal/mol`|
`percent`), `standard_state` (`1 atm`|`1 bar`|`1 M`|`n/a`), `temperature_k`, `source`,
`level_of_theory`. The loader converts to 1 M (1 bar ↔ 1 atm by RT ln 1.01325). A quantity TJ
omits is `reported`.

### Algorithms (normative where a test depends on them)

- **Normal modes:** symmetrise and mass-weight the Hessian (masses: RDKit
  `GetMostCommonIsotopeMass`, recorded in `masses_source`, error on a miss); build translations and
  rotations about the COM, orthonormalise by SVD (rank 5 if linear, else 6; N = 1 rank 3); diagonalise
  in the complement so exactly 3N−6/3N−5 eigenvalues result; ν̃ = sign(λ)√|λ| in cm⁻¹ via
  `thermo.constants`. Imaginary: < −imag_tol; soft: [−imag_tol, 0), used with |ν̃|.
- **Symmetry number:** σ = number of graph automorphisms (RDKit `GetSubstructMatches(mol, mol,
  uniquify=False, maxMatches=max_automorphisms+1)`, with H) whose proper-rotation Kabsch RMSD
  (det = +1) to the identity mapping is ≤ sym_tol; cap reached → `ThermoInputError`. Linear: σ = 2
  if centrosymmetric, else 1.
- **Thermochemistry (ideal gas, per mole):** Sackur–Tetrode at p° = pressure_atm; E_trans = 3/2 RT;
  rotation nonlinear S = R[ln(√π/σ·(8π²k_BT/h²)^{3/2}√(I_A I_B I_C)) + 3/2], E = 3/2 RT; linear S =
  R[ln(8π²I k_BT/(σh²)) + 1], E = RT; atom 0. Vibration: ZPE and E_vib (thermal excess, excl. ZPE)
  from RRHO for every real mode; S by Grimme: w = 1/(1+(ω₀/ω)^α), S = w·S_RRHO + (1−w)·S_r with
  S_r per R15, B_av = `qrrho_rotor_moment_kg_m2`; enthalpy not damped. Electronic S = R ln(2S+1).
  H = E + ZPE + E_trans + E_rot + E_vib + RT; G = H − TS + RT ln(c°k_BT/p°) (c° in molecules/m³,
  p° in Pa).
- **Boltzmann:** weights ∝ gᵢ exp(−Gᵢ/RT) by log-sum-exp; G_ens = −RT ln Σ gᵢ exp(−Gᵢ/RT).
- **Conformer flow:** pass 1 ETKDGv3 (`randomSeed=seed`, `pruneRmsThresh=-1`, `numThreads=1`,
  `enforceChirality=True`), pass 2 identical but `useExpTorsionAnglePrefs=False` (when
  `torsion_free_pass`); seeds; pre-dedup with H (seeds first, then ids ascending); optimize each
  survivor; dedup with H at rmsd_dedup; energy window on the optimized electronic energy; frequency
  per kept; imag-mode push once (new `geometry_opt` row), else drop `not_a_minimum`; degeneracy and
  mirror-partner drop (R3); thermo; ensemble. Graph-achiral: canonical isomeric SMILES equals that
  of the mirror (tetrahedral tags inverted; R37 limit).
- **Runner drop rule:** a conformer is dropped (with reason) on `OptimizationFailedError`,
  `ScfConvergenceError` or `NotAMinimumError` after the push. `EngineUnavailableError`,
  `EngineInputError`, `EngineRuntimeError` and every `OptimizerInputError` propagate.

### Dependencies, extras and licence gate

- `pyproject.toml`: `geometric` leaves `[project].dependencies`; extra `opt-geometric =
  ["geometric==1.1.1"]`; dev group gains `geometric==1.1.1` (R5); lock diff per R14.
- Licence gate: new profile `opt-geometric` (runtime base + the extra) with the pinned exemption;
  `base` drops it; `gpu`/`mlip-mace`/`mlip-uma` keep it (R38 citation); `tools/licence_gate.py`
  `PROFILES` gains the name (code change + test); CI `licence-extras` matrix gains the profile;
  AGENTS.md "Licence guardrails" rewritten accordingly.
- New ADR for TJ Q3 "A" amending ADR-0011's scope: proposed by resolve as lore (Step 5), not
  written by a slice.
- `tests/unit/test_package.py`: `eta_rxncat.core`, `.thermo`, `.conformers`, `.optimize` load no
  `geometric`, `torch`, `pyscf`, `fairchem`; `geometric` imported only inside functions of
  `optimize/geometric_impl.py` (AST); ADR-0014 ban list unchanged.
- Acceptance envs (build seat creates; audit runs `uv run --no-sync`): `.venv-accept-opt`
  (`--extra opt-geometric`; xtb recipe; xtb binary `~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`)
  and `.venv-accept-uma` rebuilt as `--extra gpu --extra mlip-uma --extra opt-geometric` (UMA
  recipe and the PySCF PCM check). AGENTS.md "Engine tests" updated in slice 04.

### Test tiers and tolerances

- **Tier D** (default suite, `.venv`, offline): thermo closed forms rel 1e-9 / abs 1e-12 Eh;
  analytic toy frequencies 1e-6 cm⁻¹; σ exact; validators pass/reject; keys byte-identical;
  optimizer on UFF; ladder with a fake engine; conformers on UFF; counts exact.
- **Tier N** (candidate → TJ → promote): HF1, HF2, T1, T2 per recipe, and `e2e5_smiles.json`.
- **Regression vs promoted (Q5 "A", both recipes, fresh store, same device):** lowest record's class
  exact (HF1 torsion class; T1 diene class; other species by RMSD ≤ 0.125 Å with H); σ and g of
  every matched record exact; \|ΔE\| ≤ 1e-5 Eh; G, ΔG, ΔG_r ≤ 0.05 kcal/mol; weights ±0.02 absolute;
  record matching per R18.
- **Accuracy (Q5 "A"):** UMA: HF1 Δ(gauche − anti) within 0.5 kcal/mol of TJ's value of the same
  kind; HF2 ΔG_r(1 M) within 2.0 kcal/mol. xtb: `reported`. Omitted quantity: `reported`.
- **T1/T2 tier gating (Q-E5 "C"):**

| Check | xtb (GFN2) | UMA |
|---|---|---|
| Structural (kept count, 0 imag at lowest, weights sum, G_BA ≤ G_lowest, both T1 classes present, P1a_n σ = 1 and g = 1, atom/charge conservation) | gated | gated |
| Caching (T2) per US-016 | gated (ALPB rerun) | gated (plain rerun) |
| Sign: T2 ΔG_rxn(1 M) < 0 | gated (GFN2 ≈ −52) | gated |
| Ordering: T1 lowest s-trans G < lowest s-cis-side G | gated (R25: H12 verified by resolve) | gated |
| Window: −42 < T2 ΔG_rxn(1 M) < −20 | reported (expected ≈ −52) | gated |
| T1 ΔE(s-cis-side − s-trans) vs 2.2 | reported | reported (label per R32) |

- **Escalation (R26):** a gated failure fails acceptance. `known_limits` lists reported deviations
  and, when GFN2 cannot carry a tier TJ needs, the proposal that MACE/UMA/OMol25 become standard,
  which the lead raises to TJ as an update. The default recipe stays GFN2 until TJ answers.

### Human fixture inputs (team-drafted, provisional per Q-E3)

- **HF1** `tests/e2e/data/hf1_butane.yaml`: `CCCC`, 0, 1, `n_embed` 50, seed 42. Recipes `xtb`
  (`xtb_subprocess`/`gfn2` for every stage) and `uma` (`uma_direct`/`uma-s-1p2p1`,
  high-precision `inference_settings`). `ThermoConfig()` defaults. Torsion class from C1–C2–C3–C4
  (atoms 0–3): |φ| > 120° anti, else gauche. Expected: one anti (σ 2, g 1), one gauche (σ 2, g 2).
- **HF2** `tests/e2e/data/hf2_diels_alder.yaml`: 1,3-butadiene `C=CC=C` (expected s-trans and
  s-cis-side/gauche records, R21), ethylene `C=C`, cyclohexene `C1CC=CCC1` (half-chair, g 2); all
  0/1; `ReactionSpec` butadiene + ethylene → cyclohexene. Incremental: xtb ALPB(toluene, gsolv) per
  kept record; PySCF PCM per R20 on ethylene's lowest, `pbe0`/`def2-svp`, CPU (both recipes).
- **T1/T2** under `tests/e2e/data/e2e5/`: TJ's four XYZ byte-identical in `xyz/`, `SOURCES.md`,
  `t1_dimethoxybutadiene.yaml`, `t2_cp_cyclopropene.yaml`.

| Tier | XYZ (TJ) | sha256 prefix | Derived SMILES (H10) | Expected |
|---|---|---|---|---|
| T1 | `2_dimethoxybutadiene.xyz` (C6H10O2, 18, 0, 1) | `12afa0690b7b3eac` | `C=C(/C=C/OC)OC` | s-trans and s-cis-side classes, methoxy rotamers; ≥ 2 kept |
| T2 | `1_cyclopentadiene.xyz` (C5H6, 11, 0, 1) | `db8390fcc9fc9212` | `C1=CCC=C1` | one conformer; σ 2 |
| T2 | `5_cyclopropene.xyz` (C3H4, 7, 0, 1) | `e61f12a6a2a1ea3f` | `C1=CC1` | one conformer; σ 2 |
| T2 | `P1a_n.xyz` (C8H10, 18, 0, 1) | `c7b9792c062bdff4` | `C1=C[C@H]2C[C@@H]1[C@H]1C[C@H]12` | one conformer; σ 1; g 1 |

  Settings: `n_embed` 40 (T1), 10 (each T2 species), each XYZ as a seed; this SPEC's dedup, window
  and recipe-engine ranking (DV-19). References (TJ's headers, M06-2X/6-31G(d), 1 atm; Liu, Paton,
  Kim, Liang, Houk, *J. Am. Chem. Soc.* 2013, 135, 15642, DOI 10.1021/ja408437u): T2 ΔE −51.42,
  ΔG −32.28 kcal/mol (−34.17 at 1 M); T1 s-trans/s-cis ΔE 2.2 kcal/mol (SI p. S6). SI PDFs and the
  builder are never committed.

### Discrepancy register (`docs/prd/v0.3.0/DISCREPANCIES.md`, minimum rows)

DV-01 thermo math in core → `eta_rxncat.thermo`; DV-02 no σ → σ from geometry; DV-03 B_av = mean
moment → `qrrho_rotor_moment_kg_m2`; DV-04 linear E_trans+rot 3 RT → 5/2 RT; DV-05 21-element mass
table, others 12.0 → RDKit Z 1–118, error on miss; DV-06 drops six eigenvalues nearest zero →
complement diagonalisation; DV-07 modes in (−10, 10) dropped → |ν̃| soft modes; DV-08 `head_gordon`
offered, falls back → not offered; DV-09 `is_valid_stationary_point` flag → `NotAMinimumError`;
DV-10 XYZ input, returns input on failure → SMILES, typed errors; DV-11 RDKit pruning merges
mirrors, no energy window → own dedup, degeneracy, window; DV-12 exponents clipped at 500 →
log-sum-exp; DV-13 geomeTRIC top-level import, writes in cwd, reconfigures logging → lazy, extra,
lower-level API (R2); DV-14 bare `except Exception` tric → cart → three-step typed ladder; DV-15
starter engine API → v0.2.0 `Engine.evaluate`/`PotentialResult`; DV-16 hard-coded fake energies →
tier-D and real runs; DV-17 starter `MolecularState` → v0.1.0 contract; DV-18 PD-007 → TJ Q4 "C";
DV-19 TJ's tier YAMLs (graph schema, `rdkit_ff` ranking, 0.35/0.25 Å) → provisional v0.3.0 format;
DV-20 TJ's `hits_by_stage["gs_opt_freq"] == 3` → `species_stage_cache`; DV-21 isotope labels → refused
(R16); DV-22 single ETKDG pass misses s-cis-side → second torsion-free pass (R21); DV-23
`PotentialResult` frozen-ness carried forward (consumers copy matrices).

## 6. Negative Constraints

- **DO NOT** import `geometric` anywhere except inside functions of
  `src/eta_rxncat/optimize/geometric_impl.py`. **DO NOT** call `geometric.optimize.run_optimizer`.
- **DO NOT** add an agent-made licence exception; the only exemption change is the one TJ's Q3 "A"
  moves. Any other failing package is reported to TJ.
- **DO NOT** write to `tests/fixtures/`, promote a candidate, invent reference values, or confirm,
  correct or "fix" a derived SMILES on TJ's behalf.
- **DO NOT** read `tests/candidate_outputs/` or `spec/archive/` during stage work, including
  through git: every `git diff`, `git show`, `git log -p` over a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`. Committing a candidate is not promoting it.
- **DO NOT** edit TJ's XYZ files (bytes, comment lines, atom order); seeds are reordered in memory.
  **DO NOT** commit the SI PDFs or TJ's builder, or execute the builder at all.
- **DO NOT** accept a seed whose perceived stereo differs from the SMILES.
- **DO NOT** decide a gate from the output of the code it gates.
- **DO NOT** pass acceptance with a gated check listed under `known_limits`, gate GFN2 on a numeric
  literature window, or widen TJ's T2 window. **DO NOT** switch the default recipe in v0.3.0.
- **DO NOT** build T3–T5, a YAML suite runner or the topology audit.
- **DO NOT** loosen a tolerance to make a run pass; a bound measured noise breaks is
  stop-and-report.
- **DO NOT** return an input, a partial result or a flag in place of a typed error; **DO NOT** catch
  `EngineError` in the optimizer bridge or ladder.
- **DO NOT** use `pruneRmsThresh` for dedup, a reflection in any dedup/σ RMSD, or
  `GetSubstructMatches` without an explicit `maxMatches`.
- **DO NOT** default a symmetry number, a mass or a multiplicity.
- **DO NOT** store `ThermoResult` as a store row, or overwrite gas-phase G with a solvated value.
- **DO NOT** change any engine file or the `eta_rxncat_engines` node.
- **DO NOT** edit `architecture.yml` by hand; `hyper_ledger.py` with `--id` on existing nodes.
- **DO NOT** run `HACF-install.sh`, `HACF-uninstall.sh` or `hyper_migrate.py apply`.
- **DO NOT** push, tag or open a PR; **DO NOT** modify `PRDs/`.
- **DO NOT** hard-code version facts in tests; derive them from the lock, `importlib.metadata`,
  geomeTRIC's `params.py` or records.
- **DO NOT** put the HF token in any file, row, log or record.

## 7. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| FD Hessian noise moves G past 0.05 kcal/mol between distinct converged geometries | Medium | High | H5 (R10) measures it first; stop and report; never loosen. |
| UMA misses TJ's T2 window | Unknown | High: acceptance fails | Measured in slice 08 before acceptance; stop and report with numbers; never widen. |
| The s-cis-side class collapses on UMA | Low (survives GFN2, R21) | Medium | H14 in slice 05; a collapse is a finding to the lead with dihedrals, not a dropped gate. |
| GFN2 overbinds T2 by ~17.8 kcal/mol (ΔG ≈ −52 at 1 M), HF2 likely similar | Certain on GFN2 | Medium | Window reported on GFN2 (Q-E5 "C"); escalation proposal in `known_limits`. |
| Automorphism count explodes on later, larger molecules | Low now | Medium | Explicit `maxMatches`, cap raises; point-group finder owned by v0.4.0+ (R8). |
| geomeTRIC's lower-level API differs from expectations | Low | Medium | H6 in slice 04 before code depends on it; stop and report. |
| Lock re-resolution drifts | Low | Medium | Exact expected diff (R14); anything else stop and report. |
| The release waits on TJ's promotion and references | Certain | Schedule | Structural: slices 01–09 complete first; slice 10 runs after the gate (R22). |
| TJ corrects a SMILES | Low | Medium | Rework slice via resolve replan before slice 10 (R22). |
| RDKit bond perception yields a wrong molecule | Low (H10) | High | Tier-D re-derivation; TJ confirms before acceptance. |
| A seat reads candidates through git | Medium | Medium | Pathspec exclusion rule (R23) and H13. |
| Ledger description limits break an audit | Medium | Low | Trims in slices 01/02; engines untouched (R11). |

## 8. Success Metrics

- All 17 user stories pass; every AGENTS.md required check exits 0 in every slice; licence gate
  passes in `base`, `opt-geometric`, `gpu`, `mlip-mace`, `mlip-uma`.
- Tier-D suite: `uv run pytest` in `.venv` (offline) completes in under 60 s for the v0.3.0 unit
  tests (recorded: `uv run pytest tests/unit/thermo tests/unit/conformers tests/unit/optimize
  tests/unit/orchestrator --durations=0`).
- Incremental counts exact (HF2: 0 upstream, Σ n_kept ALPB calls, 1 PySCF; T2 per US-016).
- `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json` at a recorded commit, from slice 10's run with
  `ETA_RXNCAT_ACCEPTANCE=1` and zero skips: xtb recipe `UV_PROJECT_ENVIRONMENT=.venv-accept-opt
  ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m "e2e and not mlip_uma" tests/e2e`, UMA recipe
  `UV_PROJECT_ENVIRONMENT=.venv-accept-uma ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m
  "e2e and mlip_uma" tests/e2e`; regression `pass` for every fixture/recipe; accuracy `pass` (UMA)
  or `reported` (xtb); T1/T2 gates per the tier table; SMILES `confirmed`; per-stage metrics.
- README and CHANGELOG v0.3.0 claims derived from that record (tests enforce it).
- `DISCREPANCIES.md` ≥ 23 rows; PD-007 `decided`.
- Candidates for HF1, HF2, T1, T2 (both recipes) and `e2e5_smiles.json` committed in
  candidates-only commits; `git diff --stat Base..HEAD -- tests/fixtures` shows only TJ's own
  commits there.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.3.0.1 | slices/01-starter | Unpack the v0.3.0 reference starter byte-identical into docs/prd/v0.3.0/, open the 23-row discrepancy register, mark PD-007 decided, and trim the scaffold ledger description to 1800 characters or fewer. |
| OPR.0.3.0.2 | slices/02-core-contracts | Add frozen, strict core contracts (ThermoAnalysisOptions, ThermoResult, OptimizerIdentity, OptimizationResult, ConformerRecord, ConformerEnsemble) with pass/reject tests, keep eta_rxncat.core free of numpy/RDKit/geomeTRIC, and trim the core ledger description. |
| OPR.0.3.0.3 | slices/03-thermo | Create eta_rxncat.thermo: CODATA 2018 constants, Eckart-projected normal modes, rotational symmetry number from geometry and capped graph automorphisms, Grimme quasi-RRHO at 1 M, log-sum-exp Boltzmann with degeneracies, and the ground-state check, all proved by tier-D tests. |
| OPR.0.3.0.4 | slices/04-optimizer | Create eta_rxncat.optimize: the Optimizer interface and errors, GeometricOptimizer on geomeTRIC's lower-level API in a logging/file sandbox with a recorded three-step ladder, and move geomeTRIC from the base runtime into the opt-geometric extra and dev group with its own licence profile (TJ Q3 A). |
| OPR.0.3.0.5 | slices/05-conformers | Create eta_rxncat.conformers: two-pass ETKDGv3 (second pass without experimental torsion preferences, F21), stereo-checked seeds, proper-rotation dedup over automorphisms, energy window, per-conformer mirror degeneracy and ensemble build, re-proving s-cis-side sampling and survival by an independent route. |
| OPR.0.3.0.6 | slices/06-species-runner | Create eta_rxncat.orchestrator: the single-species stage runner with store caching per stage, counted engine calls, one imaginary-mode push, incremental single points, per-stage metrics, ReactionSpec free energies at 1 atm and 1 M, and a deterministic JSON report writer. |
| OPR.0.3.0.7 | slices/07-human-fixtures | Run Human Fixtures 1 (n-butane) and 2 (butadiene + ethylene to cyclohexene, 1 M) end to end on the xtb and UMA recipes with the incremental-solvation counts, reference-values format and regression helpers, and commit the candidate outputs in a candidates-only commit. |
| OPR.0.3.0.8 | slices/08-e2e5-tiers | Land TJ's four XYZ verbatim with provenance, re-derive the T1/T2 SMILES for TJ's confirmation, and run Tier 1 (dimethoxybutadiene) and Tier 2 (Cp + cyclopropene to endo P1a_n, with incremental ALPB dioxane) on both recipes into committed candidates. |
| OPR.0.3.0.9 | slices/09-acceptance-record | Run HF1, HF2, T1 and T2 on both recipes in the named acceptance envs and write docs/prd/v0.3.0/ACCEPTANCE_RESULT.json with per-stage metrics and pending verdict states, deriving the README v0.3.0 claims from it, with no dependence on TJ acting first. |
| OPR.0.3.0.10 | slices/10-acceptance-verdict | After TJ's Phase 3 promotion, rerun every fixture on both recipes on fresh stores with ETA_RXNCAT_ACCEPTANCE=1 and zero skips, record the regression, accuracy and SMILES-confirmation verdicts, bump the version to 0.3.0 and derive the final README claims. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
