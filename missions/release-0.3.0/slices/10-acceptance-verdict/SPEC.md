---
id: OPR.0.3.0.10
slice: 10-acceptance-verdict
mission: release-0.3.0
status: active
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "After TJ's Phase 3 promotion, rerun every fixture on both recipes on fresh stores with ETA_RXNCAT_ACCEPTANCE=1 and zero skips, record the regression, accuracy and SMILES-confirmation verdicts, bump the version to 0.3.0 and derive the final README claims."
depends_on: [OPR.0.3.0.9]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", docs/prd/v0.3.0/ACCEPTANCE_RESULT.json, README.md, tests/unit/test_identity.py, pyproject.toml, src/eta_rxncat/__init__.py, uv.lock, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.3.0 acceptance verdict after TJ's Phase 3 promotion

## Intent

After TJ has promoted the candidates, confirmed the T1/T2 SMILES and written the reference values,
rerun every fixture on both recipes on a fresh store with `ETA_RXNCAT_ACCEPTANCE=1` and zero skips,
record the regression, accuracy and confirmation verdicts in `ACCEPTANCE_RESULT.json`, bump the
version to 0.3.0, and derive the README's final v0.3.0 claims from that record.

Context the builder needs:
- **Precondition (R22), checked first, never acted on:** these exist in `tests/fixtures/v0.3.0/`
  (`ls`; promoted files are readable): `hf1_butane.{xtb,uma}.json`,
  `hf2_diels_alder.{xtb,uma}.json`, `e2e5_t1.{xtb,uma}.json`, `e2e5_t2.{xtb,uma}.json`,
  `e2e5_smiles.json`, `reference_values.json` (TJ's promotion of the R46 candidate, or his own
  file); and the mission SPEC's trade-off log has resolve's
  promotion R-row listing them with sha256. If anything is missing, stop and report to the lead:
  the slice does not start. If TJ corrected a SMILES, resolve has compiled a rework slice that runs
  before this one; do not edit inputs here.
- Q5 "A" bounds (both recipes, fresh store, same device): class of the lowest record exact; σ and g
  of every matched record exact; |ΔE| ≤ 1e-5 Eh; G/ΔG/ΔG_r ≤ 0.05 kcal/mol; weights ±0.02; records
  matched by class and RMSD ≤ 0.125 Å with H (unmatched → fail); T1's planar point E within 1e-5
  Eh. Accuracy (R43, TJ's reference level ωB97M-V/def2-TZVPD//B3LYP/6-31G**; like for like per
  R47/R48): UMA HF1 `hf1.dG_gauche_anti` (per conformer) within 0.5 of the `gate: true` value, HF2
  `dG_r_lowest_records` at 1 M within 2.0 of the `gate: true` `hf2.dG_r` (never the ensemble
  ΔG_r); the compared records' σ equal `reference_species` σ, else `fail`; the gate flags are read
  from the promoted file; deltas against both tables
  (ωB97M-V and B3LYP/6-31G**) reported for both recipes; xtb `reported`; a quantity with no gating
  entry `reported`; `hf1.gauche_population` always `reported`. The reference file is the
  advisor's values placed by TJ; it is read, never edited.
- R26: any gated check that fails, fails this slice; the result goes to the lead (who raises it to
  TJ). `known_limits` holds only reported deviations and the Q-E5 escalation proposal.
- Fixtures under `tests/fixtures/` are TJ's and may be read; candidates may not.

- **Reader rule (mission R50, binding):** drop-path failures are cached as COMPLETED rows with
  payload `{failed_reason, message}`. Any code here that reads a stage payload from the store or a
  runner result checks `failed_reason` first; such a payload is a failure — count and report it
  (species, stage, reason), never use it as a result.
- R50: keep slice 09's `failures` counts and its R50 `known_limits` line in the rewritten record.

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

**Score: 9/10.** Fully specified; the outcome depends on TJ's promoted values and the runs.

## Mini-requirements

1. Precondition check as above, quoted in the proof.
2. Acceptance runs with `ETA_RXNCAT_ACCEPTANCE=1`, fresh stores, scratch candidate dir:
   `UV_PROJECT_ENVIRONMENT=.venv-accept-opt ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m
   "e2e and not mlip_uma" tests/e2e` and `UV_PROJECT_ENVIRONMENT=.venv-accept-uma
   ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m "e2e and mlip_uma" tests/e2e`, each exit 0
   with zero skips, zero `pending_*`.
3. `docs/prd/v0.3.0/ACCEPTANCE_RESULT.json` rewritten from this run: every regression `pass`,
   accuracy `pass` (UMA) or `reported` (xtb), `smiles_confirmation: confirmed`, T1/T2 tier gates
   `pass`, metrics per stage, devices, the fixture sha256s it compared against, and `accuracy`
   per fixture with `gating_level` and both levels' deltas.
4. Version 0.3.0 (where v0.2.0 set its version) and README v0.3.0 claims derived from the record;
   derivation tests updated.

## 3. Implementation Plan (Task List)

- [ ] Task 1: precondition check; stop if unmet.
- [ ] Task 2: both acceptance runs; merge record.
- [ ] Task 3: version, README, tests; commit; ledger updater; required checks; remove scratch.

## 4. The Negative Space (Constraints)

- **DO NOT** start without the precondition; **DO NOT** edit inputs or fixtures.
- **DO NOT** loosen a bound, widen a window, or move a gated failure into `known_limits`.
- **DO NOT** read candidates; **DO NOT** reuse a populated store for the verdict run.

## Proof contract

- [ ] Precondition: `ls tests/fixtures/v0.3.0/` output and the promotion R-row quoted.
- [ ] Both acceptance commands exit 0 with 0 skips (pytest summary quoted).
- [ ] The record shows `pass`/`reported`/`confirmed` only, no `pending_*`, and the T2 UMA
  ΔG_rxn(1 M) inside (−42, −20).
- [ ] `git diff --stat Start..HEAD -- tests/fixtures tests/candidate_outputs` is empty.
- [ ] README derivation tests pass; required checks exit 0.

## Source material

- Mission §5 R50–R52 (replan 3); R10, R18, R22, R26, R42, R43, R46–R48, "Test tiers and tolerances"; TJ Q5, Q-E5.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.9 (record) and the Phase 3 gate (TJ; resolve's promotion R-row)
