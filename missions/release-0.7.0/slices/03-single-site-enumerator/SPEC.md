---
id: OPR.0.7.0.3
slice: 03-single-site-enumerator
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Graft every library entry onto every declared (node, template) with eta's graft, choosing the lowest-RMSD fragment order, gating eligibility at the keyed RMSD, enforcing the charge rule and the cross-node invariant, and recording every refusal."
depends_on: [OPR.0.7.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_enumerator
parent: null
hacf_touches: [src/eta_rxncat/mapping/enumerator.py, "tests/unit/mapping/test_enumerator*.py", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/mapping]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.7.0 single-site enumerator, eligibility, charge and cross-node check

## Intent

`enumerate_candidates(plan, *, max_alignment_rmsd_angstrom)` in `src/eta_rxncat/mapping/enumerator.py`
turns an `EnumerationPlan` with one site into candidate graphs and a per-graft record (mission G2,
G3, G5, R3, R10, R11; US-004, US-005). It is pure and deterministic, and it never infers chemistry.

Context the builder needs:
- **Per (entry, SiteTemplateMap):** build a `GraftSpec` (template lists from the map,
  `fragment_alignment` from each of the entry's `fragment_orders`, `fragment_delete`,
  `constrained_core` from the map, `product_charge`/`product_multiplicity` from R10). Call eta's
  `graft` once per order. The order with the lowest `alignment_rmsd_angstrom` wins; ties go to the
  first listed. Record every order's RMSD (`order_rmsds_angstrom`), with `inf`-free encoding: an
  order whose graft raised is recorded with its refusal reason and no RMSD.
- **Eligibility (all must hold):** `graft` returned for the chosen order; its RMSD <=
  `max_alignment_rmsd_angstrom` (keyed, **no default**; the E2E fixture states 0.15 Å, HF-1/HF-2:
  good fits 0.033-0.049 Å, mirrors 0.483-0.494 Å); total charge and element multiset equal to the
  node's other eligible templates; every `forming_bonds` atom kept (else `forming_bond_deleted`).
  Note HF-1: the endo mirror order **grafts** (17 contacts, min 0.64 Å), so the RMSD gate is what
  refuses it — test it.
- **Refusal reasons (closed set):** `graft_input` (`GraftInputError`), `graft_clash`
  (`GraftClashError`), `alignment_rmsd`, `composition_mismatch`, `parity`, `multiplicity_conflict`,
  `multi_component_template` (template with > 1 component or count > 1), `site_atom_deleted`
  (slice 04 uses it), `forming_bond_deleted`. Each has one test.
- **Charge (R10):** `product_charge = template.total_charge + Σ charge_delta`; multiplicity declared
  else inherited from the single component; two different declared values → `multiplicity_conflict`;
  parity decided by electron count (Σ Z − charge vs multiplicity) **before** calling `graft` →
  `parity`. `whole_input_charge_sum_holds_bool` is copied to the record as reported, never used.
- **Graph output:** templates of a covered node become the eligible grafted ones, renumbered 1..k in
  declared-rank order; ids `f"{template_id}__{candidate_id}"`; graph `name =
  f"{reference.name}__{candidate_id}"`; node ids unchanged; templates no site lists are copied
  unchanged. k = 0 → candidate `unmappable`, `detail = node id`, no graph.
- **Cross-node invariant (G3, R3):** for each selectivity set of the plan: every pathway node and
  every reactant node that a site covers carries the same entry multiset as the others the site
  covers; a site must cover every pathway node of a set or none (else `inconsistent`,
  `detail="partial_pathway_coverage:<site>"`); the competing TS nodes' rank-1 eligible templates
  share element multiset, charge and multiplicity; their composition equals Σ (count × reactant
  composition) with Σ charges. Any miss → `inconsistent` with a `detail` naming the check.
- **Index carry-through:** each eligible record keeps `index_map`, `mapped_forming_bonds` (the map's
  forming bonds through `index_map`) and `constrained_core_product_indices`.
  `map_template_indices(record, indices)` maps template indices to product indices and raises on a
  deleted atom.
- **`projected_ts_searches` (R11):** Σ over `ok` candidates × selectivity-set TS nodes × eligible
  templates × (1 + `max_research`), with `max_research` passed as a keyword (default the
  `TSEnsembleOptions` default, 10).
- **Determinism:** sorted iteration everywhere; two calls on the same plan give
  `result.model_dump_json()` byte-equal. Not cached (pure, like the sampler).
- **Fixture for unit tests:** build plans from `tests/e2e/data/e2e5/xyz/TS1a_n.xyz`, `TS1a_x.xyz`,
  the slice-14 fragments `r_ethyl_cyclopropene.xyz`/`r_npropyl_cyclopropene.xyz` and their roles in
  `t4_flexible_alkyl.yaml` (read-only inputs); use the HF-1 lists (delete [16], alignment
  [7, 2, 3, 17]). Assert the chosen orders: ethyl endo [3, 4], exo [4, 3] (HF-1).
- **Edges:** `mapping/enumerator.py` imports `eta_rxncat.mapping` (graft, align) and core only.
  `mapping/__init__.py` does **not** re-export it (R19).
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

## 1. The Confidence Mandate

**Score: 9/10.** Every rule is stated and the geometry it rests on is measured (HF-1, HF-2). Residual
risk: the parity count for unusual elements; the test covers ±1 charge and a doublet on the real
fragments.

## Mini-requirements

1. US-004: per (entry, node, template) an `ok` record with the measures or a `refused` record with a
   closed-set reason; one test per reason.
2. Chosen order = lowest RMSD, ties to first; every order's RMSD recorded; endo/exo orders as HF-1.
3. The endo mirror order alone is refused `alignment_rmsd` at 0.15 Å.
4. US-005: charge_delta −1 and +1 and a declared doublet give the stated product charge and
   multiplicity; a parity violation is refused before `graft` is called (spy test); multiplicity
   conflict refused.
5. Mixed coverage (site on TS1a_n only) → `inconsistent`, `partial_pathway_coverage`.
6. k = 0 → `unmappable` with no graph; renumbering 1..k keeps declared order.
7. `map_template_indices` maps and refuses deleted atoms; `mapped_forming_bonds` correct on HF-1.
8. `projected_ts_searches` exact on a toy.
9. Two runs byte-equal.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] `mapping/enumerator.py`: plan walk, per-order graft, eligibility, charge, records.
- [ ] Cross-node invariant and candidate assembly.
- [ ] `map_template_indices`, `projected_ts_searches`.
- [ ] Tests `tests/unit/mapping/test_enumerator.py` (+ `_charge`, `_crossnode` files if large).
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** reorder templates by RMSD over declared rank, or skip a refused template silently.
- **DO NOT** infer charge or multiplicity from fragment charges.
- **DO NOT** change `graft`, `ReactionGraph` or any fixture; **DO NOT** cache enumeration.
- **DO NOT** implement multi-site products here (slice 04): a plan with > 1 site raises
  `EnumerationError("multi-site: slice 04")` until then.

## Proof contract

- [ ] `uv run pytest tests/unit/mapping -q` passes (requirements 1-9).
- [ ] Required checks exit 0.

## Source material

- Mission G2, G3, G5, R3, R10, R11, HF-1, HF-2; evidence `offline.json`, `offline_m4.json`.

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.2.
