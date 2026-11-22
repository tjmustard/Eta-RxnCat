---
id: OPR.0.1.0.7
slice: 07-gpu-acceptance
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Run the GPU smoke and gpu-marked tests once on a clean tree on this host's RTX 5060 Ti and commit docs/prd/v0.1.0/GPU_SMOKE_RESULT.json with the commit sha, as v0.1.0's acceptance gate."
depends_on: [OPR.0.1.0.1, OPR.0.1.0.2, OPR.0.1.0.3, OPR.0.1.0.4, OPR.0.1.0.5, OPR.0.1.0.6, OPR.0.1.0.8, OPR.0.1.0.9]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [docs/prd/v0.1.0/GPU_SMOKE_RESULT.json]
hacf_oracle: [[python3, "-c", "import json,sys;d=json.load(open('docs/prd/v0.1.0/GPU_SMOKE_RESULT.json'));s=d['smoke'];L=' '.join(str(v) for c in d['logs'].values() for v in c.values()).lower();sys.exit(0 if d['record_schema']==1 and s['status']=='pass' and not any(k in L for k in ('no kernel image','no_binary_for_gpu','nokernelimagefordevice','ptx jit')) and s['scf']['abs_diff_eh']<=1e-6 and s['scf']['mo_on_device'] and s['torch_op']['device']=='cuda' and s['torch_op']['max_abs_diff']<=1e-9 and d['hardware']['vram_budget_bytes']==6979321856 and all(c['exit_code']==0 for c in d['commands']) else 1)"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: GPU acceptance run on this host

## Intent

Have the build seat run the GPU smoke test and the `gpu`-marked tests once, on a clean tree at
HEAD, on this host's RTX 5060 Ti. The seat records the result with the commit sha in
`docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`. Audit verifies the file. v0.1.0 is accepted when this
slice audits PASS.

Context the builder needs (self-contained). TJ, Q3 (07:52Z): "Build, install, and run these
autonomously as to move on to the next step/question". The team runs the GPU gate on this host.
The red team's F11 called for one seat and one point: the build/execute seat runs it, here, after
slices 01–06, 08 and 09 have audited PASS. The audit seat checks the recorded file and does not run `uv sync`.

The run uses code that already exists:
- `eta-rxncat hardware-check [--smoke]` (slice 05), which wraps `probe_hardware()` /
  `run_smoke()` (slice 04);
- `tests/gpu/test_smoke.py` (slice 04, marker `gpu`);
- the `gpu` extra (slice 06).

Pass means all of these hold:
- both RHF/STO-3G H₂O SCFs converge, on GPU4PySCF and on CPU PySCF;
- |ΔE| ≤ 1e-6 Eh;
- the GPU MO coefficients are a CuPy array;
- a float64 CUDA matmul lands on a `cuda` device with max-abs-diff ≤ 1e-9;
- all of this finishes within 600 s.

Product code never calls `git`, so the seat stamps the sha itself. Node `eta_rxncat_scaffold`
owns `docs/**`, so the graph needs no change.

## 1. The Confidence Mandate

**Score: 9/10.** The commands, pass criterion, file shape and audit check are fixed. The residual
is this host's driver, CUDA and wheel state, which only the run itself can show. By TJ's design
(Q3) a failure blocks acceptance and is reported, with no workaround.

## Mini-requirements

1. Preconditions:
   - Slices 01–06, 08 and 09 have audited PASS.
   - **R46 = A (TJ, 14:49Z):** TJ installs NVIDIA cuSOLVER system-wide himself. The plan is
     Ubuntu's `libcusolver11` (11.6.1, CUDA 12.4), with NVIDIA's ubuntu2404 `libcusolver-12-8`
     11.7.3.90 as fallback. This slice does not start until the operator confirms that install
     to the lead.
   - The first check here, before command 1, uses the base dev env:
     - `ldconfig -p | grep libcusolver.so` shows a system path;
     - `uv run python -c "import ctypes.util; print(ctypes.util.find_library('cusolver'))"` prints
       a non-`None` name.
     
     Record both outputs in the result file under `preflight`. If either fails, stop and report
     it.
   - **No product shim:** nothing in `eta_rxncat` redirects `find_library`, preloads libraries,
     or sets `LD_LIBRARY_PATH`. If `import gpu4pyscf` still fails, or the smoke fails (for example
     on a cuSOLVER/CUDA minor-version mismatch), that is a finding with output (TJ, 07:52Z). `git status --porcelain` is empty. Record HEAD
   as `<sha>` before anything runs.
2. Run, in order, from the repo root, capturing stdout, stderr and exit codes:
   1. `uv sync --locked --extra gpu`
   2. `uv run eta-rxncat hardware-check`. Expect `torch.installed true`, `cuda_available true`,
      `gpu.compute_capability "12.0"`, `vram_budget_bytes 6979321856` and `flags []`.
   3. `uv run eta-rxncat hardware-check --smoke`. Expect exit 0 and `status "pass"`.
   4. `uv run pytest -m gpu -q`. Expect exit 0 and at least 1 passed.
   5. `uv run pytest -q`, the plain suite with the gpu extra installed (R44). Expect exit 0.
   
   If command 2 shows `torch_import_failed` or `gpu4pyscf_import_failed` (R43), or any command
   exits non-zero, stop. Write the record with the failing output and hand it to the lead under
   rule 4. Do not reinstall packages, change the index, or retry to get a pass.
3. Write `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` with these fields:
   - `record_schema: 1`
   - `commit_sha: <sha>`
   - `run_at_utc` (ISO-8601 Z)
   - `commands`: the five argv lists, each with its exit code
   - `hardware`: the parsed stdout of command 2
   - `smoke`: the parsed stdout of command 3
   - `pytest_gpu`: `{exit_code, summary_line}`
   - `pytest_plain`: `{exit_code, summary_line}` (command 5)
   - `preflight`: `{ldconfig_cusolver, find_library_cusolver, nvidia_smi_gpus}` (R46). The
     last is the output of `nvidia-smi --query-gpu=index,name,compute_cap --format=csv,noheader`,
     run by the seat, not by product code.
   - `logs`: for each of commands 1–5, the complete `stdout` and `stderr` text, unedited and
     untruncated (R49: hide nothing).
   
   Write it with 2-space indent and a trailing newline. Commit it alone, in one commit whose
   parent is `<sha>`.
4. On any non-zero exit or any non-pass status: write the same file with the failing output, do
   not commit, and hand back to the lead with the output. The failure is the finding.
   **Operator's acceptance rule (R49).** The run counts only as a real GPU run, proven by:
   - GPU and CPU SCF energies agreeing within 1e-6 Eh;
   - the device actually used being recorded: `smoke.torch_op.device == "cuda"`,
     `smoke.scf.mo_on_device` true, and `preflight.nvidia_smi_gpus` showing the single RTX 5060
     Ti, compute capability 12.0;
   - no silent CPU fallback anywhere;
   - no architecture error: none of `no kernel image`, `CUDA_ERROR_NO_BINARY_FOR_GPU`,
     `cudaErrorNoKernelImageForDevice`, `NO_BINARY_FOR_GPU` or `PTX JIT` (as an error) in any
     `logs` text.
   
   An architecture failure is a finding. Hand it back to the lead with the full output, and the
   lead reports it to the operator. Never retry around it.
5. Run command 1 in the default dev env (`.venv`). Afterwards, return to the base dev env with
   `uv sync --locked`, so later seats see the slice-01 environment.

## 3. Implementation Plan (Task List)

- [ ] Task 1: check the preconditions and record `<sha>`.
- [ ] Task 2: run the four commands and keep their raw outputs.
- [ ] Task 3: assemble the JSON with a short throwaway Python one-liner. Do not add product code.
- [ ] Task 4: commit the one file with the project footer. Restore the base env.

## 4. The Negative Space (Constraints)

- **DO NOT** run on a dirty tree, or before slices 01–06, 08 and 09 have audited PASS.
- **DO NOT** loosen any tolerance, rerun until it passes, edit outputs by hand, or substitute CPU
  for GPU.
- **DO NOT** change any file other than `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`.
- **DO NOT** install the MLIP extras for this run.
- **DO NOT** push.

## Proof contract

- [ ] `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` exists and parses, with `record_schema == 1` and
  `smoke.status == "pass"`.
- [ ] `smoke.scf.abs_diff_eh <= 1e-6`, `smoke.scf.mo_on_device` true, `smoke.torch_op.device ==
  "cuda"`, `smoke.torch_op.max_abs_diff <= 1e-9` and `smoke.total_seconds <= smoke.timeout_s`.
- [ ] R49: `logs` has untruncated `stdout`/`stderr` for commands 1–5. A case-insensitive search
  of all `logs` text for `no kernel image`, `NO_BINARY_FOR_GPU`, `NoKernelImageForDevice` and
  `PTX JIT` finds nothing. `preflight.nvidia_smi_gpus` names exactly one GPU, the RTX 5060 Ti with
  compute capability 12.0. `preflight.find_library_cusolver` is non-`null`.
- [ ] `hardware.gpu.compute_capability == "12.0"`, `hardware.vram_budget_bytes == 6979321856` and
  `hardware.flags == []`.
- [ ] Every `commands[*].exit_code == 0` (five commands), `pytest_gpu.summary_line` reports ≥ 1
  passed and 0 failed, and `pytest_plain.exit_code == 0`. `hardware.flags` contains no
  `*_import_failed`.
- [ ] `git merge-base --is-ancestor <commit_sha> HEAD` → exit 0. The commit that adds the file
  changes only that file.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (v0.1.0 PR #2; Hardware Constraint).
- Mission `missions/release-0.1.0/SPEC.md` §5 Contracts (GPU smoke), trade-off log R10, R11, R26;
  US-004b.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.1, OPR.0.1.0.2, OPR.0.1.0.3, OPR.0.1.0.4, OPR.0.1.0.5, OPR.0.1.0.6, OPR.0.1.0.8 (all audited PASS; 08 added by replan R37, 09 by R42, so acceptance stays last)
