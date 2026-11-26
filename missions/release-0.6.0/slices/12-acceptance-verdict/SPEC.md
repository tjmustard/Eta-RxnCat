---
id: OPR.0.6.0.12
slice: 12-acceptance-verdict
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "After TJ's Phase 3 promotion and bounds, run the verdict on both recipes against the promoted fixtures and bump the version to 0.6.0 only on pass."
depends_on: [OPR.0.6.0.11]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.6.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_package.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 acceptance verdict and the 0.6.0 bump (after TJ's Phase 3)

## Intent

After TJ promotes the v0.6.0 candidates, confirms the transcriptions and sets the regression bounds
at Phase 3, run the verdict on both recipes against the promoted fixtures, write `verdict` into the
acceptance record, and bump the version to 0.6.0 only on `pass`.

Context the builder needs:
- **Precondition (stop if not met):** TJ's Phase 3 answer is recorded by the lead as an R-row in the
  mission SPEC (promotion commit, promoted files with sha256 and blob id, TJ's verbatim answer, the
  bounds TJ set, the TS1a_x/TS1b_x/P1b_x confirmation). Only TJ writes `tests/fixtures/v0.6.0/`.
  Verify by file names and blob ids; never read `tests/candidate_outputs/`.
- **Pattern:** v0.5.0 slice 13 (`missions/release-0.5.0/slices/13-acceptance-verdict/SPEC.md`,
  read-only) with its rules: verdict `fail` on a default suite with a non-zero exit, failures or
  errors, or any command with a non-zero exit or a skip; `check()` recomputes it; a record without
  `verdict` refuses every README claim; `evidence.promotion` records TJ's answer, the commit and each
  file's sha256 and blob id; a record without `ETA_RXNCAT_ACCEPTANCE=1` is refused (R9).
- **Regression:** each pair × recipe against its promoted fixture with TJ's bounds (energies,
  ΔΔG‡, member counts, heavy RMSD; history excluded). Every slice 11 gate re-runs.
- **Bump** (only on `pass`): `pyproject.toml`, `src/eta_rxncat/__init__.py`,
  `tests/unit/test_package.py`, `uv.lock` to 0.6.0. README final v0.6.0 claims from the record.
- **Push is not this seat's:** the lead pushes under TJ's standing go after verdict pass + audit.
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

**Score: 9/10.** The v0.5.0 verdict slice is a working template; the only unknown is TJ's Phase 3
answer, which is a precondition, not a design question.

## Mini-requirements

1. US-012: the precondition is verified from the mission R-row and the fixture blob ids.
2. US-012: the verdict passes on both recipes against the promoted fixtures; `check()` agrees.
3. US-012: version 0.6.0 in all four places only on `pass`; README claims derived.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; verify the precondition.
- [x] Task 2: verdict code and offline tests.
- [x] Task 3: host-checked verdict runs (GFN2, then UMA); record.
- [x] Task 4: bump and README on pass; required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** start without the Phase 3 R-row; **DO NOT** write `tests/fixtures/`.
- **DO NOT** bump on anything but `pass`; **DO NOT** push or tag.
- **DO NOT** run heavy commands without the blocking host check, or overlapping.

## Proof contract

- [x] Verdict `pass` in `docs/prd/v0.6.0/ACCEPTANCE_RESULT.json`; `check()` passes; outcomes with
      exit codes and skip counts, each heavy run behind a recorded host check.
- [x] Version 0.6.0 in the four files; required checks exit 0.

## Source material

- Mission US-012, R6, R9, R10; slice 11 record; v0.5.0 slice 13 and its code.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

11 and TJ's Phase 3 (R-row).
