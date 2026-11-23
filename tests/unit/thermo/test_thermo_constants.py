"""Tests for eta_rxncat.thermo.constants and the masses table (v0.3.0 slice 03, R1, H9)."""

import math

import pytest

from eta_rxncat.core import ELEMENT_SYMBOLS
from eta_rxncat.engines import units
from eta_rxncat.thermo import ThermoInputError, atomic_masses_amu, masses_source
from eta_rxncat.thermo import constants as c


def test_hartree_kcal_mol_derived_from_codata() -> None:
    """engines.units.HARTREE_KCAL_MOL = E_h N_A / (1000 cal) within 1e-12 relative."""
    derived = c.HARTREE_J * c.N_AVOGADRO / (1000.0 * c.CAL_J)
    assert math.isclose(derived, units.HARTREE_KCAL_MOL, rel_tol=1e-12, abs_tol=0.0)


def test_bohr_angstrom_derived_from_codata() -> None:
    """engines.units.BOHR_ANGSTROM = a0 / 1e-10 m within 1e-12 relative."""
    assert math.isclose(c.BOHR_M * 1e10, units.BOHR_ANGSTROM, rel_tol=1e-12, abs_tol=0.0)


def test_exact_si_constants() -> None:
    """The 2019 SI exact constants and R = N_A k_B."""
    assert c.H_PLANCK == 6.62607015e-34
    assert c.K_BOLTZMANN == 1.380649e-23
    assert c.C_LIGHT == 299792458.0
    assert c.N_AVOGADRO == 6.02214076e23
    assert c.E_CHARGE == 1.602176634e-19
    assert c.R_GAS == c.N_AVOGADRO * c.K_BOLTZMANN
    assert math.isclose(c.R_GAS, 8.314462618, rel_tol=1e-9)


def test_eigenvalue_conversion() -> None:
    """sqrt(1 Eh/(Bohr^2 amu)) is 5140.487 cm^-1 (CODATA 2018)."""
    assert math.isclose(c.EIGENVALUE_TO_CM1, 5140.4871, rel_tol=1e-7)


@pytest.mark.parametrize("symbol", ELEMENT_SYMBOLS)
def test_mass_exists_for_every_element(symbol: str) -> None:
    """H9: RDKit has a positive most-common-isotope mass for every Z 1-118."""
    (mass,) = atomic_masses_amu([symbol])
    assert mass > 0.0


def test_element_table_is_z_1_to_118() -> None:
    """The loop above covers exactly the 118 canonical symbols."""
    assert len(ELEMENT_SYMBOLS) == 118


def test_known_masses_and_source() -> None:
    """H, C and Pd masses as recorded by RDKit 2026.09.2; masses_source names RDKit."""
    h, carbon, pd = atomic_masses_amu(["H", "C", "Pd"])
    assert h == pytest.approx(1.007825032, abs=1e-9)
    assert carbon == 12.0
    assert pd == pytest.approx(105.903486, abs=1e-6)
    assert masses_source().startswith("rdkit ")
    assert masses_source().endswith(" most-common-isotope")


def test_unknown_symbol_has_no_default_mass() -> None:
    """A symbol RDKit does not know raises; nothing defaults to 12 amu (DV-05)."""
    with pytest.raises(ThermoInputError):
        atomic_masses_amu(["Xx"])
