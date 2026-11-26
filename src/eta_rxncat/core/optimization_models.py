"""Geometry-optimization contracts: the optimizer identity and a converged result (v0.3.0).

Data only: pydantic and the standard library, no numpy and no optimizer imports.
"""

from typing import Any, Literal

from pydantic import (
    Field,
    FiniteFloat,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
)

from eta_rxncat.core.models import CoreModel, MolecularState, NonNegativeInt, ScalarValue
from eta_rxncat.core.results import NonNegativeFiniteFloat


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


class OptimizationFrame(CoreModel):
    """One geometry the optimizer evaluated (v0.7.0).

    Attributes:
        coordinates_angstrom: The geometry.
        energy_hartree: Energy there (Eh).
        max_gradient_hartree_per_bohr: Largest gradient component there (Eh/Bohr).
        ladder_step: The recovery-ladder step that produced it; ``None`` outside the ladder.
        accepted_bool: Whether the ladder step's trajectory file holds this geometry (so the
            optimizer took it); ``None`` when not judged, and then left out of the serialised form.
    """

    coordinates_angstrom: list[list[FiniteFloat]]
    energy_hartree: FiniteFloat
    max_gradient_hartree_per_bohr: NonNegativeFiniteFloat
    ladder_step: str | None
    accepted_bool: bool | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_acceptance(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # An unjudged frame must serialise exactly as before the field existed.
        data: dict[str, Any] = handler(self)
        if self.accepted_bool is None:
            data.pop("accepted_bool", None)
        return data


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
        frames: The evaluated geometries in order (v0.7.0); ``None`` when not captured, and then
            left out of the serialised form.
    """

    final_state: MolecularState
    final_energy_hartree: FiniteFloat
    converged: Literal[True]
    n_steps: NonNegativeInt
    n_engine_calls: NonNegativeInt
    recovery_steps: list[str]
    optimizer: OptimizerIdentity
    options: dict[str, ScalarValue]
    frames: list[OptimizationFrame] | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_frames(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # A result without frames must serialise exactly as in v0.6.0.
        data: dict[str, Any] = handler(self)
        if self.frames is None:
            data.pop("frames", None)
        return data

    @field_validator("converged", mode="before")
    @classmethod
    def _strict_converged(cls, value: object) -> object:
        # Literal[True] alone accepts 1 and 1.0 (they compare equal to True).
        if value is not True:
            raise ValueError(f"converged must be True, not {value!r}")
        return value
