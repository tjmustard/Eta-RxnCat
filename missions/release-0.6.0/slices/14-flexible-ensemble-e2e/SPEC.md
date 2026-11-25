---
id: OPR.0.6.0.14
slice: 14-flexible-ensemble-e2e
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Graft an alkyl series (ethyl, n-propyl, n-butyl) onto TS1a_n, run guarded core-frozen pre-relax and the TS ensemble on GFN2 and UMA, and gate per R at least two distinct members, unit weights, the seed's face and an all-hit rerun, with ddG dagger reported only."
depends_on: [OPR.0.6.0.13]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", "tests/candidate_outputs/v0.6.0/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest]]
lore_refs: [ADR-0031, ADR-0032, ADR-0043, ADR-0044, ADR-0048]
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 Tier 4 flexible-ensemble E2E — alkyl R-group series on TS1a_n

## Intent

Prove the ensemble mechanics on TS families that really have several conformers. Graft R = ethyl,
n-propyl and n-butyl onto the cyclopropene CH2 of TS1a_n with eta's existing graft. Pre-relax each
graft with the core frozen, under slice 13's guard, then run the v0.6.0 TS ensemble on GFN2 and UMA.
Gate per R the member count, the weights, the faces and the cache, and report everything else.
Tests and inputs only: no `src/` change.

Context the builder needs:
- **TJ, verbatim (binding):**
  - Q-RES1 (row `qitem-20261125134835-b68359c8b88aa4f6`): "B (the recommendation). Add one
    mechanics-only flexible-ensemble E2E as slice 13, before the acceptance record. Graft a
    rotor-bearing substituent (e.g. methoxymethyl) onto TS1a_n and run it on GFN2 and UMA. Gates:
    >= 2 distinct members, weights summing to 1, consistent faces, and a second run that is all
    cache hits. ddG dagger is reported only. Replan the details as needed."
  - Amended (row `qitem-20261125135141-40dabb65dfb7a8a8`), verbatim: "Can we r-group enumerate a
    new TS from with a alkyl chain". He chose: R = ethyl, n-propyl, n-butyl on the cyclopropene CH2
    of TS1a_n; eta's existing graft; core-frozen pre-relax, then the v0.6.0 TS ensemble on GFN2 and
    UMA. Per R: ≥ 2 distinct members where the chain allows (state the expectation per R before the
    run); weights summing to 1, consistent faces, the rerun all cache hits; ensemble size per chain
    length reported, non-decreasing expected. ddG dagger reported only. Apply the HF-13 guard to
    these grafts too. One engine at a time.
  - "Slice 13" in his text is this slice: 13 was already the HF-13 guard (R28).
- **Inputs (new, under `tests/e2e/data/e2e5/`):**
  - **Fragments.** `xyz/r_ethyl_cyclopropene.xyz`, `xyz/r_npropyl_cyclopropene.xyz` and
    `xyz/r_nbutyl_cyclopropene.xyz` are 3-R-cyclopropenes from SMILES `CCC1C=C1`, `CCCC1C=C1` and
    `CCCCC1C=C1`. Build each with `Chem.AddHs`, then ETKDGv3 with `randomSeed=42`, then
    `MMFFOptimizeMolecule`. Then set the chain all-anti with `rdMolTransforms.SetDihedralDeg`: the
    ring-H – ring C(sp3) – Cα – Cβ dihedral to 180°, then every C–C–C–C dihedral outward to 180°.
    Write the files once with 6 decimals, and give each a `SOURCES.md` row (generated, recipe and
    RDKit version, sha256). The anti set-up is not optional: the plain ETKDG conformer of n-propyl
    folds the chain onto Cp and the graft refuses it (`GraftClashError`, atoms 8/18 at 0.28 Å,
    measured).
  - **Fixture.** `t4_flexible_alkyl.yaml` gives per R the fragment file, the graft lists, the core
    `[0, 1, 2, 3, 4, 5]`, the forming bonds `[[1, 2], [3, 5]]`, the pre-relax `{maxiter: 200}`,
    `temperature_k` 298.15, the gates below, and the expected member counts as comments.
  - **The graft is normative.** The template is TS1a_n (`xyz/TS1a_n.xyz`, active `[0..5]`), with
    keep = all but 16 (H16, the cyclopropene CH2 hydrogen anti to Cp) and delete `[16]`. Template
    alignment is `[7, 2, 3, 17]` (C7, C2, C3, and H17, the CH2 hydrogen syn to Cp). Fragment
    alignment is `[ring C(sp3), sp2 a, sp2 b, ring-C(sp3) H]`, and `fragment_delete` is the two
    sp2 ring H's. The constrained core is `[0..5]`, charge 0, multiplicity 1.
  - **The sp2 pair order is the one with the lower alignment RMSD** (`mapping.align.superpose`
    over the four pairs). The ring is symmetric, and the wrong order is the mirror fit (0.49 Å,
    17 contacts, measured). Store the chosen order as literal indices in the YAML, and have an
    offline test recheck that it is the lower fit.
  - **Measured:** each graft has alignment RMSD 0.033–0.035 Å and no close contacts; atom counts
    are 24, 27 and 30.
- **Run (per R × recipe, one engine at a time):**
  1. Graft, then `relax_constrained_core(product, engine, GeometricOptimizer(), [0..5], {"maxiter":
     200})` **inside `eta_rxncat.orchestrator._deadline.deadline(PRE_RELAX_BUDGET_S)`**. This is
     TJ's HF-13 guard on the grafts. A `PreRelaxTimeout` there fails that R's run with reason
     `graft_pre_relax_timeout`, recorded in the candidate. It is not a hang.
  2. Seed `TSSpec(ts_id="TS1a_n_<R>", start=relaxed (active [0..5]), forming_bonds=[(1, 2), (3, 5)])`.
  3. `run_ts_ensemble_detailed(..., optimizer=GeometricOptimizer(), core_indices=[0..5],
     pathway="endo", options=TSEnsembleOptions())`, with the library defaults, which are R18's sizes.
     Use `member_gates(recipe)` from `tests/e2e/t4.py`. Member pre-relaxes are guarded by slice 13
     already.
  4. Reactants: `run_species` for cyclopentadiene (the existing Tier 4 species block) and for the
     3-R-cyclopropene (SMILES above, `n_embed` 10, seed 42), in the same store.
  5. Repeat steps 2–4 in the same store and record the second pass.
- **Gates (each R × recipe; a fail is a stop-and-report):**
  - (a) the ensemble has no `failed_reason`;
  - (b) **distinct members ≥ 2**;
  - (c) |Σ weights − 1| ≤ 1e-12;
  - (d) every member's `face` equals the seed's, and there are zero `face_mismatch` and zero
    `engine_error` exclusions;
  - (e) the second pass creates zero rows and makes zero engine calls (`constrained_preopt`,
    `ts_opt`, `frequency`, reactant stages), with an equal `TSEnsemble`;
  - (f) no `graft_pre_relax_timeout`.
- **Expectation per R (stated before the run, from resolve's measurement):**
  - **Ethyl: 3.** The seed (or anti) rotamer plus the two gauche rotamers, which are mirror images
    of each other at equal G across the TS's mirror plane, so they are genuinely distinct
    saddles. That is why ethyl is gated at ≥ 2 like the others.
  - **n-Propyl: 4. n-Butyl: 5.** These are measured counts, not gates: a run giving 2 or more
    passes.
- **Reported (not gated):**
  - members per R, and whether the count is non-decreasing with chain length;
  - exclusions by reason; merges and flagged merges;
  - per-member ΔG (kcal/mol), weights and `pre_relax_wall_time_s`, plus the maximum;
  - ΔG‡_ensemble = G_pathway − ΣG_reactants and ΔG‡_seed (seed member only), both kcal/mol;
  - the ensemble correction (their difference), and ΔΔG‡ versus ethyl. "ddG dagger is reported
    only."
  - Non-decreasing is reported, not gated. Sampling is deterministic, but a member can drop to
    `connectivity_changed` or `ts_search_failed` from one engine build to the next, and n-butyl
    already loses two this way.
- **Measured by resolve (evidence `~/.hacf/eta-rxncat-hacf/evidence/v060-replan4/`):**

  | R | GFN2 members | GFN2 wall | UMA members | UMA wall |
  |---|---|---|---|---|
  | ethyl | 3 | 192 s | 3 | 223 s |
  | n-propyl | 4 | 482 s | 4 | 206 s |
  | n-butyl | 5 | 694 s | 5 | 819 s |

  - Every run: Σw = 1, every face [1, 1], second pass 0 rows / 0 calls / equal ensemble, no
    `PreRelaxTimeout`.
  - Max member pre-relax: GFN2 282 s (n-propyl), UMA 387 s (n-butyl). These sit inside the 600 s
    budget but are the longest seen. Record them.
  - Exclusions: `outside_window` 1–3 per R; n-butyl also has 1 `connectivity_changed` and 1
    `ts_search_failed:no_reaction_mode` on both engines.
  - UMA RSS is about 8.1 GB per process.
- **Candidates:** `tests/candidate_outputs/v0.6.0/t4_flexible_<R>.<recipe>.json` (six files),
  written as slices 09/10 do (`ETA_RXNCAT_CANDIDATE_DIR` honoured), for TJ's Phase 3 look. They hold
  the inputs' sha256s, the gates, the reported block and the environment. They make no regression
  claim: no promoted fixture exists, so slice 11 records this as `pending_promotion`.
- **No src change.** Everything used exists: graft, `relax_constrained_core`, `run_ts_ensemble_detailed`,
  `run_species`, `deadline`, `PRE_RELAX_BUDGET_S`. If the builder finds a src change is needed,
  stop and report to the lead, because slice 11's reproducibility reuse (R30) depends on src being
  unchanged.
- **Heavy runs:** see slice 11's block (TJ's memory rule, verbatim). Each R × recipe is its own
  command:
  - before it, a blocking host check in its own call (`free -g` ≥ 9 G available; no other
    pytest/xtb/eta python on the host, any rig; GPU idle);
  - `timeout 3600`, `ETA_RXNCAT_ACCEPTANCE=1`, and `ETA_RXNCAT_XTB` for xtb;
  - UMA in `.venv-accept-uma`, one at a time;
  - total about 25 min per recipe.
- **Seat rules (every slice):**
  - `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp).
  - Every framework script with `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand.
  - Never read `spec/archive/` or `tests/candidate_outputs/`; writing this slice's own candidates
    is allowed.
  - Commits go under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, with the version read from
    `.agents/hacf-manifest.json` at commit time.
  - No co-author trailer, and never `--no-verify`.
  - Stage named files only. No push, tag or promote.
- **Clean room (v0.4.0 Q1, v0.5.0 A1, hard rule):**
  - Never open, clone, fetch or search Eta_Scripts or nMAP.
  - Read no TS-optimizer or conformer-search source: the installed `geometric` package internals,
    Sella, pysisyphus.
  - geomeTRIC runs only as a black box through eta's `GeometricOptimizer`.

## 1. The Confidence Mandate

**Score: 9/10.** Every step is shipped code that resolve ran end to end on both engines, with the
exact graft recipe and gates. All six R × recipe runs passed every gate. Residual risk: the
long member pre-relaxes (up to 387 s) sit inside the 600 s guard, and a timeout there would only
exclude a member, which the gates tolerate as long as ≥ 2 remain.

## Mini-requirements

1. US-008/Q-RES1 B: for each R in (ethyl, n-propyl, n-butyl) × (GFN2, UMA), gates (a)–(f) pass.
2. Offline (default suite, no engine): the three fragment files match their `SOURCES.md` sha256.
   Each graft builds with alignment RMSD ≤ 0.05 Å and no close contacts. The stored sp2 order is
   the lower of the two fits. The product's perceived bonds are the template's minus C7–H16, plus
   C7–Cα and the chain.
3. The candidates hold the gates, the reported block (including members per R and the
   non-decreasing flag), the max pre-relax wall time, the sha256s and the environment (with
   `ETA_RXNCAT_ACCEPTANCE=1`, plus `ETA_RXNCAT_XTB` for xtb).
4. The graft pre-relax runs under `deadline(PRE_RELAX_BUDGET_S)`. An offline test with a stub
   optimizer that loops, and a 1 s budget, gives `graft_pre_relax_timeout`.
5. No file under `src/` changes (`git diff --stat <Start>.. -- src` is empty, recorded in the proof).

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `tests/e2e/t4.py`,
      `tests/e2e/fixtures.py` (T4 loader), slice 10's SPEC (graft pattern), and resolve's evidence
      README (`flex.py` is a scratch prototype: implement from this SPEC).
- [x] Task 2: fragment files, `SOURCES.md` rows, `t4_flexible_alkyl.yaml`, the loader, and offline
      tests (requirements 2, 4).
- [x] Task 3: `tests/e2e/t4_flexible.py` helpers and `tests/e2e/test_t4_flexible.py`, parametrised
      R × recipe under the `e2e` + engine markers.
- [x] Task 4: host-checked runs: GFN2 then UMA, one R per command. Write the candidates, then the
      required checks.
- [x] Task 5: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** change `src/`. **DO NOT** write `tests/fixtures/`. **DO NOT** read
  `tests/candidate_outputs/` beyond writing this slice's own files.
- **DO NOT** gate ΔG‡/ΔΔG‡, the exact member counts, or the non-decreasing order.
- **DO NOT** edit slices 09/10's helpers' behaviour. Additive imports and new functions only.
- **DO NOT** run two engines at once, or skip the blocking host check.
- **DO NOT** use a chain conformer other than the all-anti recipe, and **DO NOT** pick the sp2
  order by anything but the lower fit.

## Proof contract

- [x] Six host-checked runs: exit 0, wall, RSS and gates per R × recipe; members per R reported.
- [x] Offline tests pass in the default suite; required checks exit 0; empty `src` diff recorded.

## Source material

- Mission R29, R30, HF-14, Q-RES1; slice 10 (graft pattern); slice 13 (guard); evidence
  `~/.hacf/eta-rxncat-hacf/evidence/v060-replan4/README.md`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.6.0.13 (audited). Slice 11 depends on this slice.
