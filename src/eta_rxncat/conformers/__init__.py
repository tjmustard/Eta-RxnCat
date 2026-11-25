"""Conformer generation, dedup, degeneracy and ensembles (v0.3.0); TS sampler (v0.6.0).

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
from eta_rxncat.conformers.ts_sampler import (
    FaceDescriptorError,
    TSSample,
    forming_bond_configuration,
    sample_ts_conformers,
)

__all__ = [
    "ConformerError",
    "ConformerInputError",
    "ConformerOptions",
    "ConformerPool",
    "EmbeddingFailedError",
    "EnsembleEmptyError",
    "FaceDescriptorError",
    "Kept",
    "PoolMember",
    "TSSample",
    "assign_degeneracy",
    "build_ensemble",
    "conformer_chiral",
    "dedup",
    "dihedral_deg",
    "drop_mirror_partners",
    "energy_window",
    "forming_bond_configuration",
    "generate",
    "graph_achiral",
    "sample_ts_conformers",
    "seed_geometries_sha256",
]
