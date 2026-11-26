"""v0.7.0 fallback E2E (slice 12, mission G8, HF-2): the TS seed fallback on real engines.

One command per unit (``test_v070_fallback[<construct>-<engine>]``): both constructs of
``v070_fallback.yaml`` on GFN2 (gated) and the ``run_time`` construct on UMA (reported). Each unit
has its own fresh store under ``ETA_RXNCAT_V070_STATE``, so its first pass does real engine work,
then a second pass that must be all hits with an equal record. Gated: the graft records, the
``FallbackRecord``, no TS-search call for rank 1, every engine call attributed, G7's ensemble gates
and the second pass. Candidates and run records go to ``tests/candidate_outputs/v0.7.0/``.

``graft_time``: the refused rank-1 template is refused by the enumerator, before any engine call;
mission G5 renumbers the eligible templates 1..k, so the runner's record holds the declared rank-2
template alone at rank 1 and the ``alignment_rmsd`` reason is on the candidate's graft record.
"""

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
    FALLBACK_YAML,
    candidate_dir,
    export_report,
    fallback_gates,
    fallback_name,
    reported_unit,
    run_fallback_unit,
    state_dir,
    unit_record,
    write_record,
)

from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

INPUT_XYZ = (
    "xyz/1_cyclopentadiene.xyz",
    "xyz/5_cyclopropene.xyz",
    "xyz/TS1a_n.xyz",
    "xyz/TS1a_x.xyz",
    "xyz/r_ethyl_cyclopropene.xyz",
)
UNITS = (("graft_time", "xtb"), ("run_time", "xtb"), ("run_time", "uma"))
REPORTED_ONLY = ("uma",)
"""UMA is reported once, never gated (mission G8)."""


def unit_params() -> list[Any]:
    """The three units, each under its engine marker (run one per command)."""
    marks = {p.values[0]: p.marks for p in RECIPE_PARAMS}
    return [
        pytest.param(construct, recipe, marks=marks[recipe], id=f"{construct}-{recipe}")
        for construct, recipe in UNITS
    ]


def _inputs_sha256() -> dict[str, str]:
    return {
        FALLBACK_YAML.name: sha256_file(FALLBACK_YAML),
        **{name: sha256_file(E2E5 / name) for name in INPUT_XYZ},
    }


def _environment(recipe_name: str) -> dict[str, Any]:
    env = run_environment(recipe_name)
    if "ETA_RXNCAT_XTB" in env:
        env["ETA_RXNCAT_XTB"] = env["ETA_RXNCAT_XTB"].replace(str(Path.home()), "~")
    env["TMPDIR_is_not_tmp"] = os.environ.get("TMPDIR", "/tmp") != "/tmp"
    env["cpu_count"] = os.cpu_count()
    return env


@pytest.mark.parametrize(("construct", "recipe_name"), unit_params())
def test_v070_fallback(
    construct: str,
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    commit_sha: str,
) -> None:
    """One unit, twice in its own store; candidate and run record are written before the gates."""
    state = state_dir()
    if state is None:
        pytest.skip("ETA_RXNCAT_V070_STATE is not set (the durable store and record directory)")
    if acceptance():
        assert os.environ.get("TMPDIR", "/tmp") != "/tmp"
    recipe = recipes(recipe_name)
    name = fallback_name(construct, recipe_name)
    store_path = state / f"{name}.sqlite"
    assert not store_path.exists(), f"{store_path} exists: the first pass must start fresh"
    fallback = run_fallback_unit(construct, recipe, recipe_name, store_path)
    unit = fallback.unit
    gates = fallback_gates(fallback)
    record = unit_record(unit, recipe, gates, gate_prefix="G8")
    write_record(name, record, state)
    exported = export_report(record, store_path)
    reported = reported_unit(unit)
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload: dict[str, Any] = {
        "fixture": "e2e5_v070_fallback",
        "case": name,
        "recipe": recipe_name,
        "construct": construct,
        "gated": recipe_name not in REPORTED_ONLY,
        "commit_sha": commit_sha,
        "environment": {
            **environment(identity, DEVICES[recipe_name]),
            "run": _environment(recipe_name),
        },
        "inputs_sha256": _inputs_sha256(),
        "candidate": unit.candidate.model_dump(mode="json", exclude={"graph"}),
        "templates_in_graph": [list(t) for t in fallback.templates],
        "fallback": unit.first.record.model_dump(mode="json"),
        "second_pass_fallback": unit.second.record.model_dump(mode="json"),
        "first_pass_engine_calls_by_template_stage": fallback.calls_table(),
        "reported": reported,
        "export": exported,
        "regression": {
            "status": "pending_promotion",
            "note": "no promoted fixture exists for this case (slice 12; Phase 3)",
        },
        "checks": {"tier_gates" if recipe_name not in REPORTED_ONLY else "reported_gates": gates},
    }
    payload.update(outcome_fields(payload["checks"]))
    write(candidate_dir() / f"{name}.json", payload)
    print(
        f"\n{name}: gates { {k: v['status'] for k, v in gates.items()} }; "
        f"record {[list(a.model_dump().values())[:4] for a in unit.first.record.attempts]}; "
        f"calls {fallback.calls_table()}; members {reported.get('n_members')}; "
        f"exclusions {reported.get('exclusions_by_reason')}; stalls {reported['stall_count']}; "
        f"passes {unit.first.wall_time_s:.0f}/{unit.second.wall_time_s:.1f} s; engine calls "
        f"{unit.first.engine_calls}/{unit.second.engine_calls}; rows "
        f"{unit.first.new_rows}/{unit.second.new_rows}; derivation "
        f"{unit.derivation_engine_calls}/{unit.derivation_new_rows}; resources {unit.resources}; "
        f"export {exported}"
    )
    if recipe_name not in REPORTED_ONLY:
        assert_checks_pass(payload["checks"])
