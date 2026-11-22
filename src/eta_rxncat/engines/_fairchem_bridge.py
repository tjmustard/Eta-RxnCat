"""Shared clean-room bridge for the fairchem engines (``uma_direct``, ``esen_omol25``; R31, R40).

Call path reproduced from fairchem-core 2.26 (read from the installed source), offline:

1. ``fairchem.core.calculate.pretrained_mlip.get_predict_unit(name)`` calls
   ``resolve_checkpoint(name)``: the registry entry in ``calculate/pretrained_models.json`` gives
   ``repo_id``, ``subfolder``, ``filename``, ``revision`` and the reference files
   (``atom_refs`` for both models, ``form_elem_refs`` for UMA, read with ``OmegaConf.load``;
   ``form_elem_refs`` uses its ``refs`` key). Each file is ``hf_hub_download(...,
   cache_dir=fairchem's CACHE_DIR)``. Here every download is ``local_files_only=True``.
2. ``load_predict_unit(path, inference_settings, device=..., atom_refs=..., form_elem_refs=...)``
   builds the ``MLIPPredictUnit``. The reference energies change the returned energy, so their
   sha256 values are keyed options (``atom_refs_sha256``, ``form_elem_refs_sha256``).
3. ``inference_settings`` is keyed and is ``high-precision`` (full FP32): fairchem's ``default``
   is TF32 / UMA Nitro on CUDA and makes CPU and CUDA differ by up to 1.1e-4 eV and 6.9e-4 eV/A
   on water (measured), which an unkeyed device cannot allow.
4. Direct-force checkpoints are refused after load: their flag in 2.26 is
   ``predict_unit.model.module.backbone.regress_config.direct_forces``.
5. The input is ``fairchem.core.datasets.atomic_data.AtomicData`` built directly, as
   ``FAIRChemCalculator`` -> ``AtomicData.from_ase`` would for a molecule: positions in the
   predict unit's ``base_precision_dtype`` (float32), the complete cell (identity), no PBC, no
   external edges, tags and fixed zeros, ``charge = state.charge``, ``spin = state.multiplicity``
   (both always set: fairchem defaults a missing spin to the invalid 0) and ``dataset = task``.
   ``predict_unit.predict(data)`` returns energy (eV) and forces (eV/A).

``src/eta_rxncat`` never imports ``ase`` (fairchem's own modules may load it in-process; TJ
14:57Z / 14:59Z). torch and fairchem are imported inside functions only. No credential is read,
printed or recorded here: ``huggingface_hub`` resolves cached files by itself.
"""

import importlib
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

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

DERIVED_KEYS = ("atom_refs_sha256", "form_elem_refs_sha256")
"""Keyed options the engine derives from the reference files; a caller may not set them."""

NO_REFS = "none"
"""The derived sha value when the registry entry has no such reference file."""


def _registry(name: str) -> Mapping[str, Any]:
    """Fairchem's registry entry for ``name`` (repo_id, subfolder, filename, revision, refs)."""
    pretrained = importlib.import_module("fairchem.core.calculate.pretrained_mlip")
    entry = pretrained._MODEL_CKPTS.checkpoints[name]
    return {
        "repo_id": entry.repo_id,
        "subfolder": entry.subfolder,
        "filename": entry.filename,
        "revision": entry.revision,
        "atom_refs": entry.atom_refs,
        "form_elem_refs": entry.form_elem_refs,
        "cache_dir": pretrained.CACHE_DIR,
    }


def _cached(entry: Mapping[str, Any], subfolder: str, filename: str) -> Path:
    """A file already in fairchem's HF cache (never downloads)."""
    hub = importlib.import_module("huggingface_hub")
    errors = importlib.import_module("huggingface_hub.errors")
    try:
        return Path(
            hub.hf_hub_download(
                repo_id=entry["repo_id"],
                filename=filename,
                subfolder=subfolder,
                revision=entry["revision"],
                cache_dir=entry["cache_dir"],
                local_files_only=True,
            )
        )
    except (errors.LocalEntryNotFoundError, errors.EntryNotFoundError, FileNotFoundError) as exc:
        raise FileNotFoundError(f"{entry['repo_id']}/{subfolder}/{filename} is not cached") from exc


class FairchemEngine(Engine):
    """Base of the fairchem engines. Subclasses set ``tag``, ``METHOD`` and ``REGISTRY_NAME``.

    Keyed: ``task`` (``omol`` only), ``inference_settings`` (``high-precision`` only),
    ``fd_step_bohr`` (0.005), ``engine_impl``, plus the derived ``atom_refs_sha256`` and
    ``form_elem_refs_sha256``. Runtime (never keyed): ``checkpoint_path`` (route B; default: the
    fairchem HF cache, route A), ``device`` (``auto`` | ``cpu`` | ``cuda``), and the test hooks
    ``atom_refs_path`` / ``form_elem_refs_path`` (their content is keyed through the sha).
    """

    METHOD: ClassVar[str]
    REGISTRY_NAME: ClassVar[str]
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {
        "task": OptionSpec(str, "omol", frozenset({"omol"})),
        "inference_settings": OptionSpec(str, "high-precision", frozenset({"high-precision"})),
        "fd_step_bohr": OptionSpec(float, 0.005),
    }

    @classmethod
    def check_method(cls, method: str) -> None:
        """Refuse any method but this engine's approved one."""
        if method != cls.METHOD:
            raise EngineInputError(f"{cls.tag}: method {method!r} is not {cls.METHOD!r}")

    def __init__(
        self,
        stage: StageConfig,
        *,
        checkpoint_path: str | Path | None = None,
        device: str = "auto",
        atom_refs_path: str | Path | None = None,
        form_elem_refs_path: str | Path | None = None,
        **runtime: Any,
    ) -> None:
        """Resolve weights and references, hash them, and only then load the predict unit.

        Raises:
            EngineInputError: a method other than the approved one, solvation, a bad option or
                device, a caller-set derived option, or a direct-force checkpoint.
            EngineUnavailableError: no weights (route A cache or ``checkpoint_path``), the
                ``mlip-uma`` extra missing, or ``device="cuda"`` without CUDA.
        """
        for key in DERIVED_KEYS:
            if key in stage.options:
                raise EngineInputError(f"{self.tag}: option {key!r} is derived by the engine")
        super().__init__(stage, **runtime)
        self.check_method(self.stage.method)
        if self.stage.solvation.model != "none":
            raise EngineInputError(f"{self.tag}: no implicit solvation")
        step = self.stage.options["fd_step_bohr"]
        if not isinstance(step, float) or not step > 0 or not math.isfinite(step):
            raise EngineInputError(f"{self.tag}: option 'fd_step_bohr' must be > 0, not {step!r}")
        if device not in ("auto", "cpu", "cuda"):
            raise EngineInputError(f"{self.tag}: device {device!r} not in auto|cpu|cuda")
        self._step_bohr = step
        checkpoint, atom_refs, form_refs = self._resolve(
            checkpoint_path, atom_refs_path, form_elem_refs_path
        )
        self.checkpoint_path = checkpoint
        self._digest = sha256_file(checkpoint)
        data = self.stage.model_dump()
        data["options"]["atom_refs_sha256"] = sha256_file(atom_refs) if atom_refs else NO_REFS
        data["options"]["form_elem_refs_sha256"] = sha256_file(form_refs) if form_refs else NO_REFS
        self._stage = StageConfig.model_validate(data)
        self.predict_unit, self.device = self._load(checkpoint, atom_refs, form_refs, device)

    def _resolve(
        self,
        checkpoint_path: str | Path | None,
        atom_refs_path: str | Path | None,
        form_elem_refs_path: str | Path | None,
    ) -> tuple[Path, Path | None, Path | None]:
        unavailable = EngineUnavailableError(
            f"no {self.tag} weights: provision via HF login (TJ Q3 A) or pass "
            "checkpoint_path (Q3 B)"
        )
        try:
            entry = _registry(self.REGISTRY_NAME)
        except ImportError as exc:
            raise EngineUnavailableError(
                f"{self.tag}: the mlip-uma extra is not installed "
                "(uv sync --extra gpu --extra mlip-uma)"
            ) from exc
        try:
            if checkpoint_path is not None:
                checkpoint = Path(checkpoint_path).expanduser()
                if not checkpoint.is_file():
                    raise FileNotFoundError(str(checkpoint))
            else:
                checkpoint = _cached(entry, entry["subfolder"], entry["filename"])
            refs: list[Path | None] = []
            for key, override in (
                ("atom_refs", atom_refs_path),
                ("form_elem_refs", form_elem_refs_path),
            ):
                if override is not None:
                    refs.append(Path(override))
                elif entry[key] is not None:
                    refs.append(_cached(entry, entry[key]["subfolder"], entry[key]["filename"]))
                else:
                    refs.append(None)
        except FileNotFoundError as exc:
            raise unavailable from exc
        return checkpoint, refs[0], refs[1]

    def _load(
        self, checkpoint: Path, atom_refs: Path | None, form_refs: Path | None, device: str
    ) -> tuple[Any, str]:
        """Load the predict unit, then refuse direct forces or a missing task."""
        unit, chosen = self._load_unit(checkpoint, atom_refs, form_refs, device)
        self._check_unit(unit)
        return unit, chosen

    def _load_unit(
        self, checkpoint: Path, atom_refs: Path | None, form_refs: Path | None, device: str
    ) -> tuple[Any, str]:
        """``load_predict_unit`` exactly as ``get_predict_unit`` calls it."""
        try:
            torch = importlib.import_module("torch")
            omegaconf = importlib.import_module("omegaconf")
            mlip_unit = importlib.import_module("fairchem.core.units.mlip_unit")
        except ImportError as exc:
            raise EngineUnavailableError(
                f"{self.tag}: the mlip-uma extra is not installed "
                "(uv sync --extra gpu --extra mlip-uma)"
            ) from exc
        cuda = bool(torch.cuda.is_available())
        if device == "cuda" and not cuda:
            raise EngineUnavailableError(
                f"{self.tag}: device 'cuda' requested but CUDA is not available"
            )
        chosen = "cuda" if device == "cuda" or (device == "auto" and cuda) else "cpu"
        atom = omegaconf.OmegaConf.load(atom_refs) if atom_refs else None
        form = omegaconf.OmegaConf.load(form_refs)["refs"] if form_refs else None
        try:
            unit = mlip_unit.load_predict_unit(
                str(checkpoint),
                str(self.stage.options["inference_settings"]),
                None,
                chosen,
                atom,
                form,
            )
        except (RuntimeError, ValueError, KeyError, OSError) as exc:
            raise EngineRuntimeError(f"{self.tag}: cannot load {checkpoint.name}: {exc}") from exc
        return unit, chosen

    def _check_unit(self, unit: Any) -> None:
        """Refuse a direct-force model (forces not -dE/dx) or one without the keyed task."""
        if self.direct_forces(unit):
            raise EngineInputError(
                f"{self.stage.method}: direct-force checkpoint; forces are not -dE/dx"
            )
        task = self.stage.options["task"]
        if task not in getattr(unit, "dataset_to_tasks", {task: None}):
            raise EngineInputError(f"{self.tag}: checkpoint has no {task!r} task")

    @staticmethod
    def direct_forces(unit: Any) -> bool:
        """Whether the loaded model regresses forces directly (fairchem 2.26 config flag)."""
        backbone = unit.model.module.backbone
        config = getattr(backbone, "regress_config", None)
        return bool(getattr(config, "direct_forces", False))

    @property
    def identity(self) -> EngineIdentity:
        """``<tag>`` at the installed fairchem-core version; model ``<method>@sha256:<hex>``."""
        return EngineIdentity(
            name=self.tag,
            version=library_version("fairchem-core"),
            model=f"{self.METHOD}@sha256:{self._digest}",
        )

    def batch_fields(
        self, state: MolecularState, positions_ang: list[list[float]]
    ) -> dict[str, Any]:
        """The model input as plain values: Z, positions (A), charge, spin multiplicity, task."""
        return {
            "atomic_numbers": [ATOMIC_NUMBERS[s] for s in state.symbols],
            "positions": [[float(v) for v in row] for row in positions_ang],
            "charge": state.charge,
            "spin": state.spin_multiplicity,
            "dataset": str(self.stage.options["task"]),
        }

    def _atomic_data(self, fields: dict[str, Any]) -> Any:
        """The ``AtomicData`` for ``fields`` (no ase), as ``AtomicData.from_ase`` builds it."""
        torch = importlib.import_module("torch")
        atomic_data = importlib.import_module("fairchem.core.datasets.atomic_data")
        dtype = self.predict_unit.inference_settings.base_precision_dtype
        n = len(fields["atomic_numbers"])
        return atomic_data.AtomicData(
            pos=torch.tensor(fields["positions"], dtype=torch.float64).to(dtype),
            atomic_numbers=torch.tensor(fields["atomic_numbers"], dtype=torch.long),
            cell=torch.eye(3, dtype=dtype).view(1, 3, 3),
            pbc=torch.zeros((1, 3), dtype=torch.bool),
            natoms=torch.tensor([n], dtype=torch.long),
            edge_index=torch.empty((2, 0), dtype=torch.long),
            cell_offsets=torch.empty((0, 3), dtype=dtype),
            nedges=torch.tensor([0], dtype=torch.long),
            charge=torch.tensor([fields["charge"]], dtype=torch.long),
            spin=torch.tensor([fields["spin"]], dtype=torch.long),
            fixed=torch.zeros(n, dtype=torch.long),
            tags=torch.zeros(n, dtype=torch.long),
            sid=[""],
            dataset=fields["dataset"],
        )

    def batch(self, state: MolecularState, positions_ang: list[list[float]]) -> Any:
        """The fairchem input for ``state`` at ``positions_ang``."""
        return self._atomic_data(self.batch_fields(state, positions_ang))

    def _energy_forces(
        self, state: MolecularState, positions_ang: list[list[float]]
    ) -> tuple[float, list[list[float]]]:
        """(energy eV, forces eV/A) from the predict unit."""
        data = self.batch(state, positions_ang)
        try:
            pred = self.predict_unit.predict(data)
        except (RuntimeError, ValueError, KeyError, AssertionError) as exc:
            raise EngineRuntimeError(
                f"{self.tag}: prediction failed: {exc}", tail=repr(exc)
            ) from exc
        energy = float(pred["energy"].detach().cpu().reshape(-1)[0].item())
        forces = pred["forces"].detach().cpu().tolist()
        return energy, [[float(v) for v in row] for row in forces]

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        energy_ev, forces_ev = self._energy_forces(state, state.coordinates)
        dtype = str(self.predict_unit.inference_settings.base_precision_dtype).split(".")[-1]
        device: Device = "cuda" if self.device == "cuda" else "cpu"
        result = RawResult(
            energy_hartree=ev_to_hartree(energy_ev),
            device=device,
            recovery_steps=[f"fairchem_dtype:{dtype}"],
        )
        if forces or hessian:
            result.forces_hartree_per_bohr = [
                [ev_per_angstrom_to_hartree_per_bohr(v) for v in row] for row in forces_ev
            ]
        if hessian:

            def forces_at(coords_bohr: list[list[float]]) -> list[list[float]]:
                positions = [[bohr_to_angstrom(v) for v in row] for row in coords_bohr]
                _, f_ev = self._energy_forces(state, positions)
                return [[ev_per_angstrom_to_hartree_per_bohr(v) for v in row] for row in f_ev]

            coords = [[angstrom_to_bohr(v) for v in row] for row in state.coordinates]
            matrix, asym = fd_hessian(forces_at, coords, self._step_bohr)
            result.hessian_hartree_per_bohr2 = matrix
            result.hessian_method = "finite_difference"
            result.hessian_max_asymmetry = asym
        return result
