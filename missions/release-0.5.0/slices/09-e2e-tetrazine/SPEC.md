---
id: OPR.0.5.0.9
slice: 09-e2e-tetrazine
mission: release-0.5.0
status: done
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Run the TS3a (unmapped) and TS4a (two single CF3 grafts plus core-frozen pre-relaxation) TS searches and barriers on GFN2 and UMA with the TS4a<TS3a ordering, and commit the candidates."
depends_on: [OPR.0.5.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.5.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 Tier 3 E2E — the tetrazine pair (TS3a unmapped, TS4a mapped by two grafts)

## Intent

Run the tetrazine–cyclopropene TS searches end to end on both recipes — TS3a from Liu's geometry
and TS4a from a guess built by two single CF₃ grafts on TS3a plus a core-frozen pre-relaxation —
with validated TSs, ΔG‡ against the reactant ensembles, TJ's "lowering" ordering, and committed
candidates.

Context the builder needs:
- **TJ, verbatim:** A3 "Q3. A" (dual −CF₃ = two single grafts); A4 "Q4. A" (TS3a [10.0, 24.0],
  TS4a [0.7, 14.7], UMA, 1 M); Q-TJ3 (third of "A / A / A"): GFN2 gates convergence and the mode
  count; **amended by Q-TJ4 A (mission R32)**, verbatim: "**A (Recommended).** GFN2 TS4a becomes
  report-only (the failure recorded honestly in the candidate and the acceptance record, not a
  verdict fail), AND GFN2 also gates TS identity (overlap >= 0.50, in phase, KE >= 0.60) on every
  other Tier 3 case. UMA unchanged. Resolve writes it; slices 09-13 follow." TJ's spec: "Dual −CF₃ graft onto TS3a → TS4a, lowering ΔG‡_ref from 18.9 to 9.6".
- **Inputs (slice 07):** `t3_ts3a_unmapped.yaml`, `t3_ts4a_mapped.yaml` (graft blocks,
  `pre_relax`, map), `load_ts_fixture`, the XYZ files.
- **TS4a start per recipe:** `graft` twice with the YAML blocks, then
  `relax_constrained_core(product, engine, GeometricOptimizer(), [0, 3, 6, 7], options={"maxiter": 200})`
  on that recipe's engine (v0.4.0's API; read `src/eta_rxncat/mapping/`). Measured (HF-10): xtb 17
  steps / 5.2 s, UMA 14 / 8.6 s; at the xtb start two modes below −20 (−322.1 reaction, −72.5 CF₃
  rotor), UMA one (−377.6); forming-bond overlap of the reaction mode 0.889 (xtb) / 0.898 (UMA) vs
  ≤ 0.32 (HF-7, HF-11). The pre-relaxed start is recorded in the candidate.
- **Runners, stores, gates, reports and candidate rule:** exactly as slice 08 (read its SPEC
  `missions/release-0.5.0/slices/08-e2e-diels-alder/SPEC.md` and its test once it is committed).
  Gated per recipe: both — converged and `mode_count_passed_bool`; UMA — KE, identity, window and
  the **ordering ΔG‡(TS4a) < ΔG‡(TS3a)** (1 M); GFN2 — the identity core (R32, TJ Q-TJ4 A): `forming_stretch_overlap` ≥
  `min_forming_stretch_overlap` (0.50), `forming_bonds_in_phase_bool` true, `active_core_passed_bool`
  (KE ≥ 0.60), from the validator's fields, **not** `identity_passed_bool` (which includes the
  forming-distance window; reported on GFN2); both — second-run hits and
  conservation. **Exception: GFN2 TS4a is report-only (R32)**: it runs and is recorded with every
  measured check, `failed_reason` and `failed_checks` as they came out, `report_only: true` and
  `reported_outcome` (`passed`/`failed`); nothing of that pair is gated or fails the test, and an
  `EngineError` from `run_transition_state` on that pair is caught in the test and recorded as
  `failed_reason: engine_error:<type>` with its message.
  Reported: GFN2 extras, the GFN2 window, ΔG‡ and ordering, connectivity, forming-core `[0, 3, 6, 7]` RMSD of the
  final TS4a to Liu's TS4a under the YAML map (G5) and of TS3a to Liu's TS3a, the pure-graft and
  pre-relaxed-start RMSDs, close contacts of each graft.
- **Measured at Liu's geometries (HF-3, HF-4):** UMA ΔG‡ TS3a 19.76, TS4a 12.38 (margin 2.32 to
  14.7); GFN2 −5.60 / 5.96 and ΔE‡ −16.4 / −5.9, so a GFN2 search may not keep a saddle near Liu's:
  measured at C1 fc4f38e: GFN2 TS4a `ts_search_failed:max_steps` (now report-only, R32); GFN2 TS3a
  KE 0.834, overlap 0.689, in phase. A miss on any other gate is stop-and-report with the output.
- **Candidates:** `tests/candidate_outputs/v0.5.0/t3_ts3a.{xtb,uma}.json`,
  `t3_ts4a.{xtb,uma}.json` (+ the graft summary inside `t3_ts4a.*`). C1 / E2E at C1 / C2 as slice 08.

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  geomeTRIC may run only as a black box through `geometric-optimize` and its `--help` text.
- **Clean room, nMAP (v0.4.0 Q1).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach". Never open, clone, fetch or search Eta_Scripts or nMAP (GitHub,
  `~/PROJECTS/cleanroom-nmap`, a cache, a web or code search); only its `TRANSFER_LOG.md` may be
  read. Never message the clean-room seats.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.5.0`, cut re-entrantly from Base (the
  mission commit on main, parent `0d2a8d3`). One code commit per slice unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff. Every commit ends with exactly
  two footer lines, `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, `<version>` read from
  `.agents/hacf-manifest.json` at commit time; no co-author or session trailer. Author "Thomas J.
  L. Mustard Ph.D." (repo-local git config). Never `--no-verify`, never rewrite history.
- **Code graph first.** The first command is `python3 .agents/scripts/hyper_codegraph.py index`;
  it must print `index: ok` (the red team saw `stale_index`). Anything else stops the slice. The
  graph only widens a blast radius.
- **Ledger.** Only through `hyper_ledger.py` / `hypergraph_updater.py`, never by hand. On an
  existing node, `ensure-node --id <node>` takes the **full** `--files` list (it replaces); count
  the node's globs before and after. No slice creates a node.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF v0.6.3.** No `HACF-install.sh` (never without `--ref`), no `HACF-uninstall.sh`, no
  `hyper_migrate.py apply`. On OpenRig 0.7.21, `hyper_spec.py`/`hyper_migrate.py` warn "outside
  the pinned contract", `hyper_spec.py proof` writes the proof natively and `hyper_migrate.py
  verify` skips `rig scope audit`: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git:
  every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host (shared with the hacf and cleanroom rigs).** Before any E2E, GPU, engine or full-suite
  run: `free -g` and `ps` for other rigs' heavy python/pytest/engine processes; if one is active,
  wait (poll at most every 5 minutes with Monitor or a background wait, never a foreground sleep)
  for GPU/E2E work; the full CPU unit suite may run serially beside another rig's small batches
  only with ≥ 6 G available. Record the check in the proof. GPU/E2E runs one at a time. Never kill
  another rig's process. The check and the heavy command are separate calls (or the check exits
  non-zero), never echo-then-run.
- **Engines.** Every xtb command sets
  `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (without it the
  xtb E2E skips with exit 0). UMA runs in `.venv-accept-uma` on CUDA. Every E2E command runs
  under coreutils `timeout 3600`; an expiry is stop-and-report with the output.
- **Lessons (mission R26):** unit-suffixed numeric keys (R54); no energy- or record-ordered list
  in a compared output (R55); one `gated_outcome` per test, `pending_*` fails under
  `ETA_RXNCAT_ACCEPTANCE=1` (R56); any reader of a store or runner payload checks `failed_reason`
  first (R50); re-dedup after any geometry change (v0.3.0 path unchanged); tolerances are measured
  before they are written, never guessed; the candidate rule (code commit C1 with a clean tree,
  E2E at C1, then a commit of only `tests/candidate_outputs/v0.5.0/*` as C2).
- **Required checks** (AGENTS.md), all exit 0 before each commit: `uv sync --locked`;
  `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv run pytest`;
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception (N1).
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it; never loosen a tolerance
  (TJ's or this SPEC's). Never use `AskUserQuestion`.
- **Never** push, tag or open a PR.

## 1. The Confidence Mandate

**Score: 9/10.** Inputs, grafts and gates are fixed; the measured margins are stated. Open (stop
and report): GFN2's saddle for these two, and UMA's stationary TS4a against 14.7.

## Mini-requirements

1. `tests/e2e/test_t3_tetrazine.py` (`e2e` + `slow`), both recipes, cases TS3a and TS4a, each run
   under `timeout 3600`.
2. Gates per case × recipe as above; the ordering gated on UMA and reported on GFN2; GFN2 TS4a
   report-only (a test asserts its fragment has `report_only: true` and no gated check).
3. Second runs: 100% hits on the reactants' stages and on every TS stage that ran in the first run
   (`ts_opt`, a cached failure row counts; `frequency` only if it ran), no new rows (G6, R32). Fix
   `second_run_ts_all_hits` (`tests/e2e/t3.py`), which required a `frequency` hit after a failed search. The graft and the
   pre-relaxation are not store stages: they run once per recipe and both runs use that same
   start state (GPU runs need not be bitwise reproducible, and the start is part of the `ts_opt`
   key).
4. Four candidate files in C2.
5. A failing gate: candidate written with `test_outcome: fail`, stop and report. GFN2 TS4a's
   report-only outcome is not a failing gate.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read slice 08's test and `tests/e2e/t3.py`.
- [x] Task 2: the test; graft + pre-relax helper (tier-D test of the helper against slice 07's graft numbers).
- [x] Task 3: required checks; C1.
- [x] Task 4: host check; xtb then UMA (separate calls); second runs.
- [x] Task 5: C2; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** use Liu's TS4a coordinates in the start (N13); **DO NOT** add a dihedral constraint (N12).
- **DO NOT** gate GFN2 beyond convergence, the mode count and the identity core (R32), or anything
  of GFN2 TS4a; **DO NOT** gate the GFN2 window; **DO NOT** loosen any bound.
- **DO NOT** compare `history`.

## Proof contract

- [ ] Both recipes' commands with host checks, `timeout`, exit codes, 0 skips.
- [ ] Each gated value per case × recipe, and the ordering; GFN2 TS4a's reported outcome.
- [ ] Second runs 100% hits.
- [ ] C2 contains only `t3_ts3a.*` and `t3_ts4a.*` (file names only).
- [ ] The required checks exit 0.

## Source material

- Mission R4, R16, R22, HF-3, HF-4, HF-7, HF-10, HF-11; slices 07, 08.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.8 (build order; its code and contracts are used here)
