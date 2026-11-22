"""PySCF engine (tag ``pyscf_gpu_cpu``): CPU path (v0.2.0 slice 06); GPU dispatch in slice 07."""

from eta_rxncat.engines.pyscf_gpu_cpu.engine import (
    HESSIAN_SUPPORT,
    PySCFEngine,
    hessian_method_for,
)
from eta_rxncat.engines.pyscf_gpu_cpu.solvents import DIELECTRICS

__all__ = ["DIELECTRICS", "HESSIAN_SUPPORT", "PySCFEngine", "hessian_method_for"]
