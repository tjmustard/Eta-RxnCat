---
id: OPR.0.3.0.7
slice: 07-human-fixtures
mission: release-0.3.0
status: done
stage: wip
verified: "2026-11-23 against scaffold (hyper_scope slice create)"
created: "2026-11-23"
intent: "Run Human Fixtures 1 (n-butane) and 2 (butadiene + ethylene to cyclohexene, 1 M) end to end on the xtb and UMA recipes with the incremental-solvation counts, reference-values format and regression helpers, and commit the candidate outputs in a candidates-only commit."
depends_on: [OPR.0.3.0.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: audited
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.3.0/**", pyproject.toml, docs/prd/v0.3.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e, "-m", "not e2e"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Human Fixtures 1 and 2 end to end on both recipes, with incremental solvation and committed candidates

## Intent

Draft the HF1 (n-butane) and HF2 (butadiene + ethylene → cyclohexene, 1 M) inputs, the
reference-values format, and the E2E tests that run both recipes through the species runner, prove
the incremental-solvation counts, and write candidate outputs that are committed (TJ R1 "A") in a
candidates-only commit nobody reads back.

Context the builder needs:
- TJ Q1 "C": the team drafts HF1/HF2 and runs them into `tests/candidate_outputs/v0.3.0/` for TJ to
  promote. TJ's reference values arrived (mission R46, TJ verbatim "Send as my reference"): source
  `~/.hacf/eta-rxncat-hacf/incoming/tj-reference-b3lyp-20261123/`, `results.json` sha256
  `40fe7c7f5ac697815b4e78e403ae1ec71731f7a82d925856b21597a59c97a35e`, `README.md` sha256
  `3933153bd3c750daf717b2ee5b35d0584fb539cc93e9fcc42c48503b751186be`. That approves the values,
  not a seat writing `tests/fixtures/`: this slice transcribes them into a **candidate**.
- Like for like (mission R47, R48): the reference is one conformer per species (σ by hand, no
  degeneracy, pure RRHO). Our per-record G carries σ and no g; G_ens carries g. So accuracy reads
  per-conformer quantities only: HF1 `hf1.dG_gauche_anti` (gate) and HF2 `dG_r_lowest_records` at
  1 M (gate) — never the ensemble ΔG_r, which is ≈ 0.39 kcal/mol more negative (cyclohexene g = 2,
  butadiene s-cis-side records).
  TJ Q2 "A": recipe `xtb` = `xtb_subprocess`/`gfn2` for every stage; recipe `uma` =
  `uma_direct`/`uma-s-1p2p1` with high-precision `inference_settings`. TJ R2 "A": butane ΔG(gauche −
  anti) **per conformer**, no RT ln 2. TJ R1 "A": candidates committed on the branch.
- Envs (AGENTS.md "Engine tests", updated in slice 04): `.venv-accept-opt` (`--extra
  opt-geometric`, xtb binary `~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`) and
  `.venv-accept-uma` (`--extra gpu --extra mlip-uma --extra opt-geometric`). The build seat creates
  and syncs them; the audit runs them with `uv run --no-sync`. UMA uses the host's existing HF login;
  skip with a stated reason when absent (fails under acceptance). Never write the token anywhere.
- xtb ALPB: the engine's keyed `alpb_state` defaults to `gsolv` (1 M gas → 1 M solution); write it
  explicitly. PySCF PCM: `Solvation(model="pcm", solvent="toluene")`, `options={"pcm_method":
  "C-PCM"}`; `toluene` is in `engines/pyscf_gpu_cpu/solvents.py` (2.3741).
- R23 commit order and the pathspec rule are binding for this slice (below).

- **Reader rule (mission R50, binding):** drop-path failures are cached as COMPLETED rows with
  payload `{failed_reason, message}`. Any code here that reads a stage payload from the store or a
  runner result checks `failed_reason` first; such a payload is a failure — count and report it
  (species, stage, reason), never use it as a result.
- **Standard state (mission R51):** add `checked_reaction_free_energy(spec, ensembles, config)` to
  `tests/e2e/derived.py`: every record of every ensemble must have `thermo.config == config` (whole
  model), else `ValueError` naming the species; then it calls `reaction_free_energy`. Every HF2 ΔG_r
  (gas and solvated) goes through it. Unit tests: an ensemble at `standard_state_mol_l=2.0` and one
  at another pressure are both refused.

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

**Score: 9/10.** H5 and H8 can stop the slice; the specification is otherwise complete.

## Mini-requirements

1. Inputs (provisional per TJ Q-E3), `tests/e2e/data/hf1_butane.yaml` (`CCCC`, 0, 1, `n_embed` 50,
   seed 42) and `tests/e2e/data/hf2_diels_alder.yaml` (butadiene `C=CC=C`, ethylene `C=C`,
   cyclohexene `C1CC=CCC1`, all 0/1; reaction butadiene + ethylene → cyclohexene). A loader in
   `tests/e2e/fixtures.py` validates them.
2. `tests/e2e/data/reference_values.example.json` + loader `tests/e2e/reference_values.py`
   (R43: TJ set the reference level — "ωB97M-V/def2-TZVPD//B3LYP/6-31G**: ωB97M-V/def2-TZVPD single
   points on B3LYP/6-31G** geometries, with B3LYP/6-31G** RRHO thermal corrections. BOTH tables
   (B3LYP/6-31G** and ωB97M-V) are reported, and ONLY the ωB97M-V table gates." The advisor
   computes the values; no seat computes or writes `tests/fixtures/v0.3.0/reference_values.json`).
   Format `schema: 1`, `reference_species` (per species id: `sigma`, `conformer`, `thermo_model`),
   `entries`, each: `quantity` ∈ {`hf1.dE_gauche_anti`, `hf1.dH_gauche_anti`,
   `hf1.dG_gauche_anti`, `hf1.gauche_population`, `hf2.dE_r`, `hf2.dH_r`, `hf2.dG_r`}; `level` ∈
   {`wb97mv_def2tzvpd//b3lyp_631gss`, `b3lyp_631gss`}; `method` (text); `value`; `unit`
   (`kcal/mol`|`percent`); `standard_state` (`1 atm`|`1 bar`|`1 M`|`n/a`); `temperature_k`;
   `provenance` (text: who computed it, program/version, input/output references); `gate: bool`.
   Loader rules: `gate: true` allowed only on `wb97mv_def2tzvpd//b3lyp_631gss` (else reject); one
   entry per (quantity, level) (else reject); conversion to 1 M (and 1 bar ↔ 1 atm by RT ln
   1.01325); `hf1.gauche_population` is always `reported`, even with `gate: true`. The example file
   holds one entry per level per quantity with placeholder numbers, every entry marked
   `"provenance": "EXAMPLE — not a reference"`; the loader refuses any entry with that provenance
   when it loads `tests/fixtures/v0.3.0/reference_values.json` (tested). Unit-tested in the default suite.
2a. TJ's reference as a candidate (mission R46; R23 order):
   - Copy `results.json` and `README.md` byte-identical from the source directory into
     `tests/e2e/data/reference/tj-reference-b3lyp-20261123/`, plus a `SOURCES.md` you write: origin
     path, `sha256sum` of every file in the source directory, who computed it (the advisor's helper,
     PySCF 2.15.1, geomeTRIC 1.1.1), and TJ's verbatim "Send as my reference" (2026-11-23). Scripts,
     XYZs and logs are not committed, only listed with sha256.
   - `transcribe_tj_results(path) -> dict` in `tests/e2e/reference_values.py`: a fixed table from
     results.json key paths to (quantity, level). Block `GATING REFERENCE` → level
     `wb97mv_def2tzvpd//b3lyp_631gss`; block `B3LYP/6-31G** (RRHO)` → `b3lyp_631gss`. Keys:
     `butane_gauche_minus_anti_kcal_mol.{dE, dH_298, dG_298}` → `hf1.{dE,dH,dG}_gauche_anti`;
     `butane_gauche_population_percent_298K.from_dG` → `hf1.gauche_population` (`percent`, `n/a`);
     `diels_alder_kcal_mol.{dE_r, dH_r_298}` → `hf2.{dE_r,dH_r}` (`n/a`);
     `diels_alder_kcal_mol.dG_r_298_1M` → `hf2.dG_r` (`1 M`). `temperature_k` from
     `temperature_K`. Floats are copied as parsed: no arithmetic, no rounding. `gate: true` only on
     `hf1.dG_gauche_anti` and `hf2.dG_r` at the ωB97M-V level (mission R48); every other entry
     `gate: false`. `provenance` per entry: "TJ-approved 2026-11-23 'Send as my reference'; advisor
     helper, PySCF 2.15.1 / geomeTRIC 1.1.1; results.json sha256 <full>; key <block>/<path>".
     `reference_species`: σ from `symmetry_numbers_used` (butane_anti 2, butane_gauche 2,
     butadiene_strans 2, ethylene 4, cyclohexene 2), one conformer each, `thermo_model: "RRHO"`.
     Not transcribed: the quasi-RRHO and D3(BJ) side blocks, the 1 atm ΔG_r, butadiene gauche −
     s-trans (R49).
   - Default-suite test: the committed results.json sha256 equals R46's value; the transcription
     passes the fixtures-mode loader; each value equals its key's float exactly; and, as an
     independent check against the relayed figures, rounding to 3 dp (population 1 dp) gives:
     ωB97M-V HF1 ΔE 0.609, ΔH 0.658, ΔG 0.685, population 38.6, HF2 ΔE_r −47.055, ΔH_r −42.712,
     ΔG_r(1 M) −30.922; B3LYP HF1 ΔH 0.870, ΔG 0.897, HF2 ΔH_r −38.311, ΔG_r(1 M) −26.522. A
     mismatch is stop-and-report, never an edited value.
   - A small entry point (e.g. `python -m tests.e2e.reference_values transcribe <results.json> <out>`)
     writes the candidate `tests/candidate_outputs/v0.3.0/reference_values.json` after C1; it goes
     in C2 with the other candidates. Never read it back: the test above proves it in memory.
3. `tests/e2e/conftest.py`: markers `e2e` (new, registered in `pyproject.toml` markers and deselected
   by default addopts) plus `xtb` or `mlip_uma` + `slow`; a `recipes` fixture; a fresh store per test
   under `tmp_path`; the candidate directory `tests/candidate_outputs/v0.3.0/` (write only).
4. `tests/e2e/derived.py`: HF1 torsion class (C1–C2–C3–C4 = atoms 0–3, |φ| > 120° anti, else
   gauche); ΔE/ΔH/ΔG(gauche − anti) per conformer = lowest gauche record − lowest anti record; gauche
   population = summed weights of gauche records; `class_dG_gauche_anti` = −RT ln(P_g/P_a). HF2
   (mission R47): `dX_r_lowest_records` (X ∈ E, H, G; G at 1 M) = X(lowest-G cyclohexene record) −
   X(lowest-G s-trans butadiene record) − X(lowest-G ethylene record), from per-record values;
   `dG_r_ensemble_minus_lowest` = ensemble ΔG_r(1 M) − `dG_r_lowest_records`. Accuracy helper:
   compares a quantity only after checking each compared record's σ against `reference_species`
   (mismatch → `fail` for UMA; `sigma_mismatch` beside the reported xtb delta). Unit-tested,
   including a synthetic cyclohexene with g = 2 whose ensemble and per-conformer ΔG_r differ by
   exactly −RT ln 2.
5. `tests/e2e/test_hf1_butane.py` (per recipe): run, assert one anti record (σ 2, g 1) and one gauche
   record (σ 2, g 2), lowest record 0 imaginary modes; write `hf1_butane.<recipe>.json` (§5
   candidate schema plus the derived block); then regression if `tests/fixtures/v0.3.0/hf1_butane.<recipe>.json`
   exists, else record `pending_promotion`; accuracy if `reference_values.json` exists — UMA gated
   0.5 kcal/mol against the `gate: true` entry of the same kind; deltas against **every** entry of
   both levels reported for both recipes; xtb never gated — else `pending_reference`. A quantity
   with no gating entry is `reported`.
6. `tests/e2e/test_hf2_diels_alder.py` (per recipe): three species, `ReactionSpec`; ΔE_r, ΔH_r,
   ΔG_r at 1 atm and 1 M with the conversion term; butadiene holds ≥ 1 s-trans and ≥ 1 s-cis-side
   record (atoms 0-1-2-3, |φ| ≤ 90°), cyclohexene g = 2. Incremental rerun into the same store:
   - xtb recipe: + ALPB(toluene, `alpb_state: gsolv`) single point per kept record of every species
     → 0 upstream calls, exactly Σ n_kept ALPB calls; ΔG_solv per species as mission R27; solvated
     ΔG_r(1 M) reported.
   - both recipes: + one `pyscf_gpu_cpu` `pbe0`/`def2-svp` PCM(toluene, C-PCM) single point on
     ethylene's lowest record, CPU device → exactly 1 call, 0 upstream; mechanism only (no ΔG_solv).
   - UMA ΔG_solv is `n/a`.
   - upstream rows keep their keys and `created_at_utc`.
   Writes `hf2_diels_alder.<recipe>.json` (ensemble ΔE_r/ΔH_r/ΔG_r, `dX_r_lowest_records`,
   `dG_r_ensemble_minus_lowest`); σ asserted: s-trans butadiene 2, ethylene 4, cyclohexene 2.
   Regression as HF1 (ensemble and per-conformer quantities). Accuracy (R47/R48): UMA
   `dG_r_lowest_records` at 1 M within 2.0 of the `gate: true` `hf2.dG_r`; `dE_r`/`dH_r` per
   conformer reported; both levels reported; the ensemble ΔG_r is never compared to the reference.
7. Regression helper (`tests/e2e/regression.py`, unit-tested on synthetic payloads): match records
   by class and RMSD ≤ 0.125 Å with H over automorphisms (proper rotation); unmatched → fail; σ and g
   exact; |ΔE| ≤ 1e-5 Eh; G/ΔG ≤ 0.05 kcal/mol; weights ±0.02; same device required.
8. Under `ETA_RXNCAT_ACCEPTANCE=1` every `pending_*` fails (the existing conftest hook plus an
   explicit `pytest.fail` in the helpers).

## 3. Implementation Plan (Task List)

- [x] Task 1: H8 — in `.venv-accept-uma`: `pyscf.dft.libxc.parse_xc("pbe0")` succeeds and
  `pyscf.gto.M(atom="H 0 0 0; H 0 0 0.74", basis="def2-svp")` builds; `xtb … --alpb toluene` exit 0.
  Record.
- [x] Task 2: H5 (R10) — cache disabled (fresh store per run): butane gauche re-optimized from 3
  distinct pass-1 embeddings that converge to it, and from 3 displacements of 0.01 Å, on each recipe
  (UMA on cuda); record the spread of the lowest 3 frequencies and of G. Spread of G > 0.0167
  kcal/mol → stop and report to the lead.
- [x] Task 3: inputs, loaders, derived and regression helpers, the reference provenance copy and
  `transcribe_tj_results` (req 2a) + unit tests.
- [x] Task 4: E2E tests; run both recipes in their envs.
- [ ] Task 5: H13 — after C1 (below): `git add -n tests/candidate_outputs/v0.3.0/` succeeds and
  `git diff --stat <C1>..<C2> -- . ':(exclude)tests/candidate_outputs'` prints nothing; a denial
  or leak stops and reports.
- [ ] Task 6: commits per R23 (below); ledger updater; required checks.

**Commit order (R23):** (1) commit the code as C1 on a clean tree (`git status --porcelain
--untracked-files=no` empty); (2) run the E2E tests at C1 for both recipes, which write candidates
with `commit_sha = C1`, and write the candidate `reference_values.json` with the req 2a entry point; (3) commit C2 containing only `tests/candidate_outputs/v0.3.0/*`, message
`test(07-human-fixtures): candidates produced at <C1>`. Verify C2 with `git show --name-only
--format=%s <C2>`. Never open, cat, diff or show the candidate contents.

## 4. The Negative Space (Constraints)

- **DO NOT** read candidate files back (also not through git); **DO NOT** write `tests/fixtures/`.
- **DO NOT** gate xtb accuracy; **DO NOT** loosen a Q5 bound.
- **DO NOT** fold RT ln 2 into the gated HF1 quantity, or compare the ensemble ΔG_r (or apply an
  offset to it) against the reference (R47).
- **DO NOT** retype, round, convert or edit a transcribed reference value; **DO NOT** commit the
  source scripts, XYZs or logs.
- **DO NOT** run the E2E suite in the default `uv run pytest` (markers deselect it).

## Proof contract

- [ ] H5, H8, H13 results quoted with commands and numbers.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-opt uv run --no-sync pytest -m "e2e and not mlip_uma"
  tests/e2e -k "hf1 or hf2"` exit 0 at C1 with 0 skips.
- [ ] `UV_PROJECT_ENVIRONMENT=.venv-accept-uma uv run --no-sync pytest -m "e2e and mlip_uma"
  tests/e2e -k "hf1 or hf2"` exit 0 at C1 with 0 skips.
- [ ] The HF2 incremental assertions hold on both recipes (counts in the test output).
- [ ] Unit tests for the loaders, derived and regression helpers and the writer pass in the
  default suite.
- [ ] `git show --name-only --format=%s <C2>` lists exactly `hf1_butane.{xtb,uma}.json`,
  `hf2_diels_alder.{xtb,uma}.json` and `reference_values.json`, and names C1.
- [ ] The req 2a test output (sha256 match, exact-float and rounded-figure checks) quoted.
- [ ] Required checks exit 0 at C1.

## Source material

- Mission §5 R50–R52 (replan 3); R6, R10, R13, R18, R20, R23, R27, R43, R46–R49, "Human fixture inputs", "Test tiers and tolerances",
  "Contracts" (candidate output, reference values); TJ Q1, Q2, Q5, R1, R2.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.3.0.6 (species runner)
