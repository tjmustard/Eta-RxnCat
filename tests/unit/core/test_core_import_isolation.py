"""``eta_rxncat.core`` imports neither numpy nor RDKit (mission G1)."""

import subprocess
import sys


def test_core_imports_without_numpy_or_rdkit() -> None:
    """A fresh interpreter that imports core loads no numpy and no RDKit module."""
    code = (
        "import sys, eta_rxncat.core\n"
        "assert eta_rxncat.core.EnumerationPlan\n"
        "print(sorted(m for m in sys.modules if m.split('.')[0] in ('numpy', 'rdkit')))\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, timeout=120
    )
    assert done.stdout.strip() == "[]"
