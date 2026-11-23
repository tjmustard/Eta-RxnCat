"""TJ T1/T2 derived SMILES as a candidate for TJ's confirmation (v0.3.0 slice 08, H10, R30)."""

import hashlib
from pathlib import Path

import pytest
import rdkit
from checks import write
from e2e_env import PROMOTED, acceptance
from fixtures import DATA, t1, t2
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

FILES = {
    "dimethoxybutadiene": "xyz/2_dimethoxybutadiene.xyz",
    "cyclopentadiene": "xyz/1_cyclopentadiene.xyz",
    "cyclopropene": "xyz/5_cyclopropene.xyz",
    "P1a_n": "xyz/P1a_n.xyz",
}


def canonical(smiles: str) -> str:
    """Canonical isomeric SMILES with the running RDKit."""
    return str(Chem.MolToSmiles(Chem.MolFromSmiles(smiles)))


def derive(path: Path) -> str:
    """Bond perception at charge 0 plus 3D stereo."""
    mol = Chem.Mol(Chem.MolFromXYZBlock(path.read_text(encoding="utf-8")))
    rdDetermineBonds.DetermineBonds(mol, charge=0)
    Chem.AssignStereochemistryFrom3D(mol)
    return str(Chem.MolToSmiles(Chem.RemoveHs(mol)))


def test_e2e5_smiles_candidate(candidate_dir: Path, commit_sha: str) -> None:
    """Write e2e5_smiles.json; compare with TJ's promoted file if present, else pending."""
    inputs = {s.species_id: s.smiles for f in (t1(), t2()) for s in f.species}
    species = {}
    for species_id, rel in FILES.items():
        path = DATA / "e2e5" / rel
        derived = derive(path)
        assert canonical(derived) == canonical(inputs[species_id]), species_id
        species[species_id] = {
            "xyz_file": f"tests/e2e/data/e2e5/{rel}",
            "xyz_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "derived_smiles": derived,
            "input_smiles": inputs[species_id],
            "rdkit_version": rdkit.__version__,
        }
    promoted = PROMOTED / "e2e5_smiles.json"
    if promoted.exists():
        import json

        confirmed = json.loads(promoted.read_text(encoding="utf-8"))["species"]
        same = all(
            canonical(confirmed[k]["derived_smiles"]) == canonical(v["input_smiles"])
            for k, v in species.items()
        )
        status = "confirmed" if same else "fail"
    else:
        status = "pending_confirmation"
    write(
        candidate_dir / "e2e5_smiles.json",
        {"fixture": "e2e5_smiles", "commit_sha": commit_sha, "species": species, "status": status},
    )
    print(f"\ne2e5 SMILES: { {k: v['derived_smiles'] for k, v in species.items()} } -> {status}")
    assert status != "fail"
    if status == "pending_confirmation" and acceptance():
        pytest.fail("e2e5 SMILES pending TJ's confirmation in an acceptance run")
