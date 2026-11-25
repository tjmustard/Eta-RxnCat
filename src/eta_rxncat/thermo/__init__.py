"""Ideal-gas quasi-RRHO thermochemistry from Cartesian Hessians (v0.3.0) and TS validation (v0.5.0).

numpy and RDKit are imported here, never in ``eta_rxncat.core``. The names that need RDKit load
on first use (PEP 562, mission R26), so ``eta_rxncat.thermo.constants`` and ``boltzmann`` import
without it. The API is unchanged: ``__all__`` and every ``from eta_rxncat.thermo import X`` hold.
``boltzmann`` stays imported here, not lazily: the function shares its name with its submodule.
"""

import importlib
from typing import TYPE_CHECKING, Any

from eta_rxncat.thermo.boltzmann import boltzmann
from eta_rxncat.thermo.errors import (
    NotAMinimumError,
    ThermoError,
    ThermoInputError,
    check_ground_state,
)

if TYPE_CHECKING:
    from eta_rxncat.thermo.masses import atomic_masses_amu, masses_source
    from eta_rxncat.thermo.modes import NormalModes, normal_modes
    from eta_rxncat.thermo.rrho import thermochemistry
    from eta_rxncat.thermo.symmetry import (
        rotational_symmetry_number,
        rotational_symmetry_number_from_bonds,
    )
    from eta_rxncat.thermo.ts import (
        TSValidationInputError,
        ts_thermochemistry,
        validate_transition_state,
    )

_LAZY: dict[str, str] = {
    "NormalModes": "modes",
    "TSValidationInputError": "ts",
    "atomic_masses_amu": "masses",
    "masses_source": "masses",
    "normal_modes": "modes",
    "rotational_symmetry_number": "symmetry",
    "rotational_symmetry_number_from_bonds": "symmetry",
    "thermochemistry": "rrho",
    "ts_thermochemistry": "ts",
    "validate_transition_state": "ts",
}
"""Public name -> the submodule that defines it, for the names loaded on first use."""


def __getattr__(name: str) -> Any:
    """Load a lazily exported name from its submodule and cache it on the package."""
    submodule = _LAZY.get(name)
    if submodule is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f"{__name__}.{submodule}"), name)
    globals()[name] = value
    return value


__all__ = [
    "NormalModes",
    "NotAMinimumError",
    "ThermoError",
    "ThermoInputError",
    "TSValidationInputError",
    "atomic_masses_amu",
    "boltzmann",
    "check_ground_state",
    "masses_source",
    "normal_modes",
    "rotational_symmetry_number",
    "rotational_symmetry_number_from_bonds",
    "thermochemistry",
    "ts_thermochemistry",
    "validate_transition_state",
]
