---
id: OPR.0.7.0.7
slice: 07-run-data-contract
mission: release-0.7.0
status: done
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Define RunRecord and the versioned RunData v1 contract with a strict writer, a lenient reader, a committed JSON Schema with a drift test and a canonical escaped serialisation, and export a run from the store without running an engine."
depends_on: [OPR.0.7.0.5, OPR.0.7.0.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_review
parent: null
hacf_touches: ["src/eta_rxncat/review/**", "tests/unit/review/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/review]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 run-data JSON v1 and its exporter

## Intent

One public contract every view reads, now and later (TJ's UI track; mission G11, R12, R14, R15, R18;
US-014). The exporter resolves a run's cached rows into one self-contained `RunData`; it never
computes an engine result.

Context the builder needs:
- **Package `src/eta_rxncat/review/`** (review node): `run_data.py`, `export.py`, `schema/`.
- **`RunRecord`** (exporter input, pydantic): candidates (`EnumeratedCandidate` refs by id), per
  candidate × pathway × engine the `FallbackRecord`, the `GraftRecord`s, the selectivity result,
  and the **stage keys** of every pre-relax, TS search, frequency and endpoint optimization row,
  plus `ThermoAnalysisOptions` per run.
- **`RunData` (strict writer):** `schema_version: Literal[1]`, `extra="forbid"`, every unit in its
  key. Sections: `provenance` (eta `__version__`, engine/optimizer identities with model hashes,
  stage keys, thermo options, **store file name only**), `species[]`, `frequencies[]`
  (`frequencies_cm1`, `n_imaginary`, `imag_tol_cm1`, per imaginary mode `displacements_angstrom`),
  `trajectories[]` (`kind`: `pre_relax` | `ts_search` | `endpoint_opt`; `frames[]` with
  `coordinates_angstrom`, `energy_hartree`, `max_gradient_hartree_per_bohr`, `accepted_bool | None`
  (per M11), `ladder_step | None`; `label`; `decimation_stride`; `n_frames_total`; convergence data),
  `candidates[]` (R, pathway, engine, `template_rank_used`, fallback attempts **as codes**, charge,
  multiplicity, `dG_dagger_kcal_mol | None`, `ddG_dagger_kcal_mol | None`, members with
  `weight_fraction`, `graft_rmsd_angstrom`, `stall_cap_reached_bool`, id references), `gates[]`
  (`gate_id`, `pass_bool`, value with unit, threshold, `detail_code`). Ids are deterministic strings;
  references are by id.
- **Lenient reader (R12):** `read_run_data(bytes) -> RunData` via a parallel model tree with
  `extra="ignore"` and `schema_version: int`; refuses `schema_version > 1` with
  `UnsupportedRunDataVersion`. A v1 document with an unknown key loads.
- **Version rule (in the schema `description`, and a `CHANGES` list):** additive optional keys keep
  the version; removing/renaming/retyping a key, changing a unit or meaning, or **adding an enum
  value** bumps it; the writer always emits the current version.
- **Schema artefact:** `src/eta_rxncat/review/schema/run_data.v1.schema.json` generated from
  `RunData.model_json_schema()` by a small script (`python3 -m eta_rxncat.review.schema`), committed;
  a drift test fails if they differ, its message naming the installed pydantic major.
- **Canonical serialisation (R14):** `canonical_run_data_json(run_data) -> bytes`: sorted keys, floats
  rounded to a fixed number of significant digits per unit family and written by `repr`, compact
  separators, and the characters `<`, `>`, `&`, U+2028, U+2029 written as `\u003c`, `\u003e`,
  `\u0026`, `\u2028`, `\u2029`. Valid JSON; `json.loads` of it equals the model dump after rounding.
  Round-trip tests compare re-serialised bytes, never floats.
- **Exporter (`export_run_data(record, store)`):** resolves rows by stage key; a missing row →
  `{"status": "missing", "stage_key": …}` (never recomputed); modes from the stored
  `hessian_hartree_per_bohr2` with `thermo.normal_modes` and the run's own options (so the listed
  frequencies are the gated ones; no engine call); reason **codes** only, never `message` (R15);
  decimation: `decimation_stride` chosen so the trajectory total stays within a byte budget passed
  as a keyword (slice 08 sets it from M10), `n_frames_total` always the full count.
- **Edges:** review → core, thermo, store only.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (slices 11-13 write candidates; they never read them back as input).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.

## 1. The Confidence Mandate

**Score: 9/10.** Pydantic-only, no new dependency, every rule from the red team stated. Residual risk:
pydantic's schema output across minors; the drift test names the major and regenerating is one
command.

## Mini-requirements

1. Strict writer refuses an unknown key; lenient reader loads it; version 2 is refused.
2. Committed schema == `model_json_schema()` (drift test).
3. `canonical_run_data_json` is valid JSON, escapes the five characters, and is byte-identical over
   two calls; a hostile label (`</script><img src=x onerror=…>`, `<!--`, U+2028) appears only
   escaped in the bytes.
4. Export from a stub store (built in the test with real stage keys and payloads) is byte-identical
   twice; a missing row exports `missing`; no `message` text and no absolute path appears.
5. Modes: a stub Hessian with a known imaginary mode exports the right `n_imaginary` and a
   normalised displacement.
6. Decimation: `n_frames_total` is the full count; the stride respects the byte budget.
7. Every key with a physical unit carries it (a schema walk test).

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] `review/run_data.py` (writer, reader, version error), `review/schema/__main__.py`, schema file.
- [x] `review/export.py` (`export_run_data`, `canonical_run_data_json`).
- [x] Tests `tests/unit/review/test_run_data.py`, `test_export.py`, `test_canonical_json.py`.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** run an engine or recompute a result in the exporter; **DO NOT** export messages, paths,
  usernames, hostnames or timestamps.
- **DO NOT** HTML-escape data values; **DO NOT** add `jsonschema` or any dependency.

## Proof contract

- [ ] `uv run pytest tests/unit/review -q` passes (requirements 1-7).
- [ ] Required checks exit 0.

## Source material

- Mission G11, R12, R14, R15, R18.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.5, OPR.0.7.0.6.
