"""geomeTRIC 1.1.1 behind the ``Optimizer`` interface (TJ Q3 "A"; R2, R44, R45; DV-13, DV-14).

geomeTRIC is the optional ``opt-geometric`` extra and is imported only inside this module's
functions. ``geometric.optimize.run_optimizer`` is never called: it runs
``logging.config.fileConfig``, which closes the host's handlers (R2). Its minimal path is
replicated instead: ``OptParams``, a ``Molecule``, the coordinate system built from
``geometric.internal`` (``CoordSysDict`` is a local of ``run_optimizer``, R44), and
``Optimizer(...).optimizeGeometry()``. Every step runs in a fresh temporary directory with the
``geometric`` logger redirected into it and numpy's global RNG seeded (both restored after); the
root logger is never touched. geomeTRIC writes scratch files into the working directory, so
``minimize`` also runs each step in a temporary working directory and restores the caller's
(v0.7.0, R8).

Every engine evaluation is captured as an ``OptimizationFrame`` (v0.7.0): the result carries them,
and ``capture_frames`` gives them to a caller whose run raises.
"""

import importlib.metadata
import logging
import math
import os
import tempfile
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from eta_rxncat.core import (
    MolecularState,
    OptimizationFrame,
    OptimizationResult,
    OptimizerIdentity,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import BOHR_ANGSTROM, Engine, OptionSpec
from eta_rxncat.optimize.base import (
    DihedralConstraint,
    Optimizer,
    check_constraints,
    constraints_text,
    frame_sink,
)
from eta_rxncat.optimize.errors import (
    OptimizationFailedError,
    OptimizerInputError,
    OptimizerUnavailableError,
)

CONVERGENCE_SETS = (
    "GAU",
    "NWCHEM_LOOSE",
    "GAU_LOOSE",
    "TURBOMOLE",
    "INTERFRAG_TIGHT",
    "GAU_TIGHT",
    "GAU_VERYTIGHT",
)
"""geomeTRIC 1.1.1's named convergence sets (``params.py``)."""

COORDSYS = ("tric", "cart", "dlc", "hdlc")
"""Coordinate systems offered (the subset of ``run_optimizer``'s table this package uses)."""

DIHEDRAL_TOL_DEG = 0.1
"""A converged constrained dihedral must be within this of its target (degrees)."""

ENFORCE_THRESHOLD = 0.1
"""geomeTRIC ``enforce`` threshold (a.u./rad), set only for runs with frozen atoms.

With geomeTRIC's default (0.0) a constraint is only satisfied to ``convergence_cmax`` (1e-2): a
frozen water O moved 3e-4 to 5e-4 Angstrom (slice 04, H15). With 0.1, frozen atoms move
<= 4e-9 Angstrom, deterministically across hash seeds. It is not used for dihedrals: there it
made the T1 planar run hang in 2 of 4 hash seeds, while the default reaches |phi| <= 0.01 deg
(slice 04 measurements). ``conmethod=1`` failed to converge the dihedral.
"""

GEOMETRIC_RNG_SEED = 0
"""Seed of numpy's global RNG for the duration of each geomeTRIC run (state restored after)."""

ACCEPTED_MATCH_TOL_ANGSTROM = 1e-6
"""Largest coordinate difference at which a trajectory-file frame is an evaluated one (R33).

Measured (M11): matching frames differ by at most 5.0e-11 Angstrom, the nearest other evaluation
by at least 5.3e-4 Angstrom.
"""

_CWD_LOCK = threading.Lock()
"""The working directory is process-wide, so only one run may change it at a time."""

UNAVAILABLE = (
    "geomeTRIC is not installed: the geometric optimizer needs the opt-geometric extra "
    "(uv sync --extra opt-geometric)"
)

_RETRY_ERRORS = ("GeomOptNotConvergedError", "GeomOptStructureError")


def _geometric() -> Any:
    """Import and return the ``geometric`` package, or raise ``OptimizerUnavailableError``."""
    try:
        import geometric
    except ImportError as exc:
        raise OptimizerUnavailableError(UNAVAILABLE) from exc
    return geometric


def _wrap_deg(angle: float) -> float:
    """Return ``angle`` wrapped to (-180, 180]."""
    wrapped = math.fmod(angle, 360.0)
    if wrapped <= -180.0:
        wrapped += 360.0
    elif wrapped > 180.0:
        wrapped -= 360.0
    return wrapped


def dihedral_deg(coords: Sequence[Sequence[float]], atoms: tuple[int, int, int, int]) -> float:
    """Return the dihedral angle of four atoms in degrees, in (-180, 180]."""
    p0, p1, p2, p3 = (coords[i] for i in atoms)
    b0 = [p0[k] - p1[k] for k in range(3)]
    b1 = [p2[k] - p1[k] for k in range(3)]
    b2 = [p3[k] - p2[k] for k in range(3)]

    def dot(a: list[float], b: list[float]) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def cross(a: list[float], b: list[float]) -> list[float]:
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]

    norm = math.sqrt(dot(b1, b1))
    unit = [x / norm for x in b1]
    v = [b0[k] - dot(b0, unit) * unit[k] for k in range(3)]
    w = [b2[k] - dot(b2, unit) * unit[k] for k in range(3)]
    x = dot(v, w)
    y = dot(cross(unit, v), w)
    return _wrap_deg(math.degrees(math.atan2(y, x)))


@contextmanager
def _sandbox() -> Iterator[Path]:
    """Yield a fresh temp dir; route the ``geometric`` logger into it for the duration.

    The logger's handlers, level and ``propagate`` are restored afterwards; the root logger and
    the working directory are never touched.
    """
    logger = logging.getLogger("geometric")
    saved = (list(logger.handlers), logger.level, logger.propagate)
    with tempfile.TemporaryDirectory(prefix="eta-geometric-") as tmp:
        handler = logging.FileHandler(Path(tmp) / "geometric.log", encoding="utf-8")
        try:
            logger.handlers = [handler]
            logger.setLevel(logging.INFO)
            logger.propagate = False
            yield Path(tmp)
        finally:
            logger.handlers, level, logger.propagate = saved[0], saved[1], saved[2]
            logger.setLevel(level)
            handler.close()


@contextmanager
def _scratch_cwd() -> Iterator[None]:
    """Run the block in a temporary working directory under ``$TMPDIR``; restore the old one."""
    with _CWD_LOCK:
        previous = os.getcwd()
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            try:
                os.chdir(tmp)
                yield
            finally:
                # Twice, so an asynchronous deadline signal landing in the first call cannot
                # leave the process in the directory that is about to be removed.
                try:
                    os.chdir(previous)
                finally:
                    os.chdir(previous)


def _read_xyz_frames(path: Path, n_atoms: int) -> list[Any]:
    """Return each frame of a multi-frame XYZ file as an N x 3 array.

    Raises:
        OSError: The file cannot be read.
        ValueError: It is not a multi-frame XYZ file of ``n_atoms`` atoms.
    """
    import numpy as np

    lines = path.read_text(encoding="utf-8").rstrip().splitlines()
    frames: list[Any] = []
    start = 0
    while start < len(lines):
        rows = lines[start + 2 : start + 2 + n_atoms]
        if int(lines[start]) != n_atoms or len(rows) != n_atoms:
            raise ValueError(f"frame at line {start + 1} does not hold {n_atoms} atoms")
        xyz = np.asarray([[float(v) for v in row.split()[1:4]] for row in rows], dtype=np.float64)
        if xyz.shape != (n_atoms, 3):
            raise ValueError(f"frame at line {start + 1} is not {n_atoms} x 3")
        frames.append(xyz)
        start += n_atoms + 2
    return frames


def _mark_accepted(frames: list[OptimizationFrame], first: int, path: Path) -> None:
    """Set ``accepted_bool`` on ``frames[first:]`` from one ladder step's trajectory file.

    Each frame of the file matches the first later unmatched evaluated frame within
    ``ACCEPTED_MATCH_TOL_ANGSTROM``; matched frames become ``True``, the step's others ``False``.
    A missing or unreadable file, or a file frame without a match, leaves every frame ``None``.
    Never raises: the marking is a label and must not change a run's outcome.
    """
    try:
        import numpy as np

        evaluated = [np.asarray(f.coordinates_angstrom, dtype=np.float64) for f in frames[first:]]
        if not evaluated:
            return
        written = _read_xyz_frames(path, len(evaluated[0]))
        if not written:
            return
        matched: set[int] = set()
        k = 0
        for xyz in written:
            while k < len(evaluated) and not (
                np.max(np.abs(evaluated[k] - xyz)) <= ACCEPTED_MATCH_TOL_ANGSTROM
            ):
                k += 1
            if k == len(evaluated):
                return
            matched.add(k)
            k += 1
        for i in range(len(evaluated)):
            frames[first + i] = frames[first + i].model_copy(update={"accepted_bool": i in matched})
    except Exception:
        logging.getLogger(__name__).debug("accepted frames not marked", exc_info=True)


@dataclass
class _Tally:
    """Engine calls, last energy and frames, across every ladder step of one run."""

    calls: int = 0
    last_energy: float | None = None
    frames: list[OptimizationFrame] = field(default_factory=list)


def _bridge(
    molecule: Any, state: MolecularState, engine: Engine, tally: _Tally, ladder_step: str
) -> Any:
    """Return a ``geometric.engine.Engine`` that evaluates ``engine`` (Bohr in; Eh, Eh/Bohr out)."""
    from geometric.engine import Engine as GeometricEngine

    class Bridge(GeometricEngine):  # type: ignore[misc]
        """geomeTRIC engine over an eta-rxncat ``Engine``."""

        def calc_new(self, coords: Any, dirname: str) -> dict[str, Any]:
            import numpy as np

            xyz = np.asarray(coords, dtype=np.float64).reshape(-1, 3) * BOHR_ANGSTROM
            current = MolecularState.model_validate(
                {**state.model_dump(), "coordinates": xyz.tolist()}
            )
            tally.calls += 1
            # eta_rxncat's EngineError is deliberately not caught: it ends the optimization.
            result = engine.evaluate(current, forces=True)
            forces = np.asarray(result.forces_hartree_per_bohr, dtype=np.float64)
            tally.last_energy = result.energy_hartree
            # Built whole, then appended once: an asynchronous deadline cannot leave half a frame.
            frame = OptimizationFrame(
                coordinates_angstrom=current.coordinates,
                energy_hartree=result.energy_hartree,
                max_gradient_hartree_per_bohr=float(np.max(np.abs(forces))),
                ladder_step=ladder_step,
            )
            tally.frames.append(frame)
            return {"energy": result.energy_hartree, "gradient": -forces.ravel()}

    return Bridge(molecule)


class GeometricOptimizer(Optimizer):
    """geomeTRIC 1.1.1 with a recorded three-step recovery ladder (US-008).

    Keyed options: ``coordsys`` (tric), ``convergence_set`` (GAU), ``maxiter`` (300), ``trust``
    (0.1 Bohr) and ``hessian`` (never). Ladder: ``tric`` (the given options), then
    ``tric_tight_trust`` (``trust=0.03``, ``hessian="first"``), then ``cartesian``
    (``coordsys="cart"``, ``trust=0.05``) for an unconstrained run or ``hdlc``
    (``coordsys="hdlc"``, ``trust=0.05``) for a constrained one (R45). A step is tried only after
    the previous one raised ``GeomOptNotConvergedError`` (also what reaching ``maxiter`` raises)
    or ``GeomOptStructureError``.

    While a step runs, the working directory of the whole process is a temporary one. Relative
    paths used by a host program's own threads resolve there in the meantime, so a threaded host
    should use absolute paths. The lock that serialises the directory change is not reentrant: an
    engine that calls ``minimize`` again from inside ``evaluate`` deadlocks.
    """

    OPTIONS: ClassVar[Mapping[str, OptionSpec]] = {
        "coordsys": OptionSpec(str, "tric", frozenset(COORDSYS)),
        "convergence_set": OptionSpec(str, "GAU", frozenset(CONVERGENCE_SETS)),
        "maxiter": OptionSpec(int, 300),
        "trust": OptionSpec(float, 0.1),
        "hessian": OptionSpec(str, "never", frozenset({"never", "first"})),
    }

    def __init__(self) -> None:
        """Check that geomeTRIC is importable.

        Raises:
            OptimizerUnavailableError: geomeTRIC is not installed
                (``uv sync --extra opt-geometric``).
        """
        _geometric()

    @property
    def identity(self) -> OptimizerIdentity:
        """``geometric`` at the installed version."""
        return OptimizerIdentity(name="geometric", version=importlib.metadata.version("geometric"))

    def resolved_options(self, options: Mapping[str, ScalarValue] | None) -> dict[str, ScalarValue]:
        """Resolve the options; ``maxiter`` must be >= 1 and ``trust`` > 0 and finite."""
        resolved = super().resolved_options(options)
        maxiter = resolved["maxiter"]
        if not isinstance(maxiter, int) or maxiter < 1:
            raise OptimizerInputError(f"GeometricOptimizer: maxiter must be >= 1, not {maxiter!r}")
        trust = resolved["trust"]
        if not isinstance(trust, float) or not (math.isfinite(trust) and trust > 0.0):
            raise OptimizerInputError(f"GeometricOptimizer: trust must be > 0, not {trust!r}")
        return resolved

    @staticmethod
    def ladder(
        options: Mapping[str, ScalarValue], constrained: bool
    ) -> list[tuple[str, dict[str, ScalarValue]]]:
        """Return the recovery steps as ``(name, options)`` pairs."""
        last: tuple[str, dict[str, ScalarValue]] = (
            ("hdlc", {**options, "coordsys": "hdlc", "trust": 0.05})
            if constrained
            else ("cartesian", {**options, "coordsys": "cart", "trust": 0.05})
        )
        return [
            ("tric", dict(options)),
            ("tric_tight_trust", {**options, "trust": 0.03, "hessian": "first"}),
            last,
        ]

    def minimize(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        frozen_atom_indices: Sequence[int] = (),
        dihedral_constraints: Sequence[DihedralConstraint] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> OptimizationResult:
        """Minimise ``state`` on ``engine`` through the recovery ladder.

        Raises:
            OptimizerInputError: Bad options or constraints, or ``coordsys="cart"`` with a
                constraint (geomeTRIC refuses constraints in Cartesian coordinates, R45); raised
                before any engine call.
            OptimizationFailedError: Every step failed, or a constrained dihedral of the converged
                geometry is more than 0.1 deg from its target.
            eta_rxncat.engines.EngineError: Raised by the engine; no further step is tried.
        """
        frozen = list(frozen_atom_indices)
        dihedrals = list(dihedral_constraints)
        check_constraints(state, frozen, dihedrals)
        resolved = self.resolved_options(options)
        constrained = bool(frozen or dihedrals)
        if constrained and resolved["coordsys"] == "cart":
            raise OptimizerInputError(
                "coordsys 'cart' cannot hold constraints (geomeTRIC refuses them in Cartesian "
                "coordinates); use tric, dlc or hdlc"
            )
        text = constraints_text(frozen, dihedrals)
        geometric_text = self._geometric_constraints(frozen, dihedrals)
        errors = _geometric().errors
        retry: tuple[type[BaseException], ...] = tuple(getattr(errors, n) for n in _RETRY_ERRORS)

        tried: list[str] = []
        sink = frame_sink()
        tally = _Tally() if sink is None else _Tally(frames=sink)
        first_frame = len(tally.frames)
        for name, step_options in self.ladder(resolved, constrained):
            tried.append(name)
            try:
                with _scratch_cwd():
                    coords, energy, n_steps = self._run(
                        state, engine, step_options, geometric_text, tally, name
                    )
            except retry:
                continue
            final = state.model_copy(update={"coordinates": coords})
            for constraint in dihedrals:
                phi = dihedral_deg(coords, constraint.atoms)
                if abs(_wrap_deg(phi - constraint.value_deg)) > DIHEDRAL_TOL_DEG:
                    raise OptimizationFailedError(
                        f"dihedral {list(constraint.atoms)} converged at {phi:.4f} deg, target "
                        f"{constraint.value_deg:.4f} deg (tolerance {DIHEDRAL_TOL_DEG})",
                        steps=tuple(tried),
                        last_energy_hartree=energy,
                    )
            recorded = dict(resolved)
            if text:
                recorded["constraints"] = text
            return OptimizationResult(
                final_state=final,
                final_energy_hartree=energy,
                converged=True,
                n_steps=n_steps,
                n_engine_calls=tally.calls,
                recovery_steps=tried,
                optimizer=self.identity,
                options=recorded,
                frames=tally.frames[first_frame:],
            )
        raise OptimizationFailedError(
            "geomeTRIC did not converge on any recovery step",
            steps=tuple(tried),
            last_energy_hartree=tally.last_energy,
        )

    @staticmethod
    def _geometric_constraints(
        frozen: Sequence[int], dihedrals: Sequence[DihedralConstraint]
    ) -> str:
        """Return the geomeTRIC constraint text (1-based indices), or ``""``."""
        blocks: list[str] = []
        if frozen:
            blocks.append("$freeze\nxyz " + ",".join(str(i + 1) for i in sorted(frozen)) + "\n")
        if dihedrals:
            lines = [
                "dihedral " + " ".join(str(a + 1) for a in c.atoms) + f" {c.value_deg:.6f}"
                for c in dihedrals
            ]
            blocks.append("$set\n" + "\n".join(lines) + "\n")
        return "".join(blocks)

    def _run(
        self,
        state: MolecularState,
        engine: Engine,
        options: Mapping[str, ScalarValue],
        constraint_text: str,
        tally: _Tally,
        ladder_step: str,
    ) -> tuple[list[list[float]], float, int]:
        """Run one geomeTRIC optimization; return (coords in Angstrom, energy, steps)."""
        import numpy as np
        from geometric.internal import CartesianCoordinates, DelocalizedInternalCoordinates
        from geometric.molecule import Molecule
        from geometric.optimize import Optimizer as GeometricLoop
        from geometric.params import OptParams
        from geometric.prepare import parse_constraints

        table: dict[str, tuple[Callable[..., Any], bool, bool]] = {
            "tric": (DelocalizedInternalCoordinates, False, False),
            "cart": (CartesianCoordinates, False, False),
            "dlc": (DelocalizedInternalCoordinates, True, False),
            "hdlc": (DelocalizedInternalCoordinates, False, True),
        }
        coord_class, connect, addcart = table[str(options["coordsys"])]
        with _sandbox() as tmp:
            molecule = Molecule()
            molecule.elem = list(state.symbols)
            molecule.xyzs = [np.asarray(state.coordinates, dtype=np.float64)]
            molecule.build_topology()
            cons = cvals = None
            if constraint_text:
                cons, cvals = parse_constraints(molecule, constraint_text)
            kwargs: dict[str, Any] = {
                "convergence_set": options["convergence_set"],
                "maxiter": options["maxiter"],
                "trust": options["trust"],
                "hessian": options["hessian"],
            }
            if "$freeze" in constraint_text:
                kwargs["enforce"] = ENFORCE_THRESHOLD
            params = OptParams(**kwargs)
            params.xyzout = str(tmp / "optim.xyz")
            ic = coord_class(
                molecule,
                build=True,
                connect=connect,
                addcart=addcart,
                constraints=cons,
                cvals=cvals[0] if cvals is not None else None,
            )
            bridge = _bridge(molecule, state, engine, tally, ladder_step)
            start = np.asarray(state.coordinates, dtype=np.float64).ravel() / BOHR_ANGSTROM
            loop = GeometricLoop(start, molecule, ic, bridge, str(tmp / "work"), params)
            # geomeTRIC draws from numpy's global RNG (step.py trust_step oscillation breaker;
            # internal.py GInverse_SVD perturbation), which made identical inputs converge to
            # different structures (slice 04). Seed it for the run; restore the host's state.
            rng_state = np.random.get_state()
            np.random.seed(GEOMETRIC_RNG_SEED)
            first_frame = len(tally.frames)
            try:
                progress = loop.optimizeGeometry()
            finally:
                np.random.set_state(rng_state)
                # Here, so a failed step's frames are marked before its directory is removed.
                _mark_accepted(tally.frames, first_frame, tmp / "optim.xyz")
        coords = np.asarray(progress.xyzs[-1], dtype=np.float64).tolist()
        energy = float(progress.qm_energies[-1])
        return coords, energy, len(progress.xyzs) - 1
