"""The ``eta-rxncat`` command line (v0.1.0): ``hardware-check [--smoke]`` and ``validate <path>``.

Exit codes:

======================  ======  ===============================================  =====  =======
Command                 0       1                                                2      3
======================  ======  ===============================================  =====  =======
hardware-check          report  —                                                usage  —
hardware-check --smoke  pass    fail                                             usage  skipped
validate <path>         valid   invalid / unreadable / unsupported extension     usage  —
======================  ======  ===============================================  =====  =======

Every ``validate`` failure is one ``error: <message>`` line on stderr, with no traceback.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from eta_rxncat.core import GraphValidationError, load_reaction_graph


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser with the two v0.1.0 subcommands."""
    parser = argparse.ArgumentParser(
        prog="eta-rxncat", description="Eta-RxnCat reaction-graph and hardware tools."
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    hardware = commands.add_parser(
        "hardware-check", help="print the hardware report as JSON (exit 0)"
    )
    hardware.add_argument(
        "--smoke",
        action="store_true",
        help="run the GPU smoke test instead (exit 0 pass, 1 fail, 3 skipped)",
    )
    validate = commands.add_parser("validate", help="validate a reaction-graph YAML or JSON file")
    validate.add_argument("path", type=Path, help="graph file (.yaml, .yml or .json)")
    return parser


def _hardware_check(smoke: bool) -> int:
    """Print the hardware report, or the smoke result, as JSON and return the exit code."""
    from eta_rxncat.utils.hw_probe import probe_hardware, run_smoke, smoke_exit_code

    if smoke:
        result = run_smoke()
        print(result.model_dump_json(indent=2))
        return smoke_exit_code(result)
    print(probe_hardware().model_dump_json(indent=2))
    return 0


def _validate(path: Path) -> int:
    """Validate the graph at ``path``; print a four-line summary (0) or one error line (1)."""
    try:
        graph = load_reaction_graph(path)
    except GraphValidationError as exc:
        message = " ".join(str(exc).split())  # keep the error on one line
        print(f"error: {message}", file=sys.stderr)
        return 1
    print(f"OK {path}")
    print(f"nodes: {len(graph.nodes)}")
    print(f"edges: {len(graph.edges)}")
    print(f"priority_order: {','.join(graph.priority_order())}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its exit code (2 for a usage error).

    Args:
        argv: Arguments without the program name; ``None`` means ``sys.argv[1:]``.
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse has printed usage/help; turn its exit into a return
        return exc.code if isinstance(exc.code, int) else 2
    if args.command == "hardware-check":
        return _hardware_check(args.smoke)
    return _validate(args.path)
