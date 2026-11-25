"""Unit tests for v0.5.0 P-RFO saddle-point optimizer and active-core imaginary mode validator."""

import numpy as np

from eta_rxncat.core.models import MolecularState
from eta_rxncat.engines.base import BOHR_TO_ANGSTROM, BasePotentialEngine
from eta_rxncat.core.models import PotentialResult
from eta_rxncat.optimize.ts_optimizer import (
    analyze_vibrational_modes,
    optimize_transition_state,
    validate_transition_state_modes,
)


class _AnalyticSaddlePotential(BasePotentialEngine):
    """2-atom harmonic + inverted Morse-like saddle potential along x-coordinate of atom 0."""

    name = "analytic_saddle"

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        # Saddle at x0 = 0.0, x1 = 1.5 Angstrom; negative curvature along x0
        coords_bohr = state.coords_array() / BOHR_TO_ANGSTROM
        x0 = coords_bohr[0, 0]
        x1_eq = 1.5 / BOHR_TO_ANGSTROM
        dx1 = coords_bohr[1, 0] - x1_eq
        other = coords_bohr.copy()
        other[0, 0] = 0.0
        other[1, 0] = 0.0

        k_neg = -0.04
        k_pos = 0.25
        energy = 0.5 * k_neg * (x0**2) + 0.5 * k_pos * (dx1**2) + 0.5 * k_pos * float(np.sum(other**2))

        grad = k_pos * other
        grad[0, 0] = k_neg * x0
        grad[1, 0] = k_pos * dx1

        hess = np.diag([k_neg, k_pos, k_pos, k_pos, k_pos, k_pos])
        return PotentialResult(
            electronic_energy_hartree=float(energy),
            forces_hartree_per_bohr=(-grad).tolist() if compute_forces else None,
            hessian_hartree_per_bohr2=hess.tolist() if compute_hessian else None,
        )


def test_prfo_converges_to_first_order_saddle_localized_on_active_atom() -> None:
    start = MolecularState(
        name="model_ts",
        symbols=["C", "O"],
        coordinates=[[0.12, 0.05, -0.04], [1.55, -0.03, 0.02]],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0],
    )
    opt_state, _, final_hess = optimize_transition_state(start, _AnalyticSaddlePotential(), max_steps=40)
    assert np.allclose(opt_state.coords_array()[0], [0.0, 0.0, 0.0], atol=1e-3)

    modes = analyze_vibrational_modes(opt_state, final_hess)
    ok, reasons = validate_transition_state_modes(opt_state, modes, min_active_core_fraction=0.80)
    assert ok, f"Validation failed: {reasons}"
