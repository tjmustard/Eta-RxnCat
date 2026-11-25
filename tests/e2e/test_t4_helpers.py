"""Offline tests of the Tier 4 E2E helpers (slice 09): member gates, gates, regression, paths."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fixtures import t4
from t4 import (
    candidate_dir,
    exclusions_by_reason,
    gates,
    member_gates,
    reactant_key,
    regression_endo_seed,
    second_run_all_hits,
)

from eta_rxncat.core import SelectivityResult, TSEnsemble
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import BarrierEnergies, StageMetrics, TSEnsembleRun

from t4 import PairRun  # isort: skip

FIXTURE = t4("t4_endo_exo_unmapped.yaml")


# --- member gates (Q-TJ4 A) --------------------------------------------------------------------


def validation(**overrides: Any) -> SimpleNamespace:
    """A stand-in for ``TSValidation`` with the fields the member gates read."""
    values: dict[str, Any] = {
        "mode_count_passed_bool": True,
        "active_core_passed_bool": True,
        "identity_passed_bool": True,
        "forming_stretch_overlap": 0.8,
        "forming_bonds_in_phase_bool": True,
        "options": SimpleNamespace(min_forming_stretch_overlap=0.5),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def run_of(**overrides: Any) -> Any:
    """A stand-in for ``TSRunResult``."""
    return SimpleNamespace(validation=validation(**overrides))


def test_gfn2_member_gates_use_the_identity_core_not_the_full_identity() -> None:
    """GFN2: mode count, active core, overlap >= threshold and in phase; ``identity`` is ignored."""
    gate = member_gates("xtb")
    assert all(gate(run_of()).values())
    assert set(gate(run_of())) == {
        "mode_count",
        "active_core",
        "forming_overlap",
        "forming_in_phase",
    }
    assert all(gate(run_of(identity_passed_bool=False)).values())  # distance window not gated
    assert not gate(run_of(forming_stretch_overlap=0.49))["forming_overlap"]
    assert gate(run_of(forming_stretch_overlap=0.5))["forming_overlap"]
    assert not gate(run_of(forming_stretch_overlap=None))["forming_overlap"]
    assert not gate(run_of(forming_bonds_in_phase_bool=False))["forming_in_phase"]
    assert not gate(run_of(forming_bonds_in_phase_bool=None))["forming_in_phase"]
    assert not gate(run_of(mode_count_passed_bool=False))["mode_count"]
    assert not gate(run_of(active_core_passed_bool=False))["active_core"]


def test_uma_member_gates_use_the_full_identity() -> None:
    """UMA: mode count, active core and the full identity."""
    gate = member_gates("uma")
    assert set(gate(run_of())) == {"mode_count", "active_core", "identity"}
    assert all(gate(run_of()).values())
    assert not gate(run_of(identity_passed_bool=False))["identity"]
    assert all(gate(run_of(forming_stretch_overlap=0.1)).values())  # the overlap is not a UMA gate


def test_a_run_without_validation_fails_its_gate() -> None:
    """No validation (a failed search) is a failed gate, never a silent pass."""
    result = SimpleNamespace(validation=None)
    assert member_gates("xtb")(result) == {"validation": False}
    assert member_gates("uma")(result) == {"validation": False}


def test_reactant_key_is_sorted_smiles_and_counts() -> None:
    """The ensembles' reactant key: sorted ``(SMILES, 1)`` pairs."""
    assert reactant_key(FIXTURE) == (("C1=CC1", 1), ("C1=CCC=C1", 1))


# --- gates -------------------------------------------------------------------------------------

G0 = -310.4
SHA = "d" * 64


def ensemble(pathway: str, g: float, **overrides: Any) -> TSEnsemble:
    """A one-member ensemble."""
    data: dict[str, Any] = {
        "pathway": pathway,
        "temperature_k": 298.15,
        "reactant_key": [["C1=CC1", 1], ["C1=CCC=C1", 1]],
        "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
        "members": [
            {
                "index": 0,
                "source": "seed",
                "start_sha256": SHA,
                "G_hartree": g,
                "degeneracy": 1,
                "rmsd_to_seed_angstrom": 0.0,
                "face": [1, 1],
                "validation_passed_bool": True,
                "weight": 1.0,
            }
        ],
        "G_pathway_hartree": g,
    }
    data.update(overrides)
    return TSEnsemble.model_validate(data)


def metrics(rows: int = 0, calls: int = 0, hits: int = 3) -> dict[str, StageMetrics]:
    """Stage metrics for the three ensemble stage kinds."""
    return {
        k: StageMetrics(wall_time_s=1.0, engine_calls=calls, cache_hits=hits, rows_created=rows)
        for k in ("constrained_preopt", "ts_opt", "frequency")
    }


def score(ddg: float, major: str = "endo") -> SelectivityResult:
    """A two-pathway result with the given gap."""
    minor = "exo" if major == "endo" else "endo"
    return SelectivityResult.model_validate(
        {
            "ddG_dagger_kcal_mol": ddg,
            "signed_ddG_dagger_kcal_mol": {"exo_vs_endo": ddg if major == "endo" else -ddg},
            "ratio": 2.0,
            "selectivity_percent": 10.0,
            "kind": "de",
            "major_pathway": major,
            "temperature_k": 298.15,
            "per_pathway": {
                p: {"G_pathway_hartree": G0, "n_members": 1, "n_excluded": 0, "fraction": 0.5}
                for p in (major, minor)
            },
        }
    )


def barrier(g_1m: float) -> BarrierEnergies:
    """A barrier with the given 1 M free energy."""
    return BarrierEnergies(
        dE_dagger_kcal_mol=1.0,
        dH_dagger_kcal_mol=1.0,
        dG_dagger_1atm_kcal_mol=g_1m + 1.9,
        dG_dagger_1M_kcal_mol=g_1m,
        delta_n=-1,
    )


def ensemble_barriers_stub(endo: float, exo: float) -> dict[str, dict[str, float] | None]:
    """Ensemble-based per-pathway barriers (1 M) as ``run_pair`` builds them."""
    return {
        "endo": {"dG_dagger_1M_kcal_mol": endo, "dG_dagger_1atm_kcal_mol": endo + 1.9},
        "exo": {"dG_dagger_1M_kcal_mol": exo, "dG_dagger_1atm_kcal_mol": exo + 1.9},
    }


def pair(
    ddg: float = 4.0,
    *,
    major: str = "endo",
    exo_extra: dict[str, Any] | None = None,
    run_metrics: dict[str, StageMetrics] | None = None,
    exo_ensemble: TSEnsemble | None = None,
) -> PairRun:
    """A synthetic pair run."""
    endo = ensemble("endo", G0)
    exo = exo_ensemble or ensemble("exo", G0 + ddg / HARTREE_KCAL_MOL, **(exo_extra or {}))
    runs = {
        "endo": TSEnsembleRun(endo, run_metrics or metrics(), None),  # type: ignore[arg-type]
        "exo": TSEnsembleRun(exo, run_metrics or metrics(), None),  # type: ignore[arg-type]
    }
    return PairRun(
        reactants={},
        runs=runs,
        score=score(ddg, major),
        barriers={"endo": barrier(20.0), "exo": barrier(20.0 + ddg)},
        barrier_errors={},
        ensemble_barriers=ensemble_barriers_stub(20.0, 20.0 + ddg),
    )


def statuses(recipe: str, first: PairRun, second: PairRun | None = None, reg: str = "pass") -> Any:
    """The gates' statuses."""
    out = gates(recipe, FIXTURE, first, second or pair(), {"status": reg})
    return {k: v["status"] for k, v in out.items()}


def test_all_gates_pass_on_a_good_pair() -> None:
    """Both recipes pass a pair whose summed ddG is 4.0 kcal/mol with endo major."""
    for recipe in ("xtb", "uma"):
        got = statuses(recipe, pair(4.0))
        assert {v for k, v in got.items() if k != "window_ddG_dagger"} == {"pass"}, got
    assert statuses("uma", pair(4.0))["window_ddG_dagger"] == "pass"
    assert statuses("xtb", pair(4.0))["window_ddG_dagger"] == "reported"


@pytest.mark.parametrize("ddg", [0.5, 0.4])
def test_ddg_must_exceed_half_a_kcal_strictly(ddg: float) -> None:
    """Both engines: > 0.5 strictly."""
    for recipe in ("xtb", "uma"):
        assert statuses(recipe, pair(ddg))["ddG_dagger_above_0_5"] == "fail"
    assert statuses("xtb", pair(0.51))["ddG_dagger_above_0_5"] == "pass"


@pytest.mark.parametrize(
    ("ddg", "uma_status"), [(2.29, "fail"), (2.3, "pass"), (6.3, "pass"), (6.31, "fail")]
)
def test_uma_window_ends_are_inclusive_and_gfn2_never_gates_one(
    ddg: float, uma_status: str
) -> None:
    """UMA [2.3, 6.3] inclusive (to float precision); GFN2 always ``reported``."""
    first = pair(ddg)
    assert statuses("uma", first)["window_ddG_dagger"] == uma_status
    assert statuses("xtb", first)["window_ddG_dagger"] == "reported"


def test_endo_must_be_major() -> None:
    """The computed major is endo, whatever else holds."""
    assert statuses("uma", pair(4.0, major="exo"))["endo_is_major"] == "fail"


def test_engine_error_and_face_mismatch_exclusions_fail() -> None:
    """Any ``engine_error`` or ``face_mismatch`` exclusion fails G5; other reasons only report."""

    def with_exclusion(reason: str) -> PairRun:
        excluded = [{"index": 3, "source": "perturb:2", "reason": reason}]
        return pair(exo_ensemble=ensemble("exo", G0 + 4.0 / HARTREE_KCAL_MOL, excluded=excluded))

    assert statuses("xtb", with_exclusion("engine_error"))["no_engine_error_exclusions"] == "fail"
    assert statuses("xtb", with_exclusion("face_mismatch"))["no_face_mismatch_exclusions"] == "fail"
    other = statuses("xtb", with_exclusion("outside_window"))
    assert other["no_engine_error_exclusions"] == other["no_face_mismatch_exclusions"] == "pass"
    assert exclusions_by_reason(with_exclusion("engine_error").ensembles["exo"]) == {
        "engine_error": 1
    }


def test_a_failed_seed_fails_the_gate() -> None:
    """An ensemble that failed (seed:<reason>) fails the seed gate."""
    failed = TSEnsemble.model_validate(
        {
            "pathway": "exo",
            "temperature_k": 298.15,
            "reactant_key": [["C1=CC1", 1], ["C1=CCC=C1", 1]],
            "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
            "failed_reason": "seed:ts_search_failed:max_steps",
        }
    )
    first = pair(exo_ensemble=failed)
    assert statuses("xtb", first)["seeds_converge_and_pass_member_gates"] == "fail"


def test_regression_status_is_carried_through() -> None:
    """The endo-seed regression's status is a gate."""
    assert statuses("xtb", pair(), reg="fail")["regression_endo_seed"] == "fail"
    assert (
        statuses("xtb", pair(), reg="pending_promotion")["regression_endo_seed"]
        == "pending_promotion"
    )


def test_per_pathway_difference_is_gated_only_for_single_member_pathways() -> None:
    """Single-member pathways: the per-pathway dG difference equals ddG (1e-9); else reported."""
    assert statuses("xtb", pair(4.0))["per_pathway_dG_difference_equals_ddG"] == "pass"
    off = pair(4.0)
    off = PairRun(
        off.reactants, off.runs, off.score, {"endo": barrier(20.0), "exo": barrier(23.0)}, {}
    )
    assert statuses("xtb", off)["per_pathway_dG_difference_equals_ddG"] == "fail"
    two = ensemble("exo", G0 + 4.0 / HARTREE_KCAL_MOL)
    extra = two.members[0].model_copy(update={"index": 1, "weight": 0.5})
    multi = two.model_copy(
        update={"members": [two.members[0].model_copy(update={"weight": 0.5}), extra]}
    )
    assert (
        statuses("xtb", pair(exo_ensemble=multi))["per_pathway_dG_difference_equals_ddG"]
        == "reported"
    )


def test_second_run_must_hit_every_stage_and_write_nothing() -> None:
    """G7: rows, engine calls or a stage without hits in the second run fail the gate."""
    assert second_run_all_hits(pair())
    assert not second_run_all_hits(pair(run_metrics=metrics(rows=1)))
    assert not second_run_all_hits(pair(run_metrics=metrics(calls=2)))
    assert not second_run_all_hits(pair(run_metrics=metrics(hits=0)))
    assert (
        statuses("xtb", pair(), pair(run_metrics=metrics(rows=1)))["second_run_ensembles_all_hits"]
        == "fail"
    )
    assert statuses("xtb", pair(4.0), pair(4.5))["second_run_equal_ensembles_and_score"] == "fail"


# --- regression against the promoted v0.5.0 fixture --------------------------------------------


def ts_block(g: float, e: float = -310.0) -> dict[str, Any]:
    """The pieces of a candidate's ``ts`` block the regression reads."""
    return {
        "state": {
            "symbols": ["C", "C", "C", "C", "H"],
            "coordinates": [[0, 0, 0], [1.5, 0, 0], [0, 1.5, 0], [0, 0, 1.5], [2.0, 2.0, 2.0]],
        },
        "thermo": {"electronic_energy_hartree": e, "gibbs_free_energy_hartree": g},
    }


def promoted(tmp_path: Path, recipe: str) -> Path:
    """A promoted ``t3_ts1a_n.<recipe>.json`` stand-in."""
    path = tmp_path / f"t3_ts1a_n.{recipe}.json"
    path.write_text(
        json.dumps({"ts": ts_block(-310.43), "barrier": {"dG_dagger_1M_kcal_mol": 17.7}}),
        encoding="utf-8",
    )
    return tmp_path


def payload(g: float, e: float = -310.0, dg: float = 17.7) -> dict[str, Any]:
    """A candidate-shaped payload for the regression."""
    return {"case": "ts1a_n", "ts": ts_block(g, e), "barrier": {"dG_dagger_1M_kcal_mol": dg}}


def test_regression_pending_without_a_promoted_fixture(tmp_path: Path) -> None:
    """No promoted fixture: ``pending_promotion`` (which fails an acceptance run)."""
    assert regression_endo_seed(payload(-310.43), "xtb", tmp_path)["status"] == "pending_promotion"


def test_regression_bounds_follow_the_recipe(tmp_path: Path) -> None:
    """GFN2 holds the TS G to 0.01 kcal/mol, UMA to 0.75; E to 1e-5 Eh."""
    same = payload(-310.43)
    assert regression_endo_seed(same, "xtb", promoted(tmp_path, "xtb"))["status"] == "pass"
    shift = 0.5 / HARTREE_KCAL_MOL
    drifted = payload(-310.43 + shift, dg=17.7)
    assert regression_endo_seed(drifted, "xtb", promoted(tmp_path, "xtb"))["status"] == "fail"
    assert regression_endo_seed(drifted, "uma", promoted(tmp_path, "uma"))["status"] == "pass"
    far = payload(-310.43 + 1.0 / HARTREE_KCAL_MOL)
    result = regression_endo_seed(far, "uma", promoted(tmp_path, "uma"))
    assert result["status"] == "fail" and "abs_delta_ts_gibbs_kcal_mol" in result["mismatches"]
    energy = regression_endo_seed(
        payload(-310.43, e=-310.0 + 2e-5), "uma", promoted(tmp_path, "uma")
    )
    assert energy["status"] == "fail"


def test_candidate_dir_defaults_to_v0_6_0_and_can_be_redirected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The write-only candidate directory, or ``ETA_RXNCAT_CANDIDATE_DIR``."""
    monkeypatch.setenv("ETA_RXNCAT_CANDIDATE_DIR", str(tmp_path / "scratch"))
    assert candidate_dir() == tmp_path / "scratch" and (tmp_path / "scratch").is_dir()
    monkeypatch.delenv("ETA_RXNCAT_CANDIDATE_DIR")
    assert candidate_dir().parts[-3:] == ("tests", "candidate_outputs", "v0.6.0") or (
        candidate_dir().parts[-2:] == ("candidate_outputs", "v0.6.0")
    )


def test_ensemble_barriers_shift_the_seed_barrier_to_the_summed_g() -> None:
    """Per-pathway barriers follow G_pathway; their difference is the score ddG."""
    from t4 import ensemble_barriers

    def run(g_pathway: float, g_seed: float) -> Any:
        record = SimpleNamespace(thermo=SimpleNamespace(gibbs_free_energy_hartree=g_seed))
        member = ensemble("x", g_pathway)
        return SimpleNamespace(ensemble=member, seed_result=SimpleNamespace(record=record))

    g_endo, g_exo = G0, G0 + 4.0 / HARTREE_KCAL_MOL
    runs = {
        "endo": run(g_endo - 3e-6, g_endo),  # the lowest member is a merged copy, not the seed
        "exo": run(g_exo - 1e-6, g_exo),
        "none": SimpleNamespace(
            ensemble=ensemble("n", G0), seed_result=SimpleNamespace(record=None)
        ),
    }
    barriers = {"endo": barrier(20.0), "exo": barrier(24.0), "none": None}
    out = ensemble_barriers(runs, barriers)  # type: ignore[arg-type]
    assert out["none"] is None
    assert out["endo"] is not None and out["exo"] is not None
    assert out["endo"]["dG_dagger_1M_kcal_mol"] == pytest.approx(20.0 - 3e-6 * HARTREE_KCAL_MOL)
    assert out["exo"]["dG_dagger_1atm_kcal_mol"] == pytest.approx(
        24.0 + 1.9 - 1e-6 * HARTREE_KCAL_MOL
    )
    difference = out["exo"]["dG_dagger_1M_kcal_mol"] - out["endo"]["dG_dagger_1M_kcal_mol"]
    assert difference == pytest.approx(4.0 + 2e-6 * HARTREE_KCAL_MOL, abs=1e-9)
