"""ASE calculator over eta's engines, for geomeTRIC's black-box TS cross-check (v0.5.0 slice 11).

Acceptance-only test code. This is the only file in the repository that imports ``ase`` (N1); it is
loaded by the ``geometric-optimize`` subprocess (``--engine ase --ase-class
eta_geometric_shim.EtaCalculator``), never by eta. geomeTRIC is driven through its documented CLI
only (TJ A1 "Q1. A", mission R5); nothing here calls geomeTRIC.
"""

from typing import Any

import numpy as np
from ase.calculators.calculator import Calculator, all_changes
from e2e_env import engine_for

from eta_rxncat.core import MolecularState
from eta_rxncat.engines import HARTREE_EV
from eta_rxncat.engines.units import BOHR_ANGSTROM
from eta_rxncat.orchestrator import build_engine


class EtaCalculator(Calculator):  # type: ignore[misc]
    """Energy (eV) and forces (eV/Angstrom) from eta's engine for a recipe (``xtb`` | ``uma``).

    The structure is taken as neutral and singlet (every Tier 3 case is).
    """

    implemented_properties = ["energy", "forces"]

    def __init__(self, recipe: str, **kwargs: Any) -> None:
        """Build the recipe's engine once."""
        super().__init__(**kwargs)
        stage, runtime = engine_for(recipe)
        self.engine = build_engine(stage, runtime)

    def calculate(
        self,
        atoms: Any = None,
        properties: Any = ("energy",),
        system_changes: Any = all_changes,
    ) -> None:
        """Evaluate eta's engine on ``atoms`` and store energy and forces in ASE units."""
        super().calculate(atoms, properties, system_changes)
        energy, forces = ase_results(self.engine, self.atoms)
        self.results["energy"] = energy
        self.results["forces"] = forces


def ase_results(engine: Any, atoms: Any) -> tuple[float, Any]:
    """Energy (eV) and forces (eV/Angstrom, NumPy) of ``atoms`` from an eta engine.

    ASE calculators return NumPy arrays (geomeTRIC's ASE engine calls ``.flatten()`` on them).
    """
    result = engine.evaluate(to_state(atoms), forces=True)
    forces = result.forces_hartree_per_bohr
    if forces is None:
        raise RuntimeError("eta engine returned no forces")
    converted = np.asarray(forces, dtype=np.float64) * (HARTREE_EV / BOHR_ANGSTROM)
    return result.energy_hartree * HARTREE_EV, converted


def to_state(atoms: Any) -> MolecularState:
    """An ASE ``Atoms`` as a neutral singlet ``MolecularState`` (Angstrom)."""
    return MolecularState(
        symbols=list(atoms.get_chemical_symbols()),
        coordinates=[[float(v) for v in row] for row in atoms.get_positions()],
        charge=0,
        spin_multiplicity=1,
    )
