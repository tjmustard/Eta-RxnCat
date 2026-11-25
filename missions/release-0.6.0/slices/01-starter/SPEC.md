---
id: OPR.0.6.0.1
slice: 01-starter
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Unpack the v0.6.0 starter zip byte-identical under docs/prd/v0.6.0/ as reference only, gate it off from ruff, and open the DV register with DV-01..DV-09."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["docs/prd/v0.6.0/**", docs/prd/PLAN_DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 starter (reference only) and the DV register

## Intent

Unpack the v0.6.0 starter zip byte-identical under `docs/prd/v0.6.0/` as reference only, gate it
off from ruff, and open the discrepancy register with DV-01…DV-09 so every plan-vs-zip mismatch is
logged, never followed.

Context the builder needs:
- **TJ, verbatim:** Q1 "A" (the `PRDs/` plan is authoritative, `PRDs/` read-only); Q2 "B" (the
  starter zip is reference only).
- Zip: `PRDs/Eta-RxnCat-v0.6.0.zip`, 36 files, sha256
  `0c1b1f6ebf810c8bab904f018d816bbd0d561f6055d7130aaad36509d78a88b7`. Unpack to
  `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/` exactly as v0.5.0 did (`docs/prd/v0.5.0/` is the model).
- Gate file `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/.ruff.toml` with the v0.5.0 text (a comment line
  "Not part of the v0.6.0 starter: keeps ruff (and the HACF pre-commit hook) off this verbatim
  reference copy." and `exclude = ["*"]`); without it the pre-commit hook lints the starter and
  refuses the commit. It is not a starter file; flag it in the handoff.
- DV rows: mission §5 "Starter discrepancies" DV-01…DV-09, each `open`, each citing the plan line,
  the zip path and the eta code or mission R-row. Follow `docs/prd/v0.5.0/DISCREPANCIES.md`'s
  format.
- `docs/prd/PLAN_DISCREPANCIES.md`: change only PD-010's status cell (to `logged as DV-01 in
  docs/prd/v0.6.0/DISCREPANCIES.md` or the format v0.5.0 used for its PD row); hashes unchanged.
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

**Score: 10/10.** Mechanical; the v0.5.0 slice 01 is the template. No open question.

## Mini-requirements

1. US-001: every file in the zip exists under `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/` with equal sha256
   (36/36), and nothing else is there except `.ruff.toml`.
2. US-001: `docs/prd/v0.6.0/DISCREPANCIES.md` lists DV-01…DV-09, all `open`.
3. US-001: `git diff --stat PRDs/` is empty; PD-010's status is the only change in
   `PLAN_DISCREPANCIES.md`.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start (`git rev-parse HEAD`).
- [x] Task 2: unzip into a TMPDIR scratch dir; copy the tree; per-file sha256 compare (script output
      saved in the proof).
- [x] Task 3: `.ruff.toml` gate file.
- [x] Task 4: `DISCREPANCIES.md` DV-01…DV-09; PD-010 status.
- [x] Task 5: commit; updater once (node `eta_rxncat_scaffold`).

## 4. The Negative Space (Constraints)

- **DO NOT** edit any starter file or anything under `PRDs/`.
- **DO NOT** import, run or copy starter code anywhere in `src/` or `tests/`.
- **DO NOT** change any other PD row or hash.

## Proof contract

- [ ] 36/36 sha256 matches between the zip and `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/` (command + output).
- [ ] `DISCREPANCIES.md` holds DV-01…DV-09, all open.
- [ ] `git diff --stat main -- PRDs/` empty; PD-010 the only PLAN_DISCREPANCIES change.
- [ ] Required checks (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
      `uv run pytest`) exit 0.

## Source material

- `PRDs/Eta-RxnCat-v0.6.0.zip`; `PRDs/Eta-RxnCat_Living_Master_Plan.md` l.49–51.
- `docs/prd/v0.5.0/` (model); mission §5 "Starter discrepancies".

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

None.
