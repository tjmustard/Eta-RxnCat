"""PySCF engine, CPU path (tag ``pyscf_gpu_cpu``; GPU4PySCF dispatch is slice 07).

Density-fitted (keyed) RKS/UKS/RHF/UHF with explicit charge and spin, the def2 ECP rule
(R3, ADR-0018), ddCOSMO and C-PCM/IEF-PCM solvation from a solvent name or dielectric (R2),
the SCF escalation ladder followed by a mandatory internal stability analysis (R9), and
analytic gradients, and Hessians that are analytic where PySCF's analytic Hessian is correct
(HF) and central differences of analytic gradients elsewhere (see ``HESSIAN_SUPPORT``).

PySCF (Apache-2.0) is imported lazily, inside methods only.
"""

import importlib
import math
from typing import Any, ClassVar

from eta_rxncat.core import Device, EngineIdentity, MolecularState, StageConfig
from eta_rxncat.core.elements import ATOMIC_NUMBERS
from eta_rxncat.engines.base import Engine, RawResult
from eta_rxncat.engines.errors import (
    EngineInputError,
    EngineRuntimeError,
    EngineUnavailableError,
    ScfConvergenceError,
)
from eta_rxncat.engines.fd import fd_hessian
from eta_rxncat.engines.identity import library_version
from eta_rxncat.engines.options import OptionSpec, normalise_solvent
from eta_rxncat.engines.pyscf_gpu_cpu.gpu import (
    GPU_ANALYTIC_KS_HESSIAN_CLASSES,
    GPU_KS_HESSIAN_GRID_RESPONSE,
    GPU_STABILITY_CPU_COPY_STEP,
    GPU_STABILITY_MIN_ROTATIONS,
    estimate_bytes,
    free_pools,
    gpu_error_types,
    gpu_ks_hessian_class,
    gpu_modules,
    is_gpu_oom,
    to_host,
)
from eta_rxncat.engines.pyscf_gpu_cpu.solvents import DIELECTRICS
from eta_rxncat.engines.pyscf_gpu_cpu.stability import lowest_internal
from eta_rxncat.utils.hw_probe import vram_budget_bytes

AUTO = "auto"
"""Option value meaning "apply the engine's rule" (``ecp``: rule 3; ``ladder_small_basis``)."""

ECP_NONE = "none"
"""Resolved ``ecp`` when no atom needs one (or an explicit all-electron request)."""

HEAVY_Z = 36
"""Atoms with Z above this (beyond Kr) take an ECP with def2 bases."""

RUNG_MAX_CYCLE = 100
"""SCF cycle budget for the ladder's later rungs and FD displacements (``ladder_max_cycle`` is the
DIIS rung's budget only, per Mini-requirement 5)."""

LEVEL_SHIFT = 0.25
DAMP = 0.5
MAX_STABILITY_FOLLOWS = 2

HESSIAN_SUPPORT: dict[tuple[str, str], str] = {
    ("hf", "none"): "analytic",
    ("hf", "pcm"): "analytic",
    ("hf", "ddcosmo"): "finite_difference",
    ("ks", "none"): "finite_difference",
    ("ks", "pcm"): "finite_difference",
    ("ks", "ddcosmo"): "finite_difference",
}
"""Hessian method per (method family, solvation model) on PySCF 2.15.1 (CPU), measured by the
seat command recorded in ``docs/prd/v0.2.0/evidence/pyscf-cpu-support.json``:

- HF (RHF/UHF; DF or not; with or without ECP; gas or PCM): the analytic Hessian agrees with
  FD of analytic gradients to <= 3e-5 Eh/Bohr^2, so it is used.
- Kohn-Sham: the analytic Hessian is wrong at the default grid (HBr B3LYP 84% off on H_zz, HI
  with def2 ECP 18% and still 8% at grid level 9, water 3.2e-4), while analytic gradients
  agree with FD of the energy to <= 6.5e-6. So every KS Hessian is FD of analytic gradients.
- ddCOSMO: PySCF has no analytic Hessian (AttributeError), so FD of analytic gradients.
"""


ANALYTIC_REFUSED = "analytic KS Hessian is unreliable in PySCF 2.15.1 (R41)"
"""``EngineInputError`` text for ``hessian_mode="analytic"`` where PySCF's analytic Hessian is not
trusted (a KS functional, or ddCOSMO, which has none)."""


def hessian_method_for(stage: StageConfig) -> str:
    """``analytic`` or ``finite_difference`` for ``stage`` under its keyed ``hessian_mode`` (R41).

    ``auto`` applies ``HESSIAN_SUPPORT``; ``fd_gradients`` forces FD of analytic gradients;
    ``analytic`` is honoured only where ``auto`` would choose it.

    Raises:
        EngineInputError: ``hessian_mode="analytic"`` with a KS functional or ddCOSMO.
    """
    family = "hf" if stage.method == "hf" else "ks"
    measured = HESSIAN_SUPPORT[(family, stage.solvation.model)]
    mode = stage.options.get("hessian_mode", "auto")
    if mode == "fd_gradients":
        return "finite_difference"
    if mode == "analytic":
        if measured != "analytic":
            raise EngineInputError(f"pyscf_gpu_cpu: {ANALYTIC_REFUSED}")
        return "analytic"
    return measured


def _pyscf() -> Any:
    """Import the PySCF modules the engine uses (lazily)."""
    try:
        pyscf = importlib.import_module("pyscf")
        for name in ("gto", "scf", "dft", "scf.addons", "dft.libxc", "lib.exceptions"):
            importlib.import_module(f"pyscf.{name}")
    except ImportError as exc:  # pragma: no cover - pyscf is in the base install
        raise EngineUnavailableError("PySCF is not installed (it is in the base install)") from exc
    return pyscf


def is_def2(basis: str) -> bool:
    """Whether ``basis`` is a def2 basis (case-insensitive ``def2-`` prefix)."""
    return basis.lower().startswith("def2-")


def default_small_basis(basis: str) -> str:
    """The ladder's small basis for ``basis`` (rule 5)."""
    return "minao" if is_def2(basis) else "sto-3g"


class PySCFEngine(Engine):
    """PySCF single points with analytic gradients, on the GPU (GPU4PySCF) or the CPU.

    ``stage.method`` is an xc functional name accepted by ``pyscf.dft.libxc`` or ``hf``;
    ``stage.basis`` is required. One resolved stage drives both devices; the device is never
    keyed. Runtime arguments (never keyed): ``device`` (``auto``: the GPU when the ``gpu`` extra
    and a CUDA device are present, else the CPU with ``device_reason="gpu_unavailable"``;
    ``cuda``: the GPU or ``EngineUnavailableError``; ``cpu``), ``max_memory_mb`` and
    ``ladder_max_cycle`` (the DIIS rung's cycle budget, default 100; later rungs use
    ``RUNG_MAX_CYCLE``).

    On the GPU path: ddCOSMO always runs on the CPU (``ddcosmo_cpu_only``); a VRAM estimate above
    the ADR-0008 budget runs on the CPU (``vram_estimate_over_budget``); one of the four listed
    CUDA out-of-memory errors frees CuPy's pools and re-runs once on the CPU (``gpu_oom``). Every
    CPU run on a GPU-capable host records why in ``device_reason`` and ``recovery_steps``.
    """

    tag = "pyscf_gpu_cpu"
    ENGINE_IMPL: ClassVar[int] = 2
    """2 (R54): the stability verdict is the engine's ``stability_tol`` rule, not PySCF's -1e-5."""
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {
        "density_fit": OptionSpec(bool, True),
        "auxbasis": OptionSpec(str, "def2-universal-jkfit"),
        "ecp": OptionSpec(str, AUTO),
        "grids_level": OptionSpec(int, 3),
        "conv_tol": OptionSpec(float, 1e-10),
        "init_guess": OptionSpec(str, "minao", frozenset({"minao", "atom", "huckel"})),
        "pcm_method": OptionSpec(str, "C-PCM", frozenset({"C-PCM", "IEF-PCM"})),
        "ladder_small_basis": OptionSpec(str, AUTO),
        "stability": OptionSpec(str, "internal", frozenset({"internal"})),
        "stability_tol": OptionSpec(float, 1e-3),
        "stability_noise_eh": OptionSpec(float, 1e-6),
        "fd_step_bohr": OptionSpec(float, 0.005),
        "hessian_mode": OptionSpec(str, "auto", frozenset({"auto", "fd_gradients", "analytic"})),
        # R30, ADR-0041: Cartesian basis functions for every angular momentum (mol.cart). Keyed
        # only when True: __init__ drops a False value, so earlier resolved stages are unchanged.
        "cartesian_basis": OptionSpec(bool, False),
    }

    def __init__(
        self,
        stage: StageConfig,
        *,
        device: str = "auto",
        max_memory_mb: int | None = None,
        ladder_max_cycle: int = 100,
        **runtime: Any,
    ) -> None:
        """Resolve the stage and check method, basis, options and runtime arguments.

        Raises:
            EngineInputError: an unknown xc, a non-positive tolerance/step/grid level, an
                ``alpb`` solvation, or a bad runtime argument.
            EngineUnavailableError: ``device="cuda"`` without the ``gpu`` extra or a CUDA device.
        """
        super().__init__(stage, **runtime)
        if self._stage.options["ladder_small_basis"] == AUTO and self._stage.basis:
            # Rule 5 (R37) depends on the basis only, so it is resolved into the keyed stage.
            data = self._stage.model_dump()
            data["options"]["ladder_small_basis"] = default_small_basis(self._stage.basis)
            self._stage = StageConfig.model_validate(data)
        if self._stage.options.get("cartesian_basis") is False:
            # R30, ADR-0041: absent means spherical. A False value (default or explicit) is not
            # keyed, so every pre-v0.5.0 resolved stage and cache key stays byte-identical.
            data = self._stage.model_dump()
            del data["options"]["cartesian_basis"]
            self._stage = StageConfig.model_validate(data)
        if self.cartesian_basis and self._stage.options["init_guess"] == "atom":
            # GPU4PySCF 1.9.2's atom guess asserts on a Cartesian basis; refused on both devices
            # so one resolved stage never behaves differently by device (ADR-0018).
            raise EngineInputError(
                "pyscf_gpu_cpu: cartesian_basis=True is not supported with init_guess='atom'"
            )
        if device not in ("auto", "cpu", "cuda"):
            raise EngineInputError(f"pyscf_gpu_cpu: device {device!r} not in auto|cpu|cuda")
        self.requested_device = device
        self._gpu = gpu_modules() if device in ("auto", "cuda") else None
        if device == "cuda" and self._gpu is None:
            raise EngineUnavailableError(
                "pyscf_gpu_cpu: device 'cuda' needs GPU4PySCF, CuPy and a CUDA device; install "
                "the gpu extra with `uv sync --extra gpu`"
            )
        self.vram_budget_bytes: int | None = None
        if self._gpu is not None:
            # ADR-0008 budget, read once at construction (never probe_hardware per evaluate).
            total = int(self._gpu.cupy.cuda.runtime.memGetInfo()[1])
            self.vram_budget_bytes = vram_budget_bytes(total)
        self._on_gpu = False
        for name, limit in (
            ("max_memory_mb", max_memory_mb),
            ("ladder_max_cycle", ladder_max_cycle),
        ):
            if limit is not None and (
                isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
            ):
                raise EngineInputError(f"pyscf_gpu_cpu: {name} must be an int >= 1, not {limit!r}")
        self.max_memory_mb = max_memory_mb
        self.ladder_max_cycle = ladder_max_cycle
        options = self.stage.options
        for key in ("conv_tol", "fd_step_bohr", "stability_tol", "stability_noise_eh"):
            value = options[key]
            if not isinstance(value, float) or not value > 0:
                raise EngineInputError(f"pyscf_gpu_cpu: option {key!r} must be > 0, not {value!r}")
        level = options["grids_level"]
        if not isinstance(level, int) or not 0 <= level <= 9:
            raise EngineInputError(
                f"pyscf_gpu_cpu: option 'grids_level' must be 0..9, not {level!r}"
            )
        if self.stage.solvation.model == "alpb":
            raise EngineInputError("pyscf_gpu_cpu: solvation 'alpb' is xtb's, not PySCF's")
        if self.stage.method != "hf":
            pyscf = _pyscf()
            try:
                pyscf.dft.libxc.parse_xc(self.stage.method)
            except KeyError as exc:
                raise EngineInputError(
                    f"pyscf_gpu_cpu: unknown xc functional {self.stage.method!r}"
                ) from exc
        self._dielectric = self._resolve_dielectric()
        hessian_method_for(self.stage)  # refuses an unreliable explicit "analytic" up front

    @property
    def cartesian_basis(self) -> bool:
        """Whether every Mole uses Cartesian basis functions (``cartesian_basis``, R30)."""
        return self._stage.options.get("cartesian_basis") is True

    @classmethod
    def normalise_stage(cls, stage: StageConfig) -> StageConfig:
        """Lowercase the solvent and the method."""
        stage = normalise_solvent(stage)
        if stage.method == stage.method.lower():
            return stage
        data = stage.model_dump()
        data["method"] = stage.method.lower()
        return StageConfig.model_validate(data)

    @property
    def identity(self) -> EngineIdentity:
        """``pyscf_gpu_cpu`` at the installed PySCF version; no model weights."""
        return EngineIdentity(name="pyscf_gpu_cpu", version=library_version("pyscf"), model=None)

    # ------------------------------------------------------------------ resolution

    def _resolve_dielectric(self) -> float | None:
        """ε for ddCOSMO/PCM: the explicit dielectric wins, else the solvent-name table."""
        solvation = self.stage.solvation
        if solvation.model == "none":
            return None
        if solvation.dielectric is not None:
            return float(solvation.dielectric)
        name = solvation.solvent or ""
        if name not in DIELECTRICS:
            raise EngineInputError(
                f"pyscf_gpu_cpu: unknown solvent {solvation.solvent!r}; give a dielectric or one "
                f"of {sorted(DIELECTRICS)}"
            )
        return DIELECTRICS[name]

    def resolved_stage_for(self, state: MolecularState) -> StageConfig:
        """``engine.stage`` with the concrete ``ecp`` for ``state`` (R36); never written back.

        Raises:
            EngineInputError: a non-def2 basis with Z > 36 and no explicit ``ecp``; an explicit
                ``none`` with a def2 basis and Z > 36; or an ECP PySCF lacks for an element.
        """
        basis = self.stage.basis or ""
        heavy = sorted({s for s in state.symbols if ATOMIC_NUMBERS[s] > HEAVY_Z})
        given = self.stage.options["ecp"]
        assert isinstance(given, str)
        if given == AUTO:
            if not heavy:
                ecp = ECP_NONE
            elif is_def2(basis):
                ecp = basis
            else:
                raise EngineInputError(
                    f"pyscf_gpu_cpu: basis {basis!r} is not def2 and {heavy} have Z > {HEAVY_Z}; "
                    "set the 'ecp' option explicitly"
                )
        else:
            ecp = given
            if ecp.lower() == ECP_NONE and heavy and is_def2(basis):
                raise EngineInputError(
                    f"pyscf_gpu_cpu: def2 basis {basis!r} with {heavy} needs its ECP; "
                    "ecp 'none' would run them all-electron"
                )
        if ecp.lower() != ECP_NONE:
            self._check_ecp(ecp, heavy)
        data = self.stage.model_dump()
        data["options"]["ecp"] = ecp
        return StageConfig.model_validate(data)

    def _check_ecp(self, ecp: str, heavy: list[str]) -> None:
        pyscf = _pyscf()
        missing = []
        for symbol in heavy:
            try:
                found = pyscf.gto.basis.load_ecp(ecp, symbol)
            except (RuntimeError, KeyError) as exc:
                raise EngineInputError(f"pyscf_gpu_cpu: unknown ECP {ecp!r}") from exc
            if not found:
                missing.append(symbol)
        if missing:
            raise EngineInputError(f"pyscf_gpu_cpu: ECP {ecp!r} has no data for {missing}")

    # ------------------------------------------------------------------ build

    def _build_mol(
        self, state: MolecularState, basis: str, ecp: str, coords_bohr: Any = None
    ) -> Any:
        """A PySCF Mole for ``state`` (Angstrom, or Bohr when ``coords_bohr`` is given)."""
        pyscf = _pyscf()
        if coords_bohr is None:
            atom = [(s, tuple(c)) for s, c in zip(state.symbols, state.coordinates, strict=True)]
            unit = "Angstrom"
        else:
            atom = [(s, tuple(c)) for s, c in zip(state.symbols, coords_bohr, strict=True)]
            unit = "Bohr"
        kwargs: dict[str, Any] = {
            "atom": atom,
            "unit": unit,
            "basis": basis,
            "charge": state.charge,
            "spin": state.spin_multiplicity - 1,
            "verbose": 0,
        }
        if ecp.lower() != ECP_NONE:
            kwargs["ecp"] = ecp
        if self.cartesian_basis:
            kwargs["cart"] = True
        if self.max_memory_mb is not None:
            kwargs["max_memory"] = self.max_memory_mb
        try:
            return pyscf.gto.M(**kwargs)
        except pyscf.lib.exceptions.BasisNotFoundError as exc:
            raise EngineInputError(f"pyscf_gpu_cpu: basis {basis!r} not found: {exc}") from exc
        except RuntimeError as exc:
            # PySCF raises RuntimeError for an electron count inconsistent with the spin and
            # for unparsable ECP data.
            raise EngineInputError(
                f"pyscf_gpu_cpu: charge {state.charge}, multiplicity {state.spin_multiplicity}: "
                f"{str(exc).splitlines()[0]}"
            ) from exc

    def _make_mf(self, mol: Any, stage: StageConfig, max_cycle: int = RUNG_MAX_CYCLE) -> Any:
        """The mean-field object for ``mol``: R/U, HF/KS, DF, solvent, tolerances.

        On the GPU path the same settings build ``gpu4pyscf.scf`` / ``gpu4pyscf.dft`` objects.
        """
        if self._on_gpu:
            assert self._gpu is not None
            scf_mod, dft_mod = self._gpu.scf, self._gpu.dft
        else:
            pyscf = _pyscf()
            scf_mod, dft_mod = pyscf.scf, pyscf.dft
        options = stage.options
        open_shell = mol.spin != 0
        if stage.method == "hf":
            mf = scf_mod.UHF(mol) if open_shell else scf_mod.RHF(mol)
        else:
            mf = dft_mod.UKS(mol) if open_shell else dft_mod.RKS(mol)
            mf.xc = stage.method
            mf.grids.level = options["grids_level"]
        if options["density_fit"]:
            mf = mf.density_fit(auxbasis=options["auxbasis"])
        model = stage.solvation.model
        if model == "ddcosmo":
            mf = mf.ddCOSMO()
            mf.with_solvent.eps = self._dielectric
        elif model == "pcm":
            mf = mf.PCM()
            mf.with_solvent.method = options["pcm_method"]
            mf.with_solvent.eps = self._dielectric
        mf.conv_tol = options["conv_tol"]
        mf.init_guess = options["init_guess"]
        mf.max_cycle = max_cycle
        if self.max_memory_mb is not None:
            mf.max_memory = self.max_memory_mb
        return mf

    def _kernel(self, mf: Any, dm0: Any = None) -> bool:
        """Run ``mf.kernel`` (from ``dm0`` if given); return whether it converged."""
        pyscf = _pyscf()
        try:
            if dm0 is None:
                mf.kernel()
            else:
                mf.kernel(dm0=dm0)
        except self._passthrough():
            raise  # CuPy / CUDA errors go to the OOM rule in _evaluate
        except pyscf.lib.exceptions.BasisNotFoundError as exc:
            raise EngineInputError(f"pyscf_gpu_cpu: auxbasis not found: {exc}") from exc
        except (RuntimeError, ValueError, FloatingPointError, MemoryError) as exc:
            raise EngineRuntimeError(f"pyscf_gpu_cpu: SCF failed: {exc}", tail=repr(exc)) from exc
        return bool(mf.converged) and math.isfinite(float(mf.e_tot))

    # ------------------------------------------------------------------ ladder

    def _ladder(self, state: MolecularState, mol: Any, stage: StageConfig) -> tuple[Any, list[str]]:
        """Run the R9 ladder; return the converged mean field and the steps attempted."""
        pyscf = _pyscf()
        steps: list[str] = []

        steps.append("diis")
        mf = self._make_mf(mol, stage, self.ladder_max_cycle)
        if self._kernel(mf):
            return mf, steps

        steps.append("level_shift")
        dm = mf.make_rdm1()
        mf = self._make_mf(mol, stage)
        mf.level_shift = LEVEL_SHIFT
        mf.damp = DAMP
        if self._kernel(mf, dm):
            return self._without_shift(mf), steps

        steps.append("soscf")
        dm = mf.make_rdm1()
        mf = self._make_mf(mol, stage).newton()
        if self._kernel(mf, dm):
            return mf, steps

        steps.append("small_basis_projection")
        small_basis = stage.options["ladder_small_basis"]
        assert isinstance(small_basis, str)
        ecp = stage.options["ecp"]
        assert isinstance(ecp, str)
        small_mol = self._build_mol(state, small_basis, ecp)
        small = self._make_mf(small_mol, stage)
        if self._kernel(small):
            dm_small = to_host(small.make_rdm1())
            if mol.spin != 0:
                dm0 = [pyscf.scf.addons.project_dm_nr2nr(small_mol, d, mol) for d in dm_small]
            else:
                dm0 = pyscf.scf.addons.project_dm_nr2nr(small_mol, dm_small, mol)
            mf = self._make_mf(mol, stage)
            if self._kernel(mf, dm0):
                return mf, steps
        raise ScfConvergenceError(
            f"pyscf_gpu_cpu: SCF did not converge after {steps} (charge {state.charge}, "
            f"multiplicity {state.spin_multiplicity})",
            steps=tuple(steps),
        )

    def _without_shift(self, mf: Any) -> Any:
        """Re-converge without level shift/damping, so the final orbitals are unshifted."""
        dm = mf.make_rdm1()
        mf.level_shift = 0.0
        mf.damp = 0.0
        if not self._kernel(mf, dm):
            raise ScfConvergenceError(
                "pyscf_gpu_cpu: SCF lost convergence after removing the level shift",
                steps=("diis", "level_shift"),
            )
        return mf

    @staticmethod
    def _rotation_count(mf: Any) -> int:
        """Occupied-virtual orbital pairs of the internal stability problem (per spin, summed)."""
        occ = to_host(mf.mo_occ)
        spins = occ if getattr(occ, "ndim", 1) == 2 else [occ]
        total = 0
        for spin in spins:
            n_occ = int(sum(1 for o in spin if o > 0))
            total += n_occ * (len(spin) - n_occ)
        return total

    def _stability(self, mf: Any, steps: list[str], stage: StageConfig) -> Any:
        """Internal stability analysis with the noise-robust verdict (R9, R54).

        lambda_min is the lowest eigenvalue of the internal-stability Hessian (``stability.py``,
        PySCF's own operator and Davidson at tol 1e-6). The state is unstable iff
        ``lambda_min < -stability_tol``. A follow that lowers the energy by less than
        ``stability_noise_eh`` ends the analysis as stable and does not count against the
        budget; at most ``MAX_STABILITY_FOLLOWS`` progressive follows, then
        ``ScfConvergenceError``. Every verdict records lambda_min.
        """
        threshold = float(stage.options["stability_tol"])
        noise = float(stage.options["stability_noise_eh"])
        follows = 0
        small = self._on_gpu and self._rotation_count(mf) < GPU_STABILITY_MIN_ROTATIONS
        if small:
            # R43: GPU4PySCF 1.9.2's Davidson asserts nvar >= nroots (3). Checked BEFORE the
            # analysis: analyse a CPU copy of the converged mean field (same mol/xc/grids/DF) and,
            # if unstable, follow on the GPU from the CPU copy's orbitals.
            steps.append(GPU_STABILITY_CPU_COPY_STEP)
        while True:
            analyser = mf.to_cpu() if small else mf
            lam, mo = lowest_internal(analyser)
            if not lam < -threshold:
                steps.append(f"stability:stable lambda_min={lam:+.2e}")
                return mf
            if follows == MAX_STABILITY_FOLLOWS:
                raise ScfConvergenceError(
                    f"pyscf_gpu_cpu: wavefunction still internally unstable after "
                    f"{MAX_STABILITY_FOLLOWS} follows (lambda_min={lam:+.2e})",
                    steps=tuple(steps),
                )
            steps.append(f"stability:followed lambda_min={lam:+.2e}")
            before = float(mf.e_tot)
            dm = mf.make_rdm1(mo, mf.mo_occ)
            if not self._kernel(mf, dm):
                raise ScfConvergenceError(
                    "pyscf_gpu_cpu: SCF did not converge after following an instability",
                    steps=tuple(steps),
                )
            delta = float(mf.e_tot) - before
            if not delta < -noise:
                steps.append(f"stability:followed_no_progress dE={delta:.1e}")
                return mf
            follows += 1

    # ------------------------------------------------------------------ evaluate

    def _gradient(self, mf: Any) -> list[list[float]]:
        """The analytic nuclear gradient (Eh/Bohr), N x 3."""
        try:
            grad = to_host(mf.nuc_grad_method().kernel())
        except self._passthrough():
            raise
        except (RuntimeError, ValueError, NotImplementedError) as exc:
            raise EngineRuntimeError(
                f"pyscf_gpu_cpu: gradient failed: {exc}", tail=repr(exc)
            ) from exc
        return [[float(v) for v in row] for row in grad]

    def _analytic_hessian(self, mf: Any, n_atoms: int) -> tuple[list[list[float]], float]:
        try:
            hobj = mf.Hessian()
            if self._on_gpu and hasattr(hobj, "grid_response"):
                hobj.grid_response = GPU_KS_HESSIAN_GRID_RESPONSE
            raw = to_host(hobj.kernel())
        except self._passthrough():
            raise
        except (RuntimeError, ValueError, NotImplementedError, AttributeError) as exc:
            raise EngineRuntimeError(
                f"pyscf_gpu_cpu: Hessian failed: {exc}", tail=repr(exc)
            ) from exc
        dof = 3 * n_atoms
        # PySCF returns (N, N, 3, 3) indexed [a, b, i, j] = d2E / dx_{a,i} dx_{b,j}.
        flat = [
            [float(raw[a][b][i][j]) for b in range(n_atoms) for j in range(3)]
            for a in range(n_atoms)
            for i in range(3)
        ]
        asym = 0.0
        for p in range(dof):
            for q in range(p + 1, dof):
                asym = max(asym, abs(flat[p][q] - flat[q][p]))
                mean = (flat[p][q] + flat[q][p]) / 2.0
                flat[p][q] = mean
                flat[q][p] = mean
        return flat, asym

    def _fd_hessian(
        self, state: MolecularState, stage: StageConfig, mf: Any
    ) -> tuple[list[list[float]], float]:
        """FD of analytic gradients, each displaced SCF started from the reference density."""
        ecp = stage.options["ecp"]
        assert isinstance(ecp, str) and stage.basis
        basis = stage.basis
        dm_ref = mf.make_rdm1()

        def forces_at(coords_bohr: list[list[float]]) -> list[list[float]]:
            mol = self._build_mol(state, basis, ecp, coords_bohr)
            displaced = self._make_mf(mol, stage)
            if not self._kernel(displaced, dm_ref):
                raise ScfConvergenceError(
                    "pyscf_gpu_cpu: SCF did not converge at an FD Hessian displacement",
                    steps=("fd_hessian",),
                )
            return [[-v for v in row] for row in self._gradient(displaced)]

        coords = [[float(v) for v in row] for row in mf.mol.atom_coords(unit="Bohr")]
        step = stage.options["fd_step_bohr"]
        assert isinstance(step, float)
        return fd_hessian(forces_at, coords, step)

    def _passthrough(self) -> tuple[type[BaseException], ...]:
        """CuPy / CUDA exception types to re-raise untouched (empty off the GPU path)."""
        if self._on_gpu and self._gpu is not None:
            return gpu_error_types(self._gpu)
        return ()

    def estimate_vram_bytes(self, mol: Any, stage: StageConfig) -> int:
        """The calibrated VRAM estimate for ``mol`` under ``stage`` (Mini-req 3)."""
        naux = 0
        if stage.options["density_fit"]:
            from pyscf.df import addons as df_addons

            naux = int(df_addons.make_auxmol(mol, stage.options["auxbasis"]).nao)
        return estimate_bytes(int(mol.nao), naux)

    def _hessian_method(self, stage: StageConfig, state: MolecularState) -> str:
        """Slice 06's rule; on the GPU, a KS Hessian is analytic only for a recorded class (R44)."""
        method = hessian_method_for(stage)
        if (
            self._on_gpu
            and method == "finite_difference"
            and stage.options["hessian_mode"] == "auto"
            and stage.method != "hf"
            and stage.solvation.model != "ddcosmo"
            and gpu_ks_hessian_class(stage, state) in GPU_ANALYTIC_KS_HESSIAN_CLASSES
        ):
            return "analytic"
        return method

    def _run(
        self, state: MolecularState, stage: StageConfig, *, forces: bool, hessian: bool
    ) -> RawResult:
        """SCF ladder, stability and derivatives on the current device (``self._on_gpu``)."""
        ecp = stage.options["ecp"]
        assert isinstance(ecp, str) and stage.basis
        mol = self._build_mol(state, stage.basis, ecp)
        mf, steps = self._ladder(state, mol, stage)
        mf = self._stability(mf, steps, stage)
        device: Device = "cuda" if self._on_gpu else "cpu"
        result = RawResult(energy_hartree=float(mf.e_tot), device=device, recovery_steps=steps)
        if forces or hessian:
            result.forces_hartree_per_bohr = [[-v for v in row] for row in self._gradient(mf)]
        if hessian:
            method = self._hessian_method(stage, state)
            if method == "analytic":
                matrix, asym = self._analytic_hessian(mf, len(state.symbols))
            else:
                matrix, asym = self._fd_hessian(state, stage, mf)
            result.hessian_hartree_per_bohr2 = matrix
            result.hessian_method = "analytic" if method == "analytic" else "finite_difference"
            result.hessian_max_asymmetry = asym
        return result

    def _cpu(
        self,
        state: MolecularState,
        stage: StageConfig,
        *,
        forces: bool,
        hessian: bool,
        reason: str | None,
        step: str | None = None,
    ) -> RawResult:
        """The slice-06 CPU path, recording why it ran instead of the GPU."""
        self._on_gpu = False
        result = self._run(state, stage, forces=forces, hessian=hessian)
        result.device_reason = reason
        if step is not None:
            result.recovery_steps = [step, *result.recovery_steps]
        return result

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        stage = self.resolved_stage_for(state)
        if self._gpu is None:
            reason = "gpu_unavailable" if self.requested_device == "auto" else None
            return self._cpu(state, stage, reason=reason, forces=forces, hessian=hessian)
        if stage.solvation.model == "ddcosmo":
            return self._cpu(
                state, stage, reason="ddcosmo_cpu_only", forces=forces, hessian=hessian
            )
        ecp = stage.options["ecp"]
        assert isinstance(ecp, str) and stage.basis and self.vram_budget_bytes is not None
        estimate = self.estimate_vram_bytes(self._build_mol(state, stage.basis, ecp), stage)
        if estimate > self.vram_budget_bytes:
            return self._cpu(
                state,
                stage,
                reason="vram_estimate_over_budget",
                step="vram_estimate>budget->cpu",
                forces=forces,
                hessian=hessian,
            )
        self._on_gpu = True
        try:
            result = self._run(state, stage, forces=forces, hessian=hessian)
        except gpu_error_types(self._gpu) as exc:
            self._on_gpu = False
            if not is_gpu_oom(self._gpu, exc):
                raise EngineRuntimeError(
                    f"pyscf_gpu_cpu: GPU error (not an out-of-memory error): {exc}",
                    tail=repr(exc),
                ) from exc
            free_pools(self._gpu)
            return self._cpu(
                state, stage, reason="gpu_oom", step="gpu_oom->cpu", forces=forces, hessian=hessian
            )
        finally:
            self._on_gpu = False
        result.device_reason = f"gpu4pyscf {self._gpu.version}"
        return result


__all__ = [
    "HESSIAN_SUPPORT",
    "PySCFEngine",
    "ANALYTIC_REFUSED",
    "default_small_basis",
    "hessian_method_for",
    "is_def2",
]
