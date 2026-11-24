"""Hardware capability probe for NVIDIA RTX 5060 (sm_120), PyTorch CUDA, and GPU4PySCF."""

from __future__ import annotations

import importlib.util
from pydantic import BaseModel


class HardwareReport(BaseModel):
    """Diagnostic summary of local GPU and quantum-chemistry acceleration availability."""

    torch_installed: bool
    cuda_available: bool
    device_name: str | None = None
    compute_capability: str | None = None
    total_vram_gb: float | None = None
    recommended_vram_budget_gb: float | None = None
    gpu4pyscf_installed: bool = False
    mace_installed: bool = False
    fairchem_installed: bool = False
    notes: list[str] = []


def _is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def probe_hardware(vram_safety_fraction: float = 0.80) -> HardwareReport:
    """Inspect PyTorch CUDA, GPU compute capability, VRAM headroom, and MLIP/DFT packages."""
    notes: list[str] = []
    torch_installed = _is_module_available("torch")
    gpu4pyscf_installed = _is_module_available("gpu4pyscf")
    mace_installed = _is_module_available("mace")
    fairchem_installed = _is_module_available("fairchem")

    if not torch_installed:
        notes.append("PyTorch not installed; running in CPU-only mode.")
        return HardwareReport(
            torch_installed=False,
            cuda_available=False,
            gpu4pyscf_installed=gpu4pyscf_installed,
            mace_installed=mace_installed,
            fairchem_installed=fairchem_installed,
            notes=notes,
        )

    import torch

    if not torch.cuda.is_available():
        notes.append("PyTorch installed without active CUDA device; GPU4PySCF disabled.")
        return HardwareReport(
            torch_installed=True,
            cuda_available=False,
            gpu4pyscf_installed=gpu4pyscf_installed,
            mace_installed=mace_installed,
            fairchem_installed=fairchem_installed,
            notes=notes,
        )

    props = torch.cuda.get_device_properties(0)
    total_vram_gb = round(props.total_memory / (1024**3), 2)
    budget_gb = round(total_vram_gb * vram_safety_fraction, 2)
    cc = f"{props.major}.{props.minor}"

    if props.major >= 12:
        notes.append(
            f"Blackwell architecture (sm_{props.major}{props.minor}) detected. "
            "Ensure PyTorch >=2.7+cu128 and GPU4PySCF >=1.8.0 (CUDA 12 JIT or CUDA 13)."
        )
    if total_vram_gb <= 8.5:
        notes.append(
            f"8 GB VRAM class GPU detected; capping GPU4PySCF active budget at {budget_gb} GB "
            "with automatic CPU DF-KS fallback for larger basis sets."
        )

    return HardwareReport(
        torch_installed=True,
        cuda_available=True,
        device_name=props.name,
        compute_capability=cc,
        total_vram_gb=total_vram_gb,
        recommended_vram_budget_gb=budget_gb,
        gpu4pyscf_installed=gpu4pyscf_installed,
        mace_installed=mace_installed,
        fairchem_installed=fairchem_installed,
        notes=notes,
    )


if __name__ == "__main__":
    import json

    print(json.dumps(probe_hardware().model_dump(), indent=2))
