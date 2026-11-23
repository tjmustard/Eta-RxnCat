"""R54: the noise-robust internal-stability verdict of ``pyscf_gpu_cpu`` (default suite, CPU).

The state is unstable iff ``lambda_min < -stability_tol`` (1e-3). A follow that lowers the energy
by less than ``stability_noise_eh`` (1e-6) ends the analysis as stable and does not consume the
budget of 2 progressive follows. lambda_min comes from ``stability.lowest_internal``, which replays
PySCF 2.15.1's own ``rhf_internal`` / ``uhf_internal`` operator and Davidson at tol 1e-6.
"""

import io
import re
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, StageConfig
from eta_rxncat.engines import EngineInputError, PySCFEngine, ScfConvergenceError
from eta_rxncat.engines.pyscf_gpu_cpu import engine as engine_module
from eta_rxncat.engines.pyscf_gpu_cpu.stability import (
    PINNED,
    STABILITY_DAVIDSON_TOL,
    lowest_internal,
)

WATER = MolecularState(
    symbols=["O", "H", "H"],
    coordinates=[[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]],
    charge=0,
    spin_multiplicity=1,
)
HYDROXYL = MolecularState(
    symbols=["O", "H"],
    coordinates=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.97]],
    charge=0,
    spin_multiplicity=2,
)


def hf(**options: Any) -> PySCFEngine:
    """HF/sto-3g on the CPU (fast)."""
    return PySCFEngine.from_stage(
        StageConfig(
            kind="single_point",
            engine="pyscf_gpu_cpu",
            method="hf",
            basis="sto-3g",
            options=options,
        ),
        device="cpu",
    )


def inject(
    monkeypatch: pytest.MonkeyPatch, lambdas: list[float], drops_eh: list[float]
) -> dict[str, int]:
    """lambda_min values in turn, last repeats; follow k lowers E by ``drops_eh[k]``, last repeats.

    The follow's SCF really runs from the same orbitals; its energy is then set to the energy
    before the follow minus that follow's drop.
    """
    seen = {"calls": 0, "follows": 0}
    real_kernel = PySCFEngine._kernel

    def lowest(mf: Any, tol: float = STABILITY_DAVIDSON_TOL) -> tuple[float, Any]:
        index = min(seen["calls"], len(lambdas) - 1)
        seen["calls"] += 1
        return lambdas[index], mf.mo_coeff

    def kernel(self: PySCFEngine, mf: Any, dm0: Any = None) -> bool:
        if dm0 is None or not seen["calls"]:
            return real_kernel(self, mf, dm0)
        before = float(mf.e_tot)
        ok = real_kernel(self, mf, dm0)
        drop = drops_eh[min(seen["follows"], len(drops_eh) - 1)]
        seen["follows"] += 1
        mf.e_tot = before - drop
        return ok

    monkeypatch.setattr(engine_module, "lowest_internal", lowest)
    monkeypatch.setattr(PySCFEngine, "_kernel", kernel)
    return seen


def test_keyed_defaults_and_engine_impl() -> None:
    """stability_tol 1e-3 and stability_noise_eh 1e-6 are keyed; engine_impl is 2."""
    options = hf().stage.options
    assert options["stability_tol"] == 1e-3
    assert options["stability_noise_eh"] == 1e-6
    assert options["engine_impl"] == 2
    assert PINNED == {"pyscf": "2.15.1", "gpu4pyscf": "1.9.2"}


@pytest.mark.parametrize("key", ["stability_tol", "stability_noise_eh"])
@pytest.mark.parametrize("value", [0.0, -1e-3])
def test_non_positive_thresholds_refused(key: str, value: float) -> None:
    """Both thresholds must be > 0."""
    with pytest.raises(EngineInputError, match=key):
        hf(**{key: value})


def test_lambda_just_above_threshold_is_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    """lambda_min = -9e-4 (> -1e-3): stable, no follow; lambda_min recorded."""
    seen = inject(monkeypatch, [-9e-4], [1e-3])
    result = hf().evaluate(WATER, forces=False)
    assert result.recovery_steps == ["diis", "stability:stable lambda_min=-9.00e-04"]
    assert seen == {"calls": 1, "follows": 0}


def test_lambda_below_threshold_is_followed(monkeypatch: pytest.MonkeyPatch) -> None:
    """lambda_min = -1.1e-3 (< -1e-3): followed (progressive), then stable."""
    seen = inject(monkeypatch, [-1.1e-3, 2e-2], [1e-3])
    result = hf().evaluate(WATER, forces=False)
    assert result.recovery_steps == [
        "diis",
        "stability:followed lambda_min=-1.10e-03",
        "stability:stable lambda_min=+2.00e-02",
    ]
    assert seen == {"calls": 2, "follows": 1}


def test_a_keyed_threshold_changes_the_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    """With stability_tol 1e-4, lambda_min = -9e-4 is unstable."""
    inject(monkeypatch, [-9e-4, 1e-2], [1e-3])
    steps = hf(stability_tol=1e-4).evaluate(WATER, forces=False).recovery_steps
    assert steps[1] == "stability:followed lambda_min=-9.00e-04"


def test_follow_without_progress_ends_as_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Always 'unstable', but the follow lowers E by 1e-7 < 1e-6: stable, recorded, no error."""
    seen = inject(monkeypatch, [-1e-2], [1e-7])
    result = hf().evaluate(WATER, forces=False)
    assert result.recovery_steps == [
        "diis",
        "stability:followed lambda_min=-1.00e-02",
        "stability:followed_no_progress dE=-1.0e-07",
    ]
    assert seen == {"calls": 1, "follows": 1}


def test_no_progress_after_a_progressive_follow_ends_as_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One progressive follow, then one without progress: stable, not an error (budget is 2)."""
    seen = inject(monkeypatch, [-1e-2], [1e-3, 5e-8])
    result = hf().evaluate(WATER, forces=False)
    assert [s.split(" ")[0] for s in result.recovery_steps] == [
        "diis",
        "stability:followed",
        "stability:followed",
        "stability:followed_no_progress",
    ]
    assert seen["follows"] == 2


def test_progressive_follows_past_the_budget_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Always unstable with progressive follows: ScfConvergenceError after 2, naming lambda_min."""
    inject(monkeypatch, [-1e-2], [1e-3])
    with pytest.raises(ScfConvergenceError, match=r"after 2 follows \(lambda_min=-1\.00e-02\)"):
        hf().evaluate(WATER, forces=False)


def test_an_energy_rise_is_not_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    """A follow that RAISES the energy ends as no-progress (dE positive), never as progress."""
    inject(monkeypatch, [-1e-2], [-2e-6])
    steps = hf().evaluate(WATER, forces=False).recovery_steps
    assert steps[-1] == "stability:followed_no_progress dE=2.0e-06"


def pyscf_logged_lambda(mf: Any) -> float:
    """The lowest eigenvalue PySCF's own *_internal logs at the same Davidson tol."""
    from pyscf.scf import stability

    buf = io.StringIO()
    mf.stdout, mf.verbose = buf, 4
    internal = stability.uhf_internal if mf.mo_occ.ndim == 2 else stability.rhf_internal
    internal(mf, tol=STABILITY_DAVIDSON_TOL)
    mf.verbose = 0
    found = re.search(r"_internal: lowest eigs of H = \[\s*([-+0-9.eE]+)", buf.getvalue())
    assert found, buf.getvalue()
    return float(found.group(1))


@pytest.mark.parametrize(("state", "scf_type"), [(WATER, "RHF"), (HYDROXYL, "UHF")])
def test_lambda_min_replays_pyscf_internal(state: MolecularState, scf_type: str) -> None:
    """lowest_internal's lambda_min equals PySCF 2.15.1's own internal analysis (<= 1e-8)."""
    from pyscf import gto, scf

    mol = gto.M(
        atom=[(s, tuple(c)) for s, c in zip(state.symbols, state.coordinates, strict=True)],
        basis="sto-3g",
        spin=state.spin_multiplicity - 1,
        verbose=0,
    )
    mf = (scf.UHF if scf_type == "UHF" else scf.RHF)(mol)
    mf.conv_tol = 1e-12
    mf.kernel()
    lam, mo = lowest_internal(mf)
    assert abs(lam - pyscf_logged_lambda(mf)) <= 1e-8
    assert len(mo) == (2 if scf_type == "UHF" else mf.mo_coeff.shape[0])
