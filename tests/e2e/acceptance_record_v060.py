r"""Merge the v0.6.0 Tier 4 acceptance files into docs/prd/v0.6.0/ACCEPTANCE_RESULT.json (slice 11).

Usage::

    python3 tests/e2e/acceptance_record_v060.py suite <default_suite.log> <default_suite.json>
    python3 tests/e2e/acceptance_record_v060.py unit-proof <log> <exit_code> <unit_proof.json>
    python3 tests/e2e/acceptance_record_v060.py add-command <commands.json> <log> <exit_code> \\
        <wall_s> <env.json> -- <argv...>
    python3 tests/e2e/acceptance_record_v060.py merge <acceptance_xtb.json> <acceptance_uma.json> \\
        <commands.json> <default_suite.json> <unit_proof.json> <out.json>

``add-command`` appends one run (argv, env, exit code, wall time, the pytest summary and the max
RSS read from its log) to ``commands.json``; ``suite`` derives ``default_suite`` from the pytest
log and ``unit-proof`` the G1/G4 node outcomes from a ``-v`` log. None is typed by hand. This is
the pre-promotion record: it has no ``verdict``, ``regression`` is ``pending_promotion`` and
``transcription_confirmation`` is ``pending_confirmation`` (TJ's Phase 3). A gated check is
``pass`` only when measured; anything else is a state, never a guess (R56).
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from acceptance_record_v040 import pytest_counts
from acceptance_record_v050 import command_entry, heavy_rmsd_angstrom

from eta_rxncat.engines import HARTREE_KCAL_MOL

REPO = Path(__file__).resolve().parents[2]
PAIRS = ("t4_unmapped", "t4_mapped")
RECIPES = ("xtb", "uma")
PATHWAYS = ("endo", "exo")
STATES = {"pass", "fail", "pending_promotion", "pending_confirmation", "skipped", "missing"}
TEST_OUTCOMES = {"passed", "failed", "missing"}
XYZ_DIR = REPO / "tests" / "e2e" / "data" / "e2e5" / "xyz"
TIMEOUT_REASON = "pre_relax_failed:PreRelaxTimeout"

HF1_SHA256 = {
    "TS1a_x.xyz": "ec319a528d3efd0d7c14fb1d018d31d57eae85e794df59761665ed4d0f684d60",
    "TS1b_x.xyz": "2a0b8362cdd36464c5f3f7a196927005c1cc933f3fdc6a693ae0d56ff365fd82",
    "P1b_x.xyz": "ca8706431f6e8b57662a3f65196a9ca3cba3288a4eda68308f7bc3c9699b5eec",
}
"""Mission HF-1: the three slice 08 transcriptions (the values test_t4_inputs.py checks)."""
HEADER_DDG = {"unmapped": 4.273, "mapped": 1.849}
"""Mission HF-2: Liu's header ΔΔG‡ (kcal/mol), G(exo) - G(endo), within 0.005."""
HEADER_FILES = {
    "unmapped": ("TS1a_n.xyz", "TS1a_x.xyz"),
    "mapped": ("TS1b_n.xyz", "TS1b_x.xyz"),
}

G1_TESTS = (
    "test_two_single_member_pathways_closed_form",
    "test_literature_checks",
    "test_multi_member_pathways_and_degeneracy",
    "test_degeneracy_two_is_g_minus_rt_ln_two",
    "test_tie_is_fifty_fifty",
    "test_large_gap_does_not_overflow_or_clamp",
    "test_temperature_350",
    "test_permutation_invariance_is_exact",
    "test_mixed_reactant_sets",
    "test_mixed_recipe_identities",
    "test_fewer_than_two_pathways",
    "test_ee_refused_over_multi_member_ensembles",
)
G4_TESTS = (
    "test_two_saddles_merge_copies",
    "test_weights_and_free_energy_closed_form",
    "test_every_exclusion_reason_is_recorded",
    "test_pre_relax_freezes_the_core_within_the_bound",
    "test_a_face_flip_is_the_descriptor_not_the_geometry_label",
    "test_endo_is_plus_plus_and_the_crossover_is_minus_minus",
    "test_invariant_under_reflection_and_rigid_motion",
    "test_core_is_exactly_the_seeds_and_the_face_is_kept",
    "test_deterministic_and_seed_dependent",
)
UNIT_FILES = (
    "tests/unit/orchestrator/test_selectivity_score.py",
    "tests/unit/orchestrator/test_ts_ensemble.py",
    "tests/unit/conformers/test_ts_sampler.py",
)
UNIT_GROUPS = {"G1": G1_TESTS, "G4": G4_TESTS}

PROPOSAL_BOUNDS = {
    "xtb": {
        "abs_delta_ts_energy_hartree": 1e-5,
        "heavy_rmsd_angstrom": 0.01,
        "abs_delta_ddG_dagger_kcal_mol": 0.01,
    },
    "uma": {
        "abs_delta_ts_energy_hartree": 1e-5,
        "heavy_rmsd_angstrom": 0.01,
        "abs_delta_ddG_dagger_kcal_mol": 0.75,
    },
}
"""TJ's v0.4.0 Q6 numbers and the v0.5.0 R33 ΔΔG‡ numbers (0.75 "all" read per R6)."""
BOUND_RULE = (
    "propose TJ's bound only if every measured difference of that recipe is <= 1/10 of it; "
    "otherwise propose 10x the measured maximum (slice 11 SPEC; the numeric bounds are TJ's)"
)
MEASURED_KEYS = {
    "abs_delta_ts_energy_hartree": "max_abs_delta_ts_energy_hartree",
    "heavy_rmsd_angstrom": "max_heavy_rmsd_angstrom",
    "abs_delta_ddG_dagger_kcal_mol": "max_abs_delta_ddG_dagger_kcal_mol",
}
KNOWN_LIMITS = (
    "Tier 4 ensembles are reported as measured (member count, exclusions by reason, merges); "
    "HF-10 expects one distinct member per pathway, so the Boltzmann sum is gated at unit level "
    "(G1, G4) and ΔΔG‡ equals the seed difference only when every ensemble has one member",
    "a pre_relax_failed:PreRelaxTimeout exclusion (slice 13, R28) is reported, not gated; a change "
    "in member count or exclusions between runs is expected variation, not a failure",
    "Q-RES1 is with TJ; no slice built under a Q-RES1 answer is part of this record",
)
REPORTED_NOTES = {
    "promotion": (
        "the v0.6.0 candidates are not yet TJ's fixtures: regression is pending_promotion until "
        "TJ's Phase 3 review"
    ),
    "regression_endo_seed": (
        "the endo seed is compared in process with TJ's promoted v0.5.0 fixture (mission R6); "
        "that comparison is a gate, and distinct from the pending Tier 4 regression"
    ),
}
FIXTURE_KEYS = {"t4", "unit_proof", "transcriptions", "transcription_confirmation"}
TOP_KEYS = (
    "record_schema",
    "commit_sha",
    "run_at_utc",
    "hardware",
    "engines",
    "devices",
    "environment",
    "commands",
    "logs",
    "default_suite",
    "known_limits",
    "reported_notes",
    "evidence",
    "fixtures",
    "reproducibility",
    "proposed_regression_bounds",
)


# --- states -----------------------------------------------------------------------------------


def _status(value: Any) -> Any:
    return value.get("status") if isinstance(value, dict) else value


def entry_states(entry: dict[str, Any]) -> dict[str, Any]:
    """The gated states of one pair x recipe entry, by name."""
    outcome = entry.get("test_outcome")
    if outcome == "missing":
        return {"test_outcome": "missing"}
    states: dict[str, Any] = {} if outcome == "passed" else {"test_outcome": "fail"}
    for gate, value in sorted(entry.get("tier_gates", {}).items()):
        if _status(value) != "reported":
            states[f"tier_gates.{gate}"] = _status(value)
    for pathway, block in sorted(entry.get("ensembles", {}).items()):
        for count in ("engine_error", "face_mismatch"):
            states[f"ensembles.{pathway}.{count}"] = "pass" if block.get(count) == 0 else "fail"
    states["regression"] = _status(entry.get("regression"))
    return states


def fixture_states(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Every gated state of the record's ``fixtures`` by dotted name."""
    states: dict[str, Any] = {}
    t4 = fixtures.get("t4", {})
    for pair in PAIRS:
        for recipe in RECIPES:
            entry = t4.get(pair, {}).get(recipe, {"test_outcome": "missing"})
            for name, state in entry_states(entry).items():
                states[f"t4.{pair}.{recipe}.{name}"] = state
    unit = fixtures.get("unit_proof", {})
    for group in UNIT_GROUPS:
        states[f"unit_proof.{group}"] = _status(unit.get(group, {"status": "missing"}))
    transcriptions = fixtures.get("transcriptions", {})
    for part in ("sha256", "header_ddG"):
        states[f"transcriptions.{part}"] = _status(transcriptions.get(part, {"status": "missing"}))
    states["transcription_confirmation"] = _status(
        fixtures.get("transcription_confirmation", {"status": "missing"})
    )
    return states


def outstanding(record: dict[str, Any]) -> dict[str, Any]:
    """Every gated state that is not ``pass`` (a pre-promotion record has only the pending ones)."""
    return {k: v for k, v in fixture_states(record["fixtures"]).items() if v != "pass"}


def command_problems(commands: list[dict[str, Any]]) -> list[str]:
    """A command with a non-zero exit or a skip (the skip count read from its pytest summary)."""
    problems = []
    for i, command in enumerate(commands):
        where = f"commands[{i}] {' '.join(command.get('argv', [])[-3:])}"
        if command.get("exit_code") != 0:
            problems.append(f"{where}: exit_code {command.get('exit_code')}")
        skipped = pytest_counts(str(command.get("summary", "")))["skipped"]
        if skipped:
            problems.append(f"{where}: {skipped} skipped")
    return problems


def check(record: dict[str, Any]) -> list[str]:
    """Schema problems of a record (empty when valid); a pre-promotion record has no verdict."""
    problems = [f"missing {key}" for key in TOP_KEYS if key not in record]
    if "verdict" in record or "verdict_reasons" in record:
        problems.append("a pre-promotion record states no verdict (slice 12 settles it)")
    if record.get("record_schema") != 1:
        problems.append("record_schema is not 1")
    fixtures = record.get("fixtures", {})
    if set(fixtures) != FIXTURE_KEYS:
        problems.append(f"fixtures keys {sorted(fixtures)} != {sorted(FIXTURE_KEYS)}")
    t4 = fixtures.get("t4", {})
    if set(t4) != set(PAIRS) or any(set(t4[p]) != set(RECIPES) for p in t4):
        problems.append("fixtures.t4 must be every pair x recipe")
    for name, state in fixture_states(fixtures).items():
        if state not in STATES:
            problems.append(f"{name}: state {state!r} not in {sorted(STATES)}")
    for pair in t4:
        for recipe, entry in t4[pair].items():
            if entry.get("test_outcome") not in TEST_OUTCOMES:
                problems.append(f"t4.{pair}.{recipe}: test_outcome {entry.get('test_outcome')!r}")
    if list(record.get("known_limits", [])) != list(KNOWN_LIMITS):
        problems.append("known_limits are not the fixed lines")
    for key in ("command", "exit_code", "passed", "failed"):
        if key not in record.get("default_suite", {}):
            problems.append(f"default_suite: missing {key}")
    environment = record.get("environment", {})
    for recipe in RECIPES:
        env = environment.get(recipe, {})
        if env.get("ETA_RXNCAT_ACCEPTANCE") != "1":
            problems.append(f"environment.{recipe}: ETA_RXNCAT_ACCEPTANCE=1 is not recorded (R9)")
        if recipe == "xtb" and not env.get("ETA_RXNCAT_XTB"):
            problems.append("environment.xtb: ETA_RXNCAT_XTB is not recorded (R9)")
    for command in record.get("commands", []):
        if command.get("env", {}).get("ETA_RXNCAT_ACCEPTANCE") not in (None, "1"):
            problems.append(f"a command ran with ETA_RXNCAT_ACCEPTANCE={command['env']!r}")
    return problems


# --- entries from the fragments ---------------------------------------------------------------


def ensemble_block(ensemble: dict[str, Any]) -> dict[str, Any]:
    """Per-pathway ensemble counts; only ``engine_error`` and ``face_mismatch`` are gated."""
    reasons = Counter(e["reason"] for e in ensemble.get("excluded", []))
    walls = [
        m["pre_relax_wall_time_s"]
        for m in [*ensemble.get("members", []), *ensemble.get("excluded", [])]
        if m.get("pre_relax_wall_time_s") is not None
    ]
    return {
        "failed_reason": ensemble.get("failed_reason"),
        "n_members": len(ensemble.get("members", [])),
        "n_excluded": len(ensemble.get("excluded", [])),
        "exclusions_by_reason": dict(sorted(reasons.items())),
        "n_merges": len(ensemble.get("merges", [])),
        "n_flagged_merges": len(ensemble.get("flagged_merges", [])),
        "engine_error": reasons.get("engine_error", 0),
        "face_mismatch": reasons.get("face_mismatch", 0),
        "pre_relax_timeouts": reasons.get(TIMEOUT_REASON, 0),
        "max_pre_relax_wall_time_s": max(walls) if walls else None,
        "G_pathway_hartree": ensemble.get("G_pathway_hartree"),
    }


def pair_entry(fragment: dict[str, Any]) -> dict[str, Any]:
    """The record entry of one pair x recipe from its in-process fragment."""
    if fragment.get("test_outcome") == "missing":
        return {"test_outcome": "missing"}
    checks = fragment.get("checks", {})
    score = fragment.get("score") or {}
    entry: dict[str, Any] = {
        "test_outcome": fragment.get("test_outcome"),
        "failed_checks": fragment.get("failed_checks", []),
        "tier_gates": dict(checks.get("tier_gates", {})),
        "ensembles": {
            p: ensemble_block(v["ensemble"])
            for p, v in sorted(fragment.get("pathways", {}).items())
        },
        "selectivity": {
            k: score.get(k)
            for k in (
                "ddG_dagger_kcal_mol",
                "major_pathway",
                "ratio",
                "selectivity_percent",
                "kind",
                "temperature_k",
            )
        },
        "reported": fragment.get("reported"),
        "second_run_cache": fragment.get("second_run_cache"),
        "regression": {
            "status": "pending_promotion",
            "note": "the v0.6.0 candidates are not yet TJ's fixtures (Phase 3)",
        },
    }
    if "pruning" in fragment:
        entry["pruning"] = fragment["pruning"]
    if "exo_graft" in fragment:
        graft = dict(fragment["exo_graft"])
        graft.pop("pre_relaxed_start", None)
        entry["exo_graft"] = graft
    return entry


def transcriptions_block(xyz_dir: Path = XYZ_DIR) -> dict[str, Any]:
    """HF-1 sha256s and HF-2 header ΔΔG‡, recomputed from the committed files."""
    files = {}
    for name, expected in sorted(HF1_SHA256.items()):
        path = xyz_dir / name
        observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        files[name] = {"expected": expected, "observed": observed}
    sha_ok = all(f["expected"] == f["observed"] for f in files.values())

    def header_g(name: str) -> float | None:
        path = xyz_dir / name
        if not path.is_file():
            return None
        lines = path.read_text(encoding="utf-8").splitlines()
        header = lines[1] if len(lines) > 1 else ""
        match = re.search(r"G\s*=\s*(-\d+\.\d+)", header)
        return float(match.group(1)) if match else None

    rows: dict[str, Any] = {}
    for key, (endo, exo) in HEADER_FILES.items():
        g_endo, g_exo = header_g(endo), header_g(exo)
        value = None if g_endo is None or g_exo is None else (g_exo - g_endo) * HARTREE_KCAL_MOL
        rows[key] = {
            "expected_kcal_mol": HEADER_DDG[key],
            "observed_kcal_mol": value,
            "tolerance_kcal_mol": 0.005,
        }
    ddg_ok = all(
        r["observed_kcal_mol"] is not None
        and abs(r["observed_kcal_mol"] - r["expected_kcal_mol"]) <= r["tolerance_kcal_mol"]
        for r in rows.values()
    )
    return {
        "sha256": {"status": "pass" if sha_ok else "fail", "files": files},
        "header_ddG": {"status": "pass" if ddg_ok else "fail", "rows": rows},
    }


def unit_proof_block(log_text: str, exit_code: int) -> dict[str, Any]:
    """G1 and G4 test outcomes by node id from a ``pytest -v`` log of ``UNIT_FILES``."""
    outcomes: dict[str, str] = {}
    for match in re.finditer(
        r"^(\S+\.py::\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)", log_text, re.M
    ):
        outcomes[match.group(1)] = match.group(2)
    block: dict[str, Any] = {"command_exit_code": exit_code}
    for group, names in UNIT_GROUPS.items():
        nodes: dict[str, list[str]] = {}
        for name in names:
            found = {
                node: result
                for node, result in outcomes.items()
                if re.search(rf"::{re.escape(name)}(\[|$)", node)
            }
            nodes[name] = sorted(f"{node} {result}" for node, result in found.items())
        ok = exit_code == 0 and all(
            nodes[n] and all(line.endswith(" PASSED") for line in nodes[n]) for n in names
        )
        block[group] = {"status": "pass" if ok else "fail", "nodes": nodes}
    return block


# --- reproducibility --------------------------------------------------------------------------


def run_values(fragment: dict[str, Any]) -> dict[str, Any] | None:
    """The acceptance run's per-pathway TS energy, geometry and member counts, and ΔΔG‡."""
    if fragment.get("test_outcome") == "missing":
        return None
    pathways: dict[str, Any] = {}
    for p, block in sorted(fragment.get("pathways", {}).items()):
        ts = block.get("seed_ts") or {}
        if ts.get("failed_reason") is not None or not ts.get("thermo") or not ts.get("state"):
            return None
        eb = ensemble_block(block["ensemble"])
        pathways[p] = {
            "ts_energy_hartree": ts["thermo"]["electronic_energy_hartree"],
            "ts_state": ts["state"],
            "n_members": eb["n_members"],
            "exclusions_by_reason": eb["exclusions_by_reason"],
        }
    score = fragment.get("score")
    if not pathways or score is None:
        return None
    gate = fragment.get("checks", {}).get("tier_gates", {}).get("pruning_g6", {})
    return {
        "pathways": pathways,
        "ddG_dagger_kcal_mol": score["ddG_dagger_kcal_mol"],
        "branch": gate.get("branch"),
    }


def reproducibility_entry(
    pair: str, recipe: str, pair_fragment: dict[str, Any], repro_fragment: dict[str, Any]
) -> dict[str, Any]:
    """Max |ΔE_TS|, |ΔΔG‡| and heavy RMSD over every pair of the three fresh-store runs."""
    acceptance = run_values(pair_fragment)
    if acceptance is None or repro_fragment.get("test_outcome") == "missing":
        return {"status": "missing", "reason": "a run has no converged TS or no fragment"}
    runs = [acceptance, *repro_fragment["runs"]]
    labels = ["acceptance_run", *[f"fresh_store_{k + 1}" for k in range(len(runs) - 1)]]
    index_pairs = [(i, j) for i in range(len(runs)) for j in range(i + 1, len(runs))]
    de, rmsd, member_changes, exclusion_changes = [], [], [], []
    for i, j in index_pairs:
        for p in sorted(runs[i]["pathways"]):
            a, b = runs[i]["pathways"][p], runs[j]["pathways"][p]
            de.append(abs(a["ts_energy_hartree"] - b["ts_energy_hartree"]))
            rmsd.append(heavy_rmsd_angstrom(a["ts_state"], b["ts_state"]))
            if a["n_members"] != b["n_members"]:
                member_changes.append(
                    {
                        "pathway": p,
                        "runs": [labels[i], labels[j]],
                        "members": [a["n_members"], b["n_members"]],
                    }
                )
            if a["exclusions_by_reason"] != b["exclusions_by_reason"]:
                exclusion_changes.append(
                    {
                        "pathway": p,
                        "runs": [labels[i], labels[j]],
                        "exclusions_by_reason": [
                            a["exclusions_by_reason"],
                            b["exclusions_by_reason"],
                        ],
                    }
                )
    dg = [
        abs(runs[i]["ddG_dagger_kcal_mol"] - runs[j]["ddG_dagger_kcal_mol"]) for i, j in index_pairs
    ]
    branches = [r.get("branch") for r in runs]
    return {
        "status": "measured",
        "n_runs": len(runs),
        "runs": {
            label: {
                "ddG_dagger_kcal_mol": r["ddG_dagger_kcal_mol"],
                "branch": r.get("branch"),
                "ts_energy_hartree": {p: v["ts_energy_hartree"] for p, v in r["pathways"].items()},
                "n_members": {p: v["n_members"] for p, v in r["pathways"].items()},
            }
            for label, r in zip(labels, runs, strict=True)
        },
        "max_abs_delta_ts_energy_hartree": max(de),
        "max_abs_delta_ddG_dagger_kcal_mol": max(dg),
        "max_heavy_rmsd_angstrom": max(rmsd),
        "member_count_changes": member_changes,
        "exclusion_changes": exclusion_changes,
        "branch_changed": len(set(branches)) > 1,
        "pre_relax_timeouts_in_repro_runs": repro_fragment.get("pre_relax_timeouts", 0),
    }


def proposed_bounds(reproducibility: dict[str, Any]) -> dict[str, Any]:
    """Per recipe and quantity: TJ's bound if every measurement is <= 1/10 of it, else 10x max."""
    out: dict[str, Any] = {"rule": BOUND_RULE, "decided_by": "TJ at Phase 3", "recipes": {}}
    for recipe in RECIPES:
        entries = dict(reproducibility.get(recipe, {}))
        measured = {p: e for p, e in entries.items() if e.get("status") == "measured"}
        missing = sorted(p for p, e in entries.items() if e.get("status") != "measured")
        block: dict[str, Any] = {
            "pairs_measured": sorted(measured),
            "pairs_not_measured": missing,
        }
        for quantity, bound in PROPOSAL_BOUNDS[recipe].items():
            values = [e[MEASURED_KEYS[quantity]] for e in measured.values()]
            if missing or not values:
                block[quantity] = {"status": "missing", "tj_bound": bound}
                continue
            worst = max(values)
            worst_pair = max(measured, key=lambda p: measured[p][MEASURED_KEYS[quantity]])
            if worst <= bound / 10:
                proposed, basis = bound, "tj_bound"
                statement = f"measured max {worst:.3g} <= 1/10 of TJ's {bound:g}: TJ's bound"
            else:
                proposed, basis = 10 * worst, "ten_times_measured_max"
                statement = (
                    f"measured max {worst:.3g} ({worst_pair}) exceeds 1/10 of TJ's {bound:g}: "
                    f"proposing 10x the measured maximum, {proposed:.3g}, for TJ to decide"
                )
            block[quantity] = {
                "tj_bound": bound,
                "measured_max": worst,
                "measured_max_pair": worst_pair,
                "proposed": proposed,
                "basis": basis,
                "statement": statement,
            }
        out["recipes"][recipe] = block
    return out


# --- command and suite blocks -----------------------------------------------------------------


def suite_block(suite_log: Path) -> dict[str, Any]:
    """The ``default_suite`` block from the pytest log (first line ``exit_code=<n>``)."""
    text = suite_log.read_text(encoding="utf-8")
    exit_code = int(re.search(r"exit_code=(\d+)", text).group(1))  # type: ignore[union-attr]
    return {"command": "uv run pytest", "exit_code": exit_code, **pytest_counts(text)}


# --- merge ------------------------------------------------------------------------------------


def environment_block(
    runs: dict[str, dict[str, Any]], commands: list[dict[str, Any]]
) -> dict[str, Any]:
    """Per recipe: the Python version and the variables of that recipe's recorded commands."""
    out: dict[str, Any] = {}
    for recipe in RECIPES:
        env: dict[str, str] = {}
        for command in commands:
            if command.get("env", {}).get("recipe") == recipe:
                env.update({k: v for k, v in command["env"].items() if k != "recipe"})
        out[recipe] = {"python": runs[recipe]["python"], **dict(sorted(env.items()))}
    return out


def merge_runs(
    runs: dict[str, dict[str, Any]],
    commands: list[dict[str, Any]],
    default_suite: dict[str, Any],
    unit_proof: dict[str, Any],
    xyz_dir: Path = XYZ_DIR,
) -> dict[str, Any]:
    """Build the pre-promotion record from the two per-recipe files and the command logs."""
    shas = {r["commit_sha"] for r in runs.values()}
    if len(shas) != 1 or not all(r["tree_clean"] for r in runs.values()):
        raise ValueError(f"recipes ran at different or unclean commits: {shas}")
    missing = {"test_outcome": "missing"}
    t4 = {
        pair: {recipe: pair_entry(runs[recipe]["pairs"].get(pair, missing)) for recipe in RECIPES}
        for pair in PAIRS
    }
    reproducibility = {
        recipe: {
            pair: reproducibility_entry(
                pair,
                recipe,
                runs[recipe]["pairs"].get(pair, missing),
                runs[recipe]["reproducibility"].get(pair, missing),
            )
            for pair in PAIRS
        }
        for recipe in RECIPES
    }
    fixtures = {
        "t4": t4,
        "unit_proof": unit_proof,
        **transcription_fixtures(xyz_dir),
    }
    record: dict[str, Any] = {
        "record_schema": 1,
        "commit_sha": shas.pop(),
        "run_at_utc": max(r["run_at_utc"] for r in runs.values()),
        "hardware": runs["uma"]["hardware"],
        "engines": {recipe: run["engine"] for recipe, run in sorted(runs.items())},
        "devices": {recipe: run["device"] for recipe, run in sorted(runs.items())},
        "environment": environment_block(runs, commands),
        "commands": [{k: v for k, v in c.items() if k != "log"} for c in commands],
        "logs": {
            c["log"]: {"exit_code": c["exit_code"], "summary": c["summary"]} for c in commands
        },
        "default_suite": default_suite,
        "known_limits": list(KNOWN_LIMITS),
        "reported_notes": dict(REPORTED_NOTES),
        "evidence": {
            "candidates_phase3_set": (
                "tests/candidate_outputs/v0.6.0/ (slices 09-10), committed for TJ's Phase 3 "
                "review; never read by this record"
            ),
            "record_run_candidates": "written to a scratch ETA_RXNCAT_CANDIDATE_DIR, not committed",
            "candidate_values": (
                "the acceptance run reruns slice 09-10 code in process at this commit; its values "
                "stand for the candidates' (no candidate file is read, slice 11 firewall)"
            ),
        },
        "fixtures": fixtures,
        "reproducibility": reproducibility,
        "proposed_regression_bounds": proposed_bounds(reproducibility),
    }
    problems = check(record)
    if problems:
        raise ValueError(f"record invalid: {problems}")
    return record


def transcription_fixtures(xyz_dir: Path) -> dict[str, Any]:
    """The ``transcriptions`` block and TJ's pending confirmation (never settled here)."""
    return {
        "transcriptions": transcriptions_block(xyz_dir),
        "transcription_confirmation": {
            "status": "pending_confirmation",
            "note": "TJ confirms the three transcriptions at Phase 3",
        },
    }


def _dump(path: Path, data: Any) -> None:
    text = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    """``suite``, ``unit-proof``, ``add-command`` or ``merge`` (see the module docstring)."""
    if len(argv) == 3 and argv[0] == "suite":
        _dump(Path(argv[2]), suite_block(Path(argv[1])))
        print(f"wrote {argv[2]}")
        return 0
    if len(argv) == 4 and argv[0] == "unit-proof":
        text = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
        block = unit_proof_block(text, int(argv[2]))
        _dump(Path(argv[3]), block)
        print(f"wrote {argv[3]}: G1 {block['G1']['status']}, G4 {block['G4']['status']}")
        return 0
    if len(argv) >= 8 and argv[0] == "add-command" and argv[6] == "--":
        path = Path(argv[1])
        commands = _load(argv[1]) if path.exists() else []
        commands.append(
            command_entry(Path(argv[2]), int(argv[3]), float(argv[4]), _load(argv[5]), argv[7:])
        )
        _dump(path, commands)
        print(f"{path}: {len(commands)} commands; last {commands[-1]['summary']!r}")
        return 0
    if len(argv) == 7 and argv[0] == "merge":
        runs = {"xtb": _load(argv[1]), "uma": _load(argv[2])}
        record = merge_runs(runs, _load(argv[3]), _load(argv[4]), _load(argv[5]))
        _dump(Path(argv[6]), record)
        print(f"wrote {argv[6]}; outstanding {outstanding(record)}")
        print(f"command problems: {command_problems(record['commands'])}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
