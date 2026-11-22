# v0.2.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.2.0.zip` ships a starter implementation, unpacked here under
`docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/` (26 files, byte-identical to the zip, plus the gate file
`.ruff.toml`, which is not part of the starter). It is reference only: the code in `src/` and
`tests/` is written fresh from the mission's slice specs. This register records every difference
between the starter and the rewrite, so each one can be reviewed and fixed if needed.

TJ, Q2: "B use it as reference only. Keep a list of the discrepancies so that if needed, we can go
through each of them and fix any issues that arise."

## Scope (what is compared)

Only the engine files and the version bump are registered (mission §5, "The discrepancy
register"). Modules identical to the v0.1.0 starter are not re-registered: their rows are in
`docs/prd/v0.1.0/DISCREPANCIES.md`.

`cmp` of every non-engine file against `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/` (slice 01, 2026-11-22):

- identical (18 files): `AGENTS.md`, `README.md`, `Eta-RxnCat_Living_Master_Plan.md`,
  `src/eta_rxncat/{cli.py, conformers/__init__.py, core/__init__.py, core/models.py,
  core/reaction_graph.py, mapping/__init__.py, optimize/__init__.py, orchestrator/__init__.py,
  store/__init__.py, store/artifact_store.py, utils/__init__.py, utils/hw_probe.py}`,
  `tests/unit/{test_core_schemas.py, test_hw_probe.py}`, `tests/e2e/fixtures/example_reaction_graph.yaml`;
- differ (3 files): `pyproject.toml` and `src/eta_rxncat/__init__.py`, each only in the version
  string (`0.1.0` → `0.2.0`), rows D-001 and D-002; `src/eta_rxncat/engines/__init__.py`, a
  docstring-only stub in v0.1.0 and the engine re-exports in v0.2.0, row D-003;
- new in v0.2.0 (5 files): `src/eta_rxncat/engines/{base,rdkit_xtb,mlip,pyscf_engine}.py` and
  `tests/unit/test_engines_v020.py`, registered below;
- absent from v0.2.0 (2 files): `.github/workflows/ci.yml` and `.gitignore`, present only in the
  v0.1.0 starter (registered there); no rows here.

## Inventory rules (closed)

- each engine module: every top-level public name (no leading `_`), and for each public class
  every public attribute and public method;
- `tests/unit/test_engines_v020.py`: each test function;
- the draft's known issues (mission §5 seeds), one row each, located in the starter;
- plus one `added` row for each rewrite public name absent from the starter (engine slices).

Cosmetic differences (formatting, comments, docstring wording) are not rows.

## Row format

`| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |`

- Starter paths are given in full from the repo root.
- `Disposition` ∈ `pending`, `same`, `changed`, `dropped`, `added`. `pending` (slice 01 seeds)
  means the engine slice that owns the item has not built it yet; that slice replaces it with
  `same`, `changed` or `dropped` and adds `added` rows.
- `Status` ∈ `open`, `accepted`, `fix`. Builders write `open` only; TJ decides the rest.
- Each slice appends rows to its own area section, continuing the ID sequence.

## Version

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-001 | version | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/pyproject.toml:7` `version = "0.2.0"` | — | pending | Starter bumps 0.1.0 → 0.2.0 (only `pyproject.toml` diff vs the v0.1.0 starter) | open |
| D-002 | version | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/__init__.py:3` `__version__ = "0.2.0"` | — | pending | Only `__init__.py` diff vs the v0.1.0 starter | open |

## Engines: public names

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-003 | engines `__init__` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/__init__.py:8` `__all__` (7 names) | — | pending | Package re-export list | open |
| D-004 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:13` `BOHR_TO_ANGSTROM = 0.529177210903` | `src/eta_rxncat/engines/units.py:5` `BOHR_ANGSTROM: Final = 0.529177210903` | changed | Slice 04 Mini-req 2: one CODATA 2018 unit module (`engines.units`), renamed per mission §5; same value | open |
| D-005 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:14` `HARTREE_TO_KCAL_MOL = 627.5094740631` | `src/eta_rxncat/engines/units.py:11` `HARTREE_KCAL_MOL: Final = 627.5094740631` | changed | As D-004; same value | open |
| D-006 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:18` `PotentialEngine` (runtime-checkable Protocol) | `src/eta_rxncat/engines/base.py:53` `Engine` (ABC) | dropped | Slice 04 Mini-req 5: one abstract base `Engine` replaces the Protocol + ABC pair; engines subclass it | open |
| D-007 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:21` `PotentialEngine.name: str` | `src/eta_rxncat/engines/base.py:61` `Engine.tag: ClassVar[EngineTag]` | changed | A frozen `EngineTag` (ADR-0001), not a free-form name such as `rdkit_uff`; the per-engine name seeds D-045..D-049 stay `pending` for the engine slices | open |
| D-008 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:23` `PotentialEngine.evaluate(state, *, compute_forces=True, compute_hessian=False)` | `src/eta_rxncat/engines/base.py:106` `Engine.evaluate(state, *, forces=True, hessian=False)` | changed | Mission §5 Engine API keyword names; returns a validated core `PotentialResult` | open |
| D-009 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:33` `BasePotentialEngine` (ABC) | `src/eta_rxncat/engines/base.py:53` `Engine` (ABC; `from_stage`, `stage`, `identity`, `_evaluate`) | changed | Slice 04 Mini-req 5: built from a stage via `from_stage`, which resolves the keyed options (ADR-0016); `identity` is abstract | open |
| D-010 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:36` `BasePotentialEngine.name = "base"` | `src/eta_rxncat/engines/base.py:61` `Engine.tag` (no default) | changed | No placeholder `"base"` name; every engine sets its frozen tag | open |
| D-011 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:48` `BasePotentialEngine.evaluate(...)` (times `_evaluate_impl`, mutates `wall_time_seconds`) | `src/eta_rxncat/engines/base.py:106` `Engine.evaluate` | changed | Times `_evaluate`, then builds the frozen result with `wall_time_s` and `stage_engine_impl` (never mutating a result after construction); checks force/Hessian shapes against the state; invalid output → `EngineRuntimeError`; returned lists are copies | open |
| D-012 | engines `base` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py:64` `BasePotentialEngine.numerical_hessian(state, step_angstrom=0.005)` | `src/eta_rxncat/engines/fd.py:10` `fd_hessian(force_fn, coords_bohr, step_bohr) -> (H, max_asym)` | changed | Slice 04 Mini-req 6 / R15: a function over a force callback, step in Bohr (not Angstrom), 6N calls, returns the symmetrised H and the pre-symmetrisation max asymmetry; seeds D-050/D-051 (FD MLIP Hessians) stay with the MLIP slices | open |
| D-013 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:20` `RDKitFFEngine(force_field="UFF")` | `src/eta_rxncat/engines/rdkit_ff.py:36` `RDKitFFEngine` (built with `RDKitFFEngine.from_stage(stage)`; `stage.method` `uff` \| `mmff94`) | changed | Slice 05: method from the stage, not a constructor argument; separate module `rdkit_ff.py` (xtb gets its own slice); MMFF94s not offered | open |
| D-014 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:24` `RDKitFFEngine.name` | `src/eta_rxncat/engines/rdkit_ff.py:43` `tag = "rdkit_ff"` | changed | Frozen tag `rdkit_ff` instead of `rdkit_uff`/`rdkit_mmff94`; the force field is `stage.method` (keyed), not part of the name | open |
| D-015 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:25` `RDKitFFEngine.force_field` | `src/eta_rxncat/engines/rdkit_ff.py:32` `METHODS = ("uff", "mmff94")`; `self.stage.method` | changed | The force field is the stage's `method`, lowercased by `normalise_stage` (`:65`) so `UFF` and `uff` key the same | open |
| D-016 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:82` `XTBSubprocessEngine(method="GFN2-xTB", solvation=None, xtb_executable="xtb")` | `src/eta_rxncat/engines/xtb_subprocess.py:120` `XTBSubprocessEngine` via `from_stage(stage, binary=, threads=, timeout_s=, omp_stacksize=, keep_failed=)` | changed | Slice 08: method and ALPB from the keyed stage; runtime arguments never keyed; GFN1/GFN-FF not offered (`method` must be `gfn2`) | open |
| D-017 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:91` `XTBSubprocessEngine.name` | `src/eta_rxncat/engines/xtb_subprocess.py:131` `tag = "xtb_subprocess"` | changed | Frozen tag (ADR-0001) instead of `xtb_gfn2-xtb`; identity `xtb_subprocess` / `xtb 6.8.0` from `--version`, model None | open |
| D-018 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:92` `XTBSubprocessEngine.method` | `StageConfig.method == "gfn2"` | changed | Anything else → `EngineInputError` | open |
| D-019 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:93` `XTBSubprocessEngine.solvation` | `StageConfig.solvation` (`none` \| `alpb` + solvent, lowercased) + keyed `alpb_state` (`src/eta_rxncat/engines/xtb_subprocess.py:136`, default `gsolv`) | changed | R7: the ALPB state is keyed and always passed (`--alpb <solvent> <state>`); dielectric-only refused; the starter passed no state and silently skipped ALPB without a solvent | open |
| D-020 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:94` `XTBSubprocessEngine.xtb_executable` | `src/eta_rxncat/engines/xtb_subprocess.py:51` `resolve_binary`: runtime `binary`, else `$ETA_RXNCAT_XTB`, else `PATH` | changed | R12: missing → `EngineUnavailableError` naming the provisioning step (xtb 6.8.0 tarball + digest) | open |
| D-021 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:10` `EV_TO_HARTREE` | — | pending | Unit constant | open |
| D-022 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:24` `atomic_numbers_from_symbols(symbols)` (table stops at Hg; no lanthanides 58–71) | — | pending | Public function | open |
| D-023 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:28` `MACEEngine(model_name="medium", device="auto")` | — | pending | Engine class | open |
| D-024 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:32` `MACEEngine.name` | — | pending | Instance attribute | open |
| D-025 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:33` `MACEEngine.model_name` | — | pending | Instance attribute | open |
| D-026 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:95` `UMADirectEngine(model_name="uma-s-1.2.1", task_name="omol", device="auto")` | — | pending | Engine class | open |
| D-027 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:104` `UMADirectEngine.name` | — | pending | Instance attribute | open |
| D-028 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:105` `UMADirectEngine.model_name` | — | pending | Instance attribute | open |
| D-029 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:106` `UMADirectEngine.task_name` | — | pending | Instance attribute | open |
| D-030 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:12` `PySCFEngine(functional="wB97X-D3BJ", basis="def2-SVP", solvation=None, prefer_gpu=True, vram_budget_gb=6.5, density_fit=True)` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:127` `PySCFEngine` built by `PySCFEngine.from_stage(stage, device=, max_memory_mb=, ladder_max_cycle=)` | changed | Slice 06: functional and basis come from the keyed stage (`method`, `basis`), not constructor defaults; runtime arguments are never keyed; package `engines/pyscf_gpu_cpu/` | open |
| D-031 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:24` `PySCFEngine.name` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:127` `tag = "pyscf_gpu_cpu"` | changed | Frozen tag; identity `EngineIdentity(pyscf_gpu_cpu, library_version('pyscf'), None)` | open |
| D-032 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:25` `PySCFEngine.functional` | `StageConfig.method` (lowercased by `normalise_stage`) | changed | xc name accepted by `pyscf.dft.libxc.parse_xc`, or `hf`; unknown → `EngineInputError` at `from_stage`; no `wB97X-D3BJ` default | open |
| D-033 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:26` `PySCFEngine.basis` | `StageConfig.basis` (required by core) | changed | No `def2-SVP` default | open |
| D-034 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:27` `PySCFEngine.solvation` | `StageConfig.solvation` + `_resolve_dielectric` (`engine.py:247`) | changed | ddCOSMO / C-PCM / IEF-PCM; ε from the explicit dielectric, else the solvent table; `alpb` refused | open |
| D-035 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:28` `PySCFEngine.prefer_gpu` | runtime `device` (`auto` \| `cpu` \| `cuda`), `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:636` `_evaluate` | changed | Slice 07 Mini-req 1: not a keyed flag; `auto` uses the GPU when GPU4PySCF, CuPy and a CUDA device are present, else CPU with `device_reason="gpu_unavailable"`; `cuda` without them → `EngineUnavailableError` naming `uv sync --extra gpu`; the device is never keyed | open |
| D-036 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:29` `PySCFEngine.vram_budget_gb` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:195` `self.vram_budget_bytes = vram_budget_bytes(total)` | changed | ADR-0008 budget min(6.5 GiB, total) in bytes, total from `cupy.cuda.runtime.memGetInfo()` once at construction (not a free-form GB float) | open |
| D-037 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:30` `PySCFEngine.density_fit` | keyed option `density_fit` (default true) + `auxbasis` (`def2-universal-jkfit`) | changed | Mission R2 / ADR-0018: DF vs non-DF differs by ~1e-5 Eh, so both are keyed (the starter fixed DF on and never named the auxbasis) | open |
| D-038 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:32` `PySCFEngine.estimate_vram_gb(n_basis_functions)` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:571` `estimate_vram_bytes(mol, stage)` → `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:115` `estimate_bytes(nao, naux)` | changed | Slice 07 / R42: f · 8 · (naux·nao(nao+1)/2 + 40·nao²) + VRAM_OVERHEAD_BYTES, in bytes, with naux from the keyed auxbasis | open |

## Engines: known draft issues (seeds)

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-039 | solvation | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:54` `_attach_solvation` uses only `dielectric`; `SolvationSpec.solvent` is ignored (ddCOSMO/PCM run at the default eps when only a solvent name is given) | `src/eta_rxncat/engines/pyscf_gpu_cpu/solvents.py` `DIELECTRICS` (20 solvents, Minnesota database) | changed | The solvent name is used (lowercased); values equal PySCF 2.15.1's and GPU4PySCF 1.9.2's shipped tables (tested); unknown name → `EngineInputError` | open |
| D-040 | rdkit | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:37` `except Exception: pass` around `DetermineConnectivity` | `src/eta_rxncat/engines/rdkit_ff.py:84` `_perceive`: `DetermineBonds(mol, charge=0)` + `SanitizeMol`, `ValueError` → `EngineInputError`; round-trip check (elements, formal charge 0, no radicals, no implicit H) | changed | Slice 05 Mini-req 3 (R35 order a–d): perception failures are refused, never swallowed; no coordinates-only fallback (`DetermineConnectivity` dropped) | open |
| D-041 | pyscf | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:32` `0.8 + 4.5e-6 * n_bf**2` GB VRAM estimate | `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:16` `VRAM_SAFETY = 5.13`, `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:11` `VRAM_OVERHEAD_BYTES = 64 MiB` | changed | R42: calibrated on water, the Pd anion and n-decane (`docs/prd/v0.2.0/calibration/pyscf_vram.json`); the starter's uncalibrated decimal-GB formula is dropped; without an overhead term the calibration gave f = 84.16 and sent decane to CPU (stop-report, decision A) | open |
| D-042 | pyscf | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:141` `probe_hardware()` called inside every `_evaluate_impl` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:636` `_evaluate` (no `probe_hardware()`) | dropped | R10: the per-evaluate probe created a torch CUDA context; the engine never calls `probe_hardware` and never imports torch (tested) | open |
| D-043 | uma | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:137` positions and cell built as `torch.float32` | — | pending | Seed: float32 UMA positions | open |
| D-044 | mace | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:50` `mace_mp(model=..., device=..., default_dtype="float64")` (ASE calculator factory, may download) | — | pending | Seed: `mace_mp` usage | open |
| D-045 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:24` engine `name` `rdkit_uff` / `rdkit_mmff94` | `src/eta_rxncat/engines/rdkit_ff.py:43` `rdkit_ff` for both force fields | changed | Frozen tag (ADR-0001); seed closed for RDKit | open |
| D-046 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:91` engine `name` `xtb_gfn2-xtb` | `src/eta_rxncat/engines/xtb_subprocess.py:131` `xtb_subprocess` | changed | Frozen tag; seed closed for xtb | open |
| D-047 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:32` engine `name` `mace_medium` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-048 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:104` engine `name` `uma_uma-s-1.2.1` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-049 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:24` engine `name` `pyscf_<xc>_<basis>` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:127` `pyscf_gpu_cpu` | changed | Frozen tag (ADR-0001); seed closed for PySCF | open |
| D-050 | mlip | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:85` MACE Hessian by `numerical_hessian` (finite differences) | — | pending | Seed: FD MLIP Hessians | open |
| D-051 | mlip | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:161` UMA Hessian by `numerical_hessian` (finite differences) | — | pending | Seed: FD MLIP Hessians | open |

## Tests

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-052 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:24` `test_rdkit_uff_energy_and_forces` | `tests/unit/engines/test_rdkit_ff.py` (`test_energy_and_forces_match_rdkit`, `test_fd_hessian`, `test_fd_hessian_matches_energy_second_differences`) | changed | Starter checked only finiteness and shapes; the rewrite checks energy and forces against RDKit's own API on the same input (≤1e-10 rel), forces against FD of the energy, and the Hessian against energy second differences | open |
| D-053 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:34` `test_pyscf_cpu_energy_gradient_and_vram_guard` | `tests/unit/engines/test_pyscf_cpu.py` (`test_reference_hf_sto3g_water`, slow FD and reference tests) and `tests/unit/engines/test_pyscf_gpu.py` | changed | Starter PySCF test (shapes, `< −75` bound, GB VRAM guard) replaced by reference, FD and calibrated-VRAM tests (slices 06, 07; row left pending by slice 06, resolved in slice 08) | open |
| D-054 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:38` `assert res.electronic_energy_hartree < -75.0` (B3LYP/STO-3G water) | `tests/unit/engines/test_pyscf_cpu.py` reference tests (`test_reference_hf_sto3g_water`, `test_slow_b3lyp_energy_matches_pyscf`) | changed | The `< −75.0` bound is replaced by comparisons with plain PySCF on the same input (≤1e-10 / ≤1e-8 Eh), plus FD checks of gradients and Hessians | open |

## Stack and licence gate (slice 02)

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-055 | pyproject `[tool.uv]` | — (the starter has no torch index; v0.1.0 rewrite `pyproject.toml:45` `pytorch-cu128`, D-380 in the v0.1.0 register) | `pyproject.toml:45` `[[tool.uv.index]] name = "pytorch-cu129"`, `url = …/whl/cu129`; `pyproject.toml:50` `torch = [{ index = "pytorch-cu129" }]` | changed | TJ F1 "Q1. A" (16:24Z, `qitem-20261122162111-26e232a707f003e2`): torch 2.13.0+cu129 (locked) for native `uma-s-1p2p1`; ADR-0020 PROPOSED | open |
| D-056 | pyproject extra | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/pyproject.toml:49` `fairchem-core>=2.16.0` (extra `mlip`) | `pyproject.toml:27` `mlip-uma = ["torch>=2.7.0", "fairchem-core>=2.22"]` (locks 2.26.0) | changed | TJ F1 "Q1. A": fairchem-core ≥ 2.22; the v0.1.0 rewrite had no floor | open |
| D-057 | licence gate | — | `pyproject.toml:247` exempt `cuda-toolkit` 12.9.1 (gpu, mlip-mace, mlip-uma) | added | NVIDIA CUDA runtime wheel with no licence metadata, pulled in by torch 2.13.0+cu129; version-pinned; TJ v0.1.0 Q1 A; R1 v0.2.0 | open |
| D-058 | licence gate | — | `pyproject.toml` exempt `ray-haproxy` 2.8.25 (mlip-uma) removed | dropped | ray is no longer locked under fairchem-core 2.26.0; the stale-exemption rule forces removal | open |
| D-059 | licence gate | — | `tools/licence_gate.py:335` `FAIL unnamed distribution at <path>`; test `tests/unit/tools/test_licence_gate.py:307` | added | R27: a dist-info without `Name` was silently skipped | open |
| D-060 | licence gate | — | `tools/licence_gate.py:345` `FAIL ambiguous: <name> (<versions>)`; tests `tests/unit/tools/test_licence_gate.py:320`, `:331` | added | R27: with two dist-infos for one PEP 503 name the first won; now neither is judged and the gate fails (the same folder seen twice through a repeated path entry is one distribution) | open |
| D-061 | licence gate | — | `pyproject.toml:102` `allowed` gains `"BSL-1.0"`; tests `tests/unit/tools/test_licence_gate.py:123` (4 `test_verdicts` cases) | added | R34 (lead decision within TJ's 14:57Z policy): torch 2.13.0+cu129's expression includes BSL-1.0 (Boost Software License 1.0, OSI/FSF-approved permissive); an allowed licence, not an exemption | open |

## Core: PotentialResult and engine tag (slice 03)

The starter's `core/models.py` is identical to v0.1.0's, where `PotentialResult` was `dropped` (v0.1.0 D-148..D-154, "defined by its consuming version"). v0.2.0 is that consumer, so these rows compare the starter class with the rewrite.

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-062 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:178` `class PotentialResult(BaseModel)` (mutable, extra keys ignored, no validators) | `src/eta_rxncat/core/results.py:22` `class PotentialResult(CoreModel)` (frozen, `extra="forbid"`, shape/symmetry/pairing validators), exported from `eta_rxncat.core`; separate module `core/results.py` | changed | Slice 03 / ADR-0003, ADR-0009: strict frozen core contract; data only, no numpy or engine imports | open |
| D-063 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:181` `electronic_energy_hartree: float` | `src/eta_rxncat/core/results.py:53` `energy_hartree: FiniteFloat` | changed | Mission §5 Contracts name; NaN/inf rejected | open |
| D-064 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:182` `forces_hartree_per_bohr: list[list[float]] \| None` | `src/eta_rxncat/core/results.py:54` same name, finite floats, ≥ 1 row, every row length 3 | changed | Slice 03 Mini-req 2; forces = −∂E/∂x (Eh/Bohr) stated in the docstring | open |
| D-065 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:183` `hessian_hartree_per_bohr2: list[list[float]] \| None` | `src/eta_rxncat/core/results.py:55` same name, finite, square, side a positive multiple of 3 and = 3 × force rows, exactly symmetric | changed | Slice 03 Mini-req 2, R15: Cartesian Eh/Bohr², not mass-weighted or projected; engines symmetrise, the model only validates | open |
| D-066 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:184` `wall_time_seconds: float = 0.0` | `src/eta_rxncat/core/results.py:62` `wall_time_s`, finite ≥ 0, required | changed | Mission §5 name; no silent 0.0 default (the starter's `evaluate` overwrote it after construction, which a frozen model forbids) | open |
| D-067 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:185` `backend_device: str = "cpu"` (starter engines also wrote `"cpu-subprocess"`) | `src/eta_rxncat/core/results.py:60` `device: Literal["cpu", "cuda"]`, required | changed | Mission §5: closed device set; the subprocess detail belongs in `device_reason` | open |
| D-068 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:186` `recovery_steps_used: list[str]` | `src/eta_rxncat/core/results.py:63` `recovery_steps: list[str]` (default empty) | changed | Mission §5 name | open |
| D-069 | core | — | `src/eta_rxncat/core/results.py:56` `hessian_method: Literal["analytic", "finite_difference"] \| None` | added | Slice 03 / R15: set iff the Hessian is set | open |
| D-070 | core | — | `src/eta_rxncat/core/results.py:57` `hessian_max_asymmetry` (finite ≥ 0 \| None) | added | Slice 03 / R15: largest pre-symmetrisation \|H[i][j] − H[j][i]\|; set iff the Hessian is set | open |
| D-071 | core | — | `src/eta_rxncat/core/results.py:58` `engine: EngineIdentity` | added | Slice 03 Mini-req 1: the result names its engine tag, version and model weights (ADR-0017) | open |
| D-072 | core | — | `src/eta_rxncat/core/results.py:59` `stage_engine_impl: StrictInt ≥ 1` | added | Slice 03 Mini-req 1 (ADR-0016) | open |
| D-073 | core | — | `src/eta_rxncat/core/results.py:61` `device_reason: str \| None` (min length 1) | added | Slice 03 Mini-req 1: why that device (for example a CPU fallback) | open |
| D-074 | core | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/core/models.py:52` `StageConfig.engine: Literal["rdkit_ff", "xtb", "mace", "uma", "pyscf"]` (no eSEN; the v0.1.0 rewrite's 5-tag `EngineTag` is in the v0.1.0 register) | `src/eta_rxncat/core/models.py:21` `EngineTag` gains `"esen_omol25"`; docstring: one tag per model family | added | R31, TJ 16:52Z "A - Ship it as a second model", PROPOSED ADR-0022 (amends ADR-0001's frozen set); existing cache keys unchanged (golden test) | open |

## Engines: base (slice 04)

Rows D-004..D-012 above were updated from `pending` by this slice. `__init__` (D-003) stays `pending` until the engine classes exist.

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-075 | engines `errors` | — | `src/eta_rxncat/engines/errors.py:20` `EngineError(Exception)` | added | Mission §5 Errors: base of the typed error contract | open |
| D-076 | engines `errors` | — | `src/eta_rxncat/engines/errors.py:24` `EngineUnavailableError` | added | Missing extra, binary, weights or GPU | open |
| D-077 | engines `errors` | — | `src/eta_rxncat/engines/errors.py:28` `EngineInputError` | added | Unrepresentable state, stage or option (v0.2.0 Q2 A) | open |
| D-078 | engines `errors` | — | `src/eta_rxncat/engines/errors.py:32` `ScfConvergenceError(message, steps)` | added | Carries `steps: tuple[str, ...]` | open |
| D-079 | engines `errors` | — | `src/eta_rxncat/engines/errors.py:41` `EngineRuntimeError(message, tail)` | added | Diagnostic tail capped at 40 lines (`TAIL_MAX_LINES`, `errors.py:9`) and redacted (`redact`, `errors.py:15`: HF tokens, `token=`/`Bearer` values) | open |
| D-080 | engines `units` | — | `src/eta_rxncat/engines/units.py:8` `HARTREE_EV: Final = 27.211386245988` | added | CODATA 2018 (the starter had `mlip.EV_TO_HARTREE`, D-021, left for the MLIP slices) | open |
| D-081 | engines `units` | — | `src/eta_rxncat/engines/units.py:15` `angstrom_to_bohr`, `bohr_to_angstrom` (`:20`), `ev_to_hartree` (`:25`), `kcal_mol_to_hartree` (`:30`), `ev_per_angstrom_to_hartree_per_bohr` (`:35`), `kcal_mol_per_angstrom_to_hartree_per_bohr` (`:40`) | added | Slice 04 Mini-req 2 helpers; `bohr_to_angstrom` added for engines that take Angstrom | open |
| D-082 | engines `options` | — | `src/eta_rxncat/engines/options.py:42` `OptionSpec(type, default, allowed=None)` | added | Slice 04 Mini-req 3; checks its own default | open |
| D-083 | engines `options` | — | `src/eta_rxncat/engines/options.py:65` `resolve_options(tag, table, given, engine_impl)` | added | Fills defaults, adds `engine_impl` (`ENGINE_IMPL_KEY`, `options.py:16`); unknown key, bool-for-int/float, wrong type, disallowed value or caller-set `engine_impl` → `EngineInputError`; an int for a float spec is stored as float so 1 and 1.0 key the same | open |
| D-084 | engines `options` | — | `src/eta_rxncat/engines/options.py:119` `resolved_stage(stage, table, engine_impl, normalise=normalise_solvent)` | added | Returns a new `StageConfig` (ADR-0016): implicit and explicit defaults give equal cache keys; `normalise_solvent` (`options.py:109`) lowercases `solvation.solvent` | open |
| D-085 | engines `identity` | — | `src/eta_rxncat/engines/identity.py:13` `sha256_file(path)` (1 MiB chunks, `CHUNK_BYTES`) | added | Mission R5 / ADR-0017 | open |
| D-086 | engines `identity` | — | `src/eta_rxncat/engines/identity.py:22` `model_id(name, path)` → `"<name>@sha256:<64 hex>"` | added | Content-pinned model identity; never a path | open |
| D-087 | engines `identity` | — | `src/eta_rxncat/engines/identity.py:27` `library_version(dist)` | added | `importlib.metadata`; absent → `EngineUnavailableError` | open |
| D-088 | engines `base` | — | `src/eta_rxncat/engines/base.py:32` `RawResult` (dataclass) | added | What a subclass's `_evaluate` returns; `Engine.evaluate` validates and wraps it into `PotentialResult` | open |
| D-089 | engines `base` | — | `src/eta_rxncat/engines/base.py:83` `Engine.from_stage(stage, **runtime)`; `ENGINE_IMPL`, `OPTIONS` class attributes (`:62`, `:63`); `normalise_stage` hook (`:88`); `stage` property (`:93`); abstract `identity` (`:99`) | added | Mission §5 Engine API; a foreign tag or unknown runtime argument → `EngineInputError` | open |
| D-090 | engines `tests` | — | `tests/conftest.py` collection-phase skips and xfail fail under `ETA_RXNCAT_ACCEPTANCE=1` | added | R32 (slice 01 audit `qitem-20261122165838-accad9ea`); plus the module-level-skip AST rule in `tests/unit/test_test_policy.py` | open |

## Engines: RDKit (slice 05)

Rows D-013..D-015, D-040, D-045 and D-052 above were updated from `pending` by this slice.

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-091 | engines `rdkit_ff` | — | `src/eta_rxncat/engines/rdkit_ff.py:84` charge/multiplicity check (a): only charge 0 and multiplicity 1, before any RDKit call; exact message `rdkit_ff: charge <q>, multiplicity <m>: only neutral closed-shell states (charge 0, multiplicity 1) are supported` | added | R35 (lead decision A on the slice 05 stop-report; TJ v0.2.0 Q2 A): RDKit perceives hydroxide and hydronium fine, but ions are refused; the starter accepted any charge/spin silently | open |
| D-092 | engines `rdkit_ff` | — | `src/eta_rxncat/engines/rdkit_ff.py:127` `_force_field` `UFFHasAllMoleculeParams` / `MMFFHasAllMoleculeParams` checked first; missing parameters → `EngineInputError` (check d) | added | The starter set up the force field without checking parameters (e.g. Pd, SF6 under UFF; BH3 under MMFF94) | open |
| D-093 | engines `rdkit_ff` | — | `src/eta_rxncat/engines/rdkit_ff.py:145` `_energy_and_gradient` a fresh force field per geometry on a copy of the perceived molecule, conformer moved, then `CalcEnergy()` and `CalcGrad()` at its own coordinates | added | Measured defect in RDKit 2026.09.2: on a reused force field `CalcGrad(positions)` depends on earlier calls and is not the gradient of `CalcEnergy` (a first FD Hessian of water was asymmetric by 0.03 Eh/Bohr² with wrong elements); the starter's `numerical_hessian` re-perceived per displacement instead | open |
| D-094 | engines `rdkit_ff` | — | `src/eta_rxncat/engines/rdkit_ff.py:171` `_evaluate` FD Hessian via `engines.fd.fd_hessian` on the engine's own forces at `fd_step_bohr` (keyed, 0.005 Bohr), `hessian_method="finite_difference"` | added | Replaces the starter's `numerical_hessian(state)` (0.005 Å step, re-built molecule per step) | open |
| D-095 | engines `rdkit_ff` | — | `tests/unit/engines/data/*.xyz` (5 files) + `tests/unit/engines/conftest.py` `load_case`, `test_set` the mission §5 shared test set | added | Slice 05 Task 2 | open |

## Engines: PySCF CPU (slice 06)

Rows D-030..D-034, D-037, D-039, D-049 and D-054 above were updated from `pending` by this slice. D-035, D-036, D-038, D-041 and D-042 (GPU preference, VRAM budget and estimate, per-evaluate probe) stay `pending` for slice 07.

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-096 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:160` keyed options `ecp`, `grids_level`, `conv_tol`, `init_guess`, `pcm_method`, `ladder_small_basis`, `stability`, `fd_step_bohr` | added | Slice 06 Mini-req 2 / ADR-0018: every result-changing setting is keyed and filled in `engine.stage` (implicit and explicit defaults key equal; each non-default value changes the key, tested) | open |
| D-097 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:262` `resolved_stage_for(state)`: ECP rule | added | R3 / R36: `ecp='auto'` stays in `engine.stage`; per state it resolves to the def2 basis name when Z > 36, `none` otherwise; non-def2 + Z > 36 without `ecp`, or explicit `none` with def2 + Z > 36, or an ECP PySCF lacks → `EngineInputError`; never written back. The starter ran def2 Rh/Pd all-electron | open |
| D-098 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:400` `_ladder`: `diis` → `level_shift` (0.25, damp 0.5) → `soscf` (`newton`) → `small_basis_projection` (`project_dm_nr2nr`) | added | R9: every attempted rung is recorded in `recovery_steps`; all failing → `ScfConvergenceError(steps)`; `ladder_max_cycle` is the DIIS rung's budget (later rungs `RUNG_MAX_CYCLE` 100) | open |
| D-099 | engines `pyscf_gpu_cpu` | — | `ladder_small_basis` default `minao` (def2-*) / `sto-3g` (others) | added | R37: `def2-sv(p)` does not exist in PySCF 2.15.1 (measured); `minao` covers the 5d metals that `sto-3g` lacks | open |
| D-100 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:469` `_stability`: mandatory internal stability analysis, up to 2 follows | added | R9 / red team (PdCl2 guess-dependent states 7.9 mEh apart): `stability:stable` / `stability:followed` recorded; still unstable → `ScfConvergenceError`. The starter had no stability analysis | open |
| D-101 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:60` `HESSIAN_SUPPORT` / `hessian_method_for` + keyed `hessian_mode` (`auto` \| `fd_gradients` \| `analytic`) | added | R41. `auto`, measured on PySCF 2.15.1 (`docs/prd/v0.2.0/evidence/pyscf-cpu-support.json`): HF analytic (≤ 3e-5 vs FD); every KS functional FD of analytic gradients (the analytic KS Hessian is off up to 84% for HBr at grid 3, 8% for HI+ECP at grid 9); ddCOSMO FD (no analytic Hessian). `fd_gradients` forces FD; `analytic` with KS or ddCOSMO → `EngineInputError` ("analytic KS Hessian is unreliable in PySCF 2.15.1 (R41)"). CPU grid response for the KS Hessian raises `NotImplementedError` (RKS and UKS). The starter used `mf.Hessian()` unconditionally | open |
| D-102 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:382` `_kernel`, `_build_mol`, `_gradient`, `_analytic_hessian` | added | PySCF errors caught by named type (`BasisNotFoundError`, `RuntimeError`, `KeyError`, `ValueError`, …) and re-raised as `EngineInputError` / `EngineRuntimeError` from the cause; no bare `Exception` | open |
| D-103 | engines `pyscf_gpu_cpu` | — | `docs/prd/v0.2.0/evidence/pyscf-cpu-support.json` | added | Slice 06 Mini-req 7: the Hessian support matrix (36 engine-path rows + extra grid/ECP measurements), generated by a seat command | open |

## Engines: PySCF GPU (slice 07)

Rows D-035, D-036, D-038, D-041 and D-042 above were updated from `pending` by this slice.

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-104 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:48` `gpu_modules()`; GPU path in `_make_mf` / `_run` | added | Slice 07: the same resolved stage builds `gpu4pyscf.scf` / `gpu4pyscf.dft` objects (DF, auxbasis, ECP, grids, conv_tol, init_guess, PCM, ladder, stability); GPU runs record `device="cuda"` and `device_reason="gpu4pyscf <version>"`. GPU − CPU measured ≤ 2.7e-9 Eh (water, hydroxide, hydroxyl UKS, Pd anion), cross-evaluation ≤ 1e-8 | open |
| D-105 | engines `pyscf_gpu_cpu` | — | ddCOSMO → CPU, `device_reason="ddcosmo_cpu_only"` | added | GPU4PySCF has no ddCOSMO (measured); C-PCM and IEF-PCM run on GPU (≤ 6e-12 Eh vs CPU) | open |
| D-106 | engines `pyscf_gpu_cpu` | — | estimate > budget → CPU, `device_reason="vram_estimate_over_budget"`, step `vram_estimate>budget->cpu` | added | Slice 07 Mini-req 3; never silent | open |
| D-107 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:95` `is_gpu_oom` + `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:109` `free_pools`; OOM → one CPU run, `device_reason="gpu_oom"`, step `gpu_oom->cpu` | added | Mini-req 5: exactly OutOfMemoryError, CUBLAS_STATUS_ALLOC_FAILED (3), CUSOLVER_STATUS_ALLOC_FAILED (2), cudaErrorMemoryAllocation (2); both pools freed; any other CuPy/CUDA error → `EngineRuntimeError`, no fallback; CuPy errors bypass the CPU error mapping (`_passthrough`, `engine.py:565`) so they reach this rule | open |
| D-108 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:21` `GPU_KS_ANALYTIC_HESSIAN_OK = True` (+ `GPU_KS_HESSIAN_GRID_RESPONSE = True`), `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:580` `_hessian_method` | added | R41/R42: GPU4PySCF 1.9.2's analytic KS Hessian with grid response is ≤ 3.1e-5 vs FD of GPU gradients in every measured class (RKS/UKS, DF/non-DF, PCM, def2 ECP, grids 3 and 9; `docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`), so GPU KS stages under `hessian_mode=auto` use it; without grid response it fails as on CPU (HBr 0.24) | open |
| D-109 | engines `pyscf_gpu_cpu` | — | `src/eta_rxncat/engines/pyscf_gpu_cpu/gpu.py:29` `GPU_STABILITY_MIN_ROTATIONS = 3`, `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:459` `_rotation_count` | added | Measured GPU4PySCF 1.9.2 defect: its stability Davidson asserts `nvar >= nroots` (3), so H2/sto-3g raised a bare AssertionError; R43: the rotation count is checked BEFORE calling stability; below 3 the engine analyses a CPU copy (`mf.to_cpu()`), follows any instability on the GPU from the copy's orbitals (max 2), and records `stability:cpu_copy (gpu4pyscf 1.9.2 stability assert, n_rotations<3)`; energy, forces and Hessian stay on cuda | open |
| D-110 | engines `pyscf_gpu_cpu` | — | `tests/unit/engines/data/decane.xyz` | added | n-decane calibration geometry (RDKit ETKDG randomSeed=61453, MMFF94-relaxed) | open |
| D-111 | engines `pyscf_gpu_cpu` | — | `docs/prd/v0.2.0/calibration/pyscf_vram.json`, `docs/prd/v0.2.0/evidence/pyscf-gpu-support.json` | added | Seat-command records (calibration; R41 GPU Hessian support matrix); tests check the code constants equal them | open |

## Engines: xtb (slice 08)

Rows D-016..D-020 and D-046 above were updated from `pending` by this slice (and D-053, the starter PySCF test that slice 06 left pending).

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-112 | engines `xtb_subprocess` | — | `src/eta_rxncat/engines/xtb_subprocess.py:206` `argv` | added | R4/R39/R45: `[xtb, input.xyz, --gfn, 2, --chrg, q, --uhf, m−1, --acc, a, --etemp, T, (--alpb, solvent, state), --grad]`; every call is `--grad` (only it writes `energy`/`gradient`; `--json` has 8 decimals); the starter used `--json` and `--grad`/`--hess` alternately | open |
| D-113 | engines `xtb_subprocess` | — | `src/eta_rxncat/engines/xtb_subprocess.py:316` `_evaluate`: Hessian = central FD of xtb gradients (keyed `fd_step_bohr` 0.005), 1 + 6N `--grad` calls | added | R45: xtb 6.8.0's `--hess` file is projected (translations/rotations removed; 2.7e-3 Eh/Bohr² from FD on water, out-of-plane diagonals exactly 0) and cannot be converted back (`docs/prd/v0.2.0/evidence/xtb-hessian-convention.json`); the starter read that file as the Cartesian Hessian | open |
| D-114 | engines `xtb_subprocess` | — | `src/eta_rxncat/engines/xtb_subprocess.py:266` `_invoke` / `src/eta_rxncat/engines/xtb_subprocess.py:241` `_run` | added | Each call in a fresh `tempfile.mkdtemp()` under TMPDIR, removed on success (kept on failure only with `keep_failed`); no shell; OMP/MKL threads and OMP_STACKSIZE from runtime arguments; timeout, `OSError`, non-zero exit and missing output → `EngineRuntimeError` with the stdout/stderr tail; the starter had no timeout or tail | open |
| D-115 | engines `xtb_subprocess` | — | `docs/licence-inventory.md` | added | New: external components used but never shipped; xtb 6.8.0 (LGPL-3.0 + bundled MKL/ifx, digest, TJ v0.2.0 Q2 A, ADR-0021); MACE and UMA rows reserved for slices 09/10 | open |
| D-116 | engines `xtb_subprocess` | — | `tests/unit/engines/data/xtb/` (recorded xtb 6.8.0 water `energy`, `gradient`, `hessian`, `--version`) | added | Default-suite parsing and fake-binary tests without the real binary | open |
