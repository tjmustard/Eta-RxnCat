---
id: OPR.0.6.0.10
slice: 10-e2e-mapped-pruning
mission: release-0.6.0
status: done
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Run the mapped Cp + cyclobutene endo/exo pair (TS1b_x grafted from TS1a_x) with TS ensembles on GFN2 and UMA, check TJ's 1.5 kcal/mol pruning against the measured ddG dagger, and commit the candidates."
depends_on: [OPR.0.6.0.9]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.6.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 Tier 4 E2E — mapped endo/exo (TS1b_n vs grafted TS1b_x) and pruning

## Intent

Run the mapped Cp + cyclobutene endo/exo pair end to end on GFN2 and UMA — TS1b_n from v0.4.0's M1
start, TS1b_x grafted onto TS1a_x and pre-relaxed — with TS ensembles, the Boltzmann-summed ΔΔG‡ and
TJ's 1.5 kcal/mol pruning check against the measured value, and commit the candidates.

Context the builder needs:
- **TJ, verbatim:** Q3 A (above, slice 09); Q2 A "…1.5 in the Tier 4 fixture, no library default";
  Q-E4 (P1b_x is `downstream_exo_minor`).
- Inputs: slice 08's `t4_mapped_selectivity_pruned.yaml`; TS1b_n start
  `tests/fixtures/v0.4.0/m1_relaxed.{recipe}.json` `relaxed_product` (as v0.5.0); TS1b_x start =
  `graft(TS1a_x, cyclobutene, M1 lists)` then `relax_constrained_core(…, core [1,2,3,5],
  {"maxiter": 200})` on the recipe's engine (v0.5.0 TS4a pattern, `tests/e2e/t3.py`
  `grafted_start`). Map graft→Liu TS1b_x by the ADR-0031 rule (lexicographically smallest
  element-preserving isomorphism onto the perceived graph; `tests/e2e/m1.py:derive_map`); do **not**
  reuse TS1b_n's map (HF-8: atom orders differ).
- Ensembles, member gates, store discipline and the endo regression (vs
  `tests/fixtures/v0.5.0/t3_ts1b_n.{recipe}.json`, mission R6) as slice 09.
- **Gated per recipe:** seeds converge and pass member gates; endo major; ΔΔG‡ > 0.5 (both engines,
  HF-7); UMA ΔΔG‡ ∈ (0.5, 3.8]; zero `engine_error`/`face_mismatch`; the endo regression; **G6
  pruning**: the decision uses the measured Boltzmann-summed ΔΔG‡; if > 1.5, `downstream_exo_minor`
  (P1b_x) is `pruned` with zero engine calls (counting wrapper), else it is computed through
  `run_species` and its result recorded; G7 all hits (the pruning record equal).
- **Reported:** pure-graft and final forming-core `[1,2,3,5]` RMSD to Liu's TS1b_x (measured 0.046 /
  0.022–0.027 Å) and of TS1b_n to Liu's TS1b_n; members, weights, exclusions, merges; % de; TJ's
  +1.8 and Liu's +1.849; which pruning branch ran and the margin to 1.5.
- **Measured expectations (HF-7, HF-8, HF-10):** single-TS ΔΔG‡ GFN2 +1.753 → **prune**; UMA +1.410
  → **compute P1b_x**. Both are pass outcomes (G6). One member per ensemble.
- Candidate: `tests/candidate_outputs/v0.6.0/t4_mapped.{xtb,uma}.json`.
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

**Score: 9/10.** Resolve measured the graft, both seeds and both ΔΔG‡ values on both engines
(HF-7, HF-8, HF-10). The pruning branch differs by engine by design and both branches are unit-tested
in slice 07.

## Mini-requirements

1. US-011/G5: every gated check passes on GFN2 and on UMA.
2. US-011/G6: the pruning decision matches the measured ΔΔG‡ vs 1.5; a pruned P1b_x has zero engine
   calls; a computed one has a species result.
3. US-011/G7: second run all hits, zero rows, equal payloads and decision.
4. Candidates committed.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start.
- [x] Task 2: `tests/e2e/test_t4_mapped.py` (reusing slice 09's `t4.py`); offline helper tests.
- [x] Task 3: host check (own call) → GFN2 run; host check → UMA run; record both. Each run under
      `timeout 3600` (mission R25); a timeout is a stop-and-report with its output.
- [x] Task 4: candidates-only commit; code commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** use Liu's TS1b_x as a start (it is the reference only).
- **DO NOT** change the 1.5 threshold or loosen a window after a run.
- **DO NOT** run heavy commands without the blocking host check, or overlapping.

## Proof contract

- [ ] GFN2 and UMA outcomes with exit codes, each behind a recorded host check; the pruning branch
      and ΔΔG‡ per recipe.
- [ ] `git show --stat` of the candidates-only commit; required checks exit 0.

## Source material

- Mission G5–G7, R6, R7, R12, HF-7, HF-8; slices 06–09; v0.5.0 `tests/e2e/t3.py`, `m1.py`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

09.
