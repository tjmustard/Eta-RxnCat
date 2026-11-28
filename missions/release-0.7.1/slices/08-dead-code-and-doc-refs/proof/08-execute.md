---
slice: OPR.0.7.1.8
candidate_sha: 8db4000
artifact_type: guard
verdict: CLEAR
money_evidence: "full pytest 2900 passed; doc-refs 22 passed with planted stale
  names failing; R17: 0 removals (all candidates referenced); ADR-0066 PROPOSED,
  validate ok"
---

# Execute evidence: 08-dead-code-and-doc-refs (OPR.0.7.1.8) - builder (not a QA verdict)

The artifact type is `guard` only because the proof writer has no `execute` type; the audit writes
the QA verdict.

Start `69ab910`. C1 `b4e7a90` (code, tests, README, ADR-0066 proposal and lore index). C2 `8db4000`
(ledger flags, lore stale marks, progress, task boxes, field notes). Then this proof. No push, no
tag, no package install or sync, no engine run. `E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-08`.

## Required checks (requirement 6)

Run on the C1 tree (C2 changes no code):

| command | exit | seen |
|---|---|---|
| `uv run --no-sync ruff check .` | 0 | All checks passed |
| `uv run --no-sync ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 881 files already formatted |
| `uv run --no-sync mypy` | 0 | no issues in 92 source files |
| `timeout 3600 uv run --no-sync pytest -p no:cacheprovider` | 0 | 2900 passed, 202 deselected (`E/s08-pytest-full.log`) |
| `timeout 3600 uv run --no-sync pytest tests/unit/test_doc_refs.py -v -p no:cacheprovider` | 0 | 22 passed (`E/doc-refs-v.txt`) |

`ETA_RXNCAT_XTB` and `TMPDIR` set as the run record says. Tier X not rerun: no removal.

## Requirement 1: `tools/engine_reachable.py`

`python3 tools/engine_reachable.py`, exit 0. Full output in `E/s08-reach.txt`:

- engine seed modules: `engines.esen_omol25`, `engines.mace`, `engines.pyscf_gpu_cpu.engine`,
  `engines.rdkit_ff`, `engines.uma_direct`, `engines.xtb_subprocess`;
- optimizer seed modules: `optimize.base`, `optimize.geometric_impl`, `optimize.prfo`,
  `optimize.ts_base`;
- 43 heavy-marked test files;
- excluded modules: **87 of 90**; outside the set: `eta_rxncat.__main__`,
  `eta_rxncat.review.schema.__main__`, `eta_rxncat.utils._smoke_child`.

Parent packages of every import count, as do function-level imports and the `tests/e2e` helpers the
marked files import. The set is therefore wide. No verdict below depends on it: every candidate has
at least one reference.

## Requirement 2: R17 evidence

- `timeout 3600 uv run --no-sync coverage run --source=src/eta_rxncat,tools -m pytest -q -p no:cacheprovider`:
  exit 0, 2878 passed, 202 deselected (the suite before `test_doc_refs.py`).
- `uv run --no-sync coverage report`: exit 0, TOTAL 91% (`E/s08-cov-report.txt`). 0% files:
  `__main__.py`, `review/schema/__main__.py`, `utils/_smoke_child.py`, `tools/engine_reachable.py`
  (new in this slice, not a base symbol).
- `ruff check --select F401,F841 src tools tests --exclude tests/candidate_outputs`: exit 0, no hits.
- `ruff check --select ERA001` (same paths): exit 1, 2 review prompts,
  `tests/unit/conformers/test_conformers_generate.py:160` and
  `tests/unit/orchestrator/test_species_runner.py:147`. Both are section comments, not code. Kept.
- `git grep -nwI -e <name>` over `src tools tests docs README.md`, excluding
  `tests/candidate_outputs`, at HEAD = Start, minus hits inside the definition (`E/s08_r17.py`).

Method note: the docstring edits landed while the coverage run was in progress, which shifts line
numbers in the two optimize files for `coverage report`. The table therefore maps the run's executed
lines onto the Start sources (`git show HEAD:<file>`): 817 functions and classes. A candidate is a
function or class with no executed body statement (a member of a zero function is not listed twice).
Reference counts are word matches, so generic names over-count; the cited line is a code use where
the script found one. Coverage does not follow subprocesses, so `tools/licence_gate.py`, which its
tests run as a subprocess, reads 0.

| symbol | file:line | coverage | refs outside definition (grep -w hits; a use) | __all__ | R31 | verdict: reason |
|---|---|---|---|---|---|---|
| `_registry` | `src/eta_rxncat/engines/_fairchem_bridge.py:58` | 0/3 | 6; `src/eta_rxncat/engines/_fairchem_bridge.py:170` | no | yes | keep: referenced; R31 module |
| `_cached` | `src/eta_rxncat/engines/_fairchem_bridge.py:73` | 0/5 | 8; `src/eta_rxncat/engines/_fairchem_bridge.py:182` | no | yes | keep: referenced; R31 module |
| `FairchemEngine._load_unit` | `src/eta_rxncat/engines/_fairchem_bridge.py:206` | 0/15 | 2; `src/eta_rxncat/engines/_fairchem_bridge.py:202` | no | yes | keep: referenced; R31 module |
| `FairchemEngine._atomic_data` | `src/eta_rxncat/engines/_fairchem_bridge.py:278` | 0/5 | 4; `src/eta_rxncat/engines/_fairchem_bridge.py:303` | no | yes | keep: referenced; R31 module |
| `FairchemEngine._evaluate.forces_at` | `src/eta_rxncat/engines/_fairchem_bridge.py:335` | 0/3 | 9; `src/eta_rxncat/engines/_fairchem_bridge.py:341` | no | yes | keep: referenced; R31 module |
| `_default_dtype` | `src/eta_rxncat/engines/mace.py:69` | 0/5 | 2; `src/eta_rxncat/engines/mace.py:202` | no | yes | keep: referenced; R31 module |
| `MACEEngine._energy_forces` | `src/eta_rxncat/engines/mace.py:178` | 0/23 | 6; `src/eta_rxncat/engines/mace.py:222` | no | yes | keep: referenced; R31 module |
| `MACEEngine._evaluate.forces_at` | `src/eta_rxncat/engines/mace.py:231` | 0/3 | 9; `src/eta_rxncat/engines/mace.py:237` | no | yes | keep: referenced; R31 module |
| `PySCFEngine._fd_hessian` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:583` | 0/14 | 1; `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:654` | no | yes | keep: referenced; R31 module |
| `PySCFEngine._passthrough` | `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:607` | 0/3 | 4; `src/eta_rxncat/engines/pyscf_gpu_cpu/engine.py:417` | no | yes | keep: referenced; R31 module |
| `_gpu_lowest` | `src/eta_rxncat/engines/pyscf_gpu_cpu/stability.py:93` | 0/21 | 1; `src/eta_rxncat/engines/pyscf_gpu_cpu/stability.py:56` | no | yes | keep: referenced; R31 module |
| `XTBSubprocessEngine.hessian_file` | `src/eta_rxncat/engines/xtb_subprocess.py:308` | 0/4 | 1; `tests/unit/engines/test_xtb.py:558` | no | yes | keep: referenced; R31 module; public, listed and kept |
| `CountingEngine._evaluate` | `src/eta_rxncat/orchestrator/counting.py:54` | 0/1 | 48; `src/eta_rxncat/engines/base.py:116` | no | yes | keep: referenced; R31 module; required override of the abstract `Engine._evaluate` |
| `RunMetrics.as_payload` | `src/eta_rxncat/orchestrator/species.py:191` | 0/1 | 11; `tests/e2e/t3.py:137` | no | yes | keep: referenced; R31 module; public, listed and kept |
| `_RecordingEngine.stage` | `src/eta_rxncat/orchestrator/ts.py:194` | 0/1 | 978; `src/eta_rxncat/engines/base.py:3` | no | yes | keep: referenced; R31 module; implements the abstract `Engine.stage` property |
| `_RecordingEngine.identity` | `src/eta_rxncat/orchestrator/ts.py:198` | 0/1 | 452; `src/eta_rxncat/review/export.py:460` | no | yes | keep: referenced; R31 module; implements the abstract `Engine.identity` property |
| `_RecordingEngine._evaluate` | `src/eta_rxncat/orchestrator/ts.py:217` | 0/1 | 48; `src/eta_rxncat/engines/base.py:116` | no | yes | keep: referenced; R31 module; required override of the abstract `Engine._evaluate` |
| `_RecordingEngine.__getattr__` | `src/eta_rxncat/orchestrator/ts.py:220` | 0/1 | 3; `src/eta_rxncat/orchestrator/__init__.py:105` | no | yes | keep: referenced; R31 module; dunder: delegation, called by Python |
| `main` | `src/eta_rxncat/utils/_smoke_child.py:13` | 0/21 | 97; `src/eta_rxncat/utils/_smoke_child.py:58` | no | no | keep: referenced |
| `_child_argv` | `src/eta_rxncat/utils/hw_probe.py:314` | 0/1 | 3; `src/eta_rxncat/utils/hw_probe.py:416` | no | yes | keep: referenced; R31 module |
| `normalise` | `tools/licence_gate.py:48` | 0/1 | 12; `tools/licence_gate.py:339` | no | no | keep: referenced; public, listed and kept |
| `tokenize` | `tools/licence_gate.py:53` | 0/12 | 1; `tools/licence_gate.py:139` | no | no | keep: referenced; public, listed and kept |
| `_Parser.__init__` | `tools/licence_gate.py:76` | 0/4 | 176; `tools/licence_gate.py:139` (`_Parser(...)`) | no | no | keep: referenced |
| `_Parser.peek` | `tools/licence_gate.py:82` | 0/1 | 6; `tools/licence_gate.py:100` | no | no | keep: referenced |
| `_Parser.take` | `tools/licence_gate.py:85` | 0/5 | 18; `tools/licence_gate.py:101` | no | no | keep: referenced |
| `_Parser.parse` | `tools/licence_gate.py:92` | 0/4 | 49; `tools/licence_gate.py:139` | no | no | keep: referenced |
| `_Parser.or_expr` | `tools/licence_gate.py:98` | 0/6 | 2; `tools/licence_gate.py:117` | no | no | keep: referenced |
| `_Parser.and_expr` | `tools/licence_gate.py:106` | 0/6 | 2; `tools/licence_gate.py:102` | no | no | keep: referenced |
| `_Parser.with_expr` | `tools/licence_gate.py:114` | 0/16 | 2; `tools/licence_gate.py:107` | no | no | keep: referenced |
| `spdx_allowed` | `tools/licence_gate.py:133` | 0/1 | 2; `tools/licence_gate.py:280` | no | no | keep: referenced; public, listed and kept |
| `_strings` | `tools/licence_gate.py:179` | 0/4 | 4; `tools/licence_gate.py:194` | no | no | keep: referenced |
| `_text` | `tools/licence_gate.py:186` | 0/4 | 44; `tools/licence_gate.py:237` | no | no | keep: referenced |
| `_profiles` | `tools/licence_gate.py:193` | 0/5 | 2; `tools/licence_gate.py:239` | no | no | keep: referenced |
| `_string_map` | `tools/licence_gate.py:201` | 0/4 | 3; `tools/licence_gate.py:232` | no | no | keep: referenced |
| `load_config` | `tools/licence_gate.py:210` | 0/13 | 1; `tools/licence_gate.py:404` | no | no | keep: referenced; public, listed and kept |
| `_shown` | `tools/licence_gate.py:269` | 0/2 | 1; `tools/licence_gate.py:297` | no | no | keep: referenced |
| `judge` | `tools/licence_gate.py:275` | 0/23 | 6; `tools/licence_gate.py:360` | no | no | keep: referenced; public, listed and kept |
| `_location` | `tools/licence_gate.py:310` | 0/1 | 1; `tools/licence_gate.py:330` | no | no | keep: referenced |
| `installed` | `tools/licence_gate.py:315` | 0/25 | 139; `tools/licence_gate.py:358` | no | no | keep: referenced; public, listed and kept |
| `run` | `tools/licence_gate.py:353` | 0/25 | 1084; `tools/licence_gate.py:408` | no | no | keep: referenced; public, listed and kept |
| `main` | `tools/licence_gate.py:391` | 0/19 | 97; `tools/licence_gate.py:419` | no | no | keep: referenced; public, listed and kept |

Module-level candidates (the three 0% files outside the new tool):

| module | coverage | reference | R31 | verdict: reason |
|---|---|---|---|---|
| `eta_rxncat.__main__` | 0% | `README.md:361` (`python -m eta_rxncat`), `tests/unit/cli/test_cli.py:246` | no | keep: referenced entry point, public |
| `eta_rxncat.review.schema.__main__` | 0% | `src/eta_rxncat/review/schema/__init__.py:3` | no | keep: referenced entry point, public |
| `eta_rxncat.utils._smoke_child` | 0% | `src/eta_rxncat/utils/hw_probe.py:316` | no | keep: referenced, run with `-m` |

**Result: 0 removed, all candidates kept.** No ledger description changed.

## Requirement 3: stale-reference scan

- `test_no_stale_references` passes. Negative cases: seven `test_does_not_resolve` ids,
  `test_engine_extra_modules_are_never_imported`, and `test_planted_stale_names_fail`, which plants
  stale names in README, docs, `[Unreleased]`, `[0.7.1]` and two docstrings and expects exactly
  those six (the `docs/prd`, `[0.7.0]` and comment plants are not reported).
- Stale references at `bf7b949`: **none**. The scan over `git archive bf7b949` sources and docs
  (with `PYTHONPATH` on those sources) found 35 references, 0 stale. 35 and 0 at this tree too.
- Limits for the audit: (a) the engine-extra list is explicit (seven modules). The scan never calls
  `import_module` on them, but `find_spec` imports parent packages, and `eta_rxncat.engines` and
  `eta_rxncat.optimize` import some of those modules themselves (base dependencies only). (b) For
  those modules, class members are resolved from the class body, so an inherited member would read
  as stale. (c) A name counts only when it directly follows a backtick (or `` `~ ``).

## Requirement 4: R41, docstrings only

`git diff 69ab910 b4e7a90 -- src`: two files, 10 added lines, all inside docstrings.
`optimize/geometric_impl.py` (`GeometricOptimizer`): the process-wide temporary cwd affects a
host's relative paths in other threads; the lock is not reentrant. `optimize/ts_base.py`
(`find_saddle`): one `hessian=False` evaluation per history step, in order.

## Requirement 5: R19 claim list (README)

| claim | finding | action |
|---|---|---|
| Installation: "supports Python 3.11-3.13" | no record or CI run on 3.11 or 3.13 | narrowed to "declares", cites `requires-python`; CI uses 3.12 (`.python-version`) |
| v0.2.0: "A GPU KS analytic Hessian is used only where the committed support record shows it correct" | `gpu_ks_hessian_class` ignores `cartesian_basis`; the record does not cover it | narrowed, links `pyscf-gpu-support.json` (class list checked by `tests/unit/engines/test_gpu_hessian_record.py`) |
| v0.2.0: "Known limits ... One affects users" | the GPU-Hessian VRAM limit in `known_limits` is arguably user-facing too (CPU fallback covers it) | kept; for the audit to rule |
| v0.4.0: copyright of the original `nMap` | provenance statement with no repo record | kept (author's statement) |

Checked against records and found supported: v0.2.0 energy bounds (largest CUDA reference diff
1.4e-7 Eh, largest UMA/eSEN 2.1e-8 Eh, smoke 1.0e-12 Eh); v0.7.0 53 `seed_clash` over 11 runs, ratio
0.409-1.286, 0 `bond_changed`, 0 stalls, 43 files, 11,977,758 bytes, ddG values, 15 commands exit 0
with 0 skips. v0.3.0-v0.6.0 record claims are covered by `tests/unit/test_identity.py` (113 passed
after the README edits). Pitch, header, badges, Features titles and Roadmap are untouched. No new
claim and no new number added. "Forward-only stores" agrees with the ADR-0066 wording; CHANGELOG
`[0.7.0]` is unedited and there is no `[0.7.1]` entry yet.

## Requirement 7: R45

- The propose verb, with `--supersedes ADR-0053 --body-file <file>`, as one direct command:
  `ADR-0066 written`. The scratch body equals the SPEC body (compared by script) and is contained in
  the node (`E/s08-adr-body.md`). Then the lore index, exit 0.
- `show ADR-0066`: status PROPOSED, `supersedes: [ADR-0053]`. Validate: exit 0 (`validate: ok`),
  rerun after the updater.
- ADR-0053's file is unchanged (`git diff 69ab910 -- lore/canon` is empty). Nothing approved,
  rejected or edited.
- The index also moved `planned` anchors to `anchors` on 58 nodes (union per node unchanged, no
  status change). The updater then marked ADR-0066 stale (`impact`), though it is PROPOSED.
- Slice 09 CHANGELOG `[0.7.1]` input: new node **ADR-0066**; the two deferred R41 edge cases.
