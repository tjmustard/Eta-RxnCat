---
id: OPR.0.7.0.4
slice: 04-multi-site-product
mission: release-0.7.0
status: active
stage: wip
verified: "2026-11-26 against scaffold (hyper_scope slice create)"
created: "2026-11-26"
intent: "Enumerate multi-site plans as a deterministic Cartesian product, refusing above max_candidates before any graft, remapping later sites per template through index_map, and refusing a site whose atoms an earlier graft deleted."
depends_on: [OPR.0.7.0.3]
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

# MiniPRD: v0.7.0 multi-site product, cap and index remap

## Intent

Extend `enumerate_candidates` from one site to several (mission G4, R11; US-007). The E2E uses one
site, so this slice is proven by unit tests on toys plus one real two-site plan.

Context the builder needs:
- **Order:** sites in `plan.sites` order; candidates are the Cartesian product of per-site entries
  in lexicographic (site order, entry declared order); candidate id = entry ids joined by `+`.
- **Cap:** compute the product size first; if it exceeds `max_candidates`, raise `EnumerationError`
  naming both numbers **before any graft** (spy test: `graft` never called). `unmappable` and
  `inconsistent` candidates count toward the product (they are candidates).
- **Remap per template:** a later site's `SiteTemplateMap` is declared in the **reference**
  template's index space; for template T, map it through the `index_map` of the earlier graft on T
  (each fallback template has its own map, so each remaps through its own record). A later-site
  atom (keep, delete, alignment, core, forming bond) that an earlier graft deleted → refusal
  `site_atom_deleted` for that (node, template).
- **Charge:** Σ `charge_delta` over all entries applied to the template; multiplicity declared by at
  most one value across them (else `multiplicity_conflict`).
- **Cross-node invariant** (slice 03) applies to the full entry multiset.
- **Toys:** a two-site plan on TS1a_n replacing H16 (site A, ethyl) and an H on C6 (site B, methyl
  as a 3-methylcyclopropene-free toy fragment you build in the test from RDKit with a fixed seed)
  with hand-computed product indices; a deleted-site toy where site B targets H16.
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

**Score: 9/10.** Small extension with exact rules; the remap is hand-checked on a toy.

## Mini-requirements

1. Deterministic order and ids on a 2 × 2 product.
2. Cap exceeded → `EnumerationError` before any graft.
3. Two-site remap matches hand-computed indices.
4. A site atom deleted earlier → `site_atom_deleted`.
5. Σ charge and the multiplicity conflict across sites.
6. Two runs byte-equal; slice 03's tests still pass.

## 3. Implementation Plan (Task List)

- [ ] Index.
- [ ] Product, cap, per-template remap in `mapping/enumerator.py`; remove the slice-03 single-site guard.
- [ ] Tests `tests/unit/mapping/test_enumerator_multisite.py`.
- [ ] Required checks; commit; updater once.

## 4. The Negative Space (Constraints)

- **DO NOT** truncate a product; **DO NOT** remap through another template's `index_map`.
- **DO NOT** add a ceiling to `max_candidates` (v0.8.0).

## Proof contract

- [ ] `uv run pytest tests/unit/mapping -q` passes (requirements 1-6).
- [ ] Required checks exit 0.

## Source material

- Mission G4, R11, R19 (enumerator node).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

- OPR.0.7.0.3.
