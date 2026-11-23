"""Tier-D closed-form tests for quasi-RRHO thermochemistry (v0.3.0 slice 03, DV-03, DV-04, R15).

The expected values are written out independently here, from CODATA 2018 and the formulas of the
mission's Algorithms section, rather than by calling the helpers under test.
"""

import math

import numpy as np
import pytest
import thermo_geometries as g

from eta_rxncat.core import ThermoAnalysisOptions, ThermoConfig
from eta_rxncat.thermo import atomic_masses_amu, thermochemistry
from eta_rxncat.thermo.rrho import (
    electronic_entropy,
    grimme_weight,
    rotational,
    standard_state_correction,
    translational,
)

H = 6.62607015e-34
KB = 1.380649e-23
NA = 6.02214076e23
C_CM = 299792458.0 * 100.0
R = NA * KB
AMU = 1.66053906660e-27
EH = 4.3597447222071e-18
T = 298.15
P = 101325.0
TO_EH = 1.0 / (EH * NA)


def closed_form(
    symbols: list[str],
    coords: list[list[float]],
    used_cm1: list[float],
    sigma: int,
    linear: bool,
    mult: int,
    config: ThermoConfig,
) -> dict[str, float]:
    """Return every term in J/mol or J/(mol K), computed directly from the formulas."""
    t = config.temperature_k
    p = config.pressure_atm * P
    masses = atomic_masses_amu(symbols)
    m = masses.sum() * AMU
    kt = KB * t
    s_trans = R * (math.log((2 * math.pi * m * kt / H**2) ** 1.5 * kt / p) + 2.5)
    e_trans = 1.5 * R * t
    xyz = np.asarray(coords) * 1e-10
    mk = masses * AMU
    com = (mk[:, None] * xyz).sum(axis=0) / mk.sum()
    r = xyz - com
    tensor = sum(
        mi * (ri @ ri * np.eye(3) - np.outer(ri, ri)) for mi, ri in zip(mk, r, strict=True)
    )
    moments = np.linalg.eigvalsh(tensor)
    if len(symbols) == 1:
        s_rot = e_rot = 0.0
    elif linear:
        s_rot = R * (math.log(8 * math.pi**2 * moments.max() * kt / (sigma * H**2)) + 1)
        e_rot = R * t
    else:
        q = (
            math.sqrt(math.pi)
            / sigma
            * (8 * math.pi**2 * kt / H**2) ** 1.5
            * math.sqrt(moments.prod())
        )
        s_rot = R * (math.log(q) + 1.5)
        e_rot = 1.5 * R * t
    zpe = e_vib = s_vib = 0.0
    for nu in used_cm1:
        theta = H * C_CM * nu / KB
        x = theta / t
        zpe += 0.5 * R * theta
        e_vib += R * theta / (math.exp(x) - 1)
        s_rrho = R * (x / (math.exp(x) - 1) - math.log(1 - math.exp(-x)))
        mu = H / (8 * math.pi**2 * C_CM * nu)
        b_av = config.qrrho_rotor_moment_kg_m2
        mu_p = mu * b_av / (mu + b_av)
        s_r = R * (0.5 + math.log(math.sqrt(8 * math.pi**3 * mu_p * kt / H**2)))
        w = 1 / (1 + (config.qrrho_cutoff_cm1 / nu) ** config.qrrho_alpha)
        s_vib += w * s_rrho + (1 - w) * s_r
    s_elec = R * math.log(mult)
    c0 = config.standard_state_mol_l * 1000 * NA
    ss = R * t * math.log(c0 * kt / p)
    return {
        "s_trans": s_trans,
        "s_rot": s_rot,
        "s_vib": s_vib,
        "s_elec": s_elec,
        "e_trans": e_trans,
        "e_rot": e_rot,
        "zpe": zpe,
        "e_vib": e_vib,
        "ss": ss,
    }


def test_standard_state_term() -> None:
    """RT ln(24.4654) = 1.8943 kcal/mol at 298.15 K, 1 atm -> 1 M."""
    value = standard_state_correction(ThermoConfig()) / 4184.0
    assert value == pytest.approx(1.8943, abs=1e-4)
    assert value == pytest.approx(R * T * math.log(24.4654) / 4184.0, abs=1e-4)


def test_grimme_weight_is_half_at_cutoff() -> None:
    """The Grimme weight is 0.5 at nu = omega_0, for any alpha."""
    assert grimme_weight(100.0, 100.0, 4.0) == 0.5
    assert grimme_weight(37.0, 37.0, 2.0) == 0.5


def test_linear_translation_plus_rotation_is_five_halves_rt() -> None:
    """E_trans + E_rot = 5/2 RT for a linear molecule, 3 RT for a non-linear one (DV-04)."""
    _, e_trans = translational(44.0 * AMU, T, P)
    _, e_rot_linear = rotational([0.0, 7.1e-46, 7.1e-46], 2, True, T)
    _, e_rot_bent = rotational([1e-47, 2e-47, 3e-47], 2, False, T)
    assert e_trans + e_rot_linear == pytest.approx(2.5 * R * T, rel=1e-12)
    assert e_trans + e_rot_bent == pytest.approx(3.0 * R * T, rel=1e-12)


def test_doublet_electronic_entropy() -> None:
    """S_elec = R ln 2 for a doublet, 0 for a singlet."""
    assert electronic_entropy(2) == pytest.approx(R * math.log(2), rel=1e-15)
    assert electronic_entropy(1) == 0.0


def check_against_closed_form(
    st: g.MolecularState,
    smiles: str,
    chosen: list[float],
    sigma: int,
    linear: bool,
    config: ThermoConfig,
) -> None:
    """Run thermochemistry on a toy Hessian with ``chosen`` modes and compare every term."""
    energy = -76.4
    result = thermochemistry(
        st,
        g.hessian_with_modes(st, chosen, linear=linear),
        energy,
        smiles=smiles,
        energy_source="optimization",
        config=config,
    )
    tol = ThermoAnalysisOptions().imag_tol_cm1
    used = [abs(f) for f in chosen if f >= -tol]
    exp = closed_form(st.symbols, st.coordinates, used, sigma, linear, st.spin_multiplicity, config)
    assert result.rotational_symmetry_number == sigma
    assert result.is_linear is linear
    comps = result.entropy_components_hartree_per_k
    for key, name in [
        ("translational", "s_trans"),
        ("rotational", "s_rot"),
        ("vibrational", "s_vib"),
        ("electronic", "s_elec"),
    ]:
        assert comps[key] == pytest.approx(exp[name] * TO_EH, rel=1e-9, abs=1e-30), key
    assert result.zpe_hartree == pytest.approx(exp["zpe"] * TO_EH, rel=1e-9)
    assert result.standard_state_correction_hartree == pytest.approx(exp["ss"] * TO_EH, rel=1e-9)
    t = config.temperature_k
    h_corr = (exp["zpe"] + exp["e_trans"] + exp["e_rot"] + exp["e_vib"] + R * t) * TO_EH
    assert result.thermal_correction_enthalpy_hartree == pytest.approx(h_corr, abs=1e-12)
    s_total = (exp["s_trans"] + exp["s_rot"] + exp["s_vib"] + exp["s_elec"]) * TO_EH
    assert result.entropy_hartree_per_k == pytest.approx(s_total, rel=1e-9)
    assert math.fsum(comps.values()) == pytest.approx(result.entropy_hartree_per_k, rel=1e-12)
    g_corr = h_corr - t * s_total + exp["ss"] * TO_EH
    assert result.thermal_correction_gibbs_hartree == pytest.approx(g_corr, abs=1e-12)
    assert result.gibbs_free_energy_hartree == pytest.approx(energy + g_corr, abs=1e-12)
    assert result.electronic_energy_hartree == energy


def test_water_with_soft_mode_matches_closed_form() -> None:
    """Water, modes (-5 soft, 50, 3700): every term equals its closed form; -5 enters as 5."""
    check_against_closed_form(g.water(), "O", [-5.0, 50.0, 3700.0], 2, False, ThermoConfig())


def test_doublet_diatomic_matches_closed_form() -> None:
    """OH radical (doublet, linear, sigma 1): rotation RT, S_elec = R ln 2."""
    st = g.state(["O", "H"], [[0.0, 0.0, 0.0], [0.97, 0.0, 0.0]], mult=2)
    check_against_closed_form(st, "[OH]", [3700.0], 1, True, ThermoConfig())


def test_linear_triatomic_matches_closed_form() -> None:
    """CO2 (sigma 2) at 350 K and 2 M."""
    config = ThermoConfig(temperature_k=350.0, standard_state_mol_l=2.0)
    check_against_closed_form(g.co2(), "O=C=O", [667.0, 667.5, 1333.0, 2349.0], 2, True, config)


def test_imaginary_mode_excluded_and_listed() -> None:
    """A -300 cm^-1 mode is listed and excluded from ZPE, E_vib and S; the result is returned."""
    st = g.water()
    check_against_closed_form(st, "O", [-300.0, 1600.0, 3700.0], 2, False, ThermoConfig())
    result = thermochemistry(
        st,
        g.hessian_with_modes(st, [-300.0, 1600.0, 3700.0], linear=False),
        -76.4,
        smiles="O",
        energy_source="single_point",
    )
    assert result.imaginary_frequencies_cm1 == pytest.approx([-300.0], abs=1e-6)
    assert result.soft_modes_cm1 == []
    assert result.energy_source == "single_point"


def test_single_atom() -> None:
    """An argon atom: no modes, no rotation, translational entropy only (plus S_elec = 0)."""
    st = g.state(["Ar"], [[0.0, 0.0, 0.0]])
    result = thermochemistry(
        st, np.zeros((3, 3)), -527.5, smiles="[Ar]", energy_source="optimization"
    )
    assert result.frequencies_cm1 == []
    assert result.entropy_components_hartree_per_k["rotational"] == 0.0
    assert result.entropy_components_hartree_per_k["vibrational"] == 0.0
    exp = closed_form(["Ar"], [[0.0, 0.0, 0.0]], [], 1, False, 1, ThermoConfig())
    h_corr = (exp["e_trans"] + R * T) * TO_EH
    assert result.thermal_correction_enthalpy_hartree == pytest.approx(h_corr, abs=1e-12)


def test_masses_source_recorded() -> None:
    """The result records where the masses came from."""
    st = g.water()
    result = thermochemistry(
        st,
        g.hessian_with_modes(st, [1600.0, 3700.0, 3800.0], linear=False),
        -76.4,
        smiles="O",
        energy_source="optimization",
    )
    assert result.masses_source.startswith("rdkit ")


def test_rotor_moment_changes_only_soft_mode_entropy() -> None:
    """B_av enters only the free-rotor term: a larger B_av raises S for a 20 cm^-1 mode."""
    st = g.water()
    hessian = g.hessian_with_modes(st, [20.0, 1600.0, 3700.0], linear=False)
    small = thermochemistry(st, hessian, -76.4, smiles="O", energy_source="optimization")
    large = thermochemistry(
        st,
        hessian,
        -76.4,
        smiles="O",
        energy_source="optimization",
        config=ThermoConfig(qrrho_rotor_moment_kg_m2=1e-43),
    )
    assert (
        large.entropy_components_hartree_per_k["vibrational"]
        > small.entropy_components_hartree_per_k["vibrational"]
    )
    assert large.zpe_hartree == small.zpe_hartree
