---
id: OPR.0.6.0.11
slice: 11-acceptance-record
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Assemble the v0.6.0 acceptance record from real per-check outcomes with pending states for TJ, measure run-to-run reproducibility for the Phase 3 bounds, and derive the README claims."
depends_on: [OPR.0.6.0.10, OPR.0.6.0.13, OPR.0.6.0.14]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.6.0/ACCEPTANCE_RESULT.json, README.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_acceptance_record_v060.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 acceptance record (pre-promotion) and README derivation

## Intent

Assemble `docs/prd/v0.6.0/ACCEPTANCE_RESULT.json` from real per-check outcomes of every v0.6.0
check — with pending states for what waits on TJ — measure run-to-run reproducibility for the Phase 3
bounds, and derive the README v0.6.0 claims from the record. This slice's PASS does not depend on TJ
acting first; the lead then files TJ's Phase 3 row.

Context the builder needs:
- **Pattern:** v0.5.0 slice 12 (`missions/release-0.5.0/slices/12-acceptance-record/SPEC.md`,
  read-only) and its code: `tests/e2e/acceptance.py`, `acceptance_record_v050.py`,
  `test_accept_v050.py`, `test_acceptance_record_v050.py`, `regression.py`, `gated_outcome`
  (`pending_*` fails under `ETA_RXNCAT_ACCEPTANCE=1`; a missing fragment is `missing`). New:
  `tests/e2e/acceptance_record_v060.py`, `test_accept_v060.py`, `test_acceptance_record_v060.py`.
- **Checks in the record** (state ∈ `pass` / `fail` / `pending_promotion` / `pending_confirmation` /
  `skipped` with reason / `missing`):
  - per pair × recipe (four): every slice 09/10 gate (seeds, endo major, ΔΔG‡ > 0.5, UMA window,
    zero `engine_error`, zero `face_mismatch`, endo regression vs v0.5.0 fixtures, G6 pruning
    consistency, G7 second run);
  - per ensemble: member count, exclusions by reason, merges and flagged merges — **reported**;
    `engine_error` and `face_mismatch` counts — **gated at zero** (R1, R3);
  - unit-level proof of the Boltzmann sum (G1, G4 test outcomes by node id) — gated, since Tier 4
    ensembles are one member (HF-10);
  - transcriptions: the three sha256s (HF-1) and header-G ΔΔG (+4.273, +1.849);
  - `regression`: `pending_promotion`; `transcription_confirmation`: `pending_confirmation`;
  - `default_suite`, `commands` (exit code, skip count), `environment` (must include
    `ETA_RXNCAT_ACCEPTANCE=1` and, for xtb, `ETA_RXNCAT_XTB`; R9).
- **Reproducibility:** run each pair × recipe twice more in fresh stores (host check each; GPU one
  at a time; `timeout 3600`); record per pair × recipe the max |ΔE_TS| (Eh), |ΔΔG‡| (kcal/mol), heavy
  RMSD (Å) and member-count changes between runs and against the in-process slice 09/10 result
  (never by reading candidate files). `proposed_regression_bounds`: |ΔE| ≤ 1e-5 Eh, heavy RMSD ≤
  0.01 Å, |ΔΔG‡| ≤ 0.01 (GFN2) / 0.75 (UMA) kcal/mol (TJ's "0.75 all" read per R6), **only** if every
  measured difference is ≤ 1/10 of the bound; otherwise 10× the measured maximum, said so. The lead
  puts this block in TJ's Phase 3 row.
- **README:** v0.6.0 "Features"/"Roadmap" lines derived from the record by the existing helper (a
  claim needs its check `pass`; pending → "pending TJ"). CHANGELOG is the scribe's.
- **Slice 14's checks join this record (replan 4, R29/R30; TJ Q-RES1 B, amended to the alkyl
  series).** Add a `flexible_ensemble` block per R (ethyl, n-propyl, n-butyl) × recipe, giving
  six entries.
  - **Gated:** slice 14's gates (a)–(f): no `failed_reason`, ≥ 2 distinct members,
    |Σw − 1| ≤ 1e-12, every face the seed's, zero `face_mismatch`/`engine_error`, a second pass
    with zero rows and zero calls and an equal ensemble, and no `graft_pre_relax_timeout`.
  - **Reported:** members per R plus the non-decreasing flag, exclusions by reason, max
    `pre_relax_wall_time_s`, ΔG‡_ensemble, ΔG‡_seed, the ensemble correction, and ΔΔG‡ vs ethyl.
  - **State:** `regression` for these is `pending_promotion`, since no promoted fixture exists.
  - **Sources:** the outcomes come from re-running slice 14's E2E (one R × recipe per command,
    host-checked), never from reading its candidate files.
  - **Reproducibility:** slice 14 gets no repro runs and no proposed bounds; it is mechanics-only
    and TJ gates no number.
  - **G1/G4:** the unit-level Boltzmann proof stays gated, and slice 14 adds the E2E evidence of
    multi-member sums.
- **Continuation after the replan-4 pause (R30).** The builder paused this slice after C1
  `1273070` (record assembly and repro driver) to let slice 14 run.
  - **Range:** it resumes as a continuation. Start stays `ca983a8`, so the range will contain
    slice 14's commits.
  - **Repro runs** completed at `1273070` stay valid, because slice 14 changes no `src/` (its
    requirement 5) and does not change the Tier 4 helpers' behaviour. Re-run only a repro command
    that had not finished. If slice 14's proof shows a non-empty `src` diff, all repro runs are
    void and are redone.
  - **Audit reading:** judge slice 11 on its own commits, listed in its PROOF by sha, i.e.
    `git diff ca983a8..<end>` minus the files in slice 14's PROOF. Slice 14 was audited on its own
    range. Check that the resumed C2+ commits touch only this slice's `hacf_touches`, plus the
    record's use of slice 14's helpers.
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

**Score: 9/10.** Same shape as v0.5.0 slice 12 with fewer cases; the new parts are the per-ensemble
counts, which slices 09/10 already serialise.

## Mini-requirements

1. US-012: the record holds every check above with a real state; gated checks pass on both recipes.
2. US-012: reproducibility and `proposed_regression_bounds` recorded per the rule.
3. US-012: a record without `ETA_RXNCAT_ACCEPTANCE=1` in `environment` fails `check()` (test).
4. README claims derived from the record (test).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start.
- [x] Task 2: record assembly + `check()` + offline tests.
- [x] Task 3: host-checked acceptance runs (GFN2, then UMA) and reproducibility runs; record.
- [x] Task 4: README derivation; required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** read `tests/candidate_outputs/`; **DO NOT** write `tests/fixtures/`.
- **DO NOT** mark `regression` or `transcription_confirmation` anything but pending.
- **DO NOT** run heavy commands without the blocking host check, or overlapping.

## Proof contract

- [x] `docs/prd/v0.6.0/ACCEPTANCE_RESULT.json` committed; `check()` passes; test outcomes with exit
      codes and skip counts, each heavy run behind a recorded host check.
- [x] Required checks exit 0.

## Source material

- Mission G1–G8, R1, R3, R6, R9, R10, R29, R30, HF-1, HF-10, HF-14; v0.5.0 slice 12 and its code; slice 14.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

10, 13 (HF-13 guard), 14 (flexible-ensemble E2E; replan 4).
