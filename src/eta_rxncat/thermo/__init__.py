"""Ideal-gas quasi-RRHO thermochemistry derived from Cartesian Hessians (v0.3.0).

numpy and RDKit are imported here, never in ``eta_rxncat.core``.
"""

from eta_rxncat.thermo.boltzmann import boltzmann
from eta_rxncat.thermo.errors import (
    NotAMinimumError,
    ThermoError,
    ThermoInputError,
    check_ground_state,
)
from eta_rxncat.thermo.masses import atomic_masses_amu, masses_source
from eta_rxncat.thermo.modes import NormalModes, normal_modes
from eta_rxncat.thermo.rrho import thermochemistry
from eta_rxncat.thermo.symmetry import rotational_symmetry_number

__all__ = [
    "NormalModes",
    "NotAMinimumError",
    "ThermoError",
    "ThermoInputError",
    "atomic_masses_amu",
    "boltzmann",
    "check_ground_state",
    "masses_source",
    "normal_modes",
    "rotational_symmetry_number",
    "thermochemistry",
]
