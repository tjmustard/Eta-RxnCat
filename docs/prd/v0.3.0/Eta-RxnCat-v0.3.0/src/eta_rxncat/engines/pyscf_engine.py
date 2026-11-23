"""PySCF / GPU4PySCF engine with RTX 5060 8 GB VRAM guardrails, ddCOSMO/PCM solvation, and SCF escalation ladder."""

from __future__ import annotations

import numpy as np

from eta_rxncat.core.models import MolecularState, PotentialResult, SolvationSpec
from eta_rxncat.engines.base import BasePotentialEngine
from eta_rxncat.utils.hw_probe import probe_hardware


class PySCFEngine(BasePotentialEngine):
    """DFT calculator supporting GPU4PySCF acceleration, automatic CPU fallback, and SCF basis projection."""

    def __init__(
        self,
        functional: str = "wB97X-D3BJ",
        basis: str = "def2-SVP",
        solvation: SolvationSpec | None = None,
        prefer_gpu: bool = True,
        vram_budget_gb: float = 6.5,
        density_fit: bool = True,
    ) -> None:
        self.name = f"pyscf_{functional}_{basis}"
        self.functional = functional
        self.basis = basis
        self.solvation = solvation or SolvationSpec()
        self.prefer_gpu = prefer_gpu
        self.vram_budget_gb = vram_budget_gb
        self.density_fit = density_fit

    def estimate_vram_gb(self, n_basis_functions: int) -> float:
        """Conservative empirical VRAM estimate (GB) for GPU4PySCF DF-DFT gradients/Hessians."""
        # Scales roughly O(N_bf^2) for density-fitted grids/integrals + workspace overhead
        return 0.8 + 4.5e-6 * (n_basis_functions**2)

    def _build_mol(self, state: MolecularState, basis: str) -> object:
        from pyscf import gto

        atom_str = "; ".join(
            f"{sym} {x:.10f} {y:.10f} {z:.10f}"
            for sym, (x, y, z) in zip(state.symbols, state.coordinates, strict=True)
        )
        mol = gto.M(
            atom=atom_str,
            basis=basis,
            charge=state.charge,
            spin=state.spin_multiplicity - 1,
            unit="Angstrom",
            verbose=0,
        )
        return mol

    def _attach_solvation(self, mf: object) -> object:
        if self.solvation.model == "none":
            return mf
        if self.solvation.model == "ddcosmo":
            mf = mf.ddCOSMO()  # type: ignore[attr-defined]
            if self.solvation.dielectric is not None:
                mf.with_solvent.eps = self.solvation.dielectric  # type: ignore[attr-defined]
            return mf
        if self.solvation.model == "pcm":
            mf = mf.PCM()  # type: ignore[attr-defined]
            mf.with_solvent.method = "IEF-PCM"  # type: ignore[attr-defined]
            if self.solvation.dielectric is not None:
                mf.with_solvent.eps = self.solvation.dielectric  # type: ignore[attr-defined]
            return mf
        raise ValueError(f"Unsupported PySCF solvation model: {self.solvation.model}")

    def _make_ks(self, mol: object, use_gpu: bool) -> object:
        from pyscf import dft

        mf = dft.KS(mol)  # type: ignore[arg-type]
        mf.xc = self.functional
        mf.conv_tol = 1e-8
        mf.max_cycle = 150
        if self.density_fit:
            mf = mf.density_fit()
        mf = self._attach_solvation(mf)
        if use_gpu:
            mf = mf.to_gpu()  # type: ignore[attr-defined]
        return mf

    def _run_scf_with_escalation(
        self,
        state: MolecularState,
        mol: object,
        use_gpu: bool,
    ) -> tuple[object, list[str]]:
        """Run SCF with automatic escalation: DIIS -> level-shift/SOSCF -> small-basis DM projection."""
        recovery: list[str] = []
        mf = self._make_ks(mol, use_gpu=use_gpu)
        mf.kernel()  # type: ignore[attr-defined]
        if mf.converged:  # type: ignore[attr-defined]
            return mf, recovery

        # Step 1: Level-shift + damping
        recovery.append("scf_level_shift_damping")
        mf.level_shift = 0.4  # type: ignore[attr-defined]
        mf.damp = 0.5  # type: ignore[attr-defined]
        mf.kernel()  # type: ignore[attr-defined]
        if mf.converged:  # type: ignore[attr-defined]
            return mf, recovery

        # Step 2: Second-order SCF (Newton / SOSCF)
        recovery.append("scf_newton_soscf")
        mf.level_shift = 0.0  # type: ignore[attr-defined]
        mf = mf.newton()  # type: ignore[attr-defined]
        mf.kernel()  # type: ignore[attr-defined]
        if mf.converged:  # type: ignore[attr-defined]
            return mf, recovery

        # Step 3: Minimal/small-basis SCF + density-matrix projection into target basis
        recovery.append("scf_small_basis_dm_projection")
        from pyscf.scf import addons

        small_mol = self._build_mol(state, basis="def2-SVP" if self.basis != "def2-SVP" else "STO-3G")
        small_mf = self._make_ks(small_mol, use_gpu=False)
        small_mf.level_shift = 0.3  # type: ignore[attr-defined]
        small_mf.kernel()  # type: ignore[attr-defined]
        dm_init = addons.project_dm_nr2nr(small_mol, small_mf.make_rdm1(), mol)  # type: ignore[attr-defined]

        target_mf = self._make_ks(mol, use_gpu=False)
        target_mf = target_mf.newton()  # type: ignore[attr-defined]
        target_mf.kernel(dm0=dm_init)  # type: ignore[attr-defined]
        if not target_mf.converged:  # type: ignore[attr-defined]
            raise RuntimeError(f"PySCF SCF failed to converge after full escalation ladder for {state.name}")
        return target_mf, recovery

    def _evaluate_impl(
        self,
        state: MolecularState,
        *,
        compute_forces: bool,
        compute_hessian: bool,
    ) -> PotentialResult:
        mol = self._build_mol(state, self.basis)
        n_bf = int(mol.nao_nr())  # type: ignore[attr-defined]
        est_vram = self.estimate_vram_gb(n_bf)

        hw = probe_hardware()
        use_gpu = (
            self.prefer_gpu
            and hw.cuda_available
            and hw.gpu4pyscf_installed
            and est_vram <= self.vram_budget_gb
        )
        recovery: list[str] = []
        if self.prefer_gpu and not use_gpu:
            recovery.append(f"cpu_df_fallback(est_vram={est_vram:.2f}GB)")

        mf, scf_steps = self._run_scf_with_escalation(state, mol, use_gpu=use_gpu)
        recovery.extend(scf_steps)

        energy_ha = float(mf.e_tot)  # type: ignore[attr-defined]
        forces_list: list[list[float]] | None = None
        if compute_forces or compute_hessian:
            grad_obj = mf.nuc_grad_method()  # type: ignore[attr-defined]
            grad_ha_bohr = np.asarray(grad_obj.kernel(), dtype=np.float64)
            forces_list = (-grad_ha_bohr).tolist()

        hess_list: list[list[float]] | None = None
        if compute_hessian:
            hess_obj = mf.Hessian()  # type: ignore[attr-defined]
            raw_h = np.asarray(hess_obj.kernel(), dtype=np.float64)
            dof = 3 * len(state.symbols)
            hess_list = raw_h.transpose(0, 2, 1, 3).reshape(dof, dof).tolist()

        return PotentialResult(
            electronic_energy_hartree=energy_ha,
            forces_hartree_per_bohr=forces_list,
            hessian_hartree_per_bohr2=hess_list,
            backend_device="cuda" if use_gpu else "cpu",
            recovery_steps_used=recovery,
        )
