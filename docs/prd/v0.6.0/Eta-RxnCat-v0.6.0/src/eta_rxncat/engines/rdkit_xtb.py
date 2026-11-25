"""RDKit classical force fields (BSD-3) and subprocess-isolated GFN2-xTB/ALPB engine."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, rdDetermineBonds

from eta_rxncat.core.models import MolecularState, PotentialResult, SolvationSpec
from eta_rxncat.engines.base import BOHR_TO_ANGSTROM, HARTREE_TO_KCAL_MOL, BasePotentialEngine


class RDKitFFEngine(BasePotentialEngine):
    """UFF / MMFF94 force-field evaluator using RDKit (zero copyleft dependencies)."""

    def __init__(self, force_field: Literal["UFF", "MMFF94", "MMFF94s"] = "UFF") -> None:
        self.name = f"rdkit_{force_field.lower()}"
        self.force_field = force_field

    def _build_rdmol(self, state: MolecularState) -> Chem.Mol:
        xyz_lines = [str(len(state.symbols)), state.name]
        for sym, (x, y, z) in zip(state.symbols, state.coordinates, strict=True):
            xyz_lines.append(f"{sym} {x:.8f} {y:.8f} {z:.8f}")
        raw_mol = Chem.MolFromXYZBlock("\n".join(xyz_lines))
        if raw_mol is None:
            raise ValueError(f"RDKit failed to parse coordinates for {state.name}")
        mol = Chem.Mol(raw_mol)
        try:
            rdDetermineBonds.DetermineConnectivity(mol)
        except Exception:
            # Transition-state / stretched organometallic bonds may fail valence perception;
            # UFF distance terms still evaluate on raw atomic coordinates.
            pass
        return mol

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        mol = self._build_rdmol(state)
        if self.force_field == "UFF":
            ff = AllChem.UFFGetMoleculeForceField(mol, ignoreInterfragInteractions=False)
        else:
            props = AllChem.MMFFGetMoleculeProperties(mol, mmffVariant=self.force_field)
            ff = AllChem.MMFFGetMoleculeForceField(mol, props, ignoreInterfragInteractions=False)

        if ff is None:
            raise RuntimeError(f"RDKit {self.force_field} parameterization failed for {state.name}")

        energy_kcal = float(ff.CalcEnergy())
        energy_ha = energy_kcal / HARTREE_TO_KCAL_MOL

        forces_list: list[list[float]] | None = None
        if compute_forces or compute_hessian:
            grad_kcal_ang = np.asarray(ff.CalcGrad(), dtype=np.float64).reshape(len(state.symbols), 3)
            # Convert kcal/(mol*Angstrom) -> Hartree/Bohr and negate for forces
            conv = BOHR_TO_ANGSTROM / HARTREE_TO_KCAL_MOL
            forces_list = (-grad_kcal_ang * conv).tolist()

        hess_list: list[list[float]] | None = None
        if compute_hessian:
            hess_list = self.numerical_hessian(state).tolist()

        return PotentialResult(
            electronic_energy_hartree=energy_ha,
            forces_hartree_per_bohr=forces_list,
            hessian_hartree_per_bohr2=hess_list,
            backend_device="cpu",
        )


class XTBSubprocessEngine(BasePotentialEngine):
    """Process-isolated wrapper around external `xtb` CLI binary (LGPL license firewall)."""

    def __init__(
        self,
        method: Literal["GFN2-xTB", "GFN1-xTB", "GFN-FF"] = "GFN2-xTB",
        solvation: SolvationSpec | None = None,
        xtb_executable: str = "xtb",
    ) -> None:
        self.name = f"xtb_{method.lower()}"
        self.method = method
        self.solvation = solvation or SolvationSpec()
        self.xtb_executable = xtb_executable

    def _gfn_flag(self) -> list[str]:
        if self.method == "GFN2-xTB":
            return ["--gfn", "2"]
        if self.method == "GFN1-xTB":
            return ["--gfn", "1"]
        return ["--gfnff"]

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        if shutil.which(self.xtb_executable) is None:
            raise FileNotFoundError(
                f"External executable '{self.xtb_executable}' not found on PATH."
            )

        with tempfile.TemporaryDirectory(prefix="eta_xtb_") as tmpdir:
            work = Path(tmpdir)
            xyz_path = work / "input.xyz"
            lines = [str(len(state.symbols)), state.name]
            for sym, (x, y, z) in zip(state.symbols, state.coordinates, strict=True):
                lines.append(f"{sym} {x:.10f} {y:.10f} {z:.10f}")
            xyz_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            uhf = state.spin_multiplicity - 1
            cmd = [
                self.xtb_executable,
                "input.xyz",
                *self._gfn_flag(),
                "--chrg",
                str(state.charge),
                "--uhf",
                str(uhf),
                "--json",
            ]
            if compute_hessian:
                cmd.append("--hess")
            elif compute_forces:
                cmd.append("--grad")

            if self.solvation.model == "alpb" and self.solvation.solvent:
                cmd.extend(["--alpb", self.solvation.solvent])

            proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, check=False)
            json_out = work / "xtbout.json"
            if proc.returncode != 0 or not json_out.exists():
                raise RuntimeError(f"xtb subprocess failed (rc={proc.returncode}): {proc.stderr[-500:]}")

            data = json.loads(json_out.read_text(encoding="utf-8"))
            energy_ha = float(data["total energy"])

            forces_list: list[list[float]] | None = None
            grad_file = work / "gradient"
            if (compute_forces or compute_hessian) and grad_file.exists():
                n_atoms = len(state.symbols)
                grad_lines = grad_file.read_text(encoding="utf-8").splitlines()
                # Turbomole gradient format: header + n_atoms coords + n_atoms gradients
                raw_grads = [
                    [float(val.replace("D", "E")) for val in ln.split()]
                    for ln in grad_lines[2 + n_atoms : 2 + 2 * n_atoms]
                ]
                forces_list = (-np.asarray(raw_grads, dtype=np.float64)).tolist()

            hess_list: list[list[float]] | None = None
            hess_file = work / "hessian"
            if compute_hessian and hess_file.exists():
                dof = 3 * len(state.symbols)
                tokens = [
                    float(tok)
                    for ln in hess_file.read_text(encoding="utf-8").splitlines()[1:]
                    for tok in ln.split()
                ]
                hess_list = np.asarray(tokens[: dof * dof], dtype=np.float64).reshape(dof, dof).tolist()

            return PotentialResult(
                electronic_energy_hartree=energy_ha,
                forces_hartree_per_bohr=forces_list,
                hessian_hartree_per_bohr2=hess_list,
                backend_device="cpu-subprocess",
            )
