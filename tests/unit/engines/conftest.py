"""Shared engine test set (mission §5 "Test set"): five committed .xyz states, Angstrom."""

import re
from pathlib import Path

import pytest

from eta_rxncat.core import MolecularState

DATA = Path(__file__).parent / "data"
CASES = ("water", "hydroxide", "hydroxyl", "hydronium", "pd_anion")
_HEADER = re.compile(r"charge=(-?\d+)\s+multiplicity=(\d+)")


def load_case(name: str) -> MolecularState:
    """Load ``data/<name>.xyz``; its comment line holds ``charge=<q> multiplicity=<m>``."""
    lines = (DATA / f"{name}.xyz").read_text(encoding="utf-8").splitlines()
    count = int(lines[0])
    match = _HEADER.search(lines[1])
    assert match, f"{name}.xyz comment line lacks charge=/multiplicity="
    atoms = [line.split() for line in lines[2 : 2 + count]]
    assert len(atoms) == count, f"{name}.xyz declares {count} atoms"
    return MolecularState(
        symbols=[a[0] for a in atoms],
        coordinates=[[float(v) for v in a[1:4]] for a in atoms],
        charge=int(match.group(1)),
        spin_multiplicity=int(match.group(2)),
    )


@pytest.fixture(scope="session")
def test_set() -> dict[str, MolecularState]:
    """All five test-set states by name."""
    return {name: load_case(name) for name in CASES}
