"""Engine crashes in the TS runner become cached failure rows (v0.6.0, slice 03, mission R3, G3)."""

from pathlib import Path
from typing import Any, ClassVar

import pytest
from test_ts_runner import STAGE, FakeEngine, FakeTS, _ts_options, run, ts_state

import eta_rxncat.orchestrator.species as species
from eta_rxncat.core import MolecularState
from eta_rxncat.engines import (
    EngineError,
    EngineInputError,
    EngineRuntimeError,
    EngineUnavailableError,
    RawResult,
)
from eta_rxncat.orchestrator import ENGINE_CLASSES, build_engine
from eta_rxncat.store import ArtifactStore, build_stage_key


class CrashingEngine(FakeEngine):
    """The fake engine, raising ``error`` at the chosen stage (``ts_opt`` or ``frequency``).

    ``ts_opt`` is the force evaluation of the search; ``frequency`` is the Hessian evaluation.
    """

    error: ClassVar[EngineError | None] = None
    armed_stage: ClassVar[str] = "ts_opt"

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        armed = (forces and type(self).armed_stage == "ts_opt") or (
            hessian and type(self).armed_stage == "frequency"
        )
        if armed and type(self).error is not None:
            type(self).calls += 1
            raise type(self).error
        return super()._evaluate(state, forces=forces, hessian=hessian)


@pytest.fixture(autouse=True)
def crashing_engine(monkeypatch: pytest.MonkeyPatch) -> type[CrashingEngine]:
    """Route xtb_subprocess to the crashing engine, with no error armed."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", CrashingEngine)
    monkeypatch.setattr(CrashingEngine, "error", None)
    monkeypatch.setattr(CrashingEngine, "armed_stage", "ts_opt")
    monkeypatch.setattr(CrashingEngine, "calls", 0)
    monkeypatch.setattr(
        CrashingEngine, "frequencies", [-400.0, 300.0, 800.0, 1200.0, 1600.0, 3000.0]
    )
    monkeypatch.setattr(CrashingEngine, "scf_failure", False)
    return CrashingEngine


def _arm(engine: type[CrashingEngine], error: EngineError, stage: str) -> None:
    engine.error = error
    engine.armed_stage = stage


def _stored(path: Path, kind: str) -> list[str]:
    """Return the keys of the rows the store holds for stage ``kind``."""
    with ArtifactStore(path) as store:
        return store.query(kind)


def _ts_opt_row(path: Path) -> dict[str, Any] | None:
    engine = build_engine(STAGE, {})
    stage = species._with_kind(
        engine.stage, "ts_opt", {**_ts_options(engine), "opt.forming_bonds": "0-3"}
    )
    with ArtifactStore(path) as store:
        return store.get(build_stage_key(ts_state(), stage, engine.identity))


def _frequency_row(path: Path) -> dict[str, Any] | None:
    engine = build_engine(STAGE, {})
    stage = species._with_kind(engine.stage, "frequency", engine.stage.options)
    with ArtifactStore(path) as store:
        return store.get(build_stage_key(ts_state(), stage, engine.identity))


def test_runtime_error_at_ts_opt_is_cached(
    tmp_path: Path, crashing_engine: type[CrashingEngine]
) -> None:
    """An engine crash during the search is a cached ``engine_error`` row; the rerun is free."""
    path = tmp_path / "s.sqlite"
    _arm(crashing_engine, EngineRuntimeError("xtb exited with status 128"), "ts_opt")
    first = run(path, FakeTS())
    assert first.failed_reason == "engine_error"
    assert first.search is None and first.record is None and first.validation is None
    assert first.metrics["ts_opt"].rows_created == 1
    assert first.metrics["ts_opt"].engine_calls == 1
    assert "frequency" not in first.keys
    row = _ts_opt_row(path)
    assert row is not None
    assert row == {
        "failed_reason": "engine_error",
        "message": "xtb exited with status 128",
        "error_type": "EngineRuntimeError",
    }
    calls = crashing_engine.calls
    second = run(path, FakeTS())
    assert second.failed_reason == "engine_error"
    assert second.metrics["ts_opt"].cache_hits == 1
    assert second.metrics["ts_opt"].engine_calls == 0
    assert second.metrics["ts_opt"].rows_created == 0
    assert crashing_engine.calls == calls
    assert second.as_payload()["failed_reason"] == first.as_payload()["failed_reason"]


def test_runtime_error_at_frequency_is_cached(
    tmp_path: Path, crashing_engine: type[CrashingEngine]
) -> None:
    """The search is cached as a success and the frequency stage as an ``engine_error``."""
    path = tmp_path / "s.sqlite"
    _arm(crashing_engine, EngineRuntimeError("segfault"), "frequency")
    first = run(path, FakeTS())
    assert first.failed_reason == "engine_error"
    assert first.search is not None and first.validation is None and first.record is None
    assert first.metrics["ts_opt"].rows_created == 1
    assert first.metrics["frequency"].rows_created == 1
    row = _frequency_row(path)
    assert row is not None
    assert row["failed_reason"] == "engine_error"
    assert row["error_type"] == "EngineRuntimeError"
    calls = crashing_engine.calls
    second = run(path, FakeTS())
    assert second.failed_reason == "engine_error"
    assert second.search is not None
    assert second.metrics["ts_opt"].cache_hits == 1
    assert second.metrics["frequency"].cache_hits == 1
    assert second.metrics["ts_opt"].engine_calls == 0
    assert second.metrics["frequency"].engine_calls == 0
    assert crashing_engine.calls == calls


@pytest.mark.parametrize("stage", ["ts_opt", "frequency"])
@pytest.mark.parametrize(
    "error",
    [EngineUnavailableError("no GPU on this host"), EngineInputError("bad charge")],
    ids=["unavailable", "input"],
)
def test_host_and_input_errors_propagate_and_are_never_cached(
    tmp_path: Path, crashing_engine: type[CrashingEngine], error: EngineError, stage: str
) -> None:
    """Host and input errors raise, and the failed stage leaves no row."""
    path = tmp_path / "s.sqlite"
    _arm(crashing_engine, error, stage)
    with pytest.raises(type(error)):
        run(path, FakeTS())
    assert _stored(path, stage) == []
    if stage == "ts_opt":
        assert _stored(path, "frequency") == []
    # After the fault clears, the same store runs the TS to completion: nothing was frozen.
    crashing_engine.error = None
    result = run(path, FakeTS())
    assert result.failed_reason is None
    assert result.record is not None


def test_other_failure_reasons_unchanged(
    tmp_path: Path, crashing_engine: type[CrashingEngine]
) -> None:
    """An SCF failure stays ``scf_convergence``; it is not folded into ``engine_error``."""
    crashing_engine.scf_failure = True
    result = run(tmp_path / "s.sqlite", FakeTS())
    assert result.failed_reason == "scf_convergence"
