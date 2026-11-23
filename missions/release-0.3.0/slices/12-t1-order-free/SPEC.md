---
id: OPR.0.3.0.12
slice: 12-t1-order-free
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Make Tier 1's derived block order-free (class counts and sorted distinct SMILES instead of energy-ordered per-record lists) so GPU-noise swaps cannot fail the R54 regression, and regenerate the T1 candidates in a candidates-only commit before the Phase 3 gate."
depends_on: [OPR.0.3.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.3.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_e2e_helpers.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: make T1's derived block order-free, and regenerate the T1 candidates

## Intent

Remove the energy-ordered lists from T1's `derived` block (mission R55), so a GPU-noise swap of two
near-degenerate records cannot fail the R54 regression once TJ promotes the T1 candidates, and
regenerate `e2e5_t1.{xtb,uma}.json` before the Phase 3 gate.

Context the builder needs:
- The finding (audit 08, row `qitem-20261123092430-aefe9820`): T1 `derived.classes` and
  `derived.reperceived_smiles` are per-record lists in energy order, and R54 compares lists by index.
  On UMA the 6 T1 records alternate s-trans / s-cis-side in energy order, so swapping two neighbours
  fails regression although every record still matches (R18). HF1 already leaves `classes` out.
- Resolve checked the other derived blocks in the code (not the candidates): T2's only list is the
  constant window `[low, high]` from the fixture; HF1 and HF2 carry no per-record lists; and
  `e2e5_smiles.json` is keyed by species. None of them changes.
- Record matching (R18: class + RMSD ≤ 0.125 Å with H, a bijection) and every T1 gate stay exactly as
  they are. This slice changes only the shape of the derived block.
- Reader rule (mission R50, binding): any code here that reads a stage payload from the store or a
  runner result checks `failed_reason` first; such a payload is a failure — count and report it
  (species, stage, reason), never use it as a result.
- R23 commit order and the pathspec rule are binding (below).

**Seat rules for every v0.3.0 slice (self-contained; the mission SPEC is `missions/release-0.3.0/SPEC.md`):**
- Branch `feature/eta-rxncat-v0.3.0`, cut re-entrantly from Base `7993284`. One code commit per
  slice; record `Start` (HEAD when you begin) in your handoff.
- First command of the slice: `python3 .agents/scripts/hyper_codegraph.py index`. It must print
  `index: ok`; anything else stops the slice. The audit treats `code_graph.status != ok` as a
  finding. The code graph only widens the blast radius; it never narrows it.
- Ledger: only `hyper_ledger.py` / `hypergraph_updater.py`. Use `ensure-node --id <node>` on
  existing nodes and pass the **full** `--files` list (it replaces). `ensure-node --from-spec` no
  longer drops other slices' files (HACF v0.6.1 E5), but count the node's globs before and after
  anyway. Never edit `spec/compiled/architecture.yml` by hand. `eta_rxncat_engines` is not touched.
- Scratch: `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs). Remove
  temp clones, venvs and scratch directories at the end of each step.
- No `HACF-install.sh`, `HACF-uninstall.sh` or `hyper_migrate.py apply`. Ignore any "review it with
  hyper_migrate.py plan" line (known false positive). On OpenRig 0.7.21, `hyper_spec.py` and
  `hyper_migrate.py` warn "outside the pinned contract" and `hyper_spec.py proof` writes the proof
  natively: expected, note it in the proof, not a finding.
- Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git: every `git diff`,
  `git show`, `git log -p` over a range that contains a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`. Never write `tests/fixtures/`. `PRDs/` is read-only.
- Required checks (AGENTS.md), all exit 0 before the commit: `uv sync --locked`, `uv run ruff check .`,
  `uv run ruff format --check .`, `uv run mypy`, `uv run pytest`, and
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- Licence (TJ, verbatim): "I would prefer to keep ASE out as it would be a major core dependency.
  The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for DFT, MLIP,
  conf search can be copy left. Because they can be replaced with a new engine later. But the core
  remains." / "It's fine that the engine MACE pulls in ASE just not the core." No agent-made
  licence exception.
- A host fact that does not hold, a failed engine run, or a bound that measured noise breaks is
  stop-and-report to the lead with the output — never worked around, never a loosened tolerance.
- Never push, tag or open a PR. Author: "Thomas J. L. Mustard Ph.D." (repo-local git config).

## 1. The Confidence Mandate

**Score: 10/10.** A data-shape change in one test file, with the regression helper unchanged.

## Mini-requirements

1. `tests/e2e/test_e2e5_tier1_dimethoxybutadiene.py`: remove `classes` and `reperceived_smiles`
   from `derived`. Each record entry already carries its `class`; also put its `reperceived_smiles`
   on the record entry, where R18 matching pairs it. Add to `derived`, order-free:
   `class_counts` (`{"s-trans": n, "s-cis-side": m}`, ints, exact) and `reperceived_smiles_unique`
   (sorted list of distinct strings, exact). Every existing assertion and check (≥ 2 kept, both
   classes, s-trans lowest, the planar point, every record re-perceives to the input SMILES) is
   computed from the records as before.
2. Rule for every derived block (R55): a list in `derived` is either fixed by the fixture or sorted
   by a key independent of energy; never in record or energy order. Add a default-suite test in
   `tests/e2e/test_e2e_helpers.py` that `compare_derived` passes two T1-shaped payloads whose records
   are the same set in a swapped order, and fails when a `class_counts` value changes.
3. Regenerate the T1 candidates (R23): `e2e5_t1.xtb.json` and `e2e5_t1.uma.json` at this slice's C1.
   They supersede those of `1c06fc6`. T2, `e2e5_smiles.json` and the HF candidates (`e24777d`) are
   not regenerated: none of their derived blocks holds an energy-ordered list.

## 3. Implementation Plan (Task List)

- [x] Task 1: `python3 .agents/scripts/hyper_codegraph.py index` → `index: ok`.
- [x] Task 2: req 1 and req 2, with tests.
- [ ] Task 3: C1 on a clean tree (`git status --porcelain --untracked-files=no` empty); run T1 on both
  recipes at C1 (`-k tier1`), writing the candidates with `commit_sha = C1`.
- [ ] Task 4: H13 check as slice 07 (`git add -n tests/candidate_outputs/v0.3.0/` succeeds;
  `git diff --stat <C1>..<C2> -- . ':(exclude)tests/candidate_outputs'` prints nothing).
- [ ] Task 5: C2 = only `tests/candidate_outputs/v0.3.0/e2e5_t1.{xtb,uma}.json`, message
  `test(12-t1-order-free): candidates regenerated at <C1>`; ledger updater; required checks.

## 4. The Negative Space (Constraints)

- **DO NOT** change `regression.py` tolerances, the R18 matching, or any T1 gate.
- **DO NOT** regenerate T2, `e2e5_smiles.json` or the HF candidates.
- **DO NOT** read candidates (also not through git); **DO NOT** write `tests/fixtures/`.

## Proof contract

- [ ] Req 2 tests pass in the default suite.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and not mlip_uma"
  tests/e2e -k tier1` and `UV_PROJECT_ENVIRONMENT=.venv-accept-uma uv run --no-sync pytest -m
  "e2e and mlip_uma" tests/e2e -k tier1` exit 0 at C1 with 0 skips; the printed T1 line quoted.
- [ ] `git show --name-only --format=%s <C2>` lists exactly `e2e5_t1.xtb.json` and
  `e2e5_t1.uma.json` and names C1.
- [ ] Required checks exit 0 at C1.

## Source material

- Mission §5 R18, R23, R50, R54, R55; slice 08 spec (context only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.8 (T1/T2; its audit verdict stands)
