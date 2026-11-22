"""Tests for the xtb_subprocess engine (slice 08).

Default-suite tests use recorded xtb 6.8.0 output files (``data/xtb/``) and a fake xtb script.
``xtb`` tests run the real binary, found via ``ETA_RXNCAT_XTB`` or ``PATH``: without it they skip
at fixture level (and fail under ``ETA_RXNCAT_ACCEPTANCE=1``).
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import (
    ENGINE_IMPL_KEY,
    EngineInputError,
    EngineRuntimeError,
    EngineUnavailableError,
    XTBSubprocessEngine,
)
from eta_rxncat.engines.xtb_subprocess import (
    HESSIAN_CONVENTION,
    XTB_ENV,
    parse_energy,
    parse_gradient,
    parse_hessian,
    parse_version,
    resolve_binary,
)
from eta_rxncat.store import build_stage_key

DATA = Path(__file__).parent / "data" / "xtb"
REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "docs/prd/v0.2.0/evidence/xtb-hessian-convention.json"

FAKE_XTB = f"""#!{sys.executable}
import os, shutil, sys, time
data = {str(DATA)!r}
log = os.environ.get("FAKE_XTB_LOG")
if log:
    with open(log, "a") as fh:
        fh.write(" ".join(sys.argv[1:]) + "\\n")
if "--version" in sys.argv:
    sys.stdout.write(open(os.path.join(data, "version.txt")).read())
    sys.exit(0)
time.sleep(float(os.environ.get("FAKE_XTB_SLEEP", "0")))
code = int(os.environ.get("FAKE_XTB_EXIT", "0"))
if code:
    sys.stderr.write("fake xtb: [ERROR] Program stopped due to fatal error\\n")
    sys.exit(code)
if "--grad" in sys.argv and not os.environ.get("FAKE_XTB_NO_OUTPUT"):
    shutil.copy(os.path.join(data, "water.energy"), "energy")
    shutil.copy(os.path.join(data, "water.gradient"), "gradient")
if "--hess" in sys.argv:
    shutil.copy(os.path.join(data, "water.hessian"), "hessian")
open("xtbrestart", "w").write("scratch")
"""


def stage(**kwargs: Any) -> StageConfig:
    """An xtb GFN2 single point."""
    data: dict[str, Any] = {"kind": "single_point", "engine": "xtb_subprocess", "method": "gfn2"}
    data.update(kwargs)
    return StageConfig(**data)


@pytest.fixture
def fake_xtb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """A fake xtb executable plus an argv log and a private TMPDIR for the engine's temp dirs."""
    binary = tmp_path / "bin" / "xtb"
    binary.parent.mkdir()
    binary.write_text(FAKE_XTB, encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "argv.log"
    work = tmp_path / "tmp"
    work.mkdir()
    monkeypatch.setenv("FAKE_XTB_LOG", str(log))
    monkeypatch.setattr(tempfile, "tempdir", str(work))
    for name in ("FAKE_XTB_EXIT", "FAKE_XTB_SLEEP", "FAKE_XTB_NO_OUTPUT"):
        monkeypatch.delenv(name, raising=False)
    return {"binary": binary, "log": log, "work": work}


def engine(
    binary: Path, runtime: dict[str, Any] | None = None, **kwargs: Any
) -> XTBSubprocessEngine:
    """An xtb engine on ``binary``."""
    return XTBSubprocessEngine.from_stage(stage(**kwargs), binary=binary, **(runtime or {}))


# ---------------------------------------------------------------- parsing (recorded output)


def test_parse_recorded_outputs() -> None:
    """The recorded xtb 6.8.0 water energy, gradient, Hessian and version parse as expected."""
    assert parse_energy((DATA / "water.energy").read_text()) == -5.07037076454
    grad = parse_gradient((DATA / "water.gradient").read_text(), 3)
    assert grad[0][2] == pytest.approx(2.9401779736462e-03, rel=1e-13)
    assert grad[1] == pytest.approx(
        [1.2260167167282e-19, -4.4262969998780e-03, -1.4700889868231e-03]
    )
    hess = parse_hessian((DATA / "water.hessian").read_text(), 3)
    assert len(hess) == 9 and all(len(row) == 9 for row in hess)
    assert hess[0] == [0.0] * 9 and hess[1][1] == pytest.approx(0.5940627549)
    assert parse_version((DATA / "version.txt").read_text()) == "xtb 6.8.0"


@pytest.mark.parametrize(
    ("parser", "text"),
    [
        (lambda t: parse_energy(t), "$energy\n$end\n"),
        (lambda t: parse_gradient(t, 3), "$grad\n cycle\n1 2 3 O\n"),
        (lambda t: parse_hessian(t, 3), "$hessian\n1.0 2.0\n"),
        (lambda t: parse_version(t), "no version here"),
    ],
    ids=["energy", "gradient", "hessian", "version"],
)
def test_parsers_reject_malformed(parser: Any, text: str) -> None:
    """Malformed files raise a typed parse error (ValueError / IndexError / StopIteration)."""
    with pytest.raises((ValueError, IndexError, StopIteration)):
        parser(text)


# ---------------------------------------------------------------- argv, options, keys


def test_literal_argv(fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]) -> None:
    """R4: the exact charge / uhf flags per case, ALPB with its state, and --grad last."""
    eng = engine(fake_xtb["binary"])
    head = [str(fake_xtb["binary"].resolve()), "input.xyz", "--gfn", "2"]
    tail = ["--acc", "1.0", "--etemp", "300.0", "--grad"]
    for case, chrg, uhf in (
        ("water", "0", "0"),
        ("hydroxide", "-1", "0"),
        ("hydroxyl", "0", "1"),
        ("pd_anion", "-1", "0"),
    ):
        assert eng.argv(test_set[case], "--grad") == [*head, "--chrg", chrg, "--uhf", uhf, *tail], (
            case
        )
    toluene = engine(fake_xtb["binary"], solvation=Solvation(model="alpb", solvent="Toluene"))
    argv = toluene.argv(test_set["water"], "--grad")
    assert argv[-4:] == ["--alpb", "toluene", "gsolv", "--grad"]
    assert toluene.stage.solvation.solvent == "toluene"


def test_resolved_options_and_keys(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]
) -> None:
    """Defaults are filled; each keyed option changes the key; runtime arguments do not."""
    base = engine(fake_xtb["binary"])
    assert base.stage.options == {
        "accuracy": 1.0,
        "etemp_k": 300.0,
        "alpb_state": "gsolv",
        "fd_step_bohr": 0.005,
        ENGINE_IMPL_KEY: 1,
    }
    water = test_set["water"]
    identity = base.identity

    def key(eng: XTBSubprocessEngine) -> str:
        return build_stage_key(water, eng.stage, identity).key

    for option, value in (
        ("accuracy", 0.5),
        ("etemp_k", 500.0),
        ("alpb_state", "reference"),
        ("fd_step_bohr", 0.004),
    ):
        assert key(engine(fake_xtb["binary"], options={option: value})) != key(base), option
    assert key(engine(fake_xtb["binary"], runtime={"threads": 4, "timeout_s": 10})) == key(base)
    ref = engine(
        fake_xtb["binary"],
        solvation=Solvation(model="alpb", solvent="toluene"),
        options={"alpb_state": "reference"},
    )
    gsolv = engine(fake_xtb["binary"], solvation=Solvation(model="alpb", solvent="toluene"))
    assert key(ref) != key(gsolv)


@pytest.mark.parametrize(
    ("kwargs", "runtime", "match"),
    [
        ({"method": "gfn1"}, {}, "gfn2"),
        ({"solvation": Solvation(model="alpb", dielectric=2.38)}, {}, "dielectric alone"),
        ({"options": {"alpb_state": "vacuum"}}, {}, "alpb_state"),
        ({"options": {"accuracy": 0.0}}, {}, "accuracy"),
        ({"options": {"etemp_k": -1.0}}, {}, "etemp_k"),
        ({"options": {"fd_step_bohr": 0.0}}, {}, "fd_step_bohr"),
        ({"options": {"nope": 1}}, {}, "nope"),
        ({}, {"threads": 0}, "threads"),
        ({}, {"timeout_s": 0}, "timeout_s"),
        ({}, {"omp_stacksize": "lots"}, "omp_stacksize"),
        ({}, {"gpu": True}, "gpu"),
    ],
)
def test_bad_stage_or_runtime(
    fake_xtb: dict[str, Path], kwargs: dict[str, Any], runtime: dict[str, Any], match: str
) -> None:
    """Unrepresentable stages and bad runtime arguments are EngineInputError."""
    with pytest.raises(EngineInputError, match=match):
        engine(fake_xtb["binary"], runtime=runtime, **kwargs)


def test_non_alpb_solvation_rejected_by_core() -> None:
    """DdCOSMO / PCM never reach the xtb engine: core pairs them with pyscf_gpu_cpu."""
    with pytest.raises(ValidationError, match="needs engine 'pyscf_gpu_cpu'"):
        stage(solvation=Solvation(model="pcm", dielectric=2.38))


# ---------------------------------------------------------------- binary resolution


def test_binary_resolution_order(
    fake_xtb: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit binary, then ETA_RXNCAT_XTB, then PATH; missing names the provisioning step."""
    other = tmp_path / "other" / "xtb"
    other.parent.mkdir()
    shutil.copy(fake_xtb["binary"], other)
    other.chmod(0o755)
    monkeypatch.setenv(XTB_ENV, str(other))
    monkeypatch.setenv("PATH", str(fake_xtb["binary"].parent))
    assert resolve_binary(fake_xtb["binary"]) == fake_xtb["binary"].resolve()
    assert resolve_binary(None) == other.resolve()
    monkeypatch.delenv(XTB_ENV)
    assert resolve_binary(None) == fake_xtb["binary"].resolve()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(EngineUnavailableError, match="xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz"):
        XTBSubprocessEngine.from_stage(stage())
    with pytest.raises(EngineUnavailableError, match="not an executable"):
        XTBSubprocessEngine.from_stage(stage(), binary=tmp_path / "missing")


# ---------------------------------------------------------------- runs with the fake binary


def calls(log: Path) -> list[str]:
    """The argv tails the fake xtb recorded (one line per call, --version excluded)."""
    return [line for line in log.read_text().splitlines() if "--version" not in line]


def test_every_call_runs_grad(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]
) -> None:
    """R39: a forces=False, hessian=False call still runs --grad (one call)."""
    result = engine(fake_xtb["binary"]).evaluate(test_set["water"], forces=False)
    assert result.energy_hartree == -5.07037076454 and result.forces_hartree_per_bohr is None
    recorded = calls(fake_xtb["log"])
    assert len(recorded) == 1 and recorded[0].endswith("--grad")


def test_hessian_is_fd_of_grad_calls(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]
) -> None:
    """R39 amended: hessian=True runs 1 + 6N --grad calls and never --hess."""
    eng = engine(fake_xtb["binary"])
    result = eng.evaluate(test_set["water"], hessian=True)
    recorded = calls(fake_xtb["log"])
    assert len(recorded) == 1 + 6 * 3
    assert all(line.endswith("--grad") for line in recorded)
    assert not any("--hess" in line for line in recorded)
    assert result.hessian_method == "finite_difference" and HESSIAN_CONVENTION == "fd"
    assert len(eng.calls) == 19


def test_forces_are_negative_gradient(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]
) -> None:
    """Forces = -gradient from the gradient file (Eh/Bohr)."""
    forces = engine(fake_xtb["binary"]).evaluate(test_set["water"]).forces_hartree_per_bohr
    grad = parse_gradient((DATA / "water.gradient").read_text(), 3)
    assert forces == [[-v for v in row] for row in grad]


def test_identity_from_version(fake_xtb: dict[str, Path]) -> None:
    """identity.version is 'xtb <x.y.z>' from --version; model None."""
    ident = engine(fake_xtb["binary"]).identity
    assert (ident.name, ident.version, ident.model) == ("xtb_subprocess", "xtb 6.8.0", None)


def test_temp_dirs_removed(fake_xtb: dict[str, Path], test_set: dict[str, MolecularState]) -> None:
    """Every call runs in its own temp dir under TMPDIR, removed on success; cwd is untouched."""
    before = set(os.listdir("."))
    engine(fake_xtb["binary"]).evaluate(test_set["water"], hessian=True)
    assert list(fake_xtb["work"].iterdir()) == []
    assert set(os.listdir(".")) == before


def test_nonzero_exit(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A binary that exits 1 -> EngineRuntimeError with its stderr tail; temp dir removed."""
    monkeypatch.setenv("FAKE_XTB_EXIT", "1")
    with pytest.raises(EngineRuntimeError, match="exited with 1") as info:
        engine(fake_xtb["binary"]).evaluate(test_set["water"])
    assert "fake xtb: [ERROR] Program stopped due to fatal error" in info.value.tail
    assert list(fake_xtb["work"].iterdir()) == []


def test_keep_failed_keeps_dir(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With keep_failed=True a failed call's temp dir is kept for inspection."""
    monkeypatch.setenv("FAKE_XTB_EXIT", "3")
    with pytest.raises(EngineRuntimeError):
        engine(fake_xtb["binary"], runtime={"keep_failed": True}).evaluate(test_set["water"])
    kept = list(fake_xtb["work"].iterdir())
    assert len(kept) == 1 and (kept[0] / "input.xyz").is_file()


def test_timeout(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """timeout_s=0.01 -> EngineRuntimeError mentioning the timeout."""
    monkeypatch.setenv("FAKE_XTB_SLEEP", "5")
    with pytest.raises(EngineRuntimeError, match="timed out after 0.01 s"):
        engine(fake_xtb["binary"], runtime={"timeout_s": 0.01}).evaluate(test_set["water"])


def test_missing_output(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that writes no energy file -> EngineRuntimeError naming the file."""
    monkeypatch.setenv("FAKE_XTB_NO_OUTPUT", "1")
    with pytest.raises(EngineRuntimeError, match="wrote no 'energy' file"):
        engine(fake_xtb["binary"]).evaluate(test_set["water"])


def test_threads_reach_the_environment(
    fake_xtb: dict[str, Path], test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """OMP_NUM_THREADS, MKL_NUM_THREADS and OMP_STACKSIZE follow the runtime arguments; no shell."""
    seen: dict[str, Any] = {}
    real = subprocess.run

    def spy(argv: Any, **kwargs: Any) -> Any:
        if "--grad" in argv:
            seen.update(kwargs)
            seen["argv"] = argv
        return real(argv, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    engine(fake_xtb["binary"], runtime={"threads": 3, "omp_stacksize": "2G"}).evaluate(
        test_set["water"]
    )
    env = seen["env"]
    assert (env["OMP_NUM_THREADS"], env["MKL_NUM_THREADS"], env["OMP_STACKSIZE"]) == (
        "3",
        "3",
        "2G",
    )
    assert "shell" not in seen and isinstance(seen["argv"], list)
    assert Path(seen["cwd"]).parent == fake_xtb["work"]


def test_evidence_record_matches_engine() -> None:
    """The R13 record exists and its engine choice is the code's HESSIAN_CONVENTION."""
    import json

    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert data["xtb"] == "xtb 6.8.0"
    assert data["max_abs_file_minus_fd"] > 1e-4 and data["engine_choice"].startswith(
        "finite_difference"
    )
    assert HESSIAN_CONVENTION == "fd"


# ---------------------------------------------------------------- real xtb


@pytest.fixture(scope="module")
def xtb_binary() -> Path:
    """The real xtb binary (ETA_RXNCAT_XTB or PATH); skip here, at fixture level, without it."""
    try:
        return resolve_binary(None)
    except EngineUnavailableError as exc:
        pytest.skip(f"xtb binary not provisioned: {exc}")


def real(binary: Path, **kwargs: Any) -> XTBSubprocessEngine:
    """A real xtb engine, threads 1."""
    return XTBSubprocessEngine.from_stage(stage(**kwargs), binary=binary, threads=1)


def hand_run(argv: list[str], state: MolecularState) -> tuple[float, list[list[float]]]:
    """Run ``argv`` by hand in a separate temp dir (threads 1) and parse energy + gradient."""
    with tempfile.TemporaryDirectory() as work:
        lines = [str(len(state.symbols)), "hand"] + [
            f"{s} {x!r} {y!r} {z!r}"
            for s, (x, y, z) in zip(state.symbols, state.coordinates, strict=True)
        ]
        Path(work, "input.xyz").write_text("\n".join(lines) + "\n")
        env = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_STACKSIZE": "1G"}
        subprocess.run(argv, cwd=work, env=env, check=True, capture_output=True)
        return (
            parse_energy(Path(work, "energy").read_text()),
            parse_gradient(Path(work, "gradient").read_text(), len(state.symbols)),
        )


@pytest.mark.xtb
@pytest.mark.parametrize("case", ["water", "hydroxide", "hydroxyl", "pd_anion"])
def test_real_matches_hand_run(
    xtb_binary: Path, test_set: dict[str, MolecularState], case: str
) -> None:
    """Energy and gradient equal a hand run of the same argv (<= 1e-10 Eh, <= 1e-9 Eh/Bohr)."""
    s = test_set[case]
    eng = real(xtb_binary)
    result = eng.evaluate(s)
    energy, grad = hand_run(eng.calls[-1], s)
    assert abs(result.energy_hartree - energy) <= 1e-10
    forces = result.forces_hartree_per_bohr
    assert forces is not None
    assert (
        max(
            abs(f + g)
            for fr, gr in zip(forces, grad, strict=True)
            for f, g in zip(fr, gr, strict=True)
        )
        <= 1e-9
    )


@pytest.mark.xtb
def test_real_multiplicity_changes_energy(
    xtb_binary: Path, test_set: dict[str, MolecularState]
) -> None:
    """Behavioural R4: the hydroxyl doublet and the hydroxide anion give different energies."""
    eng = real(xtb_binary)
    radical = eng.evaluate(test_set["hydroxyl"], forces=False).energy_hartree
    anion = eng.evaluate(test_set["hydroxide"], forces=False).energy_hartree
    assert abs(radical - anion) > 1e-2
    assert "--uhf" in eng.calls[0] and eng.calls[0][eng.calls[0].index("--uhf") + 1] == "1"


@pytest.mark.xtb
def test_real_alpb_state(xtb_binary: Path, test_set: dict[str, MolecularState]) -> None:
    """Water in toluene: reference vs gsolv differ by > 1e-3 Eh; gas differs from solvated."""
    water = test_set["water"]
    solv = Solvation(model="alpb", solvent="Toluene")
    gsolv = real(xtb_binary, solvation=solv).evaluate(water, forces=False).energy_hartree
    reference = (
        real(xtb_binary, solvation=solv, options={"alpb_state": "reference"})
        .evaluate(water, forces=False)
        .energy_hartree
    )
    gas = real(xtb_binary).evaluate(water, forces=False).energy_hartree
    print(
        f"water/toluene: gsolv {gsolv!r} reference {reference!r} gas {gas!r} "
        f"diff {abs(gsolv - reference):.4e}"
    )
    assert abs(gsolv - reference) > 1e-3
    assert abs(gsolv - gas) > 1e-4


@pytest.mark.xtb
def test_real_unknown_solvent(xtb_binary: Path, test_set: dict[str, MolecularState]) -> None:
    """An unknown solvent -> EngineRuntimeError (exit 128) whose tail has xtb's own message."""
    eng = real(xtb_binary, solvation=Solvation(model="alpb", solvent="unobtainium"))
    with pytest.raises(EngineRuntimeError, match="exited with 128") as info:
        eng.evaluate(test_set["water"])
    assert "solvent: 'unobtainium' is not parametrized" in info.value.tail


@pytest.mark.xtb
def test_real_hessian(xtb_binary: Path, test_set: dict[str, MolecularState]) -> None:
    """Water Hessian = FD of xtb gradients: symmetric, labelled, <= 1e-4 vs an independent FD."""
    water = test_set["water"]
    eng = real(xtb_binary)
    result = eng.evaluate(water, hessian=True)
    h = result.hessian_hartree_per_bohr2
    assert h is not None and result.hessian_method == "finite_difference"
    assert all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    step = 0.004  # a different step than the engine's 0.005: an independent check
    fd: list[list[float]] = []
    for i in range(9):
        rows = []
        for sign in (1, -1):
            c = [r[:] for r in water.coordinates]
            c[i // 3][i % 3] += sign * step * 0.529177210903
            moved = MolecularState(
                symbols=water.symbols, coordinates=c, charge=0, spin_multiplicity=1
            )
            f = eng.evaluate(moved).forces_hartree_per_bohr
            assert f is not None
            rows.append([v for row in f for v in row])
        fd.append([-(p - m) / (2 * step) for p, m in zip(rows[0], rows[1], strict=True)])
    sym = [[(fd[i][j] + fd[j][i]) / 2 for j in range(9)] for i in range(9)]
    assert max(abs(h[i][j] - sym[i][j]) for i in range(9) for j in range(9)) <= 1e-4


@pytest.mark.xtb
def test_real_hessian_vs_energy_second_differences(
    xtb_binary: Path, test_set: dict[str, MolecularState]
) -> None:
    """R45: the water Hessian agrees with gradient-free energy second differences (<= 1e-4).

    Central, h = 0.005 Bohr, xtb energies only (forces=False): diagonal (E+ - 2 E0 + E-) / h^2,
    off-diagonal (E++ - E+- - E-+ + E--) / (4 h^2), over all 45 upper-triangle elements. This checks
    xtb's gradient file against its energies, which no other test does.
    """
    water = test_set["water"]
    eng = real(xtb_binary)
    h_engine = eng.evaluate(water, hessian=True).hessian_hartree_per_bohr2
    assert h_engine is not None
    step = 0.005
    cache: dict[tuple[tuple[int, int], ...], float] = {}

    def energy(shifts: dict[int, int]) -> float:
        key = tuple(sorted(shifts.items()))
        if key not in cache:
            coords = [row[:] for row in water.coordinates]
            for index, sign in shifts.items():
                coords[index // 3][index % 3] += sign * step * 0.529177210903
            moved = MolecularState(
                symbols=water.symbols, coordinates=coords, charge=0, spin_multiplicity=1
            )
            cache[key] = eng.evaluate(moved, forces=False).energy_hartree
        return cache[key]

    e0 = energy({})
    worst = 0.0
    for i in range(9):
        for j in range(i, 9):
            if i == j:
                second = (energy({i: 1}) - 2 * e0 + energy({i: -1})) / step**2
            else:
                second = (
                    energy({i: 1, j: 1})
                    - energy({i: 1, j: -1})
                    - energy({i: -1, j: 1})
                    + energy({i: -1, j: -1})
                ) / (4 * step**2)
            worst = max(worst, abs(h_engine[i][j] - second))
    print(f"water: max |H_engine - H_energy-second-differences| = {worst:.3e} over 45 elements")
    assert worst <= 1e-4


@pytest.mark.xtb
def test_real_hessian_file_canary(xtb_binary: Path, test_set: dict[str, MolecularState]) -> None:
    """Canary: xtb 6.8.0's --hess file is still projected (> 1e-3 from the Cartesian FD Hessian).

    If this fails, xtb now writes a Cartesian Hessian: revisit R45 (HESSIAN_CONVENTION).
    """
    water = test_set["water"]
    eng = real(xtb_binary)
    fd = eng.evaluate(water, hessian=True).hessian_hartree_per_bohr2
    assert fd is not None
    projected = eng.hessian_file(water)
    gap = max(abs(projected[i][j] - fd[i][j]) for i in range(9) for j in range(9))
    assert gap > 1e-3, f"xtb hessian file now Cartesian; revisit R45 (gap {gap:.2e})"


@pytest.mark.xtb
def test_real_timeout_and_no_stray_files(
    xtb_binary: Path, test_set: dict[str, MolecularState]
) -> None:
    """A 0.01 s timeout raises EngineRuntimeError; real runs leave nothing in the repo."""
    with pytest.raises(EngineRuntimeError, match="timed out"):
        XTBSubprocessEngine.from_stage(stage(), binary=xtb_binary, timeout_s=0.01).evaluate(
            test_set["pd_anion"]
        )
    before = set(os.listdir(REPO))
    real(xtb_binary).evaluate(test_set["water"])
    assert set(os.listdir(REPO)) == before
