---
id: OPR.0.3.0.1
slice: 01-starter
mission: release-0.3.0
status: done
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Unpack the v0.3.0 reference starter byte-identical into docs/prd/v0.3.0/, open the 23-row discrepancy register, mark PD-007 decided, and trim the scaffold ledger description to 1800 characters or fewer."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["docs/prd/v0.3.0/**", docs/prd/PLAN_DISCREPANCIES.md, pyproject.toml, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.3.0 starter unpack, discrepancy register and scaffold description trim

## Intent

Unpack `PRDs/Eta-RxnCat-v0.3.0.zip` into `docs/prd/v0.3.0/` as reference only, open
`docs/prd/v0.3.0/DISCREPANCIES.md` with the 23 starter/plan rows, mark PD-007 decided, and trim the
`eta_rxncat_scaffold` ledger description so later slices can reconcile it under 2000 characters.

Context the builder needs:
- The zip is TJ's reference starter (TJ Q2 "B": reference only). Its sha256 is
  `eaa9638d7d77ad0dc8c51fb4ef749b7a1d08b28dd106ca5ae7312ab6a1ddb401` (the draft's `ad092dff…` was
  wrong, R12) and it holds 30 files (`unzip -Z1`). ADR-0007: `docs/prd/**` starters are excluded
  from every gate (ruff, mypy, pytest collection, licence gate); check the existing exclusions in
  `pyproject.toml` cover `docs/prd/v0.3.0/` exactly as they cover `v0.2.0`.
- `eta_rxncat_scaffold`'s description is 1991/2000 characters. Slices 04–06 change scaffold files
  and move three globs out of it; the audit's reconciliation would push it past 2000. Rewrite it
  now to ≤ 1800 characters with the same facts (what scaffold owns; no history), via
  `python3 .agents/scripts/hyper_ledger.py ensure-node --id eta_rxncat_scaffold --description-file <file>`.
  Do not change its files in this slice.

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

**Score: 10/10.** Byte-level unpack, a fixed row list and one ledger description edit.

## Mini-requirements

1. US-001: `docs/prd/v0.3.0/` contains the zip's 30 entries byte-identical (sha256 per file equals
   the zip member's), under the zip's own top-level directory name as `v0.2.0` did.
2. `docs/prd/v0.3.0/DISCREPANCIES.md` lists DV-01…DV-23, each with the starter file and line, the
   starter behaviour, the v0.3.0 decision and its source (mission §5 "Discrepancy register"; R-ids).
   Status column `open` for rows a later slice implements, with that slice named.
   - DV-01 `core/thermo.py` numpy math in core → `eta_rxncat.thermo` (contracts stay in core).
   - DV-02 no rotational σ → σ from geometry. DV-03 Grimme B_av = mean moment → 1e-44 kg·m².
   - DV-04 linear E_trans+rot 3 RT → 5/2 RT. DV-05 21-element table, default 12.0 → RDKit Z 1–118.
   - DV-06 drops six eigenvalues nearest zero → complement diagonalisation. DV-07 (−10, 10) cm⁻¹
     dropped → soft modes with |ν̃|. DV-08 `head_gordon` offered → not offered.
   - DV-09 stationary-point flag → `NotAMinimumError`. DV-10 XYZ input, input returned on failure →
     SMILES, typed errors. DV-11 RDKit pruning merges mirrors, no energy window → own dedup,
     degeneracy from conformer chirality, window. DV-12 exponent clip 500 → log-sum-exp.
   - DV-13 geomeTRIC module-level import, cwd files, `run_optimizer` logging → lazy import in the
     `opt-geometric` extra, lower-level API, sandbox. DV-14 bare `except` tric → cart → recorded
     three-step ladder. DV-15 starter engine API → `Engine.evaluate` / `PotentialResult`.
   - DV-16 hard-coded fake energies in `tests/unit/test_v030_thermo_conformers.py` → tier-D and
     real runs. DV-17 starter `MolecularState` → v0.1.0 contract. DV-18 plan vs zip PR #8
     incremental-solvation test → TJ Q4 "C" both.
   - DV-19 TJ's 5-tier YAMLs (graph schema, `rdkit_ff` ranking, 0.35/0.25 Å) → provisional v0.3.0
     fixture format (TJ Q-E3 "B"). DV-20 TJ's per-node `hits_by_stage` → per-species
     `species_stage_cache`.
   - DV-21 isotope-labelled SMILES → refused. DV-22 single ETKDG pass misses s-cis-side dienes →
     second pass with `useExpTorsionAnglePrefs=False`. DV-23 `PotentialResult` shallow frozen-ness →
     carried forward; consumers copy matrices.
3. `docs/prd/PLAN_DISCREPANCIES.md` PD-007 status reads exactly
   `decided (TJ v0.3.0 Q4: "C", row qitem-20261123010134-cd43c1fb3e761e27)`.
4. The scaffold description is ≤ 1800 characters (`hyper_ledger.py validate` passes).

## 3. Implementation Plan (Task List)

- [x] Task 1: `sha256sum PRDs/Eta-RxnCat-v0.3.0.zip` equals the value above; stop if not.
- [x] Task 2: unpack with Python `zipfile` into `docs/prd/v0.3.0/`; compare per-member sha256.
- [x] Task 3: confirm the gate exclusions cover the new directory (ruff, mypy, pytest, licence).
- [x] Task 4: write `DISCREPANCIES.md`; update PD-007.
- [x] Task 5: scaffold description trim; `python3 .agents/scripts/hyper_ledger.py validate`.
- [x] Task 6: required checks; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** modify `PRDs/` or any file inside the unpacked starter.
- **DO NOT** let any gate scan `docs/prd/v0.3.0/`.
- **DO NOT** change scaffold's `files` in this slice.

## Proof contract

- [ ] `python3 -c` over the zip: every member's sha256 equals its unpacked file's; 30 files.
- [ ] `grep -c '^| DV-' docs/prd/v0.3.0/DISCREPANCIES.md` → 23.
- [ ] `grep -n 'PD-007' docs/prd/PLAN_DISCREPANCIES.md` shows the exact decided text.
- [ ] `python3 .agents/scripts/hyper_ledger.py validate` exit 0; scaffold description length ≤ 1800.
- [ ] The required checks exit 0 (ruff/mypy/pytest unaffected by the starter).

## Source material

- `PRDs/Eta-RxnCat-v0.3.0.zip`; mission §5 "Discrepancy register", R11, R12; ADR-0007.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- none
