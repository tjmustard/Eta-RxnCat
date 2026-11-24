"""Geometry-optimization contracts: the optimizer identity and a converged result (v0.3.0).

Data only: pydantic and the standard library, no numpy and no optimizer imports.
"""

from typing import Literal

from pydantic import Field, FiniteFloat, field_validator

from eta_rxncat.core.models import CoreModel, MolecularState, NonNegativeInt, ScalarValue


class OptimizerIdentity(CoreModel):
    """The optimizer that produced a result.

    ``geometric`` is the geomeTRIC minimum optimizer (v0.3.0); ``prfo`` is eta's own clean-room
    P-RFO transition-state optimizer (v0.5.0, additive). Any other name is rejected.

    Attributes:
        name: Optimizer name.
        version: Optimizer library version (for ``prfo``, eta's source identity).
    """

    name: Literal["geometric", "prfo"]
    version: str = Field(min_length=1)


class OptimizationResult(CoreModel):
    """A converged geometry optimization; a failed one raises instead of returning.

    Attributes:
        final_state: The optimized structure.
        final_energy_hartree: Energy of ``final_state`` (Eh).
        converged: Always ``True``.
        n_steps: Optimizer steps taken.
        n_engine_calls: Engine evaluations made.
        recovery_steps: Recovery-ladder steps taken, in order (empty if none).
        optimizer: The optimizer name and version.
        options: The resolved optimizer options (a constrained run records its constraints here
            under ``constraints``).
    """

    final_state: MolecularState
    final_energy_hartree: FiniteFloat
    converged: Literal[True]
    n_steps: NonNegativeInt
    n_engine_calls: NonNegativeInt
    recovery_steps: list[str]
    optimizer: OptimizerIdentity
    options: dict[str, ScalarValue]

    @field_validator("converged", mode="before")
    @classmethod
    def _strict_converged(cls, value: object) -> object:
        # Literal[True] alone accepts 1 and 1.0 (they compare equal to True).
        if value is not True:
            raise ValueError(f"converged must be True, not {value!r}")
        return value
