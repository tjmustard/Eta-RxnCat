"""Ideal-gas quasi-RRHO thermochemistry at a 1 M standard state (Grimme 2012; R15).

All terms are computed per mole in SI units and converted to Hartree (per molecule) at the end.
The helper functions are the closed forms of the mission's Algorithms section, one per term.
"""

import math
from collections.abc import Sequence
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from eta_rxncat.core import MolecularState, ThermoAnalysisOptions, ThermoConfig, ThermoResult
from eta_rxncat.thermo._geometry import principal_axes
from eta_rxncat.thermo.constants import (
    AMU_KG,
    ANGSTROM_M,
    ATM_PA,
    CM1_TO_HZ,
    H_PLANCK,
    J_PER_MOL_TO_HARTREE,
    K_BOLTZMANN,
    N_AVOGADRO,
    R_GAS,
)
from eta_rxncat.thermo.masses import atomic_masses_amu, masses_source
from eta_rxncat.thermo.modes import normal_modes
from eta_rxncat.thermo.symmetry import rotational_symmetry_number


def translational(mass_kg: float, temperature_k: float, pressure_pa: float) -> tuple[float, float]:
    """Return (S, E) of translation in J/(mol K) and J/mol (Sackur-Tetrode; E = 3/2 RT)."""
    kt = K_BOLTZMANN * temperature_k
    q = (2.0 * math.pi * mass_kg * kt / H_PLANCK**2) ** 1.5 * kt / pressure_pa
    return R_GAS * (math.log(q) + 2.5), 1.5 * R_GAS * temperature_k


def rotational(
    moments_kg_m2: Sequence[float], sigma: int, linear: bool, temperature_k: float
) -> tuple[float, float]:
    """Return (S, E) of rigid rotation in J/(mol K) and J/mol.

    Non-linear: S = R[ln(sqrt(pi)/sigma (8 pi^2 kT/h^2)^(3/2) sqrt(IA IB IC)) + 3/2], E = 3/2 RT.
    Linear: S = R[ln(8 pi^2 I kT/(sigma h^2)) + 1], E = RT, with I the largest moment.
    """
    kt = K_BOLTZMANN * temperature_k
    if linear:
        inertia = max(moments_kg_m2)
        s = R_GAS * (math.log(8.0 * math.pi**2 * inertia * kt / (sigma * H_PLANCK**2)) + 1.0)
        return s, R_GAS * temperature_k
    i_a, i_b, i_c = moments_kg_m2
    q = (
        math.sqrt(math.pi)
        / sigma
        * (8.0 * math.pi**2 * kt / H_PLANCK**2) ** 1.5
        * math.sqrt(i_a * i_b * i_c)
    )
    return R_GAS * (math.log(q) + 1.5), 1.5 * R_GAS * temperature_k


def grimme_weight(wavenumber_cm1: float, cutoff_cm1: float, alpha: float) -> float:
    """Return the Grimme damping weight w = 1 / (1 + (omega_0 / nu)^alpha)."""
    return 1.0 / (1.0 + math.pow(cutoff_cm1 / wavenumber_cm1, alpha))


def rrho_vibrational_entropy(wavenumber_cm1: float, temperature_k: float) -> float:
    """Return S_RRHO = R[x/(e^x - 1) - ln(1 - e^-x)] of one mode, x = h c nu / (k T)."""
    x = H_PLANCK * CM1_TO_HZ * wavenumber_cm1 / (K_BOLTZMANN * temperature_k)
    return R_GAS * (x / math.expm1(x) - math.log(-math.expm1(-x)))


def free_rotor_entropy(
    wavenumber_cm1: float, temperature_k: float, rotor_moment_kg_m2: float
) -> float:
    """Return S_r = R[1/2 + ln((8 pi^3 mu' k T / h^2)^(1/2))] of one mode (R15).

    mu = h / (8 pi^2 c nu) and mu' = mu B_av / (mu + B_av).
    """
    mu = H_PLANCK / (8.0 * math.pi**2 * CM1_TO_HZ * wavenumber_cm1)
    mu_eff = mu * rotor_moment_kg_m2 / (mu + rotor_moment_kg_m2)
    kt = K_BOLTZMANN * temperature_k
    return R_GAS * (0.5 + 0.5 * math.log(8.0 * math.pi**3 * mu_eff * kt / H_PLANCK**2))


def vibrational(
    wavenumbers_cm1: Sequence[float], config: ThermoConfig
) -> tuple[float, float, float]:
    """Return (ZPE, E_vib, S_vib) in J/mol, J/mol and J/(mol K) over the given positive modes.

    E_vib is the thermal excess excluding ZPE. S_vib is Grimme's interpolation between S_RRHO and
    the free-rotor entropy; the energies are not damped.
    """
    t = config.temperature_k
    zpe = e_vib = s_vib = 0.0
    for nu in wavenumbers_cm1:
        theta = H_PLANCK * CM1_TO_HZ * nu / K_BOLTZMANN
        zpe += 0.5 * R_GAS * theta
        e_vib += R_GAS * theta / math.expm1(theta / t)
        w = grimme_weight(nu, config.qrrho_cutoff_cm1, config.qrrho_alpha)
        s_vib += w * rrho_vibrational_entropy(nu, t) + (1.0 - w) * free_rotor_entropy(
            nu, t, config.qrrho_rotor_moment_kg_m2
        )
    return zpe, e_vib, s_vib


def electronic_entropy(spin_multiplicity: int) -> float:
    """Return S_elec = R ln(2S + 1) in J/(mol K)."""
    return R_GAS * math.log(spin_multiplicity)


def standard_state_correction(config: ThermoConfig) -> float:
    """Return RT ln(c k T / p) in J/mol: the ideal gas at p moved to concentration c.

    c = ``standard_state_mol_l`` x 1000 x N_A molecules/m^3 and p = ``pressure_atm`` x 101325 Pa.
    """
    t = config.temperature_k
    c = config.standard_state_mol_l * 1000.0 * N_AVOGADRO
    p = config.pressure_atm * ATM_PA
    return R_GAS * t * math.log(c * K_BOLTZMANN * t / p)


def thermochemistry(
    state: MolecularState,
    hessian_hartree_per_bohr2: ArrayLike,
    electronic_energy_hartree: float,
    *,
    smiles: str,
    energy_source: Literal["optimization", "single_point"],
    config: ThermoConfig | None = None,
    analysis: ThermoAnalysisOptions | None = None,
) -> ThermoResult:
    """Return the quasi-RRHO thermochemistry of ``state`` from its Cartesian Hessian.

    Imaginary modes (below ``-analysis.imag_tol_cm1``) are excluded from ZPE, E_vib and S and
    listed; soft modes (``[-imag_tol, 0)``) enter with ``|nu|``. The result is returned either way:
    ``check_ground_state`` decides whether it is a minimum.

    Args:
        state: The stationary geometry (Angstrom), with charge and multiplicity.
        hessian_hartree_per_bohr2: Cartesian Hessian (Eh/Bohr^2), 3N x 3N; not modified.
        electronic_energy_hartree: E (Eh).
        smiles: SMILES whose ``AddHs`` atom order equals the state's (for sigma).
        energy_source: Where E comes from.
        config: Temperature, pressure, standard state and quasi-RRHO settings.
        analysis: Mode-classification and symmetry tolerances.

    Raises:
        ThermoInputError: If the Hessian, geometry or SMILES cannot be analysed.
    """
    config = config if config is not None else ThermoConfig()
    analysis = analysis if analysis is not None else ThermoAnalysisOptions()
    # The modes are analysed before sigma, as before the v0.5.0 refactor, so an input that fails
    # both checks still raises the normal-mode error first.
    normal_modes(state.symbols, state.coordinates, hessian_hartree_per_bohr2, analysis=analysis)
    sigma = rotational_symmetry_number(state, smiles, analysis=analysis)
    return _thermochemistry(
        state,
        hessian_hartree_per_bohr2,
        electronic_energy_hartree,
        sigma,
        energy_source=energy_source,
        config=config,
        analysis=analysis,
    )


def _thermochemistry(
    state: MolecularState,
    hessian_hartree_per_bohr2: ArrayLike,
    electronic_energy_hartree: float,
    sigma: int,
    *,
    energy_source: Literal["optimization", "single_point"],
    config: ThermoConfig,
    analysis: ThermoAnalysisOptions,
) -> ThermoResult:
    """Return the quasi-RRHO thermochemistry of ``state`` for a given symmetry number ``sigma``.

    The body of ``thermochemistry`` after sigma (v0.5.0 refactor): ``thermochemistry`` takes sigma
    from a SMILES, ``ts_thermochemistry`` from a bond graph. Imaginary modes (below
    ``-analysis.imag_tol_cm1``) are excluded and listed; soft modes enter with ``|nu|``.
    """
    t = config.temperature_k
    modes = normal_modes(
        state.symbols, state.coordinates, hessian_hartree_per_bohr2, analysis=analysis
    )
    masses = atomic_masses_amu(state.symbols)
    n = len(state.symbols)

    s_trans, e_trans = translational(float(masses.sum()) * AMU_KG, t, config.pressure_atm * ATM_PA)
    if n == 1:
        s_rot = e_rot = 0.0
    else:
        moments, _ = principal_axes(np.asarray(state.coordinates) * ANGSTROM_M, masses * AMU_KG)
        s_rot, e_rot = rotational(moments.tolist(), sigma, modes.is_linear, t)
    tol = analysis.imag_tol_cm1
    freqs = list(modes.frequencies_cm1)
    imaginary = [f for f in freqs if f < -tol]
    soft = [f for f in freqs if -tol <= f < 0]
    used = [abs(f) for f in freqs if f >= -tol]
    zpe, e_vib, s_vib = vibrational(used, config)
    s_elec = electronic_entropy(state.spin_multiplicity)
    ss = standard_state_correction(config)

    h_corr = zpe + e_trans + e_rot + e_vib + R_GAS * t
    s_total = s_trans + s_rot + s_vib + s_elec
    g_corr = h_corr - t * s_total + ss
    to_eh = J_PER_MOL_TO_HARTREE
    components = {
        "translational": s_trans * to_eh,
        "rotational": s_rot * to_eh,
        "vibrational": s_vib * to_eh,
        "electronic": s_elec * to_eh,
    }
    return ThermoResult(
        n_atoms=n,
        electronic_energy_hartree=electronic_energy_hartree,
        energy_source=energy_source,
        zpe_hartree=zpe * to_eh,
        thermal_correction_enthalpy_hartree=h_corr * to_eh,
        thermal_correction_gibbs_hartree=g_corr * to_eh,
        entropy_hartree_per_k=math.fsum(components.values()),
        entropy_components_hartree_per_k=components,
        gibbs_free_energy_hartree=electronic_energy_hartree + g_corr * to_eh,
        standard_state_correction_hartree=ss * to_eh,
        frequencies_cm1=freqs,
        imaginary_frequencies_cm1=imaginary,
        soft_modes_cm1=soft,
        rotational_symmetry_number=sigma,
        is_linear=modes.is_linear,
        config=config,
        analysis=analysis,
        masses_source=masses_source(),
    )
