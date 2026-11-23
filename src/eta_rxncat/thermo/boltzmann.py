"""Boltzmann weights and ensemble free energy by log-sum-exp, with degeneracies (DV-12)."""

import math
import numbers
from collections.abc import Sequence

from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS
from eta_rxncat.thermo.errors import ThermoInputError


def boltzmann(
    gibbs_hartree: Sequence[float], degeneracies: Sequence[int], temperature_k: float
) -> tuple[list[float], float]:
    """Return the Boltzmann weights and the ensemble free energy.

    Weights are proportional to ``g_i exp(-G_i / RT)`` and ``G_ens = -RT ln sum g_i exp(-G_i/RT)``,
    both evaluated relative to the lowest G with log-sum-exp, so no exponent overflows.

    Args:
        gibbs_hartree: Free energy of each conformer (Eh).
        degeneracies: Degeneracy of each conformer (positive integers).
        temperature_k: Temperature (K).

    Returns:
        The weights (summing to 1) and ``G_ens`` (Eh).

    Raises:
        ThermoInputError: On empty input, a length mismatch, a non-finite G, a non-positive
            degeneracy or temperature.
    """
    if not gibbs_hartree:
        raise ThermoInputError("boltzmann needs at least one free energy")
    if len(gibbs_hartree) != len(degeneracies):
        raise ThermoInputError(
            f"{len(gibbs_hartree)} free energies but {len(degeneracies)} degeneracies"
        )
    if not all(math.isfinite(g) for g in gibbs_hartree):
        raise ThermoInputError(f"non-finite free energy in {list(gibbs_hartree)}")
    bad = [
        g
        for g in degeneracies
        if isinstance(g, bool) or not isinstance(g, numbers.Integral) or g < 1
    ]
    if bad:
        raise ThermoInputError(f"degeneracies must be positive integers, got {bad}")
    if not (math.isfinite(temperature_k) and temperature_k > 0):
        raise ThermoInputError(f"temperature_k must be finite and > 0, got {temperature_k!r}")
    rt = R_GAS * temperature_k * J_PER_MOL_TO_HARTREE
    g_min = min(gibbs_hartree)
    exponents = [
        math.log(g) - (gi - g_min) / rt for gi, g in zip(gibbs_hartree, degeneracies, strict=True)
    ]
    top = max(exponents)
    terms = [math.exp(a - top) for a in exponents]
    total = math.fsum(terms)
    weights = [t / total for t in terms]
    g_ens = g_min - rt * (top + math.log(total))
    return weights, g_ens
