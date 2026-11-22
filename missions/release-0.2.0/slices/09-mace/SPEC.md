---
id: OPR.0.2.0.9
slice: 09-mace
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the mace engine: MACE-MP-0 medium (MIT) from a sha256-verified local file, float64 energies/forces on CPU or CUDA with an FD Hessian, neutral closed-shell only, with no ase import in eta_rxncat."
depends_on: [OPR.0.2.0.4, OPR.0.2.0.5, OPR.0.2.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", tests/unit/test_test_policy.py, docs/licence-inventory.md, docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [env, "UV_PROJECT_ENVIRONMENT=.venv-accept-mace", "ETA_RXNCAT_ACCEPTANCE=1", uv, run, "--no-sync", pytest, "-m", mlip_mace, tests/unit/engines/test_mace.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: MACE engine (`mace`), MACE-MP-0 medium, content-pinned, no ASE in eta_rxncat

## Intent

Implement `MACEEngine` (tag `mace`). It gives MACE-MP-0 "medium" energies and forces on CPU or
CUDA in float64, from a locally provisioned, sha256-verified weights file, with an FD Hessian. It
accepts neutral closed-shell states only and refuses the rest.

Context the builder needs (self-contained).

TJ v0.2.0 Q2 "A": MACE-MP-0 accepts charge 0 and multiplicity 1 only; anything else raises
`EngineInputError` naming the engine, charge and multiplicity.

TJ licence policy: engines may depend on copyleft code, but `src/eta_rxncat/` never imports `ase`
(AST ban); MACE's own library loading `ase` in-process is allowed (14:59Z; mission R11). So the
engine calls MACE's model and data code directly, without `ase`. Tests may use MACE's
`MACECalculator` plus `ase.Atoms` as the reference, because the ban covers `src/` only.

Resolve found (R5):
- `mace_mp(model="medium")` = `https://github.com/ACEsuit/mace-mp/releases/download/mace_mp_0/2023-12-03-mace-128-L1_epoch-199.model`,
  44,422,970 B, sha256 `01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845`;
  MIT per the `ACEsuit/mace-mp` README licence column (MPA-0 is MIT; OMAT/OMOL/MH are ASL);
- `mace_mp(model=None)` now resolves to `medium-mpa-0`, a different model, so the name is always
  explicit.

The stack is torch 2.13+cu129 (slice 02), with mace-torch 0.3.17 and e3nn 0.4.4 in `mlip-mace`.
Whether e3nn 0.4.4 runs under torch 2.13 is unproven: prove it here or stop with output.

The env is `.venv-accept-mace` (`UV_PROJECT_ENVIRONMENT=.venv-accept-mace uv sync --locked --extra
gpu --extra mlip-mace`), created by this seat.

## 1. The Confidence Mandate

**Score: 8/10.** The API, refusal rules, pin and tolerance are fixed. The residuals are e3nn
0.4.4 under torch 2.13 (a runtime fact) and MACE's internal data API without `ase`. Either can
stop the slice with output.

## Mini-requirements

1. Provisioning (seat command, recorded):
   - `curl -fL <URL> -o ~/.cache/eta-rxncat/mace/2023-12-03-mace-128-L1_epoch-199.model`;
   - verify the sha256;
   - add a `docs/licence-inventory.md` entry: MACE-MP-0 medium, MIT, URL, sha256, size.
2. `engines/mace.py`, `MACEEngine(Engine)`, `ENGINE_IMPL = 1`:
   - `method` must be `mace-mp-0-medium`;
   - keyed: `dtype` (`float64` only), `fd_step_bohr` (0.005), `engine_impl` (1);
   - runtime: `model_path` (required; there is no default and no download), `device`
     (`auto`|`cpu`|`cuda`).
   - At construction:
     - compute `sha256_file(model_path)`;
     - compare it with `EXPECTED_SHA256 = {"mace-mp-0-medium": "01bfe221…35845"}`; a mismatch →
       `EngineInputError`;
     - **only then** load the model with torch;
     - convert to float64;
     - move to the device.
   - `identity = EngineIdentity(name="mace", version=library_version("mace-torch"), model="mace-mp-0-medium@sha256:01bfe221…")`.
3. Evaluate:
   - refuse charge ≠ 0 or multiplicity ≠ 1 (`EngineInputError`);
   - build the model input with MACE's own `mace.data` and `mace.tools` utilities from symbols
     and positions (Å), with no `ase` import in `src/`;
   - energy eV → Eh; forces eV/Å → Eh/Bohr (units module);
   - Hessian = `fd_hessian` on the engine's forces, `finite_difference`;
   - `device` = `"cuda"` or `"cpu"`; `auto` → cuda if available.
   - torch, mace and e3nn are imported inside the engine only.
4. Register rows (status `open`) vs the starter: `mace_mp` usage replaced by the direct model;
   name `mace_medium` → the tag plus content id; float64; refusal.

## 3. Implementation Plan (Task List)

- [ ] Task 1: `.venv-accept-mace`, provisioning, the inventory entry.
- [ ] Task 2: the engine (Mini-requirements 2–3).
- [ ] Task 3: tests in `tests/unit/engines/test_mace.py`, marked `mlip_mace` (CPU and CUDA cases;
  CUDA also marked `gpu`). Plus default-suite tests (no torch needed) for refusal before load,
  the sha mismatch, and the missing `model_path`.
- [ ] Task 4: register rows; four gates in `.venv`; the marked tests in `.venv-accept-mace`.

## 4. The Negative Space (Constraints)

- **DO NOT** import `ase` in `src/eta_rxncat/`, or call `mace_mp()` / any downloading helper.
- **DO NOT** load a weights file before its sha256 matches the pin.
- **DO NOT** accept charged or open-shell states.
- **DO NOT** pin or patch e3nn or torch to make it run. A runtime incompatibility is a finding
  with output.

## Proof contract

- [ ] `mlip_mace` (CPU and CUDA), water:
  - energy equals `MACECalculator(model_paths=<path>, default_dtype="float64", device=…)` on the
    same `ase.Atoms` in the test, converted with `engines.units`, ≤1e-6 eV;
  - forces ≤1e-6 eV/Å;
  - forces vs central FD of the engine energy (step 1e-4 Å) ≤1e-4 Eh/Bohr;
  - `device` matches the request.
- [ ] Refusals: hydroxide, hydronium and hydroxyl → `EngineInputError` naming `mace`, the charge
  and the multiplicity, raised **before** any model call (a monkeypatched model that would fail
  is never called).
- [ ] A sha-mismatched file → `EngineInputError`, and torch load is not called. A missing
  `model_path` → `EngineUnavailableError` naming the provisioning step.
- [ ] `identity.model == "mace-mp-0-medium@sha256:01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845"`.
- [ ] The AST ban passes, so there is no `ase` in `src/`. The base-install no-heavy-import test
  prints `[]`.
- [ ] The four gates in `.venv` → exit 0.
  `UV_PROJECT_ENVIRONMENT=.venv-accept-mace ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m mlip_mace tests/unit/engines/test_mace.py`
  → exit 0, with 0 skipped.

## Source material

- Plan PR #5; TJ Q2 A and the licence policy; mission R4, R5, R11, R15, R19; ADR-0017 (PROPOSED);
  the starter `mlip.py` (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base), OPR.0.2.0.5 (test data), OPR.0.2.0.2 (the cu129 stack)
