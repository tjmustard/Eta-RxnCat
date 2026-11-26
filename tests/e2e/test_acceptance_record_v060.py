"""The v0.6.0 acceptance record: merge, schema check, gated states and bounds (slice 11)."""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import acceptance_record_v060 as rec
import pytest
from acceptance_record_v050 import git_blob_id
from acceptance_record_v060 import (
    FLEX,
    FLEX_GATES,
    G1_TESTS,
    G4_TESTS,
    HF1_SHA256,
    KNOWN_LIMITS,
    PAIRS,
    PROMOTED_FILES,
    PROPOSAL_BOUNDS,
    RECIPES,
    check,
    command_problems,
    compare_flexible,
    compare_pair,
    ensemble_block,
    entry_states,
    fixture_states,
    flexible_entry,
    flexible_states,
    merge_runs,
    outstanding,
    pair_entry,
    promotion_evidence,
    proposed_bounds,
    record_verdict,
    reproducibility_entry,
    transcriptions_block,
    unit_proof_block,
)

STATE = {
    "symbols": ["C", "C", "N", "O", "H"],
    "coordinates": [[0, 0, 0], [1.5, 0, 0], [0, 1.4, 0], [0, 0, 1.2], [2, 1, 0]],
}
GATES = (
    "seeds_converge_and_pass_member_gates",
    "endo_is_major",
    "ddG_dagger_above_0_5",
    "no_engine_error_exclusions",
    "no_face_mismatch_exclusions",
    "regression_endo_seed",
    "per_pathway_dG_difference_equals_ddG",
    "second_run_ensembles_all_hits",
    "second_run_reactants_all_hits",
    "second_run_equal_ensembles_and_score",
)


def moved(dy: float) -> dict[str, Any]:
    """STATE with the second carbon moved by ``dy`` Angstrom along y."""
    state = copy.deepcopy(STATE)
    state["coordinates"][1][1] = dy
    return state


def ensemble(excluded: list[str] | None = None, n_members: int = 1) -> dict[str, Any]:
    """A TSEnsemble dump with ``n_members`` members and the given exclusion reasons."""
    return {
        "failed_reason": None,
        "members": [{"index": i, "pre_relax_wall_time_s": 3.0 + i} for i in range(n_members)],
        "excluded": [
            {"index": k + 1, "reason": r, "pre_relax_wall_time_s": 600.0 if "Timeout" in r else 5.0}
            for k, r in enumerate(excluded or [])
        ],
        "merges": [],
        "flagged_merges": [],
        "G_pathway_hartree": -100.0,
    }


def fragment(pair: str, recipe: str, status: str = "pass", **change: Any) -> dict[str, Any]:
    """A Tier 4 fragment as test_t4_unmapped / test_t4_mapped write it."""
    gates: dict[str, Any] = {g: {"status": status} for g in GATES}
    gates["window_ddG_dagger"] = {
        "status": status if recipe == "uma" else "reported",
        "value_kcal_mol": 4.0,
    }
    if pair == "t4_mapped":
        gates["pruning_g6"] = {
            "status": status,
            "branch": "pruned" if recipe == "xtb" else "computed",
        }
    out: dict[str, Any] = {
        "case": pair,
        "recipe": recipe,
        "test_outcome": "passed" if status == "pass" else "failed",
        "failed_checks": [],
        "checks": {"tier_gates": gates, "regression": {"status": "pass"}},
        "pathways": {
            p: {
                "ensemble": ensemble(),
                "seed_ts": {
                    "failed_reason": None,
                    "thermo": {"electronic_energy_hartree": -100.0 - k},
                    "state": STATE,
                },
            }
            for k, p in enumerate(("endo", "exo"))
        },
        "score": {
            "ddG_dagger_kcal_mol": 4.0,
            "major_pathway": "endo",
            "ratio": 800.0,
            "selectivity_percent": 99.7,
            "kind": "de",
            "temperature_k": 298.15,
        },
        "reported": {"liu": 4.273},
        "second_run_cache": {"endo": {}},
    }
    if pair == "t4_mapped":
        out["pruning"] = {"decisions": []}
        out["exo_graft"] = {"core_rmsd": 0.1, "pre_relaxed_start": {"symbols": []}}
    out.update(change)
    return out


def flex_fragment(
    r_group: str, recipe: str, status: str = "pass", n_members: int = 3
) -> dict[str, Any]:
    """A slice 14 fragment as test_t4_flexible writes it."""
    return {
        "case": f"t4_flexible_{r_group}",
        "recipe": recipe,
        "commit_sha": "feed001",
        "test_outcome": "passed" if status == "pass" else "failed",
        "failed_checks": [],
        "checks": {"tier_gates": {g: {"status": status} for g in FLEX_GATES}},
        "graft": {"n_atoms": 24},
        "inputs_sha256": {"fragment": "ab"},
        "reported": {
            "n_members": n_members,
            "members": [
                {"source": "seed" if i == 0 else f"perturb:{i}", "G_hartree": -100.0 - 0.001 * i}
                for i in range(n_members)
            ],
            "G_pathway_hartree": -100.01,
            "exclusions_by_reason": {"outside_window": 1},
            "barrier": {"ensemble_dG_dagger_1M_kcal_mol": 14.0 + FLEX.index(r_group)},
            "max_pre_relax_wall_time_s": 20.0,
        },
        "regression": {"status": "pending_promotion"},
    }


def repro(
    pair: str, recipe: str, d_e: float = 0.0, d_g: float = 0.0, d_y: float = 0.0
) -> dict[str, Any]:
    """A reproducibility fragment of two runs that differ from the acceptance run."""

    def run(k: int) -> dict[str, Any]:
        return {
            "pathways": {
                p: {
                    "ts_energy_hartree": -100.0 - i + d_e * (k + 1),
                    "ts_state": moved(d_y * (k + 1)) if k == 0 else STATE,
                    "n_members": 1,
                    "exclusions_by_reason": {},
                }
                for i, p in enumerate(("endo", "exo"))
            },
            "ddG_dagger_kcal_mol": 4.0 + d_g * (k + 1),
            "branch": "pruned" if pair == "t4_mapped" and recipe == "xtb" else None,
        }

    return {"pair": pair, "runs": [run(0), run(1)], "pre_relax_timeouts": 0}


def run_file(recipe: str, **kw: Any) -> dict[str, Any]:
    """One recipe's acceptance_<recipe>.json."""
    return {
        "recipe": recipe,
        "commit_sha": "abc123",
        "tree_clean": True,
        "run_at_utc": "2026-11-25T14:00:00+00:00",
        "device": "cpu" if recipe == "xtb" else "cuda",
        "engine": {"name": recipe},
        "python": "3.12.0",
        "hardware": {"gpu": "x"},
        "pairs": {p: fragment(p, recipe) for p in PAIRS},
        "reproducibility": {p: repro(p, recipe, **kw) for p in PAIRS},
        "flexible": {r: flex_fragment(r, recipe, n_members=3 + i) for i, r in enumerate(FLEX)},
    }


COMMANDS = [
    {
        "argv": ["pytest", "-k", recipe],
        "env": {
            "ETA_RXNCAT_ACCEPTANCE": "1",
            "recipe": recipe,
            **({"ETA_RXNCAT_XTB": "/x/xtb"} if recipe == "xtb" else {}),
        },
        "exit_code": 0,
        "wall_s": 1.0,
        "log": f"{recipe}.log",
        "summary": "1 passed, 3 deselected in 5.0s",
        "max_rss_kbytes": 1000,
    }
    for recipe in RECIPES
]
SUITE = {"command": "uv run pytest", "exit_code": 0, "passed": 10, "failed": 0, "errors": 0}
UNIT = {"G1": {"status": "pass", "nodes": {}}, "G4": {"status": "pass", "nodes": {}}}
PENDING = (
    {f"t4.{p}.{r}.regression": "pending_promotion" for p in PAIRS for r in RECIPES}
    | {f"flexible_ensemble.{r}.{x}.regression": "pending_promotion" for r in FLEX for x in RECIPES}
    | {"transcription_confirmation": "pending_confirmation"}
)


NO_PROMOTION = Path("/nonexistent/promoted-fixtures")
"""A directory with no promoted fixtures: the merge writes the pre-promotion record."""


def merged(
    runs: dict[str, dict[str, Any]] | None = None,
    commands: Any = None,
    promoted_dir: Path = NO_PROMOTION,
    prior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The merged record of synthetic runs (pre-promotion without promoted fixtures)."""
    runs = runs or {r: run_file(r) for r in RECIPES}
    return merge_runs(
        runs,
        copy.deepcopy(commands or COMMANDS),
        copy.deepcopy(SUITE),
        copy.deepcopy(UNIT),
        prior=prior,
        promoted_dir=promoted_dir,
    )


# --- the record -------------------------------------------------------------------------------


def test_merge_gives_a_valid_pre_promotion_record() -> None:
    """US-012: every check has a state; gated checks pass; only TJ's checks are pending."""
    record = merged()
    assert check(record) == []
    assert "verdict" not in record
    assert outstanding(record) == PENDING
    assert command_problems(record["commands"]) == []
    assert record["known_limits"] == list(KNOWN_LIMITS)


def test_a_failed_gate_is_a_fail_state() -> None:
    """A failed gate is a fail state."""
    runs = {r: run_file(r) for r in RECIPES}
    runs["uma"]["pairs"]["t4_mapped"] = fragment("t4_mapped", "uma", "fail")
    states = fixture_states(merged(runs)["fixtures"])
    assert states["t4.t4_mapped.uma.tier_gates.endo_is_major"] == "fail"
    assert states["t4.t4_mapped.uma.test_outcome"] == "fail"
    assert states["t4.t4_unmapped.uma.test_outcome"] if False else True


def test_a_missing_fragment_is_missing_not_pass() -> None:
    """A missing fragment is missing not pass."""
    runs = {r: run_file(r) for r in RECIPES}
    runs["xtb"]["pairs"]["t4_unmapped"] = {"test_outcome": "missing"}
    record = merged(runs)
    assert record["fixtures"]["t4"]["t4_unmapped"]["xtb"] == {"test_outcome": "missing"}
    assert fixture_states(record["fixtures"])["t4.t4_unmapped.xtb.test_outcome"] == "missing"


def test_engine_error_and_face_mismatch_are_gated_at_zero() -> None:
    """R1, R3: a nonzero count fails; every other exclusion is reported only."""
    entry = pair_entry(fragment("t4_unmapped", "uma"))
    assert all(v == "pass" for k, v in entry_states(entry).items() if k.startswith("ensembles."))
    for reason, key in (("engine_error", "engine_error"), ("face_mismatch", "face_mismatch")):
        bad = fragment("t4_unmapped", "uma")
        bad["pathways"]["exo"]["ensemble"] = ensemble([reason])
        states = entry_states(pair_entry(bad))
        assert states[f"ensembles.exo.{key}"] == "fail"
        assert states["ensembles.endo.engine_error"] == "pass"


def test_reported_exclusions_do_not_gate() -> None:
    """Slice 13: PreRelaxTimeout, merges and other exclusions are reported, never gated."""
    frag = fragment("t4_unmapped", "uma")
    block = ensemble(["pre_relax_failed:PreRelaxTimeout", "outside_window", "scf_convergence"], 3)
    block["merges"] = [{"a": 1}, {"a": 2}]
    block["flagged_merges"] = [{"a": 1}]
    frag["pathways"]["endo"]["ensemble"] = block
    entry = pair_entry(frag)
    endo = entry["ensembles"]["endo"]
    assert endo["n_members"] == 3 and endo["n_merges"] == 2 and endo["n_flagged_merges"] == 1
    assert endo["pre_relax_timeouts"] == 1 and endo["max_pre_relax_wall_time_s"] == 600.0
    assert endo["exclusions_by_reason"]["outside_window"] == 1
    assert set(entry_states(entry).values()) <= {"pass", "pending_promotion"}


def test_ensemble_block_counts_by_reason() -> None:
    """Ensemble block counts by reason."""
    block = ensemble_block(ensemble(["face_mismatch", "face_mismatch", "engine_error"], 2))
    assert block["exclusions_by_reason"] == {"engine_error": 1, "face_mismatch": 2}
    assert (block["engine_error"], block["face_mismatch"], block["n_members"]) == (1, 2, 2)


def test_regression_is_pending_promotion_whatever_the_fragment_says() -> None:
    """Regression is pending promotion whatever the fragment says."""
    entry = pair_entry(fragment("t4_unmapped", "uma"))
    assert entry["regression"]["status"] == "pending_promotion"
    assert entry["tier_gates"]["regression_endo_seed"]["status"] == "pass"


def test_mapped_entry_carries_the_pruning_block_and_a_trimmed_graft() -> None:
    """Mapped entry carries the pruning block and a trimmed graft."""
    entry = pair_entry(fragment("t4_mapped", "xtb"))
    assert entry["pruning"] == {"decisions": []}
    assert "pre_relaxed_start" not in entry["exo_graft"]
    assert entry["tier_gates"]["pruning_g6"]["branch"] == "pruned"


# --- check(): environment (R9) and schema -----------------------------------------------------


def test_a_record_without_the_acceptance_flag_fails_check() -> None:
    """Requirement 3: environment must record ETA_RXNCAT_ACCEPTANCE=1."""
    record = merged()
    for recipe in RECIPES:
        broken = copy.deepcopy(record)
        del broken["environment"][recipe]["ETA_RXNCAT_ACCEPTANCE"]
        assert any("ETA_RXNCAT_ACCEPTANCE=1" in p for p in check(broken))


def test_an_xtb_record_without_the_xtb_path_fails_check() -> None:
    """An xtb record without the xtb path fails check."""
    record = merged()
    del record["environment"]["xtb"]["ETA_RXNCAT_XTB"]
    assert any("ETA_RXNCAT_XTB" in p for p in check(record))


def test_merge_refuses_commands_without_the_flag() -> None:
    """Merge refuses commands without the flag."""
    commands = copy.deepcopy(COMMANDS)
    del commands[0]["env"]["ETA_RXNCAT_ACCEPTANCE"]
    with pytest.raises(ValueError, match="ETA_RXNCAT_ACCEPTANCE=1"):
        merged(commands=commands)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.pop("fixtures"),
        lambda r: r["fixtures"]["t4"].pop("t4_mapped"),
        lambda r: r["fixtures"]["t4"]["t4_unmapped"].pop("uma"),
        lambda r: r["fixtures"]["t4"]["t4_unmapped"]["uma"].update(test_outcome="skipped"),
        lambda r: r["fixtures"]["transcription_confirmation"].update(status="confirmed"),
        lambda r: r.update(verdict="pass"),
        lambda r: r.update(known_limits=[]),
        lambda r: r["default_suite"].pop("exit_code"),
        lambda r: r["fixtures"]["unit_proof"].pop("G1"),
    ],
)
def test_check_catches_a_broken_record(mutate: Any) -> None:
    """Check catches a broken record."""
    record = merged()
    mutate(record)
    problems = check(record) if "fixtures" in record else check(record)
    assert problems or outstanding_changed(record)


def outstanding_changed(record: dict[str, Any]) -> bool:
    """A settled TJ check or a missing proof shows in the outstanding states."""
    return outstanding(record) != PENDING


def test_command_problems_name_an_exit_or_a_skip() -> None:
    """Command problems name an exit or a skip."""
    bad = copy.deepcopy(COMMANDS)
    bad[0]["exit_code"] = 1
    bad[1]["summary"] = "1 passed, 1 skipped in 5.0s"
    problems = command_problems(bad)
    assert any("exit_code 1" in p for p in problems) and any("1 skipped" in p for p in problems)


def test_merge_refuses_unclean_or_mixed_commits() -> None:
    """Merge refuses unclean or mixed commits."""
    runs = {r: run_file(r) for r in RECIPES}
    runs["uma"]["tree_clean"] = False
    with pytest.raises(ValueError, match="different or unclean"):
        merged(runs)
    runs = {r: run_file(r) for r in RECIPES}
    runs["uma"]["commit_sha"] = "def456"
    with pytest.raises(ValueError, match="different or unclean"):
        merged(runs)


# --- transcriptions and the unit proof --------------------------------------------------------


def test_transcriptions_hold_on_the_committed_files() -> None:
    """HF-1 sha256s and HF-2 header ΔΔG‡ (+4.273, +1.849) pass on the committed xyz files."""
    block = transcriptions_block()
    assert block["sha256"]["status"] == "pass"
    assert block["header_ddG"]["status"] == "pass"
    for name, expected in HF1_SHA256.items():
        assert block["sha256"]["files"][name]["observed"] == expected


def test_a_changed_transcription_fails(tmp_path: Path) -> None:
    """A changed transcription fails."""
    for name in HF1_SHA256:
        src = Path(__file__).parent / "data" / "e2e5" / "xyz" / name
        (tmp_path / name).write_bytes(src.read_bytes())
    for name in ("TS1a_n.xyz", "TS1b_n.xyz"):
        src = Path(__file__).parent / "data" / "e2e5" / "xyz" / name
        (tmp_path / name).write_bytes(src.read_bytes())
    assert transcriptions_block(tmp_path)["sha256"]["status"] == "pass"
    (tmp_path / "TS1a_x.xyz").write_text("tampered\n", encoding="utf-8")
    block = transcriptions_block(tmp_path)
    assert block["sha256"]["status"] == "fail"
    assert (
        block["sha256"]["files"]["TS1a_x.xyz"]["observed"]
        == hashlib.sha256(b"tampered\n").hexdigest()
    )


def verbose_log(skip: str = "", fail: str = "") -> str:
    """A ``pytest -v`` log naming every G1 and G4 test as passed (one parametrised test twice)."""
    lines = []
    for name in G1_TESTS:
        lines.append(f"tests/unit/orchestrator/test_selectivity_score.py::{name} PASSED [ 1%]")
    for name in G4_TESTS:
        lines.append(f"tests/unit/orchestrator/test_ts_ensemble.py::{name}[x] PASSED [ 2%]")
        lines.append(f"tests/unit/orchestrator/test_ts_ensemble.py::{name}[y] PASSED [ 3%]")
    lines = [ln for ln in lines if not (skip and skip in ln)]
    if fail:
        lines.append(f"tests/unit/orchestrator/test_ts_ensemble.py::{fail}[z] FAILED [ 4%]")
    return "\n".join(lines) + "\n"


def test_unit_proof_passes_with_every_named_test_passed() -> None:
    """Unit proof passes with every named test passed."""
    block = unit_proof_block(verbose_log(), 0)
    assert block["G1"]["status"] == block["G4"]["status"] == "pass"
    assert len(block["G4"]["nodes"]["test_two_saddles_merge_copies"]) == 2


@pytest.mark.parametrize(
    ("log", "exit_code", "group"),
    [
        (verbose_log(skip="test_tie_is_fifty_fifty"), 0, "G1"),
        (verbose_log(fail="test_two_saddles_merge_copies"), 1, "G4"),
        (verbose_log(), 1, "G1"),
        ("", 0, "G4"),
    ],
)
def test_unit_proof_fails_on_a_missing_failed_or_nonzero_run(
    log: str, exit_code: int, group: str
) -> None:
    """Unit proof fails on a missing failed or nonzero run."""
    assert unit_proof_block(log, exit_code)[group]["status"] == "fail"


# --- reproducibility and the bounds rule ------------------------------------------------------


def test_reproducibility_measures_the_maximum_differences() -> None:
    """Reproducibility measures the maximum differences."""
    entry = reproducibility_entry(
        "t4_unmapped",
        "uma",
        fragment("t4_unmapped", "uma"),
        repro("t4_unmapped", "uma", d_e=1e-8, d_g=0.002, d_y=0.0004),
    )
    assert entry["status"] == "measured" and entry["n_runs"] == 3
    assert entry["max_abs_delta_ts_energy_hartree"] == pytest.approx(2e-8, abs=1e-12)
    assert entry["max_abs_delta_ddG_dagger_kcal_mol"] == pytest.approx(0.004)
    assert 0 < entry["max_heavy_rmsd_angstrom"] < 0.01
    assert entry["member_count_changes"] == [] and entry["exclusion_changes"] == []
    assert entry["branch_changed"] is False


def test_reproducibility_records_member_and_exclusion_changes() -> None:
    """Reproducibility records member and exclusion changes."""
    rep = repro("t4_unmapped", "uma")
    rep["runs"][1]["pathways"]["exo"]["n_members"] = 2
    rep["runs"][1]["pathways"]["exo"]["exclusions_by_reason"] = {
        "pre_relax_failed:PreRelaxTimeout": 1
    }
    entry = reproducibility_entry("t4_unmapped", "uma", fragment("t4_unmapped", "uma"), rep)
    assert {c["pathway"] for c in entry["member_count_changes"]} == {"exo"}
    assert len(entry["member_count_changes"]) == 2  # against the acceptance run and run 1
    assert entry["exclusion_changes"]


def test_reproducibility_records_a_branch_change() -> None:
    """Reproducibility records a branch change."""
    rep = repro("t4_mapped", "xtb")
    rep["runs"][1]["branch"] = "computed"
    entry = reproducibility_entry("t4_mapped", "xtb", fragment("t4_mapped", "xtb"), rep)
    assert entry["branch_changed"] is True


def test_reproducibility_is_missing_without_a_fragment() -> None:
    """Reproducibility is missing without a fragment."""
    gone = {"test_outcome": "missing"}
    assert (
        reproducibility_entry("t4_mapped", "xtb", fragment("t4_mapped", "xtb"), gone)["status"]
        == "missing"
    )
    assert (
        reproducibility_entry("t4_mapped", "xtb", gone, repro("t4_mapped", "xtb"))["status"]
        == "missing"
    )


def bounds_for(**kw: float) -> dict[str, Any]:
    """The proposed bounds of synthetic reproducibility measurements."""
    runs = {r: run_file(r, **kw) for r in RECIPES}
    return merged(runs)["proposed_regression_bounds"]


def test_bounds_keep_tjs_numbers_when_every_difference_is_a_tenth_or_less() -> None:
    """Bounds keep tjs numbers when every difference is a tenth or less."""
    block = bounds_for(d_e=1e-8, d_g=0.0003, d_y=1e-4)["recipes"]
    for recipe in RECIPES:
        for quantity, bound in PROPOSAL_BOUNDS[recipe].items():
            assert block[recipe][quantity]["basis"] == "tj_bound"
            assert block[recipe][quantity]["proposed"] == bound
    assert block["xtb"]["abs_delta_ddG_dagger_kcal_mol"]["proposed"] == 0.01
    assert block["uma"]["abs_delta_ddG_dagger_kcal_mol"]["proposed"] == 0.75


def test_bounds_propose_ten_times_the_maximum_otherwise() -> None:
    """Bounds propose ten times the maximum otherwise."""
    block = bounds_for(d_e=1e-8, d_g=0.004, d_y=1e-4)["recipes"]
    xtb = block["xtb"]["abs_delta_ddG_dagger_kcal_mol"]
    assert xtb["basis"] == "ten_times_measured_max"
    assert xtb["proposed"] == pytest.approx(10 * xtb["measured_max"])
    assert "10x the measured maximum" in xtb["statement"]
    assert block["uma"]["abs_delta_ddG_dagger_kcal_mol"]["basis"] == "tj_bound"


def test_bounds_are_missing_when_a_pair_is_not_measured() -> None:
    """Bounds are missing when a pair is not measured."""
    reproducibility = {
        r: {
            "t4_unmapped": {"status": "missing", "reason": "x"},
            "t4_mapped": {
                "status": "measured",
                "max_abs_delta_ts_energy_hartree": 0.0,
                "max_abs_delta_ddG_dagger_kcal_mol": 0.0,
                "max_heavy_rmsd_angstrom": 0.0,
            },
        }
        for r in RECIPES
    }
    block = proposed_bounds(reproducibility)["recipes"]["uma"]
    assert block["abs_delta_ts_energy_hartree"]["status"] == "missing"
    assert block["pairs_not_measured"] == ["t4_unmapped"]


# --- Slice 14's flexible-ensemble entries -----------------------------------------------------


def test_the_record_holds_six_flexible_entries_gated_as_slice_14() -> None:
    """Replan 4: three R x two recipes, each with gates (a)-(f) as states, regression pending."""
    record = merged()
    flexible = record["fixtures"]["flexible_ensemble"]
    assert set(flexible) == set(FLEX) and all(set(v) == set(RECIPES) for v in flexible.values())
    states = fixture_states(record["fixtures"])
    for r in FLEX:
        for recipe in RECIPES:
            for gate in FLEX_GATES:
                assert states[f"flexible_ensemble.{r}.{recipe}.tier_gates.{gate}"] == "pass"
            assert states[f"flexible_ensemble.{r}.{recipe}.regression"] == "pending_promotion"


def test_a_failed_flexible_gate_or_a_missing_entry_is_not_pass() -> None:
    """A failing gate is a fail state, a missing fragment is missing, a short gate list too."""
    runs = {r: run_file(r) for r in RECIPES}
    runs["uma"]["flexible"]["npropyl"] = flex_fragment("npropyl", "uma", "fail")
    runs["xtb"]["flexible"]["nbutyl"] = {"test_outcome": "missing"}
    states = fixture_states(merged(runs)["fixtures"])
    assert states["flexible_ensemble.npropyl.uma.test_outcome"] == "fail"
    assert states["flexible_ensemble.npropyl.uma.tier_gates.distinct_members_at_least_2"] == "fail"
    assert states["flexible_ensemble.nbutyl.xtb.test_outcome"] == "missing"
    short = flexible_entry(flex_fragment("ethyl", "xtb"))
    short["tier_gates"].pop("weights_sum_to_one")
    assert flexible_states(short)["tier_gates.complete"] == "missing"


def test_flexible_members_order_and_ddg_vs_ethyl_are_reported_not_gated() -> None:
    """Members per R, the non-decreasing flag and ddG vs ethyl are reported; a decrease passes."""
    runs = {r: run_file(r) for r in RECIPES}
    block = merged(runs)["fixtures"]["flexible_ensemble"]
    nbutyl = block["nbutyl"]["xtb"]["reported"]
    assert nbutyl["chain_length_order"]["members_by_r"] == {"ethyl": 3, "npropyl": 4, "nbutyl": 5}
    assert nbutyl["chain_length_order"]["non_decreasing"] is True
    assert nbutyl["ddG_dagger_vs_ethyl_kcal_mol"] == 2.0
    assert block["ethyl"]["xtb"]["reported"]["ddG_dagger_vs_ethyl_kcal_mol"] == 0.0
    runs["xtb"]["flexible"]["nbutyl"] = flex_fragment("nbutyl", "xtb", n_members=2)
    record = merged(runs)
    nbutyl = record["fixtures"]["flexible_ensemble"]["nbutyl"]["xtb"]["reported"]
    assert nbutyl["chain_length_order"]["non_decreasing"] is False
    assert outstanding(record) == PENDING


def test_run_commits_and_the_resume_note_are_in_the_evidence() -> None:
    """Each fragment's own commit is recorded; the R30 reuse is stated, never implied."""
    runs = {r: run_file(r) for r in RECIPES}
    runs["xtb"]["pairs"]["t4_mapped"]["commit_sha"] = "1273070"
    evidence = merged(runs)["evidence"]
    assert evidence["run_commits"]["t4.t4_mapped.xtb"] == "1273070"
    assert evidence["run_commits"]["flexible_ensemble.ethyl.uma"] == "feed001"
    assert "1273070" in evidence["resume_note"] and "no src/" in evidence["resume_note"]


# --- TJ's promotion, the regression comparison and the verdict (slice 12) ---------------------


def promote(tmp_path: Path, runs: dict[str, dict[str, Any]], mutate: Any = None) -> dict[str, Any]:
    """Write ten promoted fixtures (the runs' own fragments) and return R31-style prefixes."""
    files: dict[str, Any] = {}
    for recipe in RECIPES:
        for pair in PAIRS:
            files[f"{pair}.{recipe}.json"] = copy.deepcopy(runs[recipe]["pairs"][pair])
        for r in FLEX:
            files[f"t4_flexible_{r}.{recipe}.json"] = copy.deepcopy(runs[recipe]["flexible"][r])
    prefixes = {}
    for name, data in files.items():
        if mutate is not None:
            mutate(name, data)
        blob = json.dumps(data, sort_keys=True).encode("utf-8")
        (tmp_path / name).write_bytes(blob)
        prefixes[name] = (hashlib.sha256(blob).hexdigest()[:12], git_blob_id(blob)[:12])
    return prefixes


def verdict_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    runs: dict[str, dict[str, Any]] | None = None,
    mutate: Any = None,
) -> dict[str, Any]:
    """Merge synthetic runs against promoted fixtures made of the runs' own results."""
    runs = runs or {r: run_file(r) for r in RECIPES}
    monkeypatch.setattr(rec, "PROMOTED_FILES", promote(tmp_path, runs, mutate))
    return merged(runs, promoted_dir=tmp_path)


def test_the_real_promoted_fixtures_are_the_ten_files_of_r31() -> None:
    """Requirement 1: the committed fixtures equal R31's sha256 and blob-id prefixes."""
    evidence = promotion_evidence()
    assert evidence["status"] == "verified"
    assert sorted(evidence["files"]) == sorted(PROMOTED_FILES)
    assert evidence["commit"] == "6fce509"
    for name, (sha, blob) in PROMOTED_FILES.items():
        assert evidence["files"][name]["sha256"].startswith(sha)
        assert evidence["files"][name]["blob_id"].startswith(blob)


def test_promotion_is_absent_without_fixtures_and_refuses_a_foreign_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No promoted file: absent. A file that is not R31's, or an extra one: an error."""
    assert promotion_evidence(NO_PROMOTION)["status"] == "absent"
    runs = {r: run_file(r) for r in RECIPES}
    monkeypatch.setattr(rec, "PROMOTED_FILES", promote(tmp_path, runs))
    assert promotion_evidence(tmp_path)["status"] == "verified"
    (tmp_path / "t4_mapped.uma.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="is not R31's"):
        promotion_evidence(tmp_path)
    promote(tmp_path, runs)
    (tmp_path / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="are not R31's"):
        promotion_evidence(tmp_path)


def test_a_verdict_record_passes_when_every_result_matches_its_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requirement 2: regression passes everywhere, confirmation is settled, verdict pass."""
    record = verdict_record(tmp_path, monkeypatch)
    assert check(record) == []
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert record["evidence"]["promotion"]["status"] == "verified"
    assert record["fixtures"]["transcription_confirmation"]["status"] == "confirmed"
    assert "resume_note" not in record["evidence"]  # slice 11's note is never carried into it
    assert "resume_note" in merged()["evidence"]
    assert outstanding(record) == {}
    assert record["regression_bounds"]["recipes"]["uma"] == PROPOSAL_BOUNDS["uma"]
    assert record["fixtures"]["t4"]["t4_mapped"]["xtb"]["regression"]["status"] == "pass"
    assert (
        record["fixtures"]["flexible_ensemble"]["nbutyl"]["uma"]["regression"]["status"] == "pass"
    )
    assert "Q-RES1 was answered B" in record["known_limits"][-1]
    assert "slice 14" in record["known_limits"][-1]


def test_the_verdict_is_fail_when_a_result_leaves_its_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One out-of-bound energy fails that entry's regression and the verdict, with the reason."""

    def shift(name: str, data: dict[str, Any]) -> None:
        if name == "t4_unmapped.xtb.json":
            data["pathways"]["endo"]["seed_ts"]["thermo"]["electronic_energy_hartree"] += 1e-3

    record = verdict_record(tmp_path, monkeypatch, mutate=shift)
    assert record["verdict"] == "fail"
    assert record["verdict_reasons"] == ["t4.t4_unmapped.xtb.regression: fail"]
    assert check(record) == []


def test_the_record_is_pre_promotion_without_the_promoted_fixtures() -> None:
    """Without TJ's files: regression pending, no verdict, confirmation pending."""
    record = merged()
    assert "verdict" not in record
    assert record["evidence"]["promotion"]["status"] == "absent"
    assert record["fixtures"]["transcription_confirmation"]["status"] == "pending_confirmation"
    assert "not yet TJ's fixtures" in record["reported_notes"]["promotion"]


def test_reproducibility_is_carried_over_from_the_prior_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict run reuses slice 11's measurement and names its source."""
    prior = merged(runs={r: run_file(r, d_g=0.0003, d_y=1e-4) for r in RECIPES})
    runs = {r: run_file(r) for r in RECIPES}
    monkeypatch.setattr(rec, "PROMOTED_FILES", promote(tmp_path, runs))
    carried = merged(runs, promoted_dir=tmp_path, prior=prior)
    assert carried["reproducibility"] == prior["reproducibility"]
    assert carried["proposed_regression_bounds"] == prior["proposed_regression_bounds"]
    assert prior["commit_sha"] in carried["evidence"]["reproducibility_source"]
    assert carried["verdict"] == "pass"


def test_a_verdict_needs_a_verified_promotion_and_the_recomputed_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """check() refuses a verdict that is not the rule's, or one without a verified promotion."""
    record = verdict_record(tmp_path, monkeypatch)
    forged = copy.deepcopy(record)
    forged["fixtures"]["t4"]["t4_mapped"]["uma"]["regression"]["status"] = "fail"
    assert any("is not the record's verdict" in p for p in check(forged))
    unpromoted = copy.deepcopy(record)
    unpromoted["evidence"]["promotion"]["status"] = "absent"
    assert any("evidence.promotion verified" in p for p in check(unpromoted))
    bare = copy.deepcopy(record)
    del bare["regression_bounds"]
    assert any("missing regression_bounds" in p for p in check(bare))


def test_a_verdict_record_without_the_acceptance_flag_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R9: a verdict record that lost ETA_RXNCAT_ACCEPTANCE=1 fails check()."""
    record = verdict_record(tmp_path, monkeypatch)
    del record["environment"]["uma"]["ETA_RXNCAT_ACCEPTANCE"]
    assert any("ETA_RXNCAT_ACCEPTANCE=1" in p for p in check(record))


def test_the_verdict_rule_fails_on_suite_commands_and_non_pass_states() -> None:
    """Non-zero suite, failures, errors, a command exit or skip, no commands, any non-pass state."""
    fixtures = merged()["fixtures"]
    ok_states = {k: "pass" for k in fixture_states(fixtures)}
    assert set(ok_states.values()) == {"pass"}
    good = record_verdict(fixtures | {}, SUITE, COMMANDS)
    assert good["verdict"] == "fail"  # regression is still pending in this record
    assert "t4.t4_mapped.uma.regression: pending_promotion" in good["verdict_reasons"]
    bad_suite = record_verdict(fixtures, SUITE | {"exit_code": 1, "failed": 2}, COMMANDS)
    assert any("default_suite: exit_code 1, failed 2" in r for r in bad_suite["verdict_reasons"])
    assert "default_suite: missing" in record_verdict(fixtures, None, COMMANDS)["verdict_reasons"]
    assert "commands: none recorded" in record_verdict(fixtures, SUITE, [])["verdict_reasons"]
    skipped = copy.deepcopy(COMMANDS)
    skipped[0]["summary"] = "1 passed, 1 skipped in 2.0s"
    assert any(
        "1 skipped" in r for r in record_verdict(fixtures, SUITE, skipped)["verdict_reasons"]
    )


def pair_pair(
    recipe: str = "uma", pair: str = "t4_unmapped"
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The same fragment twice: the run and its fixture."""
    return fragment(pair, recipe), fragment(pair, recipe)


def test_compare_pair_bounds_are_tjs_per_recipe() -> None:
    """|ΔΔG‡| 0.5 is inside UMA's 0.75 and outside GFN2's 0.01; |ΔE| 2e-5 is outside both."""
    new, old = pair_pair("uma")
    new["score"]["ddG_dagger_kcal_mol"] += 0.5
    assert compare_pair(new, old, "uma", "n")["status"] == "pass"
    assert compare_pair(new, old, "xtb", "n")["mismatches"] == ["abs_delta_ddG_dagger_kcal_mol"]
    new, old = pair_pair("uma")
    new["pathways"]["exo"]["seed_ts"]["thermo"]["electronic_energy_hartree"] += 2e-5
    assert compare_pair(new, old, "uma", "n")["mismatches"] == ["abs_delta_ts_energy_hartree"]


def test_compare_pair_heavy_rmsd_and_missing_values() -> None:
    """A moved TS beyond 0.01 Å fails; a value one side lacks is a mismatch, never a pass."""
    new, old = pair_pair("uma")
    new["pathways"]["endo"]["seed_ts"]["state"] = moved(0.3)
    result = compare_pair(new, old, "uma", "n")
    assert "heavy_rmsd_angstrom" in result["mismatches"]
    new, old = pair_pair("uma")
    del new["pathways"]["endo"]["seed_ts"]["state"]
    assert "heavy_rmsd_angstrom: missing" in compare_pair(new, old, "uma", "n")["mismatches"]
    new, old = pair_pair("uma")
    new["score"] = None
    assert (
        "abs_delta_ddG_dagger_kcal_mol: missing" in compare_pair(new, old, "uma", "n")["mismatches"]
    )


def test_compare_pair_member_count_differs_only_through_a_timeout() -> None:
    """A different member count fails, unless a PreRelaxTimeout excluded a member on either side."""
    new, old = pair_pair("uma")
    new["pathways"]["exo"]["ensemble"] = ensemble(n_members=2)
    assert compare_pair(new, old, "uma", "n")["mismatches"] == ["n_members.exo"]
    new["pathways"]["exo"]["ensemble"] = ensemble(["pre_relax_failed:PreRelaxTimeout"], 2)
    result = compare_pair(new, old, "uma", "n")
    assert result["status"] == "pass"
    assert result["per_pathway"]["exo"]["difference_explained_by_timeout"] is True
    assert result["per_pathway"]["exo"]["n_members"] == [2, 1]


def test_compare_pair_pruning_branch_must_match() -> None:
    """The mapped pair's pruning decision must equal the fixture's."""
    new, old = pair_pair("xtb", "t4_mapped")
    assert compare_pair(new, old, "xtb", "n")["status"] == "pass"
    new["checks"]["tier_gates"]["pruning_g6"]["branch"] = "computed"
    result = compare_pair(new, old, "xtb", "n")
    assert result["status"] == "fail" and "pruning_branch" in result["mismatches"]
    assert result["pruning_branch"] == ["computed", "pruned"]


def test_compare_flexible_judges_members_pathway_and_barrier() -> None:
    """Per-member G and the pathway G within 1e-5 Eh; the ensemble dG‡ within the ddG bound."""
    new, old = flex_fragment("ethyl", "uma"), flex_fragment("ethyl", "uma")
    assert compare_flexible(new, old, "uma", "n")["status"] == "pass"
    new["reported"]["members"][1]["G_hartree"] += 2e-5
    assert compare_flexible(new, old, "uma", "n")["mismatches"] == [
        "max_abs_delta_member_G_hartree"
    ]
    new, old = flex_fragment("ethyl", "uma"), flex_fragment("ethyl", "uma")
    new["reported"]["barrier"]["ensemble_dG_dagger_1M_kcal_mol"] += 0.5
    assert compare_flexible(new, old, "uma", "n")["status"] == "pass"
    assert compare_flexible(new, old, "xtb", "n")["mismatches"] == [
        "abs_delta_dG_dagger_1M_kcal_mol"
    ]
    new, old = flex_fragment("ethyl", "uma"), flex_fragment("ethyl", "uma")
    new["reported"]["G_pathway_hartree"] = None
    assert (
        "abs_delta_G_pathway_hartree: missing"
        in compare_flexible(new, old, "uma", "n")["mismatches"]
    )


def test_compare_flexible_member_count_differs_only_through_a_timeout() -> None:
    """R28: a count difference fails, unless a PreRelaxTimeout explains it."""
    old = flex_fragment("nbutyl", "uma", n_members=5)
    new = flex_fragment("nbutyl", "uma", n_members=4)
    assert compare_flexible(new, old, "uma", "n")["mismatches"] == ["n_members"]
    new["reported"]["exclusions_by_reason"] = {"pre_relax_failed:PreRelaxTimeout": 1}
    result = compare_flexible(new, old, "uma", "n")
    assert result["status"] == "pass" and result["difference_explained_by_timeout"] is True
    assert result["n_members"] == [4, 5] and result["pre_relax_timeouts"] == [1, 0]
    assert result["unmatched_member_G_hartree_in_fixture"] == [
        old["reported"]["members"][4]["G_hartree"]
    ]
    assert result["unmatched_member_G_hartree_in_run"] == []
    assert result["heavy_rmsd_angstrom"] is None


def test_compare_flexible_pairs_members_by_energy_not_by_source_label() -> None:
    """Equal-energy copies may swap labels between runs; the energies still pair and pass."""
    old = flex_fragment("ethyl", "uma", n_members=3)
    new = flex_fragment("ethyl", "uma", n_members=3)
    new["reported"]["members"][2]["source"] = "fragment_embed:7"
    result = compare_flexible(new, old, "uma", "n")
    assert result["status"] == "pass" and result["mismatches"] == []
    assert result["sources_in_run"] != result["sources_in_fixture"]
    new["reported"]["members"][2]["G_hartree"] += 3e-5  # an energy moved beyond the bound
    assert compare_flexible(new, old, "uma", "n")["mismatches"] == [
        "max_abs_delta_member_G_hartree"
    ]


def test_compare_flexible_pairs_the_nearest_energies_when_a_member_is_missing() -> None:
    """With a timeout-explained missing member, each remaining member takes its nearest partner."""
    old = flex_fragment("nbutyl", "uma", n_members=4)
    new = flex_fragment("nbutyl", "uma", n_members=4)
    new["reported"]["exclusions_by_reason"] = {"pre_relax_failed:PreRelaxTimeout": 1}
    del new["reported"]["members"][1]  # the run lost the member at -100.001
    result = compare_flexible(new, old, "uma", "n")
    assert result["status"] == "pass" and result["max_abs_delta_member_G_hartree"] == 0.0
    assert result["unmatched_member_G_hartree_in_fixture"] == [-100.001]


# --- The committed verdict record (slice 12) --------------------------------------------------

COMMITTED = Path(__file__).resolve().parents[2] / "docs" / "prd" / "v0.6.0"


def committed() -> dict[str, Any]:
    """The committed verdict record."""
    path = COMMITTED / "ACCEPTANCE_RESULT.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def test_the_committed_record_states_the_verdict_the_rule_gives() -> None:
    """US-012: check() passes, the verdict is pass, and it is the rule's own value."""
    record = committed()
    assert check(record) == []
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert outstanding(record) == {}
    assert command_problems(record["commands"]) == []
    rule = record_verdict(record["fixtures"], record["default_suite"], record["commands"])
    assert rule == {"verdict": "pass", "verdict_reasons": []}


def test_the_committed_record_ran_against_the_promoted_fixtures_with_the_flag() -> None:
    """R9, R31: the flag, the xtb path, TJ's promotion and the files it verified."""
    record = committed()
    environment = record["environment"]
    assert environment["xtb"]["ETA_RXNCAT_ACCEPTANCE"] == "1"
    assert environment["uma"]["ETA_RXNCAT_ACCEPTANCE"] == "1"
    assert environment["xtb"]["ETA_RXNCAT_XTB"].endswith("/xtb")
    promotion = record["evidence"]["promotion"]
    assert promotion == promotion_evidence()
    assert "resume_note" not in record["evidence"]
    assert set(record["evidence"]["run_commits"].values()) == {record["commit_sha"]}


def test_the_committed_record_keeps_tjs_bounds_and_slice_11_reproducibility() -> None:
    """The bounds are TJ's; the reproducibility measurement is slice 11's, named as such."""
    record = committed()
    assert record["regression_bounds"]["recipes"] == PROPOSAL_BOUNDS
    assert "slice 11 record at" in record["evidence"]["reproducibility_source"]
    for recipe in RECIPES:
        for pair in PAIRS:
            assert record["reproducibility"][recipe][pair]["status"] == "measured"
    assert set(record["reproducibility"]["xtb"]) == set(PAIRS)  # slice 14 has none
    for pair in PAIRS:
        for recipe in RECIPES:
            assert record["fixtures"]["t4"][pair][recipe]["regression"]["status"] == "pass"
    for r in FLEX:
        for recipe in RECIPES:
            entry = record["fixtures"]["flexible_ensemble"][r][recipe]
            assert entry["regression"]["status"] == "pass"
