"""OMol25 eSEN engine (tag ``esen_omol25``): ``esen-sm-conserving-all-omol`` on the shared bridge.

TJ 16:52Z "A - Ship it as a second model", with an honest tag (R31, ADR-0022 PROPOSED). Only the
conserving checkpoint is accepted: the direct-force OMol25 checkpoints are refused (their forces
are not -dE/dx), and ``allscaip-md-conserving-all-omol`` is not approved. Explicit charge and spin,
no ``ase`` in eta_rxncat, sha256-pinned identity, FD Hessian.
"""

from typing import ClassVar

from eta_rxncat.engines._fairchem_bridge import FairchemEngine
from eta_rxncat.engines.errors import EngineInputError

DIRECT_FORCE_METHODS: frozenset[str] = frozenset(
    {"esen-sm-direct-all-omol", "esen-md-direct-all-omol", "allscaip-md-direct-all-omol"}
)
"""OMol25 registry names whose models regress forces directly (refused by name)."""

NOT_APPROVED: frozenset[str] = frozenset({"allscaip-md-conserving-all-omol"})
"""Conserving OMol25 checkpoints TJ did not approve."""


class ESENOMol25Engine(FairchemEngine):
    """OMol25 eSEN-sm-conserving single points; ``stage.method`` must be the approved name."""

    tag = "esen_omol25"
    METHOD: ClassVar[str] = "esen-sm-conserving-all-omol"
    REGISTRY_NAME: ClassVar[str] = "esen-sm-conserving-all-omol"

    @classmethod
    def check_method(cls, method: str) -> None:
        """Refuse direct-force and unapproved OMol25 names explicitly, then anything else."""
        if method in DIRECT_FORCE_METHODS:
            raise EngineInputError(f"{method}: direct-force checkpoint; forces are not -dE/dx")
        if method in NOT_APPROVED:
            raise EngineInputError(
                f"esen_omol25: {method} not approved (TJ 16:52Z approved "
                "esen-sm-conserving-all-omol only)"
            )
        super().check_method(method)
