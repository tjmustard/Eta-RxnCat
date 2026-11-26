---
id: OPR.0.7.0.13
slice: 13-review-bundle-and-record
mission: release-0.7.0
status: done
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Bundle every v0.7.0 E2E run for TJ's visual audit, gate the real bundle's hygiene and frames, repeat the M12 smoke on it, write the acceptance record from the evidence run records, and send TJ the Phase 3 row."
depends_on: [OPR.0.7.0.9, OPR.0.7.0.11, OPR.0.7.0.12]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", docs/prd/v0.7.0/ACCEPTANCE_RESULT.json, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_acceptance_record_v070.py], [uv, run, pytest, tests/e2e/test_review_v070_helpers.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 review bundle for the real runs, acceptance record and TJ's Phase 3 audit

## Intent

Put every enumerated TS and optimization in front of TJ in the bundle he asked for, and record what
passed (mission G13, R15, R17, R18, R20, R34; US-012, US-013). TJ's visual audit is the Phase 3
gate. Replan 6 (R34) wrote the multi-store bundle, the M10 gate, the fresh-output rule, the
0-engine-call count, the M12 browsers and the Phase 3 packet into this contract.

Context the builder needs:
- **Inputs (read-only; never write to them):** slice 11's store
  `~/.hacf/eta-rxncat-hacf/evidence/v070-slice11/v070_enum.sqlite` and its `records/` (8 unit
  records; the 4 `v070_enum_<R>_selectivity_<engine>.runrecord.json` records cover all 8 runs), and
  slice 12's **three** fresh stores, one per unit,
  `~/.hacf/eta-rxncat-hacf/evidence/v070-slice12/v070_fallback_<construct>_<engine>.sqlite` for
  `graft_time`/xtb, `run_time`/xtb and `run_time`/uma, each with its own run records (store and
  record names as slice 12's proof gives them). **Four stores** in all. No row is copied between
  stores; no store is merged.
- **One bundle over four stores, no `src/` change (R34):** runs in different stores share a
  candidate, pathway and engine (`ethyl|endo|<xtb>` is in slice 11's store and in both slice 12 GFN2
  stores), and `RunData` ids are unique per document, so no single `RunData` can hold every run.
  The bundle is therefore one folder with one entry page:
  - `<root>/<sub>/` is one sub-bundle per bundled (record, store) pair, written by the real
    `eta-rxncat review-bundle --record <r> --store <s> --out <root>/<sub>` (unchanged CLI and
    writer; each sub-bundle keeps its own `index.html`, `run_data.json`, `assets/`, `MANIFEST.sha256`).
    `<sub>` is the record's file stem. The bundled records are slice 11's 4 selectivity records
    (store `v070_enum.sqlite`) and each slice 12 unit's record (its own store): 7 sub-bundles; a
    record whose every run equals (`==`) a run of an already bundled record from
    the same store is listed in the proof as covered, not bundled again.
  - `<root>/index.html` is written by the harness (Python, static, no script, the same CSP meta as
    `review.bundle.CONTENT_SECURITY_POLICY`, imported, not copied): one row per sub-bundle with a
    relative link `<sub>/index.html`, its source slice, record and store **file names** (never a
    path), its unit ids, mechanics-gate pass/fail counts, the trajectories' `decimation_stride` and
    `n_frames_total`, and its byte size; the total size at the foot. This page states the decimation
    without JS (R17, R18).
  - `<root>/MANIFEST.sha256` lists every other file of the tree (`<sha256>  <relative path>`, sorted,
    as `sha256sum -c` reads it, sub-bundle manifests included).
  - Code: `tests/e2e/review_v070.py` (harness) and `tests/e2e/test_review_v070.py` (the E2E,
    acceptance-gated), plus `tests/e2e/test_review_v070_helpers.py` (runs in the normal suite, no
    engine, no acceptance env): coverage, M10, fresh-output, index and manifest checks on stub
    stores/records built in `tmp_path`, each with a failing case. Extend `tests/e2e/v070.py` helpers
    (e.g. `counted_engine_calls` with no recipe); do not fork a second copy.
- **Coverage gate, per store (four stores):** for each store, the set of runs across the records
  bundled against it equals the set of runs in every run record written for that store (slice 11's
  store: 8; each slice 12 store: its one unit); every record is bundled against its own store only,
  and every store has at least one sub-bundle; no run is
  bundled twice in one sub-bundle; every sub-bundle's `run_data.json` has one candidate entry per run
  of its record. Counts in the proof.
- **0 engine calls, all cache hits (gap 4):** the harness calls `eta_rxncat.cli.main([...])`
  in-process inside the `Engine.evaluate` counter (slice 11's method); the gate is 0 calls over the
  whole bundle build, each store's row count unchanged before/after, and **no** `missing` entry
  (trajectory, frequency or species row) in any sub-bundle. Stage metrics and counts in the proof.
- **Fresh output, refuse not wipe (gap 3):** the scratch root
  `~/.hacf/eta-rxncat-hacf/evidence/v070-slice13/review/` must not exist or be empty, and so must
  `tests/candidate_outputs/v0.7.0/review/`; either one non-empty stops the run with a one-line
  error. Nothing is deleted, wiped or overwritten by the harness. Each sub-bundle's `--out` is a new
  directory (the CLI already refuses a non-empty one, `BundleError`, exit 1; the helper test pins it).
- **Build, gate, then copy:** the bundle is built and gated in the scratch root; only after every gate
  passes does the harness copy the tree byte for byte into `tests/candidate_outputs/v0.7.0/review/`
  and check the bytes it wrote against the scratch `MANIFEST.sha256` at write time. Gates and M12
  run on the scratch tree; no seat opens, lists or reads `tests/candidate_outputs/`. The proof
  records the root `MANIFEST.sha256`'s own sha256 (scratch and copy are the same bytes).
- **Real-bundle gates (G13), on the files as written:** root and every sub `MANIFEST.sha256` verify
  (`sha256sum -c`, exit 0); each sub-bundle <= 25 000 000 bytes (R18's ceiling is the writer's unit);
  the total is reported on the root page and in the proof, not gated; scans on every file: no
  absolute path, `$HOME`, username or hostname (R15), no network reference (`http:`, `https:`,
  `//` hosts, `ws:`), sink scan clean (R14's list), CSP meta on every HTML page; **every trajectory
  has frames** (`status: stored`, `frames` non-empty; stores are forward-only, F20); in each
  sub-bundle the embedded `run-data` bytes equal `run_data.json`.
- **M10 stop (gap 2):** read `decimation_stride` from each sub-bundle's **`run_data.json` file**
  (not the in-memory `RunData`). Any trajectory with `kind == "ts_search"` at stride > 2 is the M10
  stop-and-report: the test fails with a message starting `STOP AND REPORT: M10`, naming the
  sub-bundle, trajectory id, stride and `n_frames_total`; the builder stops and reports to the lead.
  Never raise the byte budget, re-split or drop a run to pass it. Strides of every trajectory kind are
  in the proof. The helper test feeds a stub `run_data.json` with a stride-3 `ts_search` and expects
  the stop; stride 2 passes.
- **M12 repeat** on the scratch tree from `file://`, starting at the root `index.html` (each link
  opens its sub-bundle): each TS's mode animates, each trajectory plays, the index links work, no
  console error, no network request; screenshots, console and network logs in the proof. Gate
  browsers: installed Chrome and Playwright Firefox, both headless as in slice 09 (its driver is in
  `slices/09-view-components/proof/m12/`). A Mozilla **release** Firefox run is **optional** (TJ's
  call, not a gate); if not run, the proof says so.
- **Acceptance record:** `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`, derived, never hand-typed, from
  the **evidence** run records, the slice 11/12 proof tables and the scratch bundle's manifest:
  never from `tests/candidate_outputs/` (same bytes, but a candidate is never read back as input).
  Per G7 unit and G8 construct: the gates and reported values; suite counts and skips; the bundle
  path `tests/candidate_outputs/v0.7.0/review/` and its root MANIFEST sha256; stall counts and time
  lost. Writer `tests/e2e/acceptance_record_v070.py` with its own unit test
  `tests/e2e/test_acceptance_record_v070.py`.
- **Phase 3 row (gap 6):** the builder drafts it in the proof; the lead sends it to
  `advisor-lead@kernel` tagged `question-for-tj` (never to `tjmustard@external`). It names the
  bundle path; how to open it (double-click `review/index.html`, then each row's link); what to check
  (each TS has exactly one imaginary mode and it moves the forming bonds; each optimization path is
  sensible; R sits anti to the diene; fallbacks read right); that only he promotes; and the packet:
  - `orientation_mismatch`: 3-7 exclusions per unit (reported, not gated);
  - one `gate_failed:forming_overlap` (ethyl endo, GFN2);
  - one UMA stall (ethyl exo, 600 s, cap not reached);
  - dG‡ is the **ensemble** barrier (G_pathway − G_reactants), not the seed's;
  - ddG‡ ethyl 3.93 / 4.57, n-propyl 4.23 / 4.97 kcal/mol (GFN2 / UMA), endo major;
  - slice 12's fallback results per construct and engine, copied from slice 12's proof with the
    record names, in the shape of lead ruling A (`qitem-20261126124248-0826c9cd`):
    **graft time** (GFN2): the `GraftRecord` of declared rank-1 `TS1a_n_cp_h` refused with exactly
    `alignment_rmsd`, declared rank-2 `TS1a_n` grafted `ok`, and the `FallbackRecord` holds **one**
    attempt (`TS1a_n__ethyl`, renumbered rank 1, `chosen`), so no fall-through appears in it;
    **run time** (GFN2 gated, UMA reported): rank 1 `fell_through` with `seed:face_mismatch_pathway`,
    rank 2 `chosen`; for each, the chosen template's ensemble gates.
  Values in the row are taken from the records/proofs, never retyped from this list.
- **Proof naming (gap 7):** the builder's proof is `proof/13-execute.md` with artifact type
  `execute` (or `evidence`), never a QA verdict; the audit writes the QA verdict.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (slices 11-13 write candidates; they never read them back as input).
  - The `eta_rxncat_species_runner` description is at 1979/2000: compress before adding (cap 2000).
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
- **Commands and timeouts (gap 8):** this slice runs **no engine unit**: every command, including
  the bundle E2E and M12, uses `timeout 3600` (the 5400 s bound is for slice 11/12 unit commands
  only, R7). The bundle E2E reads four stores but loads no engine; it still runs after a blocking
  host check in its own call (mission §5 "Heavy-run rule": no other eta E2E/pytest/xtb, `MemAvailable`
  >= 12 GiB; the heavy-process count includes every rig's and user's processes, excluding none
  silently), from a scratch cwd, with `ETA_RXNCAT_ACCEPTANCE=1` and
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` asserted in the proof. Honour any quiet-host hold
  the lead announces.
- **Candidate rule:** novel outputs go to `tests/candidate_outputs/v0.7.0/` only, in a
  candidate-only commit (`git show --stat` of it in the proof); never promote; never read a
  candidate back as an input; only TJ promotes at Phase 3.

## 1. The Confidence Mandate

**Score: 9/10.** Every component is built and tested; this slice composes sub-bundles with the
unchanged CLI, gates, records and drafts the row, with no `src/` change. Residual risks: the real
data rendering differently from the stub (the M12 repeat catches it) and an M10 stride > 2 on the
real trajectories (a stop-and-report, not a fix in this slice).

## Mini-requirements

1. One bundle (root page + manifest) covers every slice 11/12 run across all four stores, one
   sub-bundle per bundled record, no row copied between stores; the build made 0 engine calls and
   no store gained a row.
2. Both output roots were fresh (refused if not, never wiped).
3. All real-bundle gates pass, M10 included (stride <= 2 on every `ts_search`, read from the file).
4. M12 on the real bundle in Chrome and Playwright Firefox, evidence kept; release Firefox optional.
5. The acceptance record is derived from evidence records (not candidates) and its writer is tested.
6. The Phase 3 row text, with the packet, is in `proof/13-execute.md` for the lead.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] Harness + helper tests (coverage, M10, fresh output, root index, manifest) with failing cases.
- [x] Host check; build the bundle in scratch; run the gates; copy to candidates; M12 repeat.
- [x] Record writer + test; write the record.
- [x] Code commit; candidate-only commit (bundle); record + progress commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run an engine for the bundle; **DO NOT** promote; **DO NOT** edit the bundle by hand.
- **DO NOT** change `src/` (no CLI flag, no writer change), copy rows between stores, or merge
  stores.
- **DO NOT** wipe or overwrite a non-empty output directory; refuse.
- **DO NOT** lift the trajectory budget or drop a run to pass M10 or the size gate.

## Proof contract

- [x] `proof/13-execute.md` (type `execute`/`evidence`): coverage table, engine-call and row counts,
  gate outputs (manifests, sizes, scans, frames, byte equality), strides per sub-bundle.
- [x] M12 evidence on the real bundle (both gate browsers; release Firefox run or "not run").
- [x] `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` and its writer test.
- [x] Phase 3 row draft with the packet.
- [x] Required checks exit 0.

## Source material

- Mission G13, R14, R15, R17, R18, R20, R34; slices 08, 09, 11, 12.

## Intent visual

The bundle as built in slices 08-09, one sub-bundle per record under one root page; TJ reviews it.

## Status

- compiled

## Dependencies

- OPR.0.7.0.9, OPR.0.7.0.11, OPR.0.7.0.12. Slice 14 waits for TJ's Phase 3.
