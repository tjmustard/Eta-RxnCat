"""UMA engine (tag ``uma_direct``): fairchem ``uma-s-1p2p1``, ``omol`` task, on the shared bridge.

Explicit charge and spin multiplicity, no ``ase`` in eta_rxncat, sha256-pinned identity, FD
Hessian. Weights from the fairchem HF cache (TJ Q3 A) or ``checkpoint_path`` (Q3 B). The UMA
checkpoint is gated under the FAIR Chemistry License (``docs/licence-inventory.md``).
"""

from eta_rxncat.engines._fairchem_bridge import FairchemEngine


class UMADirectEngine(FairchemEngine):
    """UMA ``uma-s-1p2p1`` (conserving) single points; ``stage.method`` must be ``uma-s-1p2p1``."""

    tag = "uma_direct"
    METHOD = "uma-s-1p2p1"
    REGISTRY_NAME = "uma-s-1p2p1"
