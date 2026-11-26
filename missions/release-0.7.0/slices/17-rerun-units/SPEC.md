---
id: OPR.0.7.0.17
slice: 17-rerun-units
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Rerun all 11 v0.7.0 E2E units and the 4 score commands on copies of their stores with the seed checks and the new record fields, gate 0 new rows and unchanged dG dagger under the default rule, and land the fresh records as candidates after moving the old ones aside."
depends_on: [OPR.0.7.0.16]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.7.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_v070_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Rerun the v0.7.0 E2E units with the seed checks and records

## Intent

Regenerate every v0.7.0 E2E record with slice 15's seed checks and slice 16's record fields, so that
all of them are uniform, and land them as fresh candidates for TJ's re-review (mission G7, G8, G14,
R35). Promotion 9fdba68 stands until TJ re-promotes.

Context the builder needs:
- **Start gate:**
  - slices 15 and 16 are audited;
  - the lead confirms TJ's Q-R7a/Q-R7b answer, or gives the go on the defaults (A: the 1.3 ×
    covalent cut; A: reject, slot kept). Until then, do not start.
- **Which units rerun: all 11**, plus the 4 score commands.
  - Slice 11's 8 enumeration units: ethyl and n-propyl × endo and exo × GFN2 and UMA.
  - Slice 12's 3 fallback units: `graft_time`/xtb, `run_time`/xtb, `run_time`/uma.
  - Reasons: slice 16's record fields change every record; the clash check rejects samples in
    every one of the 11 units (`cov_margin.out`); and uniform records are what TJ re-promotes.
- **State, never the old evidence:**
  - The new state directory is `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7-runs/`. It must not
    exist yet: refuse, never wipe.
  - Copy the four stores into it with
    `sqlite3 <src> ".backup '<dst>'"`. The sources are slice 11's `v070_enum.sqlite` and slice 12's
    three `v070_fallback_<construct>_<engine>.sqlite`. The backup is WAL-safe and read-only on the
    source.
  - Record each copy's sha256 and `stage_artifacts` row count before and after the runs.
  - Slices 11, 12 and 13's evidence directories are never written.
- **Commands:**
  - Slice 11's unit and score commands, and slice 12's unit commands with
    `ETA_RXNCAT_V070_REUSE_STORES=1` (slice 14 C1), all with
    `ETA_RXNCAT_V070_STATE=~/.hacf/eta-rxncat-hacf/evidence/v070-replan7-runs`.
  - The node names and run scripts are those of slice 11's and slice 12's proofs (e.g.
    `v070-slice11/run.sh`, copied and retargeted into the new directory, not edited in place).
  - Each unit is one command under the heavy-run rule, `timeout 5400`.
- **Gates (default A + A):**
  - **0 rows added** to every store across all 15 commands, and the harness's second pass is all
    hits.
    - Under A + A every used sample keeps its start, so it keeps its keys. A unit that adds a row is
      a **stop-and-report**: name the unit, the sample, and the key kind.
  - Every dG‡ and every ddG‡ equals the value in `tests/fixtures/v0.7.0/` **exactly**. The proof
    has a per-unit table.
  - The G7/G8 gates pass as in slices 11 and 12.
  - The `seed_clash` exclusions equal the measured set, per unit (`v070-replan7/cov_margin.out`: 53
    starts, by unit and index).
  - `bond_changed:*` count = 0.
  - The stall count is 0: the ethyl exo UMA `PreRelaxTimeout` sample is now `seed_clash`.
- **If TJ chose Q-R7b B** (draw a replacement): rows are added and the numbers may move.
  - The gate becomes: the G7/G8 gates; every new sample start clash-free; dG‡/ddG‡ reported against
    9fdba68's with the difference.
  - The time grows by about 1.5 h of wall time and about 1 h of GPU (UMA units took 5-16 min fresh).
- **Candidates:**
  1. **First, move the old ones aside**, in one candidate-only commit:
     `git rm` of every tracked file under `tests/candidate_outputs/v0.7.0/`: the 30 `v070_*`
     records and the `review/` tree.
     - The paths come from `git ls-files` (names only; no file is opened).
     - Nothing is deleted outside git; they stay recoverable at 8210071, and the records also sit
       in `tests/fixtures/v0.7.0/`.
  2. The reruns then write fresh files to `tests/candidate_outputs/v0.7.0/`.
  3. A second candidate-only commit holds them (`git show --stat` of both commits in the proof).
- **Heavy runs (mission §5 "Heavy-run rule", normative):**
  - Before each engine/GPU command, run a blocking host check in its own call or an exiting loop
    (never echo-then-run), with the output kept in the proof:
    - `nvidia-smi`: no compute process;
    - `MemAvailable` >= 12 GiB;
    - `ps`: no other eta E2E/pytest/xtb, and no non-niced (nice < 10) process of any rig using
      >= 100 % CPU or >= 2 GiB RSS.
  - One engine and one unit per command, `timeout 5400` for a unit command and `timeout 3600`
    otherwise, from a scratch cwd.
  - Env asserted in the proof: `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`,
    `ETA_RXNCAT_ACCEPTANCE=1`, `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`.
  - Honour any quiet-host hold the lead announces. A failed GPU run is a finding.
- **Node** `eta_rxncat_species_runner` (owner of `tests/e2e/**`; 1988/2000 before slice 16's
  compression). No `src/` change. A harness fix the reruns need goes in a code commit before the
  candidate commit, and is named in the proof.
- **Times:**
  - About 1.5 h of seat time. Wall time is about 45 min for 15 commands, all store hits.
  - GPU about 10 min (UMA model loads, 0 evaluations expected).
  - Audit about 0.75 h (the audit reruns a unit in a throwaway worktree).
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
- The 0-row expectation follows from the measurement: every used start is unchanged, and the hashes
  were verified on all 121 starts.
- The commands are slices 11 and 12's, with a store copy.
- Residual: a hidden key dependency on a sample's neighbours would add rows. The 0-row gate turns
  that into a stop-and-report, not a silent change.

## Mini-requirements

1. All 11 units and 4 score commands rerun on copies of the four stores. The old evidence is
   untouched.
2. Under A + A: 0 new rows, every dG‡/ddG‡ equal to 9fdba68's, G7/G8 pass, `seed_clash` exactly
   the measured set, 0 stalls.
3. The old candidates are moved aside by `git rm`, and the fresh records land in a candidate-only
   commit.

## 3. Implementation Plan (Task List)

- [ ] Index; check the start gate (TJ's answer or the lead's go).
- [ ] Create the state directory (refuse if present); back up the four stores; record their sha256
  and row counts.
- [ ] Candidate-only commit: `git rm` the old candidates and review tree.
- [ ] Per unit: host check, then run; after all, row counts, the dG‡/ddG‡ table, and the
  `seed_clash` set against the measurement.
- [ ] Candidate-only commit of the fresh records; progress commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** write slices 11, 12 or 13's evidence directories or stores.
- **DO NOT** read a candidate back as input; compare with `tests/fixtures/v0.7.0/`.
- **DO NOT** promote, push or tag. **DO NOT** touch `tests/fixtures/`.
- **DO NOT** start before the start gate, or run two engine commands at once.
- **DO NOT** pass a unit that added a row under A + A; stop and report.

## Proof contract

- [ ] The store copies: source and copy sha256, and row counts before and after.
- [ ] Per unit: host check, env, wall time, exit code, rows added (0), gates, and the dG‡/ddG‡
  against 9fdba68.
- [ ] The `seed_clash` set against `cov_margin.out`; the stall count.
- [ ] `git show --stat` of both candidate-only commits.
- [ ] Required checks exit 0.

## Source material

- Mission G7, G8, G14, R7, R35, §5 "Heavy-run rule"; slices 11 and 12's proofs and run scripts;
  `~/.hacf/eta-rxncat-hacf/evidence/v070-replan7/`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.16, and TJ's Q-R7a/Q-R7b answer (or the lead's go on the defaults).
