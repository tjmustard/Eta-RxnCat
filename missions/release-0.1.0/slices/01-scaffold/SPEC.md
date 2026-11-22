---
id: OPR.0.1.0.1
slice: 01-scaffold
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Create the uv-managed MIT package skeleton with locked deps, strict ruff/mypy/pytest gates, a runtime-only allow-list licence gate and CI, unpack the v0.1.0 reference into an excluded docs/prd/v0.1.0/, and seed both discrepancy registers."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: blocked
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [pyproject.toml, uv.lock, ".python-version", ".github/**", README.md, AGENTS.md, ".gitignore", "docs/**", src/eta_rxncat/__init__.py, src/eta_rxncat/py.typed, "src/eta_rxncat/engines/**", "src/eta_rxncat/conformers/**", "src/eta_rxncat/mapping/**", "src/eta_rxncat/optimize/**", "src/eta_rxncat/orchestrator/**", tests/unit/test_package.py, tests/conftest.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, sync, "--locked"], [uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Repo scaffold, quality gates, licence gate and discrepancy registers

## Intent

Create the uv-managed MIT package skeleton with committed lockfile, strict ruff/mypy/pytest gates,
a runtime-only allow-list licence gate and CI, unpack the v0.1.0 reference zip into an
excluded `docs/prd/v0.1.0/`, and seed both discrepancy registers.

Context the builder needs (self-contained): Eta-RxnCat is a permissively licensed (MIT/BSD/Apache)
computational-chemistry workflow library. `PRDs/Eta-RxnCat_Living_Master_Plan.md` is the
authoritative plan; `PRDs/Eta-RxnCat-v0.1.0.zip` holds a **reference-only** starter (TJ: "B use
it as reference only. Keep a list of the discrepancies…"). You write fresh code; you never copy
starter files into `src/` or `tests/`. `PRDs/` is read-only. Never push.

**Ledger:** `spec/compiled/architecture.yml` does not exist yet. Before registering the node, run
`python3 .agents/scripts/hyper_ledger.py init` if the file is absent, then
`python3 .agents/scripts/hyper_ledger.py ensure-node --from-spec <this SPEC.md> --dimension Module`.
Node `eta_rxncat_scaffold` is **not yet in the graph**.

## 1. The Confidence Mandate

**Score: 9/10.** Everything below is specified; the one uncertainty is environmental: whether every
package in the base runtime set reports a licence string that passes the allow-list. If one does
not, stop and report it to the lead with the `pip-licenses` output (do not add an exception).

## Mini-requirements

1. US-001: `uv sync --locked` exits 0 on a fresh local clone; `uv.lock` is committed;
   `.python-version` contains `3.12`; `requires-python = ">=3.11,<3.14"`;
   `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` prints `0.1.0`.
2. US-002: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` and
   `uv run pytest` each exit 0 with `docs/prd/v0.1.0/` present; `.github/workflows/ci.yml` runs
   `uv sync --locked` then exactly these commands and the licence gate.
3. US-002a: the licence gate audits the **runtime** environment only (no `ruff`, `mypy`,
   `pytest`, `pip-licenses` rows in its output) with
   `pip-licenses --partial-match --allow-only="MIT;BSD;Apache;ISC;PSF;Python Software Foundation"`
   and exits 0; the same command over a scratch environment containing an LGPL package (e.g. `ase`)
   exits non-zero.
4. US-010: `README.md` contains the `nMap` citation (Mustard, Wender & Cheong, *ACS Catal.* 2015,
   DOI `10.1021/cs501828e`) and credits `Eta_Scripts`, has a licensing section (MIT; allow-list;
   no `ase`/`sella`/in-process `tblite`/`psi4`) and a `uv` quickstart (`uv sync`, `uv run pytest`).
5. US-011 (scaffold area): `docs/prd/v0.1.0/DISCREPANCIES.md` exists with the header, the format and
   one row per starter item of the scaffold area (see Task 7).
6. US-012: `docs/prd/PLAN_DISCREPANCIES.md` exists with the header and one row per `@@` hunk of the
   pinned command (14 today), PD-001 being the ~60-atom hunk.
7. Replan R38: the HACF pre-commit hook must accept commits of the starter copy.
   - The hook (`.agents/scripts/pre-commit`, HACF-managed, read-only) runs `ruff check -- <staged
     .py>` and `ruff format --check -- <staged .py>` with explicit paths.
   - For explicit paths, ruff applies the **nearest** config's exclude patterns, i.e. the starter's
     own `pyproject.toml`, which has none. It enforces them only when the **root** config sets
     `force-exclude = true`. Neither half works alone; resolve verified both halves together with
     ruff 0.17.6.
   - So the root `[tool.ruff]` sets `force-exclude = true`, and **one** gate file is added:
     `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.ruff.toml`, containing exactly these two lines:
     ```
     # Not part of the v0.1.0 starter: keeps ruff (and the HACF pre-commit hook) off this verbatim reference copy.
     exclude = ["*"]
     ```
     `.ruff.toml` outranks `pyproject.toml` in the same directory.
   - The 23 starter files stay byte-identical to the zip. The tree is "23 verbatim + 1 declared
     gate file".
   - `docs/prd/v0.1.0/DISCREPANCIES.md` gains an `added` row for the gate file and an `added` row
     for root `force-exclude`.
8. Replan R39 (builder's D-037, now the spec): root ruff `extend-exclude = ["docs/prd", ".agents"]`.
   `.agents/` holds HACF scripts that this project may not edit, and they fail our rules
   (120 errors / 12 files).

## 3. Implementation Plan (Task List)

- [x] Task 1 — Unpack: `unzip -q PRDs/Eta-RxnCat-v0.1.0.zip -d docs/prd/v0.1.0/` (gives
  `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/…`, 23 files). Check `git status --porcelain docs/prd | wc -l`
  after `git add -n docs/prd/v0.1.0` lists all 23 (the nested `.gitignore` must not hide any).
- [x] Task 1b — (replan R38) Add the gate file from Mini-requirement 7, and set `force-exclude =
  true` in the root `[tool.ruff]`. Stage all 16 starter `.py` files with the other starter files
  and commit through the normal hook. Never use `--no-verify`, and never edit the hook or a starter
  file.
- [x] Task 2 — `pyproject.toml` (hatchling or uv_build backend, src layout): name `eta-rxncat`,
  version `0.1.0`, `license = "MIT"`, `requires-python = ">=3.11,<3.14"`; runtime deps `numpy`,
  `scipy`, `pydantic>=2`, `pyyaml`, `rdkit`, `geometric`, `pyscf`; **no optional extras** (they
  arrive in a later slice); dev group `pytest`, `pytest-cov`, `ruff`, `mypy`, `types-PyYAML`,
  `pip-licenses`. Add `LICENSE` only if absent (one exists at the root: keep it, check it is MIT).
- [x] Task 3 — Tool config in `pyproject.toml`:
  - ruff: `line-length = 100`, `force-exclude = true`, `extend-exclude = ["docs/prd", ".agents"]`
    (R38, R39); lint `select = ["E","F","W","I","D"]`,
    `ignore = ["D100","D104"]`; pydocstyle `convention = "google"`; isort
    `known-first-party = ["eta_rxncat"]`; format `quote-style = "double"`.
  - mypy: `strict = true`, `files = ["src"]`, `plugins = ["pydantic.mypy"]`; one
    `[[tool.mypy.overrides]]` with `module = ["torch.*","gpu4pyscf.*","cupy.*","pyscf.*","rdkit.*","geometric.*"]`,
    `ignore_missing_imports = true`, `follow_imports = "skip"`.
  - pytest: `testpaths = ["tests"]`, `norecursedirs = [".*","build","dist","docs","*.egg"]`,
    `markers = ["gpu: needs a CUDA GPU and the gpu extra"]`, `addopts = "-m 'not gpu'"`.
- [x] Task 4 — Package: `src/eta_rxncat/__init__.py` (`__version__ = "0.1.0"`, docstring),
  `src/eta_rxncat/py.typed`, and empty packages `engines`, `conformers`, `mapping`, `optimize`,
  `orchestrator`, each an `__init__.py` with a one-line docstring naming the plan version that fills
  it (v0.2.0, v0.3.0, v0.4.0, v0.5.0, v0.8.0). `tests/unit/test_package.py` asserts
  `eta_rxncat.__version__ == "0.1.0"` and that importing `eta_rxncat` loads none of `torch`,
  `pyscf`, `rdkit` (subprocess + `sys.modules`).
- [x] Task 5 — `.python-version` (`3.12`); `uv lock`; `uv sync`; run the four gates.
- [ ] Task 6 — (geomeTRIC licence: pending TJ, row `qitem-20261122123511-7102e97b507c86d4`; the
  lead routes the answer through resolve. Do not drop, pin or exempt `geometric` before then.)
  Licence gate: one command, written identically in `ci.yml` and in the `AGENTS.md`
  project section, that builds/uses a runtime-only environment (e.g. `uv sync --locked --no-dev`
  into `UV_PROJECT_ENVIRONMENT=.venv-runtime`, then `uv run --with pip-licenses pip-licenses
  --python .venv-runtime/bin/python …`, or an equivalent you verify) with the allow-list above.
  Add `.venv-runtime/` to `.gitignore`. Record the negative demonstration (scratch dir outside the
  repo, `ase` installed, command exits non-zero) in your handoff with its output.
- [x] Task 7 — `docs/prd/v0.1.0/DISCREPANCIES.md`: header (purpose, TJ's Q2 quote, the closed
  inventory rules and row format below), then rows for the scaffold area: every key of the
  starter `pyproject.toml` (`[project]` with each dependency entry its own row, optional
  dependencies, scripts, build-system, each `[tool.*]` key), each step of its `ci.yml`, each line of
  its `.gitignore`, each section heading of its `AGENTS.md` and `README.md`, its
  `src/eta_rxncat/__init__.py` and the five empty package `__init__.py` files; plus `added` rows
  (e.g. `.python-version`, `uv.lock`, mypy overrides, ruff excludes, licence-gate command).
  Row format: `| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |`;
  starter paths in full (`docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:12`); Disposition ∈
  `same`/`changed`/`dropped`/`added`; Status always `open`. Known rows to confirm: starter ruff set
  `E,F,I,UP,B,SIM,RUF` vs `E,F,W,I,D`; starter CI `uv pip install --system` vs `uv sync --locked`;
  starter branch model `feat/*` one PR per unit vs `feature/eta-rxncat-v0.1.0` one commit per slice;
  starter optional extras `gpu`/`mlip` → `dropped` in this slice (reason: TJ decision pending F1/F2;
  a later slice re-adds); the starter AGENTS.md rule "update the Master Plan in the same PR" →
  `dropped` (`PRDs/` is TJ's). Later slices append rows for their areas; leave a section heading
  per area (`## Scaffold`, `## Core`, `## Store`, `## Hardware probe`, `## CLI`, `## Fixture`,
  `## Tests`).
- [x] Task 8 — `docs/prd/PLAN_DISCREPANCIES.md`: for each of the ten `PRDs/*.zip`, run
  `unzip -p PRDs/<zip> '*/Eta-RxnCat_Living_Master_Plan.md' > "$TMP/<version>.md"` with
  `TMP=$(mktemp -d)` outside the repo, then
  `LC_ALL=C diff -U0 "$TMP/<version>.md" PRDs/Eta-RxnCat_Living_Master_Plan.md`. Header: the
  command; sha256 of `PRDs/Eta-RxnCat_Living_Master_Plan.md`; a table of zip → copy sha256;
  the staleness rule ("if the PRDs/ sha256 differs from the header, this register is stale; the
  next version's architect regenerates it"). One row per `@@` hunk, deduplicated across zips that
  share a copy sha256: `| ID | Version(s) affected | Section / PR | Authoritative text (PRDs/…) | Zip copy text | Zips carrying this copy | Build follows | TJ status |`.
  PD-001 = the hunk about the ~60-atom test (Build follows `PRDs/` — TJ Q1 "No ~60-atom test in
  v0.1.0."; TJ status `decided`); PD-002… in diff order, Build follows `PRDs/`, TJ status `open`.
  Expected today: 14 rows, copies of v0.1.0–v0.6.0 and v0.8.0 identical (one sha), v0.7.0, v0.9.0
  and v1.0.0 byte-identical to `PRDs/` (no rows). If your counts differ, report the difference;
  do not force 14.
- [x] Task 9 — `README.md` per Mini-requirement 4.
- [x] Task 10 — `AGENTS.md`: append a `# Eta-RxnCat project rules` section **after** the line
  `<!-- END HACF MANAGED BLOCK: hacf -->`: branch `feature/<feature>`, one commit per slice; no
  `ase`/`sella`/in-process `tblite`/`psi4` imports; the licence allow-list and gate command; every
  `MolecularState` has explicit `charge` and `spin_multiplicity`; required checks (the four gates +
  licence gate); `PRDs/` is read-only; agents never write `tests/fixtures/`. Do not touch the
  managed block. `.gitignore`: append the starter's entries that apply (`__pycache__/`, `*.py[cod]`,
  `.venv/`, `.venv-runtime/`, caches, `*.sqlite`, `*.sqlite3`, `*.db`, `.coverage`, `htmlcov/`,
  `dist/`, `build/`, `*.egg-info/`) **after** `# END HACF MANAGED BLOCK: gitignore`.
- [x] Task 11 — `.github/workflows/ci.yml`: ubuntu-latest, `astral-sh/setup-uv` with cache, Python
  from `.python-version`, `uv sync --locked`, then the four gates and the licence gate. No GPU job.
- [ ] Task 12 — Fresh-clone proof: `git clone <repo> "$(mktemp -d)/c"` of your committed branch,
  `uv sync --locked`, run all five commands; paste the exit codes in your handoff.

## 4. The Negative Space (Constraints)

- **DO NOT** declare `[project.optional-dependencies]` in this slice.
- **DO NOT** add a licence exception (`--ignore-packages` or a longer allow-list); report instead.
- **DO NOT** edit inside any `HACF MANAGED BLOCK` in `AGENTS.md`, `CLAUDE.md` or `.gitignore`.
- **DO NOT** copy starter files into `src/` or `tests/`, or import from `docs/prd/`.
- **DO NOT** unpack any zip other than v0.1.0 into the repo; read plan copies with `unzip -p` into
  a temp dir outside the repo.
- **DO NOT** write into, move or delete anything in `PRDs/`.
- **DO NOT** write to `tests/fixtures/` or `tests/candidate_outputs/`.
- **DO NOT** let ruff, pytest or mypy read anything under `docs/prd/`.
- **DO NOT** edit any of the 23 starter files, `.agents/scripts/pre-commit` or anything else under
  `.agents/`; **DO NOT** commit with `--no-verify`; **DO NOT** add any file under the starter dir
  except the one gate file.
- **DO NOT** create `CONTRIBUTING.md`.
- **DO NOT** push, tag or open a PR.

## Proof contract

- [ ] `uv sync --locked` → exit 0 on a fresh clone; `uv run python -c "import eta_rxncat; print(eta_rxncat.__version__)"` → `0.1.0`.
- [ ] `uv run ruff check .` → exit 0 and `uv run ruff format --check .` → exit 0, with `docs/prd/v0.1.0/` present.
- [ ] `uv run mypy` → exit 0 (strict, `files = ["src"]`).
- [ ] `uv run pytest` → exit 0, and `uv run pytest . --collect-only -q` collects nothing under `docs/`.
- [ ] Licence gate → exit 0 on the runtime env; output lists no dev tools; scratch negative demo with `ase` → non-zero.
- [ ] `ci.yml` contains `uv sync --locked` and the same five commands, character-for-character as in `AGENTS.md`.
- [ ] `git ls-files docs/prd/v0.1.0/Eta-RxnCat-v0.1.0 | wc -l` → `24` (23 starter files + `.ruff.toml`).
  Each of the 23 is byte-identical to `unzip -p PRDs/Eta-RxnCat-v0.1.0.zip <path>`.
- [ ] The commit adding the 16 starter `.py` files passed the unmodified HACF hook. Re-check:
  `bash -c 'mapfile -t F < <(git ls-files "docs/prd/*.py"); .venv/bin/ruff check -- "${F[@]}" && .venv/bin/ruff format --check -- "${F[@]}"'` → exit 0.
  The same command with a deliberately bad scratch `.py` added under `src/` → exit 1 (the
  exclusion is scoped). Do not commit the scratch file.
- [ ] `grep -c '10.1021/cs501828e' README.md` → ≥ 1.
- [ ] `docs/prd/PLAN_DISCREPANCIES.md` row count = `@@` count of the pinned command over the distinct copies; header sha256 = `sha256sum PRDs/Eta-RxnCat_Living_Master_Plan.md`.
- [ ] `docs/prd/v0.1.0/DISCREPANCIES.md` has a row for every scaffold-area starter item listed in Task 7.
- [ ] `git diff <start> -- AGENTS.md .gitignore` shows changes only after the HACF END markers.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (v0.1.0 PR #1; Project Objectives; Known Constraints).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/{pyproject.toml,.github/workflows/ci.yml,.gitignore,AGENTS.md,README.md}` (reference only, after Task 1).
- Mission `missions/release-0.1.0/SPEC.md` §5 (registers, trade-off log R3, R4, R13–R16, R20).
- `.agents/rules/python.md`, `package-management.md`, `testing.md`, `git-workflow.md`.

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- none (first slice)
