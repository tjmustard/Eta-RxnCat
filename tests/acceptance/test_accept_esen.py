"""Acceptance: esen_omol25 on CUDA, four cases, vs fairchem's own high-precision predictor."""

from pathlib import Path
from typing import Any

import pytest
from accept_helpers import CASES, evaluated

from eta_rxncat.core import StageConfig
from eta_rxncat.engines import ESENOMol25Engine, ev_to_hartree

pytestmark = [pytest.mark.acceptance, pytest.mark.mlip_uma]
EV = 27.211386245988
BOHR = 0.529177210903


@pytest.fixture(scope="module")
def engine() -> ESENOMol25Engine:
    """The esen_omol25 engine on cuda (route A weights in fairchem's cache)."""
    return ESENOMol25Engine.from_stage(
        StageConfig(kind="single_point", engine="esen_omol25", method=ESENOMol25Engine.METHOD),
        device="cuda",
    )


@pytest.fixture(scope="module")
def calculator() -> Any:
    """Fairchem's own predictor + calculator, high precision, cuda."""
    from fairchem.core.calculate.ase_calculator import FAIRChemCalculator
    from fairchem.core.calculate.pretrained_mlip import get_predict_unit

    unit = get_predict_unit(
        ESENOMol25Engine.REGISTRY_NAME, inference_settings="high-precision", device="cuda"
    )
    return FAIRChemCalculator(unit, task_name="omol")


@pytest.mark.parametrize("case", CASES)
def test_case(
    engine: ESENOMol25Engine, calculator: Any, cases: dict[str, Any], out_dir: Path, case: str
) -> None:
    """Energy within max(1e-6 eV, 1e-10 |E|) and forces within 1e-5 eV/A, explicit charge/spin."""
    import ase

    s = cases[case]
    atoms = ase.Atoms(s.symbols, positions=s.coordinates)
    atoms.info.update(charge=s.charge, spin=s.spin_multiplicity)
    atoms.calc = calculator
    e_ref = float(atoms.get_potential_energy())
    f_ref = atoms.get_forces().tolist()
    result = engine.evaluate(s)
    diff = abs(result.energy_hartree - ev_to_hartree(e_ref))
    forces = result.forces_hartree_per_bohr
    assert forces is not None
    d_f = max(
        abs(f * EV / BOHR - r)
        for fr, rr in zip(forces, f_ref, strict=True)
        for f, r in zip(fr, rr, strict=True)
    )
    evaluated(
        out_dir,
        "esen_omol25",
        case,
        lambda: result,
        diff,
        reference_force_abs_diff_ev_per_ang=d_f,
        energy_tolerance_hartree=ev_to_hartree(max(1e-6, 1e-10 * abs(e_ref))),
    )
    assert result.device == "cuda"
    assert diff * EV <= max(1e-6, 1e-10 * abs(e_ref))
    assert d_f <= 1e-5
