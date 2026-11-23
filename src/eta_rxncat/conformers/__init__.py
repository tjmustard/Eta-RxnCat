"""Conformer generation, dedup, degeneracy and ensembles (v0.3.0).

RDKit and numpy are imported here; geomeTRIC, torch, PySCF and fairchem are not.
"""

from eta_rxncat.conformers.dedup import Kept, dedup, energy_window
from eta_rxncat.conformers.degeneracy import (
    assign_degeneracy,
    conformer_chiral,
    drop_mirror_partners,
    graph_achiral,
)
from eta_rxncat.conformers.ensemble import build_ensemble
from eta_rxncat.conformers.errors import (
    ConformerError,
    ConformerInputError,
    EmbeddingFailedError,
    EnsembleEmptyError,
)
from eta_rxncat.conformers.generate import (
    ConformerPool,
    PoolMember,
    generate,
    seed_geometries_sha256,
)
from eta_rxncat.conformers.geometry import dihedral_deg
from eta_rxncat.conformers.options import ConformerOptions

__all__ = [
    "ConformerError",
    "ConformerInputError",
    "ConformerOptions",
    "ConformerPool",
    "EmbeddingFailedError",
    "EnsembleEmptyError",
    "Kept",
    "PoolMember",
    "assign_degeneracy",
    "build_ensemble",
    "conformer_chiral",
    "dedup",
    "dihedral_deg",
    "drop_mirror_partners",
    "energy_window",
    "generate",
    "graph_achiral",
    "seed_geometries_sha256",
]
