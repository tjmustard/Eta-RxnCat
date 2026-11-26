"""Transition-state contracts: the P-RFO search, its validation and the TS record (v0.5.0).

Data only: pydantic and the standard library, no numpy and no optimizer imports. A TS is its own
record (mission R1): nothing here is added to ``OptimizationResult`` or ``ConformerRecord``.
"""

import re
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    FiniteFloat,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from eta_rxncat.core.models import (
    CoreModel,
    MolecularState,
    NonNegativeInt,
    PositiveFiniteFloat,
    ScalarValue,
)
from eta_rxncat.core.optimization_models import OptimizerIdentity
from eta_rxncat.core.results import HessianMethod, NonNegativeFiniteFloat
from eta_rxncat.core.thermo_models import ThermoResult

TS_VALIDATION_REASONS: frozenset[str] = frozenset(
    {
        "active_core_fraction_below_threshold",
        "forming_bonds_out_of_phase",
        "forming_distance_out_of_window",
        "forming_overlap_below_threshold",
        "imaginary_above_cutoff",
        "multiple_imaginary_modes",
        "no_imaginary_mode",
    }
)
"""Every reason a ``TSValidation`` may give for failing."""

UnitInterval = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
"""A finite float in [0, 1]."""

_PAIR_KEY = re.compile(r"^(0|[1-9][0-9]*)-(0|[1-9][0-9]*)$")


def _strictly_true(value: object) -> object:
    # Literal[True] alone accepts 1 and 1.0 (they compare equal to True).
    if value is not True:
        raise ValueError(f"converged must be True, not {value!r}")
    return value


def _check_sorted_unique(name: str, values: list[int]) -> None:
    """Raise unless ``values`` is strictly ascending (sorted, no duplicates)."""
    if any(a >= b for a, b in zip(values, values[1:], strict=False)):
        raise ValueError(f"{name} must be sorted and unique, got {values}")


class FormingBond(CoreModel):
    """A pair of atoms whose bond forms or breaks along the reaction (0-based, ``i < j``).

    Attributes:
        i: The lower atom index.
        j: The higher atom index.
    """

    i: NonNegativeInt
    j: NonNegativeInt

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.i >= self.j:
            raise ValueError(f"forming bond needs i < j, got i={self.i}, j={self.j}")
        return self


class TSStep(CoreModel):
    """One P-RFO iteration, accepted or rejected.

    Attributes:
        step: The step label, 0-based and equal to its position in the history.
        accepted_bool: Whether the step was accepted.
        energy_hartree: Energy at the step's geometry (Eh).
        max_gradient_hartree_per_bohr: Largest gradient component (Eh/Bohr).
        trust_radius_bohr: Trust radius in force for the step (Bohr).
        followed_eigenvalue_hartree_per_bohr2: Eigenvalue of the followed mode (Eh/Bohr^2).
        mode_overlap: |overlap| of the followed mode with the previous one, in [0, 1]; ``None``
            at step 0.
        hessian_source: Whether the step's Hessian was exact or a Bofill update.
        ratio: Actual over predicted energy change; ``None`` when not computed.
        coordinates_angstrom: The step's geometry (v0.7.0); ``None`` when not captured, and then
            left out of the serialised form.
    """

    step: NonNegativeInt
    accepted_bool: bool
    energy_hartree: FiniteFloat
    max_gradient_hartree_per_bohr: NonNegativeFiniteFloat
    trust_radius_bohr: PositiveFiniteFloat
    followed_eigenvalue_hartree_per_bohr2: FiniteFloat
    mode_overlap: UnitInterval | None
    hessian_source: Literal["exact", "bofill"]
    ratio: FiniteFloat | None
    coordinates_angstrom: list[list[FiniteFloat]] | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_coordinates(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # A step without coordinates must serialise exactly as in v0.6.0.
        data: dict[str, Any] = handler(self)
        if self.coordinates_angstrom is None:
            data.pop("coordinates_angstrom", None)
        return data


class TSSearchResult(CoreModel):
    """A converged transition-state search; a failed search raises instead of returning.

    ``history`` is diagnostic and never compared between runs (mission R20). The followed
    eigenvalue is recorded, not judged: whether the result is a first-order saddle is decided by
    ``TSValidation`` from the final Hessian.

    Attributes:
        final_state: The saddle-point structure.
        final_energy_hartree: Energy of ``final_state`` (Eh).
        converged: Always ``True``.
        n_steps: Iterations taken.
        n_gradient_calls: Engine gradient evaluations.
        n_hessian_calls: Engine Hessian evaluations.
        n_hessian_refreshes: Exact Hessian refreshes after the first.
        n_rejected_steps: Steps rejected by the trust-region test.
        hessian_method: How the engine computed its Hessians.
        followed_eigenvalue_hartree_per_bohr2: Followed-mode eigenvalue at the end (Eh/Bohr^2).
        final_max_gradient_hartree_per_bohr: Largest gradient component at the end (Eh/Bohr).
        final_rms_gradient_hartree_per_bohr: RMS gradient at the end (Eh/Bohr).
        final_rigid_gradient_norm_hartree_per_bohr: Norm of the gradient's rigid-motion part at
            the end (Eh/Bohr).
        forming_bonds: The followed bonds, sorted by ``(i, j)``, unique, in range.
        optimizer: The optimizer name and version.
        options: The resolved optimizer options.
        history: Every step in order; ``history[k].step == k``. Never compared.
    """

    final_state: MolecularState
    final_energy_hartree: FiniteFloat
    converged: Literal[True]
    n_steps: NonNegativeInt
    n_gradient_calls: NonNegativeInt
    n_hessian_calls: NonNegativeInt
    n_hessian_refreshes: NonNegativeInt
    n_rejected_steps: NonNegativeInt
    hessian_method: HessianMethod
    followed_eigenvalue_hartree_per_bohr2: FiniteFloat
    final_max_gradient_hartree_per_bohr: NonNegativeFiniteFloat
    final_rms_gradient_hartree_per_bohr: NonNegativeFiniteFloat
    final_rigid_gradient_norm_hartree_per_bohr: NonNegativeFiniteFloat
    forming_bonds: list[FormingBond]
    optimizer: OptimizerIdentity
    options: dict[str, ScalarValue]
    history: list[TSStep]

    @field_validator("converged", mode="before")
    @classmethod
    def _strict_converged(cls, value: object) -> object:
        return _strictly_true(value)

    @model_validator(mode="after")
    def _check_search(self) -> Self:
        pairs = [(bond.i, bond.j) for bond in self.forming_bonds]
        if any(a >= b for a, b in zip(pairs, pairs[1:], strict=False)):
            raise ValueError(f"forming_bonds must be sorted by (i, j) and unique, got {pairs}")
        n_atoms = len(self.final_state.symbols)
        out_of_range = [pair for pair in pairs if pair[1] >= n_atoms]
        if out_of_range:
            raise ValueError(f"forming_bonds {out_of_range} out of range for {n_atoms} atoms")
        misplaced = [k for k, step in enumerate(self.history) if step.step != k]
        if misplaced:
            raise ValueError(f"history positions {misplaced} do not match their step labels")
        return self


class TSValidationOptions(CoreModel):
    """Thresholds of the transition-state validator.

    The mode-count and active-core numbers are TJ's A2 ("Q2.  A"); the identity numbers are the
    measured checks of mission R3.

    Attributes:
        imag_tol_cm1: Frequencies below ``-imag_tol_cm1`` count as imaginary modes.
        cutoff_cm1: The one imaginary mode must lie below this frequency.
        min_active_core_ke_fraction: Least kinetic-energy fraction of the imaginary mode on the
            active atoms, in (0, 1].
        min_forming_stretch_overlap: Least overlap of the imaginary mode with the forming-bond
            stretch, in (0, 1].
        forming_distance_min_angstrom: Shortest allowed forming-bond distance (Angstrom).
        forming_distance_max_angstrom: Longest allowed forming-bond distance (Angstrom).
    """

    imag_tol_cm1: PositiveFiniteFloat = 20.0
    cutoff_cm1: FiniteFloat = -50.0
    min_active_core_ke_fraction: FiniteFloat = 0.60
    min_forming_stretch_overlap: FiniteFloat = 0.50
    forming_distance_min_angstrom: PositiveFiniteFloat = 1.90
    forming_distance_max_angstrom: PositiveFiniteFloat = 2.90

    @model_validator(mode="after")
    def _check_thresholds(self) -> Self:
        if not self.cutoff_cm1 < -self.imag_tol_cm1:
            raise ValueError(
                f"cutoff_cm1 {self.cutoff_cm1} must be below -imag_tol_cm1 ({-self.imag_tol_cm1})"
            )
        for name in ("min_active_core_ke_fraction", "min_forming_stretch_overlap"):
            value = getattr(self, name)
            if not 0.0 < value <= 1.0:
                raise ValueError(f"{name} {value} must be in (0, 1]")
        if not self.forming_distance_min_angstrom < self.forming_distance_max_angstrom:
            raise ValueError(
                f"forming_distance_min_angstrom {self.forming_distance_min_angstrom} must be below "
                f"forming_distance_max_angstrom {self.forming_distance_max_angstrom}"
            )
        return self


class TSValidation(CoreModel):
    """The verdict of the transition-state validator on one final Hessian.

    Attributes:
        n_imaginary: Number of modes below ``-options.imag_tol_cm1``.
        imaginary_frequency_cm1: The lowest imaginary frequency; ``None`` without one.
        active_core_ke_fraction: The imaginary mode's kinetic-energy fraction on the active
            atoms; ``None`` without an imaginary mode.
        forming_stretch_overlap: Overlap of the imaginary mode with the forming-bond stretch;
            ``None`` without an imaginary mode.
        forming_bonds_in_phase_bool: Whether every forming bond stretches in phase; ``None`` when
            not evaluated.
        forming_distances_angstrom: Forming-bond distances keyed ``"i-j"`` (``i < j``, Angstrom).
        options: The thresholds used.
        active_atom_indices: The active atoms, sorted, unique, non-empty.
        mode_count_passed_bool: Exactly one imaginary mode, below ``options.cutoff_cm1``.
        active_core_passed_bool: The active-core fraction meets its threshold.
        identity_passed_bool: The forming-bond identity checks pass (mission R3).
        passed_bool: All three checks pass.
        reasons: Why it failed, sorted, unique, from ``TS_VALIDATION_REASONS``; empty iff passed.
    """

    n_imaginary: NonNegativeInt
    imaginary_frequency_cm1: FiniteFloat | None
    active_core_ke_fraction: FiniteFloat | None
    forming_stretch_overlap: FiniteFloat | None
    forming_bonds_in_phase_bool: bool | None
    forming_distances_angstrom: dict[str, PositiveFiniteFloat]
    options: TSValidationOptions
    active_atom_indices: list[NonNegativeInt] = Field(min_length=1)
    mode_count_passed_bool: bool
    active_core_passed_bool: bool
    identity_passed_bool: bool
    passed_bool: bool
    reasons: list[str]

    @model_validator(mode="after")
    def _check_validation(self) -> Self:
        _check_sorted_unique("active_atom_indices", self.active_atom_indices)
        for key in self.forming_distances_angstrom:
            match = _PAIR_KEY.match(key)
            if match is None or int(match.group(1)) >= int(match.group(2)):
                raise ValueError(f"forming_distances_angstrom key {key!r} is not 'i-j' with i < j")
        checks = (
            self.mode_count_passed_bool,
            self.active_core_passed_bool,
            self.identity_passed_bool,
        )
        all_passed = all(checks)
        if self.passed_bool != all_passed:
            raise ValueError(
                f"passed_bool {self.passed_bool} disagrees with the three checks ({all_passed})"
            )
        if self.reasons != sorted(set(self.reasons)):
            raise ValueError(f"reasons must be sorted and unique, got {self.reasons}")
        unknown = sorted(set(self.reasons) - TS_VALIDATION_REASONS)
        if unknown:
            raise ValueError(f"unknown reasons: {unknown}")
        if self.passed_bool == bool(self.reasons):
            raise ValueError("reasons must be empty exactly when passed_bool is true")
        if self.n_imaginary == 0:
            given = [
                name
                for name in (
                    "imaginary_frequency_cm1",
                    "active_core_ke_fraction",
                    "forming_stretch_overlap",
                )
                if getattr(self, name) is not None
            ]
            if given:
                raise ValueError(f"no imaginary mode, but {given} are set")
        return self


class TransitionStateRecord(CoreModel):
    """A validated transition state: search, validation and thermochemistry of one saddle.

    Attributes:
        ts_id: Identifier of the transition state.
        state: The TS structure; equal to ``search.final_state``.
        search: The P-RFO search that found it.
        validation: The validator's verdict; its mode count must have passed.
        thermo: Thermochemistry with exactly one imaginary mode listed.
        degeneracy: Always 1: no enantiomeric-TS degeneracy (TJ Q-TJ2 "A").
    """

    ts_id: str = Field(min_length=1)
    state: MolecularState
    search: TSSearchResult
    validation: TSValidation
    thermo: ThermoResult
    degeneracy: Literal[1]

    @field_validator("degeneracy", mode="before")
    @classmethod
    def _strict_degeneracy(cls, value: object) -> object:
        # Literal[1] alone would accept True and 1.0.
        if type(value) is not int or value != 1:
            raise ValueError(f"degeneracy must be the integer 1, not {value!r}")
        return value

    @model_validator(mode="after")
    def _check_record(self) -> Self:
        if not self.validation.mode_count_passed_bool:
            raise ValueError("a TS record needs a validation whose mode count passed")
        n_imaginary = len(self.thermo.imaginary_frequencies_cm1)
        if n_imaginary != 1:
            raise ValueError(f"thermo lists {n_imaginary} imaginary modes, expected exactly 1")
        final = self.search.final_state
        for name in ("symbols", "charge", "spin_multiplicity", "coordinates"):
            if getattr(self.state, name) != getattr(final, name):
                raise ValueError(f"state.{name} differs from search.final_state.{name}")
        return self
