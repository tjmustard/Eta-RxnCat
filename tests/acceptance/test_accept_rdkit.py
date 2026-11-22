"""Acceptance: rdkit_ff (UFF) on water against RDKit's own API, plus the three refusals."""

from pathlib import Path
from typing import Any

import pytest
from accept_helpers import evaluated, refused

from eta_rxncat.core import StageConfig
from eta_rxncat.engines import EngineInputError, RDKitFFEngine, kcal_mol_to_hartree

pytestmark = pytest.mark.acceptance


def engine() -> RDKitFFEngine:
    """UFF single point."""
    return RDKitFFEngine.from_stage(
        StageConfig(kind="single_point", engine="rdkit_ff", method="uff")
    )


def test_rdkit_water(cases: dict[str, Any], out_dir: Path) -> None:
    """Water energy equals RDKit's own UFF on the same input (<= 1e-10 relative)."""
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds, rdForceFieldHelpers

    water = cases["water"]
    lines = ["3", ""] + [
        f"{s} {x!r} {y!r} {z!r}"
        for s, (x, y, z) in zip(water.symbols, water.coordinates, strict=True)
    ]
    mol = Chem.MolFromXYZBlock("\n".join(lines) + "\n")
    rdDetermineBonds.DetermineBonds(mol, charge=0)
    ff = rdForceFieldHelpers.UFFGetMoleculeForceField(mol, ignoreInterfragInteractions=False)
    ff.Initialize()
    ref = kcal_mol_to_hartree(ff.CalcEnergy())
    result = engine().evaluate(water)
    diff = abs(result.energy_hartree - ref)
    evaluated(out_dir, "rdkit_ff", "water", lambda: result, diff, reference="RDKit UFF CalcEnergy")
    assert diff <= 1e-10 * abs(ref)
    assert mol.GetNumAtoms() == 3


@pytest.mark.parametrize("case", ["hydroxide", "hydronium", "hydroxyl"])
def test_rdkit_refusals(cases: dict[str, Any], out_dir: Path, case: str) -> None:
    """Charged or open-shell states are refused with EngineInputError."""
    with pytest.raises(EngineInputError) as info:
        engine().evaluate(cases[case])
    refused(out_dir, "rdkit_ff", case, info.value)
