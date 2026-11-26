"""v0.7.0 enumeration E2E (slice 11, mission G7): enumerated candidates through the fallback runner.

One command per (R x pathway x engine) unit (``test_v070_unit[<R>-<pathway>-<engine>]``), then one
per (R, engine) score (``test_v070_score[<R>-<engine>]``) after both its units. Gated per unit: the
candidate ``ok``, charge 0 and multiplicity 1, graft RMSD <= 0.15 A with no contact, the G3
invariant, rank 1 chosen, unit weights, every member on the pathway's face, no ``engine_error`` or
``face_mismatch`` and a second pass of all hits. dG-dagger, ddG-dagger (never gated, Q-A3),
members, stalls, time lost, walls, CPU and peak RSS are reported. Candidates and run records go to
``tests/candidate_outputs/v0.7.0/`` for TJ's Phase 3; the shared store and the records read by the
score go to ``ETA_RXNCAT_V070_STATE``.
"""

import math
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from candidates import environment
from checks import assert_checks_pass, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS, acceptance
from t4_flexible import run_environment, sha256_file
from v070 import (
    E2E5,
    ENUMERATION_YAML,
    PATHWAYS,
    R_GROUPS,
    candidate_dir,
    export_report,
    read_unit_record,
    reported_unit,
    run_unit,
    score_name,
    score_pair,
    state_dir,
    unit_gates,
    unit_name,
    unit_record,
    write_record,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

STORE_NAME = "v070_enum.sqlite"
INPUT_XYZ = (
    "xyz/1_cyclopentadiene.xyz",
    "xyz/5_cyclopropene.xyz",
    "xyz/TS1a_n.xyz",
    "xyz/TS1a_x.xyz",
)


def unit_params() -> list[Any]:
    """Every recipe x R x pathway, each under its engine marker (run one per command)."""
    return [
        pytest.param(
            r_group,
            pathway,
            param.values[0],
            marks=param.marks,
            id=f"{r_group}-{pathway}-{param.values[0]}",
        )
        for param in RECIPE_PARAMS
        for r_group in R_GROUPS
        for pathway in PATHWAYS
    ]


def _state() -> Path:
    state = state_dir()
    if state is None:
        pytest.skip("ETA_RXNCAT_V070_STATE is not set (the durable store and record directory)")
    return state


def _inputs_sha256(r_group: str) -> dict[str, str]:
    files = (*INPUT_XYZ, f"xyz/r_{r_group}_cyclopropene.xyz")
    return {
        ENUMERATION_YAML.name: sha256_file(ENUMERATION_YAML),
        **{name: sha256_file(E2E5 / name) for name in files},
    }


def _environment(recipe_name: str) -> dict[str, Any]:
    env = run_environment(recipe_name)
    if "ETA_RXNCAT_XTB" in env:
        env["ETA_RXNCAT_XTB"] = env["ETA_RXNCAT_XTB"].replace(str(Path.home()), "~")
    env["TMPDIR_is_not_tmp"] = os.environ.get("TMPDIR", "/tmp") != "/tmp"
    env["cpu_count"] = os.cpu_count()
    return env


@pytest.mark.parametrize(("r_group", "pathway", "recipe_name"), unit_params())
def test_v070_unit(
    r_group: str,
    pathway: str,
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    commit_sha: str,
) -> None:
    """One unit, twice in one store; the candidate and run record are written before the gates."""
    state = _state()
    if acceptance():
        assert os.environ.get("TMPDIR", "/tmp") != "/tmp"
    recipe = recipes(recipe_name)
    store_path = state / STORE_NAME
    name = unit_name(r_group, pathway, recipe_name)
    unit = run_unit(r_group, pathway, recipe, recipe_name, store_path)
    gates = unit_gates(unit)
    record = unit_record(unit, recipe, gates)
    write_record(name, record, state)
    exported = export_report(record, store_path)
    reported = reported_unit(unit)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
        "fixture": "e2e5_v070_enumeration",
        "case": name,
        "recipe": recipe_name,
        "r_group": r_group,
        "pathway": pathway,
        "commit_sha": commit_sha,
        "environment": {
            **environment(identity, DEVICES[recipe_name]),
            "run": _environment(recipe_name),
        },
        "inputs_sha256": _inputs_sha256(r_group),
        "candidate": unit.candidate.model_dump(mode="json", exclude={"graph"}),
        "fallback": unit.first.record.model_dump(mode="json"),
        "reported": reported,
        "export": exported,
        "regression": {
            "status": "pending_promotion",
            "note": "no promoted fixture exists for this case (slice 11; Phase 3)",
        },
        "checks": {"tier_gates": gates},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / f"{name}.json", payload)
    print(
        f"\n{name}: gates { {k: v['status'] for k, v in gates.items()} }; "
        f"members {reported.get('n_members')}; exclusions {reported.get('exclusions_by_reason')}; "
        f"stalls {reported['stall_count']} lost {reported['time_lost_to_stalls_s']:.1f} s "
        f"cap {reported['stall_cap_reached_bool']}; barrier {unit.barrier} "
        f"({unit.barrier_error}); passes {unit.first.wall_time_s:.0f}/"
        f"{unit.second.wall_time_s:.1f} s; engine calls {unit.first.engine_calls}/"
        f"{unit.second.engine_calls}; rows {unit.first.new_rows}/{unit.second.new_rows}; "
        f"resources {unit.resources}; export {exported}"
    )
    assert_checks_pass(payload["checks"])


@pytest.mark.parametrize(
    ("r_group", "recipe_name"),
    [
        pytest.param(r, param.values[0], id=f"{r}-{param.values[0]}")
        for param in RECIPE_PARAMS
        for r in R_GROUPS
    ],
)
def test_v070_score(r_group: str, recipe_name: str, commit_sha: str) -> None:
    """Score endo against exo for one (R, engine) from the two units' records (no engine)."""
    state = _state()
    records = {p: read_unit_record(state, unit_name(r_group, p, recipe_name)) for p in PATHWAYS}
    result, ensembles, merged = score_pair(records)
    assert math.isfinite(result.ratio), f"STOP AND REPORT: ratio is {result.ratio}"
    name = score_name(r_group, recipe_name)
    write_record(name, merged, state)
    exported = export_report(merged, state / STORE_NAME)
    gates = {
        "both_pathways_scored": {
            "status": "pass" if sorted(result.per_pathway) == sorted(PATHWAYS) else "fail"
        },
        "unit_gates_pass": {"status": "pass" if all(g.pass_bool for g in merged.gates) else "fail"},
        "ratio_finite": {"status": "pass"},
    }
    payload: dict[str, Any] = {
        "fixture": "e2e5_v070_enumeration",
        "case": name,
        "recipe": recipe_name,
        "r_group": r_group,
        "commit_sha": commit_sha,
        "inputs_sha256": _inputs_sha256(r_group),
        "reported": {
            "ddG_dagger_kcal_mol": result.ddG_dagger_kcal_mol,
            "major_pathway": result.major_pathway,
            "selectivity": result.model_dump(mode="json"),
            "dG_dagger_kcal_mol": {r.pathway: r.dG_dagger_kcal_mol for r in merged.runs},
            "n_members": {p: len(e.members) for p, e in ensembles.items()},
        },
        "export": exported,
        "checks": {"tier_gates": gates},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / f"{name}.json", payload)
    print(
        f"\n{name}: ddG {result.ddG_dagger_kcal_mol:.4f} kcal/mol, major "
        f"{result.major_pathway}, ratio {result.ratio:.4g}; gates "
        f"{ {k: v['status'] for k, v in gates.items()} }; export {exported}"
    )
    assert_checks_pass(payload["checks"])
