---
id: OPR.0.7.1.2
slice: 02-tier-o-seams
mission: release-0.7.1
status: active
stage: wip
verified: "2026-11-27 against scaffold (hyper_scope slice create)"
created: "2026-11-27"
intent: "Check every offline module seam (store, species runner, UFF, geomeTRIC, thermo, conformers, real graft, graph IO, energies, enumerated seed inputs) in each default run, within 60 s added."
depends_on: [OPR.0.7.1.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_integration
parent: null
hacf_touches: ["tests/integration/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", ., "--extend-exclude", spec/archive, "--extend-exclude", spec/process], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/integration]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Tier O offline seams (T-O1…T-O6) and the plan-loader parity test

## Intent

Check every offline seam in each default run with real modules on both sides: store, species runner,
RDKit UFF, `GeometricOptimizer`, thermo, conformers, the real `graft` in the enumerator, graph file
IO, energies from real runner output, and the enumerated seed inputs (mission R7, R8, R21, R36;
US-003).

Context the builder needs:
- **Task 2 is M2 (stop-and-report):** measure the default suite's wall before and after adding the
  file (junit `time`, same host, idle). Added wall > 60 s is a stop-and-report to the lead; the cure
  is moving a test to Tier X, never weakening it.
- **File:** `tests/integration/test_seams_offline.py`, module `pytestmark = pytest.mark.integration`,
  using only the slice-01 conftest helpers.
- **Tests (R8, R36):**
  - **T-O1** a butane `SpeciesSpec` built in the test with `n_embed=3`, UFF recipe: `run_species`
    creates rows; a rerun on the same store makes 0 rows and `RunMetrics.engine_calls == 0`
    (`orchestrator/species.py:187`) with an equal result; a fresh store gives byte-equal keys;
    `ThermoResult` survives a payload round trip.
  - **T-O2** `reaction_free_energy` from two real `run_species` outputs equals its replay from a
    reopened store (exact).
  - **T-O3** a conformer stage through `run_species`: members are stored, weights sum to 1 within
    `1e-12`, rerun all hits.
  - **T-O4** `enumerate_candidates(plan, max_alignment_rmsd_angstrom=0.15)`
    (`mapping/enumerator.py:126`) with the real `graft` on `load_v070_plan()`: 2 `ok` candidates,
    each graft RMSD ≤ 0.15, 0 contacts, every node 0/1, `model_dump_json` byte-equal across two runs.
  - **T-O5** an enumerated candidate graph → `dump_reaction_graph_json` (`core/io.py:111`) → a
    `tmp_path` file → `load_reaction_graph` (`core/io.py:69`) equals the original. The docstring
    says the input is produced in the test (no committed standalone neutral graph file exists).
  - **T-O6** the ethyl candidate → `enumerated_pathway_inputs` (`orchestrator/ts_fallback.py:203`)
    for `TS1a_n` and `TS1a_x`: `find_clash(seed)` (`ts_ensemble.py:140`) is None; the seed's forming
    bonds equal the candidate's composed bonds order-free; the core equals
    `seed.start.active_atom_indices`. No engine.
  - **`test_plan_loader_parity` (R21):** `subprocess.run([sys.executable, "-c", ...])` with
    `sys.path` set to `tests/e2e`, running `v070.load_enumeration` on the same YAML and printing the
    plan's `model_dump_json()`; it must equal the conftest plan's byte for byte.
- **Seam breaks (R4):** each test's docstring names at least one break; the SPEC list below is the
  minimum. The audit applies each with R22's interpreter and commits
  `missions/release-0.7.1/slices/02-tier-o-seams/seam_breaks.json`.
  - T-O1 ⇐ drop the engine identity from `stage_payload` (`store/keys.py`); and ⇐ `ArtifactStore.get`
    returns None.
  - T-O2 ⇐ `reaction_free_energy` drops one species' term.
  - T-O3 ⇐ the conformer stage skips storing members.
  - T-O4 ⇐ the enumerator skips the `index_map` remap.
  - T-O5 ⇐ `dump_reaction_graph_json` omits one node field.
  - T-O6 ⇐ `enumerated_pathway_inputs` returns the reference (ungrafted) forming bonds.
  - parity ⇐ the conftest loader resolves `xyz` against the repo root instead of the YAML dir.
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

**Score: 9/10.** The APIs were re-read at `bf7b949`; T-O4's expected 2 `ok` candidates and 0 contacts
are v0.7.0's offline-pinned facts (`tests/e2e/test_v070_inputs.py:175`). Residual: M2's wall, which
is measured first with a stop line.

## Mini-requirements

1. M2 measured; added wall ≤ 60 s or stop-and-report.
2. T-O1…T-O6 and the parity test pass by id in the default suite, 0 skipped.
3. Each test's docstring names its seam break(s); the SPEC list is the minimum.
4. The slice-01 policy test stays green over the new file.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] M2 baseline.
- [ ] T-O1…T-O3.
- [ ] T-O4…T-O6 and parity.
- [ ] M2 after; required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run xtb, GPU or any MLIP; **DO NOT** add an `xtb` marker here.
- **DO NOT** compare a number with a stored reference or across two engine runs (R7).
- **DO NOT** read `tests/e2e/data/hf1_butane.yaml` (RT-19).

## Proof contract

- [ ] M2 before/after junit times; added ≤ 60 s (requirement 1).
- [ ] `uv run pytest tests/integration -q --junitxml=<proof>` shows every T-O id and the parity test
  `passed` (requirement 2).
- [ ] Required checks exit 0 (requirements 3-4).

## Source material

- Mission R4, R7, R8, R21, R22, R36; v0.7.0 slice 10's inputs.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.1.1.
