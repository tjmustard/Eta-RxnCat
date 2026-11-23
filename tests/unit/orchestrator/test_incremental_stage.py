"""Incremental stages on the species runner (v0.3.0 slice 06; TJ Q4 "C"; R7).

A rerun into the same store makes no engine call; adding one single point costs exactly one call
per kept conformer and leaves every earlier row untouched.
"""

from pathlib import Path

from orchestrator_helpers import UFF_SP, butane, rows, uff_recipe

from eta_rxncat.orchestrator import SinglePoint, run_species
from eta_rxncat.store import ArtifactStore


def test_rerun_and_incremental_single_point(tmp_path: Path) -> None:
    """Rerun: 0 calls, all hits, 0 rows; + gas SP: n_kept calls, old rows unchanged."""
    path = tmp_path / "store.sqlite"
    spec, recipe = butane(), uff_recipe()
    with ArtifactStore(path) as store:
        first = run_species(spec, recipe, store)
    before = rows(path)
    assert first.metrics.engine_calls > 0
    with ArtifactStore(path) as store:
        rerun = run_species(spec, recipe, store)
    assert rerun.metrics.engine_calls == 0
    for kind, metrics in rerun.metrics.stages.items():
        assert metrics.rows_created == 0, kind
        assert metrics.cache_hits == len(rerun.keys[kind]), kind
    assert rows(path) == before

    n_kept = len(first.ensemble.records)
    with ArtifactStore(path) as store:
        added = run_species(spec, recipe, store, single_points=[SinglePoint(UFF_SP)])
    after = rows(path)
    assert added.metrics.engine_calls == n_kept
    assert added.metrics.stages["single_point"].engine_calls == n_kept
    sp_rows = {k: v for k, v in after.items() if v[0] == "single_point"}
    assert len(sp_rows) == n_kept
    assert added.metrics.stages["single_point"].rows_created == n_kept
    for key, (kind, created) in before.items():
        assert after[key] == (kind, created)
    assert set(after) - set(before) == set(sp_rows)
    for kind in ("conformer_search", "geometry_opt", "frequency"):
        assert added.keys[kind] == first.keys[kind]
    assert set(added.single_point_energies[0]) == set(range(n_kept))


def test_only_lowest_single_point(tmp_path: Path) -> None:
    """only_lowest runs the single point on the lowest-G record alone."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_species(
            butane(), uff_recipe(), store, single_points=[SinglePoint(UFF_SP, only_lowest=True)]
        )
    assert list(result.single_point_energies[0]) == [result.ensemble.lowest_index]
    assert result.metrics.stages["single_point"].engine_calls == 1
