"""Acceptance fixtures (slice 11): the shared test set and the per-case output directory."""

import os
from pathlib import Path
from typing import Any

import pytest
from accept_helpers import CASES, load_case


@pytest.fixture(scope="session")
def cases() -> dict[str, Any]:
    """The mission §5 test set (water, hydroxide, hydroxyl, hydronium, Pd anion)."""
    return {name: load_case(name) for name in (*CASES, "hydronium")}


@pytest.fixture(scope="session")
def out_dir() -> Path:
    """$ETA_RXNCAT_ACCEPTANCE_OUT: where each case writes its JSON (outside the repo)."""
    raw = os.environ.get("ETA_RXNCAT_ACCEPTANCE_OUT")
    assert raw, "set ETA_RXNCAT_ACCEPTANCE_OUT to a directory outside the repo"
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path
