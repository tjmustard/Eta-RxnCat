"""MACE engine (tag ``mace``): MACE-MP-0 "medium" (MIT) from a sha256-pinned local file.

float64 energies and forces on CPU or CUDA, and a central-difference Hessian of the engine's
forces. Only neutral closed-shell states (charge 0, multiplicity 1) are accepted (TJ v0.2.0 Q2
"A"); MACE-MP-0 has no charge or spin input.

Licence boundary (TJ 14:57Z / 14:59Z, mission R11): this module never imports ``ase``. It calls
MACE's own model and ``mace.data`` code directly (MACE itself may load ``ase`` in-process, which
is allowed). torch, mace and e3nn are imported lazily, inside methods only. Weights are never
downloaded here: ``model_path`` is required, and the file's sha256 must equal the pin before
torch loads it (``torch.load`` unpickles, so the pin is also the trust check).
"""

import importlib
import math
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, Final

from eta_rxncat.core import Device, EngineIdentity, MolecularState, StageConfig
from eta_rxncat.core.elements import ATOMIC_NUMBERS
from eta_rxncat.engines.base import Engine, RawResult
from eta_rxncat.engines.errors import EngineInputError, EngineRuntimeError, EngineUnavailableError
from eta_rxncat.engines.fd import fd_hessian
from eta_rxncat.engines.identity import library_version, sha256_file
from eta_rxncat.engines.options import OptionSpec
from eta_rxncat.engines.units import (
    angstrom_to_bohr,
    bohr_to_angstrom,
    ev_per_angstrom_to_hartree_per_bohr,
    ev_to_hartree,
)

MODEL_NAME: Final = "mace-mp-0-medium"
"""The only accepted ``StageConfig.method``."""

EXPECTED_SHA256: Final = {
    "mace-mp-0-medium": "01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845",
}
"""Pinned content hash of each accepted weights file (mission R5, ADR-0017)."""

PROVISION_HINT: Final = (
    "download https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/"
    "2023-12-03-mace-128-L1_epoch-199.model (44,422,970 B, sha256 01bfe221...35845) to "
    "~/.cache/eta-rxncat/mace/ and pass model_path=..."
)
"""How to provision the weights (named in ``EngineUnavailableError``)."""


@contextmanager
def _default_dtype(torch: Any, dtype: Any) -> Iterator[None]:
    """Temporarily set torch's default dtype, so MACE builds its input tensors in float64."""
    old = torch.get_default_dtype()
    torch.set_default_dtype(dtype)
    try:
        yield
    finally:
        torch.set_default_dtype(old)


class MACEEngine(Engine):
    """MACE-MP-0 medium single points (float64) with an FD Hessian.

    ``stage.method`` is ``mace-mp-0-medium``. Keyed: ``dtype`` (``float64`` only),
    ``fd_step_bohr`` (0.005), ``engine_impl``. Runtime (never keyed): ``model_path`` (required),
    ``device`` (``auto``: cuda if available, else cpu; ``cpu``; ``cuda``).
    """

    tag = "mace"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {
        "dtype": OptionSpec(str, "float64", frozenset({"float64"})),
        "fd_step_bohr": OptionSpec(float, 0.005),
    }

    def __init__(
        self,
        stage: StageConfig,
        *,
        model_path: str | Path | None = None,
        device: str = "auto",
        **runtime: Any,
    ) -> None:
        """Check the stage, verify the weights' sha256, and only then load the model.

        Raises:
            EngineInputError: a method other than ``mace-mp-0-medium``, a solvation model, a bad
                option or device, or a weights file whose sha256 is not the pin.
            EngineUnavailableError: no ``model_path`` (or not a file), the ``mlip-mace`` extra
                missing, or ``device="cuda"`` without CUDA.
        """
        super().__init__(stage, **runtime)
        if self.stage.method != MODEL_NAME:
            raise EngineInputError(f"mace: method {stage.method!r} is not {MODEL_NAME!r}")
        if self.stage.solvation.model != "none":
            raise EngineInputError("mace: MACE-MP-0 has no implicit solvation")
        step = self.stage.options["fd_step_bohr"]
        if not isinstance(step, float) or not step > 0 or not math.isfinite(step):
            raise EngineInputError(f"mace: option 'fd_step_bohr' must be > 0, not {step!r}")
        if device not in ("auto", "cpu", "cuda"):
            raise EngineInputError(f"mace: device {device!r} not in auto|cpu|cuda")
        if model_path is None:
            raise EngineUnavailableError(f"mace: model_path is required; {PROVISION_HINT}")
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise EngineUnavailableError(f"mace: model file {path} not found; {PROVISION_HINT}")
        digest = sha256_file(path)
        if digest != EXPECTED_SHA256[MODEL_NAME]:
            raise EngineInputError(
                f"mace: {path} has sha256 {digest}, not the pinned "
                f"{EXPECTED_SHA256[MODEL_NAME]} for {MODEL_NAME}; refusing to load it"
            )
        self.model_path = path
        self._digest = digest
        self._step_bohr = step
        self.model, self.device = self._load_model(path, device)

    def _load_model(self, path: Path, device: str) -> tuple[Any, str]:
        """Load the (already sha-verified) model with torch, in float64, on the device."""
        try:
            torch = importlib.import_module("torch")
            importlib.import_module("mace")
        except ImportError as exc:
            raise EngineUnavailableError(
                "mace: the mlip-mace extra is not installed (uv sync --extra gpu --extra mlip-mace)"
            ) from exc
        cuda = bool(torch.cuda.is_available())
        if device == "cuda" and not cuda:
            raise EngineUnavailableError("mace: device 'cuda' requested but CUDA is not available")
        chosen = "cuda" if device == "cuda" or (device == "auto" and cuda) else "cpu"
        try:
            model = torch.load(path, map_location=chosen, weights_only=False)
        except (OSError, RuntimeError, ValueError) as exc:
            raise EngineRuntimeError(f"mace: cannot load {path}: {exc}") from exc
        return model.double().to(chosen).eval(), chosen

    @property
    def identity(self) -> EngineIdentity:
        """``mace`` at the installed mace-torch version, model ``mace-mp-0-medium@sha256:<hex>``."""
        return EngineIdentity(
            name="mace",
            version=library_version("mace-torch"),
            model=f"{MODEL_NAME}@sha256:{self._digest}",
        )

    def _refuse(self, state: MolecularState) -> None:
        if state.charge != 0 or state.spin_multiplicity != 1:
            raise EngineInputError(
                f"mace: charge {state.charge}, multiplicity {state.spin_multiplicity}: "
                "MACE-MP-0 represents only neutral closed-shell states (charge 0, multiplicity 1)"
            )

    def _energy_forces(
        self, symbols: list[str], positions_ang: list[list[float]]
    ) -> tuple[float, list[list[float]]]:
        """(energy eV, forces eV/A) from MACE's model at ``positions_ang``."""
        torch = importlib.import_module("torch")
        np = importlib.import_module("numpy")
        mdata = importlib.import_module("mace.data")
        mtools = importlib.import_module("mace.tools")
        tg = importlib.import_module("mace.tools.torch_geometric")
        key_spec = importlib.import_module("mace.data.utils").KeySpecification()
        names = list(key_spec.arrays_keys) + list(key_spec.info_keys)
        table_z = [int(z) for z in self.model.atomic_numbers]
        missing = sorted({s for s in symbols if ATOMIC_NUMBERS[s] not in table_z})
        if missing:
            raise EngineInputError(f"mace: MACE-MP-0 has no parameters for {missing}")
        config = mdata.Configuration(
            atomic_numbers=np.array([ATOMIC_NUMBERS[s] for s in symbols]),
            positions=np.array(positions_ang, dtype=np.float64),
            properties={name: None for name in names},
            property_weights={name: 0.0 for name in names},
            pbc=(False, False, False),
            cell=np.zeros((3, 3)),
        )
        table = mtools.AtomicNumberTable(table_z)
        with _default_dtype(torch, torch.float64):
            data = mdata.AtomicData.from_config(
                config, z_table=table, cutoff=float(self.model.r_max)
            )
        loader = tg.dataloader.DataLoader(
            dataset=[data], batch_size=1, shuffle=False, drop_last=False
        )
        batch = next(iter(loader)).to(self.device)
        try:
            out = self.model(batch.to_dict(), training=False, compute_force=True)
        except (RuntimeError, ValueError) as exc:
            raise EngineRuntimeError(
                f"mace: model evaluation failed: {exc}", tail=repr(exc)
            ) from exc
        energy = float(out["energy"].detach().cpu().item())
        forces = out["forces"].detach().cpu().numpy().tolist()
        return energy, [[float(v) for v in row] for row in forces]

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self._refuse(state)
        energy_ev, forces_ev = self._energy_forces(list(state.symbols), state.coordinates)
        device: Device = "cuda" if self.device == "cuda" else "cpu"
        result = RawResult(energy_hartree=ev_to_hartree(energy_ev), device=device)
        if forces or hessian:
            result.forces_hartree_per_bohr = [
                [ev_per_angstrom_to_hartree_per_bohr(v) for v in row] for row in forces_ev
            ]
        if hessian:

            def forces_at(coords_bohr: list[list[float]]) -> list[list[float]]:
                positions = [[bohr_to_angstrom(v) for v in row] for row in coords_bohr]
                _, f_ev = self._energy_forces(list(state.symbols), positions)
                return [[ev_per_angstrom_to_hartree_per_bohr(v) for v in row] for row in f_ev]

            coords = [[angstrom_to_bohr(v) for v in row] for row in state.coordinates]
            matrix, asym = fd_hessian(forces_at, coords, self._step_bohr)
            result.hessian_hartree_per_bohr2 = matrix
            result.hessian_method = "finite_difference"
            result.hessian_max_asymmetry = asym
        return result
