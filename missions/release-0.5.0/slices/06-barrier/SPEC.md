---
id: OPR.0.5.0.6
slice: 06-barrier
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Add BarrierSpec and activation_free_energy: dE, dH and dG dagger at 1 M and 1 atm from a TS record and reactant ensembles, conservation checked without a TS SMILES."
depends_on: [OPR.0.5.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator/test_barrier.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 activation barrier ΔG‡ at 1 M and 1 atm (orchestrator)

## Intent

Add `orchestrator/barrier.py` — `BarrierSpec` and `activation_free_energy` — giving ΔE‡, ΔH‡ and
ΔG‡ at 1 M and 1 atm from a TS record and its reactants' ensembles, with atom and charge
conservation checked without a TS SMILES.

Context the builder needs:
- **Read:** `orchestrator/reaction.py` (`ReactionSpec._conserved`, `_weighted`,
  `standard_state_shift_kcal_mol(config)` = RT ln(cRT/p) = 1.8943 kcal/mol at 298.15 K, 1 M,
  1 atm; `reaction_free_energy`; `ReactionEnergies`), `core/ensemble_models.py`
  (`ConformerEnsemble.ensemble_gibbs_hartree`, `boltzmann_weights`, `temperature_k`),
  `core/ts_models.py` (`TransitionStateRecord`). `ReactionSpec` and `reaction_free_energy` are not
  changed (mission R1).
- **Contract (mission §5 "Barrier"):**
  - `BarrierSpec` (pydantic, `extra="forbid"`, frozen): `reactants: tuple[tuple[str,
    PositiveInt], ...]` (min length 1), `ts_id: str` (min length 1), `smiles: dict[str, str]`
    (every reactant id present; each parses).
  - `BarrierEnergies` (pydantic, frozen): `dE_dagger_kcal_mol`, `dH_dagger_kcal_mol`,
    `dG_dagger_1atm_kcal_mol`, `dG_dagger_1M_kcal_mol: float`, `delta_n: int`.
  - `activation_free_energy(spec, ensembles: Mapping[str, ConformerEnsemble], ts:
    TransitionStateRecord, config: ThermoConfig) -> BarrierEnergies`:
    - `ts.ts_id == spec.ts_id`, else `ValueError`;
    - conservation: Σ coeff × element counts of `Chem.AddHs(MolFromSmiles(smiles))` equals the
      `Counter` of `ts.state.symbols`; Σ coeff × formal charge equals `ts.state.charge`; a
      mismatch raises `ValueError` naming both sides;
    - every ensemble's `temperature_k` and `ts.thermo.config.temperature_k` equal
      `config.temperature_k`, else `ValueError`;
    - reactants: E and H Boltzmann-weighted as `_weighted` does; G = `ensemble_gibbs_hartree`;
      TS: E = `thermo.electronic_energy_hartree`, H = E + `thermal_correction_enthalpy_hartree`,
      G = `thermo.gibbs_free_energy_hartree` (degeneracy 1, TJ Q-TJ2 "A");
    - Δn = 1 − Σ coeff; `dG_dagger_1M = (G_TS − Σ coeff·G_R)·HARTREE_KCAL_MOL`;
      `dG_dagger_1atm = dG_dagger_1M − Δn·standard_state_shift_kcal_mol(config)`.
- For a bimolecular TS (Δn = −1) at 298.15 K: `dG_1atm − dG_1M = +1.894` kcal/mol, which turns
  Liu's 1 atm 19.637 into eta's 1 M 17.742 (mission HF-9).

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

**Score: 10/10.** Pure arithmetic over existing records, with the conventions fixed.

## Mini-requirements

1. Hand-built ensembles and a hand-built `TransitionStateRecord` (fake thermo values): ΔE‡, ΔH‡,
   ΔG‡(1 M) equal the hand sums within 1e-9 kcal/mol; `dG_1atm − dG_1M = −Δn·1.8943…` within 1e-9
   for Δn = −1 and for a unimolecular TS (Δn = 0, equal values).
2. Conservation: a reactant set short by one H, and one with the wrong charge, each raise
   `ValueError` naming both sides.
3. Mismatched `ts_id` and a temperature mismatch each raise `ValueError`.
4. `reaction_free_energy` and `ReactionSpec` tests pass unchanged.
5. Liu check (tier D, no engine): with E/G taken as the literature numbers of `TS1a_n`, Cp and
   cyclopropene (mission HF-9; single-record fakes), `dG_dagger_1atm_kcal_mol` = 19.637 ± 0.001 and
   `dG_dagger_1M_kcal_mol` = 17.742 ± 0.001.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read the code named above.
- [x] Task 2: `orchestrator/barrier.py`; export.
- [x] Task 3: `tests/unit/orchestrator/test_barrier.py`; required checks.
- [x] Task 4: commit; updater for node `eta_rxncat_species_runner`.

## 4. The Negative Space (Constraints)

- **DO NOT** build a TS SMILES or pass a TS through `ReactionSpec` (R1).
- **DO NOT** apply any TS degeneracy other than 1 (Q-TJ2 A).
- **DO NOT** compare a 1 atm value with a 1 M value without the shift (N9).

## Proof contract

- [ ] `uv run pytest tests/unit/orchestrator/test_barrier.py -q` passes, including the Liu check.
- [ ] Existing reaction tests pass unchanged.
- [ ] The required checks exit 0.

## Source material

- Mission §5 "Barrier", R1, HF-9; `src/eta_rxncat/orchestrator/reaction.py`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.5 (build order; its code and contracts are used here)
