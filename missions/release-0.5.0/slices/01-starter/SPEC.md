---
id: OPR.0.5.0.1
slice: 01-starter
mission: release-0.5.0
status: done
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Unpack the v0.5.0 starter byte-identical as reference with its discrepancy register (DV-01..DV-09) and set PD-009 to decided with TJ's A1/A2 answers."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["docs/prd/v0.5.0/**", docs/prd/PLAN_DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 starter, discrepancy register and PD-009

## Intent

Unpack the v0.5.0 starter as byte-identical reference, write its discrepancy register, and set
PD-009 to `decided` with TJ's A1/A2 answers, so every later question traces to a row.

Context the builder needs:
- `PRDs/Eta-RxnCat-v0.5.0.zip`, sha256 `ecfd9aa35b218b5def341fab83f477538f0b9719269fc30f1d9d53860072eda6`,
  34 files under the top directory `Eta-RxnCat-v0.5.0/` (checked by resolve 2026-11-24).
- TJ Q2 (v0.3.0, standing), verbatim: "B use it as reference only. Keep a list of the
  discrepancies so that if needed, we can go through each of them and fix any issues that arise."
- v0.4.0 precedent: `docs/prd/v0.4.0/DISCREPANCIES.md` (read its header and status vocabulary;
  copy the structure, not the rows) and `docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/.ruff.toml`
  (`exclude = ["*"]`; without it the pre-commit hook lints the starter and refuses the commit).
- PD-009 is row 50 of `docs/prd/PLAN_DISCREPANCIES.md`, status `open`. Its decided text (status
  cell only; nothing else in the file changes):
  `decided (TJ v0.5.0 A1 "Q1. A", row qitem-20261124022519-fc0c0dfa7516da8a: own clean-room P-RFO in Cartesian coordinates from Banerjee 1985 / Baker 1986 / Bofill 1994; no TRIC; geomeTRIC --transition only as a black-box acceptance cross-check; A2 "Q2.  A", row qitem-20261124022519-e5ab60e19dea4068: exactly one mode below -20 cm-1, that mode below -50 cm-1, active-core KE fraction >= 0.60; the covalent-graph topology guard stays at v0.9.0)`.
- The DV rows (mission §5 "Starter discrepancies"), with starter paths relative to
  `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/`:
  - **DV-01 / PD-009** plan "P-RFO … >=50-60%" vs zip "TRIC P-RFO … soft-mode Hessian-refresh /
    damped fallback recovery … >=60% … covalent-graph topology guard"; decided by A1/A2.
  - **DV-02** `optimize/ts_optimizer.py` imports `MolecularState`/`VibrationalMode`/`PotentialEngine`/
    `compute_frequencies_from_hessian`/`_ATOMIC_MASSES_AMU` from modules eta does not have, and
    uses `coords_array()`/`.coordinates` shapes eta does not expose.
  - **DV-03** `_prfo_step` always maximises along the lowest eigenvector; filters eigenvalues by
    `|λ| > 1e-6` instead of projecting rigid motions; fixed 25-step Newton without a convergence
    check; `1e-8` added to a denominator. (Eta: mission §5 "P-RFO", R2, R7.)
  - **DV-04** `optimize_transition_state`: a single RMS-gradient test (3e-4); no step acceptance or
    trust update; energy and final Hessian unvalidated; no failure path. (Eta: R14, R24, R27.)
  - **DV-05** `validate_transition_state_modes` counts modes below −40 cm⁻¹ (TJ: count below −20,
    cutoff −50); default fraction 0.50 (TJ: 0.60); skips the fraction check when it is `None`. (Eta: A2, R16.)
  - **DV-06** default mass 12.0 for unknown elements (eta's `thermo.masses` raises).
  - **DV-07** `tests/unit/test_v050_ts_prfo.py`: diagonal model Hessian, so the lowest mode is the
    reaction mode by construction; mode following never exercised. (Eta: G1.)
  - **DV-08** no TS identity check beyond counting; no barrier or standard-state handling. (Eta: R3, §5 "Barrier".)
  - **DV-09** one row for each further starter file whose behaviour differs from the mission SPEC,
    or the single line "none found" with the list of files read.

  Name each row's status `decided` and the implementing slice (01–13) from the mission's execution
  checklist. Reading the starter's `ts_optimizer.py` **to write DV rows is the only permitted read
  of TS-optimizer code**, and no code from it is ever copied (seat rule 1).

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

**Score: 10/10.** File operations and a register; every row's text is given.

## Mini-requirements

1. `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/` holds the zip's 34 files byte-identical; a sha256 list of
   all 34 (sorted by path) is in the register's header, with the zip's sha256.
2. `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/.ruff.toml` contains `exclude = ["*"]` and is named in the
   register as a gate file that is not part of the starter.
3. `docs/prd/v0.5.0/DISCREPANCIES.md` has DV-01…DV-09 as above, each with status and slice.
4. `git diff <Base> -- docs/prd/PLAN_DISCREPANCIES.md` changes exactly PD-009's status cell to the
   text above, and nothing else.
5. The required checks pass with the starter in place (the lint hook skips it).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; `sha256sum PRDs/Eta-RxnCat-v0.5.0.zip`
  equals the value above (else stop).
- [x] Task 2: unzip into `docs/prd/v0.5.0/` from a scratch copy under `TMPDIR`; compare every
  file's sha256 with the zip listing.
- [x] Task 3: `.ruff.toml`; `DISCREPANCIES.md`; PD-009 cell.
- [x] Task 4: required checks; commit; `hypergraph_updater.py` for node `eta_rxncat_scaffold`
  (`docs/**` already covers the files; no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** change any other `PLAN_DISCREPANCIES.md` cell or hash.
- **DO NOT** copy starter code into `src/` or `tests/`; **DO NOT** run the starter's tests.
- **DO NOT** edit `PRDs/`.

## Proof contract

- [ ] The 34 sha256s of `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/` equal the zip's (command and output in the proof).
- [ ] `DISCREPANCIES.md` has DV-01…DV-09 with statuses and slices.
- [ ] `git diff <Base> -- docs/prd/PLAN_DISCREPANCIES.md` shows only PD-009's status cell.
- [ ] The required checks exit 0.

## Source material

- `PRDs/Eta-RxnCat-v0.5.0.zip`; `docs/prd/PLAN_DISCREPANCIES.md`; `docs/prd/v0.4.0/DISCREPANCIES.md` (format); mission §5 "Starter discrepancies".

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- none (first slice)
