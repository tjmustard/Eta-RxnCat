# TJ reference values: B3LYP/6-31G** and ωB97M-V/def2-TZVPD//B3LYP/6-31G**

Computed 2026-11-22 with PySCF 2.15.1 and geomeTRIC 1.1.1 (numpy 2.3.5, RDKit 2026.09.2 used only for the starting geometries).
The conditions are gas phase, ideal gas, 298.15 K and 1 atm (101325 Pa) unless stated otherwise. Energies are in kcal/mol, using 1 Eh = 627.509474 kcal/mol.
Every number is in `results.json`. These are reference values for the eta-rxncat v0.3.0 fixtures.

## Table 1: B3LYP/6-31G** (6-31G(d,p)), RRHO, no dispersion

| Quantity | ΔE | ΔE+ZPE | ΔH(298) | ΔG(298) |
|---|---|---|---|---|
| n-butane gauche − anti | 0.821 | 0.907 | 0.870 | 0.897 |
| butadiene s-cis/gauche − s-trans (side result) | 3.529 | 3.442 | 3.476 | 3.284 |
| Diels–Alder s-trans-butadiene + ethylene → cyclohexene, 1 atm | −42.655 | −36.349 | −38.311 | −24.627 |
| Diels–Alder ΔG_r, 1 M standard state | | | | **−26.522** |

Gauche n-butane population at 298.15 K, with both enantiomers counted: **30.6 %** from ΔG and 33.3 % from ΔE.

## Table 2: GATING REFERENCE, "ωB97M-V/def2-TZVPD//B3LYP/6-31G** with B3LYP/6-31G** RRHO thermal corrections"

ΔE comes from the ωB97M-V/def2-TZVPD single points at the B3LYP geometries. ZPE, H and G add the per-species B3LYP/6-31G** RRHO corrections (ZPE, H−E and G−E).

| Quantity | ΔE | ΔE+ZPE | ΔH(298) | ΔG(298) |
|---|---|---|---|---|
| n-butane gauche − anti | 0.609 | 0.695 | 0.658 | 0.685 |
| butadiene s-cis/gauche − s-trans | 2.750 | 2.662 | 2.696 | 2.504 |
| Diels–Alder, 1 atm | −47.055 | −40.750 | −42.712 | −29.028 |
| Diels–Alder ΔG_r, 1 M standard state | | | | **−30.922** |

Gauche n-butane population at 298.15 K, with both enantiomers counted: **38.6 %** from ΔG and 41.7 % from ΔE.

## Side result: B3LYP-D3(BJ)/6-31G**//B3LYP/6-31G**

These values add the D3(BJ) energy (B3LYP parameters, no ATM term, from pyscf-dispersion 1.7.0) to the B3LYP energies. The geometries were not re-optimised, and the thermal corrections are the B3LYP RRHO values.

| Quantity | ΔE | ΔH(298) | ΔG(298) 1 atm | ΔG(298) 1 M |
|---|---|---|---|---|
| n-butane gauche − anti | 0.533 | 0.582 | 0.609 (p_g 41.7 %) | — |
| butadiene gauche − s-trans | 3.311 | 3.258 | 3.066 | — |
| Diels–Alder | −48.067 | −43.724 | −30.040 | −31.934 |

## Formulas and standard state

- Gauche population: p_g = 2·exp(−ΔG/RT) / (1 + 2·exp(−ΔG/RT)), with RT = 0.592485 kcal/mol at 298.15 K. The ΔE form uses ΔE in place of ΔG.
- Converting to 1 M for the 2→1 reaction (Δn = −1): ΔG(1 M) = ΔG(1 atm) − RT·ln(V_m/1 L), with V_m = RT/P = 24.4654 L/mol.
  RT·ln(24.4654) = 0.592485 × 3.19725 = 1.8943 kcal/mol.
  - B3LYP: −24.6273 − 1.8943 = −26.5216 kcal/mol
  - Gating reference: −29.0279 − 1.8943 = −30.9222 kcal/mol
- ΔE_r and ΔH_r do not depend on the standard state for an ideal gas.

## Rotational symmetry numbers used

| Species | Point group | σ used | σ auto-detected by PySCF |
|---|---|---|---|
| butane anti | C2h | 2 | 2 (Ci at 1e-5 Bohr) |
| butane gauche | C2 | 2 | 1 (C1) |
| butadiene s-trans | C2h | 2 | 1 (Cs) |
| butadiene gauche | C2 | 2 | 1 (C1) |
| ethylene | D2h | 4 | 2 (C2h) |
| cyclohexene half-chair | C2 | 2 | 1 (C1) |

`pyscf.hessian.thermo.thermo` detects the point group with a 1e-5 Bohr tolerance. That tolerance misses the true group of these numerically optimised geometries. The script therefore enforces the assigned σ by applying S_rot ← S_rot − R·ln(σ_used/σ_auto) and making the matching change to G. The point group was confirmed at a looser tolerance: 1e-4 Bohr for anti butane, s-trans and gauche butadiene and ethylene, and 1e-3 Bohr for gauche butane and cyclohexene. The per-tolerance table is in `results.json`. If σ had not been corrected, the ethylene G would be off by RT·ln 2 = 0.41 kcal/mol and the cyclohexene G by the same amount in the opposite direction.

## Structures and frequencies

| Species | n_imag | lowest ν (cm⁻¹) | key dihedral |
|---|---|---|---|
| butane anti | 0 | 121.2 | C–C–C–C 180.0° |
| butane gauche | 0 | 116.4 | C–C–C–C 65.3° |
| butadiene s-trans | 0 | 177.0 | C=C–C=C 180.0° |
| butadiene gauche (s-cis side) | 0 | 156.6 | C=C–C=C 30.3° (twisted, not planar s-cis) |
| ethylene | 0 | 830.3 | — |
| cyclohexene | 0 | 166.4 | half-chair ring torsions −13.9 / 44.2 / −60.5 / 44.2 / −13.9 / −1.5° |

The maximum residual Cartesian gradient at each final geometry is at most 4.2e-6 Eh/Bohr. The frequencies are unscaled.

## Settings

- **B3LYP:** RKS with PySCF `xc='b3lyp'`. In PySCF 2.3 and later this is the VWN-RPA (VWN3) variant, the same as Gaussian's B3LYP. Basis `6-31g**` (6-31G(d,p)) with PySCF's default **spherical (5D) d functions**. Gaussian's default for 6-31G** is Cartesian 6D, so energies differ slightly (typically by a few hundredths of a kcal/mol in relative energies). `grids.level=5`, `conv_tol=1e-10`.
- **Optimisation:** geomeTRIC with the GAU_TIGHT convergence set, tightened to an energy criterion of 1e-8 Eh.
- **Frequencies:** analytic Hessian from `mf.Hessian()`, then `thermo.harmonic_analysis` and `thermo.thermo` (RRHO; the quasi-RRHO entropy side result is in the JSON).
- **ωB97M-V:** `xc='wb97m_v'` with `grids.level=5`, `nlcgrids.level=3` and `conv_tol=1e-10`. VV10 is on: `mf.do_nlc()` was asserted True, and the VV10 energy on the converged density was recorded for each species (for example, +0.0649 Eh for ethylene). def2-TZVPD is PySCF's built-in `def2-tzvpd.dat`; basis_set_exchange was not needed.
- **Resources:** 4 threads, `max_memory=3000` MB, one job at a time, and a check for at least 4000 MB available memory before each job.
- **Wall time:** about 70 min in total (4076 s for the sequential run plus an 82 s ethylene smoke test). The cyclohexene opt+freq step took 20 min and its single point 11 min.

## Sanity checks against known values (nothing was tuned)

- **Butane gauche−anti ΔH:** experiment gives about 0.6–0.7 kcal/mol. B3LYP gives 0.87, inside the typical 0.8–0.9 range. ωB97M-V//B3LYP gives 0.66, inside the experimental range.
- **Diels–Alder ΔH_r(298):** experiment gives about −40 kcal/mol (from ΔfH°: −1.0 − 26.0 − 12.5 ≈ −39.6). B3LYP/6-31G** gives −38.3, about 1.3–1.7 kcal/mol too weakly exothermic. That error is smaller than the usual "noticeable" B3LYP error, probably because the small basis set overbinds the product (BSSE cancellation). Larger basis sets typically give about −32 to −35. ωB97M-V//B3LYP gives −42.7 and B3LYP-D3(BJ) gives −43.7, both somewhat too exothermic, by about 2.7 and 3.7 kcal/mol.
- **Butadiene gauche−s-trans ΔH:** experiment and high-level theory give about 2.9 kcal/mol. B3LYP gives 3.48 (too high, as is typical for B3LYP) and ωB97M-V gives 2.70. The gauche dihedral of about 30° matches the B3LYP literature (about 30–38°).
- **Ethylene:** the frequencies match published B3LYP/6-31G** values, and S°(298) = 52.33 cal/(mol·K) against an experimental 52.4.

## Caveats

- These are pure RRHO results with no low-mode treatment. Butane and cyclohexene have torsions near 116–166 cm⁻¹, and RRHO under-counts their entropy. For example, cyclohexene S° = 72.5 against an experimental 74.3 cal/(mol·K). The Grimme quasi-RRHO entropy with ω₀ = 100 cm⁻¹ changes the reported Δ values by at most 0.01 kcal/mol. The torsions are not treated as hindered rotors.
- The main B3LYP table has no dispersion correction. Dispersion lowers the butane gap by about 0.29 kcal/mol and makes the Diels–Alder reaction more exothermic by about 5.4 kcal/mol (see the D3(BJ) side result).
- The gating reference combines ωB97M-V energies with B3LYP geometries and B3LYP thermal corrections. It is not a fully consistent ωB97M-V calculation.
- During every Hessian, PySCF printed "Krylov solver reached subspace convergence but true residual … exceeds tolerance. Falling back to per-root solve." The CPHF solve then completed by the per-root fallback. The frequencies are physically sensible (all positive, ethylene matches the literature), but this warning is recorded here.
- The basis uses 5D (spherical) d functions, not Gaussian's default 6D (see Settings).
- The butane population treats only anti and gauche± as harmonic wells. It assumes each well has its own partition function and ignores anharmonic torsional coupling.

## Files

- `calc.py` does the optimisation, frequencies, thermochemistry and single points. `run_all.sh` is the sequential driver with the memory check. `d3.py` computes the D3(BJ) energies, and `analyze.py` builds `results.json`.
- Each species has `<species>.xyz` (final B3LYP geometry, with the energy in the comment line), `<species>.freq.txt`, `<species>.opt.json` (full thermochemistry and geometry), `<species>.sp.json` (ωB97M-V), `<species>.d3.json`, and the PySCF/geomeTRIC logs (`*.log`, `*.stdout`, `*.stderr`).
- `run_all.log` has the job timings and peak memory: at most about 2.7 GB RSS, for the two butadiene single points.
