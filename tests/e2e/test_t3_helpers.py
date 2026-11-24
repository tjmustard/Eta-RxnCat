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
    overlap: float = 0.7,
    in_phase: bool = True,
    hits: int = 0,
    rows: int = 1,
    e_freq: float = -100.0,
    e_grad: float = -100.0,
    stages: tuple[str, ...] = ("ts_opt", "frequency"),
) -> Any:
    """A stand-in TSRunResult with the attributes the gates read."""
    validation = SimpleNamespace(
        mode_count_passed_bool=mode,
        active_core_passed_bool=core,
        identity_passed_bool=identity,
        forming_stretch_overlap=overlap,
        forming_bonds_in_phase_bool=in_phase,
        options=SimpleNamespace(min_forming_stretch_overlap=0.5),
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
        keys={k: "key" for k in stages},
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
    """A clean UMA case inside the window passes every gate (the GFN2-only split is reported)."""
    first = case(fake_ts(), 17.0)
    second = case(fake_ts(hits=1, rows=0), 17.0, reactant_hits=1, reactant_rows=0)
    result = statuses(gates("uma", first, second, (10.7, 24.7)))
    assert result.pop("forming_overlap") == result.pop("forming_in_phase") == "reported"
    assert set(result.values()) == {"pass"}


def test_gfn2_reports_full_identity_and_window() -> None:
    """On GFN2 the full identity (distance window) and the dG window are reported (R32)."""
    first = case(fake_ts(identity=False), 40.0)
    second = case(fake_ts(hits=1, rows=0), 40.0, reactant_hits=1, reactant_rows=0)
    result = statuses(gates("xtb", first, second, (10.7, 24.7)))
    assert result["identity"] == result["window_dG_dagger_1M"] == "reported"
    others = {v for k, v in result.items() if k not in ("identity", "window_dG_dagger_1M")}
    assert others == {"pass"}


@pytest.mark.parametrize(
    ("kwargs", "gate"),
    [
        ({"core": False}, "active_core"),
        ({"overlap": 0.3}, "forming_overlap"),
        ({"in_phase": False}, "forming_in_phase"),
    ],
)
def test_gfn2_gates_the_identity_core(kwargs: dict[str, Any], gate: str) -> None:
    """R32 (TJ Q-TJ4 A): GFN2 gates KE >= 0.60, forming overlap >= 0.50 and in phase."""
    first = case(fake_ts(**kwargs), 17.0)
    second = case(fake_ts(hits=1, rows=0, **kwargs), 17.0, reactant_hits=1, reactant_rows=0)
    assert statuses(gates("xtb", first, second, (10.7, 24.7)))[gate] == "fail"


def test_uma_reports_the_split_identity_core_and_gates_the_full_identity() -> None:
    """UMA is unchanged: full identity gated; the GFN2 overlap/phase split is reported there."""
    first = case(fake_ts(overlap=0.3, identity=False), 17.0)
    second = case(fake_ts(hits=1, rows=0), 17.0, reactant_hits=1, reactant_rows=0)
    result = statuses(gates("uma", first, second, (10.7, 24.7)))
    assert result["forming_overlap"] == result["forming_in_phase"] == "reported"
    assert result["identity"] == "fail"


def test_report_only_keeps_measured_statuses() -> None:
    """GFN2 TS4a (R32): every status is reported; what was measured is kept and summarised."""
    from t3 import reported_outcome

    first = case(fake_ts(mode=False), None)
    second = case(fake_ts(hits=1, rows=0), None, reactant_hits=1, reactant_rows=0)
    tier = gates("xtb", first, second, (0.7, 14.7), report_only=True)
    assert {v["status"] for v in tier.values()} == {"reported"}
    assert tier["mode_count"]["measured"] == "fail"
    outcome, failed = reported_outcome(tier)
    assert outcome == "failed" and "mode_count" in failed and "search_converged" not in failed


def test_second_run_after_a_failed_search_needs_only_the_ts_opt_hit() -> None:
    """R32: a cached ts_opt failure row is a hit; frequency, which never ran, is not required."""
    first = case(fake_ts(stages=("ts_opt",)), None)
    second = case(fake_ts(hits=1, rows=0, stages=("ts_opt",)), None, 1, 0)
    second.ts.metrics["frequency"].cache_hits = 0
    assert statuses(gates("xtb", first, second, (0.7, 14.7)))["second_run_ts_all_hits"] == "pass"
    extra = case(fake_ts(hits=1, rows=0), None, 1, 0)
    assert statuses(gates("xtb", first, extra, (0.7, 14.7)))["second_run_ts_all_hits"] == "fail"


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


def test_ts4a_grafts_reproduce_slice_07() -> None:
    """The helper reproduces slice 07: C7H4F6N4, 0.1462 / 0.1463 A, no contacts, core 0.0599."""
    from collections import Counter

    from t3 import ts4a_grafts

    fixture = t3("t3_ts4a_mapped.yaml")
    first, second = ts4a_grafts(fixture)
    assert Counter(second.product.symbols) == Counter({"C": 7, "H": 4, "F": 6, "N": 4})
    assert first.alignment_rmsd_angstrom == pytest.approx(0.1462, abs=1e-3)
    assert second.alignment_rmsd_angstrom == pytest.approx(0.1463, abs=1e-3)
    assert first.close_contacts == [] and second.close_contacts == []
    assert second.product.active_atom_indices == list(range(8))
    rmsds = rmsds_to_reference(second.product, fixture, [0, 3, 6, 7])
    assert rmsds["forming_core_rmsd_angstrom"] == pytest.approx(0.0599, abs=1e-3)
