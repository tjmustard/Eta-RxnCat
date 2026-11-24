"""geomeTRIC black-box TS cross-check of the five Tier 3 cases on both recipes (v0.5.0 slice 11).

TJ A1 "Q1. A", mission R5: geomeTRIC's TS search runs only through its documented CLI
(``geometric-optimize --help``) in a subprocess, on eta's engine through the ASE shim
(``eta_geometric_shim.py``), from the same start and with eta's engine Hessian as the seed. Nobody
reads geomeTRIC source and no geomeTRIC function is called in this process (N2, N4). Every record
is reported only (US-014, P1): disagreement is information for TJ, never a failure.
"""

import gc
import json
import os
import subprocess
import sys
import tempfile
import time
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from acceptance import write_fragment
from checks import write
from e2e_env import REPO, engine_for
from fixtures import TSFixture, t3
from t3 import candidate_dir

from eta_rxncat.core import MolecularState, ThermoAnalysisOptions, ThermoConfig
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import superpose
from eta_rxncat.optimize import PRFOOptimizer
from eta_rxncat.orchestrator import TSRecipe, TSSpec, build_engine, run_transition_state
from eta_rxncat.store import ArtifactStore
from eta_rxncat.thermo import validate_transition_state

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]

CASES = {
    "ts1a_n": "t3_ts1a_n_unmapped.yaml",
    "ts1b_n": "t3_ts1b_n_mapped.yaml",
    "ts3a": "t3_ts3a_unmapped.yaml",
    "ts4a": "t3_ts4a_mapped.yaml",
    "n4": "t3_n4_unmapped.yaml",
}
RECIPES = ("xtb", "uma")
RECIPE_MARKS = {"xtb": pytest.mark.xtb, "uma": pytest.mark.mlip_uma}
XCHECK_DIR = Path(
    os.environ.get("ETA_RXNCAT_XCHECK_DIR", str(Path(tempfile.gettempdir()) / "eta-xcheck"))
)
"""Per-run records (scratch, never a candidate). Runs are split per recipe and case to cut peak
memory; ``test_t3_cross_check_fragment`` assembles the ten records into the fragment."""
GEOMETRIC = REPO / ".venv-accept-uma" / "bin" / "geometric-optimize"
HESSIAN_UNITS_ASSUMPTION = (
    "geometric-optimize --help documents --hessian file+last:<path> as 'NumPy format' but states "
    "no units; the seed is eta's Cartesian Hessian in Eh/Bohr^2 (atomic units), written with "
    "numpy.savetxt (assumption, slice 11)"
)
LICENCE_NOTE = (
    "geomeTRIC 1.1.1 'BSD 3-clause Non-AI' licence: open with TJ; used only as a CLI subprocess "
    "in .venv-accept-uma, nothing vendored or imported in src/ (reported, not decided)"
)
TS4A_START = """
import json, sys
sys.path.insert(0, {e2e!r})
from e2e_env import recipe_for
from fixtures import t3
from t3 import grafted_start
start, _ = grafted_start(t3("t3_ts4a_mapped.yaml"), recipe_for({recipe!r}), [0, 3, 6, 7])
open({out!r}, "w").write(json.dumps(start.model_dump(mode="json")))
"""
"""Builds the TS4a start in its own process: its pre-relaxation uses eta's GeometricOptimizer,
which imports geomeTRIC, and this process must stay free of it (MR5)."""


def write_xyz(path: Path, state: MolecularState) -> None:
    """An XYZ file in Angstrom, fixed-point (geomeTRIC's XYZ reader refuses scientific notation)."""
    rows = "".join(
        f"{s} {x:.10f} {y:.10f} {z:.10f}\n"
        for s, (x, y, z) in zip(state.symbols, state.coordinates)
    )
    path.write_text(f"{len(state.symbols)}\nstart\n{rows}", encoding="utf-8")


def last_frame(path: Path, template: MolecularState) -> MolecularState:
    """The last structure of a multi-frame XYZ, with ``template``'s charge, spin and active set."""
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    frame = lines[-n:]
    return MolecularState.model_validate(
        {
            **template.model_dump(),
            "symbols": [row.split()[0] for row in frame],
            "coordinates": [[float(v) for v in row.split()[1:4]] for row in frame],
        }
    )


def start_state(fixture: TSFixture, case: str, recipe: str, work: Path) -> MolecularState:
    """The same start as eta's search for this case and recipe (slices 08-10)."""
    if case != "ts4a":
        return fixture.start_state(recipe)
    out = work / "ts4a_start.json"
    code = TS4A_START.format(e2e=str(REPO / "tests" / "e2e"), recipe=recipe, out=str(out))
    subprocess.run([sys.executable, "-c", code], check=True, timeout=3600)
    return MolecularState.model_validate(json.loads(out.read_text(encoding="utf-8")))


def heavy_rmsd(a: MolecularState, b: MolecularState) -> float:
    """Heavy-atom RMSD (Angstrom) after Horn superposition, identity map."""
    heavy = [k for k, s in enumerate(a.symbols) if s != "H"]
    pa = np.asarray(a.coordinates)[heavy]
    pb = np.asarray(b.coordinates)[heavy]
    return float(superpose(pa, pb).rmsd_angstrom)


def cross_check(case: str, recipe: str, work: Path) -> dict[str, Any]:
    """One geomeTRIC TS run and its comparison with eta's search from the same start."""
    fixture = t3(CASES[case])
    stage, runtime = engine_for(recipe)
    engine = build_engine(stage, runtime)
    start = start_state(fixture, case, recipe, work)
    seed = engine.evaluate(start, forces=False, hessian=True).hessian_hartree_per_bohr2
    np.savetxt(work / "seed.txt", np.asarray(seed))
    # Release this process's engine while geomeTRIC's subprocess holds its own copy (peak memory).
    del engine
    gc.collect()
    write_xyz(work / "start.xyz", start)
    prefix = work / f"{case}.{recipe}"
    argv = [
        str(GEOMETRIC),
        "start.xyz",
        "--engine",
        "ase",
        "--ase-class",
        "eta_geometric_shim.EtaCalculator",
        "--ase-kwargs",
        json.dumps({"recipe": recipe}),
        "--transition",
        "yes",
        "--hessian",
        "file+last:seed.txt",
        "--prefix",
        str(prefix),
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO / "tests" / "e2e")}
    began = time.monotonic()
    try:
        proc = subprocess.run(
            ["timeout", "3600", *argv], cwd=work, env=env, capture_output=True, text=True
        )
        exit_code, tail = proc.returncode, (proc.stdout + proc.stderr)[-2000:]
    except OSError as exc:
        exit_code, tail = -1, str(exc)
    wall = time.monotonic() - began
    log = Path(f"{prefix}.log")
    optim = Path(f"{prefix}_optim.xyz")
    converged = optim.is_file() and log.is_file() and "Converged!" in log.read_text("utf-8")
    record: dict[str, Any] = {
        "command": " ".join(["timeout", "3600", *argv]),
        "exit_code": exit_code,
        "wall_time_s": wall,
        "converged_bool": converged,
        "status": "converged"
        if converged
        else ("geometric_not_converged" if exit_code == 0 else "geometric_failed"),
    }
    if not converged:
        record["log_tail"] = tail
    with ArtifactStore(work / "eta.sqlite") as store:
        eta = run_transition_state(
            TSSpec(ts_id=fixture.ts_id, start=start, forming_bonds=fixture.forming_bonds),
            TSRecipe(
                name=recipe,
                engine_stage=stage,
                ts_optimizer=PRFOOptimizer(),
                thermo_config=ThermoConfig(),
                analysis=ThermoAnalysisOptions(),
                engine_runtime=runtime,
            ),
            store,
        )
    record["eta_failed_reason"] = eta.failed_reason
    if not converged:
        return record
    engine = build_engine(stage, runtime)
    final = last_frame(optim, start)
    energy = engine.evaluate(final, forces=True).energy_hartree
    hessian = engine.evaluate(final, forces=False, hessian=True).hessian_hartree_per_bohr2
    validation = validate_transition_state(final, hessian, forming_bonds=fixture.forming_bonds)
    record["geometric_ts_energy_hartree"] = energy
    record["validation_at_geometric_ts"] = {
        "passed_bool": validation.passed_bool,
        "reasons": validation.reasons,
        "imaginary_frequency_cm1": validation.imaginary_frequency_cm1,
        "n_imaginary": validation.n_imaginary,
        "active_core_ke_fraction": validation.active_core_ke_fraction,
        "forming_stretch_overlap": validation.forming_stretch_overlap,
        "forming_bonds_in_phase_bool": validation.forming_bonds_in_phase_bool,
        "forming_distances_angstrom": validation.forming_distances_angstrom,
    }
    if eta.search is not None:
        eta_energy = engine.evaluate(eta.search.final_state, forces=True).energy_hartree
        record["eta_ts_energy_hartree"] = eta_energy
        record["delta_e_geometric_minus_eta_kcal_mol"] = (energy - eta_energy) * HARTREE_KCAL_MOL
        record["heavy_atom_rmsd_angstrom"] = heavy_rmsd(final, eta.search.final_state)
    return record


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("recipe", [pytest.param(r, marks=RECIPE_MARKS[r], id=r) for r in RECIPES])
def test_t3_cross_check_case(recipe: str, case: str, tmp_path: Path) -> None:
    """One geomeTRIC TS run for one case and recipe; its record goes to ``XCHECK_DIR``."""
    work = tmp_path / f"{case}.{recipe}"
    work.mkdir()
    record = cross_check(case, recipe, work)
    XCHECK_DIR.mkdir(parents=True, exist_ok=True)
    (XCHECK_DIR / f"{case}.{recipe}.json").write_text(json.dumps(record), encoding="utf-8")
    print(
        f"\nXCHECK {case}.{recipe}: status {record['status']} exit {record['exit_code']} "
        f"wall {record['wall_time_s']:.0f}s eta {record['eta_failed_reason']} "
        f"dE {record.get('delta_e_geometric_minus_eta_kcal_mol')} "
        f"rmsd {record.get('heavy_atom_rmsd_angstrom')} "
        f"val {record.get('validation_at_geometric_ts')}"
    )
    assert "status" in record and "exit_code" in record
    assert "geometric" not in sys.modules  # MR5: no geomeTRIC module in this eta process


def test_t3_cross_check_fragment(commit_sha: str) -> None:
    """Assemble the ten per-run records into the cross_check fragment (reported only)."""
    records = {
        f"{case}.{recipe}": json.loads(
            (XCHECK_DIR / f"{case}.{recipe}.json").read_text(encoding="utf-8")
        )
        for recipe in RECIPES
        for case in CASES
    }
    payload = {
        "fragment": "cross_check",
        "commit_sha": commit_sha,
        "geometric_version": metadata.version("geometric"),
        "hessian_units_assumption": HESSIAN_UNITS_ASSUMPTION,
        "licence_note": LICENCE_NOTE,
        "reported_only": True,
        "records": records,
    }
    write(candidate_dir() / "t3_cross_check.json", payload)
    write_fragment("t3_cross_check", "all", payload)
    assert len(records) == 10
    assert all("status" in r and "exit_code" in r for r in records.values())
    assert "geometric" not in sys.modules  # MR5
