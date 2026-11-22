"""xtb engine (tag ``xtb_subprocess``): GFN2-xTB in an isolated subprocess (ADR-0021 PROPOSED).

The xtb 6.8.0 binary (LGPL-3.0 with statically bundled Intel MKL / ifx runtime) is downloaded
by the user, never vendored, and only ever run as a separate process with file I/O in a fresh
temporary directory (``docs/licence-inventory.md``; TJ v0.2.0 Q2 A). No shell is used.

Every evaluation runs ``--grad`` (R39): only that mode writes the ``energy`` and ``gradient``
files (``--json`` has 8 decimals, too coarse). The Hessian is central differences of xtb's
analytic gradients (``fd_step_bohr``, 6N more ``--grad`` runs): xtb's own ``--hess`` file is a
projected Hessian (translations and rotations removed), not the project's Cartesian one, and it
cannot be converted back (see ``HESSIAN_CONVENTION``).
"""

import math
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.engines.base import Engine, RawResult
from eta_rxncat.engines.errors import EngineInputError, EngineRuntimeError, EngineUnavailableError
from eta_rxncat.engines.fd import fd_hessian
from eta_rxncat.engines.options import OptionSpec
from eta_rxncat.engines.units import angstrom_to_bohr, bohr_to_angstrom

XTB_ENV = "ETA_RXNCAT_XTB"
"""Environment variable naming the xtb binary (after an explicit ``binary`` argument)."""

PROVISION_HINT = (
    "download xtb 6.8.0 (xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz, sha256 db0903...4d68) to "
    "~/.local/share/eta-rxncat/xtb/6.8.0/ and pass binary=... or set ETA_RXNCAT_XTB"
)
"""How to provision the binary (named in ``EngineUnavailableError``)."""

ALPB_STATES = frozenset({"gsolv", "bar1M", "reference"})

HESSIAN_CONVENTION = "fd"
"""How the engine gets Hessians (R45), from the measured record
``docs/prd/v0.2.0/evidence/xtb-hessian-convention.json``: xtb 6.8.0's ``hessian`` file differs
from central FD of xtb gradients by 2.7e-3 Eh/Bohr^2 on water (out-of-plane diagonals exactly 0:
translations/rotations projected out), so the engine uses FD of gradients (``fd``)."""

_VERSION = re.compile(r"xtb version (\d+\.\d+\.\d+)")


def resolve_binary(binary: str | os.PathLike[str] | None) -> Path:
    """The xtb binary: ``binary``, else ``$ETA_RXNCAT_XTB``, else ``xtb`` on ``PATH``.

    Raises:
        EngineUnavailableError: none of them names an executable file.
    """
    for candidate in (binary, os.environ.get(XTB_ENV) or None, shutil.which("xtb")):
        if candidate is None:
            continue
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
        if candidate is binary:
            raise EngineUnavailableError(f"xtb_subprocess: binary {path} is not an executable file")
    raise EngineUnavailableError(f"xtb_subprocess: no xtb binary found; {PROVISION_HINT}")


def parse_energy(text: str) -> float:
    """The total energy (Eh) from xtb's ``energy`` file (``$energy`` block, 2nd column)."""
    lines = [line.split() for line in text.splitlines() if line.strip()]
    values = [row for row in lines if not row[0].startswith("$")]
    if not values:
        raise ValueError("xtb energy file has no data line")
    return float(values[-1][1])


def parse_gradient(text: str, n_atoms: int) -> list[list[float]]:
    """The gradient (Eh/Bohr, N x 3) from xtb's Turbomole-format ``gradient`` file."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("$grad"))
    rows = lines[start + 2 + n_atoms : start + 2 + 2 * n_atoms]
    gradient = [[float(v.replace("D", "E")) for v in row.split()] for row in rows]
    if len(gradient) != n_atoms or any(len(row) != 3 for row in gradient):
        raise ValueError(f"xtb gradient file is not {n_atoms} x 3")
    return gradient


def parse_hessian(text: str, n_atoms: int) -> list[list[float]]:
    """The 3N x 3N Hessian (row-major values after ``$hessian``) from xtb's ``hessian`` file."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith("$hessian"))
    values: list[float] = []
    for line in lines[start + 1 :]:
        if line.strip().startswith("$"):
            break
        values.extend(float(v) for v in line.split())
    dof = 3 * n_atoms
    if len(values) != dof * dof:
        raise ValueError(f"xtb hessian file has {len(values)} values, not {dof * dof}")
    return [values[i * dof : (i + 1) * dof] for i in range(dof)]


def parse_version(text: str) -> str:
    """``"xtb <x.y.z>"`` from ``xtb --version`` output."""
    match = _VERSION.search(text)
    if match is None:
        raise ValueError("no 'xtb version x.y.z' line")
    return f"xtb {match.group(1)}"


def _tail(proc_out: str | bytes | None, proc_err: str | bytes | None) -> str:
    def text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        return value.decode(errors="replace") if isinstance(value, bytes) else value

    return f"--- stderr ---\n{text(proc_err)}\n--- stdout ---\n{text(proc_out)}"


class XTBSubprocessEngine(Engine):
    """GFN2-xTB single points with gradients and Hessians, via the xtb 6.8.0 binary.

    ``stage.method`` is ``gfn2``. Keyed: ``accuracy`` (1.0), ``etemp_k`` (300.0), ``alpb_state``
    (``gsolv`` | ``bar1M`` | ``reference``, default ``gsolv``), ``fd_step_bohr`` (0.005, the
    Hessian's FD step), ``engine_impl``. Solvation is
    ``none`` or ``alpb`` with a solvent name (lowercased; dielectric-only refused). Runtime (never
    keyed): ``binary``, ``threads`` (1), ``timeout_s`` (3600), ``omp_stacksize`` ("1G"),
    ``keep_failed`` (False).
    """

    tag = "xtb_subprocess"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {
        "accuracy": OptionSpec(float, 1.0),
        "etemp_k": OptionSpec(float, 300.0),
        "alpb_state": OptionSpec(str, "gsolv", ALPB_STATES),
        "fd_step_bohr": OptionSpec(float, 0.005),
    }

    def __init__(
        self,
        stage: StageConfig,
        *,
        binary: str | os.PathLike[str] | None = None,
        threads: int = 1,
        timeout_s: float = 3600.0,
        omp_stacksize: str = "1G",
        keep_failed: bool = False,
        **runtime: Any,
    ) -> None:
        """Resolve the stage, check method/solvation/runtime, and locate the binary.

        Raises:
            EngineInputError: a method other than ``gfn2``, a solvation model other than
                ``none``/``alpb``, a dielectric-only ALPB, or bad runtime/option values.
            EngineUnavailableError: no xtb binary.
        """
        super().__init__(stage, **runtime)
        if self.stage.method != "gfn2":
            raise EngineInputError(f"xtb_subprocess: method {stage.method!r} is not 'gfn2'")
        solvation = self.stage.solvation
        if solvation.model not in ("none", "alpb"):
            raise EngineInputError(
                f"xtb_subprocess: solvation {solvation.model!r} is not 'none' or 'alpb'"
            )
        if solvation.model == "alpb" and not solvation.solvent:
            raise EngineInputError(
                "xtb_subprocess: ALPB needs a solvent name; a dielectric alone is not supported"
            )
        for key in ("accuracy", "etemp_k", "fd_step_bohr"):
            value = self.stage.options[key]
            if not isinstance(value, float) or not value > 0 or not math.isfinite(value):
                raise EngineInputError(f"xtb_subprocess: option {key!r} must be > 0, not {value!r}")
        if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1:
            raise EngineInputError(f"xtb_subprocess: threads must be an int >= 1, not {threads!r}")
        if (
            isinstance(timeout_s, bool)
            or not isinstance(timeout_s, int | float)
            or not timeout_s > 0
        ):
            raise EngineInputError(f"xtb_subprocess: timeout_s must be > 0, not {timeout_s!r}")
        if not isinstance(omp_stacksize, str) or not re.fullmatch(r"\d+[KMGkmg]?", omp_stacksize):
            raise EngineInputError(f"xtb_subprocess: bad omp_stacksize {omp_stacksize!r}")
        self.binary = resolve_binary(binary)
        self.threads = threads
        self.timeout_s = float(timeout_s)
        self.omp_stacksize = omp_stacksize
        self.keep_failed = keep_failed
        self.calls: list[list[str]] = []
        self._version: str | None = None

    @property
    def identity(self) -> EngineIdentity:
        """``xtb_subprocess`` at ``"xtb <x.y.z>"`` from the binary's ``--version``."""
        if self._version is None:
            proc = self._run([str(self.binary), "--version"], cwd=None)
            try:
                self._version = parse_version(proc.stdout)
            except ValueError as exc:
                raise EngineRuntimeError(
                    "xtb_subprocess: cannot read the xtb version",
                    tail=_tail(proc.stdout, proc.stderr),
                ) from exc
        return EngineIdentity(name="xtb_subprocess", version=self._version, model=None)

    def argv(self, state: MolecularState, mode: str) -> list[str]:
        """The xtb argv for ``state``; ``mode`` is ``--grad`` or ``--hess``."""
        options = self.stage.options
        argv = [
            str(self.binary),
            "input.xyz",
            "--gfn",
            "2",
            "--chrg",
            str(state.charge),
            "--uhf",
            str(state.spin_multiplicity - 1),
            "--acc",
            str(options["accuracy"]),
            "--etemp",
            str(options["etemp_k"]),
        ]
        solvation = self.stage.solvation
        if solvation.model == "alpb":
            assert solvation.solvent
            argv += ["--alpb", solvation.solvent, str(options["alpb_state"])]
        return [*argv, mode]

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        threads = str(self.threads)
        env.update(
            {
                "OMP_NUM_THREADS": threads,
                "MKL_NUM_THREADS": threads,
                "OMP_STACKSIZE": self.omp_stacksize,
            }
        )
        return env

    def _run(self, argv: Sequence[str], cwd: Path | None) -> subprocess.CompletedProcess[str]:
        try:
            proc = subprocess.run(
                list(argv),
                cwd=cwd,
                env=self._env(),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise EngineRuntimeError(
                f"xtb_subprocess: xtb timed out after {self.timeout_s} s",
                tail=_tail(exc.stdout, exc.stderr),
            ) from exc
        except OSError as exc:
            raise EngineRuntimeError(f"xtb_subprocess: cannot run {argv[0]}: {exc}") from exc
        if proc.returncode != 0:
            raise EngineRuntimeError(
                f"xtb_subprocess: xtb exited with {proc.returncode}",
                tail=_tail(proc.stdout, proc.stderr),
            )
        return proc

    def _invoke(self, state: MolecularState, mode: str, outputs: Sequence[str]) -> dict[str, str]:
        """Run one xtb call in a fresh temp dir and return the named output files' text."""
        work = Path(tempfile.mkdtemp(prefix="eta_xtb_"))
        ok = False
        try:
            lines = [str(len(state.symbols)), "eta-rxncat"]
            lines += [
                f"{s} {x!r} {y!r} {z!r}"
                for s, (x, y, z) in zip(state.symbols, state.coordinates, strict=True)
            ]
            (work / "input.xyz").write_text("\n".join(lines) + "\n", encoding="utf-8")
            argv = self.argv(state, mode)
            self.calls.append(argv)
            proc = self._run(argv, cwd=work)
            found: dict[str, str] = {}
            for name in outputs:
                path = work / name
                if not path.is_file():
                    raise EngineRuntimeError(
                        f"xtb_subprocess: xtb wrote no {name!r} file",
                        tail=_tail(proc.stdout, proc.stderr),
                    )
                found[name] = path.read_text(encoding="utf-8")
            ok = True
            return found
        finally:
            if ok or not self.keep_failed:
                shutil.rmtree(work, ignore_errors=True)

    def _grad_run(self, state: MolecularState) -> tuple[float, list[list[float]]]:
        """One ``--grad`` call: (energy Eh, gradient Eh/Bohr N x 3)."""
        files = self._invoke(state, "--grad", ("energy", "gradient"))
        try:
            return (
                parse_energy(files["energy"]),
                parse_gradient(files["gradient"], len(state.symbols)),
            )
        except (ValueError, IndexError, StopIteration) as exc:
            raise EngineRuntimeError(
                f"xtb_subprocess: cannot parse xtb output: {exc}", tail=files["energy"]
            ) from exc

    def hessian_file(self, state: MolecularState) -> list[list[float]]:
        """Xtb's own ``--hess`` file for ``state`` (projected; for the R13 record and canary)."""
        files = self._invoke(state, "--hess", ("hessian",))
        try:
            return parse_hessian(files["hessian"], len(state.symbols))
        except (ValueError, StopIteration) as exc:
            raise EngineRuntimeError(f"xtb_subprocess: cannot parse xtb hessian: {exc}") from exc

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        energy, gradient = self._grad_run(state)
        result = RawResult(energy_hartree=energy, device="cpu", recovery_steps=[])
        if forces or hessian:
            result.forces_hartree_per_bohr = [[-v for v in row] for row in gradient]
        if hessian:

            def forces_at(coords_bohr: list[list[float]]) -> list[list[float]]:
                displaced = MolecularState(
                    symbols=state.symbols,
                    coordinates=[[bohr_to_angstrom(v) for v in row] for row in coords_bohr],
                    charge=state.charge,
                    spin_multiplicity=state.spin_multiplicity,
                )
                return [[-v for v in row] for row in self._grad_run(displaced)[1]]

            coords = [[angstrom_to_bohr(v) for v in row] for row in state.coordinates]
            step = self.stage.options["fd_step_bohr"]
            assert isinstance(step, float)
            matrix, asym = fd_hessian(forces_at, coords, step)
            result.hessian_hartree_per_bohr2 = matrix
            result.hessian_method = "finite_difference"
            result.hessian_max_asymmetry = asym
        return result
