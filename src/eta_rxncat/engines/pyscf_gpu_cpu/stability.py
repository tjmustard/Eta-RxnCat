"""The lowest eigenvalue of a converged mean field's internal-stability Hessian (R9, R54).

PySCF's own verdict is ``stable = not (lambda_min < -1e-5)`` at Davidson ``tol`` 1e-4. That sits
inside the run-to-run noise of PySCF's threaded CPU reductions on flat open-shell states (the
hydroxyl doublet's lambda_min scatters -5.3e-5 .. +2.0e-5 at 8 threads), so the engine computes
lambda_min itself, with the SAME operator and solver, and applies its own keyed threshold
(``stability_tol``) in ``engine.py``.

The calls below replay, line for line, the bodies of the pinned libraries' internal-stability
functions, returning lambda_min instead of a verdict. They use private API, so they are pinned:

- CPU, PySCF 2.15.1, ``pyscf.scf.stability.rhf_internal`` / ``uhf_internal``:
  ``pyscf.soscf.newton_ah.gen_g_hop_rhf`` / ``gen_g_hop_uhf`` (``with_symmetry=True``, as
  ``mf.stability()`` calls them), ``pyscf.lib.davidson`` (``nroots=3``) and the private
  ``pyscf.scf.stability._rotate_mo``;
- GPU, GPU4PySCF 1.9.2, ``gpu4pyscf.scf.stability.rhf_internal`` / ``uhf_internal``:
  ``gpu4pyscf.scf.soscf.gen_g_hop_rhf`` / ``gen_g_hop_uhf`` (``with_nlc=True``),
  ``gpu4pyscf.fci.direct_spin1.davidson1``, and the private
  ``gpu4pyscf.scf.stability.get_davidson_initial_guess``, ``_rotate_mo`` / ``_rotate_mo_uhf`` and
  ``STAB_HESS_NUMERICAL_ZERO``.

Only the Davidson ``tol`` differs from the libraries' defaults: 1e-6 instead of 1e-4.
"""

import importlib
from typing import Any, Final

import numpy as np

STABILITY_DAVIDSON_TOL: Final = 1e-6
"""Davidson convergence tolerance for lambda_min (R54; the libraries' default is 1e-4)."""

STABILITY_NROOTS: Final = 3
"""Roots solved for, as the libraries' ``STAB_NROOTS`` (3); lambda_min is the lowest."""

PINNED: Final = {"pyscf": "2.15.1", "gpu4pyscf": "1.9.2"}
"""The library versions whose private stability internals this module replays."""


def _is_uhf(mf: Any) -> bool:
    """Unrestricted (two spin channels of occupations)."""
    return int(np.ndim(mf.mo_occ)) == 2


def _is_gpu(mf: Any) -> bool:
    """A GPU4PySCF mean field."""
    return type(mf).__module__.startswith("gpu4pyscf")


def lowest_internal(mf: Any, tol: float = STABILITY_DAVIDSON_TOL) -> tuple[float, Any]:
    """``(lambda_min, rotated_mo)`` of ``mf``'s internal-stability Hessian (Eh).

    ``rotated_mo`` are the orbitals rotated along the lowest eigenvector (the ones PySCF's
    ``*_internal`` would return when unstable), in the mean field's own array type.
    """
    return _gpu_lowest(mf, tol) if _is_gpu(mf) else _cpu_lowest(mf, tol)


def _cpu_lowest(mf: Any, tol: float) -> tuple[float, Any]:
    """PySCF 2.15.1 ``rhf_internal`` / ``uhf_internal``, returning lambda_min."""
    lib = importlib.import_module("pyscf.lib")
    newton_ah = importlib.import_module("pyscf.soscf.newton_ah")
    stab = importlib.import_module("pyscf.scf.stability")
    uhf = _is_uhf(mf)
    gen = newton_ah.gen_g_hop_uhf if uhf else newton_ah.gen_g_hop_rhf
    g, hop, hdiag = gen(mf, mf.mo_coeff, mf.mo_occ, with_symmetry=True)
    hdiag *= 2

    def precond(dx: Any, e: Any, x0: Any) -> Any:
        hdiagd = hdiag - e
        hdiagd[abs(hdiagd) < 1e-8] = 1e-8
        return dx / hdiagd

    def hessian_x(x: Any) -> Any:
        return hop(x).real * 2

    x0 = np.zeros_like(g)
    x0[g != 0] = 1.0 / hdiag[g != 0]
    e, v = lib.davidson(hessian_x, x0, precond, tol=tol, nroots=STABILITY_NROOTS)
    e0, v0 = e[0], v[0]
    if uhf:
        nocca = int(np.count_nonzero(mf.mo_occ[0] > 0))
        nvira = int(np.count_nonzero(mf.mo_occ[0] == 0))
        mo = (
            stab._rotate_mo(mf.mo_coeff[0], mf.mo_occ[0], v0[: nocca * nvira]),
            stab._rotate_mo(mf.mo_coeff[1], mf.mo_occ[1], v0[nocca * nvira :]),
        )
    else:
        mo = stab._rotate_mo(mf.mo_coeff, mf.mo_occ, v0)
    return float(e0), mo


def _gpu_lowest(mf: Any, tol: float) -> tuple[float, Any]:
    """GPU4PySCF 1.9.2 ``rhf_internal`` / ``uhf_internal``, returning lambda_min."""
    cp = importlib.import_module("cupy")
    soscf = importlib.import_module("gpu4pyscf.scf.soscf")
    stab = importlib.import_module("gpu4pyscf.scf.stability")
    davidson1 = importlib.import_module("gpu4pyscf.fci.direct_spin1").davidson1
    uhf = _is_uhf(mf)
    gen = soscf.gen_g_hop_uhf if uhf else soscf.gen_g_hop_rhf
    _, hop, hdiag = gen(mf, mf.mo_coeff, mf.mo_occ, with_nlc=True)
    hdiag *= 2
    zero = stab.STAB_HESS_NUMERICAL_ZERO

    def precond(residuals: Any, eigenvalues: Any) -> Any:
        hdiagd = hdiag[None, :] - eigenvalues[:, None]
        hdiagd[cp.abs(hdiagd) < zero] = zero
        return residuals / hdiagd

    def hessian_x(xs: Any) -> Any:
        return cp.stack([hop(x).real * 2 for x in xs])

    x0 = stab.get_davidson_initial_guess(hdiag, STABILITY_NROOTS, STABILITY_NROOTS * 2)
    converged, e, v = davidson1(hessian_x, x0, precond, tol=tol, nroots=STABILITY_NROOTS)
    if not converged[0]:
        raise RuntimeError("internal stability Davidson did not converge the lowest root")
    rotate = stab._rotate_mo_uhf if uhf else stab._rotate_mo
    return float(e[0]), rotate(mf.mo_coeff, mf.mo_occ, v[0])
