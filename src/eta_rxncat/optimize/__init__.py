"""Geometry optimizers behind one interface (v0.3.0).

Pure Python: importing this package loads no optimizer library. ``GeometricOptimizer`` imports
geomeTRIC (the ``opt-geometric`` extra) inside its own methods.
"""

from eta_rxncat.optimize.base import (
    DihedralConstraint,
    Optimizer,
    check_constraints,
    constraints_text,
)
from eta_rxncat.optimize.errors import (
    OptimizationFailedError,
    OptimizerError,
    OptimizerInputError,
    OptimizerUnavailableError,
)
from eta_rxncat.optimize.geometric_impl import GeometricOptimizer

__all__ = [
    "DihedralConstraint",
    "GeometricOptimizer",
    "OptimizationFailedError",
    "Optimizer",
    "OptimizerError",
    "OptimizerInputError",
    "OptimizerUnavailableError",
    "check_constraints",
    "constraints_text",
]
