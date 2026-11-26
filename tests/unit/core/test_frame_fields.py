"""Tests for the v0.7.0 optimization frame fields and the orientation exclusion reason."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    MolecularState,
    OptimizationFrame,
    OptimizationResult,
    OptimizerIdentity,
    TSEnsembleExclusion,
    TSStep,
)

# Bytes written by the v0.6.0 models (slice start 14d2da1) for the objects built below.
V060_STEP_JSON = (
    '{"step":0,"accepted_bool":true,"energy_hartree":-1.1,'
    '"max_gradient_hartree_per_bohr":0.01,"trust_radius_bohr":0.1,'
    '"followed_eigenvalue_hartree_per_bohr2":-0.05,"mode_overlap":null,'
    '"hessian_source":"exact","ratio":null}'
)
V060_RESULT_JSON = (
    '{"final_state":{"symbols":["H","H"],"coordinates":[[0.0,0.0,0.0],[0.0,0.0,0.74]],'
    '"charge":0,"spin_multiplicity":1,"active_atom_indices":[],"metadata":{}},'
    '"final_energy_hartree":-1.17,"converged":true,"n_steps":2,"n_engine_calls":3,'
    '"recovery_steps":["restart"],"optimizer":{"name":"geometric","version":"1.1"},'
    '"options":{"a":1}}'
)

# Bytes of a frame as slice 02 wrote it, before ``accepted_bool`` existed.
V070_FRAME_JSON = (
    '{"coordinates_angstrom":[[0.0,0.0,0.0],[0.0,0.0,0.74]],"energy_hartree":-1.17,'
    '"max_gradient_hartree_per_bohr":0.001,"ladder_step":null}'
)

XYZ = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]]


def frame(**overrides: Any) -> OptimizationFrame:
    """Return a valid frame."""
    data: dict[str, Any] = {
        "coordinates_angstrom": XYZ,
        "energy_hartree": -1.17,
        "max_gradient_hartree_per_bohr": 0.001,
        "ladder_step": None,
    }
    data.update(overrides)
    return OptimizationFrame(**data)


def result(**overrides: Any) -> OptimizationResult:
    """Return the optimization result whose v0.6.0 bytes are pinned above."""
    data: dict[str, Any] = {
        "final_state": MolecularState(
            symbols=["H", "H"], coordinates=XYZ, charge=0, spin_multiplicity=1
        ),
        "final_energy_hartree": -1.17,
        "converged": True,
        "n_steps": 2,
        "n_engine_calls": 3,
        "recovery_steps": ["restart"],
        "optimizer": OptimizerIdentity(name="geometric", version="1.1"),
        "options": {"a": 1},
    }
    data.update(overrides)
    return OptimizationResult(**data)


def test_v060_step_reserialises_byte_for_byte() -> None:
    """A v0.6.0 TS step loads without coordinates and writes the same bytes."""
    step = TSStep.model_validate_json(V060_STEP_JSON)
    assert step.coordinates_angstrom is None
    assert step.model_dump_json() == V060_STEP_JSON
    assert "coordinates_angstrom" not in step.model_dump(mode="json")


def test_v060_result_reserialises_byte_for_byte() -> None:
    """A v0.6.0 optimization result loads without frames and writes the same bytes."""
    loaded = OptimizationResult.model_validate_json(V060_RESULT_JSON)
    assert loaded.frames is None
    assert loaded == result()
    assert loaded.model_dump_json() == V060_RESULT_JSON
    assert "frames" not in loaded.model_dump()


def test_captured_frames_round_trip() -> None:
    """Frames and step coordinates are written when set, even when empty."""
    with_frames = result(frames=[frame(), frame(ladder_step="restart")])
    assert OptimizationResult.model_validate_json(with_frames.model_dump_json()) == with_frames
    assert result(frames=[]).model_dump()["frames"] == []
    step = TSStep.model_validate_json(V060_STEP_JSON).model_copy(
        update={"coordinates_angstrom": XYZ}
    )
    assert step.model_dump(mode="json")["coordinates_angstrom"] == XYZ
    assert TSStep.model_validate_json(step.model_dump_json()) == step


def test_frame_round_trip_and_refusals() -> None:
    """A frame round-trips; non-finite values, negative gradients and no ladder step are refused."""
    assert OptimizationFrame.model_validate_json(frame().model_dump_json()) == frame()
    with pytest.raises(ValidationError):
        frame(energy_hartree=float("nan"))
    with pytest.raises(ValidationError):
        frame(coordinates_angstrom=[[float("inf"), 0.0, 0.0]])
    with pytest.raises(ValidationError):
        frame(max_gradient_hartree_per_bohr=-1.0)
    with pytest.raises(ValidationError, match="ladder_step"):
        OptimizationFrame.model_validate(
            {k: v for k, v in frame().model_dump().items() if k != "ladder_step"}
        )


def test_unjudged_frame_serialises_as_before_the_field() -> None:
    """``accepted_bool`` ``None`` is left out (slice 02's bytes); ``True``/``False`` round-trip."""
    unjudged = frame(accepted_bool=None)
    assert unjudged.model_dump_json() == V070_FRAME_JSON
    assert OptimizationFrame.model_validate_json(V070_FRAME_JSON) == unjudged
    assert "accepted_bool" not in unjudged.model_dump(mode="json")
    for value in (True, False):
        judged = frame(accepted_bool=value)
        assert judged.model_dump()["accepted_bool"] is value
        assert OptimizationFrame.model_validate_json(judged.model_dump_json()) == judged
    nested = result(frames=[frame()]).model_dump(mode="json")
    assert "accepted_bool" not in nested["frames"][0]


@pytest.mark.parametrize(
    "reason",
    [
        "ts_search_failed:max_steps",
        "scf_convergence",
        "engine_error",
        "ts_validation_failed",
        "gate_failed:distance",
        "face_mismatch",
        "pre_relax_failed:PreRelaxTimeout",
        "outside_window",
        "face_undetermined",
        "connectivity_changed",
        "orientation_mismatch",
    ],
)
def test_exclusion_reasons(reason: str) -> None:
    """Every v0.6.0 exclusion reason still validates, and ``orientation_mismatch`` does too."""
    assert TSEnsembleExclusion(index=0, source="seed", reason=reason).reason == reason


def test_unknown_exclusion_reason_refused() -> None:
    """The reason set stays closed."""
    for reason in ("orientation", "orientation_mismatch:3"):
        with pytest.raises(ValidationError, match="unknown exclusion reason"):
            TSEnsembleExclusion(index=0, source="seed", reason=reason)
