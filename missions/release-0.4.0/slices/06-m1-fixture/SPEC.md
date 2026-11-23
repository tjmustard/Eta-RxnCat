---
id: OPR.0.4.0.6
slice: 06-m1-fixture
mission: release-0.4.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Land TJ's three M1 structures with provenance and the provisional M1 YAML with the stated-rule atom map, prove the pure graft by tier-D checks, pre-relax on xtb and UMA gated on TS1b_n connectivity and junction signs, and commit the three candidates for Phase 3."
depends_on: [OPR.0.4.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_mapping
parent: null
hacf_touches: ["tests/e2e/data/e2e5/**", tests/e2e/m1.py, "tests/e2e/test_m1_*.py", "tests/candidate_outputs/v0.4.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_m1_graft.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.4.0 Fixture M1 — graft cyclobutene onto TS1a_n, pre-relax, candidates

## Intent

Land TJ's three M1 structures byte-identical with provenance, plus the provisional M1 mapping YAML
carrying the atom map derived by the stated rule. Prove the pure graft by tier-D checks
(forming-core RMSD ≤ 0.10 Å). Pre-relax the graft with its core frozen on the xtb and UMA recipes,
gated on TS1b_n's connectivity and junction signs. Commit the three candidates in a
candidates-only commit for TJ's Phase 3 review.

Context the builder needs:
- **TJ, verbatim:**
  - "Q3. B" (M1 only);
  - "Q6. A" (forming-core RMSD ≤ 0.10 Å; graft regression 1e-10 Å; relaxed regression
    |ΔE| ≤ 1e-5 Eh and heavy-atom RMSD ≤ 0.01 Å);
  - "P1 A / P2 A";
  - "R1 B, R2 A";
  - "Q4. A but the files attached can be used as reference." (index fix 1: the constrained core
    `[1, 2, 3, 5]` replaces the spec's `[0, 2, 3, 4]`).
- **Files (mission R4).**
  - Extract `TS1a_n.xyz`, `6_cyclobutene.xyz` and `TS1b_n.xyz` from the `XYZ_FILES` literal
    (an annotated assignment, `XYZ_FILES: dict[str, str] = {…}`) of
    `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py`
    with `ast.parse` + `ast.literal_eval`. **Never execute the builder, anywhere** (N3).
  - Builder sha256 `26e923529370687f78dffccbfa6f613f1e7391d50c425432c5f600ff86acc8e2`, equal to
    its `MANIFEST.sha256` line.
  - Write them byte-identical (`str.encode()`) to `tests/e2e/data/e2e5/xyz/`, with these sha256
    (resolve measured):
    - `TS1a_n.xyz` `c43753744532f36b0a3ac77b6797e7442a9dd0ee246c84edf76a34ea5810f267`
    - `6_cyclobutene.xyz` `8b25312f3c3b4948c4d3d4de6cdd2396516147dc5fc52ed2d94f7a259ab4e990`
    - `TS1b_n.xyz` `677d570d68f4d51cdf2efb29474cb26751e617b811350f77bf532d4d6785a457`
  - Add three rows to the **existing** `tests/e2e/data/e2e5/SOURCES.md` table (no second
    SOURCES.md, N6): file, SI page and header energies **from each file's own header line**
    (TS1a_n S8; cyclobutene S7; TS1b_n S8), sha256. Add a sentence that these three are M1
    (v0.4.0) and were extracted the same way.
- **`tests/e2e/data/e2e5/m1_ts1a_n_to_ts1b_n.yaml`** (team-drafted, provisional per TJ Q-E3).
  Keys:
  - `template: xyz/TS1a_n.xyz`, `fragment: xyz/6_cyclobutene.xyz`, `reference: xyz/TS1b_n.xyz`;
  - `keep: [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15]`, `delete: [7, 16, 17]`;
  - `alignment_pairs: [[2, 0], [3, 3], [10, 4], [11, 9]]` (`[template, fragment]`);
  - `fragment_delete: []`;
  - `active_atom_indices: [0, 1, 2, 3, 4, 5]`;
  - `constrained_core: [1, 2, 3, 5]`, with a comment: index fix 1, TJ Q-E4 "A", in place of the
    spec's `[0, 2, 3, 4]`;
  - `product_charge: 0`, `product_multiplicity: 1`; template and fragment charge 0, multiplicity 1;
  - `graft_to_ts1b_n_map: [0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16, 7, 8, 17, 18, 19, 20]`
    (product index → TS1b_n index; resolve measured it by the rule below; the test re-derives it);
  - `map_rule: "mission R2: lexicographically smallest element-preserving isomorphism of the graft source graph onto TS1b_n's perceived graph; no coordinates"`.

  A loader in `tests/e2e/m1.py` builds the `GraftSpec` and the three `MolecularState`s (use
  `tests/e2e/fixtures.py: read_xyz`). It sets the template's `active_atom_indices`.
- **Map rule (TJ P2 "A", mission R2; N2: never minimise an RMSD to choose)**, in `tests/e2e/m1.py`:
  1. `report.perceive_bonds` on TS1b_n. `GraftResult.source_bonds` is the graft's graph.
  2. Build two RDKit mols (element atoms, all bonds single, `SetNoImplicit(True)`). Require equal
     bond counts, else stop-and-report.
  3. `TS1b_mol.GetSubstructMatches(source_mol, uniquify=False, useChirality=False, maxMatches=100000)`.
     Zero matches is stop-and-report.
  4. The map = `min(matches)` (tuple order).
  5. Also report `n_isomorphisms` (resolve measured 32) and, per distinct heavy-atom map, the
     forming-core RMSD (measured 0.0498 Å for two, 0.9637 Å for two), sorted by the heavy-map
     tuple.
- **Tier-D checks** (`tests/e2e/test_m1_graft.py`; no markers, so it runs in the default suite and
  writes nothing). Expected values were measured by resolve (mission HF-2…HF-8):
  1. `graft()` gives 21 atoms with TS1b_n's formula; `alignment_rmsd_angstrom` 0.11573 ± 1e-4.
  2. The re-derived map equals the YAML's `graft_to_ts1b_n_map` exactly.
  3. Forming-core `[1, 2, 3, 5]` RMSD to TS1b_n under the map (`report.core_rmsd_angstrom`) is
     **≤ 0.10 Å** (TJ Q6 "A"; measured 0.04976). Active `[0..5]` and full RMSD are reported
     (measured 0.04220 and 0.7794).
  4. `close_contacts` pairs == {(0, 15), (0, 17), (4, 16), (4, 20)} (measured 1.9598, 1.1218,
     1.9611, 1.1251 Å).
  5. `planar_pair_set_bool` is True. `junctions` are for (2, 15) and (3, 16), with signs as
     computed. Resolve measured −0.0006 Å³ for both, so sign 0 at tolerance 0.05: report, do not
     gate.
  6. TS1b_n's junction volumes under the map (`report.junction_volumes` on TS1b_n coordinates
     re-indexed by the map, with the graft's `source_bonds`) are nonzero (measured +0.8505 /
     −0.8505 Å³).

  If any measured value differs beyond its stated tolerance, stop and report (do not edit the
  expectation).
- **E2E pre-relaxation** (`tests/e2e/test_m1_relax.py`; markers `e2e`, `slow`, and `xtb` or
  `mlip_uma`, the v0.3.0 convention in `tests/e2e/conftest.py`):
  - Per recipe (`recipes("xtb")`, `recipes("uma")` from `tests/e2e/e2e_env.py`), build the
    engine as v0.3.0's E2E tests do. Call
    `relax_constrained_core(result.product, engine, GeometricOptimizer(), result.constrained_core_product_indices, options={"maxiter": 200})`
    (mission R6). There are no dihedral constraints.
  - **Gates (TJ P1 "A", R2 "A"):**
    - (g1) `CoreDisplacementError` not raised (core ≤ 1e-6 Å, `CORE_FREEZE_TOLERANCE_ANGSTROM`; H-M3; mission R26). Record the measured max core displacement (`core_max_displacement_angstrom`) in the candidate; resolve measured 4.19e-8 Å on xtb at maxiter 200;
    - (g2) `report.perceive_bonds(relaxed)` mapped through the map equals
      `report.perceive_bonds(TS1b_n)` as edge sets;
    - (g3) every graft junction's sign on the relaxed coordinates is nonzero and equals TS1b_n's
      sign under the map.
  - **Reported** (not gated): full, active and forming-core RMSD to TS1b_n; appended heavy-atom
    RMSD to their TS1b_n partners after forming-core superposition; `final_energy_hartree`;
    `n_steps`; `n_engine_calls`; `recovery_steps`; `wall_time_s`; core max displacement.
  - A gate miss is H-M5: the test still writes its candidate with `test_outcome` and
    `failed_checks` recorded (R56), then fails, and you stop and report to the lead with the
    output. It is not worked around.
  - The xtb run also writes `m1_graft.json`.
  - Run each recipe's command under coreutils `timeout 3600`. The env and command pattern is
    v0.3.0's: `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and xtb"
    tests/e2e/test_m1_relax.py`, then `.venv-accept-uma` with `-m "e2e and mlip_uma"`. Heavy-run
    host check before each. The UMA run uses the GPU.
- **Candidates** (`tests/candidate_outputs/v0.4.0/`, via `ETA_RXNCAT_CANDIDATE_DIR` as v0.3.0's
  E2E tests do; read `tests/e2e/candidates.py` and `conftest.py`):
  - `m1_graft.json`: `commit_sha`, `run_at_utc`, environment, the input sha256s, the spec, the
    product (symbols, coordinates, charge, multiplicity), `index_map`, `alignment_rmsd_angstrom`,
    `close_contacts`, `junctions`, the planarity fields, `source_bonds`, `graft_to_ts1b_n_map`,
    `map_rule`, `n_isomorphisms`, `heavy_map_forming_core_rmsd_angstrom` (a list sorted by map
    tuple), the forming-core, active and full RMSD, gate outcomes, `test_outcome`.
  - `m1_relaxed.<recipe>.json`: the same identity fields, the relaxed product, `final_energy_hartree`,
    the optimizer identity and options, the gates g1–g3 with their values, the reported RMSDs,
    the metrics, `test_outcome`.

  Every numeric key is unit-suffixed (R54). Every list is fixture-ordered or sorted (R55).
- **Ledger:** `eta_rxncat_mapping` gains the globs `tests/e2e/test_m1_*.py`,
  `tests/e2e/data/e2e5/m1_*.yaml`, `tests/e2e/m1.py` and `tests/candidate_outputs/v0.4.0/**`
  (full `--files` list: the slice 03 list plus these). `tests/e2e/**` stays in
  `eta_rxncat_species_runner` too (the overlap is stated in mission R8).
- **Commits:** C1 = code, data and the ledger with a clean tree. Run both E2E recipes at C1. C2 =
  only `tests/candidate_outputs/v0.4.0/*`, message "candidates produced at C1 <sha>"
  (ADR-0027). Never read the candidates back (not through `git show` either).

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

**Score: 9/10.** Every input, rule and expected tier-D value is pinned and measured. What a run
must show (H-M3, H-M5, H-M6) is gated or stop-and-report, not left to judgment.

## Mini-requirements

1. The three XYZ files are byte-identical, with the sha256 above. SOURCES.md has the three new
   rows. The builder is never executed (the proof shows the `ast` extraction command).
2. The M1 YAML and `tests/e2e/m1.py` (loader, map rule).
3. `tests/e2e/test_m1_graft.py` checks 1–6 pass in the default suite.
4. `tests/e2e/test_m1_relax.py` runs both recipes with zero skips. Gates g1–g3 pass on each, or
   it stops and reports (H-M5).
5. Candidates `m1_graft.json`, `m1_relaxed.xtb.json` and `m1_relaxed.uma.json` are written at C1
   and committed alone in C2.
6. The ledger globs are added; `hyper_ledger.py validate` is ok.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `tests/e2e/{conftest,e2e_env,fixtures,candidates,acceptance}.py`.
- [x] Task 2: extract the XYZ in scratch (`ast` only), verify the sha256, copy them; SOURCES rows; YAML; `m1.py`.
- [x] Task 3: tier-D tests; the E2E test; required checks; ledger ensure-node; commit C1 (clean tree).
- [ ] Task 4: host check → xtb E2E under `timeout 3600` → host check → UMA E2E under `timeout 3600`, both at C1 into the repo candidate dir; commit C2 with only the candidates.
- [ ] Task 5: updater; remove scratch.

## 4. The Negative Space (Constraints)

- **DO NOT** execute the 5-tier builder, or edit TJ's XYZ files.
- **DO NOT** pick or adjust the atom map by any RMSD (N2); **DO NOT** edit an expected value to make a test pass.
- **DO NOT** gate the full RMSD or add a numeric bound TJ did not set.
- **DO NOT** call `check_ground_state` on the relaxed graft, or call it a minimum.
- **DO NOT** read `tests/candidate_outputs/`, including through git; **DO NOT** write `tests/fixtures/`.
- **DO NOT** overlap a heavy run with another rig's heavy run.
- **DO NOT** open Eta_Scripts or nMap; TJ's 5-tier spec and builder literal are the only M1 sources.

## Proof contract

- [ ] `sha256sum tests/e2e/data/e2e5/xyz/{TS1a_n,6_cyclobutene,TS1b_n}.xyz` equals the three values above.
- [ ] `uv run pytest tests/e2e/test_m1_graft.py -q` passes; the proof prints the forming-core, active and full RMSD, contacts, junctions, `n_isomorphisms` and the heavy-map RMSDs.
- [ ] `timeout 3600 env UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and xtb" tests/e2e/test_m1_relax.py` and the `.venv-accept-uma` `-m "e2e and mlip_uma"` run each exit 0 with 0 skips. The proof gives the g1–g3 values, the wall time and the host checks.
- [ ] `git show --stat --format= <C2>` lists only `tests/candidate_outputs/v0.4.0/{m1_graft,m1_relaxed.xtb,m1_relaxed.uma}.json` (names only).
- [ ] The required checks exit 0 at C1; `hyper_ledger.py validate` is ok.

## Source material

- Mission SPEC §5 "Fixture M1", R1, R2, R4, R6, R8, R16, R20, R23; HF-1…HF-8; H-M3, H-M5, H-M6.
- `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Test_Suite_Specification.md` (Tier 3 "M1").
- `tests/e2e/` (v0.3.0 harness); ADR-0027.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.4.0.5 (`relax_constrained_core`)
- OPR.0.4.0.4 (`graft`, `report`)
