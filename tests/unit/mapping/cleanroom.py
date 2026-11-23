"""Loader for the clean-room nMAP test vectors (1-based on disk, 0-based here).

See ``data/cleanroom_nmap/PROVENANCE.md``. The files are compared at 1e-6 Angstrom.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

DATA = Path(__file__).parent / "data" / "cleanroom_nmap"
TOLERANCE_ANGSTROM = 1e-6


@dataclass(frozen=True)
class Xyz:
    """One XYZ file: element symbols and coordinates (Angstrom)."""

    symbols: list[str]
    coordinates: NDArray[np.float64]


def read_xyz(path: Path) -> Xyz:
    """Read an XYZ file (count line, comment line, then one atom per line)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    n_atoms = int(lines[0].split()[0])
    rows = [line.split() for line in lines[2 : 2 + n_atoms]]
    if len(rows) != n_atoms:
        raise ValueError(f"{path}: expected {n_atoms} atoms, found {len(rows)}")
    return Xyz(
        symbols=[row[0] for row in rows],
        coordinates=np.array([[float(v) for v in row[1:4]] for row in rows], dtype=np.float64),
    )


@dataclass(frozen=True)
class Vector:
    """One clean-room vector with its request converted to 0-based indices."""

    name: str
    template: Xyz
    incoming: Xyz
    expected_product: Xyz | None
    pairs: list[tuple[int, int]]
    """(template, incoming) pairs, 0-based."""
    template_delete: list[int]
    incoming_delete: list[int]
    charge: int | None
    multiplicity: int | None
    raw: dict[str, Any]


def _zero_based(values: list[int]) -> list[int]:
    return [v - 1 for v in values]


def load_vector(name: str) -> Vector:
    """Load vector ``name`` (a directory under ``data/cleanroom_nmap/``)."""
    directory = DATA / name
    request_path = directory / "request.json"
    raw: dict[str, Any] = (
        json.loads(request_path.read_text(encoding="utf-8")) if request_path.exists() else {}
    )
    expected = directory / "expected_product.xyz"
    return Vector(
        name=name,
        template=read_xyz(directory / "template.xyz"),
        incoming=read_xyz(directory / "incoming.xyz"),
        expected_product=read_xyz(expected) if expected.exists() else None,
        pairs=[(t - 1, i - 1) for t, i in raw.get("pairs_template_incoming_1based", [])],
        template_delete=_zero_based(raw.get("template_delete_1based", [])),
        incoming_delete=_zero_based(raw.get("incoming_delete_1based", [])),
        charge=raw.get("charge"),
        multiplicity=raw.get("multiplicity"),
        raw=raw,
    )
