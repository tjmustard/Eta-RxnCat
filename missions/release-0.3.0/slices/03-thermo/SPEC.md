---
id: OPR.0.3.0.3
slice: 03-thermo
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Create eta_rxncat.thermo: CODATA 2018 constants, Eckart-projected normal modes, rotational symmetry number from geometry and capped graph automorphisms, Grimme quasi-RRHO at 1 M, log-sum-exp Boltzmann with degeneracies, and the ground-state check, all proved by tier-D tests."
depends_on: [OPR.0.3.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_thermo
parent: null
hacf_touches: ["src/eta_rxncat/thermo/**", "tests/unit/thermo/**", docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/thermo]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Thermochemistry package (constants, normal modes, symmetry number, quasi-RRHO, Boltzmann)

## Intent

Create `eta_rxncat.thermo` (new ledger node `eta_rxncat_thermo`): CODATA 2018 constants, Eckart-
projected normal modes from any Cartesian Hessian, the rotational symmetry number from geometry and
graph automorphisms, Grimme quasi-RRHO thermochemistry at the 1 M standard state, log-sum-exp
Boltzmann averaging with degeneracies, and the ground-state check — all proved by tier-D tests.

Context the builder needs:
- **Node not yet in the graph.** Create it: `python3 .agents/scripts/hyper_ledger.py ensure-node
  --id eta_rxncat_thermo --dimension Module --depends-on eta_rxncat_core --files
  'src/eta_rxncat/thermo/**,tests/unit/thermo/**' --associated-file src/eta_rxncat/thermo/__init__.py
  --description-file <file>`.
- Thermo is derived, never stored: the runner stores the Hessian; `ThermoResult` is recomputed from
  it (no store row).
- `engines.units` holds only `BOHR_ANGSTROM`, `HARTREE_EV`, `HARTREE_KCAL_MOL` and conversions; it
  must **not** be edited (engines node untouched, R1). Thermo gets its own constants module.
- `ThermoConfig` (core): `temperature_k` 298.15, `pressure_atm` 1.0, `standard_state_mol_l` 1.0,
  `qrrho_cutoff_cm1` 100, `qrrho_alpha` 4, `qrrho_rotor_moment_kg_m2` 1e-44. `ThermoAnalysisOptions`
  (core, slice 02): imag_tol 20 cm⁻¹, sym_tol 0.05 Å, linear_tol 1e-3 Å, max_automorphisms 100000.
- Masses: RDKit `Chem.GetPeriodicTable().GetMostCommonIsotopeMass(symbol)` (RDKit 2026.09.2: H
  1.007825032, C 12.0, Pd 105.903486). H9: > 0 for all Z 1–118 (red team verified). Record
  `masses_source = f"rdkit {rdkit.__version__} most-common-isotope"`. No fallback table.
- RDKit's `GetSubstructMatches` truncates at 1000 matches by default (measured on
  hexamethylethane): always pass `maxMatches` explicitly.

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

**Score: 9/10.** Every formula is written below; the residual is numerical edge behaviour that the
tier-D tests pin down.

## Mini-requirements

1. `thermo/constants.py` (CODATA 2018 exact/recommended): `H_PLANCK = 6.62607015e-34` J·s,
   `K_BOLTZMANN = 1.380649e-23` J/K, `C_LIGHT = 299792458.0` m/s, `N_AVOGADRO = 6.02214076e23`,
   `E_CHARGE = 1.602176634e-19` C, `AMU_KG = 1.66053906660e-27`, `HARTREE_J = 4.3597447222071e-18`,
   `BOHR_M = 0.529177210903e-10`, `CAL_J = 4.184`, `ATM_PA = 101325.0`, `R_GAS = N_AVOGADRO *
   K_BOLTZMANN`. Derived conversions for cm⁻¹ from Eh/(Bohr²·amu).
2. `thermo/modes.py` `normal_modes(symbols, coords_angstrom, hessian_hartree_per_bohr2, *,
   analysis) -> NormalModes(frequencies_cm1, modes_cartesian, is_linear, n_atoms)`: copy the Hessian
   into a fresh float64 array (never mutate the input), symmetrise, mass-weight; build translation
   and rotation vectors about the COM, orthonormalise by SVD (rank 3 for N = 1, 5 if linear, else
   6); diagonalise the projected Hessian in the orthogonal complement so exactly 0 / 3N−5 / 3N−6
   eigenvalues result; ν̃ = sign(λ)·√|λ| converted to cm⁻¹; ascending. Linearity: N = 2, or every
   atom within `linear_tol_angstrom` of the line through the COM along the principal axis with the
   smallest moment. |ν̃| < 1e-3 cm⁻¹ → `ThermoInputError`.
3. `thermo/symmetry.py` `rotational_symmetry_number(state, smiles, *, analysis) -> int`: RDKit mol
   from `smiles` with `Chem.AddHs`, atom order equal to the state's (caller's contract; check the
   element sequence matches, else `ThermoInputError`); automorphisms
   `mol.GetSubstructMatches(mol, uniquify=False, useChirality=False, maxMatches=max_automorphisms+1)`;
   count == cap+1 → `ThermoInputError("automorphism cap reached …")`; σ = number of automorphisms
   whose proper-rotation Kabsch RMSD (det = +1, never a reflection) between the state and its
   permuted self is ≤ `sym_tol_angstrom`. Linear: σ = 2 if centrosymmetric (every atom has a
   same-element partner at −r within sym_tol about the COM), else 1. Shared helpers (Kabsch with
   det = +1, permuted RMSD, automorphism list) live in `thermo/_geometry.py` for conformers to reuse.
4. `thermo/rrho.py` `thermochemistry(state, hessian_hartree_per_bohr2, electronic_energy_hartree, *,
   smiles, energy_source, config=ThermoConfig(), analysis=ThermoAnalysisOptions()) -> ThermoResult`,
   per mole then converted to Eh (÷ HARTREE_J·N_AVOGADRO) and Eh/K:
   - Translation: S = R[ln((2πmk_BT/h²)^{3/2}·k_BT/p°) + 5/2], p° = pressure_atm·ATM_PA; E = 3/2 RT.
   - Rotation: nonlinear S = R[ln(√π/σ·(8π²k_BT/h²)^{3/2}·√(I_A I_B I_C)) + 3/2], E = 3/2 RT;
     linear S = R[ln(8π²I k_BT/(σh²)) + 1], E = RT; atom S = E = 0.
   - Vibration (real modes, soft modes at |ν̃|): ZPE = Σ ½hcν̃·N_A; E_vib (thermal excess, **excluding
     ZPE**) = Σ R·θ/(e^{θ/T}−1), θ = hcν̃/k_B; S_RRHO = R[x/(eˣ−1) − ln(1−e^{−x})], x = θ/T; free
     rotor S_r = R[½ + ln((8π³μ′k_BT/h²)^{1/2})], μ = h/(8π²cν̃), μ′ = μB_av/(μ+B_av), B_av =
     `qrrho_rotor_moment_kg_m2`; Grimme w = 1/(1+(ω₀/ν̃)^α); S_vib = Σ[w·S_RRHO + (1−w)·S_r];
     enthalpy undamped.
   - Electronic: S = R ln(multiplicity).
   - H = E + ZPE + E_trans + E_rot + E_vib + RT; correction to standard state ΔG° = RT
     ln(c°·k_BT/p°), c° = standard_state_mol_l·1000·N_AVOGADRO molecules/m³; G = H − T·S_total + ΔG°.
   - Imaginary modes (< −imag_tol) are excluded from ZPE/E_vib/S and listed; the result is still
     returned (the caller decides via `check_ground_state`).
5. `thermo/boltzmann.py` `boltzmann(gibbs_hartree, degeneracies, temperature_k) ->
   (weights, g_ens_hartree)`: log-sum-exp; weights ∝ gᵢ exp(−Gᵢ/RT); G_ens = −RT ln Σ gᵢ
   exp(−Gᵢ/RT). Empty input or length mismatch → `ThermoInputError`.
6. `thermo/errors.py`: `ThermoError` → `ThermoInputError`, `NotAMinimumError(imaginary_cm1)`.
   `check_ground_state(result)` raises `NotAMinimumError` iff `imaginary_frequencies_cm1` is non-empty.
7. `thermo/__init__.py` exports the above; imports numpy and RDKit lazily or at module level only in
   `thermo` (never in core).

## 3. Implementation Plan (Task List)

- [ ] Task 1: create the ledger node.
- [ ] Task 2: `constants.py` + derivation test vs `engines.units`.
- [ ] Task 3: `_geometry.py`, `modes.py` + tests.
- [ ] Task 4: `symmetry.py` + tests (idealized geometries built in the test from known parameters).
- [ ] Task 5: `rrho.py`, `boltzmann.py`, `errors.py` + tests; H9 full loop Z 1–118.
- [ ] Task 6: `hypergraph_updater.py --from-diff Start..HEAD`; required checks; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** edit `engines/units.py` or any engine file; **DO NOT** duplicate a constant that
  `engines.units` defines without the derivation test.
- **DO NOT** drop "the six eigenvalues nearest zero"; **DO NOT** silently drop small modes.
- **DO NOT** call `GetSubstructMatches` without `maxMatches`; **DO NOT** use a reflection in any
  Kabsch fit.
- **DO NOT** default a mass, σ or multiplicity; **DO NOT** mutate a `PotentialResult` or input array.

## Proof contract

- [ ] Constants: `HARTREE_J*N_AVOGADRO/(1000*CAL_J)` equals `engines.units.HARTREE_KCAL_MOL` and
  `BOHR_M*1e10` equals `BOHR_ANGSTROM`, each within 1e-12 relative.
- [ ] Modes: a diatomic with spring k gives one mode equal to √(k/μ) converted, 1e-6 relative; a
  linear triatomic 3N−5; a random rigid rotation of a nonlinear toy Hessian changes no frequency by
  > 1e-6 cm⁻¹; CO₂ with O bent 1e-4 Å is linear; N = 1 → 0 modes; input array unchanged after the call;
  a `PotentialResult`'s Hessian unchanged after `normal_modes` (DV-23).
- [ ] σ: H₂O 2, NH₃ 3, CH₄ 12, ethylene 4, benzene 12, CO₂ 2, HCN 1, n-butane anti 2, gauche 2;
  water with one H moved 0.2 Å → 1; hexamethylethane `CC(C)(C)C(C)(C)C` → `ThermoInputError`
  (cap); a 1001+-match molecule with `max_automorphisms` raised counts beyond 1000.
- [ ] RRHO tier D at 298.15 K: standard-state term = RT ln(24.4654) = 1.8943 kcal/mol ± 1e-4;
  Grimme w = 0.5 at ν̃ = ω₀; linear E_trans + E_rot = 5/2 RT; S_elec = R ln 2 for a doublet; each
  term equals its closed form (rel 1e-9); total H equals an independent sum written in the test
  (abs 1e-12 Eh); entropy components sum to the total.
- [ ] Boltzmann: G equal, g = (1, 2) → (1/3, 2/3) within 1e-15; G_ens hand-checked; ΔG = 1000
  kcal/mol → finite weights (no overflow); `check_ground_state` raises on one imaginary mode.
- [ ] Masses exist for Z 1–118 (loop test).
- [ ] `uv run pytest tests/unit/thermo` exit 0; required checks exit 0; node `eta_rxncat_thermo`
  in `hyper_ledger.py validate` output.

## Source material

- Mission §5 "Algorithms", R1, R8, R9, R15; Grimme, *Chem. Eur. J.* 2012, 18, 9955; DV-01…DV-09.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.2 (core contracts)
