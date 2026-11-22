---
id: OPR.0.2.0.8
slice: 08-xtb-subprocess
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Provision the pinned xtb 6.8.0 binary outside the repo, start the licence inventory, and implement the xtb_subprocess engine: GFN2-xTB with explicit charge/spin and keyed ALPB in an isolated subprocess, with energy, gradient and a convention-checked Hessian."
depends_on: [OPR.0.2.0.4, OPR.0.2.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_engines
parent: null
hacf_touches: ["src/eta_rxncat/engines/**", "tests/unit/engines/**", docs/licence-inventory.md, AGENTS.md, docs/prd/v0.2.0/DISCREPANCIES.md, "docs/prd/v0.2.0/evidence/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/engines/test_xtb.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: xtb subprocess engine (`xtb_subprocess`), GFN2-xTB with ALPB, and the licence inventory

## Intent

Provision the official xtb 6.8.0 binary outside the repo, record it in a new licence inventory,
and implement `XTBSubprocessEngine` (tag `xtb_subprocess`). It runs GFN2-xTB with explicit charge
and spin and keyed ALPB solvation in an isolated subprocess, and returns energy, gradient and the
analytic Hessian in the project's convention.

Context the builder needs (self-contained).

TJ, 16:24Z (row `qitem-20261122162111-26e232a707f003e2`), verbatim: "Q2. A". Accept the xtb 6.8.0
binary (LGPL-3.0 plus bundled Intel MKL and ifx runtime) as a user-downloaded subprocess engine,
recorded in the licence inventory, never vendored (ADR-0021 PROPOSED).

Red team, verified against xtb 6.8.0:
- `--alpb SOLVENT [STATE]`, where STATE is `reference`, `bar1M` or `gsolv` (the default);
  `gsolv` vs `reference` differ by 3.33 kcal/mol;
- solvent names are case-insensitive;
- an unknown solvent → exit 128; an inconsistent `--uhf` → fatal, exit 128;
- `--hess` writes a `hessian` file (`$hessian`);
- the binary is static (MKL and ifx linked in).

The GitHub release asset (API digest) is `xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz`, 22,686,860 B,
`sha256:db090333361749ae0d9ccf0ce7c0035c0000f2ebad0847f6d77191d1954f4d68`. Its companion `.sha256`
file names it `xtb-bleed-…`, a provenance note to record.

Mission decisions:
- R7: ALPB state keyed, default `gsolv`; dielectric-only refused; solvent lowercased.
- R12: provisioning.
- R13: reference runs at `OMP_NUM_THREADS=MKL_NUM_THREADS=1`; energy ≤1e-10 Eh, gradient ≤1e-9
  Eh/Bohr; Hessian Cartesian Eh/Bohr², not mass-weighted, not projected.

The engine base is slice 04; the test set is in `tests/unit/engines/data/`.

## 1. The Confidence Mandate

**Score: 9/10.** Provisioning, argv and parsing are fixed. The residual is the exact convention
of xtb's `hessian` file, which this slice determines against FD of xtb gradients and records.

## Mini-requirements

1. Provisioning, a seat command recorded in the handoff (not product code, not a test):
   - download the asset URL above to `~/.local/share/eta-rxncat/xtb/6.8.0/`;
   - verify sha256 = `db0903…4d68` (stop on mismatch);
   - extract it there;
   - record `bin/xtb --version` and the path.
   
   Nothing goes into the repo.
2. `docs/licence-inventory.md` is new. It lists external, non-Python-wheel components the
   project uses but never ships. The first entries:
   - xtb 6.8.0: LGPL-3.0, statically bundled Intel MKL and ifx runtime (proprietary),
     user-downloaded, subprocess only, digest, TJ v0.2.0 Q2 A;
   - MACE-MP-0 medium weights: MIT (filled by slice 09);
   - UMA `uma-s-1p2p1` weights: `license: other`, gated (filled by slice 10).
   
   `AGENTS.md` project section: one line pointing at the inventory.
3. `engines/xtb_subprocess.py`, `XTBSubprocessEngine(Engine)`, `ENGINE_IMPL = 1`:
   - binary resolution: the runtime `binary` path, else `$ETA_RXNCAT_XTB`, else `shutil.which("xtb")`;
     missing → `EngineUnavailableError` naming the provisioning step;
   - `identity = EngineIdentity(name="xtb_subprocess", version="xtb <x.y.z>" parsed from --version, model=None)`;
   - `method` must be `gfn2`;
   - keyed: `accuracy` (float, 1.0), `etemp_k` (float, 300.0), `alpb_state`
     (`gsolv`|`bar1M`|`reference`, default `gsolv`), `engine_impl` (1);
   - runtime: `threads` (1), `timeout_s` (3600), `omp_stacksize` (`"1G"`).
4. Run:
   - write `input.xyz` (Å) in a fresh `tempfile.mkdtemp()` under `TMPDIR`;
   - argv: `[xtb, "input.xyz", "--gfn", "2", "--chrg", str(q), "--uhf", str(mult−1), "--acc", str(accuracy), "--etemp", str(etemp_k)]`;
   - add `["--alpb", solvent, alpb_state]` for ALPB, `["--grad"]` for forces, `["--hess"]`
     for a Hessian;
   - `subprocess.run(argv, cwd=tmp, env={…, "OMP_NUM_THREADS": t, "MKL_NUM_THREADS": t, "OMP_STACKSIZE": s}, capture_output=True, timeout=…)`,
     with no shell;
   - parse `energy` (Eh), `gradient` (Eh/Bohr → forces = −g) and `hessian`;
   - delete the temp dir on success. On failure keep it only if a runtime `keep_failed=True` is
     set.
   - Non-zero exit, timeout or missing output → `EngineRuntimeError` with the stderr/stdout tail.
5. ALPB:
   - a solvation model other than `none`/`alpb` → `EngineInputError`;
   - `alpb` with only a dielectric → `EngineInputError`;
   - the solvent name is lowercased in `engine.stage` (R7).
6. Hessian convention (R13): compare xtb's `hessian` file with central FD of xtb gradients (step
   0.005 Bohr) on water.
   - If the file is mass-weighted or projected, convert it to the project's convention or use FD
     (labelled).
   - Record the finding, with numbers, in `docs/prd/v0.2.0/evidence/xtb-hessian-convention.json`.
7. Register rows (status `open`) vs the starter's `XTBSubprocessEngine`: the name `xtb_gfn2-xtb` →
   the tag; argv; ALPB state; error handling.

## 3. Implementation Plan (Task List)

- [ ] Task 1: provisioning and the inventory (Mini-requirements 1–2).
- [ ] Task 2: the engine (Mini-requirements 3–5).
- [ ] Task 3: the Hessian convention check and record (Mini-requirement 6).
- [ ] Task 4: tests in `tests/unit/engines/test_xtb.py`:
  - marked `xtb` (skip with reason if no binary; fail under `ETA_RXNCAT_ACCEPTANCE=1`);
  - default-suite tests for argv building and parsing, using recorded fixture output files that
    the builder writes in `tests/unit/engines/data/xtb/` from a real run.
- [ ] Task 5: register rows; four gates; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** commit the binary or tarball, or put any xtb file in the repo other than small text
  fixtures.
- **DO NOT** run xtb in-process, through a shell, or in the repo directory.
- **DO NOT** pass an ALPB state other than the keyed one, or accept dielectric-only ALPB.
- **DO NOT** catch bare `Exception`. Catch `subprocess.TimeoutExpired`, `OSError` and parse
  errors by type.

## Proof contract

- [ ] `xtb`, all four cases, `threads=1`:
  - the engine's energy and gradient equal a hand run of the **same argv** (taken from the engine)
    in a separate temp dir: energy ≤1e-10 Eh, gradient ≤1e-9 Eh/Bohr.
- [ ] Literal argv (R4):
  - hydroxide contains `--chrg -1 --uhf 0`;
  - hydroxyl `--chrg 0 --uhf 1`;
  - the Pd anion `--chrg -1 --uhf 0`;
  - water in toluene contains `--alpb toluene gsolv`.
  
  Behavioural: hydroxyl at multiplicity 2 vs hydroxide at charge −1 give different energies.
- [ ] ALPB:
  - `alpb_state="reference"` vs the default differ by more than 1e-3 Eh for water in toluene (the
    red team saw 5.30 mEh), and the two keys differ;
  - `solvent="Toluene"` → `engine.stage` has `toluene`;
  - dielectric-only → `EngineInputError`;
  - an unknown solvent → `EngineRuntimeError` whose tail contains xtb's message.
- [ ] Hessian: the water Hessian matches FD of xtb gradients ≤1e-4 Eh/Bohr² after any conversion
  in Mini-requirement 6. It is symmetric, with `hessian_method` stated. The evidence file exists.
- [ ] Failures:
  - a fake binary that exits 1 → `EngineRuntimeError` with its stderr tail;
  - `timeout_s=0.01` → `EngineRuntimeError` mentioning the timeout;
  - a missing binary → `EngineUnavailableError` naming the provisioning step.
- [ ] `docs/licence-inventory.md` has the xtb entry with the digest and TJ Q2 A. The handoff shows
  `sha256sum` OK and `xtb --version`.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0. `ETA_RXNCAT_XTB=<path> ETA_RXNCAT_ACCEPTANCE=1 uv run pytest -m xtb tests/unit/engines/test_xtb.py`
  → exit 0, with 0 skipped.

## Source material

- Plan PR #4; TJ 16:24Z Q2 A; mission R4, R7, R12, R13; RedTeam F7, F12, F13 (measured
  behaviour); the starter `rdkit_xtb.py` (reference only); ADR-0021 (PROPOSED).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.4 (engine base), OPR.0.2.0.5 (test data directory)
