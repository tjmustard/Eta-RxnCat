r"""Merge the v0.6.0 Tier 4 acceptance files into docs/prd/v0.6.0/ACCEPTANCE_RESULT.json (slice 11).

Usage::

    python3 tests/e2e/acceptance_record_v060.py suite <default_suite.log> <default_suite.json>
    python3 tests/e2e/acceptance_record_v060.py unit-proof <log> <exit_code> <unit_proof.json>
    python3 tests/e2e/acceptance_record_v060.py add-command <commands.json> <log> <exit_code> \\
        <wall_s> <env.json> -- <argv...>
    python3 tests/e2e/acceptance_record_v060.py merge <acceptance_xtb.json> <acceptance_uma.json> \\
        <commands.json> <default_suite.json> <unit_proof.json> <out.json> [<prior_record.json>]

``add-command`` appends one run (argv, env, exit code, wall time, the pytest summary and the max
RSS read from its log) to ``commands.json``; ``suite`` derives ``default_suite`` from the pytest
log and ``unit-proof`` the G1/G4 node outcomes from a ``-v`` log. None is typed by hand. This is
Without TJ's promoted fixtures the merge writes the pre-promotion record (slice 11): no
``verdict``, ``regression`` ``pending_promotion``, ``transcription_confirmation``
``pending_confirmation``. Once ``tests/fixtures/v0.6.0/`` holds TJ's ten files, equal to R31's
sha256 and blob-id prefixes (``evidence.promotion``), the merge compares each in-process result with
its promoted fixture under TJ's bounds and writes ``verdict`` from ``record_verdict`` (slice 12):
``pass`` only with every gated check ``pass``, a clean default suite and every command at exit 0
with no skip; anything ``fail``, ``pending_*``, ``skipped`` or ``missing`` gives ``fail`` (R56).
The verdict run carries slice 11's reproducibility measurement over from the prior record.
"""

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from acceptance_record_v040 import pytest_counts
from acceptance_record_v050 import command_entry, git_blob_id, heavy_rmsd_angstrom

from eta_rxncat.engines import HARTREE_KCAL_MOL

REPO = Path(__file__).resolve().parents[2]
PAIRS = ("t4_unmapped", "t4_mapped")
RECIPES = ("xtb", "uma")
PATHWAYS = ("endo", "exo")
FLEX = ("ethyl", "npropyl", "nbutyl")
"""Slice 14: the alkyl R-group series grafted onto TS1a_n (chain length order)."""
STATES = {"pass", "fail", "pending_promotion", "pending_confirmation", "skipped", "missing"}
TEST_OUTCOMES = {"passed", "failed", "missing"}
XYZ_DIR = REPO / "tests" / "e2e" / "data" / "e2e5" / "xyz"
PROMOTED_V060 = REPO / "tests" / "fixtures" / "v0.6.0"
TIMEOUT_REASON = "pre_relax_failed:PreRelaxTimeout"
FLEX_GATES = (
    "graft_pre_relax_no_timeout",
    "ensemble_no_failed_reason",
    "distinct_members_at_least_2",
    "weights_sum_to_one",
    "faces_equal_the_seeds_no_face_or_engine_error",
    "second_pass_all_hits_equal_ensemble",
)
"""Slice 14's gates (a)-(f), by the names ``t4_flexible.gates`` writes."""

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
REGRESSION_BOUNDS = PROPOSAL_BOUNDS
"""TJ's Phase 3 bounds (mission R31, "A"): |ΔE_TS| <= 1e-5 Eh, heavy-atom RMSD <= 0.01 Å and
|ΔΔG‡| <= 0.01 kcal/mol on GFN2, <= 0.75 on UMA; they equal slice 11's proposed bounds."""
PROMOTION = {
    "source": "mission R31 (TJ's Phase 3; closes R6's pending bounds for v0.6.0)",
    "commit": "6fce509",
    "commit_subject": "Promote v0.6.0 Tier 4 fixtures (TJ's Phase 3 review)",
    "tj_answer": (
        "A (bounds, recommended); promote all 10; transcriptions + YAMLs confirmed "
        "(as the lead recorded it in mission R31)"
    ),
    "relayed_by": (
        "advisor-lead@kernel, qitem-20261125202058-42fe20c9cc89f35c, ~20:16Z, answering "
        "qitem-20261125201152-c39bcf3269a5d868"
    ),
    "copied_by": (
        'advisor-lead@kernel on TJ\'s instruction ("Advisor runs it for me") at 097fa2a; the lead '
        "verified 10/10 git blob ids equal to the committed candidates and committed 6fce509"
    ),
    "transcriptions_confirmed": (
        "TS1b_x (Liu S9/S10), P1b_x (Liu S20), the RDKit SMILES of P1b_x and TS1a_x, and the three "
        "provisional Tier 4 YAMLs (unmapped, mapped-pruned at 1.5, flexible alkyl)"
    ),
}
"""TJ's Phase 3 answer as the lead recorded it in mission R31 (never inferred from a status)."""
PROMOTED_FILES = {
    "t4_unmapped.xtb.json": ("ec7fdade2a58", "4c7e50ae1f1a"),
    "t4_unmapped.uma.json": ("485cb6124e10", "ba24561e24e3"),
    "t4_mapped.xtb.json": ("6fe221444682", "f11bcc380727"),
    "t4_mapped.uma.json": ("b5aefb47e6f4", "4503fa006267"),
    "t4_flexible_ethyl.xtb.json": ("3fe244c64527", "9a52dce1a093"),
    "t4_flexible_ethyl.uma.json": ("af37d9d5995e", "febbbd3145da"),
    "t4_flexible_npropyl.xtb.json": ("63dd6eb1f332", "3e64530495ee"),
    "t4_flexible_npropyl.uma.json": ("e32b9ef6822f", "de1cfd70431a"),
    "t4_flexible_nbutyl.xtb.json": ("ab412d6b4f46", "d9ffb8fe8bda"),
    "t4_flexible_nbutyl.uma.json": ("ba3ce53cfa60", "d19f516dc9d6"),
}
"""Mission R31's promoted files: (sha256, git blob id), 12-character prefixes as R31 lists them."""
VERDICT_KEYS = ("verdict", "verdict_reasons", "regression_bounds")
"""Required once the record states a verdict (slice 12)."""
RESUME_NOTE = (
    "slice 11 paused after C1 1273070 for slice 14 (R30); the GFN2 Tier 4 acceptance runs and the "
    "GFN2 reproducibility run were made at 1273070 and stand: slice 14 changed no src/ file and no "
    "Tier 4 helper (git diff --name-only 1273070..<resume HEAD> lists only its new fixture, helper "
    "and test files), so run_commits names the commit of each fragment"
)
KNOWN_LIMITS = (
    "Tier 4 ensembles are reported as measured (member count, exclusions by reason, merges); "
    "HF-10 expects one distinct member per pathway, so the Boltzmann sum is gated at unit level "
    "(G1, G4) and ΔΔG‡ equals the seed difference only when every ensemble has one member",
    "a pre_relax_failed:PreRelaxTimeout exclusion (slice 13, R28) is reported, not gated; a change "
    "in member count or exclusions between runs is expected variation, not a failure",
    "Q-RES1 was answered B by TJ: slice 14's flexible-ensemble checks (an alkyl R-group series on "
    "TS1a_n, ethyl, n-propyl, n-butyl) are part of this record; they gate mechanics only and carry "
    "no reproducibility runs and no proposed bounds",
)


def reported_notes(promoted: bool) -> dict[str, str]:
    """The record's notes; the promotion line states which mode the record is in."""
    notes = {
        "regression_endo_seed": (
            "the endo seed is compared in process with TJ's promoted v0.5.0 fixture (mission R6); "
            "that comparison is a gate, distinct from the Tier 4 regression"
        )
    }
    if promoted:
        notes["promotion"] = (
            "TJ promoted the ten v0.6.0 candidates at Phase 3 (mission R31); regression compares "
            "each in-process result with its promoted fixture under TJ's bounds"
        )
        notes["flexible_member_counts"] = (
            "a flexible case's member count may differ from its fixture only through a "
            "pre_relax_failed:PreRelaxTimeout exclusion (R28); that is reported, and the remaining "
            "members are judged against the bounds"
        )
    else:
        notes["promotion"] = (
            "the v0.6.0 candidates are not yet TJ's fixtures: regression is pending_promotion "
            "until TJ's Phase 3 review"
        )
    return notes


FIXTURE_KEYS = {
    "t4",
    "flexible_ensemble",
    "unit_proof",
    "transcriptions",
    "transcription_confirmation",
}
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


def flexible_states(entry: dict[str, Any]) -> dict[str, Any]:
    """The gated states of one R x recipe flexible-ensemble entry (slice 14 gates (a)-(f))."""
    outcome = entry.get("test_outcome")
    if outcome == "missing":
        return {"test_outcome": "missing"}
    states: dict[str, Any] = {} if outcome == "passed" else {"test_outcome": "fail"}
    for gate, value in sorted(entry.get("tier_gates", {}).items()):
        if _status(value) != "reported":
            states[f"tier_gates.{gate}"] = _status(value)
    if len(entry.get("tier_gates", {})) != len(FLEX_GATES):
        states["tier_gates.complete"] = "missing"
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
    flexible = fixtures.get("flexible_ensemble", {})
    for r_group in FLEX:
        for recipe in RECIPES:
            entry = flexible.get(r_group, {}).get(recipe, {"test_outcome": "missing"})
            for name, state in flexible_states(entry).items():
                states[f"flexible_ensemble.{r_group}.{recipe}.{name}"] = state
    unit = fixtures.get("unit_proof", {})
    for group in UNIT_GROUPS:
        states[f"unit_proof.{group}"] = _status(unit.get(group, {"status": "missing"}))
    transcriptions = fixtures.get("transcriptions", {})
    for part in ("sha256", "header_ddG"):
        states[f"transcriptions.{part}"] = _status(transcriptions.get(part, {"status": "missing"}))
    confirmation = _status(fixtures.get("transcription_confirmation", {"status": "missing"}))
    states["transcription_confirmation"] = "pass" if confirmation == "confirmed" else confirmation
    return states


def outstanding(record: dict[str, Any]) -> dict[str, Any]:
    """Every gated state that is not ``pass`` (a pre-promotion record has only the pending ones)."""
    return {k: v for k, v in fixture_states(record["fixtures"]).items() if v != "pass"}


def _suite_failures(block: dict[str, Any]) -> list[str]:
    code, failed, errors = block.get("exit_code"), block.get("failed", 0), block.get("errors", 0)
    if code != 0 or failed or errors:
        return [f"default_suite: exit_code {code}, failed {failed}, errors {errors}"]
    return []


def record_verdict(
    fixtures: dict[str, Any],
    default_suite: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The verdict rule (R56, v0.4.0 R27): ``pass`` or ``fail`` with the reasons.

    ``fail`` on a missing or failing default suite (non-zero exit, failures or errors), a command
    with a non-zero exit or a skip, no commands, or any gated check that is not ``pass``
    (``fail``, ``pending_*``, ``skipped``, ``missing`` or an unknown state).
    """
    reasons: list[str] = []
    if default_suite is None:
        reasons.append("default_suite: missing")
    else:
        reasons += _suite_failures(default_suite)
    if not commands:
        reasons.append("commands: none recorded")
    reasons += command_problems(commands or [])
    for name, state in fixture_states(fixtures).items():
        if state != "pass":
            reasons.append(f"{name}: {state}")
    return {"verdict": "fail" if reasons else "pass", "verdict_reasons": reasons}


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
    stated = "verdict" in record or "verdict_reasons" in record
    if stated:
        problems += [f"missing {key}" for key in VERDICT_KEYS if key not in record]
        promotion = record.get("evidence", {}).get("promotion", {})
        if promotion.get("status") != "verified":
            problems.append("a verdict needs evidence.promotion verified")
    if record.get("record_schema") != 1:
        problems.append("record_schema is not 1")
    fixtures = record.get("fixtures", {})
    if set(fixtures) != FIXTURE_KEYS:
        problems.append(f"fixtures keys {sorted(fixtures)} != {sorted(FIXTURE_KEYS)}")
    t4 = fixtures.get("t4", {})
    if set(t4) != set(PAIRS) or any(set(t4[p]) != set(RECIPES) for p in t4):
        problems.append("fixtures.t4 must be every pair x recipe")
    flexible = fixtures.get("flexible_ensemble", {})
    if set(flexible) != set(FLEX) or any(set(flexible[r]) != set(RECIPES) for r in flexible):
        problems.append("fixtures.flexible_ensemble must be every R x recipe")
    for name, state in fixture_states(fixtures).items():
        if state not in STATES:
            problems.append(f"{name}: state {state!r} not in {sorted(STATES)}")
    for pair in t4:
        for recipe, entry in t4[pair].items():
            if entry.get("test_outcome") not in TEST_OUTCOMES:
                problems.append(f"t4.{pair}.{recipe}: test_outcome {entry.get('test_outcome')!r}")
    for r_group in flexible:
        for recipe, entry in flexible[r_group].items():
            if entry.get("test_outcome") not in TEST_OUTCOMES:
                problems.append(
                    f"flexible_ensemble.{r_group}.{recipe}: test_outcome "
                    f"{entry.get('test_outcome')!r}"
                )
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
    if stated:
        expected = record_verdict(fixtures, record.get("default_suite"), record.get("commands"))
        got = {k: record.get(k) for k in expected}
        if got != expected:
            problems.append(f"verdict {got} is not the record's verdict {expected}")
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


def _timeouts(ensemble: dict[str, Any]) -> int:
    return sum(1 for e in ensemble.get("excluded", []) if e.get("reason") == TIMEOUT_REASON)


def _heavy_rmsd(a: dict[str, Any] | None, b: dict[str, Any] | None) -> float | None:
    if a is None or b is None or a["symbols"] != b["symbols"]:
        return None
    return heavy_rmsd_angstrom(a, b)


def _judge(values: dict[str, float | None], bounds: dict[str, float]) -> list[str]:
    problems = []
    for key, value in values.items():
        if value is None:
            problems.append(f"{key}: missing")
        elif value > bounds[key]:
            problems.append(key)
    return problems


def compare_pair(
    fragment: dict[str, Any], fixture: dict[str, Any], recipe: str, name: str
) -> dict[str, Any]:
    """An in-process Tier 4 pair against its promoted fixture under TJ's bounds (R31).

    Per pathway: |ΔE_TS| of the seed TS, heavy-atom RMSD of the seed TS (Horn, same atom order) and
    the member count; for the pair, |ΔΔG‡| and (mapped) the pruning branch. A member count may
    differ only through a PreRelaxTimeout exclusion on either side (R28); that is reported and the
    remaining quantities are still judged. ``search_history`` is never compared (N11).
    """
    bounds = REGRESSION_BOUNDS[recipe]
    per_pathway: dict[str, Any] = {}
    problems: list[str] = []
    energies: list[float | None] = []
    rmsds: list[float | None] = []
    for pathway in sorted(set(fragment.get("pathways", {})) | set(fixture.get("pathways", {}))):
        new = fragment.get("pathways", {}).get(pathway, {})
        old = fixture.get("pathways", {}).get(pathway, {})
        ts_new, ts_old = new.get("seed_ts") or {}, old.get("seed_ts") or {}
        e_new = (ts_new.get("thermo") or {}).get("electronic_energy_hartree")
        e_old = (ts_old.get("thermo") or {}).get("electronic_energy_hartree")
        d_e = None if e_new is None or e_old is None else abs(float(e_new) - float(e_old))
        d_rmsd = _heavy_rmsd(ts_new.get("state"), ts_old.get("state"))
        counts = [
            len(new.get("ensemble", {}).get("members", [])),
            len(old.get("ensemble", {}).get("members", [])),
        ]
        timeouts = [_timeouts(new.get("ensemble", {})), _timeouts(old.get("ensemble", {}))]
        per_pathway[pathway] = {
            "abs_delta_ts_energy_hartree": d_e,
            "heavy_rmsd_angstrom": d_rmsd,
            "n_members": counts,
            "pre_relax_timeouts": timeouts,
            "member_count_differs": counts[0] != counts[1],
            "difference_explained_by_timeout": counts[0] != counts[1] and any(timeouts),
        }
        if counts[0] != counts[1] and not any(timeouts):
            problems.append(f"n_members.{pathway}")
        energies.append(d_e)
        rmsds.append(d_rmsd)
    ddg_new = (fragment.get("score") or {}).get("ddG_dagger_kcal_mol")
    ddg_old = (fixture.get("score") or {}).get("ddG_dagger_kcal_mol")
    values: dict[str, float | None] = {
        "abs_delta_ts_energy_hartree": None if None in energies or not energies else max(energies),  # type: ignore[type-var]
        "heavy_rmsd_angstrom": None if None in rmsds or not rmsds else max(rmsds),  # type: ignore[type-var]
        "abs_delta_ddG_dagger_kcal_mol": (
            None if ddg_new is None or ddg_old is None else abs(float(ddg_new) - float(ddg_old))
        ),
    }
    problems += _judge(values, bounds)
    result: dict[str, Any] = {
        "status": "fail" if problems else "pass",
        "fixture": f"tests/fixtures/v0.6.0/{name}",
        **values,
        "per_pathway": per_pathway,
        "bounds": dict(bounds),
        "mismatches": problems,
    }
    gate_new = fragment.get("checks", {}).get("tier_gates", {}).get("pruning_g6", {})
    gate_old = fixture.get("checks", {}).get("tier_gates", {}).get("pruning_g6", {})
    if gate_new or gate_old:
        result["pruning_branch"] = [gate_new.get("branch"), gate_old.get("branch")]
        if gate_new.get("branch") != gate_old.get("branch") or gate_new.get("branch") is None:
            result["mismatches"] = [*problems, "pruning_branch"]
            result["status"] = "fail"
    return result


def _match_by_energy(
    new: list[float], old: list[float]
) -> tuple[list[float], list[float], list[float]]:
    """Pair two lists of member free energies (Eh) in ascending order.

    Equal counts pair rank by rank. Otherwise each member of the shorter list takes the nearest
    unused member of the longer one (a count difference is only allowed through a PreRelaxTimeout,
    R28). Returns the absolute differences of the pairs and the unmatched energies of each side.
    """
    a, b = sorted(new), sorted(old)
    swap = len(a) > len(b)
    short, long_ = (b, a) if swap else (a, b)
    free = list(long_)
    deltas: list[float] = []
    for g in short:
        j = min(range(len(free)), key=lambda k: abs(free[k] - g))
        deltas.append(abs(free.pop(j) - g))
    return deltas, (free if swap else []), ([] if swap else free)


def compare_flexible(
    fragment: dict[str, Any], fixture: dict[str, Any], recipe: str, name: str
) -> dict[str, Any]:
    """An in-process flexible case against its promoted fixture: counts and per-member energies.

    Members are paired by free energy, in ascending order: the lowest-G copy of a merge group may
    be a different one of two equal-energy copies from run to run, so ``source`` labels are
    reported (``sources_*``) and never matched on. |ΔG| of each pair and of the pathway's free
    energy are bounded by the energy bound, the ensemble ΔG‡ by the ΔΔG‡ bound (R31). The count may
    differ only through a PreRelaxTimeout exclusion on either side (R28): that is reported and the
    paired members are still judged. The candidates hold no geometry, so no heavy-atom RMSD exists.
    """
    bounds = REGRESSION_BOUNDS[recipe]
    new, old = fragment.get("reported") or {}, fixture.get("reported") or {}
    g_new = [float(m["G_hartree"]) for m in new.get("members", [])]
    g_old = [float(m["G_hartree"]) for m in old.get("members", [])]
    timeouts = [
        (new.get("exclusions_by_reason") or {}).get(TIMEOUT_REASON, 0),
        (old.get("exclusions_by_reason") or {}).get(TIMEOUT_REASON, 0),
    ]
    counts = [len(g_new), len(g_old)]
    problems: list[str] = []
    if counts[0] != counts[1] and not any(timeouts):
        problems.append("n_members")
    d_member, only_new, only_old = _match_by_energy(g_new, g_old)
    p_new, p_old = new.get("G_pathway_hartree"), old.get("G_pathway_hartree")
    b_new = (new.get("barrier") or {}).get("ensemble_dG_dagger_1M_kcal_mol")
    b_old = (old.get("barrier") or {}).get("ensemble_dG_dagger_1M_kcal_mol")
    values: dict[str, float | None] = {
        "max_abs_delta_member_G_hartree": max(d_member) if d_member else None,
        "abs_delta_G_pathway_hartree": (
            None if p_new is None or p_old is None else abs(float(p_new) - float(p_old))
        ),
        "abs_delta_dG_dagger_1M_kcal_mol": (
            None if b_new is None or b_old is None else abs(float(b_new) - float(b_old))
        ),
    }
    keys = {
        "max_abs_delta_member_G_hartree": "abs_delta_ts_energy_hartree",
        "abs_delta_G_pathway_hartree": "abs_delta_ts_energy_hartree",
        "abs_delta_dG_dagger_1M_kcal_mol": "abs_delta_ddG_dagger_kcal_mol",
    }
    problems += _judge(values, {k: bounds[v] for k, v in keys.items()})
    return {
        "status": "fail" if problems else "pass",
        "fixture": f"tests/fixtures/v0.6.0/{name}",
        **values,
        "n_members": counts,
        "pre_relax_timeouts": timeouts,
        "member_count_differs": counts[0] != counts[1],
        "difference_explained_by_timeout": counts[0] != counts[1] and any(timeouts),
        "unmatched_member_G_hartree_in_run": only_new,
        "unmatched_member_G_hartree_in_fixture": only_old,
        "sources_in_run": sorted(m["source"] for m in new.get("members", [])),
        "sources_in_fixture": sorted(m["source"] for m in old.get("members", [])),
        "heavy_rmsd_angstrom": None,
        "heavy_rmsd_note": "the candidates hold no geometry, so no heavy-atom RMSD is compared",
        "bounds": {k: bounds[v] for k, v in keys.items()},
        "mismatches": problems,
    }


def load_promoted(promoted_dir: Path, name: str) -> dict[str, Any] | None:
    """A promoted fixture's JSON (a test fixture, readable), or ``None`` when absent."""
    path = promoted_dir / name
    return dict(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None


def promotion_evidence(promoted_dir: Path = PROMOTED_V060) -> dict[str, Any]:
    """TJ's promotion (R31): each promoted file's sha256 and blob id against R31's prefixes.

    ``absent`` when no promoted file exists (pre-promotion); ``verified`` when all ten equal R31;
    anything else raises, since a fixture that is not TJ's must never feed a verdict.
    """
    present = sorted(p.name for p in promoted_dir.glob("*.json")) if promoted_dir.is_dir() else []
    if not present:
        return {"status": "absent", "directory": "tests/fixtures/v0.6.0/"}
    files = {}
    for name, (sha, blob) in sorted(PROMOTED_FILES.items()):
        path = promoted_dir / name
        data = path.read_bytes() if path.is_file() else b""
        observed = (hashlib.sha256(data).hexdigest(), git_blob_id(data)) if data else ("", "")
        if not (observed[0].startswith(sha) and observed[1].startswith(blob)):
            raise ValueError(f"promoted {name} is not R31's: {observed} vs {(sha, blob)}")
        files[name] = {
            "sha256": observed[0],
            "blob_id": observed[1],
            "r31_sha256_prefix": sha,
            "r31_blob_prefix": blob,
        }
    if present != sorted(PROMOTED_FILES):
        raise ValueError(f"promoted files {present} are not R31's {sorted(PROMOTED_FILES)}")
    return {
        "status": "verified",
        **PROMOTION,
        "directory": "tests/fixtures/v0.6.0/",
        "files": files,
    }


def pair_entry(
    fragment: dict[str, Any],
    fixture: dict[str, Any] | None = None,
    recipe: str = "xtb",
    name: str = "",
) -> dict[str, Any]:
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
        "run_commit_sha": fragment.get("commit_sha"),
        "regression": (
            compare_pair(fragment, fixture, recipe, name)
            if fixture is not None
            else {
                "status": "pending_promotion",
                "note": "the v0.6.0 candidates are not yet TJ's fixtures (Phase 3)",
            }
        ),
    }
    if "pruning" in fragment:
        entry["pruning"] = fragment["pruning"]
    if "exo_graft" in fragment:
        graft = dict(fragment["exo_graft"])
        graft.pop("pre_relaxed_start", None)
        entry["exo_graft"] = graft
    return entry


def flexible_entry(
    fragment: dict[str, Any],
    fixture: dict[str, Any] | None = None,
    recipe: str = "xtb",
    name: str = "",
) -> dict[str, Any]:
    """The entry of one R x recipe from slice 14's E2E fragment (gated: its gates (a)-(f))."""
    if fragment.get("test_outcome") == "missing":
        return {"test_outcome": "missing"}
    reported = dict(fragment.get("reported") or {})
    return {
        "test_outcome": fragment.get("test_outcome"),
        "failed_checks": fragment.get("failed_checks", []),
        "tier_gates": dict(fragment.get("checks", {}).get("tier_gates", {})),
        "reported": reported,
        "graft": fragment.get("graft"),
        "inputs_sha256": fragment.get("inputs_sha256"),
        "run_commit_sha": fragment.get("commit_sha"),
        "regression": (
            compare_flexible(fragment, fixture, recipe, name)
            if fixture is not None
            else {
                "status": "pending_promotion",
                "note": "no promoted fixture exists for the flexible-ensemble cases (Phase 3)",
            }
        ),
    }


def flexible_block(
    runs: dict[str, dict[str, Any]], promoted_dir: Path | None = None
) -> dict[str, Any]:
    """The six ``flexible_ensemble`` entries plus, per recipe, the reported chain-length order.

    Members per R, the order flag and ΔΔG‡ versus ethyl are reported, never gated; the entries'
    gated states are slice 14's gates (a)-(f).
    """
    gone = {"test_outcome": "missing"}

    def entry(r: str, recipe: str) -> dict[str, Any]:
        name = f"t4_flexible_{r}.{recipe}.json"
        fixture = load_promoted(promoted_dir, name) if promoted_dir else None
        return flexible_entry(runs[recipe].get("flexible", {}).get(r, gone), fixture, recipe, name)

    block: dict[str, Any] = {r: {recipe: entry(r, recipe) for recipe in RECIPES} for r in FLEX}
    for recipe in RECIPES:
        counts = {}
        barrier = {}
        for r in FLEX:
            rep = block[r][recipe].get("reported", {})
            if rep.get("n_members") is not None:
                counts[r] = rep["n_members"]
            b = rep.get("barrier") or {}
            if b.get("ensemble_dG_dagger_1M_kcal_mol") is not None:
                barrier[r] = b["ensemble_dG_dagger_1M_kcal_mol"]
        ordered = [counts[r] for r in FLEX if r in counts]
        for r in FLEX:
            if block[r][recipe].get("test_outcome") == "missing":
                continue
            block[r][recipe]["reported"]["ddG_dagger_vs_ethyl_kcal_mol"] = (
                barrier[r] - barrier["ethyl"] if r in barrier and "ethyl" in barrier else None
            )
            block[r][recipe]["reported"]["chain_length_order"] = {
                "status": "reported",
                "members_by_r": counts,
                "complete": len(ordered) == len(FLEX),
                "non_decreasing": all(a <= b for a, b in zip(ordered, ordered[1:], strict=False)),
            }
    return block


def run_commits(t4: dict[str, Any], flexible: dict[str, Any]) -> dict[str, Any]:
    """The commit each acceptance fragment's test ran at (a fragment carries its own sha)."""
    out: dict[str, Any] = {}
    for pair, by_recipe in sorted(t4.items()):
        for recipe, entry in sorted(by_recipe.items()):
            out[f"t4.{pair}.{recipe}"] = entry.get("run_commit_sha")
    for r_group, by_recipe in sorted(flexible.items()):
        for recipe, entry in sorted(by_recipe.items()):
            out[f"flexible_ensemble.{r_group}.{recipe}"] = entry.get("run_commit_sha")
    return out


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
    prior: dict[str, Any] | None = None,
    promoted_dir: Path = PROMOTED_V060,
) -> dict[str, Any]:
    """Build the record from the two per-recipe files and the command logs.

    Without TJ's promoted fixtures: the pre-promotion record, no ``verdict`` (slice 11). With them
    (verified against R31): regression from the in-process comparisons, the transcriptions
    ``confirmed`` from TJ's recorded answer, TJ's bounds and the ``verdict`` (slice 12). ``prior``
    is the slice 11 record, whose reproducibility measurement is carried over.
    """
    shas = {r["commit_sha"] for r in runs.values()}
    if len(shas) != 1 or not all(r["tree_clean"] for r in runs.values()):
        raise ValueError(f"recipes ran at different or unclean commits: {shas}")
    promotion = promotion_evidence(promoted_dir)
    promoted = promotion["status"] == "verified"
    missing = {"test_outcome": "missing"}

    def pair(pair_name: str, recipe: str) -> dict[str, Any]:
        name = f"{pair_name}.{recipe}.json"
        fixture = load_promoted(promoted_dir, name) if promoted else None
        return pair_entry(runs[recipe]["pairs"].get(pair_name, missing), fixture, recipe, name)

    t4 = {pair_name: {r: pair(pair_name, r) for r in RECIPES} for pair_name in PAIRS}
    if prior is not None:
        reproducibility = prior["reproducibility"]
        proposed = prior["proposed_regression_bounds"]
    else:
        reproducibility = {
            recipe: {
                pair_name: reproducibility_entry(
                    pair_name,
                    recipe,
                    runs[recipe]["pairs"].get(pair_name, missing),
                    runs[recipe]["reproducibility"].get(pair_name, missing),
                )
                for pair_name in PAIRS
            }
            for recipe in RECIPES
        }
        proposed = proposed_bounds(reproducibility)
    flexible = flexible_block(runs, promoted_dir if promoted else None)
    fixtures = {
        "t4": t4,
        "flexible_ensemble": flexible,
        "unit_proof": unit_proof,
        **transcription_fixtures(xyz_dir, promoted),
    }
    evidence: dict[str, Any] = {
        "run_commits": run_commits(t4, flexible),
        "resume_note": RESUME_NOTE,
        "candidates_phase3_set": (
            "tests/candidate_outputs/v0.6.0/ (slices 09-10, 14), committed for TJ's Phase 3 "
            "review; never read by this record"
        ),
        "record_run_candidates": "written to a scratch ETA_RXNCAT_CANDIDATE_DIR, not committed",
        "candidate_values": (
            "the acceptance run reruns slice 09-10 and 14 code in process at this commit; its "
            "values stand for the candidates' (no candidate file is read, firewall)"
        ),
        "promotion": promotion,
    }
    if prior is not None:
        evidence["reproducibility_source"] = (
            f"slice 11 record at {prior['commit_sha']}: three fresh-store runs per pair x recipe; "
            "carried over, not rerun for the verdict"
        )
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
        "reported_notes": reported_notes(promoted),
        "evidence": evidence,
        "fixtures": fixtures,
        "reproducibility": reproducibility,
        "proposed_regression_bounds": proposed,
    }
    if promoted:
        record["regression_bounds"] = {
            "source": "mission R31 (TJ at Phase 3)",
            "recipes": {r: dict(b) for r, b in sorted(REGRESSION_BOUNDS.items())},
            "excluded": "search_history (N11)",
            "flexible_ensemble": (
                "member counts and per-member G against the fixture; no heavy-atom RMSD (the "
                "candidates hold no geometry); a PreRelaxTimeout may explain a count difference"
            ),
        }
        record.update(record_verdict(fixtures, default_suite, record["commands"]))
    problems = check(record)
    if problems:
        raise ValueError(f"record invalid: {problems}")
    return record


def transcription_fixtures(xyz_dir: Path, promoted: bool = False) -> dict[str, Any]:
    """The ``transcriptions`` block and TJ's confirmation (settled only by his recorded answer)."""
    if promoted:
        confirmation = {
            "status": "confirmed",
            "source": PROMOTION["source"],
            "answer": PROMOTION["transcriptions_confirmed"],
        }
    else:
        confirmation = {
            "status": "pending_confirmation",
            "note": "TJ confirms the three transcriptions at Phase 3",
        }
    return {
        "transcriptions": transcriptions_block(xyz_dir),
        "transcription_confirmation": confirmation,
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
    if len(argv) in (7, 8) and argv[0] == "merge":
        runs = {"xtb": _load(argv[1]), "uma": _load(argv[2])}
        prior = _load(argv[7]) if len(argv) == 8 else None
        record = merge_runs(runs, _load(argv[3]), _load(argv[4]), _load(argv[5]), prior=prior)
        _dump(Path(argv[6]), record)
        stated = record.get("verdict", "none (pre-promotion)")
        print(f"wrote {argv[6]}; verdict {stated}; reasons {record.get('verdict_reasons')}")
        print(f"outstanding {outstanding(record)}")
        print(f"command problems: {command_problems(record['commands'])}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
