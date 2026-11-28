# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.1] - 2026-11-27

A quality point release: no new features, CPU only (RDKit UFF and GFN2 xtb in the new tests; no
GPU, UMA, MACE or PySCF run). The release record is `docs/prd/v0.7.1/QUALITY_RESULT.json`, written
by `tools/quality_record_v071.py` from the verdict runs and the committed `seam_breaks.json` files.
Each claim below names its test and its record key. Where only one of these exists it names that:
a known issue with no test and the removal result cite their record key, a lore claim its node id,
and an added tool or test file its path.

### Added
- **Integration suite** (`tests/integration/`), with real modules on both sides of each seam and a
  policy test (`test_integration_policy.py`) that forbids mocks and silent skips. Tier O
  (`test_seams_offline.py`, RDKit UFF) runs in the default suite; Tier X (`test_seams_ts_gfn2.py`, `test_seams_selectivity_gfn2.py`, CPU GFN2
  xtb) runs with `-m "integration and xtb"`. A named source break made each seam test fail
  (`integration_tests`, `suites.default`, `suites.integration_x`).
- **Per-sample stage keys** (TJ Q-71a A): `eta_rxncat.orchestrator.SampleKeys` and
  `TSEnsembleRun.samples` (`test_sample_keys_name_every_samples_rows`,
  `test_a_cached_run_records_the_same_sample_keys`,
  `test_tx2_ensemble_sampler_relax_and_store`, `integration_tests`). `tests/e2e/v070.py` keeps
  three private eta imports (`_PreRelax` and `_digest` for call attribution, `_canonical_smiles` for reactant specs),
  each listed with its reason in slice 03's proof, as that slice's requirement 2 allows. Mission goal
  G4 words this as no private import; it is judged by the slice's wording.
- `tools/engine_reachable.py` (the dead-code exclusion set; `dead_code`), a stale-reference scan
  (`tests/unit/test_doc_refs.py`, `suites.default`) and `tools/quality_record_v071.py`
  (`suites.default`).

### Changed
- **Version 0.7.1** in `pyproject.toml`, `src/eta_rxncat/__init__.py` and `uv.lock` (slice 09). A
  point release takes its `X.Y.0` roadmap position
  (`test_version_identity_point_release_readme_passes`, `version`).
- ADR-0053's reader claim is narrowed by the PROPOSED node ADR-0066, which supersedes it, pending
  TJ's approval (slice 08).

### Fixed
- t3 writes the xtb `gated_on` text of the v0.5.0 acceptance record
  (`test_gated_on_text_equals_the_record`, `known_issues` R10).
- The test-policy skip scanner now sees import aliases, decorators, defaults and class bases, and a
  teardown skip fails an acceptance run (`test_module_level_skip_scanner`,
  `test_teardown_skip_fails_under_acceptance`, `known_issues` R11).
- `ArtifactStore(open_timeout_s=math.inf)` means no deadline, and a `bool` or non-real value raises
  `TypeError` (`test_infinite_open_timeout_waits_for_a_held_lock`,
  `test_open_timeout_must_be_a_real_number`, `known_issues` R13/R29).
- Importing `mace` restores `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD`
  (`test_importing_mace_leaves_the_torch_env_as_it_was`, `known_issues` R14).
- The licence gate labels a bare "BSD" licence "BSD (variant not stated)"
  (`test_bare_bsd_passes_with_the_label`, `known_issues` R28).
- A run record with an infinite selectivity ratio writes `"Infinity"` and reads back (TJ Q-71b A;
  `test_an_infinite_ratio_round_trips_as_the_string_infinity`, `known_issues` R38).
- The wheel test builds offline (`test_the_wheel_build_is_offline`, `known_issues` R39).
- The review bundle's host-data scan skips only the byte-pinned vendored files
  (`test_the_host_data_scan_skips_the_pinned_3dmol_file`, `known_issues` R40).

### Removed
- Nothing. The scripted dead-code pass (R17, R31) found no symbol meeting all four removal
  conditions (`dead_code.removed` is empty; `dead_code.kept` lists the candidates).

### Known issues
- `PotentialResult` is not strict about floats and is frozen only shallowly. This is kept for the
  v1.0 API-freeze review (R15, `known_issues`).
- **HF-13 (carried).** geomeTRIC's pre-relax can still stall inside the black box. The guard bounds
  the stall; the out-of-process cure is v0.8.0
  (`test_a_stalled_loop_is_interrupted_near_the_budget`,
  `test_a_stalled_pre_relax_is_excluded_and_the_ensemble_continues`, `known_issues`).
- **Multi-site forming bonds** (deferred: an enumerator behaviour change no shipped plan exercises).
  A later site can delete an earlier site's forming-bond or core atom (`known_issues`).
- **`+` in library entry ids** can collide joined candidate ids (deferred: the fix changes the
  `EnumerationPlan` contract; no shipped id contains `+`; `known_issues`).
- `run_selectivity` runs only priority-1 pathways, while the v0.7.0 plan's TS nodes are priority 2
  (deferred to v0.8.0's scheduler, which owns the join; `known_issues` R35).
- **geomeTRIC edge cases** (deferred to v0.8.0's out-of-process geomeTRIC; R41): a deadline inside
  temporary-directory cleanup can leak one directory, and one inside step marking can leave a step
  partly marked (`known_issues` R41).
- The review page's red frequency-failure box is unchanged (deferred: TJ's call; `known_issues`).
- The `mace` environment guard (R14) restores nothing if `mace` was already imported in the process,
  and covers the `import mace` line only (`test_importing_mace_leaves_the_torch_env_as_it_was`,
  `known_issues`).
- With `cartesian_basis=True` on CUDA, the PySCF engine can take the GPU analytic Hessian path for a
  class whose support record was measured without that option (slice 08; no GPU run in this release;
  `known_issues`).
- `tests/e2e/v070.py` `checked_record_text` still refuses an infinite ratio, and its docstring still
  says it would be written as `null` (slice 07 QA; `known_issues`).
- In `tests/e2e/t3.py` the `GFN2_REPORT_ONLY_FIXTURE` line separates
  `ENERGY_SOURCE_BOUND_KCAL_MOL` from its docstring (slice 06 QA; `known_issues`).
- The integration policy scanner does not catch `builtins.getattr`, objects returned by eta calls,
  non-constant module names or patchers passed by other routes (slice 06 QA; `known_issues` R44).

## [0.7.0] - 2026-11-27

**Acceptance** (`docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`, verdict `pass`, `verdict_reasons` empty,
derived by `tests/e2e/acceptance_record_v070.py`): default suite `uv run pytest` 2690 passed,
0 failed, 196 deselected, exit 0. The selectivity scores are report-only (ΔΔG‡ kcal/mol, % de):
ethyl UMA 4.57 / 99.91, ethyl GFN2 3.93 / 99.74, n-propyl UMA 4.97 / 99.95, n-propyl GFN2 4.23 /
99.84.

### Added
- **Library enumeration** (`eta_rxncat.mapping`). Each library entry is grafted onto each declared
  (node, template) pair with eta's `graft`, on one site or on several (a Cartesian product with a
  cap). Entries carry declared `charge_delta` and multiplicity, with parity refused when wrong. A
  refused graft is recorded with its reason rather than skipped.
- **Ranked template fallback** (`eta_rxncat.mapping`, `eta_rxncat.conformers`). A node's templates
  are tried in declared rank order. At run time the TS ensemble runner falls through to the next
  template only when a seed fails TS validation, and only on the R4 allow-list. An `EngineError`
  still propagates (TJ Q-A1 B).
- **Seed geometry checks** (slice 15). A start geometry with a pair three or more bonds apart
  closer than 1.3 × the sum of covalent radii is rejected as `seed_clash` before any engine call.
  The sample is recorded and not replaced (TJ Q-R7a A and Q-R7b A). `bond_changed:pre_relax` and
  `bond_changed:ts` record a topology change at those stages.
- **Optimization frames** are stored as payload (ADR-0053). Geometry frames from geomeTRIC and
  P-RFO appear in success and failure payloads. Stores are forward-only: a row written before this
  release reads as "no trajectory stored".
- **Run-data contract.** `RunData` is the one public JSON contract (`schema_version` 1). The review
  page renders it.
- **Offline review bundle** (`eta-rxncat review-bundle --record <run.runrecord.json> --store <run.sqlite> --out <dir>`).
  It is a static HTML page with a content security policy, opens by double-click, and needs no
  server or network. The 3Dmol.js 2.5.5 viewer (BSD-3) is a vendored output asset that no Python
  module imports.
- **Review site dispositions** (slice 16). Every row is labelled used or not used, with its reason.
  Each TS shows its identity numbers, and a banner marks an identity failure.
- **E2E acceptance on GFN2 and UMA.** Ethyl and n-propyl on TS1a_n, endo and exo, as a single-site
  enumeration. Three fallback constructs: graft-time fallback on GFN2, and run-time fallback on GFN2
  and UMA. The mechanics gates are the pass criteria; ΔΔG‡ per R is report-only.

### Changed
- **Version 0.7.0** in `pyproject.toml`, `src/eta_rxncat/__init__.py`, and `uv.lock` (slice 14).
- The HF-13 guard keeps its 600 s base and ADR-0024. Its budget now scales with host load up to a
  cap (R7, slice 05). The out-of-process cure is v0.8.0 (TJ Q-A2 A).

### Fixed
- v0.5.0 `ACCEPTANCE_RESULT.json` text only: the xtb `gated_on` of n4, ts1a_n, ts1b_n and ts3a now names the R32 identity core, and TS4a reads report-only (TJ advisor row 1b51c1b3, 2026-11-26). No value, verdict or hash changed.
- geomeTRIC runs each call in a per-run temp directory (R8, slice 06), so it no longer writes
  `HT.v_*.txt` mode files into the working directory. This closes the v0.6.0 known issue of the
  same name.

### Phase 3 (TJ)
- The first promotion was `9fdba68`. TJ's two findings on it were ethyl sample `1f64216a4471` (its
  start geometry put ethyl H21 0.438 Å from diene C4) and pre-push minimum `071c077d750a`. They led
  to replan 7 (slices 15–18).
- The re-review and re-promotion is `ef9225e`: 30 candidate files, promoted by TJ's answer "A".
  The new review bundle shows sample 6 as `excluded: seed_clash` and the minimum as
  `superseded by push`. TJ on the re-review site: "eta v0.7.0: the website review looks great".

### Known issues
- **HF-13 (carried from v0.6.0).** geomeTRIC's pre-relax can still stall inside the black box. The
  guard bounds the stall, and the out-of-process cure is v0.8.0. Slice 11's UMA ethyl exo run hit
  one `PreRelaxTimeout` at 600.005 s (load1 7.58; the stall cap of 2 was not reached). Slice 17's
  rerun has 0 stalls: the stalled sample (index 1, `fragment_embed:0`) is now rejected as
  `seed_clash` before any engine call (lead check of the slice 17 rerun record against `9fdba68`).
- **Multi-site forming bonds.** A later site can delete an earlier site's forming-bond or core atom,
  and each record validates only its own bonds (slice 04 QA, item b). The E2E is one site, so it
  does not exercise this.
- **Run records with `ratio = inf`.** `RunRecord.model_dump_json` writes `ratio` as null, and
  `model_validate_json` then fails. RunData exports ddG and never the ratio, so the bundle is not
  affected (slice 07 QA). The related store item is v0.7.1 R13.

## [0.6.0] - 2026-11-26

### Added
- **Selectivity between competing pathways** (`eta_rxncat.orchestrator`, `selectivity.py`). A
  pathway's free energy is a Boltzmann sum over its validated, deduplicated TS ensemble, and
  `score_selectivity` reports the multi-pathway ΔΔG‡ and a % de (the ee form is refused over
  multi-member ensembles, `SelectivityInputError`). A ratio overflow returns +inf rather than
  raising (R27).
- **Per-pathway pruning** (`PathwayPruningRule` in `core`, beside the existing `PruningRule`). It
  prunes a minor pathway's priority ≥ 2 nodes when its ΔΔG‡ exceeds a threshold. There is no
  library default. TJ's 1.5 kcal/mol rule is set in the Tier 4 mapped fixture (Q2 A, R7). The
  older global `skip_remaining_nodes` is not used.
- **TS conformer ensembles** (`eta_rxncat.conformers`). The TS sampler freezes the forming core
  and samples the rest. Each sample is re-optimised with P-RFO, deduplicated, and its member
  energies are combined into one Boltzmann sum. Each member carries a degeneracy.
- **Per-fragment TS embedding.** The sampler embeds each fragment with ETKDGv3, then applies a
  seeded perturbation to the non-core atoms. It replaces the draft's coordMap embedding, which
  failed by measurement (R16, HF-4).
- **HF-13 pre-relax wall-time guard.** The geomeTRIC pre-relaxation has a 600 s budget. On
  expiry it raises `PreRelaxTimeout`, which is recorded as an exclusion with its reason rather
  than a silent skip (ADR-0048, PROPOSED).
- **Tier 4 inputs and acceptance** (`tests/e2e/test_t4_*.py`). Unmapped
  and mapped endo/exo pairs run on GFN2 and UMA, with TJ's flexible alkyl series on TS1a_n (R =
  ethyl, n-propyl, n-butyl) checking mechanics only.
- **Phase 3 (TJ):** the ten v0.6.0 candidates are promoted to `tests/fixtures/v0.6.0/` in
  `6fce509`, with TJ's regression bounds (R31): |ΔE_TS| ≤ 1e-5 Eh, heavy-atom RMSD ≤ 0.01 Å,
  |ΔΔG‡| ≤ 0.01 kcal/mol on GFN2 and ≤ 0.75 kcal/mol on UMA.
- **v0.6.0 acceptance** (`docs/prd/v0.6.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run
  2026-11-26 at `b67214b`, on an NVIDIA GeForce RTX 5060 Ti with UMA `uma-s-1p2p1` (fairchem
  2.26.0) on CUDA and xtb 6.8.0 on the CPU):
  - default suite: 2212 passed, 0 skipped, 0 failed, 180 deselected, exit 0; every acceptance
    command exits 0;
  - the acceptance run's ΔΔG‡ for each pair and recipe, kcal/mol: GFN2 unmapped endo/exo 3.98,
    GFN2 mapped 1.75 (exo pruned by the 1.5 rule); UMA unmapped 4.60, UMA mapped 1.41 (computed);
  - reproducibility over three fresh-store runs, all within TJ's bounds: GFN2 repeats exactly;
    the largest UMA |ΔΔG‡| between runs is 2.3e-4 kcal/mol (mapped) and 4.6e-5 kcal/mol
    (unmapped).

### Changed
- **Engine errors in a TS search:** an xtb `EngineError` (such as exit 128) now ends the search
  as a cached `failed_reason` instead of escaping `run_transition_state`. This closes the
  v0.5.0 known issue of the same name (slice 03).

### Known issues
- **The Tier 4 Liu TSs converge to one member per pathway (HF-10).** The multi-member Boltzmann
  sum is proven by unit tests and by the flexible alkyl series, not by the Liu systems.
- **HF-13: geomeTRIC's pre-relax can stall inside the black box.** The 600 s guard bounds the
  stall and fired in real runs. On a loaded host it also fired for GFN2 (slice 12 audit), and a
  GFN2 unmapped endo and n-butyl now show a `PreRelaxTimeout` that the fixtures lack. The budget
  is sensitive to host load and a member can be cut. Planned for v0.7.0.
- **geomeTRIC writes `HT.v_*.txt` mode files into the current working directory.** The lead
  removed the files written during the slice 12 run from the repo root. A v0.7.0 fix is planned.
- **The mapped pair misses ADR-0040's margin.** Its UMA ΔΔG‡ margin is −0.09 against 1.0
  kcal/mol (slice 10, G6). This is reported, not a failure.
- **The pruning rule straddles its threshold.** On GFN2 the mapped exo is pruned (ΔΔG‡ +1.75
  kcal/mol); on UMA the same branch is computed (+1.41 kcal/mol). The 1.5 kcal/mol cut is
  TJ's choice, and the two recipes fall on opposite sides of it.
- **ADR-0048 is PROPOSED and stale since slice 13.** It awaits TJ's lore review at the version
  end, as do the other proposed ADRs.

## [0.5.0] - 2026-11-24

### Added
- **Transition-state contracts** (`eta_rxncat.core`, `core/ts_models.py`): `FormingBond`,
  `TSStep`, `TSSearchResult`, `TSValidationOptions`, `TSValidation` and `TransitionStateRecord`,
  frozen and strict like the other core models, with the validator's named reasons in
  `TS_VALIDATION_REASONS`. `OptimizerIdentity.name` now accepts `prfo` beside `geometric`, and the
  stage kinds gain `ts_opt`. The additions are new types; existing models and keys are unchanged.
- **P-RFO transition-state search** (`eta_rxncat.optimize`): `PRFOOptimizer` behind a new
  `TransitionStateOptimizer` interface, in Cartesian coordinates, numpy only. It is a clean-room
  implementation from Banerjee et al. 1985, Baker 1986 and Bofill 1994 and the mission spec; no
  code from the v0.5.0 starter or any other optimizer was used (TJ A1).
  - The maximised mode is the one with the largest overlap with the forming bonds, not the
    lowest mode. Rigid translations and rotations are projected out.
  - λ is solved by bracketed bisection/Newton to |Δλ| ≤ 1e-12; no offset is added to a step
    denominator.
  - Trust radius 0.10 Bohr within [0.001, 0.30], with step acceptance by the energy ratio; a
    rejected step reverts, shrinks the trust radius and refreshes the Hessian exactly.
  - Bofill Hessian updates between exact refreshes (every 5 accepted steps). When the secant
    condition already holds (r = 0) or the step is zero, the update returns the symmetrised
    Hessian before any division (R29).
  - Convergence needs all four criteria: max |g| ≤ 4.5e-4 and RMS g ≤ 3.0e-4 Eh/Bohr, max step
    ≤ 1.8e-3 and RMS step ≤ 1.2e-3 Bohr.
  - A failed search raises `TSSearchFailedError` with a named reason (`max_steps` at 100 steps,
    `too_many_rejections`, `mode_lost`).
- **Active-core frequency validator** (`eta_rxncat.thermo.validate_transition_state`), TJ A2:
  exactly one mode below −20 cm⁻¹, that mode below −50 cm⁻¹, and a mass-weighted active-core
  kinetic-energy fraction ≥ 0.60, always checked. TS identity is measured on the imaginary mode:
  forming-stretch overlap ≥ 0.50, both forming bonds in phase, and each forming distance in
  [1.90, 2.90] Å. Perceived connectivity is recorded, never gated. Unusable inputs raise
  `TSValidationInputError`; an unknown element has no default mass.
- **TS thermochemistry** (`ts_thermochemistry`): the quasi-RRHO of the minimum path with the one
  imaginary mode excluded, and the symmetry number taken from the TS's perceived bond graph
  (`rotational_symmetry_number_from_bonds`), with no TS degeneracy (TJ Q-TJ2 A).
- **TS runner and barrier** (`eta_rxncat.orchestrator`): `run_transition_state` runs the cached
  `ts_opt` stage, then computes the final Hessian in the cached `frequency` stage and validates
  with it (P-RFO returns no Hessian). `activation_free_energy` gives ΔG‡ at 1 M and at 1 atm
  from `BarrierSpec`/`BarrierEnergies`.
- **PySCF `cartesian_basis` option** on `pyscf_gpu_cpu` (default off). It reproduces Gaussian's
  6D default for Pople 6-31G-family bases. It enters the resolved stage and its key only when
  true, so every existing PySCF key is byte-identical (ADR-0041, TJ "A: key only when on").
- **Tier 3 inputs** (`tests/e2e/data/e2e5/`): five literature transition states, TS1a_n and
  TS1b_n (mapped), TS3a, TS4a (mapped by two grafts) from Liu et al., *J. Am. Chem. Soc.* 2013,
  135, 15642, and N4 from Paton et al., *Angew. Chem. Int. Ed.* 2011, 50, 10366, with their
  reactants and sha256 provenance in `SOURCES.md`. Through eta's PySCF engine (M06-2X/6-31G(d),
  `cartesian_basis=True`, `grids_level=4`) the six files with a printed electronic energy
  reproduce Liu's within 1e-4 Eh (largest |ΔE| 8.25e-5 Eh, 3-dimethyltetrazine). TJ confirmed
  the transcriptions.
- **v0.5.0 acceptance** (`docs/prd/v0.5.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run
  2026-11-24 at `b2046ca`). It ran on an NVIDIA GeForce RTX 5060 Ti, with UMA `uma-s-1p2p1`
  (fairchem 2.26.0) on CUDA and xtb 6.8.0 on the CPU:
  - default suite: 1794 passed, 0 skipped; all 13 acceptance commands exit 0;
  - UMA: all five TSs pass every gate (convergence, one imaginary mode, active core, TS
    identity, TJ's ΔG‡(1 M) window, conservation, cache reuse on a second run), and
    ΔG‡(TS4a) < ΔG‡(TS3a). ΔG‡(1 M), kcal/mol: TS1a_n 19.58, TS1b_n 29.09, TS3a 22.20, TS4a
    14.60, N4 26.61;
  - GFN2: TS1a_n, TS1b_n, TS3a and N4 pass convergence, the mode count and the identity core
    (overlap ≥ 0.50, in phase, KE ≥ 0.60). The forming-distance window, ΔG‡ and the ordering are
    reported. TS4a is report-only (TJ Q-TJ4 A);
  - regression against the fixtures TJ promoted, all within TJ's bounds (|ΔE_TS| ≤ 1e-5 Eh,
    heavy-atom RMSD ≤ 0.01 Å, |ΔΔG‡(1 M)| ≤ 0.75 kcal/mol on UMA and ≤ 0.01 on GFN2): the four
    gated GFN2 cases are exact; the largest UMA |ΔΔG‡| is 0.028 kcal/mol (TS3a);
  - geomeTRIC `--transition` black-box cross-check, reported and not gated: all 10 case × recipe
    runs converged; 8 pass eta's validator at geomeTRIC's TS (heavy-atom RMSD to eta's TS ≤ 6e-4
    Å); GFN2 TS3a and GFN2 TS4a do not.
- **Phase 3 (TJ)**: the 11 candidates promoted to `tests/fixtures/v0.5.0/` in `ccacac5`, with the
  regression bounds above (mission R33, "A: 0.75 all (Recommended)").
- **Records**: proposed ADR-0033 to ADR-0041 (awaiting approval), and the v0.5.0 starter
  discrepancy register `docs/prd/v0.5.0/DISCREPANCIES.md`. PD-009 in
  `docs/prd/PLAN_DISCREPANCIES.md` is decided.

### Changed
- **Thermochemistry**: `thermochemistry` and `ts_thermochemistry` share one body after the
  symmetry number, which the first takes from a SMILES and the second from a bond graph.
- **Development toolchain**: the Hypergraph Agentic Coding Framework was upgraded to v0.6.3
  (`0d2a8d3`). The package and its dependencies did not change.
- **README**: the v0.5.0 acceptance claims, derived from the record and enforced by tests; the
  Roadmap lists v0.5.0 as built.
- **Version** 0.5.0, bumped by slice 13 only on the verdict pass.

### Known issues
- **GFN2 finds no reaction TS for TS4a.** From the grafted, pre-relaxed start the search stops at
  `max_steps` (100). At 300 steps it converges to a wrong saddle, and from Liu's TS4a xtb exits
  with code 128 mid-search. TS4a on GFN2 is report-only (TJ Q-TJ4 A, R32).
- **An xtb crash escapes `run_transition_state`.** An `EngineError` (such as xtb exit 128) inside
  a TS search propagates instead of becoming a cached `failed_reason`. The acceptance test catches
  it for GFN2 TS4a only. A v0.6.0+ robustness item, not built.
- **UMA ΔG‡ is not bitwise reproducible on CUDA (float32).** Over three fresh-store runs the
  largest spread was 0.035 kcal/mol in the record and 0.074 kcal/mol in the slice 12 audit's
  runs, both on TS3a. UMA TS energies (≤ 4.4e-8 Eh) and geometries (≤ 2.4e-5 Å) reproduce far
  more tightly. This is why TJ's UMA ΔΔG‡ bound is 0.75 kcal/mol.
- **UMA TS4a ΔG‡(1 M) is 14.600 kcal/mol** against the window's upper edge of 14.7, about 0.10
  kcal/mol inside.
- **geomeTRIC cross-check:**
  - On GFN2 TS3a geomeTRIC converges to a soft saddle that is not the reaction's (about
    −37 cm⁻¹, forming overlap 0.0), while eta's GFN2 TS3a passes the identity core.
  - The Hessian seed is given in Eh/Bohr²; `geometric-optimize --help` states the file format
    but no units, so the units are an assumption.
  - geomeTRIC 1.1.1's "BSD 3-clause Non-AI" licence is an open question with TJ. It runs only as
    a CLI subprocess in an acceptance venv; nothing in `src/` imports it.
- **Full-atom RMSDs to the literature TSs are inflated by H and CF3 labelling under the atom
  map** (TS1b_n about 0.55 Å, TS4a about 1.11 Å). The forming-core RMSD on UMA is at most
  0.037 Å.
- **The tightest PySCF transcription margin** is 3-dimethyltetrazine at −8.25e-5 Eh against the
  1e-4 Eh bound (`grids_level=4`). `cartesian_basis` makes every shell Cartesian, so it matches
  Gaussian only for d-only Pople bases at 6D (R30).
- **ADR-0001 to ADR-0041 are PROPOSED.** ADR-0032 still says 1e-8 Å for the core-freeze bound
  (measured 1e-6 Å, R26).
- **Carried forward, still true:** `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the
  whole process; a non-deterministic engine failure stays cached until `invalidate` (R50);
  UMA results carry GPU noise; the graph YAML format is still provisional (TJ Q-E3).

## [0.4.0] - 2026-11-23

### Added
- **Graft contracts** (`eta_rxncat.core`): `GraftSpec`, `GraftResult`, `CloseContact` and
  `JunctionVolume`, in `core/mapping_models.py`. They are frozen and strict, with units in their
  names. `GraftSpec` combines the ADR-0005 `AtomMappingSpec` (keep, delete, alignment) with
  ordered `fragment_alignment` pairs, an optional `fragment_delete` list, an optional
  `constrained_core`, and an explicit product charge and multiplicity. A non-empty `anchors` list
  is refused. `eta_rxncat.core` still imports no numpy or RDKit.
- **Conserved-core mapper** (`eta_rxncat.mapping`), a new MIT package that depends only on numpy at
  import:
  - `superpose`: Horn (1987) quaternion superposition of ordered atom pairs. It always gives a
    proper rotation (det R = +1). The RMSD comes from the residuals, and optional weights are
    accepted. Fewer than three pairs, a collinear pair set, or a rotation that is not unique
    raises `AlignmentError`. `pair_set_shape` reports how far the pair set is from a line and
    from a plane.
  - `graft`: ordered atom surgery. The product lists the kept template atoms in keep order, with
    their coordinates copied bit for bit, then the fragment atoms that are neither paired nor
    deleted, in ascending order. Paired fragment atoms are always dropped. The product charge and
    multiplicity come from the spec and are never inferred. Active atoms and the core are
    re-indexed. Two atoms closer than 0.5 Å raise `GraftClashError`. Close contacts are recorded,
    using RDKit covalent radii × 1.3 over pairs that are not source-graph bonds, as are the
    junction signed volumes (handedness across each new bond) and a planar-pair-set flag.
    `index_map` names each product atom's source.
  - `relax_constrained_core`: a pre-relaxation with the core frozen, through the v0.3.0
    `Optimizer` (`frozen_atom_indices`, never a dihedral constraint). If a core atom moves more
    than 1e-6 Å, it raises `CoreDisplacementError`. The result is a TS guess, not a minimum.
  - `report`: `perceive_bonds` (RDKit `DetermineConnectivity`, imported lazily),
    `covalent_radius_angstrom`, `core_rmsd_angstrom` and `junction_volumes`.
  - Typed errors under `MappingError`.
- **Clean-room test vectors** (`tests/unit/mapping/data/cleanroom_nmap/`): seven checker-approved
  vectors, with their provenance. Vectors 01–05 and 07 (adapted to eta's conventions) reproduce
  at 1e-6 Å, and vector 06 (degenerate pairs) is refused. Alignment also agrees with an
  independent SVD Kabsch, written in the test file, within 1e-10 Å on 1000 random sets.
- **Fixture M1** (`tests/e2e/`): TJ's mapping, which grafts cyclobutene onto Liu's endo TS1a_n to
  make a TS1b_n guess and compares it with Liu's own TS1b_n (DOI 10.1021/ja408437u). The three
  XYZ files are byte-identical copies with sha256 provenance. The graft → TS1b_n atom map comes
  from a stated rule (the lexicographically smallest of the 32 element-preserving graph
  isomorphisms) and never from minimising an RMSD. Tier-D checks run in the default suite. The
  xtb and UMA pre-relaxations run under the `e2e` marker. The fixtures TJ promoted are in
  `tests/fixtures/v0.4.0/`.
- **v0.4.0 acceptance** (`docs/prd/v0.4.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run
  2026-11-23 at `2dbc3ec`). It ran on an NVIDIA GeForce RTX 5060 Ti, with UMA `uma-s-1p2p1`
  (fairchem 2.26.0) on CUDA and xtb 6.8.0 on the CPU:
  - default suite: 1433 passed, 0 skipped; clean-room vector tests: 65 passed;
  - M1 graft: forming-core RMSD to TS1b_n 0.0498 Å (bound 0.10); regression against the
    promoted graft 0.0 Å (bound 1e-10); TJ confirmed the atom map by promoting the graft;
  - M1 pre-relaxation, on both recipes: converged in 17 steps; core held to 4.19e-8 Å (xtb) and
    3.54e-8 Å (UMA), bound 1e-6; perceived connectivity equal to TS1b_n's; junction signs
    nonzero and equal to TS1b_n's (+1, −1);
  - relaxed regression against the promoted fixtures: xtb |ΔE| 0.0 Eh and heavy-atom RMSD
    4.5e-17 Å; UMA |ΔE| 2.2e-8 Eh and 7.7e-8 Å (bounds 1e-5 Eh and 0.01 Å).
- **Records**: proposed ADR-0028 to ADR-0032 (awaiting approval), and the v0.4.0 starter
  discrepancy register `docs/prd/v0.4.0/DISCREPANCIES.md` (DV-01 to DV-10 and CR-01 to CR-15, all
  closed at release). PD-008 in `docs/prd/PLAN_DISCREPANCIES.md` is decided.

### Changed
- **Clean-room provenance.** `eta_rxncat.mapping` was written from an approved behaviour
  specification and the mission's own spec. No code from `nMap` or the v0.4.0 starter was used.
  TJ chose the clean room because the original code's copyright is shared with Oregon State
  University, his advisor and his co-authors.
- **Development toolchain**: the Hypergraph Coding Agent Framework was upgraded to v0.6.2
  (`c3506e6`). The package and its dependencies did not change.
- **README**: the mapper features and the v0.4.0 acceptance claims, derived from the record and
  enforced by tests; the Roadmap lists v0.4.0 as built.

### Known issues
- **The core-freeze bound is 1e-6 Å, not 1e-8 Å.** geomeTRIC's `$freeze` holds frozen atoms to
  about 1e-8–1e-7 Å, so the bound was set by measurement (mission R26). ADR-0032 still says
  1e-8 Å and is waiting for TJ's lore review.
- **The pure M1 graft has four close contacts by design**: two C…H at 1.12 Å and two C…C at
  1.96 Å. They are recorded, not refused (TJ P1 A). The pre-relaxation is gated on TS1b_n's
  connectivity instead.
- **Junction handedness cannot be determined on a planar pair set.** On the pure M1 graft both
  junction volumes are about −0.0006 Å³ (sign 0), which is reported. The sign check is applied
  to the relaxed structures.
- **Clean-room vector 07 is odd-electron.** Its request's multiplicity 1 is not a valid state.
  The eta-adapted test uses multiplicity 2, which does not change the coordinates or the order.
- **Lax `JunctionVolume` fields.** `sign` accepts `True` and `1.0` as 1, and
  `signed_volume_angstrom3` accepts `True`. This is the same Pydantic laxness as
  `PotentialResult`.
- **UMA results vary slightly from run to run** because of GPU noise (|ΔE| about 1e-8 Eh, heavy-atom
  RMSD about 1e-7 Å). Both are far inside the regression bounds.
- **The M1 YAML is provisional** until the YAML/JSON graph format is defined (TJ Q-E3).
  `GraftSpec` stands alone for now. From v0.8.0 the graph loader builds it from
  `TemplateGeometry.mapping`.
- **Scope.** R-group and ligand enumeration stays at v0.7.0 (TJ roadmap B). The Rh(I) (5+2)
  complexes are v1.x.
- **ADR-0001 to ADR-0032 are PROPOSED.**
- **Carried forward from 0.3.0, still true:**
  - `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process.
  - A non-deterministic engine failure stays cached until `invalidate` (R50).
  - The UMA cyclohexene boats sit at the dedup threshold, and UMA `dropped` reasons can swap
    between runs.
  - GFN2 is reported, not gated, and stays the default recipe until TJ decides.
  - `stability.py` pins private PySCF 2.15.1 / GPU4PySCF 1.9.2 internals. The VRAM estimate
    does not cover GPU Hessians.
  - `PotentialResult` is frozen only shallowly, and its float fields are lax.

## [0.3.0] - 2026-11-23

### Added
- **Core contracts** (`eta_rxncat.core`): `ThermoAnalysisOptions`, `ThermoResult`,
  `OptimizerIdentity`, `OptimizationResult`, `ConformerRecord` and `ConformerEnsemble`. They are
  frozen, strict and data-only. `eta_rxncat.core` still imports no numpy, RDKit or geomeTRIC.
- **Thermochemistry** (`eta_rxncat.thermo`): ideal-gas quasi-RRHO (Grimme 2012, ω₀ 100 cm⁻¹) at a
  1 M standard state from a Cartesian Hessian. It uses CODATA 2018 constants and Eckart-projected
  normal modes, in which every mode is kept and soft modes are listed. The rotational symmetry
  number comes from the geometry and capped graph automorphisms, and masses come from RDKit for
  Z 1–118. Boltzmann weights use log-sum-exp with degeneracies, without clipping.
  `check_ground_state` raises `NotAMinimumError` on an imaginary mode.
- **Optimizer interface** (`eta_rxncat.optimize`): `Optimizer`, `DihedralConstraint` and typed
  errors. `GeometricOptimizer` drives geomeTRIC 1.1.1's lower-level API, never `run_optimizer`.
  Each run uses a temporary directory and a sandboxed `geometric` logger. It records a recovery
  ladder: `tric`, then `tric_tight_trust`, then `cartesian`, or `hdlc` for a constrained run.
- **Conformers** (`eta_rxncat.conformers`): two-pass ETKDGv3 pools from a SMILES. The second pass
  runs without experimental torsion preferences, so the s-cis-side diene class is sampled.
  Stereo-checked seed geometries are accepted, and isotope labels are refused. Dedup is by
  proper-rotation RMSD over graph automorphisms, followed by an energy window, a per-conformer
  mirror degeneracy g and the ensemble build.
- **Single-species stage runner** (`eta_rxncat.orchestrator`): `run_species` caches each stage
  in the v0.1.0 artifact store: conformer search, optimisation, frequency and incremental single
  points. It counts engine calls and records per-stage metrics. It pushes along an imaginary mode
  at most once, then re-dedups the pushed conformer against the kept set.
  `run_constrained_point` gives a cached constrained optimisation. `reaction_free_energy` gives
  ΔE, ΔH, ΔG(1 atm) and ΔG(1 M), and the JSON report writer is deterministic.
- **End-to-end fixtures** (`tests/e2e/`, `e2e` marker): Human Fixture 1 (n-butane anti/gauche),
  Human Fixture 2 (butadiene + ethylene → cyclohexene, with incremental ALPB toluene and PCM
  single points), TJ's Tier 1 (2,3-dimethoxybutadiene) and Tier 2 (cyclopentadiene + cyclopropene
  → endo P1a_n, with incremental ALPB dioxane). Each runs on the xtb (GFN2) and UMA recipes. TJ's
  ωB97M-V/def2-TZVPD//B3LYP/6-31G** reference values are under
  `tests/e2e/data/reference/tj-reference-b3lyp-20261123/`. The fixtures TJ promoted are in
  `tests/fixtures/v0.3.0/`.
- **v0.3.0 acceptance** (`docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`, verdict `pass`, run
  2026-11-23 at `0a48204`). It ran on an NVIDIA GeForce RTX 5060 Ti, with UMA `uma-s-1p2p1`
  (fairchem 2.26.0) on CUDA and xtb 6.8.0 on the CPU. The xtb recipe passed 6 tests and the UMA
  recipe 5, with 0 skipped. Every fixture passed on both recipes and matched its promoted
  fixture, and TJ confirmed the derived SMILES. The UMA results compared with TJ's ωB97M-V
  reference, with these gated deltas:
  - n-butane gauche–anti ΔG: +0.009 kcal/mol (bound 0.5).
  - Diels–Alder ΔG_r: +0.056 kcal/mol (bound 2.0).
  - Tier 2 ΔG_r(1 M): −32.01 kcal/mol, inside TJ's −42 to −20 window.
  - Tier 1: all three gates pass on both recipes (both conformer classes kept, s-trans below
    s-cis-side, planar point within 0.1°).
- **Records**: proposed ADR-0023 to ADR-0027 (awaiting approval), and the v0.3.0 starter
  discrepancy register `docs/prd/v0.3.0/DISCREPANCIES.md` (23 rows, all closed at release).

### Changed
- **geomeTRIC is no longer a core dependency** (TJ Q3 A). It moved to the `opt-geometric` extra
  (`geometric==1.1.1`) and the dev group. The base licence profile has no exemption now. The
  BSD 3-clause Non-AI exemption moved to the new `opt-geometric` profile, which CI also gates. It
  stays in `gpu`, `mlip-mace` and `mlip-uma`, because `gpu4pyscf-cuda12x` pulls geomeTRIC in.
- **Test markers**: `e2e` is registered and deselected by default.
- **README**: v0.3.0 features. The v0.3.0 acceptance claims are derived from the record, and
  tests enforce them. The Acknowledgements section links the original
  [`Eta_Scripts`](https://github.com/tjmustard/Eta_Scripts) code and the author's Oregon State
  University dissertation (2015), where that code is also published.

### Known issues
- **GFN2 is reported, not gated, and it overbinds.** Its deltas against TJ's ωB97M-V reference
  are Diels–Alder ΔG_r −19.75 kcal/mol and n-butane gauche–anti ΔG −0.03 kcal/mol. Its Tier 2
  ΔG_r(1 M) is −52.36 kcal/mol, outside TJ's window. TJ's rule (Q-E5 "C"): "if it turns out MACE,
  UMA, or OMol25 are needed then they should become standard". The default recipe stays GFN2
  until TJ decides.
- **Cached failures (R50).** A non-deterministic engine failure stays cached as a completed
  failure row until `invalidate`, and is not retried under the same key.
- **UMA cyclohexene boats at the dedup threshold.** On UMA, HF2 cyclohexene keeps a Cs boat and a
  twist-boat 0.126 Å apart (threshold 0.125 Å), 0.31 kcal/mol apart and about 4 kcal/mol above
  the half-chair (weight ≈ 1e-3).
- **The UMA `dropped` list is not bit-reproducible.** GPU noise in the G order can swap which
  reason a dropped conformer gets (`duplicate_after_push` or `mirror_partner`) between runs. The
  kept records and counts are unchanged, and the regression does not compare the `dropped` list.
- **Per-conformer accuracy.** The accuracy check compares per-conformer quantities. Our G is
  quasi-RRHO and the reference uses pure RRHO (≤ 0.01 kcal/mol on these Δ values). The ensemble
  ΔG_r differs by `dG_r_ensemble_minus_lowest`, which is reported.
- **ADR-0023 to ADR-0027 are PROPOSED.** ADR-0024's body still names `CoordSysDict`, which is not
  importable; mission R44 corrected this, and the code builds its own coordinate-system table.
- **Carried forward from 0.2.0, still true:**
  - `import mace` sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process. The fix is
    planned for when engines first share a process.
  - DFT Hessians use finite differences on the CPU, and the GPU analytic KS Hessian is used only
    for the supported classes.
  - `stability.py` pins private PySCF 2.15.1 / GPU4PySCF 1.9.2 internals.
  - fairchem engines run at `high-precision` only.
  - The GPU stability follow for fewer than three rotations is tested only with fakes.
  - The VRAM estimate does not cover GPU Hessians.
  - `PotentialResult` is frozen only shallowly (DV-23).

## [0.2.0] - 2026-11-23

### Added
- **`PotentialResult`** (`eta_rxncat.core.results`): a frozen core contract with energy (Eh),
  forces (Eh/Bohr), an optional Hessian (Eh/Bohr², `analytic` or `finite_difference`), the
  engine's identity (tag, version, content-pinned model), the device and its reason, the recovery
  steps taken and the wall time.
- **Engine interface** (`eta_rxncat.engines`): one abstract `Engine`, built from a stage with
  `from_stage`. Every result-changing option is keyed and filled into the resolved stage, so
  implicit and explicit defaults give the same cache key. Runtime arguments and the device are
  never keyed. Includes CODATA 2018 units, a finite-difference Hessian helper (step in Bohr,
  symmetrised, asymmetry recorded) and typed errors (`EngineInputError`,
  `EngineUnavailableError`, `ScfConvergenceError`, `EngineRuntimeError`). An engine that cannot
  represent a state's charge and spin refuses it and never computes something else.
- **Six engines**:
  - `rdkit_ff`: RDKit UFF and MMFF94, neutral singlets only.
  - `pyscf_gpu_cpu`: PySCF on the CPU and GPU4PySCF on CUDA from one resolved stage. It covers
    RKS/UKS/RHF/UHF, density fitting (keyed, on by default), the def2 ECP rule (`ecp="auto"`),
    ddCOSMO, C-PCM and IEF-PCM solvation (no ddCOSMO on GPU), an SCF escalation ladder and an
    internal stability analysis. On CUDA, a stage over the calibrated VRAM estimate or one that
    hits a listed out-of-memory error falls back to the CPU, with the reason recorded.
  - `xtb_subprocess`: GFN2-xTB 6.8.0 as a separate process with keyed ALPB solvation. The
    Hessian is a finite difference of xtb's gradients, because xtb's own `--hess` output is
    projected.
  - `mace`: MACE-MP-0 medium in float64, neutral singlets only, with the model file checked
    against its SHA-256 pin. `eta_rxncat` never imports `ase`.
  - `uma_direct` (`uma-s-1p2p1`) and `esen_omol25` (`esen-sm-conserving-all-omol`, TJ: "A - Ship
    it as a second model"): fairchem models on one clean-room bridge, with charge and spin passed
    through. Only the conserving OMol25 checkpoint is accepted.
- **Licence inventory** (`docs/licence-inventory.md`): external programs and weights used but
  never shipped, with licence, digest and decision. These are the xtb binary (LGPL-3.0 with
  bundled MKL/ifx, run as a subprocess; TJ F12 A), the MACE-MP-0 weights (MIT) and the UMA and
  OMol25 weights (FAIR Chemistry License v1, gated).
- **Engine test policy**: `xtb`, `mlip_mace`, `mlip_uma`, `slow` and `acceptance` markers (beside `gpu`), deselected by default, named
  acceptance environments, and `ETA_RXNCAT_ACCEPTANCE=1`, which turns every skip into a
  failure. Unit tests run offline.
- **v0.2.0 acceptance** (`docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`, run at `a879590`): passed on
  an NVIDIA GeForce RTX 5060 Ti (compute capability 12.0) with PyTorch 2.13.0+cu129 and
  GPU4PySCF 1.9.2. The smoke test matched GPU and CPU to |ΔE| 1.0e-12 Eh. All six engines ran
  their acceptance cases, with the expected refusals for states an engine cannot represent. GPU
  suite: 20 passed. Plain suite: 743 passed, with the one by-design skip.
- **Records**: proposed ADR-0016 to ADR-0022 (awaiting approval), the v0.2.0 starter discrepancy
  register `docs/prd/v0.2.0/DISCREPANCIES.md`, and the calibration and support evidence under
  `docs/prd/v0.2.0/`.

### Changed
- **GPU and MLIP stack**: PyTorch 2.13.0 from the CUDA 12.9 index (`cu129`, was `cu128`) and
  `fairchem-core>=2.22`, so UMA `uma-s-1p2p1` runs natively (TJ F1 A).
- **Licence gate**: `BSL-1.0` is on the allow-list (it is in torch 2.13.0's licence expression).
  A dist-info without `Name`, or two
  dist-infos for one name, now fails instead of being skipped or resolved first-wins.
- **README**: the version badge, the Features heading and the GPU claim are derived from
  `pyproject.toml` and the acceptance record, and tests enforce them. The Roadmap is split into
  Built and Planned.

### Known issues
- **Security: `import mace` disables safe `torch.load`.** The upstream `mace` package sets
  `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process, so any later `torch.load` in that
  process unpickles arbitrary objects. v0.2.0 is not exposed, because the `mlip-mace` and
  `mlip-uma` extras cannot share an environment. A fix is planned for when engines first share a
  process.
- **DFT Hessians.** On the CPU they are finite differences of analytic gradients. PySCF 2.15.1's
  analytic KS Hessian is wrong at the default grid, and CPU grid response is not implemented. On
  the GPU, GPU4PySCF's analytic KS Hessian is used only for the classes the committed support
  record covers (`docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`). UKS with IEF-PCM is about
  2e-4 Eh/Bohr² off and goes to finite differences.
- **SCF stability rule.** An instability counts only if λ_min < −1e-3 (keyed `stability_tol`),
  and a follow that lowers the energy by less than 1e-6 Eh (keyed `stability_noise_eh`) ends as
  stable. Shallower instabilities are no longer followed. The rule changed because threaded-CPU
  noise made PySCF's own −1e-5 verdict flaky.
- **fairchem precision.** `uma_direct` and `esen_omol25` run at `high-precision` only (keyed).
  A faster mode may be added later.
- **Private PySCF internals.** `engines/pyscf_gpu_cpu/stability.py` replays private PySCF
  2.15.1 and GPU4PySCF 1.9.2 code. A lock bump needs a re-pin, and a tripwire test fails until
  it is done.
- **From the acceptance record's `known_limits`:**
  - The GPU stability follow branch for fewer than three orbital rotations is tested only with
    fakes.
  - The VRAM estimate covers SCF and gradients only. A GPU Hessian over budget relies on the
    out-of-memory CPU fallback.
  - The plain suite in the GPU environment has one by-design skip
    (`tests/unit/cli/test_cli.py::test_console_script_smoke_skipped`).

## [0.1.0] - 2026-11-22

### Added
- **Scaffold and gates.** A `uv`-managed MIT package (`eta-rxncat`, src layout, committed
  `uv.lock`, Python 3.11–3.13) with strict `ruff`, `mypy` and `pytest` gates, CI, and the
  `v0.1.0` reference starter kept read-only under `docs/prd/v0.1.0/` with discrepancy registers.
- **Licence gates.** `tools/licence_gate.py` judges every package in a runtime environment from
  its exact licence metadata (SPDX expression, classifiers or licence field, no substring
  matching). There is one profile per install (`base`, `gpu`, `mlip-mace`, `mlip-uma`), each with
  version-pinned exemptions.
- **Core models and graph loader.** Strict Pydantic v2 contracts (`MolecularState`,
  `StageConfig`, `AtomMappingSpec`, `ThermoConfig`, `ReactionGraph` and the rest) and a YAML/JSON
  loader that rejects duplicate keys and reports every failure as one `GraphValidationError`.
- **Cache key and artifact store.** A canonical, versioned per-stage cache key and a WAL-mode
  SQLite artifact store whose completed artifacts are never silently overwritten
  (`ArtifactConflictError`; `invalidate` is the only way to replace one). Opening a store runs
  the version check, the WAL switch and schema creation within one `open_timeout_s` deadline
  (default 5 s). A file locked past it raises `StoreBusyError`, and an unknown schema version
  raises `StoreSchemaError` and leaves the file untouched.
- **Hardware probe and smoke.** `probe_hardware()` reports PyTorch/CUDA, the GPU, GPU4PySCF and a
  6.5 GiB VRAM budget, and flags broken installs. `run_smoke()` compares GPU4PySCF with PySCF, and
  a CUDA matmul with the CPU result, against numeric tolerances.
- **CLI.** `eta-rxncat validate <path>` and `eta-rxncat hardware-check [--smoke]`, with a fixed
  exit-code table and one-line errors.
- **Optional extras.** `gpu` (PyTorch from the CUDA 12.8 index, GPU4PySCF, CuPy), and
  `mlip-mace` and `mlip-uma`, which are mutually exclusive and declared as conflicting.
- **Copyleft boundary.** The core install and `src/eta_rxncat/` stay MIT/BSD or equivalent.
  Copyleft and off-list licences are allowed only as unmodified, downloaded, transitive
  dependencies of the optional engine extras (for example `ase` under `mlip-mace`), each pinned
  per profile. `tests/unit/test_package.py` fails if the package imports `ase` or any
  copyleft-exempted module, or depends on one directly.
- **GPU acceptance.** The smoke test passed on an NVIDIA GeForce RTX 5060 Ti (compute
  capability 12.0, PyTorch 2.8.0+cu128, GPU4PySCF 1.9.2) at commit `ff3991e`. The GPU SCF
  energy was −74.96302313846023 Eh against −74.96302313846122 Eh on the CPU (|ΔE| 9.95e-13 Eh,
  tolerance 1e-6), with the molecular orbitals on the device. The record is
  `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`.
- **README GPU claim tied to the record.** `tests/unit/test_identity.py` reads
  `docs/prd/v<version>/GPU_SMOKE_RESULT.json`. The README may say "GPU acceptance passed" only
  when the record's smoke status is `pass`, and then it must link the record and name its GPU.
- **README, CHANGELOG and media.** A README with logo, banner and badges. The media are a
  size-named WebP set under `media/` (`icon-<N>.webp`, `banner-<W>x<H>.webp`), and each document
  embeds the next size up from its displayed width. `tests/unit/test_media.py` checks the names
  against the pixel sizes and the embeds.
- **Author guard.** `tests/unit/test_identity.py` requires the author form
  "Thomas J. L. Mustard Ph.D." in `README.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml` and
  the project section of `AGENTS.md`, including forms split across line breaks.
- **Records.** Proposed ADR-0011 to ADR-0015 under `lore/ADRs/`, awaiting approval (licence-gate exceptions, exact SPDX
  evaluation, the copyleft rule and the store-open order), and the plan discrepancy registers
  `docs/prd/PLAN_DISCREPANCIES.md` and `docs/prd/v0.1.0/DISCREPANCIES.md`.

### Changed
- Author name standardised to Thomas J. L. Mustard Ph.D.
