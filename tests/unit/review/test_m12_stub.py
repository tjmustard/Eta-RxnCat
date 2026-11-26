"""The M12 stub file is the canonical bytes of the stub, and holds the known answers."""

import math

from m12_stub import (
    HOSTILE_CANDIDATE,
    HOSTILE_FILE,
    STUB_PATH,
    TRAJECTORY_C1_X,
    m12_stub,
)
from review_helpers import HOSTILE

from eta_rxncat.review import canonical_run_data_json, read_run_data


def test_the_stub_file_is_the_canonical_bytes() -> None:
    """The committed file is what the helper writes."""
    assert STUB_PATH.read_bytes() == canonical_run_data_json(m12_stub())


def test_the_stretch_moves_only_the_named_bond_in_opposite_directions() -> None:
    """The one imaginary mode moves atoms 0 and 1 apart along the bond, and no other atom."""
    run_data = read_run_data(STUB_PATH.read_bytes())
    (entry,) = [f for f in run_data.frequencies if f.frequency_id == "frequency:stretch"]
    assert entry.status == "completed" and entry.n_imaginary == 1
    moves = entry.imaginary_modes[0].displacements_angstrom
    assert moves[0][0] < 0 < moves[1][0]
    assert moves[0] == [-moves[1][0], 0.0, 0.0]
    assert all(m == [0.0, 0.0, 0.0] for m in moves[2:])
    assert math.isclose(math.hypot(*[x for m in moves for x in m]), 1.0, abs_tol=1e-9)


def test_the_trajectory_the_two_modes_and_the_hostile_strings() -> None:
    """The three frames, the two-mode state and the hostile strings are as stated."""
    run_data = read_run_data(STUB_PATH.read_bytes())
    trajectories = {t.trajectory_id: t for t in run_data.trajectories}
    three = trajectories["ts_search:three_frames"]
    assert three.status == "stored"
    assert [f.coordinates_angstrom[1][0] for f in three.frames] == list(TRAJECTORY_C1_X)
    counts = {f.frequency_id: f.n_imaginary for f in run_data.frequencies if f.status != "missing"}
    assert counts["frequency:two_modes"] == 2
    assert HOSTILE in {s.label for s in run_data.species}
    assert HOSTILE_CANDIDATE in {c.candidate_id for c in run_data.candidates}
    assert run_data.provenance.store_file_name == HOSTILE_FILE
