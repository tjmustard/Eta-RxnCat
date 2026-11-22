---
id: OPR.0.2.0.4
slice: 04-engines-base
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Create the eta_rxncat.engines node: Engine protocol, typed errors, CODATA-2018 units, keyed-option tables producing the resolved stage for the cache key, content-pinned model identity, FD Hessian, and a base-install no-heavy-import proof."
depends_on: [OPR.0.2.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", tests/unit/test_package.py, tests/conftest.py, tests/unit/test_test_policy.py, docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [["uv", "run", "ruff", "check", "."], ["uv", "run", "ruff", "format", "--check", "."], ["uv", "run", "mypy"], ["uv", "run", "pytest"], ["uv", "run", "pytest", "tests/unit/engines/test_base.py", "tests/unit/test_package.py", "tests/unit/test_test_policy.py"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Engine base: protocol, errors, units, keyed options, resolved stage, content identity, FD Hessian

## Intent

Create `eta_rxncat.engines` as a new ledger node holding everything every engine shares:
- the `Engine` protocol;
- the typed error contract;
- one CODATA-2018 unit module;
- keyed-option tables that produce a **resolved stage** for the cache key;
- content-pinned model identity;
- a central-difference Hessian helper;
- a proof that the base install imports none of the heavy libraries.

Context the builder needs (self-contained).

v0.1.0's key is `build_stage_key(state, stage, engine)` (`eta_rxncat.store.keys`). It hashes
`StageConfig.options` and `EngineIdentity(name, version, model)`. So anything that changes a
result must be in the resolved stage's options or the identity, and anything that does not must
stay out (mission R6, ADR-0016 PROPOSED). Model identity is a content hash (R5, ADR-0017).

`EngineTag` is frozen (ADR-0001): `rdkit_ff`, `xtb_subprocess`, `mace`, `uma_direct`,
`pyscf_gpu_cpu`.

Node `eta_rxncat_engines` is **not yet in the graph**:
- Create it with `hyper_ledger.py ensure-node --id eta_rxncat_engines --dimension Module
  --depends-on eta_rxncat_core,eta_rxncat_hw_probe --files 'src/eta_rxncat/engines/**,tests/unit/engines/**,tests/acceptance/**'`
  Do **not** use `--from-spec` (R33: on an existing node it replaces `files:` with this slice's
  narrower touches).
- Remove `src/eta_rxncat/engines/**` from `eta_rxncat_scaffold` with `ensure-node --id
  eta_rxncat_scaffold --files <its full list minus that glob>`. `--files` replaces the list.
- Never hand-edit `architecture.yml`.

Today `src/eta_rxncat/engines/__init__.py` is a placeholder (v0.1.0).

## 1. The Confidence Mandate

**Score: 9/10.** The API, errors, units and option mechanics are fixed. The residual is option
tables for engines that do not exist yet. Each engine slice fills its own table through the
mechanism built here.

## Mini-requirements

1. `engines/errors.py`:
   - `EngineError(Exception)`;
   - subclasses `EngineUnavailableError`, `EngineInputError`, `ScfConvergenceError` (carries
     `steps: tuple[str, ...]`), and `EngineRuntimeError` (carries `tail: str`, at most 40 lines,
     no secrets).
   
   Export them from `eta_rxncat.engines`.
2. `engines/units.py`, CODATA 2018 constants with `Final`:
   - `BOHR_ANGSTROM = 0.529177210903`;
   - `HARTREE_EV = 27.211386245988`;
   - `HARTREE_KCAL_MOL = 627.5094740631`;
   
   plus helper functions `angstrom_to_bohr`, `ev_to_hartree`, `kcal_mol_to_hartree`,
   `ev_per_angstrom_to_hartree_per_bohr`, `kcal_mol_per_angstrom_to_hartree_per_bohr`.
3. `engines/options.py`:
   - `OptionSpec(type: type[str|int|float|bool], default, allowed: frozenset | None = None)`.
   - `resolve_options(tag, table: Mapping[str, OptionSpec], given: Mapping[str, ScalarValue], engine_impl: int) -> dict`.
     It fills defaults, checks types (`bool` is never accepted as `int` or `float`) and allowed
     values, and adds `engine_impl`. An unknown key, wrong type or disallowed value raises
     `EngineInputError` naming the key. A caller may not set `engine_impl`.
   - `resolved_stage(stage, table, engine_impl, normalise=…) -> StageConfig` returns a **new**
     `StageConfig` with the resolved options. The `normalise` hook lowercases
     `solvation.solvent`, and engines may add others.
4. `engines/identity.py`:
   - `sha256_file(path: Path) -> str`, streaming in 1 MiB chunks;
   - `model_id(name: str, path: Path) -> str`, returning `"<name>@sha256:<64 hex>"`;
   - `library_version(dist: str) -> str` via `importlib.metadata`, with `EngineUnavailableError`
     if the distribution is absent.
5. `engines/base.py`:
   - an `Engine` abstract base class with class attributes `tag: EngineTag` and `ENGINE_IMPL: int`,
     plus `OPTIONS: Mapping[str, OptionSpec]`;
   - `classmethod from_stage(stage, **runtime)`, which raises `EngineInputError` if `stage.engine
     != cls.tag` and otherwise builds `self.stage = resolved_stage(...)`;
   - abstract `identity` (property) and `_evaluate(state, *, forces, hessian)`;
   - public `evaluate(state, *, forces=True, hessian=False) -> PotentialResult`. It times the
     call, wraps the subclass result, sets `stage_engine_impl`, and checks that `state` atom
     count matches the result shapes.
6. `engines/fd.py`, `fd_hessian(force_fn, coords_bohr, step_bohr) -> (H, max_asym)`:
   - central differences of forces, giving H = −∂F/∂x in 3N×3N;
   - 6N force calls;
   - symmetrises `(H + Hᵀ)/2` and returns the pre-symmetrisation max |H − Hᵀ|.
7. `engines/__init__.py` exports the public names above and imports **no** heavy library.
8. `tests/unit/test_package.py`: a subprocess test on the base install.
   `python -c "import eta_rxncat, eta_rxncat.engines, sys; print(sorted({'ase','torch','mace','fairchem','gpu4pyscf','cupy','pyscf','rdkit'} & set(sys.modules)))"`
   must print `[]`. The existing AST import ban already covers `src/eta_rxncat/engines/`; assert
   that it scans that directory.
9. **Acceptance switch completeness** (replan R32; slice 01 audit finding
   `qitem-20261122165838-accad9ea`; makes mission R8 true). Extend `tests/conftest.py` so that
   under `ETA_RXNCAT_ACCEPTANCE=1` **any** skip fails the run:
   - (a) collection-phase skips: a module-level `pytest.skip(..., allow_module_level=True)` or
     `pytest.importorskip(...)` produces a skipped `CollectReport`. Convert it to failed in a
     `pytest_collectreport`/`pytest_make_collect_report` hook, with the reason in `longrepr`.
     The run then exits non-zero (pytest's collection-error exit) and names the module.
   - (b) xfail: a test marked `xfail` (either outcome, xfailed or xpassed) is reported `failed`,
     with `wasxfail` removed, so the exit code is non-zero and the reason is shown.
   - (c) setup and call skips: unchanged (slice 01).
   
   Without the variable, nothing changes.
   
   Also add a rule test: an AST scan of every `.py` under `tests/unit/engines/` and
   `tests/acceptance/` fails on any **module-level** (top-level statement) call to
   `pytest.importorskip` or `pytest.skip`. Engine tests skip through markers and function- or
   fixture-level `importorskip` only.
10. Register rows (status `open`):
   - starter `engines/base.py` names vs these (`changed`/`dropped`);
   - `added` rows for each module here.

## 3. Implementation Plan (Task List)

- [ ] Task 1: the ledger node and the glob move (context above).
- [ ] Task 2: errors, units, options, identity, base, fd (Mini-requirements 1–7).
- [ ] Task 3: tests in `tests/unit/engines/test_base.py`, using a toy engine class `ToyEngine`
  (tag `rdkit_ff`) with a pure-Python harmonic potential, defined in the test file.
- [ ] Task 4: the base-install subprocess test (Mini-requirement 8).
- [ ] Task 4b (R32): the conftest collection and xfail conversion, plus the module-level-skip rule
  test (Mini-requirement 9). Tests go in `tests/unit/test_test_policy.py` (slice 01's file,
  extended).
- [ ] Task 5: register rows; four gates; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** implement any real engine here.
- **DO NOT** import numpy, torch, rdkit, pyscf or any extra at module level in
  `eta_rxncat.engines`. Pure Python or function-local imports only.
- **DO NOT** let `resolve_options` accept a key it does not know, or let runtime arguments into
  options.
- **DO NOT** edit `eta_rxncat.store` or the core models (except to import them).

## Proof contract

- [ ] `resolve_options`:
  - fills defaults;
  - adds `engine_impl`;
  - rejects an unknown key, a `bool` for an `int` spec, a disallowed value, and a caller-set
    `engine_impl`, each with `EngineInputError` naming the key.
- [ ] `resolved_stage` returns a new `StageConfig` whose options include every default, with the
  solvent lowercased. The original is unchanged.
  - `build_stage_key` of two stages that differ only by a default left implicit vs given
    explicitly → **equal** keys.
  - Two stages differing only in a keyed value → different keys.
- [ ] `ToyEngine.from_stage(stage_with_engine="mace")` → `EngineInputError`.
- [ ] `fd_hessian` on a harmonic potential with known H gives max |H − H_true| ≤ 1e-6 (step
  0.005). The result is exactly symmetric, and `max_asym` ≥ 0 is reported.
- [ ] `model_id("x", f)` equals `"x@sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()`.
- [ ] Unit conversions round-trip to 1e-15 relative, and the constants equal the stated CODATA
  2018 values.
- [ ] The base-install subprocess test prints `[]`.
- [ ] R32, pytester, using the audit probe pattern
  (`~/.hacf/eta-rxncat-hacf/audit-evidence/probe201b.py`) with the real `tests/conftest.py`:
  - one module doing `pytest.importorskip("no_such_mace_xyz")` at module level plus one passing
    module, under `ETA_RXNCAT_ACCEPTANCE=1` → **non-zero** exit, the skipped module reported as
    an error or failure naming it, and no `skipped` in the outcomes;
  - the same without the variable → exit 0, `1 passed, 1 skipped`;
  - module-level `pytest.skip("x", allow_module_level=True)` under `=1` → non-zero;
  - an `xfail`-marked failing test under `=1` → non-zero exit, reported failed. Without the
    variable → exit 0, `1 xfailed`;
  - the slice-01 setup/call cases still behave as before.
- [ ] The module-level-skip rule test passes on the repo. A `tmp_path` file with a top-level
  `pytest.importorskip("x")` is flagged; one with it inside a function is not.
- [ ] `ToyEngine.evaluate` returns a valid `PotentialResult` with `stage_engine_impl == 1` and
  `wall_time_s ≥ 0`. A toy that returns 2 force rows for 3 atoms → `EngineRuntimeError`.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0. The ledger shows `eta_rxncat_engines` with the three globs, and
  scaffold no longer lists `src/eta_rxncat/engines/**`.

## Source material

- Mission §5 Contracts (Errors, Engine API, Resolved stage, Identity, Units), R5, R6, R11, R15,
  R16, R17; ADR-0001, ADR-0003, ADR-0009; ADR-0016/0017 (PROPOSED);
  `src/eta_rxncat/store/keys.py`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.3 (PotentialResult)
