---
id: OPR.0.5.0.15
slice: 15-pyscf-cartesian-basis
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Add a keyed cartesian_basis option to the pyscf_gpu_cpu engine (default False, written into the resolved stage only when True so every existing PySCF key stays byte-identical) so R9 can reproduce Gaussian 6D 6-31G(d) references."
depends_on: [OPR.0.5.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/pyscf_gpu_cpu/**", "tests/unit/engines/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/engines, tests/unit/store]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 PySCF Cartesian basis option (engines)

## Intent

Add a keyed `cartesian_basis: bool` option to the `pyscf_gpu_cpu` engine (default `False`), which
builds every PySCF `Mole` for the stage with Cartesian basis functions (`mol.cart = True`). The
option is written into the resolved stage **only when `True`**, so every existing PySCF resolved
stage and cache key stays byte-identical. Mission R30, ADR-0041 (PROPOSED). Replan 2, from slice 07's stop report
(`qitem-20261124064156-cb552525`).

Context the builder needs:
- **Why (slice 07's measurement, R30).** Liu's M06-2X/6-31G(d) reference energies come from
  Gaussian, whose 6-31G(d) uses six Cartesian d functions (6D). PySCF defaults to five spherical
  ones. On TJ's control `TS1a_n.xyz`, eta's engine (spherical, 132 AOs) gives ΔE = +3.385e-3 Eh,
  outside R9's 1e-4. Raw PySCF with `mol.cart = True` (140 AOs) gives ΔE = −6.3e-5 Eh, inside.
  The grid and the transcription are fine; the difference is the definition of the basis.
- **Name.** `cartesian_basis` names the basis-function convention (Cartesian rather than
  spherical harmonic), not PySCF's attribute. It means Cartesian functions for **every** angular
  momentum, which is what PySCF's `mol.cart` does.
- **Cache keys (R30, ADR-0041).** `resolve_options` puts every option of
  the table into the resolved stage (ADR-0016). Adding the option the plain way would add
  `"cartesian_basis": false` to every resolved PySCF stage and change every existing PySCF key.
  So: declare `cartesian_basis` in `OPTIONS` as `OptionSpec(bool, False)` (type checking and
  unknown-key refusal stay as they are). Then, in the engine's `__init__`, right where
  `ladder_small_basis` is already rewritten into the keyed stage, **remove the key from the
  resolved options when its value is `False`**. Effects:
  - the default and an explicit `False` resolve to the same stage, with no key, as they did
    before this slice;
  - `True` adds `"cartesian_basis": true` and so a different key;
  - re-resolving an already resolved stage gives the same result (idempotent).

  Absent always means spherical; that meaning is fixed and can never be changed by a default.
  Changing the default to `True` would need an `ENGINE_IMPL` bump (2 → 3) and is out of scope.
  `ENGINE_IMPL` stays 2.
- **Which Moles.** `_build_mol` sets `cart=True` on every `Mole` it builds for a stage with the
  option on: the main basis, the ladder's small-basis projection and the VRAM estimate. The DF
  auxmol is built from that Mole by PySCF's `make_auxmol`. Read whether it inherits `cart`, and
  record what you find in the proof; do not override it.
- **GPU (one resolved stage for both devices, ADR-0018).** GPU4PySCF 1.9.2 (in
  `.venv-accept-gpu`) supports `mol.cart` in its SCF and DF code, with one exception: its
  `init_guess="atom"` path asserts "Spherical averaging for Cartesian basis not supported yet"
  (`gpu4pyscf/scf/hf.py`, the atom-guess builder). So `cartesian_basis=True` with
  `init_guess="atom"` is refused at construction with `EngineInputError` on **both** devices,
  so that one stage never behaves differently by device. `minao` and `huckel` stay allowed;
  measure `huckel` on GPU, and if it fails, refuse it the same way and record why.
- **Interfaces to read:** `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py` (`OPTIONS`,
  `__init__`, `_build_mol`, the ladder, `estimate_vram_bytes`), `engines/options.py`,
  `store/keys.py`, and `tests/unit/engines/test_pyscf_cpu.py` / `test_pyscf_gpu.py` /
  `tests/unit/store/test_store_keys.py` for their fixtures and markers.

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  geomeTRIC may run only as a black box through `geometric-optimize` and its `--help` text.
  (PySCF and GPU4PySCF are engines, not TS optimizers; reading them is allowed.)
- **Clean room, nMAP (v0.4.0 Q1).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach". Never open, clone, fetch or search Eta_Scripts or nMAP (GitHub,
  `~/PROJECTS/cleanroom-nmap`, a cache, a web or code search); only its `TRANSFER_LOG.md` may be
  read. Never message the clean-room seats.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.5.0`, cut re-entrantly from Base (the
  mission commit on main, parent `0d2a8d3`). One code commit per slice unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff. Every commit ends with exactly
  two footer lines, `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, `<version>` read from
  `.agents/hacf-manifest.json` at commit time; no co-author or session trailer. Author "Thomas J.
  L. Mustard Ph.D." (repo-local git config). Never `--no-verify`, never rewrite history.
- **Code graph first.** The first command is `python3 .agents/scripts/hyper_codegraph.py index`;
  it must print `index: ok` (the red team saw `stale_index`). Anything else stops the slice. The
  graph only widens a blast radius.
- **Ledger.** Only through `hyper_ledger.py` / `hypergraph_updater.py`, never by hand. On an
  existing node, `ensure-node --id <node>` takes the **full** `--files` list (it replaces); count
  the node's globs before and after. No slice creates a node.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF v0.6.3.** No `HACF-install.sh` (never without `--ref`), no `HACF-uninstall.sh`, no
  `hyper_migrate.py apply`. On OpenRig 0.7.21, `hyper_spec.py`/`hyper_migrate.py` warn "outside
  the pinned contract", `hyper_spec.py proof` writes the proof natively and `hyper_migrate.py
  verify` skips `rig scope audit`: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git:
  every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host (shared with the hacf and cleanroom rigs).** Before any E2E, GPU, engine or full-suite
  run: `free -g` and `ps` for other rigs' heavy python/pytest/engine processes; if one is active,
  wait (poll at most every 5 minutes with Monitor or a background wait, never a foreground sleep)
  for GPU/E2E work; the full CPU unit suite may run serially beside another rig's small batches
  only with ≥ 6 G available. Record the check in the proof. GPU/E2E runs one at a time. Never kill
  another rig's process. The check and the heavy command are separate calls (or the check exits
  non-zero), never echo-then-run.
- **Engines.** Every xtb command sets
  `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (without it the
  xtb E2E skips with exit 0). UMA runs in `.venv-accept-uma` on CUDA. Every E2E command runs
  under coreutils `timeout 3600`; an expiry is stop-and-report with the output.
- **Lessons (mission R26):** unit-suffixed numeric keys (R54); no energy- or record-ordered list
  in a compared output (R55); one `gated_outcome` per test, `pending_*` fails under
  `ETA_RXNCAT_ACCEPTANCE=1` (R56); any reader of a store or runner payload checks `failed_reason`
  first (R50); re-dedup after any geometry change (v0.3.0 path unchanged); tolerances are measured
  before they are written, never guessed; the candidate rule (code commit C1 with a clean tree,
  E2E at C1, then a commit of only `tests/candidate_outputs/v0.5.0/*` as C2).
- **Required checks** (AGENTS.md), all exit 0 before each commit: `uv sync --locked`;
  `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv run pytest`;
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception (N1). No dependency changes here.
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it; never loosen a tolerance
  (TJ's or this SPEC's). Never use `AskUserQuestion`.
- **Never** push, tag or open a PR.
- **Slice 07 is paused mid-build in this tree.** Its uncommitted `tests/e2e/**` work must survive
  untouched. Stage and commit only this slice's files, by explicit path (never `git add -A` or
  `git add .`), and never stash, reset or check out over it.

## 1. The Confidence Mandate

**Score: 9/10.** The option, the key rule and the tests are fixed. The one point a measurement
settles is GPU behaviour beyond the `atom` guess (`huckel`, DF auxmol): the slice measures it and
refuses what fails, rather than assuming.

## Mini-requirements

1. **Option:** `"cartesian_basis": OptionSpec(bool, False)` in `PySCFEngine.OPTIONS`. Non-bool values are refused by the existing type rule.
2. **Keys unchanged (proof against the pre-slice code).** Before editing, at Start, compute and
   write into the test as literals two values for the default-option water stage the existing
   tests use (`RHF/STO-3G`, CPU):
   - `engine.stage.model_dump()` (the resolved stage);
   - `build_stage_key(water, engine.stage, engine.identity).key`.

   Do the same for one stage that sets non-default options (for example
   `density_fit=False, grids_level=4`). After the change, tests assert all of these:
   - the resolved stages and keys equal those literals byte for byte, both with the option
     omitted and with `cartesian_basis=False` given explicitly;
   - `"cartesian_basis"` is not in `engine.stage.options` in either case;
   - `ENGINE_IMPL == 2`;
   - the existing golden test in `tests/unit/store/test_store_keys.py` passes unmodified.

   The new tests go in `tests/unit/engines/`; nothing under `tests/unit/store/` changes.

   No committed v0.2.0–v0.4.0 fixture holds a PySCF key (`grep -rl pyscf_gpu_cpu tests/fixtures`
   is empty), so the pre-slice literals are the proof; say so in the proof.
3. **True is keyed:** with `cartesian_basis=True`, `engine.stage.options["cartesian_basis"] is
   True`, the key differs from the default's, and constructing a new engine from
   `engine.stage` gives an identical resolved stage (idempotent).
4. **It takes effect (CPU unit test, default suite):** for water/6-31G(d) with
   `cartesian_basis=True`, the built `Mole` has `cart == True` and `nao` equal to the spherical
   `nao` plus one per d shell. Water/6-31G(d) has one d shell on O, so 19 vs 18. The RHF energy
   differs from the spherical energy (record both values).
5. **Refusal:** `cartesian_basis=True` with `init_guess="atom"` raises `EngineInputError` at
   construction on CPU (no GPU needed for the test), and the message names both options. Measure
   whether `huckel` works on GPU: if it does, record it; if not, refuse it the same way.
6. **GPU parity (marker `gpu`, run in the proof under the host gate):** water M06-2X/6-31G(d),
   `cartesian_basis=True`, default DF: |E_gpu − E_cpu| ≤ 1e-6 Eh. That is the existing
   `test_pyscf_gpu.py` bound; do not tighten or loosen it. Both runs must be stable, and the GPU
   run must really be on cuda. Repeat with `density_fit=False`.
7. **Liu control (marker `gpu` + `acceptance`, in the proof only, not gated here):** `TS1a_n.xyz`
   through eta's engine with `cartesian_basis=True`. Record ΔE against Liu's −310.559154 and the
   AO count, both of which slice 07's stop report gave (−6.3e-5 Eh, 140 AOs). If ΔE is > 1e-4 Eh,
   stop and report: slice 07's R9 would fail again. Use slice 07's
   `tests/e2e/data/e2e5/xyz/TS1a_n.xyz` read-only, or TJ's committed copy; do not write it.
8. Every other PySCF test (CPU and, in the proof, GPU) passes unmodified.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; compute the MR 2 literals at Start.
- [x] Task 2: option, the remove-when-False rewrite, `_build_mol`'s `cart`, the `atom` refusal.
- [x] Task 3: tests for MR 2–5; required checks.
- [x] Task 4: host check; GPU runs for MR 6–7, as separate calls; record.
- [x] Task 5: commit by explicit path; updater for node `eta_rxncat_engines` (no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** change `ENGINE_IMPL`, any existing option's default, `resolve_options` or
  `store/keys.py`.
- **DO NOT** let `cartesian_basis=False` (implicit or explicit) appear in a resolved stage.
- **DO NOT** apply Cartesian functions selectively by angular momentum (no "6D 7F" emulation); the
  option is all-Cartesian, and the R30 limits say where that matches Gaussian.
- **DO NOT** touch `tests/e2e/**`, `tests/fixtures/**` or anything of slice 07, and change no
  other engine.
- **DO NOT** change R9's bound or slice 07's spec; resolve already amended slice 07.

## Proof contract

- [ ] The MR 2 literals, how they were computed at Start, and the passing equality tests.
- [ ] MR 4–5 test names; the cart/spherical AO counts and energies.
- [ ] MR 6 GPU−CPU differences (DF and non-DF) with the host check.
- [ ] MR 7: ΔE and AO count for `TS1a_n` through eta's engine.
- [ ] Whether the DF auxmol inherits `cart` (as read and measured).
- [ ] The required checks exit 0.

## Source material

- Mission R30 (new), R9, ADR-0016, ADR-0018, ADR-0041; slice 07's stop report
  `qitem-20261124064156-cb552525`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.1 (build order only)
