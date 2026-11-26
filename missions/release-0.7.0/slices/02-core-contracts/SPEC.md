---
id: OPR.0.7.0.2
slice: 02-core-contracts
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Add the enumeration, selectivity-set and fallback contracts, the optimization frame fields and the orientation_mismatch exclusion reason to core, all additive and numpy-free."
depends_on: [OPR.0.7.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 core contracts and frame fields

## Intent

Give every later slice typed, unit-suffixed contracts to build against (mission §5 "Contracts", G1,
R2, R9, R13, R24; US-003). Everything here is additive: `ReactionGraph` schema 1, every existing
fixture and every v0.6.0 record keep loading unchanged.

Context the builder needs:
- **New module `src/eta_rxncat/core/enumeration_models.py`**, exported from `eta_rxncat.core`,
  `CoreModel` (`extra="forbid"`, frozen), units in names, no numpy/RDKit: `SiteTemplateMap`,
  `EnumerationSite`, `LibraryEntry`, `PathwaySpec`, `SelectivitySet`, `EnumerationPlan`,
  `GraftRecord`, `EnumeratedCandidate`, `EnumerationResult`, `FallbackAttempt`, `FallbackRecord`,
  with exactly the fields in the mission's Contracts section.
- **Validators (model-level, no chemistry):**
  - `SiteTemplateMap.forming_bonds`: pairs of distinct non-negative ints, sorted within and across
    pairs; `template` is an `AtomMappingSpec` with empty `anchors`.
  - `LibraryEntry.fragment_orders`: >= 1 order, each the same length as the site's alignment minus
    nothing it can know here (length check against the site happens in slice 03); unique orders.
  - `EnumerationPlan`: unique site ids, unique entry ids, every entry's `site_id` exists, every
    `SiteTemplateMap` names a node and template present in `reference_graph`, every selectivity set
    names existing nodes, `max_candidates` >= 1.
  - `PathwaySpec.expected_face`: a non-empty tuple of +1/-1.
  - `EnumeratedCandidate`: `graph is None` iff `status != "ok"`; `detail` required when not ok.
  - `FallbackRecord`: exactly one of `chosen_template_id`, `stop_reason` is set, unless `attempts`
    is empty (then `stop_reason` is set); attempt ranks strictly increase.
- **Frame fields (`core/optimization_models.py`, `core/ts_models.py`):**
  `OptimizationFrame(coordinates_angstrom, energy_hartree, max_gradient_hartree_per_bohr,
  ladder_step: str | None)`; `OptimizationResult.frames: list[OptimizationFrame] | None = None`;
  `TSStep.coordinates_angstrom: list[list[float]] | None = None`. Defaults `None` so v0.6.0 rows
  validate; a v0.6.0 row has no `frames` key and re-serialises without one (`exclude_none` where the
  existing payload writers already use it; check `_opt_payload` and the TS payload and keep their
  current key sets for `None`).
- **Exclusion reason:** `_EXCLUSION_REASON` in `core/selectivity_models.py` gains
  `orientation_mismatch` (additive alternative).
- **Import isolation:** a unit test imports `eta_rxncat.core` in a subprocess and asserts neither
  `numpy` nor `rdkit` is in `sys.modules`.
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

**Score: 9/10.** Pure pydantic models with stated validators, in the established `CoreModel` style.
Residual risk: payload key sets for `None` frames; requirement 6 pins them byte-for-byte against a
v0.6.0 row.

## Mini-requirements

1. Each new model round-trips JSON (`model_validate_json(m.model_dump_json()) == m`).
2. Each validator above has a refusing test and a passing test.
3. Every v0.6.0 fixture graph under `tests/` and every existing unit test still passes.
4. `orientation_mismatch` validates as a `TSEnsembleExclusion.reason`; every old reason still does.
5. Core import isolation test passes.
6. A v0.6.0-shaped optimization payload and TS step (no frames) validate and re-serialise to the
   same bytes as before this slice.

## 3. Implementation Plan (Task List)

- [x] Index (`hyper_codegraph.py index`).
- [x] Write `enumeration_models.py` and export it from `core/__init__.py`.
- [x] Add the frame fields and the exclusion reason.
- [x] Tests in `tests/unit/core/test_enumeration_models.py`, `test_frame_fields.py`,
      `test_core_import_isolation.py`.
- [x] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** change any existing field, default or validator of `ReactionGraph`, `TemplateGeometry`,
  `ReactionNode`, `TSEnsembleOptions` or any v0.6.0 model.
- **DO NOT** import numpy or RDKit in core.
- **DO NOT** add behaviour (grafting, scoring) to core.

## Proof contract

- [ ] `uv run pytest tests/unit/core -q` passes (requirements 1-6).
- [ ] Required checks exit 0 (full suite green: requirement 3).

## Source material

- Mission §5 "Contracts", R2, R9, R13, R24.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.1. Slices 03, 06 and later depend on this one.
