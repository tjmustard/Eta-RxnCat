---
id: OPR.0.7.0.13
slice: 13-review-bundle-and-record
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Bundle every v0.7.0 E2E run for TJ's visual audit, gate the real bundle's hygiene and frames, repeat the M12 smoke on it, write the acceptance record from the candidates, and send TJ the Phase 3 row."
depends_on: [OPR.0.7.0.9, OPR.0.7.0.11, OPR.0.7.0.12]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_review
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", docs/prd/v0.7.0/ACCEPTANCE_RESULT.json, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_acceptance_record_v070.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 review bundle for the real runs, acceptance record and TJ's Phase 3 audit

## Intent

Put every enumerated TS and optimization in front of TJ in the bundle he asked for, and record what
passed (mission G13, R15, R17, R20; US-012, US-013). TJ's visual audit is the Phase 3 gate.

Context the builder needs:
- **Bundle:** `eta-rxncat review-bundle` over every slice 11 and 12 run record, written to
  `tests/candidate_outputs/v0.7.0/review/` (one bundle; candidates by hash route). Reruns use the
  existing stores: all cache hits, no engine call (stage metrics in the proof).
- **Real-bundle gates (G13):** `MANIFEST.sha256` verifies; size <= 25 MB or the decimation is stated
  on the page and in `RunData`; scans on the **real** files: no absolute path, `$HOME`, username or
  hostname (R15), no network reference, sink scan clean; **every trajectory has frames** (no
  `missing`, no "no trajectory stored": stores are forward-only, F20); embedded == file bytes.
- **M12 repeat** on the real bundle in Chrome and Firefox from `file://`: each TS's mode animates,
  each trajectory plays, the index links work, no console error, no network request; screenshots in
  the proof.
- **Acceptance record:** `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json`, derived from the candidates
  (never hand-typed): per G7 unit and G8 construct the gates and reported values; suite counts and
  skips; the bundle path and its MANIFEST sha256; stall counts and time lost. Writer
  `tests/e2e/acceptance_record_v070.py` with its own unit test.
- **Phase 3 row:** to TJ through advisor-lead@kernel (tag `question-for-tj`): the bundle path, how to
  open it (double-click `index.html`), what to check (each TS has exactly one imaginary mode and it
  moves the forming bonds; each optimization path is sensible; R sits anti to the diene; fallbacks
  read right), and that only he promotes. The lead sends it; the builder drafts it in the proof.
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

**Score: 9/10.** Every component is built and tested by now; this slice assembles, scans and records.
Residual risk: real-data rendering differences from the stub, which the M12 repeat catches.

## Mini-requirements

1. The bundle covers every slice 11/12 run; reruns made 0 engine calls.
2. All real-bundle gates pass.
3. M12 on the real bundle, both browsers, evidence kept.
4. The acceptance record is derived and its writer is tested.
5. The Phase 3 row text is in the proof for the lead.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] Build the bundle; run the gates; M12 repeat.
- [ ] Record writer + test; write the record.
- [ ] Candidate-only commit (bundle); code + record commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** re-run an engine for the bundle; **DO NOT** promote; **DO NOT** edit the bundle by hand.

## Proof contract

- [ ] Gate outputs (manifest, size, scans, frames, byte equality).
- [ ] M12 evidence on the real bundle.
- [ ] `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` and its writer test.
- [ ] Required checks exit 0.

## Source material

- Mission G13, R15, R17, R18, R20; slices 08, 09, 11, 12.

## Intent visual

The bundle as built in slices 08-09; TJ reviews it.

## Status

- compiled

## Dependencies

- OPR.0.7.0.9, OPR.0.7.0.11, OPR.0.7.0.12. Slice 14 waits for TJ's Phase 3.
