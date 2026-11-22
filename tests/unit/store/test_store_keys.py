"""Tests for the canonical per-stage cache key."""

import hashlib
import json
from typing import Any

import pytest

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.store import KEY_SCHEMA, build_stage_key, grid_coordinate

GOLDEN_KEY = "5a1a43c776934e8b2e2419aa4f07ca124d3a7f34afdc373be2c2aecee6ac5661"


def water(**overrides: Any) -> MolecularState:
    """Return the fixed H2O geometry of the GPU smoke test, with overrides applied."""
    data: dict[str, Any] = {
        "symbols": ["O", "H", "H"],
        "coordinates": [[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]],
        "charge": 0,
        "spin_multiplicity": 1,
    }
    data.update(overrides)
    return MolecularState(**data)


def pyscf_stage(**overrides: Any) -> StageConfig:
    """Return an RHF/STO-3G single point on PySCF, with overrides applied."""
    data: dict[str, Any] = {
        "kind": "single_point",
        "engine": "pyscf_gpu_cpu",
        "method": "RHF",
        "basis": "STO-3G",
    }
    data.update(overrides)
    return StageConfig(**data)


def pyscf_engine(**overrides: Any) -> EngineIdentity:
    """Return the PySCF engine identity, with overrides applied."""
    data: dict[str, Any] = {"name": "pyscf_gpu_cpu", "version": "2.15.1"}
    data.update(overrides)
    return EngineIdentity(**data)


def key_of(
    state: MolecularState | None = None,
    stage: StageConfig | None = None,
    engine: EngineIdentity | None = None,
) -> str:
    """Return the key hex for the given (default) inputs."""
    return build_stage_key(state or water(), stage or pyscf_stage(), engine or pyscf_engine()).key


def test_key_is_deterministic() -> None:
    """The same inputs give the same key every time."""
    assert key_of() == key_of()


def test_golden_key() -> None:
    """The H2O key is pinned, and recomputing it from json/hashlib directly agrees."""

    def canon(obj: object) -> str:
        return json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )

    def digest(obj: object) -> str:
        return hashlib.sha256(canon(obj).encode("ascii")).hexdigest()

    geometry = {
        "symbols": ["O", "H", "H"],
        "coordinates": [
            ["0.00000", "0.00000", "0.11730"],
            ["0.00000", "0.75720", "-0.46920"],
            ["0.00000", "-0.75720", "-0.46920"],
        ],
        "charge": 0,
        "spin_multiplicity": 1,
        "active_atom_indices": [],
    }
    stage = {
        "kind": "single_point",
        "engine": "pyscf_gpu_cpu",
        "method": "RHF",
        "basis": "STO-3G",
        "solvation": {"model": "none", "solvent": None, "dielectric": None},
        "frozen_atom_indices": [],
        "options": {},
        "engine_identity": {"name": "pyscf_gpu_cpu", "version": "2.15.1", "model": None},
    }
    expected = digest(
        {"key_schema": 1, "geometry_hash": digest(geometry), "stage_hash": digest(stage)}
    )
    key = build_stage_key(water(), pyscf_stage(), pyscf_engine())
    assert expected == GOLDEN_KEY == key.key
    assert key.geometry_hash == digest(geometry) and key.stage_hash == digest(stage)
    assert key.key_schema == KEY_SCHEMA == 1
    assert (key.stage_kind, key.engine, key.engine_version) == (
        "single_point",
        "pyscf_gpu_cpu",
        "2.15.1",
    )


def with_coordinate(value: float) -> MolecularState:
    """Return water with the first O coordinate replaced by ``value``."""
    return water(
        coordinates=[[value, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]]
    )


def test_same_grid_value_same_key() -> None:
    """0.123454 and 0.1234549 round to the same 5-decimal grid point."""
    assert key_of(with_coordinate(0.123454)) == key_of(with_coordinate(0.1234549))


def test_different_grid_value_different_key() -> None:
    """0.12345 and 0.12346 are different grid points."""
    assert key_of(with_coordinate(0.12345)) != key_of(with_coordinate(0.12346))


def test_negative_zero_folds_to_zero() -> None:
    """-1e-6 rounds to -0.0, which is written as 0.00000."""
    assert grid_coordinate(-1e-6) == "0.00000" == grid_coordinate(0.0)
    assert key_of(with_coordinate(-1e-6)) == key_of(with_coordinate(0.0))


BASE = key_of()


def test_charge_changes_key() -> None:
    """Charge alone is keyed (H2O+ vs H2O-, both doublets)."""
    assert key_of(water(charge=1, spin_multiplicity=2)) != key_of(
        water(charge=-1, spin_multiplicity=2)
    )


def test_spin_multiplicity_changes_key() -> None:
    """Spin multiplicity is keyed."""
    assert key_of(water(spin_multiplicity=3)) != BASE


def test_symbol_changes_key() -> None:
    """Element symbols are keyed (H2O vs H2S, same coordinates)."""
    assert key_of(water(symbols=["S", "H", "H"])) != BASE


def test_active_atoms_change_key() -> None:
    """Active atom indices are keyed (order-insensitively)."""
    assert key_of(water(active_atom_indices=[0])) != BASE
    assert key_of(water(active_atom_indices=[2, 0])) == key_of(water(active_atom_indices=[0, 2]))


def test_kind_changes_key() -> None:
    """The stage kind is keyed."""
    assert key_of(stage=pyscf_stage(kind="frequency")) != BASE


def test_engine_changes_key() -> None:
    """The engine (with a matching identity) is keyed."""
    xtb = StageConfig(kind="single_point", engine="xtb_subprocess", method="RHF")
    assert key_of(stage=xtb, engine=EngineIdentity(name="xtb_subprocess", version="2.15.1")) != BASE


def test_method_changes_key() -> None:
    """The method is keyed."""
    assert key_of(stage=pyscf_stage(method="B3LYP")) != BASE


def test_basis_changes_key() -> None:
    """The basis is keyed."""
    assert key_of(stage=pyscf_stage(basis="def2-SVP")) != BASE


def test_solvation_model_changes_key() -> None:
    """The solvation model is keyed."""
    ddcosmo = key_of(stage=pyscf_stage(solvation={"model": "ddcosmo", "solvent": "water"}))
    pcm = key_of(stage=pyscf_stage(solvation={"model": "pcm", "solvent": "water"}))
    assert ddcosmo != pcm


def test_solvent_changes_key() -> None:
    """The solvent is keyed."""
    water_solvent = key_of(stage=pyscf_stage(solvation={"model": "pcm", "solvent": "water"}))
    thf = key_of(stage=pyscf_stage(solvation={"model": "pcm", "solvent": "thf"}))
    assert water_solvent != thf


def test_dielectric_changes_key() -> None:
    """The dielectric is keyed; an integral dielectric equals its int form."""
    eps_78 = key_of(stage=pyscf_stage(solvation={"model": "pcm", "dielectric": 78.0}))
    eps_7 = key_of(stage=pyscf_stage(solvation={"model": "pcm", "dielectric": 7.4}))
    eps_78_int = key_of(stage=pyscf_stage(solvation={"model": "pcm", "dielectric": 78}))
    assert eps_78 != eps_7 and eps_78 == eps_78_int


def test_frozen_atoms_change_key() -> None:
    """Frozen atom indices are keyed (order-insensitively)."""
    assert key_of(stage=pyscf_stage(frozen_atom_indices=[0])) != BASE
    assert key_of(stage=pyscf_stage(frozen_atom_indices=[1, 0])) == key_of(
        stage=pyscf_stage(frozen_atom_indices=[0, 1])
    )


def test_option_value_changes_key() -> None:
    """Option values are keyed."""
    assert key_of(stage=pyscf_stage(options={"conv_tol": 1e-9})) != key_of(
        stage=pyscf_stage(options={"conv_tol": 1e-10})
    )


def test_engine_version_changes_key() -> None:
    """The engine version is keyed."""
    assert key_of(engine=pyscf_engine(version="2.16.0")) != BASE


def test_engine_model_changes_key() -> None:
    """The engine model id is keyed."""
    assert key_of(engine=pyscf_engine(model="weights-a")) != key_of(
        engine=pyscf_engine(model="weights-b")
    )


def test_metadata_is_not_keyed() -> None:
    """Metadata does not change the key."""
    assert key_of(water(metadata={"source": "test", "n": 3})) == BASE


def test_integral_float_option_equals_int() -> None:
    """Options {x: 1} and {x: 1.0} give the same key."""
    assert key_of(stage=pyscf_stage(options={"x": 1})) == key_of(
        stage=pyscf_stage(options={"x": 1.0})
    )


def test_bool_option_differs_from_int() -> None:
    """Options {x: True} and {x: 1} give different keys."""
    assert key_of(stage=pyscf_stage(options={"x": True})) != key_of(
        stage=pyscf_stage(options={"x": 1})
    )


def test_engine_mismatch_raises() -> None:
    """An engine identity whose name is not the stage's engine raises ValueError."""
    with pytest.raises(ValueError, match="does not match"):
        build_stage_key(water(), pyscf_stage(), EngineIdentity(name="mace", version="0.3"))
