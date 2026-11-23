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
from eta_rxncat.mapping.graft import graft
from eta_rxncat.mapping.report import (
    core_rmsd_angstrom,
    covalent_radius_angstrom,
    junction_volumes,
    perceive_bonds,
)

__all__ = [
    "AlignmentError",
    "CoreDisplacementError",
    "GraftClashError",
    "GraftInputError",
    "MappingError",
    "Superposition",
    "core_rmsd_angstrom",
    "covalent_radius_angstrom",
    "graft",
    "junction_volumes",
    "pair_set_shape",
    "perceive_bonds",
    "superpose",
]
