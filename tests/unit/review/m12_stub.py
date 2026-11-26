"""The stub run-data of the M12 browser smoke, with answers known by construction.

``python tests/unit/review/m12_stub.py`` rewrites ``data/m12_stub_run_data.json``;
``test_m12_stub.py`` checks that the committed file is what this module builds.

The first candidate also carries the disposition rows of slice 16: an excluded transition-state
sample whose identity fails (one imaginary mode, so only the identity raises its banner), a merged
sample, a ``seed_clash`` sample without frequencies, and a minimum superseded by a push.

Known answers: the transition state of candidate ``r=ethyl`` has one imaginary mode, a pure
stretch of the C0-C1 bond (only atoms 0 and 1 move, in opposite directions); its search has three
frames with C1 at x = 1.4, 1.9 and 2.4 Å; the second candidate's transition state has two
imaginary modes; and a species label, an entry id and the store file name are hostile strings.
"""

from pathlib import Path
from typing import Any

from review_helpers import HOSTILE

from eta_rxncat.review import RunData, canonical_run_data_json

STUB_PATH = Path(__file__).with_name("data") / "m12_stub_run_data.json"

SYMBOLS = ["C", "C", "H", "H", "H", "H"]
COORDINATES = [
    [0.0, 0.0, 0.0],
    [1.8, 0.0, 0.0],
    [-0.5, 0.9, 0.0],
    [-0.5, -0.9, 0.0],
    [2.3, 0.9, 0.0],
    [2.3, -0.9, 0.0],
]
HALF = 0.7071067812
STRETCH = [[-HALF, 0.0, 0.0], [HALF, 0.0, 0.0], *([[0.0, 0.0, 0.0]] * 4)]
"""The bond-stretch mode: atoms 0 and 1 along -x and +x, unit length over all components."""

BEND = [[0.0, 0.0, 0.0]] * 2 + [[0.0, HALF, 0.0], [0.0, -HALF, 0.0]] + [[0.0, 0.0, 0.0]] * 2
"""The second mode of the two-mode transition state: H2 and H3 apart along y."""

TRAJECTORY_C1_X = (1.4, 1.9, 2.4)
"""The x coordinate of atom 1 in the three frames of the known trajectory."""

HOSTILE_FILE = "<!--<img src=x onerror=alert(2)>   &.sqlite"
HOSTILE_CANDIDATE = f"r={HOSTILE}"
ENGINE_ID = "rdkit_ff|2026.1.1|none"
THERMO_ID = "thermo:20.0:0.1:0.001:100"


def key(digit: str) -> str:
    """Return a fake stage key."""
    return digit * 64


def frame(c1_x: float, energy: float, accepted: bool | None) -> dict[str, Any]:
    """Return a frame that differs from the others in atom 1's x coordinate."""
    coordinates = [list(r) for r in COORDINATES]
    coordinates[1][0] = c1_x
    return {
        "coordinates_angstrom": coordinates,
        "energy_hartree": energy,
        "max_gradient_hartree_per_bohr": 0.01,
        "accepted_bool": accepted,
        "ladder_step": None,
    }


def trajectory(
    name: str, kind: str, label: str, digit: str, frames: list[Any], total: int, stride: int
) -> dict[str, Any]:
    """Return a stored, converged trajectory."""
    return {
        "status": "stored",
        "trajectory_id": name,
        "kind": kind,
        "species_id": "ts" if kind == "ts_search" else "reactant",
        "label": label,
        "stage_key": key(digit),
        "frames": frames,
        "n_frames_total": total,
        "decimation_stride": stride,
        "convergence": {
            "converged_bool": True,
            "failed_code": None,
            "n_steps": total,
            "n_engine_calls": None,
            "final_energy_hartree": frames[-1]["energy_hartree"],
            "final_max_gradient_hartree_per_bohr": 0.0001,
            "recovery_steps": [],
        },
    }


def frequency(name: str, species: str, digit: str, modes: list[Any]) -> dict[str, Any]:
    """Return a completed frequency entry whose imaginary modes are ``modes``."""
    imaginary = [
        {"frequency_cm1": -500.0 - 100.0 * k, "displacements_angstrom": mode}
        for k, mode in enumerate(modes)
    ]
    return {
        "status": "completed",
        "frequency_id": name,
        "species_id": species,
        "stage_key": key(digit),
        "coordinates_angstrom": COORDINATES,
        "frequencies_cm1": [m["frequency_cm1"] for m in imaginary] + [900.0, 3000.0],
        "n_imaginary": len(imaginary),
        "imag_tol_cm1": 20.0,
        "imaginary_modes": imaginary,
    }


def identity(overlap: float, distance: float, reasons: list[str]) -> dict[str, Any]:
    """Return the identity numbers of a stub transition state with one imaginary mode."""
    return {
        "n_imaginary": 1,
        "imaginary_frequency_cm1": -500.0,
        "forming_overlap": overlap,
        "active_core_ke_fraction": 0.9,
        "forming_distances": [{"i": 0, "j": 1, "distance_angstrom": distance}],
        "in_phase_bool": True,
        "passed_bool": not reasons,
        "reason_codes": reasons,
    }


FAILED_IDENTITY = identity(
    0.131, 3.662, ["forming_distance_out_of_window", "forming_overlap_below_threshold"]
)

SAMPLES: list[dict[str, Any]] = [
    {
        "template_id": "t1",
        "sample_index": 0,
        "source": "seed",
        "frequency_id": "frequency:stretch",
        "kind": "member",
        "weight_fraction": 1.0,
        "identity": identity(0.9, 2.4, []),
    },
    {
        "template_id": "t1",
        "sample_index": 1,
        "source": "perturb:0",
        "frequency_id": "frequency:rejected",
        "kind": "excluded",
        "reason_code": "gate_failed:forming_overlap",
        "identity": FAILED_IDENTITY,
    },
    {
        "template_id": "t1",
        "sample_index": 2,
        "source": "perturb:1",
        "frequency_id": "frequency:merged",
        "kind": "merged",
        "merged_into_index": 0,
        "identity": identity(0.9, 2.4, []),
    },
    {
        "template_id": "t1",
        "sample_index": 3,
        "source": "perturb:2",
        "kind": "excluded",
        "reason_code": "seed_clash",
        "clash": {"i": 4, "j": 5, "distance_angstrom": 0.438, "ratio": 0.35},
    },
]

ENDPOINTS: list[dict[str, Any]] = [
    {
        "frequency_id": "frequency:superseded",
        "kind": "superseded_by_push",
        "superseded_by_frequency_id": "frequency:minimum",
    },
    {"frequency_id": "frequency:minimum", "kind": "kept"},
]


def candidate(candidate_id: str, entry_id: str, pathway: str, **extra: Any) -> dict[str, Any]:
    """Return a candidate unit; ``extra`` overrides its keys."""
    unit: dict[str, Any] = {
        "candidate_entry_id": f"{candidate_id}|{pathway}|{ENGINE_ID}",
        "candidate_id": candidate_id,
        "entry_ids_by_site": {"r": entry_id},
        "pathway": pathway,
        "node_id": "ts_node",
        "engine_id": ENGINE_ID,
        "thermo_options_id": THERMO_ID,
        "species_id": "ts",
        "charge": 0,
        "spin_multiplicity": 1,
        "template_rank_used": 1,
        "chosen_template_id": "t1",
        "stop_reason_code": None,
        "fallback_attempts": [],
        "graft_refusals": [],
        "dG_dagger_kcal_mol": None,
        "ddG_dagger_kcal_mol": None,
        "graft_rmsd_angstrom": None,
        "stall_cap_reached_bool": False,
        "members": [],
        "frequency_ids": [],
        "trajectory_ids": [],
        "endpoint_frequency_ids": [],
        "endpoint_trajectory_ids": [],
    }
    unit.update(extra)
    return unit


def m12_stub() -> RunData:
    """Return the stub document."""
    plain = candidate(
        "r=ethyl",
        "ethyl",
        "endo",
        template_rank_used=2,
        fallback_attempts=[
            {"template_id": "t0", "rank": 1, "outcome": "fell_through", "reason_code": "face"},
            {"template_id": "t1", "rank": 2, "outcome": "chosen", "reason_code": None},
        ],
        dG_dagger_kcal_mol=12.5,
        graft_rmsd_angstrom=0.05,
        members=[
            {
                "member_index": 0,
                "source": "seed",
                "weight_fraction": 1.0,
                "gibbs_free_energy_hartree": -79.0,
                "degeneracy": 1,
                "rmsd_to_seed_angstrom": 0.0,
                "frequency_id": "frequency:stretch",
                "trajectory_ids": ["ts_search:three_frames"],
            }
        ],
        frequency_ids=["frequency:stretch", "frequency:rejected", "frequency:merged"],
        trajectory_ids=["ts_search:three_frames"],
        endpoint_frequency_ids=["frequency:superseded", "frequency:minimum"],
        endpoint_trajectory_ids=["endpoint_opt:decimated"],
        sample_dispositions=SAMPLES,
        endpoint_dispositions=ENDPOINTS,
    )
    hostile = candidate(
        HOSTILE_CANDIDATE,
        HOSTILE,
        "exo",
        frequency_ids=["frequency:two_modes"],
        trajectory_ids=["ts_search:hostile"],
    )
    three = [
        frame(x, -79.0 - 0.01 * k, accepted)
        for k, (x, accepted) in enumerate(zip(TRAJECTORY_C1_X, (True, False, True), strict=True))
    ]
    five = [frame(1.5 + 0.1 * k, -79.1 - 0.001 * k, None) for k in range(5)]
    return RunData.model_validate(
        {
            "schema_version": 1,
            "provenance": {
                "eta_version": "0.7.0",
                "store_file_name": HOSTILE_FILE,
                "engines": [
                    {
                        "engine_id": ENGINE_ID,
                        "name": "rdkit_ff",
                        "version": "2026.1.1",
                        "model": None,
                    }
                ],
                "optimizers": [],
                "thermo_options": [
                    {
                        "thermo_options_id": THERMO_ID,
                        "imag_tol_cm1": 20.0,
                        "sym_tol_angstrom": 0.1,
                        "linear_tol_angstrom": 0.001,
                        "max_automorphisms": 100,
                    }
                ],
                "stage_keys": [],
            },
            "species": [
                {
                    "species_id": species_id,
                    "label": label,
                    "symbols": SYMBOLS,
                    "coordinates_angstrom": COORDINATES,
                    "charge": 0,
                    "spin_multiplicity": 1,
                    "active_atom_indices": [0, 1],
                }
                for species_id, label in (
                    ("reactant", "reactant"),
                    ("ts", "C0-C1 stretch TS"),
                    ("ts_hostile", HOSTILE),
                )
            ],
            "frequencies": [
                frequency("frequency:minimum", "reactant", "1", []),
                frequency("frequency:stretch", "ts", "2", [STRETCH]),
                frequency("frequency:two_modes", "ts_hostile", "3", [STRETCH, BEND]),
                frequency("frequency:rejected", "ts", "7", [STRETCH]),
                frequency("frequency:merged", "ts", "8", [STRETCH]),
                frequency("frequency:superseded", "reactant", "9", [BEND]),
            ],
            "trajectories": [
                trajectory("endpoint_opt:decimated", "endpoint_opt", "reactant", "4", five, 9, 2),
                trajectory("ts_search:hostile", "ts_search", HOSTILE, "5", three, 3, 1),
                trajectory("ts_search:three_frames", "ts_search", "t1:seed", "6", three, 3, 1),
            ],
            "candidates": [plain, hostile],
            "gates": [
                {
                    "gate_id": "graft_rmsd",
                    "candidate_entry_id": plain["candidate_entry_id"],
                    "pass_bool": True,
                    "value": 0.05,
                    "unit": "angstrom",
                    "threshold": 0.15,
                    "detail_code": None,
                },
                {
                    "gate_id": "one_imaginary",
                    "candidate_entry_id": hostile["candidate_entry_id"],
                    "pass_bool": False,
                    "value": 2.0,
                    "unit": "count",
                    "threshold": 1.0,
                    "detail_code": None,
                },
            ],
        }
    )


def main() -> None:
    """Write the stub file."""
    STUB_PATH.parent.mkdir(exist_ok=True)
    STUB_PATH.write_bytes(canonical_run_data_json(m12_stub()))


if __name__ == "__main__":
    main()
