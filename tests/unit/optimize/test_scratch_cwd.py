"""geomeTRIC runs in a temporary working directory and the caller's is restored (v0.7.0, R8)."""

import os
from pathlib import Path

import pytest
from test_optimize_geometric import UFF_STAGE, distorted_water, not_converged

from eta_rxncat.core import MolecularState
from eta_rxncat.engines import EngineRuntimeError, RawResult, RDKitFFEngine
from eta_rxncat.optimize import GeometricOptimizer, OptimizationFailedError


class CwdSpy(RDKitFFEngine):
    """UFF that records the working directory of each call and writes a file into it."""

    def __init__(self, error_at: int | None = None, error: BaseException | None = None) -> None:
        """Raise ``error`` from call ``error_at`` (default the first) onward."""
        super().__init__(UFF_STAGE)
        self.directories: list[str] = []
        self.error_at = error_at
        self.error = error

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self.directories.append(os.getcwd())
        Path("HT.v_spy.txt").write_text("scratch", encoding="utf-8")
        if self.error is not None and len(self.directories) >= (self.error_at or 1):
            raise self.error
        return super()._evaluate(state, forces=forces, hessian=hessian)


@pytest.fixture
def caller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A clean caller directory and a separate ``TMPDIR``."""
    for name in ("caller", "scratch"):
        (tmp_path / name).mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_path / "scratch"))
    monkeypatch.chdir(tmp_path / "caller")
    return tmp_path / "caller"


def assert_restored(caller: Path, engine: CwdSpy) -> None:
    """The cwd is the caller's again, it is untouched and the scratch directories are gone."""
    scratch = caller.parent / "scratch"
    assert Path.cwd() == caller
    assert list(caller.iterdir()) == []
    assert engine.directories
    assert all(Path(d).parent == scratch for d in engine.directories)
    assert not any(Path(d).exists() for d in engine.directories)


def test_a_run_leaves_the_caller_directory_unchanged(caller: Path) -> None:
    """Engine calls happen under ``TMPDIR``, never in the caller's directory."""
    engine = CwdSpy()
    GeometricOptimizer().minimize(distorted_water(), engine)
    assert_restored(caller, engine)


def test_restored_after_an_engine_error(caller: Path) -> None:
    """An exception inside geomeTRIC restores the directory."""
    engine = CwdSpy(error_at=2, error=EngineRuntimeError("fake crash"))
    with pytest.raises(EngineRuntimeError):
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert_restored(caller, engine)


def test_restored_after_an_exhausted_ladder(caller: Path) -> None:
    """Every ladder step failing restores the directory."""
    engine = CwdSpy(error=not_converged())
    with pytest.raises(OptimizationFailedError):
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert len(engine.directories) == 3
    assert_restored(caller, engine)


def test_restored_after_a_base_exception(caller: Path) -> None:
    """A deadline-style ``BaseException`` restores the directory and releases the lock."""
    engine = CwdSpy(error=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert_restored(caller, engine)
    GeometricOptimizer().minimize(distorted_water(), CwdSpy())
