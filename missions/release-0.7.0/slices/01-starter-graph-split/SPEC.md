---
id: OPR.0.7.0.1
slice: 01-starter-graph-split
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Unpack the v0.7.0 starter as reference with its DV register, fix the v0.6.0 README 'unit weights' claim with its helper, and split the graph into selectivity, enumerator and review nodes by the mission's R19 sequence."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["docs/prd/v0.7.0/**", docs/prd/PLAN_DISCREPANCIES.md, README.md, tests/unit/test_identity.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 starter, DV register, README wording and the graph split

## Intent

Open v0.7.0's bookkeeping before any code: the starter zip lands as reference only, the DV register
records where eta departs from it, the one v0.6.0 README claim that reads wrong is corrected
together with the claims helper that pins it, and the ledger gets room for three new nodes without
a cycle (mission G9, R19, R27, US-001, US-002, US-015).

Context the builder needs:
- **Base:** `main` = tag `v0.6.0` = `a8b8e71`. This is the first v0.7.0 slice; nothing before it
  writes `src/` or the graph.
- **Starter:** `PRDs/Eta-RxnCat-v0.7.0.zip` (sha256 `ad7b7616…f0b25`, read-only) unpacks
  byte-identical to `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/` (38 files) with
  `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` = `exclude = ["*"]` (without it the pre-commit hook lints the starter
  and refuses the commit). No `docs/prd/v0.7.0/.ruff.toml`. Reference only: copy no starter code.
- **Replan 1 (mission R29, lead rulings 1-3):**
  - *Ruff gate path.* A gate at `docs/prd/v0.7.0/.ruff.toml` does not stop the hook: the starter's own
    `pyproject.toml` `[tool.ruff]` is nearer its files. The builder measured the hook's command
    (`.agents/scripts/pre-commit:54`) `find docs/prd/v0.7.0 -name '*.py' -print0 | xargs -0 .venv/bin/ruff check --force-exclude --` → 69 errors and
    `format --check` → 13 files with the parent gate; with the gate at `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` the
    check, the format check and `ruff check .` all exit 0. v0.1.0–v0.6.0 all keep it at
    `docs/prd/vX/Eta-RxnCat-vX/.ruff.toml` (`git ls-files`). The gate lives there only, and the proof
    adds the hook-style checks, because `uv run ruff check .` cannot catch this.
  - *Import scan scope.* `tests/e2e/**` stays in species_runner's globs but imports selectivity
    modules (`tests/e2e/t4_flexible.py:45,55-56`, `test_t4_helpers.py:22`,
    `test_t4_mapped_helpers.py:12`), and `tests/unit/orchestrator/**` holds selectivity tests (the
    overlap is already recorded). The edge rule and the stop-and-report apply to imports in `src/`
    files only; test-file imports are listed in the proof's import scan and add no edge. Globs
    unchanged.
  - *Plan-vs-code rows.* `docs/prd/PLAN_DISCREPANCIES.md` is one row per plan-vs-zip hunk and its
    v0.7.0 zip row already reads "identical to PRDs/"; the mission's four "Plan-vs-code rows" bullets
    fit no column. They are appended verbatim as a short "Plan-vs-code (v0.7.0)" section under the
    table; the table, its hashes and the PD ids are unchanged.
- **DV register:** `docs/prd/v0.7.0/DISCREPANCIES.md` with DV-01…DV-10 exactly as the mission's
  "Starter discrepancies" table, plus the mission's four "Plan-vs-code rows" bullets (same section)
  appended verbatim as a "Plan-vs-code (v0.7.0)" section under the table of the existing
  `docs/prd/PLAN_DISCREPANCIES.md` (R29; table, hashes and PD ids unchanged).
- **README wording (R27):** in `README.md` the v0.6.0 claim "…with unit weights, the seed's face…"
  becomes "…with weights summing to 1, the seed's face…". The same sentence lives in the claims
  helper in `tests/unit/test_identity.py` (around line 1273, the `_v060_flexible` claim); change
  both in the same commit, because the helper compares the README text. The v0.6.0 docs commit
  `a8b8e71` restored the old wording precisely because one was changed without the other.
- **Graph split (normative):** run the mission's "Graph split (slice 01)" steps 1-10 in order, with
  `python3 .agents/scripts/hyper_ledger.py` (ensure-node / set-edges / apply-review) and the single
  updater run. Final globs and edges are in the mission; do not invent others. The import scan of
  step 6 is attached to the proof; an import **in a `src/` file** that contradicts the edges is
  stop-and-report. Test-file imports (e.g. `tests/e2e/**` and `tests/unit/orchestrator/**` into
  selectivity modules) are listed in the scan and add no edge (R29).
  `ensure-node --from-spec` is not used (it replaces node files). The ledger guard: `--files`
  replaces a node's whole glob list, so pass the complete list each time.
- **Descriptions:** core (2000) and species_runner (1999) are compressed to <= 1800 chars; the new
  nodes get <= 1800-char descriptions naming their modules and v0.7.0 role. Everything is written by
  `--description-file`; `apply-review` keeps its 2000-char cap.
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

**Score: 9/10.** Every command, glob and edge is given, and the import facts were read at the base
(only `orchestrator/__init__.py` re-exports selectivity/ts_ensemble; no species-side `src/` module
imports them; `ts_ensemble.py` imports mapping, engines and thermo). Replan 1 (R29) settles the three
points the builder's first run hit with measured evidence: the ruff gate path (hook check 0 errors
with the gate inside the starter dir), the import scan's `src/`-only edge rule, and the
PLAN_DISCREPANCIES placement. Residual risk: the ledger tool's
handling of `--allow-shared` for a file under another node's glob; the union-count check catches any
loss, and a refusal is stop-and-report, not a workaround.

## Mini-requirements

1. US-001: the 38 starter files are byte-identical to the zip (a sha256 listing in the proof), and
   `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml` (`exclude = ["*"]`, the only gate file) excludes them: the hook-style
   `find docs/prd/v0.7.0 -name '*.py' -print0 | xargs -0 .venv/bin/ruff check --force-exclude --` and
   `find docs/prd/v0.7.0 -name '*.py' -print0 | xargs -0 .venv/bin/ruff format --check --force-exclude --` both exit 0 (R29).
2. DV-01…DV-10 are present with the mission's text, and the four plan-vs-code bullets sit verbatim in
   a "Plan-vs-code (v0.7.0)" section under the PLAN_DISCREPANCIES table, the table unchanged (R29).
3. US-015: README and `tests/unit/test_identity.py` both say "weights summing to 1"; the identity
   test passes.
4. US-002: nodes `eta_rxncat_selectivity`, `eta_rxncat_enumerator`, `eta_rxncat_review` exist with
   the mission's globs, edges and `associated_file`s; species_runner has the narrowed globs.
5. The union of matched files after equals the union before plus only this slice's new files; no
   file is unowned; both tables are in the proof.
6. `hyper_ledger.py validate` passes; `set-edges` reported no cycle; descriptions <= 1800 chars.
7. The updater ran exactly once.

## 3. Implementation Plan (Task List)

- [x] `python3 .agents/scripts/hyper_codegraph.py index` → `index: ok`.
- [x] Unpack the zip to `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/`; write `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/.ruff.toml`; run the
      two hook-style ruff commands (exit 0); sha256 listing.
- [x] Write `DISCREPANCIES.md` (DV-01…DV-10) and the "Plan-vs-code (v0.7.0)" section.
- [x] Change the README sentence and the `test_identity.py` claim together; run that test.
- [x] Graph split steps 1-5 (counts before, narrow species_runner, three ensure-node).
- [x] Step 6: import scan, then set-edges.
- [x] Steps 7-8: descriptions, apply-review.
- [x] Commit; step 9: index + updater once; step 10: counts after, validate.

## 4. The Negative Space (Constraints)

- **DO NOT** edit `architecture.yml` by hand, use `--from-spec`, or run the updater twice.
- **DO NOT** move or rename any source or test file in this slice.
- **DO NOT** add an edge from species_runner into selectivity, or have `mapping/__init__.py`
  re-export the enumerator.
- **DO NOT** copy starter code into `src/`.

## Proof contract

- [ ] The starter sha256 listing equals the zip's; `uv run ruff check .` exits 0 with the starter
      present; `find docs/prd/v0.7.0 -name '*.py' -print0 | xargs -0 .venv/bin/ruff check --force-exclude --` and
      `find docs/prd/v0.7.0 -name '*.py' -print0 | xargs -0 .venv/bin/ruff format --check --force-exclude --` exit 0 (R29).
- [ ] `uv run pytest tests/unit/test_identity.py -q` passes with the new wording.
- [ ] Before/after ledger tables (per-node globs, matched files, union) and the import scan
      (`src/` imports checked against the edges; test-file imports listed, no edge; R29).
- [ ] `python3 .agents/scripts/hyper_ledger.py validate` exits 0; required checks exit 0.

## Source material

- Mission §5 "Graph split (slice 01)", "Starter discrepancies", R19, R27; `PRDs/Eta-RxnCat-v0.7.0.zip`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- The v0.6.0 release sha `a8b8e71` (base). Every later slice depends on this one.
