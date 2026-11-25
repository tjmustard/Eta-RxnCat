"""Tests for ReactionNode.pathway, PathwayPruningRule and graph validation (v0.6.0, slice 02)."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from eta_rxncat.core import (
    GraphValidationError,
    PathwayPruningRule,
    PruningRule,
    ReactionGraph,
    ReactionNode,
    load_reaction_graph,
)

TESTS = Path(__file__).resolve().parents[2]
HYDROGEN = {"symbols": ["H"], "coordinates": [[0.0, 0.0, 0.0]], "charge": 0, "spin_multiplicity": 2}


def node(node_id: str, priority: int = 1, **overrides: Any) -> dict[str, Any]:
    """Return a one-template node holding a hydrogen atom, with overrides applied."""
    data: dict[str, Any] = {
        "id": node_id,
        "label": node_id,
        "kind": "transition_state",
        "priority": priority,
        "templates": [{"id": "t1", "rank": 1, "components": [{"state": HYDROGEN, "count": 1}]}],
    }
    data.update(overrides)
    return data


def rule(**overrides: Any) -> dict[str, Any]:
    """Return a valid pathway pruning rule, with overrides applied."""
    data: dict[str, Any] = {
        "id": "endo_exo",
        "metric": "ddG_dagger_kcal_mol",
        "pathways": ["endo", "exo"],
        "threshold_kcal_mol": 1.5,
        "prune": "minor_pathway_priority_ge_2",
    }
    data.update(overrides)
    return data


def graph(**overrides: Any) -> dict[str, Any]:
    """Return a two-pathway graph with one downstream node per pathway."""
    data: dict[str, Any] = {
        "schema_version": 1,
        "name": "competing",
        "nodes": [
            node("TS_endo", pathway="endo"),
            node("TS_exo", pathway="exo"),
            node("P_endo", priority=2, kind="product", pathway="endo"),
            node("P_exo", priority=2, kind="product", pathway="exo"),
            node("Free", priority=2, kind="product"),
        ],
        "pathway_pruning_rules": [rule()],
    }
    data.update(overrides)
    return data


def test_round_trip_json_and_yaml(tmp_path: Path) -> None:
    """A graph with labels and a rule survives dump and reload in both formats."""
    parsed = ReactionGraph.model_validate(graph())
    dumped = parsed.model_dump(mode="json")
    for name, text in (("g.json", json.dumps(dumped)), ("g.yaml", yaml.safe_dump(dumped))):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        assert load_reaction_graph(path) == parsed
    assert parsed.pathway_pruning_rules[0].pathways == ("endo", "exo")
    assert parsed.nodes[4].pathway is None


def test_existing_graph_gets_empty_defaults() -> None:
    """A graph without the new keys loads with pathway None and no pathway rules."""
    data = graph()
    del data["pathway_pruning_rules"]
    for n in data["nodes"]:
        n.pop("pathway", None)
    parsed = ReactionGraph.model_validate(data)
    assert parsed.pathway_pruning_rules == []
    assert all(n.pathway is None for n in parsed.nodes)


def _graph_files() -> list[Path]:
    found = []
    for root in (TESTS / "data", TESTS / "fixtures"):
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".yaml", ".yml", ".json"}:
                continue
            try:
                loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (yaml.YAMLError, UnicodeDecodeError):
                continue
            if isinstance(loaded, dict) and "schema_version" in loaded and "nodes" in loaded:
                found.append(path)
    return found


def test_every_existing_graph_file_still_loads() -> None:
    """Every reaction graph under tests/data and tests/fixtures validates unchanged."""
    files = _graph_files()
    assert any(p.name == "example_reaction_graph.yaml" for p in files)
    for path in files:
        assert load_reaction_graph(path).pathway_pruning_rules == [], path


def test_free_form_pruning_rule_untouched() -> None:
    """The inert PruningRule keeps its fields and still validates."""
    assert set(PruningRule.model_fields) == {"id", "description", "parameters"}
    barrier = PruningRule(id="barrier_gate", description="gate", parameters={"x": 1.0})
    assert barrier.parameters == {"x": 1.0}


@pytest.mark.parametrize(
    "overrides",
    [
        {"threshold_kcal_mol": 0.0},
        {"threshold_kcal_mol": -1.0},
        {"threshold_kcal_mol": float("inf")},
        {"threshold_kcal_mol": float("nan")},
        {"pathways": ["endo", "endo"]},
        {"pathways": ["endo"]},
        {"pathways": ["endo", "exo", "x"]},
        {"pathways": ["endo", "1bad"]},
        {"metric": "ddG"},
        {"prune": "all"},
        {"unknown": 1},
    ],
)
def test_invalid_rule_refused(overrides: dict[str, Any]) -> None:
    """Out-of-range thresholds, bad pathway pairs, unknown literals and extras are refused."""
    with pytest.raises(ValidationError):
        PathwayPruningRule.model_validate(rule(**overrides))


def test_missing_threshold_refused() -> None:
    """The threshold has no default."""
    data = rule()
    del data["threshold_kcal_mol"]
    with pytest.raises(ValidationError, match="threshold_kcal_mol"):
        PathwayPruningRule.model_validate(data)


def test_unknown_pathway_refused() -> None:
    """A rule naming a pathway no priority-1 node carries is refused."""
    with pytest.raises(ValidationError, match="not the pathway of any priority-1 node"):
        ReactionGraph.model_validate(graph(pathway_pruning_rules=[rule(pathways=["endo", "nope"])]))


def test_pathway_only_on_later_tier_refused() -> None:
    """A pathway label present only on priority >= 2 nodes does not satisfy the rule."""
    data = graph()
    data["nodes"][1] = node("TS_exo")
    data["nodes"].append(node("late_exo", priority=2, pathway="exo"))
    with pytest.raises(ValidationError, match="exo"):
        ReactionGraph.model_validate(data)


def test_duplicate_id_across_rule_lists_refused() -> None:
    """A pathway rule may not reuse the id of a free-form rule."""
    data = graph(pruning_rules=[{"id": "endo_exo", "description": "d"}])
    with pytest.raises(ValidationError, match="duplicate pruning rule ids"):
        ReactionGraph.model_validate(data)


def test_duplicate_pathway_rule_ids_refused() -> None:
    """Two pathway rules with one id are refused."""
    with pytest.raises(ValidationError, match="duplicate pruning rule ids"):
        ReactionGraph.model_validate(graph(pathway_pruning_rules=[rule(), rule()]))


def test_node_cannot_reference_a_pathway_rule_as_free_form() -> None:
    """Node.pruning_rules still names only free-form rules."""
    data = graph()
    data["nodes"][2]["pruning_rules"] = ["endo_exo"]
    with pytest.raises(ValidationError, match="undefined pruning rules"):
        ReactionGraph.model_validate(data)


@pytest.mark.parametrize("label", ["", "1a", "a b", "a/b", "_x"])
def test_bad_pathway_label_refused(label: str) -> None:
    """The pathway label follows the node-id pattern."""
    with pytest.raises(ValidationError):
        ReactionNode.model_validate(node("A", pathway=label))


def test_load_error_is_graph_validation_error(tmp_path: Path) -> None:
    """The loader wraps a bad rule in GraphValidationError."""
    path = tmp_path / "g.json"
    path.write_text(json.dumps(graph(pathway_pruning_rules=[rule(threshold_kcal_mol=-1)])))
    with pytest.raises(GraphValidationError):
        load_reaction_graph(path)


def test_core_import_loads_no_numpy_or_rdkit() -> None:
    """G8: importing eta_rxncat.core pulls in neither numpy nor RDKit."""
    code = (
        "import eta_rxncat.core, sys; "
        "assert 'numpy' not in sys.modules and 'rdkit' not in sys.modules"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
