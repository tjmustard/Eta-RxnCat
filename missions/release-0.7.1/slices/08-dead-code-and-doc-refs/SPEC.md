---
id: OPR.0.7.1.8
slice: 08-dead-code-and-doc-refs
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Remove dead code only on scripted evidence, add a stale-reference scan for docs and docstrings, write the geomeTRIC docstring caveats, and tie README claims to records."
depends_on: [OPR.0.7.1.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["src/eta_rxncat/**", tools/engine_reachable.py, tests/unit/test_doc_refs.py, "tests/unit/**", README.md, "docs/*.md", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_doc_refs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Dead-code pass, stale-reference scan, docstring caveats and claims

## Intent

Remove dead code only on scripted evidence, add a deterministic stale-reference scan for docs and
docstrings, write the geomeTRIC docstring caveats, and tie every README claim to a record (mission
R17, R18, R19, R31, R41; US-008).

Context the builder needs:
- **R31 exclusion set:** commit `tools/engine_reachable.py` (scaffold, stdlib `ast` only). It prints
  every `eta_rxncat` module reachable by import from `ENGINE_CLASSES` (`orchestrator/species.py:84`)
  and from the optimizer classes in `eta_rxncat.optimize`, plus every module imported by a test that
  carries `xtb`, `gpu`, `mlip_*`, `slow`, `acceptance` or `e2e`. Its output goes in the proof.
- **R17 evidence:**
  1. `coverage run -m pytest` on the default suite, which now includes Tier O, then
     `coverage report`;
  2. `ruff check --select F401,F841 src tools tests`, run ad hoc and not added to config;
     `--select ERA001` hits are listed as review prompts only;
  3. `git grep -n '<name>'` across `src/ tools/ tests/ docs/ README.md` for each candidate.
  - **Remove only** a symbol with 0 coverage, 0 references outside its own definition, not in any
    `__all__`, and not in R31's set.
  - Public symbols are listed and kept.
  - The proof table has one row per candidate: symbol, file:line, coverage, references, verdict and
    reason.
  - Cap rule: a removal in a node at or above 1990 chars (enumerator 1997, optimize 1997,
    species_runner 1991, engines 1991) is listed and kept, unless it needs no description word.
- **R18:** new `tests/unit/test_doc_refs.py` (scaffold). Every backticked dotted name beginning
  `eta_rxncat.` must resolve. The names are taken from:
  - `README.md`;
  - `CHANGELOG.md`, from the `[Unreleased]` / `[0.7.1]` heading onward (older entries are history);
  - `docs/*.md`, but not `docs/prd/**`;
  - the docstrings under `src/**`.
  - **How names resolve:**
    - A module importable with the base deps is imported lazily.
    - An engine-extra module is found with `importlib.util.find_spec` and **never imported**. Its
      attributes are resolved by AST from the module source: top-level `def`, `class`, assignment
      and `__all__` names.
  - Positive and negative parametrised cases, including a planted stale name that fails.
  - Fix each stale reference found at `bf7b949` and list it in the proof.
- **R41 (docstrings only, optimize 1997):**
  - `optimize/geometric_impl.py`: the process-wide `chdir` affects relative paths in a host program's
    own threads, and the cwd lock is not reentrant.
  - `optimize/ts_base.py`: the one-`hessian=False`-per-step contract.
  - No code change. The two deferred edge cases go in CHANGELOG in slice 09.
- **R19:** list each README claim the review finds unsupported, and cite or remove it. Every new claim
  cites a test id and a `QUALITY_RESULT.json` key (the key is filled in slice 09). No number may
  appear without a record behind it.
- **Ledger:** each node with a removal; scaffold 1978, so compress first if needed.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/`.
  - The ruff format oracle is only
    `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`.
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.7.0/`, older
    missions or `PRDs/`. Plain literal `rm -f` only, and never `rm -rf` on a computed path.
  - Ledger caps (mission §5 carry-forward 7): any description word in a node at or above 1978 chars
    is compressed for first, with the before and after counts in the proof. Core gets no words.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.
- **Licence:** no new Python or JS dependency; the core stays MIT/BSD.

## 1. The Confidence Mandate

**Score: 9/10.** The method is fully scripted (R31, R17), and no removal is presumed. Residual: how
many stale references exist today. That is unknown until the scan runs, and each one is fixed and
listed.

## Mini-requirements

1. `tools/engine_reachable.py` exists, and its output is in the proof.
2. The R17 table is complete, and every removal meets all four conditions.
3. `test_doc_refs.py` is green, its negative cases fail, and the stale references found are fixed and
   listed.
4. The R41 docstrings are present, with no code change in optimize.
5. The R19 claim list is in the proof.
6. The default suite is green after the removals. Tier X is rerun under the heavy-run rule if any
   removal touched a module Tier X imports.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] `engine_reachable.py`; coverage, ruff and grep evidence.
- [ ] Removals and the table.
- [ ] `test_doc_refs.py` and the stale-reference fixes.
- [ ] R41 docstrings; R19 list.
- [ ] Required checks (and Tier X if triggered); commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** remove a public symbol, or anything without its evidence row.
- **DO NOT** add vulture or any other dependency, and **DO NOT** add ruff rules to the config.
- **DO NOT** change behaviour in optimize. R41 is docstrings only.
- **DO NOT** edit `docs/prd/**` or CHANGELOG entries older than 0.7.1.

## Proof contract

- [ ] The `engine_reachable.py` output and the R17 table (requirements 1-2).
- [ ] `uv run pytest tests/unit/test_doc_refs.py -q` passes, with its negative cases shown
  (requirement 3).
- [ ] The diff of the optimize files is docstring-only (requirement 4).
- [ ] The required checks exit 0 (requirements 5-6).

## Source material

- Mission R17, R18, R19, R31 and R41; the v0.7.0 slice 06 audit notes.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.7.
