---
id: OPR.0.2.0.2
slice: 02-gpu-stack-cu129
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Move the GPU/MLIP stack to torch 2.13+cu129 and fairchem>=2.22 (TJ F1 A), re-run all four licence profiles with the gate edge cases fixed, and re-prove v0.1.0's GPU acceptance on the new stack under R49, recording which cuSOLVER loads."
depends_on: [OPR.0.2.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [pyproject.toml, uv.lock, "tools/**", "tests/unit/tools/**", "docs/prd/v0.2.0/**", AGENTS.md, ".github/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, lock, "--check"], [uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/tools], [python3, "-c", "import json,sys;d=json.load(open('docs/prd/v0.2.0/evidence/stack-cu129.json'));s=d['smoke'];L=' '.join(str(v) for c in d['logs'].values() for v in c.values()).lower();sys.exit(0 if s['status']=='pass' and s['scf']['abs_diff_eh']<=1e-6 and s['scf']['mo_on_device'] and s['torch_op']['device']=='cuda' and '2.13.0' in d['hardware']['torch']['version'] and 'cu129' in d['hardware']['torch']['version'] and d['hardware']['flags']==[] and all(c['exit_code']==0 for c in d['commands']) and not any(k in L for k in ('no kernel image','no_binary_for_gpu','nokernelimagefordevice','ptx jit')) else 1)"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: GPU stack → torch 2.13+cu129 and fairchem ≥ 2.22, re-proved on this host

## Intent

Move the GPU and MLIP stack to torch 2.13 `+cu129` with `fairchem-core>=2.22`, so `uma-s-1p2p1`
is native (TJ F1 "A"). Re-run all four licence profiles on the new lock, and fix two licence-gate
edge cases. Re-prove v0.1.0's GPU acceptance on the new stack under R49's rules, recording which
cuSOLVER is actually mapped.

Context the builder needs (self-contained).

TJ, 16:24Z (row `qitem-20261122162111-26e232a707f003e2`), verbatim: "Q1. A". As restated by the
lead:
- move the GPU stack to torch 2.13 +cu129 with fairchem 2.22, for native `uma-s-1p2p1`;
- re-prove v0.1.0's GPU acceptance on the new stack under the same R49 rules (a real GPU run,
  GPU vs CPU agreement, device recorded, no fallback, no kernel-image/PTX-JIT error, full logs);
- check whether the CUDA 12.9 wheels still work with TJ's system `libcusolver11` (CUDA 12.4) and
  GPU4PySCF, and record which cuSOLVER actually loads (`/proc/self/maps`);
- any host change needing sudo goes to the operator first (via the lead), never improvised;
- the lock change must re-run all four licence profiles.

Resolve's scratch `uv lock` (index `pytorch-cu129`, `fairchem-core>=2.22`) exited 0 and resolved:
- torch 2.13.0+cu129 (every torch profile), triton 3.7.1;
- fairchem-core 2.26.0, mace-torch 0.3.17 (e3nn 0.4.4 / 0.6.0 per extra);
- gpu4pyscf-cuda12x 1.9.2, cupy-cuda12x 14.2.0, nvidia-cusolver-cu12 11.7.5.82.

Dropped: ray, ray-haproxy and their web stack. Added: `cuda-toolkit`, `cuda-bindings`,
`cuda-python`, `cuda-pathfinder`, `nvidia-cuda-nvdisasm`, `nvidia-cutlass-dsl*`,
`nvidia-nvshmem-cu12`, `warp-lang`, `nvalchemi-toolkit-ops`, `backoff`.

Current PyPI licence metadata:
- `cuda-bindings`, `cuda-python`, `cuda-pathfinder`, `nvalchemi-toolkit-ops`: Apache-2.0
  expression.
- `warp-lang`: field `Apache-2.0`. `backoff`: MIT.
- `nvidia-cutlass-dsl*`: Other/Proprietary.
- `nvidia-cuda-nvdisasm`: `LicenseRef-NVIDIA-Proprietary`.
- `cuda-toolkit` and `nvidia-nvshmem-cu12`: no licence metadata.

The locked versions are the authority. Re-check them with the gate.

The v0.1.0 gate is `tools/licence_gate.py` with `[tool.eta-rxncat.licence-gate]` (ADR-0013). It
has a single NVIDIA rule (`nvidia-` prefix plus a proprietary licence, in the gpu/MLIP profiles)
and version-pinned `exempt` tables (R48 / ADR-0014). Its two known edge cases:
- a dist-info with no `Name` is skipped;
- with several dist-infos for one name, the first wins.

v0.1.0's acceptance procedure is `missions/release-0.1.0/slices/07-gpu-acceptance/SPEC.md` (R46
preflight, R49 rule, record fields). Node `eta_rxncat_scaffold`.

## 1. The Confidence Mandate

**Score: 9/10.** The lock is proven to resolve. The residual is runtime behaviour of torch
2.13+cu129 on this host (system cuSOLVER 12.4 alongside wheel cuSOLVER 11.7.5). It is proved
here or stopped with output.

## Mini-requirements

1. `pyproject.toml`:
   - `[[tool.uv.index]]` `name = "pytorch-cu129"`, `url = "https://download.pytorch.org/whl/cu129"`,
     `explicit = true`;
   - `[tool.uv.sources] torch = [{ index = "pytorch-cu129" }]`;
   - `mlip-uma = ["torch>=2.7.0", "fairchem-core>=2.22"]`.
   
   No other dependency change. `uv lock` must give torch `2.13.*+cu129` and fairchem-core ≥ 2.22.
   A different outcome → stop and report with the output.
2. Licence gate, R27 edge cases in `tools/licence_gate.py`:
   - a dist-info without `Name` → FAIL `unnamed distribution at <path>`;
   - two dist-infos whose PEP 503-normalised names are equal → FAIL `ambiguous: <name> (<versions>)`.
   
   Add synthetic tests for both in `tests/unit/tools/`.
2b. Allowed list (replan R34, lead decision within TJ's 14:57Z policy). torch 2.13.0+cu129's
   `License-Expression` is `Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT`.
   Only `BSL-1.0` (Boost Software License 1.0, OSI/FSF-approved permissive, no copyleft) is off
   the list. Add it to `[tool.eta-rxncat.licence-gate] allowed`; the second line becomes exactly:
   `    "Apache-2.0", "ISC", "PSF-2.0", "Python-2.0", "Zlib", "CC0-1.0", "BSL-1.0",`
   It is an allowed licence, not a version-pinned exemption. Add a gate unit test, a synthetic
   dist-info, for each of: `BSL-1.0` passes; `Apache-2.0 AND BSL-1.0 AND MIT` passes;
   `LicenseRef-Unknown-1` still fails; `BSL-1.0 AND GPL-3.0-only` still fails.
3. Licence profiles: run all four (`base`, `gpu`, `mlip-mace`, `mlip-uma`) from `.venv-runtime`
   syncs.
   - Stale R48 entries (ray-haproxy, and anything else no longer locked) are removed; the
     stale-exemption rule forces this.
   - Versions of remaining entries follow the lock.
   - NVIDIA CUDA packages the NVIDIA rule does not cover (expected: `cuda-toolkit`,
     `nvidia-nvshmem-cu12`, `nvidia-cuda-nvdisasm` if its expression is unrecognised) get
     **version-pinned** `exempt` entries in the torch profiles, with reason "NVIDIA CUDA runtime
     wheel" and decision "TJ v0.1.0 Q1 A (NVIDIA CUDA wheels exempt); R1 v0.2.0".
   - Any other new failure: stop and report it to the lead with the gate output. Add no entry.
   - Record each profile's resolved download size (from `uv` output) in the handoff (R28).
4. Environments. Build `.venv-accept-gpu` (`UV_PROJECT_ENVIRONMENT=.venv-accept-gpu uv sync
   --locked --extra gpu`, dev group included). `.venv` stays base: run `uv sync --locked`
   afterwards and confirm no torch.
5. Stack re-proof, run by this seat in `.venv-accept-gpu` on a clean tree at HEAD (v0.1.0 slice
   07's procedure):
   - (1) preflight: `ldconfig -p | grep libcusolver.so`; `find_library('cusolver')`;
     `nvidia-smi --query-gpu=index,name,compute_cap --format=csv,noheader`;
   - (2) `eta-rxncat hardware-check`, expecting:
     - `torch.version` `2.13.0+cu129`;
     - `cuda_available` true;
     - CC `12.0`;
     - `vram_budget_bytes` 6979321856;
     - `flags []`.
   - (3) `eta-rxncat hardware-check --smoke` → exit 0, `status pass`;
   - (4) `pytest -m gpu -q`;
   - (5) the plain `pytest -q`.
   
   Then, as a seat command and not product code, a one-off Python run of the smoke's GPU4PySCF
   water SCF that dumps `/proc/self/maps` lines for `libcusolver`, `libcublas` and `libcudart`,
   plus `cusolverGetProperty`. Diagnostic script:
   `~/.hacf/eta-rxncat-hacf/evidence/cusolver-diag.py`, MODE=native, both import orders.
   
   Write `docs/prd/v0.2.0/evidence/stack-cu129.json` with:
   - `record_schema: 1`, `commit_sha`, `run_at_utc`;
   - `preflight`, `hardware`, `smoke`, `pytest_gpu`, `pytest_plain`;
   - `cusolver_mapped` (paths and version per import order);
   - `commands` (argv and exit code);
   - `logs` (full, untruncated stdout and stderr).
   
   R49 applies: |ΔE| ≤ 1e-6, MOs on device, torch device `cuda`, and no `no kernel image`,
   `NO_BINARY_FOR_GPU`, `NoKernelImageForDevice` or `PTX JIT` error anywhere in `logs`.
   
   On any failure, write the record with the output, do not commit it, and hand back. A host
   change needing sudo goes to the lead, for the operator.
6. Register rows in `docs/prd/v0.2.0/DISCREPANCIES.md`, each with status `open`:
   - `changed`: the torch index cu128 → cu129, and the fairchem floor (TJ F1 A);
   - `added`: the NVIDIA exempt entries, and the gate edge cases (R27).
7. `AGENTS.md` project section: the four licence-gate commands stay character-identical with
   `ci.yml`. Update only if the profile commands change; they should not.

## 3. Implementation Plan (Task List)

- [ ] Task 1: pyproject edits; `uv lock`; check versions (Mini-requirement 1).
- [ ] Task 2: gate edge cases plus tests (Mini-requirement 2).
- [ ] Task 3: the four profiles; update the exempt tables per Mini-requirement 3; stop on anything
  uncovered.
- [ ] Task 4: `.venv-accept-gpu`; re-proof; record (Mini-requirements 4–5).
- [ ] Task 5: register rows; four gates in `.venv` (base); `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** add any exempt entry outside Mini-requirement 3's two covered categories (NVIDIA CUDA
  runtime under v0.1.0 Q1 A; MLIP transitive under R48).
- **DO NOT** pin, downgrade or override packages to make the lock or a gate pass.
- **DO NOT** improvise a host change (apt, symlink, `LD_LIBRARY_PATH`). Report it.
- **DO NOT** put extras into `.venv`, or let product code read `/proc/self/maps`. That is a seat
  diagnostic only.
- **DO NOT** loosen a tolerance or retry until pass. A failure is a finding with output.
- **DO NOT** touch `src/eta_rxncat/` except where the gate tool lives (it is in `tools/`).

## Proof contract

- [ ] `uv lock --check` → 0. `uv.lock` has torch `2.13.0+cu129` from `pytorch-cu129` and
  fairchem-core ≥ 2.22.
- [ ] The allowed list contains `BSL-1.0`, with exactly the line given in Mini-requirement 2b. The four
  synthetic BSL tests pass as stated. torch 2.13.0+cu129 passes through `allowed`, not an exempt
  entry.
- [ ] Four licence profiles → exit 0 each (`base`, `gpu`, `mlip-mace`, `mlip-uma`, after the
  `BSL-1.0` change). Every new exempt entry is version-pinned and cites its
  decision. Removing one (shown once for `cuda-toolkit`) makes its profile fail.
- [ ] Gate synthetic tests: an unnamed dist-info → FAIL; a duplicate name → FAIL.
- [ ] `docs/prd/v0.2.0/evidence/stack-cu129.json`:
  - `smoke.status == "pass"`, `smoke.scf.abs_diff_eh <= 1e-6`, `smoke.scf.mo_on_device`,
    `smoke.torch_op.device == "cuda"`;
  - `hardware.torch.version` starts with `2.13.0` and contains `cu129`;
  - `hardware.flags == []`;
  - `cusolver_mapped` present for both orders;
  - every command exits 0;
  - no architecture-error string in `logs`;
  - `git merge-base --is-ancestor <commit_sha> HEAD`.
- [ ] `.venv` after `uv sync --locked`: `uv pip list` shows no torch, nvidia-* or cuda-*.
- [ ] The four gates in `.venv` → exit 0.

## Source material

- TJ 16:24Z (quoted above); mission R1, R27, R28; v0.1.0 R46/R49 and slice 07 SPEC; ADR-0010,
  ADR-0013, ADR-0014; `~/.hacf/eta-rxncat-hacf/cusolver-options.md`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.1 (test policy, `.gitignore` for acceptance envs, the v0.2.0 register)
