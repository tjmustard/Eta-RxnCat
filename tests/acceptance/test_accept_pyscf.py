"""Acceptance: pyscf_gpu_cpu, B3LYP/def2-SVP with DF, on CPU and on CUDA, all four cases.

CPU entries are checked against plain PySCF on the same input (<= 1e-8 Eh); CUDA entries against
the engine's CPU energy (<= 1e-6 Eh) and must really run on cuda. An IEF-PCM water GPU Hessian
checks that the record-driven routing (R44) chose what the GPU support record says.
"""

from pathlib import Path
from typing import Any

import pytest
from accept_helpers import CASES, evaluated

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import PySCFEngine
from eta_rxncat.engines.pyscf_gpu_cpu.gpu import (
    GPU_ANALYTIC_KS_HESSIAN_CLASSES,
    gpu_ks_hessian_class,
)

pytestmark = [pytest.mark.acceptance, pytest.mark.gpu]
CPU_ENERGY: dict[str, float] = {}
PLAIN_PARITY = {"water": 1e-8, "pd_anion": 1e-8, "hydroxide": 1e-8, "hydroxyl": 1e-6}
"""Plain-PySCF energy parity (Eh). Slice 06 sets 1e-8 for water and the Pd anion; the hydroxyl
doublet is reproducible only to ~3e-7 run to run, plain PySCF included, so it is held to 1e-6."""


def stage(**kwargs: Any) -> StageConfig:
    """B3LYP/def2-SVP (DF default) single point."""
    return StageConfig(
        kind="single_point", engine="pyscf_gpu_cpu", method="b3lyp", basis="def2-svp", **kwargs
    )


def plain_pyscf(state: MolecularState) -> float:
    """Plain PySCF as the engine documents it (DF, grid 3, conv 1e-10); no stability follow."""
    from pyscf import dft, gto

    heavy = any(s in ("Pd",) for s in state.symbols)
    mol = gto.M(
        atom=[(s, tuple(c)) for s, c in zip(state.symbols, state.coordinates, strict=True)],
        unit="Angstrom",
        basis="def2-svp",
        ecp="def2-svp" if heavy else None,
        charge=state.charge,
        spin=state.spin_multiplicity - 1,
        verbose=0,
    )
    mf = (dft.UKS if mol.spin else dft.RKS)(mol)
    mf.xc = "b3lyp"
    mf.grids.level = 3
    mf = mf.density_fit(auxbasis="def2-universal-jkfit")
    mf.conv_tol = 1e-10
    mf.max_cycle = 100
    mf.kernel()
    assert mf.converged
    return float(mf.e_tot)


@pytest.mark.parametrize("case", CASES)
def test_pyscf_cpu(cases: dict[str, Any], out_dir: Path, case: str) -> None:
    """CPU: energy equals plain PySCF on the same input (PLAIN_PARITY), UKS iff open shell."""
    from pyscf import dft

    s = cases[case]
    eng = PySCFEngine.from_stage(stage(), device="cpu")
    rs = eng.resolved_stage_for(s)
    mol = eng._build_mol(s, "def2-svp", str(rs.options["ecp"]))
    assert (mol.charge, mol.spin) == (s.charge, s.spin_multiplicity - 1)
    assert isinstance(eng._make_mf(mol, rs), dft.uks.UKS if mol.spin else dft.rks.RKS)
    result = eng.evaluate(s)
    diff = abs(result.energy_hartree - plain_pyscf(s))
    CPU_ENERGY[case] = result.energy_hartree
    evaluated(
        out_dir, "pyscf_gpu_cpu", f"{case}.cpu", lambda: result, diff, reference="plain PySCF (CPU)"
    )
    assert result.device == "cpu" and result.recovery_steps[-1].startswith("stability:stable ")
    assert diff <= PLAIN_PARITY[case]


@pytest.mark.parametrize("case", CASES)
def test_pyscf_cuda(cases: dict[str, Any], out_dir: Path, case: str) -> None:
    """CUDA: really on cuda (no fallback) and within 1e-6 Eh of the engine's CPU energy."""
    s = cases[case]
    if case not in CPU_ENERGY:
        CPU_ENERGY[case] = (
            PySCFEngine.from_stage(stage(), device="cpu").evaluate(s, forces=False).energy_hartree
        )
    result = PySCFEngine.from_stage(stage(), device="cuda").evaluate(s)
    diff = abs(result.energy_hartree - CPU_ENERGY[case])
    evaluated(
        out_dir,
        "pyscf_gpu_cpu",
        f"{case}.cuda",
        lambda: result,
        diff,
        reference="engine CPU energy",
    )
    assert result.device == "cuda"
    assert not any(step.endswith("->cpu") for step in result.recovery_steps)
    assert result.recovery_steps[-1].startswith("stability:stable ")
    assert diff <= 1e-6


def test_pyscf_cuda_iefpcm_hessian_routing(cases: dict[str, Any], out_dir: Path) -> None:
    """R44: a water IEF-PCM GPU KS Hessian uses the method the GPU support record allows."""
    water = cases["water"]
    eng = PySCFEngine.from_stage(
        stage(solvation=Solvation(model="pcm", solvent="water"), options={"pcm_method": "IEF-PCM"}),
        device="cuda",
    )
    klass = gpu_ks_hessian_class(eng.resolved_stage_for(water), water)
    expected = "analytic" if klass in GPU_ANALYTIC_KS_HESSIAN_CLASSES else "finite_difference"
    result = eng.evaluate(water, hessian=True)
    evaluated(
        out_dir,
        "pyscf_gpu_cpu",
        "water_iefpcm_hessian.cuda",
        lambda: result,
        0.0,
        hessian_method=result.hessian_method,
        hessian_class=list(klass),
        expected_hessian_method=expected,
    )
    assert result.device == "cuda"
    assert result.hessian_method == expected
