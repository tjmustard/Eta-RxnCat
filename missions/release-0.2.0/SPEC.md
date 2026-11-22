---
id: OPR.0.2.0
mission: release-0.2.0
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope mission create)"
created: "2026-11-22"
intent: "Give Eta-RxnCat one engine interface and five engines (RDKit FF, xtb subprocess, MACE, UMA direct, PySCF/GPU4PySCF) returning content-keyed energies, forces and Hessians in atomic units for explicit-charge, explicit-spin states, on the torch 2.13+cu129 stack, accepted by real runs on this host."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0001, ADR-0003, ADR-0008, ADR-0009, ADR-0010, ADR-0013, ADR-0014]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.2.0 — Clean-Room Potentials

## Intent

v0.2.0 is the second of ten versions. It gives Eta-RxnCat one engine interface and five engines
behind it: RDKit FF, xtb as a subprocess, MACE, UMA direct, and PySCF/GPU4PySCF. Each engine
returns an energy, forces and, when asked, a Hessian, in atomic units, for an explicit-charge,
explicit-spin `MolecularState`. Each also returns the content-pinned `EngineIdentity` and the
resolved stage that the v0.1.0 cache key needs.

v0.2.0 evaluates one structure at a time. It does not optimize, search or schedule anything.

## 1. Introduction & Goals

**Problem.** v0.1.0 built the data contracts, a canonical cache key and a store, but nothing in
the repo can compute an energy. Every later version (conformers, optimizers, TS search,
orchestrator) needs one interface that honours charge and spin, uses one unit system, fails with a
typed error, and keys results so that a cache hit is never a different calculation.

**Solution.** The plan's PRs #4–#6 (`PRDs/Eta-RxnCat_Living_Master_Plan.md`, v0.2.0), built in the
order of the Execution checklist (§5). Each engine is a module of `eta_rxncat.engines`. Heavy
libraries are imported only inside the engine that needs them.

**Inputs.**
- The plan, which is authoritative.
- `PRDs/Eta-RxnCat-v0.2.0.zip`, reference only. It has 26 files and is unpacked verbatim in
  slice 01.
- What v0.1.0 built at `e8b16de`: the core models, the store and keys, `hw_probe`,
  `tools/licence_gate.py`, `spec/compiled/architecture.yml` (five nodes), and ADR-0001 to
  ADR-0015 (PROPOSED).
- `spec/active/Draft_PRD.md` (sha256 `c691c554…`) and `spec/active/RedTeam_Report.md`
  (`b57c9f47…`, F1–F20).

**TJ's decisions that bind v0.2.0, quoted:**
- **Licence policy** (14:57Z): "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." (14:59Z): "It's fine that the engine MACE pulls in ASE just not the
  core."
- **Autonomy:** "Build, install, and run these autonomously as to move on to the next
  step/question." A failed GPU or engine run is a finding with output, never worked around.
- **v0.2.0 Q1** (what counts as done; PD-006): "C both". Adopt the zip copy's done criteria #4,
  #5 and #6 **and** the internal checks. Reference = the upstream library's own API on the same
  input. Literature benchmarks are out of scope.
- **v0.2.0 Q2:** "A". Engines that cannot represent a state's charge or spin raise
  `EngineInputError`. MACE-MP-0 accepts charge 0 and multiplicity 1 only.
- **v0.2.0 Q3** (UMA weights): "A If that fails we can do B". A = HF access plus a read token at
  `~/.cache/huggingface/token`. B = a local `uma-s-1p2p1.pt` outside the repo. The engine supports
  both, and v0.2.0 is not accepted until the UMA run passes. The token is a secret.
- **F1 / Part C Q1** (row `qitem-20261122162111-26e232a707f003e2`, 16:24Z): "Q1. A". Move the GPU
  stack to torch 2.13 `+cu129` with fairchem ≥ 2.22, for native `uma-s-1p2p1`, and re-prove
  v0.1.0's GPU acceptance on the new stack under R49's rules.
- **F12 / Part C Q2** (same row): "Q2. A". Accept the xtb 6.8.0 binary (LGPL-3.0 with bundled
  Intel MKL and ifx runtime) as a user-downloaded subprocess engine. It is recorded in the
  licence inventory and never vendored.
- **OMol25 second model** (16:52Z, via operator): "A - Ship it as a second model". The fairchem
  engine set also accepts the **conserving** OMol25 checkpoint `esen_sm_conserving_all.pt` and
  refuses the direct-force ones, under the lead's condition (accepted by TJ) of an **honest engine
  tag** (R31). It is an addition; UMA acceptance is still required (Q3).
- **UMA access** (operator, 16:54Z): TJ ran `hf auth login`. Header-only checks give HTTP 302 for
  `facebook/UMA` `uma-s-1p2p1.pt` and `facebook/OMol25` `esen_sm_conserving_all.pt`. Route A
  (fairchem's own download path) is used. The token is a secret: only presence and HTTP status
  are ever recorded.
- **Standing from v0.1.0:**
  - Q1 A: the plan is authoritative.
  - Q2 B: the starter is reference only, plus a DISCREPANCIES register.
  - `PLAN_DISCREPANCIES.md`.
  - Author "Thomas J. L. Mustard Ph.D.".
  - Size-named WebP media.
  - Never push, `PRDs/` untouched, HACF stays at v0.6.0.

## 2. Confidence Mandate

**Score: 9/10** (target 10).

Settled:
- Every finding F1–F20 has a decision (§5), and TJ answered both Part C questions.
- The contracts below rest on measurements resolve made on this host (§5, "Resolve's host
  measurements"):
  - the new lock resolves;
  - GPU and CPU PySCF agree to 1e-11 Eh with one DF auxiliary basis;
  - GPU4PySCF supports ECP energies, gradients and Hessians, and C-PCM, but not ddCOSMO;
  - the organometallic test complex is a stable, guess-independent SCF solution;
  - the MACE weights are MIT and pinned by sha256;
  - the xtb asset is pinned by GitHub's digest.

Open, and the reason the score is not 10. These are host facts that only a run can show:
- **fairchem internals.** The non-ASE batch construction in fairchem 2.26, and whether the eSEN
  checkpoint's charge and spin embeddings are live. Slice 10's first step checks this and stops
  with output.
- **Runtime compatibility on the new stack**, which the lock alone does not prove:
  - torch 2.13+cu129 with the system cuSOLVER;
  - e3nn 0.4.4 under torch 2.13 for MACE.

  Slices 02 and 09 prove these or stop with output.

## 3. Scope

### In scope (v0.2.0)
- Slice 01:
  - unpack the v0.2.0 zip into `docs/prd/v0.2.0/` with a declared ruff gate file;
  - create `docs/prd/v0.2.0/DISCREPANCIES.md`;
  - record PD-006 as decided;
  - set the marker policy, the acceptance environments and the skip→fail switch.
- The GPU and MLIP stack move to torch 2.13+cu129 and fairchem ≥ 2.22 (TJ F1 A). All four licence
  profiles are re-run, and v0.1.0's GPU smoke is re-proved on the new stack.
- `PotentialResult` in core; the `eta_rxncat.engines` package (protocol, errors, units, FD
  Hessian, option tables, resolved stage, content-pinned identity); and the five engines.
- Real acceptance runs on this host, GPU included, with records. The README's v0.2.0 claim is
  derived from the record (the slice-11 pattern), and the version moves to 0.2.0 in the last
  slice.
- A licence inventory for external binaries and model weights (`docs/licence-inventory.md`).

### Out of scope (explicitly)
- Optimization, conformers, Boltzmann (v0.3.0). Mapping, TS search, frequencies, thermochemistry
  (v0.4.0–v0.5.0). Hessians are returned raw.
- Writing engine results into the store; calling engines from a graph; a `build_engine` registry;
  a new CLI command (v0.8.0 / v1.0.0).
- `crest`, g-xTB, ORCA; MACE and UMA in one process (ADR-0010).
- Literature or experimental accuracy (TJ Q1).
- Vendoring, copying or deriving copyleft code. Importing `ase` or any copyleft-exempt package
  from `src/eta_rxncat/`.
- v0.1.0 carry-forwards that v0.2.0 does not touch:
  - store `open_timeout_s=inf` → `OverflowError` (store untouched);
  - an existing store waiting behind a writer (v0.8.0);
  - cuTENSOR (performance only);
  - CI runner disk for cu129 (CI cannot run without a push; recorded as a risk).
- Editing `PRDs/`, pushing, upgrading HACF.

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority | Slice |
|---|---|---|---|---|
| US-001 | As a later-version developer, I want one engine interface so callers never special-case an engine. | Every engine is built with `Engine.from_stage(stage, **runtime)` and exposes `stage` (the resolved, keyed stage), `identity` (content-pinned `EngineIdentity`) and `evaluate(state, *, forces=True, hessian=False) -> PotentialResult`. `import eta_rxncat.engines` on the base install succeeds and loads none of `ase`, `torch`, `mace`, `fairchem`, `gpu4pyscf`, `cupy`, `pyscf`, `rdkit` (subprocess `sys.modules` test). A missing extra, binary, weights or GPU raises `EngineUnavailableError` naming what is missing and the install command. | P0 | 04 |
| US-002 | As a developer, I want results in one unit system. | `PotentialResult` per §5 Contracts. Hartree, Hartree/Bohr (forces = −∂E/∂x), Hartree/Bohr² (Cartesian Hessian, not mass-weighted, not projected), exactly symmetric after symmetrisation, with `hessian_max_asymmetry` recorded. | P0 | 03, 04 |
| US-003 | As TJ, I want every engine to honour charge and spin exactly or refuse. | Literal mapping assertions per engine and case (§5 Test set): e.g. xtb argv `--chrg -1 --uhf 0` (hydroxide) and `--chrg 0 --uhf 1` (hydroxyl); PySCF `mol.charge`/`mol.spin` (= 2S); fairchem batch `charge`/`spin` (= multiplicity). A behavioural check on every engine that accepts both: same geometry, different multiplicity (or charge) gives a different energy. Refusals (`EngineInputError` naming engine, charge, multiplicity) for the anion, the cation and the doublet on RDKit and MACE. | P0 | 05–10 |
| US-004 | As TJ, I want RDKit UFF and MMFF94 energies and forces. | Equal to RDKit's own force field (≤1e-10 relative). Forces vs central FD of the energy ≤1e-5 Eh/Bohr. Perception failure and round-trip mismatch raise `EngineInputError`. | P0 | 05 |
| US-005 | As TJ, I want GFN2-xTB with ALPB through the xtb binary in a subprocess. | Provisioned xtb 6.8.0 (pinned digest). Equal to a hand run with the same argv at `OMP_NUM_THREADS=MKL_NUM_THREADS=1`: energy ≤1e-10 Eh, gradient ≤1e-9 Eh/Bohr. Hessian per the §5 convention, checked against FD of xtb gradients. ALPB state keyed. Dielectric-only ALPB is refused. Errors carry the stderr tail. | P0 | 08 |
| US-006 | As TJ, I want MACE energies and forces on CPU or CUDA. | MACE-MP-0 medium (MIT, sha256-pinned). Equal to MACE's own calculator on the same input (≤1e-6 eV, float64). Neutral closed-shell only, refusal proofs for the rest. Device recorded. No implicit download. | P0 | 09 |
| US-007 | As TJ, I want UMA `uma-s-1p2p1` (`omol`), and the OMol25 eSEN-sm-conserving model as a second model (TJ 16:52Z), each under its own honest tag, with charge and spin, with no `ase` import in eta_rxncat. | `uma_direct` and `esen_omol25` each equal fairchem's own predictor on the same input and checkpoint (≤1e-6 eV energy, ≤1e-5 eV/Å forces), on all four test cases. Direct-force checkpoints are refused. Weights via HF cache (route A; B supported). Identity `<model>@sha256:<hex>`. The token never appears in any output (test). | P0 | 03, 10, 11 |
| US-008 | As TJ, I want PySCF DFT on GPU4PySCF with an automatic CPU DF-KS fallback above the VRAM budget. | DF on both paths with one keyed auxiliary basis. GPU vs CPU ≤1e-6 Eh on every test case (resolve measured ≤5e-11), plus a cross-evaluation check. Above the budget, or on a listed OOM, CPU DF once, recorded. VRAM estimate calibrated and recorded. | P0 | 06, 07 |
| US-009 | As TJ, I want ddCOSMO and PCM from a solvent name or a dielectric. | A documented name→ε table. Unknown name → `EngineInputError`. An explicit dielectric wins. The solvated energy differs from gas. ddCOSMO runs on CPU (GPU4PySCF has none), recorded. C-PCM GPU vs CPU ≤1e-6 Eh. | P0 | 06, 07 |
| US-010 | As TJ, I want the SCF ladder to recover hard cases and prove it found the same state. | DIIS → level shift and damping → SOSCF → small-basis `project_dm_nr2nr`. Every step is recorded. Internal stability analysis always runs after convergence (≤2 follows, else `ScfConvergenceError`). Injected per-step `max_cycle` proves each step deterministically. | P0 | 06 |
| US-011 | As TJ, I want PySCF analytic gradients and Hessians checked against FD. | Gradient vs FD of energy ≤1e-5 Eh/Bohr; Hessian vs FD of gradient ≤1e-4 Eh/Bohr² on water and on the Zeise anion (with ECP). A combination PySCF can't do analytically uses FD of analytic gradients, labelled. | P0 | 06, 07 |
| US-012 | As TJ, I want TJ's licence policy to hold by construction. | All four licence-gate profiles pass on the new lock. AST ban and base-install subprocess test. External binaries and weights recorded in `docs/licence-inventory.md`. No seat adds an exemption a TJ decision does not cover. | P0 | 01, 02, 04, 08–10 |
| US-013 | As TJ, I want the v0.2.0 discrepancy register and PD-006 kept current. | `docs/prd/v0.2.0/DISCREPANCIES.md` (engine files plus version bump; v0.1.0-identical modules not re-registered) is complete at audit; PD-006 `decided`. | P0 | 01, all |
| US-014 | As TJ, I want v0.2.0 accepted only after every engine runs on this host, recorded. | `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json` holds the re-proved stack smoke plus each engine's acceptance, per R49's rules; the README claim is derived from it; version 0.2.0. | P0 | 11 |

## 5. Technical Specifications

### Resolved trade-off log

Vocabulary: **resolved** (decided here, with the slice that carries it), **out of scope** (with
the version that owns it). No finding is `accepted` and none is pending.

| ID | Finding | Severity | Disposition | Decision |
|---|---|---|---|---|
| R1 | F1 `uma-s-1p2p1` vs the locked fairchem and torch index | blocker | resolved (TJ A) | Slice 02. Index → `pytorch-cu129`, `fairchem-core>=2.22`. Resolve's scratch `uv lock`: exit 0, torch 2.13.0+cu129 in every torch profile, fairchem-core 2.26.0, mace-torch 0.3.17, gpu4pyscf-cuda12x 1.9.2, cupy-cuda12x 14.2.0, nvidia-cusolver-cu12 11.7.5.82; ray and ray-haproxy drop out. New NVIDIA packages without the `nvidia-` prefix (`cuda-toolkit`, `cuda-bindings`, `cuda-python`, `cuda-pathfinder`) and NVIDIA wheels with unrecognised metadata are handled under TJ's v0.1.0 Q1 A ("NVIDIA CUDA wheels exempt"), version-pinned; other new failures stop and are reported. v0.1.0's GPU smoke is re-proved on the new stack with R49's rules, recording which cuSOLVER is mapped. PROPOSED ADR-0020. |
| R2 | F2 GPU vs CPU agreement with DF only on CPU; one key for two approximations | high | resolved | DF on **both** paths: keyed `density_fit` (default `true`) and `auxbasis` (default `def2-universal-jkfit`). Measured: water B3LYP/def2-SVP DF GPU−CPU 6.2e-12 Eh, non-DF GPU−CPU 7.3e-12, DF−non-DF 1.0e-5 (so different keys); Zeise anion DF+ECP GPU−CPU 4.9e-11. Device is not keyed; it is recorded. GPU4PySCF 1.9.2 solvents: `pcm` and `smd`, **no ddCOSMO**. C-PCM GPU−CPU 6.0e-12 Eh, so ddCOSMO always runs on CPU, recorded. Slices 06, 07. PROPOSED ADR-0018. |
| R3 | F3 Rh/Pd def2 basis run all-electron without an ECP | high | resolved | A def2-* basis with any Z > 36 resolves keyed `ecp` = the basis name. A non-def2 basis with Z > 36 and no explicit `ecp` → `EngineInputError`. The ECP is keyed through the resolved stage. Measured: GPU4PySCF ECP energy, gradient (N×3) and Hessian (N×N×3×3) all run; CPU vs GPU ECP integrals agree to 1.2e-12. Slices 06, 07. ADR-0018. |
| R4 | F4 the reference comparison cannot catch mapping errors | high | resolved | Literal mapping assertions per engine and test case (US-003), plus a behavioural check (different multiplicity or charge gives a different energy) on every engine that accepts both. Slices 05–10. |
| R5 | F5 model id is a name, not a content pin | high | resolved | `EngineIdentity.model = "<name>@sha256:<64 hex>"`, from the weights file streamed through sha256 at construction. MACE: `mace-mp-0-medium` = `2023-12-03-mace-128-L1_epoch-199.model`, 44,422,970 B, sha256 `01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845` (resolve downloaded and hashed it), MIT per the `ACEsuit/mace-mp` README. UMA: `uma-s-1p2p1.pt` (2,333,393,615 B), with the hash computed at load because the HF LFS oid is masked while the repo is gated. MLIP model is never `None`. PROPOSED ADR-0017. |
| R6 | F6 keyed vs runtime settings undefined | high | resolved | Each engine declares a keyed-option table (§5 Contracts). `Engine.stage` is the **resolved stage**: the given `StageConfig`, with every keyed default filled, the solvent name normalised, and `engine_impl` (int, per engine, starting at 1) added. The key is `build_stage_key(state, engine.stage, engine.identity)`. Unknown option keys → `EngineInputError`. Runtime knobs (threads, timeouts, device preference, paths) are constructor arguments and are never keyed. PROPOSED ADR-0016. |
| R7 | F7 ALPB reference state unspecified (3.33 kcal/mol) | high | resolved | Keyed `alpb_state`, default `gsolv` (xtb's default, with no standard-state shift), so v0.5.0's 1 M `ThermoConfig` correction is applied exactly once. Dielectric-only ALPB → `EngineInputError`. Solvent names are lowercased in the resolved stage. Slice 08. |
| R8 | F8 acceptance environments and "not skippable" undefined | high | resolved | `.venv` stays the base dev env for the required checks and never gets extras. Acceptance envs: `.venv-accept-gpu` (`--extra gpu`), `.venv-accept-mace` (`--extra gpu --extra mlip-mace`), `.venv-accept-uma` (`--extra gpu --extra mlip-uma`), each `UV_PROJECT_ENVIRONMENT=<dir> uv sync --locked --extra …` (dev group included). Gitignored. Only the build seat creates or syncs them; the audit seat runs `uv run --no-sync`. `ETA_RXNCAT_ACCEPTANCE=1` turns any skip into a failure (conftest hook). Commands and records are in slice 11. Slice 01. PROPOSED ADR-0019. |
| R9 | F9 ladder basis, trigger, different solution, reference type | medium | resolved | `ladder_small_basis` is keyed: `def2-sv(p)` for def2-* bases, else `sto-3g`. Per-step `max_cycle` is injected (runtime, tests) as the deterministic trigger. Internal stability analysis **always** runs after convergence, on any path: at most 2 follows, else `ScfConvergenceError`. RKS/RHF for multiplicity 1, UKS/UHF above. `init_guess` keyed, `minao`. Grounded on resolve's measurement: linear PdCl₂ gives guess-dependent solutions 7.9 mEh apart (GPU and CPU each reach one), and the higher state is internally unstable; following it lands lower still and still unstable. So that molecule is excluded from the test set. Slice 06. ADR-0018. |
| R10 | F10 VRAM estimate, probe call, OOM catch | medium | resolved | The budget is read once at construction: CuPy `cupy.cuda.runtime.memGetInfo()` total → `hw_probe.vram_budget_bytes(total)`. No `probe_hardware()` per evaluate, and no torch import in the PySCF engine. The estimate formula and calibration record are `docs/prd/v0.2.0/calibration/pyscf_vram.json`. OOM is exactly: `cupy.cuda.memory.OutOfMemoryError`; `CUBLASError` with `CUBLAS_STATUS_ALLOC_FAILED`; `CUSOLVERError` with `CUSOLVER_STATUS_ALLOC_FAILED`; `CUDARuntimeError` with `cudaErrorMemoryAllocation`. On OOM: free the CuPy default and pinned pools, then one CPU DF run, recorded. Slice 07. |
| R11 | F11 "without ASE" scope | medium | resolved | No `ase` import in `src/eta_rxncat/` (AST). An engine library may load `ase` in-process. Subprocess test: the base install's `import eta_rxncat, eta_rxncat.engines` leaves `ase`, `torch`, `mace`, `fairchem`, `gpu4pyscf`, `cupy`, `pyscf`, `rdkit` out of `sys.modules`. Slice 04. |
| R12 | F12 xtb provisioning and bundled MKL | medium | resolved (TJ A) | xtb 6.8.0: `https://github.com/grimme-lab/xtb/releases/download/v6.8.0/xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz`, 22,686,860 B, GitHub digest `sha256:db090333361749ae0d9ccf0ce7c0035c0000f2ebad0847f6d77191d1954f4d68`. The release's `.sha256` file names the tarball `xtb-bleed-…`, which is recorded. Installed under `~/.local/share/eta-rxncat/xtb/6.8.0/`, outside the repo. `xtb --version` is recorded. The licence inventory records LGPL-3.0 plus statically linked Intel MKL and ifx runtime (proprietary), user-downloaded, subprocess only. Subprocess env: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OMP_STACKSIZE`. Slice 08. PROPOSED ADR-0021. |
| R13 | F13 xtb tolerance and Hessian semantics | medium | resolved | Reference runs use `OMP_NUM_THREADS=MKL_NUM_THREADS=1`: energy ≤1e-10 Eh, gradient ≤1e-9 Eh/Bohr. One convention for every engine: Cartesian, Eh/Bohr², not mass-weighted, not projected. xtb's `hessian` file is checked against FD of xtb gradients, and converted if its convention differs; the finding is recorded. Slice 08. |
| R14 | F14 RDKit perception can reproduce the charge with a wrong structure | low | resolved | Round-trip check: the perceived molecule's formula equals the state's symbols, and its total formal charge equals the state's charge, else `EngineInputError`. The remaining risk (a different resonance assignment with the same formula and charge) is documented in the engine docstring and the register. Slice 05. |
| R15 | F15 symmetry tolerance absolute; FD noise | low | resolved | Engines symmetrise `H ← (H+Hᵀ)/2` and record `hessian_max_asymmetry` (the pre-symmetrisation max) in `PotentialResult`, so validation is exact symmetry. FD step is keyed `fd_step_bohr` (default 0.005). MACE runs float64; UMA's dtype is recorded in `recovery_steps`/notes if float32. Slices 03, 04, 09, 10. |
| R16 | F16 CODATA versions | low | resolved | One `engines.units` module (CODATA 2018). Reference tests convert the upstream native result with these same constants, so version differences cancel. Coordinates go to every library in Å (PySCF `unit="Angstrom"`; xtb via an `.xyz` in Å). Slices 04–10. |
| R17 | F17 ledger ownership | low | resolved | New node `eta_rxncat_engines` (depends_on `eta_rxncat_core`, `eta_rxncat_hw_probe`), with files `src/eta_rxncat/engines/**`, `tests/unit/engines/**`, `tests/acceptance/**`. `src/eta_rxncat/engines/**` moves out of `eta_rxncat_scaffold` via `hyper_ledger.py ensure-node --files`, passing the full list. Calibration and evidence under `docs/prd/v0.2.0/**` stay with scaffold (`docs/**`). Engine GPU tests live in `tests/unit/engines/` with markers, not `tests/gpu/`. Slice 04. |
| R18 | F18 test runtime | low | resolved | Default `uv run pytest` = fast pure tests plus base-install RDKit and PySCF tests on tiny molecules. Marked and deselected by default: `gpu`, `xtb`, `mlip_mace`, `mlip_uma`, `slow` (DFT FD checks), `acceptance`. Slice 01. |
| R19 | F19 unit tests could download | low | resolved | `tests/conftest.py` sets `HF_HUB_OFFLINE=1`. MACE and UMA never download implicitly: MACE needs a local model file, and UMA needs the HF cache or a local checkpoint. Provisioning is an explicit seat command recorded in the slice, never inside a test. Slices 01, 09, 10. |
| R20 | F20 negative constraints | low | resolved | All proposed additions adopted in §6, worded per F10/F11. |
| R21 | Part B §1 state library versions | — | resolved | §5 "Target versions". |
| R22 | Part B §2 confidence while F1 open | — | resolved | F1 answered; score 9 (§2). |
| R23 | Part B §8 interim state if UMA access never arrives | — | resolved | **Runs now.** UMA access opened at 16:54Z (HTTP 302 with TJ's login; operator), so the UMA proofs are required in slice 10 and again in slice 11's acceptance. If access ever fails again, that run is a finding with output and HTTP status, never mocked, and v0.2.0 is not accepted until UMA passes (TJ Q3). |
| R24 | Part C Q1 | — | resolved (TJ A) | = R1. |
| R25 | Part C Q2 | — | resolved (TJ A) | = R12. |
| R26 | Carry-forward: store `open_timeout_s=inf` → OverflowError | — | out of scope | v0.2.0 does not touch the store (v0.8.0 or the next store change). |
| R27 | Carry-forward: licence_gate edge cases (no-Name dist-info skipped; first dist-info per name wins) | — | resolved | Slice 02 changes the gate's inputs anyway. A dist-info with no `Name` → FAIL (`unnamed distribution`); two dist-infos with one normalised name → FAIL (`ambiguous`). Synthetic tests for both. |
| R28 | Carry-forward: CI runner disk for cu128/cu129 | — | out of scope | CI cannot run without a push. §7 risk; slice 02 records the per-profile download size. |
| R29 | Carry-forward: cuTENSOR absent | — | out of scope | Performance only. |
| R30 | Resolve measurement: SCF state ambiguity on PdCl₂ | — | resolved | See R9. The test set's organometallic is `[PdCl₃(C₂H₄)]⁻`, measured guess-independent (minao = huckel) and internally stable, and also `[PdCl₄]²⁻` (spare). |
| R31 | v0.2.0 replan 1 (TJ, 16:52Z, "A - Ship it as a second model"; the lead's honest-tag condition) | — | resolved | One engine tag per model family. Core `EngineTag` gains **`esen_omol25`** (slice 03), amending ADR-0001's frozen set (PROPOSED ADR-0022). Slice 10 becomes the fairchem slice: a private shared bridge plus two engines. `uma_direct` accepts exactly `method="uma-s-1p2p1"`; `esen_omol25` accepts exactly `method="esen-sm-conserving-all-omol"` (`facebook/OMol25` `checkpoints/esen_sm_conserving_all.pt`, 50,958,067 B; FAIR Chemistry License v1, the same as UMA's). Direct-force checkpoints are refused by name **and** by the loaded config's direct-forces flag. `allscaip-md-conserving-all-omol` is refused as not approved. Identity is per ADR-0017: `esen-sm-conserving-all-omol@sha256:<hex>`. Same four-case test set and the same fairchem-predictor reference. First build step: a stop-and-report check that charge and spin are live. Slice 11 adds `esen_omol25` to acceptance; UMA stays required. Rejected: eSEN under `uma_direct` (dishonest key), and a generic `fairchem` tag (renames the plan's `uma_direct` module). |
| R32 | v0.2.0 replan 2 (slice 01 audit finding `qitem-20261122165838-accad9ea`): the acceptance switch converted only setup/call skips, so a module-level `pytest.importorskip` passed under `ETA_RXNCAT_ACCEPTANCE=1` (probe: exit 0, "1 passed, 1 skipped"), and an xfail kept exit 0 | high | resolved | Slice 04 (unbuilt, before every engine test and before 07) extends `tests/conftest.py`. Under `=1`, skipped **collect** reports become failures (non-zero exit, module named), and `xfail`-marked tests (xfailed or xpassed) are reported failed with a non-zero exit. A rule test bans module-level `pytest.importorskip` / `pytest.skip` in `tests/unit/engines/` and `tests/acceptance/`. Proofs use the audit's probe pattern with the real conftest. R8 now holds as written: any skip fails an acceptance run. Slice 01 (audited) is not edited. |
| R33 | Ledger clobber risk (lead, replan 2): `hyper_ledger.py ensure-node --from-spec` on an existing node replaces its `files:` with the slice's narrower `hacf_touches` | medium | resolved | Mission rule (§6): never run `ensure-node --from-spec` on a node that already exists. Use `ensure-node --id <node> --spec-refs <slice dot-id>` to link a slice, and change `files:` only with `--files` given the **full** current list read from `spec/compiled/architecture.yml` plus the additions. Reconcile with `hypergraph_updater.py`. `--from-spec` is allowed only to create a node that does not exist yet. Slice 04's text is updated. Listing full ownership in each slice's `hacf_touches` was rejected: touches mean "may change", not "owns". |
| R34 | v0.2.0 replan 3 (slice 02 stop-and-report): torch 2.13.0+cu129's `License-Expression` (`Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`) fails the gate only on `BSL-1.0`; torch 2.8 passed | — | resolved (lead decision, within TJ policy; TJ informed) | Add `BSL-1.0` to the SPDX `allowed` list. Boost 1.0 is OSI/FSF-approved permissive with no copyleft, i.e. "MIT/BSD/equivalent" under TJ's 14:57Z policy, the same kind of addition as `Zlib`/`CC0-1.0`, which TJ accepted ("no objection"). An allowed licence, not a version-pinned exemption. Slice 02 Mini-req 2b plus synthetic gate tests (BSL passes, AND-with-BSL passes, unknown id and BSL AND GPL still fail). Amends ADR-0013's list and v0.1.0 R45's set; no new ADR. |
| R35 | v0.2.0 replan 4 (slice 05 stop-and-report): Mini-req 3's refusal rules accepted hydroxide and hydronium (RDKit 2026.09.2 perceives `[H][O-]` / `[H][O+]([H])[H]`, round-trips the charges and has UFF and MMFF params), contradicting US-003, the §5 test plan and the slice's own proofs | — | resolved (lead decision A) | `rdkit_ff` accepts **only charge 0 and multiplicity 1**. That check runs first, before any RDKit call, with the message `rdkit_ff: charge <q>, multiplicity <m>: only neutral closed-shell states (charge 0, multiplicity 1) are supported`. The perception and round-trip check (R14) stays for neutral molecules. Rationale: UFF has no electrostatics by default, so ion energies are not meaningful. This matches TJ v0.2.0 Q2 "A" (refuse unrepresentable states) and US-003. The proofs are unchanged (they already refuse anion, cation and doublet). |

### Seed deviations

| Slice | Seed field | Was | Now | R-row |
|---|---|---|---|---|
| OPR.0.2.0.3 `03-potential-result` | Mini-req 4, constraint, proof | core unchanged except `PotentialResult` | `EngineTag` + `esen_omol25` | R31 |
| OPR.0.2.0.10 `10-uma-direct` | intent, body, depends_on (+.3), touches, oracle | one engine, `uma_direct` | two engines on one bridge (`uma_direct`, `esen_omol25`); all proofs required now | R31, R23 |
| OPR.0.2.0.11 `11-acceptance` | envs, preconditions, modules, commands, record, proof | five engines; UMA could be blocked | six engines; `hf_access` statuses; UMA required | R31, R23 |
| OPR.0.2.0.4 `04-engines-base` | Mini-req 9, Task 4b, touches (+`tests/conftest.py`, `tests/unit/test_test_policy.py`), proofs, oracle; ledger note | setup/call skip conversion only (slice 01) | collection-phase skips and xfail fail under `=1`; module-level-skip ban; no `--from-spec` on existing nodes | R32, R33 |
| OPR.0.2.0.2 `02-gpu-stack-cu129` | Mini-req 2b, proof | allowed list without `BSL-1.0` | `BSL-1.0` allowed; synthetic BSL gate tests | R34 |
| OPR.0.2.0.5 `05-rdkit-ff` | context, Mini-req 3, intent | multiplicity 1 plus a perception-reproduced charge | charge 0 and multiplicity 1 only, checked first; R14 for neutrals | R35 |

### Resolve's host measurements (2026-11-22; scratch under TMPDIR, removed)
- **Lock:** `uv lock` with `pytorch-cu129` and `fairchem-core>=2.22` → exit 0 (versions in R1).
- **PySCF 2.15.1 / GPU4PySCF 1.9.2 on the RTX 5060 Ti, B3LYP/def2-SVP, `conv_tol` 1e-10:**

  | System | Variant | GPU − CPU |
  |---|---|---|
  | water | DF (`def2-universal-jkfit`) | 6.2e-12 Eh |
  | water | non-DF | 7.3e-12 Eh |
  | water | C-PCM ε 78.3553 | 6.0e-12 Eh |
  | `[PdCl₃(C₂H₄)]⁻` | DF+ECP | 4.9e-11 Eh (E = −1586.87553329 Eh) |

  - Water DF minus non-DF = 1.0e-5 Eh.
  - On the Zeise anion, GPU took 2.5 s (kernels cached) and CPU 13.4 s.
- **GPU4PySCF solvent modules:** `pcm`, `smd`; no `ddcosmo`.
- **Linear PdCl₂ (2.25 Å):**
  - CPU `minao` and `atom` guesses → −1048.05672443 Eh; `huckel` and `1e` → −1048.04879195 Eh,
    the same state GPU `minao` reached. Cross-evaluated energies agree to 3e-11, and ECP integrals
    to 1.2e-12.
  - The high state is internally and externally unstable. Following it gives −1048.06002981 Eh,
    which is still unstable.
- **`[PdCl₄]²⁻` and `[PdCl₃(C₂H₄)]⁻`:** `minao` = `huckel`, internally stable.
- **MACE-MP-0 medium:** 44,422,970 B, sha256 `01bfe221…35845`.
- **xtb 6.8.0 asset digest:** from the GitHub API (R12).
- **HF:** `facebook/UMA` lists `checkpoints/uma-s-1p2p1.pt` (2,333,393,615 B). The LFS oid is
  masked.
- **HF, after the replan:**
  - `facebook/OMol25` `checkpoints/esen_sm_conserving_all.pt` is 50,958,067 B, LFS oid masked
    (public metadata);
  - TJ's token file is present (presence checked only, never read);
  - access: 302 for both repos (operator, 16:54Z).

### Target versions
torch 2.13.0+cu129; fairchem-core ≥ 2.22 (locked 2.26.0); mace-torch 0.3.17 (e3nn 0.4.4 in
`mlip-mace`); pyscf 2.15.1; gpu4pyscf-cuda12x 1.9.2; cupy-cuda12x 14.2.0; rdkit 2026.9.2; xtb
6.8.0. The lock is the authority. A differing version is used as locked and stated in the
handoff.

### Blast radius
Measured in the draft with `hyper_ledger.py impact`: nodes `eta_rxncat_cli`, `eta_rxncat_core`,
`eta_rxncat_hw_probe`, `eta_rxncat_scaffold`; radius those plus `eta_rxncat_store`.

| Node id | Slices | Change |
|---|---|---|
| `eta_rxncat_scaffold` | 01, 02, 11 | `docs/prd/v0.2.0/**`, `pyproject.toml` (index, fairchem floor, markers, gate config), `uv.lock`, `tests/conftest.py`, `.gitignore`, `AGENTS.md` project section, `tools/licence_gate.py` (R27), `docs/licence-inventory.md`, README/version (11). Loses `src/eta_rxncat/engines/**` to the new node. |
| `eta_rxncat_core` | 03 | `PotentialResult` added; `EngineTag` gains `esen_omol25` (R31). `store`/`cli` → needs_review; no consumed field changes, and existing keys are unchanged. |
| `eta_rxncat_engines` (**new**, not in the graph yet) | 04–10 | `src/eta_rxncat/engines/**`, `tests/unit/engines/**`, `tests/acceptance/**`; depends_on `eta_rxncat_core`, `eta_rxncat_hw_probe`. |
| `eta_rxncat_hw_probe` | — | Read only (`vram_budget_bytes`). |
| `eta_rxncat_store` | — | Read only (`build_stage_key`). The key contract is honoured through the resolved stage and identity. |

### Execution checklist (build order)
1. `01-reference-and-test-policy` — zip unpack and gate file, v0.2.0 register, PD-006, markers,
   acceptance envs, skip→fail switch, offline tests.
2. `02-gpu-stack-cu129` — TJ F1 A: index, fairchem floor, lock, four licence profiles, gate edge
   cases (R27), v0.1.0 GPU smoke re-proved on the new stack.
3. `03-potential-result` — core `PotentialResult`; `EngineTag` + `esen_omol25` (R31).
4. `04-engines-base` — new node; protocol, errors, units, options, resolved stage, identity,
   FD Hessian, base-install import test.
5. `05-rdkit-ff` — UFF/MMFF94.
6. `06-pyscf-cpu` — PySCF CPU: DF, ECP, solvation table, ladder plus stability, analytic
   derivatives.
7. `07-pyscf-gpu` — GPU4PySCF dispatch, budget, calibration, OOM fallback, GPU/CPU agreement.
8. `08-xtb-subprocess` — provisioning, licence inventory, subprocess engine, ALPB.
9. `09-mace` — MACE-MP-0 medium, pinned.
10. `10-uma-direct` — fairchem engines on one bridge: `uma_direct` (`uma-s-1p2p1`) and
    `esen_omol25` (OMol25 eSEN-sm-conserving), weights via HF (route A), secret handling (R31).
11. `11-acceptance` — every engine on this host, R49 rules, record, README claim, version
    0.2.0.

The feature is done when slice 11 audits PASS.

### Contracts

**Errors** (`eta_rxncat.engines.errors`):
- `EngineError` is the base, with four subclasses:
  - `EngineUnavailableError`: a missing extra, binary, weights or GPU; names the piece and the
    install or provision command.
  - `EngineInputError`: the state, stage or option cannot be represented; names engine, charge,
    multiplicity where relevant.
  - `ScfConvergenceError`: records the steps tried.
  - `EngineRuntimeError`: a library or subprocess failure, carrying a diagnostic tail of at most
    40 lines.
- No partial results. No bare `except Exception`. Library exceptions are caught by named type
  and re-raised `from` the cause.

**Engine API** (`eta_rxncat.engines.base`):
- `Engine.from_stage(stage: StageConfig, **runtime) -> Engine` raises `EngineInputError` if
  `stage.engine` ≠ the engine's tag.
- Properties: `tag`, `stage` (the resolved `StageConfig`), `identity` (`EngineIdentity`).
- `evaluate(state, *, forces: bool = True, hessian: bool = False) -> PotentialResult`.
- `kind` does not change a single-point evaluation, and `frozen_atom_indices` is accepted and
  ignored for single points; both stay keyed as in v0.1.0.

**Resolved stage and options.** Keyed options live in `StageConfig.options` and are filled with
their defaults in `engine.stage`, together with `engine_impl`. Runtime arguments are constructor
keywords and never reach the key. Any other option key → `EngineInputError`.

| Engine (tag) | `method` | keyed options (default) | runtime arguments |
|---|---|---|---|
| RDKit (`rdkit_ff`) | `uff` \| `mmff94` | `fd_step_bohr` (0.005), `engine_impl` (1) | — |
| xtb (`xtb_subprocess`) | `gfn2` | `accuracy` (1.0), `etemp_k` (300.0), `alpb_state` (`gsolv`), `engine_impl` (1) | `binary`, `threads` (1), `timeout_s` (3600), `omp_stacksize` (`"1G"`) |
| MACE (`mace`) | `mace-mp-0-medium` | `dtype` (`float64`), `fd_step_bohr` (0.005), `engine_impl` (1) | `model_path`, `device` (`auto`) |
| UMA (`uma_direct`) | `uma-s-1p2p1` | `task` (`omol`), `fd_step_bohr` (0.005), `engine_impl` (1) | `checkpoint_path` or HF cache, `device` (`auto`) |
| eSEN OMol25 (`esen_omol25`, R31) | `esen-sm-conserving-all-omol` | `task` (`omol`), `fd_step_bohr` (0.005), `engine_impl` (1) | `checkpoint_path` or HF cache, `device` (`auto`) |
| PySCF (`pyscf_gpu_cpu`) | xc name or `hf`; `basis` required | `density_fit` (true), `auxbasis` (`def2-universal-jkfit`), `ecp` (rule R3), `grids_level` (3), `conv_tol` (1e-10), `init_guess` (`minao`), `pcm_method` (`C-PCM`), `ladder_small_basis` (rule R9), `stability` (`internal`), `engine_impl` (1) | `device` (`auto`\|`cpu`\|`cuda`), `max_memory_mb`, `ladder_max_cycle` (tests only) |

**Identity:**
- `EngineIdentity(name=<tag>, version=<installed library version | "xtb <x.y.z>">, model=<None | "<name>@sha256:<hex64>">)`.
- `model` is `None` only for RDKit, xtb and PySCF. Neither the HF token nor any path goes into
  the identity.

**`PotentialResult`** (core; strict; frozen; `extra="forbid"`):

| Field | Type |
|---|---|
| `energy_hartree` | `FiniteFloat` |
| `forces_hartree_per_bohr` | `list[list[FiniteFloat]] \| None` (N×3) |
| `hessian_hartree_per_bohr2` | `list[list[FiniteFloat]] \| None` (3N×3N, exactly symmetric) |
| `hessian_method` | `Literal["analytic","finite_difference"] \| None`, set iff the Hessian is set |
| `hessian_max_asymmetry` | `FiniteFloat ≥ 0 \| None`, set iff the Hessian is set |
| `engine` | `EngineIdentity` |
| `stage_engine_impl` | `int` |
| `device` | `Literal["cpu","cuda"]` |
| `device_reason` | `str \| None` (e.g. `ddcosmo_cpu_only`, `vram_estimate_over_budget`, `gpu_oom`) |
| `wall_time_s` | `FiniteFloat ≥ 0` |
| `recovery_steps` | `list[str]` |

Shape checks are internal to the model: forces N×3; Hessian 3N×3N; N consistent when both are
present.

**Units:** `engines.units`, CODATA 2018: Bohr = 0.529177210903 Å; Hartree = 27.211386245988 eV;
Hartree = 627.5094740631 kcal/mol. Forces = −∂E/∂x.

**Test set** (`tests/unit/engines/data/`, committed `.xyz` plus charge and multiplicity; Å):
- water: `O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692`, charge 0, multiplicity 1.
- hydroxide anion: `O 0 0 0; H 0 0 0.97`, charge −1, multiplicity 1.
- hydroxyl radical (doublet): the same geometry, charge 0, multiplicity 2.
- hydronium cation (refusal case): `O 0 0 0.0656; H 0 0.9369 -0.1754; H 0.8114 -0.4685 -0.1754;
  H -0.8114 -0.4685 -0.1754`, charge +1, multiplicity 1.
- `[PdCl₃(C₂H₄)]⁻`: `Pd 0 0 0; Cl -2.32 0 0; Cl 0 2.32 0; Cl 0 -2.32 0; C 2.10 0 0.69;
  C 2.10 0 -0.69; H 2.30 0.93 1.23; H 2.30 -0.93 1.23; H 2.30 0.93 -1.23; H 2.30 -0.93 -1.23`,
  charge −1, multiplicity 1. Resolve-verified stable and guess-independent at
  B3LYP/def2-SVP+ECP.

Who runs what:
- UMA, eSEN (`esen_omol25`), xtb and PySCF run water, hydroxide, hydroxyl and the Pd anion.
- RDKit and MACE run water and prove refusal on hydroxide, hydroxyl and hydronium.
- Literal mapping checks use each case's own charge and multiplicity. For example, xtb gets
  `--chrg -1 --uhf 0` for hydroxide and `--chrg 0 --uhf 1` for hydroxyl. PySCF gets `mol.spin`
  0 / 1, and fairchem gets batch `spin` 1 / 2.

**Environments:**
- `.venv` (base dev; required checks).
- `.venv-accept-gpu`, `.venv-accept-mace`, `.venv-accept-uma` (R8).
- The xtb binary is outside the repo (R12). MACE weights are in `~/.cache/eta-rxncat/mace/`, and
  UMA in the HF cache or a TJ-given path, all outside the repo.

**Acceptance record** (`docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`, slice 11): `record_schema: 2`,
`commit_sha`, `run_at_utc`, `preflight` (as v0.1.0), `smoke` (v0.1.0's `SmokeResult` re-run on
the final HEAD), `engines.<tag>` (per case: energy, device, `device_reason`, `recovery_steps`,
identity, reference |Δ|), `commands` with exit codes, `logs` (full, untruncated), and for UMA,
`hf_token_present: bool` only. R49's architecture-error scan applies to all logs.

### The discrepancy register
`docs/prd/v0.2.0/DISCREPANCIES.md` has the same format, writer, checker and owner as v0.1.0. Only
the engine files and the version bump are compared; v0.1.0-identical modules are not
re-registered. The draft's known entries are seeds:
- solvent name ignored;
- swallowed perception errors;
- the GB VRAM formula;
- the per-evaluate probe;
- float32 UMA positions;
- `mace_mp` usage;
- engine names that differ from the tags;
- FD MLIP Hessians;
- the starter's `< −75.0` test.

`PLAN_DISCREPANCIES.md`: PD-006 → `decided` (TJ Q1 "C both"); the v0.2.0 zip-hash row confirmed.

## 6. Negative Constraints
- **DO NOT** import `ase`, `sella`, in-process `tblite`, `psi4` or any copyleft-exempt package in
  `src/eta_rxncat/`. An engine *library* loading `ase` in-process is allowed (TJ 14:59Z).
- **DO NOT** import torch, mace, fairchem, gpu4pyscf, cupy, pyscf or rdkit at module import time.
- **DO NOT** vendor, copy or derive copyleft code, or commit the xtb binary or any weights.
- **DO NOT** silently ignore charge or multiplicity. **DO NOT** return a partial result or catch
  bare `Exception`. Catch only the named exceptions (R10).
- **DO NOT** pass a def2 basis for Z > 36 without its ECP (R3).
- **DO NOT** key runtime-only knobs, or leave a result-changing setting unkeyed (R6).
- **DO NOT** record an MLIP model id without its content hash (R5).
- **DO NOT** call `probe_hardware()` per evaluation (R10).
- **DO NOT** run acceptance in `.venv`, `uv sync` an acceptance env from the audit seat, or count a
  skipped acceptance test as a pass (R8).
- **DO NOT** let unit tests reach the network or download weights (R19).
- **DO NOT** pass an ALPB state other than the keyed one (R7).
- **DO NOT** run a model under another family's tag, or accept a direct-force fairchem checkpoint
  (R31).
- **DO NOT** add a licence exemption that no TJ decision covers; report it to the lead.
- **DO NOT** write engine results into the store, or add a CLI command.
- **DO NOT** work around a failed GPU or engine run (skip, CPU substitution, looser tolerance,
  reinstall loops). Report it with output.
- **DO NOT** write, log, echo or record a Hugging Face token, or ask for one in a row or a
  message.
- **DO NOT** run `hyper_ledger.py ensure-node --from-spec` on an existing node. Use `--id … --spec-refs …`,
  and `--files` only with the full current list (R33).
- **DO NOT** edit `PRDs/`, push, or upgrade HACF. Do not touch HACF-managed files.

## 7. Risks & Mitigation
- **New stack runtime breakage** (torch 2.13+cu129 with the system cuSOLVER; e3nn 0.4.4 under
  torch 2.13). *Mitigation:* slices 02 and 09 run real proofs first and stop with output.
- **UMA access lost again.** *Mitigation:* R23. The failure is a finding with HTTP status;
  nothing is mocked.
- **SCF state ambiguity on organometallics** (measured, R30). *Mitigation:* a keyed guess,
  mandatory stability analysis, and a stable test complex.
- **Upstream API drift** (fairchem internals for the clean-room bridge). *Mitigation:* pinned by
  the lock, tested against fairchem's own predictor.
- **VRAM estimate wrong.** *Mitigation:* the calibration record, plus one recorded OOM fallback.
- **CI disk** for cu129 profiles (R28). *Mitigation:* recorded; CI is not run in v0.2.0.
- **xtb binary provenance.** *Mitigation:* the pinned digest, the `.sha256` name mismatch
  recorded, `xtb --version` recorded.

## 8. Success Metrics
- `AGENTS.md` required checks exit 0 in `.venv`. All four licence profiles exit 0 on the new
  lock.
- `docs/prd/v0.2.0/evidence/stack-cu129.json` shows v0.1.0's smoke passing on the new stack
  (slice 02).
- `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json` has `smoke.status == "pass"` and every
  `engines.<tag>` passing per §5 (slice 11). The README claim tested against it; version 0.2.0.
- `docs/prd/v0.2.0/DISCREPANCIES.md` complete; PD-006 `decided`.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.2.0.1 | slices/01-reference-and-test-policy | Unpack the v0.2.0 reference zip with its ruff gate file, seed the v0.2.0 discrepancy register, decide PD-006, and install the engine test policy (markers, acceptance envs, skip-to-fail switch, offline unit tests). |
| OPR.0.2.0.2 | slices/02-gpu-stack-cu129 | Move the GPU/MLIP stack to torch 2.13+cu129 and fairchem>=2.22 (TJ F1 A), re-run all four licence profiles with the gate edge cases fixed, and re-prove v0.1.0's GPU acceptance on the new stack under R49, recording which cuSOLVER loads. |
| OPR.0.2.0.3 | slices/03-potential-result | Add the strict, frozen PotentialResult core data contract (energy, forces, exactly-symmetric Cartesian Hessian in atomic units, identity, device, recovery record), and add the esen_omol25 engine tag (one tag per model family, R31). |
| OPR.0.2.0.4 | slices/04-engines-base | Create the eta_rxncat.engines node: Engine protocol, typed errors, CODATA-2018 units, keyed-option tables producing the resolved stage for the cache key, content-pinned model identity, FD Hessian, and a base-install no-heavy-import proof. |
| OPR.0.2.0.5 | slices/05-rdkit-ff | Implement the rdkit_ff engine: UFF/MMFF94 energies, analytic forces and FD Hessians for neutral closed-shell states only (charge 0, multiplicity 1; R35), with perception and round-trip checks, refusing everything else. |
| OPR.0.2.0.6 | slices/06-pyscf-cpu | Implement the PySCF engine's CPU path: keyed DF and auxbasis, the def2 ECP rule, explicit charge/spin RKS/UKS, ddCOSMO and C-PCM from a solvent table, the SCF escalation ladder with mandatory stability analysis, and analytic gradients/Hessians checked against FD. |
| OPR.0.2.0.7 | slices/07-pyscf-gpu | Add GPU4PySCF dispatch to the PySCF engine on one resolved stage: ADR-0008 budget read once, calibrated VRAM estimate, ddCOSMO on CPU, a listed-OOM single CPU fallback with pool cleanup, and GPU-CPU agreement with a cross-evaluation check. |
| OPR.0.2.0.8 | slices/08-xtb-subprocess | Provision the pinned xtb 6.8.0 binary outside the repo, start the licence inventory, and implement the xtb_subprocess engine: GFN2-xTB with explicit charge/spin and keyed ALPB in an isolated subprocess, with energy, gradient and a convention-checked Hessian. |
| OPR.0.2.0.9 | slices/09-mace | Implement the mace engine: MACE-MP-0 medium (MIT) from a sha256-verified local file, float64 energies/forces on CPU or CUDA with an FD Hessian, neutral closed-shell only, with no ase import in eta_rxncat. |
| OPR.0.2.0.10 | slices/10-uma-direct | Implement the fairchem engines on one clean-room bridge with honest per-family tags: uma_direct (uma-s-1p2p1) and esen_omol25 (OMol25 esen-sm-conserving-all-omol), explicit charge/spin, no ase in eta_rxncat, sha256-pinned identities, direct-force checkpoints refused; both proved on this host (UMA access open since 16:54Z). |
| OPR.0.2.0.11 | slices/11-acceptance | Run every engine's acceptance on this host in the three named envs with skips as failures, record it under R49 in docs/prd/v0.2.0/GPU_SMOKE_RESULT.json, and in the same commit bump the version to 0.2.0 and derive the README's v0.2.0 claims from that record. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
