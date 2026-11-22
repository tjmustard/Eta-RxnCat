"""Tests for the top-level ``eta_rxncat`` package."""

import json
import subprocess
import sys

import eta_rxncat

HEAVY_MODULES = ("torch", "pyscf", "rdkit")


def test_version() -> None:
    """The package reports the v0.1.0 version string."""
    assert eta_rxncat.__version__ == "0.1.0"


def test_import_loads_no_heavy_modules() -> None:
    """Importing the package in a fresh interpreter loads none of the heavy backends."""
    code = (
        "import json, sys\n"
        "import eta_rxncat\n"
        f"heavy = {HEAVY_MODULES!r}\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in heavy)\n"
        "print(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []
