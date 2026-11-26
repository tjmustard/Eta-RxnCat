---
id: OPR.0.7.0.14
slice: 14-acceptance-verdict
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "After TJ's Phase 3 visual audit and promotion, run the verdict on both engines against the promoted outputs, document the review command and the run-data contract, and bump to 0.7.0."
depends_on: [OPR.0.7.0.18]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.7.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, tests/unit/test_package.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_package.py, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 acceptance verdict, docs and the 0.7.0 bump

## Intent

Close v0.7.0 on real outcomes after TJ's audit (mission US-013, §8 Release).

Context the builder needs:
- **Replan 7 (R35) re-pointed this slice.**
  - **C1 `e641ba1` stands as is:** the verdict rule, and the field-by-field rerun comparison against
    `tests/fixtures/v0.7.0/` with its `VOLATILE` list.
  - The fields slices 15-16 add (`SeedCheckDetail`, dispositions, `validation`) are deterministic,
    so no `VOLATILE` change is expected.
    - A new difference is a finding, not a `VOLATILE` edit.
    - The one exception is a wall time this run measures: add it with its reason, disclosed in the
      proof.
  - The executing state and Start `9fdba68` stay as recorded. TJ's re-promotion is a **work
    gate**, not a new Start.
  - The one updater run after the last commit uses `--from-diff 9fdba68`, so C1 is covered. Nodes
    of slices 15-18 that it flags again (already reconciled by their audits) are listed in the
    proof for the audit.
- **Start gate:** TJ's Phase 3 re-review of slice 18's bundle is closed.
  - His **re-promotion commit** of the replan-7 candidates exists, and the lead names its sha.
  - If TJ asked for changes, or the re-promoted file set differs from the 30 `v070_*` names, stop:
    the lead replans.
- **Verdict:** rerun the G7/G8 E2E against the re-promoted fixtures, gate on suite counts and skips,
  and write `verdict` into `docs/prd/v0.7.0/ACCEPTANCE_RESULT.json` (derived; slice 18 re-derived
  it).
  - The rerun is cache hits on copies of the **replan-7 stores**, through the named source root
    slice 18 set in `review_v070.py`. It never uses slices 11/12's stores.
  - Fresh engine work runs only under the heavy-run rule.
  - An E2E skip is a failure under `ETA_RXNCAT_ACCEPTANCE=1`.
- **Docs:** README sections for `eta-rxncat review-bundle` and the run-data contract (version rule,
  forward-only stores, the CSP/offline design, the row dispositions and TS identity of slice 16), and
  the seed checks of slice 15 (`seed_clash`, `bond_changed:*`, the clash rule TJ chose);
  every claim derived from the record and pinned by
  the claims helper in `tests/unit/test_identity.py`; CHANGELOG `[0.7.0]` is the scribe's (the lead
  dispatches it).
- **Bump:** `version = "0.7.0"` in `pyproject.toml` and `src/eta_rxncat/__init__.py`;
  `tests/unit/test_package.py`; `uv lock`.
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
  One engine and one unit per command, `timeout 5400` for a G7/G8 unit command (R7, HF3-BOUND) and
  `timeout 3600` for every other command, from a scratch cwd (never the repo root:
  geomeTRIC writes `HT.v_*.txt` into the cwd until slice 06 lands). Env asserted in the proof:
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`, `ETA_RXNCAT_ACCEPTANCE=1`,
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Honour any quiet-host hold the lead announces.

## 1. The Confidence Mandate

**Score: 9/10.** The same shape as v0.6.0's verdict slice, on a smaller E2E. Replan 7 changes
only the start gate, the stores the rerun reads and two README claims. C1's comparison code holds
against the re-promoted fixtures.

## Mini-requirements

1. TJ's Phase 3 re-review is closed, and his re-promotion commit exists (work gate).
2. Verdict pass with suite counts and skips = 0 under acceptance.
3. README claims derived and pinned; version 0.7.0 everywhere.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] Verdict runs (host check per command); record `verdict`.
- [ ] README + claims helper; bump; `uv lock`.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** start before TJ's re-promotion; **DO NOT** push or tag (the lead does).
- **DO NOT** widen `VOLATILE` to absorb a non-timing difference.

## Proof contract

- [ ] Verdict output with counts, skips, host checks and env.
- [ ] `uv run pytest tests/unit/test_package.py tests/unit/test_identity.py -q` passes.
- [ ] Required checks exit 0.

## Source material

- Mission §8 Release, US-013, R35; slice 18's record and bundle; C1 `e641ba1`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.18 and TJ's re-promotion (Phase 3 re-review).
