---
id: OPR.0.7.0.15
slice: 15-seed-geometry-checks
mission: release-0.7.0
status: done
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Refuse a clashing start geometry before any engine call and exclude any TS whose pre-relax or search made or broke a bond outside the template's forming bonds, each with a recorded reason and detail, behind a seed_checks keyword the fallback runner turns on."
depends_on: [OPR.0.7.0.13]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_selectivity
parent: null
hacf_touches: [src/eta_rxncat/orchestrator/ts_ensemble.py, src/eta_rxncat/orchestrator/ts_fallback.py, src/eta_rxncat/orchestrator/__init__.py, src/eta_rxncat/core/selectivity_models.py, src/eta_rxncat/core/enumeration_models.py, src/eta_rxncat/core/__init__.py, "tests/unit/orchestrator/**", "tests/unit/core/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator, tests/unit/core]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Seed clash check and unintended-bond check

## Intent

Keep a clashing start geometry away from every engine, and keep any TS whose path made or broke a
bond the template does not intend out of the ensemble. Each refusal gets a recorded reason and
detail (mission G14, R35; TJ's replan-7 decisions "Fix site + seed clash check" and "Yes, add it in
v0.7.0" for the unintended-bond check).

Context the builder needs:
- **Why (measured; evidence `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7/MEASUREMENT.md`):**
  - TJ's flagged TS is sample 6 (`1f64216a4471`, ethyl endo GFN2, `fragment_embed:6`). Its start
    (frame 0 of pre-relax row `c50bc2b4e5ca…`) puts ethyl H21 **0.438 Å** from diene C4.
  - The pre-relax formed C4–C17 and C0–H21 and broke C17–H21, and the TS search kept them.
  - eta excluded it only indirectly, as `gate_failed:forming_overlap`.
  - The same start on UMA gave an `orientation_mismatch` TS. The ethyl exo UMA 600 s
    `PreRelaxTimeout` stall also had a clashing start (C6–C17, 1.632 Å).
- **Topology `T` of an ensemble:** the seed TS's perceived bonds `seed_bonds` (as today), plus the
  forming bonds as graph edges. A pair is **non-bonded** when its graph distance in `T` is >= 3.
- **Clash rule (TJ's Q-R7a; default A until he answers):**
  - A non-bonded pair `(i, j)` clashes when `d_ij < SEED_CLASH_FACTOR × (r_i + r_j)`.
    - `r` is `mapping.report.covalent_radius_angstrom`.
    - `SEED_CLASH_FACTOR` is a named constant in `orchestrator/ts_ensemble.py`, equal to
      `mapping.graft.CONTACT_FACTOR` (1.3, imported, not retyped).
  - The detail is the pair with the lowest `d_ij / (r_i + r_j)`: `(i, j)` with `i < j`, `d` in Å,
    and the ratio.
  - Measured over all 121 starts of the 11 units, it rejects 53. Every one of them is already
    excluded today. It rejects 0 of the 68 seeds, members and merged samples:
    - used starts are >= 1.543;
    - rejected starts are <= 1.286;
    - sample 6 is 0.409.
  - If TJ picks B (scaled vdW 0.45 × Bondi) or C (an absolute Å), only the constant and the radius
    function change. The lead amends this slice before its audit.
- **Reject rule (TJ's Q-R7b; default A):**
  - A clashing sample is excluded `seed_clash` with its detail, and **no engine call** is made.
  - It keeps its sample index (its slot in `options.max_research` is used), and nothing is drawn in
    its place. So every other sample's start, and every stage key, is unchanged.
  - If TJ picks B (draw a replacement), the lead replans this rule before the slice merges.
- **Unintended-bond check** (fixed; not a TJ choice): for a geometry `G` and an intended bond set
  `B` (forming pairs excluded on both sides):
  - `formed = perceive_bonds(G) − B − forming` and `broken = B − perceive_bonds(G)`;
  - either one non-empty is `bond_changed:<stage>`, with both lists (sorted `(i, j)`) in the detail.
- **Where the checks run.** New keyword `seed_checks: bool = False` on `run_ts_ensemble_detailed` and
  `run_ts_ensemble`. It is not a `TSEnsembleOptions` field (R6's pattern), so a `False` call is
  v0.6.0's behaviour byte for byte. `run_ts_with_fallback` passes `True`. With `True`, in
  `run_ts_ensemble_detailed`:
  1. **Seed TS:** after `run_transition_state(seed)` and before the member gates, check
     `bond_changes(seed TS final, perceive_bonds(seed.start) − forming)`. On a change, fail with
     `seed:bond_changed:ts` plus the detail.
  2. **Each sample, before `pre_relax.run`:** `find_clash(sample.state, T)`. On a clash, exclude it
     `seed_clash` with `pre_relax_wall_time_s` None.
  3. **After a successful pre-relax:** `bond_changes(relaxed, seed_bonds)`. On a change, exclude it
     `bond_changed:pre_relax` before the TS search.
  4. **After `run_transition_state` returns a record, before the member gates:**
     `bond_changes(final, seed_bonds)`. On a change, exclude it `bond_changed:ts`.
  - The existing `connectivity_changed` check stays where it is.
- **In `run_ts_with_fallback`, per template:**
  - **Before the guarded pre-relax:** if any of that template's `GraftRecord`s has
    `close_contact_count > 0`, note `fell_through` `seed:seed_clash` with detail
    `close_contact_count`, at **0 engine calls**.
    - This is graft's own contact rule: the same 1.3 factor, applied to template–fragment pairs
      minus the graft's source bonds.
    - Every v0.7.0 graft records 0 contacts (G7), so no run changes.
    - `enumerated_pathway_inputs` already holds the node's records (R32).
  - **After the pre-relax, before the face check:**
    `bond_changes(relaxed, perceive_bonds(graft output) − forming)`. On a change, the attempt is
    `seed:bond_changed:pre_relax`.
  - Then call the ensemble with `seed_checks=True`.
- **R4 allow-list** (`_FALL_THROUGH_REASONS`): add `seed:seed_clash`, `seed:bond_changed:pre_relax`
  and `seed:bond_changed:ts`. Each is a geometry fault of that template's seed, so it falls through.
  The `typing.get_args(TSSearchFailureReason)` test is unchanged.
- **Core (additive, numpy-free):**
  - New `SeedCheckDetail` in `core/selectivity_models.py`:
    `check: Literal["clash", "bond_changed"]`, `pair: tuple[int, int] | None`,
    `distance_angstrom`, `ratio_to_covalent_sum`, `bonds_formed`, `bonds_broken`,
    `close_contact_count: int | None`.
  - It is carried as `TSEnsembleExclusion.detail`, `TSEnsemble.failed_detail` and
    `FallbackAttempt.detail` (core/enumeration_models.py). Each defaults to `None` and is **left out
    of the serialised form when `None`**, through a wrap serializer as
    `OptimizationFrame.accepted_bool` does.
  - `_EXCLUSION_REASON` gains `seed_clash` and `bond_changed:(pre_relax|ts)`.
  - The core ledger description (1973/2000) is not changed.
- **Old records:**
  - every `TSEnsemble`, `TSEnsembleExclusion` and `FallbackRecord` in `tests/fixtures/v0.6.0/**` and
    `tests/fixtures/v0.7.0/**` loads and re-serialises byte-equal (a test);
  - every existing `run_ts_ensemble*` test passes unchanged (`seed_checks` False).
- **Known-answer geometry test.** `tests/unit/orchestrator/data/v070_sample6_start.xyz` and
  `v070_member1_start.xyz` are written from the evidence store:
  - the sources are pre-relax frame 0 of `c50bc2b4e5ca…` and of `1e060de0dcbc…` (ethyl endo GFN2,
    `fragment_embed:0`, a member);
  - the coordinates are read with sqlite `mode=ro` and the provenance is in the proof;
  - the seed topology is `perceive_bonds` of the fixture `v070_enum_ethyl_endo_xtb.runrecord.json`
    `TS1a_n__ethyl` species state (the graft output, measured to have the seed TS's topology), plus
    the forming bonds `[1, 2]` and `[3, 5]`.
  - `find_clash` returns `(4, 21)`, 0.438 Å, ratio 0.409 (±0.001) on sample 6, and `None` on the
    member.
- **Engine-free tests** (fake engines, as in `test_ts_ensemble_guards.py`):
  - a clashing sample is excluded with 0 engine calls for it;
  - a fake pre-relax that forms a bond is excluded `bond_changed:pre_relax` with 0 `ts_opt` calls
    for it;
  - a fake TS that forms a bond is `bond_changed:ts` before the gates;
  - a seed TS that changes a bond fails `seed:bond_changed:ts`;
  - the fallback with `close_contact_count` 1 gives `fell_through` `seed:seed_clash` at 0 engine
    calls, and rank 2 is chosen;
  - the allow-list test is extended;
  - `None` details are omitted when serialised.
- **No engine command and no store write in this slice.** No `review/` change: slice 16 renders the
  new reasons and details.
- **Node** `eta_rxncat_selectivity` (description 1249/2000). Add one sentence on the seed checks.
- **Times:** build about 2.5 h of seat time and audit about 0.75 h. GPU 0.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (the E2E writes candidates and never reads them back as input;
    `tests/fixtures/v0.7.0/` holds byte-equal copies and may be read).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
    Plain literal `rm -f` only (never `rm -rf` on a computed path).
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.

## 1. The Confidence Mandate

**Score: 9/10.**
- The rule, the cut and its margins are measured on all 121 real starts.
- The sample-6 bonds are confirmed at the pre-relax and at the TS.
- The hooks fall exactly at existing seams (before `pre_relax.run`, after it, after
  `run_transition_state`).
- Residual: TJ may pick another cut or rule (one constant, or a lead replan before the merge).

## Mini-requirements

1. No sample whose start clashes reaches an engine. It is excluded `seed_clash`, with its pair,
   distance and ratio.
2. A bond made or broken outside the forming bonds, at the pre-relax or at the TS, excludes the
   sample (or fails the seed) before the next stage, with the bonds listed.
3. A graft with recorded close contacts is never seeded: the attempt is `seed:seed_clash` and falls
   through.
4. With `seed_checks=False`, every result and serialised record is unchanged.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] Core: `SeedCheckDetail`, the three optional fields with the omit-when-None serializer, the
  reason regex; round-trip tests on the v0.6.0/v0.7.0 fixtures.
- [x] `find_clash`, `bond_changes` and `SEED_CLASH_FACTOR` in `ts_ensemble.py`; the known-answer
  geometry test.
- [x] `seed_checks` in the ensemble (four hooks) and in the fallback (close contacts, pre-relax
  bonds, allow-list); fake-engine tests.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change any stage key, `TSEnsembleOptions` field, sampler output or sample index.
- **DO NOT** run an engine, write a store, or touch `review/`, `tests/e2e/` or the fixtures.
- **DO NOT** repair or replace a clashing sample (Q-R7b A) unless the lead amends the slice.
- **DO NOT** change behaviour when `seed_checks` is False.

## Proof contract

- [x] The known-answer clash numbers (sample 6 and the member) and the provenance of the two
  geometries.
- [x] Fake-engine tests: per check, the reason, the detail and the engine-call counts.
- [x] Round-trip byte equality of the old fixtures; `seed_checks=False` tests unchanged.
- [x] Required checks exit 0.

## Source material

- Mission G14, R4, R6, R35; `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7/` (MEASUREMENT.md,
  cov_margin.out, connectivity.out, TJ_QUESTION.md); `orchestrator/ts_ensemble.py:272-505`,
  `orchestrator/ts_fallback.py:47-70, 312-367`, `mapping/graft.py:CONTACT_FACTOR`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.13 (the last audited slice). TJ's Q-R7a/Q-R7b answer may amend the cut or the rule
  before the audit.
