"""An engine wrapper that counts evaluations per runner stage kind (R7)."""

from collections import Counter
from typing import Any

from eta_rxncat.core import EngineIdentity, MolecularState, PotentialResult, StageConfig
from eta_rxncat.engines import Engine, RawResult


class CountingEngine(Engine):
    """Delegate ``stage``, ``identity`` and ``evaluate`` to ``engine``, counting each call.

    The runner sets ``kind`` before each stage; every ``evaluate`` (including the optimizer's,
    through its bridge) is counted under the current kind.

    Attributes:
        counts: Evaluations per stage kind.
        kind: The stage kind the next evaluation is counted under.
    """

    def __init__(self, engine: Engine) -> None:
        """Wrap ``engine`` (no stage resolution of its own: the wrapped engine's is used)."""
        self._engine = engine
        self.counts: Counter[str] = Counter()
        self.kind = "unassigned"

    @property
    def wrapped(self) -> Engine:
        """The engine being counted."""
        return self._engine

    @property
    def stage(self) -> StageConfig:
        """The wrapped engine's resolved stage."""
        return self._engine.stage

    @property
    def identity(self) -> EngineIdentity:
        """The wrapped engine's identity."""
        return self._engine.identity

    @property
    def total(self) -> int:
        """All evaluations so far."""
        return sum(self.counts.values())

    def evaluate(
        self, state: MolecularState, *, forces: bool = True, hessian: bool = False
    ) -> PotentialResult:
        """Count one call under ``kind`` and delegate to the wrapped engine."""
        self.counts[self.kind] += 1
        return self._engine.evaluate(state, forces=forces, hessian=hessian)

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        raise NotImplementedError("CountingEngine delegates evaluate; _evaluate is never used")

    def __getattr__(self, name: str) -> Any:
        """Forward anything else (``tag``, ``OPTIONS``, ...) to the wrapped engine."""
        return getattr(self._engine, name)
