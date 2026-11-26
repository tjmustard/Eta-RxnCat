"""Frame capture: geomeTRIC bridge frames, accepted marking, the sink and P-RFO step geometries."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from test_optimize_geometric import FlakyUFF, distorted_water, not_converged
from test_prfo import SurfaceEngine, s1, s1_start

from eta_rxncat.core import MolecularState, OptimizationFrame, PotentialResult
from eta_rxncat.engines import ScfConvergenceError
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer, capture_frames, prfo
from eta_rxncat.optimize.geometric_impl import _mark_accepted
from eta_rxncat.orchestrator.ts import _RecordingEngine, _StepRecordError, _with_step_coordinates

PRFO_VERSION = "src-897c4e19cb4e738a"
"""The ``ts_opt`` key's optimizer version (v0.5.0 R11). Editing ``prfo.py`` changes it, which
reopens both the stage key and the step mapping of ``orchestrator/ts.py`` (mission R33)."""


# --- geomeTRIC frames ---------------------------------------------------------------------------


def test_every_evaluation_is_a_frame() -> None:
    """One frame per engine call, each carrying its geometry, energy, gradient and ladder step."""
    engine = FlakyUFF({})
    result = GeometricOptimizer().minimize(distorted_water(), engine)
    frames = result.frames
    assert frames is not None
    assert len(frames) == result.n_engine_calls == engine.calls
    assert {frame.ladder_step for frame in frames} == {"tric"}
    assert frames[0].coordinates_angstrom == pytest.approx(
        np.asarray(distorted_water().coordinates), abs=1e-8
    )
    assert frames[-1].energy_hartree == pytest.approx(result.final_energy_hartree, abs=1e-10)
    assert frames[0].max_gradient_hartree_per_bohr > frames[-1].max_gradient_hartree_per_bohr


def test_accepted_frames_of_a_real_run() -> None:
    """Every frame is judged against the step's trajectory file; the final geometry is accepted."""
    result = GeometricOptimizer().minimize(distorted_water(), FlakyUFF({}))
    assert result.frames is not None
    assert all(frame.accepted_bool is not None for frame in result.frames)
    assert result.frames[0].accepted_bool is True
    final = np.asarray(result.final_state.coordinates)
    assert any(
        frame.accepted_bool
        and np.max(np.abs(np.asarray(frame.coordinates_angstrom) - final)) <= 1e-6
        for frame in result.frames
    )


def test_ladder_step_per_frame_and_failed_steps_marked() -> None:
    """A failed step's frames keep its name and are marked before its directory is removed."""
    engine = FlakyUFF({3: not_converged()})
    result = GeometricOptimizer().minimize(distorted_water(), engine)
    assert result.frames is not None
    steps = [frame.ladder_step for frame in result.frames]
    assert steps[:2] == ["tric", "tric"]
    assert set(steps[2:]) == {"tric_tight_trust"}
    assert len(result.frames) == result.n_engine_calls - 1  # the raising call has no result
    assert result.frames[0].accepted_bool is True


@pytest.mark.parametrize(
    ("kwargs", "last"), [({}, "cartesian"), ({"frozen_atom_indices": [0]}, "hdlc")]
)
def test_sink_holds_the_frames_of_a_failed_run(kwargs: dict[str, list[int]], last: str) -> None:
    """The caller's sink has every frame when ``minimize`` raises."""
    engine = FlakyUFF({2: not_converged(), 4: not_converged(), 6: not_converged()})
    with capture_frames() as frames, pytest.raises(Exception, match="did not converge"):
        GeometricOptimizer().minimize(distorted_water(), engine, **kwargs)  # type: ignore[arg-type]
    assert [frame.ladder_step for frame in frames] == ["tric", "tric_tight_trust", last]


def test_sink_holds_frames_when_the_engine_raises() -> None:
    """An engine error propagates and the frames before it are kept."""
    engine = FlakyUFF({3: ScfConvergenceError("fake", steps=("diis",))})
    with capture_frames() as frames, pytest.raises(ScfConvergenceError):
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert len(frames) == 2


def test_result_frames_are_only_this_run() -> None:
    """Two runs in one sink: each result carries its own frames, the sink all of them."""
    with capture_frames() as frames:
        first = GeometricOptimizer().minimize(distorted_water(), FlakyUFF({}))
        second = GeometricOptimizer().minimize(distorted_water(), FlakyUFF({}))
    assert first.frames is not None and second.frames is not None
    assert len(frames) == len(first.frames) + len(second.frames)
    third = GeometricOptimizer().minimize(distorted_water(), FlakyUFF({}))
    assert len(frames) == len(first.frames) + len(second.frames)  # the sink is closed
    assert third.frames is not None


# --- accepted marking ---------------------------------------------------------------------------


def frame_at(x: float) -> OptimizationFrame:
    """Return a two-atom frame whose second atom sits at ``x``."""
    return OptimizationFrame(
        coordinates_angstrom=[[0.0, 0.0, 0.0], [x, 0.0, 0.0]],
        energy_hartree=-1.0,
        max_gradient_hartree_per_bohr=0.1,
        ladder_step="tric",
    )


def write_xyz(path: Path, xs: Sequence[float]) -> Path:
    """Write a multi-frame XYZ file of ``frame_at`` geometries."""
    blocks = [f"2\nIteration {i}\nH 0.0 0.0 0.0\nH {x:.12f} 0.0 0.0\n" for i, x in enumerate(xs)]
    path.write_text("".join(blocks), encoding="utf-8")
    return path


def marks(xs: Sequence[float], written: Sequence[float], tmp_path: Path) -> list[bool | None]:
    """Mark frames at ``xs`` from a file holding ``written``."""
    frames = [frame_at(x) for x in xs]
    _mark_accepted(frames, 0, write_xyz(tmp_path / "optim.xyz", written))
    return [frame.accepted_bool for frame in frames]


def test_matches_are_accepted_in_order(tmp_path: Path) -> None:
    """File frames match the first later evaluated frame within 1e-6 A."""
    assert marks([0.7, 0.8, 0.9, 1.0], [0.7 + 5e-11, 0.9, 1.0], tmp_path) == [
        True,
        False,
        True,
        True,
    ]
    assert marks([0.7, 0.7, 0.8], [0.7], tmp_path) == [True, False, False]


def test_only_the_steps_frames_are_marked(tmp_path: Path) -> None:
    """Frames of earlier steps are untouched."""
    frames = [frame_at(0.7), frame_at(0.8), frame_at(0.9)]
    _mark_accepted(frames, 1, write_xyz(tmp_path / "optim.xyz", [0.9]))
    assert [frame.accepted_bool for frame in frames] == [None, False, True]


@pytest.mark.parametrize("written", [[0.7, 0.8 + 5e-4], [0.8, 0.7], [float("nan")]])
def test_an_unmatched_file_frame_leaves_none(written: list[float], tmp_path: Path) -> None:
    """A file frame without a match (too far, out of order, NaN) judges nothing."""
    assert marks([0.7, 0.8], written, tmp_path) == [None, None]


@pytest.mark.parametrize(
    "text", [None, "", "junk\n", "2\nc\nH 0 0 0\n", "3\nc\nH 0 0 0\nH 1 0 0\nH 2 0 0\n", "-2\nc\n"]
)
def test_a_missing_or_unreadable_file_leaves_none(text: str | None, tmp_path: Path) -> None:
    """A missing or unparseable file never raises and judges nothing."""
    path = tmp_path / "optim.xyz"
    if text is not None:
        path.write_text(text, encoding="utf-8")
    frames = [frame_at(0.7)]
    _mark_accepted(frames, 0, path)
    assert frames[0].accepted_bool is None


# --- P-RFO step geometries ----------------------------------------------------------------------


class SpyEngine(SurfaceEngine):
    """``SurfaceEngine`` that also keeps the geometry of every ``hessian=False`` evaluation."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Start with no recorded geometry."""
        super().__init__(*args, **kwargs)
        self.trials: list[list[list[float]]] = []

    def evaluate(
        self, state: MolecularState, *, forces: bool = True, hessian: bool = False
    ) -> PotentialResult:
        """Keep the trial geometry, then evaluate."""
        if not hessian:
            self.trials.append(state.coordinates)
        return super().evaluate(state, forces=forces, hessian=hessian)


def search_with_a_rejection() -> tuple[SpyEngine, _RecordingEngine, object]:
    """Run P-RFO on S1 with one forced rejection (and so one exact refresh)."""
    model = s1()
    spy = SpyEngine(model.evaluate, trial_energy_offset=1.0, offset_calls=frozenset({4}))
    recorder = _RecordingEngine(spy)
    result = PRFOOptimizer().find_saddle(model.state(s1_start()), recorder, forming_bonds=[(0, 3)])
    return spy, recorder, result


def test_step_coordinates_are_the_trial_geometries() -> None:
    """The k-th ``hessian=False`` evaluation is step k, across a rejection and a refresh."""
    spy, recorder, result = search_with_a_rejection()
    assert result.n_rejected_steps >= 1 and result.n_hessian_refreshes >= 1  # type: ignore[attr-defined]
    filled = _with_step_coordinates(result, recorder.frames)  # type: ignore[arg-type]
    assert len(filled.history) == len(spy.trials) == len(recorder.frames)
    assert [step.coordinates_angstrom for step in filled.history] == spy.trials
    stripped = [s.model_copy(update={"coordinates_angstrom": None}) for s in filled.history]
    assert stripped == result.history  # type: ignore[attr-defined]


def test_a_shifted_or_longer_record_is_a_code_fault() -> None:
    """A records list shifted by one, or with an extra record, raises the mapping error."""
    _, recorder, result = search_with_a_rejection()
    frames = recorder.frames
    shifted = frames[1:] + frames[:1]
    for bad in (shifted, [*frames, frames[-1]], frames[:-1]):
        with pytest.raises(_StepRecordError):
            _with_step_coordinates(result, bad)  # type: ignore[arg-type]
    assert issubclass(_StepRecordError, RuntimeError)


def test_prfo_source_identity_is_pinned() -> None:
    """``prfo.py`` is unedited: its bytes key ``ts_opt`` and fix the call order mapped above."""
    assert prfo._source_identity().version == PRFO_VERSION
