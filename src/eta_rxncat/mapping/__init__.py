"""Clean-room conserved-core mapper: superposition, graft surgery and core-frozen relaxation.

Importing this package loads numpy only among heavy modules (no geometric, torch, pyscf, fairchem
or rdkit).
"""

from eta_rxncat.mapping.align import Superposition, pair_set_shape, superpose
from eta_rxncat.mapping.errors import (
    AlignmentError,
    CoreDisplacementError,
    GraftClashError,
    GraftInputError,
    MappingError,
)

__all__ = [
    "AlignmentError",
    "CoreDisplacementError",
    "GraftClashError",
    "GraftInputError",
    "MappingError",
    "Superposition",
    "pair_set_shape",
    "superpose",
]
