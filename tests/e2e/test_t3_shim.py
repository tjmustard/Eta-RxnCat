"""Tier-D test of the geomeTRIC ASE shim (v0.5.0 slice 11): units only, on a 3-atom fake.

Only ``eta_geometric_shim`` imports ``ase`` (N1); this test drives its conversion function with a
stand-in for ``Atoms`` and a fake engine, in the acceptance env that has ``ase``.
"""

from types import SimpleNamespace
from typing import Any

import pytest

pytestmark = pytest.mark.acceptance


def test_shim_returns_ev_and_ev_per_angstrom() -> None:
    """Energy (eV) and forces (eV/A) equal eta's Eh and Eh/Bohr x the unit constants (1e-12 rel)."""
    shim = pytest.importorskip("eta_geometric_shim")
    from eta_rxncat.engines import HARTREE_EV
    from eta_rxncat.engines.units import BOHR_ANGSTROM

    forces = [[0.01, -0.02, 0.03], [-0.005, 0.0, 0.007], [0.0, 0.011, -0.013]]
    seen: list[Any] = []

    class FakeEngine:
        def evaluate(self, state: Any, *, forces: bool = True) -> Any:
            seen.append(state)
            return SimpleNamespace(energy_hartree=-76.4, forces_hartree_per_bohr=FORCES)

    FORCES = forces
    atoms = SimpleNamespace(
        get_chemical_symbols=lambda: ["O", "H", "H"],
        get_positions=lambda: [[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
    )
    energy, got = shim.ase_results(FakeEngine(), atoms)
    assert energy == pytest.approx(-76.4 * HARTREE_EV, rel=1e-12)
    assert got.shape == (3, 3)
    for row, expected in zip(got.tolist(), forces, strict=True):
        for g, e in zip(row, expected, strict=True):
            assert g == pytest.approx(e * HARTREE_EV / BOHR_ANGSTROM, rel=1e-12, abs=1e-300)
    assert seen[0].symbols == ["O", "H", "H"]
    assert (seen[0].charge, seen[0].spin_multiplicity) == (0, 1)


def test_only_the_shim_imports_ase() -> None:
    """N1: nothing in src/ imports ase; under tests/e2e only the shim does.

    (Pre-v0.5.0 MLIP acceptance tests elsewhere under tests/ also import ase; they are not E2E.)
    """
    import re
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    pattern = re.compile(r"^\s*(import ase\b|from ase\b)", re.MULTILINE)

    def importers(root: Path) -> list[str]:
        return sorted(
            str(p.relative_to(repo))
            for p in root.rglob("*.py")
            if pattern.search(p.read_text(encoding="utf-8"))
        )

    assert importers(repo / "src") == []
    assert importers(repo / "tests" / "e2e") == ["tests/e2e/eta_geometric_shim.py"]
