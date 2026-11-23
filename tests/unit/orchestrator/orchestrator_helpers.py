"""Shared helpers for the runner tests: a small butane recipe and fake engines."""

import sqlite3
from pathlib import Path

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import MolecularState, StageConfig
from eta_rxncat.engines import EngineInputError, RawResult, RDKitFFEngine
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import Recipe, SpeciesSpec

UFF = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
UFF_SP = StageConfig(kind="single_point", engine="rdkit_ff", method="uff")


def butane(n_embed: int = 4) -> SpeciesSpec:
    """n-butane with a small pool."""
    return SpeciesSpec("n_butane", "CCCC", 0, 1, ConformerOptions(n_embed=n_embed))


def water() -> SpeciesSpec:
    """Water with a tiny pool."""
    return SpeciesSpec("water", "O", 0, 1, ConformerOptions(n_embed=2))


def uff_recipe() -> Recipe:
    """rdkit_ff UFF with GeometricOptimizer defaults."""
    return Recipe("uff", UFF, GeometricOptimizer())


def rows(path: Path) -> dict[str, tuple[str, str]]:
    """Return {key: (stage_kind, created_at_utc)} read straight from the store file."""
    with sqlite3.connect(path) as conn:
        return {
            k: (kind, created)
            for k, kind, created in conn.execute(
                "SELECT key, stage_kind, created_at_utc FROM stage_artifacts"
            )
        }


class ImaginaryUFF(RDKitFFEngine):
    """rdkit_ff UFF whose Hessians get a negative curvature on atom 1 (all axes).

    ``imaginary_calls`` lists the Hessian calls (1-based) that are modified; others are real.
    """

    imaginary_calls: frozenset[int] = frozenset({1})
    hessian_calls = 0

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        raw = super()._evaluate(state, forces=forces, hessian=hessian)
        if not hessian:
            return raw
        type(self).hessian_calls += 1
        if type(self).hessian_calls not in self.imaginary_calls:
            return raw
        assert raw.hessian_hartree_per_bohr2 is not None
        matrix = [list(row) for row in raw.hessian_hartree_per_bohr2]
        for i in (3, 4, 5):  # atom 1 (a hydrogen), every axis: survives the rigid projection
            matrix[i][i] -= 2.0
        return RawResult(
            energy_hartree=raw.energy_hartree,
            device=raw.device,
            forces_hartree_per_bohr=raw.forces_hartree_per_bohr,
            hessian_hartree_per_bohr2=matrix,
            hessian_method=raw.hessian_method,
            hessian_max_asymmetry=raw.hessian_max_asymmetry,
        )


class RefusingUFF(RDKitFFEngine):
    """rdkit_ff UFF that refuses every evaluation."""

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        raise EngineInputError("fake engine refuses this state")


def water_state() -> MolecularState:
    """A near-equilibrium water geometry in SMILES ``O`` atom order (O, H, H)."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
        charge=0,
        spin_multiplicity=1,
    )
