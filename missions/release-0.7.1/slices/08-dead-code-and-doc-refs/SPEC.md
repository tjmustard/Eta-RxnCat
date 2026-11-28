---
id: OPR.0.7.1.8
slice: 08-dead-code-and-doc-refs
mission: release-0.7.1
status: done
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Remove dead code only on scripted evidence, add a stale-reference scan for docs and docstrings, write the geomeTRIC docstring caveats, and tie README claims to records."
depends_on: [OPR.0.7.1.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["src/eta_rxncat/**", tools/engine_reachable.py, tests/unit/test_doc_refs.py, "tests/unit/**", README.md, "docs/*.md", "lore/**", lore_hypergraph.yml, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_doc_refs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Dead-code pass, stale-reference scan, docstring caveats and claims

## Intent

Remove dead code only on scripted evidence, add a deterministic stale-reference scan for docs and
docstrings, write the geomeTRIC docstring caveats, and tie every README claim to a record. It also
proposes the narrowed successor of ADR-0053 that TJ chose (mission R17, R18, R19, R31, R41, R45;
US-008).

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
- **R45, ADR-0053 narrowed (replan 1; TJ "Narrow it (Recommended)", advisor relay
  `qitem-20261127204642-06c18509e72ce4bb`):** ADR-0053 says "A v0.6.0 reader refuses v0.7.0 rows".
  The probe proved less than that: a v0.6.0 reader refuses v0.7.0 successful TS-search (`ts_opt`)
  rows (87 of 87 on a replan-7 store copy; v0.7.0 `NOTES.md`, field note of 11-27). The README's
  "Forward-only stores" bullet already says only this.
  - Write the body below to a scratch file under `TMPDIR`, then run, as one direct command (not in a
    heredoc or a Python wrapper, which the gate hook refuses):
    `python3 .agents/scripts/hyper_lore.py propose --type decision --title 'Optimization frames are
    payload-only, a v0.6.0 reader refuses v0.7.0 TS-search rows, and geomeTRIC runs in a per-run temp
    cwd' --body-file <file> --supersedes ADR-0053 --relates-to ADR-0016,ADR-0024 --anchors-components
    eta_rxncat_optimize,eta_rxncat_core,eta_rxncat_species_runner --anchors-files
    src/eta_rxncat/optimize/geometric_impl.py,src/eta_rxncat/core/optimization_models.py,src/eta_rxncat/core/ts_models.py
    --source OPR.0.7.1.8`, then `python3 .agents/scripts/hyper_lore.py index`.
  - Do not edit ADR-0053's files, and run no gated lore verb (approve, reject, retire, review). The
    node stays PROPOSED until TJ approves it at a pane.
  - **Body (exact):**

    ```markdown
    ## Context

    TJ's Phase 3 audit needs every optimization's path (v0.7.0 Q-A3). eta's stage keys (ADR-0016) are
    the cache contract, and geomeTRIC is a black box run in-process (ADR-0024). The clean room forbids
    reading its source. geomeTRIC writes mode files (`HT.v_*.txt`) into the process cwd: 14 landed in
    the repo root during the v0.6.0 verdict. ADR-0053 said a v0.6.0 reader refuses every v0.7.0 row.
    A probe measured less: on a v0.7.0 replan-7 store copy, a v0.6.0 reader refused 87 of 87
    successful `ts_opt` rows, because `TSStep` gained `coordinates_angstrom`, while its geometry_opt
    rebuild picks known payload keys. TJ chose to narrow the claim to what was proved (v0.7.1 R45).

    ## Decision

    - **Payload-only frames.** Optimization frames are additive, optional payload fields. `TSStep`
      gains `coordinates_angstrom` (eta's own P-RFO, every step). geomeTRIC runs gain
      `OptimizationFrame`s captured at eta's own `Bridge.calc_new` hook after each evaluation, in
      success **and** failure rows (a timed-out or failed pre-relax keeps its path). Accepted steps are
      labelled only from geomeTRIC's output file (`xyzout`); otherwise the list is labelled as engine
      evaluations including trial points.
    - **Keys unchanged.** Stage keys are unchanged, and frames never alter a result.
    - **Forward-only stores, as measured.** A v0.6.0 reader refuses v0.7.0 transition-state search
      (`ts_opt`) rows. Nothing is claimed for other v0.7.0 rows read by v0.6.0, so a v0.7.0 store is
      not supported under v0.6.0. A v0.6.0 row read by v0.7.0 shows "no trajectory stored".
    - **Temp cwd.** Each geomeTRIC call runs with a per-run temporary directory as cwd, restored in
      `finally` under a lock.

    ## Consequences

    - No recomputation and no cache invalidation. The cost is store size, which is measured and
      decimated in the run-data, never in the store.
    - Using a v0.7.0 store under v0.6.0 is unsupported, and its TS-search rows fail loudly. The v0.7.0
      Phase 3 bundle gates that every trajectory has frames, so a reused old store cannot pass it.
    - The repo and any caller's cwd stay clean of geomeTRIC files.
    - Supersedes ADR-0053, whose reader claim was wider than its evidence.
    ```

  - Check that the README and CHANGELOG claims agree with the new wording (R19). The CHANGELOG
    `[0.7.0]` text is history and is not edited. Name the new node id in the proof and in slice 09's
    CHANGELOG `[0.7.1]` input.
- **Ledger:** each node with a removal; scaffold 1998 (1978 at compile; slice 01's audit added 20),
  so compress first if needed.
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
7. R45: the PROPOSED node exists with the exact body, supersedes ADR-0053, and
   `python3 .agents/scripts/hyper_lore.py validate` exits 0. ADR-0053's files are unchanged.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] `engine_reachable.py`; coverage, ruff and grep evidence.
- [x] Removals and the table.
- [x] `test_doc_refs.py` and the stale-reference fixes.
- [x] R41 docstrings; R19 list.
- [x] R45: propose the ADR-0053 successor, index, validate.
- [x] Required checks (and Tier X if triggered); commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** remove a public symbol, or anything without its evidence row.
- **DO NOT** add vulture or any other dependency, and **DO NOT** add ruff rules to the config.
- **DO NOT** change behaviour in optimize. R41 is docstrings only.
- **DO NOT** edit `docs/prd/**` or CHANGELOG entries older than 0.7.1.
- **DO NOT** approve, reject or edit lore by hand (R45 is a `propose` only), and do not touch
  ADR-0053's files.

## Proof contract

- [ ] The `engine_reachable.py` output and the R17 table (requirements 1-2).
- [ ] `uv run pytest tests/unit/test_doc_refs.py -q` passes, with its negative cases shown
  (requirement 3).
- [ ] The diff of the optimize files is docstring-only (requirement 4).
- [ ] The required checks exit 0 (requirements 5-6).
- [ ] The new lore node's id, `hyper_lore.py show <id>` (status PROPOSED, `supersedes: [ADR-0053]`),
  and `validate` exit 0 (requirement 7).

## Source material

- Mission R17, R18, R19, R31, R41 and R45; the v0.7.0 slice 06 audit notes; ADR-0053
  (`lore/canon/ADR-0053.md`); `missions/release-0.7.0/NOTES.md`, field note of 11-27 (read only).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.7.
