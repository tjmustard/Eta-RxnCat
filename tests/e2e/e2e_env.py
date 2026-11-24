"""Shared E2E constants and recipes (imported by conftest and the tests; not a conftest itself)."""

import os
from pathlib import Path

import pytest

from eta_rxncat.core import StageConfig
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import Recipe

REPO = Path(__file__).resolve().parents[2]
CANDIDATES = REPO / "tests" / "candidate_outputs" / "v0.3.0"
PROMOTED = REPO / "tests" / "fixtures" / "v0.3.0"

RECIPE_PARAMS = [
    pytest.param("xtb", marks=pytest.mark.xtb, id="xtb"),
    pytest.param("uma", marks=pytest.mark.mlip_uma, id="uma"),
]
"""Both recipes (TJ Q2 "A"), each under its engine marker."""

DEVICES = {"xtb": "cpu", "uma": "cuda"}


def engine_for(name: str) -> tuple[StageConfig, dict[str, str]]:
    """The named recipe's engine stage and runtime (no optimizer, so geomeTRIC is never loaded)."""
    if name == "xtb":
        stage = StageConfig(
            kind="geometry_opt",
            engine="xtb_subprocess",
            method="gfn2",
            options={"alpb_state": "gsolv"},
        )
        return stage, {}
    stage = StageConfig(
        kind="geometry_opt",
        engine="uma_direct",
        method="uma-s-1p2p1",
        options={"inference_settings": "high-precision"},
    )
    return stage, {"device": DEVICES["uma"]}


def recipe_for(name: str) -> Recipe:
    """The named recipe: ``xtb`` = xtb_subprocess/gfn2, ``uma`` = uma_direct high precision."""
    stage, runtime = engine_for(name)
    return Recipe(name, stage, GeometricOptimizer(), engine_runtime=runtime)


def acceptance() -> bool:
    """Whether this is an acceptance run."""
    return os.environ.get("ETA_RXNCAT_ACCEPTANCE") == "1"
