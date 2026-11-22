---
id: OPR.0.2.0.11
slice: 11-acceptance
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Run every engine's acceptance on this host in the three named envs with skips as failures, record it under R49 in docs/prd/v0.2.0/GPU_SMOKE_RESULT.json, and in the same commit bump the version to 0.2.0 and derive the README's v0.2.0 claims from that record."
depends_on: [OPR.0.2.0.5, OPR.0.2.0.7, OPR.0.2.0.8, OPR.0.2.0.9, OPR.0.2.0.10]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["tests/acceptance/**", docs/prd/v0.2.0/GPU_SMOKE_RESULT.json, docs/prd/v0.2.0/evidence/pyscf-gpu-support.json, "src/eta_rxncat/engines/pyscf_gpu_cpu/**", tests/unit/engines/test_gpu_hessian_record.py, pyproject.toml, uv.lock, src/eta_rxncat/__init__.py, tests/unit/test_package.py, README.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py, tests/unit/test_package.py], [python3, "-c", "import json,re,sys;d=json.load(open('docs/prd/v0.2.0/GPU_SMOKE_RESULT.json'));s=d['smoke'];L=' '.join(str(v) for c in d['logs'].values() for v in c.values()).lower();raw=json.dumps(d);ok=d['record_schema']==2 and s['status']=='pass' and s['scf']['abs_diff_eh']<=1e-6 and s['scf']['mo_on_device'] and s['torch_op']['device']=='cuda' and '2.13.0' in d['hardware']['torch']['version'] and d['hardware']['flags']==[] and all(c['exit_code']==0 for c in d['commands']) and isinstance(d['hf_token_present'],bool) and not re.search(r'hf_[A-Za-z0-9]{20,}',raw) and not any(k in L for k in ('no kernel image','no_binary_for_gpu','nokernelimagefordevice','ptx jit'));sys.exit(0 if ok else 1)"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.2.0 acceptance: every engine on this host, recorded; version 0.2.0; record-derived README

## Intent

The build seat runs every engine's acceptance on this host, GPU included, in the three named
acceptance envs with skips turned into failures. It records everything in
`docs/prd/v0.2.0/GPU_SMOKE_RESULT.json` under R49's rules. Then it bumps the version to 0.2.0 and
updates the README's v0.2.0 claims from that record, in one commit. v0.2.0 is accepted when this
slice audits PASS.

Context the builder needs (self-contained).

This is modelled on v0.1.0 slice 07 (R46 preflight; R49: a real GPU run, GPU vs CPU agreement,
device recorded, no silent fallback, no `no kernel image` / `NO_BINARY_FOR_GPU` /
`NoKernelImageForDevice` / `PTX JIT` error, full untruncated logs) and v0.1.0 slice 11 (the
README's GPU claim is derived from and tested against `docs/prd/v<version>/GPU_SMOKE_RESULT.json`,
with the version read from `pyproject.toml`).

Because the README checker is keyed by version, the record, the version bump and the README
update must land in the **same commit**.

TJ's rules:
- "Build, install, and run these autonomously as to move on to the next step/question."
- A failed GPU or engine run is a finding with output, never worked around.
- Q3: v0.2.0 is not accepted until the UMA run passes. The HF token is never recorded; only
  `hf_token_present`.

Environments (mission R8):
- `.venv-accept-gpu` (`--extra gpu`): RDKit, PySCF CPU/GPU, xtb, the v0.1.0 smoke.
- `.venv-accept-mace` (`--extra gpu --extra mlip-mace`).
- `.venv-accept-uma` (`--extra gpu --extra mlip-uma`): both fairchem engines, `uma_direct` and
  `esen_omol25` (R31).

Only this seat syncs them. The audit verifies the record and may re-run `uv run --no-sync`, never
`uv sync`.

The test set is mission §5 (`tests/unit/engines/data/`). Who runs what:
- UMA, eSEN (`esen_omol25`), xtb and PySCF run all four cases;
- RDKit and MACE run water plus refusal proofs.

UMA access is open (operator, 16:54Z: HTTP 302 for both `facebook/UMA` and `facebook/OMol25`
with TJ's login). The UMA run is required for acceptance (TJ Q3); eSEN is an addition, not a
substitute.

## 1. The Confidence Mandate

**Score: 9/10.** The commands, record and checks are fixed. The residuals are host facts, chiefly
TJ's UMA weights access. Without it this slice is a blocked finding (R23), never a pass.

## Mini-requirements

1. Preconditions:
   - slices 01–10 audited PASS;
   - `git status --porcelain` empty; record HEAD as `<sha>`;
   - the xtb binary provisioned (slice 08) and the MACE file present (slice 09);
   - UMA and eSEN weights present in the HF cache (route A, provisioned in slice 10). If either
     is absent or access fails, stop and report with the output and HTTP status, never the
     token.
1b. **Pre-run fix: GPU Hessian support record completeness** (R44; slice 07 audit note). Slice 07 is
   audited; this slice **touches its code** in `src/eta_rxncat/engines/pyscf_gpu_cpu/`, stated
   here, and this slice's audit judges the change.
   - (a) Measure and **add IEF-PCM rows** to `docs/prd/v0.2.0/evidence/pyscf-gpu-support.json`,
     using slice 07's method and schema: GPU4PySCF 1.9.2 analytic KS Hessian (grid response on)
     vs FD of GPU analytic gradients, step 0.005 Bohr, def2-SVP, B3LYP, DF.
     - Systems: water, HCl, HBr, HI (+def2 ECP).
     - Grids 3 and 9.
     - RKS, and UKS: the same closed-shell molecules run through UKS, plus the hydroxyl radical
       at multiplicity 2.

     The audit's probe (`~/.hacf/eta-rxncat-hacf/audit-evidence/probe207.py`) measured water
     B3LYP IEF-PCM at 6.3e-5 (C-PCM: 1.0e-5).
   - (b) **Record-driven routing.** `hessian_mode="auto"` may route a GPU KS Hessian to analytic
     only for a class `(scf_type RKS|UKS, solvation none|C-PCM|IEF-PCM, ecp yes|no, grids_level)`
     whose record rows are **present** and **all ≤1e-4 Eh/Bohr²**. Anything unrecorded or over the
     limit → FD of GPU analytic gradients. Derive the routing from the committed record (or a
     generated constant checked against it), not from a hand list.
   - (c) **Completeness test** (`tests/unit/engines/test_gpu_hessian_record.py`, default suite,
     no GPU):
     - for every class the `auto` rule can route to GPU analytic, the record has rows for it,
       all ≤1e-4;
     - a synthetic record missing the IEF-PCM class makes the router choose FD for IEF-PCM;
     - removing a recorded row makes the test fail.

   Commit (a)–(c) with the acceptance modules, before the run (Task 1).
2. `tests/acceptance/`, one module per engine (`test_accept_rdkit.py`, `test_accept_pyscf.py`,
   `test_accept_xtb.py`, `test_accept_mace.py`, `test_accept_uma.py`, `test_accept_esen.py`), each
   marked `acceptance` plus its piece markers:
   - each evaluates its cases at the slice-specified reference settings (PySCF: B3LYP/def2-SVP,
     DF, on **both** CPU and GPU) and asserts the engine slices' reference tolerances;
   - each writes one JSON per case to `$ETA_RXNCAT_ACCEPTANCE_OUT` (a temp dir outside the repo)
     with: `engine`, `case`, `energy_hartree`, `device`, `device_reason`, `recovery_steps`,
     `identity` (name, version, model), `reference_abs_diff`, `wall_time_s`;
   - refusal cases record `refused: true` and the error class.
3. Commands, run in order from the repo root, capturing argv, exit code, and full stdout/stderr:
   1. preflight: `ldconfig -p | grep libcusolver.so`;
      `uv run python -c "import ctypes.util; print(ctypes.util.find_library('cusolver'))"`;
      `nvidia-smi --query-gpu=index,name,compute_cap --format=csv,noheader`;
   2. `.venv-accept-gpu`: `eta-rxncat hardware-check`; `eta-rxncat hardware-check --smoke`;
      `pytest -m gpu -q -rs`; `pytest -q -rs` (plain; `-rs` prints each skip's node id and reason, R49);
   3. `.venv-accept-gpu`: `ETA_RXNCAT_ACCEPTANCE=1 ETA_RXNCAT_XTB=<path> pytest -m acceptance tests/acceptance/test_accept_rdkit.py tests/acceptance/test_accept_pyscf.py tests/acceptance/test_accept_xtb.py`;
   4. `.venv-accept-mace`: `ETA_RXNCAT_ACCEPTANCE=1 pytest -m acceptance tests/acceptance/test_accept_mace.py`;
   5. `.venv-accept-uma`: `ETA_RXNCAT_ACCEPTANCE=1 pytest -m acceptance tests/acceptance/test_accept_uma.py tests/acceptance/test_accept_esen.py`.
   6. HF access, header-only via `huggingface_hub` (which reads TJ's token file itself), recording
      **only** the HTTP status per file: `facebook/UMA` `checkpoints/uma-s-1p2p1.pt` and
      `facebook/OMol25` `checkpoints/esen_sm_conserving_all.pt`. Never print or capture request
      headers.
   
   All use `UV_PROJECT_ENVIRONMENT=<env> uv run --no-sync …`, after the seat's own `uv sync
   --locked --extra …` for each env.
4. Record `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`, 2-space indent:
   - `record_schema: 2`, `commit_sha: <sha>`, `run_at_utc`;
   - `preflight`, `hardware` (command 2's report), `smoke` (command 2's `SmokeResult`);
   - `pytest_gpu`, `pytest_plain`;
   - `engines` (from the per-case JSONs, keyed `<tag>.<case>`);
   - `commands` (argv and exit code);
   - `logs` (full, untruncated per command);
   - `hf_token_present: bool`, and `hf_access` (`{"facebook/UMA": <status>, "facebook/OMol25": <status>}`);
   - the UMA and eSEN checkpoint names, sizes and sha256s;
   - `known_limits` (R44), a list of plain statements, at least:
     - "R43 CPU-copy stability follow branch is exercised only by fakes (no real n_rotations<3 unstable case)";
     - "GPU Hessian memory is not covered by the VRAM estimate (calibrated for SCF + gradient); a GPU Hessian over budget relies on the listed-OOM CPU fallback (R10)".
     - "plain suite in .venv-accept-gpu has exactly one by-design skip: tests/unit/cli/test_cli.py::test_console_script_smoke_skipped (torch is installed in this environment; the real skip path cannot be observed)" (R49).
   
   No token, no token path content, no secrets.
5. In the same commit:
   - version 0.1.0 → 0.2.0 in `pyproject.toml`, `src/eta_rxncat/__init__.py` and the
     `tests/unit/test_package.py` assertion;
   - README: the Features section gains an "Engines (v0.2.0)" bullet set describing exactly what
     slices 03–10 built (the five engines, units, refusal rule, keyed resolved stage);
   - the GPU-acceptance clause is restated from the v0.2.0 record via slice 11's
     `check_gpu_claim` vocabulary (`GPU acceptance passed`, the GPU name, a link to
     `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`);
   - claim nothing the record does not show;
   - `uv lock` only if the version bump requires it (`uv lock --check` must pass).
6. On any failure (a non-zero exit, a failed check in Mini-requirement 7, a blocked UMA): write
   the record with the failing output, commit **nothing**, and hand back with the output. The
   failure is the finding.

## 3. Implementation Plan (Task List)

- [ ] Task 1: preconditions; the R44 pre-run fix (Mini-requirement 1b) and the acceptance modules
  (Mini-requirement 2), committed **before** the run as their own commit, so the run's `<sha>`
  includes them.
- [ ] Task 2: sync the three envs; run commands 1–5; assemble the record (Mini-requirements 3–4).
- [ ] Task 3: the version bump and README (Mini-requirement 5); four gates in `.venv`; commit the
  record, version and README together.
- [ ] Task 4: restore `.venv` with `uv sync --locked`; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** run acceptance in `.venv`, skip a case, loosen a tolerance, rerun until pass,
  substitute CPU for GPU, or edit outputs.
- **DO NOT** record any token or secret.
- **DO NOT** commit the record without the version bump and README update, or vice versa.
- **DO NOT** change engine code here, except Mini-requirement 1b's record-driven Hessian routing in
  `engines/pyscf_gpu_cpu` (R44). Any other defect found here is a finding for a replan.
- **DO NOT** push.

## Proof contract

- [ ] The record parses, `record_schema == 2`, and:
  - `smoke.status == "pass"`, `smoke.scf.abs_diff_eh <= 1e-6`, `smoke.scf.mo_on_device`,
    `smoke.torch_op.device == "cuda"`;
  - `hardware.torch.version` contains `2.13.0` and `cu129`; `hardware.flags == []`;
  - `preflight.find_library_cusolver` is not null; `nvidia_smi_gpus` names the RTX 5060 Ti, CC
    12.0.
- [ ] `engines` has every `<tag>.<case>` required by the test set:
  - rdkit_ff and mace: water plus three refusals;
  - pyscf_gpu_cpu (CPU and GPU), xtb_subprocess, uma_direct and esen_omol25: four cases each.
  
  Every non-refusal entry has `reference_abs_diff` within its engine's tolerance. PySCF GPU
  entries have `device == "cuda"` and GPU−CPU ≤1e-6 Eh. Every refusal has `refused: true`,
  `EngineInputError`.
- [ ] Every `commands[*].exit_code == 0`. Skip and error scans (this mission's R49):
  - a case-insensitive scan of **all** `logs` finds none of the **v0.1.0 R49** architecture-error strings
    (`no kernel image`, `NO_BINARY_FOR_GPU`, `NoKernelImageForDevice`, `PTX JIT`);
  - acceptance commands 3–5 (run under `ETA_RXNCAT_ACCEPTANCE=1`) and command 2's
    `pytest -m gpu`: **zero** skips (no `skipped` in their logs);
  - command 2's plain `pytest -q -rs`: **exactly one** skip, the node id
    `tests/unit/cli/test_cli.py::test_console_script_smoke_skipped` with reason "`torch is installed in this environment; the real skip path cannot be observed`". Its summary line shows `1 skipped`. Any other or
    additional skip fails this proof;
  - `known_limits` names that node id.

  Also: `hf_token_present` is a bool, `hf_access` holds
  only integer status codes, and no string in the record matches `hf_[A-Za-z0-9]{20,}`.
- [ ] R44:
  - `pyscf-gpu-support.json` has IEF-PCM rows for water, HCl, HBr and HI+ECP at grids 3 and 9,
    RKS and UKS, plus hydroxyl UKS;
  - `tests/unit/engines/test_gpu_hessian_record.py` passes, and its synthetic missing-class case
    routes IEF-PCM to FD;
  - in the acceptance run, any IEF-PCM GPU KS Hessian's `hessian_method` matches the record's
    verdict for its class;
  - the record's `known_limits` contains both R44 statements.
- [ ] `git merge-base --is-ancestor <commit_sha> HEAD`. The final commit changes exactly the
  record, the version files and the README.
- [ ] `uv run pytest tests/unit/test_identity.py tests/unit/test_package.py` → exit 0 (the README
  claim matches the v0.2.0 record; the version is 0.2.0). The four gates → exit 0.

## Source material

- Mission §5 (Acceptance record, Test set, Environments), R8, R23; v0.1.0 slices 07 and 11
  (R46, R49, R54); TJ's autonomy rule and Q3.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.5, OPR.0.2.0.7, OPR.0.2.0.8, OPR.0.2.0.9, OPR.0.2.0.10 (every engine; transitively all slices)
