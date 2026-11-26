"""Unit tests for v0.3.0 Grimme quasi-RRHO thermochemistry, Boltzmann ensemble, and GS optimization."""

import numpy as np

from eta_rxncat.conformers.ensemble import build_boltzmann_ensemble, generate_conformers
from eta_rxncat.core.models import MolecularState, ThermoConfig
from eta_rxncat.core.thermo import compute_thermochemistry
from eta_rxncat.engines.rdkit_xtb import RDKitFFEngine
from eta_rxncat.optimize.gs_optimizer import optimize_ground_state


def _butane() -> MolecularState:
    return MolecularState(
        name="n_butane",
        symbols=["C", "C", "C", "C", "H", "H", "H", "H", "H", "H", "H", "H", "H", "H"],
        coordinates=[
            [-1.90, -0.25, 0.00],
            [-0.64, 0.60, 0.00],
            [0.64, -0.25, 0.00],
            [1.90, 0.60, 0.00],
            [-2.80, 0.38, 0.00],
            [-1.93, -0.89, 0.89],
            [-1.93, -0.89, -0.89],
            [-0.64, 1.25, 0.89],
            [-0.64, 1.25, -0.89],
            [0.64, -0.90, 0.89],
            [0.64, -0.90, -0.89],
            [2.80, -0.03, 0.00],
            [1.93, 1.24, 0.89],
            [1.93, 1.24, -0.89],
        ],
        charge=0,
        spin_multiplicity=1,
    )


def test_conformer_generation_and_boltzmann_weights() -> None:
    confs = generate_conformers(_butane(), num_confs=10, rmsd_threshold_angstrom=0.25)
    assert len(confs) >= 2
    energies = [-158.4500, -158.4485][: len(confs)]
    ens = build_boltzmann_ensemble("n_butane", confs[: len(energies)], energies)
    assert ens.lowest_conformer_index == 0
    assert ens.boltzmann_averaged_gibbs_hartree <= energies[0]


def test_gs_optimization_and_qrrho_thermochemistry() -> None:
    ff = RDKitFFEngine("UFF")
    opt_state, opt_e = optimize_ground_state(_butane(), ff, maxiter=100)
    hess_res = ff.evaluate(opt_state, compute_forces=False, compute_hessian=True)
    thermo = compute_thermochemistry(
        opt_state,
        opt_e,
        np.asarray(hess_res.hessian_hartree_per_bohr2),
        ThermoConfig(quasi_rrho_mode="grimme", concentration_mol_l=1.0),
    )
    assert thermo.is_valid_stationary_point
    assert thermo.zpe_hartree > 0.05
