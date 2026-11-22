# v0.1.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.1.0.zip` ships a starter implementation, unpacked here under
`docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/`. It is reference only: the code in `src/` and `tests/` is
written fresh from the mission's slice specs. This register records every difference between the
starter and the rewrite, so each one can be reviewed and fixed if needed.

TJ, Q2: "B use it as reference only. Keep a list of the discrepancies so that if needed, we can go
through each of them and fix any issues that arise."

## Inventory rules (closed)

One row per starter item, by area:

- each Python module under `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/`: every top-level public name
  (no leading `_`), and for each public class every public field and public method;
- `pyproject.toml`: every key of `[project]` (each dependency entry its own row),
  `[project.optional-dependencies]`, `[project.scripts]`, `[build-system]`, and every key of each
  `[tool.*]` table;
- `.github/workflows/ci.yml`: each step; `.gitignore`: each line;
- SQL: the table, each column, each index; CLI: each subcommand, argument, output and exit
  behaviour;
- the fixture: each top-level key and each key of node, edge and template objects;
- `AGENTS.md`, `README.md`: each section heading;
- starter tests: each test function, mapped to the rewrite test covering it or `dropped`.

Plus one `added` row for each rewrite public name, config key, CLI argument or SQL column absent
from the starter. Cosmetic differences (formatting, comments, docstring wording) are not rows.

## Row format

`| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |`

- Starter paths are given in full from the repo root.
- `Disposition` ∈ `same`, `changed`, `dropped`, `added`.
- `Status` ∈ `open`, `accepted`, `fix`. Builders write `open` only; TJ decides the rest.
- Each slice appends rows to its own area section, continuing the ID sequence.

## Scaffold

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-001 | pyproject `[build-system]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:2` `requires = ["hatchling>=1.25.0"]` | `pyproject.toml:2` | same | Slice 01 Task 2 allows hatchling | open |
| D-002 | pyproject `[build-system]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:3` `build-backend = "hatchling.build"` | `pyproject.toml:3` | same | — | open |
| D-003 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:6` `name` | `pyproject.toml:6` | same | — | open |
| D-004 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:7` `version = "0.1.0"` | `pyproject.toml:7` | same | — | open |
| D-005 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:8` `description` (mentions MLIPs, GPU4PySCF) | `pyproject.toml:8` | changed | Describes the library without features v0.1.0 does not ship | open |
| D-006 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:9` `readme` | `pyproject.toml:9` | same | — | open |
| D-007 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:10` `license = { text = "MIT" }` | `pyproject.toml:10` `license = "MIT"` | changed | Slice 01 Task 2: SPDX string form (PEP 639) | open |
| D-008 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:11` `requires-python = ">=3.11"` | `pyproject.toml:12` `">=3.11,<3.14"` | changed | Mission R14: upper bound for lock determinism | open |
| D-009 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:12` `authors` | `pyproject.toml:13` | same | — | open |
| D-010 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:15` `keywords` | — | dropped | Not in slice 01 Task 2 | open |
| D-011 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:23` `classifiers` | — | dropped | Not in slice 01 Task 2; licence comes from the SPDX `license` field | open |
| D-012 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:33` `numpy>=1.26.0,<3.0.0` | `pyproject.toml:15` `numpy` | changed | Slice 01 Task 2 lists unpinned names; `uv.lock` pins versions | open |
| D-013 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:34` `scipy>=1.12.0` | `pyproject.toml:16` `scipy` | changed | As D-012 | open |
| D-014 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:35` `pydantic>=2.7.0` | `pyproject.toml:17` `pydantic>=2` | changed | Slice 01 Task 2 floor `>=2` | open |
| D-015 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:36` `pyyaml>=6.0.1` | `pyproject.toml:18` `pyyaml` | changed | As D-012 | open |
| D-016 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:37` `rdkit>=2024.03.1` | `pyproject.toml:19` `rdkit` | changed | As D-012 | open |
| D-017 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:38` `geometric>=1.0.2` | `pyproject.toml:20` `geometric` (locks 1.1.1) | changed | As D-012. The licence gate fails on it: geometric 1.1.1 reports `UNKNOWN` and its LICENSE is "BSD 3-clause Non-AI"; raised to TJ | open |
| D-018 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:39` `pyscf>=2.6.0` | `pyproject.toml:21` `pyscf` | changed | As D-012 | open |
| D-019 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:43` extra `gpu` | — | dropped | No extras in slice 01 (TJ F1/F2 decided 08:19Z; slice 06 re-adds `gpu`) | open |
| D-020 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:46` extra `mlip` | — | dropped | No extras in slice 01; slice 06 adds conflicting `mlip-mace` / `mlip-uma` instead (mission R1) | open |
| D-021 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:51` extra `dev` | `pyproject.toml:24` `[dependency-groups] dev` | changed | Dev tools are a uv dependency group, not a published extra; same six packages, unpinned | open |
| D-022 | pyproject `[project.scripts]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:61` `eta-rxncat = "eta_rxncat.cli:main"` | — | dropped | No CLI in slice 01; slice 05 owns the CLI | open |
| D-023 | pyproject `[tool.hatch]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:64` `packages = ["src/eta_rxncat"]` | `pyproject.toml:35` | same | — | open |
| D-024 | pyproject `[tool.ruff]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:67` `line-length = 100` | `pyproject.toml:38` | same | — | open |
| D-025 | pyproject `[tool.ruff]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:68` `target-version = "py311"` | — | dropped | Not in slice 01 Task 3; ruff infers it from `requires-python` | open |
| D-026 | pyproject `[tool.ruff.lint]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:71` `select = ["E","F","I","UP","B","SIM","RUF"]` | `pyproject.toml:43` `["E","F","W","I","D"]` | changed | Slice 01 Task 3 and `.agents/rules/python.md` | open |
| D-027 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:74` `python_version = "3.11"` | — | dropped | Not in slice 01 Task 3 | open |
| D-028 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:75` `strict = true` | `pyproject.toml:56` | same | — | open |
| D-029 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:76` `warn_return_any = true` | `pyproject.toml:56` (implied by `strict`) | dropped | Redundant under `strict = true` | open |
| D-030 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:77` `warn_unused_configs = true` | `pyproject.toml:56` (implied by `strict`) | dropped | Redundant under `strict = true` | open |
| D-031 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:78` `plugins = ["pydantic.mypy"]` | `pyproject.toml:58` | same | — | open |
| D-032 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:81` `testpaths = ["tests"]` | `pyproject.toml:66` | same | — | open |
| D-033 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:82` `addopts = "-ra -q"` | `pyproject.toml:69` `addopts = "-m 'not gpu'"` | changed | Slice 01 Task 3: GPU tests deselected by default | open |
| D-034 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:84` marker `gpu` | `pyproject.toml:68` | changed | Text names the `gpu` extra | open |
| D-035 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:85` marker `e2e` | — | dropped | Not in slice 01 Task 3; e2e fixtures arrive with later versions | open |
| D-036 | pyproject `[project]` | — | `pyproject.toml:11` `license-files = ["LICENSE"]` | added | Ships the root MIT `LICENSE` in the wheel | open |
| D-037 | pyproject `[tool.ruff]` | — | `pyproject.toml:40` `extend-exclude = ["docs/prd", ".agents"]` | added | `docs/prd`: mission R4. `.agents`: mission R39 (HACF scripts may not be edited and fail 120 lint / 12 format checks) | open |
| D-038 | pyproject `[tool.ruff.lint]` | — | `pyproject.toml:44` `ignore = ["D100","D104"]` | added | Slice 01 Task 3 | open |
| D-039 | pyproject `[tool.ruff.lint.pydocstyle]` | — | `pyproject.toml:47` `convention = "google"` | added | Slice 01 Task 3 | open |
| D-040 | pyproject `[tool.ruff.lint.isort]` | — | `pyproject.toml:50` `known-first-party` | added | Slice 01 Task 3 | open |
| D-041 | pyproject `[tool.ruff.format]` | — | `pyproject.toml:53` `quote-style = "double"` | added | Slice 01 Task 3 | open |
| D-042 | pyproject `[tool.mypy]` | — | `pyproject.toml:57` `files = ["src"]` | added | Mission R4: mypy never reads `docs/prd` | open |
| D-043 | pyproject `[[tool.mypy.overrides]]` | — | `pyproject.toml:60` heavy-module overrides | added | Mission R13 | open |
| D-044 | pyproject `[tool.pytest]` | — | `pyproject.toml:67` `norecursedirs` | added | Mission R4 | open |
| D-045 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:13` `actions/checkout@v4` | `.github/workflows/ci.yml:11` | same | — | open |
| D-046 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:14` `actions/setup-python@v5` (3.11) | `.github/workflows/ci.yml:16` `uv python install` | changed | Python comes from `.python-version` (3.12), slice 01 Task 11 | open |
| D-047 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:18` `astral-sh/setup-uv@v3` | `.github/workflows/ci.yml:12` `astral-sh/setup-uv@v6` with cache | changed | Slice 01 Task 11: setup-uv with cache | open |
| D-048 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:20` `uv pip install --system -e ".[dev]"` | `.github/workflows/ci.yml:18` `uv sync --locked` | changed | Mission R14: locked, reproducible environment | open |
| D-049 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:23` `ruff check src tests` | `.github/workflows/ci.yml:20` `uv run ruff check .` | changed | Whole tree, per slice 01 US-002 | open |
| D-050 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:25` `mypy src` | `.github/workflows/ci.yml:24` `uv run mypy` | changed | Files come from `[tool.mypy] files` | open |
| D-051 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:27` `pip-licenses --fail-on="GPL;LGPL;AGPL"` | `.github/workflows/ci.yml:29` runtime-only allow-list gate | changed | Mission R3: deny-list was exact-match blind and audited dev tools | open |
| D-052 | CI step | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:29` `pytest tests/unit` | `.github/workflows/ci.yml:26` `uv run pytest` | changed | All of `tests/` via `testpaths` | open |
| D-053 | CI step | — | `.github/workflows/ci.yml:22` `uv run ruff format --check .` | added | Slice 01 US-002 | open |
| D-054 | CI trigger | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:3` `on:` push/PR to `main` only | `.github/workflows/ci.yml:3` every push and PR | changed | Work happens on `feature/*` branches, so CI must run on them | open |
| D-055 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:1` `__pycache__/` | `.gitignore:11` | same | — | open |
| D-056 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:2` `*.py[cod]` | `.gitignore:12` | same | — | open |
| D-057 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:3` `*$py.class` | — | dropped | Jython artefact; not in slice 01 Task 10 list | open |
| D-058 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:4` `.venv/` | `.gitignore:13` | same | — | open |
| D-059 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:5` `venv/` | — | dropped | uv always uses `.venv/`; not in slice 01 Task 10 list | open |
| D-060 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:6` `dist/` | `.gitignore:23` | same | — | open |
| D-061 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:7` `build/` | `.gitignore:24` | same | — | open |
| D-062 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:8` `*.egg-info/` | `.gitignore:25` | same | — | open |
| D-063 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:9` `.pytest_cache/` | `.gitignore:15` | same | — | open |
| D-064 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:10` `.mypy_cache/` | `.gitignore:16` | same | — | open |
| D-065 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:11` `.ruff_cache/` | `.gitignore:17` | same | — | open |
| D-066 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:12` `.coverage` | `.gitignore:21` | same | — | open |
| D-067 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:13` `htmlcov/` | `.gitignore:22` | same | — | open |
| D-068 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:14` `*.sqlite` | `.gitignore:18` | same | — | open |
| D-069 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:15` `*.sqlite3` | `.gitignore:19` | same | — | open |
| D-070 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:16` `*.db` | `.gitignore:20` | same | — | open |
| D-071 | .gitignore | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.gitignore:17` `.eta_cache/` | — | dropped | Mission R7: the store has no default path; the caller supplies it | open |
| D-072 | .gitignore | — | `.gitignore:14` `.venv-runtime/` | added | Licence-gate runtime environment (slice 01 Task 6) | open |
| D-073 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:1` `# Eta-RxnCat Engineering & Agent Collaboration Guidelines` | `AGENTS.md:294` `# Eta-RxnCat project rules` | changed | Sits after the HACF managed block (mission R20) | open |
| D-074 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:5` `## 1. Branching & Pull Request Protocol` (`feat/*`, one PR per unit, never commit to `main`) | `AGENTS.md:298` `## Branches and commits` (`feature/<feature>`, one commit per slice, never push) | changed | Rig branch model | open |
| D-075 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:8` rule "update the Master Plan in the same PR" | — | dropped | `PRDs/` is TJ's (mission R20) | open |
| D-076 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:10` `## 2. Clean-Room & Permissive License Guardrails` | `AGENTS.md:303` `## Licence guardrails` | changed | Adds the allow-list and the gate command | open |
| D-077 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:15` `## 3. Scientific & Numerical Standards` | `AGENTS.md:316` `## Scientific standards` | changed | Keeps the charge/spin rule only; the VRAM and caching rules belong to the slices that build them (04, 03) | open |
| D-078 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:20` `## 4. Required Checks Before Opening a PR` | `AGENTS.md:320` `## Required checks` | changed | The four `uv run` gates plus the runtime licence gate | open |
| D-079 | AGENTS.md | — | `AGENTS.md:333` `## Protected paths` | added | `PRDs/` read-only; agents never write `tests/fixtures/` | open |
| D-080 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:1` `# Eta-RxnCat` | `README.md:1` | changed | Intro states what v0.1.0 ships | open |
| D-081 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:7` `## Scientific Heritage & Homage` | `README.md:10` `## Scientific heritage` | changed | Keeps the nMap citation and Eta_Scripts credit; drops the AutoRW paragraph | open |
| D-082 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:16` `## Licensing Philosophy` | `README.md:22` `## Licensing` | changed | States the allow-list and runtime-only gate | open |
| D-083 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:20` `## Quickstart (v0.1.0)` (`uv venv`, `uv pip install -e`, `hw_probe`) | `README.md:33` `## Quickstart` (`uv sync`, `uv run pytest`) | changed | Slice 01 US-010; the hardware check arrives with slices 04–05 | open |
| D-084 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:38` `## Project Roadmap` (points at a root plan copy) | `README.md:50` `## Roadmap` (points at `PRDs/`) | changed | TJ Q1: `PRDs/` plan governs | open |
| D-085 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/__init__.py:3` `__version__ = "0.1.0"` | `src/eta_rxncat/__init__.py:3` | same | — | open |
| D-086 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/engines/__init__.py:1` empty package (v0.2.0) | `src/eta_rxncat/engines/__init__.py:1` | same | — | open |
| D-087 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/conformers/__init__.py:1` empty package (v0.3.0) | `src/eta_rxncat/conformers/__init__.py:1` | same | — | open |
| D-088 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/mapping/__init__.py:1` empty package (v0.4.0) | `src/eta_rxncat/mapping/__init__.py:1` | same | — | open |
| D-089 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/optimize/__init__.py:1` empty package (v0.5.0) | `src/eta_rxncat/optimize/__init__.py:1` | same | — | open |
| D-090 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/orchestrator/__init__.py:1` empty package (v0.8.0) | `src/eta_rxncat/orchestrator/__init__.py:1` | same | — | open |
| D-091 | package | — | `src/eta_rxncat/py.typed` | added | PEP 561 marker (slice 01 Task 4) | open |
| D-092 | repo | — | `.python-version` `3.12` | added | Mission R14 | open |
| D-093 | repo | — | `uv.lock` | added | Mission R14: committed lockfile | open |
| D-094 | licence gate | — | `.github/workflows/ci.yml:29`, `AGENTS.md:313` runtime-only `pip-licenses --partial-match --allow-only=…` | added | Mission R3 | open |
| D-095 | tests | — | `tests/unit/test_package.py` `test_version`, `test_import_loads_no_heavy_modules` | added | Slice 01 Task 4 | open |
| D-096 | pyproject `[tool.ruff]` | — | `pyproject.toml:39` `force-exclude = true` | added | Mission R38: makes ruff honour excludes for explicit paths, as the HACF pre-commit hook passes them | open |
| D-097 | starter gate file | — | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.ruff.toml` (2 lines, `exclude = ["*"]`) | added | Mission R38: declared, not part of the starter; keeps ruff and the hook off the verbatim copy (23 verbatim + 1 gate file) | open |

## Core

## Store

## Hardware probe

## CLI

## Fixture

## Tests
