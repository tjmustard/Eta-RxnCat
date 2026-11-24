# v0.5.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.5.0.zip` (sha256
`ecfd9aa35b218b5def341fab83f477538f0b9719269fc30f1d9d53860072eda6`) ships a starter implementation,
unpacked here under `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/` (34 files, byte-identical to the zip, plus the
gate file `.ruff.toml`, which is not part of the starter and keeps the pre-commit lint off it). The
plan copy inside it, `Eta-RxnCat-v0.5.0/Eta-RxnCat_Living_Master_Plan.md`, has sha256
`ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438`, the same bytes as the v0.4.0 plan
copy (and the value `docs/prd/PLAN_DISCREPANCIES.md` already records for this zip). The starter is
reference only: the code in `src/` and `tests/` is written fresh from the mission's slice specs, and no
code is copied from it. This register records every difference between the starter and the rewrite, so
each one can be reviewed and fixed if needed.

TJ, Q2 (v0.3.0, standing): "B use it as reference only. Keep a list of the discrepancies so that if
needed, we can go through each of them and fix any issues that arise."

**Clean room (TJ A1 "Q1. A").** No code of `optimize/ts_optimizer.py` is copied or followed. P-RFO is
written only from Banerjee et al. 1985, Baker 1986, Bofill 1994 and the mission SPEC. Rows DV-02…DV-06
take their text from mission §5 "Starter discrepancies".

## Scope

The rows of mission `missions/release-0.5.0/SPEC.md` §5 "Starter discrepancies". Starter paths are
relative to `docs/prd/v0.5.0/Eta-RxnCat-v0.5.0/`. R-, G- and A-numbers cite the mission SPEC.

**Status.** `decided` means the v0.5.0 decision is fixed. The Slice column names the implementing slice
or slices, from the mission's execution checklist. The auditor of that slice lists the row in its PASS
handoff, and the scribe closes it at v0.5.0 docs time.

## Starter files (sha256, sorted by path)

```
be9a8b1192d13313be459dfc026e2119d60ade8e0d708080a999509792d8401b  Eta-RxnCat-v0.5.0/AGENTS.md
ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438  Eta-RxnCat-v0.5.0/Eta-RxnCat_Living_Master_Plan.md
0142d01d180d7682bb00d458f7320ca256152a2d3db06da53d6bbc37e718806a  Eta-RxnCat-v0.5.0/README.md
eb0cd6078f82684ace03e380f61bd306a73c923ff740d3d90ed5621f08c4a27a  Eta-RxnCat-v0.5.0/pyproject.toml
64d8f2587aeb1d88d87207cedd53cf7a71bd79f99353297db94a37f84fb9b5d6  Eta-RxnCat-v0.5.0/src/eta_rxncat/__init__.py
4c1f0353223fb5d1e5bc2bfe7c473a5d4ae7f7d95a5748311e290ade62eaf89c  Eta-RxnCat-v0.5.0/src/eta_rxncat/cli.py
463b53ab83c27dd23d0df67693a8968fba186d38a911e99007e69532e388bd08  Eta-RxnCat-v0.5.0/src/eta_rxncat/conformers/__init__.py
d3d5fb49e23d28a98d93a5b26c58f3b78186a339b0e3ee259e78b62e5263eb72  Eta-RxnCat-v0.5.0/src/eta_rxncat/conformers/ensemble.py
71af842c0cc19380273a916c4e068ce23b7c48c83a7b86ebd1d5daaa709c4d93  Eta-RxnCat-v0.5.0/src/eta_rxncat/core/__init__.py
13634dec4b731c9d85e1c6865b45d2310e1bff1c9ecdb29b24590f8d862f9fd0  Eta-RxnCat-v0.5.0/src/eta_rxncat/core/models.py
6b2b85a536e58156e7e1bf005ebe86f52595d34d5b35f8fa1e463227924a25ae  Eta-RxnCat-v0.5.0/src/eta_rxncat/core/reaction_graph.py
1a7faff35ed4f5a8487241ac2b18914b7d7be5807dd97e0988bd3a8c81beb1ed  Eta-RxnCat-v0.5.0/src/eta_rxncat/core/thermo.py
472fcbd4d8da15105307aa9aabc774c5d8b13afb8c8c6cd1daca98a02d1e5e54  Eta-RxnCat-v0.5.0/src/eta_rxncat/engines/__init__.py
23177208c1770212f3c4b74538cb230cf766ad2fa170f2ebab663cadf4e738df  Eta-RxnCat-v0.5.0/src/eta_rxncat/engines/base.py
7651aec1a626da6abb4568833d97ad0c6836c7b22cff1801863afbb8ec320156  Eta-RxnCat-v0.5.0/src/eta_rxncat/engines/mlip.py
2b214584bc6adfe6704a654b9045965bcf968f18985d28186b2d53d59076faa7  Eta-RxnCat-v0.5.0/src/eta_rxncat/engines/pyscf_engine.py
fbd24e11b4c1269abddb2db9a378a32409e8c34c03cb8486592d6c2859d73a96  Eta-RxnCat-v0.5.0/src/eta_rxncat/engines/rdkit_xtb.py
8f7611a72f269f757fb8345851dd3357d51f857034ad3df36a54007994097071  Eta-RxnCat-v0.5.0/src/eta_rxncat/mapping/__init__.py
9fd962372458dc60998b86fa5730a6dc1e53df4b837c3bcb1362267c99a101ec  Eta-RxnCat-v0.5.0/src/eta_rxncat/mapping/core_mapper.py
acae51005256dfe263067472a1388d44a63af9a10ba3f3173575bf1f95b67c86  Eta-RxnCat-v0.5.0/src/eta_rxncat/optimize/__init__.py
6320acfa603878c6698bd931dfe706ae577c599320d30da5cad1d01a422f42e5  Eta-RxnCat-v0.5.0/src/eta_rxncat/optimize/gs_optimizer.py
da3ac514ecafbd1829cab3e93f44f3ae3a2fc97934faf626bb1149694edc99f1  Eta-RxnCat-v0.5.0/src/eta_rxncat/optimize/ts_optimizer.py
00a569d23af4560266bf0366132139c0d441c58af6cd17e4b38be9f582713814  Eta-RxnCat-v0.5.0/src/eta_rxncat/orchestrator/__init__.py
54c757b6364550b5f5cf70d4609640067abed565b898170b229a0b595e2fdfb4  Eta-RxnCat-v0.5.0/src/eta_rxncat/store/__init__.py
893c7654b6842912c3bd6fc9e528def8ffc64623f606f03aad02f94b9d018486  Eta-RxnCat-v0.5.0/src/eta_rxncat/store/artifact_store.py
9d0cfcd002e95e69b35cb9dbbf828b18a05de0e963b7f6a22e3719d6a27ea14e  Eta-RxnCat-v0.5.0/src/eta_rxncat/utils/__init__.py
c7ff3b3fac91b73a9e5243d122ef21a3343e2ccb3687adc220b8453fae50fb0e  Eta-RxnCat-v0.5.0/src/eta_rxncat/utils/hw_probe.py
4905299ad38147ce2fc29527cd2812bf707f11187bb76bd01ac1e2830872a319  Eta-RxnCat-v0.5.0/tests/e2e/fixtures/example_reaction_graph.yaml
19daf6124b844070c4e6ad96a02dac7e17d5d89640b9b83a993708440aff02a7  Eta-RxnCat-v0.5.0/tests/unit/test_core_schemas.py
ad17d0bd4c47e724df63ad88cd62c9a5451723cef379d4411d8105d73a56ec78  Eta-RxnCat-v0.5.0/tests/unit/test_engines_v020.py
3a579cfbce91c86a4bb813ddd3a537b208d8fd77742a98e1f2c267256dcb8ca8  Eta-RxnCat-v0.5.0/tests/unit/test_hw_probe.py
1496c28244a0f8374bef60ab81328aa08c5c36190658f44a2e2c754c6fa29ef0  Eta-RxnCat-v0.5.0/tests/unit/test_v030_thermo_conformers.py
7091704036f57eb9705822095f4bbca8203d1c81c65bd6f764eb99bdd7c64107  Eta-RxnCat-v0.5.0/tests/unit/test_v040_core_mapper.py
0258f127b8059f74a49357f1270b260462d6f930ade98eb28494ed479c2f1ea8  Eta-RxnCat-v0.5.0/tests/unit/test_v050_ts_prfo.py
```

## Register

| ID | Source | Behaviour there | v0.5.0 decision | Slice | Status |
|---|---|---|---|---|---|
| DV-01 / PD-009 | starter plan vs zip, PR #10 | plan: "P-RFO … >=50-60%"; zip: "TRIC P-RFO … soft-mode Hessian-refresh / damped fallback recovery … >=60% … covalent-graph topology guard" | TJ A1 "Q1. A": own clean-room P-RFO in Cartesian coordinates, no TRIC; geomeTRIC `--transition` only as a black-box cross-check. TJ A2 "Q2.  A": exactly one mode below −20 cm⁻¹, that mode below −50 cm⁻¹, active-core KE fraction ≥ 0.60. The covalent-graph topology guard stays at v0.9.0. PD-009 set to `decided` in slice 01. | 01, 03, 04, 11 | decided |
| DV-02 | `src/eta_rxncat/optimize/ts_optimizer.py` imports | imports `MolecularState`/`VibrationalMode`/`PotentialEngine`/`compute_frequencies_from_hessian`/`_ATOMIC_MASSES_AMU` from modules eta does not have; uses `coords_array()`/`.coordinates` shapes eta does not expose | the TS contracts are new, additive types in `core/ts_models.py` on eta's own models; the optimizer uses eta's engine and state interfaces only. | 02, 03 | decided |
| DV-03 | same, `_prfo_step` | always maximises along the lowest eigenvector; filters eigenvalues by `\|λ\| > 1e-6` instead of projecting rigid motions; fixed 25-step Newton without a convergence check; `1e-8` added to a denominator | mission §5 "P-RFO": the maximised mode follows the forming bonds (R2); rigid translations and rotations are projected out with the centroid rigid basis (R7); λ_n is solved by bracketed bisection/Newton to \|Δλ\| ≤ 1e-12 within 200 iterations, else `mode_lost`; no offset is added to a step denominator. | 03 | decided |
| DV-04 | same, `optimize_transition_state` | a single RMS-gradient test (3e-4); no step acceptance or trust update; energy and final Hessian unvalidated; no failure path | four convergence criteria, all required (R24); trust radius and step acceptance with every number keyed (R14); P-RFO returns no Hessian, the runner computes and validates the final Hessian in the `frequency` stage (R27); a failed search raises `TSSearchFailedError` with a named reason. | 03, 05 | decided |
| DV-05 | same, `validate_transition_state_modes` | counts modes below −40 cm⁻¹; default fraction 0.50; skips the fraction check when it is `None` | TJ A2: count below −20 cm⁻¹, cutoff −50 cm⁻¹, fraction ≥ 0.60, always checked; edge cases raise (R16). | 04 | decided |
| DV-06 | same | default mass 12.0 for an unknown element | eta's `thermo.masses` raises on an unknown element; no default mass. | 04 | decided |
| DV-07 | `tests/unit/test_v050_ts_prfo.py` | diagonal, geometry-independent model Hessian, so the lowest mode is the reaction mode by construction; mode following is never exercised | G1: tier-D model surfaces are non-diagonal, with unequal masses, and the reaction mode is not the lowest. | 03 | decided |
| DV-08 | `src/eta_rxncat/optimize/ts_optimizer.py` | no TS identity check beyond counting imaginary modes; no barrier or standard-state handling | TS identity is the three measured checks of R3 (connectivity reported, never the gate); barriers at 1 M and 1 atm in mission §5 "Barrier". | 04, 06 | decided |
| DV-09a | `pyproject.toml` | `version = "0.5.0"` | eta's version stays `0.4.0` until the acceptance verdict passes; slice 13 bumps it only on pass. | 13 | decided |
| DV-09b | `src/eta_rxncat/__init__.py` | `__version__ = "0.5.0"` | as DV-09a. | 13 | decided |

**DV-09, how the further files were checked.** The 34 starter files were compared by sha256 with the
v0.4.0 starter (`docs/prd/v0.4.0/Eta-RxnCat-v0.4.0/`, registered in `docs/prd/v0.4.0/DISCREPANCIES.md`).
30 files are byte-identical to it, including the plan copy, so they bring nothing new to v0.5.0. Four
files differ: `optimize/ts_optimizer.py` (new; DV-02…DV-06, DV-08), `tests/unit/test_v050_ts_prfo.py`
(new; DV-07), `pyproject.toml` and `src/eta_rxncat/__init__.py`. The last two were read as a diff against
v0.4.0, and each differs only in its version string (DV-09a, DV-09b). The test file was read in full.
`optimize/ts_optimizer.py` was not opened. Its rows are mission §5's text (seat rule 1).
