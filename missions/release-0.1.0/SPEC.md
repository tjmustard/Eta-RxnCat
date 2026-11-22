---
id: OPR.0.1.0
mission: release-0.1.0
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope mission create)"
created: "2026-11-22"
intent: "Stand up the Eta-RxnCat v0.1.0 foundation: a uv-managed MIT Python package with CI, a hardware capability probe, Pydantic v2 core schemas with a YAML/JSON ReactionGraph loader, and a stage-decomposed SQLite artifact store."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: []
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: Eta-RxnCat v0.1.0 — Repo Scaffold, Hardware Gate & Core Schemas

## Intent

Stand up the Eta-RxnCat v0.1.0 foundation: a uv-managed MIT Python package with CI and a closed
licence gate, a hardware capability probe with a GPU smoke test, strict Pydantic v2 core schemas
with a YAML/JSON ReactionGraph loader, and a versioned, stage-decomposed SQLite artifact store.

## 1. Introduction & Goals

**Problem.** The authoritative plan (`PRDs/Eta-RxnCat_Living_Master_Plan.md`) describes
Eta-RxnCat as a permissively licensed library and adaptive workflow engine for homogeneous
organometallic and organocatalytic reaction mechanisms. Every later milestone (engines v0.2.0,
conformers v0.3.0, mapper v0.4.0, TS optimizer v0.5.0, …, orchestrator v0.8.0) imports the data
contracts and the cache-key scheme built here. A loose contract now is inherited by nine later
versions, so v0.1.0 pins the contracts precisely.

**Solution overview.** The Master Plan's three v0.1.0 PRs, split into independently buildable
slices (see §5 Execution checklist):
1. **Repo scaffold** (PR #1): `pyproject.toml` (MIT, `uv`, committed `uv.lock`), the
   `src/eta_rxncat/` layout, README with the `nMap` / `Eta_Scripts` homage, project rules in
   `AGENTS.md` outside the HACF block, GitHub Actions CI (`ruff`, `mypy`, `pytest`, licence gate),
   the unpacked v0.1.0 reference and both discrepancy registers.
2. **Hardware probe** (PR #2): `eta_rxncat.utils.hw_probe` — typed report of PyTorch CUDA,
   GPU4PySCF, compute capability, total VRAM and the 6.5 GiB budget, plus an opt-in GPU smoke
   test with a numeric pass criterion.
3. **Core schemas and store** (PR #3): strict Pydantic v2 models, a duplicate-key-rejecting
   YAML/JSON loader and validator, and a versioned SQLite artifact store with a canonical,
   versioned cache key.

**Audience.** TJ (computational chemist, project owner) and the agents and contributors who build
v0.2.0+ against these contracts. Runtime target: this host's NVIDIA RTX 5060 Ti (8151 MiB,
compute capability 12.0, driver 595.99.02). CPU-only machines, CI included, are first-class.

**Inputs (read-only).**
- `PRDs/Eta-RxnCat_Living_Master_Plan.md` — **authoritative** (TJ, Q1).
- `PRDs/Eta-RxnCat-v0.1.0.zip`, unpacked to `docs/prd/v0.1.0/` (real paths
  `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/…`) — **reference only** (TJ, Q2).

**TJ's decisions, quoted** (relayed by the lead and operator; rows recorded in the interview log of
the drafts copy):
- Goal: "The living master plan + start with V0.1.0 then V0.2.0 and so on till V1.0.0. Zips should
  be unpacked in repo as needed in appropriate sub directories."
- Q1: "A". The `PRDs/` Master Plan is authoritative; zip copies are reference only; no ~60-atom
  test in v0.1.0.
- Q2: "B use it as reference only. Keep a list of the discrepancies so that if needed, we can go
  through each of them and fix any issues that arise."
- "Also want to build a list of discrepancies between the master plan and the ziped files. Example
  the 60 atom test for v0.1.0"
- Q3, amended 07:52Z: "Build, install, and run these autonomously as to move on to the next
  step/question." The team runs the GPU smoke on this host; TJ is brought only real decisions.
- Never push. `PRDs/` untouched. HACF stays at v0.6.0.
- F1 + F2 (row `qitem-20261122075815-4c32a48f2e42363c`, 08:19Z, verbatim): "Q1 A, Q2 A".
  Q1 A: LGPL only as transitive deps of the optional MLIP extras; never core, never vendored,
  `eta_rxncat` never imports `ase`/`matscipy`; NVIDIA CUDA wheels exempt; CI licence check per
  extra. Q2 A: separate mutually exclusive extras `mlip-mace` and `mlip-uma`, declared conflicting
  so uv locks both. Realised in slice 06.

## 2. Confidence Mandate

**Score: 9/10** (target 10).

Settled: plan authority (Q1); starter is reference only with a closed-inventory register (Q2,
F15); the plan-copy register with a pinned diff command (F16); the team runs the GPU gate (Q3);
all 25 design findings F3–F27 have a decision in §5 Resolved trade-off log, with testable
contracts.

F1/F2 are settled by TJ ("Q1 A, Q2 A"); slice 06 encodes them.

Open, and the reason the score is not 10:
- Host facts only a run can answer: whether current `mace-torch` / `fairchem-core` each lock
  against a cu128 torch (slice 06, `uv lock`), and this host's driver/CUDA state (slice 07).

Questions needed to reach 10:
1. ~~F2 licence policy~~ answered: Q1 A.
2. ~~F1 MACE/UMA co-install~~ answered: Q2 A.
3. (Host fact, slice 06) Whether a CUDA-12 PyTorch build that satisfies the chosen MLIP extras
   exists on the PyTorch index — answered by `uv lock`, not by TJ.

## 3. Scope

### In scope (v0.1.0 only)
- Unpack `PRDs/Eta-RxnCat-v0.1.0.zip` into `docs/prd/v0.1.0/` as-is; it is reference input, never
  imported, executed, linted, type-checked or test-collected (F4).
- Product code at the repo root: `pyproject.toml`, `uv.lock`, `.python-version`,
  `src/eta_rxncat/`, `tests/`, `.github/workflows/ci.yml`, `README.md`, a project section in
  `AGENTS.md` outside the HACF managed block (F20), `.gitignore` additions outside the HACF block.
- Core models in scope: `MolecularState`, `AtomMappingSpec`, `StageConfig` (+ `Solvation`),
  `ThermoConfig`, `Component`, `TemplateGeometry`, `ReactionNode`, `ReactionEdge`,
  `PruningRule`, `ReactionGraph`, `EngineIdentity`; the YAML/JSON loader and validator.
- Store: canonical versioned cache key, `ArtifactStore` (SQLite, WAL, schema version 1).
- Hardware probe and `--smoke`; CLI `eta-rxncat hardware-check [--smoke]` and
  `eta-rxncat validate <graph>`.
- Example graph at `tests/data/reaction_graphs/example_reaction_graph.yaml` (F17).
- `docs/prd/v0.1.0/DISCREPANCIES.md` (TJ, Q2) and `docs/prd/PLAN_DISCREPANCIES.md` (TJ, 07:45Z).
- The team's GPU acceptance run, recorded in `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` (TJ, Q3).

### Out of scope (explicitly)
- `ConformerEnsemble` (v0.3.0 defines it), `PotentialResult` (v0.2.0), `ThermoResult` and
  `VibrationalMode` (v0.3.0/v0.5.0), covalent connectivity validation (v0.9.0 topology audit).
  The plan's PR #3 names only the v0.1.0 models; the starter's extra models become `dropped`
  register rows (F8).
- Any compute engine, conformer generation, mapping/surgery, TS optimizer, selectivity,
  enumeration, orchestrator/scheduler, pruning-rule *evaluation*, crash-resume logic, reporting,
  E2E harness — their plan versions own them.
- CLI commands beyond `hardware-check` and `validate` (v1.0.0). Any GUI (v1.1.0+).
- A ~60-atom VRAM test (TJ, Q1). A VRAM budget that scales with card size (F12: the plan's target
  is the 8 GB card; revisit when another card is a target).
- Blob sidecar storage for large payloads (F25: deferred to the version that first stores
  Hessians, v0.3.0/v0.5.0; the v0.1.0 column contract is set now).
- Copying starter code into `src/` or `tests/`; fixing register entries without TJ's word;
  unpacking any other zip; touching `PRDs/`; overwriting HACF's managed blocks; pushing, tagging,
  PRs; a GPU in CI.

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority | Slice |
|---|---|---|---|---|
| US-001 | As TJ, I want `uv sync` to install from a committed lockfile so every machine gets the same environment. | `uv sync --locked` exits 0 on a fresh local clone; `uv.lock` committed; `.python-version` = `3.12`; `requires-python = ">=3.11,<3.14"`; `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` prints `0.1.0`. | P0 | 01 |
| US-002 | As TJ, I want lint, types, tests and a licence audit locally and in CI. | `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` (strict, `files = ["src"]`), `uv run pytest` and the licence gate each exit 0 on a fresh local clone with `docs/prd/v0.1.0/` present. `ci.yml` runs exactly these commands after `uv sync --locked` (F14: "in CI" is checked as "ci.yml runs the same commands", since nobody pushes). | P0 | 01 |
| US-002a | As TJ, I want the licence gate to catch real copyleft licence strings. | The gate uses `pip-licenses --partial-match --allow-only` with the allow-list in §5, audits the **runtime** environment only (no dev tools in its table), and fails on `UNKNOWN`. A scratch-env demonstration with an LGPL package exits non-zero (F3). | P0 | 01 |
| US-003 | As TJ, I want `eta-rxncat hardware-check` to report GPU, compute capability, PyTorch/CUDA and GPU4PySCF versions, total VRAM and the 6.5 GiB budget. | JSON report per §5 Contracts, exit 0 always (flags are in the JSON). CPU-only host: `cuda_available: false` with a note. Versions below CUDA 12.8 / GPU4PySCF 1.8.0 appear in `flags`. | P0 | 04, 05 |
| US-004a | As TJ, I want `--smoke` and a `gpu` test that prove a GPU4PySCF kernel and a CUDA op actually run. | Implemented per §5 smoke contract; exit 0 pass / 1 fail / 3 skipped; skipped on a CPU-only host with the reason; default `pytest` deselects `gpu`. Audited on the CPU path. | P0 | 04, 05 |
| US-004b | As TJ, I want v0.1.0 accepted only after the smoke passes on this host. | The build seat runs it once on a clean tree; `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` records `status: pass` and the commit sha it ran against; audit verifies it (F11, F26). | P0 | 07 |
| US-005 | As a later-version developer, I want `MolecularState` to reject silently wrong charge or spin. | Missing charge/multiplicity, multiplicity < 1, non-strict ints (`"1"`, `1.0`, `True`), unknown element symbols, symbol/coordinate count mismatch, non-N×3 or non-finite coordinates, out-of-range or duplicate active indices, electron-parity mismatch and unknown keys each raise (F9). | P0 | 02 |
| US-006 | As a later-version developer, I want the mapping spec to enforce the full invariant list. | Every invariant in §5 Contracts › AtomMappingSpec raises when broken; list order survives a round-trip (F19). | P0 | 02 |
| US-007 | As TJ, I want `eta-rxncat validate` to accept or reject a YAML/JSON graph with a clear message. | Example graph exits 0 and prints the §5 output. Duplicate node ids, unknown edge endpoints, self-loops, duplicate edges, unknown pruning-rule refs, duplicate YAML/JSON keys and unsupported extensions each exit 1 with one `error:` line on stderr naming the offender, no traceback. YAML → model → JSON → model round-trip is equal. | P0 | 02, 05 |
| US-008 | As TJ, I want thermochemistry to default to Grimme qRRHO and 1 M. | Defaults per §5 Contracts › ThermoConfig; non-positive values and `None` concentration raise (F23). | P0 | 02 |
| US-009 | As a later-version developer, I want one canonical, versioned cache key per stage. | Per §5 Contracts › Cache key: coordinates equal after rounding to 5 decimals give the same key; `-0.0` and `0.0` give the same key; changing any keyed field gives a different key; a pinned golden key for a fixed input; `key_schema` is in the key (F5, F6). | P0 | 03 |
| US-009a | As a later-version developer, I want the store never to lose a completed artifact. | Per §5 Contracts › Store: status state machine, completed rows immutable except via `invalidate`, conflict error on a different payload, schema version check, WAL with two concurrent connections (F7). | P0 | 03 |
| US-010 | As TJ, I want the README to credit `nMap` and `Eta_Scripts` and state the licence philosophy. | README contains DOI `10.1021/cs501828e`, a licensing section and a `uv` quickstart that works on a fresh clone. | P1 | 01, 08 |
| US-011 | As TJ, I want a durable list of every way the rewrite differs from the starter. | `docs/prd/v0.1.0/DISCREPANCIES.md` holds one row per starter inventory item (closed inventory, §5) with disposition `same`/`changed`/`dropped`, plus `added` rows; each slice completes the rows for its area (F15). | P0 | 01–05 |
| US-012 | As TJ, I want a durable list of every place the Master Plan differs from each zip's plan copy. | `docs/prd/PLAN_DISCREPANCIES.md` has one row per `@@` hunk of the pinned `diff -U0` command (§5), headed by the sha256 of `PRDs/` plan and of each distinct zip copy; 14 rows today, each listing v0.1.0–v0.6.0 and v0.8.0; PD-001 is the ~60-atom hunk (F16). | P0 | 01 |

## 5. Technical Specifications

### Resolved trade-off log

Every Red Team finding, both Part A (ledger) and Part B (per-section), has exactly one decision.
Vocabulary: **resolved** — the design changes so the risk is gone (the lead's "mitigated");
**accepted** — real risk kept, raised as a human row; **out of scope** — excluded with a reason
(the lead's "rejected"). No finding is `accepted` and none is still pending.

| R | Finding | Severity | Decision | Choice and one line of why |
|---|---|---|---|---|
| R1 | F1 `mlip` extra unresolvable | blocker | resolved (TJ Q2 A) | Separate extras `mlip-mace` and `mlip-uma`, declared under `[tool.uv] conflicts` so `uv lock` resolves both; one MLIP per environment. Slices 01–05 declare no extras; slice 06 adds them and proves `uv lock`. |
| R2 | F2 dependency set breaks the licence constraint | blocker | resolved (TJ Q1 A) | Base runtime set is permissive with no exemptions (slice 01). Per-extra gate (slice 06): NVIDIA CUDA wheels exempt; the MLIP extras additionally exempt exactly the transitive LGPL packages the lock resolves (`ase`, `matscipy`), never declared directly, never imported (AST test), never vendored. |
| R3 | F3 `--fail-on` exact-match blind | high | resolved | Allow-list: `pip-licenses --partial-match --allow-only="MIT;BSD;Apache;ISC;PSF;Python Software Foundation"` over the runtime env only; `UNKNOWN` fails by construction. A failing package is reported to the lead, never exempted by a seat. |
| R4 | F4 starter under `docs/prd/` fails gates | high | resolved | Keep TJ's "unpack in repo"; exclude `docs/prd` in ruff (`extend-exclude`), pytest (`testpaths = ["tests"]`, `norecursedirs` + `docs`), mypy (`files = ["src"]`). Register cells use the full `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/…` path. |
| R5 | F5 cache key incomplete, unversioned | high | resolved | Explicit canonical payload with `key_schema: 1`, including active and frozen atoms, solvation, options and a required `EngineIdentity` (name, version, model). A schema bump means old keys miss; no migration of keys. |
| R6 | F6 geometry hash not canonical | high | resolved | Grid semantics: round to 5 decimals, normalise `-0.0`, fixed-point strings; element symbols validated canonical (no case folding); integral floats in options canonicalised to int; non-finite rejected. US-009 rewritten. |
| R7 | F7 store semantics undefined | high | resolved | Status enum `pending/running/completed/failed`; completed rows immutable except `invalidate`; same-key different-payload → `ArtifactConflictError`; `PRAGMA user_version = 1`, other versions refused; WAL + `busy_timeout = 5000`; no default path — caller supplies the file path, parent must exist. |
| R8 | F8 core scope silent | high | resolved (scope) | In: PR #3's models plus the node/edge/template types the graph needs and `EngineIdentity`. Out: `ConformerEnsemble`, `PotentialResult`, `ThermoResult`, `VibrationalMode`, connectivity validation — defined by their consuming versions; starter copies recorded `dropped`. |
| R9 | F9 charge/spin still silently wrong | high | resolved | All five checks are v0.1.0 requirements: strict ints (bools rejected), duplicate-key-rejecting YAML loader and JSON hook, element table Z 1–118, electron-parity check, finite coordinates; plus `extra="forbid"` on every model. |
| R10 | F10 smoke pass criterion and CUDA line | high | resolved | Pass = SCF converged on GPU and CPU, \|E_gpu − E_cpu\| ≤ 1e-6 Eh, GPU arrays on device, float64 matmul max-abs-diff ≤ 1e-9 on a CUDA tensor, all within 600 s in a child process. Exit 0/1/3. CUDA 12 line (plan: "PyTorch `>=2.7.0+cu128`"): `gpu4pyscf-cuda12x`, `cupy-cuda12x`, torch from the PyTorch cu12x index — wired in slice 06. The runner seat stamps the sha; product code never calls `git`. |
| R11 | F11 who commits the GPU result | high | resolved | One seat (build/execute), one point: slice 07, after slices 01–06 are audited PASS, on a clean tree at HEAD. Audit verifies the JSON and does not run `uv sync`. v0.1.0 is accepted when slice 07 audits PASS; recommendation to the lead: v0.2.0's architect waits for it. |
| R12 | F12 VRAM units, card, API | medium | resolved | GiB (as torch reports bytes): budget = min(6.5 GiB, total) in bytes; total memory, not free (free reported, informational); host is the 5060 Ti; typed `HardwareReport` and `probe_hardware()` API. Card-scaled budget is out of scope (see §3). |
| R13 | F13 mypy depends on extras | medium | resolved | `[[tool.mypy.overrides]]` for `torch.*`, `gpu4pyscf.*`, `cupy.*`, `pyscf.*`, `rdkit.*`, `geometric.*`: `ignore_missing_imports = true`, `follow_imports = "skip"`; heavy imports are function-local. Gate env = dev env without extras; must also pass with extras (checked in 06/07). |
| R14 | F14 lockfile/CI determinism | medium | resolved | `uv sync --locked` in CI; `requires-python = ">=3.11,<3.14"`; `.python-version` `3.12`; "in CI" restated as local fresh-clone run plus `ci.yml` command equality. |
| R15 | F15 register completeness unbounded | medium | resolved | Closed inventory (§5 Discrepancy register): one row per starter item with disposition, plus `added` rows; audit checks it as a checklist, per slice area. |
| R16 | F16 hunk count depends on diff tool | medium | resolved | Pin `LC_ALL=C diff -U0 <zip copy> PRDs/Eta-RxnCat_Living_Master_Plan.md` (GNU diffutils); one row per `@@`; header records sha256s; a changed `PRDs/` plan sha marks the register stale and the next version's architect regenerates it. |
| R17 | F17 fixture path vs `tests/fixtures/` | medium | resolved | Example graph at `tests/data/reaction_graphs/`; agents never write `tests/fixtures/`. |
| R18 | F18 ReactionGraph semantics | medium | resolved | Two fields, one meaning each: `templates` = ranked alternative geometries of one node; `components` (inside a template) = the species of a separated state with stoichiometric `count`. All templates of a node share total charge and element multiset. Cycles allowed (catalytic cycles); self-loops and duplicate edges rejected. |
| R19 | F19 mapping invariants partial | medium | resolved | Full list (§5 Contracts › AtomMappingSpec): ≥ 0 and < atom count, no duplicates in any list, keep ∩ delete = ∅, keep ∪ delete = all template atoms, alignment ⊆ keep (≥ 3), anchors ⊆ keep. Strict now because relaxing later is non-breaking for existing graphs; TJ may relax the partition rule via a register/lore review. |
| R20 | F20 contributor rules invisible to agents | medium | resolved | Project rules go in `AGENTS.md` **after** the HACF END marker (the plan's PR #1 location; the block mechanism preserves it); no `CONTRIBUTING.md`. The starter's "update the Master Plan in the same PR" rule is not carried over (`PRDs/` is TJ's). |
| R21 | F21 CLI exit codes | low | resolved | Exit table in §5 Contracts › CLI; one `error: …` stderr line, no traceback. |
| R22 | F22 engine tags vs plan names | low | resolved | Freeze the plan's module-boundary names: `rdkit_ff`, `mace`, `uma_direct`, `pyscf_gpu_cpu`, `xtb_subprocess` (g-xTB is a `method` of `xtb_subprocess`). Adding a tag later does not change existing keys. |
| R23 | F23 ThermoConfig gas-phase hole | low | resolved | Concentration is a required-positive float defaulting to 1.0, `None` forbidden; α and B_av are fields with Grimme defaults. |
| R24 | F24 unowned files | low | resolved | `files:` globs per node in §5 Blast radius; scaffold owns `docs/**`, the five empty packages and root config. |
| R25 | F25 payload volume | low | resolved (contract) / out of scope (sidecars) | v0.1.0 stores payloads as canonical JSON `TEXT` plus `payload_sha256`; sidecar blobs deferred to the first version storing Hessians. |
| R26 | F26 US-004 bundles feature and acceptance | low | resolved | Split into US-004a (slices 04–05) and US-004b (slice 07). |
| R27 | F27 missing negative constraints | low | resolved | All eight adopted into §6. |
| R28 | Part B §1: "RTX 5060" vs 5060 Ti; "8 GB ceiling detection" meaning | — | resolved | Host card is the 5060 Ti; "ceiling detection" = detecting total VRAM from which the budget is computed (no class flag). |
| R29 | Part B §2: architect default "full runtime set" rationale; smoke JSON checked how | — | resolved | Base runtime set declared now (rationale holds: it is permissive and audited); extras follow F1/F2. The smoke JSON is checked by field values (status, tolerances, sha), not golden text — still not a novel output. |
| R30 | Part B §2/§6: "in-process dependency" undefined; `mace` importing `ase` | — | resolved (TJ Q1 A) | `ase`/`matscipy` may be installed as transitive deps of the MLIP extras; `eta_rxncat` never imports them (slice 06 AST test). |
| R31 | Part B §7: missing risks (unresolvable extras, CUDA mixing, stale cache, living plan) | — | resolved | Added to §7. |
| R32 | Part B §8: every metric a command + expected result | — | resolved | §8 rewritten as commands. |
| R33 | Part C Q1, Q2 (TJ-only) | — | resolved | TJ: "Q1 A, Q2 A" (see R1, R2). |
| R34 | Replan (TJ, row `qitem-20261122123807-a377da3572ef57f8`): README and CHANGELOG "like HACF, OIN-SMILES, and eta-skills" | — | resolved | New slice 08 `08-repo-identity`: sibling-pattern README (logo 200×200 header, banner hero, pitch, badges, TOC, eight sections) that keeps slice 01's US-010 content and claims only what v0.1.0 builds (Roadmap marked "Planned, not yet built"); Keep a Changelog 1.1.0 + SemVer `CHANGELOG.md` with `[Unreleased]` only. Per-release CHANGELOG upkeep (v0.1.0 … v1.0.0) belongs to the scribe (docs+commit step). Slice 01, mid-build, is not changed. |
| R35 | Replan (TJ): author "Thomas J. L. Mustard Ph.D." "In the README, LICENSE, and everywhere else" | — | resolved | Slice 08: LICENSE line 3, `pyproject` authors (no email), README License section; no CITATION.cff in v0.1.0. Guard `tests/unit/test_identity.py` (filesystem only) scans project-owned files and rejects every other `Thomas/Tom/TJ/T. … Mustard` form; it excludes `PRDs/`, HACF-installed files, the HACF block of `AGENTS.md`, `docs/prd/**` (verbatim reference copies), `missions/`, `lore/`, `spec/`. Surname-first literature citations stay as published. |
| R36 | Replan (TJ): logo "to use as the icon in the README"; banner "beside the icon. And if it is needed in the README" | — | resolved | `media/logo.png` (1024×1024 RGBA, transparent, sha256 `3b2a0b76…`) and `media/banner.webp` (2576×1438, sha256 `5ec0e886…`) copied byte for byte from `~/.hacf/eta-rxncat-hacf/incoming/media/`. Banner used as a full-width hero under the header; its own text is not copied, so the title and tagline carry "Eta-RxnCat". |
| R37 | Replan: build order with slice 08 | — | resolved | Slice 08 depends on 01–06 (the README describes what they built); slice 07 now also depends on 08, so GPU acceptance stays last. Build order: 01, 02, 03, 04, 05, 06, 08, 07. |
| R38 | Replan 2 (builder, slice 01 blocked): the HACF pre-commit hook runs `ruff check/format --check -- <staged .py>` with explicit paths; ruff then uses the starter's nested `pyproject.toml` (no excludes), so the 16 starter `.py` files cannot be committed | — | resolved | Verified by resolve (ruff 0.17.6, scratch copy). For explicit paths, ruff uses the **nearest** config's exclude patterns but enforces them only when the **root** config sets `force-exclude = true`; neither half alone works, which is why the builder's root-only attempt failed. Fix: root `force-exclude = true` plus one declared gate file `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.ruff.toml` (`exclude = ["*"]`), which outranks the starter `pyproject.toml`. All 23 starter files are committed verbatim, so TJ's instruction stands and no TJ question is needed. The proof becomes "23 verbatim + 1 gate file". A bad `src/` file is still caught. Hook and `.agents/` untouched; no `--no-verify`. |
| R39 | Replan 2 (builder D-037): `ruff check .` / `format --check .` fail on HACF scripts under `.agents/` (120 errors / 12 files), which we may not edit | — | resolved | Root ruff `extend-exclude = ["docs/prd", ".agents"]`; slice 01 spec updated so the audit checks the new value. Extends R4. |
| R40 | Replan 2 (TJ, 12:43Z via advisor): banner regenerated | — | resolved | Supersedes R36's banner facts: `media/banner.webp` is now 2576×1274, sha256 `ca80c101…`, and reads "Eta-RxnCat" with the full tagline and icon, so slice 08 drops the "don't copy banner text" caveat. The superseded `old-catalysis-engine-banner.*` is never committed. |

### Seed deviations

| Slice | Seed field | Was | Now | R-row |
|---|---|---|---|---|
| OPR.0.1.0.7 `07-gpu-acceptance` | `depends_on` | OPR.0.1.0.1–.6 | OPR.0.1.0.1–.6, OPR.0.1.0.8 | R37 |
| OPR.0.1.0.8 `08-repo-identity` | (new slice) | — | depends on OPR.0.1.0.1–.6 | R34–R37 |
| OPR.0.1.0.1 `01-scaffold` | ruff config, Task 1b, starter count proof, hook proof | `extend-exclude = ["docs/prd"]`; `ls-files docs/prd/v0.1.0` = 23 | `force-exclude = true`, `extend-exclude = ["docs/prd", ".agents"]`; gate `.ruff.toml`; `ls-files …/Eta-RxnCat-v0.1.0` = 24 (23 verbatim + gate) | R38, R39 |
| OPR.0.1.0.8 `08-repo-identity` | banner sha/size, oracle | `5ec0e886…`, 2576×1438 | `ca80c101…`, 2576×1274 | R40 |

### Blast radius

Greenfield: `spec/compiled/architecture.yml` **does not exist**, so no existing node is touched.
**None of these node ids is in the ledger yet**; slice 01's builder runs
`python3 .agents/scripts/hyper_ledger.py init` if the file is absent, and each slice's builder
registers its own node with `hyper_ledger.py ensure-node --from-spec <slice SPEC.md> --dimension
Module`.

| Node id | Slice | Owns (`files:`) | depends_on |
|---|---|---|---|
| `eta_rxncat_scaffold` | 01 (06 extends) | `pyproject.toml`, `uv.lock`, `.python-version`, `.github/**`, `README.md`, `AGENTS.md`, `.gitignore`, `docs/**`, `src/eta_rxncat/__init__.py`, `src/eta_rxncat/py.typed`, `src/eta_rxncat/{engines,conformers,mapping,optimize,orchestrator}/**`, `tests/unit/test_package.py`, `tests/conftest.py` | — |
| `eta_rxncat_core` | 02 | `src/eta_rxncat/core/**`, `tests/unit/core/**`, `tests/data/**` | — |
| `eta_rxncat_store` | 03 | `src/eta_rxncat/store/**`, `tests/unit/store/**` | `eta_rxncat_core` |
| `eta_rxncat_hw_probe` | 04 | `src/eta_rxncat/utils/**`, `tests/unit/utils/**`, `tests/gpu/**` | — |
| `eta_rxncat_cli` | 05 | `src/eta_rxncat/cli.py`, `src/eta_rxncat/__main__.py`, `tests/unit/cli/**` | `eta_rxncat_core`, `eta_rxncat_hw_probe` |

Slice 07 changes only `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` (owned by the scaffold node).
Slice 08 (scaffold node) adds `CHANGELOG.md`, `LICENSE`, `media/**` and `tests/unit/test_identity.py` to that node's `files:` via `hyper_ledger.py ensure-node --files` if absent.

### Execution checklist (the build loop's queue, in order)

1. `01-scaffold` — scaffold, gates, licence gate, unpack, both registers seeded. *(compiled)*
2. `02-core-schemas` — core models, loader, validator. *(compiled; depends on 01)*
3. `03-artifact-store` — cache key and store. *(compiled; depends on 02)*
4. `04-hw-probe` — probe, report API, smoke implementation (CPU-audited). *(compiled; depends on 01)*
5. `05-cli` — `hardware-check`, `validate`, exit table. *(compiled; depends on 02, 04)*
6. `06-optional-extras` — `gpu`, `mlip-mace`, `mlip-uma` (conflicting), cu128 torch index,
   per-extra licence gate. *(compiled; depends on 04)*
7. `07-gpu-acceptance` — the team's GPU run and `GPU_SMOKE_RESULT.json`. *(compiled; depends on
   01–06)*

8. `08-repo-identity` — README/CHANGELOG/author name/media. *(compiled; replan R34–R37; depends on
   01–06; built before 07)*

Build order: 01, 02, 03, 04, 05, 06, 08, 07. The feature is done when slice 07 audits PASS.

### Dependency direction
- `core` imports only `numpy`, `pydantic`, `pyyaml` and the stdlib.
- `store` imports `core` and the stdlib (`sqlite3`, `hashlib`, `json`).
- `utils` imports nothing from the package; `torch`, `gpu4pyscf`, `cupy`, `pyscf` only inside
  functions.
- `cli` imports `core` and `utils`; never `store` in v0.1.0.

### The discrepancy register (TJ, Q2; closed inventory per F15)
- **Where:** `docs/prd/v0.1.0/DISCREPANCIES.md`, committed. Written by each slice's builder in the
  same commit as its code; checked by the audit; fixes decided by TJ only.
- **Inventory (closed):** one row per starter item, by area:
  - each Python module under `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/`: every top-level public name
    (no leading `_`), and for each public class every public field and public method;
  - `pyproject.toml`: every key of `[project]` (each dependency entry its own row),
    `[project.optional-dependencies]`, `[project.scripts]`, `[build-system]`, and every key of
    each `[tool.*]` table;
  - `.github/workflows/ci.yml`: each step; `.gitignore`: each line;
  - SQL: the table, each column, each index; CLI: each subcommand, argument, output and exit
    behaviour;
  - the fixture: each top-level key and each key of node, edge and template objects;
  - `AGENTS.md`, `README.md`: each section heading;
  - starter tests: each test function, mapped to the rewrite test covering it or `dropped`.
  Plus one `added` row for each rewrite public name, config key, CLI argument or SQL column absent
  from the starter. Cosmetic differences (formatting, comments, docstring wording) are not rows.
- **Row format:**

  | ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
  |---|---|---|---|---|---|---|
  | D-001 | hw_probe VRAM budget | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:NN` `0.80 × total` | `src/eta_rxncat/utils/hw_probe.py:NN` min(6.5 GiB, total) | changed | Master Plan: "~6.5 GB VRAM budget"; F12 units GiB | open |

  `Disposition` ∈ `same`, `changed`, `dropped`, `added`. `Status` ∈ `open`, `accepted`, `fix`;
  builders write `open` only.

### The plan-copy register (TJ, 07:45Z; F16)
- **Where:** `docs/prd/PLAN_DISCREPANCIES.md`, committed; written in slice 01.
- **Command (pinned):** for each zip,
  `unzip -p PRDs/<zip> '*/Eta-RxnCat_Living_Master_Plan.md' > <tmpdir>/<version>.md`, then
  `LC_ALL=C diff -U0 <tmpdir>/<version>.md PRDs/Eta-RxnCat_Living_Master_Plan.md` (GNU diffutils).
  Zips whose copy is byte-identical to `PRDs/` produce no rows. One row per `@@` hunk, deduplicated
  across zips with the same copy sha256.
- **Header:** the command, the sha256 of `PRDs/Eta-RxnCat_Living_Master_Plan.md`, and a table of
  each zip with the sha256 of its copy. If the `PRDs/` sha changes, the register is stale; the next
  version's architect regenerates it (row ids kept where the hunk text is unchanged).
- **Row format:** | ID | Version(s) affected | Section / PR | Authoritative text (`PRDs/…`) | Zip
  copy text | Zips carrying this copy | Build follows | TJ status |. **PD-001** is the ~60-atom hunk
  (status `decided`, TJ Q1); PD-002… follow diff order. Every other row: build follows `PRDs/`,
  TJ status `open`.

### Contracts

All models: Pydantic v2, `model_config = ConfigDict(extra="forbid", frozen=True)`. Integers that
carry chemistry (`charge`, `spin_multiplicity`, `count`, `priority`, `rank`, indices) are
`StrictInt`, rejecting `bool`, `str` and `float`.

**MolecularState** — `symbols: list[str]` (≥ 1, each an exact canonical symbol for Z 1–118:
`Fe` ok, `fe`/`FE`/`Xx` rejected); `coordinates: list[list[float]]` in Å, N×3, all finite;
`charge: StrictInt` (required, no default); `spin_multiplicity: StrictInt ≥ 1` (2S+1, required, no
default); `active_atom_indices: list[StrictInt]` (default `[]`, unique, 0 ≤ i < N);
`metadata: dict[str, str | int | float | bool]` (default `{}`). Electron check:
n_e = ΣZ − charge; n_e ≥ 0, `spin_multiplicity − 1 ≤ n_e`, and
`(n_e − (spin_multiplicity − 1)) % 2 == 0` (neutral H₂O with multiplicity 2 raises).

**AtomMappingSpec** — ordered 0-based `keep`, `delete`, `alignment`, `anchors`
(`list[StrictInt]`, `anchors` default `[]`). Invariants, each a test: every index ≥ 0; no
duplicate within any list; keep ∩ delete = ∅; alignment ⊆ keep and `len(alignment) ≥ 3`;
anchors ⊆ keep. Checked at `TemplateGeometry` level against the template atom count N: every
index < N and keep ∪ delete = {0 … N−1}. Order is preserved through YAML/JSON round-trips.

**StageConfig** — `kind ∈ {conformer_search, constrained_preopt, geometry_opt, frequency,
single_point}`; `engine ∈ {rdkit_ff, mace, uma_direct, pyscf_gpu_cpu, xtb_subprocess}`;
`method: str` (non-empty; the literal `default` in any case is rejected); `basis: str | None`
(required non-empty iff `engine == pyscf_gpu_cpu`, else must be `None`); `solvation: Solvation`
(default model `none`); `frozen_atom_indices: list[StrictInt]` (default `[]`, unique, ≥ 0;
non-empty required when `kind == constrained_preopt`); `options: dict[str, str | int | float |
bool]` (default `{}`, finite floats). **Solvation** — `model ∈ {none, ddcosmo, pcm, alpb}`,
`solvent: str | None`, `dielectric: float | None` (> 0). `none` requires both `None`; any other
model requires at least one. `ddcosmo`/`pcm` only with `pyscf_gpu_cpu`; `alpb` only with
`xtb_subprocess`.

**EngineIdentity** — `name` (one of the engine tags), `version: str` (non-empty), `model: str |
None` (weights id, e.g. `uma-s-1.2.1`). Required to build a cache key; supplied by engines from
v0.2.0.

**ThermoConfig** — `entropy_model: Literal["grimme_qrrho"]` (default); `temperature_k: float = 298.15`;
`pressure_atm: float = 1.0`; `standard_state_mol_l: float = 1.0` (never `None`);
`qrrho_cutoff_cm1: float = 100.0` (ω₀); `qrrho_alpha: float = 4.0`;
`qrrho_rotor_moment_kg_m2: float = 1.0e-44` (B_av). Every numeric field > 0 and finite.

**Component** — `state: MolecularState`, `count: StrictInt ≥ 1` (stoichiometric coefficient),
`label: str | None`. **TemplateGeometry** — `id: str`, `rank: StrictInt ≥ 1`,
`components: list[Component]` (≥ 1), `mapping: AtomMappingSpec | None`. The template's atom
index space is the concatenation of its components' atoms in listed order (each component once,
independent of `count`).

**ReactionNode** — `id` (`^[A-Za-z][A-Za-z0-9_.-]*$`), `label: str`, `kind ∈ {reactant,
intermediate, transition_state, product, off_cycle_sink}`, `priority: StrictInt ≥ 1`,
`templates` (≥ 1, unique `id` and unique `rank` within the node), `stages: list[StageConfig] |
None` (`None` → the graph's `default_stages`), `pruning_rules: list[str]` (rule ids, default
`[]`). All templates of a node have equal Σ(count × charge) and equal element multiset
Σ(count × symbols).

**ReactionEdge** — `source`, `target` (existing node ids), `label: str | None`. Self-loops and
duplicate (source, target) pairs rejected; cycles allowed.

**PruningRule** — `id` (unique), `description: str`, `parameters: dict[str, str | int | float |
bool]`. Validated as a schema and by reference only; never evaluated in v0.1.0.

**ReactionGraph** — `schema_version: Literal[1]` (required), `name: str`, `nodes` (≥ 1, unique
ids), `edges`, `default_stages: list[StageConfig]` (default `[]`), `thermo: ThermoConfig`
(default), `pruning_rules: list[PruningRule]` (default `[]`). `priority_order()` returns node ids
sorted by `(priority, id)`.

**Loader** — `load_reaction_graph(path: Path) -> ReactionGraph`. `.yaml`/`.yml` via a
`yaml.SafeLoader` subclass that raises on a duplicate mapping key (naming the key and line);
`.json` via `json.loads` with an `object_pairs_hook` that raises on a duplicate key. Any other
extension raises naming it. All failures raise one `GraphValidationError` whose message names the
offender. `dump_reaction_graph_json(graph) -> str` for round-trips.

**Cache key** (`key_schema = 1`) — canonical JSON = `json.dumps(obj, sort_keys=True,
separators=(",", ":"), ensure_ascii=True, allow_nan=False)`; hash = sha256 hex.
- `geometry` = `{symbols, coordinates, charge, spin_multiplicity, active_atom_indices}` with each
  coordinate `round(x, 5)`, `-0.0` → `0.0`, written as a fixed-point string `f"{v:.5f}"`;
  `active_atom_indices` sorted.
- `stage` = `{kind, engine, method, basis, solvation, frozen_atom_indices (sorted), options}` with
  integral floats in `options` (and `dielectric`) written as ints; plus `engine_identity`
  `{name, version, model}`.
- `geometry_hash = sha256(canon(geometry))`, `stage_hash = sha256(canon(stage))`,
  `key = sha256(canon({"key_schema": 1, "geometry_hash": …, "stage_hash": …}))`.
- `metadata` is not keyed. A field added to a model is keyed only by a deliberate `key_schema`
  bump; old keys then miss (no migration). One key per stage, never per bundle.

**Store** — `ArtifactStore(path: Path)` opens/creates the SQLite **file** at `path`; the parent
directory must exist (else `FileNotFoundError`); nothing else is created. Pragmas:
`journal_mode=WAL`, `busy_timeout=5000`, `user_version=1` (a new file is stamped 1; any other
non-zero value raises `StoreSchemaError`). Table `stage_artifacts(key TEXT PRIMARY KEY,
key_schema INTEGER, geometry_hash TEXT, stage_hash TEXT, stage_kind TEXT, engine TEXT,
engine_version TEXT, status TEXT, payload_json TEXT, payload_sha256 TEXT, created_at_utc TEXT,
updated_at_utc TEXT)`, indexes on `geometry_hash` and `(stage_kind, engine)`.
- Status ∈ `pending, running, completed, failed`. `put(key, status, payload)`: new key → insert;
  existing non-completed row → update; existing completed row with the same `payload_sha256` and
  `status=completed` → no-op (idempotent); any other write to a completed row →
  `ArtifactConflictError` and the row is unchanged. `invalidate(key)` deletes a row (the only way
  to replace a completed artifact).
- `get(key)` returns the payload only for `completed`, else `None`. `query(stage_kind=…,
  engine=…)` lists keys.
- Payload: canonical JSON text (`allow_nan=False`); sidecar blobs deferred (R25).

**Hardware probe** — `probe_hardware() -> HardwareReport` (pure read; never raises for a missing
package). `HardwareReport` JSON: `report_schema: 1`, `python_version`, `platform`,
`torch {installed, version, cuda_available, cuda_version}`, `gpu {name, compute_capability,
total_vram_bytes, total_vram_gib, free_vram_bytes} | null`, `gpu4pyscf {installed, version}`,
`vram_budget_gib: 6.5`, `vram_budget_bytes = min(6.5 × 2³⁰, total) | null`, `flags: list[str]`,
`notes: list[str]`. Flags: `cuda_unavailable`, `torch_missing`, `torch_cuda_below_12.8`,
`gpu4pyscf_missing`, `gpu4pyscf_below_1.8.0`. Versions compared by numeric dotted prefix.

**GPU smoke** — `run_smoke(timeout_s: float = 600.0) -> SmokeResult`, run in a child process
killed at the timeout. Skipped (exit 3) when torch, gpu4pyscf or CUDA is unavailable, with the
reason. Otherwise: H₂O (O 0 0 0.1173; H 0 0.7572 −0.4692; H 0 −0.7572 −0.4692 Å), charge 0,
singlet, RHF/STO-3G on GPU4PySCF and on CPU PySCF; float64 512×512 matmul (seeded) on CUDA vs CPU,
TF32 off. **Pass** (exit 0) iff both SCFs converged, |ΔE| ≤ 1e-6 Eh, the GPU MO coefficients are a
CuPy array, the CUDA result tensor's device type is `cuda` and its max-abs-diff ≤ 1e-9, all within
the timeout. Anything else is fail (exit 1) with the reason. JSON: `result_schema: 1`, `status`,
`reason`, `scf {converged_gpu, converged_cpu, energy_gpu_eh, energy_cpu_eh, abs_diff_eh,
tolerance_eh, mo_on_device, seconds}`, `torch_op {device, max_abs_diff, tolerance, seconds}`,
`total_seconds`, `timeout_s`, `host` (the HardwareReport). Product code never calls `git`.

**CLI** (`argparse`, console script `eta-rxncat = "eta_rxncat.cli:main"`):

| Command | Exit 0 | Exit 1 | Exit 2 | Exit 3 |
|---|---|---|---|---|
| `hardware-check` | report printed (flags inside JSON) | — | usage error | — |
| `hardware-check --smoke` | smoke pass | smoke fail | usage error | skipped |
| `validate <path>` | valid | invalid / unreadable / unsupported extension | usage error | — |

`validate` success stdout, exactly: `OK <path>`, `nodes: <N>`, `edges: <M>`,
`priority_order: <id>,<id>,…` (four lines). Every failure: one line `error: <message>` on stderr,
no traceback.

### Dependencies (slice 01; extras in 06)
- Runtime: `numpy`, `scipy`, `pydantic>=2`, `pyyaml`, `rdkit`, `geometric`, `pyscf` (all
  permissive). No optional extras until slice 06.
- Extras (slice 06, TJ Q1 A / Q2 A): `gpu` = torch>=2.7.0 (cu128 index), `gpu4pyscf-cuda12x>=1.8.0`,
  `cupy-cuda12x`; `mlip-mace` = torch, `mace-torch`; `mlip-uma` = torch, `fairchem-core`;
  `mlip-mace` ⟂ `mlip-uma` via `[tool.uv] conflicts`.
- Dev: `pytest`, `pytest-cov`, `ruff`, `mypy`, `types-PyYAML`, `pip-licenses`.
- Any pin that differs from the starter is a register row.

## 6. Negative Constraints
- **DO NOT** import `ase`, `sella`, `tblite` or `psi4` anywhere in `src/eta_rxncat/`.
- **DO NOT** add a runtime dependency that fails the §5 allow-list; never add a licence exception
  without TJ's decision through the lead.
- **DO NOT** give `charge` or `spin_multiplicity` a default, or accept non-strict ints for them.
- **DO NOT** accept duplicate keys in YAML or JSON graph files.
- **DO NOT** bundle multiple stages into one cache key, or hash a raw `model_dump()`.
- **DO NOT** overwrite a `completed` store row through `put`.
- **DO NOT** create the store directory or any file other than the path the caller gave.
- **DO NOT** implement any compute engine, optimizer, mapper, scheduler or pruning evaluator.
- **DO NOT** use `yaml.load`, `yaml.full_load`, `yaml.unsafe_load` or `pickle`; only
  `yaml.SafeLoader` or a subclass of it.
- **DO NOT** import `torch`, `pyscf`, `gpu4pyscf`, `cupy`, `rdkit`, `mace` or `fairchem` when
  importing `eta_rxncat.core` or running `eta-rxncat validate` (tested via `sys.modules` in a
  subprocess).
- **DO NOT** invoke `git` or access the network from package code, at import time or in unit tests.
- **DO NOT** let ruff, pytest or mypy read anything under `docs/prd/`.
- **DO NOT** write to `tests/fixtures/` or `tests/candidate_outputs/`.
- **DO NOT** copy the starter files into `src/` or `tests/`, or import from `docs/prd/`.
- **DO NOT** change code to "fix" a register entry without TJ's decision.
- **DO NOT** unpack any zip into the repo other than v0.1.0; read plan copies with `unzip -p` only.
- **DO NOT** write into, move or delete anything in `PRDs/`.
- **DO NOT** edit HACF managed blocks in `AGENTS.md`, `CLAUDE.md` or `.gitignore`.
- **DO NOT** make a GPU a requirement for any unit test or CI step.
- **DO NOT** push, tag or open a PR.

## 7. Risks & Mitigation
- **Rewrite drift from TJ's domain intent.** *Mitigation:* the closed-inventory register makes
  every difference reviewable (Q2); §5 pins the domain-critical behaviour.
- **Strict mapping partition (R19) rejects graphs TJ considers valid.** *Mitigation:* the rule is
  in the register and lore as PROPOSED; relaxing it later is non-breaking.
- **Unresolvable optional extras (F1).** *Mitigation:* TJ chose conflicting extras (Q2 A); slices
  01–05 declare none; slice 06 proves `uv lock` and stops with the output if an engine cannot
  lock against cu128 torch.
- **CUDA 12/13 runtime mixing (F10).** *Mitigation:* one CUDA-12 line pinned in slice 06;
  `hardware-check` reports the torch CUDA version.
- **Stale cache after an engine upgrade (F5).** *Mitigation:* `EngineIdentity.version` is keyed.
- **Living `PRDs/` plan invalidates the plan-copy register (F16).** *Mitigation:* the header sha
  marks staleness; regeneration belongs to the next architect.
- **GPU gate depends on this host's driver/CUDA/wheel state.** *Mitigation:* by TJ's design (Q3)
  it blocks acceptance; a failure is a finding with output, no workaround.
- **Heavy installs (`rdkit`, `pyscf`) slow CI.** *Mitigation:* `uv` cache in CI.

## 8. Success Metrics
Each on a fresh local clone (`git clone <repo> <tmp> && cd <tmp> && uv sync --locked`):
- `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest` and the
  licence gate → exit 0; `ci.yml` runs exactly these.
- `uv run eta-rxncat validate tests/data/reaction_graphs/example_reaction_graph.yaml` → exit 0 and
  the four-line output; each US-007 invalid case → exit 1, one `error:` line.
- `uv run eta-rxncat hardware-check` → exit 0, JSON per contract; on this host
  `compute_capability: "12.0"` and `vram_budget_gib: 6.5` (after slice 06 installs torch).
- `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` → `status: "pass"` and a commit sha that is an ancestor
  of HEAD (slice 07).
- `docs/prd/v0.1.0/DISCREPANCIES.md` → every closed-inventory item has a row.
- `docs/prd/PLAN_DISCREPANCIES.md` → row count equals the pinned command's `@@` count (14 today).

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.1.0.1 | slices/01-scaffold | Create the uv-managed MIT package skeleton with locked deps, strict ruff/mypy/pytest gates, a runtime-only allow-list licence gate and CI, unpack the v0.1.0 reference into an excluded docs/prd/v0.1.0/, and seed both discrepancy registers. |
| OPR.0.1.0.2 | slices/02-core-schemas | Implement the strict Pydantic v2 core data contracts and a duplicate-key-rejecting YAML/JSON ReactionGraph loader and validator, with a test for every invariant. |
| OPR.0.1.0.3 | slices/03-artifact-store | Implement the canonical versioned per-stage cache key and a WAL-mode SQLite artifact store whose completed artifacts are never silently overwritten. |
| OPR.0.1.0.4 | slices/04-hw-probe | Implement the typed hardware probe with the 6.5 GiB VRAM budget and a GPU-vs-CPU smoke test with a numeric pass criterion, proven on the CPU path. |
| OPR.0.1.0.5 | slices/05-cli | Implement the eta-rxncat console script with hardware-check [--smoke] and validate, a fixed exit-code table and one-line stderr errors. |
| OPR.0.1.0.6 | slices/06-optional-extras | Declare the gpu, mlip-mace and mlip-uma optional extras (MLIP extras conflicting) with torch from the PyTorch cu128 index, and a per-extra licence gate that exempts only NVIDIA CUDA wheels and the MLIP extras' transitive LGPL packages, per TJ's Q1 A / Q2 A. |
| OPR.0.1.0.7 | slices/07-gpu-acceptance | Run the GPU smoke and gpu-marked tests once on a clean tree on this host's RTX 5060 Ti and commit docs/prd/v0.1.0/GPU_SMOKE_RESULT.json with the commit sha, as v0.1.0's acceptance gate. |
| OPR.0.1.0.8 | slices/08-repo-identity | Give the repo the sibling-project public face (logo and banner README, Keep a Changelog CHANGELOG, media/) and the author form Thomas J. L. Mustard Ph.D. everywhere the project writes an author, with a filesystem test that blocks any other form; the README claims only what v0.1.0 builds. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
