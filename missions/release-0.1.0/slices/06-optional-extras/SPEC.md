---
id: OPR.0.1.0.6
slice: 06-optional-extras
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Declare the gpu, mlip-mace and mlip-uma optional extras (MLIP extras conflicting) with torch from the PyTorch cu128 index, and a per-extra licence gate that exempts only NVIDIA CUDA wheels and the MLIP extras' transitive LGPL packages, per TJ's Q1 A / Q2 A."
depends_on: [OPR.0.1.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [pyproject.toml, uv.lock, AGENTS.md, ".github/**", ".gitignore", tests/unit/test_package.py, src/eta_rxncat/utils/hw_probe.py, "tests/unit/utils/**", "tests/unit/cli/**", docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, lock, "--check"], [uv, sync, "--locked"], [uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Optional GPU and MLIP extras with a per-extra licence gate

## Intent

Declare the optional extras `gpu`, `mlip-mace` and `mlip-uma` in `pyproject.toml`, with the two MLIP
extras declared as conflicting so `uv lock` resolves both. Pull torch from the PyTorch CUDA-12.8
index. Extend the licence gate to run once per extra under TJ's policy. Keep the four gates passing
both with and without the extras installed.

Context the builder needs (self-contained). TJ decided F1/F2 (08:19Z, verbatim: "Q1 A, Q2 A"):
- **Q1 A:** LGPL packages are allowed **only** as transitive dependencies of the optional MLIP
  extras. They never enter the core install, are never vendored, and `eta_rxncat` code never
  imports `ase` or `matscipy`. NVIDIA CUDA runtime wheels are exempt. The CI licence check runs per
  extra.
- **Q2 A:** `mlip-mace` and `mlip-uma` are separate, mutually exclusive extras, declared
  conflicting so uv locks both. One environment uses one MLIP at a time. Today `mace-torch` pins
  `e3nn==0.4.4` while `fairchem-core` needs `e3nn>=0.5`, which is why the starter's single `mlip`
  extra cannot lock.

The plan sets the CUDA line: PyTorch `>=2.7.0+cu128` (`sm_120`, RTX 5060 Ti) and GPU4PySCF
`1.8.0+`. Slice 01 built the base install, the four gates and the runtime-only licence gate, and
forbade exceptions. This slice adds the exceptions TJ authorised, and only those. No product code
in this slice imports torch, MACE or fairchem; engines arrive in later versions. Node
`eta_rxncat_scaffold` already exists (slice 01). Refresh it with `hyper_ledger.py ensure-node
--from-spec <slice 01 SPEC.md> --dimension Module` only if your files fall outside its `files:`.
Do not hand-edit `architecture.yml`.

## 1. The Confidence Mandate

**Score: 9/10.** TJ settled the policy, and the extras, conflicts, index and gate shape are fixed.
One residual is a host fact that `uv lock` answers, not a judgement call: whether current
`mace-torch` and `fairchem-core` releases each resolve against a cu128 torch. If either does not,
stop and report it to the lead with the `uv lock` output. Do not weaken a pin silently, and do not
drop an extra.

## Mini-requirements

1. `[project.optional-dependencies]`:
   - `gpu = ["torch>=2.7.0", "gpu4pyscf-cuda12x>=1.8.0", "cupy-cuda12x"]`
   - `mlip-mace = ["torch>=2.7.0", "mace-torch"]`
   - `mlip-uma = ["torch>=2.7.0", "fairchem-core"]`
   
   Use version floors only. Record any pin you find necessary as a register row with the reason.
   No other extra exists, and the starter's single `mlip` extra is not recreated.
2. `[tool.uv] conflicts = [[{ extra = "mlip-mace" }, { extra = "mlip-uma" }]]`. Add torch from an
   explicit index:
   - `[[tool.uv.index]] name = "pytorch-cu128"`, `url = "https://download.pytorch.org/whl/cu128"`,
     `explicit = true`;
   - `[tool.uv.sources] torch = [{ index = "pytorch-cu128" }]`.
   
   `uv lock` exits 0, and the committed `uv.lock` contains both MLIP extras. The base `uv sync
   --locked` (no extras) installs no torch, CUDA, MACE, fairchem, `ase` or `matscipy` package.
3. The supported combinations sync from the lock:
   - `uv sync --locked --extra gpu`
   - `uv sync --locked --extra gpu --extra mlip-mace`
   - `uv sync --locked --extra gpu --extra mlip-uma`
   
   These are the combinations to check. `--extra mlip-mace --extra mlip-uma` is rejected by uv.
   Torch wheels from the cu128 index install without a GPU, so the syncs run on a CPU CI runner.
4. The per-extra licence gate (US-002a extended, Q1 A). It is one command per environment, written
   identically in `ci.yml` and in the `AGENTS.md` project section:
   - `base` (no extras): unchanged from slice 01, with no exemptions.
   - `gpu`: the slice-01 allow-list, plus `--ignore-packages` naming exactly the NVIDIA CUDA
     runtime packages (`nvidia-*`) that the lock resolves for that extra.
   - `mlip-mace`, `mlip-uma` (each together with `gpu`): the same NVIDIA exemption, plus exactly
     the LGPL packages that the lock resolves for that extra (expected `ase` and `matscipy` for
     MACE and `ase` for UMA; the lock is the authority).
   
   Each exemption list is written out literally. Wildcards are not allowed unless `pip-licenses`
   accepts them and you verify that the expansion matches the list. `AGENTS.md` states why each
   package is exempt (TJ Q1 A, row `qitem-20261122075815-4c32a48f2e42363c`).
   A CLI `--ignore-packages` **replaces** the `[tool.pip-licenses]` list from slice 01; it does not
   extend it (verified with pip-licenses 5.5.5). So every per-extra list also contains
   `geometric:1.1.1` (R41, ADR-0011). The `base` gate passes no `--ignore-packages` and uses the
   config unchanged.
5. Exemption guard: `tests/unit/test_package.py` gains:
   - (a) an AST scan of every `.py` under `src/eta_rxncat/` that fails on any `import`/`from`
     of `ase`, `matscipy`, `sella`, `tblite` or `psi4`, and names the file and line;
   - (b) a test that reads `pyproject.toml`'s `[project.dependencies]` and every extra, and fails
     if `ase` or `matscipy` is declared **directly** anywhere.
6. mypy (R13) passes in the dev environment with `--extra gpu --extra mlip-mace` installed, and
   with `--extra gpu --extra mlip-uma` installed. The slice-01 overrides stay unchanged. Add
   `mace.*` and `fairchem.*` to the override list only if mypy needs them, and add a register row
   if you do.
7. CI: `ci.yml` keeps the base job unchanged. It gains a `licence-extras` job with a matrix over
   `gpu`, `gpu+mlip-mace` and `gpu+mlip-uma`. Each job runs `uv sync --locked --no-dev` with
   those extras into a runtime env, then that extra's gate command. There is no GPU job.
8. US-011 (scaffold area): `docs/prd/v0.1.0/DISCREPANCIES.md` gains:
   - a `changed` row: starter `mlip` extra → `mlip-mace` / `mlip-uma` conflicting (F1, TJ Q2 A);
   - a `changed` row: starter licence policy → per-extra exemptions (F2, TJ Q1 A);
   - `added` rows for the `gpu` extra, the torch index and the `licence-extras` CI job.
   
   Status of each row: `open`.
9. Replan R43, slice-04 audit note 1 (row `qitem-20261122132935-9169e7c0`): report a broken torch
   or GPU4PySCF install; never raise. This slice is the first to install a real torch.
   Today, if `torch` is installed but importing it raises something other than `ImportError`
   (e.g. `OSError: libcudart.so.12: cannot open shared object file`), `probe_hardware()` and
   `run_smoke()` raise. Change `src/eta_rxncat/utils/hw_probe.py` so that:
   - The torch import catches `Exception` (not `BaseException`). When the distribution is present
     (`importlib.metadata.version("torch")` succeeds) but the import raised, the report has:
     - `torch.installed = true`, `torch.version` = the metadata version;
     - `cuda_available = false`, `cuda_version = null`, `gpu = null`, `vram_budget_bytes = null`;
     - a new flag `torch_import_failed`;
     - a note `Importing torch raised <ExceptionType>: <message>`.
   - GPU4PySCF follows the same rule, with flag `gpu4pyscf_import_failed` instead of
     `gpu4pyscf_missing`. Its note already exists.
   - Fixed flag order: `torch_missing`, `torch_import_failed`, `cuda_unavailable`,
     `torch_cuda_below_12.8`, `gpu4pyscf_missing`, `gpu4pyscf_import_failed`,
     `gpu4pyscf_below_1.8.0`. `report_schema` stays 1 (only a new flag value is added).
   - `run_smoke()`: when either `*_import_failed` flag is set, the result is **`fail`** (exit 1),
     not `skipped`. The reason names the package and the exception, and no child process starts.
     `skipped` (exit 3) keeps meaning "not installed / no CUDA". A broken install on the
     acceptance host must surface as a failure with its output (TJ, 07:52Z), never be mistaken for
     an absent package.
   - No retry, reinstall or fallback logic. This is reporting only.
10. Replan R44, slice-04 audit note 2: the plain suite does not depend on the environment.
    `uv run pytest` must exit 0 both in the base dev env (no extras) and with `--extra gpu`
    installed. Convert every test under `tests/unit/` that assumes torch, CUDA or GPU4PySCF is
    absent to a fake host, by monkeypatching the module's import seam (`hw_probe._import` or
    equivalent) so that the package reads as absent. Known cases:
    - `tests/unit/utils/test_utils_smoke.py::test_skipped_on_this_environment`; rename it
      `test_skipped_without_torch`.
    - Any slice-05 CLI test of `hardware-check --smoke` → exit 3.
    
    Keep the real-environment "skipped" check as one subprocess test that is skipped with a
    reason when `importlib.util.find_spec("torch")` is not `None`. Do not weaken any assertion.

## 3. Implementation Plan (Task List)

- [ ] Task 1: add the extras, conflicts, index and sources to `pyproject.toml`; run `uv lock`.
  On failure, stop and report to the lead with the output.
- [ ] Task 2: sync each supported combination into a scratch runtime env and run `pip-licenses`
  on it. Derive the exact NVIDIA and LGPL exemption lists from that output, and keep the output for
  the handoff.
- [ ] Task 3: write the four gate commands (base, gpu, gpu+mlip-mace, gpu+mlip-uma) in `AGENTS.md`
  and `ci.yml`, character for character the same.
- [ ] Task 4: write the two exemption-guard tests (Mini-requirement 5).
- [ ] Task 5: run mypy with each MLIP combination installed, then return to the base dev env.
- [ ] Task 6: add the register rows. Re-run the four gates in the base dev env.

## 4. The Negative Space (Constraints)

- **DO NOT** add `ase`, `matscipy` or any LGPL/GPL package as a direct dependency, in core or in
  any extra.
- **DO NOT** let any exempt package into the base (no-extras) install.
- **DO NOT** exempt any package that the lock did not resolve for that extra.
- **DO NOT** extend the base allow-list, or add an exemption for a reason other than TJ's Q1 A or the `geometric:1.1.1` exception (R41).
- **DO NOT** make the MLIP extras co-installable by pinning one engine to an old release, or by
  overriding `e3nn`.
- **DO NOT** add any new import of `torch` (beyond `hw_probe`'s existing function-local one), `mace`, `fairchem`, `ase` or `matscipy` anywhere in `src/eta_rxncat/`
  in this slice.
- **DO NOT** run the GPU smoke or commit `GPU_SMOKE_RESULT.json`; that belongs to slice 07.
- **DO NOT** add a GPU job to CI.
- **DO NOT** edit `src/eta_rxncat/{core,store}` or `cli.py`. In `utils`, change only `hw_probe.py`, and only for Mini-requirement 9 (R43).
- **DO NOT** add retry, reinstall or CPU-fallback logic for a broken torch/GPU4PySCF; report it.

## Proof contract

- [ ] `uv lock --check` → exit 0. `uv.lock` lists `mace-torch` and `fairchem-core` under their
  extras and torch from `pytorch-cu128`.
- [ ] `uv sync --locked` (no extras) followed by `uv pip list` contains none of `torch`,
  `nvidia-*`, `mace-torch`, `fairchem-core`, `ase` or `matscipy`.
- [ ] Each of the three supported combinations → `uv sync --locked …` exits 0.
  `--extra mlip-mace --extra mlip-uma` → non-zero, and the message names the conflict.
- [ ] Each of the four licence-gate commands → exit 0 in its env. The exemption list for each
  equals the set of packages that fail the bare allow-list in that env. Removing one exempt name
  makes the command exit non-zero (shown once for an NVIDIA package and once for `ase`).
- [ ] Exemption-guard tests pass. A scratch file under `tmp_path` containing `import ase` makes the
  AST scanner report it (the scanner is a function tested on a path argument).
- [ ] `uv run mypy` → exit 0 with `gpu+mlip-mace` installed, and with `gpu+mlip-uma` installed.
- [ ] `ci.yml` has the `licence-extras` matrix job, and its commands match `AGENTS.md` character
  for character.
- [ ] The four gates → exit 0 in the base dev env. The register rows from Mini-requirement 8 are
  present.
- [ ] R43: unit tests using a fake `torch` (and a fake `gpu4pyscf`) whose import raises
  `OSError("libcudart.so.12: cannot open shared object file")`, with the distribution metadata
  present. Expected: `probe_hardware()` returns `installed true`, flags containing
  `torch_import_failed` (resp. `gpu4pyscf_import_failed`) in the fixed order, and the note text.
  `run_smoke()` returns `fail` naming the package, exit 1, with no child process. A torch whose
  import raises `ImportError` with no metadata still gives `torch_missing` / `skipped`.
- [ ] R44: `uv run pytest` → exit 0 in the base dev env, **and** → exit 0 after
  `uv sync --locked --extra gpu` (then return to the base env with `uv sync --locked`). Paste both
  summary lines. `grep -rn "installed is False" tests/unit` hits only fake-host tests.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (Hardware Constraint; v0.1.0 PR #1/#2; CUDA line).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml` (reference only: the starter `mlip` extra).
- Mission `missions/release-0.1.0/SPEC.md` §5, trade-off log R1, R2, R10, R13, R30; TJ's answer on
  `qitem-20261122075815-4c32a48f2e42363c`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.4 (hardware probe: the extras feed its torch/gpu4pyscf detection; transitively
  OPR.0.1.0.1 for the scaffold, gates and licence gate)
