---
id: OPR.0.7.1
mission: release-0.7.1
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope mission create)"
created: "2026-11-27"
intent: "eta v0.7.1 quality release: deterministic integration tests at the real module seams (store, engines, optimize, conformers, mapping, orchestrator/selectivity, review), each proven able to fail, plus a review pass that fixes the verified known issues, removes evidenced dead code and keeps docs record-derived; no new features, no GPU/UMA."
depends_on: []
hacf_schema: 1
hacf_type: SuperPRD
hacf_status: compiled
node_id: null
lore_refs: [ADR-0003, ADR-0010, ADR-0013, ADR-0014, ADR-0015, ADR-0019, ADR-0027, ADR-0045, ADR-0047, ADR-0049, ADR-0050, ADR-0052, ADR-0053]
hacf_source: {draft: spec/active/Draft_PRD.md}
---

# SuperPRD: eta v0.7.1 — Integration Tests at the Module Seams & Quality Review Pass

## Intent

eta v0.7.1 is a quality point release with no new features and no GPU, UMA, MACE or PySCF runs.

- **Integration tests at the real module seams:** store, engines, optimize, conformers, mapping and
  enumerator, the orchestrator (species, TS, ensemble, fallback, selectivity) and review. Real modules
  meet at each seam with no mocks across it.
  - **Tier O** is offline (RDKit UFF) and runs in the default suite.
  - **Tier X** is CPU GFN2 xtb, marked, and run by each audit.
  - Each test is proven able to fail by a named seam break applied in a throwaway worktree.
- **A review pass:**
  - fixes the verified known issues;
  - removes dead code only on scripted evidence;
  - adds a stale-reference scan;
  - ties README and CHANGELOG claims to records.
- **A verdict slice** sets version 0.7.1 and writes `docs/prd/v0.7.1/QUALITY_RESULT.json` from the
  proofs.

**Base and sources:**
- **Base:** v0.7.0 release, `main` = tag `v0.7.0` = `bf7b949`.
  - The lead verified this with ls-remote at 19:19Z on 11-27.
  - Resolve re-verified every file:line cited here at that sha on 2026-11-27.
- **Draft rev 1:** sha256 `b42bb342e27f14b0c9818ad898c34314bee498eba1190e97c1947863fe2a1949`.
- **Red Team report:** sha256 `cde9488027f7b1cb54b0a02a831683017c680778701db720e17cc09024370495`, with
  20 findings, all mediated in §5.
- **Resolve evidence** is in `~/.hacf/eta-rxncat-hacf/evidence/v071-resolve/`: `PHASE1.md`, the M1
  measurements `m1a*`, `m1b*` and `m1c*`, `hostcheck.sh` and `run.sh`.

**Placement:** the lead's placement, a v0.7.1 point release. It has no entry in
`PRDs/Eta-RxnCat_Living_Master_Plan.md` and no starter zip, so there is no `docs/prd/v0.7.1/` starter
and no DISCREPANCIES step. The `docs/prd/v0.7.1/QUALITY_RESULT.json` record is the only file written
under `docs/prd/v0.7.1/`.

### TJ decisions (verbatim; binding)

| Id | Row | Text (verbatim) | Effect |
|---|---|---|---|
| Go | `qitem-20261126032019-1cf1b5efa1c119b8` | "QUALITY PASS: tests/integration has 0 test functions at every tag (the advisor's progress report). Propose and run a small, separately audited quality track: integration tests between the module seams (store, engines, mapping, orchestrator, conformers), plus a review pass for dead code, docs and known-issue follow-ups. - Your call on placement: v0.7.0 slices that don't touch v0.7.0's files, or a v0.7.1 point release right after. - Avoid branch conflicts with v0.7.0. - No GPU or UMA in the quality track while v0.7.0's E2E runs. CPU and GFN2 are fine." and "v0.7.0 stays first priority." | This mission. Branch `feature/eta-rxncat-v0.7.1` is cut from `bf7b949`. CPU and GFN2 only. |
| Q1 = B | answer `qitem-20261126035551-a6b73d9791adcc5a` | "map the bare 'BSD License' classifier to an allowed id LicenseRef-BSD-classifier, so the report says 'BSD (variant not stated)'. The same packages pass." | R12/R28, slice 06. |
| Q-RT1 = A | relay `qitem-20261126041105-cfb78689c81d9fd9` | Option A: "apply the same mapping to the `names` entries "BSD" and "BSD License", so every bare BSD reads "variant not stated"." | R28, slice 06. |
| Licence | standing | "I would prefer to keep ASE out as it would be a major core dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later. But the core remains." | No new dependency. The integration tests import only eta and its existing dependencies. |
| Usage | `qitem a839426b` | "Run all, accept the stop" | Every seat leaves recoverable state at task boundaries. |
| Phase 3 / Push / Clean room | standing | culture | Only TJ promotes. This release writes **no** candidate output (R7). The lead pushes on a verdict pass under the standing go. Never open Eta_Scripts/nMap. Read no TS-optimizer or conformer-search source. geomeTRIC is a black box. `PRDs/` is read-only. |
| Q-71a = A | relay `qitem-20261127193135-56e30a8bf6ae383a` (answering `qitem-20261127193108-2f45ca23757fa8fa`) | "A: add it now (Recommended)" | R37, slice 03: a read-only per-sample stage-key field on `TSEnsembleRun`, plus the defd982 unit test. |
| Q-71b = A | same relay | "A: save as \"Infinity\" (Recommended)" | R38, slice 07: an infinite ratio is written as the JSON string `"Infinity"` and read back as inf; finite records stay byte-identical. |

**OPEN TJ questions: none.**

**Lore:** 51 CANON nodes (TJ, `cd2a91e`). ADR-0037 is superseded by ADR-0047, and ADR-0012 is retired
in favour of ADR-0015. This mission keeps every CANON decision. Its PROPOSED decisions (§5) refine
ADR-0015 (R29), ADR-0019 (R24, R25) and ADR-0013 (R28) without contradicting them, and none of them
supersedes a node.

## 1. Introduction & Goals

**Problem.**
- At every tag, `tests/integration/` holds only `.gitkeep`. Every seam between modules is tested from
  one side, with a fake on the other.
- Six seams have **no offline test with real modules on both sides** at `bf7b949`:
  1. **G-1** `run_transition_state` (`orchestrator/ts.py:393`) with a real engine.
  2. **G-2** `run_ts_ensemble_detailed` (`orchestrator/ts_ensemble.py:345`) with a real engine and
     optimizer.
  3. **G-3** `run_selectivity` (`orchestrator/selectivity.py:337`) with the real
     `run_ts_ensemble_detailed` and `run_species`.
  4. **G-4** graph file → `load_reaction_graph` (`core/io.py:69`) → the selectivity chain.
  5. **G-5** `enumerate_candidates` (`mapping/enumerator.py:126`) with the real `graft`.
  6. **G-6** `reaction_free_energy` / `activation_free_energy` fed from real runner output.
- v0.7.0 added three more seams with no integration test, each measured in minutes in the E2E:
  - `enumerated_pathway_inputs` and `run_ts_with_fallback` (`orchestrator/ts_fallback.py:203,262`),
    including the seed checks `find_clash` and `bond_changes` (`ts_ensemble.py:140,179`);
  - `export_run_data` (`review/export.py:699`);
  - `read_run_data` (`review/run_data.py:739`) and `write_review_bundle` (`review/bundle.py:405`).
- The E2E tests are `e2e`+`slow` runs and write candidate outputs. No cheap check tells a builder that
  a seam broke.
- The lead carries verified known issues and the v0.7.0 audit carry-forwards (§5, "Carry-forwards").

**Solution.** The two-tier integration suite, the review pass and the verdict described in the Intent.

**Audience:**
- the builder and audit seats, who get fast and honest seam regressions;
- the v0.8.0 scheduler work, which builds on these seams and on R13, R14 and the sample keys;
- TJ, who gets a release whose every claim is backed by a command and an outcome.

### Goals (each gated in §8)

- **G1 Harness.** `tests/integration/` gets a registered, default-selected `integration` marker,
  shared real-module helpers, and a policy test that forbids mocks across seams and silent skips (R2,
  R3, R24, R25, R26).
- **G2 Graph.** A new node `eta_rxncat_integration` owns `tests/integration/**`. Each
  `tests/fixtures/vX/**` gets the owner of the matching `tests/candidate_outputs/vX/**` (R27). The
  graph stays acyclic, and the core description does not change.
- **G3 Tier O seams.** T-O1…T-O6 (R8, R36) run in the default suite, with ≤ 60 s added (M2).
- **G4 Sample keys.** `TSEnsembleRun` exposes each sample's stage keys. The v0.7.0 E2E drops its
  private imports, and its re-derived record is byte-equal (R37, TJ Q-71a = A).
- **G5 Tier X TS seams.** T-X1…T-X3 (R9): P-RFO, the ensemble and the fallback runner on GFN2.
- **G6 Selectivity chain + review.** T-X4 and T-X5 (R9, R35): enumerated graph file → load →
  `run_selectivity` on GFN2 → score, then RunData from that store → schema → lenient reader → bundle
  bytes.
- **G7 Each test can fail.** Each integration test has at least one named seam break that makes it
  fail. The proof shows the patched module was the one imported (R4, R22).
- **G8 Known issues closed.** R10, R11, R13, R14, R28, R38 (ratio inf), R39 (wheel offline) and R40
  (host-data scan). Each has a test that fails on the base and passes after.
- **G9 Dead code and docs.** Scripted removals (R17, R31), a stale-reference scan (R18), the docstring
  caveats (R41), and record-derived claims (R19).
- **G10 Verdict.** Version 0.7.1, the point-release identity rule (R23), CHANGELOG `[0.7.1]`, and
  `QUALITY_RESULT.json` generated from the named evidence (R20, R30).

## 2. Confidence Mandate

**Score: 9/10.**
- M1 was measured on this host on CPU GFN2 (§5, R33).
- Every cited symbol was re-read at `bf7b949`.
- RT-01's input question is settled against the v0.7.0 files that actually shipped (R21).

The residual risks are measured first in their slices, each as a stop-and-report:
- M2, Tier O's added wall time (slice 02);
- the measured walls of T-X3 and T-X4 on the 24-atom ethyl candidate, which are estimated from M1b
  and M1c (slices 04 and 05);
- the sample-key parity rerun (slice 03).

## 3. Scope

### In scope

1. The harness, the marker split (R24), the guarded directory (R25), the mock policy (R26), the node
   and fixture ownership (R27) — slice 01.
2. Tier O, T-O1…T-O6 — slice 02.
3. The public per-sample stage keys and the defd982 unit test (TJ Q-71a = A) — slice 03.
4. Tier X TS seams, T-X1…T-X3 — slice 04.
5. The Tier X selectivity chain and the review export round trip, T-X4 and T-X5 — slice 05.
6. Tooling and test-text known issues: R10, R11, R28, R39 and R40 — slice 06.
7. Runtime known issues: R13/R29, R14 and R38 — slice 07.
8. The dead-code pass, the stale-reference scan, docstrings and claims: R17/R31, R18, R19 and R41 —
   slice 08.
9. The verdict: 0.7.1, the R23 identity rule, CHANGELOG and `QUALITY_RESULT.json` — slice 09.

The test-policy amendments of RT-03 (R23) and RT-04 (R24) are named here, so they are in scope, not
creep.

### Out of scope

- New features, and any behaviour change beyond R13, R14, R29, R37 and R38.
- GPU, UMA, MACE or PySCF runs. R14 is tested offline with a stub package.
- Any new candidate output, any new fixture, and Phase 3 (R7). The slice-03 parity rerun runs in a
  throwaway worktree, and its output is compared and then discarded, never committed.
- `PotentialResult` strict floats and deep freeze. R15 keeps them as a documented limit for the v1.0
  API freeze.
- An existing store's open waiting behind an active writer, which belongs to v0.8.0 crash recovery.
- Any change to `ReactionGraph` schema 1, a stage key, a cache payload, `score_selectivity`, a RunData
  v1 field, or `EnumerationPlan`.
- A new Python or JS dependency, including mutation-testing tools.
- Ownership of `lore/`, `missions/`, `.agents/`, `.claude/`, `PRDs/` and `spec/`. These are toolchain
  and process files, not product.
- `missions/release-0.7.0/` and older missions are read-only.
- **Deferred carry-forwards (each with its reason, §5 "Carry-forwards"):**
  - multi-site forming bonds (5);
  - `+` in entry ids (6);
  - `run_selectivity`'s priority-1 rule against the plan's priority-2 TS nodes (4d, R35);
  - geomeTRIC temp-dir and partial-mark edge cases (lead notes, slice 06 of v0.7.0);
  - the red frequency-failure box (TJ's own call; the lead's version-end batch).

## 4. User Stories (Atomic)

| ID | User Story | Acceptance Criteria | Priority |
|---|---|---|---|
| US-001 | As a builder, I want a shared integration harness so seam tests are cheap and cannot quietly fake a seam or skip. | `integration` is registered and default-selected (R24). `tests/integration` is in `GUARDED_DIRS` (R25). `test_integration_policy.py` fails on every R26 form and on any skip/xfail form, with one negative case each. The default suite is green. | P0 |
| US-002 | As the lead, I want the new tests and every promoted fixture owned in the graph. | `eta_rxncat_integration` owns `tests/integration/**`. Its `depends_on` = the import scan plus the data owners (R5, RT-14). The R27 fixture globs are added. The graph is acyclic and the glob counts are checked before and after. Core and engines descriptions are unchanged. | P0 |
| US-003 | As a builder, I want the offline seams checked in every default run. | T-O1…T-O6 are `passed` by id in the default junit, with 0 skipped and ≤ 60 s added (M2). Each seam break fails (R4, R22). | P0 |
| US-004 | As the review and E2E code, I want each TS sample's stage keys from the runner, not from private helpers. | `TSEnsembleRun.samples` (R37). `tests/e2e/v070.py` imports no `_`-prefixed eta name. A unit test pins the clashed-sample rule (defd982). The parity rerun record is byte-equal to `tests/fixtures/v0.7.0/v070_enum_ethyl_endo_xtb.runrecord.json`. | P0 |
| US-005 | As a builder, I want the TS seams checked against a real engine. | T-X1…T-X3 pass under the Tier X command (R2) with `ETA_RXNCAT_ACCEPTANCE=1`, 0 skipped, inside R33's budget. Each seam break fails. | P0 |
| US-006 | As a builder, I want the selectivity chain and the review export checked from a real graph file. | T-X4 and T-X5 (R9, R35): the RunData from a real store validates against the schema, round-trips through `read_run_data`, and gives equal bundle bytes across two writes. | P0 |
| US-007 | As TJ, I want each known issue closed or explicitly kept. | R10, R11, R13/R29, R14, R28, R38, R39 and R40 each have a test that fails at `bf7b949` and passes after. R15 is kept, R12's two edge cases are dropped, and the deferred carry-forwards are listed with reasons in the CHANGELOG. | P0 |
| US-008 | As a maintainer, I want dead code removed only on evidence and stale doc references caught. | The R17/R31 table has one evidence row per candidate. `tests/unit/test_doc_refs.py` (R18) is green and fails on a planted stale name. The R41 docstrings are present. Each claim is cited (R19). | P1 |
| US-009 | As the lead, I want a verdict that gates on real outcomes. | 0.7.1 in the R20 places, plus the README badge. `test_identity` is green under R23. `QUALITY_RESULT.json` is generated from the R30 evidence. The script exits non-zero on any missing source. | P0 |

## 5. Technical Specifications

### Resolved trade-off log

R1–R20 are the draft's rows as amended by the Red Team mediation. R21–R41 are new: R21–R34 come from
Phase 1, and R35–R41 from the compile re-verify and the carry-forwards. Each row's slice is named.

| # | Item | Decision | Detail |
|---|---|---|---|
| R1 | Placement and base | lead | A v0.7.1 point release. Branch `feature/eta-rxncat-v0.7.1` is cut from `bf7b949` after the v0.7.0 push. v0.8.0 is compiled after v0.7.1 and relies on R13, R14 and R37. |
| R2 | Marker and suite placement | architect, amended by R24/R25 | Every integration test carries `pytest.mark.integration`, which is registered in `pyproject.toml` `markers` and **not** deselected, so Tier O runs in every default run. Tier X tests also carry `xtb` and so stay out of the default suite. **Tier X command:** `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb ETA_RXNCAT_ACCEPTANCE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m pytest -m "integration and xtb" tests/integration`. Under `=1` a skip is a failure (ADR-0019). No `gpu`, `mlip_mace`, `mlip_uma` or `slow` marker appears under `tests/integration/`. |
| R3 | No mocks across the seam | architect, amended by R26 | Engines come only from eta's registry through the public recipe path (`build_engine`, `orchestrator/species.py:269`). **Helpers** live in `tests/integration/conftest.py`: the real recipes (UFF, and GFN2 xtb rebuilt literally from `tests/e2e/e2e_env.py:28-34`: `StageConfig(kind="geometry_opt", engine="xtb_subprocess", method="gfn2", options={"alpb_state": "gsolv"})`), a per-test `ArtifactStore(tmp_path / "store.db")`, the R21 plan loader, a cwd-in-`tmp_path` fixture and a row-count helper. No helper imports from `tests/unit/` or `tests/e2e/`. |
| R4 | Proving each test can fail | architect, amended by R22 | Each integration test's docstring names at least one **seam break**: a minimal source edit that breaks the seam it guards. The slice SPEC lists them as `T-id ⇐ break`. **Audit procedure:** `git worktree add <literal path>` at the slice commit, apply each break as a patch file, run only that test (R22), and record the command and the failing outcome. Then remove the worktree by its literal path. A break that leaves its test green is a FAIL. The audit commits `missions/release-0.7.1/slices/<NN-slug>/seam_breaks.json` with its PROGRESS row (R30). |
| R5 | Integration node | architect, amended (RT-14) | `ensure-node --id eta_rxncat_integration --dimension Module --files 'tests/integration/**'`. **`depends_on`** = the import scan of `tests/integration/**` **plus** the data owners: `eta_rxncat_species_runner` (`tests/e2e/**`) and `eta_rxncat_core` (`tests/data/**`). The description is ≤ 1200 chars. `tests/integration/**` is unowned today (`tests/integration/.gitkeep` is its only file, verified with `git ls-files`). `--files` **replaces** the list, so pass the full list and check the glob count before and after. |
| R6 | Fixture ownership | superseded by R27 | — |
| R7 | Determinism and no novel output | architect, amended (RT-16) | Integration tests assert **invariants**: equal keys, a rerun that is all cache hits (0 new rows, and 0 `engine_calls` from `StageMetrics`/`RunMetrics.engine_calls`, the only engine-call oracle), payload round trips, Σw within `1e-12` (`abs(sum - 1) <= 1e-12`, the committed `weights_sum_tolerance` of `t4_flexible_alkyl.yaml`), an imaginary-mode count of 1, face and connectivity gates, schema validity and equal bytes. Numbers are compared only between a fresh result and its cache replay, with exact equality, never across two engine runs and never against a stored reference. No test writes to `tests/candidate_outputs/` or `tests/fixtures/`. Lists are compared order-free unless order is the contract. |
| R8 | Tier O tests | architect, amended (RT-19, R21) | **T-O1** store ↔ species runner ↔ RDKit UFF ↔ `GeometricOptimizer` ↔ thermo, on a butane `SpeciesSpec` built in the harness with `n_embed=3` (M2 confirms the cost). Rows are created; a rerun on the same store makes 0 rows and 0 engine calls with equal results; a fresh store gives byte-equal keys; `ThermoResult` survives a payload round trip. **T-O2** G-6: `reaction_free_energy` from two real `run_species` outputs equals its own replay from a reopened store. **T-O3** conformers ↔ engine ↔ store: a conformer stage through `run_species`. Members are stored, the weights sum to 1 within 1e-12, and the rerun is all hits. **T-O4** G-5: `enumerate_candidates` with the **real** `graft` on the R21 plan. It asserts 2 `ok` candidates, each graft RMSD ≤ the plan's `max_alignment_rmsd_angstrom` (0.15), 0 contacts, declared charge/multiplicity 0/1, and byte-equal `model_dump_json` across two runs. **T-O5** G-4 in part: an enumerated candidate graph through `dump_reaction_graph_json` → a `tmp_path` file → `load_reaction_graph` equals the original. The input is produced in the test, because no committed standalone neutral `ReactionGraph` file exists. |
| R9 | Tier X tests | architect, amended (RT-07, R21, R35, R37) | All CPU GFN2, under the heavy-run rule. **T-X1** G-1: `run_transition_state` with `PRFOOptimizer` + xtb on `TS1a_n` (M1a: converged, 1 imaginary mode, identity core true, 7.7 s). It gates convergence, mode count 1, the identity core (ADR-0047), the record round trip, and a rerun that is all hits with an equal payload. **T-X2** G-2: `run_ts_ensemble_detailed` with the real sampler, `relax_constrained_core`, `GeometricOptimizer`, P-RFO and the store, with `TSEnsembleOptions(n_embed=1, n_perturb=1, max_research=1)` (the `PositiveInt` minimum, M1b 41 s). It gates that the seed is a member, Σw within 1e-12, each member on the seed's face, a rerun that is all hits, and (after slice 03) each `samples` key present in the store. **T-X3** fallback: `run_ts_with_fallback` on T-O4's ethyl candidate, endo node `TS1a_n`, with rank 1 eligible and 1/1/1 options. It gates that the `FallbackRecord` names rank 1 with no fall-through, the seed checks ran (no `seed_clash` on the seed), and a rerun that is all hits. **T-X4** and **T-X5** are as R35. |
| R10 | `tests/e2e/t3.py:291` xtb `gated_on` | fix (slice 06) | Verified at `bf7b949`: `block["gated_on"] = "convergence, mode count" if recipe_name == "xtb" else "all (UMA, Q-TJ3)"`. t3 must emit exactly the per-case text of `docs/prd/v0.5.0/ACCEPTANCE_RESULT.json` (corrected by 14d2da1): `"convergence, mode count, identity core (forming overlap, in phase, KE)"` for n4, ts1a_n, ts1b_n and ts3a, and `"none (report-only, R32)"` for ts4a. The test compares, for each v0.5.0 case, the text t3 would write with the record's. Text only. Owner: `eta_rxncat_species_runner`. |
| R11 | Test-policy AST and teardown skip | fix (slice 06) | Verified: `module_level_skips` is at `tests/unit/test_test_policy.py:213`, and `pytest_runtest_makereport` at `tests/conftest.py:61`, with `when in ("setup", "call")` at :80. (a) Collect `import pytest as X` aliases and visit `decorator_list`, `args.defaults`/`kw_defaults` and class `bases`/`keywords`, while still skipping function bodies. Add parametrised cases for each. (b) Add `"teardown"`. A pytester test shows that a teardown skip fails under `=1` and stays a skip without it. Owner: scaffold (1978/2000; no description growth). |
| R12 | Licence gate | fix (Q1 = B), amended by R28 + drop | **Dropped, already fixed:** the unnamed-distribution and ambiguous-name cases (`tools/licence_gate.py:333-335`, `:342-345`, tested). The fix itself is R28. |
| R13 | Store `open_timeout_s=inf` | fix (slice 07), amended by R29 | Verified at `bf7b949`: `store/artifact_store.py:101` (`not open_timeout_s > 0`), :109-110 (`connect(timeout=open_timeout_s)`) and :143 (`int(remaining * 1000)`, which is an `OverflowError` at inf). **`inf` means "no open deadline"** (ADR-0015's step 1 "validate the timeout" admits it). |
| R14 | MACE env leak | fix (slice 07) | Verified: `engines/mace.py:123` `importlib.import_module("mace")`, and :133 `weights_only=False`, with no env handling in the file. A context manager around that import saves the prior state of `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD` (absent or a value) and restores it in `finally`. **Test** (offline, default suite): a stub package `mace` on `sys.path` via `tmp_path` sets the variable on import. The test evicts and restores `sys.modules["mace"]` and `sys.path` (RT-17). The docstring and CHANGELOG state the limit: the guard restores nothing if `mace` was imported earlier in the process. Owner: engines (**1991/2000**; no description change). |
| R15 | `PotentialResult` floats and freeze | keep | Documented limit (`core/results.py`, DV-23). Goes to the v1.0 API-freeze review. CHANGELOG "Known issues" names it. |
| R16 | Unowned files, record-derived docs | see R27, R19 | — |
| R17 | Dead-code pass | architect, amended by R31 (slice 08) | Evidence comes from three sources: (1) `coverage run -m pytest` on the default suite (which includes Tier O); (2) `ruff check --select F401,F841 src tools tests` (rules run ad hoc, not added to config), with ERA001 hits treated as review prompts only; (3) `git grep -n '<name>'` across `src/ tools/ tests/ docs/ README.md`. **Remove only** a symbol with 0 coverage, 0 references outside its definition, not in any `__all__`, and not in R31's exclusion set. Public symbols are listed and kept (the v1.0 freeze is TJ's). The proof table has one row per candidate: symbol, file:line, coverage, references, verdict and reason. |
| R18 | Stale-reference scan | architect, amended (RT-18) (slice 08) | New `tests/unit/test_doc_refs.py` (owner scaffold). Every backticked dotted name beginning `eta_rxncat.` in `README.md`, `CHANGELOG.md` (the `[0.7.1]` entry onward), `docs/*.md` (not `docs/prd/**`) and `src/**` docstrings must resolve. Modules importable with the base deps are imported lazily. Engine-extra modules are found with `importlib.util.find_spec` and **never imported**, and their attributes are resolved by AST: top-level `def`, `class`, assignment and `__all__` names of the module source. Positive and negative parametrised cases. Each stale reference found at the base is fixed and listed. |
| R19 | Record-derived claims | architect (slices 08, 09) | Each new README or CHANGELOG claim cites its test id plus a `QUALITY_RESULT.json` key. Each existing README claim the reviewer finds unsupported is cited or removed, and listed. No claim states a number that no record holds. |
| R20 | Verdict record | architect, amended by R23/R30 (slice 09) | `docs/prd/v0.7.1/QUALITY_RESULT.json` is written by `tools/quality_record_v071.py` from the R30 sources, never by hand. **Keys:** `version`, `base_sha` (`bf7b949…` full), `verdict_run_sha`, and `suites.{default,integration_x}.{passed,failed,skipped,deselected,errors,wall_s}` parsed from junit. `integration_tests[]` holds `{id, tier, seam, seam_breaks: [{break, failed_test}]}`. `known_issues[]` holds `{id, verdict: fixed\|kept\|dropped\|deferred, test}`. `dead_code.{removed,kept}`. **Gates:** default suite 0 failed and 0 errors, and each T-O id `passed` by id with 0 skipped among `integration` ids (R25); Tier X 0 failed, 0 errors and 0 skipped under `=1`; every seam break failed; every R10/R11/R13/R14/R28/R38/R39/R40 test present and passing. **Version 0.7.1** goes in `pyproject.toml`, `src/eta_rxncat/__init__.py`, the README Features title, the README badge `release-v0.7.1` and `uv.lock` (`uv lock`), with CHANGELOG `## [0.7.1]`. |
| R21 | Enumeration input (RT-01) | resolve (re-checked at `bf7b949`) | The plan is v0.7.0's `tests/e2e/data/e2e5/v070_enumeration.yaml`, read in place. Its loader `tests/e2e/v070.py:109` `load_enumeration` imports sibling e2e modules at top level (`from e2e_env import REPO`, `fixtures`, `t3` and `t4`, :31-34), so it is **not** importable as a `tests.*` module. **Ruling:** `tests/integration/conftest.py` carries `load_v070_plan()`, a copy of the loader's rules: schema 1; exact top-level keys = the plan keys ∪ {`max_alignment_rmsd_angstrom`, `orientation_centers`} ∪ {`schema`, `fixture`}; every `xyz` path resolved against the YAML's directory; each `xyz` block read with its declared `charge` and `spin_multiplicity`; then `EnumerationPlan.model_validate`. No new format. **Parity test** `test_plan_loader_parity` (Tier O): a subprocess `sys.executable -c` with `sys.path` set to `tests/e2e` runs `v070.load_enumeration` and prints the plan's `model_dump_json()`, which must equal the conftest plan's byte for byte. It is a real call, not a double, so R26's import ban holds. |
| R22 | Seam-break interpreter (RT-02) | resolve | Every seam-break command is `PYTHONPATH=<literal worktree>/src /home/tjmustard/PROJECTS/eta-rxncat/.venv/bin/python -m pytest <test id>`. Before each break the proof records `python -c "import eta_rxncat; print(eta_rxncat.__file__)"` under the same environment, and the path must be under the worktree. `git apply --check` runs first, and a patch that does not apply is a proof error. **Never run `uv` in a worktree.** |
| R23 | Point-release identity (RT-03) | resolve (slice 09) | `tests/unit/test_identity.py`: `PLAN_VERSIONS` (:257) and `check_version_identity` (:291) get a point-release rule. A version `X.Y.Z` with `Z > 0` takes `X.Y.0`'s roadmap position: Built lists up to `X.Y.0`, and Planned lists the rest. The README badge is `release-v0.7.1` (:300-302). Add a positive case (0.7.1) and a negative case (0.7.1 with 0.8.0 under Built). Scaffold test change; no description words. |
| R24 | Marker split (RT-04) | resolve (slice 01) | `tests/unit/test_test_policy.py:14` `MARKERS` → `DESELECTED_MARKERS` (the seven) and `DEFAULT_SELECTED_MARKERS = ("integration",)`. `test_markers_and_default_deselection` (:91) asserts that addopts deselects exactly the first set and never names the second, and that declared markers equal their union. |
| R25 | No silent skip (RT-05) | resolve (slices 01, 09) | Add `tests/integration` to `GUARDED_DIRS` (:210). The integration policy test forbids `pytest.skip`, `importorskip`, `skipif` and `xfail` (as a call or a marker) anywhere in `tests/integration/**`. Tier X's missing-xtb path stays the existing `xtb` marker plus the acceptance conversion. The verdict counts T-O ids `passed` by id. |
| R26 | Mock policy, full forms (RT-06) | resolve (slice 01) | The AST scan in `tests/integration/test_integration_policy.py` fails on: `unittest.mock` (import or from); any attribute of a `monkeypatch` parameter, tracked by name and by alias, outside {`setenv`, `delenv`, `chdir`}; assignment, augmented assignment or `del` to an `Attribute`/`Subscript` rooted at an imported `eta_rxncat` module name or `sys.modules`; the builtins `setattr`/`delattr`; and any import from `tests.*` other than `tests.integration`. Also forbidden: the markers `gpu`, `mlip_mace`, `mlip_uma` and `slow`. One negative case per form. |
| R27 | Fixture ownership rule (RT-08) | resolve (slice 01) | At `bf7b949` each `tests/fixtures/vX/**` joins the node owning `tests/candidate_outputs/vX/**`. Counted with `git ls-files tests/fixtures` at `bf7b949`: v0.3.0 10, v0.5.0 11, v0.6.0 10 and v0.7.0 30 → `eta_rxncat_species_runner`; v0.4.0 3 → `eta_rxncat_mapping`. `tests/fixtures/.gitkeep` and `tests/candidate_outputs/.gitkeep` → `eta_rxncat_scaffold`. That is 65 files in total. The proof lists the counts before and after. |
| R28 | BSD label (RT-09; Q1 B; Q-RT1 A) | resolve (slice 06) | `pyproject.toml` `[tool.eta-rxncat.licence-gate.classifiers]` `"BSD License"` (:113) and `[…names]` `"BSD"` and `"BSD License"` (:126-127) → `LicenseRef-BSD-classifier`, which is added to `allowed`. `"3-Clause BSD License"` (:128) keeps BSD-3-Clause because it names the variant. A new table `[tool.eta-rxncat.licence-gate.labels]` holds `"LicenseRef-BSD-classifier" = "BSD (variant not stated)"`. The row's licence column (`tools/licence_gate.py:375`) prints `<raw> [BSD (variant not stated)]` when the resolved id has a label; the exact text is tested. The tests cover the classifier path, both names paths, and a `License-Expression: BSD-3-Clause` package that stays BSD-3-Clause unlabelled. **Proof:** each profile's PASS/FAIL set is equal before and after (antlr4-python3-runtime passes in `mlip-uma`). `docs/licence-inventory.md` is updated if it names the mapping. |
| R29 | `open_timeout_s` contract (RT-10) | resolve (slice 07) | `inf` = no deadline. `bool` and non-real values raise **`TypeError`**, and `True` is newly refused. NaN and ≤ 0 raise `ValueError`. Clamp to `2**31 - 1` ms at **both** `connect(timeout=…)` and each `PRAGMA busy_timeout`. **Held-lock test:** the open runs in a daemon worker thread joined with a 30 s bound, and the releaser thread is joined with a timeout. A live thread fails the test, so the default suite cannot hang. Docstring updated. Owner: store (1804). |
| R30 | Verdict sources (RT-11) | resolve (slice 09) | The sources are each Tier O/X slice's committed `missions/release-0.7.1/slices/<NN-slug>/seam_breaks.json` (slices 02, 04 and 05) and the verdict run's junit XML at `~/.hacf/eta-rxncat-hacf/evidence/v071-verdict/{default,integration_x}.xml`. The record script exits non-zero if any expected test id, slice file or list is missing or empty. `verdict_run_sha` = HEAD at the verdict run. |
| R31 | Dead-code exclusion by script (RT-13) | resolve (slice 08) | A committed helper, `tools/engine_reachable.py`, computes the exclusion set: every module reachable by import from `ENGINE_CLASSES` (`orchestrator/species.py:84`) and the optimizer classes (`eta_rxncat.optimize`), plus every module imported by a test carrying `xtb`, `gpu`, `mlip_*`, `slow`, `acceptance` or `e2e`. Its output goes in the proof. **Cap list:** enumerator 1997, optimize 1997, species_runner 1991, engines 1991, review 1983, scaffold 1978 and core 1973. A removal in a node at or above 1990 is listed and kept unless it needs no description word. |
| R32 | Tier X host and threads (RT-12) | resolve | The host check is v0.7.0's by content (`~/.hacf/eta-rxncat-hacf/evidence/v071-resolve/hostcheck.sh`): MemAvailable ≥ 12 GiB; GPU ≤ 20 % with no compute app; no un-niced process at ≥ 100 % CPU or ≥ 2 GiB RSS; and no other eta, xtb or pytest process (the metis rig included). Tier O (the default suite) is **exempt**. Tier X pins the **parent** `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 (M1a.t1: 36.4 s against 37.6 s unpinned, and 3.5× less CPU). xtb's own threads stay eta's default of 1 (`engines/xtb_subprocess.py`). The values are recorded in the proof `.env`. |
| R33 | Tier X budget (M1) | resolve | Measured on CPU GFN2 and parent threads pinned or not as stated: T-X1 ≈ 8 s (M1a), T-X2 ≈ 41 s (M1b), T-X3 ≤ 80 s (estimated at 2× M1b, 24-atom candidate) and T-X4 ≤ 90 s (estimated at 1.5× M1c); T-X5 adds ≈ 0 because it shares T-X4's store. Σ ≈ 220 s × 1.5 ≈ **5.5 min**, under the 30 min stop line. Each Tier X module runs under `timeout 600` (the floor). Slices 04 and 05 **measure their module first** and stop-and-report if it is over 2× the estimate. |
| R34 | Slice split (RT-15) | resolve | Tooling and test text (slice 06) are split from runtime source (slice 07), so product-source changes get their own audit. |
| R35 | T-X4 graph priority (carry-forward 4d) | resolve (slice 05) | Verified: `run_selectivity` runs only priority-1 pathways (`selectivity.py:371`) and treats priority ≥ 2 as downstream species (:412). The v0.7.0 plan puts its TS nodes at **priority 2** (`v070_enumeration.yaml:28,40`), by design for the fallback runner. **Ruling:** T-X4 takes T-O4's ethyl candidate graph through the T-O5 file round trip (dump → `tmp_path` file → `load_reaction_graph`). It builds the run graph from the loaded one with `model_copy`, setting **only** the two TS nodes to priority 1 and stating it in the test docstring. There are then no priority ≥ 2 nodes, so `downstream={}`. The pathway inputs come from `enumerated_pathway_inputs` on the unmodified candidate. Then `run_selectivity(kind="de")` runs on GFN2 with 1/1/1. **Gates:** each pathway has at least 1 member, Σw within 1e-12 per set, a score is present, and a rerun is all hits with an equal score. The priority mismatch is **not fixed** in v0.7.1: it is not a defect of either contract, and v0.8.0's graph-to-TS scheduler owns the join. CHANGELOG "Known issues" states it. **T-X5** exports RunData from T-X4's store through `export_run_data` (`review/export.py:699`), with a `RunRecord` built from the T-X4 result, its samples taken from `TSEnsembleRun.samples` (R37). It validates against `src/eta_rxncat/review/schema/run_data.v1.schema.json`, round-trips through `read_run_data`, and `write_review_bundle` gives equal bytes across two writes to fresh directories. T-X4 and T-X5 share one module-scoped store. |
| R36 | T-O6 seed seam (v0.7.0 slice 15) | resolve (slice 02) | Offline, no engine: T-O4's candidate → `enumerated_pathway_inputs` for `TS1a_n` and `TS1a_x` → the seed `TSSpec`. **Gates:** `find_clash(seed)` is None; the seed's forming bonds are the candidate's composed bonds (order-free); the core equals `seed.start.active_atom_indices`; and the run-time fallback construct's rank 1 (the TS1a_x geometry in the endo node) gives the face mismatch before any search. The input is the R21 plan only. |
| R37 | Per-sample stage keys (carry-forward 1; **TJ Q-71a = A**) | resolve (slice 03) | `TSEnsembleRun` (`ts_ensemble.py:101`, a frozen runtime dataclass that is not cached) gets `samples: tuple[SampleKeys, ...] = ()`. `SampleKeys` is a new frozen dataclass exported from `eta_rxncat.orchestrator`, with `{index, source, pre_relax_key, ts_opt_key, frequency_key}`, each key `str \| None`. Index 0 is the seed. The runner fills it from the keys it already builds, so no stage key, payload or RunData field changes. A clashed sample (`seed_clash`) has all three keys None. **The E2E** `tests/e2e/v070.py` `derive_samples` (:376) maps `run.samples` to `RecordSample`s and drops `_digest`, `_PreRelax` and `_sorted_pairs` (:67-68). The `CountingEngine` import (:66) stays only if a non-sample use needs it, and is listed. **Tests:** fake-engine unit tests in `tests/unit/orchestrator/test_ts_ensemble*.py`: the keys of the seed, a searched sample, a pre-relax-failed sample and a clashed sample, and that every non-None key is a row in the store. **defd982 unit test:** a clashed index produces a `RecordSample` with only `source`, even when the store holds rows for that start from an earlier run (carry-forward 2). **Parity:** rerun the v0.7.0 E2E unit ethyl-endo-xtb in a throwaway worktree at the slice commit, under the heavy-run rule and `timeout 5400`. Its runrecord must be byte-equal to `tests/fixtures/v0.7.0/v070_enum_ethyl_endo_xtb.runrecord.json`, as v0.7.0 slice 17's audit compared them. A difference is a stop-and-report. |
| R38 | `ratio = inf` round trip (carry-forward 3; **TJ Q-71b = A**) | resolve (slice 07) | Verified: `RunRecord` (`review/run_data.py:263`), `_Record` config `allow_inf_nan=False` (:84), nesting `SelectivityResult.ratio` (`core/selectivity_models.py:350`, `allow_inf_nan=True`). There is no `ser_json_inf_nan` anywhere in `src/`. **Fix:** the record JSON writes an infinite ratio as the string `"Infinity"`, and reading it back gives `inf`. The mechanism is the smallest one that makes `RunRecord.model_validate_json(record.model_dump_json()) == record` true; the builder measures `ser_json_inf_nan="strings"` on the record config first. No change to `SelectivityResult` (core, 1973). Records with a finite ratio stay byte-identical: the test re-serialises every committed `tests/fixtures/v0.7.0/*.runrecord.json` to its exact bytes. Owner: review (1983; no description words). |
| R39 | Wheel test offline (carry-forward 4a) | resolve (slice 06) | Verified: `tests/unit/review/test_assets.py:59` runs `uv build --wheel` (:66) with no `--offline`, so an offline host fails the assert. **Fix:** build with `--offline`. The builder first measures `UV_OFFLINE=1 uv build --wheel --offline` on this host, and a missing cached build backend is a stop-and-report. When `uv` is absent the test still skips (:61-63), and under `ETA_RXNCAT_ACCEPTANCE=1` that skip fails, which is ADR-0019 as written: a missing tool in an acceptance run must not pass. Owner: review (tests only). |
| R40 | Host-data scan false positive (carry-forward 4b) | resolve (slice 06) | Verified: `tests/unit/review/test_bundle_scans.py:63` matches `getpass.getuser()` and `socket.gethostname()` as plain substrings (:78), so the user `root` matches the vendored 3Dmol text. **Fix:** files byte-pinned by the bundle's vendored-asset sha256 are excluded from the user/host scan, since their pin already proves no host data entered them. Every other file is scanned as before. A test plants the user name in a non-vendored file (it fails) and shows that the pinned 3Dmol file is not scanned. `test_export.py:63-64` is unchanged. Owner: review (tests only). |
| R41 | Docstring caveats (carry-forward 4c; v0.7.0 slice 06 notes) | resolve (slice 08) | Docstring-only edits: `optimize/geometric_impl.py` states that its process-wide `chdir` affects relative paths in a host program's own threads, and that the cwd lock is not reentrant; `optimize/ts_base.py` states the one-`hessian=False`-per-step contract. No code change. The two behaviour edge cases (a deadline inside `TemporaryDirectory` cleanup leaking one temp dir; a deadline inside `_mark_accepted` leaving a step partly marked) are **deferred** to v0.8.0's out-of-process geomeTRIC (TJ Q-B1 A), which replaces this path, and listed in CHANGELOG "Known issues". Owner: optimize (**1997/2000**; no description words). |

### Carry-forwards from v0.7.0's audits (placement)

| # | Item | Placement |
|---|---|---|
| 1 | Public per-sample stage keys on `TSEnsembleRun` | **Slice 03**, R37 (TJ Q-71a = A). |
| 2 | Unit test for defd982 (clashed sample → no rows in the record) | **Slice 03**, R37. `derive_samples` is in `tests/e2e/v070.py:376` (not `src/`); no unit test covers it today (`git grep derive_samples tests/unit` is empty). |
| 3 | `ratio = inf` record round trip | **Slice 07**, R38, beside R13/R29 (TJ Q-71b = A). |
| 4a | Wheel test offline | **Slice 06**, R39. |
| 4b | Username/hostname scan | **Slice 06**, R40. |
| 4c | Docstrings (geomeTRIC cwd, cwd lock, ts_base) | **Slice 08**, R41. |
| 4d | TS priority vs `run_selectivity` | **Slice 05**, R35. The test adapts; the join is deferred to v0.8.0 with a CHANGELOG line. |
| 5 | Multi-site forming bonds | **Deferred.** It is a behaviour change in the enumerator (description 1997/2000), and no v0.7.1 seam has two sites: the shipped plan has one site, `c7`. The run path already refuses the dangerous case (`enumerated_pathway_inputs` raises `multi_site_seed_atom_deleted`, `ts_fallback.py:220`). It stays in CHANGELOG "Known issues" for v0.8.0's enumerator work. |
| 6 | `+` in entry ids can collide joined candidate ids (`enumerator.py:193`) | **Deferred.** The fix is a validation rule on library entry ids, which is an `EnumerationPlan` contract change (core, 1973), and this mission forbids contract changes. No shipped id contains `+` (the entries are `ethyl` and `npropyl`). Added to CHANGELOG "Known issues". |
| 7 | Ledger descriptions near the cap | §6 and R31: any slice whose builder or audit needs a description word in species_runner (1991), engines (1991), enumerator (1997), optimize (1997), review (1983) or scaffold (1978) compresses first and states the before and after counts. Core gets no words. |

### PROPOSED lore (registered at compile; TJ approves with `/hyper-lore-approve`)

One decision per contract-changing row: R21, R22, R24/R25, R26, R28, R29, R30, R31, R32, R35, R37 and
R38. Each states which CANON node it refines. None supersedes one.

### Heavy-run rule (normative for slices 03, 04, 05 and 09 and their audits)

- Before each engine command, run the blocking host check (R32) as a **separate call**, or as a loop
  that exits. Never echo-then-run. Its output stays in the proof.
- **CPU GFN2 only.** Never GPU, UMA, MACE or PySCF. Never beside another eta/xtb/pytest run or another
  rig's announced quiet-host hold.
- One Tier X module per command, under `timeout 600`, or `timeout 5400` for the slice-03 E2E parity
  unit, with `/usr/bin/time -v` and the R32 thread pins.
- Run from a scratch cwd under `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Afterwards
  `git status --porcelain` shows no `HT.v_*`.
- `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` and
  `ETA_RXNCAT_ACCEPTANCE=1` are always set.

### Blast radius (measured with `hyper_ledger.py impact --files` at `bf7b949`)

| Slice | Nodes touched | Files |
|---|---|---|
| 01 | new `eta_rxncat_integration`; scaffold (`pyproject.toml`, `tests/unit/test_test_policy.py`); species_runner, mapping and scaffold (files lists, R27) | `tests/integration/{conftest.py,test_integration_policy.py}`, `pyproject.toml`, `tests/unit/test_test_policy.py` |
| 02 | integration | `tests/integration/test_seams_offline.py` |
| 03 | selectivity (`ts_ensemble.py`, `orchestrator/__init__.py`, its unit tests); species_runner (`tests/e2e/v070.py`) | as R37 |
| 04 | integration | `tests/integration/test_seams_ts_gfn2.py` |
| 05 | integration | `tests/integration/test_seams_selectivity_gfn2.py` |
| 06 | species_runner (`tests/e2e/t3.py` and its test); scaffold (`tests/conftest.py`, `tests/unit/test_test_policy.py`, `tools/licence_gate.py`, `pyproject.toml`, `tests/unit/tools/test_licence_gate.py`, `docs/licence-inventory.md`); review (`tests/unit/review/test_assets.py`, `test_bundle_scans.py`) | as R10, R11, R28, R39, R40 |
| 07 | store (`artifact_store.py` and its tests); engines (`mace.py` and its tests); review (`run_data.py` and its tests) | as R14, R29, R38 |
| 08 | any `src/` node with an evidenced removal; optimize (docstrings); scaffold (`tests/unit/test_doc_refs.py`, `tools/engine_reachable.py`, README, docs) | per the R17 table |
| 09 | scaffold, cli (`pyproject.toml`, `uv.lock`) | the version files, `tests/unit/test_identity.py`, README, CHANGELOG, `tools/quality_record_v071.py`, `docs/prd/v0.7.1/QUALITY_RESULT.json` |

- **Product source touched:** selectivity (slice 03, additive), store, engines and review (slice 07),
  optimize (docstrings, slice 08), and any slice-08 evidenced removal.
- **Untouched:** core, thermo, conformers, mapping and enumerator source.

### Execution checklist (build order; one slice at a time, each separately audited)

01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09.

- The tests come before the fixes, so the suite is green on the unfixed code first, and the fixes are
  then shown to break no seam.
- Slice 03 comes before the Tier X slices because T-X2 and T-X5 use `samples`.
- Slice 08 follows the fixes, so coverage includes every new test.
- Each slice's updater runs once after its commit (`hypergraph_updater.py --from-diff <Start>
  --apply`, re-indexing first).

### Contracts (slices cite these by name)

- **Marker contract (R2, R24):** `integration` = "integration test across module seams; real
  modules, no mocks across the seam (v0.7.1)". It is in `DEFAULT_SELECTED_MARKERS` and never in
  addopts. Tier X = `integration` + `xtb`.
- **Mock-policy contract (R26):**
  - Forbidden: every form listed in R26, and skip/xfail in any form (R25).
  - Allowed: `monkeypatch.setenv`, `monkeypatch.delenv`, `monkeypatch.chdir`, and a subprocess run of
    a committed loader (R21).
- **Seam-break contract (R4, R22):** one row per break,
  `{test_id, break_description, patch_file, eta_file, command, failed: true}`, in
  `missions/release-0.7.1/slices/<NN-slug>/seam_breaks.json`.
- **`ArtifactStore.__init__(path, *, open_timeout_s: float = 5.0)` (R29):**
  - `open_timeout_s` is > 0, and `math.inf` means no deadline.
  - `bool` or a non-real value raises `TypeError`.
  - NaN or ≤ 0 raises `ValueError`.
  - `connect` and each `busy_timeout` are ≤ `2**31 - 1` ms.
- **`SampleKeys` (R37):** frozen; `index: int`, `source: str`, and
  `pre_relax_key | ts_opt_key | frequency_key: str | None`. `TSEnsembleRun.samples` is in sample
  order, with the seed first.
- **Licence label (R28):** `LicenseRef-BSD-classifier` ∈ `allowed`. The label table entry is
  `"BSD (variant not stated)"`, and the row's licence column reads `<raw> [BSD (variant not
  stated)]`.
- **RunRecord JSON (R38):** an infinite `ratio` is written as `"Infinity"` and read back as `inf`.
  Finite values are unchanged.
- **`QUALITY_RESULT.json` (R20, R30):** generated, never hand-edited.

### Dependencies

- **No new Python or JS dependency.** `coverage` is already in `.venv`, and ruff rules are run ad hoc.
- **v0.7.0 (shipped at `bf7b949`):**
  - enumerator (`enumerate_candidates`);
  - ts_fallback (`enumerated_pathway_inputs`, `run_ts_with_fallback`, the seed-check allow-list at
    `ts_fallback.py:60`);
  - seed checks (`find_clash`, `bond_changes`, `SeedCheckDetail` at `core/selectivity_models.py:68`);
  - review (`export_run_data`, `read_run_data`, `write_review_bundle`, `run_data.v1.schema.json`;
    `TSIdentity` and the dispositions are in `review/run_data.py:505-543`);
  - the E2E inputs `v070_enumeration.yaml` and `v070.py`.
- **v0.8.0** relies on R13/R29, R14 and R37 landing here.

## 6. Negative Constraints

- **DO NOT** run GPU, UMA, MACE or PySCF in any slice or audit. Run CPU GFN2 only, under the heavy-run
  rule.
- **DO NOT** mock, monkeypatch-replace or stub across the seam a test guards. Do not import from
  `tests.unit` or `tests.e2e` in `tests/integration/**`.
- **DO NOT** compare numbers across two engine runs or against a stored reference. The one byte-parity
  check against a promoted fixture is R37's, which checks that the record format did not change, not
  a numeric value. Do not write to `tests/candidate_outputs/` or `tests/fixtures/`, and do not
  promote.
- **DO NOT** change a stage key, a cache payload, `ReactionGraph` schema 1, `EnumerationPlan`,
  `score_selectivity`, or a RunData v1 field to make a test pass. A seam defect found by a test is a
  stop-and-report to the lead, never a quiet fix.
- **DO NOT** change behaviour beyond R13/R29, R14, R37 and R38. Do not make `PotentialResult` strict
  or deep-frozen (R15).
- **DO NOT** remove a public (`__all__`) symbol, or anything without its R17/R31 evidence row.
- **DO NOT** add a Python or JS dependency.
- **DO NOT** add words to the core description. Compress first in any node at or above 1978 (§5
  carry-forward 7).
- **DO NOT** hand-edit `architecture.yml`. Run the updater once per slice.
- **DO NOT** run `uv` in a worktree (R22).
- **DO NOT** edit `PRDs/` or `missions/release-0.7.0/` and older missions, and do not approve lore.
  Do not read `spec/archive/` or `tests/candidate_outputs/`.
- **DO NOT** open Eta_Scripts/nMap or any TS-optimizer/conformer-search source, and do not read or
  patch geomeTRIC source.
- **DO NOT** use `rm -rf` on computed paths. Remove worktrees and scratch by literal path.
- The ruff format oracle is **only**
  `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process`.

## 7. Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Tier O makes the default suite slow | M2: ≤ 60 s added, measured as slice 02's first task. Over budget is stop-and-report: move a test to Tier X, never weaken it. |
| Tier X is too heavy for a small release | M1 picked the smallest inputs (≈ 5.5 min). Slices 04 and 05 measure first, with 2× the estimate as the stop. |
| GFN2 nondeterminism makes a test flaky | R7: only invariants and exact fresh-vs-replay equality (M1a/b/c: replay equal). |
| A test "passes" because it cannot fail | R4 seam breaks, run with R22's interpreter. The proof shows `eta_rxncat.__file__` under the worktree. A surviving break is a FAIL. |
| A seam-break proof imports the main checkout | R22: `PYTHONPATH=<worktree>/src` with an import-path record, and never `uv` in a worktree. |
| A test passes by skipping | R25 (guarded dir, no skip forms), Tier X under `=1`, and the verdict counting T-O ids `passed` by id. |
| The inputs do not exist in the form the seams take | R21, settled against the shipped v0.7.0 files, with a parity test against the E2E loader. |
| The plan's TS priority does not fit `run_selectivity` | R35: an explicit, stated priority copy in the test, with the join deferred to v0.8.0. |
| Integration tests find a real seam defect | Stop and report to the lead. A fix is a separate decision. |
| Ledger description caps | §5 carry-forward 7. Compress first and state the counts. |
| `ensure-node --files` replaces lists | Pass full lists, and check glob counts before and after (R5, R27). |
| Dead-code removal breaks an engine path | R31's scripted exclusion set. Public symbols are kept, and the suite stays green. |

## 8. Success Metrics

- **G1/G2:** the policy test is green and each negative case fails as designed. The ledger validates.
  The new node owns `tests/integration/**`. The R27 globs are added, with 65 fixture files owned.
  Core and engines descriptions are unchanged.
- **G3:** T-O1…T-O6 and the R21 parity test are `passed` by id in the default junit, with 0 skipped
  and ≤ 60 s added.
- **G4:** `samples` is present. `v070.py` has no private eta import. The defd982 test is green. The
  parity record is byte-equal.
- **G5/G6:** T-X1…T-X5 are green with 0 skipped under `=1`, inside R33's budget, with every host check
  in the proof.
- **G7:** every seam break failed its test, with `eta_file` under the worktree (the
  `seam_breaks.json` files).
- **G8:** each known-issue test fails at `bf7b949` and passes after. R15 is kept, R12's two edge cases
  are dropped, and the deferrals are listed, each with its reason in the CHANGELOG.
- **G9:** the R17 table is complete. `test_doc_refs.py` is green and fails on a planted stale name.
  The R41 docstrings are present, and every new claim is cited.
- **G10:** `QUALITY_RESULT.json` is generated, and its gates pass. `test_identity` is green at 0.7.1.
  The version is 0.7.1 everywhere. The lead pushes on the verdict.

## Slices

<!-- BEGIN HACF GENERATED: slices -->
| id | slice | intent |
|---|---|---|
| OPR.0.7.1.1 | slices/01-integration-harness | Give tests/integration a default-selected integration marker, real-module helpers, a no-mock no-skip policy test, the eta_rxncat_integration node, and ownership of every promoted fixture. |
| OPR.0.7.1.2 | slices/02-tier-o-seams | Check every offline module seam (store, species runner, UFF, geomeTRIC, thermo, conformers, real graft, graph IO, energies, enumerated seed inputs) in each default run, within 60 s added. |
| OPR.0.7.1.3 | slices/03-ensemble-sample-keys | Expose each TS ensemble sample's stage keys on TSEnsembleRun, switch the v0.7.0 E2E off private helpers with a byte-equal record, and unit-test the clashed-sample rule. |
| OPR.0.7.1.4 | slices/04-tier-x-ts-seams | Check the P-RFO, TS ensemble and seed fallback seams against CPU GFN2 xtb with real modules on both sides. |
| OPR.0.7.1.5 | slices/05-tier-x-selectivity-review | Check the enumerated graph file to selectivity score chain on CPU GFN2 and the review export from that store through the schema, lenient reader and bundle writer. |
<!-- END HACF GENERATED: slices -->

## Status

- compiled
