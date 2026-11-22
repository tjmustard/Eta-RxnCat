"""Acceptance: mace (MACE-MP-0 medium, CUDA) on water against MACECalculator, plus the refusals."""

import os
from pathlib import Path
from typing import Any

import pytest
from accept_helpers import evaluated, refused

from eta_rxncat.core import StageConfig
from eta_rxncat.engines import EngineInputError, MACEEngine, ev_to_hartree

pytestmark = [pytest.mark.acceptance, pytest.mark.mlip_mace]
MODEL = Path(
    os.environ.get(
        "ETA_RXNCAT_MACE_MODEL",
        str(Path.home() / ".cache/eta-rxncat/mace/2023-12-03-mace-128-L1_epoch-199.model"),
    )
)


@pytest.fixture(scope="module")
def engine() -> MACEEngine:
    """The MACE engine on cuda (an acceptance run never falls back to CPU)."""
    return MACEEngine.from_stage(
        StageConfig(kind="single_point", engine="mace", method="mace-mp-0-medium"),
        model_path=MODEL,
        device="cuda",
    )


def test_mace_water(engine: MACEEngine, cases: dict[str, Any], out_dir: Path) -> None:
    """Water energy equals MACECalculator on the same ase.Atoms (<= 1e-6 eV), on cuda."""
    import ase
    from mace.calculators import MACECalculator

    water = cases["water"]
    atoms = ase.Atoms(water.symbols, positions=water.coordinates)
    atoms.calc = MACECalculator(model_paths=str(MODEL), default_dtype="float64", device="cuda")
    ref = ev_to_hartree(float(atoms.get_potential_energy()))
    result = engine.evaluate(water)
    diff = abs(result.energy_hartree - ref)
    evaluated(out_dir, "mace", "water", lambda: result, diff, reference_unit="Eh")
    assert result.device == "cuda"
    assert diff <= ev_to_hartree(1e-6)


@pytest.mark.parametrize("case", ["hydroxide", "hydronium", "hydroxyl"])
def test_mace_refusals(engine: MACEEngine, cases: dict[str, Any], out_dir: Path, case: str) -> None:
    """Charged or open-shell states are refused with EngineInputError."""
    with pytest.raises(EngineInputError) as info:
        engine.evaluate(cases[case])
    refused(out_dir, "mace", case, info.value)
