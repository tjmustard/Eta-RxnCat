---
id: OPR.0.6.0.5
slice: 05-ts-sampler
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Add a deterministic core-frozen TS conformer sampler (per-fragment ETKDGv3 anchored on the seed plus seeded non-core perturbation) and the relative-configuration face descriptor."
depends_on: [OPR.0.6.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_conformers
parent: null
hacf_touches: ["src/eta_rxncat/conformers/**", "tests/unit/conformers/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/conformers/test_ts_sampler.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 TS conformer sampler and the face descriptor

## Intent

Add a deterministic, core-frozen TS conformer sampler (per-fragment ETKDGv3 anchored on the seed,
plus seeded perturbation of the non-core atoms) and the relative-configuration face descriptor, so
that samples never move the reactive core and never cross to the other diastereomeric face.

Context the builder needs:
- **TJ, verbatim (Q1):** "B: add a TS conformer search in v0.6.0 (core-frozen conformer sampling
  around each TS, each re-searched with P-RFO, deduplicated and Boltzmann-summed; about 2-3 more
  slices) — NOT the recommendation. Mind the memory rule for GPU TS searches."
- Mission R1 (face, normative §5 "Face check"), R11, R16, HF-3…HF-5. Module
  `src/eta_rxncat/conformers/ts_sampler.py`, node `eta_rxncat_conformers`:
  - `forming_bond_configuration(state, forming_bonds, bonds) -> tuple[int, ...]` and
    `FaceDescriptorError`;
  - `sample_ts_conformers(seed: MolecularState, core_indices, forming_bonds, bonds, options:
    TSEnsembleOptions) -> list[TSSample]` (`TSSample`: `source` `"fragment_embed:<k>"` or
    `"perturb:<k>"`, `state`, `face`, `start_sha256`), seed excluded, pre-deduplicated, ordered per R11.
- **Measured (do not repeat the failed design):** ETKDG `coordMap` over the whole two-fragment TS is
  ignored by RDKit 2026.09.2 (core off by up to 2.15 Å, faces scrambled; HF-4). Per connected
  fragment of the perceived graph (forming bonds are not bonds): build the fragment as its own
  RDKit molecule (bond orders by `rdDetermineBonds.DetermineBonds(charge=0)` per fragment, falling
  back to connectivity, recorded), embed `n_embed` conformers with ETKDGv3 (`randomSeed`,
  `numThreads=1`) and a coordMap on the fragment's **anchor** atoms = its core atoms, plus their
  heavy neighbours inside the fragment when the core atoms are fewer than three or collinear
  (Tier 4: Cp anchor `{0,1,4,5}`, dienophile anchor `{2,3}` + its ring CH₂ carbons). Kabsch-place
  each embedding on the seed by the anchor; combine fragment k of each embedding into sample k.
  Then `n_perturb` samples: seed + `default_rng(random_seed)` normal noise σ `perturb_sigma_angstrom`
  on every non-core atom. In **every** sample set the core coordinates to the seed's exactly.
  Pre-dedup (seed first) at `pre_dedup_rmsd_angstrom` with proper-rotation RMSD with H using the
  seed's perceived-graph automorphisms (`thermo._geometry.automorphisms` + `permuted_rmsds`; cap
  `max_automorphisms`, reaching it is an error).
- Face descriptor (R1): for each forming bond (i, j), s = sign V_i · sign V_j, V_c =
  det[x_a − x_c, x_b − x_c, x_p − x_c] with (a, b) the two lowest-index neighbours of c in the
  **seed's** perceived graph other than partner p. Measured on Liu's xyz files (Liu atom order):
  TS1a_n (+1, +1), TS1a_x (−1, −1), TS1b_n (+1, +1), TS1b_x (−1, −1). Tests read
  `tests/e2e/data/e2e5/xyz/TS1a_n.xyz`, `TS1b_n.xyz` (and slice 08's TS1a_x/TS1b_x once landed; until
  then the test builds the exo case by the reflection below).
- Crossover fixture for G4: reflect the dienophile's non-core heavy atoms and their H through the
  plane containing C2, C3 and the normal of the diene plane — the descriptor must flip for both
  forming bonds and the sampler must never produce it.
- Determinism: two calls with equal inputs give byte-equal coordinates (test).
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

**Score: 9/10.** The algorithm was prototyped and measured by resolve on all four Tier 4 seeds
(HF-5: core ≤ 0.011 Å before reset, 50/50 faces kept, deterministic). The remaining risk is
packaging it cleanly with RDKit per-fragment molecules; the tests pin the behaviour.

## Mini-requirements

1. US-007/G4: every sample's core coordinates equal the seed's exactly; every sample's face equals
   the seed's (Tier 4 seeds and a stub); samples are pre-deduplicated and ordered per R11.
2. G4: determinism (byte-equal) for a fixed seed; a different `random_seed` changes the perturbations.
3. G4/R1: `forming_bond_configuration` returns the four measured tuples, is invariant under
   reflection and rigid motion, flips under the crossover, and raises `FaceDescriptorError` on a
   degenerate (zero-volume) or under-coordinated end.
4. G8: importing `eta_rxncat.conformers.ts_sampler` loads no `torch`, `pyscf`, `fairchem`,
   `geometric` (subprocess test).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `conformers/generate.py`,
      `thermo/_geometry.py`, `mapping/report.py` (`perceive_bonds`).
- [x] Task 2: `forming_bond_configuration` + tests.
- [x] Task 3: per-fragment embedding, Kabsch placement, perturbation, core reset, pre-dedup.
- [x] Task 4: `tests/unit/conformers/test_ts_sampler.py` (G4 sampler parts, G8); required checks.
- [x] Task 5: commit; updater once (node `eta_rxncat_conformers`).

## 4. The Negative Space (Constraints)

- **DO NOT** use a coordMap across disconnected fragments; **DO NOT** move core atoms.
- **DO NOT** call an engine here; **DO NOT** import geomeTRIC.
- **DO NOT** read any conformer-search source outside this repo (clean room).

## Proof contract

- [ ] `uv run pytest tests/unit/conformers/test_ts_sampler.py -q` passes (core, face, crossover,
      determinism, G8).
- [ ] Required checks exit 0.

## Source material

- Mission R1, R11, R16, HF-3…HF-5, §5 "Face check"; resolve's prototype (behaviour only, not code
  to copy) is described in `~/.hacf/eta-rxncat-hacf/evidence/v060-resolve/README.md`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

02.
