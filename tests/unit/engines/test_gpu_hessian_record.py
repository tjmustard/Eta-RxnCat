"""R44: the GPU KS analytic-Hessian routing is complete with respect to the committed record.

Default suite, no GPU. The router may choose GPU4PySCF's analytic KS Hessian only for a class
``(scf_type, solvation, ecp, grids_level)`` whose rows in
``docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`` are present and all <= 1e-4 Eh/Bohr^2.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import PySCFEngine
from eta_rxncat.engines.pyscf_gpu_cpu import engine as engine_module
from eta_rxncat.engines.pyscf_gpu_cpu.gpu import (
    GPU_ANALYTIC_KS_HESSIAN_CLASSES,
    HessianClass,
    classes_from_record,
    gpu_ks_hessian_class,
)

RECORD = Path(__file__).resolve().parents[3] / "docs/prd/v0.2.0/evidence/pyscf-gpu-support.json"
LIMIT = 1e-4


def rows() -> list[dict[str, Any]]:
    """The committed record's rows."""
    return list(json.loads(RECORD.read_text(encoding="utf-8"))["rows"])


def completeness_errors(
    classes: frozenset[HessianClass], record_rows: list[dict[str, Any]]
) -> list[str]:
    """Why ``classes`` is not exactly what ``record_rows`` support (empty: complete and sound)."""
    supported = classes_from_record(record_rows, LIMIT)
    errors = [f"routed but unsupported by the record: {k}" for k in sorted(classes - supported)]
    errors += [f"supported by the record but not routed: {k}" for k in sorted(supported - classes)]
    return errors


def test_routing_constant_equals_record() -> None:
    """Every class the auto rule routes to GPU analytic has rows, all <= 1e-4 (and vice versa)."""
    assert completeness_errors(GPU_ANALYTIC_KS_HESSIAN_CLASSES, rows()) == []
    for klass in GPU_ANALYTIC_KS_HESSIAN_CLASSES:
        errors = [
            r["max_abs_analytic_minus_fd"]
            for r in rows()
            if r.get("grid_response")
            and r.get("xc") != "hf"
            and (r["scf_type"], r["solvation"], r["ecp_present"], r["grid"]) == klass
        ]
        assert errors and max(errors) <= LIMIT, klass


def test_record_has_the_r44_iefpcm_rows() -> None:
    """IEF-PCM rows for water, HCl, HBr, HI+ECP at grids 3 and 9, RKS and UKS, plus hydroxyl UKS."""
    ief = {(r["case"], r["scf_type"], r["grid"]) for r in rows() if r.get("solvation") == "IEF-PCM"}
    expected = {
        (c, s, g) for c in ("water", "hcl", "hbr", "hi") for s in ("RKS", "UKS") for g in (3, 9)
    }
    expected |= {("hydroxyl", "UKS", g) for g in (3, 9)}
    assert expected <= ief
    assert all(
        r["ecp_present"] for r in rows() if r.get("solvation") == "IEF-PCM" and r["case"] == "hi"
    )


@pytest.mark.parametrize("klass", sorted(GPU_ANALYTIC_KS_HESSIAN_CLASSES))
def test_removing_a_class_rows_fails_completeness(klass: HessianClass) -> None:
    """Dropping a routed class's rows from the record makes the completeness check fail."""
    trimmed = [
        r
        for r in rows()
        if not (
            r.get("xc") != "hf"
            and (r.get("scf_type"), r.get("solvation"), r.get("ecp_present"), r.get("grid"))
            == klass
        )
    ]
    assert completeness_errors(GPU_ANALYTIC_KS_HESSIAN_CLASSES, trimmed) != []


def test_an_over_limit_row_removes_its_class() -> None:
    """A class with one row over 1e-4 is not analytic-eligible."""
    base = [
        {
            "xc": "b3lyp",
            "grid_response": True,
            "scf_type": "RKS",
            "solvation": "none",
            "ecp_present": False,
            "grid": 3,
            "max_abs_analytic_minus_fd": 1e-5,
        }
    ]
    assert classes_from_record(base) == {("RKS", "none", False, 3)}
    assert (
        classes_from_record([*base, {**base[0], "max_abs_analytic_minus_fd": 2e-4}]) == frozenset()
    )


def fake_gpu() -> SimpleNamespace:
    """Just enough of gpu_modules() for construction (budget from memGetInfo)."""
    runtime = SimpleNamespace(memGetInfo=lambda: (7_000_000_000, 8_073_248_768))
    return SimpleNamespace(
        cupy=SimpleNamespace(cuda=SimpleNamespace(runtime=runtime)), version="fake"
    )


@pytest.fixture
def water_states() -> dict[str, MolecularState]:
    """Water, and the hydroxyl radical, for routing classes."""
    return {
        "water": MolecularState(
            symbols=["O", "H", "H"],
            coordinates=[[0, 0, 0.1173], [0, 0.7572, -0.4692], [0, -0.7572, -0.4692]],
            charge=0,
            spin_multiplicity=1,
        ),
        "hydroxyl": MolecularState(
            symbols=["O", "H"], coordinates=[[0, 0, 0], [0, 0, 0.97]], charge=0, spin_multiplicity=2
        ),
    }


def route(
    monkeypatch: pytest.MonkeyPatch,
    classes: frozenset[HessianClass],
    state: MolecularState,
    pcm: str | None,
) -> str:
    """The method the GPU router picks for a B3LYP/def2-SVP stage under ``classes``."""
    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    monkeypatch.setattr(engine_module, "GPU_ANALYTIC_KS_HESSIAN_CLASSES", classes)
    kwargs: dict[str, Any] = {}
    if pcm:
        kwargs = {
            "solvation": Solvation(model="pcm", solvent="water"),
            "options": {"pcm_method": pcm},
        }
    eng = PySCFEngine.from_stage(
        StageConfig(
            kind="frequency", engine="pyscf_gpu_cpu", method="b3lyp", basis="def2-svp", **kwargs
        ),
        device="cuda",
    )
    stage = eng.resolved_stage_for(state)
    eng._on_gpu = True
    try:
        return eng._hessian_method(stage, state)
    finally:
        eng._on_gpu = False


def test_synthetic_record_without_iefpcm_routes_fd(
    monkeypatch: pytest.MonkeyPatch, water_states: dict[str, MolecularState]
) -> None:
    """A record missing the IEF-PCM class makes the router choose FD for IEF-PCM."""
    water = water_states["water"]
    no_ief = classes_from_record([r for r in rows() if r.get("solvation") != "IEF-PCM"])
    assert route(monkeypatch, no_ief, water, "IEF-PCM") == "finite_difference"
    full = classes_from_record(rows())
    klass = ("RKS", "IEF-PCM", False, 3)
    assert route(monkeypatch, full, water, "IEF-PCM") == (
        "analytic" if klass in full else "finite_difference"
    )


def test_router_uses_the_state_class(
    monkeypatch: pytest.MonkeyPatch, water_states: dict[str, MolecularState]
) -> None:
    """The class is computed per state: a doublet is UKS; an unrecorded grid level is FD."""
    hydroxyl = water_states["hydroxyl"]
    stage = StageConfig(
        kind="frequency",
        engine="pyscf_gpu_cpu",
        method="b3lyp",
        basis="def2-svp",
        options={"ecp": "none", "grids_level": 3},
    )
    assert gpu_ks_hessian_class(stage, hydroxyl) == ("UKS", "none", False, 3)
    only_rks = frozenset({("RKS", "none", False, 3)})
    assert route(monkeypatch, only_rks, hydroxyl, None) == "finite_difference"
    assert route(monkeypatch, only_rks, water_states["water"], None) == "analytic"
