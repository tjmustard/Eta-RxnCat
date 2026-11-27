---
slice: OPR.0.7.1.1
candidate_sha: 809be0c
artifact_type: guard
verdict: CLEAR
money_evidence: full pytest 2747 passed, 0 skipped; 57 integration ids
  default-selected; ledger valid, 65/65 fixtures owned
---

# Execute evidence: 01-integration-harness (OPR.0.7.1.1) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `8707bed`. C1 `1d26110` (code, tests, ledger node and fixture globs). C2 `809be0c` (updater
flags, lore stale marks, progress, task boxes, field note). Then this proof. No push, no tag.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-slice01`.

## Commands and exit codes

`TMPDIR=~/.cache/eta-rxncat-tmp`; each under `timeout` (3600 for uv, 600 for scripts).

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and again before the updater) | 0 | `index: ok` |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 859 files already formatted |
| `uv run mypy` | 0 | no issues, 91 source files |
| `uv run pytest tests/integration tests/unit/test_test_policy.py -q --junitxml=E/targeted.xml` | 0 | 83 passed (57 integration) |
| `uv run pytest -q --junitxml=E/default.xml` | 0 | 2747 passed, 196 deselected, 0 skipped; 57 integration ids selected; 204.9 s |

The full run was on the working tree that became C1; afterwards only mission files, lore flags and
ledger flags changed. A first `ruff check` during iteration failed on 3 findings (2 line length,
1 docstring capital); fixed before the runs above.

## Requirement 4: loader and recipes against the E2E originals (scratch script, not committed)

`.venv/bin/python` with `tests/e2e` on `sys.path`, exit 0: `load_v070_plan().plan.model_dump_json()`
== `v070.load_enumeration().plan.model_dump_json()`; both run settings equal;
`gfn2_stage() == e2e_env.engine_for("xtb")[0]` and its runtime is `{}`. The committed parity test
is slice 02's.

## Ledger (requirement 5)

- `ensure-node --id eta_rxncat_integration --dimension Module --files 'tests/integration/**'
  --depends-on core,store,optimize,selectivity,species_runner --description-file ... --spec-refs
  OPR.0.7.1.1` (full ids), exit 0. Description 800 chars.
- `ensure-node --from-spec <SPEC>` exit 0, no change (skipped the glob and the three owned paths).
- `ensure-node --files` with each node's full previous list plus the new globs, exit 0 each.

| node | files entries | tracked paths matched | fixtures | description chars |
|---|---|---|---|---|
| species_runner | 12 -> 16 | 234 -> 295 | 0 -> 61 | 1991 unchanged |
| mapping | 9 -> 10 | 63 -> 66 | 0 -> 3 | 1865 unchanged |
| scaffold | 23 -> 25 | 279 -> 281 | 0 -> 1 | 1978 unchanged |

Fixtures: 65 tracked, owned 0 -> 65. The ledger diff adds only `files` lines to existing nodes, so
core and engines are untouched by `ensure-node`. `validate` ok (exit 0, again after C2).
`impact --files tests/integration/conftest.py` -> `nodes: ["eta_rxncat_integration"]`, exit 0.

Import scan of `tests/integration/**` (AST):

| module imported (all from conftest.py) | names | owning node |
|---|---|---|
| eta_rxncat.core | EnumerationPlan, MolecularState, StageConfig | core |
| eta_rxncat.optimize | GeometricOptimizer | optimize |
| eta_rxncat.orchestrator | Recipe | selectivity (`__init__.py`) |
| eta_rxncat.store | ArtifactStore | store |

Plus the data owners species_runner and core.

## Updater (once, after C1)

`hypergraph_updater.py --from-diff 8707bed --apply --slice OPR.0.7.1.1 --json`, exit 0.

- dirty: cli, core, hw_probe, integration, scaffold, store (several own `pyproject.toml` or the
  ledger file).
- blast radius: all 15 nodes.
- unmapped: the 4 mission files (PROGRESS.md, mission.yaml, slice PROGRESS.md and SPEC.md), plus
  untracked files the updater also lists: the two `.claude/*.bak-*`, `spec/archive/**` and
  `spec/process/**` (names only; none were opened or staged).
- lore marked stale (impact): ADR-0054..ADR-0065 (all PROPOSED). Kept and committed in C2.

## For the audit to rule on

1. `depends_on` has no `eta_rxncat_engines`: the spec expects "core, store, engines, orchestrator",
   but nothing under `tests/integration/` imports engines. It has optimize (imported) and
   selectivity (`Recipe` comes from the orchestrator package).
2. `load_v070_plan()` returns a `V070Plan` NamedTuple (`.plan` plus the two settings). The context
   bullet says "the plan plus ..."; mini-requirement 4 says "returns an EnumerationPlan".
3. Added `tests/integration/__init__.py`, so helpers import as `from .conftest import ...`.
   Checked with a scratch test (removed): it passes, and `tests.integration` is not importable
   under `uv run pytest` ("No module named 'tests'").
4. The scanner reports more than R26 lists: `pytest.MonkeyPatch.*`, relative imports that leave the
   directory, `add_marker`/`applymarker` with a skip or forbidden-marker string, `unittest.mock`
   attribute use, any load of `setattr`/`delattr`, and assignment into any name imported from
   `eta_rxncat` (classes too).
5. Not caught by the scanner: bare-name imports of e2e/unit helpers through a `sys.path` edit
   (`from e2e_env import ...`), `getattr` indirection, `sys.modules.pop()`/`update()`, and
   `monkeypatch` passed on to a helper under another parameter name. R26 names none of these.
6. R4 docstrings: only the policy module docstring names a seam break (remove a rule from `scan`);
   its four test functions carry none. The slice SPEC lists no breaks and R30 reads none from 01.
7. Three commits (code; flags; proof), as v0.7.0 did, since the updater runs after the commit.
8. The gate hook denied one combined command (a heredoc script plus `hyper_lore.py note`) in this
   permission mode; nothing ran. The note was then run as its own direct call, as the hook's
   message and the round notes say.
