"""CODATA 2018 constants and the unit conversions thermochemistry needs (R1).

``eta_rxncat.engines.units`` keeps its own two engine conversions; ``tests/unit/thermo`` derives
them from the constants here so the two modules cannot drift apart.
"""

import math
from typing import Final

H_PLANCK: Final = 6.62607015e-34
"""Planck constant (J s, exact)."""

K_BOLTZMANN: Final = 1.380649e-23
"""Boltzmann constant (J/K, exact)."""

C_LIGHT: Final = 299792458.0
"""Speed of light in vacuum (m/s, exact)."""

N_AVOGADRO: Final = 6.02214076e23
"""Avogadro constant (1/mol, exact)."""

E_CHARGE: Final = 1.602176634e-19
"""Elementary charge (C, exact)."""

AMU_KG: Final = 1.66053906660e-27
"""Atomic mass constant (kg)."""

HARTREE_J: Final = 4.3597447222071e-18
"""Hartree energy (J)."""

BOHR_M: Final = 0.529177210903e-10
"""Bohr radius (m)."""

CAL_J: Final = 4.184
"""Thermochemical calorie (J)."""

ATM_PA: Final = 101325.0
"""Standard atmosphere (Pa)."""

R_GAS: Final = N_AVOGADRO * K_BOLTZMANN
"""Molar gas constant (J/(mol K))."""

ANGSTROM_M: Final = 1.0e-10
"""One Angstrom (m)."""

J_PER_MOL_TO_HARTREE: Final = 1.0 / (HARTREE_J * N_AVOGADRO)
"""Factor from J/mol to Hartree per molecule."""

EIGENVALUE_TO_CM1: Final = math.sqrt(HARTREE_J / (BOHR_M**2 * AMU_KG)) / (
    2.0 * math.pi * C_LIGHT * 100.0
)
"""Factor from sqrt(eigenvalue in Eh/(Bohr^2 amu)) to a wavenumber in cm^-1."""

CM1_TO_HZ: Final = C_LIGHT * 100.0
"""Factor from a wavenumber in cm^-1 to a frequency in Hz."""
