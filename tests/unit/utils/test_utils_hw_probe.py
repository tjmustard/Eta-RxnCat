"""Tests for probe_hardware with fake torch / gpu4pyscf modules (no GPU needed)."""

import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from eta_rxncat.utils import hw_probe
from eta_rxncat.utils.hw_probe import (
    MIN_GPU4PYSCF,
    MIN_TORCH_CUDA,
    VRAM_BUDGET_GIB,
    parse_version_prefix,
    probe_hardware,
    vram_budget_bytes,
)

MIB = 2**20
GIB = 2**30
RTX_5060_TI_BYTES = 8151 * MIB  # 8,546,942,976
BUDGET_BYTES = 6979321856  # int(6.5 * 2**30)


def fake_torch(
    version: str = "2.8.0+cu128",
    cuda: str | None = "12.8",
    available: bool = True,
    total_bytes: int = RTX_5060_TI_BYTES,
    capability: tuple[int, int] = (12, 0),
) -> ModuleType:
    """Return a stand-in ``torch`` module exposing what the probe reads."""
    module = ModuleType("torch")
    module.__version__ = version  # type: ignore[attr-defined]
    module.version = SimpleNamespace(cuda=cuda)  # type: ignore[attr-defined]
    props = SimpleNamespace(
        name="NVIDIA GeForce RTX 5060 Ti",
        major=capability[0],
        minor=capability[1],
        total_memory=total_bytes,
    )
    module.cuda = SimpleNamespace(  # type: ignore[attr-defined]
        is_available=lambda: available,
        get_device_properties=lambda index: props,
        mem_get_info=lambda index: (total_bytes // 2, total_bytes),
    )
    return module


def fake_gpu4pyscf(version: str = "1.8.0") -> ModuleType:
    """Return a stand-in ``gpu4pyscf`` module."""
    module = ModuleType("gpu4pyscf")
    module.__version__ = version  # type: ignore[attr-defined]
    return module


def install(
    monkeypatch: pytest.MonkeyPatch,
    torch: ModuleType | None,
    gpu4pyscf: ModuleType | None,
) -> None:
    """Make ``import torch`` / ``import gpu4pyscf`` return the fakes (``None`` = not installed)."""
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "gpu4pyscf", gpu4pyscf)


def test_constants_and_budget() -> None:
    """The public constants and the budget rule min(6.5 GiB, total)."""
    assert VRAM_BUDGET_GIB == 6.5 and MIN_TORCH_CUDA == (12, 8) and MIN_GPU4PYSCF == (1, 8, 0)
    assert vram_budget_bytes(RTX_5060_TI_BYTES) == BUDGET_BYTES
    assert vram_budget_bytes(2 * GIB) == 2 * GIB


@pytest.mark.parametrize(
    ("text", "expected"),
    [("2.13.0+cu128", (2, 13, 0)), ("12.8", (12, 8)), ("1.8.0rc1", (1, 8, 0)), ("dev", ())],
)
def test_parse_version_prefix(text: str, expected: tuple[int, ...]) -> None:
    """Versions compare by their numeric dotted prefix."""
    assert parse_version_prefix(text) == expected


def test_rtx_5060_ti(monkeypatch: pytest.MonkeyPatch) -> None:
    """An 8151 MiB, CC 12.0 GPU with CUDA 12.8 torch and gpu4pyscf 1.8.0 has no flags."""
    install(monkeypatch, fake_torch(), fake_gpu4pyscf())
    report = probe_hardware()
    assert report.gpu is not None
    assert report.gpu.compute_capability == "12.0"
    assert report.gpu.total_vram_bytes == 8_546_942_976
    assert report.gpu.total_vram_gib == 7.96
    assert report.gpu.free_vram_bytes == RTX_5060_TI_BYTES // 2
    assert report.vram_budget_bytes == BUDGET_BYTES
    assert report.vram_budget_gib == 6.5
    assert report.flags == []
    assert report.torch.cuda_version == "12.8" and report.gpu4pyscf.version == "1.8.0"


def test_budget_ignores_free_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    """The budget comes from total VRAM; free VRAM is only reported."""
    install(monkeypatch, fake_torch(), fake_gpu4pyscf())
    report = probe_hardware()
    assert report.gpu is not None and report.gpu.free_vram_bytes is not None
    assert report.gpu.free_vram_bytes < BUDGET_BYTES
    assert report.vram_budget_bytes == BUDGET_BYTES


@pytest.mark.parametrize(("total", "budget"), [(24 * GIB, BUDGET_BYTES), (4 * GIB, 4 * GIB)])
def test_budget_is_capped_by_total(
    monkeypatch: pytest.MonkeyPatch, total: int, budget: int
) -> None:
    """A 24 GiB GPU is capped at 6.5 GiB; a 4 GiB GPU gets all of it."""
    install(monkeypatch, fake_torch(total_bytes=total), fake_gpu4pyscf())
    assert probe_hardware().vram_budget_bytes == budget


def test_no_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without torch the probe reports missing torch and CUDA and does not raise."""
    install(monkeypatch, None, fake_gpu4pyscf())
    report = probe_hardware()
    assert {"torch_missing", "cuda_unavailable"} <= set(report.flags)
    assert report.gpu is None and report.vram_budget_bytes is None
    assert report.torch.installed is False


def test_torch_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """CPU-only torch flags cuda_unavailable and reports no GPU."""
    install(
        monkeypatch, fake_torch(version="2.8.0+cpu", cuda=None, available=False), fake_gpu4pyscf()
    )
    report = probe_hardware()
    assert report.flags == ["cuda_unavailable"]
    assert report.gpu is None and report.torch.installed is True


def test_old_cuda_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """A torch 2.6.0+cu124 build is flagged below CUDA 12.8."""
    install(monkeypatch, fake_torch(version="2.6.0+cu124", cuda="12.4"), fake_gpu4pyscf())
    assert "torch_cuda_below_12.8" in probe_hardware().flags


def test_cuda_version_from_local_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without torch.version.cuda, the +cuNNN tag gives the CUDA version."""
    install(monkeypatch, fake_torch(version="2.6.0+cu124", cuda=None), fake_gpu4pyscf())
    report = probe_hardware()
    assert report.torch.cuda_version == "12.4" and "torch_cuda_below_12.8" in report.flags


def test_old_gpu4pyscf(monkeypatch: pytest.MonkeyPatch) -> None:
    """gpu4pyscf 1.7.0 is flagged below 1.8.0."""
    install(monkeypatch, fake_torch(), fake_gpu4pyscf("1.7.0"))
    assert probe_hardware().flags == ["gpu4pyscf_below_1.8.0"]


def test_gpu4pyscf_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An absent gpu4pyscf is flagged missing."""
    install(monkeypatch, fake_torch(), None)
    report = probe_hardware()
    assert report.flags == ["gpu4pyscf_missing"] and report.gpu4pyscf.installed is False


def test_broken_cuda_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """If torch.cuda raises, the probe records a note instead of raising."""
    torch = fake_torch()

    def broken() -> bool:
        raise RuntimeError("driver mismatch")

    torch.cuda.is_available = broken  # type: ignore[attr-defined]
    install(monkeypatch, torch, fake_gpu4pyscf())
    report = probe_hardware()
    assert "cuda_unavailable" in report.flags
    assert any("driver mismatch" in note for note in report.notes)


def test_broken_device_query_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """If reading device 0 fails, the probe reports no GPU and a note."""
    torch = fake_torch()

    def broken(index: int) -> object:
        raise RuntimeError("no device 0")

    torch.cuda.get_device_properties = broken  # type: ignore[attr-defined]
    install(monkeypatch, torch, fake_gpu4pyscf())
    report = probe_hardware()
    assert report.gpu is None and report.vram_budget_bytes is None
    assert any("no device 0" in note for note in report.notes)


def test_gpu4pyscf_import_error_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """A gpu4pyscf import that fails with a non-ImportError is reported as missing."""
    install(monkeypatch, fake_torch(), fake_gpu4pyscf())

    def failing_import(name: str) -> ModuleType | None:
        if name == "gpu4pyscf":
            raise OSError("libcudart.so.12: cannot open shared object file")
        return fake_torch()

    monkeypatch.setattr(hw_probe, "_import", failing_import)
    report = probe_hardware()
    assert "gpu4pyscf_missing" in report.flags
    assert any("libcudart" in note for note in report.notes)


def test_this_environment_report() -> None:
    """On this environment (no torch, no gpu4pyscf) the real probe reports both missing."""
    report = probe_hardware()
    assert {"torch_missing", "cuda_unavailable", "gpu4pyscf_missing"} <= set(report.flags)
    assert report.report_schema == 1 and report.vram_budget_bytes is None


def test_report_json_fields() -> None:
    """The report serialises with exactly the contract's top-level fields."""
    assert set(probe_hardware().model_dump()) == {
        "report_schema",
        "python_version",
        "platform",
        "torch",
        "gpu",
        "gpu4pyscf",
        "vram_budget_gib",
        "vram_budget_bytes",
        "flags",
        "notes",
    }


def test_import_loads_no_torch() -> None:
    """Importing the probe module does not import torch."""
    code = "import eta_rxncat.utils.hw_probe, sys; assert 'torch' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
