---
id: OPR.0.5.0.10
slice: 10-e2e-cyclobutenone
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Run the Paton N4 cyclopentadiene + cyclobutenone TS search and barrier on GFN2 and UMA from Paton's geometry and commit the candidates."
depends_on: [OPR.0.5.0.8]
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

# MiniPRD: v0.5.0 Tier 3 E2E — the cyclobutenone barrier (Paton N4, unmapped)

## Intent

Run the cyclopentadiene + cyclobutenone endo TS search (Paton 2011 N4) end to end on both recipes
from Paton's geometry, with a validated TS, ΔG‡ against the reactant ensembles, and committed
candidates.

Context the builder needs:
- **TJ, verbatim:** A3 "Q3. A"; A4 "Q4. A" (N4 [15.6, 29.6], UMA, 1 M); Q-TJ3 (third of "A / A /
  A"): GFN2 gates convergence and the mode count; amended by **Q-TJ4 A** (mission R32), verbatim:
  "GFN2 also gates TS identity (overlap >= 0.50, in phase, KE >= 0.60) on every other Tier 3
  case. UMA unchanged." N4 is one of those cases.
- **Inputs (slice 07):** `t3_n4_unmapped.yaml` (active `[1, 2, 9, 10, 12, 13]`, forming bonds
  `[[1, 9], [2, 10]]`), `xyz/TS_N4.xyz`, `xyz/cyclobutenone.xyz`, `xyz/1_cyclopentadiene.xyz`.
- **Paton's energies:** its "E(M06-2X)" column is the **thermally corrected** energy, not the
  electronic energy (Cp: Paton E −193.906541 vs Liu's electronic −194.004692, while both G agree
  to 2e-6 Eh). The reference is G only: 24.463 kcal/mol at 1 atm, 22.569 at 1 M (HF-9). Never
  report a literature ΔE‡ for N4.
- **Runners, stores, gates, reports, candidate rule:** exactly as slice 08 (read its SPEC and
  test). Gated: both — converged and `mode_count_passed_bool`; UMA — KE, identity, window; GFN2 — the identity core (R32, TJ Q-TJ4 A): `forming_stretch_overlap` ≥
  `min_forming_stretch_overlap` (0.50), `forming_bonds_in_phase_bool` true, `active_core_passed_bool`
  (KE ≥ 0.60), from the validator's fields, **not** `identity_passed_bool` (which includes the
  forming-distance window; reported on GFN2); both — second-run hits, conservation. Reported: GFN2 extras, the GFN2 window and ΔG‡, connectivity, RMSD of the final TS to
  Paton's N4 (identity map), the asymmetric forming distances (Paton 2.166 / 2.309 Å, HF-2).
- **Measured at Paton's geometry (HF-3, HF-4):** UMA ΔG‡ 26.50 (margin 3.10), one imaginary at
  −517.9 cm⁻¹, KE 0.951, overlap 0.802; GFN2 12.91, −471.4 cm⁻¹, 0.951.
- **Candidates:** `tests/candidate_outputs/v0.5.0/t3_n4.{xtb,uma}.json`.

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

**Score: 9/10.** Fixed as slice 08; open only where the stationary TS lands.

## Mini-requirements

1. `tests/e2e/test_t3_cyclobutenone.py` (`e2e` + `slow`), both recipes, under `timeout 3600`.
2. Gates as above; no literature ΔE‡ anywhere in the candidate.
3. Second runs: 100% hits on the reactants' stages and on every TS stage that ran in the first run
   (`ts_opt`, a cached failure row counts; `frequency` only if it ran), no new rows (G6, R32). Use slice 09's fixed
   `second_run_ts_all_hits`.
4. Two candidate files in C2.
5. A failing gate: candidate written with `test_outcome: fail`, stop and report.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read slice 08's test and helpers.
- [ ] Task 2: the test (reuse `tests/e2e/t3.py`).
- [ ] Task 3: required checks; C1.
- [ ] Task 4: host check; xtb then UMA (separate calls); second runs.
- [ ] Task 5: C2; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** use Paton's E column as an electronic energy.
- **DO NOT** gate GFN2 beyond convergence, the mode count and the identity core (R32); **DO NOT**
  gate the GFN2 window; **DO NOT** loosen any bound.

## Proof contract

- [ ] Both recipes' commands with host checks, `timeout`, exit codes, 0 skips.
- [ ] Each gated value per recipe.
- [ ] Second runs 100% hits.
- [ ] C2 contains only `t3_n4.*` (file names only).
- [ ] The required checks exit 0.

## Source material

- Mission R4, R8, R16, HF-2…HF-4, HF-9; slices 07, 08.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.8 (build order; its code and contracts are used here)
