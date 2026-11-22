"""CODATA 2018 unit constants and conversions used by every engine (mission §5 Units)."""

from typing import Final

BOHR_ANGSTROM: Final = 0.529177210903
"""One Bohr in Angstrom (CODATA 2018)."""

HARTREE_EV: Final = 27.211386245988
"""One Hartree in eV (CODATA 2018)."""

HARTREE_KCAL_MOL: Final = 627.5094740631
"""One Hartree in kcal/mol (CODATA 2018, via the thermochemical calorie)."""


def angstrom_to_bohr(value: float) -> float:
    """Convert a length from Angstrom to Bohr."""
    return value / BOHR_ANGSTROM


def bohr_to_angstrom(value: float) -> float:
    """Convert a length from Bohr to Angstrom."""
    return value * BOHR_ANGSTROM


def ev_to_hartree(value: float) -> float:
    """Convert an energy from eV to Hartree."""
    return value / HARTREE_EV


def kcal_mol_to_hartree(value: float) -> float:
    """Convert an energy from kcal/mol to Hartree."""
    return value / HARTREE_KCAL_MOL


def ev_per_angstrom_to_hartree_per_bohr(value: float) -> float:
    """Convert a force or gradient component from eV/Angstrom to Hartree/Bohr."""
    return value * BOHR_ANGSTROM / HARTREE_EV


def kcal_mol_per_angstrom_to_hartree_per_bohr(value: float) -> float:
    """Convert a force or gradient component from kcal/(mol Angstrom) to Hartree/Bohr."""
    return value * BOHR_ANGSTROM / HARTREE_KCAL_MOL
