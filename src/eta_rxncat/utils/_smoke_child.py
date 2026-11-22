"""Child process of ``run_smoke``: does the GPU work and prints one JSON object of measurements.

Run as ``python -m eta_rxncat.utils._smoke_child``. The parent judges the measurements; this
module only measures. Every heavy import is local to :func:`main`.
"""

import json
import time

WATER_ANGSTROM = "O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692"


def main() -> None:
    """Run RHF/STO-3G on GPU and CPU and a float64 CUDA matmul; print the measurements."""
    import cupy
    import gpu4pyscf.scf
    import pyscf
    import torch

    mol = pyscf.gto.M(
        atom=WATER_ANGSTROM, unit="Angstrom", basis="sto-3g", charge=0, spin=0, verbose=0
    )
    scf_start = time.monotonic()
    mf_gpu = gpu4pyscf.scf.RHF(mol)
    mf_gpu.kernel()
    mf_cpu = pyscf.scf.RHF(mol)
    mf_cpu.kernel()
    scf_seconds = time.monotonic() - scf_start

    torch_start = time.monotonic()
    torch.backends.cuda.matmul.allow_tf32 = False
    generator = torch.Generator().manual_seed(0)
    a = torch.rand(512, 512, dtype=torch.float64, generator=generator)
    b = torch.rand(512, 512, dtype=torch.float64, generator=generator)
    c_gpu = a.cuda() @ b.cuda()
    device = c_gpu.device.type
    max_abs_diff = float((c_gpu.cpu() - a @ b).abs().max())
    torch_seconds = time.monotonic() - torch_start

    print(
        json.dumps(
            {
                "converged_gpu": bool(mf_gpu.converged),
                "converged_cpu": bool(mf_cpu.converged),
                "energy_gpu_eh": float(mf_gpu.e_tot),
                "energy_cpu_eh": float(mf_cpu.e_tot),
                "mo_on_device": isinstance(mf_gpu.mo_coeff, cupy.ndarray),
                "scf_seconds": scf_seconds,
                "device": device,
                "max_abs_diff": max_abs_diff,
                "torch_seconds": torch_seconds,
            }
        )
    )


if __name__ == "__main__":
    main()
