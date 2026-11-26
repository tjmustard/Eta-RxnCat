"""Tests for the ensemble guards (v0.7.0, slice 05): pathway face, stall cap and orientation.

Reuses the stub surface of ``test_ts_ensemble`` (TS1a_n, scripted fates per sample).
"""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from test_ts_ensemble import (
    CORE,
    FORMING,
    OPTIONS,
    REACTANTS,
    TagRelax,
    gates,
    reasons,
    recipe,
    saddle_coordinates,
    seed_spec,
    tag_engine,
    tag_of,
)

import eta_rxncat.orchestrator.ts_ensemble as module
from eta_rxncat.core import MolecularState
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.orchestrator import run_ts_ensemble, run_ts_ensemble_detailed
from eta_rxncat.orchestrator._deadline import PreRelaxTimeout
from eta_rxncat.store import ArtifactStore

__all__ = ["tag_engine"]  # the autouse fixture that routes xtb_subprocess to the tag engine

TIMEOUT = "pre_relax_failed:PreRelaxTimeout"


class StallingRelax(TagRelax):
    """A minimizer whose ``pre_timeout`` calls raise the deadline signal at once."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Raise ``PreRelaxTimeout`` for a ``pre_timeout`` tag, else behave as ``TagRelax``."""
        tag = self.script[self.calls] if self.calls < len(self.script) else "A"
        if tag == "pre_timeout":
            self.calls += 1
            raise PreRelaxTimeout
        return super().minimize(state, engine, **kwargs)


def run(path: Path, relax: TagRelax, *, seed_tag: str = "seed", **kwargs: Any) -> Any:
    """Run the detailed ensemble once."""
    with ArtifactStore(path) as store:
        return run_ts_ensemble_detailed(
            seed_spec(seed_tag),
            recipe(),
            store,
            optimizer=relax,
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=OPTIONS,
            member_gates=gates,
            **kwargs,
        )


# --- R2: the pathway face ------------------------------------------------------------------------


def test_the_pathway_face_matches(tmp_path: Path) -> None:
    """The seed's own face passes."""
    result = run(tmp_path / "s.sqlite", TagRelax(), expected_face=(1, 1))
    assert result.ensemble.failed_reason is None


def test_another_face_fails_the_pathway_before_sampling(tmp_path: Path) -> None:
    """A seed of the other face: ``seed:face_mismatch_pathway``, nothing sampled."""
    relax = TagRelax()
    result = run(tmp_path / "s.sqlite", relax, expected_face=(-1, -1))
    assert result.ensemble.failed_reason == "seed:face_mismatch_pathway"
    assert result.ensemble.members == [] and relax.calls == 0


# --- R6: the stall cap ---------------------------------------------------------------------------

SCRIPT = ["B", "pre_timeout", "A", "pre_timeout", "B", "pre_timeout"]


def test_the_cap_stops_sampling_after_two_timeouts(tmp_path: Path) -> None:
    """US-016: two timeouts stop sampling; the members stay; the run says the cap was reached."""
    relax = StallingRelax(SCRIPT)
    result = run(tmp_path / "s.sqlite", relax, max_pre_relax_timeouts=2)
    assert result.stall_cap_reached_bool
    assert relax.calls == 4
    assert reasons(result.ensemble) == {2: TIMEOUT, 4: TIMEOUT}
    assert result.ensemble.failed_reason is None
    assert [m.index for m in result.ensemble.members] == [0, 1]


def test_no_cap_samples_everything(tmp_path: Path) -> None:
    """``None`` is v0.6.0: every sample is tried and the flag stays False."""
    relax = StallingRelax(SCRIPT)
    result = run(tmp_path / "s.sqlite", relax)
    assert not result.stall_cap_reached_bool
    assert relax.calls == OPTIONS.max_research
    assert reasons(result.ensemble) == {2: TIMEOUT, 4: TIMEOUT, 6: TIMEOUT}


def test_a_cached_run_reaches_the_same_cap(tmp_path: Path) -> None:
    """The cap counts cached timeout rows, so a rerun is equal and free."""
    path = tmp_path / "s.sqlite"
    first = run(path, StallingRelax(SCRIPT), max_pre_relax_timeouts=2)
    relax = StallingRelax(SCRIPT)
    second = run(path, relax, max_pre_relax_timeouts=2)
    assert relax.calls == 0 and second.stall_cap_reached_bool
    assert second.ensemble == first.ensemble
    assert second.total_pre_relax_wall_time_s == first.total_pre_relax_wall_time_s


def test_a_cap_below_one_is_refused(tmp_path: Path) -> None:
    """Zero is not a cap."""
    with pytest.raises(ValueError, match="max_pre_relax_timeouts"):
        run(tmp_path / "s.sqlite", TagRelax(), max_pre_relax_timeouts=0)


def test_the_plain_entry_point_takes_the_guards(tmp_path: Path) -> None:
    """``run_ts_ensemble`` passes the three keywords on."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        ensemble = run_ts_ensemble(
            seed_spec(),
            recipe(),
            store,
            optimizer=StallingRelax(SCRIPT),
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=OPTIONS,
            member_gates=gates,
            expected_face=(1, 1),
            max_pre_relax_timeouts=1,
            orientation_centers=(6,),
        )
    assert reasons(ensemble) == {2: TIMEOUT}


# --- R24: orientation ----------------------------------------------------------------------------

BONDS = perceive_bonds(
    seed_spec().start.model_copy(update={"coordinates": saddle_coordinates("A").tolist()})
)
CENTER = 6


def neighbours(center: int) -> list[int]:
    """Return a centre's neighbours in the seed's bonds, ascending."""
    return sorted(j if i == center else i for i, j in BONDS if center in (i, j))


def swapped_saddle() -> np.ndarray:
    """The seed's saddle with two substituents of the centre exchanged (R/H swap)."""
    xyz = saddle_coordinates("A")
    hydrogens = [n for n in neighbours(CENTER) if seed_spec().start.symbols[n] == "H"]
    assert len(hydrogens) == 2
    out = xyz.copy()
    out[hydrogens[0]], out[hydrogens[1]] = xyz[hydrogens[1]], xyz[hydrogens[0]]
    return out


def test_the_swap_moves_a_judged_neighbour() -> None:
    """The swap is judged: a swapped hydrogen is among the centre's three lowest neighbours."""
    low = neighbours(CENTER)[:3]
    hydrogens = [n for n in neighbours(CENTER) if seed_spec().start.symbols[n] == "H"]
    assert len(low) == 3
    assert set(hydrogens) & set(low)


def test_a_swapped_centre_is_excluded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A member with R and H exchanged at the centre is ``orientation_mismatch``."""
    import test_ts_ensemble

    real = test_ts_ensemble.saddle_coordinates
    monkeypatch.setattr(
        test_ts_ensemble,
        "saddle_coordinates",
        lambda tag: swapped_saddle() if tag == "swap" else real(tag),
    )
    # The swapped geometry has the same bonds and face, so only the orientation check can fail it.
    swapped = seed_spec().start.model_copy(update={"coordinates": swapped_saddle().tolist()})
    assert sorted(perceive_bonds(swapped)) == sorted(BONDS)
    assert module.forming_bond_configuration(swapped, FORMING, BONDS) == (1, 1)

    with_check = run(tmp_path / "a.sqlite", TagRelax(["swap"]), orientation_centers=(CENTER,))
    assert reasons(with_check.ensemble) == {1: "orientation_mismatch"}
    assert [m.index for m in with_check.ensemble.members] == [0]
    without = run(tmp_path / "b.sqlite", TagRelax(["swap"]))
    assert 1 not in reasons(without.ensemble)


def test_the_face_check_precedes_orientation(tmp_path: Path) -> None:
    """A member of the wrong face is ``face_mismatch`` even if a centre is asked for."""
    result = run(tmp_path / "s.sqlite", TagRelax(["X"]), orientation_centers=(CENTER,))
    assert reasons(result.ensemble)[1] == "face_mismatch"


@pytest.mark.parametrize(
    "centers, message", [((99,), "out of range"), ((12,), "needs 3")], ids=["range", "terminal"]
)
def test_a_bad_centre_is_refused(tmp_path: Path, centers: tuple[int, ...], message: str) -> None:
    """A centre out of range, or with fewer than three neighbours, is refused."""
    if message == "needs 3":
        assert len(neighbours(centers[0])) < 3
    with pytest.raises(ValueError, match=message):
        run(tmp_path / "s.sqlite", TagRelax(), orientation_centers=centers)


def test_tag_of_is_the_stub_surface() -> None:
    """Guard against the helper import drifting."""
    assert tag_of(seed_spec("B").start) == "B"
