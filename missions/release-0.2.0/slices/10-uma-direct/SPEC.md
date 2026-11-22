---
id: OPR.0.2.0.10
slice: 10-uma-direct
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the uma_direct engine on fairchem>=2.22: uma-s-1p2p1 with the omol task and explicit charge and spin (multiplicity), via fairchem's predictor without ase in eta_rxncat, weights from the HF cache or a local checkpoint, a sha256-pinned identity, and secret-safe errors."
depends_on: [OPR.0.2.0.4, OPR.0.2.0.5, OPR.0.2.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/licence-inventory.md, docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [env, "UV_PROJECT_ENVIRONMENT=.venv-accept-uma", "ETA_RXNCAT_ACCEPTANCE=1", uv, run, "--no-sync", pytest, "-m", mlip_uma, tests/unit/engines/test_uma.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: UMA direct engine (`uma_direct`), fairchem `uma-s-1p2p1` (`omol`), charge and spin, no ASE in eta_rxncat

## Intent

Implement `UMADirectEngine` (tag `uma_direct`) on fairchem-core ≥ 2.22. It evaluates `uma-s-1p2p1`
with the `omol` task and explicit charge and spin, through fairchem's predictor and without
`ase` in eta_rxncat. Weights come from the HF cache (TJ Q3 A) or a local checkpoint (Q3 B). The
identity is pinned to the checkpoint's sha256, and credentials never appear in any output.

Context the builder needs (self-contained).

TJ, Q3 verbatim: "A If that fails we can do B".
- A: TJ gets `facebook/UMA` access and puts a read token at `~/.cache/huggingface/token`.
- B: TJ puts `uma-s-1p2p1.pt` at a local path outside the repo.
- "Build the engine to support both"; "v0.2.0 is not accepted until the UMA run passes".
- The token is a secret. It lives only in the env or HF cache, never in the repo, rows, logs,
  errors or evidence. The evidence records only `hf_token_present: true/false` and the
  checkpoint's name and sha256.

TJ F1 "A": torch 2.13+cu129 with fairchem ≥ 2.22 (locked 2.26.0, slice 02), whose registry
includes `uma-s-1p2p1`.

The HF repo lists `checkpoints/uma-s-1p2p1.pt` at 2,333,393,615 B. Its LFS sha256 is masked
while gated, so the hash is computed at load (R5). On 2026-11-22 `~/.cache/huggingface/token` was
absent and `HF_TOKEN` was unset; only presence was checked, never the content.

fairchem facts (red team, 2.21, so verify on 2.26):
- `spin` is the **multiplicity**;
- the `omol` head silently defaults to charge 0 and spin 1 when unset;
- `fairchem.core.datasets.atomic_data` imports `ase` at module top, which is allowed in-process
  (TJ 14:59Z), but `src/eta_rxncat/` never imports `ase` (AST ban).

The env is `.venv-accept-uma` (`--extra gpu --extra mlip-uma`). Unit tests run with
`HF_HUB_OFFLINE=1` (slice 01).

## 1. The Confidence Mandate

**Score: 8/10.** The API, charge and spin mapping, identity and secret handling are fixed. The
residuals:
- fairchem 2.26's exact non-ASE `AtomicData` construction (the builder determines it from the
  installed source);
- **weights access**: an external dependency on TJ, with an explicit interim state.

## Mini-requirements

1. `engines/uma_direct.py`, `UMADirectEngine(Engine)`, `ENGINE_IMPL = 1`:
   - `method` must be `uma-s-1p2p1`;
   - keyed: `task` (`omol` only), `fd_step_bohr` (0.005), `engine_impl` (1);
   - runtime: `checkpoint_path` (optional; path B), `device` (`auto`|`cpu`|`cuda`).
2. Weights:
   - with a `checkpoint_path`, load it with fairchem's local loader;
   - otherwise resolve the checkpoint from the HF cache **with `local_files_only=True`**
     (path A, already downloaded by a provisioning seat command, never by the engine);
   - neither available → `EngineUnavailableError("no UMA weights: provision via HF login (TJ Q3 A) or pass checkpoint_path (Q3 B)")`.
     The message never contains a token, `HF_TOKEN`'s value, or the HF cache's token file
     content.
   - Before loading, compute `sha256_file(checkpoint)`.
     `identity = EngineIdentity(name="uma_direct", version=library_version("fairchem-core"), model=f"uma-s-1p2p1@sha256:{hex}")`.
3. Evaluate:
   - build fairchem's input batch from symbols, positions (Å), `charge = state.charge`, and
     `spin = state.multiplicity` (fairchem convention), with task `omol`, using fairchem's own
     data classes and **no `ase` import in `src/`**;
   - call the predictor;
   - energy eV → Eh; forces eV/Å → Eh/Bohr;
   - Hessian = `fd_hessian` on the engine's forces, `finite_difference`;
   - record the model's position dtype. If float32, add `"uma_dtype:float32"` to
     `recovery_steps` (R15);
   - `device` = `"cuda"` or `"cpu"`;
   - torch and fairchem are imported inside the engine only.
4. Provisioning, a seat command recorded in the handoff:
   - path A: with TJ's login present, `huggingface_hub.hf_hub_download("facebook/UMA", "checkpoints/uma-s-1p2p1.pt")`
     into the HF cache;
   - path B: TJ's file;
   - record the checkpoint's sha256 and size in `docs/licence-inventory.md` (UMA weights,
     `license: other`, gated), never the token.
5. Register rows (status `open`) vs the starter `mlip.py` UMA part: float32 positions, the
   charge/spin mapping, the model name `uma-s-1.2.1` → `uma-s-1p2p1` (TJ F1 A), FD Hessian, the
   ASE path.
6. **Interim state (R23).** If no weights are available when the build is otherwise complete:
   - finish everything that does not need weights;
   - leave the weights-dependent proofs unticked;
   - hand back **BLOCKED on TJ's UMA access** (via the lead and operator), with the output of the
     `EngineUnavailableError` path.
   
   Never mock the model, and never mark the proofs passed.

## 3. Implementation Plan (Task List)

- [ ] Task 1: `.venv-accept-uma`. Read fairchem 2.26's predictor and data API in the installed
  source, and write down the call path in the module docstring.
- [ ] Task 2: the engine (Mini-requirements 1–3).
- [ ] Task 3: tests in `tests/unit/engines/test_uma.py`:
  - `mlip_uma` (and `gpu` for CUDA) tests needing weights;
  - default-suite tests needing no weights: the missing-weights error, the secret-redaction test,
    option validation.
- [ ] Task 4: provisioning when access exists (Mini-requirement 4); register rows; four gates;
  marked tests in `.venv-accept-uma`.

## 4. The Negative Space (Constraints)

- **DO NOT** import `ase` in `src/eta_rxncat/`.
- **DO NOT** download in the engine or in tests (`local_files_only=True`; `HF_HUB_OFFLINE=1`).
- **DO NOT** write, log, echo or record a token, or ask for one anywhere.
- **DO NOT** omit `charge` or `spin` from the batch, or rely on fairchem's defaults.
- **DO NOT** mock the predictor in a test that claims a reference match.

## Proof contract

- [ ] Default suite:
  - no weights → `EngineUnavailableError` with the stated message;
  - redaction: with `HF_TOKEN=hf_SENTINEL_do_not_print` set via monkeypatch, the error message,
    `caplog` text and any `PotentialResult` repr contain no `hf_SENTINEL`;
  - `task="spin"` → `EngineInputError`.
- [ ] `mlip_uma` (CPU and CUDA), all four cases:
  - energy and forces equal fairchem's own predictor (or `FAIRChemCalculator` with `ase.Atoms`
    in the test file) with `charge` and `spin` set explicitly, converted with `engines.units`:
    energy ≤1e-6 eV, forces ≤1e-5 eV/Å;
  - literal: the built batch has `charge == -1, spin == 1` for hydroxide, `charge == 0, spin == 2`
    for hydroxyl, and `charge == -1, spin == 1` for the Pd anion;
  - behavioural: the hydroxyl geometry at multiplicity 2 vs 4 gives different energies.
- [ ] `identity.model` matches `^uma-s-1p2p1@sha256:[0-9a-f]{64}$` and equals the sha256 of the
  checkpoint file used. `docs/licence-inventory.md` records the same hash and size.
- [ ] The AST ban passes (no `ase` in `src/`). The base-install no-heavy-import test prints `[]`.
- [ ] The four gates in `.venv` → exit 0.
  `UV_PROJECT_ENVIRONMENT=.venv-accept-uma ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m mlip_uma tests/unit/engines/test_uma.py`
  → exit 0, with 0 skipped. Without weights this bullet is the blocked finding of
  Mini-requirement 6.

## Source material

- Plan PR #5; TJ Q3, F1 A; mission R1, R4, R5, R11, R15, R19, R23; ADR-0017 (PROPOSED); the starter
  `mlip.py` (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base), OPR.0.2.0.5 (test data), OPR.0.2.0.2 (fairchem ≥ 2.22 on cu129)
