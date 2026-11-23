"""Shared helpers for the conformer tests: RDKit-built geometries and UFF optimization."""

from functools import lru_cache
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem

from eta_rxncat.core import (
    ConformerRecord,
    MolecularState,
    OptimizationResult,
    StageConfig,
    ThermoConfig,
)
from eta_rxncat.engines import RDKitFFEngine
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.thermo import thermochemistry

UFF = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
T1 = "C=C(/C=C/OC)OC"
BUTADIENE = "C=CC=C"
P1A_N = "C1=C[C@H]2C[C@@H]1[C@H]1C[C@H]12"


def uff() -> RDKitFFEngine:
    """Return the rdkit_ff UFF engine."""
    return RDKitFFEngine(UFF)


@lru_cache(maxsize=1)
def optimizer() -> GeometricOptimizer:
    """Return one GeometricOptimizer."""
    return GeometricOptimizer()


def embedded(smiles: str, seed: int = 42) -> MolecularState:
    """Return one ETKDG embedding of ``smiles`` (with H) as a neutral singlet state."""
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    assert AllChem.EmbedMolecule(mol, randomSeed=seed) == 0
    return state_of(mol)


def state_of(mol: Any, conf_id: int = -1) -> MolecularState:
    """Return the state of an RDKit molecule's conformer, in the molecule's atom order."""
    return MolecularState(
        symbols=[a.GetSymbol() for a in mol.GetAtoms()],
        coordinates=mol.GetConformer(conf_id).GetPositions().tolist(),
        charge=0,
        spin_multiplicity=1,
    )


def optimize(state: MolecularState) -> OptimizationResult:
    """UFF-optimize ``state`` with GeometricOptimizer."""
    return optimizer().minimize(state, uff())


def record(
    opt: OptimizationResult, smiles: str, degeneracy: int, source_ids: list[int]
) -> ConformerRecord:
    """Return a ConformerRecord with UFF (finite-difference Hessian) thermochemistry."""
    engine = uff()
    hessian = engine.evaluate(opt.final_state, forces=False, hessian=True)
    assert hessian.hessian_hartree_per_bohr2 is not None
    thermo = thermochemistry(
        opt.final_state,
        hessian.hessian_hartree_per_bohr2,
        opt.final_energy_hartree,
        smiles=smiles,
        energy_source="optimization",
        config=ThermoConfig(),
    )
    return ConformerRecord(
        state=opt.final_state,
        optimization=opt,
        thermo=thermo,
        degeneracy=degeneracy,  # type: ignore[arg-type]
        source_ids=source_ids,
    )
