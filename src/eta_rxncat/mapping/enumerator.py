"""Library enumeration: site product, graft, eligibility, charge and cross-node check (v0.7.0).

``enumerate_candidates`` takes the Cartesian product of the library entries of a plan's sites,
grafts each combination onto every declared (node, template) with eta's ``graft``, one site after
the other, and assembles one candidate graph per combination. It is pure and deterministic, is not
cached, and infers no chemistry: charge and multiplicity come from the template and the entries'
declared values. ``eta_rxncat.mapping`` does not re-export this module (mission R19).
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from typing import Any

from pydantic import ValidationError

from eta_rxncat.core import (
    ATOMIC_NUMBERS,
    AtomMappingSpec,
    Component,
    EnumeratedCandidate,
    EnumerationPlan,
    EnumerationResult,
    GraftRecord,
    GraftRefusalReason,
    GraftResult,
    GraftSpec,
    LibraryEntry,
    MolecularState,
    ReactionGraph,
    ReactionNode,
    SelectivitySet,
    SiteTemplateMap,
    StageConfig,
    TemplateGeometry,
    TSEnsembleOptions,
)
from eta_rxncat.mapping.errors import (
    AlignmentError,
    GraftClashError,
    GraftInputError,
    MappingError,
)
from eta_rxncat.mapping.graft import graft

DEFAULT_MAX_RESEARCH: int = TSEnsembleOptions().max_research
"""Samples re-searched per TS template, read from ``TSEnsembleOptions``."""


class EnumerationError(MappingError):
    """A plan cannot be enumerated, or a template index has no image in a product."""


@dataclass(frozen=True)
class _SiteView:
    """A site map rewritten into the index space of one graft input."""

    template: AtomMappingSpec
    constrained_core: list[int]
    forming_bonds: list[tuple[int, int]]


@dataclass(frozen=True)
class _Eligible:
    """An eligible template: its final product and its composed (remapped) stages."""

    template: TemplateGeometry
    result: GraftResult
    stages: list[StageConfig]


def map_template_indices(record: GraftRecord, indices: Sequence[int]) -> list[int]:
    """Map graft-input atom indices to the product indices of a graft record.

    The input is the template for the first site and the previous site's product afterwards.

    Args:
        record: A graft record that kept its ``index_map``.
        indices: Atom indices of the record's graft input.

    Returns:
        The product index of each input index, in the given order.

    Raises:
        EnumerationError: The record has no product, or an index has no image (a deleted atom).
    """
    where = f"entry '{record.entry_id}', node '{record.node_id}', template '{record.template_id}'"
    if record.index_map is None:
        raise EnumerationError(f"{where}: the record has no graft product")
    position = _template_positions(record.index_map)
    lost = [i for i in indices if i not in position]
    if lost:
        raise EnumerationError(f"{where}: template atoms {lost} are not in the product")
    return [position[i] for i in indices]


def projected_ts_searches(
    candidates: Sequence[EnumeratedCandidate],
    selectivity_sets: Sequence[SelectivitySet],
    *,
    max_research: int = DEFAULT_MAX_RESEARCH,
) -> int:
    """Upper bound on the TS searches of the ``ok`` candidates (mission R11).

    Args:
        candidates: Enumerated candidates.
        selectivity_sets: Sets whose pathway nodes are the TS nodes; a shared node counts once.
        max_research: Samples re-searched per template, besides the seed.

    Returns:
        The sum over ``ok`` candidates, TS nodes and eligible templates of ``1 + max_research``.
    """
    ts_nodes = {p.node_id for s in selectivity_sets for p in s.pathways}
    templates = sum(
        len(node.templates)
        for candidate in candidates
        if candidate.graph is not None
        for node in candidate.graph.nodes
        if node.id in ts_nodes
    )
    return templates * (1 + max_research)


def enumerate_candidates(
    plan: EnumerationPlan,
    *,
    max_alignment_rmsd_angstrom: float,
    max_research: int = DEFAULT_MAX_RESEARCH,
) -> EnumerationResult:
    """Enumerate one candidate graph per combination of one library entry per site.

    Sites apply in ``plan.sites`` order. Candidates are the Cartesian product of each site's
    entries (library declared order), the last site varying fastest, and are named by their entry
    ids joined with ``+``. Records are ordered by node id, template rank, then site order.

    Args:
        plan: The plan, with at least one site.
        max_alignment_rmsd_angstrom: Largest alignment RMSD of an eligible graft (no default).
        max_research: Used only for ``projected_ts_searches``.

    Returns:
        Every candidate with its graft records.

    Raises:
        EnumerationError: The plan has no site, a site maps one (node, template) twice, or the
            product exceeds ``plan.max_candidates`` (decided before any graft).
    """
    if not plan.sites:
        raise EnumerationError("the plan has no site")
    for site in plan.sites:
        keys = Counter((m.node_id, m.template_id) for m in site.maps)
        repeated = sorted(key for key, n in keys.items() if n > 1)
        if repeated:
            raise EnumerationError(
                f"site '{site.id}' maps (node, template) {repeated} more than once"
            )
    per_site = [[e for e in plan.library if e.site_id == site.id] for site in plan.sites]
    size = math.prod(len(entries) for entries in per_site)
    if size > plan.max_candidates:
        raise EnumerationError(
            f"{size} candidates exceed max_candidates {plan.max_candidates}; nothing is truncated"
        )

    candidates = [
        _candidate(plan, combination, max_alignment_rmsd_angstrom)
        for combination in product(*per_site)
    ]
    return EnumerationResult(
        candidates=candidates,
        max_alignment_rmsd_angstrom=max_alignment_rmsd_angstrom,
        projected_ts_searches=projected_ts_searches(
            candidates, plan.selectivity_sets, max_research=max_research
        ),
    )


def _candidate(
    plan: EnumerationPlan, entries: Sequence[LibraryEntry], max_rmsd: float
) -> EnumeratedCandidate:
    """Graft one entry per site onto every mapped template, then check and assemble the graph.

    Args:
        plan: The plan.
        entries: One entry per site, in ``plan.sites`` order.
        max_rmsd: Alignment RMSD ceiling.
    """
    reference = plan.reference_graph
    nodes = {n.id: n for n in reference.nodes}
    maps = [{(m.node_id, m.template_id): m for m in site.maps} for site in plan.sites]
    covered = sorted({m.node_id for site in plan.sites for m in site.maps})
    candidate_id = "+".join(e.id for e in entries)
    # Per covered node, the sites (by position in the plan) that map any of its templates.
    covering = {
        node_id: [k for k, site in enumerate(maps) if any(n == node_id for n, _ in site)]
        for node_id in covered
    }

    records: list[GraftRecord] = []
    eligible: dict[str, list[_Eligible]] = {}
    dropped: list[str] = []
    for node_id in covered:
        node = nodes[node_id]
        stages = node.stages if node.stages is not None else reference.default_stages
        eligible[node_id] = []
        for template in sorted(node.templates, key=lambda t: t.rank):
            key = (node_id, template.id)
            if any(key not in maps[k] for k in covering[node_id]):
                dropped.append(f"{node_id}/{template.id}")
                continue
            chain = [(entries[k], maps[k][key]) for k in covering[node_id]]
            first = eligible[node_id][0].result if eligible[node_id] else None
            made, found = _graft_sites(chain, template, stages, first, max_rmsd)
            records.extend(made)
            if found is not None:
                eligible[node_id].append(found)

    def outcome(
        status: str, detail: str | None, graph: ReactionGraph | None = None
    ) -> EnumeratedCandidate:
        return EnumeratedCandidate.model_validate(
            {
                "candidate_id": candidate_id,
                "entry_ids_by_site": {e.site_id: e.id for e in entries},
                "status": status,
                "detail": detail,
                "graph": graph,
                "records": records,
            }
        )

    for node_id in covered:
        if not eligible[node_id]:
            return outcome("unmappable", node_id)
    # A set's pathway nodes carry the same entry multiset once each site covers all or none.
    for selectivity_set in sorted(plan.selectivity_sets, key=lambda s: s.id):
        pathway_nodes = {p.node_id for p in selectivity_set.pathways}
        for k, site in enumerate(plan.sites):
            hit = pathway_nodes & {n for n in covered if k in covering[n]}
            if 0 < len(hit) < len(pathway_nodes):
                return outcome("inconsistent", f"partial_pathway_coverage:{site.id}")
    for node_id in covered:
        if any(e.stages != eligible[node_id][0].stages for e in eligible[node_id]):
            return outcome("inconsistent", f"frozen_index_mismatch:{node_id}")

    graph = _candidate_graph(reference, candidate_id, eligible)
    failed = _cross_node_failure(graph, plan.selectivity_sets)
    if failed is None:
        carried = {n: Counter(entries[k].id for k in covering[n]) for n in covered}
        failed = _entry_multiset_failure(carried, plan.selectivity_sets)
    if failed is not None:
        return outcome("inconsistent", failed)
    detail = "dropped_unlisted:" + ",".join(sorted(dropped)) if dropped else None
    return outcome("ok", detail, graph)


def _entry_multiset_failure(
    carried: dict[str, Counter[str]], selectivity_sets: Sequence[SelectivitySet]
) -> str | None:
    """Return the first set whose TS entry multiset is not the union of its reactants' entries.

    The union reading (mission R31): a set's pathway nodes carry one multiset (checked by the
    coverage rule), which must equal the multiset sum over its covered reactant nodes.

    Args:
        carried: Entry ids carried by each covered node.
        selectivity_sets: The sets to check.
    """
    for selectivity_set in sorted(selectivity_sets, key=lambda s: s.id):
        union: Counter[str] = Counter()
        for node_id in selectivity_set.reactant_node_ids:
            union.update(carried.get(node_id, Counter()))
        for node_id in sorted({p.node_id for p in selectivity_set.pathways}):
            if carried.get(node_id, Counter()) != union:
                return f"entry_multiset_mismatch:{selectivity_set.id}"
    return None


def _product_multiplicity(declared: Sequence[int | None], inherited: int) -> int | None:
    """Return the declared multiplicity, else the inherited one; ``None`` on two different ones.

    Args:
        declared: The multiplicity each applied entry declares (``None``: declares none).
        inherited: The template's own multiplicity.
    """
    values = {value for value in declared if value is not None}
    if len(values) > 1:
        return None
    return values.pop() if values else inherited


def _parity_holds(symbols: Sequence[str], charge: int, multiplicity: int) -> bool:
    """Return True if the electron count allows the charge and multiplicity."""
    electrons = sum(ATOMIC_NUMBERS[s] for s in symbols) - charge
    unpaired = multiplicity - 1
    return 0 <= unpaired <= electrons and (electrons - unpaired) % 2 == 0


def _template_positions(index_map: Sequence[tuple[str, int]]) -> dict[int, int]:
    """Return ``{template index: product index}`` of a graft's index map."""
    return {i: p for p, (source, i) in enumerate(index_map) if source == "template"}


def _remap_stages(stages: Sequence[StageConfig], result: GraftResult) -> list[StageConfig]:
    """Rewrite every stage's frozen atoms as product indices (list order kept)."""
    position = _template_positions(result.index_map)
    return [
        StageConfig.model_validate(
            {**dict(stage), "frozen_atom_indices": [position[i] for i in stage.frozen_atom_indices]}
        )
        for stage in stages
    ]


def _graft_order(
    entry: LibraryEntry,
    site_map: SiteTemplateMap | _SiteView,
    state: MolecularState,
    order: list[int],
    charge: int,
    multiplicity: int,
) -> GraftResult | GraftRefusalReason:
    """Graft one fragment order, or return why it is refused."""
    fragment = entry.fragment
    keep = site_map.template.keep
    if len(order) != len(site_map.template.alignment):
        return "graft_input"
    # Parity is decided from the product's atoms before graft is called. Out-of-range indices
    # have no product atoms; graft refuses them itself.
    in_range = all(i < len(state.symbols) for i in keep) and all(
        j < len(fragment.symbols) for j in [*order, *entry.fragment_delete]
    )
    if in_range:
        dropped = set(order) | set(entry.fragment_delete)
        symbols = [state.symbols[i] for i in keep]
        symbols += [s for j, s in enumerate(fragment.symbols) if j not in dropped]
        if not _parity_holds(symbols, charge, multiplicity):
            return "parity"
    try:
        spec = GraftSpec(
            template=site_map.template,
            fragment_alignment=order,
            fragment_delete=entry.fragment_delete,
            constrained_core=site_map.constrained_core,
            product_charge=charge,
            product_multiplicity=multiplicity,
        )
    except ValidationError:  # the lists do not form a request (e.g. a paired atom deleted)
        return "graft_input"
    try:
        return graft(state, fragment, spec)
    except (GraftInputError, AlignmentError):
        return "graft_input"
    except GraftClashError:
        return "graft_clash"


def _listed_indices(site_map: SiteTemplateMap) -> set[int]:
    """Return every template atom a site map names."""
    mapping = site_map.template
    return {
        *mapping.keep,
        *mapping.delete,
        *mapping.alignment,
        *site_map.constrained_core,
        *(i for pair in site_map.forming_bonds for i in pair),
    }


def _remap_site(
    site_map: SiteTemplateMap, position: dict[int, int], n_template: int, n_current: int
) -> _SiteView:
    """Rewrite a site map from template indices into the current graft input's indices.

    Atoms appended by earlier grafts are not nameable in the template's index space; they are
    kept, after the declared ``keep``, in ascending order.

    Args:
        site_map: A map none of whose atoms an earlier graft deleted.
        position: ``{template index: current index}`` of the surviving template atoms.
        n_template: Atom count of the template.
        n_current: Atom count of the current graft input.
    """

    def image(i: int) -> int:
        # An index outside the template stays outside the input, so graft refuses it.
        return position[i] if i < n_template else n_current + i

    appended = sorted(set(range(n_current)) - set(position.values()))
    mapping = site_map.template
    return _SiteView(
        template=AtomMappingSpec(
            keep=[image(i) for i in mapping.keep] + appended,
            delete=[image(i) for i in mapping.delete],
            alignment=[image(i) for i in mapping.alignment],
        ),
        constrained_core=[image(i) for i in site_map.constrained_core],
        forming_bonds=[(image(i), image(j)) for i, j in site_map.forming_bonds],
    )


def _graft_sites(
    chain: Sequence[tuple[LibraryEntry, SiteTemplateMap]],
    template: TemplateGeometry,
    stages: Sequence[StageConfig],
    first_eligible: GraftResult | None,
    max_rmsd: float,
) -> tuple[list[GraftRecord], _Eligible | None]:
    """Graft every covering site onto one template, in site order, stopping at a refusal.

    Args:
        chain: ``(entry, site map)`` of each covering site; maps are in template indices.
        template: The template to graft onto.
        stages: The node's effective stages, in template indices.
        first_eligible: The node's best-ranked eligible final product so far.
        max_rmsd: Alignment RMSD ceiling of every graft.

    Returns:
        One record per attempted site, and the template when every site was eligible.
    """
    records: list[GraftRecord] = []
    state = template.components[0].state
    n_template = len(state.symbols)
    position = {i: i for i in range(n_template)}  # surviving template atom -> current index
    current_stages = list(stages)
    applied: list[LibraryEntry] = []
    final: _Eligible | None = None
    for step, (entry, site_map) in enumerate(chain):
        applied.append(entry)
        deleted = set(range(n_template)) - set(position)
        view: SiteTemplateMap | _SiteView | None = site_map
        if step > 0:
            view = (
                None
                if _listed_indices(site_map) & deleted
                else _remap_site(site_map, position, n_template, len(state.symbols))
            )
        record, result = _graft_template(
            applied,
            view,
            site_map.node_id,
            template,
            state,
            current_stages,
            first_eligible if step == len(chain) - 1 else None,
            max_rmsd,
        )
        records.append(record)
        if result is None:
            return records, None
        moved = _template_positions(result.index_map)
        position = {i: moved[c] for i, c in position.items() if c in moved}
        current_stages = _remap_stages(current_stages, result)
        state = result.product
        final = _Eligible(template, result, current_stages)
    return records, final


def _graft_template(
    applied: Sequence[LibraryEntry],
    view: SiteTemplateMap | _SiteView | None,
    node_id: str,
    template: TemplateGeometry,
    state: MolecularState,
    stages: Sequence[StageConfig],
    first_eligible: GraftResult | None,
    max_rmsd: float,
) -> tuple[GraftRecord, GraftResult | None]:
    """Record one site's graft; the result is returned only when it is eligible.

    Args:
        applied: The entries applied to this template so far; the last one is grafted now.
        view: How the site reads on the graft input; ``None`` if an earlier graft deleted one of
            its atoms.
        node_id: Node of the template.
        template: The reference template.
        state: The graft input: the template's state, or the previous site's product.
        stages: The node's stages in the input's indices; their frozen atoms must survive.
        first_eligible: At the last site, the node's best-ranked eligible final product so far,
            which fixes its composition and charge.
        max_rmsd: Alignment RMSD ceiling.
    """
    entry = applied[-1]
    data: dict[str, Any] = {
        "entry_id": entry.id,
        "site_id": entry.site_id,
        "node_id": node_id,
        "template_id": template.id,
    }

    def refused(reason: GraftRefusalReason) -> tuple[GraftRecord, None]:
        return GraftRecord.model_validate({**data, "status": "refused", "reason": reason}), None

    if len(template.components) > 1 or template.components[0].count > 1:
        return refused("multi_component_template")
    multiplicity = _product_multiplicity(
        [e.multiplicity for e in applied], template.components[0].state.spin_multiplicity
    )
    if multiplicity is None:
        return refused("multiplicity_conflict")
    if view is None:
        return refused("site_atom_deleted")
    kept = set(view.template.keep)
    if any(i not in kept for stage in stages for i in stage.frozen_atom_indices):
        return refused("graft_input")
    charge = template.total_charge + sum(e.charge_delta for e in applied)

    outcomes = [
        _graft_order(entry, view, state, order, charge, multiplicity)
        for order in entry.fragment_orders
    ]
    data["order_rmsds_angstrom"] = [
        o.alignment_rmsd_angstrom if isinstance(o, GraftResult) else o for o in outcomes
    ]
    returned = [(i, o) for i, o in enumerate(outcomes) if isinstance(o, GraftResult)]
    if not returned:  # every order was refused: report the first listed order's reason
        return refused(next(o for o in outcomes if isinstance(o, str)))

    # The lowest RMSD wins; ``min`` keeps the first listed order on a tie.
    index, result = min(returned, key=lambda item: item[1].alignment_rmsd_angstrom)
    rmsd = result.alignment_rmsd_angstrom
    position = _template_positions(result.index_map)
    bonds = view.forming_bonds
    bonds_kept = all(i in position and j in position for i, j in bonds)
    data.update(
        chosen_order_index=index,
        alignment_rmsd_angstrom=rmsd,
        min_interatomic_distance_angstrom=result.min_interatomic_distance_angstrom,
        close_contact_count=len(result.close_contacts),
        index_map=result.index_map,
        product_charge=result.product_charge,
        product_multiplicity=result.product.spin_multiplicity,
        mapped_forming_bonds=(
            [(position[i], position[j]) for i, j in bonds] if bonds_kept else None
        ),
        constrained_core_product_indices=result.constrained_core_product_indices,
        whole_input_charge_sum_holds_bool=result.whole_input_charge_sum_holds_bool,
    )
    if rmsd > max_rmsd:
        return refused("alignment_rmsd")
    if first_eligible is not None and (
        result.product_charge != first_eligible.product_charge
        or Counter(result.product.symbols) != Counter(first_eligible.product.symbols)
    ):
        return refused("composition_mismatch")
    if not bonds_kept:
        return refused("forming_bond_deleted")
    return GraftRecord.model_validate({**data, "status": "ok"}), result


def _candidate_graph(
    reference: ReactionGraph, candidate_id: str, eligible: dict[str, list[_Eligible]]
) -> ReactionGraph:
    """Replace each covered node's templates by its eligible products, ranked 1..k."""
    nodes: list[ReactionNode] = []
    for node in reference.nodes:
        if node.id not in eligible:
            nodes.append(node)
            continue
        templates = [
            TemplateGeometry(
                id=f"{item.template.id}__{candidate_id}",
                rank=rank,
                components=[
                    Component(
                        state=item.result.product,
                        count=1,
                        label=item.template.components[0].label,
                    )
                ],
            )
            for rank, item in enumerate(eligible[node.id], start=1)
        ]
        # Node stages are shared by its templates (checked equal). Defaults are copied onto the
        # node only when they freeze atoms.
        stages: list[StageConfig] | None = eligible[node.id][0].stages
        if node.stages is None and not any(s.frozen_atom_indices for s in reference.default_stages):
            stages = None
        nodes.append(
            ReactionNode.model_validate({**dict(node), "templates": templates, "stages": stages})
        )
    return ReactionGraph.model_validate(
        {**dict(reference), "name": f"{reference.name}__{candidate_id}", "nodes": nodes}
    )


def _cross_node_failure(
    graph: ReactionGraph, selectivity_sets: Sequence[SelectivitySet]
) -> str | None:
    """Return the first failed cross-node check of a candidate graph (mission G3, R3).

    The rank-1 templates of a set's competing TS nodes must share composition, charge and
    multiplicity, and match the sum over its reactant nodes in composition and charge.
    """
    best = {n.id: min(n.templates, key=lambda t: t.rank) for n in graph.nodes}
    for selectivity_set in sorted(selectivity_sets, key=lambda s: s.id):
        ts = [best[i] for i in sorted({p.node_id for p in selectivity_set.pathways})]
        if not ts:
            continue
        name = selectivity_set.id
        if any(t.element_counts != ts[0].element_counts for t in ts):
            return f"ts_composition_mismatch:{name}"
        if any(t.total_charge != ts[0].total_charge for t in ts):
            return f"ts_charge_mismatch:{name}"
        if any(_multiplicities(t) != _multiplicities(ts[0]) for t in ts):
            return f"ts_multiplicity_mismatch:{name}"
        reactants = [best[i] for i in selectivity_set.reactant_node_ids]
        composition: Counter[str] = Counter()
        for reactant in reactants:
            composition.update(reactant.element_counts)
        if composition != ts[0].element_counts:
            return f"reactant_composition_mismatch:{name}"
        if sum(r.total_charge for r in reactants) != ts[0].total_charge:
            return f"reactant_charge_mismatch:{name}"
    return None


def _multiplicities(template: TemplateGeometry) -> list[int]:
    """Return the multiplicity of every species of a template, sorted."""
    return sorted(c.state.spin_multiplicity for c in template.components for _ in range(c.count))
