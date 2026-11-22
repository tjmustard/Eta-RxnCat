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
| D-013 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:20` `RDKitFFEngine(force_field="UFF")` | — | pending | Engine class (UFF/MMFF94/MMFF94s) | open |
| D-014 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:24` `RDKitFFEngine.name` | — | pending | Instance attribute | open |
| D-015 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:25` `RDKitFFEngine.force_field` | — | pending | Instance attribute | open |
| D-016 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:82` `XTBSubprocessEngine(method="GFN2-xTB", solvation=None, xtb_executable="xtb")` | — | pending | Engine class | open |
| D-017 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:91` `XTBSubprocessEngine.name` | — | pending | Instance attribute | open |
| D-018 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:92` `XTBSubprocessEngine.method` | — | pending | Instance attribute | open |
| D-019 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:93` `XTBSubprocessEngine.solvation` | — | pending | Instance attribute | open |
| D-020 | engines `rdkit_xtb` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:94` `XTBSubprocessEngine.xtb_executable` | — | pending | Instance attribute | open |
| D-021 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:10` `EV_TO_HARTREE` | — | pending | Unit constant | open |
| D-022 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:24` `atomic_numbers_from_symbols(symbols)` (table stops at Hg; no lanthanides 58–71) | — | pending | Public function | open |
| D-023 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:28` `MACEEngine(model_name="medium", device="auto")` | — | pending | Engine class | open |
| D-024 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:32` `MACEEngine.name` | — | pending | Instance attribute | open |
| D-025 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:33` `MACEEngine.model_name` | — | pending | Instance attribute | open |
| D-026 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:95` `UMADirectEngine(model_name="uma-s-1.2.1", task_name="omol", device="auto")` | — | pending | Engine class | open |
| D-027 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:104` `UMADirectEngine.name` | — | pending | Instance attribute | open |
| D-028 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:105` `UMADirectEngine.model_name` | — | pending | Instance attribute | open |
| D-029 | engines `mlip` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:106` `UMADirectEngine.task_name` | — | pending | Instance attribute | open |
| D-030 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:12` `PySCFEngine(functional="wB97X-D3BJ", basis="def2-SVP", solvation=None, prefer_gpu=True, vram_budget_gb=6.5, density_fit=True)` | — | pending | Engine class | open |
| D-031 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:24` `PySCFEngine.name` | — | pending | Instance attribute | open |
| D-032 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:25` `PySCFEngine.functional` | — | pending | Instance attribute | open |
| D-033 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:26` `PySCFEngine.basis` | — | pending | Instance attribute | open |
| D-034 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:27` `PySCFEngine.solvation` | — | pending | Instance attribute | open |
| D-035 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:28` `PySCFEngine.prefer_gpu` | — | pending | Instance attribute | open |
| D-036 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:29` `PySCFEngine.vram_budget_gb` | — | pending | Instance attribute | open |
| D-037 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:30` `PySCFEngine.density_fit` | — | pending | Instance attribute | open |
| D-038 | engines `pyscf_engine` | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:32` `PySCFEngine.estimate_vram_gb(n_basis_functions)` | — | pending | Public method | open |

## Engines: known draft issues (seeds)

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-039 | solvation | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:54` `_attach_solvation` uses only `dielectric`; `SolvationSpec.solvent` is ignored (ddCOSMO/PCM run at the default eps when only a solvent name is given) | — | pending | Seed: solvent name ignored | open |
| D-040 | rdkit | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:37` `except Exception: pass` around `DetermineConnectivity` | — | pending | Seed: swallowed perception errors | open |
| D-041 | pyscf | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:32` `0.8 + 4.5e-6 * n_bf**2` GB VRAM estimate | — | pending | Seed: the GB VRAM formula (decimal GB vs the GiB budget; uncalibrated) | open |
| D-042 | pyscf | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:141` `probe_hardware()` called inside every `_evaluate_impl` | — | pending | Seed: the per-evaluate probe | open |
| D-043 | uma | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:137` positions and cell built as `torch.float32` | — | pending | Seed: float32 UMA positions | open |
| D-044 | mace | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:50` `mace_mp(model=..., device=..., default_dtype="float64")` (ASE calculator factory, may download) | — | pending | Seed: `mace_mp` usage | open |
| D-045 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:24` engine `name` `rdkit_uff` / `rdkit_mmff94` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-046 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/rdkit_xtb.py:91` engine `name` `xtb_gfn2-xtb` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-047 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:32` engine `name` `mace_medium` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-048 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:104` engine `name` `uma_uma-s-1.2.1` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-049 | names | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/pyscf_engine.py:24` engine `name` `pyscf_<xc>_<basis>` | — | pending | Seed: engine name differs from the frozen tag | open |
| D-050 | mlip | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:85` MACE Hessian by `numerical_hessian` (finite differences) | — | pending | Seed: FD MLIP Hessians | open |
| D-051 | mlip | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/mlip.py:161` UMA Hessian by `numerical_hessian` (finite differences) | — | pending | Seed: FD MLIP Hessians | open |

## Tests

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-052 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:24` `test_rdkit_uff_energy_and_forces` | — | pending | Starter test; mapped by the engine slices | open |
| D-053 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:34` `test_pyscf_cpu_energy_gradient_and_vram_guard` | — | pending | Starter test; mapped by the engine slices | open |
| D-054 | tests | `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/tests/unit/test_engines_v020.py:38` `assert res.electronic_energy_hartree < -75.0` (B3LYP/STO-3G water) | — | pending | Seed: the `< −75.0` test (a loose bound, not a reference value) | open |

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
