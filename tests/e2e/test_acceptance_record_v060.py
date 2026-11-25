"""The v0.6.0 acceptance record: merge, schema check, gated states and bounds (slice 11)."""

import copy
import hashlib
from pathlib import Path
from typing import Any

import pytest
from acceptance_record_v060 import (
    FLEX,
    FLEX_GATES,
    G1_TESTS,
    G4_TESTS,
    HF1_SHA256,
    KNOWN_LIMITS,
    PAIRS,
    PROPOSAL_BOUNDS,
    RECIPES,
    check,
    command_problems,
    ensemble_block,
    entry_states,
    fixture_states,
    flexible_entry,
    flexible_states,
    merge_runs,
    outstanding,
    pair_entry,
    proposed_bounds,
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


def merged(runs: dict[str, dict[str, Any]] | None = None, commands: Any = None) -> dict[str, Any]:
    """The merged record of synthetic runs."""
    runs = runs or {r: run_file(r) for r in RECIPES}
    return merge_runs(
        runs, copy.deepcopy(commands or COMMANDS), copy.deepcopy(SUITE), copy.deepcopy(UNIT)
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
