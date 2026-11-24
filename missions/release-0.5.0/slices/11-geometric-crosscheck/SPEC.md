---
id: OPR.0.5.0.11
slice: 11-geometric-crosscheck
mission: release-0.5.0
status: done
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Cross-check every Tier 3 TS against geomeTRIC's TS search run as a black box (documented CLI, subprocess, same start, engine and seed Hessian) and record the comparison, reported only."
depends_on: [OPR.0.5.0.9, OPR.0.5.0.10]
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

# MiniPRD: v0.5.0 geomeTRIC black-box TS cross-check (acceptance only)

## Intent

Cross-check every Tier 3 TS against geomeTRIC's own TS search run strictly as a black box —
documented CLI only, in a subprocess, from the same start, on the same eta engine and seed
Hessian — and record the comparison for TJ, so a home-written P-RFO that lands on a different
saddle is visible.

Context the builder needs:
- **TJ A1, verbatim "Q1. A":** geomeTRIC's `--transition` is used only as a black-box cross-check
  in acceptance, never in the product path. **Nobody reads geomeTRIC source** (any file of the
  installed package) — only `geometric-optimize --help`.
- **Mechanism (mission R5), documented flags only** (`.venv-accept-uma/bin/geometric-optimize
  --help`, geomeTRIC 1.1.1): `--engine ase` with `--ase-class <module.Class>` and
  `--ase-kwargs <json>`; `--transition yes`; `--hessian file+last:<path>` ("Read initial Hessian
  data in NumPy format from path … then compute for the last structure"); `--prefix`. The coordinate
  system is geomeTRIC's default. `.venv-accept-uma` has geometric 1.1.1, ase 3.29.0 and fairchem
  2.26.0 (resolve checked); eta's xtb subprocess engine also runs there with `ETA_RXNCAT_XTB`.
- **Shim** `tests/e2e/eta_geometric_shim.py` (acceptance-only test code; the only file in the repo
  that imports `ase`, N1): `EtaCalculator(ase.calculators.calculator.Calculator)` with
  `implemented_properties = ["energy", "forces"]`, kwargs `recipe` (`"xtb"` | `"uma"`) built with
  `tests/e2e/e2e_env.py:recipe_for` + `orchestrator.build_engine`; `calculate()` converts the ASE
  `Atoms` to a `MolecularState` (charge 0, multiplicity 1), calls `engine.evaluate(forces=True)`,
  and returns energy in eV and forces in eV/Å (`engines.units`: `HARTREE_EV`, `BOHR_ANGSTROM`).
- **Per case × recipe** (five cases, slices 08–10): the same start geometry as eta's search (for
  TS1b_n and TS4a, the recipe's start as recorded in that slice's candidate inputs — rebuild it the
  same way; never read a candidate file), the seed Hessian = eta's engine Hessian at that start
  written with `numpy.savetxt` (Eh/Bohr², geomeTRIC's documented NumPy text format), the XYZ
  written in Å. Run `timeout 3600 geometric-optimize <start>.xyz --engine ase --ase-class
  eta_geometric_shim.EtaCalculator --ase-kwargs '{"recipe": "<r>"}' --transition yes --hessian
  file+last:<seed>.txt --prefix <scratch>/<case>.<r>` with `PYTHONPATH=tests/e2e`, cwd a scratch
  dir under `TMPDIR`. If geomeTRIC's TS-mode Hessian file must use different units, that is read
  from `--help` only; if `--help` does not say, record the assumption in the proof.
- **Recorded** (acceptance record `cross_check.<case>.<recipe>`): exit code, wall time,
  `converged_bool` (geomeTRIC's final-structure file exists and its log says converged),
  `geometric_not_converged` otherwise; ΔE (geomeTRIC TS − eta TS, eta's engine energy at both,
  kcal/mol); heavy-atom RMSD after Horn superposition (`mapping.superpose`, identity map: same
  start, same atom order); eta's frequency Hessian at geomeTRIC's TS → `validate_transition_state`
  with the case's forming bonds and active set → its `passed_bool`, reasons, ν, KE, overlap.
  **Reported only** (US-014, P1): the verdict needs each run attempted and recorded, never
  agreement. GFN2 and UMA both run.
- The licence look at geomeTRIC's "BSD 3-clause Non-AI" licence is open with TJ; this use (a CLI
  subprocess in an acceptance env, nothing vendored or imported in `src/`) is the same exposure as
  the existing acceptance cross-checks. Report, do not decide.

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

**Score: 8/10.** The mechanism uses only documented flags, but whether geomeTRIC's ASE engine
path, the Hessian file format and its TS mode behave as `--help` describes is unverified until the
first run. A mechanism failure is recorded per case as the outcome, and if no case can run at all,
stop and report to the lead (the cross-check is reported-only, so the lead decides whether the
mission continues without it).

## Mini-requirements

1. The shim passes a tier-D test (marker `acceptance`) on a 3-atom fake: energy and forces in eV
   and eV/Å match eta's values × the unit constants within 1e-12 relative.
2. `tests/e2e/test_t3_cross_check.py` (markers `e2e` + `slow` + `acceptance`) runs the ten
   subprocesses one at a time (GPU ones on a clear host) and writes the `cross_check` fragment
   `tests/candidate_outputs/v0.5.0/t3_cross_check.json`.
3. Every case × recipe has a record with the fields above, `converged_bool` true or a
   `geometric_not_converged` / `geometric_failed` status with the exit code and log tail.
4. `grep -rn "import ase\|from ase" src/` is empty (N1).
5. No geomeTRIC module is imported in any eta process (`python -X importtime` on the test process,
   or a test asserting `"geometric" not in sys.modules` after the run).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `--help`; read slices 08–10's tests for the starts.
- [x] Task 2: shim + its test; the cross-check test; required checks; C1.
- [x] Task 3: host check; run (xtb first, then UMA; separate calls; `timeout 3600` each subprocess).
- [x] Task 4: C2 (`t3_cross_check.json` only); updater.

## 4. The Negative Space (Constraints)

- **DO NOT** read geomeTRIC source or call any geomeTRIC function in-process (N2, N4).
- **DO NOT** import `ase` outside `tests/e2e/eta_geometric_shim.py` (N1).
- **DO NOT** feed geomeTRIC's TS into the cache, the barrier or a gate.

## Proof contract

- [ ] The ten subprocess commands with host checks, `timeout`, exit codes.
- [ ] The cross-check fragment lists ten records.
- [ ] The `grep` and the `sys.modules` checks are empty / pass.
- [ ] The required checks exit 0.

## Source material

- Mission R5, R3, N1, N2, N4; `geometric-optimize --help`; slices 05, 08–10.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.9 (build order; its code and contracts are used here)
- OPR.0.5.0.10 (build order; its code and contracts are used here)
