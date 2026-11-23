"""Grimme quasi-RRHO thermochemistry and 1 M standard-state free energy corrections."""

from __future__ import annotations

import math
import numpy as np

from eta_rxncat.core.models import MolecularState, ThermoConfig, ThermoResult

AMU_TO_KG = 1.66053906660e-27
BOHR_TO_M = 0.529177210903e-10
ANGSTROM_TO_M = 1.0e-10
HARTREE_TO_J = 4.3597447222071e-18
HARTREE_TO_KCAL_MOL = 627.5094740631
AVOGADRO = 6.02214076e23
KB = 1.380649e-23
PLANCK = 6.62607015e-34
SPEED_OF_LIGHT_CM = 2.99792458e10
R_J_MOL_K = KB * AVOGADRO
R_CAL_MOL_K = R_J_MOL_K / 4.184
ATM_TO_PA = 101325.0

_ATOMIC_MASSES_AMU: dict[str, float] = {
    "H": 1.007825, "B": 11.009305, "C": 12.000000, "N": 14.003074, "O": 15.994915,
    "F": 18.998403, "P": 30.973762, "S": 31.972071, "Cl": 34.968853, "Br": 78.918337,
    "I": 126.904473, "Ti": 47.947946, "Fe": 55.934937, "Ni": 57.935342, "Cu": 62.929597,
    "Zr": 89.904704, "Ru": 101.904349, "Rh": 102.905504, "Pd": 105.903486, "Ir": 192.962926,
    "Pt": 194.964791,
}


def compute_frequencies_from_hessian(
    state: MolecularState,
    hessian_ha_bohr2: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Mass-weight Cartesian Hessian, project translations/rotations, and return (freqs_cm1, modes_cart)."""
    n_atoms = len(state.symbols)
    masses_amu = np.asarray([_ATOMIC_MASSES_AMU.get(s, 12.0) for s in state.symbols], dtype=np.float64)
    inv_sqrt_m = np.repeat(1.0 / np.sqrt(masses_amu), 3)

    # Convert Hartree/Bohr^2 -> J / m^2 / kg
    conv = HARTREE_TO_J / (BOHR_TO_M**2 * AMU_TO_KG)
    mw_hess = (hessian_ha_bohr2 * conv) * np.outer(inv_sqrt_m, inv_sqrt_m)
    mw_hess = 0.5 * (mw_hess + mw_hess.T)

    # Project out center-of-mass translation and rigid-body rotation
    coords_ang = state.coords_array()
    com = np.average(coords_ang, axis=0, weights=masses_amu)
    centered = coords_ang - com

    basis_vectors: list[np.ndarray] = []
    for axis in range(3):
        t_vec = np.zeros((n_atoms, 3), dtype=np.float64)
        t_vec[:, axis] = np.sqrt(masses_amu)
        basis_vectors.append(t_vec.reshape(-1))

    for axis in range(3):
        rot_axis = np.zeros(3, dtype=np.float64)
        rot_axis[axis] = 1.0
        r_vec = np.cross(centered, rot_axis) * np.sqrt(masses_amu)[:, None]
        norm = np.linalg.norm(r_vec)
        if norm > 1e-8:
            basis_vectors.append(r_vec.reshape(-1))

    # Orthonormalize Eckart vectors via SVD
    eckart_mat = np.column_stack(basis_vectors)
    u_mat, s_vals, _ = np.linalg.svd(eckart_mat, full_matrices=False)
    rank = int(np.sum(s_vals > 1e-8))
    q_tr = u_mat[:, :rank]
    proj = np.eye(3 * n_atoms) - q_tr @ q_tr.T

    proj_hess = proj @ mw_hess @ proj
    eigvals, eigvecs = np.linalg.eigh(proj_hess)

    # Filter out the zeroed translation/rotation modes
    keep_mask = np.ones(3 * n_atoms, dtype=bool)
    zero_indices = np.argsort(np.abs(eigvals))[:rank]
    keep_mask[zero_indices] = False

    vib_eigvals = eigvals[keep_mask]
    vib_vecs = eigvecs[:, keep_mask]

    freqs_cm1 = np.sign(vib_eigvals) * np.sqrt(np.abs(vib_eigvals)) / (2.0 * math.pi * SPEED_OF_LIGHT_CM)
    order = np.argsort(freqs_cm1)
    return freqs_cm1[order], vib_vecs[:, order]


def compute_thermochemistry(
    state: MolecularState,
    electronic_energy_hartree: float,
    hessian_ha_bohr2: np.ndarray,
    config: ThermoConfig | None = None,
    *,
    expect_transition_state: bool = False,
) -> ThermoResult:
    """Compute ZPE, thermal enthalpy, Grimme quasi-RRHO entropy, and 1 M Gibbs free energy."""
    cfg = config or ThermoConfig()
    T = cfg.temperature_k
    P_pa = cfg.pressure_atm * ATM_TO_PA

    freqs_cm1, _ = compute_frequencies_from_hessian(state, hessian_ha_bohr2)
    imag_freqs = [float(f) for f in freqs_cm1 if f < -10.0]
    real_freqs = np.asarray([float(f) for f in freqs_cm1 if f > 10.0], dtype=np.float64)

    # Average molecular moment of inertia B_av for Grimme qRRHO damping
    masses_kg = np.asarray([_ATOMIC_MASSES_AMU.get(s, 12.0) * AMU_TO_KG for s in state.symbols])
    coords_m = state.coords_array() * ANGSTROM_TO_M
    total_mass = float(np.sum(masses_kg))
    com = np.average(coords_m, axis=0, weights=masses_kg)
    r = coords_m - com
    inertia = np.zeros((3, 3), dtype=np.float64)
    for m_i, r_i in zip(masses_kg, r, strict=True):
        inertia += m_i * (np.dot(r_i, r_i) * np.eye(3) - np.outer(r_i, r_i))
    principals = np.linalg.eigvalsh(inertia)
    b_av = float(np.mean(principals[principals > 1e-47])) if np.any(principals > 1e-47) else 1e-44

    # Translational entropy (Sackur-Tetrode at P_pa)
    q_trans = ((2.0 * math.pi * total_mass * KB * T / (PLANCK**2)) ** 1.5) * (KB * T / P_pa)
    s_trans = R_J_MOL_K * (math.log(q_trans) + 2.5)

    # Rotational entropy
    if len(state.symbols) == 1:
        s_rot = 0.0
    elif np.sum(principals > 1e-47) == 2:
        i_lin = float(np.max(principals))
        q_rot = 8.0 * (math.pi**2) * i_lin * KB * T / (PLANCK**2)
        s_rot = R_J_MOL_K * (math.log(q_rot) + 1.0)
    else:
        i_a, i_b, i_c = principals
        q_rot = math.sqrt(math.pi * i_a * i_b * i_c) * ((8.0 * (math.pi**2) * KB * T / (PLANCK**2)) ** 1.5)
        s_rot = R_J_MOL_K * (math.log(q_rot) + 1.5)

    # Electronic entropy
    s_elec = R_J_MOL_K * math.log(float(state.spin_multiplicity))

    # Vibrational ZPE, thermal energy, and Grimme quasi-RRHO entropy
    zpe_j_mol = 0.0
    e_vib_therm_j_mol = 0.0
    s_vib_j_mol_k = 0.0

    for nu_cm1 in real_freqs:
        nu_hz = nu_cm1 * SPEED_OF_LIGHT_CM
        theta_v = PLANCK * nu_hz / KB
        x = theta_v / T
        zpe_j_mol += 0.5 * R_J_MOL_K * theta_v
        exp_neg_x = math.exp(-min(x, 500.0))
        e_vib_therm_j_mol += R_J_MOL_K * theta_v * exp_neg_x / (1.0 - exp_neg_x)

        s_rrho = R_J_MOL_K * (x * exp_neg_x / (1.0 - exp_neg_x) - math.log(1.0 - exp_neg_x))
        if cfg.quasi_rrho_mode == "grimme":
            mu = PLANCK / (8.0 * (math.pi**2) * nu_hz)
            mu_prime = mu * b_av / (mu + b_av)
            s_rotor = R_J_MOL_K * (0.5 + math.log(math.sqrt(8.0 * (math.pi**3) * mu_prime * KB * T / (PLANCK**2))))
            weight = 1.0 / (1.0 + (cfg.omega0_cm1 / nu_cm1) ** 4)
            s_vib_j_mol_k += weight * s_rrho + (1.0 - weight) * s_rotor
        else:
            s_vib_j_mol_k += s_rrho

    # Enthalpy H = E_elec + ZPE + E_trans(3/2 RT) + E_rot(3/2 RT) + E_vib_therm + RT
    e_trans_rot = 3.0 * R_J_MOL_K * T if len(state.symbols) > 1 else 1.5 * R_J_MOL_K * T
    h_corr_j_mol = zpe_j_mol + e_trans_rot + e_vib_therm_j_mol + R_J_MOL_K * T

    s_total_j_mol_k = s_trans + s_rot + s_vib_j_mol_k + s_elec
    g_corr_j_mol = h_corr_j_mol - T * s_total_j_mol_k

    # Standard-state concentration adjustment (1 atm ideal gas -> c_mol_l M solution)
    if cfg.concentration_mol_l is not None:
        v_gas_l_mol = (R_J_MOL_K * T / P_pa) * 1000.0
        g_corr_j_mol += R_J_MOL_K * T * math.log(cfg.concentration_mol_l * v_gas_l_mol)

    j_mol_to_ha = 1.0 / (HARTREE_TO_J * AVOGADRO)
    g_total_ha = electronic_energy_hartree + g_corr_j_mol * j_mol_to_ha

    notes: list[str] = []
    valid = True
    if expect_transition_state:
        if len(imag_freqs) != 1:
            valid = False
            notes.append(f"Expected exactly 1 imaginary frequency for TS, found {len(imag_freqs)}: {imag_freqs}")
    elif len(imag_freqs) > 0:
        valid = False
        notes.append(f"Expected 0 imaginary frequencies for ground state, found {len(imag_freqs)}: {imag_freqs}")

    return ThermoResult(
        electronic_energy_hartree=electronic_energy_hartree,
        zpe_hartree=zpe_j_mol * j_mol_to_ha,
        thermal_enthalpy_corr_hartree=h_corr_j_mol * j_mol_to_ha,
        entropy_cal_per_mol_k=s_total_j_mol_k / 4.184,
        gibbs_free_energy_hartree=g_total_ha,
        imaginary_frequencies_cm1=imag_freqs,
        is_valid_stationary_point=valid,
        validation_notes=notes,
    )
