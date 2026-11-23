---
id: OPR.0.4.0.2
slice: 02-graft-contracts
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Add frozen strict core contracts GraftSpec, GraftResult, CloseContact and JunctionVolume in core/mapping_models.py with pass/reject tests for every validator, keeping eta_rxncat.core free of numpy and RDKit."
depends_on: [OPR.0.4.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_core
parent: null
hacf_touches: [src/eta_rxncat/core/mapping_models.py, src/eta_rxncat/core/__init__.py, "tests/unit/core/**", tests/unit/test_package.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core/test_core_mapping_models.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 graft contracts in core

## Intent

Add the frozen, strict core contracts `GraftSpec`, `GraftResult`, `CloseContact` and
`JunctionVolume`, with `NonNegativeFiniteFloat`, in `src/eta_rxncat/core/mapping_models.py`. Each
validator gets a pass test and a reject test, and `eta_rxncat.core` stays free of numpy and RDKit.

Context the builder needs:
- Core models subclass `CoreModel` (`core/models.py`: `extra="forbid"`, frozen, strict per
  ADR-0003). Reuse its types: `StrictInt`, `PositiveInt`, `NonNegativeInt`,
  `PositiveFiniteFloat`, and `FiniteFloat` from `core/optimization_models.py` or wherever it is
  defined (read the code). Units go in field names.
- **`AtomMappingSpec` (ADR-0005) is reused unchanged.** Its own validator enforces:
  - keep ∩ delete = ∅;
  - alignment ⊆ keep, with ≥ 3 entries;
  - anchors ⊆ keep;

  and `check_atom_count(n)` enforces ranges and the keep/delete partition. Do not edit it.
- Add `NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]` in
  `mapping_models.py`.

**`GraftSpec`**
- `template: AtomMappingSpec`.
- `fragment_alignment: list[NonNegativeInt]`.
- `fragment_delete: list[NonNegativeInt] = []`.
- `constrained_core: list[NonNegativeInt] = []`.
- `product_charge: StrictInt`.
- `product_multiplicity: PositiveInt`.
- `min_distance_angstrom: PositiveFiniteFloat = 0.5`.
- `degenerate_tolerance_angstrom: PositiveFiniteFloat = 1e-3`.
- `planar_tolerance_angstrom: PositiveFiniteFloat = 0.05`.
- `junction_volume_tolerance_angstrom3: PositiveFiniteFloat = 0.05`.

`GraftSpec` validators (each raises `ValueError`, surfaced as pydantic `ValidationError`):
1. `len(fragment_alignment) == len(template.alignment)`.
2. `template.alignment` has no duplicates; `fragment_alignment` has no duplicates (mission CR-08).
3. `fragment_delete` has no duplicates and is disjoint from `fragment_alignment`. Message:
   paired fragment atoms are always dropped (TJ R1 "B", mission R15).
4. `constrained_core` has no duplicates and is ⊆ `template.keep`.
5. `template.anchors` is empty (mission R11: anchors are not used by the graft, so a non-empty
   list is refused rather than ignored).

**`CloseContact`**
- `i: NonNegativeInt`, `j: NonNegativeInt`, `distance_angstrom: PositiveFiniteFloat`.
- Validator: `i < j`.

**`JunctionVolume`**
- `template_atom: NonNegativeInt`, `appended_atom: NonNegativeInt`.
- `neighbour_a: NonNegativeInt | None`, `neighbour_b: NonNegativeInt | None`.
- `signed_volume_angstrom3: FiniteFloat | None`.
- `sign: Literal[-1, 0, 1] | None`.
- Validator: the neighbours, the volume and the sign are all `None` together, or all set with
  `neighbour_a < neighbour_b`.

**`GraftResult`**
- `product: MolecularState`.
- `index_map: list[tuple[Literal["template", "fragment"], NonNegativeInt]]`.
- `alignment_rmsd_angstrom: NonNegativeFiniteFloat`.
- `template_charge: StrictInt`, `fragment_charge: StrictInt`, `product_charge: StrictInt`.
- `whole_input_charge_sum_holds_bool: bool`.
- `constrained_core_product_indices: list[NonNegativeInt]`, `active_product_indices: list[NonNegativeInt]`.
- `min_interatomic_distance_angstrom: PositiveFiniteFloat`.
- `template_pair_planarity_rms_angstrom: NonNegativeFiniteFloat`, `fragment_pair_planarity_rms_angstrom: NonNegativeFiniteFloat`.
- `planar_pair_set_bool: bool`.
- `source_bonds: list[tuple[NonNegativeInt, NonNegativeInt]]`.
- `close_contacts: list[CloseContact]`.
- `junctions: list[JunctionVolume]`.

`GraftResult` validators:
1. `len(index_map) == len(product.symbols)` (read `MolecularState` for its atom-list field name).
2. Every index in `constrained_core_product_indices`, `active_product_indices`, `source_bonds`,
   `close_contacts` and `junctions` is < the product atom count.
3. `constrained_core_product_indices` and `active_product_indices` are strictly ascending.
4. `source_bonds` pairs have i < j and the list is strictly ascending.
5. `close_contacts` is strictly ascending by (i, j); `junctions` by (template_atom, appended_atom).
6. `product_charge == product.charge`.

The docstring of `whole_input_charge_sum_holds_bool` states (mission R10): "product charge ==
template charge + fragment charge over the whole inputs, deleted atoms included. It is reported
only, never used to infer, and it is False for a correct graft whose deleted atoms carry charge."

Export all of these from `eta_rxncat.core`. `mapping_models.py` imports no numpy, so
`import eta_rxncat.core` still loads neither numpy nor RDKit; the existing test in
`tests/unit/test_package.py` (or the core one) must keep passing. Extend it if it lists modules.

**Seat rules for every v0.4.0 slice.** These are self-contained. The mission SPEC is
`missions/release-0.4.0/SPEC.md`; its R-rows are cited by number.

- **Clean room (TJ Q1, hard rule).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach".
  - No seat opens, clones, fetches or searches Eta_Scripts or nMap in any form (GitHub, a local
    or cached copy, a web search, a code search).
  - No seat asks the clean-room rig's seats about code.
  - Behaviour comes only from this SPEC, TJ's M1 spec and the approved documents in
    `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/`.
  - Never copy code from the starter (`docs/prd/v0.4.0/`).
  - A conflict between a clean-room document and this SPEC is a stop-and-report for a replan.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.4.0`, cut re-entrantly from Base, which is
  the mission commit on main (parent `c3506e6`). One code commit per slice, unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff.
- **Code graph first.** The first command of the slice is
  `python3 .agents/scripts/hyper_codegraph.py index`, and it must print `index: ok` (the red team
  saw `stale_index`). Anything else stops the slice. The audit treats
  `code_graph.status != ok` as a finding. The graph only widens a blast radius, never narrows it.
- **Ledger.** Write it only with `hyper_ledger.py` / `hypergraph_updater.py`, never by hand.
  - On existing nodes use `ensure-node --id <node>` with the **full** `--files` list (it
    replaces).
  - Count the node's globs before and after.
  - `eta_rxncat_engines` is not touched.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF.** HACF is v0.6.2. No `HACF-install.sh` (a plain run silently DOWNGRADES to 0.6.1 right
  now), no `HACF-uninstall.sh`, no `hyper_migrate.py apply`.
- **OpenRig 0.7.21.** `hyper_migrate.py verify` runs `rig scope audit` (HACF v0.6.2 on OpenRig
  0.7.21). If `hyper_spec.py` or `hyper_migrate.py` warn "outside the pinned contract", note it in
  the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git.
  Every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host memory (heavy runs).** Before any E2E, GPU, relaxation or full-suite run:
  - run `free -g` and list other rigs' heavy python/pytest/engine processes (`ps`);
  - if another heavy run is active, wait (poll at most every 5 minutes with Monitor or a
    background wait, not a foreground sleep);
  - record the check in the proof.

  Heavy runs are sequential. Never kill another rig's process.
- **v0.3.0 lessons (mission R23):**
  - **R54:** every numeric key in an output carries its unit suffix.
  - **R55:** no list in a compared output is in record or energy order; it is fixed by the fixture
    or sorted by an energy-independent key.
  - **R56:** a test records its real outcome through one `gated_outcome`, and `pending_*` fails
    under `ETA_RXNCAT_ACCEPTANCE=1`.
  - **R50:** any code that reads a store or runner payload checks `failed_reason` first (v0.4.0
    adds no such reader).
  - **Candidates (ADR-0027):** code commit C1 with a clean tree, run the E2E at C1, then commit
    only `tests/candidate_outputs/v0.4.0/*` as C2.
- **Required checks** (AGENTS.md), all exit 0 before each commit:
  - `uv sync --locked`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy`
  - `uv run pytest`
  - `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception.
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it, and never loosen a
  tolerance (TJ's or this SPEC's).
- **Never** push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 9/10.** The fields and validators are fixed. The only reading the builder must do is
`MolecularState`'s field names and where `FiniteFloat` lives.

## Mini-requirements

1. `src/eta_rxncat/core/mapping_models.py` with the five types above, exported from `eta_rxncat.core`.
2. `tests/unit/core/test_core_mapping_models.py`:
   - for each validator listed above, one valid instance and one rejected instance (asserting
     `ValidationError` and the message fragment);
   - frozen (assignment raises);
   - `extra="forbid"` (an unknown field raises);
   - strict (`product_charge=True` and `"0"` are refused).
3. A valid M1-shaped `GraftSpec` round-trips through `model_dump_json` / `model_validate_json`
   unchanged. Its fields: keep `[0,1,2,3,4,5,6,8,9,10,11,12,13,14,15]`, delete `[7,16,17]`,
   alignment `[2,3,10,11]`, `fragment_alignment` `[0,3,4,9]`, `constrained_core` `[1,2,3,5]`,
   charge 0, multiplicity 1.
4. `import eta_rxncat.core` loads no numpy or RDKit (subprocess test).

## 3. Implementation Plan (Task List)

- [ ] Task 1: codegraph index → `index: ok`; record Start; read `core/models.py`, `core/optimization_models.py`, `core/__init__.py`.
- [ ] Task 2: write the models and exports.
- [ ] Task 3: write the tests; run the required checks.
- [ ] Task 4: commit; run the updater. Core already owns `src/eta_rxncat/core/**` and `tests/unit/core/**`; no glob change.

## 4. The Negative Space (Constraints)

- **DO NOT** modify `AtomMappingSpec`, `MolecularState` or any existing core model.
- **DO NOT** import numpy, RDKit or anything from `eta_rxncat.mapping` in core.
- **DO NOT** add behaviour (no graft logic) to the models; only validation.

## Proof contract

- [ ] `uv run pytest tests/unit/core/test_core_mapping_models.py -q` passes, with every validator covered both ways (list them in the proof).
- [ ] The subprocess import test passes: `eta_rxncat.core` loads no numpy or RDKit.
- [ ] `git diff Start..HEAD --stat` touches only `src/eta_rxncat/core/{mapping_models,__init__}.py` and `tests/unit/core/**` (plus `tests/unit/test_package.py` if extended).
- [ ] The required checks exit 0.

## Source material

- Mission SPEC §5 "Contracts", R10, R11, R15, R16, R20(b)(c); `src/eta_rxncat/core/models.py`; ADR-0003, ADR-0005.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.1 (the branch and starter; no code dependency)
