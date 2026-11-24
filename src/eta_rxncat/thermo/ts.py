"""Transition-state validation and TS thermochemistry (v0.5.0, mission §5 "Validator and TS").

``validate_transition_state`` applies TJ's A2 gate ("Q2.  A": exactly one mode below
``-imag_tol_cm1``, that mode below ``cutoff_cm1``, mass-weighted active-core kinetic-energy
fraction >= 0.60) and the measured TS identity check of mission R3 (forming-stretch overlap,
in-phase forming bonds, forming distances in a window). Connectivity is never part of it.

``ts_thermochemistry`` is the minimum path's quasi-RRHO with the one imaginary mode excluded, sigma
from the TS's bond graph and no TS degeneracy (TJ Q-TJ2 "A"). The bonds are passed in: this module
imports neither ``eta_rxncat.mapping`` nor ``eta_rxncat.orchestrator``.
"""

from collections.abc import Sequence
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

from eta_rxncat.core import (
    MolecularState,
    ThermoAnalysisOptions,
    ThermoConfig,
    ThermoResult,
    TSValidation,
    TSValidationOptions,
)
from eta_rxncat.thermo.errors import ThermoInputError
from eta_rxncat.thermo.masses import atomic_masses_amu
from eta_rxncat.thermo.modes import normal_modes
from eta_rxncat.thermo.rrho import _thermochemistry
from eta_rxncat.thermo.symmetry import rotational_symmetry_number_from_bonds

IMAGINARY_MATCH_TOL_CM1 = 1e-6
"""Largest allowed difference between the validated and the recomputed imaginary frequency."""


class TSValidationInputError(ThermoInputError):
    """A validator input that cannot be judged (mission R16): empty sets, bad pairs, tolerances."""


def _checked_bonds(
    state: MolecularState, forming_bonds: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Return the forming bonds as sorted ``(min, max)`` pairs, or raise TSValidationInputError."""
    if not forming_bonds:
        raise TSValidationInputError(
            "no forming bonds given; a TS cannot be validated without them"
        )
    n_atoms = len(state.symbols)
    pairs: list[tuple[int, int]] = []
    for pair in forming_bonds:
        if (
            not isinstance(pair, Sequence)
            or len(pair) != 2
            or any(isinstance(a, bool) or not isinstance(a, int) for a in pair)
        ):
            raise TSValidationInputError(f"a forming bond must be two ints, not {pair!r}")
        i, j = pair
        if not (0 <= i < n_atoms and 0 <= j < n_atoms):
            raise TSValidationInputError(f"forming bond {pair!r} out of range for {n_atoms} atoms")
        if i == j:
            raise TSValidationInputError(f"forming bond {pair!r} joins an atom to itself")
        pairs.append((min(i, j), max(i, j)))
    if len(set(pairs)) != len(pairs):
        raise TSValidationInputError(f"duplicate forming bonds in {list(forming_bonds)}")
    return sorted(pairs)


def validate_transition_state(
    state: MolecularState,
    hessian_hartree_per_bohr2: ArrayLike,
    *,
    forming_bonds: Sequence[tuple[int, int]],
    options: TSValidationOptions | None = None,
    analysis: ThermoAnalysisOptions | None = None,
) -> TSValidation:
    """Judge whether ``state`` with its Cartesian Hessian is the intended first-order saddle.

    The reaction mode is the lowest-frequency normal mode. Its kinetic-energy fraction on the
    active atoms is ``sum_{a in active} m_a |d_a|^2 / sum_a m_a |d_a|^2`` (d the unit Cartesian
    displacement of ``normal_modes``, m from ``atomic_masses_amu``). Identity (R3): the overlap
    ``|<s, d>|`` with the unit forming stretch s (for each pair, -u on i and +u on j, u the unit
    i->j vector), every ``(d_j - d_i).u_ij`` of one sign, and every forming distance in the window.

    Args:
        state: The TS geometry (Angstrom); its ``active_atom_indices`` are the active core.
        hessian_hartree_per_bohr2: Cartesian Hessian (Eh/Bohr^2), 3N x 3N; not modified.
        forming_bonds: Pairs of atoms whose bond forms or breaks.
        options: The gate's thresholds.
        analysis: Normal-mode tolerances; ``imag_tol_cm1`` must equal ``options.imag_tol_cm1``.

    Raises:
        TSValidationInputError: An empty active set, no forming bonds, a bad pair, or
            ``options.imag_tol_cm1 != analysis.imag_tol_cm1``.
        ThermoInputError: If the Hessian or geometry cannot be analysed.
    """
    options = options if options is not None else TSValidationOptions()
    analysis = analysis if analysis is not None else ThermoAnalysisOptions()
    active = sorted(state.active_atom_indices)
    if not active:
        raise TSValidationInputError("state.active_atom_indices is empty")
    pairs = _checked_bonds(state, forming_bonds)
    if options.imag_tol_cm1 != analysis.imag_tol_cm1:
        raise TSValidationInputError(
            f"options.imag_tol_cm1 {options.imag_tol_cm1} != analysis.imag_tol_cm1 "
            f"{analysis.imag_tol_cm1}: the gate and the thermochemistry must agree"
        )
    modes = normal_modes(
        state.symbols, state.coordinates, hessian_hartree_per_bohr2, analysis=analysis
    )
    coords = np.asarray(state.coordinates, dtype=np.float64)
    units = {
        (i, j): (coords[j] - coords[i]) / np.linalg.norm(coords[j] - coords[i]) for i, j in pairs
    }
    distances = {f"{i}-{j}": float(np.linalg.norm(coords[j] - coords[i])) for i, j in pairs}
    frequencies = modes.frequencies_cm1
    n_imaginary = sum(1 for f in frequencies if f < -options.imag_tol_cm1)

    if n_imaginary == 0:
        return TSValidation(
            n_imaginary=0,
            imaginary_frequency_cm1=None,
            active_core_ke_fraction=None,
            forming_stretch_overlap=None,
            forming_bonds_in_phase_bool=None,
            forming_distances_angstrom=distances,
            options=options,
            active_atom_indices=active,
            mode_count_passed_bool=False,
            active_core_passed_bool=False,
            identity_passed_bool=False,
            passed_bool=False,
            reasons=["no_imaginary_mode"],
        )

    reasons: list[str] = []
    nu = float(frequencies[0])
    if n_imaginary > 1:
        reasons.append("multiple_imaginary_modes")
    if not nu < options.cutoff_cm1:
        reasons.append("imaginary_above_cutoff")
    mode_count_passed = n_imaginary == 1 and nu < options.cutoff_cm1

    d = modes.modes_cartesian[:, 0].reshape(-1, 3)
    weights = atomic_masses_amu(state.symbols) * np.sum(d * d, axis=1)
    fraction = float(weights[active].sum() / weights.sum())
    active_core_passed = fraction >= options.min_active_core_ke_fraction
    if not active_core_passed:
        reasons.append("active_core_fraction_below_threshold")

    stretch = np.zeros_like(coords)
    for (i, j), u in units.items():
        stretch[i] -= u
        stretch[j] += u
    stretch /= np.linalg.norm(stretch)
    overlap = float(abs(np.sum(stretch * d)))
    components = [float((d[j] - d[i]) @ u) for (i, j), u in units.items()]
    in_phase = all(c > 0.0 for c in components) or all(c < 0.0 for c in components)
    in_window = all(
        options.forming_distance_min_angstrom <= value <= options.forming_distance_max_angstrom
        for value in distances.values()
    )
    if overlap < options.min_forming_stretch_overlap:
        reasons.append("forming_overlap_below_threshold")
    if not in_phase:
        reasons.append("forming_bonds_out_of_phase")
    if not in_window:
        reasons.append("forming_distance_out_of_window")
    identity_passed = overlap >= options.min_forming_stretch_overlap and in_phase and in_window

    passed = mode_count_passed and active_core_passed and identity_passed
    return TSValidation(
        n_imaginary=n_imaginary,
        imaginary_frequency_cm1=nu,
        active_core_ke_fraction=fraction,
        forming_stretch_overlap=overlap,
        forming_bonds_in_phase_bool=in_phase,
        forming_distances_angstrom=distances,
        options=options,
        active_atom_indices=active,
        mode_count_passed_bool=mode_count_passed,
        active_core_passed_bool=active_core_passed,
        identity_passed_bool=identity_passed,
        passed_bool=passed,
        reasons=sorted(reasons),
    )


def ts_thermochemistry(
    state: MolecularState,
    hessian_hartree_per_bohr2: ArrayLike,
    electronic_energy_hartree: float,
    *,
    validation: TSValidation,
    bonds: Sequence[tuple[int, int]],
    energy_source: Literal["optimization", "single_point"],
    config: ThermoConfig | None = None,
    analysis: ThermoAnalysisOptions | None = None,
) -> ThermoResult:
    """Return the quasi-RRHO thermochemistry of a validated transition state.

    The one imaginary mode is excluded (as every imaginary mode is on the minimum path), sigma
    comes from ``bonds`` (the TS's perceived bond graph), and there is no TS degeneracy.

    Args:
        state: The TS geometry (Angstrom).
        hessian_hartree_per_bohr2: Cartesian Hessian (Eh/Bohr^2), 3N x 3N; not modified.
        electronic_energy_hartree: E (Eh).
        validation: The validator's verdict on this geometry and Hessian.
        bonds: The TS's bond graph, for sigma.
        energy_source: Where E comes from.
        config: Temperature, pressure, standard state and quasi-RRHO settings.
        analysis: Mode-classification and symmetry tolerances.

    Raises:
        ThermoInputError: The validation's mode count did not pass, or the recomputed imaginary
            list is not exactly the validated frequency (within 1e-6 cm^-1).
    """
    config = config if config is not None else ThermoConfig()
    analysis = analysis if analysis is not None else ThermoAnalysisOptions()
    if not validation.mode_count_passed_bool:
        raise ThermoInputError("ts_thermochemistry needs a validation whose mode count passed")
    sigma = rotational_symmetry_number_from_bonds(state, bonds, analysis=analysis)
    result = _thermochemistry(
        state,
        hessian_hartree_per_bohr2,
        electronic_energy_hartree,
        sigma,
        energy_source=energy_source,
        config=config,
        analysis=analysis,
    )
    imaginary = result.imaginary_frequencies_cm1
    expected = validation.imaginary_frequency_cm1
    if (
        len(imaginary) != 1
        or expected is None
        or abs(imaginary[0] - expected) > IMAGINARY_MATCH_TOL_CM1
    ):
        raise ThermoInputError(
            f"imaginary frequencies {imaginary} do not match the validated {expected} cm^-1"
        )
    return result
