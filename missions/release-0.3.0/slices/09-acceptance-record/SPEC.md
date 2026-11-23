---
id: OPR.0.3.0.9
slice: 09-acceptance-record
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Run HF1, HF2, T1 and T2 on both recipes in the named acceptance envs and write docs/prd/v0.3.0/ACCEPTANCE_RESULT.json with per-stage metrics and pending verdict states, deriving the README v0.3.0 claims from it, with no dependence on TJ acting first."
depends_on: [OPR.0.3.0.12]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.3.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.3.0 acceptance record (pre-promotion) and README derivation

## Intent

Run every v0.3.0 fixture (HF1, HF2, T1, T2) on both recipes in the named acceptance environments,
write `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json` with per-stage benchmark metrics and the current
regression/accuracy/confirmation states (`pending_*` allowed), and derive the README's v0.3.0 claims
from it — a slice whose PASS does not depend on TJ acting first.

Context the builder needs:
- TJ Q4 "C": benchmark metrics go in the acceptance record. The record follows the v0.2.0
  `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json` conventions (`commit_sha`, `run_at_utc`, `hardware`,
  `commands`, `logs`, `known_limits`, `evidence`). README claim tests live in
  `tests/unit/test_identity.py` (scaffold node); extend them there.
- R22: this slice is **before** the Phase 3 gate. `pending_promotion`, `pending_reference` and
  `pending_confirmation` are expected values here. The verdict run with `ETA_RXNCAT_ACCEPTANCE=1` is
  slice 10, after TJ promotes.
- R26: `known_limits` lists reported deviations only (GFN2 vs TJ's T2 window and vs the HF2/HF1
  references) and, where GFN2 cannot carry a tier, the Q-E5 proposal that MACE/UMA/OMol25
  become standard (TJ: "Q5. C, if it turns out MACE, UMA, or OMol25 are needed then they should
  become standard."). A gated failure is never a known limit; it fails the run. One fixed
  `known_limits` line (mission R47): "accuracy compares per-conformer quantities; our G is Grimme
  quasi-RRHO (ω₀ 100 cm⁻¹), the reference pure RRHO (≤ 0.01 kcal/mol on these Δ values per its
  README); the ensemble ΔG_r differs from the per-conformer ΔG_r by `dG_r_ensemble_minus_lowest`
  (reported)."
- R46–R48: TJ's reference exists only as the candidate until TJ promotes it, so `accuracy.verdict`
  here is `pending_reference`. The deltas are the R48 quantities like for like: HF1 per conformer,
  HF2 `dX_r_lowest_records` (never the ensemble ΔG_r), each with the σ check of R47.
- The acceptance driver lives at `tests/e2e/test_accept_v030.py` (species-runner node; **not**
  `tests/acceptance/**`, which belongs to the engines node, R11).
- The E2E tests write candidates; this slice must not rewrite the committed candidates. Point the
  acceptance driver's candidate output at a scratch directory (`ETA_RXNCAT_CANDIDATE_DIR`, default
  the repo path) so the record run never touches the committed files.

- **Reader rule (mission R50, binding):** drop-path failures are cached as COMPLETED rows with
  payload `{failed_reason, message}`. Any code here that reads a stage payload from the store or a
  runner result checks `failed_reason` first; such a payload is a failure — count and report it
  (species, stage, reason), never use it as a result.
- R50: the record counts failures per fixture, species and stage (`failures`: reason → count) and
  `known_limits` carries: "a non-deterministic engine failure stays cached as a completed failure row
  until `invalidate`; it is not retried under the same key (R50)".

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

**Score: 9/10.** The record schema is fixed; runtime numbers are whatever the run measures.

## Mini-requirements

1. `tests/e2e/conftest.py`: honour `ETA_RXNCAT_CANDIDATE_DIR` (default
   `tests/candidate_outputs/v0.3.0/`).
2. `tests/e2e/test_accept_v030.py` (`e2e`, `acceptance`): aggregates the E2E results of one
   recipe into a per-recipe JSON under `$ETA_RXNCAT_ACCEPTANCE_OUT` (outside the repo).
   `tools/` or a test helper merges the two recipe files into `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json`
   (`record_schema: 1`): per `fixtures.<fixture>.<recipe>` — per-stage `wall_time_s`,
   `engine_calls`, `cache_hits`; `n_pool`, `n_kept`; `optimizer_steps_total`, `recovery_steps`;
   `device`; `regression` with deltas; `accuracy` = {`verdict` (`pass`|`fail`|`reported`|
   `pending_reference`), `gating_level: "wb97mv_def2tzvpd//b3lyp_631gss"`, `deltas` per level per
   quantity (both levels, R43; quantities per R47/R48)}; HF2 also `dG_r_ensemble_minus_lowest`;
   `smiles_confirmation` (T1/T2); 
   `incremental_solvation` (observed vs expected calls); `species_stage_cache` (HF2, T2); plus
   `commit_sha`, `run_at_utc`, `hardware`, `commands`, `logs`, `known_limits`, `evidence`.
3. A record-schema test (default suite): the committed record parses, has every fixture × recipe,
   every required key, and only allowed verdict values.
4. README "Features" and "Roadmap" v0.3.0 lines derived from the record (claims only about what the
   record shows: e.g. "conformer ensembles, quasi-RRHO 1 M thermochemistry, cached stage runner;
   regression pending TJ promotion"); `tests/unit/test_identity.py` asserts each README claim
   against the record.
5. Version stays as is (the release bump happens at the verdict, slice 10).

## 3. Implementation Plan (Task List)

- [ ] Task 1: env var, driver, merge helper, schema test.
- [ ] Task 2: run both recipes (`ETA_RXNCAT_CANDIDATE_DIR` and `ETA_RXNCAT_ACCEPTANCE_OUT` in
  scratch under TMPDIR) at the code commit; merge into the record; README; derivation tests.
- [ ] Task 3: commit (record + README + tests); ledger updater; required checks; remove scratch.

## 4. The Negative Space (Constraints)
- **DO NOT** set `ETA_RXNCAT_ACCEPTANCE=1` in this slice, or treat `pending_*` as a failure here.
- **DO NOT** rewrite or read the committed candidates; **DO NOT** write `tests/fixtures/`.
- **DO NOT** list a gated failure under `known_limits`.
- **DO NOT** claim in README anything the record does not show.

## Proof contract

- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and not mlip_uma"
  tests/e2e` and the `.venv-accept-uma` `-m "e2e and mlip_uma"` run exit 0, 0 skips, with
  scratch candidate and output dirs.
- [ ] `git diff --stat Start..HEAD -- tests/candidate_outputs tests/fixtures` is empty.
- [ ] The record has HF1, HF2, T1, T2 × {xtb, uma}, metrics per stage, and verdict values only from
  the allowed sets; the schema test passes.
- [ ] README derivation tests pass; required checks exit 0.

## Source material

- Mission §5 R50–R52 (replan 3); R4, R11, R22, R26, R43, R46–R48, "Contracts" (acceptance record); `docs/prd/v0.2.0/GPU_SMOKE_RESULT.json`;
  `tests/unit/test_identity.py`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.12 (order-free T1 derived block; regenerated T1 candidates; mission R55)
- OPR.0.3.0.8 (T1/T2)
