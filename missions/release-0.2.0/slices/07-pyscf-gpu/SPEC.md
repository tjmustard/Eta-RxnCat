---
id: OPR.0.2.0.7
slice: 07-pyscf-gpu
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Add GPU4PySCF dispatch to the PySCF engine on one resolved stage: ADR-0008 budget read once, calibrated VRAM estimate, ddCOSMO on CPU, a listed-OOM single CPU fallback with pool cleanup, and GPU-CPU agreement with a cross-evaluation check."
depends_on: [OPR.0.2.0.6, OPR.0.2.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/prd/v0.2.0/DISCREPANCIES.md, "docs/prd/v0.2.0/calibration/**", "docs/prd/v0.2.0/evidence/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [env, "UV_PROJECT_ENVIRONMENT=.venv-accept-gpu", "ETA_RXNCAT_ACCEPTANCE=1", uv, run, "--no-sync", pytest, "-m", gpu, tests/unit/engines/test_pyscf_gpu.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: PySCF engine, GPU path: GPU4PySCF dispatch, VRAM budget, calibrated estimate, OOM fallback

## Intent

Add GPU4PySCF dispatch to `PySCFEngine`. It runs on the GPU when the `gpu` extra and CUDA are
present and the estimated VRAM fits the 6.5 GiB budget; otherwise it runs the slice-06 CPU DF
path, recording why. A listed CUDA out-of-memory error falls back to CPU once, recorded. GPU and
CPU give the same answer for the same resolved stage.

Context the builder needs (self-contained).

Resolve measured on this host (RTX 5060 Ti, gpu4pyscf-cuda12x 1.9.2, B3LYP/def2-SVP, conv 1e-10):
- GPU − CPU, DF with `def2-universal-jkfit`: water 6.2e-12 Eh; `[PdCl₃(C₂H₄)]⁻` with ECP 4.9e-11;
- non-DF water: 7.3e-12; C-PCM ε 78.3553: 6.0e-12;
- GPU4PySCF ECP gradients and Hessians run (shapes N×3 and N×N×3×3);
- GPU4PySCF has `pcm` and `smd` solvent modules, and **no ddCOSMO**. Both C-PCM and IEF-PCM run
  on GPU and match CPU to 1e-6 rounding (replan 6 sweep);
- GPU UKS (hydroxyl, B3LYP/DF, `conv_tol` 1e-10): def2-SVP GPU − CPU = 7e-8 Eh, both internally
  stable. On STO-3G, GPU stops 7.3e-7 Eh from CPU and its stability check reports unstable
  (CPU: stable); following it moves the energy by 5e-7. This is a minimal-basis tolerance
  artefact, so keep GPU agreement proofs at def2-SVP as specified, and expect a possible
  `stability:followed` on minimal-basis GPU UKS;
- on linear PdCl₂, GPU `minao` reached a different SCF state from CPU `minao` (7.9 mEh). Slice
  06's mandatory stability analysis and keyed `init_guess` apply to the GPU path too.

The budget is `eta_rxncat.utils.hw_probe.vram_budget_bytes(total_bytes)` = min(6.5 GiB, total)
(ADR-0008), which is 6,979,321,856 B here. Get `total` from CuPy once, at construction. Never
call `probe_hardware()` per evaluation (it creates a torch CUDA context), and never import torch
in this engine (R10).

`.venv-accept-gpu` (slice 02's `--extra gpu` env on torch 2.13+cu129) is where GPU tests run.
`.venv` has no GPU stack, so GPU tests are marked `gpu` and run via `UV_PROJECT_ENVIRONMENT=.venv-accept-gpu`.

## 1. The Confidence Mandate

**Score: 9/10.** Dispatch, exceptions and agreement were measured. The residual is the estimate
calibration, which this slice measures and records.

## Mini-requirements

1. Dispatch, with runtime `device`:
   - `cpu` → slice 06;
   - `cuda` → GPU, or `EngineUnavailableError` if the gpu extra or CUDA is missing;
   - `auto` → GPU when `gpu4pyscf` and `cupy` import and a CUDA device exists, else CPU with
     `device_reason="gpu_unavailable"`.
   
   The GPU path builds the same mol, functional, DF, auxbasis, ECP, grids, conv_tol, init_guess,
   solvation, ladder and stability as slice 06, using `gpu4pyscf.dft` / `gpu4pyscf.scf`. One
   resolved stage drives both paths, and the device is not keyed.
2. ddCOSMO → always CPU, `device_reason="ddcosmo_cpu_only"`. C-PCM / IEF-PCM run on GPU via
   `gpu4pyscf` PCM.
3. Budget and estimate:
   - at construction, `total = cupy.cuda.runtime.memGetInfo()[1]`;
     `budget = vram_budget_bytes(total)`;
   - `estimate_bytes(nao, naux) = f · 8 · (naux · nao(nao+1)/2 + 40 · nao²)`, with `f`
     (`VRAM_SAFETY: Final`) from calibration;
   - estimate > budget → CPU DF, `device_reason="vram_estimate_over_budget"`, and
     `recovery_steps` gets `"vram_estimate>budget->cpu"`.
4. Calibration:
   - a seat command (not a test) runs water, the Pd anion, and n-decane (RDKit ETKDG,
     `randomSeed=61453`, MMFF-relaxed, committed as `tests/unit/engines/data/decane.xyz`);
   - each runs on the GPU and records `nao`, `naux`, the estimate with f = 1, and the measured
     peak `cupy.get_default_memory_pool().total_bytes()` after the SCF and gradient;
   - write `docs/prd/v0.2.0/calibration/pyscf_vram.json`;
   - `VRAM_SAFETY` = ⌈max(measured / estimate_f1) × 1.25, to 2 decimals⌉, and at least 1.0.
5. OOM. Exactly these mean GPU out-of-memory:
   - `cupy.cuda.memory.OutOfMemoryError`;
   - `cupy_backends.cuda.libs.cublas.CUBLASError` with status `CUBLAS_STATUS_ALLOC_FAILED`;
   - `cupy_backends.cuda.libs.cusolver.CUSOLVERError` with status `CUSOLVER_STATUS_ALLOC_FAILED`;
   - `cupy.cuda.runtime.CUDARuntimeError` with `cudaErrorMemoryAllocation`.
   
   On one of these:
   - free `cupy.get_default_memory_pool()` and `cupy.get_default_pinned_memory_pool()` (call
     `free_all_blocks()`);
   - run the CPU DF path once;
   - set `device_reason="gpu_oom"`, and add `"gpu_oom->cpu"` to `recovery_steps`.
   
   Any other CuPy or CUDA error → `EngineRuntimeError`, with no fallback.
6. Results: `device = "cuda"` or `"cpu"`; GPU arrays converted to plain lists; the Hessian
   (N,N,3,3) → 3N×3N, symmetrised, with `hessian_method`. If GPU4PySCF lacks an analytic Hessian
   for a combination, use FD of GPU analytic gradients (labelled). Record the GPU support matrix
   in `docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`.
7. Register rows (status `open`) vs the starter: the GB formula → the calibrated estimate plus the
   ADR-0008 budget; the per-evaluate probe dropped; OOM handling; ddCOSMO on CPU.

## 3. Implementation Plan (Task List)

- [ ] Task 1: dispatch and the GPU builder (Mini-requirements 1–2).
- [ ] Task 2: budget, estimate, calibration record (Mini-requirements 3–4).
- [ ] Task 3: OOM handling (Mini-requirement 5) and results (Mini-requirement 6).
- [ ] Task 4: tests in `tests/unit/engines/test_pyscf_gpu.py`, marked `gpu` and run in
  `.venv-accept-gpu`. Plus default-suite unit tests for estimate and dispatch logic with fakes,
  which need no GPU.
- [ ] Task 5: register rows; four gates in `.venv`; the `gpu` tests in `.venv-accept-gpu`;
  `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** call `probe_hardware()` or import torch in the PySCF engine.
- **DO NOT** key the device, or let the GPU path differ from the CPU path in any keyed setting.
- **DO NOT** catch any CuPy or CUDA exception outside Mini-requirement 5's list, or fall back more
  than once.
- **DO NOT** substitute CPU silently. Every CPU run on a GPU-capable host carries a
  `device_reason`.
- **DO NOT** loosen the agreement tolerance. A disagreement is a finding with output.

## Proof contract

- [ ] `gpu`, B3LYP/def2-SVP, `.venv-accept-gpu`. For water, hydroxide, hydroxyl (UKS) and the Pd
  anion (ECP):
  - |E_gpu − E_cpu| ≤ 1e-6 Eh (record the values; resolve saw ≤5e-11);
  - both converged, `stability:stable`;
  - cross-evaluation: the CPU energy evaluated at the GPU density equals E_gpu within 1e-8 Eh;
  - `device == "cuda"` for GPU runs.
- [ ] `gpu`:
  - GPU gradient vs CPU gradient ≤1e-6 Eh/Bohr;
  - GPU Hessian (water) vs CPU analytic Hessian ≤1e-5 Eh/Bohr²;
  - water C-PCM GPU vs CPU ≤1e-6 Eh;
  - ddCOSMO with `device="auto"` → `device == "cpu"`, `device_reason == "ddcosmo_cpu_only"`.
- [ ] Default suite, fakes:
  - a budget of 1 byte → CPU, with `vram_estimate_over_budget` and the recorded step;
  - a fake GPU kernel raising `OutOfMemoryError` once → CPU, `gpu_oom`, both pools'
    `free_all_blocks` called once;
  - a fake `CUDARuntimeError` that is not an allocation error → `EngineRuntimeError` with no
    fallback;
  - `device="cuda"` without gpu4pyscf → `EngineUnavailableError` naming `uv sync --extra gpu`.
- [ ] `docs/prd/v0.2.0/calibration/pyscf_vram.json` has three entries, and `VRAM_SAFETY` in code
  equals the record's derived value. For each entry, estimate (with `VRAM_SAFETY`) ≥ measured.
- [ ] `python -c "import eta_rxncat.engines.pyscf_gpu_cpu, sys; assert 'torch' not in sys.modules"`
  in `.venv-accept-gpu` → exit 0.
- [ ] The four gates in `.venv` → exit 0.
  `UV_PROJECT_ENVIRONMENT=.venv-accept-gpu uv run --no-sync pytest -m gpu tests/unit/engines/test_pyscf_gpu.py`
  → exit 0, with 0 skipped under `ETA_RXNCAT_ACCEPTANCE=1`.

## Source material

- Plan PR #6; mission R2, R3, R9, R10, "Resolve's host measurements"; ADR-0008, ADR-0018
  (PROPOSED); slice 06 SPEC; `src/eta_rxncat/utils/hw_probe.py` (`vram_budget_bytes`).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.6 (CPU path), OPR.0.2.0.2 (the cu129 GPU stack and `.venv-accept-gpu`)
