"""A stub run for the review tests: real stage keys, hand-written rows in the runners' shapes.

The molecule is H2 on the x axis. Its stored Hessian has one negative force constant along the
bond, so the exported normal mode has a known answer.
"""

from pathlib import Path
from typing import Any

from eta_rxncat.core import (
    EngineIdentity,
    MolecularState,
    StageConfig,
)
from eta_rxncat.review import RunRecord
from eta_rxncat.store import (
    ArtifactStatus,
    ArtifactStore,
    build_stage_key,
    geometry_payload,
)

ENGINE = EngineIdentity(name="rdkit_ff", version="2026.1.1", model=None)
SECRET = "/home/someone/secret/eta"
"""A path that stands in a row's ``message``; it must never be exported."""

HOSTILE = "</script><img src=x onerror=alert(1)><!--  &"
"""A label that would break out of an HTML script element if written as it is."""

H2 = MolecularState(
    symbols=["H", "H"],
    coordinates=[[0.0, 0.0, 0.0], [1.2000012345, 0.0, 0.0]],
    charge=0,
    spin_multiplicity=1,
    active_atom_indices=[0, 1],
)


def stretch_hessian(constant: float = -0.3) -> list[list[float]]:
    """Return the Hessian of a spring of ``constant`` (Eh/Bohr^2) along x."""
    hessian = [[0.0] * 6 for _ in range(6)]
    hessian[0][0] = hessian[3][3] = constant
    hessian[0][3] = hessian[3][0] = -constant
    return hessian


def key_of(state: MolecularState, kind: str, tag: str = "") -> Any:
    """Return the stage key of ``state`` under ``kind``; ``tag`` makes distinct rows."""
    stage = StageConfig(
        kind=kind,
        engine="rdkit_ff",
        method="uff",
        frozen_atom_indices=[0] if kind == "constrained_preopt" else [],
        options={"tag": tag} if tag else {},
    )
    return build_stage_key(state, stage, ENGINE)


def frames(n: int) -> list[dict[str, Any]]:
    """Return ``n`` stored optimizer frames, the energy falling with the index."""
    return [
        {
            "coordinates_angstrom": [[0.0, 0.0, 0.0], [1.2 + 0.001 * k, 0.0, 0.0]],
            "energy_hartree": -1.0 - 0.001 * k,
            "max_gradient_hartree_per_bohr": 0.1 / (k + 1),
            "ladder_step": "primary",
            "accepted_bool": k % 2 == 0,
        }
        for k in range(n)
    ]


def opt_row(n: int) -> dict[str, Any]:
    """Return a converged optimization row with ``n`` frames."""
    return {
        "final_xyz": [list(r) for r in H2.coordinates],
        "final_energy_hartree": -1.1,
        "n_steps": n,
        "n_engine_calls": n + 1,
        "recovery_steps": [],
        "optimizer": {"name": "geometric", "version": "1.1.1"},
        "options": {"maxiter": 200},
        "wall_time_s": 1.0,
        "frames": frames(n),
    }


def put(path: Path, rows: dict[str, tuple[str, dict[str, Any]]], n_frames: int = 12) -> None:
    """Write the stub rows (see ``stub_keys``) into the store at ``path``."""
    keys = stub_keys()
    defaults: dict[str, dict[str, Any]] = {
        "pre": opt_row(n_frames),
        "ts": {
            "failed_reason": "ts_search_failed:max_steps",
            "message": f"failed in {SECRET}",
            "frames": frames(n_frames),
        },
        "freq": {
            "energy_hartree": -1.1,
            "hessian_hartree_per_bohr2": stretch_hessian(),
            "hessian_method": "analytic",
            "geometry": geometry_payload(H2),
        },
        "end": opt_row(3),
    }
    with ArtifactStore(path) as store:
        for name, payload in defaults.items():
            payload = rows.get(name, (name, payload))[1]
            store.put(keys[name], ArtifactStatus.COMPLETED, payload)


def stub_keys() -> dict[str, Any]:
    """Return the stage keys of the stub rows; ``gone`` is never written."""
    return {
        "pre": key_of(H2, "constrained_preopt"),
        "ts": key_of(H2, "ts_opt"),
        "freq": key_of(H2, "frequency"),
        "end": key_of(H2, "geometry_opt"),
        "gone": key_of(H2, "frequency", "gone"),
    }


def stub_record(label: str = "endo TS", entry_id: str = "ethyl") -> RunRecord:
    """Return a one-unit record over the stub rows, with a gate and a selectivity result."""
    keys = {name: key.key for name, key in stub_keys().items()}
    engine = ENGINE.model_dump()
    candidate_id = f"r={entry_id}"
    unit = {"candidate_id": candidate_id, "pathway": "endo", "engine": engine}
    return RunRecord.model_validate(
        {
            "species": [
                {"species_id": "ts", "label": label, "state": H2.model_dump()},
                {"species_id": "reactant", "label": "reactant", "state": H2.model_dump()},
            ],
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "entry_ids_by_site": {"r": entry_id},
                    "records": [
                        {
                            "entry_id": entry_id,
                            "site_id": "r",
                            "node_id": "ts_node",
                            "template_id": "t1",
                            "status": "refused",
                            "reason": "alignment_rmsd",
                        },
                        {
                            "entry_id": entry_id,
                            "site_id": "r",
                            "node_id": "ts_node",
                            "template_id": "t2",
                            "status": "ok",
                            "alignment_rmsd_angstrom": 0.05,
                        },
                    ],
                }
            ],
            "runs": [
                {
                    **unit,
                    "optimizers": [{"name": "geometric", "version": "1.1.1"}],
                    "species_id": "ts",
                    "analysis": {},
                    "fallback": {
                        "node_id": "ts_node",
                        "chosen_template_id": f"t2__{candidate_id}",
                        "attempts": [
                            {
                                "template_id": f"t2__{candidate_id}",
                                "rank": 2,
                                "outcome": "chosen",
                                "wall_time_s": 3.0,
                            }
                        ],
                    },
                    "ensemble": {
                        "pathway": "endo",
                        "temperature_k": 298.15,
                        "reactant_key": [["[HH]", 1]],
                        "recipe_identity": engine,
                        "members": [
                            {
                                "index": 0,
                                "source": "seed",
                                "start_sha256": "0" * 64,
                                "G_hartree": -1.05,
                                "degeneracy": 1,
                                "rmsd_to_seed_angstrom": 0.0,
                                "face": [1],
                                "validation_passed_bool": True,
                                "weight": 1.0,
                            }
                        ],
                        "G_pathway_hartree": -1.05,
                    },
                    "dG_dagger_kcal_mol": 12.5,
                    "samples": [
                        {
                            "template_id": f"t2__{candidate_id}",
                            "sample_index": 0,
                            "source": "seed",
                            "species_id": "ts",
                            "pre_relax_key": keys["pre"],
                            "ts_opt_key": keys["ts"],
                            "frequency_key": keys["freq"],
                        },
                        {
                            "template_id": f"t2__{candidate_id}",
                            "sample_index": 1,
                            "source": "perturb:0",
                            "species_id": "ts",
                            "frequency_key": keys["gone"],
                        },
                    ],
                    "endpoints": [{"species_id": "reactant", "opt_keys": [keys["end"]]}],
                }
            ],
            "selectivity": [
                {
                    "candidate_id": candidate_id,
                    "engine": engine,
                    "result": {
                        "ddG_dagger_kcal_mol": 1.5,
                        "signed_ddG_dagger_kcal_mol": {"exo_vs_endo": 1.5},
                        "ratio": 12.6,
                        "selectivity_percent": 85.0,
                        "kind": "de",
                        "major_pathway": "endo",
                        "temperature_k": 298.15,
                        "per_pathway": {
                            name: {
                                "G_pathway_hartree": -1.05,
                                "n_members": 1,
                                "n_excluded": 0,
                                "fraction": 0.5,
                            }
                            for name in ("endo", "exo")
                        },
                    },
                }
            ],
            "gates": [
                {
                    "gate_id": "graft_rmsd",
                    "unit_ref": unit,
                    "pass_bool": True,
                    "value": 0.05,
                    "unit": "angstrom",
                    "threshold": 0.15,
                }
            ],
        }
    )
