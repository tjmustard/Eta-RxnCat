"""Tier 3 run-to-run reproducibility: each case and recipe twice more in fresh stores (slice 12).

The measurement behind ``proposed_regression_bounds`` (v0.3.0 R1 "R1. A": the numeric bounds are
TJ's). Each run is slice 08-10 code from scratch in its own store, with the same start as the
acceptance run (TS4a: the grafted, pre-relaxed start rebuilt per run). The fragment keeps each
run's TS energy, ΔG‡(1 M) and TS geometry; ``acceptance_record_v050.py`` compares them with each
other and with the acceptance run's in-process values. GFN2 TS4a is report-only (R32) and has no
converged TS, so it is not run here; the record gives it ``n/a`` with that reason. Nothing reads a
candidate file.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from acceptance import out_dir, write_fragment
from e2e_env import RECIPE_PARAMS
from fixtures import t3
from t3 import grafted_start, run_case

from eta_rxncat.orchestrator import Recipe

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]

CASES = {
    "ts1a_n": ("t3_ts1a_n_unmapped.yaml", [1, 2, 3, 5]),
    "ts1b_n": ("t3_ts1b_n_mapped.yaml", [1, 2, 3, 5]),
    "ts3a": ("t3_ts3a_unmapped.yaml", [0, 3, 6, 7]),
    "ts4a": ("t3_ts4a_mapped.yaml", [0, 3, 6, 7]),
    "n4": ("t3_n4_unmapped.yaml", [1, 2, 9, 10]),
}
"""Case: (fixture YAML, forming core) as in the slice 08-10 tests."""
REPORT_ONLY = {("xtb", "ts4a")}
"""R32 (TJ Q-TJ4 A): GFN2 TS4a has no converged TS; its reproducibility is n/a."""
N_RUNS = 2


def pairs() -> list[Any]:
    """Every recipe x case except the report-only pair (never a skip: it is not collected)."""
    out = []
    for param in RECIPE_PARAMS:
        recipe = param.values[0]
        for case in CASES:
            if (recipe, case) not in REPORT_ONLY:
                out.append(pytest.param(recipe, case, marks=param.marks, id=f"{recipe}-{case}"))
    return out


@pytest.mark.parametrize(("recipe_name", "case"), pairs())
def test_t3_reproducibility(
    recipe_name: str,
    case: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
) -> None:
    """Two more fresh-store runs; both must converge to a barrier (no number is invented)."""
    out = out_dir()
    if out is None:
        pytest.skip("ETA_RXNCAT_ACCEPTANCE_OUT is not set (acceptance record runs only)")
    recipe = recipes(recipe_name)
    name, forming_core = CASES[case]
    fixture = t3(name)
    runs: list[dict[str, Any]] = []
    for k in range(N_RUNS):
        start = grafted_start(fixture, recipe, forming_core)[0] if case == "ts4a" else None
        run = run_case(fixture, recipe, recipe_name, tmp_path / f"fresh{k}.sqlite", start)
        ts = run.ts
        assert ts.failed_reason is None, f"run {k}: {ts.failed_reason}"
        assert ts.record is not None and ts.search is not None and run.barrier is not None, (
            f"run {k}: no record or barrier ({run.barrier_error})"
        )
        runs.append(
            {
                "ts_energy_hartree": ts.record.thermo.electronic_energy_hartree,
                "dG_dagger_1M_kcal_mol": run.barrier.dG_dagger_1M_kcal_mol,
                "ts_state": ts.search.final_state.model_dump(mode="json"),
            }
        )
    write_fragment(f"repro_{case}", recipe_name, {"case": case, "runs": runs})
    print(
        f"\nREPRO {case} {recipe_name}: "
        f"{[(r['ts_energy_hartree'], r['dG_dagger_1M_kcal_mol']) for r in runs]}"
    )
