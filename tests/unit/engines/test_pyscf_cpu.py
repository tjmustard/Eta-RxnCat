"""Tests for the PySCF engine's CPU path against PySCF's own API on the same input (slice 06)."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import (
    ENGINE_IMPL_KEY,
    EngineInputError,
    EngineUnavailableError,
    PySCFEngine,
    ScfConvergenceError,
    library_version,
)
from eta_rxncat.engines.pyscf_gpu_cpu import DIELECTRICS, HESSIAN_SUPPORT, hessian_method_for
from eta_rxncat.engines.pyscf_gpu_cpu import engine as engine_module
from eta_rxncat.engines.pyscf_gpu_cpu.engine import ANALYTIC_REFUSED
from eta_rxncat.store import build_stage_key

REPO = Path(__file__).resolve().parents[3]
SUPPORT = REPO / "docs/prd/v0.2.0/evidence/pyscf-cpu-support.json"
AUX = "def2-universal-jkfit"


@pytest.fixture(scope="module")
def ps() -> SimpleNamespace:
    """PySCF modules, imported at test time (pyscf is in the base install)."""
    from pyscf import dft, gto, scf

    return SimpleNamespace(gto=gto, scf=scf, dft=dft)


def stage(method: str = "hf", basis: str = "sto-3g", **kwargs: Any) -> StageConfig:
    """A PySCF single-point stage."""
    return StageConfig(
        kind="single_point", engine="pyscf_gpu_cpu", method=method, basis=basis, **kwargs
    )


def engine(
    method: str = "hf", basis: str = "sto-3g", runtime: dict[str, Any] | None = None, **kwargs: Any
) -> PySCFEngine:
    """A CPU PySCF engine for the given stage fields (``device="cpu"`` unless overridden)."""
    return PySCFEngine.from_stage(
        stage(method, basis, **kwargs), **{"device": "cpu", **(runtime or {})}
    )


def plain_mf(
    ps: SimpleNamespace,
    state: MolecularState,
    method: str,
    basis: str,
    ecp: str | None = None,
    solvent_eps: float | None = None,
    pcm: str | None = None,
) -> Any:
    """Plain PySCF built the way the engine documents it, without the engine."""
    mol = ps.gto.M(
        atom=[(s, tuple(c)) for s, c in zip(state.symbols, state.coordinates, strict=True)],
        unit="Angstrom",
        basis=basis,
        ecp=ecp,
        charge=state.charge,
        spin=state.spin_multiplicity - 1,
        verbose=0,
    )
    if method == "hf":
        mf = ps.scf.RHF(mol) if mol.spin == 0 else ps.scf.UHF(mol)
    else:
        mf = ps.dft.RKS(mol) if mol.spin == 0 else ps.dft.UKS(mol)
        mf.xc = method
        mf.grids.level = 3
    mf = mf.density_fit(auxbasis=AUX)
    if pcm is not None:
        mf = mf.PCM()
        mf.with_solvent.method = pcm
        mf.with_solvent.eps = solvent_eps
    mf.conv_tol = 1e-10
    mf.max_cycle = 100
    mf.kernel()
    assert mf.converged
    return mf


def flat(rows: list[list[float]] | None) -> list[float]:
    """Flatten a matrix."""
    assert rows is not None
    return [v for row in rows for v in row]


def moved(state: MolecularState, index: int, delta_bohr: float) -> MolecularState:
    """``state`` with coordinate ``index`` (3 * atom + axis) moved by ``delta_bohr``."""
    coords = [row[:] for row in state.coordinates]
    coords[index // 3][index % 3] += delta_bohr * 0.529177210903
    return MolecularState(
        symbols=state.symbols,
        coordinates=coords,
        charge=state.charge,
        spin_multiplicity=state.spin_multiplicity,
    )


# ---------------------------------------------------------------- reference (default suite)


def test_reference_hf_sto3g_water(ps: SimpleNamespace, test_set: dict[str, MolecularState]) -> None:
    """Energy, gradient and Hessian equal plain PySCF (DF, same auxbasis) on HF/sto-3g water."""
    water = test_set["water"]
    result = engine().evaluate(water, hessian=True)
    mf = plain_mf(ps, water, "hf", "sto-3g")
    assert abs(result.energy_hartree - mf.e_tot) <= 1e-10
    grad = mf.nuc_grad_method().kernel()
    assert (
        max(
            abs(f + g)
            for f, g in zip(flat(result.forces_hartree_per_bohr), grad.reshape(-1), strict=True)
        )
        <= 1e-8
    )
    raw = mf.Hessian().kernel().transpose(0, 2, 1, 3).reshape(9, 9)
    ref = 0.5 * (raw + raw.T)
    hess = result.hessian_hartree_per_bohr2
    assert hess is not None and result.hessian_method == "analytic"
    assert max(abs(hess[i][j] - ref[i, j]) for i in range(9) for j in range(9)) <= 1e-8
    assert all(hess[i][j] == hess[j][i] for i in range(9) for j in range(9))
    assert result.device == "cpu" and result.device_reason is None
    assert verdicts(result.recovery_steps) == ["diis", "stability:stable"]
    assert result.engine.name == "pyscf_gpu_cpu" and result.engine.version == library_version(
        "pyscf"
    )
    assert result.engine.model is None


# ---------------------------------------------------------------- options and stage


def test_resolved_options() -> None:
    """Every keyed option is filled; ecp stays 'auto'; the small basis follows the basis."""
    assert engine().stage.options == {
        "density_fit": True,
        "auxbasis": AUX,
        "ecp": "auto",
        "grids_level": 3,
        "conv_tol": 1e-10,
        "init_guess": "minao",
        "pcm_method": "C-PCM",
        "ladder_small_basis": "sto-3g",
        "stability": "internal",
        "stability_tol": 1e-3,
        "stability_noise_eh": 1e-6,
        "fd_step_bohr": 0.005,
        "hessian_mode": "auto",
        ENGINE_IMPL_KEY: 2,
    }
    assert engine(basis="def2-svp").stage.options["ladder_small_basis"] == "minao"
    assert engine(basis="DEF2-TZVP").stage.options["ladder_small_basis"] == "minao"
    assert engine(method="B3LYP").stage.method == "b3lyp"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("density_fit", False),
        ("auxbasis", "def2-svp-jkfit"),
        ("ecp", "def2-svp"),
        ("grids_level", 4),
        ("conv_tol", 1e-9),
        ("init_guess", "atom"),
        ("pcm_method", "IEF-PCM"),
        ("ladder_small_basis", "minao"),
        ("fd_step_bohr", 0.004),
        ("hessian_mode", "fd_gradients"),
    ],
)
def test_every_keyed_option_changes_the_key(
    test_set: dict[str, MolecularState], key: str, value: Any
) -> None:
    """Each keyed option, set to a non-default value, gives a different cache key."""
    water = test_set["water"]
    base = engine()
    other = engine(options={key: value})
    k0 = build_stage_key(water, base.stage, base.identity).key
    k1 = build_stage_key(water, other.stage, other.identity).key
    assert k0 != k1


def test_implicit_and_explicit_defaults_key_equal(test_set: dict[str, MolecularState]) -> None:
    """A default given explicitly keys the same as the implicit default."""
    water = test_set["water"]
    a = engine()
    b = engine(options={"density_fit": True, "ladder_small_basis": "sto-3g", "ecp": "auto"})
    assert build_stage_key(water, a.stage, a.identity) == build_stage_key(
        water, b.stage, b.identity
    )


@pytest.mark.parametrize(
    ("kwargs", "runtime", "error", "match"),
    [
        ({"options": {"stability": "external"}}, {}, EngineInputError, "stability"),
        ({"options": {"init_guess": "sad"}}, {}, EngineInputError, "init_guess"),
        ({"options": {"pcm_method": "COSMO"}}, {}, EngineInputError, "pcm_method"),
        ({"options": {"conv_tol": 0.0}}, {}, EngineInputError, "conv_tol"),
        ({"options": {"fd_step_bohr": -1.0}}, {}, EngineInputError, "fd_step_bohr"),
        ({"options": {"grids_level": 12}}, {}, EngineInputError, "grids_level"),
        ({"options": {"nope": 1}}, {}, EngineInputError, "nope"),
        ({"options": {"hessian_mode": "numeric"}}, {}, EngineInputError, "hessian_mode"),
        ({"method": "nosuchxc"}, {}, EngineInputError, "nosuchxc"),
        ({}, {"device": "cuda"}, EngineUnavailableError, "CUDA"),
        ({}, {"device": "tpu"}, EngineInputError, "tpu"),
        ({}, {"ladder_max_cycle": 0}, EngineInputError, "ladder_max_cycle"),
        ({}, {"max_memory_mb": True}, EngineInputError, "max_memory_mb"),
        ({}, {"threads": 2}, EngineInputError, "threads"),
    ],
)
def test_bad_stage_or_runtime(
    monkeypatch: pytest.MonkeyPatch,
    kwargs: dict[str, Any],
    runtime: dict[str, Any],
    error: type[Exception],
    match: str,
) -> None:
    """Disallowed or mistyped options, unknown xc, cuda (slice 07) and bad runtime arguments.

    The GPU lookup is faked to "no GPU stack", so the cuda case refuses on every host, GPU hosts
    included (slice 11); the real-GPU path is covered by ``test_pyscf_gpu.py``.
    """
    monkeypatch.setattr(engine_module, "gpu_modules", lambda: None)
    data: dict[str, Any] = {"method": "hf", "basis": "sto-3g"}
    data.update(kwargs)
    method, basis = data.pop("method"), data.pop("basis")
    with pytest.raises(error, match=match):
        PySCFEngine.from_stage(stage(method, basis, **data), **runtime)


def test_runtime_arguments_are_not_keyed() -> None:
    """device, max_memory_mb and ladder_max_cycle never reach the options."""
    eng = engine(runtime={"device": "cpu", "max_memory_mb": 2000, "ladder_max_cycle": 7})
    assert eng.stage == engine().stage and eng.ladder_max_cycle == 7


def test_unknown_basis_refused(test_set: dict[str, MolecularState]) -> None:
    """A basis PySCF does not know is an EngineInputError at evaluate."""
    with pytest.raises(EngineInputError, match="no-such-basis"):
        engine(basis="no-such-basis").evaluate(test_set["water"])


# ---------------------------------------------------------------- charge, spin, ECP


def test_literal_charge_spin_mapping(test_set: dict[str, MolecularState]) -> None:
    """R4: hydroxide charge -1 spin 0 RKS; hydroxyl spin 1 UKS; the Pd anion has 86 electrons."""
    from pyscf import dft

    eng = engine(method="b3lyp", basis="def2-svp")
    for case, charge, spin, cls in (
        ("hydroxide", -1, 0, dft.rks.RKS),
        ("hydroxyl", 0, 1, dft.uks.UKS),
    ):
        s = test_set[case]
        rs = eng.resolved_stage_for(s)
        mol = eng._build_mol(s, "def2-svp", str(rs.options["ecp"]))
        assert (mol.charge, mol.spin) == (charge, spin)
        assert isinstance(eng._make_mf(mol, rs), cls)
    pd = test_set["pd_anion"]
    rs = eng.resolved_stage_for(pd)
    mol = eng._build_mol(pd, "def2-svp", str(rs.options["ecp"]))
    assert mol.nelectron == 86 and mol.charge == -1 and mol.spin == 0
    all_electron = eng._build_mol(pd, "def2-svp", "none")
    assert all_electron.nelectron == 114


def test_hf_mapping_classes(test_set: dict[str, MolecularState]) -> None:
    """Method 'hf' gives RHF for a singlet and UHF for a doublet."""
    from pyscf import scf

    eng = engine()
    for case, cls in (("water", scf.hf.RHF), ("hydroxyl", scf.uhf.UHF)):
        s = test_set[case]
        mol = eng._build_mol(s, "sto-3g", "none")
        assert isinstance(eng._make_mf(mol, eng.resolved_stage_for(s)), cls)


def test_doublet_and_anion_differ(test_set: dict[str, MolecularState]) -> None:
    """Behavioural R4: the hydroxyl doublet and the hydroxide anion give different energies."""
    eng = engine()
    radical = eng.evaluate(test_set["hydroxyl"], forces=False)
    anion = eng.evaluate(test_set["hydroxide"], forces=False)
    assert abs(radical.energy_hartree - anion.energy_hartree) > 1e-2


def test_ecp_rule(test_set: dict[str, MolecularState]) -> None:
    """def2 + Z > 36: ecp = basis; water: none; non-def2 + Z > 36: refused; never written back."""
    pd = test_set["pd_anion"]
    eng = engine(method="b3lyp", basis="def2-svp")
    assert eng.resolved_stage_for(pd).options["ecp"] == "def2-svp"
    assert eng.stage.options["ecp"] == "auto"
    assert eng.resolved_stage_for(test_set["water"]).options["ecp"] == "none"
    with pytest.raises(EngineInputError, match="not def2"):
        engine(method="b3lyp", basis="cc-pvdz").resolved_stage_for(pd)
    with pytest.raises(EngineInputError, match="needs its ECP"):
        engine(method="b3lyp", basis="def2-svp", options={"ecp": "none"}).resolved_stage_for(pd)
    explicit = engine(method="b3lyp", basis="cc-pvdz", options={"ecp": "def2-svp"})
    assert explicit.resolved_stage_for(pd).options["ecp"] == "def2-svp"
    assert explicit.stage.options["ecp"] == "def2-svp"
    with pytest.raises(EngineInputError, match="no-such-ecp"):
        engine(basis="def2-svp", options={"ecp": "no-such-ecp"}).resolved_stage_for(pd)
    assert (
        engine(options={"ecp": "none"}).resolved_stage_for(test_set["water"]).options["ecp"]
        == "none"
    )


# ---------------------------------------------------------------- ladder and stability


def test_ladder_recovers_from_diis_failure(
    ps: SimpleNamespace, test_set: dict[str, MolecularState]
) -> None:
    """ladder_max_cycle=1 fails DIIS (its budget only); a later rung converges (<= 1e-8)."""
    water = test_set["water"]
    result = engine(runtime={"ladder_max_cycle": 1}).evaluate(water, forces=False)
    steps = result.recovery_steps
    assert (
        steps[0] == "diis"
        and steps[1] == "level_shift"
        and steps[-1].startswith("stability:stable ")
    )
    assert set(steps[:-1]) <= {"diis", "level_shift", "soscf", "small_basis_projection"}
    assert abs(result.energy_hartree - plain_mf(ps, water, "hf", "sto-3g").e_tot) <= 1e-8


@pytest.mark.parametrize(
    ("failures", "expected"),
    [
        (0, ["diis"]),
        (1, ["diis", "level_shift"]),
        (2, ["diis", "level_shift", "soscf"]),
        (3, ["diis", "level_shift", "soscf", "small_basis_projection"]),
    ],
    ids=["diis", "level_shift", "soscf", "small_basis_projection"],
)
def test_each_rung_recovers(
    ps: SimpleNamespace,
    test_set: dict[str, MolecularState],
    monkeypatch: pytest.MonkeyPatch,
    failures: int,
    expected: list[str],
) -> None:
    """With the first k rungs forced to fail, rung k+1 converges to the plain energy."""
    water = test_set["water"]
    real = PySCFEngine._kernel
    calls = {"n": 0}

    def kernel(self: PySCFEngine, mf: Any, dm0: Any = None) -> bool:
        calls["n"] += 1
        converged = real(self, mf, dm0)
        return converged and calls["n"] > failures

    monkeypatch.setattr(PySCFEngine, "_kernel", kernel)
    result = engine().evaluate(water, forces=False)
    assert verdicts(result.recovery_steps) == [*expected, "stability:stable"]
    assert abs(result.energy_hartree - plain_mf(ps, water, "hf", "sto-3g").e_tot) <= 1e-8


def test_every_rung_failing_raises(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every rung reporting not converged -> ScfConvergenceError with all four steps."""
    real = PySCFEngine._kernel

    def never(self: PySCFEngine, mf: Any, dm0: Any = None) -> bool:
        real(self, mf, dm0)
        return False

    monkeypatch.setattr(PySCFEngine, "_kernel", never)
    with pytest.raises(ScfConvergenceError) as info:
        engine().evaluate(test_set["water"])
    assert info.value.steps == ("diis", "level_shift", "soscf", "small_basis_projection")


def fake_stability(
    monkeypatch: pytest.MonkeyPatch, lambdas: list[float], drop_eh: float = 1e-3
) -> dict[str, int]:
    """Inject lambda_min values in turn (last repeats); each follow lowers E by ``drop_eh`` (R54).

    The follow's SCF really runs (from the same orbitals); its energy is then lowered by
    ``drop_eh`` per follow so far, so a follow is "progressive" when ``drop_eh`` exceeds the
    noise floor (``stability_noise_eh``).
    """
    seen = {"calls": 0, "follows": 0}
    real_kernel = PySCFEngine._kernel

    def lowest(mf: Any, tol: float = 1e-6) -> tuple[float, Any]:
        index = min(seen["calls"], len(lambdas) - 1)
        seen["calls"] += 1
        return lambdas[index], mf.mo_coeff

    def kernel(self: PySCFEngine, mf: Any, dm0: Any = None) -> bool:
        ok = real_kernel(self, mf, dm0)
        if dm0 is not None and seen["calls"]:  # a stability follow
            seen["follows"] += 1
            mf.e_tot = float(mf.e_tot) - drop_eh * seen["follows"]
        return ok

    monkeypatch.setattr(engine_module, "lowest_internal", lowest)
    monkeypatch.setattr(PySCFEngine, "_kernel", kernel)
    return seen


def verdicts(steps: Any) -> list[str]:
    """Recovery steps with the R54 ``lambda_min=`` / ``dE=`` values stripped."""
    return [step.split(" ")[0] for step in steps]


def test_stability_follow_is_recorded(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unstable once, then stable -> 'followed' then 'stable', each with lambda_min."""
    seen = fake_stability(monkeypatch, [-1e-2, 1e-4])
    result = engine().evaluate(test_set["water"], forces=False)
    assert result.recovery_steps == [
        "diis",
        "stability:followed lambda_min=-1.00e-02",
        "stability:stable lambda_min=+1.00e-04",
    ]
    assert seen["calls"] == 2


def test_always_unstable_raises(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always unstable with progressive follows -> ScfConvergenceError after exactly 2 follows."""
    seen = fake_stability(monkeypatch, [-1e-2])
    with pytest.raises(ScfConvergenceError, match="unstable") as info:
        engine().evaluate(test_set["water"], forces=False)
    assert verdicts(info.value.steps) == ["diis", "stability:followed", "stability:followed"]
    assert seen["calls"] == 3


def test_stability_uses_the_internal_lambda_min(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One lowest_internal call on the converged mean field; its value is recorded."""
    real = engine_module.lowest_internal
    seen: list[float] = []

    def spy(mf: Any, tol: float = 1e-6) -> tuple[float, Any]:
        lam, mo = real(mf)
        seen.append(lam)
        return lam, mo

    monkeypatch.setattr(engine_module, "lowest_internal", spy)
    result = engine().evaluate(test_set["water"], forces=False)
    assert len(seen) == 1 and seen[0] > 0
    assert result.recovery_steps[-1] == f"stability:stable lambda_min={seen[0]:+.2e}"


# ---------------------------------------------------------------- solvation


def pcm_stage(**solvation: Any) -> PySCFEngine:
    """HF/sto-3g with PCM solvation."""
    return engine(solvation=Solvation(model="pcm", **solvation))


@pytest.mark.slow
def test_pcm_solvent_name_equals_dielectric(test_set: dict[str, MolecularState]) -> None:
    """C-PCM with solvent 'water' equals dielectric 78.3553 (<= 1e-10) and differs from gas."""
    water = test_set["water"]
    by_name = pcm_stage(solvent="water").evaluate(water, forces=False).energy_hartree
    by_eps = pcm_stage(dielectric=78.3553).evaluate(water, forces=False).energy_hartree
    gas = engine().evaluate(water, forces=False).energy_hartree
    assert abs(by_name - by_eps) <= 1e-10
    assert abs(by_name - gas) > 1e-4


@pytest.mark.slow
def test_pcm_matches_plain_pyscf(ps: SimpleNamespace, test_set: dict[str, MolecularState]) -> None:
    """C-PCM and IEF-PCM energies equal plain PySCF on the same input."""
    water = test_set["water"]
    for method in ("C-PCM", "IEF-PCM"):
        got = engine(
            solvation=Solvation(model="pcm", solvent="water"), options={"pcm_method": method}
        )
        ref = plain_mf(ps, water, "hf", "sto-3g", solvent_eps=78.3553, pcm=method).e_tot
        assert abs(got.evaluate(water, forces=False).energy_hartree - ref) <= 1e-10


@pytest.mark.slow
def test_ddcosmo_runs_and_dielectric_wins(test_set: dict[str, MolecularState]) -> None:
    """DdCOSMO runs; an explicit dielectric wins over the solvent name."""
    water = test_set["water"]
    ddc = engine(solvation=Solvation(model="ddcosmo", solvent="water")).evaluate(water, forces=True)
    assert ddc.forces_hartree_per_bohr is not None
    toluene = engine(solvation=Solvation(model="ddcosmo", solvent="toluene")).evaluate(
        water, forces=False
    )
    toluene_eps = engine(
        solvation=Solvation(model="ddcosmo", solvent="water", dielectric=2.3741)
    ).evaluate(water, forces=False)
    assert abs(toluene.energy_hartree - toluene_eps.energy_hartree) <= 1e-10
    assert abs(toluene.energy_hartree - ddc.energy_hartree) > 1e-4


def test_solvent_name_normalised_and_unknown_refused() -> None:
    """'Water' resolves to 'water' in engine.stage; an unknown solvent is an EngineInputError."""
    assert pcm_stage(solvent="Water").stage.solvation.solvent == "water"
    with pytest.raises(EngineInputError, match="unknown solvent 'unobtainium'"):
        pcm_stage(solvent="unobtainium")


def test_alpb_is_not_a_pyscf_model() -> None:
    """ALPB pairs with xtb only (core rejects it for pyscf_gpu_cpu before the engine)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="needs engine 'xtb_subprocess'"):
        stage(solvation=Solvation(model="alpb", solvent="water"))


def test_solvent_table_matches_pyscf_copy() -> None:
    """Every value equals PySCF's shipped Minnesota-database epsilon; required names present."""
    from pyscf.solvent._solvent_data import solvent_db

    lower = {k.lower(): v for k, v in solvent_db.items() if isinstance(v, list)}
    for name, eps in DIELECTRICS.items():
        assert lower[name][5] == eps, name
    required = {
        "water",
        "toluene",
        "acetonitrile",
        "methanol",
        "ethanol",
        "dichloromethane",
        "tetrahydrofuran",
        "dimethylsulfoxide",
        "benzene",
        "chloroform",
        "acetone",
        "n,n-dimethylformamide",
    }
    assert required <= set(DIELECTRICS)
    assert DIELECTRICS["water"] == 78.3553 and DIELECTRICS["toluene"] == 2.3741


# ---------------------------------------------------------------- Hessian support matrix


def test_support_matrix_matches_engine() -> None:
    """The recorded support matrix exists, and every analytic/FD choice in the engine matches it."""
    data = json.loads(SUPPORT.read_text(encoding="utf-8"))
    assert data["pyscf_version"] == library_version("pyscf")
    assert data["rule"] == {f"{f}/{s}": c for (f, s), c in HESSIAN_SUPPORT.items()}
    assert len(data["rows"]) == 36
    for row in data["rows"]:
        solvation = {
            "none": Solvation(),
            "pcm": Solvation(model="pcm", dielectric=78.3553),
            "ddcosmo": Solvation(model="ddcosmo", dielectric=78.3553),
        }[row["solvent"]]
        choice = hessian_method_for(stage(row["method"], row["basis"], solvation=solvation))
        assert row["engine_choice"] == choice, row
        if choice == "analytic":
            assert row["analytic_runs"] and row["max_abs_analytic_minus_fd"] <= 1e-4, row
    ddcosmo = [r for r in data["rows"] if r["solvent"] == "ddcosmo"]
    assert ddcosmo and not any(r["analytic_runs"] for r in ddcosmo)


@pytest.mark.parametrize(
    ("method", "model", "expected"),
    [
        ("hf", "none", "analytic"),
        ("hf", "pcm", "analytic"),
        ("hf", "ddcosmo", "finite_difference"),
        ("b3lyp", "none", "finite_difference"),
        ("pbe", "pcm", "finite_difference"),
        ("lda", "ddcosmo", "finite_difference"),
    ],
)
def test_hessian_rule(method: str, model: str, expected: str) -> None:
    """auto: HF analytic (ddCOSMO FD); every KS functional FD; fd_gradients always FD."""
    solvation = Solvation() if model == "none" else Solvation(model=model, dielectric=10.0)
    assert hessian_method_for(stage(method, "sto-3g", solvation=solvation)) == expected
    forced = stage(method, "sto-3g", solvation=solvation, options={"hessian_mode": "fd_gradients"})
    assert hessian_method_for(forced) == "finite_difference"
    explicit = stage(method, "sto-3g", solvation=solvation, options={"hessian_mode": "analytic"})
    if expected == "analytic":
        assert hessian_method_for(explicit) == "analytic"
        assert PySCFEngine.from_stage(explicit).stage.options["hessian_mode"] == "analytic"
    else:
        with pytest.raises(EngineInputError, match=re.escape(ANALYTIC_REFUSED)):
            PySCFEngine.from_stage(explicit)


@pytest.mark.slow
def test_fd_gradients_forces_fd_for_hf(test_set: dict[str, MolecularState]) -> None:
    """hessian_mode='fd_gradients' gives an FD Hessian for HF, close to the analytic one."""
    water = test_set["water"]
    analytic = engine().evaluate(water, hessian=True)
    forced = engine(options={"hessian_mode": "fd_gradients"}).evaluate(water, hessian=True)
    assert analytic.hessian_method == "analytic"
    assert forced.hessian_method == "finite_difference"
    a, f = analytic.hessian_hartree_per_bohr2, forced.hessian_hartree_per_bohr2
    assert a is not None and f is not None
    assert max(abs(a[i][j] - f[i][j]) for i in range(9) for j in range(9)) <= 1e-4


@pytest.mark.slow
def test_ks_hessian_is_fd_hf_is_analytic(test_set: dict[str, MolecularState]) -> None:
    """The engine reports the method it used: HF analytic, KS finite_difference (sto-3g water)."""
    water = test_set["water"]
    hf = engine().evaluate(water, hessian=True)
    ks = engine(method="lda").evaluate(water, hessian=True)
    assert hf.hessian_method == "analytic" and ks.hessian_method == "finite_difference"
    h = ks.hessian_hartree_per_bohr2
    assert h is not None and all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    assert ks.hessian_max_asymmetry is not None and ks.hessian_max_asymmetry < 1e-3


@pytest.mark.slow
def test_ddcosmo_hessian_is_finite_difference(test_set: dict[str, MolecularState]) -> None:
    """DdCOSMO has no analytic Hessian in PySCF 2.15.1, so the engine uses FD of gradients."""
    result = engine(solvation=Solvation(model="ddcosmo", solvent="water")).evaluate(
        test_set["water"], hessian=True
    )
    h = result.hessian_hartree_per_bohr2
    assert h is not None and result.hessian_method == "finite_difference"
    assert all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    assert result.hessian_max_asymmetry is not None and result.hessian_max_asymmetry < 1e-4


def test_results_do_not_alias(test_set: dict[str, MolecularState]) -> None:
    """Mutating one result's forces does not change the next result."""
    eng = engine()
    first = eng.evaluate(test_set["water"])
    assert first.forces_hartree_per_bohr is not None
    keep = first.forces_hartree_per_bohr[0][2]
    first.forces_hartree_per_bohr[0][2] = 9.0
    second = eng.evaluate(test_set["water"]).forces_hartree_per_bohr
    assert second is not None and abs(second[0][2] - keep) <= 1e-10
    assert second[0][2] != 9.0


# ---------------------------------------------------------------- slow: B3LYP / def2-SVP


@pytest.mark.slow
@pytest.mark.parametrize("case", ["water", "pd_anion"])
def test_slow_b3lyp_energy_matches_pyscf(
    ps: SimpleNamespace, test_set: dict[str, MolecularState], case: str
) -> None:
    """B3LYP/def2-SVP energies equal plain PySCF (<= 1e-8 Eh); the Pd anion is stable."""
    s = test_set[case]
    result = engine(method="b3lyp", basis="def2-svp").evaluate(s, forces=False)
    ecp = "def2-svp" if case == "pd_anion" else None
    assert abs(result.energy_hartree - plain_mf(ps, s, "b3lyp", "def2-svp", ecp=ecp).e_tot) <= 1e-8
    assert result.recovery_steps[-1].startswith("stability:stable ")


@pytest.mark.slow
@pytest.mark.parametrize(
    ("case", "indices"),
    [("water", list(range(9))), ("pd_anion", [0, 1, 2, 12, 13, 14])],
    ids=["water-all", "pd-anion-pd-and-first-c"],
)
def test_slow_gradient_vs_fd_energy(
    test_set: dict[str, MolecularState], case: str, indices: list[int]
) -> None:
    """Analytic forces equal -central FD of the energy (step 1e-3 Bohr) to <= 1e-5 Eh/Bohr."""
    s = test_set[case]
    eng = engine(method="b3lyp", basis="def2-svp")
    forces = flat(eng.evaluate(s).forces_hartree_per_bohr)
    step = 1e-3
    for i in indices:
        e_plus = eng.evaluate(moved(s, i, step), forces=False).energy_hartree
        e_minus = eng.evaluate(moved(s, i, -step), forces=False).energy_hartree
        fd_force = -(e_plus - e_minus) / (2 * step)
        assert abs(forces[i] - fd_force) <= 1e-5, (case, i, forces[i], fd_force)


def fd_of_gradients(eng: PySCFEngine, s: MolecularState, step: float = 5e-3) -> list[list[float]]:
    """Symmetrised central differences of the engine's analytic forces (Eh/Bohr^2)."""
    n = 3 * len(s.symbols)
    rows: list[list[float]] = []
    for i in range(n):
        plus = flat(eng.evaluate(moved(s, i, step)).forces_hartree_per_bohr)
        minus = flat(eng.evaluate(moved(s, i, -step)).forces_hartree_per_bohr)
        rows.append([-(p - m) / (2 * step) for p, m in zip(plus, minus, strict=True)])
    return [[(rows[i][j] + rows[j][i]) / 2 for j in range(n)] for i in range(n)]


@pytest.mark.slow
def test_slow_hf_analytic_hessian_vs_fd_gradients(test_set: dict[str, MolecularState]) -> None:
    """Proof (i): the analytic HF/def2-SVP water Hessian equals FD of gradients (<= 1e-4)."""
    water = test_set["water"]
    eng = engine(method="hf", basis="def2-svp")
    result = eng.evaluate(water, hessian=True)
    assert result.hessian_method == "analytic"
    h = result.hessian_hartree_per_bohr2
    assert h is not None
    fd = fd_of_gradients(eng, water)
    assert max(abs(h[i][j] - fd[i][j]) for i in range(9) for j in range(9)) <= 1e-4


@pytest.mark.slow
def test_slow_b3lyp_fd_hessian_vs_energy_second_differences(
    test_set: dict[str, MolecularState],
) -> None:
    """Proof (ii): the B3LYP water FD Hessian agrees with energy-only second differences.

    B3LYP/def2-SVP; no gradients in the reference; <= 1e-4 Eh/Bohr^2 on diagonal and
    off-diagonal elements.
    """
    water = test_set["water"]
    eng = engine(method="b3lyp", basis="def2-svp")
    result = eng.evaluate(water, hessian=True)
    assert result.hessian_method == "finite_difference"
    h = result.hessian_hartree_per_bohr2
    assert h is not None
    step = 5e-3

    def energy(shifts: dict[int, float]) -> float:
        s = water
        for index, delta in shifts.items():
            s = moved(s, index, delta)
        return eng.evaluate(s, forces=False).energy_hartree

    e0 = energy({})
    for i, j in [(2, 2), (4, 4), (5, 5), (2, 5), (4, 5), (1, 7)]:
        if i == j:
            second = (energy({i: step}) - 2 * e0 + energy({i: -step})) / step**2
        else:
            second = (
                energy({i: step, j: step})
                - energy({i: step, j: -step})
                - energy({i: -step, j: step})
                + energy({i: -step, j: -step})
            ) / (4 * step**2)
        assert abs(h[i][j] - second) <= 1e-4, (i, j, h[i][j], second)


@pytest.mark.slow
def test_slow_hbr_analytic_ks_hessian_canary(ps: SimpleNamespace) -> None:
    """Proof (iii), canary: PySCF 2.15.1's default analytic B3LYP HBr Hessian (grid 3) is wrong.

    Grid response is off (the CPU default; turning it on raises NotImplementedError). Measured gap
    0.24 Eh/Bohr^2. If this fails, PySCF has fixed it: revisit R41 and re-measure the support
    matrix before allowing analytic KS Hessians.
    """
    hbr = MolecularState(
        symbols=["H", "Br"],
        coordinates=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.41]],
        charge=0,
        spin_multiplicity=1,
    )
    eng = engine(method="b3lyp", basis="def2-svp")
    rs = eng.resolved_stage_for(hbr)
    mol = eng._build_mol(hbr, "def2-svp", str(rs.options["ecp"]))
    mf, steps = eng._ladder(hbr, mol, rs)
    mf = eng._stability(mf, steps, rs)
    analytic, _ = eng._analytic_hessian(mf, 2)
    result = eng.evaluate(hbr, hessian=True)
    fd = result.hessian_hartree_per_bohr2
    assert fd is not None and result.hessian_method == "finite_difference"
    gap = max(abs(analytic[i][j] - fd[i][j]) for i in range(6) for j in range(6))
    print(
        f"HBr B3LYP/def2-SVP grid 3: max|analytic - FD| = {gap:.3e} "
        f"(H_zz {analytic[5][5]:.6f} vs {fd[5][5]:.6f})"
    )
    assert gap > 1e-2, f"default analytic KS Hessian now agrees; revisit R41 (gap {gap:.2e})"


@pytest.mark.slow
def test_slow_b3lyp_pcm_solvent_vs_dielectric(test_set: dict[str, MolecularState]) -> None:
    """B3LYP/def2-SVP C-PCM: solvent 'water' equals dielectric 78.3553 and differs from gas."""
    water = test_set["water"]
    by_name = engine(
        method="b3lyp", basis="def2-svp", solvation=Solvation(model="pcm", solvent="water")
    )
    by_eps = engine(
        method="b3lyp", basis="def2-svp", solvation=Solvation(model="pcm", dielectric=78.3553)
    )
    gas = engine(method="b3lyp", basis="def2-svp")
    e_name = by_name.evaluate(water, forces=False).energy_hartree
    assert abs(e_name - by_eps.evaluate(water, forces=False).energy_hartree) <= 1e-10
    assert abs(e_name - gas.evaluate(water, forces=False).energy_hartree) > 1e-4
