"""Every failure row written around a geomeTRIC run or a TS search carries its frames (R13, R33)."""

import time
from pathlib import Path
from typing import Any, ClassVar

import pytest
from test_ts_runner import FakeEngine as TSFakeEngine
from test_ts_runner import FakeTS, recipe, run, spec

from eta_rxncat.core import MolecularState, StageConfig
from eta_rxncat.engines import EngineRuntimeError, RawResult, RDKitFFEngine, ScfConvergenceError
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer, TSSearchFailedError
from eta_rxncat.orchestrator import ENGINE_CLASSES, Recipe, TSRecipe
from eta_rxncat.orchestrator.species import _opt_from_payload, _opt_payload, _Runner
from eta_rxncat.orchestrator.ts import _TSRun
from eta_rxncat.orchestrator.ts_ensemble import _PreRelax
from eta_rxncat.store import ArtifactStore, build_stage_key

STAGE = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")


def water() -> MolecularState:
    """Distorted water."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.0], [1.1, 0.0, 0.0], [-0.55, 0.953, 0.0]],
        charge=0,
        spin_multiplicity=1,
    )


class Scripted(RDKitFFEngine):
    """UFF whose evaluations follow a class-level script (call number -> exception or stall)."""

    script: ClassVar[dict[int, Any]] = {}
    calls: ClassVar[int] = 0

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        type(self).calls += 1
        action = type(self).script.get(type(self).calls)
        if action == "stall":
            for _ in range(600):  # interrupted by the deadline long before this ends
                time.sleep(0.05)
        elif action is not None:
            raise action
        return super()._evaluate(state, forces=forces, hessian=hessian)


@pytest.fixture(autouse=True)
def scripted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route rdkit_ff to the scripted engine with an empty script."""
    monkeypatch.setitem(ENGINE_CLASSES, "rdkit_ff", Scripted)
    monkeypatch.setattr(Scripted, "script", {})
    monkeypatch.setattr(Scripted, "calls", 0)


def not_converged() -> BaseException:
    """GeomeTRIC's own not-converged error: the ladder step fails."""
    from geometric.errors import GeomOptNotConvergedError

    return GeomOptNotConvergedError("fake")


class Displacing(GeometricOptimizer):
    """Converges, then moves atom 0, so the frozen-core check fails after ``minimize`` returns."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Minimise, then displace atom 0."""
        result = super().minimize(state, engine, **kwargs)
        moved = [list(row) for row in result.final_state.coordinates]
        moved[0][0] += 0.1
        final = result.final_state.model_copy(update={"coordinates": moved})
        return result.model_copy(update={"final_state": final})


def pre_relax(
    tmp_path: Path, optimizer: GeometricOptimizer, budget_s: float | None = None
) -> tuple[str | None, dict[str, Any]]:
    """Run one pre-relaxation; return its failure reason and the stored row."""
    recipe = TSRecipe(name="p", engine_stage=STAGE, ts_optimizer=PRFOOptimizer())
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        relax = _PreRelax(recipe, store, optimizer, [0], budget_s)
        _, reason, _ = relax.run(water())
        payload = store.get(build_stage_key(water(), relax.stage(), relax.engine.identity))
    assert payload is not None
    return reason, payload


@pytest.mark.parametrize(
    ("script", "reason", "n_frames"),
    [
        ({2: "stall"}, "pre_relax_failed:PreRelaxTimeout", 1),
        (
            {2: "fail", 4: "fail", 6: "fail"},
            "pre_relax_failed:OptimizationFailedError",
            3,
        ),
        ({3: ScfConvergenceError("fake", steps=("diis",))}, "scf_convergence", 2),
        ({3: EngineRuntimeError("fake crash")}, "engine_error", 2),
    ],
)
def test_pre_relax_failure_rows_carry_frames(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: dict[int, Any],
    reason: str,
    n_frames: int,
) -> None:
    """Timeout, optimizer failure, SCF failure and engine crash rows keep the evaluated frames."""
    resolved = {k: not_converged() if v == "fail" else v for k, v in script.items()}
    monkeypatch.setattr(Scripted, "script", resolved)
    budget = 1.0 if "PreRelaxTimeout" in reason else None
    got, payload = pre_relax(tmp_path, GeometricOptimizer(), budget)
    assert got == reason == payload["failed_reason"]
    assert len(payload["frames"]) == n_frames
    assert payload["frames"][0]["ladder_step"] == "tric"
    assert len(payload["frames"][0]["coordinates_angstrom"]) == 3


def test_core_displacement_row_carries_frames(tmp_path: Path) -> None:
    """A failure raised after ``minimize`` returns still stores every frame."""
    reason, payload = pre_relax(tmp_path, Displacing())
    assert reason == "pre_relax_failed:CoreDisplacementError"
    assert len(payload["frames"]) == Scripted.calls


def test_a_failure_before_any_evaluation_has_no_frames_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty list is left out."""
    monkeypatch.setattr(Scripted, "script", {1: EngineRuntimeError("fake crash")})
    _, payload = pre_relax(tmp_path, GeometricOptimizer())
    assert "frames" not in payload


def test_pre_relax_success_row_carries_frames(tmp_path: Path) -> None:
    """A successful pre-relaxation stores its frames."""
    reason, payload = pre_relax(tmp_path, GeometricOptimizer())
    assert reason is None
    assert len(payload["frames"]) == payload["n_engine_calls"]


def species_runner(store: ArtifactStore) -> _Runner:
    """A species runner on the scripted engine (``optimize`` needs no species)."""
    recipe = Recipe(name="s", engine_stage=STAGE, optimizer=GeometricOptimizer())
    return _Runner(None, recipe, store)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("script", "reason", "n_frames"),
    [
        ({2: "fail", 4: "fail", 6: "fail"}, "optimization_failed", 3),
        ({3: ScfConvergenceError("fake", steps=("diis",))}, "scf_convergence", 2),
    ],
)
def test_species_failure_rows_carry_frames(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: dict[int, Any],
    reason: str,
    n_frames: int,
) -> None:
    """``geometry_opt`` failure rows keep the evaluated frames."""
    resolved = {k: not_converged() if v == "fail" else v for k, v in script.items()}
    monkeypatch.setattr(Scripted, "script", resolved)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result, got, _, key = species_runner(store).optimize(water())
        runner = species_runner(store)
        stage = runner.opt_stage("")
        payload = store.get(build_stage_key(water(), stage, runner.engine.identity))
    assert result is None and got == reason
    assert payload is not None and payload["failed_reason"] == reason
    assert len(payload["frames"]) == n_frames
    assert key


def test_species_success_round_trips_frames(tmp_path: Path) -> None:
    """A cached success returns the frames the run captured."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        first, _, hit, _ = species_runner(store).optimize(water())
        second, _, second_hit, _ = species_runner(store).optimize(water())
    assert not hit and second_hit
    assert first is not None and second is not None and first.frames
    assert second.frames == first.frames


def test_a_v060_row_loads_without_frames() -> None:
    """A payload without ``frames`` loads as ``None`` and writes the same payload (G10)."""
    payload = {
        "final_xyz": [list(row) for row in water().coordinates],
        "final_energy_hartree": -1.0,
        "n_steps": 2,
        "n_engine_calls": 3,
        "recovery_steps": ["tric"],
        "optimizer": {"name": "geometric", "version": "1.1.1"},
        "options": {"maxiter": 300},
    }
    result = _opt_from_payload(water(), payload)
    assert result.frames is None
    assert _opt_payload(result) == payload
    assert list(_opt_payload(result)) == list(payload)
    assert _opt_payload(result.model_copy(update={"frames": []})) == payload


# --- TS search ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (
            TSSearchFailedError("fake", reason="max_steps", steps=("0",), last_energy_hartree=-1.0),
            "ts_search_failed:max_steps",
        ),
        (ScfConvergenceError("fake", steps=("diis",)), "scf_convergence"),
        (EngineRuntimeError("fake crash"), "engine_error"),
    ],
)
def test_ts_failure_rows_carry_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception, reason: str
) -> None:
    """A failed search stores the evaluated step geometries, unjudged."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", TSFakeEngine)
    path = tmp_path / "s.sqlite"
    result = run(path, FakeTS(error=error))
    assert result.failed_reason == reason
    with ArtifactStore(path) as store:
        probe = _TSRun(spec(), recipe(FakeTS()), store)
        payload = store.get(build_stage_key(spec().start, probe.ts_stage(), probe.engine.identity))
    assert payload is not None and payload["failed_reason"] == reason
    (frame,) = payload["frames"]
    assert frame["ladder_step"] is None and "accepted_bool" not in frame
    assert frame["coordinates_angstrom"] == spec().start.coordinates


def test_ts_success_stores_step_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A converged search stores each step's geometry and a rerun loads it."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", TSFakeEngine)
    first = run(tmp_path / "s.sqlite", FakeTS())
    second = run(tmp_path / "s.sqlite", FakeTS())
    assert first.search is not None and second.search is not None
    assert first.search.history[0].coordinates_angstrom == first.search.final_state.coordinates
    assert second.search == first.search
