"""Tests for ReactionGraph validation and the YAML/JSON loader."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from eta_rxncat.core import (
    GraphValidationError,
    ReactionGraph,
    dump_reaction_graph_json,
    load_reaction_graph,
)

EXAMPLE = Path(__file__).parents[2] / "data" / "reaction_graphs" / "example_reaction_graph.yaml"

HYDROGEN = {"symbols": ["H"], "coordinates": [[0.0, 0.0, 0.0]], "charge": 0, "spin_multiplicity": 2}


def node(node_id: str, priority: int = 1, **overrides: Any) -> dict[str, Any]:
    """Return a one-template node holding a hydrogen atom, with overrides applied."""
    data: dict[str, Any] = {
        "id": node_id,
        "label": node_id,
        "kind": "intermediate",
        "priority": priority,
        "templates": [{"id": "t1", "rank": 1, "components": [{"state": HYDROGEN, "count": 1}]}],
    }
    data.update(overrides)
    return data


def graph(**overrides: Any) -> dict[str, Any]:
    """Return a valid three-node chain A -> B -> C, with overrides applied."""
    data: dict[str, Any] = {
        "schema_version": 1,
        "name": "chain",
        "nodes": [node("A"), node("B"), node("C", priority=2)],
        "edges": [{"source": "A", "target": "B"}, {"source": "B", "target": "C"}],
    }
    data.update(overrides)
    return data


def load_dict(tmp_path: Path, data: dict[str, Any]) -> ReactionGraph:
    """Write ``data`` as JSON and load it through :func:`load_reaction_graph`."""
    path = tmp_path / "graph.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_reaction_graph(path)


def test_valid_chain_loads(tmp_path: Path) -> None:
    """The baseline graph validates."""
    assert load_dict(tmp_path, graph()).name == "chain"


def test_duplicate_node_id(tmp_path: Path) -> None:
    """Two nodes with one id raise, naming the id."""
    data = graph(nodes=[node("A"), node("B"), node("A")], edges=[])
    with pytest.raises(GraphValidationError, match="duplicate node ids.*'A'"):
        load_dict(tmp_path, data)


def test_unknown_edge_endpoint(tmp_path: Path) -> None:
    """An edge to a missing node raises, naming the id."""
    data = graph(edges=[{"source": "A", "target": "Z"}])
    with pytest.raises(GraphValidationError, match="unknown node id 'Z'"):
        load_dict(tmp_path, data)


def test_self_loop(tmp_path: Path) -> None:
    """An edge from a node to itself raises."""
    data = graph(edges=[{"source": "B", "target": "B"}])
    with pytest.raises(GraphValidationError, match="B -> B is a self-loop"):
        load_dict(tmp_path, data)


def test_duplicate_edge(tmp_path: Path) -> None:
    """The same (source, target) pair twice raises."""
    data = graph(
        edges=[{"source": "A", "target": "B"}, {"source": "A", "target": "B", "label": "x"}]
    )
    with pytest.raises(GraphValidationError, match="duplicate edge A -> B"):
        load_dict(tmp_path, data)


def test_undefined_pruning_rule_reference(tmp_path: Path) -> None:
    """A node referencing a rule the graph does not define raises, naming both."""
    data = graph(nodes=[node("A", pruning_rules=["gate"]), node("B"), node("C")])
    with pytest.raises(GraphValidationError, match=r"node 'A'.*'gate'"):
        load_dict(tmp_path, data)


def test_duplicate_pruning_rule_id(tmp_path: Path) -> None:
    """Two pruning rules with one id raise."""
    rule = {"id": "gate", "description": "d"}
    with pytest.raises(GraphValidationError, match="duplicate pruning rule ids.*'gate'"):
        load_dict(tmp_path, graph(pruning_rules=[rule, rule]))


def test_templates_with_different_total_charge(tmp_path: Path) -> None:
    """Templates of one node must share total charge."""
    proton = {
        "symbols": ["H"],
        "coordinates": [[0.0, 0.0, 0.0]],
        "charge": 1,
        "spin_multiplicity": 1,
    }
    a = node("A")
    a["templates"].append({"id": "t2", "rank": 2, "components": [{"state": proton, "count": 1}]})
    with pytest.raises(GraphValidationError, match=r"node 'A'.*'t2'.*total charge"):
        load_dict(tmp_path, graph(nodes=[a, node("B"), node("C")]))


def test_templates_with_different_elements(tmp_path: Path) -> None:
    """Templates of one node must share their element multiset (count x symbols)."""
    a = node("A")
    a["templates"].append({"id": "t2", "rank": 2, "components": [{"state": HYDROGEN, "count": 2}]})
    with pytest.raises(GraphValidationError, match=r"node 'A'.*'t2'.*element"):
        load_dict(tmp_path, graph(nodes=[a, node("B"), node("C")]))


def test_duplicate_template_rank(tmp_path: Path) -> None:
    """Two templates of one node with the same rank raise, naming the node."""
    a = node("A")
    a["templates"].append(copy.deepcopy(a["templates"][0]) | {"id": "t2"})
    with pytest.raises(GraphValidationError, match=r"node 'A'.*duplicate template ranks"):
        load_dict(tmp_path, graph(nodes=[a, node("B"), node("C")]))


def test_bad_node_id_pattern(tmp_path: Path) -> None:
    """Node ids must start with a letter."""
    with pytest.raises(GraphValidationError, match="nodes.0.id"):
        load_dict(tmp_path, graph(nodes=[node("1A")], edges=[]))


def test_schema_version_required(tmp_path: Path) -> None:
    """``schema_version`` is required and must be 1."""
    data = graph()
    del data["schema_version"]
    with pytest.raises(GraphValidationError, match="schema_version"):
        load_dict(tmp_path, data)
    with pytest.raises(GraphValidationError, match="schema_version"):
        load_dict(tmp_path, graph(schema_version=2))


def test_cycle_is_valid(tmp_path: Path) -> None:
    """A catalytic cycle A -> B -> C -> A validates."""
    edges = [
        {"source": "A", "target": "B"},
        {"source": "B", "target": "C"},
        {"source": "C", "target": "A"},
    ]
    assert len(load_dict(tmp_path, graph(edges=edges)).edges) == 3


def test_priority_order(tmp_path: Path) -> None:
    """Node ids sort by (priority, id): tiers {B:1, A:1, C:2} give A, B, C."""
    data = graph(nodes=[node("B", 1), node("A", 1), node("C", 2)], edges=[])
    assert load_dict(tmp_path, data).priority_order() == ["A", "B", "C"]


def test_yaml_duplicate_key(tmp_path: Path) -> None:
    """A YAML mapping with ``charge:`` twice raises, naming the key."""
    text = EXAMPLE.read_text(encoding="utf-8").replace(
        "              charge: -1\n", "              charge: -1\n              charge: 0\n", 1
    )
    path = tmp_path / "dup.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(GraphValidationError, match=r"duplicate key 'charge' at line \d+"):
        load_reaction_graph(path)


def test_json_duplicate_key(tmp_path: Path) -> None:
    """A JSON object with a duplicate key raises, naming the key."""
    path = tmp_path / "dup.json"
    path.write_text(
        '{"schema_version": 1, "name": "a", "name": "b", "nodes": []}', encoding="utf-8"
    )
    with pytest.raises(GraphValidationError, match="duplicate key 'name'"):
        load_reaction_graph(path)


def test_unsupported_extension(tmp_path: Path) -> None:
    """``graph.toml`` raises, naming ``.toml``."""
    path = tmp_path / "graph.toml"
    path.write_text("name = 'x'\n", encoding="utf-8")
    with pytest.raises(GraphValidationError, match=r"\.toml"):
        load_reaction_graph(path)


def test_missing_file(tmp_path: Path) -> None:
    """An unreadable file raises GraphValidationError naming the path."""
    with pytest.raises(GraphValidationError, match="missing.yaml"):
        load_reaction_graph(tmp_path / "missing.yaml")


@pytest.mark.parametrize("name", ["bad.yaml", "bad.json"])
def test_non_utf8_file(tmp_path: Path, name: str) -> None:
    """A file that is not valid UTF-8 raises GraphValidationError naming the path."""
    path = tmp_path / name
    path.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(GraphValidationError, match=rf"{name}: file is not valid UTF-8"):
        load_reaction_graph(path)


@pytest.mark.parametrize("name", ["deep.yaml", "deep.json"])
def test_deeply_nested_input(tmp_path: Path, name: str) -> None:
    """Pathologically nested input raises GraphValidationError, not RecursionError."""
    path = tmp_path / name
    path.write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    with pytest.raises(GraphValidationError, match=rf"{name}: "):
        load_reaction_graph(path)


def test_yaml_syntax_error(tmp_path: Path) -> None:
    """Invalid YAML raises GraphValidationError."""
    path = tmp_path / "bad.yaml"
    path.write_text("name: [unclosed\n", encoding="utf-8")
    with pytest.raises(GraphValidationError, match="syntax error"):
        load_reaction_graph(path)


def test_example_graph_loads_and_round_trips(tmp_path: Path) -> None:
    """The example graph loads, and YAML -> model -> JSON -> model is equal."""
    graph_model = load_reaction_graph(EXAMPLE)
    kinds = {n.kind for n in graph_model.nodes}
    assert "transition_state" in kinds and len(graph_model.nodes) >= 3
    assert len({n.priority for n in graph_model.nodes}) >= 2 and len(graph_model.edges) >= 2
    path = tmp_path / "example.json"
    path.write_text(dump_reaction_graph_json(graph_model), encoding="utf-8")
    assert load_reaction_graph(path) == graph_model


def test_core_import_loads_no_heavy_modules() -> None:
    """Importing ``eta_rxncat.core`` loads none of the heavy backends."""
    code = (
        "import eta_rxncat.core, sys; "
        "assert not {'torch','pyscf','rdkit','gpu4pyscf','cupy'} & set(sys.modules)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_no_unsafe_yaml_or_pickle_in_core() -> None:
    """``eta_rxncat.core`` never calls yaml.load/full_load/unsafe_load or uses pickle."""
    core = Path(__file__).parents[3] / "src" / "eta_rxncat" / "core"
    result = subprocess.run(
        ["grep", "-rnE", r"yaml\.(load|full_load|unsafe_load)\(|pickle", str(core)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout
