"""Tests for the rotational symmetry number (v0.3.0 slice 03, DV-02, R8, R9)."""

import numpy as np
import pytest
import thermo_geometries as g
from rdkit import Chem
from rdkit.Chem import AllChem

from eta_rxncat.core import MolecularState, ThermoAnalysisOptions
from eta_rxncat.thermo import ThermoInputError, rotational_symmetry_number
from eta_rxncat.thermo._geometry import automorphisms, kabsch_rmsd

ANALYSIS = ThermoAnalysisOptions()


@pytest.mark.parametrize(
    ("name", "st", "smiles", "sigma"),
    [
        ("water", g.water(), "O", 2),
        ("ammonia", g.ammonia(), "N", 3),
        ("methane", g.methane(), "C", 12),
        ("ethylene", g.ethylene(), "C=C", 4),
        ("benzene", g.benzene(), "c1ccccc1", 12),
        ("CO2", g.co2(), "O=C=O", 2),
        ("HCN", g.hcn(), "C#N", 1),
        ("n-butane anti", g.butane(180.0), "CCCC", 2),
        ("n-butane gauche", g.butane(60.0), "CCCC", 2),
        ("water, H moved 0.2 A", g.water(h_shift=0.2), "O", 1),
    ],
)
def test_symmetry_numbers(name: str, st: MolecularState, smiles: str, sigma: int) -> None:
    """Sigma of idealised geometries is exact."""
    assert rotational_symmetry_number(st, smiles, analysis=ANALYSIS) == sigma, name


def test_single_atom_sigma_is_one() -> None:
    """A single atom has sigma 1."""
    assert (
        rotational_symmetry_number(g.state(["Ar"], [[0.0, 0.0, 0.0]]), "[Ar]", analysis=ANALYSIS)
        == 1
    )


def test_bent_co2_within_tolerance_keeps_sigma_two() -> None:
    """CO2 bent 1e-4 Angstrom is linear and centrosymmetric within tolerance (R9)."""
    assert rotational_symmetry_number(g.co2(bend=1e-4), "O=C=O", analysis=ANALYSIS) == 2


def test_hexamethylethane_reaches_the_cap() -> None:
    """CC(C)(C)C(C)(C)C with H has more than 100000 automorphisms: ThermoInputError (R8)."""
    mol = Chem.AddHs(Chem.MolFromSmiles("CC(C)(C)C(C)(C)C"))
    AllChem.EmbedMolecule(mol, randomSeed=42)
    coords = mol.GetConformer().GetPositions().tolist()
    st = MolecularState(
        symbols=[a.GetSymbol() for a in mol.GetAtoms()],
        coordinates=coords,
        charge=0,
        spin_multiplicity=1,
    )
    with pytest.raises(ThermoInputError, match="automorphism cap reached"):
        rotational_symmetry_number(st, "CC(C)(C)C(C)(C)C", analysis=ANALYSIS)


def test_counts_beyond_rdkit_default_of_1000() -> None:
    """Neopentane has 4! x 6^4 = 31104 automorphisms; RDKit's default would stop at 1000."""
    mol = Chem.AddHs(Chem.MolFromSmiles("CC(C)(C)C"))
    assert len(mol.GetSubstructMatches(mol, uniquify=False)) == 1000
    assert len(automorphisms(mol, ANALYSIS.max_automorphisms)) == 31104
    assert rotational_symmetry_number(g.neopentane(), "CC(C)(C)C", analysis=ANALYSIS) == 12


def test_cap_is_honoured_when_lowered() -> None:
    """With max_automorphisms 1000, neopentane's 31104 automorphisms hit the cap."""
    low = ThermoAnalysisOptions(max_automorphisms=1000)
    with pytest.raises(ThermoInputError, match="automorphism cap reached"):
        rotational_symmetry_number(g.neopentane(), "CC(C)(C)C", analysis=low)


def test_element_order_must_match_smiles() -> None:
    """A state whose atoms are not in AddHs order is rejected."""
    st = g.state(["H", "O", "H"], np.asarray(g.water().coordinates)[[1, 0, 2]])
    with pytest.raises(ThermoInputError, match="do not match"):
        rotational_symmetry_number(st, "O", analysis=ANALYSIS)


def test_unparsable_smiles_rejected() -> None:
    """A SMILES RDKit cannot parse raises ThermoInputError."""
    with pytest.raises(ThermoInputError, match="does not parse"):
        rotational_symmetry_number(g.water(), "O(", analysis=ANALYSIS)


def test_kabsch_never_reflects() -> None:
    """A chiral arrangement and its mirror image do not superimpose (no improper rotation)."""
    tetra = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.5, 0.0], [0.0, 0.0, 2.0]])
    mirror = tetra * np.array([1.0, 1.0, -1.0])
    assert kabsch_rmsd(tetra, tetra) == pytest.approx(0.0, abs=1e-12)
    assert kabsch_rmsd(tetra, mirror) > 0.1
