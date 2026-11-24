"""Tier-D tests of the Tier 3 E2E helpers (tests/e2e/t3.py; no engine)."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from e2e_env import recipe_for
from fixtures import t3
from t3 import (
    CANDIDATES_V050,
    ENERGY_SOURCE_BOUND_KCAL_MOL,
    candidate_dir,
    energy_source,
    gates,
    rmsds_to_reference,
    ts_recipe,
)

from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.optimize import PRFOOptimizer
from eta_rxncat.orchestrator import StageMetrics


def metrics(hits: int, rows: int) -> dict[str, StageMetrics]:
    """TS stage metrics with the given hits and rows on both stages."""
    return {k: StageMetrics(cache_hits=hits, rows_created=rows) for k in ("ts_opt", "frequency")}


def fake_ts(
    *,
    mode: bool = True,
    core: bool = True,
    identity: bool = True,
    hits: int = 0,
    rows: int = 1,
    e_freq: float = -100.0,
    e_grad: float = -100.0,
) -> Any:
    """A stand-in TSRunResult with the attributes the gates read."""
    validation = SimpleNamespace(
        mode_count_passed_bool=mode, active_core_passed_bool=core, identity_passed_bool=identity
    )
    record = SimpleNamespace(
        thermo=SimpleNamespace(electronic_energy_hartree=e_freq),
        search=SimpleNamespace(final_energy_hartree=e_grad),
    )
    return SimpleNamespace(
        search=object(),
        validation=validation,
        record=record,
        failed_reason=None,
        metrics=metrics(hits, rows),
        as_payload=lambda: {"search": {"history": [1], "n_steps": 3}, "metrics": {}, "x": 1},
    )


def fake_reactant(hits: int, rows: int) -> Any:
    """A stand-in SpeciesResult with one key per reactant stage."""
    stages = {
        k: StageMetrics(cache_hits=hits, rows_created=rows)
        for k in ("conformer_search", "geometry_opt", "frequency")
    }
    return SimpleNamespace(metrics=SimpleNamespace(stages=stages), keys={k: ("k",) for k in stages})


def case(ts: Any, dg: float | None, reactant_hits: int = 0, reactant_rows: int = 1) -> Any:
    """A stand-in CaseRun."""
    barrier = None if dg is None else SimpleNamespace(dG_dagger_1M_kcal_mol=dg)
    return SimpleNamespace(
        ts=ts,
        barrier=barrier,
        barrier_error=None,
        reactants={"a": fake_reactant(reactant_hits, reactant_rows)},
    )


def statuses(result: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Gate name -> status."""
    return {k: v["status"] for k, v in result.items()}


def test_all_pass_on_uma() -> None:
    """A clean UMA case inside the window passes every gate."""
    first = case(fake_ts(), 17.0)
    second = case(fake_ts(hits=1, rows=0), 17.0, reactant_hits=1, reactant_rows=0)
    assert set(statuses(gates("uma", first, second, (10.7, 24.7))).values()) == {"pass"}


def test_gfn2_reports_core_identity_and_window() -> None:
    """On GFN2 the active core, identity and window are reported, never gated (Q-TJ3)."""
    first = case(fake_ts(core=False, identity=False), 40.0)
    second = case(fake_ts(hits=1, rows=0), 40.0, reactant_hits=1, reactant_rows=0)
    result = statuses(gates("xtb", first, second, (10.7, 24.7)))
    assert (
        result["active_core"] == result["identity"] == result["window_dG_dagger_1M"] == "reported"
    )
    assert result["mode_count"] == result["search_converged"] == "pass"


@pytest.mark.parametrize(
    ("first", "second", "gate"),
    [
        (case(fake_ts(mode=False), 17.0), None, "mode_count"),
        (case(fake_ts(core=False), 17.0), None, "active_core"),
        (case(fake_ts(identity=False), 17.0), None, "identity"),
        (case(fake_ts(), 30.0), None, "window_dG_dagger_1M"),
        (case(fake_ts(), None), None, "barrier_conservation"),
        (
            case(fake_ts(), 17.0),
            case(fake_ts(hits=0, rows=1), 17.0, 1, 0),
            "second_run_ts_all_hits",
        ),
        (
            case(fake_ts(), 17.0),
            case(fake_ts(hits=1, rows=0), 17.0, 0, 1),
            "second_run_reactants_all_hits",
        ),
        (
            case(fake_ts(), 17.0),
            case(fake_ts(hits=1, rows=0), 18.0, 1, 0),
            "second_run_equal_payload",
        ),
        (case(fake_ts(e_freq=-100.0, e_grad=-100.001), 17.0), None, "energy_source_consistent"),
    ],
)
def test_each_uma_gate_fails_alone(first: Any, second: Any, gate: str) -> None:
    """Each gate fails on its own defect, the others pass."""
    second = second or case(
        fake_ts(hits=1, rows=0), first.barrier and first.barrier.dG_dagger_1M_kcal_mol, 1, 0
    )
    result = statuses(gates("uma", first, second, (10.7, 24.7)))
    assert result[gate] == "fail"


def test_energy_source_numbers() -> None:
    """The energy-source delta is frequency minus gradient energy, with the 0.01 kcal/mol bound."""
    source = energy_source(fake_ts(e_freq=-100.0, e_grad=-100.00001))
    assert source is not None
    assert source["delta_hartree"] == pytest.approx(1e-5, abs=1e-12)
    assert source["delta_kcal_mol"] == pytest.approx(1e-5 * HARTREE_KCAL_MOL)
    assert source["within_bound_bool"] is (1e-5 * HARTREE_KCAL_MOL <= ENERGY_SOURCE_BOUND_KCAL_MOL)
    assert energy_source(SimpleNamespace(record=None)) is None


def test_rmsds_of_the_reference_to_itself_are_zero() -> None:
    """The reference TS mapped onto itself has zero full, active and forming-core RMSDs."""
    fixture = t3("t3_ts1a_n_unmapped.yaml")
    rmsds = rmsds_to_reference(fixture.reference, fixture, [1, 2, 3, 5])
    assert all(v == pytest.approx(0.0, abs=1e-10) for v in rmsds.values())


def test_ts1b_n_start_maps_onto_liu() -> None:
    """The M1 start of TS1b_n mapped onto Liu's TS1b_n has a small forming-core RMSD."""
    fixture = t3("t3_ts1b_n_mapped.yaml")
    rmsds = rmsds_to_reference(fixture.start_state("xtb"), fixture, [1, 2, 3, 5])
    assert rmsds["forming_core_rmsd_angstrom"] < 0.2


@pytest.mark.parametrize("name", ["xtb", "uma"])
def test_ts_recipe_keeps_the_engine_and_uses_prfo_defaults(name: str) -> None:
    """The TS recipe has the species recipe's engine stage, runtime and thermo, and P-RFO."""
    recipe = recipe_for(name)
    ts = ts_recipe(recipe)
    assert ts.engine_stage == recipe.engine_stage
    assert dict(ts.engine_runtime) == dict(recipe.engine_runtime)
    assert ts.thermo_config == recipe.thermo_config and ts.analysis == recipe.analysis
    assert isinstance(ts.ts_optimizer, PRFOOptimizer) and dict(ts.ts_options) == {}


def test_candidate_dir_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ETA_RXNCAT_CANDIDATE_DIR redirects the candidates; the default is v0.5.0."""
    monkeypatch.setenv("ETA_RXNCAT_CANDIDATE_DIR", str(tmp_path / "c"))
    assert candidate_dir() == tmp_path / "c" and (tmp_path / "c").is_dir()
    assert CANDIDATES_V050.parts[-2:] == ("candidate_outputs", "v0.5.0")
