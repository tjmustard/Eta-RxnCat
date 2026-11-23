"""Thermochemistry contracts: analysis tolerances and the ``ThermoResult`` record (v0.3.0).

Data only: pydantic and the standard library, no numpy. ``eta_rxncat.thermo`` computes the
numbers; these models validate their shape and internal consistency and never change them.
"""

from typing import Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from eta_rxncat.core.models import CoreModel, PositiveFiniteFloat, PositiveInt, ThermoConfig

EntropyComponent = Literal["translational", "rotational", "vibrational", "electronic"]
"""The four entropy contributions every ``ThermoResult`` reports."""

ENTROPY_COMPONENTS: tuple[EntropyComponent, ...] = (
    "translational",
    "rotational",
    "vibrational",
    "electronic",
)

_ENTROPY_REL_TOL = 1e-12
_ENTROPY_ABS_FLOOR = 1e-30
_GIBBS_ABS_TOL_HARTREE = 1e-12


class ThermoAnalysisOptions(CoreModel):
    """Tolerances of the normal-mode and symmetry analysis behind a ``ThermoResult``.

    Not stored on their own (thermochemistry is derived); recorded in each ``ThermoResult``.

    Attributes:
        imag_tol_cm1: Frequencies below ``-imag_tol_cm1`` are imaginary modes; those in
            ``[-imag_tol_cm1, 0)`` are soft modes treated with ``|nu|``.
        sym_tol_angstrom: Distance tolerance of the rotational-symmetry search (Angstrom).
        linear_tol_angstrom: Largest distance of any atom from the molecular axis for which the
            molecule counts as linear (Angstrom).
        max_automorphisms: Cap on graph automorphisms enumerated; reaching it is an error.
    """

    imag_tol_cm1: PositiveFiniteFloat = 20.0
    sym_tol_angstrom: PositiveFiniteFloat = 0.05
    linear_tol_angstrom: PositiveFiniteFloat = 1e-3
    max_automorphisms: PositiveInt = 100000


class ThermoResult(CoreModel):
    """Thermochemistry of one stationary geometry, in Hartree, Hartree/K and cm^-1.

    There is deliberately no ground-state flag: ``eta_rxncat.thermo.check_ground_state`` raises
    ``NotAMinimumError`` listing the imaginary modes.

    Attributes:
        n_atoms: Number of atoms.
        electronic_energy_hartree: Electronic energy E (Eh).
        energy_source: Whether E comes from the optimization or a separate single point.
        zpe_hartree: Zero-point energy (Eh).
        thermal_correction_enthalpy_hartree: H - E, ZPE included (Eh).
        thermal_correction_gibbs_hartree: G - E, ZPE and the standard-state correction included.
        entropy_hartree_per_k: Total entropy (Eh/K).
        entropy_components_hartree_per_k: Exactly the four ``ENTROPY_COMPONENTS``, summing to the
            total.
        gibbs_free_energy_hartree: G = E + ``thermal_correction_gibbs_hartree`` (Eh).
        standard_state_correction_hartree: The 1 atm -> standard-state correction inside G (Eh).
        frequencies_cm1: All 3N-6 (3N-5 if linear, 0 if N = 1) frequencies, ascending,
            imaginary ones negative.
        imaginary_frequencies_cm1: Exactly the frequencies below ``-analysis.imag_tol_cm1``.
        soft_modes_cm1: Exactly the frequencies in ``[-analysis.imag_tol_cm1, 0)``.
        rotational_symmetry_number: Rotational symmetry number sigma.
        is_linear: Whether the molecule is linear (always for N = 2, never for N = 1).
        config: The thermochemistry settings used.
        analysis: The analysis tolerances used.
        masses_source: Where the atomic masses came from.
    """

    n_atoms: PositiveInt
    electronic_energy_hartree: FiniteFloat
    energy_source: Literal["optimization", "single_point"]
    zpe_hartree: FiniteFloat
    thermal_correction_enthalpy_hartree: FiniteFloat
    thermal_correction_gibbs_hartree: FiniteFloat
    entropy_hartree_per_k: FiniteFloat
    entropy_components_hartree_per_k: dict[EntropyComponent, FiniteFloat]
    gibbs_free_energy_hartree: FiniteFloat
    standard_state_correction_hartree: FiniteFloat
    frequencies_cm1: list[FiniteFloat]
    imaginary_frequencies_cm1: list[FiniteFloat]
    soft_modes_cm1: list[FiniteFloat]
    rotational_symmetry_number: PositiveInt
    is_linear: bool
    config: ThermoConfig
    analysis: ThermoAnalysisOptions
    masses_source: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_thermo(self) -> Self:
        self._check_entropy()
        self._check_frequencies()
        expected_g = self.electronic_energy_hartree + self.thermal_correction_gibbs_hartree
        if abs(self.gibbs_free_energy_hartree - expected_g) > _GIBBS_ABS_TOL_HARTREE:
            raise ValueError(
                f"gibbs_free_energy_hartree {self.gibbs_free_energy_hartree!r} != "
                f"electronic_energy_hartree + thermal_correction_gibbs_hartree ({expected_g!r})"
            )
        return self

    def _check_entropy(self) -> None:
        components = self.entropy_components_hartree_per_k
        missing = [key for key in ENTROPY_COMPONENTS if key not in components]
        if missing:
            raise ValueError(f"entropy_components_hartree_per_k is missing {missing}")
        total = sum(components[key] for key in ENTROPY_COMPONENTS)
        tolerance = max(_ENTROPY_REL_TOL * abs(self.entropy_hartree_per_k), _ENTROPY_ABS_FLOOR)
        if abs(total - self.entropy_hartree_per_k) > tolerance:
            raise ValueError(
                f"entropy components sum to {total!r}, not entropy_hartree_per_k "
                f"{self.entropy_hartree_per_k!r}"
            )

    def _check_frequencies(self) -> None:
        n = self.n_atoms
        if n == 1 and self.is_linear:
            raise ValueError("a single atom is not linear")
        if n == 2 and not self.is_linear:
            raise ValueError("a diatomic must be linear")
        if n == 1:
            expected = 0
        else:
            expected = 3 * n - 5 if self.is_linear else 3 * n - 6
        freqs = self.frequencies_cm1
        if len(freqs) != expected:
            shape = "linear" if self.is_linear else "non-linear"
            raise ValueError(
                f"{len(freqs)} frequencies for a {shape} molecule of {n} atoms, expected {expected}"
            )
        if any(a > b for a, b in zip(freqs, freqs[1:], strict=False)):
            raise ValueError("frequencies_cm1 is not ascending")
        tol = self.analysis.imag_tol_cm1
        imaginary = [f for f in freqs if f < -tol]
        if self.imaginary_frequencies_cm1 != imaginary:
            raise ValueError(
                f"imaginary_frequencies_cm1 {self.imaginary_frequencies_cm1} != the frequencies "
                f"below -{tol} cm^-1 {imaginary}"
            )
        soft = [f for f in freqs if -tol <= f < 0]
        if self.soft_modes_cm1 != soft:
            raise ValueError(
                f"soft_modes_cm1 {self.soft_modes_cm1} != the frequencies in [-{tol}, 0) {soft}"
            )
