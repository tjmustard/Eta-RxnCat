---
id: OPR.0.4.0.4
slice: 04-graft
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Implement ordered graft surgery (paired fragment atoms dropped, optional fragment_delete, explicit charge/spin, re-indexed active atoms and core, overlap floor) with recorded close contacts, junction signed volumes and the planar flag, proved on hand-built cases and clean-room vectors 04, 05 and 07."
depends_on: [OPR.0.4.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["src/eta_rxncat/mapping/**", "tests/unit/mapping/**", tests/unit/test_package.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/mapping]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 ordered graft surgery (mapping.graft) and report helpers

## Intent

Implement `mapping.graft.graft()` and `mapping.report`:
- ordered keep/delete/alignment surgery with paired fragment atoms always dropped and an optional
  `fragment_delete`;
- explicit charge and multiplicity;
- re-indexed active atoms and core;
- an overlap floor that raises;
- recorded close contacts, junction signed volumes and the planar-pair flag.

Prove it on hand-built cases and the clean-room vectors 04, 05 and 07 (eta-adapted).

Context the builder needs:
- **Inputs:** `template: MolecularState`, `fragment: MolecularState`, `spec: GraftSpec` (slice
  02). Alignment comes from `mapping.align.superpose` (slice 03).
- **Algorithm** (normative; mission §5 "Algorithms" G1–G8):
  - **G1. Ranges.**
    - `spec.template.check_atom_count(len(template.symbols))`; re-raise its `ValueError` as
      `GraftInputError(...) from err` (mission R14).
    - Every index in `spec.fragment_alignment` and `spec.fragment_delete` must be
      < `len(fragment.symbols)`, else `GraftInputError`.
    - `template.active_atom_indices ∩ spec.template.delete` must be empty, else
      `GraftInputError` naming the atoms. The same holds for `spec.constrained_core` (⊆ keep is
      already a model rule).
    - A non-empty `fragment.active_atom_indices` raises `GraftInputError` (it would otherwise be
      dropped silently).
  - **G2. Elements.** For each position p, `template.symbols[template.alignment[p]] ==
    fragment.symbols[fragment_alignment[p]]`, else `GraftInputError` naming the pair and both
    symbols (mission R17, CR-07).
  - **G3. Superpose** `fragment[fragment_alignment]` (mobile) onto `template[template.alignment]`
    (reference), unweighted, with `degenerate_tolerance_angstrom=spec.degenerate_tolerance_angstrom`.
    `AlignmentError` propagates unchanged.
  - **G4. Assemble.**
    - Product = `template.keep` in **keep-list order**, with coordinates copied from the
      template's numbers (never recomputed, never passed through numpy arithmetic: kept
      coordinates must compare `==` to the template's floats).
    - Then the **appended** atoms: fragment indices that are in neither `fragment_alignment` nor
      `fragment_delete`, in ascending fragment index, at `superposition.apply` coordinates.
    - `index_map[k]` = `("template", i)` or `("fragment", j)`.
  - **G5. Overlap floor.** Compute all product pair distances. If any pair is
    < `spec.min_distance_angstrom`, raise `GraftClashError(i, j, d)` for the first such pair in
    (i, j) order. Otherwise `min_interatomic_distance_angstrom` = the minimum.
  - **G6. Source graph and contacts.**
    - `report.perceive_bonds` on the template and on the fragment separately.
    - The source graph, in product indices, contains:
      - template bonds whose both ends are kept;
      - fragment bonds whose both ends are appended;
      - **junction bonds** (t, a) for every fragment bond (f, a) where f = `fragment_alignment[p]`
        and t = `template.alignment[p]`, and a is appended.
    - Any bond touching a deleted, dropped or fragment-deleted atom is omitted.
    - `source_bonds` is sorted with i < j.
    - `close_contacts` are pairs (i, j), i a kept-template product index and j an appended product
      index, that are **not** in `source_bonds` and have distance
      < 1.3 × (`report.covalent_radius_angstrom(sym_i)` + `…(sym_j)`). They are recorded, sorted,
      never raised (TJ P1 "A", mission R1). 1.3 is RDKit `DetermineConnectivity`'s own default
      `covFactor`.
  - **G7. Planarity and junctions** (TJ R2 "A", mission R16).
    - `template_pair_planarity_rms_angstrom` and `fragment_pair_planarity_rms_angstrom` are the
      `rms_off_plane_angstrom` values of the two pair sets.
    - `planar_pair_set_bool` is true if either is ≤ `spec.planar_tolerance_angstrom`.
    - `junctions = report.junction_volumes(product_coords, source_bonds, n_kept, spec.junction_volume_tolerance_angstrom3)`.
  - **G8. Product.** Build a `MolecularState` with:
    - `symbols`, `coordinates`;
    - `charge=spec.product_charge`, `spin_multiplicity=spec.product_multiplicity`. Parity is
      checked by `MolecularState`; its `ValueError` surfaces as `ValidationError`, and the test
      pins that;
    - `active_atom_indices` = template actives re-indexed, sorted;
    - `metadata`: `alignment_rmsd_angstrom` and, if present, the inputs' `name` metadata as
      `template_name` / `fragment_name`.

    `GraftResult` adds:
    - the three charges and `whole_input_charge_sum_holds_bool = (spec.product_charge ==
      template.charge + fragment.charge)`;
    - `constrained_core_product_indices` (re-indexed, sorted);
    - `active_product_indices`;
    - the remaining fields.
- **`src/eta_rxncat/mapping/report.py`.** RDKit is imported **inside** the functions only.
  - `perceive_bonds(state) -> list[tuple[int, int]]`: an RDKit `RWMol` with one atom per symbol
    and a conformer from the coordinates, then `rdDetermineBonds.DetermineConnectivity(mol)` with
    its defaults. Returns the sorted (i < j) bond list.
  - `covalent_radius_angstrom(symbol) -> float`: `Chem.GetPeriodicTable().GetRcovalent(symbol)`.
  - `core_rmsd_angstrom(a_coords, b_coords, indices_a, indices_b) -> float`: superpose (A1–A4)
    `b[indices_b]` onto `a[indices_a]` and return the RMSD.
  - `junction_volumes(coords, source_bonds, n_kept, tolerance) -> list[JunctionVolume]`:
    - A junction is a source bond (t, a) with t < n_kept ≤ a.
    - n1 < n2 are the two lowest indices among t's source-graph neighbours that are < n_kept and
      ≠ a.
    - V = (p_a − p_t) · [(p_n1 − p_t) × (p_n2 − p_t)].
    - sign = 0 if |V| ≤ tolerance, else ±1.
    - With fewer than 2 such neighbours, the neighbours, V and sign are all `None`.
    - Sorted by (t, a).
- **Vectors** (`tests/unit/mapping/data/cleanroom_nmap/`, copied in slice 03; 1-based in the
  files, use the slice 03 loader).

  All compare at 1e-6 Å on coordinates and RMSD.
  - **04 aryl para:** template delete {9} (1-based); pairs as in `request.json`;
    `fragment_delete` = the incoming delete list minus the paired atoms (1-based {7..11}). The
    product equals `expected_product.xyz` (11 template atoms, then N, H, H). The N is 1.40 Å from
    template C4 (`template.keep` index of C4).
  - **05 planar reversed:** the same as 04 with 05's pairs. The product equals 05's
    `expected_product.xyz` (amine H swapped versus 04). `planar_pair_set_bool` is True. This is
    the nMAP behaviour TJ R2 "A" asks to flag. Both 04 and 05 report the junction (C4, N) with
    sign 0 (the ring is planar).
  - **07 eta-adapted** (mission R18):
    - (a) The literal request (template delete {2,3,5}, with template 5 paired) is refused at
      `GraftSpec` construction (`ValidationError`: alignment ⊆ keep, ADR-0005).
    - (b) The eta request: template delete {2,3} (1-based), pairs (1,1), (4,2), (5,3),
      `fragment_delete` []. Product = template atoms 1, 4, 5, 6 (C, C, H, O), then incoming 4, 5
      (N, Cl). Expected coordinates: C (0,0,0), C (0,0,1), H (1,1,0), O (0,0,2), N (0,1,1),
      Cl (1,0,1), within 1e-6. Resolve measured exactly this; RMSD 6e-16.
    - nMAP's "keep a paired incoming atom" case is inexpressible under TJ R1 "B" (paired atoms
      always dropped); overlap is tested by the hand-built clash case below.

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

**Score: 9/10.** Every rule is normative and has an expected value. The contact factor and the
junction rule were measured on M1 by resolve (mission HF-5, HF-8); slice 06 asserts the M1
values, not this slice.

## Mini-requirements

1. **CH3Cl → CH3F, hand-built.**
   - Template: CH3Cl.
   - Fragment: CH3F built in the template frame, then moved by a known rigid motion.
   - Pairs: C and the three H. Template delete: Cl.
   - Product: [C, H, H, H, F], with the template coordinates `==` the input floats and F within
     1e-10 Å of its pre-motion position.
   - `index_map` exact; RMSD ≤ 1e-10.
2. **Product order with `fragment_delete`:** a fragment with 6 atoms, pairs on 3 and
   `fragment_delete` on 1. The appended atoms are the remaining 2 in ascending order;
   `index_map` exact.
3. **Charge:**
   - the spec's charge and multiplicity land on the product;
   - an odd-electron/multiplicity-1 spec raises `ValidationError` (parity);
   - `whole_input_charge_sum_holds_bool` is True for (0, 0 → 0) and False for (+1 template,
     −1 fragment → +1 product).
4. **Errors:**
   - out-of-range template index → `GraftInputError` with `__cause__` a `ValueError` (R14);
   - out-of-range fragment index;
   - active atom deleted; core atom deleted (core ⊄ keep is a `ValidationError` at the spec,
     tested in 02, so test an active atom here);
   - element mismatch in a pair;
   - non-empty fragment `active_atom_indices`.

   Each raises `GraftInputError` with the offending indices in the message.
5. **Clash:** an appended atom placed 0.3 Å from a kept template atom raises
   `GraftClashError` with `.i`, `.j` and `.distance_angstrom` set. At 0.6 Å it raises nothing,
   and that pair is in `close_contacts`.
6. **Contacts:** a hand-built case with one non-source pair inside 1.3 × Σr_cov and one outside.
   Only the first is recorded; junction bonds are never contacts.
7. **Junctions:**
   - a hand-built non-planar junction gives sign +1, and reflecting the appended atom through
     the (t, n1, n2) plane gives −1 (`junction_volumes` directly);
   - a junction atom with fewer than 2 kept neighbours gives `None`;
   - lists are sorted.
8. **Vectors 04, 05 and 07 (a)/(b)** as specified above.
9. **Imports:** extend the slice 03 import test with `eta_rxncat.mapping.graft` and
   `eta_rxncat.mapping.report`. Still no `rdkit` loaded at import.
10. **Kept coordinates are bitwise:** for every vector and hand case,
    `product.coordinates[k] == template.coordinates[keep[k]]` element for element (Python float
    equality).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read slice 02/03 code.
- [x] Task 2: `report.py`, then `graft.py`; export `graft` and the report helpers from `eta_rxncat.mapping`.
- [x] Task 3: `tests/unit/mapping/test_graft.py`, `tests/unit/mapping/test_report.py`; required checks.
- [x] Task 4: commit; updater (node `eta_rxncat_mapping`; no glob change).

## 4. The Negative Space (Constraints)

- **DO NOT** infer charge or multiplicity, or copy the template's.
- **DO NOT** move, round or recompute kept template coordinates.
- **DO NOT** raise on a close contact; raise only below `min_distance_angstrom`.
- **DO NOT** import RDKit at module level anywhere in `eta_rxncat.mapping`.
- **DO NOT** run any M1 file in this slice (slice 06 owns every M1 check; mission R20(a)).
- **DO NOT** import `eta_rxncat.thermo`; **DO NOT** read Eta_Scripts or nMap.

## Proof contract

- [ ] `uv run pytest tests/unit/mapping -q` passes; the proof names each mini-requirement's test.
- [ ] Vectors 04, 05 and 07(b) match at 1e-6 Å (max deviation printed), and 07(a) is refused.
- [ ] The import test passes with `graft` and `report` included.
- [ ] The required checks exit 0.

## Source material

- Mission SPEC §5 "Contracts", "Algorithms" G1–G8, report helpers; R1, R10, R14–R18, CR-01…CR-11.
- `NMAP_BEHAVIOUR_SPEC.md` §5–§9 (approved clean-room document).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.3 (`superpose`, errors, the vector copy and loader)
