---
id: OPR.0.7.0.16
slice: 16-review-dispositions
mission: release-0.7.0
status: done
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Show on every review-site frequency row whether it fed the result and why not, group rejected rows apart from used ones, show each TS's identity numbers with a banner on any identity failure, and carry the endpoint disposition from the species runner into the run record."
depends_on: [OPR.0.7.0.15]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_review
parent: null
hacf_touches: ["src/eta_rxncat/review/**", "tests/unit/review/**", src/eta_rxncat/orchestrator/species.py, "tests/unit/orchestrator/**", tests/e2e/v070.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/review, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Review dispositions and TS identity on every row

## Intent

Make the review site say, on every frequency row, whether that row fed the result and why not.
Rejected rows are grouped apart from used ones, each TS shows its identity numbers, and a failed
identity raises a banner (mission G15, R35; TJ's "Fix site": "every row shows
member/excluded/superseded and why, rejected rows grouped apart, each TS shows imaginary frequency,
forming-bond overlap and bond lengths").

Context the builder needs:
- **Why (diagnosis `~/.hacf/eta-rxncat-hacf/evidence/v070-diag/DIAGNOSIS.md`):**
  - `review/export.py` adds a frequency entry for every sample and every endpoint frequency key.
  - `review/bundle.py:_unit_summary` labels each one "Transition state … (sample <key>)" or
    "Minimum …", and banners only on mode count.
  - So TJ saw an excluded TS (count 1, no banner) and a pre-push minimum (1 imaginary mode) with
    nothing saying they were rejected or superseded.
  - The endpoint disposition is not in the run record at all.
- **Species runner (`orchestrator/species.py`):**
  - `SpeciesResult` gains `frequency_dispositions: tuple[FrequencyDisposition, ...] = ()`, a
    frozen dataclass `(frequency_key, kind, reason, superseded_by_key)`. It has one entry per
    frequency row the run used, in visit order. `kind` is one of:
    - `kept`: the record is in the returned ensemble;
    - `superseded_by_push`: `check_ground_state` raised and `_push` gave a new row, named by
      `superseded_by_key`;
    - `dropped`: the run's own drop reason, e.g. `duplicate_after_push`, `not_a_minimum`,
      `optimization_failed` or a mirror reason.
  - No stage key, result or engine call changes; a test pins it.
  - A unit test with a fake engine covers each kind, including the push chain
    (`superseded_by_push` → the new row, then `duplicate_after_push`).
  - The species_runner description is 1988/2000: compress before adding (cap 2000).
- **RunRecord** (`review/run_data.py`; the exporter's input):
  - `record_version` stays **1**. Both additions are optional and **left out of the serialised
    form when absent**:
    - `RecordEndpoint.frequency_dispositions: list[RecordFrequencyDisposition] | None`, which
      mirrors the dataclass with codes and stage keys;
    - `RecordRun.validation: TSValidationOptions | None`, where `None` means
      `TSValidationOptions()` (every v0.7.0 run used the default).
  - Every existing record (`tests/fixtures/v0.7.0/*.runrecord.json`, the evidence records) loads and
    exports. Its endpoint rows read `not_recorded` (never guessed).
  - The E2E record writer `tests/e2e/v070.py:unit_record` fills both fields.
- **TS dispositions** come from the record as it is (no new record field). They are per sample of
  the run:
  - `member` (with its weight);
  - `merged` (with `merged_into_index`);
  - `excluded` (`reason_code`, plus slice 15's `SeedCheckDetail` when present: clash pair, distance
    and ratio, bonds formed and broken);
  - `fell_through` (samples of a template that fell through: the attempt's reason).
- **RunData** (`schema_version` stays **1**):
  - v0.7.0 is unreleased, every addition is an optional key with a default, and no value is added
    to an existing enum (R12). So `read_run_data` still loads a document written before this slice.
    A test loads one built with the pre-slice field set.
  - The committed JSON Schema is regenerated; the drift test passes. `CHANGES` is unchanged.
  - `Candidate.sample_dispositions: list[SampleDisposition] = []`. Each entry has `template_id`,
    `sample_index`, `source`, `frequency_id | None`, `kind` (`member|merged|excluded|fell_through`),
    `reason_code`, `merged_into_index`, `weight_fraction`, `clash` (`{i, j, distance_angstrom,
    ratio}` or None), `bonds_formed`, `bonds_broken` and `identity: TSIdentity | None`.
  - `TSIdentity` holds `n_imaginary`, `imaginary_frequency_cm1`, `forming_overlap`,
    `active_core_ke_fraction`, `forming_distances` (`[{i, j, distance_angstrom}]`), `in_phase_bool`,
    `passed_bool` and `reason_codes`.
    - It is recomputed by the exporter with `thermo.ts.validate_transition_state`. The inputs are the
      stored Hessian, the `ts_opt` row's forming bonds, the run's `analysis` and its `validation`.
      No engine runs (R12).
  - `Candidate.endpoint_dispositions: list[EndpointDisposition] = []`. Each entry has
    `frequency_id`, `kind` (`kept|superseded_by_push|dropped|not_recorded`), `reason_code` and
    `superseded_by_frequency_id`.
- **Static summary (R17, `bundle.py`), per unit:**
  - **"Used in the result":** the `member` TS rows and the `kept` endpoint rows.
  - **"Not used (rejected, merged or superseded)":** everything else, below the used rows.
  - Every block's heading names its disposition, e.g.:
    - "excluded: gate_failed:forming_overlap";
    - "excluded: seed_clash C4–H21 0.438 Å";
    - "superseded by push → <frequency id>".
  - A sample with no frequency row (e.g. `seed_clash`) is a one-line row in the not-used group.
  - **Every TS block** shows the identity numbers: imaginary frequency, overlap, KE fraction, each
    forming distance, in phase, pass/fail with reason codes.
  - **The banner** fires when `n_imaginary != 1` **or** `passed_bool` is False, not only on count.
  - A `superseded_by_push` minimum keeps its count banner, with the "superseded" label beside it.
- **JS (`assets/eta-view.js`):**
  - Every component that lists or selects a frequency row shows the disposition label and lists
    not-used rows after used rows.
  - It reads only `RunData` and still writes text only through `textContent`/`setAttribute`. The R14
    sink scan and the CSP are unchanged.
- **M12 repeat on stubs** (slice 09's driver `slices/09-view-components/proof/m12/`; installed Chrome
  and Playwright Firefox, headless, `file://`):
  - The stub gains one `excluded` TS row with a failing identity (banner shown), one `merged` row, one
    `seed_clash` row with no frequency, and one `superseded_by_push` minimum.
  - Screenshots, console and network logs go in the proof.
- **Real-data known answer** (proof only, read-only):
  - Export `tests/fixtures/v0.7.0/v070_enum_ethyl_endo_xtb.runrecord.json` against slice 11's store
    (sqlite `mode=ro`) with 0 engine calls.
  - Sample 6's `TSIdentity` must match the diagnosis: overlap 0.131, distances 3.662 / 2.853 Å,
    `passed_bool` False, reasons `forming_distance_out_of_window`,
    `forming_overlap_below_threshold`.
  - Its row must be in the not-used group with a banner.
- **Node** `eta_rxncat_review` (description 1991/2000: compress before adding, cap 2000). It also
  touches `orchestrator/species.py` and `tests/e2e/v070.py` (species_runner node) for the endpoint
  disposition. That is listed in the proof, and the updater flags the blast radius.
- **Times:** build about 3.5 h of seat time (Python, JS, M12 on stubs) and audit about 1 h. GPU 0.
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (the E2E writes candidates and never reads them back as input;
    `tests/fixtures/v0.7.0/` holds byte-equal copies and may be read).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
    Plain literal `rm -f` only (never `rm -rf` on a computed path).
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.

## 1. The Confidence Mandate

**Score: 9/10.**
- The data behind every disposition already exists: the ensemble's members, merges and exclusions,
  the fallback attempts, and species.py's `dropped` and push path.
- The identity numbers are recomputed with eta's own validator, as the diagnosis did, and matched
  the record.
- Residual: the JS layout on the real bundle; slice 18 repeats M12 on it.

## Mini-requirements

1. Every TS sample and every endpoint frequency row in `RunData` carries a disposition. Endpoints in
   an old record read `not_recorded`.
2. The static summary groups used rows apart from not-used rows. Every TS block shows imaginary
   frequency, overlap, KE fraction and forming distances, and the banner fires on an identity
   failure.
3. The JS views show the same disposition and grouping. M12 passes on stubs in both gate browsers.
4. Old records and pre-slice `RunData` documents still load. Stage keys and species results are
   unchanged.

## 3. Implementation Plan (Task List)

- [x] Index.
- [x] species.py `frequency_dispositions` and its tests; compress the species_runner description.
- [x] RunRecord fields (omit when absent); `unit_record` fills them; old-record load tests.
- [x] RunData models, schema regeneration, the exporter (dispositions and `TSIdentity`); tests.
- [x] Static summary grouping and banners; JS labels and grouping; R14 scan; stub M12 in Chrome and
  Playwright Firefox.
- [x] Real-data known answer (read-only export); required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** bump `schema_version` or `record_version`, change a key's meaning, unit or type, or add
  a value to an existing enum.
- **DO NOT** run an engine in the exporter or write any store. **DO NOT** change a stage key.
- **DO NOT** guess a disposition the record does not carry; it is `not_recorded`.
- **DO NOT** hide rejected rows. They are grouped below and labelled, never dropped.
- **DO NOT** add an `innerHTML`-class sink, a network reference or a second data contract.

## Proof contract

- [x] Tests for each disposition kind (species and exporter); old record and old `RunData` loads;
  schema drift test.
- [x] Static-summary tests: grouping, disposition headings, identity numbers, the identity-failure
  banner.
- [x] M12 stub evidence in both gate browsers (screenshots, console, network).
- [x] The real-data sample-6 known answer, read-only, 0 engine calls.
- [x] Required checks exit 0.

## Source material

- Mission G12, G15, R12, R14, R17, R35; DIAGNOSIS.md §2 and §5; `review/{run_data,export,bundle}.py`,
  `assets/eta-view.js`, `orchestrator/species.py:515-730`, `tests/e2e/v070.py:unit_record`.

## Intent visual

Per unit, a "Used in the result" group, then a "Not used" group. Every block is headed by its
disposition, and every TS block lists its identity numbers; the banner sits on any identity failure.

## Status

- compiled

## Dependencies

- OPR.0.7.0.15 (it renders slice 15's reasons and `SeedCheckDetail`).
