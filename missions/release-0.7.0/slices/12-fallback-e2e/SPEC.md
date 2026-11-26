---
id: OPR.0.7.0.12
slice: 12-fallback-e2e
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Prove the fallback end to end on GFN2: a rank-1 template refused at graft time and a rank-1 seed refused by the pathway face each fall through to rank 2, which yields the ensemble, with rank 1's reason recorded; UMA reported once."
depends_on: [OPR.0.7.0.5, OPR.0.7.0.6, OPR.0.7.0.10]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_v070_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 fallback E2E (G8)

## Intent

Show TJ's Q-A1 B working on real engines with deterministic constructs (mission G8, R2, R4, HF-2;
US-011).

Context the builder needs:
- **Constructs (`v070_fallback.yaml`, slice 10):** graft-time — rank 1 refused `alignment_rmsd`
  (alignment on a Cp H, fit 0.888 Å); run-time — rank 1 = TS1a_x geometry in the endo node,
  `seed:face_mismatch_pathway` decided on the pre-relaxed start before any TS search.
- **Units:** GFN2 gated: one unit per construct (2 commands, `timeout 5400` each per HF3-BOUND), each with a second pass. UMA: the
  run-time construct once, reported (not gated).
- **Gates (GFN2):** the `FallbackRecord` has rank 1 `fell_through` with exactly the expected reason
  and rank 2 `chosen`; rank 2's ensemble passes G7's ensemble gates (Σw = 1, faces, zero
  `engine_error`/`face_mismatch`); the run-time construct made **no** TS-search engine calls for
  rank 1 (stage metrics); the second pass is all hits with an equal record.
- **Writes:** `tests/candidate_outputs/v0.7.0/v070_fallback_<construct>_<engine>.json` and the run
  records. Test file `tests/e2e/test_v070_fallback.py`.
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

**Score: 9/10.** Both constructs fail by contract, not by optimizer behaviour (HF-2), so the outcome
is deterministic.

## Mini-requirements

1. GFN2 graft-time construct: rank 1 `alignment_rmsd`, rank 2 chosen, gates pass.
2. GFN2 run-time construct: rank 1 `seed:face_mismatch_pathway` with 0 TS-search calls, rank 2
   chosen, gates pass.
3. Second passes all hits.
4. UMA run-time construct reported.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] `tests/e2e/test_v070_fallback.py`.
- [x] Run the GFN2 units then the UMA unit (host check per command).
- [x] Candidate-only commit; code commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** use a stretched-geometry construct (non-deterministic, F13).
- **DO NOT** run two units at once or from the repo root.

## Proof contract

- [x] Per unit: host check, env, the `FallbackRecord`, gates, second-pass counts.
- [x] `git show --stat` of the candidate-only commit.
- [x] Required checks exit 0.

## Source material

- Mission G8, R2, R4, HF-2; slice 10 inputs.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.5, OPR.0.7.0.6, OPR.0.7.0.10.
