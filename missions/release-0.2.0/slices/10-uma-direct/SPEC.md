---
id: OPR.0.2.0.10
slice: 10-uma-direct
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the fairchem engines on one clean-room bridge with honest per-family tags: uma_direct (uma-s-1p2p1) and esen_omol25 (OMol25 esen-sm-conserving-all-omol), explicit charge/spin, no ase in eta_rxncat, sha256-pinned identities, direct-force checkpoints refused; both proved on this host (UMA access open since 16:54Z)."
depends_on: [OPR.0.2.0.4, OPR.0.2.0.5, OPR.0.2.0.2, OPR.0.2.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/licence-inventory.md, docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [["uv", "run", "ruff", "check", "."], ["uv", "run", "ruff", "format", "--check", "."], ["uv", "run", "mypy"], ["uv", "run", "pytest"], ["env", "UV_PROJECT_ENVIRONMENT=.venv-accept-uma", "ETA_RXNCAT_ACCEPTANCE=1", "uv", "run", "--no-sync", "pytest", "-m", "mlip_uma", "tests/unit/engines/"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: fairchem engines: `uma_direct` (UMA `uma-s-1p2p1`) and `esen_omol25` (OMol25 eSEN-sm-conserving), one bridge, no ASE in eta_rxncat

## Intent

Implement two charge- and spin-aware MLIP engines on fairchem-core ≥ 2.22, sharing one clean-room
fairchem bridge. Each has its own honest engine tag:
- `uma_direct`: `uma-s-1p2p1`, `omol` task;
- `esen_omol25`: the conserving OMol25 checkpoint `esen-sm-conserving-all-omol`.

Charge and spin are explicit, and there is no `ase` import in eta_rxncat. Weights come from the HF
cache (TJ Q3 A) or a local checkpoint (Q3 B). Identities are pinned to each checkpoint's sha256.
Direct-force checkpoints are refused, and credentials never appear in any output.

Both halves are provable now. UMA access opened at 16:54Z, so every proof below is required for
this slice's audit.

Context the builder needs (self-contained).

TJ, 16:52Z (via operator), verbatim: "A - Ship it as a second model". This is option A of
`~/.hacf/eta-rxncat-hacf/omol25-assessment.md`, which you should read. The fairchem engine also
accepts the **conserving** OMol25 checkpoint `esen_sm_conserving_all.pt` alongside
`uma-s-1p2p1`, and refuses the direct-force checkpoints. It goes through the same tests (match
fairchem's own predictor on the neutral, anion, radical and Pd cases).

Plus the lead's condition, which TJ accepted: an **honest engine tag**, because the tag is in the
cache key. Resolve's design (R31, PROPOSED ADR-0022 amending ADR-0001): one tag per model family.
`esen_omol25` is added to core `EngineTag` by slice 03. Each tag accepts exactly its approved
`method`, and both engines share a private bridge module.

UMA acceptance is still required for v0.2.0 (TJ Q3). OMol25 is an addition, not a substitute.

Host facts (operator, 16:52Z):
- TJ saved an HF token at `~/.cache/huggingface/token` (mode 600). **It is a secret.** Never
  print, log, copy or commit it, or put it in a row, record or evidence. `huggingface_hub` reads
  it itself.
- 16:52Z: `facebook/OMol25` `esen_sm_conserving_all.pt` → HTTP 302 (access OK).
- 16:54Z: TJ ran `hf auth login`. Header-only checks with the token file give `facebook/UMA`
  `uma-s-1p2p1.pt` → **302** and OMol25 → 302. UMA access is open.
- Use fairchem's own download path (TJ's route A). Route B (a local checkpoint) stays
  supported in code but is not provisioned.
- Evidence records only "credentials present: yes/no" and HTTP status codes.

Public HF metadata (resolve, unauthenticated):
- `checkpoints/esen_sm_conserving_all.pt` is 50,958,067 B; `checkpoints/uma-s-1p2p1.pt` is
  2,333,393,615 B;
- both LFS oids are masked, so sha256 is computed at load (ADR-0017).

Assessment facts (fairchem 2.22; verify on the locked 2.26):
- `get_predict_unit(name)` and `load_predict_unit(path)` load both families;
- charge and spin are embedded by both backbones (`csd_embedding`);
- `spin` is the **multiplicity**;
- `atomic_data.py` defaults a missing spin to **0** (invalid), so always set both;
- direct-force models run inference under `no_grad`, and their forces are not −∇E.

Registry names:
- conserving: `esen-sm-conserving-all-omol` (approved), `allscaip-md-conserving-all-omol` (not
  approved by TJ);
- direct: `esen-sm-direct-all-omol`, `esen-md-direct-all-omol`, `allscaip-md-direct-all-omol`.

Stack, env and test policy:
- torch 2.13+cu129, fairchem-core 2.26.0 (slice 02);
- env `.venv-accept-uma` (`--extra gpu --extra mlip-uma`; the extra name stays);
- unit tests run with `HF_HUB_OFFLINE=1` (slice 01).

## 1. The Confidence Mandate

**Score: 8/10.** The tag scheme, bridge, identity, refusal rules and secret handling are fixed.
The residuals:
- fairchem 2.26's exact non-ASE `AtomicData` construction (read from the installed source);
- whether the eSEN checkpoint's embedded config really makes charge and spin live. That is the
  first build step, stop-and-report (Mini-requirement 3);
- none external: both repos return 302 for TJ's login (16:54Z).

## Mini-requirements

1. `engines/_fairchem_bridge.py` (private, shared):
   - reproduce **exactly** what `get_predict_unit(name)` does in fairchem 2.26, but offline. Its
     registry entry (`fairchem/core/calculate/pretrained_models.json`) gives `repo_id`,
     `subfolder: "checkpoints"` and `filename`, plus **reference files** that change the returned
     energy:
     - `atom_refs`: `references/iso_atom_elem_refs.yaml` (both models);
     - `form_elem_refs`: `references/form_elem_refs.yaml` (UMA).

     Resolve each with `hf_hub_download(repo_id, filename, subfolder=…, local_files_only=True)`,
     or take the checkpoint from `checkpoint_path` (route B), and pass the refs to
     `load_predict_unit(path, atom_refs=…, form_elem_refs=…)` exactly as `get_predict_unit` does
     (read its source; R40);
   - **key the references** (R40): at construction, add the derived keyed options
     `atom_refs_sha256` and `form_elem_refs_sha256` (64-hex, or `"none"` when the registry entry
     has none) to `engine.stage`. The checkpoint's hash stays in `identity.model` (ADR-0017). A
     caller may not set these two options; they are derived like `engine_impl`;
   - **refuse** a model whose loaded config has direct forces (`direct_forces` true, or the
     equivalent flag in 2.26), with `EngineInputError("<method>: direct-force checkpoint; forces are not -dE/dx")`.
     This is checked after load, and in addition to the per-engine method allow-list;
   - build fairchem's input batch from symbols, positions (Å), `charge = state.charge` and
     `spin = state.multiplicity`, with task `omol`, using fairchem's data classes and **no `ase`
     import in `src/`**. In 2.26, `AtomicData.__init__` takes `charge`, `spin` and `dataset`; the
     task goes in `dataset` (`from_ase` calls it `task_name`). Build `AtomicData` directly;
   - predict; energy eV → Eh; forces eV/Å → Eh/Bohr (units module);
   - Hessian = `fd_hessian` on the engine's forces (`finite_difference`);
   - record the position dtype: float32 → `"fairchem_dtype:float32"` in `recovery_steps`;
   - `device` = `"cuda"` or `"cpu"`;
   - torch and fairchem are imported inside functions only.
2. Two engines on the bridge, `ENGINE_IMPL = 1` each. Keyed options: `task` (`omol` only),
   `inference_settings` (allowed `{"high-precision"}`, default `"high-precision"`; R47),
   `fd_step_bohr` (0.005), `engine_impl` (1). Runtime: `checkpoint_path` (optional), `device`.

   **Precision (R47).** fairchem 2.26's default `inference_settings` uses TF32 / "UMA Nitro" on
   CUDA (CC 8.x–12.x; this GPU is 12.0) and "general" on CPU. Measured on water, CUDA vs CPU
   differ by ΔE 1.1e-4 eV and ΔF 6.9e-4 eV/Å for UMA, and by 1.0e-5 / 2.5e-4 for eSEN, with the
   device unkeyed, so one cache key would mix precisions. With `"high-precision"` the difference
   is ≤1e-7 eV and ≤6e-7 eV/Å. The bridge passes `inference_settings=<stage value>` to fairchem's
   loader on **both** devices. Any other value → `EngineInputError`.

   | | `UMADirectEngine` | `ESENOMol25Engine` |
   |---|---|---|
   | file | `engines/uma_direct.py` | `engines/esen_omol25.py` |
   | tag | `uma_direct` | `esen_omol25` |
   | `method` | must be `uma-s-1p2p1` | must be `esen-sm-conserving-all-omol` |
   | HF repo / file | `facebook/UMA` / `checkpoints/uma-s-1p2p1.pt` | `facebook/OMol25` / `checkpoints/esen_sm_conserving_all.pt` |
   | identity `model` | `uma-s-1p2p1@sha256:<hex>` | `esen-sm-conserving-all-omol@sha256:<hex>` |
   
   - Any other `method` → `EngineInputError`. For eSEN, a direct-force name is refused with
     "direct-force checkpoint", and `allscaip-md-conserving-all-omol` with "not approved (TJ
     16:52Z approved esen-sm-conserving-all-omol only)".
   - identity: `EngineIdentity(name=<tag>, version=library_version("fairchem-core"), model=<as above>)`,
     with the sha256 computed **before** load.
   - Neither weights path available → `EngineUnavailableError("no <tag> weights: provision via HF login (TJ Q3 A) or pass checkpoint_path (Q3 B)")`.
     No message contains a token, `HF_TOKEN`'s value, or token-file content.
3. **First build step, stop-and-report.** Provision both checkpoints via seat commands with TJ's
   login (route A, fairchem's own download path):
   `huggingface_hub.hf_hub_download("facebook/OMol25", "checkpoints/esen_sm_conserving_all.pt")`
   and `huggingface_hub.hf_hub_download("facebook/UMA", "checkpoints/uma-s-1p2p1.pt")` (2.33 GB),
   into the HF cache, recording only the HTTP outcome. Then, for **each** model, check that:
   - water at charge 0 vs the same geometry at charge −1 give different energies;
   - hydroxyl at multiplicity 2 vs 4 give different energies.
   
   If either is equal, charge or spin is not live: stop and hand back with the output.
4. Provisioning record, `docs/licence-inventory.md`:
   - OMol25 eSEN-sm-conserving: FAIR Chemistry License v1 (May 14 2025), gated, size, sha256;
   - UMA `uma-s-1p2p1`: same licence family; size; sha256 once provisioned;
   - one line noting the Acceptable Use Policy is TJ's to read (assessment §c).
   
   Credentials are recorded only as present: yes/no.
5. Markers: UMA and eSEN weight-dependent tests are marked `mlip_uma` (same env), and CUDA cases
   are also marked `gpu`. No new marker.
6. Register rows (status `open`): `added` for `esen_omol25` (TJ 16:52Z A, R31); the starter
   `mlip.py` UMA part vs `uma_direct` (float32, charge/spin mapping, `uma-s-1.2.1` →
   `uma-s-1p2p1`, FD Hessian, the ASE path).

## 3. Implementation Plan (Task List)

- [ ] Task 1: `.venv-accept-uma`. Read fairchem 2.26's predictor and data API in the installed
  source, and write down the call path in the bridge docstring.
- [ ] Task 2: eSEN provisioning and the liveness check (Mini-requirement 3). Stop on failure.
- [ ] Task 3: the bridge and both engines (Mini-requirements 1–2); the inventory and markers
  (Mini-requirements 4–5).
- [ ] Task 4: tests:
  - `tests/unit/engines/test_fairchem_bridge.py` (default suite, no weights: option and method
    validation, refusals, missing-weights errors, redaction, batch construction with a fake
    predictor capturing `charge` and `spin`);
  - `tests/unit/engines/test_esen.py` (`mlip_uma`; CPU and CUDA, CUDA also `gpu`);
  - `tests/unit/engines/test_uma.py` (`mlip_uma`; CPU and CUDA, CUDA also `gpu`).
- [ ] Task 5: register rows; four gates in `.venv`; the eSEN and UMA tests in `.venv-accept-uma`;
  `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** import `ase` in `src/eta_rxncat/`.
- **DO NOT** download in an engine or a test (`local_files_only=True`; `HF_HUB_OFFLINE=1`).
  Provisioning is a seat command.
- **DO NOT** print, log, copy, commit or record the token, or ask for one anywhere. Record only
  present: yes/no and HTTP status codes.
- **DO NOT** run eSEN under `uma_direct`, or UMA under `esen_omol25`. Each tag accepts exactly its
  approved method.
- **DO NOT** accept a direct-force checkpoint, or `allscaip-md-conserving-all-omol`.
- **DO NOT** omit `charge` or `spin` from the batch, or rely on fairchem's defaults.
- **DO NOT** mock the predictor in a test that claims a reference match.

## Proof contract

**Energy tolerance (R48).** Every energy comparison in this slice uses ≤max(1e-6 eV, 1e-10·|E|),
where |E| is the reference energy in eV. That is 1e-6 eV for the small molecules and about
4.3e-6 eV for the Pd anion (|E| ≈ 43,190 eV). It sits above fairchem's measured same-device
repeat spread (≤1.9e-6 eV, about 4e-11 relative, on the Pd anion; ≤2.6e-7 eV for the small
molecules) and well below any physical difference. Force tolerances are unchanged (≤1e-5 eV/Å;
measured ≤2.4e-6).

**All required for this slice's audit** (both repos are 302 since 16:54Z):
- [ ] Default suite:
  - an unknown `method` per tag → `EngineInputError`;
  - `esen-sm-direct-all-omol` / `esen-md-direct-all-omol` / `allscaip-md-direct-all-omol` →
    "direct-force checkpoint";
  - `allscaip-md-conserving-all-omol` → "not approved";
  - eSEN given a stage with `engine="uma_direct"` → `EngineInputError`;
  - no weights → `EngineUnavailableError` for each tag;
  - redaction: with `HF_TOKEN=hf_SENTINEL_do_not_print` (monkeypatch), no error, `caplog` text or
    result repr contains `hf_SENTINEL`;
  - a fake predictor captures the batch: hydroxide `charge == -1, spin == 1`; hydroxyl
    `charge == 0, spin == 2`; the Pd anion `charge == -1, spin == 1`, for both engines.
- [ ] The bridge refuses a loaded model reporting direct forces. Use a fake predict unit with
  that config flag in the default suite, and record the real config flag name from 2.26 in the
  bridge docstring.
- [ ] `mlip_uma`, for **each** of eSEN (`esen-sm-conserving-all-omol`) and UMA (`uma-s-1p2p1`),
  CPU and CUDA, all four cases (water, hydroxide, hydroxyl, Pd anion):
  - energy and forces equal fairchem's own predictor,
    `get_predict_unit(name, inference_settings="high-precision", device=…)` for the same
    checkpoint (or `FAIRChemCalculator` built on that predict unit, with `ase.Atoms` in the test
    file), with charge and spin set explicitly, converted with `engines.units`: energy ≤max(1e-6 eV, 1e-10·|E|) (R48),
    forces ≤1e-5 eV/Å;
  - R47/R48, CPU vs CUDA for the same model and case at `"high-precision"`: |ΔE| ≤max(1e-6 eV, 1e-10·|E|)
    and max|ΔF| ≤1e-5 eV/Å;
  - `inference_settings="default"` (or any value other than `"high-precision"`) →
    `EngineInputError`, and `engine.stage.options["inference_settings"] == "high-precision"`
    for a stage with no option;
  - the liveness checks of Mini-requirement 3 hold;
  - forces vs central FD of the engine energy (step 1e-3 Å) ≤1e-3 eV/Å, which holds for a
    conserving model;
  - `hessian=True` on water → 9×9, `finite_difference`, symmetric.
- [ ] R40: for each model, `engine.stage.options` holds `atom_refs_sha256` (and, for UMA,
  `form_elem_refs_sha256`) equal to the sha256 of the files used. The engine energy equals
  `get_predict_unit(name, inference_settings="high-precision", device=…)`'s on the same input (≤max(1e-6 eV, 1e-10·|E|)), which would show any
  reference-file mismatch as an offset. Changing the refs file (a `tmp_path` copy with one value
  edited, passed via a test hook) changes the key.
- [ ] eSEN `identity.model` matches `^esen-sm-conserving-all-omol@sha256:[0-9a-f]{64}$`, and UMA's
  matches `^uma-s-1p2p1@sha256:[0-9a-f]{64}$`; each equals the sha256 of the file used.
  `docs/licence-inventory.md` has both, with sizes 50,958,067 and 2,333,393,615.
- [ ] The AST ban passes (no `ase` in `src/`). The base-install no-heavy-import test prints `[]`.
- [ ] The four gates in `.venv` → exit 0.
  `UV_PROJECT_ENVIRONMENT=.venv-accept-uma ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m mlip_uma tests/unit/engines/`
  → exit 0, with 0 skipped.

## Source material

- TJ 16:52Z "A - Ship it as a second model"; `~/.hacf/eta-rxncat-hacf/omol25-assessment.md`;
  plan PR #5; TJ Q3, F1 A; mission R1, R4, R5, R11, R15, R19, R23, R31; ADR-0017, ADR-0022
  (PROPOSED); the starter `mlip.py` (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base), OPR.0.2.0.5 (test data), OPR.0.2.0.2 (fairchem ≥ 2.22 on cu129),
  OPR.0.2.0.3 (core `EngineTag` gains `esen_omol25`)
