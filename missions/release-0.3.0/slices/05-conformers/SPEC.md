---
id: OPR.0.3.0.5
slice: 05-conformers
mission: release-0.3.0
status: done
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Create eta_rxncat.conformers: two-pass ETKDGv3 (second pass without experimental torsion preferences, F21), stereo-checked seeds, proper-rotation dedup over automorphisms, energy window, per-conformer mirror degeneracy and ensemble build, re-proving s-cis-side sampling and survival by an independent route."
depends_on: [OPR.0.3.0.3, OPR.0.3.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_conformers
parent: null
hacf_touches: ["src/eta_rxncat/conformers/**", "tests/unit/conformers/**", tests/unit/test_package.py, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/conformers]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Conformer generation (two-pass ETKDGv3, stereo-checked seeds, dedup, window, mirror degeneracy)

## Intent

Create `eta_rxncat.conformers` (new ledger node `eta_rxncat_conformers`): a two-pass ETKDGv3 pool
from a SMILES with explicit charge and multiplicity, stereo-checked seed geometries, proper-rotation
dedup over graph automorphisms, an energy window, degeneracy from each conformer's own chirality,
and ensemble assembly — and re-prove, by an independent route, that the s-cis-side diene class is
sampled and survives optimization (F21).

Context the builder needs:
- **F21 (blocker, resolved R21):** ETKDGv3 with experimental torsion preferences never samples the
  s-cis-side class of a conjugated diene. Resolve measured (RDKit 2026.09.2, seed 42,
  `numThreads=1`, `pruneRmsThresh=-1`): pass 1 s-cis-side (|φ(0-1-2-3)| ≤ 90°) 0/40 for T1
  `C=C(/C=C/OC)OC` and 0/50 for butadiene `C=CC=C`; a second pass with
  `useExpTorsionAnglePrefs=False` gives 24/40 and 26/50, bit-reproducible. On xtb 6.8.0 (`xtb
  <file> --gfn 2 --opt tight`, run directly): a T1 s-cis-side embedding at 48.7° relaxed to 2.1°,
  butadiene −65.6° → −18.3° (class survives); s-trans lies lower by 1.69 (T1) and 2.13 (butadiene)
  kcal/mol ΔE. So the "both classes present" and "s-trans below s-cis-side" gates hold on GFN2.
- **F3 (resolved R3):** a found-pair mirror rule loses g = 2 when pre-dedup or optimization removes
  one enantiomeric conformer. Degeneracy is decided per conformer.
- **F24 (R24):** `GetSubstructMatch` without `useChirality` accepts a Z seed for an E SMILES and an
  exo seed for endo P1a_n (measured).
- H3: RDKit `pruneRmsThresh=0.5` keeps 2 butane conformers of 100 (merges g⁺/g⁻ by threshold);
  never use it.
- Butane on UFF after optimization: heavy-atom RMSD g⁺ vs g⁻ 0.513 Å, anti vs gauche 0.644 Å; with
  H 1.254 and 1.184 Å (red team).
- Reuse `thermo/_geometry.py` (Kabsch det = +1, permuted RMSD, automorphisms with explicit
  `maxMatches`).
- New node: `ensure-node --id eta_rxncat_conformers --dimension Module --depends-on
  eta_rxncat_core,eta_rxncat_thermo --files 'src/eta_rxncat/conformers/**,tests/unit/conformers/**'
  --associated-file src/eta_rxncat/conformers/generate.py --description-file <file>`; scaffold loses
  `src/eta_rxncat/conformers/**` (full `--files` list).
- geomeTRIC is in `.venv` via the dev group (slice 04), so UFF-optimizer tests run in the default
  suite.

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

**Score: 9/10.** Algorithms and tests are fixed; H14 (UMA survival) is the one measured unknown, with
a defined stop.

## Mini-requirements

1. `conformers/options.py` `ConformerOptions` (frozen pydantic, not core): `n_embed` 50, `seed` 42,
   `torsion_free_pass` True, `pre_dedup_rmsd_angstrom` 0.125, `rmsd_dedup_angstrom` 0.125,
   `energy_window_kcal_mol` 6.0, `include_h_in_rmsd` True, `max_automorphisms` 100000;
   `as_stage_options() -> dict[str, ScalarValue]` (sorted, keyed by the runner).
2. `conformers/errors.py`: `ConformerError` → `ConformerInputError`, `EmbeddingFailedError(counts)`,
   `EnsembleEmptyError(reasons)`.
3. `conformers/generate.py` `generate(smiles, *, charge, spin_multiplicity, options,
   seed_geometries=()) -> ConformerPool` where `ConformerPool` holds members `(source_id, origin ∈
   {"etkdg", "etkdg_free", "seed"}, state: MolecularState)`, per-pass RDKit failure counts and the
   pre-dedup survivor ids.
   - Input checks → `ConformerInputError`: unparsable SMILES; any isotope label; total formal
     charge ≠ `charge`; impossible electron parity (via `MolecularState`).
   - Pass 1: `ETKDGv3()` with `randomSeed=seed`, `pruneRmsThresh=-1`, `numThreads=1`,
     `enforceChirality=True`, `n_embed` conformers, ids 0…n_embed−1. Pass 2 (if `torsion_free_pass`):
     identical except `useExpTorsionAnglePrefs=False`, ids n_embed…2·n_embed−1. Zero embeddings in
     both → `EmbeddingFailedError`.
   - Seeds (`MolecularState`, same charge/multiplicity else `ConformerInputError`): RDKit mol from
     the XYZ, `rdDetermineBonds.DetermineBonds(mol, charge=charge)`, `AssignStereochemistryFrom3D`;
     its canonical isomeric SMILES must equal the input's and `smiles_mol.GetSubstructMatch(seed_mol,
     useChirality=True)` over all atoms incl. H must succeed; else `ConformerInputError` naming the
     seed. Reorder the seed's atoms into SMILES order. Ids 2·n_embed….
   - Seed hash text (R28): `f"{n}\n\n"` + per atom `f"{symbol} {x:.6f} {y:.6f} {z:.6f}\n"` after
     reordering; `seed_geometries_sha256(seeds)` = sorted hex sha256 joined by `,` or `""`.
   - Pre-dedup with H at `pre_dedup_rmsd_angstrom`: visit seeds first, then embeddings by id; keep a
     member unless it is within the threshold (min over automorphisms, proper rotation) of a kept
     one. A seed is never removed.
4. `conformers/dedup.py`: `dedup(states, energies, options) -> list[Kept(index, source_ids)]`
   ordered by energy (ties → lower index), merging members within `rmsd_dedup_angstrom` (with H,
   automorphisms, proper rotation) into the lower-energy one; `energy_window(kept, energies, options)`
   keeps E − E_min ≤ window (kcal/mol via `engines.units`).
5. `conformers/degeneracy.py`: `graph_achiral(smiles) -> bool` (canonical isomeric SMILES equals
   that of the copy with every tetrahedral tag inverted; double-bond stereo unchanged — limit R37);
   `conformer_chiral(state, smiles, options) -> bool` (its x-inverted geometry is >
   `rmsd_dedup_angstrom` from itself under every automorphism with a proper rotation);
   `assign_degeneracy(...) -> 2 if graph_achiral and conformer_chiral else 1`;
   `drop_mirror_partners(records)` removes a record whose inversion matches a kept lower-G record
   (ties → lower index), returning `(kept, dropped=[(id, "mirror_partner")])`.
6. `conformers/ensemble.py` `build_ensemble(species_id, smiles, records, temperature_k) ->
   ConformerEnsemble` using `thermo.boltzmann` on G and degeneracies.
7. `conformers/geometry.py` `dihedral_deg(state, i, j, k, l)` (for class labels by callers).
8. σ on optimizer-converged geometries (R9): UFF-optimize water, ethylene, benzene with
   `GeometricOptimizer` and check `rotational_symmetry_number` = 2, 4, 12.

## 3. Implementation Plan (Task List)

- [x] Task 1: H4 — two `generate` calls (butane, T1, butadiene) give bit-identical coordinates for
  both passes; record. H3 note in the proof.
- [x] Task 2: H12 (independent of this slice's code): in a scratch dir, with RDKit and the xtb CLI
  only, optimize TJ's T1 XYZ (s-trans seed; from the `XYZ_FILES` literal of
  `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py`
  via `ast.literal_eval`, never executing it) and every pass-2 s-cis-side embedding (seed 42, n 40)
  with `--gfn 2 --opt tight`; lowest s-cis-side E − s-trans E must be > 0 and every optimized
  s-cis-side geometry must keep |φ| ≤ 90° for at least one member. Record numbers. A contradiction
  is stop-and-report (the gate is not re-decided).
- [x] Task 3: options, errors, generate (+ seeds) + tests.
- [x] Task 4: dedup, window, degeneracy, ensemble + tests.
- [x] Task 5: H14 in `.venv-accept-uma` (create/sync it per AGENTS.md as `--extra gpu --extra
  mlip-uma --extra opt-geometric`): optimize one pass-2 s-cis-side embedding of butadiene and of T1
  with `GeometricOptimizer` on `uma_direct`/`uma-s-1p2p1`; record final φ. |φ| > 90° for either →
  stop and report to the lead with the dihedrals.
- [x] Task 6: ledger; required checks; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** use `pruneRmsThresh` for dedup, or a reflection in any RMSD.
- **DO NOT** accept a seed whose perceived stereo or connectivity differs; **DO NOT** drop a seed
  silently or modify the caller's state.
- **DO NOT** assign degeneracy from finding a partner.
- **DO NOT** decide the H12/H14 verdict from this slice's own pipeline output.
- **DO NOT** return the input or a partial pool in place of a typed error.

## Proof contract

- [ ] `generate("CC", charge=1, …)` → `ConformerInputError`; `[2H]C` → `ConformerInputError`;
  `generate` with a Z-diene seed for `C=C(/C=C/OC)OC` and with an exo seed for the endo P1a_n SMILES
  `C1=C[C@H]2C[C@@H]1[C@H]1C[C@H]12` → `ConformerInputError` (seeds built in the test by RDKit).
- [ ] Butadiene and T1 pools at defaults contain ≥ 1 pass-2 member with |φ(0-1-2-3)| ≤ 90°; with
  `torsion_free_pass=False` they contain 0 (documents F21).
- [ ] A seed is always among the pre-dedup survivors.
- [ ] Butane, seed 42, every pool member UFF-optimized, dedup → exactly 1 anti record (|φ| > 120°,
  g = 1) and exactly 1 gauche record (g = 2); repeated with the g⁺ members removed before dedup →
  still exactly 1 gauche record with g = 2.
- [ ] `graph_achiral("CCCC")` True; `graph_achiral` of a chiral SMILES (`C[C@H](O)CC`) False; for P1a_n
  True with its Cs geometry `conformer_chiral` False (g = 1).
- [ ] σ on UFF-optimized water 2, ethylene 4, benzene 12.
- [ ] `build_ensemble` weights sum to 1 within 1e-12; G_ens ≤ G_min − RT ln g_lowest.
- [ ] H4, H12 and H14 results quoted in the proof with commands and numbers.
- [ ] Required checks exit 0; `tests/unit/conformers` runs in the default suite.

## Source material

- Mission §5 R3, R9, R16, R21, R24, R25, R28, R37, "Algorithms"; DV-10, DV-11, DV-21, DV-22.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.3 (thermo helpers, σ), OPR.0.3.0.4 (optimizer for UFF tests)
