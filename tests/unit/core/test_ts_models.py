"""Tests for the v0.5.0 TS contracts, the "prfo" optimizer name and the "ts_opt" stage kind."""

import json
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from eta_rxncat.core import (
    TS_VALIDATION_REASONS,
    FormingBond,
    MolecularState,
    OptimizerIdentity,
    StageConfig,
    StageKind,
    ThermoAnalysisOptions,
    ThermoConfig,
    ThermoResult,
    TransitionStateRecord,
    TSSearchResult,
    TSStep,
    TSValidation,
    TSValidationOptions,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def water() -> MolecularState:
    """Return a neutral singlet water molecule with atom 0 active."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0],
    )


def step(k: int, **overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid TSStep labelled ``k``."""
    data: dict[str, Any] = {
        "step": k,
        "accepted_bool": True,
        "energy_hartree": -76.3 - 0.001 * k,
        "max_gradient_hartree_per_bohr": 0.01,
        "trust_radius_bohr": 0.1,
        "followed_eigenvalue_hartree_per_bohr2": -0.05,
        "mode_overlap": None if k == 0 else 0.98,
        "hessian_source": "exact" if k == 0 else "bofill",
        "ratio": None if k == 0 else 0.9,
    }
    data.update(overrides)
    return data


def search(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid TSSearchResult, with overrides applied."""
    data: dict[str, Any] = {
        "final_state": water(),
        "final_energy_hartree": -76.3,
        "converged": True,
        "n_steps": 2,
        "n_gradient_calls": 3,
        "n_hessian_calls": 1,
        "n_hessian_refreshes": 0,
        "n_rejected_steps": 0,
        "hessian_method": "analytic",
        "followed_eigenvalue_hartree_per_bohr2": -0.05,
        "final_max_gradient_hartree_per_bohr": 1e-4,
        "final_rms_gradient_hartree_per_bohr": 5e-5,
        "final_rigid_gradient_norm_hartree_per_bohr": 1e-9,
        "forming_bonds": [FormingBond(i=0, j=1), FormingBond(i=0, j=2)],
        "optimizer": OptimizerIdentity(name="prfo", version="src-0123456789abcdef"),
        "options": {"max_steps": 100, "trust_radius_bohr": 0.1},
        "history": [TSStep(**step(0)), TSStep(**step(1))],
    }
    data.update(overrides)
    return data


def validation(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a passing TSValidation, with overrides applied."""
    data: dict[str, Any] = {
        "n_imaginary": 1,
        "imaginary_frequency_cm1": -400.0,
        "active_core_ke_fraction": 0.8,
        "forming_stretch_overlap": 0.7,
        "forming_bonds_in_phase_bool": True,
        "forming_distances_angstrom": {"0-1": 2.2, "0-2": 2.3},
        "options": TSValidationOptions(),
        "active_atom_indices": [0, 1],
        "mode_count_passed_bool": True,
        "active_core_passed_bool": True,
        "identity_passed_bool": True,
        "passed_bool": True,
        "reasons": [],
    }
    data.update(overrides)
    return data


def failing(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a TSValidation that failed on the active core only."""
    data = validation(
        active_core_ke_fraction=0.4,
        active_core_passed_bool=False,
        passed_bool=False,
        reasons=["active_core_fraction_below_threshold"],
    )
    data.update(overrides)
    return data


def ts_thermo(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid N = 3 ThermoResult with one imaginary mode."""
    components = {"translational": 5.0e-5, "rotational": 3.0e-5, "vibrational": 1.0e-6}
    components["electronic"] = 0.0
    data: dict[str, Any] = {
        "n_atoms": 3,
        "electronic_energy_hartree": -76.3,
        "energy_source": "optimization",
        "zpe_hartree": 0.015,
        "thermal_correction_enthalpy_hartree": 0.018,
        "thermal_correction_gibbs_hartree": 0.002,
        "entropy_hartree_per_k": sum(components.values()),
        "entropy_components_hartree_per_k": components,
        "gibbs_free_energy_hartree": -76.3 + 0.002,
        "standard_state_correction_hartree": 0.003,
        "frequencies_cm1": [-400.0, 500.0, 1600.0],
        "imaginary_frequencies_cm1": [-400.0],
        "soft_modes_cm1": [],
        "rotational_symmetry_number": 2,
        "is_linear": False,
        "config": ThermoConfig(),
        "analysis": ThermoAnalysisOptions(),
        "masses_source": "eta_rxncat.thermo.masses",
    }
    data.update(overrides)
    return data


def record(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid TransitionStateRecord, with overrides applied."""
    data: dict[str, Any] = {
        "ts_id": "TS1",
        "state": water(),
        "search": TSSearchResult(**search()),
        "validation": TSValidation(**validation()),
        "thermo": ThermoResult(**ts_thermo()),
        "degeneracy": 1,
    }
    data.update(overrides)
    return data


def rejected(cls: type[BaseModel], kwargs: dict[str, Any], fragment: str) -> None:
    """Assert that ``cls(**kwargs)`` fails validation with a message containing ``fragment``."""
    with pytest.raises(ValidationError) as info:
        cls(**kwargs)
    assert fragment in str(info.value), str(info.value)


# --- OptimizerIdentity and StageKind (additive widenings) ---


def test_prfo_identity_validates() -> None:
    """The P-RFO optimizer name is accepted (mini-requirement 1)."""
    identity = OptimizerIdentity(name="prfo", version="src-0123456789abcdef")
    assert identity.name == "prfo"


@pytest.mark.parametrize("name", ["sella", "PRFO", "pysisyphus", ""])
def test_other_identity_names_rejected(name: str) -> None:
    """Only "geometric" and "prfo" are optimizer names."""
    with pytest.raises(ValidationError):
        OptimizerIdentity(name=name, version="1.0")


def test_ts_opt_stage_kind() -> None:
    """StageConfig accepts "ts_opt", and every earlier stage kind still validates."""
    kinds = get_args(StageKind)
    assert kinds[-1] == "ts_opt"
    assert set(kinds) == {
        "conformer_search",
        "constrained_preopt",
        "geometry_opt",
        "frequency",
        "single_point",
        "ts_opt",
    }
    for kind in kinds:
        frozen = [0] if kind == "constrained_preopt" else []
        config = StageConfig(
            kind=kind, engine="xtb_subprocess", method="GFN2-xTB", frozen_atom_indices=frozen
        )
        assert config.kind == kind


def _optimizer_blocks(value: object) -> list[dict[str, Any]]:
    """Return every ``optimizer`` mapping nested anywhere in ``value``."""
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "optimizer" and isinstance(item, dict):
                found.append(item)
            else:
                found.extend(_optimizer_blocks(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_optimizer_blocks(item))
    return found


@pytest.mark.parametrize(("version", "expected_count"), [("v0.3.0", 0), ("v0.4.0", 2)])
def test_promoted_fixture_optimizer_blocks_validate(version: str, expected_count: int) -> None:
    """Every committed fixture optimizer block loads unchanged under the widened name.

    No v0.3.0 fixture carries an ``optimizer`` block (only ``environment.versions``); the counts
    are asserted so that a new fixture cannot slip past this check.
    """
    blocks = [
        block
        for path in sorted((FIXTURES / version).glob("*.json"))
        for block in _optimizer_blocks(json.loads(path.read_text(encoding="utf-8")))
    ]
    assert len(blocks) == expected_count
    for block in blocks:
        assert OptimizerIdentity.model_validate(block).model_dump(mode="json") == block


# --- FormingBond and TSStep ---


def test_forming_bond_order() -> None:
    """A forming bond needs i < j."""
    assert FormingBond(i=0, j=3).j == 3
    rejected(FormingBond, {"i": 2, "j": 1}, "i < j")
    rejected(FormingBond, {"i": 1, "j": 1}, "i < j")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("step", -1),
        ("step", True),
        ("energy_hartree", float("nan")),
        ("max_gradient_hartree_per_bohr", -1e-3),
        ("trust_radius_bohr", 0.0),
        ("mode_overlap", 1.2),
        ("mode_overlap", -0.1),
        ("hessian_source", "bfgs"),
        ("ratio", float("inf")),
    ],
)
def test_step_fields_rejected(field: str, value: object) -> None:
    """TSStep fields keep their types and ranges."""
    with pytest.raises(ValidationError):
        TSStep(**step(1, **{field: value}))


# --- TSSearchResult ---


def test_search_valid() -> None:
    """A valid search constructs, with its forming bonds and history kept in order."""
    result = TSSearchResult(**search())
    assert [(b.i, b.j) for b in result.forming_bonds] == [(0, 1), (0, 2)]
    assert [s.step for s in result.history] == [0, 1]


@pytest.mark.parametrize("value", [1, 1.0, False, "true"])
def test_search_converged_strict(value: object) -> None:
    """The converged flag must be the boolean True, not something equal to it."""
    rejected(TSSearchResult, search(converged=value), "converged must be True")


def test_search_history_labels() -> None:
    """history[k].step must equal k."""
    history = [TSStep(**step(0)), TSStep(**step(2))]
    rejected(TSSearchResult, search(history=history), "history positions [1]")


@pytest.mark.parametrize(
    ("bonds", "fragment"),
    [
        ([(0, 2), (0, 1)], "sorted by (i, j)"),
        ([(0, 1), (0, 1)], "sorted by (i, j)"),
        ([(0, 3)], "out of range for 3 atoms"),
    ],
)
def test_search_forming_bonds_rejected(bonds: list[tuple[int, int]], fragment: str) -> None:
    """forming_bonds are sorted, unique and in range."""
    forming = [FormingBond(i=i, j=j) for i, j in bonds]
    rejected(TSSearchResult, search(forming_bonds=forming), fragment)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n_rejected_steps", -1),
        ("n_hessian_calls", 1.0),
        ("hessian_method", "numerical"),
        ("final_rigid_gradient_norm_hartree_per_bohr", -1e-9),
        ("optimizer", {"name": "sella", "version": "2.3"}),
        ("options", {"nested": {"a": 1}}),
    ],
)
def test_search_fields_rejected(field: str, value: object) -> None:
    """Counts are strict non-negative ints; norms non-negative; options scalar."""
    with pytest.raises(ValidationError):
        TSSearchResult(**search(**{field: value}))


# --- TSValidationOptions ---


def test_validation_option_defaults() -> None:
    """The defaults are TJ's A2 numbers and the mission's R3 identity numbers."""
    options = TSValidationOptions()
    assert options.imag_tol_cm1 == 20.0
    assert options.cutoff_cm1 == -50.0
    assert options.min_active_core_ke_fraction == 0.60
    assert options.min_forming_stretch_overlap == 0.50
    assert options.forming_distance_min_angstrom == 1.90
    assert options.forming_distance_max_angstrom == 2.90


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"cutoff_cm1": -10.0}, "must be below -imag_tol_cm1"),
        ({"cutoff_cm1": -20.0}, "must be below -imag_tol_cm1"),
        ({"min_active_core_ke_fraction": 0.0}, "must be in (0, 1]"),
        ({"min_forming_stretch_overlap": 1.5}, "must be in (0, 1]"),
        ({"forming_distance_min_angstrom": 3.0}, "must be below forming_distance_max"),
        ({"imag_tol_cm1": 0.0}, "greater than 0"),
        ({"forming_distance_max_angstrom": -1.0}, "greater than 0"),
    ],
)
def test_validation_options_rejected(kwargs: dict[str, float], fragment: str) -> None:
    """Thresholds keep their order and ranges."""
    rejected(TSValidationOptions, kwargs, fragment)


# --- TSValidation ---


def test_validation_pass_and_fail_construct() -> None:
    """A passing and a failing validation both construct."""
    assert TSValidation(**validation()).passed_bool
    assert not TSValidation(**failing()).passed_bool


def test_validation_no_imaginary_mode() -> None:
    """With no imaginary mode the three numbers are None, and setting one is rejected."""
    none_found = failing(
        n_imaginary=0,
        imaginary_frequency_cm1=None,
        active_core_ke_fraction=None,
        forming_stretch_overlap=None,
        forming_bonds_in_phase_bool=None,
        mode_count_passed_bool=False,
        active_core_passed_bool=False,
        identity_passed_bool=False,
        reasons=["no_imaginary_mode"],
    )
    assert TSValidation(**none_found).n_imaginary == 0
    none_found["forming_stretch_overlap"] = 0.3
    rejected(TSValidation, none_found, "no imaginary mode, but ['forming_stretch_overlap']")


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"passed_bool": False, "reasons": ["no_imaginary_mode"]}, "disagrees with the three"),
        ({"identity_passed_bool": False}, "disagrees with the three"),
        ({"reasons": ["no_imaginary_mode"]}, "reasons must be empty"),
    ],
)
def test_validation_passed_inconsistent(overrides: dict[str, Any], fragment: str) -> None:
    """passed_bool equals the three checks, and a pass carries no reasons."""
    rejected(TSValidation, validation(**overrides), fragment)


def test_validation_reasons_rejected() -> None:
    """Reasons are sorted, unique and from the vocabulary; a failure needs one."""
    rejected(
        TSValidation,
        failing(reasons=["imaginary_above_cutoff", "active_core_fraction_below_threshold"]),
        "sorted and unique",
    )
    rejected(TSValidation, failing(reasons=["no_imaginary_mode", "no_imaginary_mode"]), "unique")
    rejected(TSValidation, failing(reasons=["low_overlap"]), "unknown reasons: ['low_overlap']")
    rejected(TSValidation, failing(reasons=[]), "reasons must be empty exactly")


def test_validation_reason_vocabulary() -> None:
    """The reason vocabulary is the mission's seven reasons."""
    assert sorted(TS_VALIDATION_REASONS) == [
        "active_core_fraction_below_threshold",
        "forming_bonds_out_of_phase",
        "forming_distance_out_of_window",
        "forming_overlap_below_threshold",
        "imaginary_above_cutoff",
        "multiple_imaginary_modes",
        "no_imaginary_mode",
    ]
    for reason in sorted(TS_VALIDATION_REASONS):
        assert TSValidation(**failing(reasons=[reason])).reasons == [reason]


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"active_atom_indices": []}, "at least 1 item"),
        ({"active_atom_indices": [1, 0]}, "sorted and unique"),
        ({"active_atom_indices": [0, 0]}, "sorted and unique"),
        ({"forming_distances_angstrom": {"1-0": 2.2}}, "'1-0'"),
        ({"forming_distances_angstrom": {"0_1": 2.2}}, "'0_1'"),
        ({"forming_distances_angstrom": {"01-2": 2.2}}, "'01-2'"),
        ({"forming_distances_angstrom": {"0-1": 0.0}}, "greater than 0"),
        ({"n_imaginary": -1}, "greater than or equal to 0"),
    ],
)
def test_validation_fields_rejected(overrides: dict[str, Any], fragment: str) -> None:
    """Active atoms are sorted, unique, non-empty; distance keys are 'i-j' with i < j."""
    rejected(TSValidation, validation(**overrides), fragment)


# --- TransitionStateRecord ---


def test_record_valid() -> None:
    """A valid record constructs with degeneracy 1."""
    assert TransitionStateRecord(**record()).degeneracy == 1


def test_record_failed_mode_count() -> None:
    """A record needs a validation whose mode count passed."""
    bad = TSValidation(
        **failing(
            n_imaginary=2,
            mode_count_passed_bool=False,
            reasons=["active_core_fraction_below_threshold", "multiple_imaginary_modes"],
        )
    )
    rejected(TransitionStateRecord, record(validation=bad), "mode count passed")


def test_record_two_imaginary_modes() -> None:
    """The record's thermochemistry lists exactly one imaginary mode."""
    two = ThermoResult(
        **ts_thermo(
            frequencies_cm1=[-400.0, -60.0, 1600.0], imaginary_frequencies_cm1=[-400.0, -60.0]
        )
    )
    rejected(TransitionStateRecord, record(thermo=two), "2 imaginary modes, expected exactly 1")


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"charge": 2}, "charge"),
        ({"spin_multiplicity": 3}, "spin_multiplicity"),
        (
            {"coordinates": [[0.0, 0.0, 0.118], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]]},
            "coordinates",
        ),
    ],
)
def test_record_state_must_match_search(change: dict[str, Any], field: str) -> None:
    """The state equals search.final_state in symbols, charge, multiplicity and coordinates."""
    state = water().model_copy(update=change)
    state = MolecularState.model_validate(state.model_dump())
    rejected(TransitionStateRecord, record(state=state), f"state.{field} differs")


def test_record_symbols_must_match_search() -> None:
    """A state with other elements is rejected."""
    state = MolecularState(
        symbols=["S", "H", "H"],
        coordinates=water().coordinates,
        charge=0,
        spin_multiplicity=1,
    )
    rejected(TransitionStateRecord, record(state=state), "state.symbols differs")


@pytest.mark.parametrize("value", [2, True, 1.0, "1"])
def test_record_degeneracy_strict(value: object) -> None:
    """Degeneracy is the integer 1 (TJ Q-TJ2 "A")."""
    rejected(TransitionStateRecord, record(degeneracy=value), "degeneracy must be the integer 1")


def test_record_ts_id_required() -> None:
    """ts_id is non-empty."""
    rejected(TransitionStateRecord, record(ts_id=""), "at least 1 character")


# --- Round trips, frozen, extra keys ---

ROUND_TRIP_CASES: list[tuple[type[BaseModel], Any]] = [
    (FormingBond, lambda: {"i": 0, "j": 1}),
    (TSStep, lambda: step(1)),
    (TSSearchResult, search),
    (TSValidationOptions, dict),
    (TSValidation, validation),
    (TSValidation, failing),
    (TransitionStateRecord, record),
]


@pytest.mark.parametrize(("cls", "factory"), ROUND_TRIP_CASES)
def test_round_trip_json(cls: type[BaseModel], factory: Any) -> None:
    """Every model round-trips exactly through JSON-mode dump and validate."""
    value = cls(**factory())
    dumped = value.model_dump(mode="json")
    again = cls.model_validate(json.loads(json.dumps(dumped)))
    assert again == value
    assert again.model_dump(mode="json") == dumped


@pytest.mark.parametrize(("cls", "factory"), ROUND_TRIP_CASES)
def test_frozen_and_extra_forbidden(cls: type[BaseModel], factory: Any) -> None:
    """Every model is frozen and rejects unknown keys."""
    value = cls(**factory())
    field = next(iter(cls.model_fields))
    with pytest.raises(ValidationError):
        setattr(value, field, getattr(value, field))
    with pytest.raises(ValidationError):
        cls(**factory(), unexpected=1)
