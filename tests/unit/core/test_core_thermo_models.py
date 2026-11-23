"""Tests for ThermoAnalysisOptions and ThermoResult (v0.3.0 slice 02)."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import ThermoAnalysisOptions, ThermoConfig, ThermoResult

COMPONENTS = {
    "translational": 5.0e-5,
    "rotational": 3.0e-5,
    "vibrational": 1.0e-6,
    "electronic": 0.0,
}
TOTAL_S = 5.0e-5 + 3.0e-5 + 1.0e-6 + 0.0


def thermo(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid non-linear N = 3 result, with overrides applied.

    Frequencies -25 (imaginary at the default 20 cm^-1 tolerance), -5 (soft) and 1600 cm^-1.
    """
    data: dict[str, Any] = {
        "n_atoms": 3,
        "electronic_energy_hartree": -76.4,
        "energy_source": "optimization",
        "zpe_hartree": 0.021,
        "thermal_correction_enthalpy_hartree": 0.025,
        "thermal_correction_gibbs_hartree": 0.004,
        "entropy_hartree_per_k": TOTAL_S,
        "entropy_components_hartree_per_k": dict(COMPONENTS),
        "gibbs_free_energy_hartree": -76.4 + 0.004,
        "standard_state_correction_hartree": 0.003,
        "frequencies_cm1": [-25.0, -5.0, 1600.0],
        "imaginary_frequencies_cm1": [-25.0],
        "soft_modes_cm1": [-5.0],
        "rotational_symmetry_number": 2,
        "is_linear": False,
        "config": ThermoConfig(),
        "analysis": ThermoAnalysisOptions(),
        "masses_source": "rdkit 2026.09.2 most abundant isotope",
    }
    data.update(overrides)
    return data


def rejected(fragment: str, **overrides: Any) -> None:
    """Assert that ``overrides`` fail validation with a message containing ``fragment``."""
    with pytest.raises(ValidationError) as info:
        ThermoResult(**thermo(**overrides))
    assert fragment in str(info.value), str(info.value)


def test_analysis_defaults() -> None:
    """ThermoAnalysisOptions carries the mission's default tolerances."""
    options = ThermoAnalysisOptions()
    assert options.imag_tol_cm1 == 20.0
    assert options.sym_tol_angstrom == 0.05
    assert options.linear_tol_angstrom == 1e-3
    assert options.max_automorphisms == 100000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("imag_tol_cm1", 0.0),
        ("sym_tol_angstrom", -0.1),
        ("linear_tol_angstrom", float("nan")),
        ("max_automorphisms", 0),
        ("max_automorphisms", True),
        ("max_automorphisms", 10.0),
    ],
)
def test_analysis_rejects(field: str, value: object) -> None:
    """Non-positive, non-finite and non-strict-int tolerances are rejected."""
    with pytest.raises(ValidationError):
        ThermoAnalysisOptions(**{field: value})


def test_valid_result_round_trips() -> None:
    """A valid result constructs and round-trips through model_dump / model_validate."""
    value = ThermoResult(**thermo())
    assert ThermoResult.model_validate(value.model_dump()) == value


def test_missing_entropy_key_rejected() -> None:
    """All four entropy components are required."""
    components = dict(COMPONENTS)
    del components["electronic"]
    rejected("missing ['electronic']", entropy_components_hartree_per_k=components)


def test_unknown_entropy_key_rejected() -> None:
    """Only the four named components are allowed."""
    rejected(
        "entropy_components_hartree_per_k",
        entropy_components_hartree_per_k={
            **COMPONENTS,
            "conformational": 0.0,
        },
    )


def test_entropy_sum_within_tolerance_passes() -> None:
    """A total within 1e-12 relative of the component sum passes."""
    ThermoResult(**thermo(entropy_hartree_per_k=TOTAL_S * (1 + 5e-13)))


def test_entropy_sum_mismatch_rejected() -> None:
    """A total off by more than 1e-12 relative is rejected."""
    rejected("entropy components sum", entropy_hartree_per_k=TOTAL_S * (1 + 1e-9))


def test_entropy_absolute_floor() -> None:
    """With all-zero entropy the 1e-30 absolute floor applies."""
    zero = dict.fromkeys(COMPONENTS, 0.0)
    ThermoResult(**thermo(entropy_hartree_per_k=5e-31, entropy_components_hartree_per_k=zero))
    rejected(
        "entropy components sum",
        entropy_hartree_per_k=1e-29,
        entropy_components_hartree_per_k=zero,
    )


def test_single_atom_has_no_frequencies() -> None:
    """N = 1: zero frequencies passes; one frequency, or is_linear, is rejected."""
    atom = {
        "n_atoms": 1,
        "frequencies_cm1": [],
        "imaginary_frequencies_cm1": [],
        "soft_modes_cm1": [],
        "rotational_symmetry_number": 1,
    }
    ThermoResult(**thermo(**atom))
    rejected("expected 0", **{**atom, "frequencies_cm1": [100.0]})
    rejected("single atom is not linear", **{**atom, "is_linear": True})


def test_diatomic_must_be_linear() -> None:
    """N = 2: linear with one frequency passes; non-linear is rejected."""
    diatomic = {
        "n_atoms": 2,
        "frequencies_cm1": [2100.0],
        "imaginary_frequencies_cm1": [],
        "soft_modes_cm1": [],
        "is_linear": True,
    }
    ThermoResult(**thermo(**diatomic))
    rejected("diatomic must be linear", **{**diatomic, "is_linear": False})


def test_linear_triatomic_has_3n_minus_5() -> None:
    """A linear N = 3 molecule needs 4 frequencies; 3 (the non-linear count) is rejected."""
    linear = {
        "is_linear": True,
        "frequencies_cm1": [-25.0, -5.0, 600.0, 1600.0],
    }
    ThermoResult(**thermo(**linear))
    rejected("expected 4", **{**linear, "frequencies_cm1": [-25.0, -5.0, 1600.0]})


def test_nonlinear_count_3n_minus_6() -> None:
    """A non-linear N = 3 molecule with 4 frequencies (the linear count) is rejected."""
    rejected("expected 3", frequencies_cm1=[-25.0, -5.0, 600.0, 1600.0])


def test_frequencies_must_ascend() -> None:
    """Frequencies out of order are rejected."""
    rejected(
        "not ascending",
        frequencies_cm1=[-25.0, 1600.0, -5.0],
    )


def test_imaginary_must_equal_frequencies_below_tolerance() -> None:
    """The imaginary list must be exactly the frequencies below -imag_tol."""
    rejected("imaginary_frequencies_cm1", imaginary_frequencies_cm1=[])
    rejected("imaginary_frequencies_cm1", imaginary_frequencies_cm1=[-25.0, -5.0])


def test_soft_modes_must_equal_window() -> None:
    """The soft list must be exactly the frequencies in [-imag_tol, 0)."""
    rejected("soft_modes_cm1", soft_modes_cm1=[])
    rejected("soft_modes_cm1", soft_modes_cm1=[-25.0, -5.0])


def test_tolerance_boundary_is_soft() -> None:
    """A frequency of exactly -imag_tol is a soft mode, not an imaginary one."""
    ThermoResult(
        **thermo(
            frequencies_cm1=[-20.0, -5.0, 1600.0],
            imaginary_frequencies_cm1=[],
            soft_modes_cm1=[-20.0, -5.0],
        )
    )


def test_classification_follows_analysis_tolerance() -> None:
    """With imag_tol 2 cm^-1, -5 becomes imaginary."""
    ThermoResult(
        **thermo(
            analysis=ThermoAnalysisOptions(imag_tol_cm1=2.0),
            imaginary_frequencies_cm1=[-25.0, -5.0],
            soft_modes_cm1=[],
        )
    )


def test_gibbs_must_equal_e_plus_correction() -> None:
    """G = E + thermal_correction_gibbs within 1e-12 Eh."""
    ThermoResult(**thermo(gibbs_free_energy_hartree=-76.4 + 0.004 + 5e-13))
    rejected("gibbs_free_energy_hartree", gibbs_free_energy_hartree=-76.4 + 0.004 + 1e-9)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_atoms", 0),
        ("n_atoms", True),
        ("energy_source", "frequency"),
        ("zpe_hartree", float("inf")),
        ("rotational_symmetry_number", 0),
        ("masses_source", ""),
    ],
)
def test_field_types_rejected(field: str, value: object) -> None:
    """Field-level types: positive strict ints, the energy-source literal, finite floats."""
    with pytest.raises(ValidationError):
        ThermoResult(**thermo(**{field: value}))


def test_single_point_energy_source_accepted() -> None:
    """energy_source may be single_point."""
    assert ThermoResult(**thermo(energy_source="single_point")).energy_source == "single_point"


def test_no_ground_state_flag() -> None:
    """ThermoResult has no ground-state boolean field."""
    assert not [
        name
        for name, info in ThermoResult.model_fields.items()
        if info.annotation is bool and name != "is_linear"
    ]


@pytest.mark.parametrize(
    ("cls", "kwargs", "field"),
    [
        (ThermoAnalysisOptions, {}, "imag_tol_cm1"),
        (ThermoResult, thermo(), "n_atoms"),
    ],
)
def test_frozen_and_extra_forbidden(cls: type, kwargs: dict[str, Any], field: str) -> None:
    """Both models are frozen (assignment raises) and reject unknown fields."""
    value = cls(**kwargs)
    with pytest.raises(ValidationError):
        setattr(value, field, getattr(value, field))
    with pytest.raises(ValidationError):
        cls(**kwargs, unexpected=1)
