"""Acceptance helpers (slice 11): the test-set loader and the per-case JSON writer."""

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from eta_rxncat.core import MolecularState

DATA = Path(__file__).resolve().parents[1] / "unit" / "engines" / "data"
CASES = ("water", "hydroxide", "hydroxyl", "pd_anion")
_HEADER = re.compile(r"charge=(-?\d+)\s+multiplicity=(\d+)")


def load_case(name: str) -> MolecularState:
    """Load the committed test-set ``data/<name>.xyz`` (charge/multiplicity in its comment line)."""
    lines = (DATA / f"{name}.xyz").read_text(encoding="utf-8").splitlines()
    count = int(lines[0])
    match = _HEADER.search(lines[1])
    assert match, name
    atoms = [line.split() for line in lines[2 : 2 + count]]
    return MolecularState(
        symbols=[a[0] for a in atoms],
        coordinates=[[float(v) for v in a[1:4]] for a in atoms],
        charge=int(match.group(1)),
        spin_multiplicity=int(match.group(2)),
    )


def record(out: Path, engine: str, case: str, **fields: Any) -> None:
    """Write ``<engine>.<case>.json`` (identity as name/version/model)."""
    identity = fields.pop("identity", None)
    if identity is not None:
        fields["identity"] = {
            "name": identity.name,
            "version": identity.version,
            "model": identity.model,
        }
    payload = {"engine": engine, "case": case, **fields}
    (out / f"{engine}.{case}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def evaluated(
    out: Path,
    engine: str,
    case: str,
    run: Callable[[], Any],
    reference_abs_diff: float,
    **extra: Any,
) -> Any:
    """Record an evaluated case from its result."""
    result = run()
    record(
        out,
        engine,
        case,
        energy_hartree=result.energy_hartree,
        device=result.device,
        device_reason=result.device_reason,
        recovery_steps=list(result.recovery_steps),
        identity=result.engine,
        reference_abs_diff=reference_abs_diff,
        wall_time_s=result.wall_time_s,
        refused=False,
        **extra,
    )
    return result


def refused(out: Path, engine: str, case: str, error: BaseException) -> None:
    """Record a refusal case."""
    record(out, engine, case, refused=True, error_class=type(error).__name__, message=str(error))


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    """(result, seconds)."""
    start = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - start
