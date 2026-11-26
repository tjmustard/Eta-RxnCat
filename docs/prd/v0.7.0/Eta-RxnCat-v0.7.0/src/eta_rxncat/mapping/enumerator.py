"""Combinatorial R-group/ligand enumeration across ReactionGraphs and multi-template ranking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from eta_rxncat.core.models import AtomMappingSpec, MolecularState
from eta_rxncat.core.reaction_graph import ReactionGraph, ReactionNode, TemplateGeometry
from eta_rxncat.mapping.core_mapper import graft_substituent_onto_template


class SubstituentCandidate(BaseModel):
    """Library entry representing an R-group or ligand fragment to graft onto a ReactionGraph."""

    candidate_id: str
    structure: MolecularState
    mapping: AtomMappingSpec
    charge_delta: int = Field(
        default=0,
        description="Net formal charge change applied when replacing the leaving group with this fragment.",
    )


def select_best_template(
    node: ReactionNode,
    candidate: SubstituentCandidate | None = None,
) -> TemplateGeometry:
    """Select highest-priority template (or lowest alignment RMSD template when candidate is provided)."""
    ranked = sorted(node.templates, key=lambda t: t.priority_rank)
    if candidate is None or len(ranked) == 1:
        return ranked[0]

    best_tmpl = ranked[0]
    best_rmsd = float("inf")
    for tmpl in ranked:
        if len(tmpl.mapping.alignment_atoms) != len(candidate.mapping.alignment_atoms):
            continue
        _, rmsd = graft_substituent_onto_template(
            tmpl.structure,
            tmpl.mapping,
            candidate.structure,
            candidate.mapping,
            charge_delta=candidate.charge_delta,
        )
        if rmsd < best_rmsd:
            best_rmsd = rmsd
            best_tmpl = tmpl
    return best_tmpl


def enumerate_reaction_graphs(
    reference_graph: ReactionGraph,
    library: list[SubstituentCandidate],
    target_node_ids: list[str] | None = None,
) -> list[ReactionGraph]:
    """Generate one enumerated ReactionGraph per SubstituentCandidate across specified nodes."""
    target_set = set(target_node_ids) if target_node_ids is not None else {n.node_id for n in reference_graph.nodes}
    enumerated: list[ReactionGraph] = []

    for cand in library:
        new_nodes: list[ReactionNode] = []
        for node in reference_graph.nodes:
            if node.node_id not in target_set:
                new_nodes.append(node.model_copy(deep=True))
                continue

            tmpl = select_best_template(node, cand)
            mapped_struct, rmsd = graft_substituent_onto_template(
                tmpl.structure,
                tmpl.mapping,
                cand.structure,
                cand.mapping,
                charge_delta=cand.charge_delta,
                new_name=f"{node.node_id}_{cand.candidate_id}",
            )
            n_mapped = len(mapped_struct.symbols)
            identity_spec = AtomMappingSpec(
                keep_atoms=list(range(n_mapped)),
                delete_atoms=[],
                alignment_atoms=list(range(min(3, n_mapped))),
            )
            new_tmpl = TemplateGeometry(
                template_id=f"{tmpl.template_id}_{cand.candidate_id}",
                structure=mapped_struct,
                mapping=identity_spec,
                priority_rank=1,
            )
            new_nodes.append(
                node.model_copy(
                    update={
                        "templates": [new_tmpl],
                        "notes": f"{node.notes} [enumerated={cand.candidate_id}, align_rmsd={rmsd:.4f}A]".strip(),
                    }
                )
            )

        enumerated.append(
            reference_graph.model_copy(
                update={
                    "name": f"{reference_graph.name}__{cand.candidate_id}",
                    "nodes": new_nodes,
                }
            )
        )

    return enumerated
