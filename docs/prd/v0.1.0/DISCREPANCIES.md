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
| D-009 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:13` `authors = [{ name = "Thomas J. L. Mustard" }]` | `pyproject.toml:13` `authors = [{ name = "Thomas J. L. Mustard Ph.D." }]` | changed | TJ: author is "Thomas J. L. Mustard Ph.D." everywhere (slice 08); no email | open |
| D-010 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:15` `keywords` | — | dropped | Not in slice 01 Task 2 | open |
| D-011 | pyproject `[project]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:23` `classifiers` | — | dropped | Not in slice 01 Task 2; licence comes from the SPDX `license` field | open |
| D-012 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:33` `numpy>=1.26.0,<3.0.0` | `pyproject.toml:15` `numpy` | changed | Slice 01 Task 2 lists unpinned names; `uv.lock` pins versions | open |
| D-013 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:34` `scipy>=1.12.0` | `pyproject.toml:16` `scipy` | changed | As D-012 | open |
| D-014 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:35` `pydantic>=2.7.0` | `pyproject.toml:17` `pydantic>=2` | changed | Slice 01 Task 2 floor `>=2` | open |
| D-015 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:36` `pyyaml>=6.0.1` | `pyproject.toml:18` `pyyaml` | changed | As D-012 | open |
| D-016 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:37` `rdkit>=2024.03.1` | `pyproject.toml:19` `rdkit` | changed | As D-012 | open |
| D-017 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:38` `geometric>=1.0.2` | `pyproject.toml:20` `geometric` (locks 1.1.1) | changed | As D-012. geometric 1.1.1 reports `UNKNOWN` and its LICENSE is "BSD 3-clause Non-AI"; gated by the version-pinned exception in D-098 (TJ "B", R41) | open |
| D-018 | pyproject dependency | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:39` `pyscf>=2.6.0` | `pyproject.toml:21` `pyscf` | changed | As D-012 | open |
| D-019 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:43` extra `gpu` | `pyproject.toml:25` `gpu = ["torch>=2.7.0", "gpu4pyscf-cuda12x>=1.8.0", "cupy-cuda12x"]` | changed | Re-added in slice 06; also declares torch (cu128 index) and cupy-cuda12x | open |
| D-020 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:46` extra `mlip` | `pyproject.toml:26` `mlip-mace`, `pyproject.toml:27` `mlip-uma` | changed | Split into two mutually exclusive extras declared conflicting (F1, TJ Q2 A): mace-torch pins e3nn 0.4.4, fairchem-core needs e3nn ≥ 0.5; the lock resolves e3nn 0.4.4 and 0.6.0 per fork | open |
| D-021 | pyproject optional deps | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:51` extra `dev` | `pyproject.toml:32` `[dependency-groups] dev` | changed | Dev tools are a uv dependency group, not a published extra; unpinned; `pip-licenses` removed in slice 06 (R45: replaced by `tools/licence_gate.py`) | open |
| D-022 | pyproject `[project.scripts]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:61` `eta-rxncat = "eta_rxncat.cli:main"` | `pyproject.toml:30` | same | Same entry point, added by slice 05 (dropped in slice 01, which had no CLI) | open |
| D-023 | pyproject `[tool.hatch]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:64` `packages = ["src/eta_rxncat"]` | `pyproject.toml:53` | same | — | open |
| D-024 | pyproject `[tool.ruff]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:67` `line-length = 100` | `pyproject.toml:56` | same | — | open |
| D-025 | pyproject `[tool.ruff]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:68` `target-version = "py311"` | — | dropped | Not in slice 01 Task 3; ruff infers it from `requires-python` | open |
| D-026 | pyproject `[tool.ruff.lint]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:71` `select = ["E","F","I","UP","B","SIM","RUF"]` | `pyproject.toml:61` `["E","F","W","I","D"]` | changed | Slice 01 Task 3 and `.agents/rules/python.md` | open |
| D-027 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:74` `python_version = "3.11"` | — | dropped | Not in slice 01 Task 3 | open |
| D-028 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:75` `strict = true` | `pyproject.toml:74` | same | — | open |
| D-029 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:76` `warn_return_any = true` | `pyproject.toml:74` (implied by `strict`) | dropped | Redundant under `strict = true` | open |
| D-030 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:77` `warn_unused_configs = true` | `pyproject.toml:74` (implied by `strict`) | dropped | Redundant under `strict = true` | open |
| D-031 | pyproject `[tool.mypy]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:78` `plugins = ["pydantic.mypy"]` | `pyproject.toml:76` | same | — | open |
| D-032 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:81` `testpaths = ["tests"]` | `pyproject.toml:84` | same | — | open |
| D-033 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:82` `addopts = "-ra -q"` | `pyproject.toml:87` `addopts = "-m 'not gpu'"` | changed | Slice 01 Task 3: GPU tests deselected by default | open |
| D-034 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:84` marker `gpu` | `pyproject.toml:86` | changed | Text names the `gpu` extra | open |
| D-035 | pyproject `[tool.pytest]` | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/pyproject.toml:85` marker `e2e` | — | dropped | Not in slice 01 Task 3; e2e fixtures arrive with later versions | open |
| D-036 | pyproject `[project]` | — | `pyproject.toml:11` `license-files = ["LICENSE"]` | added | Ships the root MIT `LICENSE` in the wheel | open |
| D-037 | pyproject `[tool.ruff]` | — | `pyproject.toml:58` `extend-exclude = ["docs/prd", ".agents"]` | added | `docs/prd`: mission R4. `.agents`: mission R39 (HACF scripts may not be edited and fail 120 lint / 12 format checks) | open |
| D-038 | pyproject `[tool.ruff.lint]` | — | `pyproject.toml:62` `ignore = ["D100","D104"]` | added | Slice 01 Task 3 | open |
| D-039 | pyproject `[tool.ruff.lint.pydocstyle]` | — | `pyproject.toml:65` `convention = "google"` | added | Slice 01 Task 3 | open |
| D-040 | pyproject `[tool.ruff.lint.isort]` | — | `pyproject.toml:68` `known-first-party` | added | Slice 01 Task 3 | open |
| D-041 | pyproject `[tool.ruff.format]` | — | `pyproject.toml:71` `quote-style = "double"` | added | Slice 01 Task 3 | open |
| D-042 | pyproject `[tool.mypy]` | — | `pyproject.toml:75` `files = ["src", "tools"]` | added | Mission R4: mypy never reads `docs/prd`; slice 06 adds `tools` (R45) | open |
| D-043 | pyproject `[[tool.mypy.overrides]]` | — | `pyproject.toml:78` heavy-module overrides | added | Mission R13 | open |
| D-044 | pyproject `[tool.pytest]` | — | `pyproject.toml:85` `norecursedirs` | added | Mission R4 | open |
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
| D-076 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:10` `## 2. Clean-Room & Permissive License Guardrails` | `AGENTS.md:306` `## Licence guardrails` | changed | Adds the allow-list and the gate command | open |
| D-077 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:15` `## 3. Scientific & Numerical Standards` | `AGENTS.md:338` `## Scientific standards` | changed | Keeps the charge/spin rule only; the VRAM and caching rules belong to the slices that build them (04, 03) | open |
| D-078 | AGENTS.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/AGENTS.md:20` `## 4. Required Checks Before Opening a PR` | `AGENTS.md:342` `## Required checks` | changed | The four `uv run` gates plus the runtime licence gate | open |
| D-079 | AGENTS.md | — | `AGENTS.md:355` `## Protected paths` | added | `PRDs/` read-only; agents never write `tests/fixtures/` | open |
| D-080 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:1` `# Eta-RxnCat` | `README.md:3` centered header (logo, `<h1>Eta-RxnCat</h1>`, tagline), banner, pitch, badges | changed | Slice 08: sibling README pattern (HACF, OIN-SMILES, eta-skills); describes only what v0.1.0 builds | open |
| D-081 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:7` `## Scientific Heritage & Homage` | `README.md:207` `## 🙏 Acknowledgements` | changed | Keeps the nMap citation (DOI) and Eta_Scripts credit; drops the AutoRW paragraph | open |
| D-082 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:16` `## Licensing Philosophy` | `README.md:219` `## 📄 License` | changed | TJ 14:57Z: MIT core; copyleft only in optional engine extras users download; nothing copyleft in the repo. Describes the exact licence gate (R45), not pip-licenses | open |
| D-083 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:20` `## Quickstart (v0.1.0)` (`uv venv`, `uv pip install -e`, `hw_probe`) | `README.md:73` `## ⚡ Installation` (`uv sync`, `uv run pytest`, extras) | changed | Slice 01 US-010 kept; adds the extras and the MLIP mutual exclusion; the hardware check is under Usage | open |
| D-084 | README.md | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/README.md:38` `## Project Roadmap` (points at a root plan copy) | `README.md:191` `## 🧭 Roadmap` (Planned, not yet built: v0.2.0–v1.0.0; points at `PRDs/`) | changed | TJ Q1: `PRDs/` plan governs; nothing beyond v0.1.0 outside Roadmap | open |
| D-085 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/__init__.py:3` `__version__ = "0.1.0"` | `src/eta_rxncat/__init__.py:3` | same | — | open |
| D-086 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/engines/__init__.py:1` empty package (v0.2.0) | `src/eta_rxncat/engines/__init__.py:1` | same | — | open |
| D-087 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/conformers/__init__.py:1` empty package (v0.3.0) | `src/eta_rxncat/conformers/__init__.py:1` | same | — | open |
| D-088 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/mapping/__init__.py:1` empty package (v0.4.0) | `src/eta_rxncat/mapping/__init__.py:1` | same | — | open |
| D-089 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/optimize/__init__.py:1` empty package (v0.5.0) | `src/eta_rxncat/optimize/__init__.py:1` | same | — | open |
| D-090 | package | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/orchestrator/__init__.py:1` empty package (v0.8.0) | `src/eta_rxncat/orchestrator/__init__.py:1` | same | — | open |
| D-091 | package | — | `src/eta_rxncat/py.typed` | added | PEP 561 marker (slice 01 Task 4) | open |
| D-092 | repo | — | `.python-version` `3.12` | added | Mission R14 | open |
| D-093 | repo | — | `uv.lock` | added | Mission R14: committed lockfile | open |
| D-094 | licence gate | — | `.github/workflows/ci.yml:29`, `AGENTS.md:320` runtime-only base gate `tools/licence_gate.py --profile base` | added | Mission R3, R41; slice 06 R45 replaces the pip-licenses command (unsound `--partial-match`) | open |
| D-095 | tests | — | `tests/unit/test_package.py` `test_version`, `test_import_loads_no_heavy_modules` | added | Slice 01 Task 4 | open |
| D-096 | pyproject `[tool.ruff]` | — | `pyproject.toml:57` `force-exclude = true` | added | Mission R38: makes ruff honour excludes for explicit paths, as the HACF pre-commit hook passes them | open |
| D-097 | starter gate file | — | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.ruff.toml` (2 lines, `exclude = ["*"]`) | added | Mission R38: declared, not part of the starter; keeps ruff and the hook off the verbatim copy (23 verbatim + 1 gate file) | open |
| D-098 | pyproject `[tool.eta-rxncat.licence-gate]` | — | `pyproject.toml:89` `allowed`, `allowed-exceptions`, `classifiers`, `names`, `nvidia-rule`, pinned `exempt` (geometric 1.1.1 in every profile) | added | Mission R41 (TJ "B", 12:49Z; ADR-0011) for geometric; slice 06 R45 (ADR-0013 PROPOSED) replaces `[tool.pip-licenses]` | open |
| D-379 | scaffold | — | `pyproject.toml:42` `[tool.uv] conflicts` | added | mlip-mace and mlip-uma declared conflicting so `uv lock` resolves both (F1, TJ Q2 A) | open |
| D-380 | scaffold | — | `pyproject.toml:45` `[[tool.uv.index]] pytorch-cu128` (explicit) | added | torch from https://download.pytorch.org/whl/cu128 (plan: PyTorch ≥ 2.7.0+cu128, sm_120); locks torch 2.8.0+cu128 | open |
| D-381 | scaffold | — | `pyproject.toml:50` `[tool.uv.sources] torch` | added | Routes only torch to the explicit cu128 index | open |
| D-382 | scaffold | — | `tests/unit/test_package.py:75` AST import guard + `tests/unit/test_package.py:157` direct-dependency guard | added | Slice 06 Mini-req 5 (TJ Q1 A): no ase/matscipy/sella/tblite/psi4 import in src; no direct ase/matscipy dependency | open |
| D-386 | scaffold | — | `tools/licence_gate.py:358` `tools/licence_gate.py` | added | R45: stdlib-only exact gate (SPDX AND/OR/WITH, exact classifier and name maps, no substring matching), run by the target env's interpreter, `--profile base|gpu|mlip-mace|mlip-uma` | open |
| D-387 | scaffold | — | `tests/unit/tools/test_licence_gate.py` | added | R45 proof: the 14 synthetic cases plus NVIDIA-rule scoping and removal, profile scoping, precedence | open |
| D-388 | scaffold | — | `pyproject.toml:95` `allowed` includes `Zlib`, `CC0-1.0`, `MIT-0`, `MIT-CMU`, `0BSD`, `Python-2.0` | added | R45: numpy's expression `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` and pillow's `MIT-CMU` passed the old gate only by substring; now listed explicitly (resolve's call, flagged for TJ) | open |
| D-389 | scaffold | — | `pyproject.toml:123` `nvidia-rule` | added | TJ Q1 A: `nvidia-*` with a proprietary classifier or field, profiles gpu/mlip-mace/mlip-uma only | open |
| D-390 | scaffold | — | `pyproject.toml:140` MLIP exemption lists: mlip-mace `ase:3.29.0`, `matscipy:1.3.1`, `python-hostlist:2.3.0`, `lmdb:1.7.3`, `torch-ema:0.3`, `tqdm:4.70.1`, `orjson:3.13.0`; mlip-uma `ase:3.29.0`, `psycopg2-binary:2.9.13`, `ase_db_backends:0.11.0`, `ray-haproxy:2.8.25`, `lmdb:1.7.3`, `certifi:2026.11.20`, `tqdm:4.70.1`, `orjson:3.13.0`, `clusterscope:0.0.18` | added | R48 / ADR-0014 (TJ A, 14:49Z): copyleft and off-list licences only as downloaded, unmodified, transitive deps of the optional MLIP extras; never vendored, copied or imported. Versions equal the lock; each list equals its profile's FAIL set | open |
| D-391 | scaffold | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/.github/workflows/ci.yml:28` licence policy: deny-list `--fail-on="GPL;LGPL;AGPL"` over the dev env | `pyproject.toml:89` per-profile exact allow-list gate with pinned exemptions | changed | F2, TJ Q1 A, R45, R48: exact SPDX allow-list over each runtime env (base, gpu, gpu+mlip-mace, gpu+mlip-uma); exemptions only for geometric (R41), NVIDIA wheels (Q1 A) and the MLIP transitive lists (R48) | open |
| D-392 | scaffold | — | `.github/workflows/ci.yml:31` CI job `licence-extras` (matrix gpu, gpu+mlip-mace, gpu+mlip-uma) | added | Slice 06 Mini-req 7: one runtime sync + gate per extra combination; commands identical to AGENTS.md; no GPU job | open |
| D-393 | scaffold | — | `AGENTS.md:323` the three per-extra gate commands and TJ's R48 rule | added | Slice 06 Mini-req 4 / Task 3 | open |
| D-394 | scaffold | — | `tests/unit/test_package.py:43` import ban + `tests/unit/test_package.py:60` direct-dependency ban extended to the R48 copyleft distributions | added | Slice 06 Mini-req 5 (c): modules hostlist, psycopg2, ase_db_backends, ray_haproxy, tqdm, orjson, certifi (from top_level.txt in the profile envs); lmdb, torch_ema, clusterscope not banned (permissive) | open |
| D-395 | scaffold | — | `tests/unit/tools/test_licence_gate.py:332` `test_exemptions_only_in_mlip_profiles`, `test_exemption_entries_are_complete`, `test_r48_lists` | added | Slice 06 Mini-req 5 (d) and R48: MLIP exemptions never in base/gpu; every entry pinned with licence, pulled-in-by, reason, decision | open |
| D-396 | scaffold | — | `tools/licence_gate.py:150` exemption fields `licence`, `pulled-in-by` (required) | added | R48: each exemption records what the metadata says and the direct parent in its profile | open |
| D-397 | scaffold | — (the starter ships no `LICENSE`; its `pyproject.toml` declares MIT) | `LICENSE:3` `Copyright (c) 2026 Thomas J. L. Mustard Ph.D.` | changed | Slice 08: the repo LICENSE copyright line (was `Thomas Mustard`) uses the canonical author form; MIT text unchanged | open |
| D-398 | scaffold | — | `README.md:46` `Features (v0.1.0)`, `README.md:96` `Usage`, `README.md:165` `Development` sections | added | Slice 08 Mini-req 2: what v0.1.0 builds, reproducible CLI examples, the four gates and the licence gates | open |
| D-399 | scaffold | — | `CHANGELOG.md` | added | Slice 08: Keep a Changelog 1.1.0 + SemVer; `[Unreleased]` only; the scribe maintains it per release (AGENTS.md) | open |
| D-400 | scaffold | — | `media/logo.png` (1024×1024 RGBA, sha256 3b2a0b76…) | added | TJ's README icon, copied byte for byte | open |
| D-401 | scaffold | — | `media/banner.webp` (2576×1439, 279188 bytes, sha256 cc3fe67b…) | added | TJ's final banner, README hero image, copied byte for byte | open |
| D-402 | scaffold | — | `tests/unit/test_identity.py:80` `tests/unit/test_identity.py` | added | Slice 08 Mini-req 5: canonical-author guard (pure filesystem) plus README structure checks | open |

## Core

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-099 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:14` `NodeKind` | `src/eta_rxncat/core/graph.py:18` `NodeKind` Literal | changed | Literal of the same five values instead of a str Enum | open |
| D-100 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:17` `NodeKind.REACTANT` | `src/eta_rxncat/core/graph.py:18` `"reactant"` | same | Same value, as a Literal member | open |
| D-101 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:18` `NodeKind.INTERMEDIATE` | `src/eta_rxncat/core/graph.py:18` `"intermediate"` | same | Same value, as a Literal member | open |
| D-102 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:19` `NodeKind.TRANSITION_STATE` | `src/eta_rxncat/core/graph.py:18` `"transition_state"` | same | Same value, as a Literal member | open |
| D-103 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:20` `NodeKind.PRODUCT` | `src/eta_rxncat/core/graph.py:18` `"product"` | same | Same value, as a Literal member | open |
| D-104 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:21` `NodeKind.OFF_CYCLE_SINK` | `src/eta_rxncat/core/graph.py:18` `"off_cycle_sink"` | same | Same value, as a Literal member | open |
| D-105 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:24` `StageKind` | `src/eta_rxncat/core/models.py:16` `StageKind` Literal | changed | Literal of the same five values instead of a str Enum | open |
| D-106 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:27` `StageKind.CONFORMER_SEARCH` | `src/eta_rxncat/core/models.py:16` `"conformer_search"` | same | Same value, as a Literal member | open |
| D-107 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:28` `StageKind.CONSTRAINED_PREOPT` | `src/eta_rxncat/core/models.py:16` `"constrained_preopt"` | same | Same value, as a Literal member | open |
| D-108 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:29` `StageKind.GEOMETRY_OPT` | `src/eta_rxncat/core/models.py:16` `"geometry_opt"` | same | Same value, as a Literal member | open |
| D-109 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:30` `StageKind.FREQUENCY` | `src/eta_rxncat/core/models.py:16` `"frequency"` | same | Same value, as a Literal member | open |
| D-110 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:31` `StageKind.SINGLE_POINT` | `src/eta_rxncat/core/models.py:16` `"single_point"` | same | Same value, as a Literal member | open |
| D-111 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:34` `SolvationSpec` | `src/eta_rxncat/core/models.py:113` `Solvation` | changed | Renamed per the contract; `none` forbids solvent/dielectric; engine compatibility checked on StageConfig | open |
| D-112 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:37` `model` | `src/eta_rxncat/core/models.py:122` | same | — | open |
| D-113 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:38` `solvent` | `src/eta_rxncat/core/models.py:123` | changed | Non-empty when given; forbidden for model `none` | open |
| D-114 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:39` `dielectric` | `src/eta_rxncat/core/models.py:124` | changed | Must also be finite; forbidden for model `none` | open |
| D-115 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:48` `StageConfig` | `src/eta_rxncat/core/models.py:142` | changed | Mission contract: strict method/basis/solvation/frozen-atom rules | open |
| D-116 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:51` `stage` | `src/eta_rxncat/core/models.py:155` `kind` | changed | Renamed `stage` → `kind` (mission contract) | open |
| D-117 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:52` `engine` | `src/eta_rxncat/core/models.py:156` | changed | Tags `rdkit_ff, mace, uma_direct, pyscf_gpu_cpu, xtb_subprocess` replace `rdkit_ff, xtb, mace, uma, pyscf` (mission R22) | open |
| D-118 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:53` `method` | `src/eta_rxncat/core/models.py:157` | changed | Required, no `"default"` default; the literal `default` in any case is rejected | open |
| D-119 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:57` `basis` | `src/eta_rxncat/core/models.py:158` | changed | Required non-empty iff engine is `pyscf_gpu_cpu`, otherwise must be `None` | open |
| D-120 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:61` `solvation` | `src/eta_rxncat/core/models.py:159` | changed | Type renamed to `Solvation` | open |
| D-121 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:62` `extra_options` | `src/eta_rxncat/core/models.py:161` `options` | changed | Renamed `extra_options` → `options`; float values must be finite | open |
| D-122 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:64` `stage_hash()` | — | dropped | Hashing belongs to the store slice (03, mission R5); this slice must not implement it | open |
| D-123 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:70` `ThermoConfig` | `src/eta_rxncat/core/models.py:265` | changed | Mission contract / R23 | open |
| D-124 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:73` `temperature_k` | `src/eta_rxncat/core/models.py:279` | changed | Must also be finite | open |
| D-125 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:74` `pressure_atm` | `src/eta_rxncat/core/models.py:280` | changed | Must also be finite | open |
| D-126 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:75` `concentration_mol_l` | `src/eta_rxncat/core/models.py:281` `standard_state_mol_l` | changed | Renamed; `None` forbidden (mission R23) | open |
| D-127 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:80` `quasi_rrho_mode` | `src/eta_rxncat/core/models.py:278` `entropy_model` | changed | Only `grimme_qrrho`; `head_gordon` and `none` dropped | open |
| D-128 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:81` `omega0_cm1` | `src/eta_rxncat/core/models.py:282` `qrrho_cutoff_cm1` | changed | Renamed per the contract | open |
| D-129 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:88` `MolecularState` | `src/eta_rxncat/core/models.py:61` | changed | Mission contract / R9: strict ints, canonical symbols, finite N×3, electron parity | open |
| D-130 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:91` `name` | — | dropped | Not in the mission contract (labels live on `Component`) | open |
| D-131 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:92` `symbols` | `src/eta_rxncat/core/models.py:73` | changed | Each must be a canonical symbol, Z 1–118 | open |
| D-132 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:93` `coordinates` | `src/eta_rxncat/core/models.py:74` | changed | Values must be finite | open |
| D-133 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:94` `charge` | `src/eta_rxncat/core/models.py:75` | changed | `StrictInt`: rejects `True`, `"1"`, `1.0` (mission R9) | open |
| D-134 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:95` `spin_multiplicity` | `src/eta_rxncat/core/models.py:76` | changed | `StrictInt ≥ 1` plus the electron-count/parity check (mission R9) | open |
| D-135 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:96` `active_atom_indices` | `src/eta_rxncat/core/models.py:77` | changed | `StrictInt` and unique | open |
| D-136 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:100` `metadata` | `src/eta_rxncat/core/models.py:78` | same | — | open |
| D-137 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:115` `coords_array()` | — | dropped | Not in the mission contract; numeric arrays arrive with the engines (v0.2.0) | open |
| D-138 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:118` `geometry_hash()` | — | dropped | Hashing belongs to the store slice (03, mission R6) | open |
| D-139 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:133` `AtomMappingSpec` | `src/eta_rxncat/core/models.py:203` | changed | Mission R19: full invariant list, plus template-level checks | open |
| D-140 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:143` `keep_atoms` | `src/eta_rxncat/core/models.py:213` `keep` | changed | Renamed; non-negative, unique | open |
| D-141 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:144` `delete_atoms` | `src/eta_rxncat/core/models.py:214` `delete` | changed | Renamed; required (no default); non-negative, unique | open |
| D-142 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:145` `alignment_atoms` | `src/eta_rxncat/core/models.py:215` `alignment` | changed | Renamed; must be ⊆ keep (≥ 3) | open |
| D-143 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:146` `attachment_anchors` | `src/eta_rxncat/core/models.py:216` `anchors` | changed | Renamed; must be ⊆ keep, unique | open |
| D-144 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:165` `VibrationalMode` | — | dropped | mission R8: defined by its consuming version | open |
| D-145 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:168` `VibrationalMode.frequency_cm1` | — | dropped | mission R8: defined by its consuming version | open |
| D-146 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:169` `VibrationalMode.displacement_vectors` | — | dropped | mission R8: defined by its consuming version | open |
| D-147 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:170` `VibrationalMode.active_core_kinetic_fraction` | — | dropped | mission R8: defined by its consuming version | open |
| D-148 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:178` `PotentialResult` | — | dropped | mission R8: defined by its consuming version | open |
| D-149 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:181` `PotentialResult.electronic_energy_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-150 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:182` `PotentialResult.forces_hartree_per_bohr` | — | dropped | mission R8: defined by its consuming version | open |
| D-151 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:183` `PotentialResult.hessian_hartree_per_bohr2` | — | dropped | mission R8: defined by its consuming version | open |
| D-152 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:184` `PotentialResult.wall_time_seconds` | — | dropped | mission R8: defined by its consuming version | open |
| D-153 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:185` `PotentialResult.backend_device` | — | dropped | mission R8: defined by its consuming version | open |
| D-154 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:186` `PotentialResult.recovery_steps_used` | — | dropped | mission R8: defined by its consuming version | open |
| D-155 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:189` `ThermoResult` | — | dropped | mission R8: defined by its consuming version | open |
| D-156 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:192` `ThermoResult.electronic_energy_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-157 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:193` `ThermoResult.zpe_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-158 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:194` `ThermoResult.thermal_enthalpy_corr_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-159 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:195` `ThermoResult.entropy_cal_per_mol_k` | — | dropped | mission R8: defined by its consuming version | open |
| D-160 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:196` `ThermoResult.gibbs_free_energy_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-161 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:197` `ThermoResult.imaginary_frequencies_cm1` | — | dropped | mission R8: defined by its consuming version | open |
| D-162 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:198` `ThermoResult.is_valid_stationary_point` | — | dropped | mission R8: defined by its consuming version | open |
| D-163 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:199` `ThermoResult.validation_notes` | — | dropped | mission R8: defined by its consuming version | open |
| D-164 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:202` `ConformerEnsemble` | — | dropped | mission R8: defined by its consuming version | open |
| D-165 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:205` `ConformerEnsemble.species_name` | — | dropped | mission R8: defined by its consuming version | open |
| D-166 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:206` `ConformerEnsemble.conformers` | — | dropped | mission R8: defined by its consuming version | open |
| D-167 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:207` `ConformerEnsemble.gibbs_energies_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-168 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:208` `ConformerEnsemble.boltzmann_weights` | — | dropped | mission R8: defined by its consuming version | open |
| D-169 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:209` `ConformerEnsemble.lowest_conformer_index` | — | dropped | mission R8: defined by its consuming version | open |
| D-170 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/models.py:210` `ConformerEnsemble.boltzmann_averaged_gibbs_hartree` | — | dropped | mission R8: defined by its consuming version | open |
| D-171 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:21` `TemplateGeometry` | `src/eta_rxncat/core/graph.py:36` | changed | Mission R18: multi-component templates, unique rank | open |
| D-172 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:24` `template_id` | `src/eta_rxncat/core/graph.py:49` `id` | changed | Renamed; unique within the node | open |
| D-173 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:25` `structure` | `src/eta_rxncat/core/graph.py:51` `components` | changed | One `MolecularState` → list of `Component` (state + count), mission R18 | open |
| D-174 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:26` `mapping` | `src/eta_rxncat/core/graph.py:52` | changed | Optional; checked against the template atom count (index < N, keep ∪ delete = all) | open |
| D-175 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:27` `priority_rank` | `src/eta_rxncat/core/graph.py:50` `rank` | changed | Renamed; required `StrictInt ≥ 1`, unique within the node | open |
| D-176 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:34` `PruningRule` | `src/eta_rxncat/core/graph.py:143` | changed | Schema and reference check only; never evaluated in v0.1.0 (mission contract) | open |
| D-177 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:37` `rule_id` | `src/eta_rxncat/core/graph.py:152` `id` | changed | Renamed; unique within the graph | open |
| D-178 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:38` `metric` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-179 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:39` `reference_node_id` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-180 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:40` `target_node_id` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-181 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:41` `operator` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-182 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:42` `threshold` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-183 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:43` `on_fail` | `src/eta_rxncat/core/graph.py:154` `parameters` | dropped | Typed rule fields replaced by free-form `parameters`; rule evaluation is out of v0.1.0 scope | open |
| D-184 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:46` `ReactionNode` | `src/eta_rxncat/core/graph.py:83` | changed | Mission contract / R18 | open |
| D-185 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:49` `node_id` | `src/eta_rxncat/core/graph.py:96` `id` | changed | Renamed; pattern `^[A-Za-z][A-Za-z0-9_.-]*$` | open |
| D-186 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:50` `label` | `src/eta_rxncat/core/graph.py:97` | same | — | open |
| D-187 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:51` `kind` | `src/eta_rxncat/core/graph.py:98` | changed | Literal instead of Enum | open |
| D-188 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:52` `priority` | `src/eta_rxncat/core/graph.py:99` | changed | Required `StrictInt ≥ 1` (no default 1) | open |
| D-189 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:57` `stoichiometry_multipliers` | `src/eta_rxncat/core/graph.py:32` `Component.count` | dropped | Stoichiometry moves to `Component.count` (mission R18) | open |
| D-190 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:61` `templates` | `src/eta_rxncat/core/graph.py:100` | changed | Unique ids and ranks; equal total charge and element multiset across templates | open |
| D-191 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:62` `stages` | `src/eta_rxncat/core/graph.py:101` | changed | `None` (not `[]`) means the graph's default stages | open |
| D-192 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:66` `notes` | — | dropped | Not in the mission contract | open |
| D-193 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:92` `ReactionEdge` | `src/eta_rxncat/core/graph.py:129` | changed | Self-loops and duplicate pairs rejected at graph level | open |
| D-194 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:95` `source_id` | `src/eta_rxncat/core/graph.py:138` `source` | changed | Renamed | open |
| D-195 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:96` `target_id` | `src/eta_rxncat/core/graph.py:139` `target` | changed | Renamed | open |
| D-196 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:97` `step_label` | `src/eta_rxncat/core/graph.py:140` `label` | changed | Renamed; optional, default `None` | open |
| D-197 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:98` `is_reversible` | — | dropped | Not in the mission contract | open |
| D-198 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:101` `ReactionGraph` | `src/eta_rxncat/core/graph.py:157` | changed | Mission contract | open |
| D-199 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:104` `name` | `src/eta_rxncat/core/graph.py:171` | same | — | open |
| D-200 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:105` `description` | — | dropped | Not in the mission contract | open |
| D-201 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:106` `default_stages` | `src/eta_rxncat/core/graph.py:174` | changed | Default `[]` instead of required, non-empty | open |
| D-202 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:107` `thermo` | `src/eta_rxncat/core/graph.py:175` | same | — | open |
| D-203 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:108` `nodes` | `src/eta_rxncat/core/graph.py:172` | same | — | open |
| D-204 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:109` `edges` | `src/eta_rxncat/core/graph.py:173` | changed | Self-loops and duplicate (source, target) pairs rejected; cycles allowed (mission R18) | open |
| D-205 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:110` `pruning_rules` | `src/eta_rxncat/core/graph.py:176` | changed | Unique ids; nodes reference them by id (starter rules referenced nodes instead) | open |
| D-206 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:132` `effective_stages()` | — | dropped | Not in the mission contract; stage resolution belongs to the orchestrator (v0.8.0) | open |
| D-207 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:137` `get_node()` | — | dropped | Not in the mission contract | open |
| D-208 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:143` `execution_order()` | `src/eta_rxncat/core/graph.py:207` `priority_order()` | changed | Returns ids sorted by `(priority, id)`, not nodes in declaration order | open |
| D-209 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:147` `to_yaml()` | — | dropped | Not in the mission contract (JSON dump only) | open |
| D-210 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:150` `to_json()` | `src/eta_rxncat/core/io.py:111` `dump_reaction_graph_json()` | changed | Module function per the contract | open |
| D-211 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/reaction_graph.py:154` `from_file()` | `src/eta_rxncat/core/io.py:69` `load_reaction_graph()` | changed | Module function; rejects duplicate keys; every failure is `GraphValidationError` (mission R9) | open |
| D-212 | core | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/core/__init__.py:24` `__all__` re-exports | `src/eta_rxncat/core/__init__.py:26` | changed | Re-exports the rewrite's public names (dropped models removed, new ones added) | open |
| D-213 | core | — | `src/eta_rxncat/core/elements.py:6` `ELEMENT_SYMBOLS` | added | Mission R9 / slice 02 Task 1: immutable Z 1–118 table | open |
| D-214 | core | — | `src/eta_rxncat/core/elements.py:23` `ATOMIC_NUMBERS` | added | Read-only symbol → Z map for the electron check | open |
| D-215 | core | — | `src/eta_rxncat/core/models.py:21` `EngineTag` | added | Frozen engine tags (mission R22) | open |
| D-216 | core | — | `src/eta_rxncat/core/models.py:24` `SolvationModel` | added | Solvation model Literal | open |
| D-217 | core | — | `src/eta_rxncat/core/models.py:27` `ScalarValue` | added | Value type of options/metadata/parameters maps | open |
| D-218 | core | — | `src/eta_rxncat/core/models.py:30` `PositiveInt` | added | `StrictInt ≥ 1` alias (mission R9) | open |
| D-219 | core | — | `src/eta_rxncat/core/models.py:31` `NonNegativeInt` | added | `StrictInt ≥ 0` alias | open |
| D-220 | core | — | `src/eta_rxncat/core/models.py:32` `PositiveFiniteFloat` | added | Finite float > 0 alias (ThermoConfig, dielectric) | open |
| D-221 | core | — | `src/eta_rxncat/core/models.py:35` `CoreModel` | added | Base: `extra="forbid"`, `frozen=True` on every model | open |
| D-222 | core | — | `src/eta_rxncat/core/models.py:160` `StageConfig.frozen_atom_indices` | added | Mission contract; required for `constrained_preopt` | open |
| D-223 | core | — | `src/eta_rxncat/core/models.py:189` `EngineIdentity` | added | Mission R5: engine identity for cache keys | open |
| D-224 | core | — | `src/eta_rxncat/core/models.py:198` `EngineIdentity.name` | added | Engine tag | open |
| D-225 | core | — | `src/eta_rxncat/core/models.py:199` `EngineIdentity.version` | added | Non-empty version | open |
| D-226 | core | — | `src/eta_rxncat/core/models.py:200` `EngineIdentity.model` | added | Optional weights id | open |
| D-227 | core | — | `src/eta_rxncat/core/models.py:247` `AtomMappingSpec.check_atom_count()` | added | Template-level checks (index < N, keep ∪ delete = all), mission R19 | open |
| D-228 | core | — | `src/eta_rxncat/core/models.py:283` `ThermoConfig.qrrho_alpha` | added | Mission R23: Grimme α default 4.0 | open |
| D-229 | core | — | `src/eta_rxncat/core/models.py:284` `ThermoConfig.qrrho_rotor_moment_kg_m2` | added | Mission R23: B_av default 1e-44 kg m² | open |
| D-230 | core | — | `src/eta_rxncat/core/graph.py:22` `Component` | added | Mission R18: species of a separated state with stoichiometric count | open |
| D-231 | core | — | `src/eta_rxncat/core/graph.py:31` `Component.state` | added | The species' structure | open |
| D-232 | core | — | `src/eta_rxncat/core/graph.py:32` `Component.count` | added | `StrictInt ≥ 1` | open |
| D-233 | core | — | `src/eta_rxncat/core/graph.py:33` `Component.label` | added | Optional name | open |
| D-234 | core | — | `src/eta_rxncat/core/graph.py:55` `TemplateGeometry.atom_count` | added | Size of the template index space | open |
| D-235 | core | — | `src/eta_rxncat/core/graph.py:60` `TemplateGeometry.total_charge` | added | Σ(count × charge), for the node consistency check | open |
| D-236 | core | — | `src/eta_rxncat/core/graph.py:65` `TemplateGeometry.element_counts` | added | Σ(count × symbols), for the node consistency check | open |
| D-237 | core | — | `src/eta_rxncat/core/graph.py:102` `ReactionNode.pruning_rules` | added | Rule ids referenced by the node | open |
| D-238 | core | — | `src/eta_rxncat/core/graph.py:154` `PruningRule.parameters` | added | Free-form scalar parameters | open |
| D-239 | core | — | `src/eta_rxncat/core/graph.py:153` `PruningRule.description` | added | What the rule gates | open |
| D-240 | core | — | `src/eta_rxncat/core/graph.py:170` `ReactionGraph.schema_version` | added | Required `Literal[1]` file schema version | open |
| D-241 | core | — | `src/eta_rxncat/core/io.py:13` `GraphValidationError` | added | Single error type for every loader failure (mission contract) | open |

## Store

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-270 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:23` `StageCacheKey` | `src/eta_rxncat/store/keys.py:82` `StageKey` | changed | Frozen dataclass with key_schema, stage kind, engine and version (mission R5) | open |
| D-271 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:26` `input_geometry_hash` | `src/eta_rxncat/store/keys.py:96` `geometry_hash` | changed | Renamed; hash of the field-by-field canonical geometry payload (5-decimal grid, -0.0 folded), not `sha256(model_dump())` (R6) | open |
| D-272 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:27` `stage_config_hash` | `src/eta_rxncat/store/keys.py:97` `stage_hash` | changed | Renamed; canonical stage payload including EngineIdentity, integral floats as ints (R5) | open |
| D-273 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:28` `composite_key` | `src/eta_rxncat/store/keys.py:98` `key` | changed | `h({key_schema, geometry_hash, stage_hash})` instead of `sha256("g:s")`; versioned (R5) | open |
| D-274 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:31` `StageCacheKey.build(state, stage)` | `src/eta_rxncat/store/keys.py:104` `build_stage_key(state, stage, engine)` | changed | Module function; requires an EngineIdentity whose name matches the stage engine (R5) | open |
| D-275 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:42` `ArtifactStore` | `src/eta_rxncat/store/artifact_store.py:72` | changed | Immutable completed rows, WAL, versioned schema (R7) | open |
| D-276 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:45` `ArtifactStore(db_path=".eta_cache/artifacts.sqlite")` + `mkdir(parents=True)` | `src/eta_rxncat/store/artifact_store.py:80` `ArtifactStore(path, *, open_timeout_s=5.0)` | changed | Required path, no default, no mkdir; missing parent → FileNotFoundError (R7) | open |
| D-277 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:46` attribute `db_path` | `src/eta_rxncat/store/artifact_store.py:105` `path` | changed | Renamed | open |
| D-278 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:73` `get(key)` | `src/eta_rxncat/store/artifact_store.py:245` | same | Returns the payload only when completed, as before | open |
| D-279 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:85` `put(key, stage, payload, status="completed")` with `INSERT OR REPLACE` | `src/eta_rxncat/store/artifact_store.py:182` `put(key, status, payload)` | changed | No overwrite of completed rows (ArtifactConflictError; same payload = no-op); `BEGIN IMMEDIATE`; canonical JSON with `allow_nan=False`; stage taken from the key (R7) | open |
| D-280 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:57` SQL table `stage_artifacts` | `src/eta_rxncat/store/artifact_store.py:26` | changed | Created once on a new file under `user_version` 1, not `IF NOT EXISTS` on every open | open |
| D-281 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:58` column `composite_key` | `src/eta_rxncat/store/artifact_store.py:27` | changed | Renamed `key` | open |
| D-282 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:59` column `input_geometry_hash` | `src/eta_rxncat/store/artifact_store.py:29` | changed | Renamed `geometry_hash` | open |
| D-283 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:60` column `stage_config_hash` | `src/eta_rxncat/store/artifact_store.py:30` | changed | Renamed `stage_hash` | open |
| D-284 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:61` column `stage_kind` | `src/eta_rxncat/store/artifact_store.py:31` | same | — | open |
| D-285 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:62` column `engine` | `src/eta_rxncat/store/artifact_store.py:32` | same | — | open |
| D-286 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:63` column `status` | `src/eta_rxncat/store/artifact_store.py:34` | changed | `CHECK(status IN ('pending','running','completed','failed'))` | open |
| D-287 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:64` column `payload_json` | `src/eta_rxncat/store/artifact_store.py:35` | changed | Canonical JSON (`sort_keys`, compact, ASCII, `allow_nan=False`) | open |
| D-288 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:65` column `created_at_utc` | `src/eta_rxncat/store/artifact_store.py:37` | same | — | open |
| D-289 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/artifact_store.py:70` index `idx_geom_hash` | `src/eta_rxncat/store/artifact_store.py:41` `idx_stage_artifacts_geometry` | changed | Renamed; same column (geometry hash) | open |
| D-290 | store | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/__init__.py:5` `__all__` re-exports | `src/eta_rxncat/store/__init__.py:22` | changed | Re-exports the rewrite's public names | open |
| D-291 | store | — | `src/eta_rxncat/store/keys.py:15` `KEY_SCHEMA` | added | Mission R5: versioned key payload | open |
| D-292 | store | — | `src/eta_rxncat/store/keys.py:18` `JsonScalar` | added | Type alias of option scalars | open |
| D-293 | store | — | `src/eta_rxncat/store/keys.py:21` `canon()` | added | Mission contract canonical JSON | open |
| D-294 | store | — | `src/eta_rxncat/store/keys.py:32` `h()` | added | sha256 of canon | open |
| D-295 | store | — | `src/eta_rxncat/store/keys.py:37` `grid_coordinate()` | added | Mission R6: 5-decimal grid, -0.0 folded, fixed-point string | open |
| D-296 | store | — | `src/eta_rxncat/store/keys.py:45` `canonical_number()` | added | Integral floats keyed as ints | open |
| D-297 | store | — | `src/eta_rxncat/store/keys.py:52` `geometry_payload()` | added | Field-by-field geometry payload; metadata not keyed | open |
| D-298 | store | — | `src/eta_rxncat/store/keys.py:63` `stage_payload()` | added | Field-by-field stage payload with engine identity | open |
| D-299 | store | — | `src/eta_rxncat/store/keys.py:95` `StageKey.key_schema` | added | Payload schema version | open |
| D-300 | store | — | `src/eta_rxncat/store/keys.py:99` `StageKey.stage_kind` | added | Stored in its own column for `query` | open |
| D-301 | store | — | `src/eta_rxncat/store/keys.py:100` `StageKey.engine` | added | Stored in its own column for `query` | open |
| D-302 | store | — | `src/eta_rxncat/store/keys.py:101` `StageKey.engine_version` | added | Stored in its own column | open |
| D-303 | store | — | `src/eta_rxncat/store/artifact_store.py:17` `SCHEMA_VERSION` | added | `PRAGMA user_version` this code reads (R7) | open |
| D-304 | store | — | `src/eta_rxncat/store/artifact_store.py:46` `ArtifactStatus` (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`) | added | Mission R7 status enum (starter used a free string) | open |
| D-305 | store | — | `src/eta_rxncat/store/artifact_store.py:55` `ArtifactConflictError` | added | Refused write to a completed row (R7) | open |
| D-306 | store | — | `src/eta_rxncat/store/artifact_store.py:59` `StoreSchemaError` | added | Unknown `user_version` (R7) | open |
| D-307 | store | — | `src/eta_rxncat/store/artifact_store.py:257` `ArtifactStore.status()` | added | Status lookup | open |
| D-308 | store | — | `src/eta_rxncat/store/artifact_store.py:265` `ArtifactStore.invalidate()` | added | The only way to replace a completed artifact (R7) | open |
| D-309 | store | — | `src/eta_rxncat/store/artifact_store.py:283` `ArtifactStore.query()` | added | Sorted keys filtered by stage kind and engine | open |
| D-310 | store | — | `src/eta_rxncat/store/artifact_store.py:297` `ArtifactStore.close()`, `__enter__`, `__exit__` | added | Explicit close and context manager | open |
| D-311 | store | — | `src/eta_rxncat/store/artifact_store.py:124` pragmas `journal_mode=WAL`, `busy_timeout=5000` | added | Mission R7: concurrent readers/writers | open |
| D-312 | store | — | `src/eta_rxncat/store/artifact_store.py:170` pragma `user_version=1` | added | Mission R7: schema version; other non-zero values refused | open |
| D-313 | store | — | `src/eta_rxncat/store/artifact_store.py:28` column `key_schema` | added | Mission R5 | open |
| D-314 | store | — | `src/eta_rxncat/store/artifact_store.py:33` column `engine_version` | added | Mission R5 | open |
| D-315 | store | — | `src/eta_rxncat/store/artifact_store.py:36` column `payload_sha256` | added | Idempotent completed re-put (R7) | open |
| D-316 | store | — | `src/eta_rxncat/store/artifact_store.py:38` column `updated_at_utc` | added | Updated on non-completed rewrites | open |
| D-317 | store | — | `src/eta_rxncat/store/artifact_store.py:42` index `idx_stage_artifacts_kind_engine` | added | Supports `query(stage_kind, engine)` | open |
| D-318 | store | — | `tests/unit/store/test_store_keys.py` | added | Key proof bullets (golden key, grid, per-field sensitivity, metadata, int/float/bool) | open |
| D-319 | store | — | `tests/unit/store/test_store_artifacts.py` | added | Store proof bullets (path, pragmas, schema, write rules, invalidate, query, threads, NaN) | open |
| D-403 | store | — | `src/eta_rxncat/store/artifact_store.py:63` `StoreBusyError` | added | Slice 09 (R42, R52): any BUSY/LOCKED during open past `open_timeout_s` (version read, WAL switch or schema transaction; RESERVED, IMMEDIATE or EXCLUSIVE holder); chains the last `OperationalError`; a raw 'database is locked' never escapes `__init__` | open |
| D-404 | store | — | `src/eta_rxncat/store/artifact_store.py:80` `ArtifactStore(path, *, open_timeout_s=5.0)` | added | Slice 09 (R42, R52; ADR-0015 PROPOSED): one deadline for the whole open. The version read, WAL switch and BEGIN IMMEDIATE each wait at most the remaining time (busy_timeout set per attempt, BUSY/LOCKED retried 5 ms doubling to 100 ms); must be > 0; the version is checked before any write; busy_timeout 5000 after open | open |

## Hardware probe

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-320 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/__init__.py:1` module `eta_rxncat.utils` (docstring only) | `src/eta_rxncat/utils/__init__.py:1` | same | Docstring-only package module | open |
| D-321 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:9` `HardwareReport` | `src/eta_rxncat/utils/hw_probe.py:85` | changed | Mission contract: `report_schema` 1, nested torch/gpu/gpu4pyscf objects, flags; `extra="forbid"` | open |
| D-322 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:12` `torch_installed` | `src/eta_rxncat/utils/hw_probe.py:62` `torch.installed` | changed | Moved into the nested `torch` object (`TorchInfo`) | open |
| D-323 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:13` `cuda_available` | `src/eta_rxncat/utils/hw_probe.py:64` `torch.cuda_available` | changed | Moved into `torch`; `cuda_unavailable` flag | open |
| D-324 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:14` `device_name` | `src/eta_rxncat/utils/hw_probe.py:71` `gpu.name` | changed | Moved into the nested `gpu` object (`GpuInfo`), `null` without a GPU | open |
| D-325 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:15` `compute_capability` | `src/eta_rxncat/utils/hw_probe.py:72` `gpu.compute_capability` | changed | Moved into `gpu`; same `"12.0"` form | open |
| D-326 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:16` `total_vram_gb` | `src/eta_rxncat/utils/hw_probe.py:73` `gpu.total_vram_gib / gpu.total_vram_bytes` | changed | Exact bytes plus GiB (2 dp) instead of rounded "GB" (mission R12) | open |
| D-327 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:17` `recommended_vram_budget_gb` | `src/eta_rxncat/utils/hw_probe.py:100` `vram_budget_bytes` | changed | Budget min(6.5 GiB, total) in bytes, not `0.80 × total` in GB (Master Plan "~6.5 GB VRAM budget"; R12 GiB) | open |
| D-328 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:18` `gpu4pyscf_installed` | `src/eta_rxncat/utils/hw_probe.py:81` `gpu4pyscf.installed` | changed | Moved into the nested `gpu4pyscf` object with its version; `gpu4pyscf_missing` / `gpu4pyscf_below_1.8.0` flags | open |
| D-329 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:19` `mace_installed` | — | dropped | MLIP packages are slice 06's optional extras; not in the report contract | open |
| D-330 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:20` `fairchem_installed` | — | dropped | As `mace_installed` | open |
| D-331 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:21` `notes` | `src/eta_rxncat/utils/hw_probe.py:102` `notes` | same | Free-text notes | open |
| D-332 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:28` `probe_hardware(vram_safety_fraction=0.80)` | `src/eta_rxncat/utils/hw_probe.py:248` `probe_hardware()` | changed | No safety-fraction argument (fixed 6.5 GiB rule); reads versions and CUDA runtime; never raises for a broken CUDA or gpu4pyscf import | open |
| D-333 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:25` probe depth: importability via `find_spec` | `src/eta_rxncat/utils/hw_probe.py:382` `run_smoke()` (kernel execution) | changed | Plan PR #2 asks for JIT/native kernel execution: the smoke test runs GPU4PySCF and a CUDA matmul against CPU references | open |
| D-334 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:65` Blackwell / 8 GB class notes | — | dropped | Replaced by machine-readable flags and the fixed budget; no GPU-class special cases (mission R12, out of scope §3) | open |
| D-335 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/utils/hw_probe.py:90` `python -m eta_rxncat.utils.hw_probe` JSON print | — | dropped | `eta-rxncat hardware-check` (slice 05) prints the report | open |
| D-336 | hw_probe | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/unit/test_hw_probe.py:6` `test_probe_hardware_returns_valid_report` | `tests/unit/utils/test_utils_hw_probe.py:288`, `tests/unit/utils/test_utils_hw_probe.py:110` | changed | Fake absent-package report (R44) plus fake-GPU reports with exact budget and flags | open |
| D-337 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:21` `VRAM_BUDGET_GIB` | added | 6.5 GiB budget constant | open |
| D-338 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:24` `MIN_TORCH_CUDA` | added | (12, 8): sm_120 support | open |
| D-339 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:27` `MIN_GPU4PYSCF` | added | (1, 8, 0) | open |
| D-340 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:30` `SCF_TOLERANCE_EH` | added | Smoke pass criterion |ΔE| ≤ 1e-6 Eh (mission R10) | open |
| D-341 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:33` `MATMUL_TOLERANCE` | added | Smoke pass criterion max-abs-diff ≤ 1e-9 (mission R10) | open |
| D-342 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:44` `parse_version_prefix()` | added | Numeric dotted-prefix version comparison | open |
| D-343 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:54` `vram_budget_bytes()` | added | min(int(6.5 × 2³⁰), total) | open |
| D-344 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:59` `TorchInfo` (`installed`, `version`, `cuda_available`, `cuda_version`) | added | Nested report object | open |
| D-345 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:68` `GpuInfo` (`name`, `compute_capability`, `total_vram_bytes`, `total_vram_gib`, `free_vram_bytes`) | added | Nested report object; free VRAM reported, never used for the budget | open |
| D-346 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:78` `Gpu4PySCFInfo` (`installed`, `version`) | added | Nested report object | open |
| D-347 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:93` `HardwareReport.report_schema` | added | Report schema version 1 | open |
| D-348 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:94` `HardwareReport.python_version` | added | Contract field | open |
| D-349 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:95` `HardwareReport.platform` | added | Contract field | open |
| D-350 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:99` `HardwareReport.vram_budget_gib` | added | Always 6.5 | open |
| D-351 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:101` `HardwareReport.flags` | added | Machine-readable problems (five exact strings) | open |
| D-352 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:265` `ScfCheck` | added | Smoke SCF record (mission contract) | open |
| D-353 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:278` `TorchOpCheck` | added | Smoke matmul record | open |
| D-354 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:287` `SmokeResult` | added | Smoke result (`result_schema` 1, status, reason, scf, torch_op, timings, host) | open |
| D-355 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:382` `run_smoke(timeout_s=600.0)` | added | US-004a: child process, numeric pass criterion, skip when torch/CUDA/gpu4pyscf are missing | open |
| D-356 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:434` `smoke_exit_code()` | added | pass 0, fail 1, skipped 3 | open |
| D-357 | hw_probe | — | `src/eta_rxncat/utils/_smoke_child.py:13` `eta_rxncat.utils._smoke_child` | added | Child-process smoke work (H₂O RHF/STO-3G on GPU and CPU, seeded float64 CUDA matmul); prints measurements only | open |
| D-358 | hw_probe | — | `tests/unit/utils/test_utils_hw_probe.py` | added | Probe proof bullets with fake torch/gpu4pyscf modules | open |
| D-359 | hw_probe | — | `tests/unit/utils/test_utils_smoke.py` | added | Smoke proof bullets with fake hosts and child scripts (pass, each failing check, timeout, malformed output, crash) | open |
| D-360 | hw_probe | — | `tests/gpu/test_smoke.py:9` `tests/gpu/test_smoke.py` | added | `@pytest.mark.gpu` acceptance test (deselected by default; slice 07 runs it) | open |
| D-383 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:232` flags `torch_import_failed`, `gpu4pyscf_import_failed` | added | Mission R43: an installed package whose import raises is reported (installed true, metadata version, note), never raised and never read as missing | open |
| D-384 | hw_probe | — | `src/eta_rxncat/utils/hw_probe.py:319` `run_smoke` fails on a broken install | added | Mission R43: `*_import_failed` → `fail` (exit 1) with the package and exception, no child process; `skipped` keeps meaning not installed / no CUDA | open |
| D-385 | hw_probe | — | `tests/unit/utils/test_utils_smoke.py:99` `test_skipped_without_torch` (was `test_skipped_on_this_environment`) | added | Mission R44: unit tests use a fake host via the `_import`/`_dist_version` seam; the one real-environment skip check is `tests/unit/cli/test_cli.py::test_console_script_smoke_skipped`, skipped when torch is installed | open |

## CLI

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-361 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:14` `main(argv: list[str] | None)` | `src/eta_rxncat/cli.py:70` `main(argv: Sequence[str] | None)` | changed | Accepts any sequence; returns 2 on a usage error instead of letting argparse raise SystemExit | open |
| D-362 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:16` parser `prog`/`description` | `src/eta_rxncat/cli.py:27` | changed | Same prog; description reworded | open |
| D-363 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:21` subcommand `hardware-check` | `src/eta_rxncat/cli.py:31` | same | Same name | open |
| D-364 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:30` `hardware-check` output `json.dumps(model_dump(), indent=2)` | `src/eta_rxncat/cli.py:51` `model_dump_json(indent=2)` | changed | Pydantic JSON serialisation of the slice-04 report (contract fields) | open |
| D-365 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:31` `hardware-check` exit 0 | `src/eta_rxncat/cli.py:52` | same | Exit 0; flags are inside the JSON | open |
| D-366 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:23` subcommand `validate` | `src/eta_rxncat/cli.py:38` | same | Same name | open |
| D-367 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:24` argument `graph_file` (`type=Path`) | `src/eta_rxncat/cli.py:39` `path` | changed | Renamed `path` per the slice spec; still `type=Path` | open |
| D-368 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:37` `validate` output: one sentence with name, counts and a Python list of ids | `src/eta_rxncat/cli.py:63` four lines `OK <path>`, `nodes:`, `edges:`, `priority_order:` | changed | Fixed four-line format (mission contract, CLI) | open |
| D-369 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:35` order via `execution_order()` (declaration order within a tier) | `src/eta_rxncat/cli.py:66` `priority_order()` | changed | Sorted by `(priority, id)` (slice 02) | open |
| D-370 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:34` invalid graph → uncaught exception and traceback | `src/eta_rxncat/cli.py:59` `error: <message>` on stderr, exit 1 | changed | One line, no traceback; only GraphValidationError is caught (mission R21) | open |
| D-371 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:43` fall-through `return 1` | — | dropped | Unreachable: the subcommand is required and both are handled | open |
| D-372 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:46` `sys.exit(main())` under `__main__` in cli.py | `src/eta_rxncat/__main__.py:6` `src/eta_rxncat/__main__.py` | changed | `python -m eta_rxncat` instead of `python -m eta_rxncat.cli` | open |
| D-373 | cli | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py:11` module-level import of `hw_probe` | `src/eta_rxncat/cli.py:45` | changed | Imported inside the hardware-check handler, so `validate` loads nothing from utils | open |
| D-374 | cli | — | `src/eta_rxncat/cli.py:34` `hardware-check --smoke` | added | US-004a: smoke JSON on stdout, exit `smoke_exit_code` (0/1/3) | open |
| D-375 | cli | — | `src/eta_rxncat/cli.py:3` exit-code table (0/1/2/3) | added | Mission R21: fixed table, documented in the module docstring | open |
| D-376 | cli | — | `src/eta_rxncat/cli.py:79` usage error → exit 2 returned from `main` | added | argparse usage errors (no command, unknown command, missing/extra argument, unknown flag) return 2 | open |
| D-377 | cli | — | `src/eta_rxncat/cli.py:60` multi-line error messages collapsed to one line | added | PyYAML syntax errors span lines; stderr stays one line | open |
| D-378 | cli | — | `tests/unit/cli/test_cli.py` | added | CLI proof bullets: in-process `main()` and installed-script subprocess tests | open |

## Fixture

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-242 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml` (file) | `tests/data/reaction_graphs/example_reaction_graph.yaml` | changed | New path (mission R17; agents never write `tests/fixtures/`); a new graph (SN2 Cl⁻ + CH₃Cl), not a copy | open |
| D-243 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:1` top-level `name` | `tests/data/reaction_graphs/example_reaction_graph.yaml:6` | same | — | open |
| D-244 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:2` top-level `description` | — | dropped | Not in the graph contract (replaced by a YAML comment) | open |
| D-245 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:3` top-level `default_stages` | `tests/data/reaction_graphs/example_reaction_graph.yaml:7` | changed | Uses `kind` and the frozen engine tags; three stages | open |
| D-246 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:20` top-level `thermo` | `tests/data/reaction_graphs/example_reaction_graph.yaml:24` | changed | Keys `temperature_k`, `standard_state_mol_l` (starter `concentration_mol_l`, `quasi_rrho_mode`, `omega0_cm1` renamed/dropped) | open |
| D-247 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:26` top-level `nodes` | `tests/data/reaction_graphs/example_reaction_graph.yaml:32` | changed | Three nodes (TS, reactants, products) in two priority tiers | open |
| D-248 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:50` top-level `edges` | `tests/data/reaction_graphs/example_reaction_graph.yaml:117` | changed | Two edges (starter has none) | open |
| D-249 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:51` top-level `pruning_rules` | `tests/data/reaction_graphs/example_reaction_graph.yaml:27` | changed | One rule, referenced by the TS node (starter has none) | open |
| D-250 | fixture | — | `tests/data/reaction_graphs/example_reaction_graph.yaml:5` top-level `schema_version` | added | Required by the graph contract | open |
| D-251 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:27` node `node_id` | `tests/data/reaction_graphs/example_reaction_graph.yaml:33` | changed | Renamed `id` | open |
| D-252 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:28` node `label` | `tests/data/reaction_graphs/example_reaction_graph.yaml:34` | same | — | open |
| D-253 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:29` node `kind` | `tests/data/reaction_graphs/example_reaction_graph.yaml:35` | same | — | open |
| D-254 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:30` node `priority` | `tests/data/reaction_graphs/example_reaction_graph.yaml:36` | same | — | open |
| D-255 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:31` node `templates` | `tests/data/reaction_graphs/example_reaction_graph.yaml:38` | same | — | open |
| D-256 | fixture | — | `tests/data/reaction_graphs/example_reaction_graph.yaml:37` node `pruning_rules` | added | Node references a graph rule | open |
| D-257 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:32` template `template_id` | `tests/data/reaction_graphs/example_reaction_graph.yaml:39` | changed | Renamed `id` | open |
| D-258 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:33` template `priority_rank` | `tests/data/reaction_graphs/example_reaction_graph.yaml:40` | changed | Renamed `rank` | open |
| D-259 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:34` template `structure` | `tests/data/reaction_graphs/example_reaction_graph.yaml:41` | changed | Replaced by `components` (state + count). Starter state CH3 (9 electrons) with multiplicity 1 is chemically impossible and would fail the new electron check | open |
| D-260 | fixture | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/e2e/fixtures/example_reaction_graph.yaml:45` template `mapping` | `tests/data/reaction_graphs/example_reaction_graph.yaml:56` | changed | Keys `keep`, `delete`, `alignment`, `anchors` (renamed); keep ∪ delete covers all atoms | open |
| D-261 | fixture | — (starter `edges: []` has no edge objects) | `tests/data/reaction_graphs/example_reaction_graph.yaml:118` edge `source`, `target`, `label` | added | Edge object keys per the contract | open |

## Tests

| ID | Area | Starter item (path:line) | Rewrite (path:line or —) | Disposition | Reason | Status |
|---|---|---|---|---|---|---|
| D-262 | tests | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/unit/test_core_schemas.py:39` `test_molecular_state_requires_charge_and_multiplicity` | `tests/unit/core/test_core_molecule.py:32` | changed | Rewritten; strictness cases in `test_charge_and_multiplicity_are_strict_ints` | open |
| D-263 | tests | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/unit/test_core_schemas.py:46` `test_atom_mapping_spec_rejects_overlap` | `tests/unit/core/test_core_mapping_thermo.py:55` (`keep-delete-overlap`) | changed | One parametrised case per invariant | open |
| D-264 | tests | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/unit/test_core_schemas.py:55` `test_reaction_graph_yaml_roundtrip_and_priority_order` | `tests/unit/core/test_core_graph_io.py:228`, `tests/unit/core/test_core_graph_io.py:161` | changed | Split into round-trip and `(priority, id)` ordering tests | open |
| D-265 | tests | `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/tests/unit/test_core_schemas.py:85` `test_stage_decomposed_cache_incremental_solvation` | `tests/unit/store/test_store_artifacts.py:161` | changed | Covered by slice 03: a second stage on the same geometry misses while the first hits | open |
| D-266 | tests | — | `tests/unit/core/test_core_molecule.py` | added | MolecularState proof bullets (slice 02) | open |
| D-267 | tests | — | `tests/unit/core/test_core_stage.py` | added | StageConfig/Solvation/EngineIdentity proof bullets | open |
| D-268 | tests | — | `tests/unit/core/test_core_mapping_thermo.py` | added | AtomMappingSpec and ThermoConfig proof bullets | open |
| D-269 | tests | — | `tests/unit/core/test_core_graph_io.py` | added | Graph, loader, import-isolation and no-unsafe-YAML proof bullets | open |
