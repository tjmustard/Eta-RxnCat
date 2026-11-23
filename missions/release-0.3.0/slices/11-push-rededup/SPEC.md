---
id: OPR.0.3.0.11
slice: 11-push-rededup
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Re-dedup a conformer moved by the imaginary-mode push against the kept set with the existing proper-rotation rule, prove it with unit tests, and regenerate the Human Fixture candidates in a candidates-only commit before the Phase 3 gate."
depends_on: [OPR.0.3.0.7]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["src/eta_rxncat/orchestrator/**", "tests/unit/orchestrator/**", "tests/e2e/**", "tests/candidate_outputs/v0.3.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: re-dedup a pushed conformer against the kept set, and regenerate the HF candidates

## Intent

Make the species runner drop a conformer that the imaginary-mode push moved onto another kept
conformer (mission R53, superseding R52(1)), prove it with a unit test, and regenerate the Human
Fixture candidates so the Phase 3 set never contains the double-counted UMA cyclohexene.

Context the builder needs:
- The finding (slice 07 builder, row `qitem-20261123072034-b092d8bb`; numbers from that handoff, the
  candidates were not read): UMA HF2 cyclohexene keeps 4 records; record 0 (sources [0, 3, 7],
  recovery `tric`) and record 3 (source [52], recovery `tric`, `imag_mode_push`, `tric`) are the same
  half-chair — ΔG 0.000, ΔE 0.000 kcal/mol, φ(0-1-2-3) 14.0°, lowest frequencies 166.7/277.2 vs
  166.6/276.9 cm⁻¹, both σ 2, g 2. The ensemble G(cyclohexene) and ensemble ΔG_r are then low by
  ≈ RT ln 2 ≈ 0.41 kcal/mol; the gated per-conformer quantities (R47/R48) are unaffected. xtb HF2
  cyclohexene keeps 2 records (not inspected).
- Cause (resolve read `src/eta_rxncat/orchestrator/species.py`): `dedup` runs on the optimized
  geometries **before** the frequency stage; the push re-optimizes and moves a conformer; afterwards
  only `drop_mirror_partners` runs, which catches a pushed mirror image but not a pushed copy.
- Slice 06 is finished and its spec is not edited; this slice changes the runner code under the
  same node (`eta_rxncat_species_runner`). Slice 07's audit verdict stands for 07.
- The rule is the existing one (mission R3, ADR-0025 PROPOSED): proper-rotation RMSD over graph
  automorphisms, with H, at `rmsd_dedup_angstrom`. No new tolerance.
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

**Score: 9/10.** The cause is read from the code and the fix reuses the existing dedup rule; the open
point is whether UMA's and xtb's other cyclohexene records are distinct minima, which Task 4
measures and reports.

## Mini-requirements

1. `run_species`: after frequency, push and thermo, and **before** `drop_mirror_partners`, re-run
   `eta_rxncat.conformers.dedup` over the records' final geometries, visited by record G (ties →
   lower index). A record that matches an earlier survivor is dropped with reason
   `duplicate_after_push` (reported by its first `source_id`, R52(2)); the survivor is unchanged.
   No engine call, no store key and no stage row changes: a cached rerun is still 0 calls and the
   slice 06 tests pass unchanged. Without a push no pair can match (the geometries were already
   deduplicated), and a test proves the record set is then identical.
2. Unit tests (`tests/unit/orchestrator/`, default suite, fake engine/UFF): (a) a push that lands on a
   kept conformer → exactly one record survives, `dropped` has one `duplicate_after_push`, and
   G_ens equals the single-record value; (b) a push that lands on a new minimum → both kept;
   (c) no push → records and ensemble byte-identical to the pre-change behaviour.
3. `tests/e2e/derived.py`: `assert_no_duplicate_records(ensemble, smiles, options)` — no two kept
   records within `rmsd_dedup_angstrom` (proper rotation, with H, over automorphisms); called for
   every species in the HF1 and HF2 tests, and available to slice 08.
4. Cyclohexene characterization (both recipes, after the fix): for each kept record print ΔG and ΔE
   to the lowest, the ring torsions, the lowest two frequencies, the recovery steps, and the
   pairwise minimum RMSD (proper rotation, and mirror). Cyclohexene has one minimum family (the
   half-chair; g = 2 covers its mirror). If more than one record survives, report them to the lead
   with these numbers; two records with |ΔG| ≤ 0.01 kcal/mol and RMSD above the threshold is
   **stop-and-report** (a dedup-threshold question for resolve, never a changed tolerance here).
5. Regenerate the Human Fixture candidates (R23): all four (`hf1_butane.{xtb,uma}.json`,
   `hf2_diels_alder.{xtb,uma}.json`) at this slice's C1, so the Phase 3 set comes from one code
   commit; re-run the `reference_values.json` transcription (slice 07 req 2a) into the same
   directory (expected byte-identical). They supersede the files of `32ee699`. Report per
   fixture/recipe/species: n_kept, and the count of `duplicate_after_push`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: `python3 .agents/scripts/hyper_codegraph.py index` → `index: ok`.
- [ ] Task 2: runner change (req 1) + unit tests (req 2).
- [ ] Task 3: `assert_no_duplicate_records` (req 3) wired into the HF1/HF2 tests.
- [ ] Task 4: C1 on a clean tree; run HF1 and HF2 on both recipes at C1 (writes candidates with
  `commit_sha = C1`); the cyclohexene characterization (req 4); the transcription entry point.
- [ ] Task 5: H13 check as slice 07 (`git add -n tests/candidate_outputs/v0.3.0/` succeeds;
  `git diff --stat <C1>..<C2> -- . ':(exclude)tests/candidate_outputs'` prints nothing).
- [ ] Task 6: C2 = only `tests/candidate_outputs/v0.3.0/*`, message
  `test(11-push-rededup): candidates regenerated at <C1>`; ledger updater; required checks.

**Commit order (R23):** C1 code on a clean tree (`git status --porcelain --untracked-files=no`
empty) → E2E at C1 writes candidates → C2 candidates only. Verify with `git show --name-only
--format=%s <C2>`. Never open, cat, diff or show candidate contents.

## 4. The Negative Space (Constraints)

- **DO NOT** add or change a tolerance (`rmsd_dedup_angstrom`, window, imag thresholds).
- **DO NOT** merge the dropped record's source ids into the survivor, or change any store key.
- **DO NOT** edit the slice 06 or 07 specs; **DO NOT** read candidates (also not through git);
  **DO NOT** write `tests/fixtures/`.

## Proof contract

- [ ] Unit tests (req 2) pass in the default suite; slice 06's orchestrator tests pass unchanged.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and not mlip_uma"
  tests/e2e -k "hf1 or hf2"` and `UV_PROJECT_ENVIRONMENT=.venv-accept-uma uv run --no-sync pytest
  -m "e2e and mlip_uma" tests/e2e -k "hf1 or hf2"` exit 0 at C1 with 0 skips.
- [ ] The cyclohexene characterization (req 4) and the per-species n_kept / `duplicate_after_push`
  counts (req 5) quoted.
- [ ] `git show --name-only --format=%s <C2>` lists `hf1_butane.{xtb,uma}.json`,
  `hf2_diels_alder.{xtb,uma}.json` (and `reference_values.json` only if its bytes changed, which
  is itself a finding) and names C1.
- [ ] Required checks exit 0 at C1.

## Source material

- Mission §5 R3, R23, R50, R52, R53; ADR-0025 (PROPOSED); slice 06 and 07 specs (context only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.7 (Human Fixtures; its audit verdict stands)
