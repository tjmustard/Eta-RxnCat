"""The ``Engine`` base class every engine implements (mission §5 Contracts, Engine API).

An engine is built from a stage with ``Engine.from_stage(stage, **runtime)``. Its ``stage`` is
the resolved stage (every keyed option filled, plus ``engine_impl``), which is what the cache key
hashes. Runtime arguments are constructor keywords and never reach the key. ``evaluate`` times
the subclass's ``_evaluate``, checks the shapes against the state, and returns a validated
``PotentialResult``.
"""

import abc
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

from pydantic import ValidationError

from eta_rxncat.core import (
    Device,
    EngineIdentity,
    EngineTag,
    HessianMethod,
    MolecularState,
    PotentialResult,
    StageConfig,
)
from eta_rxncat.engines.errors import EngineInputError, EngineRuntimeError
from eta_rxncat.engines.options import OptionSpec, normalise_solvent, resolved_stage


@dataclass
class RawResult:
    """What a subclass's ``_evaluate`` returns; ``Engine.evaluate`` validates and wraps it.

    Units as ``PotentialResult``: Eh, Eh/Bohr (forces, ``-dE/dx``), Eh/Bohr^2 (Hessian).
    """

    energy_hartree: float
    device: Device
    forces_hartree_per_bohr: Sequence[Sequence[float]] | None = None
    hessian_hartree_per_bohr2: Sequence[Sequence[float]] | None = None
    hessian_method: HessianMethod | None = None
    hessian_max_asymmetry: float | None = None
    device_reason: str | None = None
    recovery_steps: Sequence[str] = field(default_factory=tuple)


def _copy_matrix(rows: Sequence[Sequence[float]] | None) -> list[list[float]] | None:
    """Return a fresh list-of-lists copy of ``rows`` (never aliasing the engine's data)."""
    return None if rows is None else [[float(value) for value in row] for row in rows]


class Engine(abc.ABC):
    """Base of every engine: a tag, an implementation version and a keyed-option table.

    Subclasses set ``tag``, ``ENGINE_IMPL`` and ``OPTIONS``, implement ``identity`` and
    ``_evaluate``, and take their runtime arguments as keyword-only ``__init__`` parameters,
    passing the stage on to ``super().__init__``.
    """

    tag: ClassVar[EngineTag]
    ENGINE_IMPL: ClassVar[int]
    OPTIONS: ClassVar[Mapping[str, OptionSpec]]

    def __init__(self, stage: StageConfig, **runtime: Any) -> None:
        """Resolve ``stage`` for this engine; reject a foreign tag or unknown runtime arguments.

        Raises:
            EngineInputError: ``stage.engine`` is not this engine's tag, an option is unknown,
                mistyped or not allowed, or a runtime argument is unknown.
        """
        if stage.engine != self.tag:
            raise EngineInputError(
                f"{type(self).__name__} runs engine {self.tag!r}, not {stage.engine!r}"
            )
        if runtime:
            raise EngineInputError(
                f"engine {self.tag!r}: unknown runtime argument(s) {sorted(runtime)}"
            )
        self._stage = resolved_stage(stage, self.OPTIONS, self.ENGINE_IMPL, self.normalise_stage)

    @classmethod
    def from_stage(cls, stage: StageConfig, **runtime: Any) -> Self:
        """Build the engine for ``stage``; runtime arguments go to the constructor only."""
        return cls(stage, **runtime)

    @classmethod
    def normalise_stage(cls, stage: StageConfig) -> StageConfig:
        """Canonicalise non-option stage fields before keying (default: lowercase the solvent)."""
        return normalise_solvent(stage)

    @property
    def stage(self) -> StageConfig:
        """The resolved stage: every keyed option filled, plus ``engine_impl``."""
        return self._stage

    @property
    @abc.abstractmethod
    def identity(self) -> EngineIdentity:
        """The engine tag, library version and content-pinned model id."""

    @abc.abstractmethod
    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        """Evaluate ``state``; raise only ``EngineError`` subclasses."""

    def evaluate(
        self, state: MolecularState, *, forces: bool = True, hessian: bool = False
    ) -> PotentialResult:
        """Evaluate ``state`` and return a validated ``PotentialResult``.

        Raises:
            EngineRuntimeError: the engine returned a requested quantity missing, shapes that do
                not match the state's atom count, or values ``PotentialResult`` rejects.
        """
        start = time.perf_counter()
        raw = self._evaluate(state, forces=forces, hessian=hessian)
        wall = time.perf_counter() - start
        n_atoms = len(state.symbols)
        if forces and raw.forces_hartree_per_bohr is None:
            raise EngineRuntimeError(f"engine {self.tag!r} returned no forces")
        if hessian and raw.hessian_hartree_per_bohr2 is None:
            raise EngineRuntimeError(f"engine {self.tag!r} returned no Hessian")
        if raw.forces_hartree_per_bohr is not None and (
            len(raw.forces_hartree_per_bohr) != n_atoms
        ):
            raise EngineRuntimeError(
                f"engine {self.tag!r} returned {len(raw.forces_hartree_per_bohr)} force rows "
                f"for {n_atoms} atoms"
            )
        if raw.hessian_hartree_per_bohr2 is not None and (
            len(raw.hessian_hartree_per_bohr2) != 3 * n_atoms
        ):
            raise EngineRuntimeError(
                f"engine {self.tag!r} returned a Hessian of side "
                f"{len(raw.hessian_hartree_per_bohr2)} for {n_atoms} atoms"
            )
        try:
            return PotentialResult(
                energy_hartree=raw.energy_hartree,
                forces_hartree_per_bohr=_copy_matrix(raw.forces_hartree_per_bohr),
                hessian_hartree_per_bohr2=_copy_matrix(raw.hessian_hartree_per_bohr2),
                hessian_method=raw.hessian_method,
                hessian_max_asymmetry=raw.hessian_max_asymmetry,
                engine=self.identity,
                stage_engine_impl=self.ENGINE_IMPL,
                device=raw.device,
                device_reason=raw.device_reason,
                wall_time_s=wall,
                recovery_steps=list(raw.recovery_steps),
            )
        except ValidationError as exc:
            raise EngineRuntimeError(
                f"engine {self.tag!r} returned an invalid result", tail=str(exc)
            ) from exc
