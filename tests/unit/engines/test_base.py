"""Tests for the engine base: errors, units, keyed options, identity, Engine and FD Hessian."""

import hashlib
import importlib.metadata as md
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

import pytest

import eta_rxncat.engines as engines
from eta_rxncat.core import EngineIdentity, MolecularState, Solvation, StageConfig
from eta_rxncat.engines import (
    BOHR_ANGSTROM,
    ENGINE_IMPL_KEY,
    HARTREE_EV,
    HARTREE_KCAL_MOL,
    Engine,
    EngineError,
    EngineInputError,
    EngineRuntimeError,
    EngineUnavailableError,
    OptionSpec,
    RawResult,
    ScfConvergenceError,
    angstrom_to_bohr,
    bohr_to_angstrom,
    ev_per_angstrom_to_hartree_per_bohr,
    ev_to_hartree,
    fd_hessian,
    kcal_mol_per_angstrom_to_hartree_per_bohr,
    kcal_mol_to_hartree,
    library_version,
    model_id,
    resolve_options,
    resolved_stage,
    sha256_file,
)
from eta_rxncat.engines.errors import TAIL_MAX_LINES
from eta_rxncat.engines.identity import CHUNK_BYTES
from eta_rxncat.store import build_stage_key

# ---------------------------------------------------------------- toy engine


def water() -> MolecularState:
    """Water in Angstrom (the mission test set geometry)."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]],
        charge=0,
        spin_multiplicity=1,
    )


def coupling_matrix(dof: int) -> list[list[float]]:
    """A known symmetric, positive-definite force-constant matrix (Eh/Bohr^2) with couplings."""
    return [
        [(0.5 + 0.1 * i) if i == j else 0.02 / (1 + abs(i - j)) for j in range(dof)]
        for i in range(dof)
    ]


K_TRUE = coupling_matrix(9)
X0_BOHR = [angstrom_to_bohr(v) for row in water().coordinates for v in row]


def harmonic_forces(coords_bohr: Sequence[Sequence[float]]) -> list[list[float]]:
    """Forces -K (x - x0) of E = 1/2 (x - x0)^T K (x - x0), in Eh/Bohr, N x 3."""
    dx = [v - x0 for v, x0 in zip((v for row in coords_bohr for v in row), X0_BOHR, strict=True)]
    flat = [-sum(K_TRUE[i][j] * dx[j] for j in range(9)) for i in range(9)]
    return [flat[3 * a : 3 * a + 3] for a in range(3)]


def harmonic_energy(coords_bohr: Sequence[Sequence[float]]) -> float:
    """E = 1/2 (x - x0)^T K (x - x0) in Eh."""
    dx = [v - x0 for v, x0 in zip((v for row in coords_bohr for v in row), X0_BOHR, strict=True)]
    return 0.5 * sum(dx[i] * K_TRUE[i][j] * dx[j] for i in range(9) for j in range(9))


class ToyEngine(Engine):
    """A pure-Python harmonic potential behind the rdkit_ff tag (tests only)."""

    tag = "rdkit_ff"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {
        "fd_step_bohr": OptionSpec(float, 0.005),
        "scale": OptionSpec(int, 1, frozenset({1, 2})),
    }

    def __init__(self, stage: StageConfig, *, offset: float = 0.0, **runtime: Any) -> None:
        """Take the runtime argument ``offset`` (never keyed) and pass the stage on."""
        super().__init__(stage, **runtime)
        self.offset = offset
        self.calls = 0

    @property
    def identity(self) -> EngineIdentity:
        """A fixed toy identity."""
        return EngineIdentity(name="rdkit_ff", version="toy-1")

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self.calls += 1
        coords = [[angstrom_to_bohr(v) for v in row] for row in state.coordinates]
        result = RawResult(energy_hartree=harmonic_energy(coords) + self.offset, device="cpu")
        if forces or hessian:
            result.forces_hartree_per_bohr = harmonic_forces(coords)
        if hessian:
            step = self.stage.options["fd_step_bohr"]
            assert isinstance(step, float)
            h, asym = fd_hessian(harmonic_forces, coords, step)
            result.hessian_hartree_per_bohr2 = h
            result.hessian_method = "finite_difference"
            result.hessian_max_asymmetry = asym
        return result


def toy_stage(**options: Any) -> StageConfig:
    """An rdkit_ff single point with the given options."""
    return StageConfig(kind="single_point", engine="rdkit_ff", method="uff", options=options)


# ---------------------------------------------------------------- errors


@pytest.mark.parametrize(
    "cls",
    [EngineUnavailableError, EngineInputError, ScfConvergenceError, EngineRuntimeError],
)
def test_error_hierarchy(cls: type[EngineError]) -> None:
    """Every typed error is an EngineError and is exported from eta_rxncat.engines."""
    assert issubclass(cls, EngineError) and issubclass(EngineError, Exception)
    assert getattr(engines, cls.__name__) is cls and cls.__name__ in engines.__all__


def test_scf_convergence_error_steps() -> None:
    """ScfConvergenceError carries the steps tried as a tuple."""
    error = ScfConvergenceError("no convergence", steps=["diis", "level_shift"])  # type: ignore[arg-type]
    assert error.steps == ("diis", "level_shift") and str(error) == "no convergence"
    assert ScfConvergenceError("x").steps == ()


def test_runtime_error_tail_is_capped_and_redacted() -> None:
    """The tail keeps the last 40 lines and redacts HF tokens and token=/Bearer values."""
    lines = [f"line {i}" for i in range(100)]
    lines[-1] = "auth hf_abcdefghijklmnopqrstuvwxyz0123 Bearer abc.def token=s3cret"
    error = EngineRuntimeError("xtb failed", tail="\n".join(lines))
    kept = error.tail.splitlines()
    assert len(kept) == TAIL_MAX_LINES == 40
    assert kept[0] == "line 60"
    assert "hf_abc" not in error.tail and "abc.def" not in error.tail and "s3cret" not in error.tail
    assert kept[-1].count("<redacted>") == 3
    assert EngineRuntimeError("x").tail == ""


# ---------------------------------------------------------------- units


def test_codata_2018_constants() -> None:
    """The constants equal the stated CODATA 2018 values exactly."""
    assert BOHR_ANGSTROM == 0.529177210903
    assert HARTREE_EV == 27.211386245988
    assert HARTREE_KCAL_MOL == 627.5094740631


@pytest.mark.parametrize("value", [1.0, -0.37, 1234.5678, 1e-9])
def test_unit_conversions(value: float) -> None:
    """Each conversion matches its formula and round-trips to 1e-15 relative."""
    rel = 1e-15
    assert angstrom_to_bohr(value) == value / BOHR_ANGSTROM
    assert bohr_to_angstrom(value) == value * BOHR_ANGSTROM
    assert ev_to_hartree(value) == value / HARTREE_EV
    assert kcal_mol_to_hartree(value) == value / HARTREE_KCAL_MOL
    assert ev_per_angstrom_to_hartree_per_bohr(value) == value * BOHR_ANGSTROM / HARTREE_EV
    assert kcal_mol_per_angstrom_to_hartree_per_bohr(value) == pytest.approx(
        value * BOHR_ANGSTROM / HARTREE_KCAL_MOL, rel=rel
    )
    assert bohr_to_angstrom(angstrom_to_bohr(value)) == pytest.approx(value, rel=rel)
    assert ev_to_hartree(value) * HARTREE_EV == pytest.approx(value, rel=rel)
    assert kcal_mol_to_hartree(value) * HARTREE_KCAL_MOL == pytest.approx(value, rel=rel)
    assert ev_per_angstrom_to_hartree_per_bohr(value) * HARTREE_EV / BOHR_ANGSTROM == (
        pytest.approx(value, rel=rel)
    )
    assert kcal_mol_per_angstrom_to_hartree_per_bohr(value) * HARTREE_KCAL_MOL / BOHR_ANGSTROM == (
        pytest.approx(value, rel=rel)
    )


def test_force_sign_and_magnitude() -> None:
    """1 eV/Angstrom is 0.0194469... Eh/Bohr (no sign change: conversions are pure scalings)."""
    assert ev_per_angstrom_to_hartree_per_bohr(1.0) == pytest.approx(0.019446903811441, rel=1e-12)
    assert ev_per_angstrom_to_hartree_per_bohr(-1.0) < 0


# ---------------------------------------------------------------- options

TABLE = {
    "accuracy": OptionSpec(float, 1.0),
    "level": OptionSpec(int, 3),
    "flag": OptionSpec(bool, True),
    "mode": OptionSpec(str, "gsolv", frozenset({"gsolv", "reference"})),
}


def test_resolve_fills_defaults_and_engine_impl() -> None:
    """Every table key gets its default, and engine_impl is added."""
    assert resolve_options("x", TABLE, {}, 1) == {
        "accuracy": 1.0,
        "level": 3,
        "flag": True,
        "mode": "gsolv",
        ENGINE_IMPL_KEY: 1,
    }
    given = resolve_options("x", TABLE, {"level": 5, "mode": "reference", "flag": False}, 2)
    assert given["level"] == 5 and given["mode"] == "reference" and given["flag"] is False
    assert given[ENGINE_IMPL_KEY] == 2


def test_int_for_float_becomes_float() -> None:
    """An int given for a float option is stored as float, so 1 and 1.0 key the same."""
    value = resolve_options("x", TABLE, {"accuracy": 2}, 1)["accuracy"]
    assert value == 2.0 and type(value) is float


@pytest.mark.parametrize(
    ("given", "key"),
    [
        ({"nope": 1}, "nope"),
        ({"level": True}, "level"),
        ({"accuracy": False}, "accuracy"),
        ({"level": 3.0}, "level"),
        ({"accuracy": "1.0"}, "accuracy"),
        ({"flag": 1}, "flag"),
        ({"mode": 7}, "mode"),
        ({"mode": "vacuum"}, "mode"),
        ({ENGINE_IMPL_KEY: 1}, ENGINE_IMPL_KEY),
    ],
    ids=[
        "unknown-key",
        "bool-for-int",
        "bool-for-float",
        "float-for-int",
        "str-for-float",
        "int-for-bool",
        "int-for-str",
        "disallowed-value",
        "caller-engine-impl",
    ],
)
def test_resolve_rejections(given: dict[str, Any], key: str) -> None:
    """Each bad option raises EngineInputError naming the engine and the key."""
    with pytest.raises(EngineInputError) as info:
        resolve_options("toy_tag", TABLE, given, 1)
    assert key in str(info.value) and "toy_tag" in str(info.value)


@pytest.mark.parametrize("impl", [0, -1, True, 1.0])
def test_resolve_needs_positive_int_impl(impl: Any) -> None:
    """engine_impl itself must be a positive int (a programming error otherwise)."""
    with pytest.raises(ValueError, match="engine_impl"):
        resolve_options("x", TABLE, {}, impl)


def test_table_may_not_define_engine_impl() -> None:
    """An option table that defines engine_impl is a programming error."""
    with pytest.raises(ValueError, match="engine_impl"):
        resolve_options("x", {ENGINE_IMPL_KEY: OptionSpec(int, 1)}, {}, 1)


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ((list, []), TypeError),
        ((int, True), TypeError),
        ((float, "1"), TypeError),
        ((str, "a", frozenset({"b"})), ValueError),
    ],
)
def test_option_spec_checks_itself(args: tuple[Any, ...], error: type[Exception]) -> None:
    """An OptionSpec with an unknown type, a mistyped default or a disallowed default fails."""
    with pytest.raises(error):
        OptionSpec(*args)


def xtb_stage(**overrides: Any) -> StageConfig:
    """An xtb ALPB stage (the solvent name exercises the normalise hook)."""
    data: dict[str, Any] = {
        "kind": "single_point",
        "engine": "xtb_subprocess",
        "method": "gfn2",
        "solvation": Solvation(model="alpb", solvent="Water"),
    }
    data.update(overrides)
    return StageConfig(**data)


def test_resolved_stage_is_new_and_complete() -> None:
    """resolved_stage returns a new stage with every default and a lowercased solvent."""
    original = xtb_stage(options={"level": 4})
    snapshot = original.model_dump()
    resolved = resolved_stage(original, TABLE, 1)
    assert resolved is not original
    assert resolved.options == {
        "accuracy": 1.0,
        "level": 4,
        "flag": True,
        "mode": "gsolv",
        ENGINE_IMPL_KEY: 1,
    }
    assert resolved.solvation.solvent == "water"
    assert original.model_dump() == snapshot and original.solvation.solvent == "Water"
    assert resolved.model_dump(exclude={"options", "solvation"}) == original.model_dump(
        exclude={"options", "solvation"}
    )


def test_custom_normalise_hook() -> None:
    """An engine's normalise hook is applied before the options are set."""

    def upper_method(stage: StageConfig) -> StageConfig:
        return stage.model_copy(update={"method": stage.method.upper()})

    resolved = resolved_stage(xtb_stage(), TABLE, 1, normalise=upper_method)
    assert resolved.method == "GFN2" and resolved.solvation.solvent == "Water"


def key(stage: StageConfig) -> str:
    """The v0.1.0 cache key of the resolved stage for water."""
    return build_stage_key(
        water(), resolved_stage(stage, TABLE, 1), EngineIdentity(name=stage.engine, version="1")
    ).key


def test_implicit_and_explicit_defaults_key_equal() -> None:
    """A default left implicit and the same value given explicitly give equal keys."""
    assert key(xtb_stage()) == key(xtb_stage(options={"accuracy": 1.0, "mode": "gsolv"}))
    assert key(xtb_stage()) == key(xtb_stage(options={"accuracy": 1}))
    assert key(xtb_stage(solvation=Solvation(model="alpb", solvent="WATER"))) == key(xtb_stage())


def test_keyed_value_changes_key() -> None:
    """Two stages differing only in a keyed value give different keys."""
    assert key(xtb_stage()) != key(xtb_stage(options={"accuracy": 0.5}))
    assert key(xtb_stage()) != key(xtb_stage(options={"mode": "reference"}))


def test_engine_impl_is_keyed() -> None:
    """A new engine implementation version changes the key."""
    stage = xtb_stage()
    one = build_stage_key(
        water(), resolved_stage(stage, TABLE, 1), EngineIdentity(name="xtb_subprocess", version="1")
    )
    two = build_stage_key(
        water(), resolved_stage(stage, TABLE, 2), EngineIdentity(name="xtb_subprocess", version="1")
    )
    assert one.key != two.key


# ---------------------------------------------------------------- identity


def test_model_id_and_sha256(tmp_path: Path) -> None:
    """model_id is name@sha256:<hex> of the file content, streamed past one 1 MiB chunk."""
    path = tmp_path / "weights.bin"
    path.write_bytes(bytes(range(256)) * (CHUNK_BYTES // 256 * 2 + 7))
    assert path.stat().st_size > 2 * CHUNK_BYTES
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha256_file(path) == expected
    assert model_id("x", path) == "x@sha256:" + expected
    assert str(tmp_path) not in model_id("x", path)


def test_model_id_changes_with_content(tmp_path: Path) -> None:
    """Same name, different bytes: different ids."""
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"1")
    b.write_bytes(b"2")
    assert model_id("m", a) != model_id("m", b)


def test_library_version() -> None:
    """library_version reads importlib.metadata, and an absent distribution is unavailable."""
    assert library_version("pydantic") == md.version("pydantic")
    with pytest.raises(EngineUnavailableError, match="no-such-dist-xyz"):
        library_version("no-such-dist-xyz")


# ---------------------------------------------------------------- Engine


def test_from_stage_resolves_and_keeps_runtime_out() -> None:
    """from_stage builds the resolved stage; runtime arguments never reach the options."""
    engine = ToyEngine.from_stage(toy_stage(scale=2), offset=1.5)
    assert engine.tag == "rdkit_ff" and engine.offset == 1.5
    assert engine.stage.options == {"fd_step_bohr": 0.005, "scale": 2, ENGINE_IMPL_KEY: 1}
    assert "offset" not in engine.stage.options
    assert engine.identity == EngineIdentity(name="rdkit_ff", version="toy-1")


def test_from_stage_rejects_foreign_tag() -> None:
    """A stage for another engine raises EngineInputError naming both tags."""
    stage = StageConfig(kind="single_point", engine="mace", method="mace-mp-0-medium")
    with pytest.raises(EngineInputError, match="'rdkit_ff'.*'mace'"):
        ToyEngine.from_stage(stage)


def test_from_stage_rejects_unknown_runtime_and_options() -> None:
    """An unknown runtime argument or option raises EngineInputError."""
    with pytest.raises(EngineInputError, match="threads"):
        ToyEngine.from_stage(toy_stage(), threads=4)
    with pytest.raises(EngineInputError, match="scale"):
        ToyEngine.from_stage(toy_stage(scale=3))


def test_evaluate_returns_valid_result() -> None:
    """Evaluate gives a PotentialResult with identity, impl 1, cpu and a timed wall clock."""
    engine = ToyEngine.from_stage(toy_stage())
    result = engine.evaluate(water())
    assert result.engine == engine.identity and result.stage_engine_impl == 1
    assert result.wall_time_s >= 0 and result.device == "cpu"
    assert result.energy_hartree == pytest.approx(0.0, abs=1e-24)
    assert result.forces_hartree_per_bohr is not None and len(result.forces_hartree_per_bohr) == 3
    assert result.hessian_hartree_per_bohr2 is None and result.hessian_method is None


def test_evaluate_with_fd_hessian() -> None:
    """The FD Hessian of the toy matches K to 1e-6, is exactly symmetric and records asymmetry."""
    result = ToyEngine.from_stage(toy_stage()).evaluate(water(), hessian=True)
    hessian = result.hessian_hartree_per_bohr2
    assert hessian is not None and result.hessian_method == "finite_difference"
    assert result.hessian_max_asymmetry is not None and result.hessian_max_asymmetry >= 0
    assert max(abs(hessian[i][j] - K_TRUE[i][j]) for i in range(9) for j in range(9)) <= 1e-6
    assert all(hessian[i][j] == hessian[j][i] for i in range(9) for j in range(9))


def test_result_does_not_alias_engine_data() -> None:
    """Mutating a returned result's lists does not touch the engine's data or later results."""

    class Fixed(ToyEngine):
        FORCES: ClassVar[list[list[float]]] = [[0.1, 0.2, 0.3]] * 3

        def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
            return RawResult(energy_hartree=-1.0, device="cpu", forces_hartree_per_bohr=self.FORCES)

    engine = Fixed.from_stage(toy_stage())
    first = engine.evaluate(water())
    assert first.forces_hartree_per_bohr is not None
    first.forces_hartree_per_bohr[0][0] = 99.0
    assert Fixed.FORCES[0][0] == 0.1
    second = engine.evaluate(water())
    assert second.forces_hartree_per_bohr is not None
    assert second.forces_hartree_per_bohr[0][0] == 0.1


class Broken(ToyEngine):
    """A toy whose _evaluate returns whatever ``RAW`` holds."""

    RAW: ClassVar[RawResult]

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        return self.RAW


@pytest.mark.parametrize(
    ("raw", "kwargs", "message"),
    [
        (RawResult(-1.0, "cpu", forces_hartree_per_bohr=[[0.0] * 3] * 2), {}, "2 force rows"),
        (RawResult(-1.0, "cpu"), {}, "no forces"),
        (
            RawResult(-1.0, "cpu", forces_hartree_per_bohr=[[0.0] * 3] * 3),
            {"hessian": True},
            "no Hessian",
        ),
        (
            RawResult(
                -1.0,
                "cpu",
                forces_hartree_per_bohr=[[0.0] * 3] * 3,
                hessian_hartree_per_bohr2=[[0.0] * 6] * 6,
                hessian_method="analytic",
                hessian_max_asymmetry=0.0,
            ),
            {"hessian": True},
            "side 6",
        ),
        (RawResult(math.nan, "cpu", forces_hartree_per_bohr=[[0.0] * 3] * 3), {}, "invalid result"),
        (
            RawResult(
                -1.0,
                "cpu",
                forces_hartree_per_bohr=[[0.0] * 3] * 3,
                hessian_hartree_per_bohr2=[
                    [float(i == j) + 0.1 * (i < j) for j in range(9)] for i in range(9)
                ],
                hessian_method="analytic",
                hessian_max_asymmetry=0.1,
            ),
            {"hessian": True},
            "invalid result",
        ),
    ],
    ids=[
        "two-rows-for-three-atoms",
        "missing-forces",
        "missing-hessian",
        "hessian-side",
        "nan-energy",
        "asymmetric-hessian",
    ],
)
def test_evaluate_rejects_bad_engine_output(
    raw: RawResult, kwargs: dict[str, bool], message: str
) -> None:
    """Mismatched shapes, missing quantities or invalid values raise EngineRuntimeError."""
    Broken.RAW = raw
    with pytest.raises(EngineRuntimeError, match=message) as info:
        Broken.from_stage(toy_stage()).evaluate(water(), **kwargs)
    if message == "invalid result":
        assert info.value.tail and info.value.__cause__ is not None


def test_engine_is_abstract() -> None:
    """Engine itself cannot be instantiated; identity and _evaluate are abstract."""
    with pytest.raises(TypeError):
        Engine(toy_stage())  # type: ignore[abstract]
    assert {"identity", "_evaluate"} <= Engine.__abstractmethods__


# ---------------------------------------------------------------- fd_hessian


def test_fd_hessian_harmonic() -> None:
    """On a harmonic potential with known K the FD Hessian is within 1e-6, in exactly 6N calls."""
    calls = 0

    def counted(coords: list[list[float]]) -> list[list[float]]:
        nonlocal calls
        calls += 1
        return harmonic_forces(coords)

    base = [[angstrom_to_bohr(v) for v in row] for row in water().coordinates]
    before = [row[:] for row in base]
    hessian, asym = fd_hessian(counted, base, 0.005)
    assert calls == 6 * 3
    assert base == before
    assert len(hessian) == 9 and all(len(row) == 9 for row in hessian)
    assert max(abs(hessian[i][j] - K_TRUE[i][j]) for i in range(9) for j in range(9)) <= 1e-6
    assert all(hessian[i][j] == hessian[j][i] for i in range(9) for j in range(9))
    assert 0 <= asym <= 1e-6


def test_fd_hessian_symmetrises_and_reports_asymmetry() -> None:
    """A non-conservative field: H becomes (H + H^T)/2 and max |H - H^T| is reported."""

    def skew(coords: list[list[float]]) -> list[list[float]]:
        x = [v for row in coords for v in row]
        # F = -A x with A[0][1] = 0.3 and A[1][0] = 0.1, so H_raw[0][1] = 0.1, H_raw[1][0] = 0.3.
        f = [-(0.3 * x[1]), -(0.1 * x[0]), 0.0]
        return [f]

    hessian, asym = fd_hessian(skew, [[0.0, 0.0, 0.0]], 0.01)
    assert asym == pytest.approx(0.2, abs=1e-12)
    assert hessian[0][1] == hessian[1][0] == pytest.approx(0.2, abs=1e-12)


@pytest.mark.parametrize("step", [0.0, -0.005, math.nan, math.inf])
def test_fd_hessian_bad_step(step: float) -> None:
    """A non-positive or non-finite step is rejected."""
    with pytest.raises(ValueError, match="step_bohr"):
        fd_hessian(harmonic_forces, [[0.0, 0.0, 0.0]] * 3, step)


def test_fd_hessian_bad_shapes() -> None:
    """Coordinates that are not N x 3, or forces of the wrong shape, are rejected."""
    with pytest.raises(ValueError, match="coords_bohr"):
        fd_hessian(harmonic_forces, [[0.0, 0.0]], 0.005)
    with pytest.raises(ValueError, match="coords_bohr"):
        fd_hessian(harmonic_forces, [], 0.005)
    with pytest.raises(ValueError, match="force_fn"):
        fd_hessian(lambda c: [[0.0, 0.0, 0.0]], [[0.0] * 3] * 2, 0.005)
