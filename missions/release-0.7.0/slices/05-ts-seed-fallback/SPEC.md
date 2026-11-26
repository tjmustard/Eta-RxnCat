---
id: OPR.0.7.0.5
slice: 05-ts-seed-fallback
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Add run_ts_with_fallback and enumerated_pathway_inputs, falling through only on the R4 allow-list, plus the ensemble guards: pathway expected face, orientation centres, a reporting stall cap and the measured load-scaled pre-relax budget."
depends_on: [OPR.0.7.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_selectivity
parent: null
hacf_touches: [src/eta_rxncat/orchestrator/ts_fallback.py, src/eta_rxncat/orchestrator/ts_ensemble.py, src/eta_rxncat/orchestrator/_deadline.py, src/eta_rxncat/orchestrator/__init__.py, "tests/unit/orchestrator/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/orchestrator]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 TS seed fallback, ensemble guards and the guard budget source

## Intent

At run time, a TS node of an enumerated candidate tries its eligible templates in rank order and
falls through **only** when a seed fails TS validation (TJ Q-A1 B), while the ensemble gains the
guards the red team asked for (mission G6, R2, R4-R7, R24; US-006, US-016).

Context the builder needs:
- **First task, M13 (stop-and-report):** measure the guard's budget source before writing R7.
  Instrument (scratch, not committed) one GFN2 TS1a_n ensemble at R18 sizes: per guarded pre-relax
  record wall, `os.getloadavg()[0]`, `os.cpu_count()` and process CPU. Run it once on an idle host
  and once beside a loaded host (the lead names when; never beside a non-niced heavy process of
  another rig: if no loaded window is offered, run idle only and say so). Put the table in the
  proof. If, under load, a healthy pre-relax exceeds the R7 load-scaled budget, stop and report to
  the lead before writing R7. Mission HF-3: an n-propyl exo GFN2 member pre-relax already took 408.5 s beside a niced load (68 % of 600 s); the 1200 s cap is set by the per-command bound (HF3-BOUND). Mission HF-6: GFN2 xtb uses ~14 cores (3333 s CPU in 234 s), which is
  why a process-CPU budget is rejected.
- **R7, load-scaled budget (`orchestrator/_deadline.py`, `ts_ensemble.py`):** a helper
  `effective_budget_s(base_s) -> tuple[float, float]` returns
  `(min(1200.0, base_s * max(1.0, load1 / n_cpu)), load1)`, read once at guard entry. `_PreRelax`
  uses it; a timeout row stores `budget_s` (effective), `load1` and `budget_kind:
  "load_scaled_wall"`. `PRE_RELAX_BUDGET_S` stays 600.0 (the base). `pre_relax_budget_s=None` still
  disables the guard. The budget enters no stage key.
- **R6, stall cap:** keyword `max_pre_relax_timeouts: int | None = None` on `run_ts_ensemble` and
  `run_ts_ensemble_detailed` (not a `TSEnsembleOptions` field). After that many
  `pre_relax_failed:PreRelaxTimeout` exclusions, stop sampling; keep the members; set
  `TSEnsembleRun.stall_cap_reached_bool = True` (new dataclass field, default False). `None` =
  v0.6.0 behaviour. The ensemble is still valid (report, not stop).
- **R2, pathway face:** keyword `expected_face: tuple[int, ...] | None = None`; when set and the
  seed's face differs → `fail("seed:face_mismatch_pathway", …)`.
- **R24, orientation:** keyword `orientation_centers: Sequence[int] = ()`; per centre the sign of
  `det([x_a - x_c, x_b - x_c, x_d - x_c])` over its three lowest-index neighbours in the seed's
  bonds; a member whose signs differ from the seed's is excluded `orientation_mismatch` (after the
  face check, before dedup). An empty tuple = v0.6.0.
- **`orchestrator/ts_fallback.py` (new, selectivity node):**
  - `enumerated_pathway_inputs(candidate, node_id, template_id, recipe, member_gates) ->
    PathwayInputs`: seed `TSSpec` from the grafted template (forming bonds and active core
    composed by R32, below), `reactant_key`
    **derived** from the candidate's reactant nodes (R3: canonical SMILES by RDKit `DetermineBonds`
    at the declared charge on each reactant node's rank-1 eligible template, with counts) — no
    `reactant_key` argument. Refuses (`FallbackInputError`) a candidate that is not `ok`, or whose
    selectivity-set TSs disagree on composition/charge/multiplicity, and any node at charge != 0 or
    multiplicity != 1 (`charged_run_not_supported_v070`, R5).
  - **R32, multi-site seed composition (no core or enumerator change):** `template_id` is a
    template of the candidate graph's node, `f"{ref}__{candidate.candidate_id}"` as the enumerator
    writes it; strip that exact suffix to get the reference id `ref`. The node's *records* are the
    `status == "ok"` entries of `candidate.records` with `node_id == node_id` and
    `template_id == ref`, in list order (= site order; the enumerator appends one per covering
    site and an eligible template has every site `ok`). None → `FallbackInputError`. Record `k`'s
    `mapped_forming_bonds` and `constrained_core_product_indices` are in record `k`'s product
    space; compose each index into the final product (the last record's product = the candidate
    template's geometry) by calling `map_template_indices(records[j], ·)` (public, slice 04) for
    `j = k+1 … n-1` in order, not by reading `index_map` directly. If any call raises
    `EnumerationError` (a later site deleted the atom), raise `FallbackInputError` whose message
    begins `multi_site_seed_atom_deleted` and names node, `ref`, the earlier record's `site_id`,
    the deleting record's `site_id` and the lost index. Seed: **one record** → its two lists
    verbatim (no sort, no dedup; exactly today's seed and stage keys). **Several** → forming bonds
    = concatenation in site order of each record's composed pairs, dropping a pair whose unordered
    form is already present; active core = `sorted(set(...))` of the composed cores.
    `run_ts_with_fallback` derives the inputs of every eligible template **before its first engine
    call**, so this refusal (like R5's) propagates as `FallbackInputError` with 0 engine calls; it
    is not on the R4 allow-list and never falls through.
  - `run_ts_with_fallback(candidate, node_id, pathway: PathwaySpec, recipe, store, *, optimizer,
    options, member_gates, orientation_centers=()) -> tuple[FallbackRecord, TSEnsembleRun | None]`.
    For each eligible template in rank order: (1) guarded pre-relax through the **cached**
    `_PreRelax` stage (`constrained_preopt`, same key rules), timeout →
    `stopped:graft_pre_relax_timeout`; other pre-relax failures are template faults recorded
    `fell_through` with their reason **only if** in the allow-list, else stop; (2) face of the
    pre-relaxed start vs `pathway.expected_face` → `seed:face_mismatch_pathway` falls through
    without a TS search; (3) `run_ts_ensemble_detailed(..., expected_face=…,
    max_pre_relax_timeouts=2, orientation_centers=…)`. The first ensemble with members and no
    `failed_reason` is chosen.
  - **R4 allow-list (exact):** falls through on `seed:ts_search_failed:{max_steps,
    too_many_rejections,mode_lost,no_reaction_mode}`, `seed:ts_validation_failed`,
    `seed:gate_failed:<any>`, `seed:face_undetermined`, `seed:face_mismatch_pathway`. Every other
    reason → `stopped:<reason>` and the node stops (including `seed:engine_error`,
    `seed:scf_convergence`, `seed:ts_search_failed:wall_time_exceeded`, unknown strings). A live
    `EngineError`/`EngineUnavailableError` propagates unchanged. All attempts exhausted →
    `stop_reason="all_templates_failed"`.
  - **No new cache rows of its own:** a rerun re-derives the identical `FallbackRecord` from cached
    rows (pre-relax, TS, frequency) with 0 engine calls.
- **Exports:** `orchestrator/__init__.py` lazily re-exports the two functions (it is a selectivity
  file after slice 01).
- **Seat rules (every slice):**
  - Set `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp). Run every framework script with
    `python3`.
  - Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`, which must print `index: ok`.
  - Run `hypergraph_updater.py --from-diff <Start> --apply` **once** after the commit, re-indexing
    first. A rerun needs `git restore spec/compiled/architecture.yml` first and a disclosure.
  - Never edit `spec/compiled/architecture.yml` by hand. Never read `spec/archive/` or
    `tests/candidate_outputs/` (slices 11-13 write candidates; they never read them back as input).
  - Commit under this machine's git identity, ending with exactly
    `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
    `Agentic-Framework: HACF v<version> (OpenRig)`, the version read from
    `.agents/hacf-manifest.json` at commit time. No co-author trailer, never `--no-verify`.
  - Stage named files only. No push, tag or promote. Never touch `missions/release-0.6.0/` or `PRDs/`.
- **Clean room (hard rule):** never open, clone, fetch or search Eta_Scripts or nMAP. Read no
  TS-optimizer or conformer-search source (the installed `geometric` package, Sella, pysisyphus).
  geomeTRIC runs only as a black box through eta's `GeometricOptimizer`; reading its **output files**
  is allowed. Any stack you look at is filtered to eta frames plus a count of geomeTRIC frames.
- **Licence:** the core stays MIT/BSD; no ASE, Sella or copyleft in core; geomeTRIC stays in the
  `opt-geometric` extra and is never vendored. No new Python dependency.
- **Heavy runs (mission §5 "Heavy-run rule", normative):** before each engine/GPU command, a
  blocking host check in its own call or an exiting loop (never echo-then-run), output kept in the
  proof: `nvidia-smi` no compute process; `MemAvailable` >= 12 GiB; `ps`: no other eta
  E2E/pytest/xtb and no non-niced (nice < 10) process of any rig using >= 100 % CPU or >= 2 GiB RSS.
  One engine and one unit per command, `timeout 3600`, from a scratch cwd (never the repo root:
  geomeTRIC writes `HT.v_*.txt` into the cwd until slice 06 lands). Env asserted in the proof:
  `ETA_RXNCAT_XTB=~/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`, `ETA_RXNCAT_ACCEPTANCE=1`,
  `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`. Honour any quiet-host hold the lead announces.

## 1. The Confidence Mandate

**Score: 9/10.** The strings are read at the base (HF-4), the guards are optional keywords that leave
v0.6.0 calls byte-identical, and the face separation is measured (HF-2). R32's composition uses
only slice 04's public `map_template_indices` and the record fields as built (read at 45ffa04:
records appended in site order, each record's lists in its own product space), so it needs no
core or enumerator change, and one site keeps today's seed verbatim. Residual risk: R7's
constants under real load, which M13 measures first with a stop-and-report gate.

## Mini-requirements

1. M13 table in the proof (idle, and loaded if offered); R7 written only after it.
2. US-006: a fake engine raising the real `EngineRuntimeError` through `run_transition_state` →
   `stopped:seed:engine_error`; the same from a cached row (second store open) also stops.
3. A fake `PreRelaxTimeout` on the graft pre-relax → `stopped:graft_pre_relax_timeout`.
4. Each allow-list reason falls through (fake seeds); `seed:scf_convergence` and
   `ts_search_failed:wall_time_exceeded` stop; an unknown string stops.
5. A test iterates `typing.get_args(TSSearchFailureReason)` and fails on any reason not classified.
6. `seed:face_mismatch_pathway` before the search: the TS search is never called (spy).
7. US-016: a fake staller with `max_pre_relax_timeouts=2` stops sampling after 2 timeouts, keeps
   members, `stall_cap_reached_bool` True; `None` reproduces v0.6.0 (existing ensemble tests pass).
8. R7: a timeout row records `budget_s`, `load1`, `budget_kind`; `effective_budget_s` unit-tested
   (load below/above n_cpu, cap 1200).
9. Orientation: a member with swapped R/H at a centre is excluded `orientation_mismatch`.
10. Charged and open-shell candidates refused; `reactant_key` derived (no argument).
11. Rerun: identical `FallbackRecord`, 0 engine calls.
12. R32 single site: for a one-site `ok` candidate, the seed's forming bonds and active core
    equal the record's `mapped_forming_bonds` and `constrained_core_product_indices` verbatim
    (pinned, with the TS stage key unchanged).
13. R32 refusal: a two-site plan on one TS template whose second site's `template.delete` names an
    atom of the first site's `forming_bonds` enumerates `ok`, and `enumerated_pathway_inputs`
    raises `FallbackInputError` beginning `multi_site_seed_atom_deleted` (naming both sites);
    `run_ts_with_fallback` on it raises the same with 0 engine calls (spy).
14. R32 composed: a two-site plan whose sites each declare one forming bond and core atoms, none
    deleted by the other, gives forming bonds = site 1's pair mapped through site 2's record via
    `map_template_indices`, then site 2's pair, and active core = the sorted union; each composed
    pair indexes the final product (asserted by element symbols at those indices).
15. One GFN2 smoke: `run_ts_with_fallback` on the enumerated ethyl/TS1a_n candidate (slice 03
    plan) chooses rank 1 with members, behind the host check.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] M13 measurement (scratch instrument; host check per run); proof table.
- [ ] `_deadline.py`/`ts_ensemble.py`: R7, R6, R2, R24 keywords.
- [ ] `ts_fallback.py`: inputs (R32 composition), fallback loop, allow-list, refusals; lazy exports.
- [ ] Tests `tests/unit/orchestrator/test_ts_fallback.py`, `test_ts_ensemble_guards.py`,
      `test_deadline.py` additions.
- [ ] GFN2 smoke behind the host check.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** fall through outside the R4 list, or change `score_selectivity`, the sampler or P-RFO.
- **DO NOT** change ADR-0024 (the optimizer stays in-process), or add a stage kind or key field.
- **DO NOT** make the stall cap a `TSEnsembleOptions` field or change any default v0.6.0 behaviour.
- **DO NOT** use a process-CPU budget (HF-6).
- **DO NOT** edit `mapping/enumerator.py` or core for R32, or seed a multi-site template from one
  record's lists uncomposed.

## Proof contract

- [ ] M13 table with host checks.
- [ ] `uv run pytest tests/unit/orchestrator -q` passes (requirements 2-11, 12-14).
- [ ] GFN2 smoke result with its host check and env.
- [ ] Required checks exit 0.

## Source material

- Mission G6, R2, R4-R7, R24, R32, HF-2, HF-4, HF-6; ADR-0045, ADR-0048.
- Slice 04 audit `proof/04-qa.md`, observed item (b) (R32).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.3 (and OPR.0.7.0.2 through it).
