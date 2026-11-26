"""Unit tests for v0.7.0 combinatorial ReactionGraph enumeration and multi-template selection."""

from eta_rxncat.core.models import (
    AtomMappingSpec,
    MolecularState,
    NodeKind,
    StageConfig,
    StageKind,
)
from eta_rxncat.core.reaction_graph import ReactionGraph, ReactionNode, TemplateGeometry
from eta_rxncat.mapping.enumerator import SubstituentCandidate, enumerate_reaction_graphs


def test_enumerate_reaction_graphs_propagates_charge_and_geometry() -> None:
    tmpl_struct = MolecularState(
        name="ref_core",
        symbols=["C", "H", "H", "H", "Cl"],
        coordinates=[
            [0.0, 0.0, 0.0],
            [1.09, 0.0, 0.0],
            [-0.36, 1.03, 0.0],
            [-0.36, -0.51, 0.89],
            [0.0, 0.0, -1.78],
        ],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0, 1],
    )
    tmpl = TemplateGeometry(
        template_id="ref_t1",
        structure=tmpl_struct,
        mapping=AtomMappingSpec(keep_atoms=[0, 1, 2, 3], delete_atoms=[4], alignment_atoms=[0, 1, 2]),
    )
    ref_graph = ReactionGraph(
        name="sn2_screen",
        default_stages=[StageConfig(stage=StageKind.GEOMETRY_OPT, engine="rdkit_ff", method="UFF")],
        nodes=[
            ReactionNode(node_id="ts1", label="TS1", kind=NodeKind.TRANSITION_STATE, priority=1, templates=[tmpl]),
        ],
    )

    cand = SubstituentCandidate(
        candidate_id="fluoro_anionic",
        structure=MolecularState(
            name="sub_f",
            symbols=["C", "H", "H", "H", "F"],
            coordinates=[
                [2.0, 0.0, 0.0],
                [3.09, 0.0, 0.0],
                [1.64, 1.03, 0.0],
                [1.64, -0.51, 0.89],
                [2.0, 0.0, -1.35],
            ],
            charge=0,
            spin_multiplicity=1,
        ),
        mapping=AtomMappingSpec(keep_atoms=[4], delete_atoms=[0, 1, 2, 3], alignment_atoms=[0, 1, 2]),
        charge_delta=-1,
    )

    graphs = enumerate_reaction_graphs(ref_graph, [cand])
    assert len(graphs) == 1
    g_enum = graphs[0]
    assert g_enum.name == "sn2_screen__fluoro_anionic"
    mapped_st = g_enum.get_node("ts1").templates[0].structure
    assert mapped_st.symbols == ["C", "H", "H", "H", "F"]
    assert mapped_st.charge == -1
