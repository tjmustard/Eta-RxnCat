---
id: OPR.0.7.0.18
slice: 18-rereview-bundle
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Bundle the rerun records with the fixed site through slice 13's harness retargeted to the replan-7 evidence, gate every row's disposition and TS identity, repeat M12, re-derive the acceptance record and draft TJ's Phase 3 re-review row."
depends_on: [OPR.0.7.0.17]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", docs/prd/v0.7.0/ACCEPTANCE_RESULT.json, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_acceptance_record_v070.py], [uv, run, pytest, tests/e2e/test_review_v070_helpers.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Fresh review bundle, re-derived record and TJ's Phase 3 re-review

## Intent

Put the rerun records in front of TJ in the fixed site, re-derive the acceptance record from them,
and send TJ the Phase 3 re-review row. He re-promotes, or he does not (mission G13, G15, R34, R35).

Context the builder needs:
- **Start gate:** slice 17 is audited, and its candidate-only commit exists.
- **Harness:** slice 13's `tests/e2e/review_v070.py`, with every gate as R34 wrote it. Only its
  sources and roots are retargeted:
  - **Sources:** the records and the four stores in
    `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7-runs/`, replacing `SLICE11`/`SLICE12`.
    - Use one named source root, so slice 14's verdict reads the same thing;
      `acceptance_record_v070.py` and its test follow.
    - The old constants are not kept as dead code.
  - **Scratch root:** `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7-runs/review/`.
  - **Copy target:** `tests/candidate_outputs/v0.7.0/review/`.
  - Both roots must be absent or empty, and either one non-empty is refused (slice 17 `git rm`'d the
    old tree). Nothing is wiped.
- **Every slice 13 gate, unchanged:**
  - coverage per store;
  - 0 `Engine.evaluate` calls and unchanged row counts;
  - no `missing` entry;
  - root and sub `MANIFEST.sha256` verify;
  - each sub-bundle <= 25 000 000 bytes;
  - the host-data, network and sink scans and the CSP;
  - every trajectory has frames, and the embedded bytes equal `run_data.json`;
  - M10: stride <= 2 on every `ts_search`, read from the file.
- **New gates (G15), on the scratch tree's `run_data.json` and static `index.html`:**
  - Every TS sample of every unit has a `sample_dispositions` entry, and every endpoint frequency
    has an `endpoint_dispositions` entry. None is `not_recorded`.
  - Every frequency row on the static page sits in the "Used" or the "Not used" group, under a
    heading that names its disposition.
  - Every TS block shows `TSIdentity`, and every block whose `passed_bool` is False carries the
    banner.
  - Known answers:
    - ethyl endo GFN2 sample 6 is `excluded: seed_clash` with pair (4, 21) at 0.438 Å, and has no
      frequency row;
    - `071c077d750a` (n-propyl UMA cyclopropene) is `superseded_by_push` and sits in the not-used
      group;
    - its push successor carries the species runner's recorded kind.
- **M12 repeat** on the scratch tree from `file://`, starting at the root `index.html`:
  - installed Chrome and Playwright Firefox, headless, with slice 09's driver;
  - each TS mode animates, each trajectory plays, every link works;
  - the disposition labels and grouping show in the JS views;
  - no console error and no network request; screenshots and logs go in the proof.
- **Acceptance record:** `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` is re-derived by its writer from
  the replan-7 evidence records and the slice 17 proof. Never from candidates.
  - Per unit: the gates, `seed_clash` and `bond_changed` counts, stalls and time lost, and dG‡ and
    ddG‡.
  - A `replan_7` block: what changed against slice 13's record (the exclusion reasons; stalls
    1 → 0), the clash rule TJ chose, and the bundle's root `MANIFEST.sha256`.
- **Phase 3 row (drafted in `proof/18-execute.md`).** The lead sends it to `advisor-lead@kernel`
  tagged `question-for-tj`. It states:
  - the bundle path and how to open it;
  - TJ's two findings and what the site now shows for each;
  - that rejected rows are grouped apart and labelled;
  - the clash rule in force;
  - that numbers are unchanged (under A + A; otherwise the per-unit differences from slice 17);
  - that re-promotion replaces the 30 files of 9fdba68 with the new candidates, and only he
    promotes.
  - Values are taken from the records and proofs, never retyped.
- **Commands:** this slice runs no engine unit. Every command uses `timeout 3600`, from a scratch
  cwd, after a blocking host check in its own call: no other eta E2E/pytest/xtb, and
  `MemAvailable` >= 12 GiB. Env asserted: `ETA_RXNCAT_ACCEPTANCE=1` and
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Honour any quiet-host hold.
- **Candidate rule:** the bundle goes to `tests/candidate_outputs/v0.7.0/review/` in a
  candidate-only commit (`git show --stat` in the proof). Never promote.
- **Proof naming:** `proof/18-execute.md`, type `execute`/`evidence`; the audit writes the QA
  verdict.
- **Node** `eta_rxncat_species_runner` (owner of `tests/e2e/**`). No `src/` change.
- **Times:** about 2.5 h of seat time (harness retarget, build, M12, record, row) and an audit of
  about 1 h. GPU 0.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (the E2E writes candidates and never reads them back as input;
    `tests/fixtures/v0.7.0/` holds byte-equal copies and may be read).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
    Plain literal `rm -f` only (never `rm -rf` on a computed path).
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.

## 1. The Confidence Mandate

**Score: 9/10.**
- The harness, its gates and M12 are slice 13's, already proven on these stores' ancestors.
- The new gates read fields slice 16 defines and tests.
- Residual: the real layout in the browsers (M12 catches it).

## Mini-requirements

1. One fresh bundle covers every replan-7 run, with 0 engine calls. Every slice 13 gate passes, and
   both roots were fresh.
2. Every row on the site carries a disposition, in its group. TS identity and banners show, and the
   two known answers hold.
3. M12 on the real bundle in both gate browsers.
4. The acceptance record is re-derived from the replan-7 evidence, with the `replan_7` block.
5. The Phase 3 re-review row is drafted for the lead.

## 3. Implementation Plan (Task List)

- [x] Index; retarget the harness sources and roots (one named root); update the helper tests.
- [x] Host check; build in scratch; run the R34 gates and the G15 gates; copy to candidates; M12.
- [x] Record writer: re-derive the record, with the `replan_7` block.
- [x] Code commit; candidate-only commit (the bundle); record and progress commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run an engine, change `src/`, or edit the bundle by hand.
- **DO NOT** wipe or overwrite a non-empty output root; refuse.
- **DO NOT** read candidates back; derive from the evidence records.
- **DO NOT** lift the size or stride budgets, or drop a run to pass a gate.

## Proof contract

- [x] `proof/18-execute.md`: coverage, engine-call and row counts, R34 gate outputs, G15 gate
  outputs and both known answers.
- [x] M12 evidence on the real bundle (both gate browsers).
- [x] The re-derived `ACCEPTANCE_RESULT.json` and its writer test.
- [x] The Phase 3 re-review row draft.
- [x] Required checks exit 0.

## Source material

- Mission G13, G15, R14, R15, R17, R18, R34, R35; slice 13's SPEC and proof; slices 16 and 17.

## Intent visual

The slice 13 bundle layout, with slice 16's "Used" and "Not used" groups and the identity numbers
on every TS block.

## Status

- compiled

## Dependencies

- OPR.0.7.0.17. Slice 14 waits for TJ's re-promotion.
