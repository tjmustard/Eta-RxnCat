---
id: OPR.0.7.0.10
slice: 10-e2e-inputs
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Write the v0.7.0 E2E inputs: the Tier 4 endo/exo reference graph, the enumeration plan with the H16 site maps, expected faces and orientation centre, the two fallback constructs, and offline tests that pin the measured geometry."
depends_on: [OPR.0.7.0.3, OPR.0.7.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_v070_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 E2E inputs and offline checks

## Intent

Freeze every input the E2E slices run, and pin the resolve measurements as offline tests so a later
change that breaks them fails fast without an engine (mission HF-1, HF-2, R2, R24-R26; supports
US-010, US-011).

Context the builder needs:
- **Files (R26):** `tests/e2e/data/e2e5/v070_enumeration.yaml`, `v070_fallback.yaml`, a loader
  `tests/e2e/v070.py`, and `SOURCES.md` rows. Inputs are the existing `xyz/TS1a_n.xyz`,
  `xyz/TS1a_x.xyz`, `xyz/1_cyclopentadiene.xyz`, `xyz/5_cyclopropene.xyz` and the slice-14 fragments
  `r_ethyl_cyclopropene.xyz`, `r_npropyl_cyclopropene.xyz` with their roles in
  `t4_flexible_alkyl.yaml`; no new geometry is invented.
- **Reference graph (schema 1):** nodes `cyclopentadiene` and `cyclopropene` (kind `reactant`,
  priority 1, one template each) and `TS1a_n` (pathway `endo`) and `TS1a_x` (pathway `exo`), kind
  `transition_state`, one template each.
- **Enumeration plan:** one site `c7` with maps on `TS1a_n`, `TS1a_x` and the `cyclopropene` reactant
  (its CH2 H anti-rule analogue: the reactant has no diene, so the map is declared by the C7 H that
  the fragment's own `ring_h` pairs with; record the choice and the fit in the fixture comment);
  TS maps: keep all but 16, delete [16], alignment [7, 2, 3, 17], core [0..5], forming bonds
  [[1, 2], [3, 5]]; library entries `ethyl`, `npropyl` (both sp2 orders listed); selectivity set
  `endo_exo` with `expected_face` endo [1, 1], exo [-1, -1] (HF-2), reactant nodes cyclopentadiene +
  cyclopropene; `max_candidates: 2`; `max_alignment_rmsd_angstrom: 0.15`; orientation centre = the
  product index of C7 (7).
- **Fallback plan:** node `TS1a_n` with two templates. Graft-time construct: rank 1 = TS1a_n with
  alignment [7, 2, 3, 8] (a Cp H; HF-2 best fit 0.888 Å → `alignment_rmsd`), rank 2 = the real map.
  Run-time construct: rank 1 = the **TS1a_x geometry** in the endo node (same composition, its own
  map), rank 2 = TS1a_n; expected face endo [1, 1], so rank 1 gives `seed:face_mismatch_pathway`
  before any search. Entry: ethyl only.
- **Offline tests (`tests/e2e/test_v070_inputs.py`, no engine, always run):** the site rule picks H16
  on both TSs (angles 179.9° / 163.5°); chosen orders ethyl endo [3, 4] / exo [4, 3]; fits within
  HF-1's ranges; faces of TS1a_n/TS1a_x and of every enumerated product; the C7 orientation sign
  flips between H16 and H17; the enumerator on the plan gives N = 2 `ok` candidates, 0 contacts,
  `projected_ts_searches` as computed; the fallback plan gives rank-1 refusal `alignment_rmsd` and,
  for the run-time construct, a start face [-1, -1] != expected; file sha256s match `SOURCES.md`.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (slices 11-13 write candidates; they never read them back as input).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.

## 1. The Confidence Mandate

**Score: 9/10.** Every number pinned here was measured by resolve (HF-1, HF-2) with the same files.
Residual risk: the reactant map on `5_cyclopropene.xyz`, which the builder measures and records with
a stop-and-report if no clean fit (≤ 0.15 Å) exists.

## Mini-requirements

1. The two YAML files load into `EnumerationPlan`s through `tests/e2e/v070.py`.
2. The offline tests above pass without an engine.
3. `SOURCES.md` rows with sha256 for every input used.
4. The reactant map's fit is recorded; ≤ 0.15 Å or stop-and-report.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] Write the YAMLs, loader and SOURCES rows.
- [ ] Offline tests.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** edit any existing fixture or xyz; **DO NOT** run an engine here.
- **DO NOT** use a `t5_` prefix (Human Fixture Tier 5 collision).

## Proof contract

- [ ] `uv run pytest tests/e2e/test_v070_inputs.py -q` passes (requirements 1-4).
- [ ] Required checks exit 0.

## Source material

- Mission HF-1, HF-2, R2, R24-R26; evidence `offline.json`, `offline_m4.json`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.3, OPR.0.7.0.5.
