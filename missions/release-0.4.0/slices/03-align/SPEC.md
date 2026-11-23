---
id: OPR.0.4.0.3
slice: 03-align
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Create eta_rxncat.mapping with its errors and Horn-quaternion superpose that refuses degenerate pair sets and reports planarity, create the eta_rxncat_mapping ledger node, and prove alignment against a test-local SVD and clean-room vectors 01-03 and 06."
depends_on: [OPR.0.4.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["src/eta_rxncat/mapping/**", "tests/unit/mapping/**", tests/unit/test_package.py, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/mapping/test_align.py, tests/unit/test_package.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 quaternion superposition (mapping.align) and the mapping node

## Intent

Create `eta_rxncat.mapping` with its errors and the Horn-quaternion `superpose`, which refuses
degenerate pair sets and reports their planarity. Create the `eta_rxncat_mapping` ledger node.
Prove alignment against an independent test-local SVD and the clean-room vectors 01, 02, 03 and
06.

Context the builder needs:
- **Node not yet in the graph.** Create it, then move the glob out of scaffold, with the full list
  (read `architecture.yml` for scaffold's current list and drop only `src/eta_rxncat/mapping/**`):
  ```
  python3 .agents/scripts/hyper_ledger.py ensure-node --id eta_rxncat_mapping --dimension Module \
    --depends-on eta_rxncat_core,eta_rxncat_engines,eta_rxncat_optimize \
    --files 'src/eta_rxncat/mapping/**,tests/unit/mapping/**' \
    --associated-file src/eta_rxncat/mapping/__init__.py --description-file <file>
  python3 .agents/scripts/hyper_ledger.py ensure-node --id eta_rxncat_scaffold --files '<scaffold list minus src/eta_rxncat/mapping/**>'
  ```
  - The description stays ≤ 1800 characters: clean-room conserved-core mapper (Horn
    superposition, ordered graft surgery, core-frozen pre-relaxation), numpy, RDKit lazy, inputs
    `MolecularState` + `GraftSpec`, output `GraftResult`.
  - The scaffold description is unchanged (it is at 1975/2000).
  - Count both nodes' globs before and after, then run `python3 .agents/scripts/hyper_ledger.py validate`.
  - The edges to engines/optimize exist because slice 05's `relax.py` uses their interfaces
    (mission R8). There is no thermo edge (R5).
- **Errors (`src/eta_rxncat/mapping/errors.py`):** `MappingError(Exception)`, with subclasses:
  - `AlignmentError`;
  - `GraftInputError`;
  - `GraftClashError(i, j, distance_angstrom)` (stores the three attributes; a message naming them);
  - `CoreDisplacementError(atom, displacement_angstrom)` (same pattern).

  All are exported from `eta_rxncat.mapping`.
- **`src/eta_rxncat/mapping/align.py`** (numpy only):
  - `pair_set_shape(points) -> tuple[float, float]` returns `(rms_off_line_angstrom, rms_off_plane_angstrom)`.
    For the centred (k, 3) set with singular values s1 ≥ s2 ≥ s3, these are `sqrt((s2² + s3²)/k)`
    and `s3/sqrt(k)`.
  - `superpose(mobile, reference, weights=None, *, degenerate_tolerance_angstrom=1e-3) -> Superposition`:
    1. Inputs are converted to float64 (k, 3) arrays. A shape mismatch, k < 3, non-finite values,
       or weights that are not positive and finite or not of length k raise `AlignmentError`.
    2. Shape guard: if either set has `rms_off_line_angstrom <= degenerate_tolerance_angstrom`,
       raise `AlignmentError` (collinear or coincident; nMAP's crash/arbitrary-spin defect,
       mission CR-05).
    3. Centroids: weighted means (plain means when `weights is None`).
    4. Correlation M = Σ wᵢ (mᵢ − c_m)(rᵢ − c_r)ᵀ. Horn's 4×4 symmetric key matrix N from M.
       `numpy.linalg.eigh(N)`; q = the eigenvector of the largest eigenvalue.
    5. If λ_max − λ_second ≤ 1e-10·max(1, |λ_max|), raise `AlignmentError("rotation not unique")`.
    6. R is the rotation matrix of the unit quaternion q (det = +1 by construction; there is
       **no** reflection fix-up and no SVD).
    7. `rmsd_angstrom` = sqrt(Σ wᵢ ‖R(mᵢ − c_m) + c_r − rᵢ‖² / Σ wᵢ), computed from residual
       coordinates, never from eigenvalues.
  - `Superposition` is a frozen dataclass with `rotation` (3×3), `mobile_centroid`,
    `reference_centroid`, `rmsd_angstrom`, `mobile_shape` and `reference_shape` (the two
    `pair_set_shape` tuples), and `apply(coords) -> ndarray`: x′ = R(x − c_m) + c_r.
- **`src/eta_rxncat/mapping/__init__.py`** exports the errors, `superpose`, `pair_set_shape` and
  `Superposition`. Importing it loads no `geometric`, `torch`, `pyscf`, `fairchem` or `rdkit`
  (mission R9).
- **Clean-room vectors.**
  - Copy `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/test_vectors/01_rigid_recovery …
    07_delete_lists_and_order` (all seven directories, every file, byte-identical) to
    `tests/unit/mapping/data/cleanroom_nmap/`.
  - Verify each file's sha256 against the per-file list in
    `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/TRANSFER_LOG.md` (transfer 1).
  - Write `tests/unit/mapping/data/cleanroom_nmap/PROVENANCE.md` with:
    - origin path;
    - transfer 1, 2026-11-23T18:44:06Z, "approved by room-checker (rows 2df20f9f + 04f688a2)";
    - CHECKER_REPORT "Approved for transfer";
    - TJ Q1 (clean room);
    - the per-file sha256;
    - "1-based indices; converted to 0-based by the test loader";
    - "compare at 1e-6 Å (six-decimal files)".

  Slice 04 uses 04, 05 and 07. Read only the approved documents in that directory (mission R18;
  NMAP_BEHAVIOUR_SPEC.md §4, §9 describe the vectors).
- **Test-local reference** (mission R5): `tests/unit/mapping/_svd_reference.py` holds an
  independent SVD Kabsch (determinant-corrected) that returns R and the RMSD computed from
  residual coordinates. Never import `eta_rxncat.thermo` (N4). Resolve measured Horn vs this SVD:
  |ΔRMSD| ≤ 4.4e-15 Å and |ΔR| ≤ 2.0e-14 over 1000 random sets, so 1e-10 Å is honest.

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

**Score: 9/10.** The algorithm, the guards and the tolerances are fixed and measured. H-M4
(determinism of `eigh`) is the one host fact this slice verifies.

## Mini-requirements

1. **Known motion:** a random rotation (det +1) plus a translation of a random non-degenerate set
   is recovered; `apply(mobile)` equals `reference` within 1e-10 Å; RMSD ≤ 1e-10 Å.
2. **Random sets:** 1000 random pairs of sets, seeded `numpy.random.default_rng(20261123)`, with
   k drawn from 3–29.
   - Reject and redraw any set whose `rms_off_line_angstrom` < 0.1 Å, or whose key-matrix top
     gap < 1e-6.
   - det(R) = +1 within 1e-12 every time.
   - |RMSD − SVD-reference RMSD| ≤ 1e-10 Å.
   - max |R − R_svd| ≤ 1e-9.
3. **Mirror (non-coplanar):** a random non-coplanar set against its reflection gives RMSD > 1e-3 Å
   and det(R) = +1. Vector 03 (atoms 1–4 of `incoming.xyz` onto atoms 1–4 of `template.xyz`):
   RMSD = 0.750000 ± 1e-6 Å, and `apply(incoming)` equals `expected_product.xyz` rows 5–8 within
   1e-6 Å.
4. **Vectors 01 and 02 at alignment level:**
   - pairs from `request.json` (converted to 0-based);
   - RMSD ≤ 1e-6;
   - the moved unpaired incoming atom equals the last row of `expected_product.xyz` within 1e-6 Å
     (01: O at (1, 1, 1); 02: Cl at (0, 0, 1)).
5. **Refusals (vector 06):** `AlignmentError` for 1 pair, 2 pairs and 3 collinear pairs on its
   files. Also for: k = 2 random points, all-coincident points, shape mismatch, NaN, a zero weight
   and a negative weight.
6. **Weights:** with weights all 2.0, the result equals unweighted within 1e-12. A weighted case
   checks the weighted centroid and the weighted RMSD against a hand formula.
7. **H-M4:** `superpose` twice on identical inputs gives bitwise-identical `rotation` and
   `rmsd_angstrom` (`numpy.array_equal`).
8. **`pair_set_shape`:** a planar square gives off-plane 0 (≤ 1e-12) and off-line > 0. A line
   gives off-line ≤ 1e-12.
9. **Imports:** `tests/unit/test_package.py` gains a fresh-interpreter test. Importing
   `eta_rxncat.mapping`, `eta_rxncat.mapping.align` and `eta_rxncat.mapping.errors` adds none of
   `geometric`, `torch`, `pyscf`, `fairchem`, `rdkit` to `sys.modules`. Slices 04 and 05 add their
   modules to the same list.
10. **No `assert` in `src/eta_rxncat/mapping/`:** a test parses the package's `.py` files with
    `ast` and finds no `Assert` node (mission R7).
11. **Ledger:** the node exists with the edges and files above; scaffold no longer lists
    `src/eta_rxncat/mapping/**`; `hyper_ledger.py validate` is ok.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `src/eta_rxncat/mapping/__init__.py` (the scaffold placeholder) and `architecture.yml`.
- [x] Task 2: ledger ensure-node (new node + scaffold glob move); validate; count the globs.
- [x] Task 3: errors, align and `__init__`; copy the vectors and verify their sha256; write PROVENANCE.md.
- [x] Task 4: tests (`tests/unit/mapping/test_align.py`, `_svd_reference.py`, the vector loader `tests/unit/mapping/cleanroom.py`); required checks; commit; updater.

## 4. The Negative Space (Constraints)

- **DO NOT** import or modify `eta_rxncat.thermo` (N4); `thermo/_geometry.py` stays untouched.
- **DO NOT** fix up a reflection by flipping a sign; the quaternion gives det +1 by construction.
- **DO NOT** compute RMSD from eigenvalues.
- **DO NOT** edit the copied vector files; **DO NOT** read anything in `incoming/cleanroom-nmap/`
  beyond its approved documents; never Eta_Scripts or nMap.
- **DO NOT** use `assert` in library code.

## Proof contract

- [ ] `uv run pytest tests/unit/mapping/test_align.py tests/unit/test_package.py -q` passes; the proof lists the max |ΔRMSD| and |ΔR| measured over the 1000 sets.
- [ ] The vector copy: 33 files (seven directories; 06 has no request.json or expected product), sha256 all equal to TRANSFER_LOG transfer 1 (script output in the proof).
- [ ] `python3 .agents/scripts/hyper_ledger.py validate` is ok; `show` lists `eta_rxncat_mapping` with depends_on core, engines, optimize; scaffold's glob count dropped by exactly 1.
- [ ] The required checks exit 0.

## Source material

- Mission SPEC §5 "Algorithms" A1–A4, R5, R8, R9, R12, R16, R18, R19; HF-3, HF-9.
- `~/.hacf/eta-rxncat-hacf/incoming/cleanroom-nmap/NMAP_BEHAVIOUR_SPEC.md` §4 (approved).
- Horn, B. K. P., *J. Opt. Soc. Am. A* 1987, 4, 629 (the published method).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.2 (core contracts; `GraftSpec` tolerances are named there)
