"""ReactionGraph contracts: templates, nodes, edges, pruning rules and the graph itself."""

from collections import Counter
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from eta_rxncat.core.models import (
    AtomMappingSpec,
    CoreModel,
    MolecularState,
    PositiveFiniteFloat,
    PositiveInt,
    ScalarValue,
    StageConfig,
    ThermoConfig,
)

NodeKind = Literal["reactant", "intermediate", "transition_state", "product", "off_cycle_sink"]
"""Chemical role of a node in the mechanism."""


class Component(CoreModel):
    """One species of a (possibly separated) state, with its stoichiometric count.

    Attributes:
        state: The species' structure.
        count: Stoichiometric coefficient (>= 1).
        label: Optional human-readable name.
    """

    state: MolecularState
    count: PositiveInt
    label: str | None = None


class TemplateGeometry(CoreModel):
    """One candidate geometry of a node; a node ranks alternative templates.

    The template's atom index space is the concatenation of its components' atoms in listed
    order, each component once regardless of ``count``.

    Attributes:
        id: Template identifier, unique within its node.
        rank: Preference order (1 is tried first), unique within its node.
        components: The species making up this geometry.
        mapping: Optional atom-surgery lists over the template's index space.
    """

    id: str
    rank: PositiveInt
    components: list[Component] = Field(min_length=1)
    mapping: AtomMappingSpec | None = None

    @property
    def atom_count(self) -> int:
        """Number of atoms in the template's index space."""
        return sum(len(c.state.symbols) for c in self.components)

    @property
    def total_charge(self) -> int:
        """Sum of ``count x charge`` over the components."""
        return sum(c.count * c.state.charge for c in self.components)

    @property
    def element_counts(self) -> Counter[str]:
        """Element multiset: ``count x symbols`` summed over the components."""
        counts: Counter[str] = Counter()
        for component in self.components:
            for symbol in component.state.symbols:
                counts[symbol] += component.count
        return counts

    @model_validator(mode="after")
    def _check_mapping(self) -> Self:
        if self.mapping is not None:
            try:
                self.mapping.check_atom_count(self.atom_count)
            except ValueError as exc:
                raise ValueError(f"template '{self.id}': {exc}") from exc
        return self


class ReactionNode(CoreModel):
    """A stationary point or separated state of the mechanism.

    Attributes:
        id: Node identifier (``^[A-Za-z][A-Za-z0-9_.-]*$``).
        label: Human-readable name.
        kind: Chemical role.
        priority: Execution tier (1 runs first).
        templates: Ranked alternative geometries; all share total charge and element multiset.
        stages: Node-specific stages; ``None`` means the graph's ``default_stages``.
        pruning_rules: Ids of graph pruning rules that apply to this node.
        pathway: Optional label of the competing pathway this node belongs to (v0.6.0); the
            ``PathwayPruningRule`` of the graph names pathways by it. ``None`` for every
            existing graph.
    """

    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")
    label: str
    kind: NodeKind
    priority: PositiveInt
    templates: list[TemplateGeometry] = Field(min_length=1)
    stages: list[StageConfig] | None = None
    pruning_rules: list[str] = Field(default_factory=list)
    pathway: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")

    @model_validator(mode="after")
    def _check_templates(self) -> Self:
        ids = Counter(t.id for t in self.templates)
        dup_ids = sorted(i for i, n in ids.items() if n > 1)
        if dup_ids:
            raise ValueError(f"node '{self.id}': duplicate template ids {dup_ids}")
        ranks = Counter(t.rank for t in self.templates)
        dup_ranks = sorted(r for r, n in ranks.items() if n > 1)
        if dup_ranks:
            raise ValueError(f"node '{self.id}': duplicate template ranks {dup_ranks}")
        first = self.templates[0]
        for other in self.templates[1:]:
            if other.total_charge != first.total_charge:
                raise ValueError(
                    f"node '{self.id}': template '{other.id}' has total charge "
                    f"{other.total_charge}, template '{first.id}' has {first.total_charge}"
                )
            if other.element_counts != first.element_counts:
                raise ValueError(
                    f"node '{self.id}': template '{other.id}' has a different element "
                    f"composition from template '{first.id}'"
                )
        return self


class ReactionEdge(CoreModel):
    """A directed mechanistic step between two nodes.

    Attributes:
        source: Source node id.
        target: Target node id.
        label: Optional step name.
    """

    source: str
    target: str
    label: str | None = None


class PruningRule(CoreModel):
    """A named gating rule; validated as a schema and by reference, never evaluated in v0.1.0.

    Attributes:
        id: Rule identifier, unique within the graph.
        description: What the rule gates.
        parameters: Scalar rule parameters.
    """

    id: str
    description: str
    parameters: dict[str, ScalarValue] = Field(default_factory=dict)


class PathwayPruningRule(CoreModel):
    """A typed, evaluable rule: prune the computed minor pathway of two competing pathways (v0.6.0).

    Unlike the free-form ``PruningRule`` (inert), this one is evaluated by the selectivity runner
    once every priority-1 pathway has its TS ensemble. There is no default threshold.

    Attributes:
        id: Rule identifier, unique across both rule lists of the graph.
        metric: The compared quantity; only the TS free-energy gap, in kcal/mol.
        pathways: The two competing pathway labels (distinct).
        threshold_kcal_mol: The gap above which the minor pathway is pruned (> 0, required).
        prune: What is pruned: the minor pathway's nodes with ``priority >= 2``.
    """

    id: str
    metric: Literal["ddG_dagger_kcal_mol"]
    pathways: tuple[
        Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")],
        Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$")],
    ]
    threshold_kcal_mol: PositiveFiniteFloat
    prune: Literal["minor_pathway_priority_ge_2"]

    @field_validator("pathways")
    @classmethod
    def _distinct(cls, value: tuple[str, str]) -> tuple[str, str]:
        if value[0] == value[1]:
            raise ValueError(f"pathways must be two distinct labels, got {value}")
        return value


class ReactionGraph(CoreModel):
    """A reaction network: nodes, directed edges (cycles allowed), stages and thermo settings.

    Attributes:
        schema_version: Graph file schema version; only ``1`` exists.
        name: Graph name.
        nodes: The nodes, with unique ids.
        edges: Directed edges; no self-loops, no duplicate (source, target) pairs.
        default_stages: Stages for nodes whose ``stages`` is ``None``.
        thermo: Thermochemistry settings.
        pruning_rules: Rules that nodes may reference by id.
        pathway_pruning_rules: Typed per-pathway pruning rules (v0.6.0), evaluated by the
            selectivity runner.
    """

    schema_version: Literal[1]
    name: str
    nodes: list[ReactionNode] = Field(min_length=1)
    edges: list[ReactionEdge] = Field(default_factory=list)
    default_stages: list[StageConfig] = Field(default_factory=list)
    thermo: ThermoConfig = Field(default_factory=ThermoConfig)
    pruning_rules: list[PruningRule] = Field(default_factory=list)
    pathway_pruning_rules: list[PathwayPruningRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_graph(self) -> Self:
        node_ids = Counter(n.id for n in self.nodes)
        dup_nodes = sorted(i for i, n in node_ids.items() if n > 1)
        if dup_nodes:
            raise ValueError(f"duplicate node ids {dup_nodes}")
        rule_ids = Counter(r.id for r in self.pruning_rules)
        all_rule_ids = rule_ids + Counter(r.id for r in self.pathway_pruning_rules)
        dup_rules = sorted(i for i, n in all_rule_ids.items() if n > 1)
        if dup_rules:
            raise ValueError(f"duplicate pruning rule ids {dup_rules}")
        seen_edges: set[tuple[str, str]] = set()
        for edge in self.edges:
            for end in (edge.source, edge.target):
                if end not in node_ids:
                    raise ValueError(
                        f"edge {edge.source} -> {edge.target}: unknown node id '{end}'"
                    )
            if edge.source == edge.target:
                raise ValueError(f"edge {edge.source} -> {edge.target} is a self-loop")
            pair = (edge.source, edge.target)
            if pair in seen_edges:
                raise ValueError(f"duplicate edge {edge.source} -> {edge.target}")
            seen_edges.add(pair)
        first_tier = {n.pathway for n in self.nodes if n.priority == 1 and n.pathway is not None}
        for pruning_rule in self.pathway_pruning_rules:
            missing = [p for p in pruning_rule.pathways if p not in first_tier]
            if missing:
                raise ValueError(
                    f"pathway pruning rule '{pruning_rule.id}': pathways {missing} are not the "
                    "pathway of any priority-1 node"
                )
        for node in self.nodes:
            undefined = [r for r in node.pruning_rules if r not in rule_ids]
            if undefined:
                raise ValueError(f"node '{node.id}' references undefined pruning rules {undefined}")
        return self

    def priority_order(self) -> list[str]:
        """Return the node ids sorted by ``(priority, id)``."""
        return [n.id for n in sorted(self.nodes, key=lambda n: (n.priority, n.id))]
