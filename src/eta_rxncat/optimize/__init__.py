"""Geometry optimizers behind one interface (v0.3.0) and the P-RFO TS search (v0.5.0).

Importing this package loads no optimizer library. ``GeometricOptimizer`` imports geomeTRIC (the
``opt-geometric`` extra) inside its own methods. ``PRFOOptimizer`` is eta's own numpy code (base
install); ``TransitionStateOptimizer`` is pure Python.
"""

from eta_rxncat.optimize.base import (
    DihedralConstraint,
    Optimizer,
    capture_frames,
    check_constraints,
    constraints_text,
)
from eta_rxncat.optimize.errors import (
    OptimizationFailedError,
    OptimizerError,
    OptimizerInputError,
    OptimizerUnavailableError,
    TSSearchFailedError,
)
from eta_rxncat.optimize.geometric_impl import GeometricOptimizer
from eta_rxncat.optimize.prfo import PRFOOptimizer
from eta_rxncat.optimize.ts_base import TransitionStateOptimizer

__all__ = [
    "DihedralConstraint",
    "GeometricOptimizer",
    "OptimizationFailedError",
    "Optimizer",
    "OptimizerError",
    "OptimizerInputError",
    "OptimizerUnavailableError",
    "PRFOOptimizer",
    "TSSearchFailedError",
    "TransitionStateOptimizer",
    "capture_frames",
    "check_constraints",
    "constraints_text",
]
