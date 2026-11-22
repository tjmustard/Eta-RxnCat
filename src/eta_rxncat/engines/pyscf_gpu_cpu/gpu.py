"""GPU4PySCF support for the PySCF engine (v0.2.0 slice 07): availability, budget, OOM rules.

Nothing here imports gpu4pyscf, CuPy or torch at module level; ``gpu_modules`` imports
gpu4pyscf and CuPy lazily, and torch is never imported (R10).
"""

import importlib
from types import SimpleNamespace
from typing import Any, Final

VRAM_OVERHEAD_BYTES: Final = 64 * 2**20
"""Fixed VRAM overhead (CuPy / cuBLAS / grid workspace) added to every estimate: twice the
largest peak measured for a tiny system (water, 30.7 MB) in
``docs/prd/v0.2.0/calibration/pyscf_vram.json``."""

VRAM_SAFETY: Final = 5.13
"""Safety factor ``f`` of ``estimate_bytes``, derived from the calibration record as
max(1.0, ceil(max((measured - VRAM_OVERHEAD_BYTES) / estimate_f1) * 1.25, 2 decimals)) (slice 07
Mini-req 4, with the overhead term; a test checks both constants equal the record)."""

GPU_KS_ANALYTIC_HESSIAN_OK: Final = True
"""Whether GPU4PySCF 1.9.2's analytic KS Hessian may be used under ``hessian_mode="auto"``
(R41): only if EVERY measured case in ``docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`` is
<= 1e-4 Eh/Bohr^2 against FD of GPU analytic gradients (a test checks it equals the record)."""

GPU_KS_HESSIAN_GRID_RESPONSE: Final = True
"""The Hessian ``grid_response`` setting the verdict above was measured with."""

GPU_STABILITY_MIN_ROTATIONS: Final = 3
"""GPU4PySCF 1.9.2's internal stability Davidson asserts ``nvar >= nroots`` with nroots 3; below
that (e.g. H2/sto-3g, 1 rotation) the engine analyses a CPU copy instead (measured, slice 07)."""

GPU_STABILITY_CPU_COPY_STEP: Final = (
    "stability:cpu_copy (gpu4pyscf 1.9.2 stability assert, n_rotations<3)"
)
"""The ``recovery_steps`` entry recorded before the stability verdict on that path (R43)."""

CUDA_RUNTIME_ALLOC = 2
"""``cudaErrorMemoryAllocation``."""

CUBLAS_ALLOC_FAILED = 3
"""``CUBLAS_STATUS_ALLOC_FAILED``."""

CUSOLVER_ALLOC_FAILED = 2
"""``CUSOLVER_STATUS_ALLOC_FAILED``."""


def gpu_modules() -> SimpleNamespace | None:
    """The GPU modules (``cupy``, ``gpu4pyscf.scf``, ``gpu4pyscf.dft``, error classes), or None.

    None means the ``gpu`` extra is not installed or no CUDA device is visible.
    """
    try:
        cupy = importlib.import_module("cupy")
        gpu_scf = importlib.import_module("gpu4pyscf.scf")
        gpu_dft = importlib.import_module("gpu4pyscf.dft")
        gpu4pyscf = importlib.import_module("gpu4pyscf")
        memory = importlib.import_module("cupy.cuda.memory")
        runtime = importlib.import_module("cupy_backends.cuda.api.runtime")
        driver = importlib.import_module("cupy_backends.cuda.api.driver")
        cublas = importlib.import_module("cupy_backends.cuda.libs.cublas")
        cusolver = importlib.import_module("cupy_backends.cuda.libs.cusolver")
    except ImportError:
        return None
    try:
        count = cupy.cuda.runtime.getDeviceCount()
    except runtime.CUDARuntimeError:
        return None
    if count < 1:
        return None
    return SimpleNamespace(
        cupy=cupy,
        scf=gpu_scf,
        dft=gpu_dft,
        version=str(gpu4pyscf.__version__),
        OutOfMemoryError=memory.OutOfMemoryError,
        CUDARuntimeError=runtime.CUDARuntimeError,
        CUDADriverError=driver.CUDADriverError,
        CUBLASError=cublas.CUBLASError,
        CUSOLVERError=cusolver.CUSOLVERError,
    )


def gpu_error_types(gpu: SimpleNamespace) -> tuple[type[BaseException], ...]:
    """Every CuPy / CUDA exception type the GPU path can raise (OOM or not)."""
    return (
        gpu.OutOfMemoryError,
        gpu.CUDARuntimeError,
        gpu.CUDADriverError,
        gpu.CUBLASError,
        gpu.CUSOLVERError,
    )


def is_gpu_oom(gpu: SimpleNamespace, exc: BaseException) -> bool:
    """Whether ``exc`` is one of exactly the four listed GPU out-of-memory errors (Mini-req 5)."""
    if isinstance(exc, gpu.OutOfMemoryError):
        return True
    status = getattr(exc, "status", None)
    if isinstance(exc, gpu.CUBLASError):
        return status == CUBLAS_ALLOC_FAILED
    if isinstance(exc, gpu.CUSOLVERError):
        return status == CUSOLVER_ALLOC_FAILED
    if isinstance(exc, gpu.CUDARuntimeError):
        return status == CUDA_RUNTIME_ALLOC
    return False


def free_pools(gpu: SimpleNamespace) -> None:
    """Release CuPy's default device and pinned memory pools."""
    gpu.cupy.get_default_memory_pool().free_all_blocks()
    gpu.cupy.get_default_pinned_memory_pool().free_all_blocks()


def estimate_bytes(
    nao: int, naux: int, safety: float = VRAM_SAFETY, overhead: int = VRAM_OVERHEAD_BYTES
) -> int:
    """VRAM estimate ``f * 8 * (naux * nao(nao+1)/2 + 40 * nao^2) + overhead`` bytes."""
    return int(safety * 8 * (naux * nao * (nao + 1) / 2 + 40 * nao * nao)) + overhead


def to_host(value: Any) -> Any:
    """A NumPy copy of a CuPy array (or the value itself if it is already on the host)."""
    get = getattr(value, "get", None)
    return get() if callable(get) else value
