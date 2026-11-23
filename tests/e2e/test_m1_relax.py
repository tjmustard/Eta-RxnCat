"""Fixture M1, E2E: core-frozen pre-relaxation of the M1 graft on xtb and UMA (v0.4.0 slice 06).

Gates per recipe (TJ "P1 A", "R2 A"; mission R1, R16, R26):
- g1: the core stays within ``CORE_FREEZE_TOLERANCE_ANGSTROM`` (no ``CoreDisplacementError``);
- g2: the perceived connectivity of the relaxed graft, mapped by the stated-rule map, equals
  TS1b_n's perceived connectivity (edge sets);
- g3: every junction's sign on the relaxed coordinates is nonzero and equals TS1b_n's.
RMSDs are reported, never gated. The result is a pre-relaxed TS guess, not a minimum. Candidates go
to ``tests/candidate_outputs/v0.4.0/`` (or ``ETA_RXNCAT_CANDIDATE_DIR``) and are never read back.
"""

import math
import platform
import time
from collections.abc import Callable
from importlib import metadata
from typing import Any

import pytest
from acceptance import write_fragment
from candidates import environment
from checks import assert_checks_pass, gated_outcome, outcome_fields, write
from e2e_env import DEVICES, RECIPE_PARAMS
from m1 import (
    FORMING_CORE_BOUND_ANGSTROM,
    M1,
    PROMOTED_V040,
    AtomMap,
    appended_heavy_rmsd_angstrom,
    candidate_dir,
    derive_map,
    heavy_map_rmsds,
    load_m1,
    map_confirmation,
    mapped_bonds,
    product_payload,
    reference_junction_signs,
    regression_graft,
    regression_relaxed,
    rmsds_to_reference,
    spec_payload,
)

from eta_rxncat.core import GraftResult
from eta_rxncat.mapping import (
    CoreDisplacementError,
    graft,
    junction_volumes,
    perceive_bonds,
    relax_constrained_core,
)
from eta_rxncat.mapping.relax import CORE_FREEZE_TOLERANCE_ANGSTROM
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import Recipe, build_engine

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

RELAX_OPTIONS = {"maxiter": 200}
"""Mission R6: an explicit iteration cap; no dihedral constraint is ever passed."""


def _status(ok: bool) -> str:
    return "pass" if ok else "fail"


def identity_fields(m1: M1, commit_sha: str) -> dict[str, Any]:
    """Fields every M1 candidate carries."""
    return {
        "fixture": "m1_ts1a_n_to_ts1b_n",
        "commit_sha": commit_sha,
        "run_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_sha256": dict(sorted(m1.input_sha256.items())),
        "spec": spec_payload(m1),
        "graft_to_ts1b_n_map": list(m1.config["graft_to_ts1b_n_map"]),
        "map_rule": m1.config["map_rule"],
        "r50": {
            "failure_count": 0,
            "note": "no store or runner payload is read; relax raises on any engine or optimizer "
            "failure, so there is no failed_reason to check",
        },
    }


def graft_candidate(
    m1: M1, result: GraftResult, atom_map: AtomMap, commit_sha: str
) -> dict[str, Any]:
    """``m1_graft.json``: the pure graft, the map and the tier-D checks (written by the xtb run)."""
    mapping = atom_map.graft_to_ts1b_n_map
    rmsds = rmsds_to_reference(result.product.coordinates, m1.reference, result, mapping)
    ref_junctions = reference_junction_signs(
        result, m1.reference, mapping, m1.spec.junction_volume_tolerance_angstrom3
    )
    contacts = {(c.i, c.j) for c in result.close_contacts}
    gates = {
        "d2_map_equals_yaml": {"status": _status(mapping == m1.config["graft_to_ts1b_n_map"])},
        "d3_forming_core_rmsd": {
            "status": _status(rmsds["forming_core_rmsd_angstrom"] <= FORMING_CORE_BOUND_ANGSTROM),
            "value_angstrom": rmsds["forming_core_rmsd_angstrom"],
            "bound_angstrom": FORMING_CORE_BOUND_ANGSTROM,
        },
        "d4_close_contacts": {
            "status": _status(contacts == {(0, 15), (0, 17), (4, 16), (4, 20)}),
        },
        "d5_planar_flag": {"status": _status(result.planar_pair_set_bool)},
        "d6_reference_junctions_nonzero": {
            "status": _status(all(r["sign"] in (-1, 1) for r in ref_junctions)),
        },
    }
    outcome = outcome_fields({"tier_gates": gates})
    return {
        **identity_fields(m1, commit_sha),
        "environment": {
            "versions": {
                "python": platform.python_version(),
                **{d: metadata.version(d) for d in ("rdkit", "numpy")},
            }
        },
        "product": product_payload(result.product),
        "index_map": [list(entry) for entry in result.index_map],
        "alignment_rmsd_angstrom": result.alignment_rmsd_angstrom,
        "close_contacts": [c.model_dump() for c in result.close_contacts],
        "junctions": [j.model_dump() for j in result.junctions],
        "reference_junctions": ref_junctions,
        "template_pair_planarity_rms_angstrom": result.template_pair_planarity_rms_angstrom,
        "fragment_pair_planarity_rms_angstrom": result.fragment_pair_planarity_rms_angstrom,
        "planar_pair_set_bool": result.planar_pair_set_bool,
        "min_interatomic_distance_angstrom": result.min_interatomic_distance_angstrom,
        "source_bonds": [list(b) for b in result.source_bonds],
        "constrained_core_product_indices": result.constrained_core_product_indices,
        "active_product_indices": result.active_product_indices,
        "n_isomorphisms": atom_map.n_isomorphisms,
        "heavy_map_forming_core_rmsd_angstrom": heavy_map_rmsds(result, m1.reference, atom_map),
        **rmsds,
        "tier_gates": gates,
        **outcome,
    }


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_m1_relax(recipe_name: str, recipes: Callable[[str], Recipe], commit_sha: str) -> None:
    """Pre-relax the M1 graft with its core frozen; gate g1-g3; write the candidate(s)."""
    recipe = recipes(recipe_name)
    m1 = load_m1()
    result = graft(m1.template, m1.fragment, m1.spec)
    atom_map = derive_map(result, m1.reference)
    mapping = atom_map.graft_to_ts1b_n_map
    out = candidate_dir()
    if recipe_name == "xtb":
        graft_payload = graft_candidate(m1, result, atom_map, commit_sha)
        write(out / "m1_graft.json", graft_payload)
        graft_checks = {
            **graft_payload["tier_gates"],
            "regression_graft": regression_graft(graft_payload),
            "map_confirmation": {"status": map_confirmation(m1.config["graft_to_ts1b_n_map"])},
        }
        write_fragment(
            "m1",
            "graft",
            {
                "forming_core_rmsd": graft_payload["tier_gates"]["d3_forming_core_rmsd"],
                "tier_d": graft_payload["tier_gates"],
                "regression_graft": graft_checks["regression_graft"],
                "map_confirmation": graft_checks["map_confirmation"]["status"],
                "reported": {
                    key: graft_payload[key]
                    for key in (
                        "alignment_rmsd_angstrom",
                        "active_rmsd_angstrom",
                        "full_rmsd_angstrom",
                        "planar_pair_set_bool",
                        "n_isomorphisms",
                    )
                }
                | {
                    "close_contacts": graft_payload["close_contacts"],
                    "junctions": graft_payload["junctions"],
                },
                **outcome_fields({"tier_gates": graft_checks}),
            },
        )
        assert_checks_pass({"tier_gates": graft_checks})

    engine = build_engine(recipe.engine_stage, recipe.engine_runtime)
    core = result.constrained_core_product_indices
    tolerance = m1.spec.junction_volume_tolerance_angstrom3
    start = time.monotonic()
    relaxed = None
    try:
        relaxed = relax_constrained_core(
            result.product, engine, GeometricOptimizer(), core, options=RELAX_OPTIONS
        )
        displacement = max(
            math.dist(relaxed.final_state.coordinates[k], result.product.coordinates[k])
            for k in core
        )
    except CoreDisplacementError as err:
        displacement = err.displacement_angstrom
    wall_time_s = time.monotonic() - start

    gates: dict[str, Any] = {
        "g1_core_frozen": {
            "status": _status(relaxed is not None),
            "core_max_displacement_angstrom": displacement,
            "bound_angstrom": CORE_FREEZE_TOLERANCE_ANGSTROM,
        }
    }
    payload: dict[str, Any] = {
        **identity_fields(m1, commit_sha),
        "recipe": recipe_name,
        "environment": environment(engine.identity, DEVICES[recipe_name]),
        "core_max_displacement_angstrom": displacement,
        "metrics": {"wall_time_s": wall_time_s},
    }
    if relaxed is not None:
        coords = relaxed.final_state.coordinates
        relaxed_bonds = mapped_bonds(perceive_bonds(relaxed.final_state), mapping)
        reference_bonds = set(perceive_bonds(m1.reference))
        gates["g2_connectivity_equals_ts1b_n"] = {
            "status": _status(relaxed_bonds == reference_bonds),
            "missing_bonds_ts1b_n_indices": sorted(reference_bonds - relaxed_bonds),
            "extra_bonds_ts1b_n_indices": sorted(relaxed_bonds - reference_bonds),
        }
        relaxed_junctions = junction_volumes(
            coords, result.source_bonds, len(m1.spec.template.keep), tolerance
        )
        reference_junctions = reference_junction_signs(result, m1.reference, mapping, tolerance)
        signs = [j.sign for j in relaxed_junctions]
        reference_signs = [r["sign"] for r in reference_junctions]
        gates["g3_junction_signs_equal_ts1b_n"] = {
            "status": _status(all(s in (-1, 1) for s in signs) and signs == reference_signs),
            "relaxed": [j.model_dump() for j in relaxed_junctions],
            "ts1b_n": reference_junctions,
        }
        payload |= {
            "relaxed_product": product_payload(relaxed.final_state),
            "final_energy_hartree": relaxed.final_energy_hartree,
            "optimizer": relaxed.optimizer.model_dump(),
            "optimizer_options": dict(sorted(relaxed.options.items())),
            "reported": {
                **rmsds_to_reference(coords, m1.reference, result, mapping),
                "appended_heavy_rmsd_angstrom": appended_heavy_rmsd_angstrom(
                    coords, m1.reference, result, mapping
                ),
            },
            "metrics": {
                "wall_time_s": wall_time_s,
                "n_steps": relaxed.n_steps,
                "n_engine_calls": relaxed.n_engine_calls,
                "recovery_steps": list(relaxed.recovery_steps),
            },
        }
    payload["tier_gates"] = gates
    if relaxed is not None:
        regression = regression_relaxed(payload, recipe_name)
    elif (PROMOTED_V040 / f"m1_relaxed.{recipe_name}.json").is_file():
        regression = {"status": "fail", "mismatches": ["no relaxed structure (g1 failed)"]}
    else:
        regression = {"status": "pending_promotion"}
    checks = {"tier_gates": {**gates, "regression_relaxed": {"status": regression["status"]}}}
    payload["regression_relaxed"] = regression
    payload |= outcome_fields(checks)
    write(out / f"m1_relaxed.{recipe_name}.json", payload)
    write_fragment(
        "m1",
        recipe_name,
        {
            "relaxed_gates": {
                "status": _status(all(g["status"] == "pass" for g in gates.values())),
                **gates,
            },
            "regression_relaxed": regression,
            "reported": payload.get("reported", {}),
            "metrics": {**payload["metrics"], "device": DEVICES[recipe_name]},
            "core_max_displacement_angstrom": displacement,
            **outcome_fields(checks),
        },
    )
    print(
        f"M1 {recipe_name}: outcome {gated_outcome(checks)}; "
        f"core max displacement {displacement:.3e} A; wall {wall_time_s:.1f} s; "
        f"gates { {k: v['status'] for k, v in gates.items()} }; "
        f"reported {payload.get('reported')}; metrics {payload['metrics']}"
    )
    assert_checks_pass(checks)
