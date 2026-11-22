"""Hardware probe (PyTorch/CUDA, GPU4PySCF, VRAM budget) and the GPU-vs-CPU smoke test.

``torch``, ``gpu4pyscf``, ``cupy`` and ``pyscf`` are imported only inside functions, so importing
this module is cheap and works on hosts without them. ``probe_hardware`` never raises for a
missing package or an absent GPU; ``run_smoke`` runs the GPU work in a child process.
"""

import importlib.metadata
import json
import math
import platform
import re
import subprocess
import sys
import time
from types import ModuleType
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

VRAM_BUDGET_GIB: Final = 6.5
"""Active VRAM budget for GPU work, in GiB (Master Plan "~6.5 GB VRAM budget")."""

MIN_TORCH_CUDA: Final = (12, 8)
"""Lowest PyTorch CUDA runtime that supports sm_120 (Blackwell)."""

MIN_GPU4PYSCF: Final = (1, 8, 0)
"""Lowest GPU4PySCF version with sm_120 kernels."""

SCF_TOLERANCE_EH: Final = 1e-6
"""Largest accepted |E_gpu - E_cpu| in Hartree."""

MATMUL_TOLERANCE: Final = 1e-9
"""Largest accepted max-abs difference of the float64 CUDA matmul against the CPU result."""

_TORCH_DISTRIBUTIONS: Final = ("torch",)
_GPU4PYSCF_DISTRIBUTIONS: Final = ("gpu4pyscf-cuda12x", "gpu4pyscf-cuda13x", "gpu4pyscf")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


def parse_version_prefix(version: str) -> tuple[int, ...]:
    """Return the numeric dotted prefix of a version string.

    ``"2.13.0+cu128"`` gives ``(2, 13, 0)``, ``"12.8"`` gives ``(12, 8)`` and a string without a
    leading number gives ``()``.
    """
    match = re.match(r"\d+(?:\.\d+)*", version.strip())
    return tuple(int(part) for part in match.group(0).split(".")) if match else ()


def vram_budget_bytes(total_bytes: int) -> int:
    """Return the VRAM budget for a GPU with ``total_bytes`` of memory: min(6.5 GiB, total)."""
    return min(int(VRAM_BUDGET_GIB * 2**30), total_bytes)


class TorchInfo(_Model):
    """PyTorch installation and CUDA runtime."""

    installed: bool
    version: str | None
    cuda_available: bool
    cuda_version: str | None


class GpuInfo(_Model):
    """The first CUDA device."""

    name: str
    compute_capability: str
    total_vram_bytes: int
    total_vram_gib: float
    free_vram_bytes: int | None


class Gpu4PySCFInfo(_Model):
    """GPU4PySCF installation."""

    installed: bool
    version: str | None


class HardwareReport(_Model):
    """What this host can run: PyTorch/CUDA, the GPU, GPU4PySCF and the VRAM budget.

    ``flags`` holds machine-readable problems (``torch_missing``, ``cuda_unavailable``,
    ``torch_cuda_below_12.8``, ``gpu4pyscf_missing``, ``gpu4pyscf_below_1.8.0``); ``notes`` holds
    human-readable detail.
    """

    report_schema: Literal[1] = 1
    python_version: str
    platform: str
    torch: TorchInfo
    gpu: GpuInfo | None
    gpu4pyscf: Gpu4PySCFInfo
    vram_budget_gib: float = VRAM_BUDGET_GIB
    vram_budget_bytes: int | None
    flags: list[str]
    notes: list[str]


def _import(name: str) -> ModuleType | None:
    """Import ``name``; whatever the import raises propagates (the test seam for fake hosts)."""
    return importlib.import_module(name)


def _dist_version(distributions: tuple[str, ...]) -> str | None:
    """Return the installed version of the first of ``distributions`` that is present."""
    for dist in distributions:
        try:
            return importlib.metadata.version(dist)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def _load(
    name: str, distributions: tuple[str, ...], notes: list[str]
) -> tuple[ModuleType | None, str | None]:
    """Import ``name`` without raising.

    Returns:
        ``(module, None)`` on success; ``(None, version)`` when the distribution is installed but
        the import raised (a broken install, noted); ``(None, None)`` when it is not installed.
    """
    try:
        module = _import(name)
    except Exception as exc:  # a broken install can raise OSError, RuntimeError, ...
        version = _dist_version(distributions)
        if version is not None or not isinstance(exc, ImportError):
            notes.append(f"Importing {name} raised {type(exc).__name__}: {exc}")
        return None, version
    return module, None


def _torch_cuda_version(torch: ModuleType) -> str | None:
    """Return torch's CUDA runtime version, falling back to the ``+cuNNN`` local tag."""
    cuda = getattr(getattr(torch, "version", None), "cuda", None)
    if isinstance(cuda, str) and cuda:
        return cuda
    tag = re.search(r"\+cu(\d+)(\d)$", str(getattr(torch, "__version__", "")))
    return f"{tag.group(1)}.{tag.group(2)}" if tag else None


def _probe_torch(notes: list[str]) -> tuple[TorchInfo, GpuInfo | None, bool]:
    """Probe PyTorch and its first CUDA device; never raises.

    Returns:
        The torch info, the GPU (or ``None``) and whether an installed torch failed to import.
    """
    torch, broken_version = _load("torch", _TORCH_DISTRIBUTIONS, notes)
    if torch is None:
        if broken_version is not None:
            info = TorchInfo(
                installed=True, version=broken_version, cuda_available=False, cuda_version=None
            )
            return info, None, True
        notes.append("PyTorch is not installed (the gpu extra provides it).")
        return (
            TorchInfo(installed=False, version=None, cuda_available=False, cuda_version=None),
            None,
            False,
        )
    version = str(getattr(torch, "__version__", "")) or None
    cuda_version = _torch_cuda_version(torch)
    try:
        cuda_available = bool(torch.cuda.is_available())
    except Exception as exc:  # a broken CUDA install must not crash the probe
        notes.append(f"torch.cuda.is_available() raised {type(exc).__name__}: {exc}")
        cuda_available = False
    info = TorchInfo(
        installed=True, version=version, cuda_available=cuda_available, cuda_version=cuda_version
    )
    if not cuda_available:
        notes.append("PyTorch reports no usable CUDA device.")
        return info, None, False
    try:
        props = torch.cuda.get_device_properties(0)
        total = int(props.total_memory)
        gpu = GpuInfo(
            name=str(props.name),
            compute_capability=f"{props.major}.{props.minor}",
            total_vram_bytes=total,
            total_vram_gib=round(total / 2**30, 2),
            free_vram_bytes=None,
        )
    except Exception as exc:
        notes.append(f"Reading CUDA device 0 failed: {type(exc).__name__}: {exc}")
        return info, None, False
    try:
        free, _ = torch.cuda.mem_get_info(0)
        gpu = gpu.model_copy(update={"free_vram_bytes": int(free)})
    except Exception as exc:
        notes.append(f"Free VRAM unavailable: {type(exc).__name__}: {exc}")
    return info, gpu, False


def _gpu4pyscf_version(module: ModuleType) -> str | None:
    """Return GPU4PySCF's version from the module or its distribution metadata."""
    version = getattr(module, "__version__", None)
    if isinstance(version, str) and version:
        return version
    return _dist_version(_GPU4PYSCF_DISTRIBUTIONS)


def _probe_gpu4pyscf(notes: list[str]) -> tuple[Gpu4PySCFInfo, bool]:
    """Probe GPU4PySCF; never raises.

    Returns:
        The GPU4PySCF info and whether an installed GPU4PySCF failed to import.
    """
    module, broken_version = _load("gpu4pyscf", _GPU4PYSCF_DISTRIBUTIONS, notes)
    if module is None:
        if broken_version is not None:
            return Gpu4PySCFInfo(installed=True, version=broken_version), True
        notes.append("GPU4PySCF is not importable (the gpu extra provides it).")
        return Gpu4PySCFInfo(installed=False, version=None), False
    return Gpu4PySCFInfo(installed=True, version=_gpu4pyscf_version(module)), False


def _flags(
    torch: TorchInfo, torch_failed: bool, gpu4pyscf: Gpu4PySCFInfo, gpu4pyscf_failed: bool
) -> list[str]:
    """Return the report flags, in a fixed order."""
    flags: list[str] = []
    if not torch.installed:
        flags.append("torch_missing")
    if torch_failed:
        flags.append("torch_import_failed")
    if not torch.cuda_available:
        flags.append("cuda_unavailable")
    if torch.cuda_version is not None and parse_version_prefix(torch.cuda_version) < MIN_TORCH_CUDA:
        flags.append("torch_cuda_below_12.8")
    if not gpu4pyscf.installed:
        flags.append("gpu4pyscf_missing")
    if gpu4pyscf_failed:
        flags.append("gpu4pyscf_import_failed")
    if gpu4pyscf.installed and (
        gpu4pyscf.version is None or parse_version_prefix(gpu4pyscf.version) < MIN_GPU4PYSCF
    ):
        flags.append("gpu4pyscf_below_1.8.0")
    return flags


def probe_hardware() -> HardwareReport:
    """Report PyTorch/CUDA, the first GPU, GPU4PySCF and the VRAM budget; never raises."""
    notes: list[str] = []
    torch, gpu, torch_failed = _probe_torch(notes)
    gpu4pyscf, gpu4pyscf_failed = _probe_gpu4pyscf(notes)
    return HardwareReport(
        python_version=platform.python_version(),
        platform=platform.platform(),
        torch=torch,
        gpu=gpu,
        gpu4pyscf=gpu4pyscf,
        vram_budget_bytes=None if gpu is None else vram_budget_bytes(gpu.total_vram_bytes),
        flags=_flags(torch, torch_failed, gpu4pyscf, gpu4pyscf_failed),
        notes=notes,
    )


class ScfCheck(_Model):
    """GPU4PySCF vs PySCF RHF/STO-3G on H2O."""

    converged_gpu: bool
    converged_cpu: bool
    energy_gpu_eh: float
    energy_cpu_eh: float
    abs_diff_eh: float
    tolerance_eh: float = SCF_TOLERANCE_EH
    mo_on_device: bool
    seconds: float


class TorchOpCheck(_Model):
    """Seeded float64 512x512 matmul on CUDA vs CPU."""

    device: str
    max_abs_diff: float
    tolerance: float = MATMUL_TOLERANCE
    seconds: float


class SmokeResult(_Model):
    """Outcome of :func:`run_smoke`."""

    result_schema: Literal[1] = 1
    status: Literal["pass", "fail", "skipped"]
    reason: str | None
    scf: ScfCheck | None
    torch_op: TorchOpCheck | None
    total_seconds: float
    timeout_s: float
    host: HardwareReport


class _ChildOutput(_Model):
    """Raw measurements printed by ``eta_rxncat.utils._smoke_child``."""

    converged_gpu: bool
    converged_cpu: bool
    energy_gpu_eh: float
    energy_cpu_eh: float
    mo_on_device: bool
    scf_seconds: float
    device: str
    max_abs_diff: float
    torch_seconds: float


def _child_argv() -> list[str]:
    """Return the command that runs the smoke work in a child interpreter."""
    return [sys.executable, "-m", "eta_rxncat.utils._smoke_child"]


def _broken_install_reason(host: HardwareReport) -> str | None:
    """Return why an installed torch or GPU4PySCF cannot be imported, or ``None``."""
    reasons = []
    for package, flag in (
        ("torch", "torch_import_failed"),
        ("gpu4pyscf", "gpu4pyscf_import_failed"),
    ):
        if flag in host.flags:
            note = next((n for n in host.notes if n.startswith(f"Importing {package} raised")), "")
            reasons.append(f"broken {package} install ({flag}): {note}".rstrip(": "))
    return "; ".join(reasons) or None


def _skip_reason(host: HardwareReport) -> str | None:
    """Return why the smoke test cannot run on ``host``, or ``None`` if it can."""
    missing = []
    if not host.torch.installed:
        missing.append("torch is not installed")
    elif not host.torch.cuda_available:
        missing.append("CUDA is not available to torch")
    if not host.gpu4pyscf.installed:
        missing.append("gpu4pyscf is not installed")
    return "; ".join(missing) or None


def _within(value: float, tolerance: float) -> bool:
    """Return whether ``value`` is finite and at most ``tolerance`` (NaN never passes)."""
    return math.isfinite(value) and value <= tolerance


def _judge(out: _ChildOutput) -> tuple[ScfCheck, TorchOpCheck, list[str]]:
    """Build the check records and the list of failed checks."""
    abs_diff = abs(out.energy_gpu_eh - out.energy_cpu_eh)
    scf = ScfCheck(
        converged_gpu=out.converged_gpu,
        converged_cpu=out.converged_cpu,
        energy_gpu_eh=out.energy_gpu_eh,
        energy_cpu_eh=out.energy_cpu_eh,
        abs_diff_eh=abs_diff,
        mo_on_device=out.mo_on_device,
        seconds=out.scf_seconds,
    )
    op = TorchOpCheck(device=out.device, max_abs_diff=out.max_abs_diff, seconds=out.torch_seconds)
    failed = []
    if not out.converged_gpu:
        failed.append("convergence check: GPU SCF did not converge")
    if not out.converged_cpu:
        failed.append("convergence check: CPU SCF did not converge")
    if not _within(abs_diff, SCF_TOLERANCE_EH):
        failed.append(
            f"energy check: |E_gpu - E_cpu| = {abs_diff:.3e} Eh > {SCF_TOLERANCE_EH:g} Eh"
        )
    if not out.mo_on_device:
        failed.append("mo_coeff check: GPU MO coefficients are not a cupy.ndarray")
    if out.device != "cuda":
        failed.append(f"device check: matmul result is on '{out.device}', not 'cuda'")
    if not _within(out.max_abs_diff, MATMUL_TOLERANCE):
        failed.append(
            f"matmul check: max |C_gpu - C_cpu| = {out.max_abs_diff:.3e} > {MATMUL_TOLERANCE:g}"
        )
    return scf, op, failed


def run_smoke(timeout_s: float = 600.0) -> SmokeResult:
    """Run the GPU4PySCF-vs-PySCF and CUDA matmul smoke test.

    Returns ``fail`` (no child process) when an installed torch or GPU4PySCF fails to import,
    and ``skipped`` (no child process) when torch, CUDA or GPU4PySCF is not available;
    otherwise runs the work in a child process killed after ``timeout_s`` and returns ``pass``
    only if every check passes, else ``fail`` with a reason naming the failed checks.
    """
    start = time.monotonic()
    host = probe_hardware()

    def result(
        status: Literal["pass", "fail", "skipped"],
        reason: str | None,
        scf: ScfCheck | None = None,
        op: TorchOpCheck | None = None,
    ) -> SmokeResult:
        return SmokeResult(
            status=status,
            reason=reason,
            scf=scf,
            torch_op=op,
            total_seconds=round(time.monotonic() - start, 3),
            timeout_s=timeout_s,
            host=host,
        )

    broken = _broken_install_reason(host)
    if broken is not None:  # installed but unusable: a failure to surface, never a skip
        return result("fail", broken)
    skip = _skip_reason(host)
    if skip is not None:
        return result("skipped", skip)
    try:
        proc = subprocess.run(_child_argv(), timeout=timeout_s, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return result("fail", f"timeout: smoke child did not finish within {timeout_s:g} s")
    except OSError as exc:
        return result("fail", f"smoke child could not start: {exc}")
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-1:] or ["no stderr"]
        return result("fail", f"smoke child exited {proc.returncode}: {tail[0]}")
    try:
        out = _ChildOutput.model_validate(json.loads(proc.stdout))
    except (json.JSONDecodeError, ValidationError) as exc:
        return result("fail", f"smoke child printed malformed output: {exc}")
    scf, op, failed = _judge(out)
    if failed:
        return result("fail", "; ".join(failed), scf, op)
    return result("pass", None, scf, op)


def smoke_exit_code(result: SmokeResult) -> int:
    """Return the process exit code for a smoke result: pass 0, fail 1, skipped 3."""
    return {"pass": 0, "fail": 1, "skipped": 3}[result.status]
