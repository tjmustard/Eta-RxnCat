"""Clean-room Partitioned Rational Function Optimization (P-RFO) saddle-point search
and active-core imaginary mode validation (Mustard et al., ACS Catal. 2015).
"""

from __future__ import annotations

import numpy as np

from eta_rxncat.core.models import MolecularState, VibrationalMode
from eta_rxncat.core.thermo import _ATOMIC_MASSES_AMU, compute_frequencies_from_hessian
from eta_rxncat.engines.base import BOHR_TO_ANGSTROM, PotentialEngine


def analyze_vibrational_modes(
    state: MolecularState,
    hessian_ha_bohr2: np.ndarray,
) -> list[VibrationalMode]:
    """Compute normal modes and fraction of mass-weighted kinetic energy on active_atom_indices."""
    freqs_cm1, mw_modes = compute_frequencies_from_hessian(state, hessian_ha_bohr2)
    n_atoms = len(state.symbols)
    masses = np.asarray([_ATOMIC_MASSES_AMU.get(s, 12.0) for s in state.symbols], dtype=np.float64)
    inv_sqrt_m = np.repeat(1.0 / np.sqrt(masses), 3)

    active_dof: list[int] = []
    for a_idx in state.active_atom_indices:
        active_dof.extend([3 * a_idx, 3 * a_idx + 1, 3 * a_idx + 2])

    modes: list[VibrationalMode] = []
    for m_idx, freq in enumerate(freqs_cm1):
        q_mw = mw_modes[:, m_idx]
        # In mass-weighted coordinates, mode kinetic energy distribution is q_mw_i^2
        total_norm_sq = float(np.sum(q_mw**2))
        if active_dof and total_norm_sq > 1e-12:
            active_frac = float(np.sum(q_mw[active_dof] ** 2) / total_norm_sq)
        else:
            active_frac = None

        cart_disp = (q_mw * inv_sqrt_m).reshape(n_atoms, 3).tolist()
        modes.append(
            VibrationalMode(
                frequency_cm1=float(freq),
                displacement_vectors=cart_disp,
                active_core_kinetic_fraction=active_frac,
            )
        )
    return modes


def validate_transition_state_modes(
    state: MolecularState,
    modes: list[VibrationalMode],
    *,
    min_imag_freq_cm1: float = -40.0,
    min_active_core_fraction: float = 0.50,
) -> tuple[bool, list[str]]:
    """Verify single imaginary mode localized on reactive core atoms."""
    reasons: list[str] = []
    imag_modes = [m for m in modes if m.frequency_cm1 < min_imag_freq_cm1]
    if len(imag_modes) != 1:
        reasons.append(
            f"TS requires exactly 1 imaginary frequency < {min_imag_freq_cm1} cm^-1; found {len(imag_modes)}."
        )
        return False, reasons

    ts_mode = imag_modes[0]
    if (
        state.active_atom_indices
        and ts_mode.active_core_kinetic_fraction is not None
        and ts_mode.active_core_kinetic_fraction < min_active_core_fraction
    ):
        reasons.append(
            f"Imaginary mode ({ts_mode.frequency_cm1:.1f} cm^-1) has only "
            f"{ts_mode.active_core_kinetic_fraction:.1%} kinetic energy on active atoms "
            f"(minimum {min_active_core_fraction:.0%})."
        )
        return False, reasons

    return True, []


def _prfo_step(
    gradient: np.ndarray,
    hessian: np.ndarray,
    trust_radius_bohr: float = 0.15,
) -> np.ndarray:
    """Compute a single Partitioned RFO step maximizing along mode 0 and minimizing along modes 1..N-1."""
    eigvals, eigvecs = np.linalg.eigh(0.5 * (hessian + hessian.T))
    # Project out near-zero translational/rotational eigenvalues
    mask = np.abs(eigvals) > 1e-6
    vals = eigvals[mask]
    vecs = eigvecs[:, mask]
    if len(vals) == 0:
        return np.zeros_like(gradient)

    g_proj = vecs.T @ gradient

    # Maximize along lowest mode (index 0)
    b0 = float(vals[0])
    f0 = float(g_proj[0])
    # Solve 2x2 RFO secular equation for maximization: lambda_p > b0
    lambda_p = 0.5 * (b0 + np.sqrt(b0**2 + 4.0 * f0**2))
    step_0 = -f0 / (b0 - lambda_p - 1e-8)

    # Minimize along remaining modes (indices 1:)
    step_rest = np.zeros(len(vals) - 1, dtype=np.float64)
    if len(vals) > 1:
        b_rest = vals[1:]
        f_rest = g_proj[1:]
        # Solve RFO shift lambda_n < min(b_rest) via simple Newton/bisection
        lam_n = min(float(np.min(b_rest)) - 0.1, -0.05)
        for _ in range(25):
            denom = b_rest - lam_n
            phi = lam_n + float(np.sum((f_rest**2) / denom))
            dphi = 1.0 + float(np.sum((f_rest**2) / (denom**2)))
            lam_n -= phi / max(dphi, 1e-8)
        step_rest = -f_rest / (b_rest - lam_n)

    full_mode_step = np.concatenate([[step_0], step_rest])
    cart_step = vecs @ full_mode_step

    norm = float(np.linalg.norm(cart_step))
    if norm > trust_radius_bohr:
        cart_step *= trust_radius_bohr / norm
    return cart_step


def optimize_transition_state(
    state: MolecularState,
    engine: PotentialEngine,
    *,
    max_steps: int = 80,
    grad_rms_tol: float = 3.0e-4,
    hessian_refresh_interval: int = 8,
    trust_radius_bohr: float = 0.15,
) -> tuple[MolecularState, float, np.ndarray]:
    """Optimize a first-order saddle point using P-RFO with periodic exact Hessian refreshes."""
    cur_state = state.model_copy(deep=True)
    res = engine.evaluate(cur_state, compute_forces=True, compute_hessian=True)
    hess = np.asarray(res.hessian_hartree_per_bohr2, dtype=np.float64)
    grad = -np.asarray(res.forces_hartree_per_bohr, dtype=np.float64).reshape(-1)
    energy = res.electronic_energy_hartree
    cur_trust = trust_radius_bohr

    for step_idx in range(1, max_steps + 1):
        g_rms = float(np.sqrt(np.mean(grad**2)))
        if g_rms < grad_rms_tol:
            break

        dx_bohr = _prfo_step(grad, hess, trust_radius_bohr=cur_trust)
        new_coords = cur_state.coords_array() + dx_bohr.reshape(-1, 3) * BOHR_TO_ANGSTROM
        cand_state = cur_state.model_copy(update={"coordinates": new_coords.tolist()})

        refresh = (step_idx % hessian_refresh_interval == 0)
        cand_res = engine.evaluate(cand_state, compute_forces=True, compute_hessian=refresh)
        new_grad = -np.asarray(cand_res.forces_hartree_per_bohr, dtype=np.float64).reshape(-1)

        if refresh and cand_res.hessian_hartree_per_bohr2 is not None:
            hess = np.asarray(cand_res.hessian_hartree_per_bohr2, dtype=np.float64)
        else:
            # Bofill quasi-Newton Hessian update (preserves negative curvature)
            dg = new_grad - grad
            y_minus_hs = dg - hess @ dx_bohr
            s_norm2 = float(np.dot(dx_bohr, dx_bohr))
            if s_norm2 > 1e-12:
                h_psb = (
                    np.outer(y_minus_hs, dx_bohr) + np.outer(dx_bohr, y_minus_hs)
                ) / s_norm2 - (float(np.dot(y_minus_hs, dx_bohr)) / (s_norm2**2)) * np.outer(
                    dx_bohr, dx_bohr
                )
                sy = float(np.dot(dx_bohr, y_minus_hs))
                y_norm2 = float(np.dot(y_minus_hs, y_minus_hs))
                phi = (sy**2) / max(s_norm2 * y_norm2, 1e-16)
                h_sr1 = np.outer(y_minus_hs, y_minus_hs) / sy if abs(sy) > 1e-10 else np.zeros_like(hess)
                hess = hess + (1.0 - phi) * h_psb + phi * h_sr1

        cur_state = cand_state
        grad = new_grad
        energy = cand_res.electronic_energy_hartree

    # Final exact Hessian at converged saddle point
    final_res = engine.evaluate(cur_state, compute_forces=False, compute_hessian=True)
    final_hess = np.asarray(final_res.hessian_hartree_per_bohr2, dtype=np.float64)
    return cur_state, energy, final_hess
