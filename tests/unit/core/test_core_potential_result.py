"""Tests for the PotentialResult contract and the esen_omol25 engine tag (v0.2.0 slice 03)."""

import math
import subprocess
import sys
import typing
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    EngineIdentity,
    EngineTag,
    MolecularState,
    PotentialResult,
    Solvation,
    StageConfig,
)
from eta_rxncat.store import build_stage_key


def symmetric(side: int) -> list[list[float]]:
    """Return a side x side symmetric matrix with distinct off-diagonal values."""
    return [[0.1 * (min(i, j) + 1) + 0.01 * max(i, j) for j in range(side)] for i in range(side)]


def forces(n: int) -> list[list[float]]:
    """Return n force rows of length 3."""
    return [[0.01 * a, -0.02 * a, 0.03] for a in range(n)]


def result(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid N = 3 result, with overrides applied."""
    data: dict[str, Any] = {
        "energy_hartree": -74.963,
        "forces_hartree_per_bohr": forces(3),
        "hessian_hartree_per_bohr2": symmetric(9),
        "hessian_method": "analytic",
        "hessian_max_asymmetry": 0.0,
        "engine": {"name": "pyscf_gpu_cpu", "version": "2.15.1"},
        "stage_engine_impl": 1,
        "device": "cpu",
        "wall_time_s": 0.5,
    }
    data.update(overrides)
    return data


def rejected(field: str, **overrides: Any) -> ValidationError:
    """Assert that ``overrides`` fail validation with an error naming ``field``."""
    with pytest.raises(ValidationError) as info:
        PotentialResult(**result(**overrides))
    assert field in str(info.value), str(info.value)
    return info.value


def test_valid_result_round_trips() -> None:
    """A full N = 3 result constructs, and model_dump round-trips through model_validate."""
    value = PotentialResult(**result())
    assert value.recovery_steps == [] and value.device_reason is None
    assert PotentialResult.model_validate(value.model_dump()) == value
    assert PotentialResult.model_validate_json(value.model_dump_json()) == value


def test_minimal_result_energy_only() -> None:
    """Forces, Hessian and its two companions are all optional together."""
    value = PotentialResult(
        **result(
            forces_hartree_per_bohr=None,
            hessian_hartree_per_bohr2=None,
            hessian_method=None,
            hessian_max_asymmetry=None,
        )
    )
    assert value.forces_hartree_per_bohr is None and value.hessian_hartree_per_bohr2 is None


def test_hessian_without_forces_is_allowed() -> None:
    """A Hessian alone is checked only for its own shape."""
    value = PotentialResult(**result(forces_hartree_per_bohr=None))
    assert len(value.hessian_hartree_per_bohr2 or []) == 9


def test_optional_fields_accept_values() -> None:
    """finite_difference, a positive asymmetry, cuda, a reason and recovery steps all validate."""
    value = PotentialResult(
        **result(
            hessian_method="finite_difference",
            hessian_max_asymmetry=3.2e-9,
            device="cuda",
            device_reason="gpu4pyscf available and under the VRAM budget",
            recovery_steps=["scf_level_shift_damping"],
            engine={"name": "mace", "version": "0.3.17", "model": "mace-mp-0-medium"},
            stage_engine_impl=2,
            wall_time_s=0.0,
        )
    )
    assert value.device == "cuda" and value.recovery_steps == ["scf_level_shift_damping"]


@pytest.mark.parametrize(
    ("field", "overrides"),
    [
        (
            "forces_hartree_per_bohr",
            {"forces_hartree_per_bohr": [[0.0, 0.0, 0.0]] * 2 + [[0.0, 0.0]]},
        ),
        ("forces_hartree_per_bohr", {"forces_hartree_per_bohr": [[0.0, 0.0, 0.0, 0.0]] * 3}),
        (
            "forces_hartree_per_bohr",
            {
                "forces_hartree_per_bohr": [],
                "hessian_hartree_per_bohr2": None,
                "hessian_method": None,
                "hessian_max_asymmetry": None,
            },
        ),
        ("hessian_hartree_per_bohr2", {"hessian_hartree_per_bohr2": symmetric(8)}),
        (
            "hessian_hartree_per_bohr2",
            {"hessian_hartree_per_bohr2": [], "forces_hartree_per_bohr": None},
        ),
        (
            "hessian_hartree_per_bohr2",
            {"hessian_hartree_per_bohr2": symmetric(9)[:8] + [[0.0] * 8]},
        ),
        ("hessian_hartree_per_bohr2", {"forces_hartree_per_bohr": forces(4)}),
        ("hessian_method", {"hessian_method": None}),
        ("hessian_max_asymmetry", {"hessian_max_asymmetry": None}),
        (
            "hessian_method",
            {"hessian_hartree_per_bohr2": None, "hessian_max_asymmetry": None},
        ),
        (
            "hessian_max_asymmetry",
            {"hessian_hartree_per_bohr2": None, "hessian_method": None},
        ),
        ("hessian_method", {"hessian_method": "numerical"}),
        ("hessian_max_asymmetry", {"hessian_max_asymmetry": -1e-12}),
        ("energy_hartree", {"energy_hartree": math.nan}),
        ("energy_hartree", {"energy_hartree": math.inf}),
        (
            "forces_hartree_per_bohr",
            {"forces_hartree_per_bohr": [[math.inf, 0.0, 0.0]] + forces(2)},
        ),
        (
            "forces_hartree_per_bohr",
            {"forces_hartree_per_bohr": [[math.nan, 0.0, 0.0]] + forces(2)},
        ),
        ("device", {"device": "gpu"}),
        ("device_reason", {"device_reason": ""}),
        ("stage_engine_impl", {"stage_engine_impl": 0}),
        ("stage_engine_impl", {"stage_engine_impl": True}),
        ("stage_engine_impl", {"stage_engine_impl": "1"}),
        ("wall_time_s", {"wall_time_s": -1}),
        ("wall_time_s", {"wall_time_s": math.inf}),
        ("hessian_max_asymmetry", {"hessian_max_asymmetry": math.nan}),
        ("engine", {"engine": {"name": "psi4", "version": "1"}}),
        ("surprise", {"surprise": 1}),
    ],
    ids=[
        "forces-row-length-2",
        "forces-row-length-4",
        "forces-empty",
        "hessian-8x8",
        "hessian-empty",
        "hessian-not-square",
        "hessian-9x9-with-4x3-forces",
        "hessian-without-method",
        "hessian-without-asymmetry",
        "method-without-hessian",
        "asymmetry-without-hessian",
        "method-unknown",
        "asymmetry-negative",
        "energy-nan",
        "energy-inf",
        "force-inf",
        "force-nan",
        "device-gpu",
        "device-reason-empty",
        "impl-zero",
        "impl-bool",
        "impl-string",
        "wall-time-negative",
        "wall-time-inf",
        "asymmetry-nan",
        "engine-unknown-tag",
        "extra-field",
    ],
)
def test_rejections(field: str, overrides: dict[str, Any]) -> None:
    """Each invalid input raises ValidationError naming the offending field."""
    rejected(field, **overrides)


def test_hessian_must_be_exactly_symmetric() -> None:
    """H[0][1] differing from H[1][0] by 1e-15 is rejected; the model never symmetrises."""
    hessian = symmetric(9)
    hessian[0][1] = hessian[1][0] + 1e-15
    assert hessian[0][1] != hessian[1][0]
    error = rejected("hessian_hartree_per_bohr2", hessian_hartree_per_bohr2=hessian)
    assert "[0][1]" in str(error)


@pytest.mark.parametrize(("i", "j"), [(0, 8), (3, 4), (7, 8)])
def test_every_off_diagonal_pair_is_checked(i: int, j: int) -> None:
    """Asymmetry anywhere in the upper triangle (including the last pair) is caught."""
    hessian = symmetric(9)
    hessian[j][i] = hessian[i][j] * (1 + 1e-12)
    error = rejected("hessian_hartree_per_bohr2", hessian_hartree_per_bohr2=hessian)
    assert f"[{i}][{j}]" in str(error)


def test_frozen() -> None:
    """Instances are immutable."""
    value = PotentialResult(**result())
    with pytest.raises(ValidationError):
        value.energy_hartree = 0.0  # type: ignore[misc]


def test_docstring_states_units_and_conventions() -> None:
    """The docstring names every unit and sign convention of the contract."""
    doc = PotentialResult.__doc__ or ""
    for phrase in (
        "Hartree (Eh)",
        "-dE/dx",
        "Hartree/Bohr",
        "Hartree/Bohr^2",
        "3N x 3N",
        "not mass-weighted",
        "not",
        "projected",
        "exactly symmetric",
        "seconds",
    ):
        assert phrase in doc, phrase


def test_esen_omol25_tag() -> None:
    """esen_omol25 is a tag; StageConfig and EngineIdentity accept it under existing rules."""
    assert "esen_omol25" in typing.get_args(EngineTag)
    assert set(typing.get_args(EngineTag)) == {
        "rdkit_ff",
        "mace",
        "uma_direct",
        "pyscf_gpu_cpu",
        "xtb_subprocess",
        "esen_omol25",
    }
    stage = StageConfig(
        kind="single_point", engine="esen_omol25", method="esen-sm-conserving-all-omol"
    )
    assert stage.basis is None and stage.solvation.model == "none"
    assert EngineIdentity(name="esen_omol25", version="x").model is None
    with pytest.raises(ValidationError, match="takes no basis"):
        StageConfig(
            kind="single_point",
            engine="esen_omol25",
            method="esen-sm-conserving-all-omol",
            basis="def2-svp",
        )
    for solvation in (
        Solvation(model="pcm", dielectric=78.4),
        Solvation(model="ddcosmo", dielectric=78.4),
        Solvation(model="alpb", solvent="water"),
    ):
        with pytest.raises(ValidationError, match="needs engine"):
            StageConfig(
                kind="single_point",
                engine="esen_omol25",
                method="esen-sm-conserving-all-omol",
                solvation=solvation,
            )


def test_esen_stage_key_differs_from_uma() -> None:
    """The new tag is part of the key, so an eSEN stage never collides with a UMA stage."""
    state = MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]],
        charge=0,
        spin_multiplicity=1,
    )
    keys = {
        build_stage_key(
            state,
            StageConfig(kind="single_point", engine=tag, method="m"),
            EngineIdentity(name=tag, version="1", model="w"),
        ).key
        for tag in ("esen_omol25", "uma_direct")
    }
    assert len(keys) == 2


def test_core_import_is_engine_free() -> None:
    """Importing eta_rxncat.core loads no numpy, torch, pyscf, rdkit or fairchem."""
    code = (
        "import eta_rxncat.core, sys; "
        "bad = {'numpy', 'torch', 'pyscf', 'rdkit', 'fairchem', 'ase'} & set(sys.modules); "
        "sys.exit(f'loaded: {sorted(bad)}' if bad else 0)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
