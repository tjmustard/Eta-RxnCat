"""The ``Optimizer`` interface, keyed options and geometric constraints (v0.3.0, R42).

Pure Python: no numpy, no optimizer library. Concrete optimizers import their library inside
their own methods.
"""

import abc
import math
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator

from eta_rxncat.core import (
    MolecularState,
    OptimizationFrame,
    OptimizationResult,
    OptimizerIdentity,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import Engine, OptionSpec
from eta_rxncat.optimize.errors import OptimizerInputError

_FRAME_SINK: ContextVar[list[OptimizationFrame] | None] = ContextVar(
    "eta_rxncat_frame_sink", default=None
)


@contextmanager
def capture_frames() -> Iterator[list[OptimizationFrame]]:
    """Yield a fresh list that a ``minimize`` run in this context appends its frames to.

    The caller therefore holds every evaluated geometry even when the run (or a check after it)
    raises. The sink is per context, so another thread never writes into it.
    """
    frames: list[OptimizationFrame] = []
    token = _FRAME_SINK.set(frames)
    try:
        yield frames
    finally:
        _FRAME_SINK.reset(token)


def frame_sink() -> list[OptimizationFrame] | None:
    """Return the active ``capture_frames`` list, or ``None`` outside one."""
    return _FRAME_SINK.get()


class DihedralConstraint(BaseModel):
    """Hold the dihedral angle ``atoms[0]-atoms[1]-atoms[2]-atoms[3]`` at ``value_deg``.

    Attributes:
        atoms: Four distinct 0-based atom indices.
        value_deg: Target angle in degrees, finite, in (-180, 180].
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    atoms: tuple[int, int, int, int]
    value_deg: float

    @model_validator(mode="before")
    @classmethod
    def _check(cls, data: Any) -> Any:
        # Checked before field parsing so every bad value raises OptimizerInputError, which is
        # not a ValueError and therefore propagates out of pydantic unchanged.
        if not isinstance(data, Mapping):
            raise OptimizerInputError(f"DihedralConstraint needs a mapping, not {data!r}")
        atoms = data.get("atoms")
        if (
            not isinstance(atoms, Sequence)
            or isinstance(atoms, str)
            or len(atoms) != 4
            or any(isinstance(a, bool) or not isinstance(a, int) for a in atoms)
        ):
            raise OptimizerInputError(f"dihedral atoms must be four ints, not {atoms!r}")
        if any(a < 0 for a in atoms):
            raise OptimizerInputError(f"dihedral atoms {list(atoms)} must be >= 0")
        if len(set(atoms)) != 4:
            raise OptimizerInputError(f"dihedral atoms {list(atoms)} must be distinct")
        value = data.get("value_deg")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise OptimizerInputError(f"dihedral value_deg must be a number, not {value!r}")
        if not math.isfinite(value) or not -180.0 < value <= 180.0:
            raise OptimizerInputError(f"dihedral value_deg {value!r} is not finite in (-180, 180]")
        return {**data, "atoms": tuple(atoms), "value_deg": float(value)}

    def check_atoms(self, n_atoms: int) -> Self:
        """Return ``self`` if every index is below ``n_atoms``; else raise OptimizerInputError."""
        too_big = [a for a in self.atoms if a >= n_atoms]
        if too_big:
            raise OptimizerInputError(
                f"dihedral atoms {list(self.atoms)}: {too_big} out of range for {n_atoms} atoms"
            )
        return self


def check_constraints(
    state: MolecularState,
    frozen_atom_indices: Sequence[int],
    dihedral_constraints: Sequence[DihedralConstraint],
) -> None:
    """Check constraints against ``state``.

    Raises:
        OptimizerInputError: A non-int, negative, out-of-range or duplicate frozen index, or a
            dihedral index out of range.
    """
    n = len(state.symbols)
    bad = [i for i in frozen_atom_indices if isinstance(i, bool) or not isinstance(i, int)]
    if bad:
        raise OptimizerInputError(f"frozen_atom_indices must be ints, not {bad}")
    out = [i for i in frozen_atom_indices if not 0 <= i < n]
    if out:
        raise OptimizerInputError(f"frozen_atom_indices {out} out of range for {n} atoms")
    if len(set(frozen_atom_indices)) != len(frozen_atom_indices):
        raise OptimizerInputError(f"duplicate frozen_atom_indices in {list(frozen_atom_indices)}")
    for constraint in dihedral_constraints:
        if not isinstance(constraint, DihedralConstraint):
            raise OptimizerInputError(f"not a DihedralConstraint: {constraint!r}")
        constraint.check_atoms(n)


def constraints_text(
    frozen_atom_indices: Sequence[int], dihedral_constraints: Sequence[DihedralConstraint]
) -> str:
    """Return the canonical text of a run's constraints; ``""`` when it has none.

    One entry for the frozen atoms, ``freeze:<sorted comma-joined indices>``, and one per dihedral,
    ``dihedral:i,j,k,l:<value_deg %.6f>``; the entries are sorted and joined by ``;``. The runner
    keys it as ``opt.constraints``; a constrained result carries it as ``options["constraints"]``.
    """
    entries: list[str] = []
    if frozen_atom_indices:
        entries.append("freeze:" + ",".join(str(i) for i in sorted(frozen_atom_indices)))
    for c in dihedral_constraints:
        entries.append("dihedral:" + ",".join(str(a) for a in c.atoms) + f":{c.value_deg:.6f}")
    return ";".join(sorted(entries))


def _coerce(spec: OptionSpec, value: ScalarValue) -> ScalarValue | None:
    """Return ``value`` as the spec's type, or ``None`` (the ADR-0016 rule of engine options).

    ``bool`` is accepted only for ``bool`` specs, and an ``int`` given for a ``float`` spec
    becomes a ``float``, so ``1`` and ``1.0`` key the same.
    """
    if spec.type is bool:
        return value if isinstance(value, bool) else None
    if isinstance(value, bool):
        return None
    if spec.type is float and isinstance(value, int | float):
        return float(value)
    if spec.type is int and isinstance(value, int):
        return value
    if spec.type is str and isinstance(value, str):
        return value
    return None


class Optimizer(abc.ABC):
    """Base of every geometry optimizer: an identity, a keyed-option table and ``minimize``."""

    OPTIONS: ClassVar[Mapping[str, OptionSpec]]

    @property
    @abc.abstractmethod
    def identity(self) -> OptimizerIdentity:
        """The optimizer name and library version."""

    def resolved_options(self, options: Mapping[str, ScalarValue] | None) -> dict[str, ScalarValue]:
        """Return every option of ``OPTIONS`` (given or default), sorted by key.

        Raises:
            OptimizerInputError: An unknown key, a value of the wrong type or one outside
                ``allowed``; the message names the key.
        """
        given = dict(options or {})
        name = type(self).__name__
        unknown = sorted(set(given) - set(self.OPTIONS))
        if unknown:
            raise OptimizerInputError(
                f"{name}: unknown option(s) {unknown}; known: {sorted(self.OPTIONS)}"
            )
        resolved: dict[str, ScalarValue] = {}
        for key in sorted(self.OPTIONS):
            spec = self.OPTIONS[key]
            raw = given.get(key, spec.default)
            value = _coerce(spec, raw)
            if value is None:
                raise OptimizerInputError(
                    f"{name}: option {key!r} must be {spec.type.__name__}, "
                    f"not {type(raw).__name__} {raw!r}"
                )
            if spec.allowed is not None and value not in spec.allowed:
                raise OptimizerInputError(
                    f"{name}: option {key!r} value {value!r} not in {sorted(spec.allowed)}"
                )
            resolved[key] = value
        return resolved

    @abc.abstractmethod
    def minimize(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        frozen_atom_indices: Sequence[int] = (),
        dihedral_constraints: Sequence[DihedralConstraint] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> OptimizationResult:
        """Minimise ``state`` on ``engine`` and return the converged result.

        Raises:
            OptimizerInputError: Bad options, constraints or state, before any engine call.
            OptimizationFailedError: Every recovery step failed, or a constraint is broken.
            eta_rxncat.engines.EngineError: Raised by the engine; propagated unchanged.
        """
