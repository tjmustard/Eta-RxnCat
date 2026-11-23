---
id: OPR.0.3.0.4
slice: 04-optimizer
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Create eta_rxncat.optimize: the Optimizer interface and errors, GeometricOptimizer on geomeTRIC's lower-level API in a logging/file sandbox with a recorded three-step ladder, and move geomeTRIC from the base runtime into the opt-geometric extra and dev group with its own licence profile (TJ Q3 A)."
depends_on: [OPR.0.3.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_optimize
parent: null
hacf_touches: ["src/eta_rxncat/optimize/**", "tests/unit/optimize/**", pyproject.toml, uv.lock, ".github/workflows/ci.yml", AGENTS.md, tools/licence_gate.py, "tests/unit/tools/**", tests/unit/test_package.py, tests/conftest.py, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/optimize, tests/unit/tools, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Optimizer interface, geomeTRIC in the opt-geometric extra, recovery ladder and licence profile

## Intent

Create `eta_rxncat.optimize` (new ledger node `eta_rxncat_optimize`): the `Optimizer` interface and
error contract, `GeometricOptimizer` driving geomeTRIC 1.1.1 through its lower-level API in a
logging/file sandbox, a recorded three-step recovery ladder, and move geomeTRIC out of the base
runtime into the `opt-geometric` extra (and the dev group) with its own licence profile (TJ Q3 "A").

Context the builder needs:
- TJ Q3: "Q3. A" — an `Optimizer` interface; geomeTRIC becomes one optimizer in the optional extra
  `opt-geometric`, which carries its licence exception; core and the base install never import it.
  The exemption itself is TJ's v0.1.0 decision (ADR-0011): geomeTRIC 1.1.1, BSD 3-clause Non-AI
  (clause 4 restricts AI-training datasets), metadata UNKNOWN. A PROPOSED decision amending
  ADR-0011's scope has been filed by resolve; this slice does not write an ADR.
- **R2 (red team, measured):** `geometric.optimize.run_optimizer` calls `logging.config.fileConfig`
  on every run, which closes every existing host handler; a snapshot/restore cannot undo that.
  **Never call `run_optimizer`.** Replicate its minimal path from `geometric/optimize.py` (read lines
  1157–1300 first; H6): `OptParams(**kw)` from `geometric.params`, a `geometric.molecule.Molecule`
  with `elem` and `xyzs` (Å), then `IC = CoordClass(M, build=True, connect=connect,
  addcart=addcart, constraints=Cons, cvals=CVals[0] or None)`, then
  `geometric.optimize.Optimizer(coords_bohr, M, IC, bridge_engine, dirname, params).optimizeGeometry()`.
  **`CoordSysDict` is not importable** (R44, measured): it is a local inside `run_optimizer`
  (`optimize.py:1259`). Build the table yourself from `geometric.internal`, copied from that line
  range: `tric` → (`DelocalizedInternalCoordinates`, connect False, addcart False); `cart` →
  (`CartesianCoordinates`, False, False); `dlc` → (`DelocalizedInternalCoordinates`, True, False);
  `hdlc` → (`DelocalizedInternalCoordinates`, False, True). Constraints come from
  `geometric.prepare.parse_constraints(M, text)` (returns `Cons, CVals`): frozen atoms
  `"$freeze\nxyz <1-based list>\n"`, dihedrals `"$set\ndihedral i j k l <deg>\n"` (1-based).
- **TJ F32 "A the planar geometry" (R42):** v0.3.0 needs one dihedral-constrained optimization (T1's
  planar s-cis point), so dihedral constraints are part of the `Optimizer` interface from this
  slice on. Resolve verified on geomeTRIC 1.1.1 (UFF, T1 SMILES, seed 42, the path above with
  `tric` and `$set dihedral 1 2 3 4 0.0`): φ reached −0.0068° in 47 steps. **`cart` refuses every
  constraint** with `RuntimeError("Do not use constraints with Cartesian coordinates")` (R45), so a
  constrained run's ladder step 3 is `hdlc`, not `cartesian`. Whether `hdlc` accepts `$set
  dihedral` and `$freeze xyz` is H15 (Task 1).
- **R5:** `geometric==1.1.1` goes in the **dev** group too, so `.venv` (required checks) has it and
  every optimizer test runs in the default `uv run pytest`. No new marker. The `--no-dev` runtime
  gate keeps base geomeTRIC-free.
- **R14:** the expected `uv lock` diff: `geometric`, `networkx`, `six` leave the base runtime closure
  (they remain under the extra, the dev group and `gpu4pyscf-cuda12x`); no package changes version.
  Anything else → stop and report.
- H1: `gpu4pyscf-cuda12x` depends on `geometric`, so the `gpu`, `mlip-mace`, `mlip-uma` profiles
  (CI syncs them `--extra gpu …`, `.github/workflows/ci.yml`) keep the exemption.
- `tools/licence_gate.py:35` hard-codes `PROFILES = ("base", "gpu", "mlip-mace", "mlip-uma")`.
- geomeTRIC 1.1.1 facts (red team): convergence sets exactly `GAU`, `NWCHEM_LOOSE`, `GAU_LOOSE`,
  `TURBOMOLE`, `INTERFRAG_TIGHT`, `GAU_TIGHT`, `GAU_VERYTIGHT` (`params.py:187`); failures
  `GeomOptNotConvergedError`, `GeomOptStructureError` (`geometric.errors`); geomeTRIC's own
  `EngineError` is a different class from `eta_rxncat.engines.EngineError`, and our engine errors
  propagate through `Engine.calc`.
- **Scaffold:** this slice changes scaffold files (`pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`,
  `AGENTS.md`, `tools/licence_gate.py`, `tests/unit/tools/**`, `tests/unit/test_package.py`) and
  moves `src/eta_rxncat/optimize/**` out of scaffold: `ensure-node --id eta_rxncat_scaffold --files`
  with the full current list minus that glob. Create the new node: `ensure-node --id
  eta_rxncat_optimize --dimension Module --depends-on eta_rxncat_core,eta_rxncat_engines --files
  'src/eta_rxncat/optimize/**,tests/unit/optimize/**' --associated-file
  src/eta_rxncat/optimize/base.py --description-file <file>`. `eta_rxncat_cli` is in the blast radius
  through `pyproject.toml`/`uv.lock` (needs_review only).

**Seat rules for every v0.3.0 slice (self-contained; the mission SPEC is `missions/release-0.3.0/SPEC.md`):**
- Branch `feature/eta-rxncat-v0.3.0`, cut re-entrantly from Base `7993284`. One code commit per
  slice; record `Start` (HEAD when you begin) in your handoff.
- First command of the slice: `python3 .agents/scripts/hyper_codegraph.py index`. It must print
  `index: ok`; anything else stops the slice. The audit treats `code_graph.status != ok` as a
  finding. The code graph only widens the blast radius; it never narrows it.
- Ledger: only `hyper_ledger.py` / `hypergraph_updater.py`. Use `ensure-node --id <node>` on
  existing nodes and pass the **full** `--files` list (it replaces). `ensure-node --from-spec` no
  longer drops other slices' files (HACF v0.6.1 E5), but count the node's globs before and after
  anyway. Never edit `spec/compiled/architecture.yml` by hand. `eta_rxncat_engines` is not touched.
- Scratch: `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs). Remove
  temp clones, venvs and scratch directories at the end of each step.
- No `HACF-install.sh`, `HACF-uninstall.sh` or `hyper_migrate.py apply`. Ignore any "review it with
  hyper_migrate.py plan" line (known false positive). On OpenRig 0.7.21, `hyper_spec.py` and
  `hyper_migrate.py` warn "outside the pinned contract" and `hyper_spec.py proof` writes the proof
  natively: expected, note it in the proof, not a finding.
- Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git: every `git diff`,
  `git show`, `git log -p` over a range that contains a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`. Never write `tests/fixtures/`. `PRDs/` is read-only.
- Required checks (AGENTS.md), all exit 0 before the commit: `uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, and
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- Licence (TJ, verbatim): "I would prefer to keep ASE out as it would be a major core dependency.
  The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP,
  conf search can be copy left. Because they can be replaced with a new engine later. But the core
  remains." / "It's fine that the engine MACE pulls in ASE just not the core." No agent-made
  licence exception.
- A host fact that does not hold, a failed engine run, or a bound that measured noise breaks is
  stop-and-report to the lead with the output — never worked around, never a loosened tolerance.
- Never push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 9/10.** The API path, the sandbox test and the lock diff are fixed; H6 confirms the
lower-level API details before the bridge is written.

## Mini-requirements

1. `optimize/errors.py`: `OptimizerError` → `OptimizerUnavailableError` (message contains
   `uv sync --extra opt-geometric`), `OptimizerInputError`, `OptimizationFailedError(steps:
   tuple[str, ...], last_energy_hartree: float | None)`.
2. `optimize/base.py`: `class Optimizer(abc.ABC)` with `identity -> OptimizerIdentity`, `OPTIONS:
   ClassVar[Mapping[str, OptionSpec]]` (reuse `eta_rxncat.engines.options.OptionSpec` and the
   ADR-0016 resolution rule: unknown or mistyped option → `OptimizerInputError`), and
   `minimize(state, engine, *, frozen_atom_indices=(), dihedral_constraints=(), options=None) ->
   OptimizationResult`. `resolved_options(options) -> dict[str, ScalarValue]`.
   `DihedralConstraint(atoms: tuple[int, int, int, int], value_deg: float)`: frozen pydantic model
   in `optimize/base.py` (not core); atoms four distinct 0-based indices; `value_deg` finite in
   (−180, 180]; out-of-range indices (against the state) → `OptimizerInputError`.
   `constraints_text(frozen_atom_indices, dihedral_constraints) -> str`: canonical, `""` when
   unconstrained, else per constraint `freeze:<sorted comma-joined indices>` and
   `dihedral:i,j,k,l:<value_deg formatted %.6f>`, sorted, joined by `;`. The runner keys it as
   `opt.constraints` (slice 06); a constrained `OptimizationResult.options` carries it as
   `"constraints"` (the existing `dict[str, ScalarValue]`; no core change).
3. `optimize/geometric_impl.py` `GeometricOptimizer(Optimizer)`: `import geometric` only inside
   methods; `ImportError` → `OptimizerUnavailableError`. Options: `coordsys` ∈ {tric, cart, dlc,
   hdlc} = tric; `convergence_set` ∈ the seven names = GAU; `maxiter` = 300; `trust` = 0.1; `hessian`
   ∈ {never, first} = never. Identity `OptimizerIdentity(name="geometric",
   version=importlib.metadata.version("geometric"))`.
4. Bridge: a `geometric.engine.Engine` subclass whose `calc_new(coords, dirname)` takes Bohr,
   builds a new `MolecularState` (Å; same charge, multiplicity, metadata), calls
   `engine.evaluate(state, forces=True)` and returns `{"energy": E, "gradient": -forces}` (Eh,
   Eh/Bohr, flattened). It never catches `eta_rxncat.engines.EngineError`.
5. Sandbox: each call in a fresh `tempfile.TemporaryDirectory()` used as `dirname` and for any
   prefix; never `chdir`. The `geometric` logger (and its children) gets `propagate=False` and one
   `FileHandler` inside the temp dir for the call; its previous handlers, level and `propagate` are
   restored in `finally`. The root logger is never touched.
6. Ladder (US-008): (1) `tric` (the given options); (2) `tric_tight_trust`: `trust=0.03`,
   `hessian="first"` (geomeTRIC's FD Hessian via the bridge); (3) unconstrained runs `cartesian`:
   `coordsys="cart"`, `trust=0.05`; constrained runs (any frozen atom or dihedral) `hdlc`:
   `coordsys="hdlc"`, `trust=0.05` (R45) — or, if H15 shows `hdlc` refuses a constraint kind, no
   step 3 for runs with that kind. The user's `coordsys="cart"` with a constraint →
   `OptimizerInputError` before any engine call. A step is tried only after the previous raised `GeomOptNotConvergedError` or
   `GeomOptStructureError` (or hit maxiter — confirm which exception that is, H6). Each step tried is
   appended to `recovery_steps` by name, in order. Exhaustion → `OptimizationFailedError` with the
   steps and last energy. Any `eta_rxncat.engines.EngineError` stops the ladder and propagates.
7. `frozen_atom_indices` → `$freeze xyz`; out of range or duplicate → `OptimizerInputError`.
   `dihedral_constraints` → one `$set dihedral i+1 j+1 k+1 l+1 <value>` line each. After
   convergence every constrained dihedral of the final state must be within 0.1° of its value
   (angle difference wrapped to (−180, 180]); otherwise `OptimizationFailedError` (never a returned
   result). geomeTRIC's constraint `RuntimeError` is never caught generically.
8. Packaging (US-014): `[project].dependencies` loses `geometric`; `[project.optional-dependencies]
   opt-geometric = ["geometric==1.1.1"]`; dev group gains `"geometric==1.1.1"`; `uv lock`; the diff
   matches R14 exactly.
9. Licence gate: new profile `opt-geometric` = runtime base + the extra, with the version-pinned
   geomeTRIC exemption (licence, `pulled-in-by = "opt-geometric"`, reason, decision ADR-0011/TJ Q3
   "A"); `base` exemption removed; `gpu`, `mlip-mace`, `mlip-uma` keep it with `pulled-in-by`
   naming `gpu4pyscf-cuda12x` and the CI profile definition (`--extra gpu`); `PROFILES` gains
   `opt-geometric` with a unit test in `tests/unit/tools/`; a stale exemption still fails (test).
10. CI `licence-extras` matrix gains `opt-geometric`:
    `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev --extra opt-geometric && .venv-runtime/bin/python -I tools/licence_gate.py --profile opt-geometric`.
11. AGENTS.md project rules (outside the HACF block): "Licence guardrails" — the base sentence
    becomes "`base` has none"; add the `opt-geometric` command line and exemption sentence. "Engine
    tests" — add `.venv-accept-opt` (`--extra opt-geometric`) and change `.venv-accept-uma` to
    `--extra gpu --extra mlip-uma --extra opt-geometric`.
12. `tests/unit/test_package.py`: `eta_rxncat.optimize` (package import) loads no `geometric`,
    `torch`, `pyscf`, `fairchem`; AST rule: `geometric` imported only inside functions of
    `optimize/geometric_impl.py`.

## 3. Implementation Plan (Task List)

- [x] Task 1: H6 + H15 — read `geometric/optimize.py` 1157–1300, `prepare.py` (`parse_constraints`),
  `params.py`, `errors.py`; in a scratch dir, run via the lower-level path: a two-step toy (H₂ on a
  fake engine); UFF on `C=C(/C=C/OC)OC` (seed 42) with `$set dihedral 1 2 3 4 0.0` on `tric` and on
  `hdlc`; UFF water with `$freeze xyz 1` on `tric` and `hdlc`; record the exact calls, the maxiter
  exception, the final dihedrals and whether `hdlc` accepts each constraint kind. Stop if the
  `tric` dihedral result differs from resolve's (|φ| ≤ 0.1°).
- [x] Task 2: errors, base, options + tests (`tests/unit/optimize/test_base.py`).
- [x] Task 3: `geometric_impl.py`, bridge, sandbox + tests.
- [x] Task 4: ladder + fake-engine tests.
- [x] Task 5: pyproject, lock (check R14 diff with `git diff uv.lock`), licence gate, CI, AGENTS.md.
- [x] Task 6: ledger (new node, scaffold glob move); required checks; licence gate all five
  profiles; commit.

## 4. The Negative Space (Constraints)

- **DO NOT** call `geometric.optimize.run_optimizer` or `logging.config.*`.
- **DO NOT** import `geometric` outside functions of `optimize/geometric_impl.py`.
- **DO NOT** catch `eta_rxncat.engines.EngineError`; no bare `except`.
- **DO NOT** add any licence exemption beyond moving geomeTRIC's.
- **DO NOT** hard-code the GAU thresholds in tests; read them from `geometric.params` at runtime.

## Proof contract

- [ ] With `sys.modules["geometric"] = None` (monkeypatch), `GeometricOptimizer()` raises
  `OptimizerUnavailableError` whose message contains `uv sync --extra opt-geometric`.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev` then
  `.venv-runtime/bin/python -I -c "import importlib.util,sys; sys.exit(importlib.util.find_spec('geometric') is not None)"` exit 0.
- [ ] Water distorted (O–H 1.1 Å, 120°) on `rdkit_ff`/`uff`: converges; |F|max ≤ GAU gmax read from
  `geometric.params`; energy within 1e-5 Eh of RDKit's own `UFFOptimizeMolecule(maxIters=10000)`
  with tight thresholds on the same molecule, converted with `engines.units`.
- [ ] Sandbox: cwd listing before == after; a root `logging.FileHandler(tmp/"app.log", mode="w")`
  and `caplog` both contain a message logged **after** the optimization; `capfd` stderr has no
  geomeTRIC output; the `geometric` logger's handlers/level/propagate equal their pre-call values.
- [ ] Ladder: a fake engine making TRIC fail → `recovery_steps == ["tric", "tric_tight_trust"]` on
  success at step 2; failing all → `OptimizationFailedError.steps == ("tric", "tric_tight_trust",
  "cartesian")`; a fake engine raising `EngineInputError` on call 3 → that error propagates and no
  further step is tried.
- [ ] Frozen atoms: the frozen atoms move ≤ 1e-8 Å; index out of range → `OptimizerInputError`.
- [ ] Dihedral: UFF on `C=C(/C=C/OC)OC` (seed 42 embedding) with `DihedralConstraint((0, 1, 2,
  3), 0.0)` converges with |φ(0-1-2-3)| ≤ 0.1° and `OptimizationResult.options["constraints"] ==
  "dihedral:0,1,2,3:0.000000"`; repeated indices, an index ≥ N, or `value_deg = 200` →
  `OptimizerInputError`; `coordsys="cart"` with any constraint → `OptimizerInputError` before an
  engine call; a constrained fake-engine run that fails steps 1–2 records step 3 as `hdlc` (or
  exhausts after two steps, per H15) and never `cartesian`.
- [ ] H15 results quoted (commands, final dihedrals, `hdlc` acceptance per constraint kind).
- [ ] `git diff Start -- uv.lock` matches R14 (geometric/networkx/six marker moves only, no version
  changes) — quoted in the proof.
- [ ] Licence gate exit 0 for `base` (no geomeTRIC exemption), `opt-geometric`, `gpu`, `mlip-mace`,
  `mlip-uma` (AGENTS.md commands); stale-exemption test fails as designed.
- [ ] Required checks exit 0; `tests/unit/test_package.py` AST and no-heavy-import rules pass.

## Source material

- Mission §5 R2, R5, R14, R38, R42, R44, R45, H15, "Dependencies, extras and licence gate"; ADR-0010, ADR-0011,
  ADR-0013, ADR-0014, ADR-0016; DV-13, DV-14; red team F2 measurement.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.2 (core `OptimizationResult`, `OptimizerIdentity`)
