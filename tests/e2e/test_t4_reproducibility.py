"""Tier 4 run-to-run reproducibility: each pair and recipe twice more in fresh stores (slice 11).

The measurement behind ``proposed_regression_bounds`` (the numeric bounds are TJ's). Each run is
slice 09-10 code from scratch in its own store; the mapped pair rebuilds its grafted exo start per
run. The fragment keeps each run's per-pathway seed TS energy and geometry, member counts and
exclusions, ΔΔG‡ and the pruning branch; ``acceptance_record_v060.py`` compares them with each
other and with the acceptance run's in-process values. Nothing reads a candidate file.
"""

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from acceptance import out_dir, write_fragment
from e2e_env import RECIPE_PARAMS
from fixtures import t4
from t3 import ts_payload
from t4 import PairRun, grafted_exo_start, run_mapped_pair, run_pair

from eta_rxncat.orchestrator import Recipe

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]

PAIRS = {
    "t4_unmapped": "t4_endo_exo_unmapped.yaml",
    "t4_mapped": "t4_mapped_selectivity_pruned.yaml",
}
N_RUNS = 2
TIMEOUT_REASON = "pre_relax_failed:PreRelaxTimeout"


def run_values(first: PairRun, branch: str | None) -> dict[str, Any]:
    """One run's per-pathway seed TS energy and geometry, member counts and exclusions, ΔΔG‡."""
    assert first.score is not None, "no selectivity score"
    pathways: dict[str, Any] = {}
    for name, run in sorted(first.runs.items()):
        ts = ts_payload(run.seed_result)
        assert ts["failed_reason"] is None and ts["thermo"] and ts["state"], (name, ts)
        reasons = Counter(e.reason for e in run.ensemble.excluded)
        pathways[name] = {
            "ts_energy_hartree": ts["thermo"]["electronic_energy_hartree"],
            "ts_state": ts["state"],
            "n_members": len(run.ensemble.members),
            "exclusions_by_reason": dict(sorted(reasons.items())),
            "max_pre_relax_wall_time_s": run.max_pre_relax_wall_time_s,
        }
    return {
        "pathways": pathways,
        "ddG_dagger_kcal_mol": first.score.ddG_dagger_kcal_mol,
        "branch": branch,
    }


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
@pytest.mark.parametrize("pair", PAIRS)
def test_t4_reproducibility(
    pair: str, recipe_name: str, recipes: Callable[[str], Recipe], tmp_path: Path
) -> None:
    """Two more fresh-store runs; each must converge to a score (no number is invented)."""
    out = out_dir()
    if out is None:
        pytest.skip("ETA_RXNCAT_ACCEPTANCE_OUT is not set (acceptance record runs only)")
    recipe = recipes(recipe_name)
    fixture = t4(PAIRS[pair])
    runs: list[dict[str, Any]] = []
    for k in range(N_RUNS):
        store = tmp_path / f"fresh{k}.sqlite"
        if pair == "t4_mapped":
            exo_start, _ = grafted_exo_start(fixture, recipe)
            starts = {"endo": fixture.pathway("endo").start_state(recipe_name), "exo": exo_start}
            first = run_mapped_pair(fixture, recipe, recipe_name, store, starts)
            assert first.selectivity is not None and first.selectivity.nodes
            down = fixture.downstream
            assert down is not None
            branch = first.selectivity.nodes[down.node_id].status
        else:
            first = run_pair(fixture, recipe, recipe_name, store)
            branch = None
        runs.append(run_values(first, branch))
    timeouts = sum(
        v["exclusions_by_reason"].get(TIMEOUT_REASON, 0)
        for r in runs
        for v in r["pathways"].values()
    )
    write_fragment(
        f"repro_{pair}",
        recipe_name,
        {"pair": pair, "runs": runs, "pre_relax_timeouts": timeouts},
    )
    print(
        f"\nREPRO {pair} {recipe_name}: "
        f"{[(r['ddG_dagger_kcal_mol'], r['branch']) for r in runs]}; timeouts {timeouts}"
    )
