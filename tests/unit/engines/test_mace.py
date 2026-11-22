"""Tests for the mace engine (slice 09).

Default-suite tests need no torch (the sha check, refusals and the loader are faked). ``mlip_mace``
tests use the real MACE-MP-0 medium weights in ``.venv-accept-mace`` (CUDA cases also ``gpu``):
``UV_PROJECT_ENVIRONMENT=.venv-accept-mace ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m
mlip_mace tests/unit/engines/test_mace.py``. The weights come from ``ETA_RXNCAT_MACE_MODEL`` or
``~/.cache/eta-rxncat/mace/``; without them those tests skip at fixture level.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import (
    ENGINE_IMPL_KEY,
    EngineInputError,
    EngineUnavailableError,
    MACEEngine,
    ev_per_angstrom_to_hartree_per_bohr,
    ev_to_hartree,
)
from eta_rxncat.engines import mace as mace_module
from eta_rxncat.engines.mace import EXPECTED_SHA256, MODEL_NAME

PIN = "01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845"
DEFAULT_MODEL = Path.home() / ".cache/eta-rxncat/mace/2023-12-03-mace-128-L1_epoch-199.model"


def stage(**kwargs: Any) -> StageConfig:
    """A MACE-MP-0 medium single point."""
    data: dict[str, Any] = {"kind": "single_point", "engine": "mace", "method": MODEL_NAME}
    data.update(kwargs)
    return StageConfig(**data)


# ---------------------------------------------------------------- default suite (no torch)


class ExplodingModel:
    """A model that fails the test if it is ever called."""

    atomic_numbers = [1, 8]
    r_max = 6.0

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Fail: a refusal must happen before any model call."""
        raise AssertionError("the MACE model was called")


@pytest.fixture
def faked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """A weights file whose (faked) sha256 is the pin, and a loader that records calls."""
    weights = tmp_path / "model.model"
    weights.write_bytes(b"not really a model")
    loads: list[tuple[Path, str]] = []

    def load(self: MACEEngine, path: Path, device: str) -> tuple[Any, str]:
        loads.append((path, device))
        return ExplodingModel(), "cpu"

    monkeypatch.setattr(mace_module, "sha256_file", lambda path: PIN)
    monkeypatch.setattr(MACEEngine, "_load_model", load)
    return {"weights": weights, "loads": loads}


def test_pin() -> None:
    """The pin is the mission's MACE-MP-0 medium sha256."""
    assert EXPECTED_SHA256 == {MODEL_NAME: PIN} and MODEL_NAME == "mace-mp-0-medium"


def test_sha_mismatch_refused_before_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file whose sha256 is not the pin -> EngineInputError; the loader is never called."""
    weights = tmp_path / "evil.model"
    weights.write_bytes(b"pickle bombs welcome")

    def load(self: MACEEngine, path: Path, device: str) -> Any:
        raise AssertionError("torch load called")

    monkeypatch.setattr(MACEEngine, "_load_model", load)
    with pytest.raises(EngineInputError, match="not the pinned 01bfe221"):
        MACEEngine.from_stage(stage(), model_path=weights)


@pytest.mark.parametrize("path", [None, "missing.model"])
def test_missing_model_path(tmp_path: Path, path: str | None) -> None:
    """No model_path, or no such file -> EngineUnavailableError naming the provisioning step."""
    arg = None if path is None else tmp_path / path
    with pytest.raises(EngineUnavailableError, match="2023-12-03-mace-128-L1_epoch-199.model"):
        MACEEngine.from_stage(stage(), model_path=arg)


@pytest.mark.parametrize("case", ["hydroxide", "hydronium", "hydroxyl"])
def test_refusals_before_any_model_call(
    faked: dict[str, Any], test_set: dict[str, MolecularState], case: str
) -> None:
    """Anion, cation and doublet -> EngineInputError naming mace, charge and multiplicity."""
    s = test_set[case]
    eng = MACEEngine.from_stage(stage(), model_path=faked["weights"])
    with pytest.raises(EngineInputError) as info:
        eng.evaluate(s)
    assert str(info.value).startswith(
        f"mace: charge {s.charge}, multiplicity {s.spin_multiplicity}: "
    )


def test_load_happens_after_sha_check(faked: dict[str, Any]) -> None:
    """With the pin matched the loader runs once, with the path and the requested device."""
    MACEEngine.from_stage(stage(), model_path=faked["weights"], device="cpu")
    assert faked["loads"] == [(faked["weights"], "cpu")]


def test_resolved_options_and_identity(
    faked: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keyed dtype float64, fd_step_bohr 0.005, engine_impl 1; identity is name@sha256."""
    monkeypatch.setattr(mace_module, "library_version", lambda dist: "0.3.17")
    eng = MACEEngine.from_stage(stage(), model_path=faked["weights"])
    assert eng.stage.options == {"dtype": "float64", "fd_step_bohr": 0.005, ENGINE_IMPL_KEY: 1}
    assert eng.identity.model == f"{MODEL_NAME}@sha256:{PIN}"
    assert eng.identity.name == "mace" and eng.identity.version == "0.3.17"
    assert str(faked["weights"].parent) not in (eng.identity.model or "")


@pytest.mark.parametrize(
    ("kwargs", "runtime", "error", "match"),
    [
        ({"method": "mace-mp-0-large"}, {}, EngineInputError, "mace-mp-0-medium"),
        ({"options": {"dtype": "float32"}}, {}, EngineInputError, "dtype"),
        ({"options": {"fd_step_bohr": 0.0}}, {}, EngineInputError, "fd_step_bohr"),
        ({"options": {"nope": 1}}, {}, EngineInputError, "nope"),
        ({}, {"device": "tpu"}, EngineInputError, "tpu"),
        ({}, {"threads": 2}, EngineInputError, "threads"),
    ],
)
def test_bad_stage_or_runtime(
    faked: dict[str, Any],
    kwargs: dict[str, Any],
    runtime: dict[str, Any],
    error: type[Exception],
    match: str,
) -> None:
    """Wrong method, dtype, step, unknown option, device or runtime argument are refused."""
    with pytest.raises(error, match=match):
        MACEEngine.from_stage(stage(**kwargs), model_path=faked["weights"], **runtime)


def test_solvation_rejected_by_core() -> None:
    """Implicit solvation never reaches MACE: core pairs ddCOSMO/PCM/ALPB with other engines."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="needs engine"):
        stage(solvation=Solvation(model="pcm", dielectric=10.0))


# ---------------------------------------------------------------- real MACE


@pytest.fixture(scope="module")
def model_path() -> Path:
    """The real weights (ETA_RXNCAT_MACE_MODEL or the cache); skip here, at fixture level."""
    path = Path(os.environ.get("ETA_RXNCAT_MACE_MODEL", str(DEFAULT_MODEL))).expanduser()
    if not path.is_file():
        pytest.skip(f"MACE-MP-0 medium weights not provisioned at {path}")
    return path


@pytest.fixture(scope="module")
def mace_stack() -> SimpleNamespace:
    """torch, e3nn and MACE's calculator (the reference); a marked test without them fails."""
    import e3nn
    import torch
    from mace.calculators import MACECalculator

    return SimpleNamespace(torch=torch, e3nn=e3nn, MACECalculator=MACECalculator)


def reference(
    stack: SimpleNamespace, path: Path, state: MolecularState, device: str
) -> tuple[float, Any]:
    """MACE's own calculator on the same ase.Atoms: (energy eV, forces eV/A)."""
    import ase

    calc = stack.MACECalculator(model_paths=str(path), default_dtype="float64", device=device)
    atoms = ase.Atoms(state.symbols, positions=state.coordinates)
    atoms.calc = calc
    return float(atoms.get_potential_energy()), atoms.get_forces()


def check_against_reference(
    stack: SimpleNamespace, path: Path, test_set: dict[str, MolecularState], device: str
) -> None:
    """Water on ``device``: energy/forces vs MACECalculator, forces vs FD of the energy."""
    water = test_set["water"]
    eng = MACEEngine.from_stage(stage(), model_path=path, device=device)
    result = eng.evaluate(water)
    assert result.device == device
    e_ref, f_ref = reference(stack, path, water, device)
    print(f"{device}: E_engine {result.energy_hartree!r} Eh, E_ref {e_ref!r} eV")
    assert abs(result.energy_hartree - ev_to_hartree(e_ref)) <= ev_to_hartree(1e-6)
    forces = result.forces_hartree_per_bohr
    assert forces is not None
    for row, ref_row in zip(forces, f_ref, strict=True):
        for f, r in zip(row, ref_row, strict=True):
            assert abs(f - ev_per_angstrom_to_hartree_per_bohr(float(r))) <= (
                ev_per_angstrom_to_hartree_per_bohr(1e-6)
            )
    step = 1e-4  # Angstrom
    for atom in range(3):
        for axis in range(3):
            e = []
            for sign in (1, -1):
                c = [r[:] for r in water.coordinates]
                c[atom][axis] += sign * step
                moved = MolecularState(
                    symbols=water.symbols, coordinates=c, charge=0, spin_multiplicity=1
                )
                e.append(eng.evaluate(moved, forces=False).energy_hartree)
            fd = -(e[0] - e[1]) / (2 * step / 0.529177210903)
            assert abs(forces[atom][axis] - fd) <= 1e-4, (atom, axis)


@pytest.mark.mlip_mace
def test_cpu_matches_mace_calculator(
    mace_stack: SimpleNamespace, model_path: Path, test_set: dict[str, MolecularState]
) -> None:
    """CPU water: energy and forces equal MACECalculator (<= 1e-6 eV, eV/A); forces = -dE/dx."""
    print(f"torch {mace_stack.torch.__version__}, e3nn {mace_stack.e3nn.__version__}")
    check_against_reference(mace_stack, model_path, test_set, "cpu")


@pytest.mark.mlip_mace
@pytest.mark.gpu
def test_cuda_matches_mace_calculator(
    mace_stack: SimpleNamespace, model_path: Path, test_set: dict[str, MolecularState]
) -> None:
    """CUDA water: the same checks, the engine really on cuda."""
    assert mace_stack.torch.cuda.is_available(), "CUDA test without CUDA"
    check_against_reference(mace_stack, model_path, test_set, "cuda")


@pytest.mark.mlip_mace
@pytest.mark.parametrize("case", ["hydroxide", "hydronium", "hydroxyl"])
def test_real_refusals_never_call_the_model(
    mace_stack: SimpleNamespace,
    model_path: Path,
    test_set: dict[str, MolecularState],
    case: str,
) -> None:
    """With the real weights loaded, refusals happen before the (monkeypatched, failing) model."""
    eng = MACEEngine.from_stage(stage(), model_path=model_path, device="cpu")
    eng.model = ExplodingModel()
    s = test_set[case]
    with pytest.raises(
        EngineInputError, match=f"mace: charge {s.charge}, multiplicity {s.spin_multiplicity}"
    ):
        eng.evaluate(s)


@pytest.mark.mlip_mace
def test_real_identity_and_hessian(
    mace_stack: SimpleNamespace, model_path: Path, test_set: dict[str, MolecularState]
) -> None:
    """identity.model is the pinned content id; the water Hessian is FD, symmetric, recorded."""
    eng = MACEEngine.from_stage(stage(), model_path=model_path, device="cpu")
    assert eng.identity.model == (
        "mace-mp-0-medium@sha256:01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845"
    )
    result = eng.evaluate(test_set["water"], hessian=True)
    h = result.hessian_hartree_per_bohr2
    assert h is not None and result.hessian_method == "finite_difference"
    assert all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    assert result.hessian_max_asymmetry is not None and result.hessian_max_asymmetry < 1e-4
    assert mace_stack.torch.get_default_dtype() == mace_stack.torch.float32  # restored
