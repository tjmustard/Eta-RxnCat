"""H10: TJ's T1/T2 XYZ re-derive to the input SMILES (v0.3.0 slice 08; tier D, writes nothing).

The SMILES in the T1/T2 inputs were derived from TJ's XYZ; this re-derives them with the running
RDKit and compares molecules (both canonicalised), never strings as written (R30).
"""

from pathlib import Path

import pytest
import yaml
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds

E2E5 = Path(__file__).resolve().parents[2] / "e2e" / "data" / "e2e5"


def inputs() -> list[tuple[str, str]]:
    """(xyz path relative to e2e5/, input SMILES) for every seeded T1/T2 species."""
    pairs = []
    for name in ("t1_dimethoxybutadiene.yaml", "t2_cp_cyclopropene.yaml"):
        data = yaml.safe_load((E2E5 / name).read_text(encoding="utf-8"))
        for species in data["species"]:
            for xyz in species["seed_xyz"]:
                pairs.append((xyz, species["smiles"]))
    return pairs


def canonical(smiles: str) -> str:
    """RDKit's canonical isomeric SMILES of ``smiles``."""
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, smiles
    return str(Chem.MolToSmiles(mol))


def derive(path: Path) -> str:
    """Bond perception at charge 0 plus 3D stereo, as the conformer seed check does (R24)."""
    mol = Chem.Mol(Chem.MolFromXYZBlock(path.read_text(encoding="utf-8")))
    rdDetermineBonds.DetermineBonds(mol, charge=0)
    Chem.AssignStereochemistryFrom3D(mol)
    return str(Chem.MolToSmiles(Chem.RemoveHs(mol)))


def test_four_tj_structures_present() -> None:
    """T1 has one seed and T2 three: TJ's four XYZ files."""
    assert sorted(xyz for xyz, _ in inputs()) == [
        "xyz/1_cyclopentadiene.xyz",
        "xyz/2_dimethoxybutadiene.xyz",
        "xyz/5_cyclopropene.xyz",
        "xyz/P1a_n.xyz",
    ]


@pytest.mark.parametrize(("xyz", "smiles"), inputs(), ids=[x for x, _ in inputs()])
def test_xyz_rederives_to_input_smiles(xyz: str, smiles: str) -> None:
    """The XYZ re-derives to the same molecule as the input SMILES (stereo included)."""
    assert canonical(derive(E2E5 / xyz)) == canonical(smiles)
