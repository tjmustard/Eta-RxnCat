## Context

The plan's v0.7.0 enumerator ranks and selects multiple template fallbacks and propagates
charge/multiplicity deltas. The reference starter reorders templates by lowest RMSD, silently skips
mismatched templates, and fabricates an identity mapping after the graft. `ReactionGraph` schema 1
carries no graft sites, and every fixture depends on it. Resolve measured on the Tier 4 TSs that
the symmetric mirror fragment order fits at about 0.49 Å against 0.03–0.05 Å, that on TS1a_n it
grafts without a clash, and that the lower-fit order differs between TS1a_n and TS1a_x for the same
fragment.

## Decision

- **A separate input.** Enumeration input is an `EnumerationPlan` beside `ReactionGraph` schema 1,
  which is unchanged. It holds sites with one `SiteTemplateMap` per (node, template) (keep, delete,
  alignment, core and forming bonds in that template's index space), library entries with declared
  `charge_delta`/multiplicity and every symmetric fragment order, selectivity sets with each
  pathway's expected face, and a required `max_candidates` that refuses, never truncates.
- **Ranking.** Declared rank wins. RMSD is an eligibility gate (keyed, no default; 0.15 Å in the
  v0.7.0 fixtures). Every order is tried and recorded, and the lowest-RMSD order is chosen per
  template.
- **Refusals** come from a closed set and are always recorded. A node with no eligible template
  makes its candidate `unmappable`.
- **Charge (TJ v0.4.0 Q5 A).** Product charge = template charge + Σ declared deltas. Multiplicity is
  declared or inherited. Parity is refused before any graft. Nothing is inferred.
- **Cross-node invariant.** The nodes of a selectivity set carry the same entry multiset, and the
  competing TSs share composition, charge and multiplicity with Σ reactants. `reactant_key` is
  derived from the candidate. The v0.6.0 scorer is unchanged.

## Consequences

- Existing graphs and fixtures are untouched, and enumeration stays pure and byte-deterministic (not
  cached).
- Site maps are verbose, one per template, which is the price of correct indices across fallback
  templates.
- A direct `score_selectivity` caller with a hand-built key keeps v0.6.0's behaviour. That is a
  stated limit.
