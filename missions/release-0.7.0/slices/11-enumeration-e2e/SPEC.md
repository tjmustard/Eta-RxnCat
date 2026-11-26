---
id: OPR.0.7.0.11
slice: 11-enumeration-e2e
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Prove the enumeration end to end: enumerate ethyl and n-propyl onto TS1a_n and TS1a_x and run each (R x pathway x engine) unit through run_ts_with_fallback on GFN2 then UMA, gating the mechanics and reporting dG dagger per R, stalls and time lost."
depends_on: [OPR.0.7.0.4, OPR.0.7.0.6, OPR.0.7.0.10]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_v070_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 enumeration E2E (G7)

## Intent

The first real run of the v0.7.0 path: enumerated candidates through the fallback runner on both
engines, with the mechanics gated and the chemistry reported (mission G7, R6, R7, HF-3; US-010).

Context the builder needs:
- **Gate to start:** mission HF-3 holds the exo units' numbers (core displacement, healthy wall,
  peak RSS, worst-case bound). If HF-3's table is empty or any exo unit failed, stop and report
  (the endo-only fallback of R25 is the lead's call).
- **Units:** 2 R × 2 pathways × 2 engines = 8 units, one per command, GFN2 first, then UMA. Each
  unit: `enumerate_candidates` on `v070_enumeration.yaml` (pure), `run_ts_with_fallback` for the
  pathway (`max_pre_relax_timeouts=2`, orientation centre C7, R18 ensemble sizes), the reactants
  through the species runner (the derived `reactant_key`), and a **second pass in the same store**
  (0 rows, 0 engine calls, equal `FallbackRecord` and ensemble). Then `score_selectivity` per
  (R, engine) over the two pathways' ensembles, run in its own small command after both units.
- **Gates per unit:** candidate `ok`; charge 0 / multiplicity 1; graft RMSD <= 0.15 Å, 0 contacts;
  the G3 invariant; `chosen` at rank 1; Σw = 1 within 1e-12; every member's face == the pathway's
  expected face; zero `engine_error` and `face_mismatch` exclusions; the second pass all hits.
- **Reported, not gated:** ΔG‡ (when reactants computed), ΔΔG‡ per R and engine, members,
  `orientation_mismatch` count, stall count, `stall_cap_reached_bool`, time lost to stalls, wall,
  user+sys CPU, peak RSS, `load1` at each timeout.
- **Writes:** a `RunRecord` JSON per unit and the candidate JSON in
  `tests/candidate_outputs/v0.7.0/` (names `v070_enum_<R>_<pathway>_<engine>.json`).
- **E2E test files:** `tests/e2e/test_v070_enumeration.py` (parametrised by R, pathway, engine;
  skips count as failures under `ETA_RXNCAT_ACCEPTANCE=1`); `tests/e2e/v070.py` helpers.
- **Timeout sizing (HF3-BOUND):** each unit command runs under `timeout 5400` (1.5 × 1170 s healthy
  maximum + 3 × 1200 s, R7's cap). The scoring commands use `timeout 3600`. A command timeout is
  stop-and-report with its output. HF-3's healthy walls per unit are the reference: 234/1170 s GFN2
  and 737/476 s UMA (ethyl/n-propyl exo); endo from v0.6.0 HF-14.
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
- **Heavy runs (mission §5 "Heavy-run rule", normative):** before each engine/GPU command, a
  blocking host check in its own call or an exiting loop (never echo-then-run), output kept in the
  proof: `nvidia-smi` no compute process; `MemAvailable` >= 12 GiB; `ps`: no other eta
  E2E/pytest/xtb and no non-niced (nice < 10) process of any rig using >= 100 % CPU or >= 2 GiB RSS.
  One engine and one unit per command, `timeout 3600`, from a scratch cwd (never the repo root:
  geomeTRIC writes `HT.v_*.txt` into the cwd until slice 06 lands). Env asserted in the proof:
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`, `ETA_RXNCAT_ACCEPTANCE=1`,
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Honour any quiet-host hold the lead announces.
- **Candidate rule:** novel outputs go to `tests/candidate_outputs/v0.7.0/` only, in a
  candidate-only commit (`git show --stat` of it in the proof); never promote; never read a
  candidate back as an input; only TJ promotes at Phase 3.

## 1. The Confidence Mandate

**Score: 9/10.** Inputs are pinned offline (slice 10), the runner is unit-tested (slice 05), and the
exo units were measured before the build (HF-3). Residual risk: a stall under load in a UMA unit,
bounded by R6/R7 and reported.

## Mini-requirements

1. HF-3 present (start gate).
2. All 8 units pass every gate above; the host check and env are in the proof for each.
3. The second pass of each unit: 0 rows, 0 engine calls, equal records.
4. Reported values recorded per unit, including stalls and time lost.
5. Candidates and run records in a candidate-only commit.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] `tests/e2e/test_v070_enumeration.py` + helpers.
- [ ] Run the 8 units (host check per command), then the 4 scoring commands.
- [ ] Candidate-only commit; code commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run two units at once or from the repo root; **DO NOT** grow the E2E without the lead.
- **DO NOT** gate ΔΔG‡ (Q-A3: report only).

## Proof contract

- [ ] Per unit: host check, env, wall/CPU/RSS, gates, second-pass counts.
- [ ] `git show --stat` of the candidate-only commit.
- [ ] Required checks exit 0.

## Source material

- Mission G7, R6, R7, R25, HF-1..HF-3; slice 10 inputs.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.4, OPR.0.7.0.6, OPR.0.7.0.10.
