---
id: OPR.0.3.0.8
slice: 08-e2e5-tiers
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Land TJ's four XYZ verbatim with provenance, re-derive the T1/T2 SMILES for TJ's confirmation, and run Tier 1 (dimethoxybutadiene) and Tier 2 (Cp + cyclopropene to endo P1a_n, with incremental ALPB dioxane) on both recipes into committed candidates."
depends_on: [OPR.0.3.0.11]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", tests/unit/conformers/test_e2e5_smiles_derivation.py, "tests/candidate_outputs/v0.3.0/**", docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/conformers/test_e2e5_smiles_derivation.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: TJ's 5-tier suite Tiers 1 and 2 end to end on both recipes, with SMILES re-derivation

## Intent

Land TJ's four XYZ files verbatim with provenance, draft the T1 (1,3-dimethoxybutadiene) and T2
(cyclopentadiene + cyclopropene → endo P1a_n) inputs, re-derive and report the SMILES for TJ's
confirmation, and run both tiers on both recipes through the species runner — T2 with an incremental
ALPB(dioxane) stage — into committed candidates.

Context the builder needs:
- TJ Q-E2 "A": T1/T2 join v0.3.0. Q-E3 "B": inputs are provisional. Q-E4 "A": TJ's XYZ as given;
  SIs are references. Q-E5 "C": numeric windows gate UMA only; GFN2 values are reported. TJ's T2
  window: −42 < ΔG_rxn(1 M) < −20 kcal/mol (on `standard_state_mol_l: 1.0`).
- TJ's XYZ come from the `XYZ_FILES` literal in
  `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py`.
  Extract it with `ast.parse` + `ast.literal_eval` — **never execute the builder** — write UTF-8,
  and check each full sha256 starts with: `2_dimethoxybutadiene` 12afa0690b7b3eac,
  `1_cyclopentadiene` db8390fcc9fc9212, `5_cyclopropene` e61f12a6a2a1ea3f, `P1a_n` c7b9792c062bdff4.
  Check the builder's own sha256 against `MANIFEST.sha256` in that directory.
- Derived SMILES (H10, RDKit 2026.09.2 `DetermineBonds(charge=0)` + `AssignStereochemistryFrom3D`):
  T1 `C=C(/C=C/OC)OC`; Cp `C1=CCC=C1`; cyclopropene `C1=CC1`; P1a_n
  `C1=C[C@H]2C[C@@H]1[C@H]1C[C@H]12` (meso, endo; σ 1; g 1).
- References (TJ's headers; Liu, Paton, Kim, Liang, Houk, *J. Am. Chem. Soc.* 2013, 135, 15642, DOI
  10.1021/ja408437u; M06-2X/6-31G(d), 1 atm): T2 ΔE −51.42, ΔG −32.28 kcal/mol (−34.17 at 1 M); T1
  s-trans/s-cis ΔE 2.2 kcal/mol (SI p. S6). GFN2 overbinds T2 (ΔE −69.19 measured; ΔG ≈ −52 at 1 M):
  reported, not gated, on xtb.
- F32 answered (R42): TJ, verbatim, "A the planar geometry" (row
  `qitem-20261123032327-833f8c98768fa58f`). The 2.2 kcal/mol is s-trans → **planar** s-cis. The
  literature comparison is `dE_planar_scis_strans` = E(planar s-cis point) − E(lowest s-trans kept
  record), electronic energies on the recipe engine, kcal/mol, **reported only on both recipes**.
  The planar point comes from `run_constrained_point` (slice 06) started at the lowest-G kept
  s-cis-side record with `DihedralConstraint((0, 1, 2, 3), 0.0)` (SMILES atoms 0-1-2-3 of
  `C=C(/C=C/OC)OC`); it has no Hessian, frequencies, thermo or G and is not an ensemble record.
  The label stays a data field, `literature.label: "planar s-cis (diene dihedral constrained to
  0°)"` in `t1_dimethoxybutadiene.yaml`, read by the test (never a code constant).
- H12 was settled before this slice (resolve's xtb CLI measurement, re-measured in slice 05): the T1
  ordering check is **gated on both recipes**. It is not re-decided here.
- The commit order and pathspec rule of slice 07 (R23) apply unchanged.

- **Reader rule (mission R50, binding):** drop-path failures are cached as COMPLETED rows with
  payload `{failed_reason, message}`. Any code here that reads a stage payload from the store or a
  runner result checks `failed_reason` first; such a payload is a failure — count and report it
  (species, stage, reason), never use it as a result.
- **Standard state (mission R51):** every T2 ΔG_rxn (gas and the ALPB(dioxane) solvated value)
  goes through slice 07's `tests/e2e/derived.py: checked_reaction_free_energy`; never call
  `reaction_free_energy` directly.

- **No duplicate records (mission R53):** the runner re-dedups pushed conformers (slice 11). Call
  `tests/e2e/derived.py: assert_no_duplicate_records` for every T1/T2 species (the diene, Cp,
  cyclopropene, P1a_n) and report per species n_kept and the count of `duplicate_after_push`.
- **Derived regression (mission R54):** slice 11's `regression.compare` walks the whole `derived`
  block and fails on a numeric float with no unit on its path. Every numeric T1/T2 derived value
  needs a unit-suffixed key or parent: `_kcal_mol`, `_hartree` (e.g. the planar point's E, Q5 1e-5
  Eh) or `_percent`. Counts are ints, labels strings (both exact).

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

**Score: 9/10.** The UMA T2 window is unmeasured; a miss is a stop-and-report, not a spec gap.

## Mini-requirements

1. `tests/e2e/data/e2e5/xyz/{2_dimethoxybutadiene,1_cyclopentadiene,5_cyclopropene,P1a_n}.xyz`
   byte-identical to the extracted bytes; `tests/e2e/data/e2e5/SOURCES.md` per file: citation, SI
   page from the header, level of theory, transcriber "TJ", full sha256; the builder's sha256 and its
   MANIFEST match. The SI PDFs and the builder are not committed.
2. `tests/e2e/data/e2e5/t1_dimethoxybutadiene.yaml` (SMILES, 0, 1, `n_embed` 40, seed 42, XYZ seed,
   `literature: {quantity: dE_planar_scis_strans, value_kcal_mol: 2.2, source, label: "planar
   s-cis (diene dihedral constrained to 0°)"}`, and `planar_point: {dihedral_atoms: [0, 1, 2, 3],
   value_deg: 0.0}`) and `t2_cp_cyclopropene.yaml` (three
   species, `n_embed` 10 each, each XYZ as a seed, reaction Cp + cyclopropene → P1a_n, window
   `[-42, -20]`, literature ΔE/ΔG). DV-19 already records the departure from TJ's YAML.
3. `tests/unit/conformers/test_e2e5_smiles_derivation.py` (tier D, default suite): for each XYZ,
   re-derive the SMILES and assert **molecule equality** with the input SMILES (both through
   `Chem.MolToSmiles(Chem.MolFromSmiles(s))` with the running RDKit). Writes nothing.
4. `tests/e2e/test_e2e5_smiles_candidate.py` (`e2e`): writes `e2e5_smiles.json` = per species {xyz
   file, xyz sha256, derived SMILES, RDKit version}; if `tests/fixtures/v0.3.0/e2e5_smiles.json`
   exists, the inputs must equal it as molecules (else `fail`), else `pending_confirmation` (fails
   under acceptance).
5. `tests/e2e/test_e2e5_tier1_dimethoxybutadiene.py` (per recipe): diene class per record from atoms
   0-1-2-3 (`s-trans` |φ| > 90°, else `s-cis-side`). Gated: ≥ 2 kept; lowest record 0 imaginary;
   weights sum to 1 within 1e-12; G_BA ≤ G_lowest; ≥ 1 kept s-trans and ≥ 1 kept s-cis-side;
   lowest s-trans G < lowest s-cis-side G. Planar point (R42): read `planar_point` from the YAML,
   run `run_constrained_point` from the lowest-G kept s-cis-side record; gated only that it
   converged with |φ(0-1-2-3)| ≤ 0.1° (a mechanism check, both recipes); reported
   `dE_planar_scis_strans` beside the literature value and `label`, plus the planar point's E and
   xyz. Also reported: ΔE and ΔG(s-cis-side − s-trans) per conformer, class populations,
   `reperceived_smiles` per record. Writes `e2e5_t1.<recipe>.json`; regression vs promoted as slice
   07 (class = diene class) plus the planar point's E within 1e-5 Eh.
6. `tests/e2e/test_e2e5_tier2_cp_cyclopropene.py` (per recipe): gated on both — atoms and charge
   conserved; ΔG_rxn(1 M) < 0; every species' lowest record 0 imaginary; P1a_n σ = 1, g = 1; UMA only
   −42 < ΔG_rxn(1 M) < −20 (xtb: value and deviation reported). xtb incremental rerun into the same
   store adding ALPB(dioxane, `alpb_state: gsolv`) per kept record: 0 upstream engine calls;
   `species_stage_cache` geometry_opt/frequency hits 3 misses 0, single_point misses 3 (a species is a
   hit only if every kept conformer's row was served); exactly Σ n_kept ALPB calls; every species has
   a finite ΔG_solv (R27: per-conformer G_solv = G_gas + E_ALPB − E_gas, re-Boltzmann); solvated
   ΔG_rxn(1 M) = gas ΔG_rxn(1 M) + Σν ΔG_solv and differs from the gas value by > 1e-6 kcal/mol;
   signs reported. UMA: plain rerun → 0 engine calls. Writes `e2e5_t2.<recipe>.json`.

## 3. Implementation Plan (Task List)

- [x] Task 1: extract the XYZ (no execution), verify sha256s and the MANIFEST; H10 re-run.
- [x] Task 2: inputs, `SOURCES.md`, SMILES derivation test.
- [ ] Task 3: T1, T2, SMILES-candidate E2E tests; run on both recipes. A UMA T2 window miss, a
  missing class, or a failed ordering gate → stop and report to the lead with the numbers (no edit
  to the gate or window).
- [ ] Task 4: commits per R23 (C1 code, C2 candidates only); ledger updater; required checks.

## 4. The Negative Space (Constraints)

- **DO NOT** execute TJ's builder, edit his XYZ bytes/comments/atom order, or commit SI PDFs.
- **DO NOT** confirm or correct a SMILES; a SMILES that does not re-derive is stop-and-report.
- **DO NOT** widen the T2 window, gate GFN2 on it, or re-decide the ordering gate.
- **DO NOT** read candidates back; **DO NOT** write `tests/fixtures/`.

## Proof contract

- [ ] Four XYZ sha256s (full) and the builder/MANIFEST match quoted.
- [ ] `uv run pytest tests/unit/conformers/test_e2e5_smiles_derivation.py` exit 0 (default suite).
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and not mlip_uma"
  tests/e2e -k e2e5` exit 0 at C1, 0 skips.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-uma uv run --no-sync pytest -m "e2e and mlip_uma"
  tests/e2e -k e2e5` exit 0 at C1, 0 skips (includes the UMA T2 window).
- [ ] `git show --name-only --format=%s <C2>` lists exactly `e2e5_t1.{xtb,uma}.json`,
  `e2e5_t2.{xtb,uma}.json`, `e2e5_smiles.json` and names C1.
- [ ] `git ls-files | grep -Ei 'SI\.pdf|Zip_Builder'` is empty.
- [ ] Required checks exit 0 at C1.

## Source material

- Mission §5 R53, R54 (replan 4); R50–R52 (replan 3); R21, R23–R32, R42, "Human fixture inputs", "Test tiers and tolerances" (tier table); TJ
  Q-E2…Q-E5, R1.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.11 (pushed-duplicate re-dedup and regenerated HF candidates; mission R53)
- OPR.0.3.0.7 (e2e conftest, helpers, candidate writer use)
