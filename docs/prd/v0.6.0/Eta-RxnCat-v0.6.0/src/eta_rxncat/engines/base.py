"""Unified clean-room Potential energy, gradient, and Hessian protocol."""

from __future__ import annotations

import abc
import time
from typing import Protocol, runtime_checkable

import numpy as np

from eta_rxncat.core.models import MolecularState, PotentialResult, SolvationSpec

BOHR_TO_ANGSTROM = 0.529177210903
HARTREE_TO_KCAL_MOL = 627.5094740631


@runtime_checkable
class PotentialEngine(Protocol):
    """Protocol implemented by all classical, SQM, MLIP, and DFT calculators."""

    name: str

    def evaluate(
        self,
        state: MolecularState,
        *,
        compute_forces: bool = True,
        compute_hessian: bool = False,
    ) -> PotentialResult:
        ...


class BasePotentialEngine(abc.ABC):
    """Base helper providing timing, finite-difference Hessian fallback, and unit helpers."""

    name: str = "base"

    @abc.abstractmethod
    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        ...

    def evaluate(
        self,
        state: MolecularState,
        *,
        compute_forces: bool = True,
        compute_hessian: bool = False,
    ) -> PotentialResult:
        t0 = time.perf_counter()
        res = self._evaluate_impl(
            state,
            compute_forces=compute_forces,
            compute_hessian=compute_hessian,
        )
        res.wall_time_seconds = round(time.perf_counter() - t0, 4)
        return res

    def numerical_hessian(self, state: MolecularState, step_angstrom: float = 0.005) -> np.ndarray:
        """Central finite-difference Hessian in Hartree / Bohr^2 from analytical forces."""
        n_atoms = len(state.symbols)
        dof = 3 * n_atoms
        hess = np.zeros((dof, dof), dtype=np.float64)
        step_bohr = step_angstrom / BOHR_TO_ANGSTROM
        base_coords = state.coords_array()

        for idx in range(dof):
            atom_i, cart_i = divmod(idx, 3)
            c_plus = base_coords.copy()
            c_plus[atom_i, cart_i] += step_angstrom
            s_plus = state.model_copy(update={"coordinates": c_plus.tolist()})
            f_plus = np.asarray(
                self._evaluate_impl(s_plus, compute_forces=True, compute_hessian=False).forces_hartree_per_bohr,
                dtype=np.float64,
            ).reshape(-1)

            c_minus = base_coords.copy()
            c_minus[atom_i, cart_i] -= step_angstrom
            s_minus = state.model_copy(update={"coordinates": c_minus.tolist()})
            f_minus = np.asarray(
                self._evaluate_impl(s_minus, compute_forces=True, compute_hessian=False).forces_hartree_per_bohr,
                dtype=np.float64,
            ).reshape(-1)

            # Force = -dE/dR -> Hessian d^2E/dR^2 = -(F(R+h) - F(R-h)) / (2h)
            hess[:, idx] = -(f_plus - f_minus) / (2.0 * step_bohr)

        return 0.5 * (hess + hess.T)
