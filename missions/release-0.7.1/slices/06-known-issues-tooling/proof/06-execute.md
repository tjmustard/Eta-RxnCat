---
slice: OPR.0.7.1.6
candidate_sha: 5e09deb
artifact_type: guard
verdict: CLEAR
money_evidence: 21 new tests fail at bf7b949 and 31 at 1d26110, then pass; full
  pytest 2848 passed; R28 verdict sets equal
---

# Execute evidence: 06-known-issues-tooling (OPR.0.7.1.6) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `e98f5c6`. C1 `b9d0f3d` (code and tests). C2 `5e09deb` (ledger flags, progress, task boxes,
field note). Then this proof. No push, no tag, no package install or sync.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-06`. `P` = the project root.

## Failing at the base, passing after (requirements 1, 2, 4, 5)

R22 interpreter: `PYTHONPATH=<worktree>/src P/.venv/bin/python -m pytest -p no:cacheprovider`;
`eta_rxncat.__file__` was under each worktree. `src/`, `tools/`, `tests/conftest.py` and
`tests/e2e/t3.py` were unchanged in both worktrees. Both worktrees were removed afterwards.

Worktree at `bf7b949`: only the new tests added (the new file `test_t3_gated_on.py`; new cases and
tests spliced into the base test files; R40's `stand_in`, `IN_PINNED_ONLY` and two tests appended
to the base scan file). Exit 1, **21 failed, 71 passed** (`E/fail-base.txt`).

| R | failed at `bf7b949` | seen |
|---|---|---|
| R10 | `tests/e2e/test_t3_gated_on.py::test_gated_on_text_equals_the_record[{n4,ts1a_n,ts1b_n,ts3a,ts4a}-xtb]` | `'convergence, mode count' == 'convergence,...in phase, KE)'` (ts4a: `== 'none (report-only, R32)'`) |
| R11a | `tests/unit/test_test_policy.py::test_module_level_skip_scanner[{module-alias,module-alias-in-if,decorator,argument-default,keyword-only-default,async-default,lambda-default,method-decorator,class-base,class-keyword}]` | `assert False is True` |
| R11b | `tests/unit/test_test_policy.py::test_teardown_skip_fails_under_acceptance` | `ExitCode.OK == 1` |
| R39 | `tests/unit/review/test_assets.py::test_the_wheel_build_is_offline` | `'--offline' in ['uv', 'build', '--wheel', '--out-dir', ...]` |
| R40 | `tests/unit/review/test_bundle_scans.py::test_the_host_data_scan_skips_the_pinned_3dmol_file[{plain,hostile}-{user,host}]` | `('assets/3Dmol-min.js', 'Float32Array')` |

The uma cases of R10, the skip-without-variable test and the negative skip cases pass at the base,
as expected.

R44, worktree at `1d26110`: the base scanner with the new `NEGATIVE_CASES`, positive cases and two
new tests. Exit 1, **31 failed, 61 passed** (`E/fail-1d.txt`). Failed:

- `test_scanner_reports_form[...]`, each `assert '<form>' in set()`: `sibling-e2e`,
  `sibling-e2e-from`, `sibling-t3`, `sibling-t4`, `sibling-v070`, `sibling-unit`, `wrapper-return`,
  `wrapper-yield`, `wrapper-named-fixture`, `wrapper-of-wrapper`, `wrapper-tuple`,
  `wrapper-tuple-index`, `wrapper-attribute`, `getattr-eta`, `getattr-sys-modules`, `vars-eta`,
  `vars-sys-modules`, `dict-eta`, `dict-sys-modules`, `sys-modules-pop`, `sys-modules-update`,
  `sys-modules-setdefault`, `sys-modules-setitem`, `import-module-mock`, `import-module-alias`,
  `dunder-import-mock`, `dunder-import-fromlist`, `dunder-import-positional`,
  `dunder-import-bare-mock` (29);
- `test_sibling_names_come_from_the_directories` and `test_wrapper_alias_crosses_modules` (these
  two fail there because the helper functions do not exist yet).

After the change the new tests pass (required checks below), including
`test_integration_directory_is_clean`.

## R28 profile verdicts (requirement 3)

`UV_PROJECT_ENVIRONMENT=<env> uv run --no-sync python -I tools/licence_gate.py --profile <p>`,
before any edit and after. Compared per (package, version): pass / exempt / FAIL, and the FAIL
lines. Outputs `E/before-<p>.txt`, `E/after-<p>.txt`.

| profile | env | exit before / after | packages | pass, exempt, FAIL | verdicts and FAIL lines equal | labelled rows after |
|---|---|---|---|---|---|---|
| base | `.venv-runtime` | 0 / 0 | 13 | 13, 0, 0 | yes | 1 |
| gpu | `.venv-accept-gpu` | 1 / 1 | 59 | 41, 17, 1 | yes | 4 |
| mlip-mace | `.venv-accept-mace` | 1 / 1 | 87 | 62, 24, 1 | yes | 8 |
| mlip-uma | `.venv-accept-uma` | 1 / 1 | 139 | 108, 30, 1 | yes | 11 |

The one FAIL in the three extra profiles, before and after, is `pathspec:1.1.1` (MPL-2.0). I infer
it comes from these acceptance envs holding the dev tools, which the CI commands leave out
(`--no-dev`); I did not build a no-dev env to confirm it.
`antlr4-python3-runtime 4.9.3` in `mlip-uma`: `BSD [BSD (variant not stated)] ... pass`.

## R39 measurement

Before the edit: `UV_OFFLINE=1 uv build --wheel --offline --out-dir <scratch>` exit 0
(`eta_rxncat-0.7.0-py3-none-any.whl`), uv 0.13.8. Also seen: with every proxy pointed at a dead
port, `uv build --wheel` **without** `--offline` still succeeded from the warm cache (with
`--refresh` it failed on the hatchling index), so a network-blocked run cannot fail reliably at the
base. The failing test therefore checks the command the wheel test runs.

## Required checks (requirement 6)

On the tree that became C1, `uv run --no-sync`, `TMPDIR` and `ETA_RXNCAT_XTB` set:

| command | exit | seen |
|---|---|---|
| `ruff check .` | 0 | All checks passed |
| `ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 874 files already formatted |
| `mypy` | 0 | no issues, 91 source files |
| `pytest tests/unit/test_test_policy.py tests/unit/tools/test_licence_gate.py tests/unit/review tests/integration/test_integration_policy.py` | 0 | 291 passed |
| `timeout 3600 ... pytest` | 0 | **2848 passed, 202 deselected**, 2 warnings, 219.33 s (2763 at slice 05, +85) |
| licence gate, base, `.venv-runtime` | 0 | 13 packages, 0 failures |

`uv sync --locked` and the `.venv-runtime` sync in AGENTS.md "Required checks" were not run (round
notes: no installs). The 2 warnings' text was not kept; the targeted run of 326 tests over the
changed areas printed no warnings summary in its tail. Host before the full run: 11 GiB available,
one other `python3` process at 100 % CPU.

## Ledger and other commands

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and before the updater) | 0 | `index: ok` |
| `hyper_gates.py mode`; `hyper_spec.py resolve <slice dir> --json` | 0 | interactive; no errors |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | see below |
| `hypergraph_updater.py --from-diff e98f5c6 --apply --slice OPR.0.7.1.6 --json` (once) | 0 | see below |
| `hyper_ledger.py validate` | 0 | ok |
| one field note (mission `NOTES.md`) | 0 | |
| `pytest` on the two policy files while iterating | 1, then 0 | `wrapper-of-wrapper` failed until `scan` resolved wrapper chains |
| `ruff check tests/` while iterating | 1, then 0 | one long docstring line in `tests/conftest.py` |
| two `uv build ... --refresh` probes with `UV_NO_CACHE=` set empty | 2 | my setup error; rerun without it |
| the first command writing this proof | blocked | the gate hook refused a heredoc whose text named the lore script; no lore command was in it; body written with the Write tool |

`ensure-node`: skipped the glob `tests/e2e/test_t3_*.py` and the paths owned by
`species_runner`, `review` and `integration`. It appended three exact paths to
`eta_rxncat_scaffold` (25 to 28 entries; all 25 kept): `tools/licence_gate.py`,
`tests/unit/tools/test_licence_gate.py`, `docs/licence-inventory.md`, each already covered by that
node's own `tools/**`, `tests/unit/tools/**` and `docs/**`.

Updater: dirty `cli`, `core`, `hw_probe`, `integration`, `review`, `scaffold`, `species_runner`,
`store`; blast radius also `conformers`, `engines`, `enumerator`, `mapping`, `optimize`,
`selectivity`, `thermo`. `lore_stale_candidates` empty. `unmapped`: the `.claude` backups, the
mission and slice files, and untracked `spec/` files listed by name (none opened). Full JSON
`E/updater.json`. No `src/` file changed; `impact --files pyproject.toml` names only `cli` and
`scaffold`, and the code graph's component list equals the dirty list. I did not trace why `core`,
`hw_probe` and `store` are in it.

No ledger description changed.

## For the auditor to rule on

1. **R44, wrapper forms.** A wrapper that returns `monkeypatch` itself gets the full allow-list. A
   wrapper that returns it inside a tuple, a call result or an attribute is a "container": on it and
   on names unpacked from it only the patcher's mutator names are reported (`setattr`, `delattr`,
   `setitem`, `delitem`, `syspath_prepend`, `context`, `undo`), so that `tmp_path.joinpath` in the
   same tuple stays legal. A wrapper counts only where a parameter carries its name.
2. **R44, reach.** Wrappers are resolved across modules (`scan` takes an optional third argument)
   and through `@pytest.fixture(name=...)`. Still not caught: `builtins.getattr`, indirection on an
   object returned by an eta call (not an imported name), a non-constant module name, and a patcher
   passed on by other routes (a global, an attribute set outside the returning function).
3. **R11a.** At the base a class base or keyword using plain `pytest.` is already walked, so the two
   class cases use the module alias to fail there. Lambda defaults are visited too; annotations are
   not.
4. **R28.** The loader treats a missing `labels` table as no labels. Adding the id to `allowed`
   also allows a package that declares `LicenseRef-BSD-classifier` as its expression.
   `docs/licence-inventory.md` does not name the mapping, so it is unchanged.
5. **R10.** t3 picks the report-only text by the fixture name `e2e5_t3_ts4a_mapped`.
6. **R40.** The skip is by content hash, so both pinned files (`3Dmol-min.js`,
   `LICENSE-3Dmol.txt`) are skipped for every forbidden string, paths included; a changed 3Dmol
   file is scanned. The pins are imported from `test_assets.py`. The planted-name cases are guards on
   the new skip, not failing-first tests. `test_export.py` is unchanged.
7. **Extra positive cases:** `monkeypatch-user-not-wrapper` and `dynamic-import-not-mock`;
   `conftest-relative-import` is close to the older `relative-import`.
8. **Carry-forward (from the slice 05 audit, not changed):** `_ts_recipe` and `_member_gates` still
   live in `test_seams_ts_gfn2.py`, not `conftest.py`.
9. The optional integration description clause for R44 was left to the audit's `apply-review`.
