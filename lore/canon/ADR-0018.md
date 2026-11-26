Decision (resolve, v0.2.0, R2/R3/R9/R10/R30; Red Team F2, F3, F9, F10). The PySCF engine uses one resolved stage for both its CPU and GPU paths.

Keyed settings:
- density fitting with an auxiliary basis (default true, def2-universal-jkfit);
- a def2 ECP whenever a def2 basis meets Z > 36; a non-def2 basis there without an ECP is refused;
- init_guess (default minao);
- grids_level and conv_tol.

The device is recorded, not keyed. ddCOSMO always runs on CPU, because GPU4PySCF 1.9.2 has PCM and SMD but no ddCOSMO. An internal SCF stability analysis always follows convergence: at most 2 follows, otherwise ScfConvergenceError.

Measured by resolve on this host (B3LYP/def2-SVP):
- GPU−CPU agreement is ≤5e-11 Eh with DF (water and [PdCl3(C2H4)]−), 7e-12 non-DF, and 6e-12 C-PCM;
- DF minus non-DF is 1.0e-5 Eh, hence keyed;
- linear PdCl2 converges to guess-dependent SCF solutions 7.9 mEh apart, and the GPU and CPU minao each reached a different one. The higher state is unstable, and following it lands lower and still unstable. Hence mandatory stability analysis, and that molecule is excluded from tests.

The VRAM budget comes from ADR-0008, read once from CuPy. A calibrated estimate sends over-budget jobs to CPU DF. A listed set of CUDA allocation errors triggers one recorded CPU fallback after freeing the CuPy pools.
