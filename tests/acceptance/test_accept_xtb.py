"""Acceptance: xtb_subprocess (GFN2) on all four cases against a hand run of the same argv."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from accept_helpers import CASES, evaluated

from eta_rxncat.core import StageConfig
from eta_rxncat.engines import XTBSubprocessEngine
from eta_rxncat.engines.xtb_subprocess import parse_energy

pytestmark = [pytest.mark.acceptance, pytest.mark.xtb]


@pytest.mark.parametrize("case", CASES)
def test_xtb(cases: dict[str, Any], out_dir: Path, case: str) -> None:
    """Energy equals a hand run of the engine's own argv in a separate temp dir (<= 1e-10 Eh)."""
    s = cases[case]
    eng = XTBSubprocessEngine.from_stage(
        StageConfig(kind="single_point", engine="xtb_subprocess", method="gfn2"), threads=1
    )
    result = eng.evaluate(s)
    argv = eng.calls[-1]
    with tempfile.TemporaryDirectory() as work:
        lines = [str(len(s.symbols)), "hand"] + [
            f"{a} {x!r} {y!r} {z!r}" for a, (x, y, z) in zip(s.symbols, s.coordinates, strict=True)
        ]
        Path(work, "input.xyz").write_text("\n".join(lines) + "\n")
        env = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_STACKSIZE": "1G"}
        subprocess.run(argv, cwd=work, env=env, check=True, capture_output=True)
        ref = parse_energy(Path(work, "energy").read_text())
    diff = abs(result.energy_hartree - ref)
    evaluated(out_dir, "xtb_subprocess", case, lambda: result, diff, argv_tail=argv[1:])
    assert diff <= 1e-10
