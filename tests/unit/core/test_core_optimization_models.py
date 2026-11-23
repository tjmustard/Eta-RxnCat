"""Tests for OptimizerIdentity and OptimizationResult (v0.3.0 slice 02)."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import MolecularState, OptimizationResult, OptimizerIdentity


def water() -> MolecularState:
    """Return a neutral singlet water molecule."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
        charge=0,
        spin_multiplicity=1,
    )


def optimization(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid OptimizationResult, with overrides applied."""
    data: dict[str, Any] = {
        "final_state": water(),
        "final_energy_hartree": -76.4,
        "converged": True,
        "n_steps": 7,
        "n_engine_calls": 8,
        "recovery_steps": [],
        "optimizer": OptimizerIdentity(name="geometric", version="1.1.1"),
        "options": {"coordsys": "tric", "maxiter": 300, "trust": 0.1},
    }
    data.update(overrides)
    return data


def test_valid_result_round_trips() -> None:
    """A valid result constructs and round-trips through model_dump / model_validate."""
    value = OptimizationResult(**optimization())
    assert OptimizationResult.model_validate(value.model_dump()) == value


def test_constraints_recorded_in_options() -> None:
    """A constrained run records its constraints as an ordinary scalar option (R42)."""
    value = OptimizationResult(
        **optimization(options={"coordsys": "tric", "constraints": "dihedral:0,1,2,3:0.000000"})
    )
    assert value.options["constraints"] == "dihedral:0,1,2,3:0.000000"


def test_recovery_steps_kept_in_order() -> None:
    """Recovery steps are kept as given."""
    steps = ["tric", "cart"]
    assert OptimizationResult(**optimization(recovery_steps=steps)).recovery_steps == steps


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("converged", False),
        ("converged", 1),
        ("n_steps", -1),
        ("n_steps", True),
        ("n_engine_calls", 1.0),
        ("final_energy_hartree", float("nan")),
        ("options", {"nested": {"a": 1}}),
        ("options", {"values": [1, 2]}),
        ("recovery_steps", "tric"),
    ],
)
def test_result_fields_rejected(field: str, value: object) -> None:
    """Require converged True; counts are non-negative strict ints; options are scalars."""
    with pytest.raises(ValidationError):
        OptimizationResult(**optimization(**{field: value}))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "sella", "version": "2.3"},
        {"name": "geometric", "version": ""},
        {"name": "geometric"},
    ],
)
def test_identity_rejected(kwargs: dict[str, str]) -> None:
    """Only geomeTRIC, with a non-empty version, is a valid optimizer identity in v0.3.0."""
    with pytest.raises(ValidationError):
        OptimizerIdentity(**kwargs)


@pytest.mark.parametrize(
    ("cls", "kwargs", "field"),
    [
        (OptimizerIdentity, {"name": "geometric", "version": "1.1.1"}, "version"),
        (OptimizationResult, optimization(), "n_steps"),
    ],
)
def test_frozen_and_extra_forbidden(cls: type, kwargs: dict[str, Any], field: str) -> None:
    """Both models are frozen (assignment raises) and reject unknown fields."""
    value = cls(**kwargs)
    with pytest.raises(ValidationError):
        setattr(value, field, getattr(value, field))
    with pytest.raises(ValidationError):
        cls(**kwargs, unexpected=1)
