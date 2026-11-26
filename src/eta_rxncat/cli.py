"""The ``eta-rxncat`` command line: ``hardware-check``, ``validate`` and ``review-bundle``.

Exit codes:

======================  ======  ===============================================  =====  =======
Command                 0       1                                                2      3
======================  ======  ===============================================  =====  =======
hardware-check          report  —                                                usage  —
hardware-check --smoke  pass    fail                                             usage  skipped
validate <path>         valid   invalid / unreadable / unsupported extension     usage  —
review-bundle           written record, store or output directory refused        usage  —
======================  ======  ===============================================  =====  =======

Every ``validate`` failure is one ``error: <message>`` line on stderr, with no traceback; every
``review-bundle`` failure is one ``error: <ErrorType>: <message>`` line.
"""

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from eta_rxncat.core import GraphValidationError, load_reaction_graph


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser with its subcommands."""
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
    bundle = commands.add_parser(
        "review-bundle", help="write the offline HTML review bundle of a run from its store"
    )
    bundle.add_argument("--record", type=Path, required=True, help="run record JSON (RunRecord)")
    bundle.add_argument("--store", type=Path, required=True, help="the run's artifact store")
    bundle.add_argument("--out", type=Path, required=True, help="new or empty output directory")
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


def _review_bundle(record_path: Path, store_path: Path, out: Path) -> int:
    """Export the record's run from the store and write its bundle (0), or print one error (1)."""
    from eta_rxncat.review import (
        TRAJECTORY_BYTE_BUDGET,
        RunRecord,
        export_run_data,
        write_review_bundle,
    )
    from eta_rxncat.store import ArtifactStore, StoreBusyError, StoreSchemaError

    try:
        record = RunRecord.model_validate_json(record_path.read_bytes())
        if not store_path.is_file():  # opening a missing path would create an empty store
            raise FileNotFoundError(f"no store file at {store_path}")
        with ArtifactStore(store_path) as store:
            run_data = export_run_data(record, store, trajectory_byte_budget=TRAJECTORY_BYTE_BUDGET)
        write_review_bundle(run_data, out)
    except (OSError, ValueError, StoreBusyError, StoreSchemaError, sqlite3.Error) as exc:
        message = " ".join(str(exc).split())  # keep the error on one line
        print(f"error: {type(exc).__name__}: {message}", file=sys.stderr)
        return 1
    print(f"OK {out}")
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
    if args.command == "review-bundle":
        return _review_bundle(args.record, args.store, args.out)
    return _validate(args.path)
