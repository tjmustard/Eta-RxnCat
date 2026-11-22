"""Unit tests for v0.2.0 engines (RDKit FF, PySCF STO-3G analytical gradient/Hessian, VRAM guard)."""

import numpy as np

from eta_rxncat.core.models import MolecularState
from eta_rxncat.engines.pyscf_engine import PySCFEngine
from eta_rxncat.engines.rdkit_xtb import RDKitFFEngine


def _water() -> MolecularState:
    return MolecularState(
        name="water",
        symbols=["O", "H", "H"],
        coordinates=[
            [0.0, 0.0, 0.1173],
            [0.0, 0.7572, -0.4692],
            [0.0, -0.7572, -0.4692],
        ],
        charge=0,
        spin_multiplicity=1,
    )


def test_rdkit_uff_energy_and_forces() -> None:
    engine = RDKitFFEngine("UFF")
    res = engine.evaluate(_water(), compute_forces=True, compute_hessian=True)
    assert np.isfinite(res.electronic_energy_hartree)
    assert res.forces_hartree_per_bohr is not None
    assert np.asarray(res.forces_hartree_per_bohr).shape == (3, 3)
    assert res.hessian_hartree_per_bohr2 is not None
    assert np.asarray(res.hessian_hartree_per_bohr2).shape == (9, 9)


def test_pyscf_cpu_energy_gradient_and_vram_guard() -> None:
    engine = PySCFEngine(functional="B3LYP", basis="STO-3G", prefer_gpu=False)
    assert engine.estimate_vram_gb(1500) > 6.5
    res = engine.evaluate(_water(), compute_forces=True, compute_hessian=True)
    assert res.electronic_energy_hartree < -75.0
    assert np.asarray(res.forces_hartree_per_bohr).shape == (3, 3)
    assert np.asarray(res.hessian_hartree_per_bohr2).shape == (9, 9)
