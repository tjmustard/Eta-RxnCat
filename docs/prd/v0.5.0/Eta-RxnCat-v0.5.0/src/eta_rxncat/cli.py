"""Command-line interface entrypoint for Eta-RxnCat."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from eta_rxncat.core.reaction_graph import ReactionGraph
from eta_rxncat.utils.hw_probe import probe_hardware


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eta-rxncat",
        description="Eta-RxnCat computational catalysis workflow engine",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hardware-check", help="Inspect CUDA, PyTorch, and GPU4PySCF capabilities")

    val_p = sub.add_parser("validate", help="Validate a ReactionGraph YAML or JSON file")
    val_p.add_argument("graph_file", type=Path, help="Path to reaction graph (.yaml/.yml/.json)")

    args = parser.parse_args(argv)

    if args.command == "hardware-check":
        report = probe_hardware()
        print(json.dumps(report.model_dump(), indent=2))
        return 0

    if args.command == "validate":
        graph = ReactionGraph.from_file(args.graph_file)
        order = graph.execution_order()
        print(
            f"Valid ReactionGraph '{graph.name}' "
            f"({len(graph.nodes)} nodes, {len(graph.edges)} edges). "
            f"Priority execution order: {[n.node_id for n in order]}"
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
