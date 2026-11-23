"""Rotational symmetry number from the geometry and capped graph automorphisms (DV-02, R8, R9)."""

import numpy as np
from rdkit import Chem

from eta_rxncat.core import MolecularState, ThermoAnalysisOptions
from eta_rxncat.thermo._geometry import automorphisms, center_of_mass, is_linear, permuted_rmsds
from eta_rxncat.thermo.errors import ThermoInputError
from eta_rxncat.thermo.masses import atomic_masses_amu


def _centrosymmetric(state: MolecularState, sym_tol_angstrom: float) -> bool:
    """Return whether every atom has a same-element partner at -r about the centre of mass."""
    coords = np.asarray(state.coordinates, dtype=np.float64)
    r = coords - center_of_mass(coords, atomic_masses_amu(state.symbols))
    for i, symbol in enumerate(state.symbols):
        partners = [j for j, other in enumerate(state.symbols) if other == symbol]
        distances = np.linalg.norm(r[partners] + r[i], axis=1)
        if not np.any(distances <= sym_tol_angstrom):
            return False
    return True


def rotational_symmetry_number(
    state: MolecularState, smiles: str, *, analysis: ThermoAnalysisOptions
) -> int:
    """Return the rotational symmetry number sigma of ``state``.

    sigma is the number of graph automorphisms of the SMILES molecule (hydrogens added) whose
    permutation of the geometry is undone by a proper rotation to within ``sym_tol_angstrom``
    RMSD. A linear molecule has sigma 2 if centrosymmetric, else 1; a single atom has sigma 1.

    Args:
        state: The geometry; its atom order must equal that of ``Chem.AddHs(smiles)``.
        smiles: The molecule's SMILES.
        analysis: ``sym_tol_angstrom``, ``linear_tol_angstrom`` and ``max_automorphisms``.

    Raises:
        ThermoInputError: If the SMILES does not parse, its atoms do not match the state's
            element sequence, or the automorphism cap is reached.
    """
    parsed = Chem.MolFromSmiles(smiles)
    if parsed is None:
        raise ThermoInputError(f"SMILES does not parse: {smiles!r}")
    mol = Chem.AddHs(parsed)
    elements = [atom.GetSymbol() for atom in mol.GetAtoms()]
    if elements != list(state.symbols):
        raise ThermoInputError(
            f"SMILES {smiles!r} atoms {elements} do not match the state's {list(state.symbols)}"
        )
    if len(elements) == 1:
        return 1
    masses = atomic_masses_amu(state.symbols)
    if is_linear(state.coordinates, masses, analysis.linear_tol_angstrom):
        return 2 if _centrosymmetric(state, analysis.sym_tol_angstrom) else 1
    perms = automorphisms(mol, analysis.max_automorphisms)
    rmsds = permuted_rmsds(state.coordinates, perms)
    sigma = int(np.count_nonzero(rmsds <= analysis.sym_tol_angstrom))
    if sigma < 1:  # the identity always matches; this guards a broken automorphism list
        raise ThermoInputError("no automorphism (not even the identity) matched the geometry")
    return sigma
