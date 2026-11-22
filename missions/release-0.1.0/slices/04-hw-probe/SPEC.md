---
id: OPR.0.1.0.4
slice: 04-hw-probe
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the typed hardware probe with the 6.5 GiB VRAM budget and a GPU-vs-CPU smoke test with a numeric pass criterion, proven on the CPU path."
depends_on: [OPR.0.1.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_hw_probe
parent: null
hacf_touches: ["src/eta_rxncat/utils/**", "tests/unit/utils/**", "tests/gpu/**", docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/utils]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Hardware probe and GPU smoke test (CPU-audited)

## Intent

Implement `eta_rxncat.utils.hw_probe`: a typed `probe_hardware()` report of PyTorch/CUDA,
GPU4PySCF, the GPU, total VRAM and the 6.5 GiB budget, and `run_smoke()` — an H₂O/STO-3G
GPU4PySCF-vs-CPU SCF plus a CUDA matmul with a numeric pass criterion — proven on the CPU path.

Context the builder needs (self-contained): the plan's PR #2 asks for a probe "verifying PyTorch
CUDA `12.8+` (`sm_120`), `GPU4PySCF` (`1.8.0+`) JIT/native kernel execution, and 8 GB VRAM
ceiling detection", with "auto-fallback to CPU `PySCF` above ~6.5 GB VRAM budget". The host is an
RTX 5060 Ti (8151 MiB, compute capability 12.0). v0.2.0's PySCF engine will consume the budget
through this module's Python API. In this slice `torch` and `gpu4pyscf` are **not installed**
(the optional extras arrive in slice 06); the GPU path is run for real in slice 07. So: implement
both paths, unit-test everything with mocks/monkeypatching on CPU, and prove the real "skipped"
behaviour on this environment. The starter `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py`
is **reference only** (it checks importability only and uses `0.80 × total`). Node
`eta_rxncat_hw_probe` is **not yet in the graph**: register it with `hyper_ledger.py ensure-node
--from-spec <this SPEC.md> --dimension Module`.

## 1. The Confidence Mandate

**Score: 9/10.** Report schema, budget rule, pass criterion and exit semantics are fixed.
Residual: the real GPU behaviour (JIT time, exact energies) is only observable in slice 07; the
pass criterion here is relative (GPU vs CPU) so no literature energy is needed.

## Mini-requirements

1. US-003 `probe_hardware() -> HardwareReport` (pydantic model, `extra="forbid"`), never raises
   for a missing package or absent GPU. JSON fields: `report_schema: 1`, `python_version`,
   `platform`, `torch: {installed, version, cuda_available, cuda_version}`, `gpu: {name,
   compute_capability ("12.0" form), total_vram_bytes, total_vram_gib (2 dp), free_vram_bytes} |
   null`, `gpu4pyscf: {installed, version}`, `vram_budget_gib: 6.5`, `vram_budget_bytes:
   min(int(6.5 * 2**30), total_vram_bytes) | null`, `flags: list[str]`, `notes: list[str]`.
   Flags (exact strings): `torch_missing`, `cuda_unavailable`, `torch_cuda_below_12.8`,
   `gpu4pyscf_missing`, `gpu4pyscf_below_1.8.0`. Versions compared by their numeric dotted prefix
   (`"2.13.0+cu128"` → (2, 13, 0); `"12.8"` → (12, 8)). Public constants:
   `VRAM_BUDGET_GIB: Final = 6.5`, `MIN_TORCH_CUDA: Final = (12, 8)`,
   `MIN_GPU4PYSCF: Final = (1, 8, 0)`; `vram_budget_bytes(total_bytes: int) -> int`.
2. US-004a `run_smoke(timeout_s: float = 600.0) -> SmokeResult`. Skipped (`status="skipped"`,
   `reason` set) when torch, gpu4pyscf or CUDA is unavailable — determined from `probe_hardware()`
   before any child process. Otherwise run the work in a child process
   (`subprocess.run([sys.executable, "-m", "eta_rxncat.utils._smoke_child"], timeout=timeout_s,
   capture_output=True)`; the child prints one JSON object); timeout or non-JSON output → `fail`
   with the reason. Work: H₂O (Å) O (0, 0, 0.1173), H (0, 0.7572, −0.4692), H (0, −0.7572,
   −0.4692), charge 0, spin 0, basis `sto-3g`; `gpu4pyscf.scf.RHF(mol).kernel()` and
   `pyscf.scf.RHF(mol).kernel()`; torch: `torch.backends.cuda.matmul.allow_tf32 = False`, seeded
   (`torch.Generator().manual_seed(0)`) float64 512×512 A, B on CPU, `C_gpu = (A.cuda() @
   B.cuda())`, record `C_gpu.device.type`, `max_abs_diff = (C_gpu.cpu() − A @ B).abs().max()`.
   **Pass** iff both SCFs converged, `|E_gpu − E_cpu| ≤ 1e-6` Eh, the GPU `mo_coeff` is a
   `cupy.ndarray`, device type is `"cuda"`, `max_abs_diff ≤ 1e-9`. Else `fail` with a reason
   naming the failed check. `SmokeResult` JSON: `result_schema: 1`, `status ∈ {pass, fail,
   skipped}`, `reason: str | null`, `scf: {converged_gpu, converged_cpu, energy_gpu_eh,
   energy_cpu_eh, abs_diff_eh, tolerance_eh: 1e-6, mo_on_device, seconds} | null`, `torch_op:
   {device, max_abs_diff, tolerance: 1e-9, seconds} | null`, `total_seconds`, `timeout_s`,
   `host: HardwareReport`. `smoke_exit_code(result) -> int`: pass 0, fail 1, skipped 3.
3. `tests/gpu/test_smoke.py`: one test marked `@pytest.mark.gpu` asserting
   `run_smoke().status == "pass"` (prints the JSON on failure). Deselected by default
   (`addopts = "-m 'not gpu'"` from slice 01); `uv run pytest -m gpu --collect-only -q` collects it.
4. US-011 (hardware probe area): `docs/prd/v0.1.0/DISCREPANCIES.md` `## Hardware probe` gains a row
   for every public name of the starter `utils/*.py`, each test function of the starter
   `tests/unit/test_hw_probe.py`, and `added` rows. Known `changed` rows: VRAM budget
   `0.80 × total` → min(6.5 GiB, total) (Master Plan "~6.5 GB VRAM budget"; R12 GiB); probe depth
   importability (`find_spec`) → kernel execution via `--smoke` (plan PR #2). Status `open`.

## 3. Implementation Plan (Task List)

- [ ] Task 1 — `utils/__init__.py` (docstring), version-prefix parser, constants, `vram_budget_bytes`.
- [ ] Task 2 — `HardwareReport` and nested models; `probe_hardware()` with function-local imports of
  `torch`/`gpu4pyscf` guarded by `ImportError` (and `importlib.metadata.version` for versions).
- [ ] Task 3 — `_smoke_child.py` (the work above, prints JSON; only runs under `__main__`).
- [ ] Task 4 — `SmokeResult`, `run_smoke`, `smoke_exit_code`.
- [ ] Task 5 — Unit tests in `tests/unit/utils/` with monkeypatched fakes for: no torch; torch
  without CUDA; CUDA 12.4 torch; gpu4pyscf 1.7.0; a fake 8151 MiB GPU; a fake 24 GiB GPU; a child
  that times out; a child that prints passing / each kind of failing JSON.
- [ ] Task 6 — `tests/gpu/test_smoke.py` (Mini-requirement 3).
- [ ] Task 7 — Register rows; four gates exit 0 (mypy strict with the slice-01 overrides).

## 4. The Negative Space (Constraints)

- **DO NOT** import `torch`, `gpu4pyscf`, `cupy` or `pyscf` at module level anywhere in `eta_rxncat`.
- **DO NOT** import anything from `eta_rxncat.core`, `store` or `cli` in `utils`.
- **DO NOT** invoke `git`, `nvidia-smi` or the network from product code.
- **DO NOT** use free VRAM to compute the budget (report it only).
- **DO NOT** loosen tolerances, substitute CPU for GPU, or report `pass` without every check.
- **DO NOT** make any unit test or CI step need a GPU; GPU work lives only under `tests/gpu/` with the `gpu` marker.
- **DO NOT** install the GPU or MLIP packages or edit `[project.optional-dependencies]` (slice 06).

## Proof contract

- [ ] Fake 8151 MiB GPU (8,546,942,976 bytes), CUDA 12.8, gpu4pyscf 1.8.0 → `compute_capability == "12.0"`, `vram_budget_bytes == 6979321856`, `flags == []`.
- [ ] Fake 24 GiB GPU → `vram_budget_bytes == 6979321856`; fake 4 GiB GPU → `vram_budget_bytes == 4294967296`.
- [ ] No torch → `flags` contains `torch_missing` and `cuda_unavailable`, `gpu is None`, `vram_budget_bytes is None`; no exception.
- [ ] torch `2.6.0+cu124` → flag `torch_cuda_below_12.8`; gpu4pyscf `1.7.0` → `gpu4pyscf_below_1.8.0`; absent → `gpu4pyscf_missing`.
- [ ] `run_smoke()` on this environment (no torch) → `status == "skipped"`, `reason` mentions torch, `smoke_exit_code == 3`, no child process started.
- [ ] Child prints a passing JSON → `pass`/0; |ΔE| = 2e-6 → `fail`/1 naming the energy check; device `"cpu"` → `fail`; `max_abs_diff` 1e-6 → `fail`; `mo_on_device` false → `fail`; child times out (timeout 0.5 s with a sleeping child) → `fail` naming the timeout.
- [ ] `uv run pytest -m gpu --collect-only -q` collects `tests/gpu/test_smoke.py`; plain `uv run pytest` does not run it.
- [ ] `python -c "import eta_rxncat.utils.hw_probe, sys; assert 'torch' not in sys.modules"` (subprocess test) → exit 0.
- [ ] Four gates exit 0; DISCREPANCIES.md has a row for every probe starter item.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (v0.1.0 PR #2; Hypothesis 3; Hardware Constraint).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py`, `tests/unit/test_hw_probe.py` (reference only).
- Mission `missions/release-0.1.0/SPEC.md` §5 Contracts (Hardware probe, GPU smoke) and trade-off log R10, R12, R13, R28.

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.1 (scaffold: package, pytest marker config, mypy overrides)
