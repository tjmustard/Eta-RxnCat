---
id: OPR.0.6.0.9
slice: 09-e2e-unmapped
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Run the unmapped Cp + cyclopropene endo/exo pair with TS ensembles on GFN2 and UMA, gated per TJ Q3 A, and commit the candidates."
depends_on: [OPR.0.6.0.7, OPR.0.6.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.6.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 Tier 4 E2E — unmapped endo/exo (TS1a_n vs TS1a_x) with TS ensembles

## Intent

Run the unmapped Cp + cyclopropene endo/exo pair end to end on GFN2 and UMA — seed TSs from Liu's
geometries, TS ensembles, Boltzmann-summed ΔΔG‡ and % de — gated per TJ's Q3 A, and commit the
candidates for TJ's Phase 3.

Context the builder needs:
- **TJ, verbatim (Q3):** "A: assertions on both engines (GFN2 gated per pair only if measured to
  reproduce, else report-only) + UMA within reference +/-2.0 floored at 0.5; pre-build misses come
  back to TJ (the recommendation)." Q1 B (ensembles). v0.5.0 Phase 3 "A: 0.75 all (Recommended)".
- Inputs: slice 08's `t4_endo_exo_unmapped.yaml`; reactants through `run_species` as v0.5.0 slice 08
  did (`tests/e2e/t3.py`, `e2e_env.recipe_for`); TS ensembles with slice 06 (`GeometricOptimizer()`
  injected, `TSEnsembleOptions()` defaults = Tier 4 sizes, R18); score with slice 04 (`kind="de"`).
  Each recipe uses a **fresh store** under TMPDIR, then a second run in the same store (G7).
- **Member gates** (slice 06's `member_gates`): GFN2 = mode count + active core (KE ≥ 0.60) + forming
  overlap ≥ 0.50 + in phase (Q-TJ4 A); UMA = mode count + active core + full identity.
- **Gated per recipe** (one `gated_outcome` per test): seeds converge and pass member gates; endo
  is major; Boltzmann-summed ΔΔG‡ > 0.5 (both engines; GFN2 gated on this pair, HF-7); UMA ΔΔG‡ ∈
  [2.3, 6.3]; zero `engine_error` and zero `face_mismatch` exclusions; **endo seed regression vs
  `tests/fixtures/v0.5.0/t3_ts1a_n.{recipe}.json`** per mission R6 (TS E ≤ 1e-5 Eh, geometry ≤
  0.01 Å, TS G and ΔG‡(1 M) ≤ 0.01 GFN2 / 0.75 UMA kcal/mol); per-pathway ΔG‡ difference equals
  ΔΔG‡ within 1e-9 kcal/mol (single-member pathways) — report it otherwise; G7 second run all hits,
  zero rows, equal ensembles and score.
- **Reported, never gated:** members, weights, exclusions by reason, merges and flagged merges, seed
  forming-core RMSD to Liu's TS (identity map), per-pathway ΔG‡ at 1 M and 1 atm, % de, Liu's
  +4.273 and TJ's +4.3, metrics (calls, hits, wall time).
- **Measured expectations (HF-6, HF-7, HF-10):** single-TS ΔΔG‡ GFN2 +3.977, UMA +4.602; one member
  per ensemble on both engines; ensemble wall time GFN2 ~70–100 s, UMA UMA ~100–145 s (one stall seen, HF-13);. A large
  deviation from these is a finding to report, not a reason to change a bound.
- Candidate: `tests/candidate_outputs/v0.6.0/t4_unmapped.{xtb,uma}.json` (v0.5.0 candidate rule:
  committed in a candidates-only commit, `git show` in the proof; nothing reads it back). The
  ledger writer adds `tests/candidate_outputs/v0.6.0/**` to `eta_rxncat_species_runner` through this
  slice's touches (ensure-node, R15).
- **Heavy-run rules (TJ's memory rule, verbatim: "(3) Memory rule: swap full, both rigs build at
  once, NO overlapping heavy runs host-wide; clear seats between runs; recover stalled seats.")**:
  before **each** GPU/E2E command, run a blocking host check in its **own** call — `free -g`
  (≥ 9 G available) plus `ps` for other rigs' pytest / eta python — that exits non-zero on a miss;
  run the heavy command only in a **separate** call after it passes; never echo-then-run, never
  overlap; if blocked, wait with a background wait (no foreground sleep) and re-check. Record each
  check's output in the proof. One (pair × recipe) per command. UMA one seat at a time (ADR-0008).
  Every E2E/verdict command sets `ETA_RXNCAT_ACCEPTANCE=1` and, for xtb,
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (unset, the xtb E2E silently
  skips with exit 0); both are recorded in the proof. UMA runs in `.venv-accept-uma`.
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

**Score: 9/10.** Resolve ran this flow on both engines (HF-6…HF-10): seeds validate, the regression
holds, ΔΔG‡ is inside every gate, ensembles are one member. Residual risk is ordinary E2E plumbing.

## Mini-requirements

1. US-010/G5: every gated check passes on GFN2 and on UMA.
2. US-010/G7: second run all hits, zero rows, equal payloads.
3. US-010: the candidates list every member, weight, exclusion and merge, and are committed.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start.
- [ ] Task 2: `tests/e2e/t4.py` helpers (recipes, member gates, case run, gates, candidate payload)
      and `tests/e2e/test_t4_unmapped.py`; offline helper tests.
- [ ] Task 3: host check (own call) → GFN2 run; host check → UMA run; record both. Each run under
      `timeout 3600` (mission R25); a timeout is a stop-and-report with its output.
- [ ] Task 4: candidates-only commit; code commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** loosen a gate after a run; a miss is a stop-and-report to the lead (for TJ).
- **DO NOT** gate GFN2 on a numeric window; **DO NOT** write `tests/fixtures/`.
- **DO NOT** run heavy commands without the blocking host check, or overlapping.

## Proof contract

- [ ] GFN2 and UMA test outcomes (`ETA_RXNCAT_ACCEPTANCE=1`, `ETA_RXNCAT_XTB` set) with exit codes
      and pass counts, each behind a recorded host check.
- [ ] `git show --stat` of the candidates-only commit.
- [ ] Required checks exit 0.

## Source material

- Mission G5, G7, R1–R3, R6, R9, R10, R12, R18, R21, HF-6…HF-11; slice 08 inputs; v0.5.0
  `tests/e2e/t3.py`, `test_t3_diels_alder.py`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

07, 08.
