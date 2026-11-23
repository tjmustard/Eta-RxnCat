---
id: OPR.0.4.0.5
slice: 05-constrained-relax
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Implement relax_constrained_core: core-frozen pre-relaxation through Optimizer.minimize with frozen_atom_indices and never a dihedral constraint, raising CoreDisplacementError above 1e-8 A, proved with a recording fake and UFF."
depends_on: [OPR.0.4.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["src/eta_rxncat/mapping/**", "tests/unit/mapping/**", tests/unit/test_package.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/mapping/test_relax.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 core-frozen pre-relaxation (mapping.relax)

## Intent

Implement `mapping.relax.relax_constrained_core`. It pre-relaxes a grafted structure with its
conserved core frozen through v0.3.0's `Optimizer.minimize(frozen_atom_indices=…)`, never with a
dihedral constraint, and raises `CoreDisplacementError` if any core atom moves more than 1e-8 Å.
Prove it with a recording fake and with UFF.

Context the builder needs:
- TJ Q2, verbatim: "Q2. (b)". Core-frozen pre-relaxation is in v0.4.0. The core is **frozen,
  not restrained**, and reuses geomeTRIC `$freeze` through the existing `frozen_atom_indices`.
  v0.3.0 measured ≤ 4e-9 Å displacement on UFF water.
- **`Optimizer.minimize` (`src/eta_rxncat/optimize/base.py`):**
  `minimize(state, engine, *, frozen_atom_indices=(), dihedral_constraints=(), options=None) -> OptimizationResult`.
  - It raises `OptimizerInputError` (bad input), `OptimizationFailedError` (ladder exhausted), or
    an `EngineError` (propagated).
  - `OptimizationResult.converged` is `Literal[True]`; failures raise.
  - `GeometricOptimizer` keys: `coordsys`, `convergence_set`, `maxiter` (default 300), `trust`.
  - Read the code; do not change `optimize/`.
- **Audit 04's note** (v0.3.0): frozen atoms plus a dihedral constraint hung in 2 of 4 hash seeds
  (`ENFORCE_THRESHOLD` docstring, `geometric_impl.py`). So no v0.4.0 path ever combines them
  (mission R6).
- **Contract** (mission §5 "Algorithms" X1–X4):
  - **X1.** `relax_constrained_core(state: MolecularState, engine: Engine, optimizer: Optimizer, core_indices: Sequence[int], options: Mapping[str, ScalarValue] | None = None) -> OptimizationResult`.
  - **X2.** Before any engine call, raise `MappingError` if:
    - `core_indices` is empty, has duplicates, or has an index out of range for `state`;
    - `options` has a key `"constraints"`.
  - **X3.** Call `optimizer.minimize(state, engine, frozen_atom_indices=tuple(core_indices), options=options)`,
    passing **no** `dihedral_constraints` argument. Do not catch `EngineError` or
    `OptimizerError` (or any subclass); they propagate unchanged.
  - **X4.** Compute `max_k ‖final[k] − input[k]‖` over the core atoms. There is no superposition:
    the frame is the template's. If it is > 1e-8 Å, raise `CoreDisplacementError(atom,
    displacement_angstrom)` for the worst atom. Otherwise return the `OptimizationResult`
    unchanged.

  No `assert` statements. The docstring says the result is a pre-relaxation of a TS guess,
  **not a minimum**, and must never be passed to `check_ground_state`.
- `relax.py` imports only `eta_rxncat.core`, `eta_rxncat.optimize` (interface and errors) and
  `eta_rxncat.engines` (the `Engine` type). `eta_rxncat.optimize` loads only numpy among heavy
  modules (red team measured). Add `eta_rxncat.mapping.relax` to the import test (no `geometric`,
  `torch`, `pyscf`, `fairchem`, `rdkit` at import).

**Seat rules for every v0.4.0 slice.** These are self-contained. The mission SPEC is
`missions/release-0.4.0/SPEC.md`; its R-rows are cited by number.

- **Clean room (TJ Q1, hard rule).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach".
  - No seat opens, clones, fetches or searches Eta_Scripts or nMap in any form (GitHub, a local
    or cached copy, a web search, a code search).
  - No seat asks the clean-room rig's seats about code.
  - Behaviour comes only from this SPEC, TJ's M1 spec and the approved documents in
    `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/`.
  - Never copy code from the starter (`docs/prd/v0.4.0/`).
  - A conflict between a clean-room document and this SPEC is a stop-and-report for a replan.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.4.0`, cut re-entrantly from Base, which is
  the mission commit on main (parent `c3506e6`). One code commit per slice, unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff.
- **Code graph first.** The first command of the slice is
  `python3 .agents/scripts/hyper_codegraph.py index`, and it must print `index: ok` (the red team
  saw `stale_index`). Anything else stops the slice. The audit treats
  `code_graph.status != ok` as a finding. The graph only widens a blast radius, never narrows it.
- **Ledger.** Write it only with `hyper_ledger.py` / `hypergraph_updater.py`, never by hand.
  - On existing nodes use `ensure-node --id <node>` with the **full** `--files` list (it
    replaces).
  - Count the node's globs before and after.
  - `eta_rxncat_engines` is not touched.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF.** HACF is v0.6.2. No `HACF-install.sh` (a plain run silently DOWNGRADES to 0.6.1 right
  now), no `HACF-uninstall.sh`, no `hyper_migrate.py apply`.
- **OpenRig 0.7.21.** `hyper_spec.py` and `hyper_migrate.py` warn "outside the pinned contract",
  `hyper_spec.py proof` writes the proof natively, and `verify` skips `rig scope audit`. All of
  this is expected: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git.
  Every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host memory (heavy runs).** Before any E2E, GPU, relaxation or full-suite run:
  - run `free -g` and list other rigs' heavy python/pytest/engine processes (`ps`);
  - if another heavy run is active, wait (poll at most every 5 minutes with Monitor or a
    background wait, not a foreground sleep);
  - record the check in the proof.

  Heavy runs are sequential. Never kill another rig's process.
- **v0.3.0 lessons (mission R23):**
  - **R54:** every numeric key in an output carries its unit suffix.
  - **R55:** no list in a compared output is in record or energy order; it is fixed by the fixture
    or sorted by an energy-independent key.
  - **R56:** a test records its real outcome through one `gated_outcome`, and `pending_*` fails
    under `ETA_RXNCAT_ACCEPTANCE=1`.
  - **R50:** any code that reads a store or runner payload checks `failed_reason` first (v0.4.0
    adds no such reader).
  - **Candidates (ADR-0027):** code commit C1 with a clean tree, run the E2E at C1, then commit
    only `tests/candidate_outputs/v0.4.0/*` as C2.
- **Required checks** (AGENTS.md), all exit 0 before each commit:
  - `uv sync --locked`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy`
  - `uv run pytest`
  - `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception.
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it, and never loosen a
  tolerance (TJ's or this SPEC's).
- **Never** push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 9/10.** The behaviour is fixed. Whether xtb and UMA hold 1e-8 Å (H-M3) is measured in
slice 06, not here.

## Mini-requirements

1. **Recording fake optimizer** (tier D; a test double implementing the `Optimizer` interface):
   - asserts it received `frozen_atom_indices == (1, 2, 3, 5)`, `dihedral_constraints == ()`
     (default) and the given `options`;
   - returns a result with the core unchanged; `relax_constrained_core` returns it unchanged.
2. **Displacement:** a fake returning the core moved by 2e-8 Å on one atom raises
   `CoreDisplacementError` with that atom and the displacement. A fake moving only non-core atoms
   by 1 Å returns normally.
3. **Refusals before any call:** empty core, a duplicate, an out-of-range index, and
   `options={"constraints": "x"}` each raise `MappingError`, and the fake records zero calls.
4. **Propagation:** a fake raising `OptimizationFailedError`, and one raising an `EngineError`
   subclass, propagate the same exception object (`is`).
5. **UFF (tier D, default suite; geomeTRIC is in the dev group):**
   - `GeometricOptimizer` on the RDKit UFF engine: read `tests/unit/optimize/` for how v0.3.0
     builds it;
   - a small distorted molecule (e.g. n-butane with one C–H stretched to 1.3 Å), with a 3-atom
     core frozen;
   - converges; the core max displacement is ≤ 1e-8 Å (record the measured value in the proof);
   - `n_steps ≥ 1`.
6. **Import and assert tests** (from slice 03) include `mapping.relax`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read `optimize/base.py`, `optimize/geometric_impl.py`, `tests/unit/optimize/`.
- [ ] Task 2: `relax.py`; export `relax_constrained_core`.
- [ ] Task 3: `tests/unit/mapping/test_relax.py`; required checks (host check before the full suite).
- [ ] Task 4: commit; updater (node `eta_rxncat_mapping`; no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** change anything in `src/eta_rxncat/optimize/` or `engines/`.
- **DO NOT** pass `dihedral_constraints`, or add a restraint or penalty feature.
- **DO NOT** catch engine or optimizer errors, or retry.
- **DO NOT** call `check_ground_state`, or name the result a minimum.
- **DO NOT** widen 1e-8 Å; a UFF miss is stop-and-report.

## Proof contract

- [ ] `uv run pytest tests/unit/mapping/test_relax.py -q` passes; the proof records the UFF core displacement.
- [ ] A test or grep shows `minimize` is called without `dihedral_constraints` in `src/eta_rxncat/mapping/relax.py`.
- [ ] The import test includes `eta_rxncat.mapping.relax` and passes.
- [ ] The required checks exit 0.

## Source material

- Mission SPEC §5 "Algorithms" X1–X4, R6, R7, H-M3; `src/eta_rxncat/optimize/`; ADR-0023, ADR-0024.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.4 (the mapping package and its errors; build order)
