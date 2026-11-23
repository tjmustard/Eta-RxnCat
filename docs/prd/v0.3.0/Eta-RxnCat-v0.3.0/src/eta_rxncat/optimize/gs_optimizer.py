"""Ground-state geometry optimizer built on geomeTRIC (BSD-3) with soft-mode fallback."""

from __future__ import annotations

import numpy as np
from geometric.engine import Engine as GeometricEngine
from geometric.molecule import Molecule as GeometricMolecule
from geometric.optimize import run_optimizer

from eta_rxncat.core.models import MolecularState
from eta_rxncat.engines.base import BOHR_TO_ANGSTROM, PotentialEngine


class _EtaGeometricBridge(GeometricEngine):
    """Adapter connecting Eta-RxnCat PotentialEngine to geomeTRIC TRIC optimizer."""

    def __init__(self, state: MolecularState, engine: PotentialEngine) -> None:
        geom_mol = GeometricMolecule()
        geom_mol.elem = list(state.symbols)
        geom_mol.xyzs = [state.coords_array()]
        super().__init__(geom_mol)
        self._state = state
        self._engine = engine

    def calc_new(self, coords: np.ndarray, dirname: str) -> dict[str, np.ndarray | float]:
        # geomeTRIC passes coords in Bohr
        coords_ang = coords.reshape(-1, 3) * BOHR_TO_ANGSTROM
        cur = self._state.model_copy(update={"coordinates": coords_ang.tolist()})
        res = self._engine.evaluate(cur, compute_forces=True, compute_hessian=False)
        grad = -np.asarray(res.forces_hartree_per_bohr, dtype=np.float64).reshape(-1)
        return {"energy": res.electronic_energy_hartree, "gradient": grad}


def optimize_ground_state(
    state: MolecularState,
    engine: PotentialEngine,
    maxiter: int = 200,
    constraints_file: str | None = None,
) -> tuple[MolecularState, float]:
    """Minimize geometry in TRIC coordinates with automatic Cartesian fallback for floppy modes."""
    for coord_sys in ("tric", "cart"):
        try:
            bridge = _EtaGeometricBridge(state, engine)
            params: dict[str, object] = {
                "coordsys": coord_sys,
                "maxiter": maxiter,
                "converge": ["energy", "1e-6", "grms", "3e-4", "gmax", "4.5e-4"],
            }
            if constraints_file is not None:
                params["constraints"] = constraints_file
            traj = run_optimizer(customengine=bridge, input="eta_opt.xyz", **params)
            final_xyz = np.asarray(traj.xyzs[-1], dtype=np.float64)
            final_e = float(traj.qm_energies[-1])
            opt_state = state.model_copy(update={"coordinates": final_xyz.tolist()})
            return opt_state, final_e
        except Exception:
            if coord_sys == "cart":
                raise
    raise RuntimeError("Unreachable optimizer fallback state")
