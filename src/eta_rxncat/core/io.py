"""Load and dump ReactionGraph files (YAML or JSON), rejecting duplicate keys."""

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from eta_rxncat.core.graph import ReactionGraph


class GraphValidationError(ValueError):
    """A reaction-graph file could not be read, parsed or validated.

    The message names the offender: the file, the duplicate key and its line, or the field
    location and the failing node, template, edge or rule id.
    """


class _UniqueKeyLoader(yaml.SafeLoader):
    """A ``yaml.SafeLoader`` that raises on a duplicate key inside one mapping."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        """Construct a mapping after checking it has no duplicate keys."""
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                continue  # unhashable key: the base constructor raises a ConstructorError
            if key in seen:
                raise GraphValidationError(
                    f"duplicate key '{key}' at line {key_node.start_mark.line + 1}"
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """``object_pairs_hook`` for :func:`json.loads` that raises on a duplicate key."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GraphValidationError(f"duplicate key '{key}'")
        result[key] = value
    return result


def _parse_yaml(text: str) -> Any:
    """Parse one YAML document with the duplicate-key-rejecting safe loader."""
    loader = _UniqueKeyLoader(text)
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def _format_validation_error(exc: ValidationError) -> str:
    """Render each pydantic error as ``location: message`` on one line."""
    parts = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def load_reaction_graph(path: Path) -> ReactionGraph:
    """Load and validate a reaction graph from a ``.yaml``, ``.yml`` or ``.json`` file.

    Args:
        path: The graph file.

    Returns:
        The validated graph.

    Raises:
        GraphValidationError: On an unsupported extension, an unreadable file, a syntax error,
            a duplicate key or a validation failure; the message names the offender.
    """
    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json"}:
        raise GraphValidationError(
            f"{path}: unsupported graph file extension '{path.suffix}' "
            "(expected .yaml, .yml or .json)"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GraphValidationError(f"{path}: cannot read file: {exc}") from exc
    try:
        if suffix == ".json":
            data = json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
        else:
            data = _parse_yaml(text)
    except GraphValidationError as exc:
        raise GraphValidationError(f"{path}: {exc}") from exc
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise GraphValidationError(f"{path}: syntax error: {exc}") from exc
    try:
        return ReactionGraph.model_validate(data)
    except ValidationError as exc:
        raise GraphValidationError(f"{path}: {_format_validation_error(exc)}") from exc


def dump_reaction_graph_json(graph: ReactionGraph) -> str:
    """Serialise a graph to JSON that :func:`load_reaction_graph` reads back to an equal graph.

    Args:
        graph: The graph to serialise.

    Returns:
        Indented JSON text.
    """
    return graph.model_dump_json(indent=2)
