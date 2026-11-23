"""Clean-room PyTorch MLIP engines for MACE and Meta FAIRChem UMA (zero ASE dependency)."""

from __future__ import annotations

import numpy as np

from eta_rxncat.core.models import MolecularState, PotentialResult
from eta_rxncat.engines.base import BOHR_TO_ANGSTROM, BasePotentialEngine

EV_TO_HARTREE = 1.0 / 27.211386245988

_SYMBOL_TO_Z: dict[str, int] = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
    "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
    "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
    "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34,
    "Br": 35, "Kr": 36, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42,
    "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49, "Sn": 50,
    "Sb": 51, "Te": 52, "I": 53, "Xe": 54, "Cs": 55, "Ba": 56, "La": 57, "Hf": 72,
    "Ta": 73, "W": 74, "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80,
}


def atomic_numbers_from_symbols(symbols: list[str]) -> list[int]:
    return [_SYMBOL_TO_Z[s] for s in symbols]


class MACEEngine(BasePotentialEngine):
    """Direct PyTorch tensor bridge for MACE foundation models (MIT licensed)."""

    def __init__(self, model_name: str = "medium", device: str = "auto") -> None:
        self.name = f"mace_{model_name}"
        self.model_name = model_name
        self._device = device
        self._model = None

    def _resolve_device(self) -> str:
        if self._device != "auto":
            return self._device
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self) -> tuple[object, str]:
        import torch
        from mace.calculators import mace_mp

        dev = self._resolve_device()
        if self._model is None:
            calc = mace_mp(model=self.model_name, device=dev, default_dtype="float64")
            self._model = calc.models[0].to(dev)
        return self._model, dev

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        import torch
        from mace.data import AtomicData, Configuration
        from mace.tools import torch_geometric, utils

        model, dev = self._load_model()
        z_table = utils.AtomicNumberTable([int(z) for z in model.atomic_numbers.tolist()])  # type: ignore[attr-defined]
        cfg = Configuration(
            atomic_numbers=np.asarray(atomic_numbers_from_symbols(state.symbols), dtype=np.int64),
            positions=state.coords_array(),
        )
        data = AtomicData.from_config(cfg, z_table=z_table, cutoff=float(model.r_max.item()))  # type: ignore[attr-defined]
        batch = torch_geometric.batch.Batch.from_data_list([data]).to(dev)
        batch["positions"].requires_grad_(compute_forces or compute_hessian)

        out = model(batch.to_dict(), compute_force=compute_forces or compute_hessian)  # type: ignore[operator]
        energy_ha = float(out["energy"].detach().cpu().item()) * EV_TO_HARTREE

        forces_list: list[list[float]] | None = None
        if (compute_forces or compute_hessian) and out.get("forces") is not None:
            f_ev_ang = out["forces"].detach().cpu().numpy()
            forces_list = (f_ev_ang * (EV_TO_HARTREE * BOHR_TO_ANGSTROM)).tolist()

        hess_list: list[list[float]] | None = None
        if compute_hessian:
            hess_list = self.numerical_hessian(state).tolist()

        return PotentialResult(
            electronic_energy_hartree=energy_ha,
            forces_hartree_per_bohr=forces_list,
            hessian_hartree_per_bohr2=hess_list,
            backend_device=dev,
        )


class UMADirectEngine(BasePotentialEngine):
    """Clean-room PyTorch bridge for Meta FAIRChem UMA (omol task) bypassing ASE."""

    def __init__(
        self,
        model_name: str = "uma-s-1.2.1",
        task_name: str = "omol",
        device: str = "auto",
    ) -> None:
        self.name = f"uma_{model_name}"
        self.model_name = model_name
        self.task_name = task_name
        self._device = device
        self._predictor = None

    def _resolve_device(self) -> str:
        if self._device != "auto":
            return self._device
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"

    def _load_predictor(self) -> tuple[object, str]:
        from fairchem.core import pretrained_mlip

        dev = self._resolve_device()
        if self._predictor is None:
            self._predictor = pretrained_mlip.get_predict_unit(self.model_name, device=dev)
        return self._predictor, dev

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        import torch
        from fairchem.core.datasets.atomic_data import AtomicData, atomicdata_list_to_batch

        predictor, dev = self._load_predictor()
        n_atoms = len(state.symbols)
        pos = torch.tensor(state.coords_array(), dtype=torch.float32, device=dev)
        z = torch.tensor(atomic_numbers_from_symbols(state.symbols), dtype=torch.long, device=dev)

        adata = AtomicData(
            pos=pos,
            atomic_numbers=z,
            cell=torch.zeros((1, 3, 3), dtype=torch.float32, device=dev),
            pbc=torch.tensor([[False, False, False]], dtype=torch.bool, device=dev),
            natoms=torch.tensor([n_atoms], dtype=torch.long, device=dev),
            charge=torch.tensor([state.charge], dtype=torch.long, device=dev),
            spin=torch.tensor([state.spin_multiplicity], dtype=torch.long, device=dev),
            dataset=[self.task_name],
        )
        batch = atomicdata_list_to_batch([adata])
        preds = predictor.predict(batch)  # type: ignore[attr-defined]

        energy_ha = float(preds["energy"].detach().cpu().item()) * EV_TO_HARTREE
        forces_list: list[list[float]] | None = None
        if (compute_forces or compute_hessian) and "forces" in preds:
            f_ev_ang = preds["forces"].detach().cpu().numpy()
            forces_list = (f_ev_ang * (EV_TO_HARTREE * BOHR_TO_ANGSTROM)).tolist()

        hess_list: list[list[float]] | None = None
        if compute_hessian:
            hess_list = self.numerical_hessian(state).tolist()

        return PotentialResult(
            electronic_energy_hartree=energy_ha,
            forces_hartree_per_bohr=forces_list,
            hessian_hartree_per_bohr2=hess_list,
            backend_device=dev,
        )
