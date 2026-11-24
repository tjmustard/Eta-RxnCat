"""The ``TransitionStateOptimizer`` interface (v0.5.0, mission R12, ADR-0033).

Pure Python: no numpy, no optimizer library. Separate from ``Optimizer``, so a minimiser can never
be passed as a TS search and no existing ``Optimizer`` subclass changes. A TS search takes no
frozen atoms, dihedrals or ``constraints`` option (R21).
"""

import abc
from collections.abc import Mapping, Sequence
from typing import ClassVar

from eta_rxncat.core import MolecularState, OptimizerIdentity, TSSearchResult
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import Engine, OptionSpec
from eta_rxncat.optimize.base import _coerce
from eta_rxncat.optimize.errors import OptimizerInputError


class TransitionStateOptimizer(abc.ABC):
    """Base of every transition-state search: an identity, keyed options and ``find_saddle``."""

    OPTIONS: ClassVar[Mapping[str, OptionSpec]]

    @property
    @abc.abstractmethod
    def identity(self) -> OptimizerIdentity:
        """The optimizer name and version."""

    def resolved_options(self, options: Mapping[str, ScalarValue] | None) -> dict[str, ScalarValue]:
        """Return every option of ``OPTIONS`` (given or default), sorted by key.

        The same rules and messages as ``Optimizer.resolved_options``, and a ``constraints`` key
        is refused by name.

        Raises:
            OptimizerInputError: A ``constraints`` key, an unknown key, a value of the wrong type
                or one outside ``allowed``; the message names the key.
        """
        given = dict(options or {})
        name = type(self).__name__
        if "constraints" in given:
            raise OptimizerInputError(
                f"{name}: option 'constraints' is refused; a TS search takes no constraints"
            )
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
    def find_saddle(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        forming_bonds: Sequence[tuple[int, int]] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> TSSearchResult:
        """Search for a first-order saddle point from ``state`` on ``engine``.

        Args:
            state: The start structure.
            engine: The engine giving energies, gradients and Hessians.
            forming_bonds: Atom pairs whose bond forms or breaks; they choose the initial mode.
            options: Keyed options; see ``OPTIONS``.

        Returns:
            The converged search.

        Raises:
            OptimizerInputError: Bad options, forming bonds or state, before any engine call.
            TSSearchFailedError: The search stopped without converging.
            eta_rxncat.engines.EngineError: Raised by the engine; propagated unchanged.
        """
