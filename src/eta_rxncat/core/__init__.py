"""Core data contracts and the ReactionGraph loader (v0.1.0)."""

from eta_rxncat.core.elements import ATOMIC_NUMBERS, ELEMENT_SYMBOLS
from eta_rxncat.core.graph import (
    Component,
    NodeKind,
    PruningRule,
    ReactionEdge,
    ReactionGraph,
    ReactionNode,
    TemplateGeometry,
)
from eta_rxncat.core.io import GraphValidationError, dump_reaction_graph_json, load_reaction_graph
from eta_rxncat.core.models import (
    AtomMappingSpec,
    EngineIdentity,
    EngineTag,
    MolecularState,
    Solvation,
    SolvationModel,
    StageConfig,
    StageKind,
    ThermoConfig,
)

__all__ = [
    "ATOMIC_NUMBERS",
    "ELEMENT_SYMBOLS",
    "AtomMappingSpec",
    "Component",
    "EngineIdentity",
    "EngineTag",
    "GraphValidationError",
    "MolecularState",
    "NodeKind",
    "PruningRule",
    "ReactionEdge",
    "ReactionGraph",
    "ReactionNode",
    "Solvation",
    "SolvationModel",
    "StageConfig",
    "StageKind",
    "TemplateGeometry",
    "ThermoConfig",
    "dump_reaction_graph_json",
    "load_reaction_graph",
]
