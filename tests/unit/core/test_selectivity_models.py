"""Tests for the TS-ensemble and selectivity result models (v0.6.0, slice 02)."""

import math
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    EngineIdentity,
    PathwaySelectivity,
    PruningDecision,
    SelectivityResult,
    TSEnsemble,
    TSEnsembleExclusion,
    TSEnsembleMember,
    TSEnsembleMerge,
    TSEnsembleOptions,
)

SHA = "a" * 64


def member(index: int = 0, weight: float = 1.0, **overrides: Any) -> dict[str, Any]:
    """Return a valid member dict."""
    data: dict[str, Any] = {
        "index": index,
        "source": "seed" if index == 0 else f"perturb:{index}",
        "start_sha256": SHA,
        "G_hartree": -100.0,
        "degeneracy": 1,
        "rmsd_to_seed_angstrom": 0.0,
        "face": [1, -1],
        "validation_passed_bool": True,
        "weight": weight,
    }
    data.update(overrides)
    return data


def ensemble(**overrides: Any) -> dict[str, Any]:
    """Return a valid one-member ensemble dict."""
    data: dict[str, Any] = {
        "pathway": "endo",
        "temperature_k": 298.15,
        "reactant_key": [["C=CC=C", 1], ["C=CC=O", 1]],
        "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
        "members": [member()],
        "G_pathway_hartree": -100.0,
    }
    data.update(overrides)
    return data


def test_options_defaults_match_the_mission() -> None:
    """R16-R18: the keyed defaults."""
    options = TSEnsembleOptions()
    assert options.model_dump() == {
        "n_embed": 10,
        "n_perturb": 10,
        "perturb_sigma_angstrom": 0.3,
        "pre_dedup_rmsd_angstrom": 0.125,
        "random_seed": 42,
        "max_research": 10,
        "rmsd_dedup_angstrom": 0.125,
        "flag_dG_kcal_mol": 0.05,
        "energy_window_kcal_mol": 3.0,
        "max_automorphisms": 100000,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"n_embed": 0},
        {"n_embed": 1.5},
        {"n_embed": True},
        {"perturb_sigma_angstrom": 0.0},
        {"perturb_sigma_angstrom": math.inf},
        {"energy_window_kcal_mol": -1.0},
        {"random_seed": 1.0},
        {"surprise": 1},
    ],
)
def test_options_refuse_bad_values(overrides: dict[str, Any]) -> None:
    """Strict ints, positive finite floats, no extras."""
    with pytest.raises(ValidationError):
        TSEnsembleOptions(**overrides)


def test_valid_ensemble_round_trips() -> None:
    """A valid ensemble survives a JSON round-trip."""
    parsed = TSEnsemble.model_validate(ensemble())
    assert TSEnsemble.model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.recipe_identity == EngineIdentity(name="xtb_subprocess", version="6.8.0")


def test_weights_must_sum_to_one() -> None:
    """Two members whose weights miss 1 by more than 1e-12 are refused."""
    members = [member(0, 0.5), member(1, 0.5 + 1e-9)]
    with pytest.raises(ValidationError, match="not 1 within 1e-12"):
        TSEnsemble.model_validate(ensemble(members=members))


def test_weights_within_tolerance_accepted() -> None:
    """A 1e-13 deviation is inside the tolerance."""
    members = [member(0, 0.5), member(1, 0.5 + 1e-13)]
    assert len(TSEnsemble.model_validate(ensemble(members=members)).members) == 2


def test_duplicate_member_index_refused() -> None:
    """Member indices are unique."""
    members = [member(0, 0.5), member(0, 0.5)]
    with pytest.raises(ValidationError, match="duplicate member indices"):
        TSEnsemble.model_validate(ensemble(members=members))


def test_g_and_failed_reason_mutually_exclusive() -> None:
    """A pathway has a free energy or a failure, not both."""
    with pytest.raises(ValidationError, match="mutually exclusive"):
        TSEnsemble.model_validate(ensemble(failed_reason="no_valid_member"))


def test_failed_pathway_has_no_members_and_no_g() -> None:
    """A failed ensemble: empty members, G None, a reason."""
    failed = TSEnsemble.model_validate(
        ensemble(members=[], G_pathway_hartree=None, failed_reason="no_valid_member")
    )
    assert failed.G_pathway_hartree is None


def test_g_without_members_refused() -> None:
    """A free energy needs at least one summed member."""
    with pytest.raises(ValidationError, match="at least one summed member"):
        TSEnsemble.model_validate(ensemble(members=[]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"face": [0]},
        {"face": [2, 1]},
        {"face": []},
        {"degeneracy": 0},
        {"weight": 1.5},
        {"weight": -0.1},
        {"source": "random:3"},
        {"source": "perturb:"},
        {"start_sha256": "xyz"},
        {"G_hartree": math.nan},
        {"rmsd_to_seed_angstrom": -0.1},
        {"pre_relax_wall_time_s": -1.0},
        {"extra": 1},
    ],
)
def test_member_refuses_bad_values(overrides: dict[str, Any]) -> None:
    """Face entries are +-1; weights in [0, 1]; sources and digests are checked."""
    with pytest.raises(ValidationError):
        TSEnsembleMember.model_validate(member(**overrides))


def test_member_records_pre_relax_wall_time() -> None:
    """R25: the wall time is optional and recorded."""
    assert TSEnsembleMember.model_validate(member()).pre_relax_wall_time_s is None
    assert TSEnsembleMember.model_validate(member(pre_relax_wall_time_s=12.5)).pre_relax_wall_time_s


@pytest.mark.parametrize(
    "reason",
    [
        "ts_search_failed:mode_lost",
        "scf_convergence",
        "engine_error",
        "ts_validation_failed",
        "gate_failed:forming_overlap",
        "face_mismatch",
        "pre_relax_failed:RuntimeError",
        "outside_window",
        "face_undetermined",
        "connectivity_changed",
    ],
)
def test_exclusion_accepts_the_closed_reasons(reason: str) -> None:
    """Every R19 reason plus the two additions validates."""
    assert TSEnsembleExclusion(index=1, source="perturb:1", reason=reason).reason == reason


@pytest.mark.parametrize(
    "reason", ["", "ts_search_failed:", "gate_failed:", "mystery", "Engine_Error", "engine_error "]
)
def test_exclusion_refuses_other_reasons(reason: str) -> None:
    """The reason set is closed."""
    with pytest.raises(ValidationError):
        TSEnsembleExclusion(index=1, source="perturb:1", reason=reason)


def test_merge_cannot_merge_into_itself() -> None:
    """kept_index and merged_index differ."""
    with pytest.raises(ValidationError):
        TSEnsembleMerge(kept_index=2, merged_index=2, dG_kcal_mol=0.0, rmsd_angstrom=0.0)
    merge = TSEnsembleMerge(kept_index=0, merged_index=2, dG_kcal_mol=0.01, rmsd_angstrom=0.1)
    assert merge.merged_index == 2


def decision(**overrides: Any) -> dict[str, Any]:
    """Return a valid decision dict."""
    data: dict[str, Any] = {
        "rule_id": "endo_exo",
        "pathways": ["endo", "exo"],
        "ddG_dagger_kcal_mol": 2.0,
        "signed_ddG_dagger_kcal_mol": {"exo_vs_endo": 2.0},
        "threshold_kcal_mol": 1.5,
        "pruned_node_ids": ["P_exo"],
        "reason": "ddG exceeds threshold",
    }
    data.update(overrides)
    return data


def test_decision_valid_and_uncomputed() -> None:
    """A decision with a gap, and one where no gap could be computed."""
    assert PruningDecision.model_validate(decision()).pruned_node_ids == ["P_exo"]
    none = PruningDecision.model_validate(
        decision(ddG_dagger_kcal_mol=None, signed_ddG_dagger_kcal_mol={}, pruned_node_ids=[])
    )
    assert none.ddG_dagger_kcal_mol is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"pruned_node_ids": ["b", "a"]},
        {"pruned_node_ids": ["a", "a"]},
        {"ddG_dagger_kcal_mol": -0.1},
        {"threshold_kcal_mol": 0.0},
        {"reason": ""},
    ],
)
def test_decision_refuses_bad_values(overrides: dict[str, Any]) -> None:
    """Sorted unique ids, unsigned gap, positive threshold, a reason."""
    with pytest.raises(ValidationError):
        PruningDecision.model_validate(decision(**overrides))


def result(**overrides: Any) -> dict[str, Any]:
    """Return a valid two-pathway result dict."""
    data: dict[str, Any] = {
        "ddG_dagger_kcal_mol": 1.7,
        "signed_ddG_dagger_kcal_mol": {"exo_vs_endo": 1.7},
        "ratio": 17.6,
        "selectivity_percent": 89.2,
        "kind": "de",
        "major_pathway": "endo",
        "temperature_k": 298.15,
        "per_pathway": {
            "endo": {
                "G_pathway_hartree": -100.0,
                "n_members": 1,
                "n_excluded": 0,
                "fraction": 0.95,
            },
            "exo": {"G_pathway_hartree": -99.99, "n_members": 1, "n_excluded": 2, "fraction": 0.05},
        },
        "pruning": decision(),
    }
    data.update(overrides)
    return data


def test_result_round_trips() -> None:
    """The US-004 keys are all present and round-trip."""
    parsed = SelectivityResult.model_validate(result())
    assert SelectivityResult.model_validate_json(parsed.model_dump_json()) == parsed
    assert {
        "ddG_dagger_kcal_mol",
        "signed_ddG_dagger_kcal_mol",
        "ratio",
        "selectivity_percent",
        "kind",
        "major_pathway",
        "temperature_k",
        "per_pathway",
    } <= set(SelectivityResult.model_fields)
    assert isinstance(parsed.per_pathway["endo"], PathwaySelectivity)


def test_result_accepts_r7_keys_in_either_direction_and_three_pathways() -> None:
    """R7: "<b>_vs_<a>" keys, any ordered pair; N > 2 pathways validate."""
    both = result(signed_ddG_dagger_kcal_mol={"exo_vs_endo": 1.7, "endo_vs_exo": -1.7})
    assert len(SelectivityResult.model_validate(both).signed_ddG_dagger_kcal_mol) == 2
    third = {"G_pathway_hartree": -99.9, "n_members": 1, "n_excluded": 0, "fraction": 0.0}
    three = result(
        per_pathway={**result()["per_pathway"], "meta": third},
        signed_ddG_dagger_kcal_mol={"exo_vs_endo": 1.7, "meta_vs_endo": 5.0},
    )
    assert "meta_vs_endo" in SelectivityResult.model_validate(three).signed_ddG_dagger_kcal_mol


def test_pathway_names_containing_vs_are_unambiguous() -> None:
    """A pathway called "a_vs_b" does not confuse the key check."""
    entry = result()["per_pathway"]["endo"]
    per = {"a_vs_b": entry, "c": entry}
    ok = result(per_pathway=per, major_pathway="c", signed_ddG_dagger_kcal_mol={"a_vs_b_vs_c": 1.0})
    assert SelectivityResult.model_validate(ok)
    bad = result(per_pathway=per, major_pathway="c", signed_ddG_dagger_kcal_mol={"a_vs_b": 1.0})
    with pytest.raises(ValidationError):
        SelectivityResult.model_validate(bad)


def test_decision_signed_keys_follow_rule_order() -> None:
    """A decision's keys are "<b>_vs_<a>" over its two pathways, either direction."""
    swapped = decision(signed_ddG_dagger_kcal_mol={"endo_vs_exo": -2.0})
    assert PruningDecision.model_validate(swapped)
    for keys in ({"endo": 0.0}, {"exo_vs_other": 2.0}, {"endo_vs_endo": 0.0}):
        with pytest.raises(ValidationError):
            PruningDecision.model_validate(decision(signed_ddG_dagger_kcal_mol=keys))


def test_result_without_pruning_is_valid() -> None:
    """The decision is optional."""
    assert SelectivityResult.model_validate(result(pruning=None)).pruning is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "dr"},
        {"ratio": 0.5},
        {"selectivity_percent": 100.5},
        {"selectivity_percent": -1.0},
        {"ddG_dagger_kcal_mol": -1.0},
        {"major_pathway": "other"},
        {"signed_ddG_dagger_kcal_mol": {}},
        {"signed_ddG_dagger_kcal_mol": {"endo": 1.7}},
        {"signed_ddG_dagger_kcal_mol": {"exo_vs_other": 1.7}},
        {"signed_ddG_dagger_kcal_mol": {"endo_vs_endo": 0.0}},
        {"signed_ddG_dagger_kcal_mol": {"exo_vs_endo": math.nan}},
        {"temperature_k": 0.0},
        {"ratio": math.inf},
        {"extra": 1},
    ],
)
def test_result_refuses_bad_values(overrides: dict[str, Any]) -> None:
    """Closed kinds, ranges, consistent pathway names, no extras."""
    with pytest.raises(ValidationError):
        SelectivityResult.model_validate(result(**overrides))


def test_result_needs_two_pathways() -> None:
    """A selectivity needs at least two pathways."""
    one = {"endo": result()["per_pathway"]["endo"]}
    with pytest.raises(ValidationError):
        SelectivityResult.model_validate(
            result(per_pathway=one, signed_ddG_dagger_kcal_mol={"endo_vs_endo": 0.0})
        )


def test_models_are_frozen() -> None:
    """CoreModel instances are immutable."""
    parsed = TSEnsembleOptions()
    with pytest.raises(ValidationError):
        parsed.n_embed = 3  # type: ignore[misc]
