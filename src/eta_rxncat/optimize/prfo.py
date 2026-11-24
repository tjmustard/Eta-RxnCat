"""Clean-room Cartesian partitioned-RFO transition-state search (v0.5.0, mission §5 "P-RFO").

Written from the methods of Banerjee, Adams, Simons & Shepard, J. Phys. Chem. 1985, 89, 52
(partitioned rational-function optimisation), Baker, J. Comput. Chem. 1986, 7, 385 (P-RFO for
transition states, eigenvector following) and Bofill, J. Comput. Chem. 1994, 15, 1 (the Hessian
update), and the slice specification; no other implementation was consulted (TJ A1).

Coordinates are unweighted Cartesian, in Bohr (mission R7). Rigid motions are projected out with
the orthonormal complement C of the three translations and the three rotations about the
geometric centroid; no masses are used. The search starts from an exact engine Hessian, updates it
with Bofill's formula between exact refreshes, and follows one mode uphill with a trust radius.
"""

import functools
import hashlib
import math
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import ClassVar

import numpy as np
import numpy.typing as npt

from eta_rxncat.core import (
    FormingBond,
    MolecularState,
    OptimizerIdentity,
    PotentialResult,
    TSSearchResult,
    TSStep,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.core.results import HessianMethod
from eta_rxncat.engines import Engine, OptionSpec
from eta_rxncat.engines.units import BOHR_ANGSTROM
from eta_rxncat.optimize.errors import (
    OptimizerInputError,
    TSSearchFailedError,
    TSSearchFailureReason,
)
from eta_rxncat.optimize.ts_base import TransitionStateOptimizer

Vector = npt.NDArray[np.float64]
Matrix = npt.NDArray[np.float64]

_RIGID_RANK_RTOL = 1e-8
"""Singular values of the rigid basis below this fraction of the largest count as zero."""

_ROOT_TOL = 1e-12
"""Bracket width at which the lambda_n root counts as converged (Eh/Bohr^2)."""

_ROOT_MAX_ITERATIONS = 200

_BOFILL_PSB_RTOL = 1e-12
"""Below ``|r.s| < _BOFILL_PSB_RTOL * |r| |s|`` the update is PSB alone."""


@functools.cache
def _source_identity() -> OptimizerIdentity:
    """Return the identity keyed by this module's source bytes (mission R11)."""
    digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return OptimizerIdentity(name="prfo", version="src-" + digest[:16])


def rigid_complement(x_bohr: Vector) -> tuple[Matrix, int]:
    """Return the orthonormal complement of the rigid motions at ``x_bohr`` and their rank.

    The rigid basis is the three unit translations and the three infinitesimal rotations
    ``e_a x (r_k - centroid)`` about the unweighted geometric centroid, orthonormalised by SVD.

    Args:
        x_bohr: Flat Cartesian coordinates (3N,), Bohr.

    Returns:
        ``(C, rank)``: C is 3N x (3N - 6) with orthonormal columns orthogonal to every rigid
        motion (for a linear structure, rank < 6 and C is not meaningful).
    """
    positions = x_bohr.reshape(-1, 3)
    centered = positions - positions.mean(axis=0)
    n_coords = x_bohr.size
    basis = np.zeros((n_coords, 6))
    for axis in range(3):
        basis[axis::3, axis] = 1.0
        unit = np.zeros(3)
        unit[axis] = 1.0
        basis[:, 3 + axis] = np.cross(unit, centered).ravel()
    left, singular, _ = np.linalg.svd(basis, full_matrices=True)
    rank = int(np.count_nonzero(singular > _RIGID_RANK_RTOL * singular[0]))
    return left[:, 6:], rank


def forming_stretch(x_bohr: Vector, pairs: Sequence[tuple[int, int]]) -> Vector:
    """Return the summed forming-bond stretch: for each (i, j), -u on atom i and +u on atom j.

    ``u`` is the unit vector from atom i to atom j. The result is not normalised.
    """
    positions = x_bohr.reshape(-1, 3)
    stretch = np.zeros_like(positions)
    for i, j in pairs:
        bond = positions[j] - positions[i]
        unit = bond / np.linalg.norm(bond)
        stretch[i] -= unit
        stretch[j] += unit
    return stretch.ravel()


def bofill_update(hessian: Matrix, step: Vector, gradient_change: Vector) -> Matrix:
    """Return Bofill's (1994) update of ``hessian`` for a step and its gradient change.

    With ``r = y - H s``: ``H_MS = H + r r^T / (r^T s)``, ``H_PSB = H + (r s^T + s r^T)/(s^T s)
    - (r^T s) s s^T / (s^T s)^2``, ``phi = (r^T s)^2 / ((r^T r)(s^T s))`` and the update is
    ``phi H_MS + (1 - phi) H_PSB``, symmetrised. When ``|r^T s| < 1e-12 |r| |s|`` it is PSB alone.

    Args:
        hessian: The current Cartesian Hessian (3N x 3N), Eh/Bohr^2.
        step: The accepted step s (3N,), Bohr.
        gradient_change: y = g_new - g_old (3N,), Eh/Bohr.
    """
    residual = gradient_change - hessian @ step
    rs = float(residual @ step)
    ss = float(step @ step)
    rr = float(residual @ residual)
    psb = (
        hessian
        + (np.outer(residual, step) + np.outer(step, residual)) / ss
        - rs * np.outer(step, step) / ss**2
    )
    if abs(rs) < _BOFILL_PSB_RTOL * math.sqrt(rr) * math.sqrt(ss):
        updated = psb
    else:
        murtagh_sargent = hessian + np.outer(residual, residual) / rs
        phi = rs**2 / (rr * ss)
        updated = phi * murtagh_sargent + (1.0 - phi) * psb
    return 0.5 * (updated + updated.T)


class _RootNotFoundError(Exception):
    """The lambda_n root did not converge (reported as ``mode_lost``)."""


def prfo_step(eigenvalues: Vector, gradient: Vector, followed: int) -> Vector:
    """Return the P-RFO step in the Hessian eigenbasis (Baker 1986).

    The followed mode is maximised with ``lambda_p = b_f/2 + sqrt(b_f^2 + 4 F_f^2)/2`` and
    ``step_f = -F_f / (b_f - lambda_p)``; every other mode is minimised with ``lambda_n``, the root
    of ``lambda = sum_k F_k^2 / (lambda - b_k)`` below ``min(0, min_k b_k)``, and
    ``step_k = -F_k / (b_k - lambda_n)``.

    Args:
        eigenvalues: Ascending eigenvalues b of the projected Hessian.
        gradient: Gradient components F in the same eigenbasis.
        followed: Index of the followed mode.

    Raises:
        _RootNotFoundError: The lambda_n root did not converge within 200 iterations.
    """
    step = np.zeros_like(gradient)
    b_f = float(eigenvalues[followed])
    f_f = float(gradient[followed])
    if f_f != 0.0:
        root = math.sqrt(b_f * b_f + 4.0 * f_f * f_f)
        # -F/(b - lambda_p) = F/(lambda_p - b), with lambda_p - b = (root - b)/2, written in the
        # cancellation-free form for each sign of b.
        step[followed] = (root + b_f) / (2.0 * f_f) if b_f >= 0.0 else 2.0 * f_f / (root - b_f)
    others = np.arange(eigenvalues.size) != followed
    b_o = eigenvalues[others]
    f_o = gradient[others]
    lambda_n = _lambda_n(b_o, f_o)
    with np.errstate(divide="ignore", invalid="ignore"):
        minimised = np.where(f_o == 0.0, 0.0, -f_o / (b_o - lambda_n))
    step[others] = minimised
    return step


def _lambda_n(eigenvalues: Vector, gradient: Vector) -> float:
    """Return the root of ``lambda - sum F_k^2/(lambda - b_k)`` below ``min(0, min b_k)``.

    The function rises monotonically from -inf on that interval, so the root is bracketed and
    found by bisection to a bracket width of 1e-12.
    """
    squares = gradient * gradient

    def secular(value: float) -> float:
        return value - float(np.sum(squares / (value - eigenvalues)))

    upper = min(0.0, float(eigenvalues.min()))
    lower = upper - 1.0
    for _ in range(_ROOT_MAX_ITERATIONS):
        if secular(lower) < 0.0:
            break
        lower = upper - 2.0 * (upper - lower)
    else:
        raise _RootNotFoundError("no lower bracket for lambda_n")
    for _ in range(_ROOT_MAX_ITERATIONS):
        middle = 0.5 * (lower + upper)
        if secular(middle) < 0.0:
            lower = middle
        else:
            upper = middle
        if upper - lower <= _ROOT_TOL:
            return 0.5 * (lower + upper)
    raise _RootNotFoundError(f"lambda_n bracket still {upper - lower} wide")


def _projected_eigen(complement: Matrix, hessian: Matrix) -> tuple[Vector, Matrix]:
    """Return the ascending eigenvalues of C^T H C and the Cartesian eigenvectors C V."""
    projected = complement.T @ hessian @ complement
    eigenvalues, vectors = np.linalg.eigh(0.5 * (projected + projected.T))
    return eigenvalues, complement @ vectors


class PRFOOptimizer(TransitionStateOptimizer):
    """Cartesian P-RFO saddle search with exact-Hessian seed and refresh and Bofill updates.

    Counts in the result: ``n_gradient_calls`` is every engine evaluation (each returns a
    gradient), ``n_hessian_calls`` the evaluations that also returned an exact Hessian, and
    ``n_hessian_refreshes`` the exact Hessians after the first.
    """

    OPTIONS: ClassVar[Mapping[str, OptionSpec]] = {
        "max_steps": OptionSpec(int, 100),
        "hessian_refresh_steps": OptionSpec(int, 5),
        "trust_radius_bohr": OptionSpec(float, 0.10),
        "trust_min_bohr": OptionSpec(float, 0.001),
        "trust_max_bohr": OptionSpec(float, 0.30),
        "max_consecutive_rejections": OptionSpec(int, 5),
        "min_initial_overlap": OptionSpec(float, 0.60),
        "min_mode_overlap": OptionSpec(float, 0.50),
        "max_gradient_hartree_per_bohr": OptionSpec(float, 4.5e-4),
        "rms_gradient_hartree_per_bohr": OptionSpec(float, 3.0e-4),
        "max_step_bohr": OptionSpec(float, 1.8e-3),
        "rms_step_bohr": OptionSpec(float, 1.2e-3),
        "max_wall_time_s": OptionSpec(float, 1800.0),
        "ratio_floor_hartree": OptionSpec(float, 1e-8),
    }

    @property
    def identity(self) -> OptimizerIdentity:
        """``prfo`` with ``src-`` and the first 16 hex digits of this module's sha256."""
        return _source_identity()

    def resolved_options(self, options: Mapping[str, ScalarValue] | None) -> dict[str, ScalarValue]:
        """Resolve as the base class, then require positive numbers and ordered trust bounds.

        Raises:
            OptimizerInputError: As the base class, a non-positive number, or
                ``trust_min_bohr <= trust_radius_bohr <= trust_max_bohr`` violated.
        """
        resolved = super().resolved_options(options)
        name = type(self).__name__
        for key, value in resolved.items():
            if isinstance(value, int | float) and not value > 0:
                raise OptimizerInputError(f"{name}: option {key!r} must be positive, not {value!r}")
        low, radius, high = (
            resolved["trust_min_bohr"],
            resolved["trust_radius_bohr"],
            resolved["trust_max_bohr"],
        )
        if not (isinstance(low, float) and isinstance(radius, float) and isinstance(high, float)):
            raise OptimizerInputError(f"{name}: trust options must be floats")
        if not low <= radius <= high:
            raise OptimizerInputError(
                f"{name}: need trust_min_bohr {low} <= trust_radius_bohr {radius} <= "
                f"trust_max_bohr {high}"
            )
        if not math.isfinite(radius) or not math.isfinite(high):
            raise OptimizerInputError(f"{name}: trust options must be finite")
        return resolved

    def find_saddle(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        forming_bonds: Sequence[tuple[int, int]] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> TSSearchResult:
        """Search for a first-order saddle point; see the module docstring and mission §5.

        Raises:
            OptimizerInputError: Bad options, forming bonds or state, before any engine call.
            TSSearchFailedError: ``max_steps``, ``too_many_rejections``, ``mode_lost``,
                ``no_reaction_mode`` or ``wall_time_exceeded``.
            eta_rxncat.engines.EngineError: Raised by the engine; propagated unchanged.
        """
        resolved = self.resolved_options(options)
        pairs = _checked_pairs(state, forming_bonds)
        x0 = np.asarray(state.coordinates, dtype=np.float64).ravel() / BOHR_ANGSTROM
        if len(state.symbols) < 3:
            raise OptimizerInputError(
                f"a TS search needs at least 3 atoms, not {len(state.symbols)}"
            )
        _, rank = rigid_complement(x0)
        if rank < 6:
            raise OptimizerInputError(f"the state is linear (rigid-basis rank {rank} < 6)")
        return _Search(self.identity, resolved, pairs, state, engine).run(x0)


def _checked_pairs(
    state: MolecularState, forming_bonds: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Return the forming bonds as sorted ``(min, max)`` pairs, or raise OptimizerInputError."""
    n_atoms = len(state.symbols)
    pairs: list[tuple[int, int]] = []
    for pair in forming_bonds:
        if (
            not isinstance(pair, Sequence)
            or len(pair) != 2
            or any(isinstance(a, bool) or not isinstance(a, int) for a in pair)
        ):
            raise OptimizerInputError(f"a forming bond must be two ints, not {pair!r}")
        i, j = pair
        if not (0 <= i < n_atoms and 0 <= j < n_atoms):
            raise OptimizerInputError(f"forming bond {pair!r} out of range for {n_atoms} atoms")
        if i == j:
            raise OptimizerInputError(f"forming bond {pair!r} joins an atom to itself")
        pairs.append((min(i, j), max(i, j)))
    if len(set(pairs)) != len(pairs):
        raise OptimizerInputError(f"duplicate forming bonds in {list(forming_bonds)}")
    return sorted(pairs)


class _Search:
    """One P-RFO run: its options, counts, history and the current point."""

    def __init__(
        self,
        identity: OptimizerIdentity,
        options: dict[str, ScalarValue],
        pairs: list[tuple[int, int]],
        state: MolecularState,
        engine: Engine,
    ) -> None:
        self.identity = identity
        self.options = options
        self.pairs = pairs
        self.state = state
        self.engine = engine
        self.history: list[TSStep] = []
        self.n_gradient_calls = 0
        self.n_hessian_calls = 0
        self.n_rejected = 0
        self.last_energy: float | None = None
        self.hessian_method: HessianMethod | None = None
        self.start_time = time.monotonic()

    def _int(self, key: str) -> int:
        value = self.options[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"option {key!r} is not an int")
        return value

    def _float(self, key: str) -> float:
        value = self.options[key]
        if not isinstance(value, float):
            raise TypeError(f"option {key!r} is not a float")
        return value

    def _fail(self, reason: TSSearchFailureReason, message: str) -> TSSearchFailedError:
        return TSSearchFailedError(
            message,
            reason=reason,
            steps=tuple(str(step.step) for step in self.history),
            last_energy_hartree=self.last_energy,
        )

    def _state_at(self, x_bohr: Vector) -> MolecularState:
        coordinates = (x_bohr.reshape(-1, 3) * BOHR_ANGSTROM).tolist()
        return MolecularState.model_validate(
            {**self.state.model_dump(), "coordinates": coordinates}
        )

    def _evaluate(self, state: MolecularState, *, hessian: bool) -> PotentialResult:
        elapsed = time.monotonic() - self.start_time
        limit = self._float("max_wall_time_s")
        if elapsed > limit:
            raise self._fail("wall_time_exceeded", f"{elapsed:.3f} s elapsed, limit {limit} s")
        result = self.engine.evaluate(state, forces=True, hessian=hessian)
        self.n_gradient_calls += 1
        if hessian:
            self.n_hessian_calls += 1
            self.hessian_method = result.hessian_method
        self.last_energy = result.energy_hartree
        return result

    def _exact(self, state: MolecularState) -> tuple[float, Vector, Matrix]:
        result = self._evaluate(state, hessian=True)
        hessian = np.array(result.hessian_hartree_per_bohr2, dtype=np.float64)
        return result.energy_hartree, _gradient(result), 0.5 * (hessian + hessian.T)

    def run(self, x: Vector) -> TSSearchResult:
        """Run the search from ``x`` (Bohr) and return the converged result."""
        max_steps = self._int("max_steps")
        refresh_every = self._int("hessian_refresh_steps")
        max_rejections = self._int("max_consecutive_rejections")
        trust = self._float("trust_radius_bohr")
        trust_min = self._float("trust_min_bohr")
        trust_max = self._float("trust_max_bohr")
        ratio_floor = self._float("ratio_floor_hartree")

        energy, gradient, hessian = self._exact(self.state)
        exact = True
        previous: Vector | None = None
        n_accepted = 0
        consecutive_rejections = 0
        while True:
            if len(self.history) >= max_steps:
                raise self._fail("max_steps", f"not converged after {max_steps} steps")
            complement, _ = rigid_complement(x)
            eigenvalues, vectors = _projected_eigen(complement, hessian)
            followed, overlap = self._choose_mode(
                x, complement, eigenvalues, vectors, previous, exact
            )
            if followed < 0:
                # The mode was lost on a Bofill Hessian: refresh exactly and choose again.
                energy, gradient, hessian = self._exact(self._state_at(x))
                exact = True
                eigenvalues, vectors = _projected_eigen(complement, hessian)
                followed, overlap = self._choose_mode(
                    x, complement, eigenvalues, vectors, previous, exact
                )
            mode = vectors[:, followed]
            if previous is not None and float(mode @ previous) < 0.0:
                mode = -mode
            try:
                step_eigen = prfo_step(eigenvalues, vectors.T @ gradient, followed)
            except _RootNotFoundError as exc:
                raise self._fail("mode_lost", str(exc)) from None
            dx = vectors @ step_eigen
            length = float(np.linalg.norm(dx))
            if length > trust:
                dx *= trust / length
                length = trust
            predicted = float(gradient @ dx + 0.5 * dx @ hessian @ dx)
            trial = self._evaluate(self._state_at(x + dx), hessian=False)
            trial_gradient = _gradient(trial)
            actual = trial.energy_hartree - energy
            ratio = 1.0 if abs(predicted) < ratio_floor else actual / predicted
            accepted = 0.0 <= ratio <= 3.0
            self.history.append(
                TSStep(
                    step=len(self.history),
                    accepted_bool=accepted,
                    energy_hartree=trial.energy_hartree,
                    max_gradient_hartree_per_bohr=float(np.max(np.abs(trial_gradient))),
                    trust_radius_bohr=trust,
                    followed_eigenvalue_hartree_per_bohr2=float(eigenvalues[followed]),
                    mode_overlap=None if overlap is None else min(overlap, 1.0),
                    hessian_source="exact" if exact else "bofill",
                    ratio=ratio,
                )
            )
            previous = mode
            if not accepted:
                self.n_rejected += 1
                consecutive_rejections += 1
                trust = max(0.25 * trust, trust_min)
                if consecutive_rejections > max_rejections:
                    raise self._fail(
                        "too_many_rejections", f"{consecutive_rejections} rejections in a row"
                    )
                energy, gradient, hessian = self._exact(self._state_at(x))
                exact = True
                continue
            consecutive_rejections = 0
            n_accepted += 1
            if 0.75 <= ratio <= 1.25 and length >= 0.9 * trust:
                trust = min(2.0 * trust, trust_max)
            elif ratio < 0.25 or ratio > 1.75:
                trust = max(0.5 * trust, trust_min)
            gradient_change = trial_gradient - gradient
            x = x + dx
            energy, gradient = trial.energy_hartree, trial_gradient
            if self._converged(gradient, dx):
                return self._result(x, energy, gradient, float(eigenvalues[followed]))
            if n_accepted % refresh_every == 0:
                energy, gradient, hessian = self._exact(self._state_at(x))
                exact = True
            else:
                hessian = bofill_update(hessian, dx, gradient_change)
                exact = False

    def _choose_mode(
        self,
        x: Vector,
        complement: Matrix,
        eigenvalues: Vector,
        vectors: Matrix,
        previous: Vector | None,
        exact: bool,
    ) -> tuple[int, float | None]:
        """Return the followed mode index and its overlap; index -1 asks for an exact refresh.

        At the first step the mode with the largest |overlap| with the projected forming
        stretch (or, without forming bonds, the lowest eigenvalue); afterwards the one with the
        largest |overlap| with the previous followed vector.
        """
        if previous is None:
            if not self.pairs:
                return 0, None
            stretch = complement @ (complement.T @ forming_stretch(x, self.pairs))
            stretch /= np.linalg.norm(stretch)
            overlaps = np.abs(vectors.T @ stretch)
            best = int(np.argmax(overlaps))
            if overlaps[best] < self._float("min_initial_overlap"):
                raise self._fail(
                    "no_reaction_mode",
                    f"largest forming-stretch overlap {overlaps[best]:.3f} is below "
                    f"{self._float('min_initial_overlap')}",
                )
            return best, None
        overlaps = np.abs(vectors.T @ previous)
        best = int(np.argmax(overlaps))
        value = float(overlaps[best])
        if value < self._float("min_mode_overlap"):
            if not exact:
                return -1, value
            raise self._fail(
                "mode_lost",
                f"largest overlap with the followed mode {value:.3f} is below "
                f"{self._float('min_mode_overlap')}",
            )
        return best, value

    def _converged(self, gradient: Vector, dx: Vector) -> bool:
        """All four criteria on the unprojected gradient and the accepted step (mission R24)."""
        return (
            float(np.max(np.abs(gradient))) <= self._float("max_gradient_hartree_per_bohr")
            and math.sqrt(float(np.mean(gradient**2)))
            <= self._float("rms_gradient_hartree_per_bohr")
            and float(np.max(np.abs(dx))) <= self._float("max_step_bohr")
            and math.sqrt(float(np.mean(dx**2))) <= self._float("rms_step_bohr")
        )

    def _result(
        self, x: Vector, energy: float, gradient: Vector, followed_eigenvalue: float
    ) -> TSSearchResult:
        complement, _ = rigid_complement(x)
        rigid = gradient - complement @ (complement.T @ gradient)
        if self.hessian_method is None:
            raise TypeError("no exact Hessian was evaluated")
        return TSSearchResult(
            final_state=self._state_at(x),
            final_energy_hartree=energy,
            converged=True,
            n_steps=len(self.history),
            n_gradient_calls=self.n_gradient_calls,
            n_hessian_calls=self.n_hessian_calls,
            n_hessian_refreshes=self.n_hessian_calls - 1,
            n_rejected_steps=self.n_rejected,
            hessian_method=self.hessian_method,
            followed_eigenvalue_hartree_per_bohr2=followed_eigenvalue,
            final_max_gradient_hartree_per_bohr=float(np.max(np.abs(gradient))),
            final_rms_gradient_hartree_per_bohr=math.sqrt(float(np.mean(gradient**2))),
            final_rigid_gradient_norm_hartree_per_bohr=float(np.linalg.norm(rigid)),
            forming_bonds=[FormingBond(i=i, j=j) for i, j in self.pairs],
            optimizer=self.identity,
            options=dict(self.options),
            history=list(self.history),
        )


def _gradient(result: PotentialResult) -> Vector:
    """Return the gradient (minus the forces) of ``result`` as a flat array, Eh/Bohr."""
    if result.forces_hartree_per_bohr is None:
        raise TypeError("the engine returned no forces")
    return -np.asarray(result.forces_hartree_per_bohr, dtype=np.float64).ravel()
