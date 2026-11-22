"""Tests for run_smoke and smoke_exit_code with fake hosts and fake child processes."""

import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.utils import hw_probe
from eta_rxncat.utils.hw_probe import (
    Gpu4PySCFInfo,
    GpuInfo,
    HardwareReport,
    TorchInfo,
    run_smoke,
    smoke_exit_code,
)

PASSING = {
    "converged_gpu": True,
    "converged_cpu": True,
    "energy_gpu_eh": -74.962928,
    "energy_cpu_eh": -74.962928,
    "mo_on_device": True,
    "scf_seconds": 3.2,
    "device": "cuda",
    "max_abs_diff": 1e-12,
    "torch_seconds": 0.4,
}


def capable_host() -> HardwareReport:
    """Return a report for a host that can run the smoke test."""
    return HardwareReport(
        python_version="3.12.0",
        platform="test",
        torch=TorchInfo(
            installed=True, version="2.8.0+cu128", cuda_available=True, cuda_version="12.8"
        ),
        gpu=GpuInfo(
            name="fake",
            compute_capability="12.0",
            total_vram_bytes=8151 * 2**20,
            total_vram_gib=7.96,
            free_vram_bytes=None,
        ),
        gpu4pyscf=Gpu4PySCFInfo(installed=True, version="1.8.0"),
        vram_budget_bytes=6979321856,
        flags=[],
        notes=[],
    )


def use_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str) -> None:
    """Pretend the host is capable and make the smoke child run ``script``."""
    path = tmp_path / "child.py"
    path.write_text(script, encoding="utf-8")
    monkeypatch.setattr(hw_probe, "probe_hardware", capable_host)
    monkeypatch.setattr(hw_probe, "_child_argv", lambda: [sys.executable, str(path)])


def printing(payload: dict[str, Any]) -> str:
    """Return a child script that prints ``payload`` as JSON text (NaN written as ``NaN``)."""
    return f"print({json.dumps(json.dumps(payload))})\n"


def forbid_child(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any attempt to start the smoke child fail the test."""

    def no_child(*args: object, **kwargs: object) -> None:
        raise AssertionError("no child process may start here")

    monkeypatch.setattr(subprocess, "run", no_child)


def fake_imports(
    monkeypatch: pytest.MonkeyPatch,
    modules: dict[str, ModuleType | Exception],
    versions: dict[str, str],
) -> None:
    """Fake the probe's import seam: each name maps to a module or to the exception it raises."""

    def fake_import(name: str) -> ModuleType | None:
        found = modules.get(name, ModuleNotFoundError(f"No module named '{name}'"))
        if isinstance(found, Exception):
            raise found
        return found

    def fake_dist_version(distributions: tuple[str, ...]) -> str | None:
        return next((versions[d] for d in distributions if d in versions), None)

    monkeypatch.setattr(hw_probe, "_import", fake_import)
    monkeypatch.setattr(hw_probe, "_dist_version", fake_dist_version)


def test_skipped_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without torch the smoke test is skipped before any child process starts."""
    fake_imports(monkeypatch, {}, {})
    forbid_child(monkeypatch)
    result = run_smoke()
    assert result.status == "skipped"
    assert result.reason is not None and "torch" in result.reason
    assert smoke_exit_code(result) == 3
    assert result.scf is None and result.torch_op is None and result.host.torch.installed is False


LIBCUDART = OSError("libcudart.so.12: cannot open shared object file")


def test_broken_torch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """An installed torch that fails to import makes the smoke test fail (exit 1), not skip."""
    fake_imports(monkeypatch, {"torch": LIBCUDART}, {"torch": "2.8.0+cu128"})
    forbid_child(monkeypatch)
    result = run_smoke()
    assert result.status == "fail" and smoke_exit_code(result) == 1
    assert result.reason is not None
    assert "torch" in result.reason and "OSError" in result.reason and "libcudart" in result.reason
    assert "torch_import_failed" in result.host.flags


def test_broken_gpu4pyscf_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """An installed gpu4pyscf that fails to import makes the smoke test fail, naming it."""
    torch = ModuleType("torch")
    torch.__version__ = "2.8.0+cu128"  # type: ignore[attr-defined]
    torch.version = SimpleNamespace(cuda="12.8")  # type: ignore[attr-defined]
    torch.cuda = SimpleNamespace(is_available=lambda: False)  # type: ignore[attr-defined]
    fake_imports(
        monkeypatch, {"torch": torch, "gpu4pyscf": LIBCUDART}, {"gpu4pyscf-cuda12x": "1.9.2"}
    )
    forbid_child(monkeypatch)
    result = run_smoke()
    assert result.status == "fail" and smoke_exit_code(result) == 1
    assert result.reason is not None and "gpu4pyscf" in result.reason and "OSError" in result.reason


def test_import_error_without_metadata_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    """A torch ImportError with no distribution metadata is still "missing" → skipped."""
    fake_imports(monkeypatch, {"torch": ImportError("No module named 'torch'")}, {})
    forbid_child(monkeypatch)
    result = run_smoke()
    assert result.status == "skipped" and "torch_missing" in result.host.flags


def test_skipped_without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    """Torch without CUDA skips, naming CUDA."""
    host = capable_host()
    host = host.model_copy(
        update={"torch": host.torch.model_copy(update={"cuda_available": False})}
    )
    monkeypatch.setattr(hw_probe, "probe_hardware", lambda: host)
    result = run_smoke()
    assert result.status == "skipped" and result.reason is not None and "CUDA" in result.reason


def test_skipped_without_gpu4pyscf(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing gpu4pyscf skips, naming it."""
    host = capable_host().model_copy(
        update={"gpu4pyscf": Gpu4PySCFInfo(installed=False, version=None)}
    )
    monkeypatch.setattr(hw_probe, "probe_hardware", lambda: host)
    result = run_smoke()
    assert result.status == "skipped" and result.reason == "gpu4pyscf is not installed"


def test_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A child reporting every check within tolerance passes with exit code 0."""
    use_child(monkeypatch, tmp_path, printing(PASSING))
    result = run_smoke()
    assert result.status == "pass" and result.reason is None and smoke_exit_code(result) == 0
    assert result.scf is not None and result.scf.abs_diff_eh == 0.0
    assert result.scf.tolerance_eh == 1e-6
    assert result.torch_op is not None and result.torch_op.tolerance == 1e-9
    assert json.loads(result.model_dump_json())["result_schema"] == 1


@pytest.mark.parametrize(
    ("override", "check"),
    [
        ({"energy_gpu_eh": -74.962928 + 2e-6}, "energy check"),
        ({"energy_gpu_eh": float("nan")}, "energy check"),
        ({"device": "cpu"}, "device check"),
        ({"max_abs_diff": 1e-6}, "matmul check"),
        ({"max_abs_diff": float("nan")}, "matmul check"),
        ({"mo_on_device": False}, "mo_coeff check"),
        ({"converged_gpu": False}, "GPU SCF did not converge"),
        ({"converged_cpu": False}, "CPU SCF did not converge"),
    ],
    ids=["energy", "energy-nan", "device", "matmul", "matmul-nan", "mo", "gpu-scf", "cpu-scf"],
)
def test_each_failing_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, override: dict[str, Any], check: str
) -> None:
    """Each failed check gives fail / exit 1 with a reason naming that check."""
    use_child(monkeypatch, tmp_path, printing(PASSING | override))
    result = run_smoke()
    assert result.status == "fail" and smoke_exit_code(result) == 1
    assert result.reason is not None and check in result.reason


def test_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A child still running at the timeout fails, naming the timeout."""
    use_child(monkeypatch, tmp_path, "import time\ntime.sleep(30)\n")
    result = run_smoke(timeout_s=0.5)
    assert result.status == "fail" and result.reason is not None and "timeout" in result.reason
    assert result.timeout_s == 0.5 and result.total_seconds < 10


def test_non_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A child that prints non-JSON fails."""
    use_child(monkeypatch, tmp_path, "print('hello')\n")
    result = run_smoke()
    assert result.status == "fail" and result.reason is not None and "malformed" in result.reason


def test_incomplete_json_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A child whose JSON lacks a measurement fails."""
    partial = {k: v for k, v in PASSING.items() if k != "device"}
    use_child(monkeypatch, tmp_path, printing(partial))
    result = run_smoke()
    assert result.status == "fail" and result.reason is not None and "malformed" in result.reason


def test_crashing_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A child that exits non-zero fails, quoting its last stderr line."""
    use_child(monkeypatch, tmp_path, "raise RuntimeError('cuda init failed')\n")
    result = run_smoke()
    assert result.status == "fail" and result.reason is not None
    assert "exited 1" in result.reason and "cuda init failed" in result.reason


def test_child_cannot_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """A child command that cannot be executed fails instead of raising."""
    monkeypatch.setattr(hw_probe, "probe_hardware", capable_host)
    monkeypatch.setattr(hw_probe, "_child_argv", lambda: ["/nonexistent/python"])
    result = run_smoke()
    assert (
        result.status == "fail" and result.reason is not None and "could not start" in result.reason
    )
