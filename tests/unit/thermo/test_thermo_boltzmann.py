"""Tests for Boltzmann weights, ensemble G and the ground-state check (v0.3.0 slice 03, DV-12)."""

import math

import pytest
import thermo_geometries as g

from eta_rxncat.thermo import (
    NotAMinimumError,
    ThermoInputError,
    boltzmann,
    check_ground_state,
    thermochemistry,
)

RT_298 = 6.02214076e23 * 1.380649e-23 * 298.15 / (4.3597447222071e-18 * 6.02214076e23)  # Eh


def test_equal_g_with_degeneracies() -> None:
    """Equal G and g = (1, 2) give weights (1/3, 2/3) within 1e-15."""
    weights, _ = boltzmann([-76.4, -76.4], [1, 2], 298.15)
    assert abs(weights[0] - 1.0 / 3.0) <= 1e-15
    assert abs(weights[1] - 2.0 / 3.0) <= 1e-15


def test_ensemble_g_hand_checked() -> None:
    """G_ens = -RT ln sum g_i exp(-G_i/RT), written out for two conformers."""
    g_values = [-76.40, -76.399]
    weights, g_ens = boltzmann(g_values, [1, 2], 298.15)
    z = 1.0 * math.exp(0.0) + 2.0 * math.exp(-(g_values[1] - g_values[0]) / RT_298)
    expected = g_values[0] - RT_298 * math.log(z)
    assert g_ens == pytest.approx(expected, abs=1e-12)
    assert weights[0] == pytest.approx(1.0 / z, rel=1e-12)
    assert math.fsum(weights) == pytest.approx(1.0, abs=1e-15)
    assert g_ens <= min(g_values)


def test_huge_gap_does_not_overflow() -> None:
    """A 1000 kcal/mol gap gives finite weights (1, 0) and G_ens = G_min."""
    gap = 1000.0 / 627.5094740631
    weights, g_ens = boltzmann([-1.0, -1.0 + gap], [1, 1], 298.15)
    assert all(math.isfinite(w) for w in weights)
    assert weights == [1.0, 0.0]
    assert g_ens == pytest.approx(-1.0, abs=1e-15)


@pytest.mark.parametrize(
    ("gibbs", "degeneracies", "temperature", "fragment"),
    [
        ([], [], 298.15, "at least one"),
        ([-1.0, -2.0], [1], 298.15, "2 free energies but 1"),
        ([-1.0], [0], 298.15, "positive integers"),
        ([-1.0], [True], 298.15, "positive integers"),
        ([float("nan")], [1], 298.15, "non-finite"),
        ([-1.0], [1], 0.0, "temperature_k"),
    ],
)
def test_bad_inputs_rejected(
    gibbs: list[float], degeneracies: list[int], temperature: float, fragment: str
) -> None:
    """Empty input, length mismatch, bad degeneracies, NaN G and T <= 0 raise ThermoInputError."""
    with pytest.raises(ThermoInputError, match=fragment):
        boltzmann(gibbs, degeneracies, temperature)


def test_check_ground_state() -> None:
    """One imaginary mode raises NotAMinimumError naming it; a minimum passes."""
    st = g.water()
    saddle = thermochemistry(
        st,
        g.hessian_with_modes(st, [-300.0, 1600.0, 3700.0], linear=False),
        -76.4,
        smiles="O",
        energy_source="optimization",
    )
    with pytest.raises(NotAMinimumError) as info:
        check_ground_state(saddle)
    assert info.value.imaginary_cm1 == pytest.approx((-300.0,), abs=1e-6)
    assert "-300.00" in str(info.value)
    minimum = thermochemistry(
        st,
        g.hessian_with_modes(st, [1600.0, 3700.0, 3800.0], linear=False),
        -76.4,
        smiles="O",
        energy_source="optimization",
    )
    check_ground_state(minimum)


def test_soft_mode_is_not_imaginary() -> None:
    """A -5 cm^-1 mode is soft, not imaginary, so the ground-state check passes."""
    st = g.water()
    result = thermochemistry(
        st,
        g.hessian_with_modes(st, [-5.0, 1600.0, 3700.0], linear=False),
        -76.4,
        smiles="O",
        energy_source="optimization",
    )
    assert result.soft_modes_cm1 == pytest.approx([-5.0], abs=1e-6)
    check_ground_state(result)
