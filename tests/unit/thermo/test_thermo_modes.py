"""Tests for eta_rxncat.thermo.normal_modes (v0.3.0 slice 03, DV-06, DV-07, DV-23)."""

import copy
import math

import numpy as np
import pytest
import thermo_geometries as g
from scipy.spatial.transform import Rotation

from eta_rxncat.core import PotentialResult, ThermoAnalysisOptions
from eta_rxncat.thermo import ThermoInputError, atomic_masses_amu, normal_modes

ANALYSIS = ThermoAnalysisOptions()

# CODATA 2018, written out for the analytic diatomic.
HARTREE_J = 4.3597447222071e-18
BOHR_M = 0.529177210903e-10
AMU_KG = 1.66053906660e-27
C_CM = 299792458.0 * 100.0


def test_diatomic_spring_frequency() -> None:
    """A CO spring of k Eh/Bohr^2 gives one mode sqrt(k/mu)/(2 pi c), 1e-6 relative."""
    k = 1.2
    st = g.state(["C", "O"], [[0.0, 0.0, 0.0], [1.128, 0.0, 0.0]])
    hessian = np.zeros((6, 6))
    hessian[0, 0] = hessian[3, 3] = k
    hessian[0, 3] = hessian[3, 0] = -k
    m1, m2 = atomic_masses_amu(st.symbols)
    mu = m1 * m2 / (m1 + m2)
    expected = math.sqrt(k * HARTREE_J / BOHR_M**2 / (mu * AMU_KG)) / (2.0 * math.pi * C_CM)
    modes = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert modes.is_linear
    assert len(modes.frequencies_cm1) == 1
    assert math.isclose(modes.frequencies_cm1[0], expected, rel_tol=1e-6)


def test_linear_triatomic_has_3n_minus_5_modes() -> None:
    """CO2 with four chosen modes returns exactly those four (3N-5)."""
    st = g.co2()
    chosen = [667.0, 667.5, 1333.0, 2349.0]
    hessian = g.hessian_with_modes(st, chosen, linear=True)
    modes = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert modes.is_linear
    assert modes.frequencies_cm1 == pytest.approx(chosen, abs=1e-6)
    assert modes.modes_cartesian.shape == (9, 4)


def test_nonlinear_toy_hessian_recovers_chosen_modes() -> None:
    """Water with modes (-150, -5, 1600, 3700, 3800) minus one: 3N-6 = 3 recovered, ascending."""
    st = g.water()
    chosen = [-150.0, 1600.0, 3700.0]
    modes = normal_modes(
        st.symbols,
        st.coordinates,
        g.hessian_with_modes(st, chosen, linear=False),
        analysis=ANALYSIS,
    )
    assert not modes.is_linear
    assert modes.frequencies_cm1 == pytest.approx(chosen, abs=1e-6)
    assert list(modes.frequencies_cm1) == sorted(modes.frequencies_cm1)


def test_mode_vectors_are_unit_cartesian_displacements() -> None:
    """Each column is a unit-length Cartesian displacement with no centre-of-mass motion."""
    st = g.water()
    modes = normal_modes(
        st.symbols,
        st.coordinates,
        g.hessian_with_modes(st, [1600.0, 3700.0, 3800.0], linear=False),
        analysis=ANALYSIS,
    )
    masses = atomic_masses_amu(st.symbols)
    for k in range(3):
        column = modes.modes_cartesian[:, k]
        assert np.linalg.norm(column) == pytest.approx(1.0, abs=1e-12)
        com_shift = (masses[:, None] * column.reshape(3, 3)).sum(axis=0)
        assert np.abs(com_shift).max() < 1e-10


def test_rigid_rotation_leaves_frequencies_unchanged() -> None:
    """Rotating geometry and Hessian rigidly changes no frequency by more than 1e-6 cm^-1."""
    st = g.butane(60.0)
    chosen = sorted(np.random.default_rng(3).uniform(-200.0, 3200.0, 3 * 14 - 6).tolist())
    hessian = g.hessian_with_modes(st, chosen, linear=False)
    before = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    rot = Rotation.from_euler("zyx", [0.7, -1.1, 2.3]).as_matrix()
    big = np.kron(np.eye(14), rot)
    rotated = g.state(st.symbols, np.asarray(st.coordinates) @ rot.T)
    after = normal_modes(st.symbols, rotated.coordinates, big @ hessian @ big.T, analysis=ANALYSIS)
    diff = np.abs(np.array(before.frequencies_cm1) - np.array(after.frequencies_cm1))
    assert diff.max() <= 1e-6
    assert before.frequencies_cm1 == pytest.approx(chosen, abs=1e-6)


def test_bent_co2_within_tolerance_is_linear() -> None:
    """CO2 with one O bent 1e-4 Angstrom is linear at linear_tol 1e-3 Angstrom (R9)."""
    st = g.co2(bend=1e-4)
    hessian = g.hessian_with_modes(g.co2(), [667.0, 667.5, 1333.0, 2349.0], linear=True)
    modes = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert modes.is_linear
    assert len(modes.frequencies_cm1) == 4


def test_bent_co2_beyond_tolerance_is_not_linear() -> None:
    """Bent by 0.01 Angstrom, CO2 is non-linear and has 3N-6 = 3 modes."""
    st = g.co2(bend=1e-2)
    hessian = g.hessian_with_modes(st, [600.0, 1333.0, 2349.0], linear=False)
    modes = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert not modes.is_linear
    assert modes.frequencies_cm1 == pytest.approx([600.0, 1333.0, 2349.0], abs=1e-6)


def test_single_atom_has_no_modes() -> None:
    """N = 1 gives zero modes and is not linear."""
    modes = normal_modes(["Ar"], [[0.0, 0.0, 0.0]], np.zeros((3, 3)), analysis=ANALYSIS)
    assert modes.frequencies_cm1 == ()
    assert not modes.is_linear
    assert modes.n_atoms == 1


def test_input_hessian_is_not_modified() -> None:
    """The caller's array (asymmetric on purpose) is unchanged after the call."""
    st = g.water()
    hessian = g.hessian_with_modes(st, [1600.0, 3700.0, 3800.0], linear=False)
    hessian[0, 1] += 1e-9
    original = hessian.copy()
    normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert np.array_equal(hessian, original)


def test_potential_result_hessian_is_not_modified() -> None:
    """DV-23: a PotentialResult's Hessian lists are unchanged after normal_modes."""
    st = g.water()
    matrix = g.hessian_with_modes(st, [1600.0, 3700.0, 3800.0], linear=False).tolist()
    result = PotentialResult(
        energy_hartree=-76.4,
        hessian_hartree_per_bohr2=matrix,
        hessian_method="analytic",
        hessian_max_asymmetry=0.0,
        engine={"name": "xtb_subprocess", "version": "6.8.0"},
        stage_engine_impl=1,
        device="cpu",
        wall_time_s=0.1,
    )
    snapshot = copy.deepcopy(result.hessian_hartree_per_bohr2)
    assert result.hessian_hartree_per_bohr2 is not None
    normal_modes(st.symbols, st.coordinates, result.hessian_hartree_per_bohr2, analysis=ANALYSIS)
    assert result.hessian_hartree_per_bohr2 == snapshot


def test_near_zero_mode_is_an_error() -> None:
    """|nu| < 1e-3 cm^-1 raises instead of being dropped (R15, DV-07)."""
    st = g.water()
    hessian = g.hessian_with_modes(st, [1e-4, 3700.0, 3800.0], linear=False)
    with pytest.raises(ThermoInputError, match="1e-03|0.001"):
        normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)


def test_small_real_modes_are_kept() -> None:
    """A 2 cm^-1 mode is returned, not dropped (DV-06/DV-07)."""
    st = g.water()
    hessian = g.hessian_with_modes(st, [-8.0, 2.0, 3800.0], linear=False)
    modes = normal_modes(st.symbols, st.coordinates, hessian, analysis=ANALYSIS)
    assert modes.frequencies_cm1 == pytest.approx([-8.0, 2.0, 3800.0], abs=1e-6)


@pytest.mark.parametrize(
    ("coords", "hessian", "fragment"),
    [
        ([[0.0, 0.0, 0.0]] * 2, np.zeros((9, 9)), "coordinates shape"),
        ([[0.0, 0.0, 0.0]] * 3, np.zeros((6, 6)), "Hessian shape"),
        ([[0.0, 0.0, 0.0]] * 3, np.full((9, 9), np.nan), "non-finite"),
    ],
)
def test_bad_inputs_rejected(coords: list[list[float]], hessian: np.ndarray, fragment: str) -> None:
    """Shape mismatches and non-finite Hessians raise ThermoInputError."""
    with pytest.raises(ThermoInputError, match=fragment):
        normal_modes(["O", "H", "H"], coords, hessian, analysis=ANALYSIS)
