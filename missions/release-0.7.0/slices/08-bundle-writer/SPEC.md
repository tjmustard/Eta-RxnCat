---
id: OPR.0.7.0.8
slice: 08-bundle-writer
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Write the static offline review bundle from RunData with a JS-free static summary, a CSP, the canonical embedded JSON, vendored 3Dmol.js 2.5.5 verified against npm, and the eta-rxncat review-bundle command, with Python-side scans."
depends_on: [OPR.0.7.0.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_review
parent: null
hacf_touches: ["src/eta_rxncat/review/**", "tests/unit/review/**", src/eta_rxncat/cli.py, "tests/unit/cli/**", pyproject.toml, uv.lock, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/review, tests/unit/cli]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 review bundle writer, CLI and vendored 3Dmol.js

## Intent

`write_review_bundle(run_data, out_dir)` writes a folder TJ opens with a double-click: no server, no
network, deterministic bytes (mission G11, G12, R14, R15, R17, R18, R20; US-009). This slice is the
Python side; slice 09 writes `eta-view.js`.

Context the builder needs:
- **Layout:** `index.html` (one page; candidate pages by hash route `#c/<candidate_id>`),
  `run_data.json`, `assets/eta-view.js` (slice 09; this slice ships a placeholder that only renders
  "components pending" via `textContent`), `assets/3Dmol-min.js`, `assets/LICENSE-3Dmol.txt`,
  `MANIFEST.sha256` (sorted, every file but itself).
- **Embedded data:** `<script type="application/json" id="run-data">` + the **same bytes** as
  `run_data.json`, both from `canonical_run_data_json` (slice 07). A test asserts byte equality.
  Classic `<script src>` only (no modules); no `fetch`.
- **Static summary (R17):** Python renders, with `html.escape` on every interpolated **text** (the
  summary is HTML text, not data), per TS: `n_imaginary`, the frequencies (imaginary in red), the
  gates and a loud banner when `n_imaginary != 1` on a TS or >= 1 on a minimum; and the index table
  with gate pass/fail. It reads only `RunData`.
- **CSP meta (R14):** `default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'none'`; slice 09's M12 may add only what 3Dmol needs, recorded.
  Inline scripts: none (the JSON element is data, not script).
- **3Dmol (R20, HF-5):** re-download `https://registry.npmjs.org/3dmol/-/3dmol-2.5.5.tgz` into a
  fresh dir under TMPDIR (never executed), verify its sha512 against `npm view 3dmol@2.5.5
  dist.integrity` (`sha512-kqNH…Cdw==`, mission HF-5), vendor `package/build/3Dmol-min.js` as
  `src/eta_rxncat/review/assets/3Dmol-min.js` (sha256 `f7cc7892…8016`) and `package/LICENSE` as
  `LICENSE-3Dmol.txt`, and add `src/eta_rxncat/review/assets/SOURCES.md` with URL, version, date,
  both hashes, the licence banner inventory (GLmol dual MIT/LGPL3 — eta elects MIT; three.js MIT;
  jQuery MIT; iobuffer, netcdfjs, upng-js MIT; pako MIT AND Zlib). A unit test pins the sha256 and
  checks the licence file. `pyproject.toml` package data includes `review/assets/*` and
  `review/schema/*` (scaffold), and a wheel-build test lists them.
- **CLI:** `eta-rxncat review-bundle --record <run_record.json> --store <path> --out <dir>` =
  `export_run_data` then `write_review_bundle`. Exit 0 on success; a typed error message otherwise.
- **Scans (Python tests on the written bundle from a stub run):** no `http://`/`https://` in any
  `src=`/`href=` (anchors `#…` allowed); no absolute path, `$HOME`, username (`getpass.getuser()`)
  or hostname (`socket.gethostname()`) in any file; the JS sink scan (R14) over every `.js` file
  eta wrote (not 3Dmol); byte-identical across two writes.
- **M10 (stop-and-report):** dry-export a bundle from slice 06's GFN2 smoke store scaled to the E2E
  (2 R × 2 pathways × 2 engines + G8 runs; extrapolate from the per-ensemble size) and record bytes.
  Set the exporter's byte budget so the bundle stays <= 25 MB; if decimation would drop below
  every-other frame on TS searches, stop and report.
- ruff ignores `.js`; mypy is Python only.
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

**Score: 9/10.** The asset is pinned and verified (HF-5); everything here is Python-testable. Residual
risk: bundle size, measured in M10 with a stop-and-report gate.

## Mini-requirements

1. The layout above; `MANIFEST.sha256` verifies.
2. Embedded JSON bytes == `run_data.json` bytes.
3. Static summary shows a banner for a stub TS with 2 imaginary modes and for one with 0.
4. CSP meta present with the stated policy.
5. 3Dmol sha256 pinned; integrity verified in the proof; licence and SOURCES rows present; wheel
   includes the assets.
6. Scans clean (network refs, host data, sinks); two writes byte-identical.
7. CLI round trip on a stub record exits 0 and writes the bundle.
8. M10 numbers and the chosen byte budget in the proof.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] Vendor 3Dmol (verify, hashes, SOURCES.md, licence).
- [x] `review/bundle.py` (layout, embedded JSON, static summary, CSP, manifest).
- [x] `cli.py` `review-bundle`; `pyproject.toml` package data.
- [x] Tests `tests/unit/review/test_bundle.py`, `test_bundle_scans.py`, `test_assets.py`,
      `tests/unit/cli/test_review_bundle_cli.py`.
- [x] M10 dry export; proof.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** load anything over the network from the page, add a server, `fetch()` or ES modules.
- **DO NOT** vendor any other asset, or an unverified 3Dmol; **DO NOT** add a JS toolchain.
- **DO NOT** put messages, timestamps or host data in any file.

## Proof contract

- [ ] Integrity check output (npm sha512 == tarball; vendored sha256).
- [ ] `uv run pytest tests/unit/review tests/unit/cli -q` passes (requirements 1-7).
- [ ] M10 table.
- [ ] Required checks exit 0.

## Source material

- Mission G11, G12, R14, R15, R17, R18, R20, HF-5; evidence `m9-3dmol-2.5.5/`.

## Intent visual

The page layout: an index table of candidates with gate badges; per candidate a static summary block
above the component panels (molecule + mode, trajectory player + energy plot).

## Status

- compiled

## Dependencies

- OPR.0.7.0.7.
