"""Tests for the v0.5.0 clean-room P-RFO TS search (slice 03) on analytic model surfaces.

The tier-D surfaces S1 and S2 are functions of interatomic distances only, so they are invariant
under rigid motions; their energy, gradient and Hessian are analytic (Hartree, Bohr). The states
carry unequal masses (H, C, O, ...) that the search must never use (mission R7, N6).
"""

import ast
import hashlib
import json
import math
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import numpy.typing as npt
import pytest

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig, TSSearchResult
from eta_rxncat.engines import Engine, EngineRuntimeError, OptionSpec
from eta_rxncat.engines.base import RawResult
from eta_rxncat.engines.units import BOHR_ANGSTROM
from eta_rxncat.optimize import (
    OptimizationFailedError,
    OptimizerInputError,
    PRFOOptimizer,
    TransitionStateOptimizer,
    TSSearchFailedError,
)
from eta_rxncat.optimize.prfo import bofill_update

Array = npt.NDArray[np.float64]
PRFO_SRC = Path(__file__).parents[3] / "src" / "eta_rxncat" / "optimize" / "prfo.py"
TS_BASE_SRC = PRFO_SRC.with_name("ts_base.py")
STAGE = StageConfig(kind="ts_opt", engine="xtb_subprocess", method="model-surface")

# --- Model surfaces ---------------------------------------------------------------------------

DistanceEnergy = Callable[[Array], tuple[float, Array, Array]]
"""E(r) of the pair distances: energy, dE/dr (P,) and d2E/dr2 (P, P)."""


def all_pairs(n_atoms: int) -> list[tuple[int, int]]:
    """Return every atom pair (i < j), in lexicographic order."""
    return [(i, j) for i in range(n_atoms) for j in range(i + 1, n_atoms)]


def distances(x: Array, pairs: Sequence[tuple[int, int]]) -> Array:
    """Return the pair distances of flat coordinates ``x`` (Bohr)."""
    r = x.reshape(-1, 3)
    return np.array([np.linalg.norm(r[j] - r[i]) for i, j in pairs])


def cartesian(
    x: Array, pairs: Sequence[tuple[int, int]], energy_of_r: DistanceEnergy
) -> tuple[float, Array, Array]:
    """Return E, the Cartesian gradient and the Cartesian Hessian of a distance surface."""
    r = x.reshape(-1, 3)
    n = x.size
    jac = np.zeros((len(pairs), n))
    second = []
    for p, (i, j) in enumerate(pairs):
        bond = r[j] - r[i]
        length = float(np.linalg.norm(bond))
        u = bond / length
        jac[p, 3 * j : 3 * j + 3] = u
        jac[p, 3 * i : 3 * i + 3] = -u
        block = (np.eye(3) - np.outer(u, u)) / length
        d2 = np.zeros((n, n))
        for a, sa in ((i, -1.0), (j, 1.0)):
            for b, sb in ((i, -1.0), (j, 1.0)):
                d2[3 * a : 3 * a + 3, 3 * b : 3 * b + 3] = sa * sb * block
        second.append(d2)
    energy, d_e, d2_e = energy_of_r(distances(x, pairs))
    gradient = jac.T @ d_e
    hessian = jac.T @ d2_e @ jac + sum(d_e[p] * second[p] for p in range(len(pairs)))
    return energy, gradient, 0.5 * (hessian + hessian.T)


class Surface:
    """A rigid-motion-invariant model surface: reference geometry and E(r) of all pairs."""

    def __init__(self, symbols: list[str], reference_bohr: Array, energy_of_r: DistanceEnergy):
        """Keep the symbols, the saddle geometry (flat, Bohr) and the distance energy."""
        self.symbols = symbols
        self.reference = reference_bohr
        self.pairs = all_pairs(len(symbols))
        self.energy_of_r = energy_of_r

    def evaluate(self, x: Array) -> tuple[float, Array, Array]:
        """Return E, gradient and Hessian at flat coordinates ``x`` (Bohr)."""
        return cartesian(x, self.pairs, self.energy_of_r)

    def state(self, x: Array) -> MolecularState:
        """Return a neutral state at ``x`` (Bohr), with the surface's symbols."""
        n_electrons = sum({"H": 1, "C": 6, "O": 8}[s] for s in self.symbols)
        return MolecularState(
            symbols=self.symbols,
            coordinates=(x.reshape(-1, 3) * BOHR_ANGSTROM).tolist(),
            charge=0,
            spin_multiplicity=1 + n_electrons % 2,
        )


def harmonic_plus(
    reference_r: Array,
    constants: Array,
    reaction: Callable[[Array], tuple[float, Array, Array]],
) -> DistanceEnergy:
    """Return E(r) = sum over the harmonic pairs (constant > 0) plus ``reaction(r)``."""

    def energy_of_r(r: Array) -> tuple[float, Array, Array]:
        dr = r - reference_r
        e_rxn, g_rxn, h_rxn = reaction(r)
        energy = 0.5 * float(np.sum(constants * dr**2)) + e_rxn
        return energy, constants * dr + g_rxn, np.diag(constants) + h_rxn

    return energy_of_r


S1_REFERENCE = np.array(
    [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.3, 1.9, 0.2], [0.5, 0.4, 2.1]]
).ravel()
S1_K = 0.6
S1_SOFT_PAIR = (1, 2)
S1_K_SOFT = 0.15
S1_K1 = 0.2
S1_C = 0.5
# In (sqrt(k1/3c), sqrt(k1/c)) = (0.365, 0.632) Bohr: inside the well, where x is convex.
S1_START_X = 0.55


def s1() -> Surface:
    """S1: four atoms (H, C, O, C), reaction coordinate x = r03 - r03_ref, one soft pair."""
    pairs = all_pairs(4)
    ref_r = distances(S1_REFERENCE, pairs)
    p03 = pairs.index((0, 3))
    constants = np.full(len(pairs), S1_K)
    constants[pairs.index(S1_SOFT_PAIR)] = S1_K_SOFT
    constants[p03] = 0.0

    def reaction(r: Array) -> tuple[float, Array, Array]:
        x = r[p03] - ref_r[p03]
        grad = np.zeros_like(r)
        hess = np.zeros((r.size, r.size))
        grad[p03] = -S1_K1 * x + S1_C * x**3
        hess[p03, p03] = -S1_K1 + 3.0 * S1_C * x**2
        return -0.5 * S1_K1 * x**2 + 0.25 * S1_C * x**4, grad, hess

    return Surface(["H", "C", "O", "C"], S1_REFERENCE, harmonic_plus(ref_r, constants, reaction))


S2_REFERENCE = np.array(
    [
        [0.0, 0.0, 0.0],
        [2.6, 0.1, 0.0],
        [-0.9, 2.3, 0.3],
        [3.4, 2.2, -0.4],
        [0.2, -0.3, 4.2],
        [2.5, 0.4, 4.3],
    ]
).ravel()
S2_FRAGMENT = frozenset({0, 1, 2, 3})
S2_K_INTRA = 0.6
S2_K_INTER = 0.1
S2_K1 = 0.6
S2_C = 1.5
S2_K2 = 0.4


def s2() -> Surface:
    """S2: six atoms in fragments {0..3} and {4, 5}, forming bonds (0, 4) and (1, 5).

    Pairs inside a fragment are stiff, pairs across fragments soft, so the reference is a saddle
    with q+ = (x1 + x2)/sqrt(2) the one descending direction (asserted in the G1 test).
    """
    pairs = all_pairs(6)
    ref_r = distances(S2_REFERENCE, pairs)
    p1, p2 = pairs.index((0, 4)), pairs.index((1, 5))
    constants = np.array(
        [S2_K_INTRA if (i in S2_FRAGMENT) == (j in S2_FRAGMENT) else S2_K_INTER for i, j in pairs]
    )
    constants[[p1, p2]] = 0.0
    root2 = math.sqrt(2.0)

    def reaction(r: Array) -> tuple[float, Array, Array]:
        x1, x2 = r[p1] - ref_r[p1], r[p2] - ref_r[p2]
        qp, qm = (x1 + x2) / root2, (x1 - x2) / root2
        energy = -0.5 * S2_K1 * qp**2 + 0.25 * S2_C * qp**4 + 0.5 * S2_K2 * qm**2
        de_qp, de_qm = -S2_K1 * qp + S2_C * qp**3, S2_K2 * qm
        d2_qp = -S2_K1 + 3.0 * S2_C * qp**2
        grad = np.zeros_like(r)
        grad[p1] = (de_qp + de_qm) / root2
        grad[p2] = (de_qp - de_qm) / root2
        hess = np.zeros((r.size, r.size))
        hess[p1, p1] = hess[p2, p2] = 0.5 * (d2_qp + S2_K2)
        hess[p1, p2] = hess[p2, p1] = 0.5 * (d2_qp - S2_K2)
        return energy, grad, hess

    return Surface(
        ["C", "C", "H", "O", "C", "H"], S2_REFERENCE, harmonic_plus(ref_r, constants, reaction)
    )


def rotation(seed: int) -> Array:
    """Return a seeded random proper rotation matrix."""
    q, r = np.linalg.qr(np.random.default_rng(seed).normal(size=(3, 3)))
    q = q * np.sign(np.diag(r))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def s1_start() -> Array:
    """S1's start: x = 0.45 Bohr, every pair perturbed, the frame rotated and shifted."""
    rng = np.random.default_rng(11)
    r = S1_REFERENCE.reshape(-1, 3).copy()
    r += rng.normal(scale=0.05, size=r.shape)
    u = (r[3] - r[0]) / np.linalg.norm(r[3] - r[0])
    current = np.linalg.norm(r[3] - r[0]) - np.linalg.norm(S1_REFERENCE[9:12] - S1_REFERENCE[:3])
    r[3] += (S1_START_X - current) * u
    return (r @ rotation(5).T + np.array([0.7, -1.2, 0.4])).ravel()


def s2_start(scale: float, shift: float) -> Array:
    """S2's start: noise of ``scale`` Bohr plus ``shift`` Bohr along both forming bonds."""
    rng = np.random.default_rng(23)
    r = S2_REFERENCE.reshape(-1, 3).copy()
    r += rng.normal(scale=scale, size=r.shape)
    for i, j in ((0, 4), (1, 5)):
        u = (r[j] - r[i]) / np.linalg.norm(r[j] - r[i])
        r[j] += 0.5 * shift * u
        r[i] -= 0.5 * shift * u
    return (r @ rotation(7).T).ravel()


# --- Engines --------------------------------------------------------------------------------


class SurfaceEngine(Engine):
    """An engine over a model surface; logs every call and can inject faults (tests only)."""

    tag = "xtb_subprocess"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {}

    def __init__(
        self,
        evaluate: Callable[[Array], tuple[float, Array, Array]],
        *,
        trial_energy_offset: float = 0.0,
        offset_calls: frozenset[int] = frozenset(),
        delay_s: float = 0.0,
        fail_at_call: int | None = None,
        error: Exception | None = None,
    ) -> None:
        """Wrap ``evaluate``; ``offset_calls`` are 1-based call numbers whose energy is raised."""
        super().__init__(STAGE)
        self.surface = evaluate
        self.trial_energy_offset = trial_energy_offset
        self.offset_calls = offset_calls
        self.delay_s = delay_s
        self.fail_at_call = fail_at_call
        self.error = error
        self.log: list[bool] = []  # one entry per call: whether a Hessian was requested

    @property
    def identity(self) -> EngineIdentity:
        """A fixed fake identity."""
        return EngineIdentity(name="xtb_subprocess", version="model-surface")

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self.log.append(hessian)
        if self.fail_at_call is not None and len(self.log) == self.fail_at_call:
            raise self.error or RuntimeError("no error given")
        if self.delay_s:
            time.sleep(self.delay_s)
        x = np.asarray(state.coordinates, dtype=np.float64).ravel() / BOHR_ANGSTROM
        energy, gradient, hess = self.surface(x)
        hess = 0.5 * (hess + hess.T)  # exactly symmetric, as PotentialResult requires
        if len(self.log) in self.offset_calls:
            energy += self.trial_energy_offset
        return RawResult(
            energy_hartree=energy,
            device="cpu",
            forces_hartree_per_bohr=(-gradient).reshape(-1, 3).tolist() if forces else None,
            hessian_hartree_per_bohr2=hess.tolist() if hessian else None,
            hessian_method="analytic" if hessian else None,
            hessian_max_asymmetry=0.0 if hessian else None,
        )


def quadratic(reference: Array, hessian: Callable[[int], Array]) -> Callable[..., Any]:
    """Return a quadratic surface about ``reference`` whose Hessian depends on the call number."""
    calls = [0]

    def evaluate(x: Array) -> tuple[float, Array, Array]:
        calls[0] += 1
        h = hessian(calls[0])
        d = x - reference
        return 0.5 * float(d @ h @ d), h @ d, h

    return evaluate


# --- Test-side geometry helpers -------------------------------------------------------------


def complement(x: Array) -> Array:
    """Return an orthonormal basis of the rigid-motion complement (test-local, by SVD)."""
    r = x.reshape(-1, 3)
    c = r - r.mean(axis=0)
    basis = np.zeros((x.size, 6))
    for a in range(3):
        basis[a::3, a] = 1.0
        e = np.zeros(3)
        e[a] = 1.0
        basis[:, 3 + a] = np.cross(e, c).ravel()
    u, _, _ = np.linalg.svd(basis, full_matrices=True)
    return u[:, 6:]


def projected_eigen(x: Array, hessian: Array) -> tuple[Array, Array]:
    """Return ascending projected eigenvalues and the Cartesian eigenvectors at ``x``."""
    c = complement(x)
    values, vectors = np.linalg.eigh(c.T @ hessian @ c)
    return values, c @ vectors


def stretch(x: Array, bonds: Sequence[tuple[int, int]]) -> Array:
    """Return the unit projected forming-bond stretch at ``x`` (test-local)."""
    r = x.reshape(-1, 3)
    s = np.zeros_like(r)
    for i, j in bonds:
        u = (r[j] - r[i]) / np.linalg.norm(r[j] - r[i])
        s[i] -= u
        s[j] += u
    c = complement(x)
    v = c @ (c.T @ s.ravel())
    return v / np.linalg.norm(v)


def superposed_deviation(x: Array, reference: Array) -> float:
    """Return the largest atom deviation (Bohr) after unweighted SVD (Kabsch) superposition."""
    p = x.reshape(-1, 3) - x.reshape(-1, 3).mean(axis=0)
    q = reference.reshape(-1, 3) - reference.reshape(-1, 3).mean(axis=0)
    u, _, vt = np.linalg.svd(p.T @ q)
    d = np.sign(np.linalg.det(u @ vt))
    rot = u @ np.diag([1.0, 1.0, d]) @ vt
    return float(np.max(np.linalg.norm(p @ rot - q, axis=1)))


def x_of(state: MolecularState) -> Array:
    """Return the flat Bohr coordinates of ``state``."""
    return np.asarray(state.coordinates, dtype=np.float64).ravel() / BOHR_ANGSTROM


def run(surface: Surface, start: Array, **kwargs: Any) -> tuple[TSSearchResult, SurfaceEngine]:
    """Run P-RFO on ``surface`` from ``start``; return the result and the engine."""
    engine = SurfaceEngine(surface.evaluate)
    bonds = kwargs.pop("forming_bonds", ())
    result = PRFOOptimizer().find_saddle(
        surface.state(start), engine, forming_bonds=bonds, options=kwargs or None
    )
    return result, engine


# --- G1: convergence to the reference saddle ----------------------------------------------------


def test_s1_start_conditions() -> None:
    """At S1's start the lowest mode is not the reaction mode; another mode is (>= 0.60)."""
    start = s1_start()
    _, _, hessian = s1().evaluate(start)
    values, vectors = projected_eigen(start, hessian)
    overlaps = np.abs(vectors.T @ stretch(start, [(0, 3)]))
    assert overlaps[0] < 0.60
    assert int(np.argmax(overlaps)) != 0
    assert overlaps.max() >= 0.60
    assert values[0] < values[int(np.argmax(overlaps))]


@pytest.mark.parametrize(
    ("name", "surface", "start", "bonds"),
    [
        ("S1", s1, s1_start, [(0, 3)]),
        ("S2", s2, lambda: s2_start(0.05, 0.15), [(0, 4), (1, 5)]),
    ],
)
def test_g1_converges_to_the_reference_saddle(
    name: str,
    surface: Callable[[], Surface],
    start: Callable[[], Array],
    bonds: list[tuple[int, int]],
) -> None:
    """G1: converged, every atom within 1e-4 Bohr of the reference, one negative eigenvalue."""
    model = surface()
    result, _ = run(model, start(), forming_bonds=bonds)
    x = x_of(result.final_state)
    assert superposed_deviation(x, model.reference) <= 1e-4
    _, _, hessian = model.evaluate(x)
    values, _ = projected_eigen(x, hessian)
    assert int(np.count_nonzero(values < 0.0)) == 1
    assert result.final_rigid_gradient_norm_hartree_per_bohr <= 1e-10
    assert result.final_max_gradient_hartree_per_bohr <= 4.5e-4
    assert result.converged is True
    assert result.optimizer.name == "prfo"
    assert [(b.i, b.j) for b in result.forming_bonds] == bonds


def test_s2_start_reaction_mode_is_lowest() -> None:
    """S2's start has the reaction mode as the lowest eigenvector (>= 0.60 overlap)."""
    start = s2_start(0.05, 0.15)
    _, _, hessian = s2().evaluate(start)
    _, vectors = projected_eigen(start, hessian)
    overlaps = np.abs(vectors.T @ stretch(start, [(0, 4), (1, 5)]))
    assert int(np.argmax(overlaps)) == 0
    assert overlaps[0] >= 0.60


def test_s3_converges_in_three_steps() -> None:
    """S3: S2 started very close to the saddle converges in at most 3 steps."""
    model = s2()
    result, _ = run(model, s2_start(1e-3, 0.0), forming_bonds=[(0, 4), (1, 5)])
    assert result.n_steps <= 3
    assert superposed_deviation(x_of(result.final_state), model.reference) <= 1e-4


def test_repeat_run_is_identical() -> None:
    """Two runs from the same start give the same result, field for field (determinism)."""
    first, _ = run(s1(), s1_start(), forming_bonds=[(0, 3)])
    second, _ = run(s1(), s1_start(), forming_bonds=[(0, 3)])
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


# --- Mode choice ----------------------------------------------------------------------------


def test_s1_initial_mode_is_max_overlap_not_lowest() -> None:
    """On S1 the first followed mode is the max-overlap eigenvector, not the lowest."""
    start = s1_start()
    _, _, hessian = s1().evaluate(start)
    values, vectors = projected_eigen(start, hessian)
    best = int(np.argmax(np.abs(vectors.T @ stretch(start, [(0, 3)]))))
    result, _ = run(s1(), start, forming_bonds=[(0, 3)])
    followed = result.history[0].followed_eigenvalue_hartree_per_bohr2
    assert followed == pytest.approx(values[best], abs=1e-10)
    assert followed != pytest.approx(values[0], abs=1e-6)
    assert result.history[0].mode_overlap is None


def test_without_forming_bonds_the_lowest_mode_is_followed() -> None:
    """With forming_bonds=() the first followed mode is the lowest eigenvalue."""
    start = s2_start(0.05, 0.15)
    _, _, hessian = s2().evaluate(start)
    values, _ = projected_eigen(start, hessian)
    result, _ = run(s2(), start)
    assert result.history[0].followed_eigenvalue_hartree_per_bohr2 == pytest.approx(
        values[0], abs=1e-10
    )
    assert result.forming_bonds == []


# --- Hessian cadence (US-004) ---------------------------------------------------------------


def expected_calls(result: TSSearchResult, refresh_every: int) -> tuple[list[bool], list[str]]:
    """Return the expected call log (True = Hessian) and the expected source of each step."""
    calls = [True]
    sources: list[str] = []
    exact = True
    accepted = 0
    last = len(result.history) - 1
    for k, step in enumerate(result.history):
        sources.append("exact" if exact else "bofill")
        calls.append(False)
        if not step.accepted_bool:
            calls.append(True)
            exact = True
            continue
        accepted += 1
        if k == last:
            break
        exact = accepted % refresh_every == 0
        if exact:
            calls.append(True)
    return calls, sources


def test_hessian_cadence_and_counts() -> None:
    """Exact Hessians at step 0, every 5th accepted step and after each rejection; Bofill else."""
    model = s1()
    engine = SurfaceEngine(model.evaluate, trial_energy_offset=1.0, offset_calls=frozenset({4}))
    result = PRFOOptimizer().find_saddle(model.state(s1_start()), engine, forming_bonds=[(0, 3)])
    calls, sources = expected_calls(result, 5)
    assert result.n_rejected_steps >= 1
    assert sum(step.accepted_bool for step in result.history) > 5
    assert engine.log == calls
    assert [step.hessian_source for step in result.history] == sources
    assert result.n_gradient_calls == len(engine.log)
    assert result.n_hessian_calls == sum(engine.log)
    assert result.n_hessian_refreshes == sum(engine.log) - 1
    assert result.n_rejected_steps == sum(not step.accepted_bool for step in result.history)
    assert [step.step for step in result.history] == list(range(result.n_steps))


# --- Bofill -----------------------------------------------------------------------------------


def test_bofill_update_matches_the_formula() -> None:
    """The update equals phi H_MS + (1 - phi) H_PSB for random s, y (formula written here)."""
    rng = np.random.default_rng(3)
    a = rng.normal(size=(6, 6))
    h = 0.5 * (a + a.T)
    s = rng.normal(size=6)
    y = rng.normal(size=6)
    r = y - h @ s
    h_ms = h + np.outer(r, r) / (r @ s)
    h_psb = (
        h + (np.outer(r, s) + np.outer(s, r)) / (s @ s) - (r @ s) * np.outer(s, s) / (s @ s) ** 2
    )
    phi = (r @ s) ** 2 / ((r @ r) * (s @ s))
    expected = phi * h_ms + (1 - phi) * h_psb
    np.testing.assert_allclose(bofill_update(h, s, y), 0.5 * (expected + expected.T), atol=1e-12)


def test_bofill_psb_only_when_r_orthogonal_to_s() -> None:
    """With r.s = 0 the update is PSB alone."""
    rng = np.random.default_rng(4)
    a = rng.normal(size=(6, 6))
    h = 0.5 * (a + a.T)
    s = rng.normal(size=6)
    r = rng.normal(size=6)
    r -= (r @ s) / (s @ s) * s
    y = h @ s + r
    psb = h + (np.outer(r, s) + np.outer(s, r)) / (s @ s)
    np.testing.assert_allclose(bofill_update(h, s, y), psb, atol=1e-12)


# --- Failures -------------------------------------------------------------------------------


def spread_basis(x: Array, lead: Array, spread: Array) -> Array:
    """Return an orthonormal basis of the rigid complement at ``x`` whose first modes mix ``lead``.

    ``lead`` (unit, in the complement) is first expanded to a complement basis A; the returned
    basis is A with its leading block multiplied by the orthogonal ``spread``.
    """
    c = complement(x)
    m = c.shape[1]
    q, _ = np.linalg.qr(np.column_stack([c.T @ lead, np.eye(m)]))
    q = q[:, :m] * np.sign(float(q[:, 0] @ (c.T @ lead)))
    a = c @ q
    k = spread.shape[0]
    a[:, :k] = a[:, :k] @ spread
    return a


def uniform_first_row(size: int) -> Array:
    """Return an orthogonal matrix whose first row is uniform (every entry 1/sqrt(size))."""
    q, _ = np.linalg.qr(np.column_stack([np.ones(size), np.eye(size)[:, 1:]]))
    return q.T


def failure(
    engine: SurfaceEngine, state: MolecularState, bonds: Sequence[tuple[int, int]] = (), **opts: Any
) -> TSSearchFailedError:
    """Run P-RFO expecting a TSSearchFailedError and return it."""
    with pytest.raises(TSSearchFailedError) as info:
        PRFOOptimizer().find_saddle(state, engine, forming_bonds=bonds, options=opts or None)
    error = info.value
    assert isinstance(error, OptimizationFailedError)
    assert error.reason in str(error)
    assert all(isinstance(step, str) for step in error.steps)
    assert error.last_energy_hartree is not None
    return error


def test_no_reaction_mode() -> None:
    """A forming bond spread over four modes (overlap 0.5 each) has no reaction mode."""
    x = S1_REFERENCE
    lead = stretch(x, [(0, 3)])
    basis = spread_basis(x, lead, uniform_first_row(4))
    hessian = basis @ np.diag([-0.1, 0.2, 0.3, 0.4, 0.5, 0.6]) @ basis.T
    engine = SurfaceEngine(quadratic(x, lambda _call: hessian))
    error = failure(engine, s1().state(x), [(0, 3)])
    assert error.reason == "no_reaction_mode"
    assert error.steps == ()
    assert engine.log == [True]


def test_too_many_rejections() -> None:
    """A trial energy raised by 1 Eh at every gradient call makes every step a rejection."""
    model = s2()
    engine = SurfaceEngine(
        model.evaluate, trial_energy_offset=1.0, offset_calls=frozenset(range(2, 100, 2))
    )
    error = failure(engine, model.state(s2_start(0.05, 0.15)), [(0, 4), (1, 5)])
    assert error.reason == "too_many_rejections"
    assert error.steps == tuple(str(k) for k in range(6))


def test_max_steps() -> None:
    """max_steps=2 far from the saddle stops after two steps."""
    model = s1()
    error = failure(SurfaceEngine(model.evaluate), model.state(s1_start()), [(0, 3)], max_steps=2)
    assert error.reason == "max_steps"
    assert error.steps == ("0", "1")


def test_mode_lost() -> None:
    """A fake whose eigenvectors rotate after the first call loses the followed mode."""
    x = S2_REFERENCE.copy()
    x[12:15] += np.array([0.1, -0.05, 0.08])
    first = complement(x)
    values = np.linspace(-0.2, 0.9, first.shape[1])
    h1 = first @ np.diag(values) @ first.T
    turned = first.copy()
    turned[:, :6] = first[:, :6] @ uniform_first_row(6)
    h2 = turned @ np.diag(values) @ turned.T
    assert np.max(np.abs(first[:, 0] @ turned)) < 0.5
    engine = SurfaceEngine(quadratic(S2_REFERENCE, lambda call: h1 if call == 1 else h2))
    error = failure(engine, s2().state(x), hessian_refresh_steps=1)
    assert error.reason == "mode_lost"
    assert error.steps[0] == "0"


def test_wall_time_exceeded() -> None:
    """A slow engine with a tiny wall-time limit stops before an engine call."""
    model = s1()
    engine = SurfaceEngine(model.evaluate, delay_s=0.02)
    error = failure(engine, model.state(s1_start()), [(0, 3)], max_wall_time_s=0.05)
    assert error.reason == "wall_time_exceeded"
    assert list(error.steps) == [str(k) for k in range(len(error.steps))]


def test_engine_error_propagates_unchanged() -> None:
    """An EngineError from the engine propagates as the same object."""
    model = s1()
    error = EngineRuntimeError("fake engine failure")
    engine = SurfaceEngine(model.evaluate, fail_at_call=3, error=error)
    with pytest.raises(EngineRuntimeError) as info:
        PRFOOptimizer().find_saddle(model.state(s1_start()), engine, forming_bonds=[(0, 3)])
    assert info.value is error


# --- Refusals before any engine call ---------------------------------------------------------


def linear_state() -> MolecularState:
    """Return a linear three-atom state."""
    return MolecularState(
        symbols=["O", "C", "O"],
        coordinates=[[0.0, 0.0, -1.16], [0.0, 0.0, 0.0], [0.0, 0.0, 1.16]],
        charge=0,
        spin_multiplicity=1,
    )


def two_atoms() -> MolecularState:
    """Return a two-atom state."""
    return MolecularState(
        symbols=["H", "H"], coordinates=[[0, 0, 0], [0, 0, 0.74]], charge=0, spin_multiplicity=1
    )


@pytest.mark.parametrize(
    ("options", "bonds", "state", "fragment"),
    [
        ({"bogus": 1}, [(0, 3)], None, "unknown option"),
        ({"max_steps": 10.5}, [(0, 3)], None, "'max_steps' must be int"),
        ({"max_steps": True}, [(0, 3)], None, "'max_steps' must be int"),
        ({"trust_radius_bohr": "0.1"}, [(0, 3)], None, "'trust_radius_bohr' must be float"),
        ({"constraints": "freeze:0"}, [(0, 3)], None, "'constraints' is refused"),
        ({"max_steps": 0}, [(0, 3)], None, "'max_steps' must be positive"),
        ({"ratio_floor_hartree": -1e-8}, [(0, 3)], None, "must be positive"),
        ({"min_mode_overlap": 0.0}, [(0, 3)], None, "must be positive"),
        ({"trust_radius_bohr": 0.5}, [(0, 3)], None, "trust_radius_bohr 0.5 <= trust_max"),
        ({"trust_min_bohr": 0.2}, [(0, 3)], None, "need trust_min_bohr 0.2"),
        (None, [(0, 4)], None, "out of range for 4 atoms"),
        (None, [(-1, 2)], None, "out of range"),
        (None, [(2, 2)], None, "joins an atom to itself"),
        (None, [(0, 3), (3, 0)], None, "duplicate forming bonds"),
        (None, [(0, True)], None, "two ints"),
        (None, [(0, 1, 2)], None, "two ints"),
        (None, [], "two", "at least 3 atoms"),
        (None, [], "linear", "linear"),
    ],
)
def test_refused_before_any_engine_call(
    options: dict[str, Any] | None, bonds: list[Any], state: str | None, fragment: str
) -> None:
    """Every bad option, forming bond or state raises OptimizerInputError with zero calls."""
    model = s1()
    engine = SurfaceEngine(model.evaluate)
    states = {None: model.state(s1_start()), "two": two_atoms(), "linear": linear_state()}
    with pytest.raises(OptimizerInputError) as info:
        PRFOOptimizer().find_saddle(states[state], engine, forming_bonds=bonds, options=options)
    assert fragment in str(info.value), str(info.value)
    assert engine.log == []


def test_resolved_options_defaults() -> None:
    """The resolved defaults are the mission's keyed numbers, sorted by key."""
    resolved = PRFOOptimizer().resolved_options(None)
    assert list(resolved) == sorted(resolved)
    assert resolved == {
        "hessian_refresh_steps": 5,
        "max_consecutive_rejections": 5,
        "max_gradient_hartree_per_bohr": 4.5e-4,
        "max_step_bohr": 1.8e-3,
        "max_steps": 100,
        "max_wall_time_s": 1800.0,
        "min_initial_overlap": 0.60,
        "min_mode_overlap": 0.50,
        "ratio_floor_hartree": 1e-8,
        "rms_gradient_hartree_per_bohr": 3.0e-4,
        "rms_step_bohr": 1.2e-3,
        "trust_max_bohr": 0.30,
        "trust_min_bohr": 0.001,
        "trust_radius_bohr": 0.10,
    }
    coerced = PRFOOptimizer().resolved_options({"max_wall_time_s": 60})["max_wall_time_s"]
    assert coerced == 60.0
    assert isinstance(coerced, float)


# --- Identity, interface and imports ---------------------------------------------------------


def test_identity_is_the_source_hash() -> None:
    """The version is "src-" plus the first 16 hex digits of prfo.py's sha256."""
    identity = PRFOOptimizer().identity
    digest = hashlib.sha256(PRFO_SRC.read_bytes()).hexdigest()[:16]
    assert identity.name == "prfo"
    assert identity.version == "src-" + digest
    assert len(identity.version) == 20
    int(identity.version[4:], 16)


def test_prfo_is_a_transition_state_optimizer() -> None:
    """PRFOOptimizer is a TransitionStateOptimizer, and the ABC has no constraint parameters."""
    import inspect

    assert isinstance(PRFOOptimizer(), TransitionStateOptimizer)
    parameters = inspect.signature(TransitionStateOptimizer.find_saddle).parameters
    assert list(parameters) == ["self", "state", "engine", "forming_bonds", "options"]


def test_ts_modules_import_no_optimizer_or_engine_library() -> None:
    """G3: importing the TS modules loads no geomeTRIC, torch, PySCF, fairchem or RDKit."""
    heavy = ("geometric", "torch", "pyscf", "fairchem", "rdkit")
    code = (
        "import json, sys\n"
        "import eta_rxncat.optimize, eta_rxncat.optimize.ts_base, eta_rxncat.optimize.prfo\n"
        f"print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in {heavy!r})))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


@pytest.mark.parametrize(
    ("path", "banned"),
    [
        (TS_BASE_SRC, {"numpy", "geometric", "thermo"}),
        (PRFO_SRC, {"geometric", "thermo"}),
    ],
)
def test_ts_module_imports(path: Path, banned: set[str]) -> None:
    """ts_base.py imports no numpy; neither module imports geomeTRIC or thermo (N2, N6)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    hits = {name for name in names for ban in banned if ban in name.split(".")}
    assert hits == set()
