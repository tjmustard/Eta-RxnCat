"""Unit tests for MolecularState, AtomMappingSpec, ReactionGraph, and stage-decomposed caching."""

from pathlib import Path

import pytest

from eta_rxncat.core.models import (
    AtomMappingSpec,
    MolecularState,
    NodeKind,
    SolvationSpec,
    StageConfig,
    StageKind,
)
from eta_rxncat.core.reaction_graph import (
    ReactionEdge,
    ReactionGraph,
    ReactionNode,
    TemplateGeometry,
)
from eta_rxncat.store.artifact_store import ArtifactStore, StageCacheKey


def _sample_water(charge: int = 0, mult: int = 1) -> MolecularState:
    return MolecularState(
        name="water",
        symbols=["O", "H", "H"],
        coordinates=[
            [0.0, 0.0, 0.1173],
            [0.0, 0.7572, -0.4692],
            [0.0, -0.7572, -0.4692],
        ],
        charge=charge,
        spin_multiplicity=mult,
        active_atom_indices=[0, 1],
    )


def test_molecular_state_requires_charge_and_multiplicity() -> None:
    state = _sample_water(charge=-1, mult=2)
    assert state.charge == -1
    assert state.spin_multiplicity == 2
    assert state.coords_array().shape == (3, 3)


def test_atom_mapping_spec_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="overlap"):
        AtomMappingSpec(
            keep_atoms=[0, 1],
            delete_atoms=[1, 2],
            alignment_atoms=[0, 1, 2],
        )


def test_reaction_graph_yaml_roundtrip_and_priority_order(tmp_path: Path) -> None:
    water = _sample_water()
    mapping = AtomMappingSpec(keep_atoms=[0, 1], delete_atoms=[2], alignment_atoms=[0, 1, 2])
    tmpl = TemplateGeometry(template_id="t1", structure=water, mapping=mapping)

    graph = ReactionGraph(
        name="test_cycle",
        default_stages=[
            StageConfig(stage=StageKind.GEOMETRY_OPT, engine="uma", method="uma-s-1.2.1"),
            StageConfig(stage=StageKind.FREQUENCY, engine="uma", method="uma-s-1.2.1"),
        ],
        nodes=[
            ReactionNode(node_id="int_1", label="Intermediate 1", kind=NodeKind.INTERMEDIATE, priority=2, templates=[tmpl]),
            ReactionNode(node_id="ts_sel", label="Selectivity TS", kind=NodeKind.TRANSITION_STATE, priority=1, templates=[tmpl]),
            ReactionNode(node_id="react", label="Reactant", kind=NodeKind.REACTANT, priority=1, templates=[tmpl]),
        ],
        edges=[
            ReactionEdge(source_id="react", target_id="ts_sel"),
            ReactionEdge(source_id="ts_sel", target_id="int_1"),
        ],
    )

    yaml_path = tmp_path / "graph.yaml"
    yaml_path.write_text(graph.to_yaml(), encoding="utf-8")

    loaded = ReactionGraph.from_file(yaml_path)
    ordered_ids = [n.node_id for n in loaded.execution_order()]
    assert ordered_ids == ["ts_sel", "react", "int_1"]


def test_stage_decomposed_cache_incremental_solvation(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts.sqlite")
    state = _sample_water()

    opt_stage = StageConfig(stage=StageKind.GEOMETRY_OPT, engine="pyscf", method="B3LYP", basis="def2-SVP")
    solv_sp_stage = StageConfig(
        stage=StageKind.SINGLE_POINT,
        engine="pyscf",
        method="wB97X-D3BJ",
        basis="def2-TZVPP",
        solvation=SolvationSpec(model="ddcosmo", solvent="toluene"),
    )

    opt_key = StageCacheKey.build(state, opt_stage)
    assert store.get(opt_key) is None
    store.put(opt_key, opt_stage, {"energy_hartree": -76.38})

    # Resubmission hits opt_key and misses only the newly appended solvation SP stage
    assert store.get(opt_key) == {"energy_hartree": -76.38}
    solv_key = StageCacheKey.build(state, solv_sp_stage)
    assert store.get(solv_key) is None
