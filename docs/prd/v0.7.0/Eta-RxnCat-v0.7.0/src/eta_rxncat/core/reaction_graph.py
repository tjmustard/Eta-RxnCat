"""Priority-gated ReactionGraph schema with multi-template mapping and YAML/JSON I/O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from eta_rxncat.core.models import (
    AtomMappingSpec,
    MolecularState,
    NodeKind,
    StageConfig,
    ThermoConfig,
)


class TemplateGeometry(BaseModel):
    """Reference 3D geometry and atom surgery rules for mapping new catalysts/substrates."""

    template_id: str
    structure: MolecularState
    mapping: AtomMappingSpec
    priority_rank: int = Field(
        default=1,
        ge=1,
        description="Lower rank is tried first when multiple templates exist for a node.",
    )


class PruningRule(BaseModel):
    """Conditional gating rule evaluated after high-priority nodes complete."""

    rule_id: str
    metric: Literal["delta_g_dagger_kcal", "delta_delta_g_dagger_kcal", "ee_percent", "tof_s_inv"]
    reference_node_id: str
    target_node_id: str | None = None
    operator: Literal["lt", "le", "gt", "ge"]
    threshold: float
    on_fail: Literal["skip_remaining_nodes", "flag_and_continue"] = "skip_remaining_nodes"


class ReactionNode(BaseModel):
    """Single mechanistic state (reactant, intermediate, TS, product, or off-cycle sink)."""

    node_id: str
    label: str
    kind: NodeKind
    priority: int = Field(
        default=1,
        ge=1,
        description="Execution tier (1 = highest importance, executed first to gate downstream steps).",
    )
    stoichiometry_multipliers: list[int] = Field(
        default_factory=lambda: [1],
        description="Stoichiometric counts for multi-molecule separated states (e.g., [1, 1] for A + B).",
    )
    templates: list[TemplateGeometry] = Field(..., min_length=1)
    stages: list[StageConfig] = Field(
        default_factory=list,
        description="Node-specific stage overrides; falls back to ReactionGraph.default_stages if empty.",
    )
    notes: str = ""

    @model_validator(mode="after")
    def _validate_templates_and_stoich(self) -> ReactionNode:
        if len(self.stoichiometry_multipliers) != len(self.templates) and len(
            self.stoichiometry_multipliers
        ) != 1:
            raise ValueError(
                "stoichiometry_multipliers must have length 1 or match number of templates."
            )
        for tmpl in self.templates:
            n_atoms = len(tmpl.structure.symbols)
            all_idx = (
                tmpl.mapping.keep_atoms
                + tmpl.mapping.delete_atoms
                + tmpl.mapping.alignment_atoms
                + tmpl.mapping.attachment_anchors
            )
            for idx in all_idx:
                if idx < 0 or idx >= n_atoms:
                    raise ValueError(
                        f"Template '{tmpl.template_id}' index {idx} out of bounds for {n_atoms} atoms."
                    )
        return self


class ReactionEdge(BaseModel):
    """Directed mechanistic step connecting two ReactionNodes."""

    source_id: str
    target_id: str
    step_label: str = ""
    is_reversible: bool = True


class ReactionGraph(BaseModel):
    """Top-level reaction network specification authored in YAML or JSON."""

    name: str
    description: str = ""
    default_stages: list[StageConfig] = Field(..., min_length=1)
    thermo: ThermoConfig = Field(default_factory=ThermoConfig)
    nodes: list[ReactionNode] = Field(..., min_length=1)
    edges: list[ReactionEdge] = Field(default_factory=list)
    pruning_rules: list[PruningRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_graph_references(self) -> ReactionGraph:
        node_ids = [n.node_id for n in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("Duplicate node_id entries found in ReactionGraph.")
        valid_ids = set(node_ids)

        for edge in self.edges:
            if edge.source_id not in valid_ids or edge.target_id not in valid_ids:
                raise ValueError(
                    f"Edge ({edge.source_id} -> {edge.target_id}) references unknown node_id."
                )

        for rule in self.pruning_rules:
            if rule.reference_node_id not in valid_ids:
                raise ValueError(f"PruningRule '{rule.rule_id}' references unknown node '{rule.reference_node_id}'.")
            if rule.target_node_id is not None and rule.target_node_id not in valid_ids:
                raise ValueError(f"PruningRule '{rule.rule_id}' references unknown target '{rule.target_node_id}'.")
        return self

    def effective_stages(self, node_id: str) -> list[StageConfig]:
        """Return node-specific stages if defined, otherwise graph default_stages."""
        node = self.get_node(node_id)
        return node.stages if node.stages else self.default_stages

    def get_node(self, node_id: str) -> ReactionNode:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(f"Unknown node_id: {node_id}")

    def execution_order(self) -> list[ReactionNode]:
        """Sort nodes by ascending priority tier (1 first), preserving declaration order within tiers."""
        return sorted(self.nodes, key=lambda n: n.priority)

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2)

    @classmethod
    def from_file(cls, path: Path | str) -> ReactionGraph:
        file_path = Path(path)
        raw_text = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(raw_text)
        elif file_path.suffix.lower() == ".json":
            data = json.loads(raw_text)
        else:
            raise ValueError(f"Unsupported graph file extension: {file_path.suffix}")
        return cls.model_validate(data)
