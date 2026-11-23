"""Atomic masses from RDKit's most-common-isotope table (Z 1-118, no fallback)."""

from collections.abc import Sequence

import numpy as np
import rdkit
from numpy.typing import NDArray
from rdkit import Chem

from eta_rxncat.thermo.errors import ThermoInputError


def masses_source() -> str:
    """Return the ``masses_source`` text recorded in every ``ThermoResult``."""
    return f"rdkit {rdkit.__version__} most-common-isotope"


def atomic_masses_amu(symbols: Sequence[str]) -> NDArray[np.float64]:
    """Return the most-common-isotope mass (amu) of each symbol.

    Args:
        symbols: Element symbols.

    Returns:
        One mass per symbol.

    Raises:
        ThermoInputError: If RDKit has no positive mass for a symbol.
    """
    table = Chem.GetPeriodicTable()
    masses: list[float] = []
    for symbol in symbols:
        try:
            mass = float(table.GetMostCommonIsotopeMass(symbol))
        except RuntimeError as exc:
            raise ThermoInputError(f"no RDKit mass for element {symbol!r}") from exc
        if not mass > 0.0:
            raise ThermoInputError(f"RDKit mass for element {symbol!r} is {mass!r}, not > 0")
        masses.append(mass)
    return np.asarray(masses, dtype=np.float64)
