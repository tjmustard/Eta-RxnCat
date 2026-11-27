---
id: OPR.0.7.1.4
slice: 04-tier-x-ts-seams
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Check the P-RFO, TS ensemble and seed fallback seams against CPU GFN2 xtb with real modules on both sides."
depends_on: [OPR.0.7.1.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_integration
parent: null
hacf_touches: ["tests/integration/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Tier X TS seams on CPU GFN2 (T-X1…T-X3)

## Intent

Check the TS seams against a real engine: P-RFO ↔ GFN2 ↔ store ↔ TS validation and thermo; the
ensemble with its sampler, constrained relax and store; and the TS seed fallback runner on a real
enumerated candidate (mission R7, R9, R32, R33; US-005).

Context the builder needs:
- **File:** `tests/integration/test_seams_ts_gfn2.py`, `pytestmark = [pytest.mark.integration,
  pytest.mark.xtb]`; recipes from the slice-01 conftest (`gfn2_stage()`), the TS recipe built the
  way `tests/e2e/t3.py` `ts_recipe` builds it (read it; rebuild literally, no import).
- **Task 2 is the measurement (stop-and-report):** run the module once under the heavy-run rule and
  record each test's wall. T-X1 > 16 s, T-X2 > 82 s or T-X3 > 160 s (2× R33) is a stop-and-report.
- **Tests (R9):**
  - **T-X1** `run_transition_state` (`orchestrator/ts.py:393`) with `PRFOOptimizer` on
    `tests/e2e/data/e2e5/xyz/TS1a_n.xyz` (the M1a spec `t3_ts1a_n_unmapped.yaml` gives charge,
    multiplicity and forming bonds; read it in place): converged, exactly 1 imaginary mode, the
    identity core passes (ADR-0047), the record round-trips, and a rerun on the same store is all
    hits (`TSRunResult.metrics[*].engine_calls == 0`) with an equal payload.
  - **T-X2** `run_ts_ensemble_detailed` (`ts_ensemble.py:345`) on the same seed with
    `TSEnsembleOptions(n_embed=1, n_perturb=1, max_research=1)`: the seed is a member, Σw within
    `1e-12`, each member on the seed's face, rerun all hits, and every non-None key in
    `run.samples` (slice 03) is a row in the store.
  - **T-X3** `run_ts_with_fallback` (`ts_fallback.py:262`) on T-O4's ethyl candidate
    (`load_v070_plan()` → `enumerate_candidates`), node `TS1a_n`, endo pathway with
    `expected_face` from the plan, 1/1/1 options, `orientation_centers` from the plan: the
    `FallbackRecord` names rank 1 with no fall-through, no `seed:seed_clash` / `seed:bond_changed:*`
    on the seed, and a rerun is all hits.
- **Run command:** the mission R2 Tier X command restricted to this file, after a separate blocking
  host check (`~/.hacf/eta-rxncat-hacf/evidence/v071-resolve/hostcheck.sh` content), under
  `timeout 600` and `/usr/bin/time -v`, from a scratch cwd; afterwards `git status --porcelain` shows
  no `HT.v_*`.
- **Seam breaks (R4; the audit commits
  `missions/release-0.7.1/slices/04-tier-x-ts-seams/seam_breaks.json`):**
  - T-X1 ⇐ `run_transition_state` skips storing the `frequency` row; and ⇐ the identity gate reads
    the wrong forming-bond order.
  - T-X2 ⇐ `relax_constrained_core` swaps the frozen-atom list for the non-core atoms.
  - T-X3 ⇐ the fallback runner drops `expected_face`.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/`.
  - The ruff format oracle is only
    `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`.
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.7.0/`, older
    missions or `PRDs/`. Plain literal `rm -f` only, and never `rm -rf` on a computed path.
  - Ledger caps (mission §5 carry-forward 7): any description word in a node at or above 1978 chars
    is compressed for first, with the before and after counts in the proof. Core gets no words.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.
- **Licence:** no new Python or JS dependency; the core stays MIT/BSD.

## 1. The Confidence Mandate

**Score: 9/10.** T-X1 and T-X2 inputs and costs are measured (M1a 7.7 s, M1b 41 s, replay equal).
Residual: T-X3 on the 24-atom candidate is estimated (≤ 80 s), measured first with a 2× stop.

## Mini-requirements

1. The measurement is in the proof; each test within 2× its R33 estimate.
2. T-X1…T-X3 pass under the Tier X command with `ETA_RXNCAT_ACCEPTANCE=1`, 0 skipped.
3. Each test's docstring names its seam break(s).
4. The default suite is green and does not collect these tests (deselected by `xtb`).

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] T-X1, T-X2, T-X3.
- [ ] Host check; measured run; required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run GPU, UMA, MACE or PySCF; CPU GFN2 only.
- **DO NOT** assert numbers across two engine runs (R7).
- **DO NOT** import `tests/e2e/t3.py` or `e2e_env.py`; rebuild recipes literally.

## Proof contract

- [ ] Host check output, the command, `/usr/bin/time -v`, and junit with T-X1…T-X3 `passed`,
  0 skipped (requirements 1-2).
- [ ] `git status --porcelain` shows no `HT.v_*`.
- [ ] Required checks exit 0 (requirements 3-4).

## Source material

- Mission R9, R32, R33, heavy-run rule; resolve evidence `m1a*`, `m1b*`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.3.
