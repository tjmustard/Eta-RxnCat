---
id: OPR.0.5.0.8
slice: 08-e2e-diels-alder
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Run the TS1a_n (unmapped) and TS1b_n (mapped from M1) TS searches and barriers on GFN2 and UMA, gated per TJ's Q-TJ3, and commit the candidates."
depends_on: [OPR.0.5.0.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.5.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 Tier 3 E2E — the Diels–Alder pair (TS1a_n unmapped, TS1b_n mapped from M1)

## Intent

Run the two Cp Diels–Alder TS searches end to end on both recipes — Liu's TS1a_n from its own
geometry and the TS1b_n mapped start from v0.4.0's promoted M1 product — computing validated TSs
and ΔG‡ against their reactant ensembles, gated per recipe as TJ decided, and commit the
candidates for TJ's Phase 3.

Context the builder needs:
- **TJ, verbatim:** A2 "Q2.  A"; A4 "Q4. A" (TS1a_n [10.7, 24.7], TS1b_n [20, 34], UMA-gated,
  1 M); Q-TJ3 (third of "A / A / A"): on GFN2, convergence and exactly one imaginary mode below the
  cutoff are gated; KE fraction, identity, connectivity and ΔG‡ are reported. Q-E5 "Q5. C, if it
  turns out MACE, UMA, or OMol25 are needed then they should become standard.": a UMA miss is a
  finding for TJ, never a loosened window.
- **Inputs (slice 07):** `tests/e2e/data/e2e5/t3_ts1a_n_unmapped.yaml`, `t3_ts1b_n_mapped.yaml`,
  `load_ts_fixture`; the M1 starts `tests/fixtures/v0.4.0/m1_relaxed.{xtb,uma}.json`
  (`relaxed_product`, promoted by TJ; never read `tests/candidate_outputs/`); M1's
  `graft_to_ts1b_n_map` (in the YAML).
- **Runners:** reactants with v0.3.0's `run_species` (read `tests/e2e/test_e2e5_tier2_cp_cyclopropene.py`
  for the recipe fixtures, store, candidate and `gated_outcome` helpers — follow them); the TS with
  slice 05's `run_transition_state` (`TSRecipe` with `PRFOOptimizer()` default options and the
  recipe's engine stage from `tests/e2e/e2e_env.py:recipe_for`, `TSValidationOptions()` defaults);
  ΔG‡ with slice 06's `activation_free_energy`. Each run uses a **fresh store** under `TMPDIR`, then
  a second run in the same store (G6).
- **Per recipe and case, gated** (one `gated_outcome` per test, R56):
  - both recipes: search converged (no `failed_reason` other than `None`) and
    `validation.mode_count_passed_bool`;
  - UMA only: `active_core_passed_bool`, `identity_passed_bool`, ΔG‡(1 M) inside the window;
  - both: second run has `ts_opt` and `frequency` all hits, zero rows created; the reactant species
    are 100% hits on their stages;
  - both: barrier conservation holds.
- **Reported** (in the candidate, never gated): GFN2's KE fraction, identity numbers and ΔG‡;
  `connectivity_equal_bool` (both); forming-core `[1, 2, 3, 5]` RMSD of the final TS1b_n TS to
  Liu's TS1b_n under the map (G5) and of TS1a_n to Liu's TS1a_n (identity map); full and active
  RMSDs; the search counts; `hessian_method`; ΔG‡ at 1 atm; the literature values and the
  difference.
- **Measured expectations (mission HF-3…7):** at Liu's geometries UMA ΔG‡ 19.38 / 29.05 kcal/mol,
  one imaginary at −376 / −527 cm⁻¹, KE 0.901 / 0.947, overlap 0.723 / 0.786; at the UMA M1 start
  the forming-bond rule picks the reaction mode (0.841 vs ≤ 0.338).
- **Candidates (ADR-0027, R1 "R1. A"):** `tests/candidate_outputs/v0.5.0/t3_ts1a_n.{xtb,uma}.json`
  and `t3_ts1b_n.{xtb,uma}.json`: the TS state, the search result (with `history` under a key the
  regression excludes), the validation, thermo, barrier, reactant ensemble summaries, the
  reported block, environment and commit sha. C1 = code with a clean tree; run the E2E at C1;
  C2 = only these candidate files.
- **Ledger:** this slice adds `tests/candidate_outputs/v0.5.0/**` to node
  `eta_rxncat_species_runner` (`ensure-node` with the **full** files list:
  `src/eta_rxncat/orchestrator/**, tests/unit/orchestrator/**, tests/e2e/**,
  tests/candidate_outputs/v0.3.0/**, tests/candidate_outputs/v0.5.0/**`; count before/after).

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

**Score: 9/10.** Everything up to the run is fixed and measured at the literature geometries. Open
(stop-and-report, never a loosened bound): where UMA's stationary TS lands and whether GFN2 keeps
a saddle.

## Mini-requirements

1. `tests/e2e/test_t3_diels_alder.py`, markers `e2e` + `slow`, parametrised over both recipes
   (`RECIPE_PARAMS`), cases TS1a_n and TS1b_n; each run under `timeout 3600`.
2. Per case × recipe: the gates above hold; the reported block is complete.
3. Second run: all hits, zero rows created, equal payload (excluding metrics, timing and `history`).
4. Four candidate files committed in C2; their keys are unit-suffixed; no list in energy order.
5. A failing gate leaves the candidate written with `test_outcome: fail` and the failed checks, and
   the slice stops and reports to the lead with the output.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read the v0.3.0 T2 E2E and its helpers.
- [ ] Task 2: the E2E test and any shared helper in `tests/e2e/t3.py`; tier-D tests of the helper.
- [ ] Task 3: required checks; commit C1.
- [ ] Task 4: host check; xtb run (`ETA_RXNCAT_XTB` set), then UMA run (separate calls); second runs.
- [ ] Task 5: commit C2 (candidates only); ledger `ensure-node`; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** gate GFN2 beyond convergence and the mode count (N10, R4); **DO NOT** gate connectivity (N7).
- **DO NOT** loosen a window, A2 or R3 bound; **DO NOT** retry a failed search with other options.
- **DO NOT** start TS1b_n from anything but the promoted M1 product for that recipe.
- **DO NOT** compare `history` (N11).

## Proof contract

- [ ] Both recipes' E2E commands (with the host checks, `timeout`, exit codes and 0 skips) are in the proof.
- [ ] Each gated check per case × recipe is listed with its value.
- [ ] The second runs show 100% hits.
- [ ] C2 contains only `tests/candidate_outputs/v0.5.0/t3_ts1a_n.*` and `t3_ts1b_n.*` (file names only).
- [ ] The required checks exit 0.

## Source material

- Mission G4–G6, R3, R4, R6, R11, R15, R20, HF-3…HF-7; v0.3.0 `tests/e2e/test_e2e5_tier2_cp_cyclopropene.py`; slices 05–07.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.7 (build order; its code and contracts are used here)
