"""Tests for the v0.5.0 TS runner (slice 05): stages, cache, failures, N3 and the payload."""

import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest
from numpy.typing import NDArray

import eta_rxncat.orchestrator.species as species
import eta_rxncat.thermo as thermo
from eta_rxncat.core import (
    EngineIdentity,
    FormingBond,
    MolecularState,
    OptimizerIdentity,
    StageConfig,
    TSSearchResult,
    TSStep,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import Engine, OptionSpec, RawResult, ScfConvergenceError
from eta_rxncat.optimize import TransitionStateOptimizer, TSSearchFailedError
from eta_rxncat.orchestrator import (
    ENGINE_CLASSES,
    TSRecipe,
    TSRunResult,
    TSSpec,
    build_engine,
    run_transition_state,
)
from eta_rxncat.store import ArtifactStore, build_stage_key
from eta_rxncat.thermo import atomic_masses_amu

Array = NDArray[np.float64]
STAGE = StageConfig(kind="geometry_opt", engine="xtb_subprocess", method="gfn2")

# --- A 4-atom TS (C, O, H, N): forming bond (0, 3) at 2.257 A, active core 0, 1, 3 ------------

SYMBOLS = ["C", "O", "H", "N"]
COORDS = np.array([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [-0.5, 0.9, 0.1], [0.4, 0.3, 2.2]])
ONE_IMAGINARY = [-400.0, 300.0, 800.0, 1200.0, 1600.0, 3000.0]
TWO_IMAGINARY = [-400.0, -100.0, 800.0, 1200.0, 1600.0, 3000.0]

# CODATA 2018, written out so the test Hessian does not lean on eta_rxncat.thermo.constants.
_HARTREE_J = 4.3597447222071e-18
_BOHR_M = 0.529177210903e-10
_AMU_KG = 1.66053906660e-27
_C_CM = 299792458.0 * 100.0


def ts_state(coords: Array = COORDS, symbols: Sequence[str] = SYMBOLS) -> MolecularState:
    """Return the TS geometry with its active core."""
    return MolecularState(
        symbols=list(symbols),
        coordinates=np.asarray(coords).tolist(),
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0, 1, 3],
    )


def eigenvalue(wavenumber_cm1: float) -> float:
    """Return the mass-weighted Hessian eigenvalue (Eh/(Bohr^2 amu)) of a wavenumber."""
    omega = 2.0 * math.pi * _C_CM * abs(wavenumber_cm1)
    return math.copysign(omega**2 * _BOHR_M**2 * _AMU_KG / _HARTREE_J, wavenumber_cm1)


def ts_hessian(frequencies: list[float], coords: Array = COORDS) -> list[list[float]]:
    """Return a Cartesian Hessian whose lowest mode follows the (0, 3) forming stretch."""
    masses = atomic_masses_amu(SYMBOLS)
    sqrt_m = np.repeat(np.sqrt(masses), 3)
    r = coords - (masses[:, None] * coords).sum(axis=0) / masses.sum()
    rigid = []
    for axis in range(3):
        t = np.zeros_like(coords)
        t[:, axis] = 1.0
        rigid.append(t.ravel() * sqrt_m)
        unit = np.zeros(3)
        unit[axis] = 1.0
        rigid.append(np.cross(unit, r).ravel() * sqrt_m)
    u, _, _ = np.linalg.svd(np.column_stack(rigid), full_matrices=True)
    comp = u[:, 6:]
    stretch = np.zeros_like(coords)
    bond = (coords[3] - coords[0]) / np.linalg.norm(coords[3] - coords[0])
    stretch[0] -= bond
    stretch[3] += bond
    q0 = comp @ (comp.T @ (sqrt_m * stretch.ravel()))
    q0 /= np.linalg.norm(q0)
    rest = comp - np.outer(q0, q0 @ comp)
    rest, _ = np.linalg.qr(rest)
    rest = rest[:, : comp.shape[1] - 1]
    basis = np.column_stack([q0, rest])
    lam = np.diag([eigenvalue(f) for f in frequencies])
    hessian = (basis @ lam @ basis.T) * np.outer(sqrt_m, sqrt_m)
    return (0.5 * (hessian + hessian.T)).tolist()


class FakeEngine(Engine):
    """An xtb_subprocess stand-in: energy -100 Eh, zero forces and a chosen Hessian."""

    tag = "xtb_subprocess"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {"accuracy": OptionSpec(float, 1.0)}
    frequencies: ClassVar[list[float]] = ONE_IMAGINARY
    scf_failure: ClassVar[bool] = False
    calls: ClassVar[int] = 0

    @property
    def identity(self) -> EngineIdentity:
        """A fixed fake identity."""
        return EngineIdentity(name="xtb_subprocess", version="fake-1")

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        type(self).calls += 1
        if hessian and type(self).scf_failure:
            raise ScfConvergenceError("fake SCF failure", steps=("diis",))
        coords = np.asarray(state.coordinates)
        return RawResult(
            energy_hartree=-100.0,
            device="cpu",
            forces_hartree_per_bohr=np.zeros_like(coords).tolist() if forces else None,
            hessian_hartree_per_bohr2=ts_hessian(type(self).frequencies, coords)
            if hessian
            else None,
            hessian_method="analytic" if hessian else None,
            hessian_max_asymmetry=0.0 if hessian else None,
        )


class FakeTS(TransitionStateOptimizer):
    """A TS optimizer returning the start as the saddle after one engine call, or raising."""

    OPTIONS: ClassVar[Mapping[str, OptionSpec]] = {
        "max_steps": OptionSpec(int, 100),
        "trust_radius_bohr": OptionSpec(float, 0.1),
    }

    def __init__(self, version: str = "src-0123456789abcdef", error: Exception | None = None):
        """Keep the version and the error to raise (if any); count calls."""
        self.version = version
        self.error = error
        self.calls = 0

    @property
    def identity(self) -> OptimizerIdentity:
        """``prfo`` at the fake version."""
        return OptimizerIdentity(name="prfo", version=self.version)

    def find_saddle(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        forming_bonds: Sequence[tuple[int, int]] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> TSSearchResult:
        """Evaluate once, then return ``state`` as a converged saddle (or raise)."""
        self.calls += 1
        result = engine.evaluate(state, forces=True)
        if self.error is not None:
            raise self.error
        return TSSearchResult(
            final_state=state,
            final_energy_hartree=result.energy_hartree,
            converged=True,
            n_steps=1,
            n_gradient_calls=1,
            n_hessian_calls=0,
            n_hessian_refreshes=0,
            n_rejected_steps=0,
            hessian_method="analytic",
            followed_eigenvalue_hartree_per_bohr2=-0.05,
            final_max_gradient_hartree_per_bohr=0.0,
            final_rms_gradient_hartree_per_bohr=0.0,
            final_rigid_gradient_norm_hartree_per_bohr=0.0,
            forming_bonds=[FormingBond(i=i, j=j) for i, j in forming_bonds],
            optimizer=self.identity,
            options=self.resolved_options(options),
            history=[
                TSStep(
                    step=0,
                    accepted_bool=True,
                    energy_hartree=result.energy_hartree,
                    max_gradient_hartree_per_bohr=0.0,
                    trust_radius_bohr=0.1,
                    followed_eigenvalue_hartree_per_bohr2=-0.05,
                    mode_overlap=None,
                    hessian_source="exact",
                    ratio=1.0,
                )
            ],
        )


@pytest.fixture(autouse=True)
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> type[FakeEngine]:
    """Route xtb_subprocess to the fake engine, with one imaginary mode and no SCF failure."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", FakeEngine)
    monkeypatch.setattr(FakeEngine, "frequencies", ONE_IMAGINARY)
    monkeypatch.setattr(FakeEngine, "scf_failure", False)
    monkeypatch.setattr(FakeEngine, "calls", 0)
    return FakeEngine


def spec(**overrides: Any) -> TSSpec:
    """Return the TS spec of the 4-atom model."""
    values: dict[str, Any] = {"ts_id": "TS-model", "start": ts_state(), "forming_bonds": ((0, 3),)}
    values.update(overrides)
    return TSSpec(**values)


def recipe(optimizer: TransitionStateOptimizer, **overrides: Any) -> TSRecipe:
    """Return a recipe on the fake engine."""
    values: dict[str, Any] = {"name": "fake", "engine_stage": STAGE, "ts_optimizer": optimizer}
    values.update(overrides)
    return TSRecipe(**values)


def run(
    store_path: Path, optimizer: TransitionStateOptimizer, **spec_overrides: Any
) -> TSRunResult:
    """Run the TS runner once on a store at ``store_path``."""
    with ArtifactStore(store_path) as store:
        return run_transition_state(spec(**spec_overrides), recipe(optimizer), store)


def comparable(result: TSRunResult) -> dict[str, Any]:
    """Return the payload without metrics (timing and counters differ between runs)."""
    payload = result.as_payload()
    payload.pop("metrics")
    return payload


# --- Happy path and cache (G6) ------------------------------------------------------------------


def test_happy_path_makes_a_record(tmp_path: Path) -> None:
    """A fake saddle with one imaginary mode on the active set gives a validated record."""
    result = run(tmp_path / "s.sqlite", FakeTS())
    assert result.failed_reason is None
    assert result.record is not None
    assert result.record.degeneracy == 1
    assert result.record.thermo.imaginary_frequencies_cm1 == [pytest.approx(-400.0, abs=1e-6)]
    assert result.validation is not None and result.validation.passed_bool
    assert result.connectivity_equal_bool is None
    assert result.metrics["ts_opt"].rows_created == 1
    assert result.metrics["frequency"].rows_created == 1
    assert result.metrics["ts_opt"].engine_calls == 1
    assert result.metrics["frequency"].engine_calls == 1
    assert set(result.keys) == {"ts_opt", "frequency"}


def test_second_run_is_served_from_the_cache(tmp_path: Path) -> None:
    """G6: a rerun hits both stages, writes nothing and calls neither optimizer nor engine."""
    optimizer = FakeTS()
    first = run(tmp_path / "s.sqlite", optimizer)
    calls_after_first = (optimizer.calls, FakeEngine.calls)
    second = run(tmp_path / "s.sqlite", optimizer)
    assert (optimizer.calls, FakeEngine.calls) == calls_after_first
    for kind in ("ts_opt", "frequency"):
        assert second.metrics[kind].cache_hits == 1
        assert second.metrics[kind].rows_created == 0
        assert second.metrics[kind].engine_calls == 0
    assert comparable(second) == comparable(first)
    assert second.search == first.search


# --- Keys ----------------------------------------------------------------------------------------


def ts_key(tmp_path: Path, name: str, optimizer: FakeTS | None = None, **overrides: Any) -> str:
    """Return the ts_opt key of one run in a fresh store."""
    with ArtifactStore(tmp_path / f"{name}.sqlite") as store:
        options = overrides.pop("ts_options", {})
        result = run_transition_state(
            spec(**overrides), recipe(optimizer or FakeTS(), ts_options=options), store
        )
    return result.keys["ts_opt"]


def test_ts_opt_key_covers_options_bonds_version_and_geometry(tmp_path: Path) -> None:
    """Every keyed input changes the ts_opt key; the defaults spelled out do not."""
    base = ts_key(tmp_path, "base")
    moved = COORDS.copy()
    moved[2, 0] += 0.01
    assert ts_key(tmp_path, "explicit", ts_options={"max_steps": 100}) == base
    assert ts_key(tmp_path, "option", ts_options={"max_steps": 50}) != base
    assert ts_key(tmp_path, "trust", ts_options={"trust_radius_bohr": 0.2}) != base
    assert ts_key(tmp_path, "bonds", forming_bonds=((0, 3), (1, 3))) != base
    assert ts_key(tmp_path, "version", FakeTS(version="src-ffffffffffffffff")) != base
    assert ts_key(tmp_path, "geometry", start=ts_state(moved)) != base
    assert ts_key(tmp_path, "bond order", forming_bonds=((3, 0),)) == base


def test_frequency_key_equals_the_species_runner_key(tmp_path: Path) -> None:
    """The frequency key is the species runner's for the same geometry and engine stage."""
    result = run(tmp_path / "s.sqlite", FakeTS())
    engine = build_engine(STAGE, {})
    stage = species._with_kind(engine.stage, "frequency", engine.stage.options)
    assert result.search is not None
    expected = build_stage_key(result.search.final_state, stage, engine.identity).key
    assert result.keys["frequency"] == expected


# --- Failures are cached -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (
            TSSearchFailedError("fake", reason="max_steps", steps=("0",), last_energy_hartree=-1.0),
            "ts_search_failed:max_steps",
        ),
        (ScfConvergenceError("fake SCF failure", steps=("diis",)), "scf_convergence"),
    ],
)
def test_search_failure_is_cached(tmp_path: Path, error: Exception, reason: str) -> None:
    """A failed search is a cached completed row; the rerun returns it with no optimizer call."""
    optimizer = FakeTS(error=error)
    first = run(tmp_path / "s.sqlite", optimizer)
    assert first.failed_reason == reason
    assert first.search is None and first.record is None and first.validation is None
    assert first.metrics["ts_opt"].rows_created == 1
    assert "frequency" not in first.keys
    second = run(tmp_path / "s.sqlite", optimizer)
    assert optimizer.calls == 1
    assert second.failed_reason == reason
    assert second.metrics["ts_opt"].cache_hits == 1
    assert second.metrics["ts_opt"].rows_created == 0
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        engine = build_engine(STAGE, {})
        key = build_stage_key(
            ts_state(),
            species._with_kind(
                engine.stage, "ts_opt", {**_ts_options(engine), "opt.forming_bonds": "0-3"}
            ),
            engine.identity,
        )
        row = store.get(key)
    assert row is not None
    assert row["failed_reason"] == reason
    assert "fake" in row["message"]


def _ts_options(engine: Engine) -> dict[str, ScalarValue]:
    """Return the ts_opt stage options of the default FakeTS recipe (test-local rule)."""
    optimizer = FakeTS()
    options: dict[str, ScalarValue] = dict(engine.stage.options)
    options.update({f"opt.{k}": v for k, v in optimizer.resolved_options({}).items()})
    options["opt.name"] = "prfo"
    options["opt.version"] = optimizer.version
    return options


def test_frequency_scf_failure_is_cached(
    tmp_path: Path, fake_engine: type[FakeEngine], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An SCF failure of the frequency stage is cached and returned on the rerun."""
    monkeypatch.setattr(fake_engine, "scf_failure", True)
    first = run(tmp_path / "s.sqlite", FakeTS())
    assert first.failed_reason == "scf_convergence"
    assert first.search is not None and first.validation is None
    calls = fake_engine.calls
    second = run(tmp_path / "s.sqlite", FakeTS())
    assert second.failed_reason == "scf_convergence"
    assert second.metrics["frequency"].cache_hits == 1
    assert fake_engine.calls == calls


def test_two_imaginary_modes_fail_validation(
    tmp_path: Path, fake_engine: type[FakeEngine], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two imaginary modes: ts_validation_failed, no record or thermo, the validation kept."""
    monkeypatch.setattr(fake_engine, "frequencies", TWO_IMAGINARY)
    result = run(tmp_path / "s.sqlite", FakeTS())
    assert result.failed_reason == "ts_validation_failed"
    assert result.record is None
    assert result.validation is not None
    assert not result.validation.mode_count_passed_bool
    assert "multiple_imaginary_modes" in result.validation.reasons
    payload = result.as_payload()
    assert payload["thermo"] is None and payload["validation"] is not None


# --- N3: the minimum path is never used ----------------------------------------------------------


def test_minimum_path_is_never_called(
    tmp_path: Path, fake_engine: type[FakeEngine], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The species runner's minimum-path helpers are never called (happy and failure paths)."""
    calls: list[str] = []

    def forbidden(name: str) -> Any:
        def call(*args: Any, **kwargs: Any) -> Any:
            calls.append(name)
            raise AssertionError(f"{name} called by the TS runner")

        return call

    for name in ("check_ground_state", "_frequency_and_thermo", "_push", "_dedup_after_push"):
        monkeypatch.setattr(species, name, forbidden(name))
    monkeypatch.setattr(species, "run_species", forbidden("run_species"))
    monkeypatch.setattr(thermo, "check_ground_state", forbidden("thermo.check_ground_state"))

    assert run(tmp_path / "a.sqlite", FakeTS()).record is not None
    failure = TSSearchFailedError("x", reason="mode_lost", steps=(), last_energy_hartree=None)
    assert run(tmp_path / "b.sqlite", FakeTS(error=failure)).failed_reason is not None
    monkeypatch.setattr(fake_engine, "frequencies", TWO_IMAGINARY)
    assert run(tmp_path / "c.sqlite", FakeTS()).failed_reason == "ts_validation_failed"
    assert calls == []


# --- Connectivity (reported only) ----------------------------------------------------------------


def test_connectivity_equal_with_the_start_as_reference(tmp_path: Path) -> None:
    """A reference equal to the start, identity map: connectivity equal."""
    result = run(tmp_path / "s.sqlite", FakeTS(), reference=ts_state())
    assert result.connectivity_equal_bool is True


def test_connectivity_with_a_permuted_reference_and_its_map(tmp_path: Path) -> None:
    """A reference in another atom order is compared through reference_map."""
    order = [2, 0, 3, 1]  # reference atom k is start atom order[k]
    reference = ts_state(COORDS[order], [SYMBOLS[k] for k in order])
    start_to_reference = tuple(order.index(i) for i in range(4))
    result = run(
        tmp_path / "s.sqlite", FakeTS(), reference=reference, reference_map=start_to_reference
    )
    assert result.connectivity_equal_bool is True


def test_connectivity_missing_bond_is_reported_not_gated(tmp_path: Path) -> None:
    """A reference missing the C-H bond gives False, and the record is still made."""
    far = COORDS.copy()
    far[2] = [-3.0, 3.0, 0.0]
    result = run(tmp_path / "s.sqlite", FakeTS(), reference=ts_state(far))
    assert result.connectivity_equal_bool is False
    assert result.record is not None
    assert result.failed_reason is None


def test_reference_map_must_cover_every_atom() -> None:
    """A reference map of the wrong length is refused."""
    with pytest.raises(ValueError, match="3 entries for 4 atoms"):
        spec(reference=ts_state(), reference_map=(0, 1, 2))


# --- Payload -------------------------------------------------------------------------------------

UNIT = re.compile(
    r"_(hartree|cm1|angstrom|bohr|s|k|atm|mol_l|kg_m2)$"
    r"|_hartree_per_(bohr|bohr2|k)$"
)
DIMENSIONLESS = {
    "active_atom_indices",
    "active_core_ke_fraction",
    "cache_hits",
    "charge",
    "degeneracy",
    "engine_calls",
    "forming_stretch_overlap",
    "hessian_refresh_steps",
    "i",
    "j",
    "max_automorphisms",
    "max_consecutive_rejections",
    "max_steps",
    "min_active_core_ke_fraction",
    "min_forming_stretch_overlap",
    "min_initial_overlap",
    "min_mode_overlap",
    "mode_overlap",
    "qrrho_alpha",
    "ratio",
    "rotational_symmetry_number",
    "rows_created",
    "spin_multiplicity",
    "step",
}
"""Counts, indices, fractions and overlaps: numbers without a unit."""
CONTRACT_EXCEPTIONS = {"coordinates"}
"""MolecularState.coordinates (Angstrom) predates the suffix rule (v0.1.0 contract)."""


def unsuffixed_numbers(value: Any, key: str = "", unit_from_parent: bool = False) -> list[str]:
    """Return the paths of numeric values whose key carries no unit and is not dimensionless."""
    if isinstance(value, Mapping):
        inherited = bool(UNIT.search(key))
        found: list[str] = []
        for child_key, child in value.items():
            found += [
                f"{key}.{path}" if key else path
                for path in unsuffixed_numbers(child, str(child_key), inherited)
            ]
        return found
    if isinstance(value, list):
        return sorted(
            {p for item in value for p in unsuffixed_numbers(item, key, unit_from_parent)}
        )
    if isinstance(value, bool) or not isinstance(value, int | float):
        return []
    plain = key.removeprefix("opt.")
    if (
        unit_from_parent
        or UNIT.search(plain)
        or plain in DIMENSIONLESS
        or plain.startswith("n_")
        or key in CONTRACT_EXCEPTIONS
    ):
        return []
    return [key]


def test_payload_keys_carry_units(tmp_path: Path) -> None:
    """Every numeric key in as_payload() carries a unit or is dimensionless by name."""
    payload = run(tmp_path / "s.sqlite", FakeTS()).as_payload()
    assert unsuffixed_numbers(payload) == []
    assert unsuffixed_numbers({"energy": 1.0}) == ["energy"]


def test_payload_lists_are_not_in_energy_order(tmp_path: Path) -> None:
    """The payload's record lists are in step or index order, never in energy order."""
    payload = run(tmp_path / "s.sqlite", FakeTS()).as_payload()
    search = payload["search"]
    assert [step["step"] for step in search["history"]] == list(range(len(search["history"])))
    bonds = [(b["i"], b["j"]) for b in search["forming_bonds"]]
    assert bonds == sorted(bonds)
    assert payload["validation"]["reasons"] == sorted(payload["validation"]["reasons"])
    assert list(payload["keys"]) == sorted(payload["keys"])


def test_runs_with_the_real_prfo_optimizer(tmp_path: Path) -> None:
    """The real PRFOOptimizer plugs in: zero forces converge in one step; its identity keys it."""
    from eta_rxncat.optimize import PRFOOptimizer

    optimizer = PRFOOptimizer()
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_transition_state(spec(), recipe(optimizer), store)
    assert result.failed_reason is None
    assert result.search is not None
    assert result.search.optimizer == optimizer.identity
    assert result.search.n_steps == 1
    assert result.record is not None and result.validation is not None
    assert result.validation.passed_bool
    assert result.metrics["ts_opt"].engine_calls == result.search.n_gradient_calls
