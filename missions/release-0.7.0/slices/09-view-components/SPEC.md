---
id: OPR.0.7.0.9
slice: 09-view-components
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Write eta-view.js, five reusable framework-free components that render only RunData, and record the M12 browser smoke on stub run-data with known answers in Chrome and Firefox from file://."
depends_on: [OPR.0.7.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_review
parent: null
hacf_touches: ["src/eta_rxncat/review/**", "tests/unit/review/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/review]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 view components and the M12 browser smoke

## Intent

The reusable components every later view composes (TJ's UI track; mission G12, R14, R16, R17;
US-009): `moleculeViewer`, `modeAnimator`, `trajectoryPlayer`, `energyPlot`, `candidateTable`.

Context the builder needs:
- **File:** `src/eta_rxncat/review/assets/eta-view.js`, MIT header naming eta-rxncat, plain ES2017,
  one classic script defining `window.EtaView`. No framework, no build, no npm, no transpiler.
- **Signature:** each component is `(element, runData, id) -> {update, destroy}`; reads only
  `runData` (parsed once from `#run-data` by a tiny `EtaView.load()` that checks `schema_version`
  first and renders "unsupported run-data version N" via `textContent` otherwise); keeps no global
  state.
- **Components:** `moleculeViewer` (3Dmol viewer of one species/frame); `modeAnimator` (3Dmol
  multi-frame model of the imaginary mode: 20 frames of ± 0.4 Å maximum displacement from
  `displacements_angstrom`, Å, never Bohr); `trajectoryPlayer` (slider, play/pause, step readout;
  drives a `moleculeViewer`; shows `label`, `accepted_bool` and "decimated: every Nth of M" when
  `decimation_stride > 1`); `energyPlot` (dependency-free SVG via `createElementNS`; current step
  marked and linked to the player); `candidateTable` (sortable; gate badges; links `#c/<id>`).
- **Safety (R14):** text only through `textContent`/`setAttribute`/`createTextNode`; the Python sink
  scan from slice 08 runs on this file (no `innerHTML`, `outerHTML`, `insertAdjacentHTML`,
  `document.write`, `eval(`, `Function(`, string timers).
- **M12 (recorded browser smoke, both browsers, from `file://`):** a stub `RunData` with known
  answers — a TS whose imaginary mode is a pure stretch of a named bond (the animation must move
  only those two atoms, in opposite directions), a 3-frame trajectory with known coordinates (the
  player must show them in order), a candidate with 2 imaginary modes (banner), and hostile strings
  in a label, an entry id and a provenance field (rendered as text). Evidence: screenshots, the
  console log (no error) and the network log (no request) for Chrome and Firefox, kept in the proof
  folder. Record any CSP addition 3Dmol needs (e.g. `worker-src blob:`) and update slice 08's CSP
  constant with that exact addition only.
- This is the components' only rendering check (no JS in CI); slice 13 repeats M12 on the real
  bundle.
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

**Score: 9/10.** Small, framework-free components over a fixed contract, with a known-answer smoke.
Residual risk: 3Dmol behaviour under the CSP over `file://`, which M12 measures and records.

## Mini-requirements

1. Five components with the signature; `EtaView.load` version check.
2. The sink scan is clean on `eta-view.js`.
3. M12 in Chrome and Firefox: the named-bond mode moves only those atoms; the 3-frame trajectory
   plays in order; the banner shows; hostile strings render as text; no console error; no network
   request.
4. Any CSP addition is recorded and minimal.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] Write `eta-view.js`; replace slice 08's placeholder.
- [x] Stub run-data fixture `tests/unit/review/data/m12_stub_run_data.json` (written by a test
      helper through `canonical_run_data_json`).
- [x] Run M12 in both browsers; save evidence.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** add a framework, a bundler, npm, a CDN reference or a second data source.
- **DO NOT** let any component read anything but `RunData`.

## Proof contract

- [ ] M12 evidence (screenshots, console and network logs, both browsers).
- [ ] `uv run pytest tests/unit/review -q` passes (sink scan, assets).
- [ ] Required checks exit 0.

## Source material

- Mission G12, R14, R16, R17.

## Intent visual

Per candidate: left, the molecule/mode viewer; right, the trajectory player above the energy plot
with the current step marked; above both, the static summary; the index is a sortable table.

## Status

- compiled

## Dependencies

- OPR.0.7.0.8.
