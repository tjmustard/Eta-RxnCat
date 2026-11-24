"""Tests for the pyscf_gpu_cpu ``cartesian_basis`` option (v0.5.0 slice 15, R30, ADR-0041).

CPU tests run in the default suite. ``gpu`` tests compare the GPU with the CPU under the existing
1e-6 Eh parity bound.
"""

import json
from typing import Any

import pytest
from conftest import load_case

from eta_rxncat.core import StageConfig
from eta_rxncat.engines import EngineInputError, PySCFEngine
from eta_rxncat.store import build_stage_key

# Pinned at the slice's Start (1a18618, before the option existed) with the unmodified engine:
# PySCFEngine.from_stage(<stage>, device="cpu"); json.dumps(engine.stage.model_dump(),
# sort_keys=True) and build_stage_key(load_case("water"), engine.stage, engine.identity).key.
START_DEFAULT_STAGE = (
    '{"basis": "sto-3g", "engine": "pyscf_gpu_cpu", "frozen_atom_indices": [], "kind": '
    '"single_point", "method": "hf", "options": {"auxbasis": "def2-universal-jkfit", '
    '"conv_tol": 1e-10, "density_fit": true, "ecp": "auto", "engine_impl": 2, "fd_step_bohr": '
    '0.005, "grids_level": 3, "hessian_mode": "auto", "init_guess": "minao", '
    '"ladder_small_basis": "sto-3g", "pcm_method": "C-PCM", "stability": "internal", '
    '"stability_noise_eh": 1e-06, "stability_tol": 0.001}, "solvation": {"dielectric": null, '
    '"model": "none", "solvent": null}}'
)
START_DEFAULT_KEY = "5b55a9613856d1d893e0dc33e647635af91aa1eb0c9f2532f1b84eefdf2bcb4e"
START_NONDEFAULT_STAGE = (
    '{"basis": "sto-3g", "engine": "pyscf_gpu_cpu", "frozen_atom_indices": [], "kind": '
    '"single_point", "method": "hf", "options": {"auxbasis": "def2-universal-jkfit", '
    '"conv_tol": 1e-10, "density_fit": false, "ecp": "auto", "engine_impl": 2, "fd_step_bohr": '
    '0.005, "grids_level": 4, "hessian_mode": "auto", "init_guess": "minao", '
    '"ladder_small_basis": "sto-3g", "pcm_method": "C-PCM", "stability": "internal", '
    '"stability_noise_eh": 1e-06, "stability_tol": 0.001}, "solvation": {"dielectric": null, '
    '"model": "none", "solvent": null}}'
)
START_NONDEFAULT_KEY = "f51ed412273514e0cb6f7a0c326154653b21a2a7a50a1345311fa2686a70ff71"
NONDEFAULT: dict[str, Any] = {"density_fit": False, "grids_level": 4}


def stage(method: str = "hf", basis: str = "sto-3g", **options: Any) -> StageConfig:
    """A PySCF single-point stage with the given options."""
    return StageConfig(
        kind="single_point", engine="pyscf_gpu_cpu", method=method, basis=basis, options=options
    )


def cpu(method: str = "hf", basis: str = "sto-3g", **options: Any) -> PySCFEngine:
    """A CPU PySCF engine."""
    return PySCFEngine.from_stage(stage(method, basis, **options), device="cpu")


def dumped(engine: PySCFEngine) -> str:
    """The resolved stage as sorted JSON."""
    return json.dumps(engine.stage.model_dump(), sort_keys=True)


# --- MR 2: keys unchanged ---------------------------------------------------------------------


@pytest.mark.parametrize("explicit", [{}, {"cartesian_basis": False}])
def test_default_stage_and_key_equal_start(explicit: dict[str, Any]) -> None:
    """Omitted or explicit False: the resolved stage and key equal Start's, byte for byte."""
    engine = cpu(**explicit)
    assert dumped(engine) == START_DEFAULT_STAGE
    key = build_stage_key(load_case("water"), engine.stage, engine.identity).key
    assert key == START_DEFAULT_KEY
    assert "cartesian_basis" not in engine.stage.options


@pytest.mark.parametrize("explicit", [{}, {"cartesian_basis": False}])
def test_nondefault_stage_and_key_equal_start(explicit: dict[str, Any]) -> None:
    """A stage with non-default options also resolves and keys exactly as at Start."""
    engine = cpu(**NONDEFAULT, **explicit)
    assert dumped(engine) == START_NONDEFAULT_STAGE
    key = build_stage_key(load_case("water"), engine.stage, engine.identity).key
    assert key == START_NONDEFAULT_KEY
    assert "cartesian_basis" not in engine.stage.options


def test_engine_impl_unchanged() -> None:
    """ENGINE_IMPL stays 2 (R30: a default change would need 3)."""
    assert PySCFEngine.ENGINE_IMPL == 2
    assert cpu().stage.options["engine_impl"] == 2


# --- MR 1, 3: the option is typed, keyed when True, idempotent --------------------------------


def test_option_is_declared_bool_false() -> None:
    """cartesian_basis is OptionSpec(bool, False)."""
    spec = PySCFEngine.OPTIONS["cartesian_basis"]
    assert spec.type is bool and spec.default is False


@pytest.mark.parametrize("value", [1, "true", 1.0])
def test_non_bool_refused(value: object) -> None:
    """The existing type rule refuses a non-bool value."""
    with pytest.raises(EngineInputError, match="cartesian_basis"):
        cpu(cartesian_basis=value)


def again(engine: PySCFEngine) -> StageConfig:
    """Re-resolve an engine's stage (``engine_impl`` is set by the engine, so it is dropped)."""
    data = engine.stage.model_dump()
    data["options"].pop("engine_impl")
    return PySCFEngine.from_stage(StageConfig.model_validate(data), device="cpu").stage


def test_true_is_keyed_and_idempotent() -> None:
    """True adds the key and changes the stage key; re-resolving gives the same stage."""
    engine = cpu(cartesian_basis=True)
    assert engine.stage.options["cartesian_basis"] is True
    water = load_case("water")
    assert build_stage_key(water, engine.stage, engine.identity).key != START_DEFAULT_KEY
    assert again(engine) == engine.stage
    assert again(cpu()) == cpu().stage


# --- MR 4: it takes effect -----------------------------------------------------------------------

# RHF/6-31G(d) of the test-set water on this host's PySCF (CPU), measured in slice 15.
RHF_631GD_SPHERICAL_HARTREE = -76.0090822934167
RHF_631GD_CARTESIAN_HARTREE = -76.01047615856282


def test_cartesian_mole_has_one_more_ao_per_d_shell() -> None:
    """Water/6-31G(d): cart True and 19 AOs (spherical 18: one d shell on O)."""
    water = load_case("water")
    spherical = cpu("hf", "6-31g*")._build_mol(water, "6-31g*", "none")
    cartesian = cpu("hf", "6-31g*", cartesian_basis=True)._build_mol(water, "6-31g*", "none")
    assert (spherical.cart, spherical.nao) == (False, 18)
    assert (cartesian.cart, cartesian.nao) == (True, 19)


def test_cartesian_energy_differs_from_spherical() -> None:
    """The RHF energy changes with the basis convention (both values recorded)."""
    water = load_case("water")
    e_sph = cpu("hf", "6-31g*").evaluate(water, forces=False).energy_hartree
    e_cart = cpu("hf", "6-31g*", cartesian_basis=True).evaluate(water, forces=False).energy_hartree
    assert e_sph == pytest.approx(RHF_631GD_SPHERICAL_HARTREE, abs=1e-8)
    assert e_cart == pytest.approx(RHF_631GD_CARTESIAN_HARTREE, abs=1e-8)
    assert e_cart < e_sph - 1e-3


def test_every_mole_of_the_stage_is_cartesian() -> None:
    """The ladder's small-basis Mole and the DF auxmol (PySCF make_auxmol) are Cartesian too."""
    from pyscf.df import addons

    engine = cpu("hf", "6-31g*", cartesian_basis=True)
    water = load_case("water")
    small = engine._build_mol(water, str(engine.stage.options["ladder_small_basis"]), "none")
    assert small.cart is True
    aux = addons.make_auxmol(engine._build_mol(water, "6-31g*", "none"), "def2-universal-jkfit")
    assert aux.cart is True  # make_auxmol copies the Mole: the auxiliary basis inherits cart


# --- MR 5: the atom guess is refused on both devices ---------------------------------------------


def test_atom_guess_refused_with_cartesian_basis() -> None:
    """cartesian_basis=True with init_guess='atom' is refused at construction (CPU too)."""
    with pytest.raises(EngineInputError) as info:
        cpu(cartesian_basis=True, init_guess="atom")
    assert "cartesian_basis" in str(info.value) and "init_guess" in str(info.value)
    assert cpu(cartesian_basis=False, init_guess="atom").stage.options["init_guess"] == "atom"
    assert cpu(cartesian_basis=True, init_guess="huckel").cartesian_basis


# --- MR 6: GPU parity (gpu) -----------------------------------------------------------------------


@pytest.mark.gpu
@pytest.mark.parametrize("density_fit", [True, False])
def test_gpu_cpu_parity_cartesian(density_fit: bool) -> None:
    """Water M06-2X/6-31G(d), cartesian: |E_gpu - E_cpu| <= 1e-6 Eh, the GPU run on cuda."""
    water = load_case("water")
    options = {"cartesian_basis": True, "density_fit": density_fit}
    gpu = PySCFEngine.from_stage(stage("m062x", "6-31g*", **options), device="cuda")
    on_gpu = gpu.evaluate(water, forces=False)
    on_cpu = cpu("m062x", "6-31g*", **options).evaluate(water, forces=False)
    print(
        json.dumps(
            {
                "density_fit": density_fit,
                "gpu_hartree": on_gpu.energy_hartree,
                "cpu_hartree": on_cpu.energy_hartree,
                "delta_hartree": on_gpu.energy_hartree - on_cpu.energy_hartree,
                "device": on_gpu.device,
            }
        )
    )
    assert on_gpu.device == "cuda" and on_cpu.device == "cpu"
    assert abs(on_gpu.energy_hartree - on_cpu.energy_hartree) <= 1e-6


@pytest.mark.gpu
def test_gpu_huckel_guess_with_cartesian_basis() -> None:
    """GPU4PySCF accepts init_guess='huckel' with a Cartesian basis (measured; stays allowed)."""
    water = load_case("water")
    options = {"cartesian_basis": True, "init_guess": "huckel"}
    gpu = PySCFEngine.from_stage(stage("m062x", "6-31g*", **options), device="cuda")
    on_gpu = gpu.evaluate(water, forces=False)
    on_cpu = cpu("m062x", "6-31g*", **options).evaluate(water, forces=False)
    assert on_gpu.device == "cuda"
    assert abs(on_gpu.energy_hartree - on_cpu.energy_hartree) <= 1e-6
