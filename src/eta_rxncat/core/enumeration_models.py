"""Enumeration and fallback contracts: sites, library entries, grafts, candidates (v0.7.0).

Data only: pydantic and the standard library, no numpy and no RDKit (mission G1, R9). The
enumerator and the fallback runner compute the values; these models check their shape and the
cross-references that need no chemistry.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal, Self

from pydantic import (
    Field,
    SerializerFunctionWrapHandler,
    StrictInt,
    field_validator,
    model_serializer,
    model_validator,
)

from eta_rxncat.core.graph import ReactionGraph
from eta_rxncat.core.mapping_models import IndexSource
from eta_rxncat.core.models import (
    AtomMappingSpec,
    CoreModel,
    MolecularState,
    NonNegativeInt,
    PositiveFiniteFloat,
    PositiveInt,
)
from eta_rxncat.core.results import NonNegativeFiniteFloat
from eta_rxncat.core.selectivity_models import SeedCheckDetail

GraftRefusalReason = Literal[
    "graft_input",
    "graft_clash",
    "alignment_rmsd",
    "composition_mismatch",
    "parity",
    "multiplicity_conflict",
    "multi_component_template",
    "site_atom_deleted",
    "forming_bond_deleted",
]
"""The closed set of reasons an enumeration graft is refused (mission §5 "Contracts")."""


def _duplicate_ids(ids: Iterable[str]) -> list[str]:
    """Return the ids that occur more than once, sorted."""
    return sorted(i for i, n in Counter(ids).items() if n > 1)


class SiteTemplateMap(CoreModel):
    """How one substitution site reads on one template (mission R2).

    Attributes:
        node_id: Node of the reference graph.
        template_id: Template of that node.
        template: Keep/delete/alignment lists in the template's index space; ``anchors`` empty.
        constrained_core: Template atoms frozen in the pre-relaxation.
        forming_bonds: Forming bonds in the template's index space: ``(i, j)`` with ``i < j``,
            strictly ascending across pairs.
    """

    node_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    template: AtomMappingSpec
    constrained_core: list[NonNegativeInt]
    forming_bonds: list[tuple[NonNegativeInt, NonNegativeInt]]

    @model_validator(mode="after")
    def _check_map(self) -> Self:
        if self.template.anchors:
            raise ValueError(
                f"template.anchors must be empty (the graft does not use anchors), "
                f"got {self.template.anchors}"
            )
        reversed_pairs = [pair for pair in self.forming_bonds if not pair[0] < pair[1]]
        if reversed_pairs:
            raise ValueError(f"forming_bonds pairs need i < j, got {reversed_pairs}")
        pairs = self.forming_bonds
        if any(a >= b for a, b in zip(pairs, pairs[1:], strict=False)):
            raise ValueError(f"forming_bonds must be sorted and unique, got {pairs}")
        return self


class EnumerationSite(CoreModel):
    """One substitution site, declared on each template it applies to.

    Attributes:
        id: Site identifier, unique within a plan.
        maps: One ``SiteTemplateMap`` per covered (node, template).
    """

    id: str = Field(min_length=1)
    maps: list[SiteTemplateMap]


class LibraryEntry(CoreModel):
    """One fragment that can be grafted onto one site.

    Attributes:
        id: Entry identifier, unique within a plan.
        site_id: The site the entry substitutes.
        fragment: The fragment structure.
        fragment_orders: At least one order of fragment atoms paired with the site's alignment;
            unique. Their length is checked against the site by the enumerator.
        fragment_delete: Further fragment atoms to drop.
        charge_delta: Change of the template's total charge (mission R10).
        multiplicity: Declared ``2S + 1`` of the product; ``None`` inherits the template's.
    """

    id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    fragment: MolecularState
    fragment_orders: list[list[NonNegativeInt]] = Field(min_length=1)
    fragment_delete: list[NonNegativeInt]
    charge_delta: StrictInt = 0
    multiplicity: PositiveInt | None = None

    @field_validator("fragment_orders")
    @classmethod
    def _unique_orders(cls, value: list[list[int]]) -> list[list[int]]:
        if len({tuple(order) for order in value}) != len(value):
            raise ValueError(f"fragment_orders must be unique, got {value}")
        return value


class PathwaySpec(CoreModel):
    """One competing pathway of a selectivity set (mission R2).

    Attributes:
        pathway: The pathway label.
        node_id: The pathway's transition-state node.
        expected_face: The face descriptor the pathway must have, each entry +1 or -1.
    """

    pathway: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    expected_face: tuple[StrictInt, ...] = Field(min_length=1)

    @field_validator("expected_face")
    @classmethod
    def _face(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(entry not in (-1, 1) for entry in value):
            raise ValueError(f"expected_face entries must be +1 or -1, got {value}")
        return value


class SelectivitySet(CoreModel):
    """Competing pathways scored against each other, with their shared reactants.

    Attributes:
        id: Set identifier.
        pathways: The competing pathways.
        reactant_node_ids: Reactant nodes of the set.
    """

    id: str = Field(min_length=1)
    pathways: list[PathwaySpec]
    reactant_node_ids: list[str]


class EnumerationPlan(CoreModel):
    """A reference graph, its substitution sites, the fragment library and the sets to score.

    Attributes:
        reference_graph: The graph whose templates the library substitutes (schema 1, unchanged).
        sites: Substitution sites with unique ids.
        library: Library entries with unique ids, each naming an existing site.
        selectivity_sets: Sets of competing pathways, naming existing nodes.
        max_candidates: Required cap on the candidate count.
    """

    reference_graph: ReactionGraph
    sites: list[EnumerationSite]
    library: list[LibraryEntry]
    selectivity_sets: list[SelectivitySet]
    max_candidates: PositiveInt

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        site_ids = [s.id for s in self.sites]
        if dupes := _duplicate_ids(site_ids):
            raise ValueError(f"duplicate site ids {dupes}")
        if dupes := _duplicate_ids(e.id for e in self.library):
            raise ValueError(f"duplicate library entry ids {dupes}")
        for entry in self.library:
            if entry.site_id not in site_ids:
                raise ValueError(f"entry '{entry.id}': unknown site id '{entry.site_id}'")
        templates = {n.id: {t.id for t in n.templates} for n in self.reference_graph.nodes}
        for site in self.sites:
            for site_map in site.maps:
                if site_map.node_id not in templates:
                    raise ValueError(f"site '{site.id}': unknown node id '{site_map.node_id}'")
                if site_map.template_id not in templates[site_map.node_id]:
                    raise ValueError(
                        f"site '{site.id}': node '{site_map.node_id}' has no template "
                        f"'{site_map.template_id}'"
                    )
        for selectivity_set in self.selectivity_sets:
            named = [
                *(p.node_id for p in selectivity_set.pathways),
                *selectivity_set.reactant_node_ids,
            ]
            unknown = sorted(set(named) - set(templates))
            if unknown:
                raise ValueError(
                    f"selectivity set '{selectivity_set.id}': unknown node ids {unknown}"
                )
        return self


class GraftRecord(CoreModel):
    """What happened when one entry was grafted onto one (node, template).

    A measure is ``None`` when the refusal happened before it could be taken.

    Attributes:
        entry_id: Library entry grafted.
        site_id: Site substituted.
        node_id: Node of the template.
        template_id: Template grafted onto.
        status: ``ok`` or ``refused``.
        reason: Why it was refused; ``None`` when ``ok``.
        order_rmsds_angstrom: One item per fragment order, in declared order: its alignment RMSD
            (Angstrom), or the refusal reason of an order whose graft raised.
        chosen_order_index: Index into ``fragment_orders`` of the winning order.
        alignment_rmsd_angstrom: Alignment RMSD of the winning order.
        min_interatomic_distance_angstrom: Shortest product pair distance.
        close_contact_count: Number of close contacts recorded by the graft.
        index_map: Source of each product atom: ``("template" | "fragment", input index)``.
        product_charge: Formal charge of the product.
        product_multiplicity: ``2S + 1`` of the product.
        mapped_forming_bonds: The map's forming bonds as product indices.
        constrained_core_product_indices: Product indices of the constrained core.
        whole_input_charge_sum_holds_bool: The graft's report of product charge == template +
            fragment charge over the whole inputs; reported, never used. ``None`` when no graft of
            the record returned.
    """

    entry_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    status: Literal["ok", "refused"]
    reason: GraftRefusalReason | None = None
    order_rmsds_angstrom: list[NonNegativeFiniteFloat | GraftRefusalReason] = Field(
        default_factory=list
    )
    chosen_order_index: NonNegativeInt | None = None
    alignment_rmsd_angstrom: NonNegativeFiniteFloat | None = None
    min_interatomic_distance_angstrom: PositiveFiniteFloat | None = None
    close_contact_count: NonNegativeInt | None = None
    index_map: list[tuple[IndexSource, NonNegativeInt]] | None = None
    product_charge: StrictInt | None = None
    product_multiplicity: PositiveInt | None = None
    mapped_forming_bonds: list[tuple[NonNegativeInt, NonNegativeInt]] | None = None
    constrained_core_product_indices: list[NonNegativeInt] | None = None
    whole_input_charge_sum_holds_bool: bool | None = None


class EnumeratedCandidate(CoreModel):
    """One library combination: its graph if usable, and every graft behind it.

    Attributes:
        candidate_id: Deterministic candidate identifier.
        entry_ids_by_site: The entry chosen at each site.
        status: ``ok``, ``unmappable`` or ``inconsistent``.
        detail: Why the candidate is not ``ok``; required then. On an ``ok`` candidate it is
            ``None``, or ``dropped_unlisted:<node>/<template>,…`` naming the unlisted templates of
            covered nodes that were dropped.
        graph: The candidate graph; present exactly when ``status`` is ``ok``.
        records: The graft records.
    """

    candidate_id: str = Field(min_length=1)
    entry_ids_by_site: dict[str, str]
    status: Literal["ok", "unmappable", "inconsistent"]
    detail: str | None = Field(default=None, min_length=1)
    graph: ReactionGraph | None = None
    records: list[GraftRecord]

    @model_validator(mode="after")
    def _check_status(self) -> Self:
        if (self.graph is None) == (self.status == "ok"):
            raise ValueError(
                f"graph must be present exactly when status is ok, not {self.status!r}"
            )
        if self.status != "ok" and self.detail is None:
            raise ValueError(f"detail is required when status is {self.status!r}")
        return self


class EnumerationResult(CoreModel):
    """Every candidate of one enumeration, with the bound on the engine work it implies.

    Attributes:
        candidates: The candidates in deterministic order.
        max_alignment_rmsd_angstrom: The alignment RMSD ceiling used.
        projected_ts_searches: Upper bound on TS searches (mission R11).
    """

    candidates: list[EnumeratedCandidate]
    max_alignment_rmsd_angstrom: PositiveFiniteFloat
    projected_ts_searches: NonNegativeInt


class FallbackAttempt(CoreModel):
    """One template tried as the TS seed of a node.

    Attributes:
        template_id: The template tried.
        rank: Its rank.
        outcome: ``chosen``, ``fell_through`` or ``stopped``.
        reason: Why it was not chosen; ``None`` otherwise.
        wall_time_s: Wall time of the attempt.
        detail: What a seed check found; left out of the serialised form when ``None``.
    """

    template_id: str = Field(min_length=1)
    rank: PositiveInt
    outcome: Literal["chosen", "fell_through", "stopped"]
    reason: str | None = Field(default=None, min_length=1)
    wall_time_s: NonNegativeFiniteFloat
    detail: SeedCheckDetail | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_detail(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.detail is None:
            data.pop("detail", None)
        return data


class FallbackRecord(CoreModel):
    """The ranked attempts at one node and how they ended.

    Attributes:
        node_id: The node.
        attempts: Attempts in rank order (ranks strictly increase).
        chosen_template_id: The template that produced the ensemble.
        stop_reason: Why no template was chosen. Exactly one of this and
            ``chosen_template_id`` is set; with no attempts it is this one.
    """

    node_id: str = Field(min_length=1)
    attempts: list[FallbackAttempt]
    chosen_template_id: str | None = Field(default=None, min_length=1)
    stop_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _check_record(self) -> Self:
        if (self.chosen_template_id is None) == (self.stop_reason is None):
            raise ValueError("exactly one of chosen_template_id and stop_reason must be set")
        if not self.attempts and self.stop_reason is None:
            raise ValueError("a record without attempts needs a stop_reason")
        ranks = [a.rank for a in self.attempts]
        if any(a >= b for a, b in zip(ranks, ranks[1:], strict=False)):
            raise ValueError(f"attempt ranks must strictly increase, got {ranks}")
        return self
