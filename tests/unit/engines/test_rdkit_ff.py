"""Tests for the rdkit_ff engine against RDKit's own API on the same input (slice 05)."""

import re
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, StageConfig
from eta_rxncat.engines import (
    ENGINE_IMPL_KEY,
    EngineInputError,
    RDKitFFEngine,
    angstrom_to_bohr,
    kcal_mol_per_angstrom_to_hartree_per_bohr,
    kcal_mol_to_hartree,
    library_version,
)

METHODS = ("uff", "mmff94")
REFUSAL = "only neutral closed-shell states (charge 0, multiplicity 1) are supported"


@pytest.fixture(scope="module")
def rd() -> SimpleNamespace:
    """RDKit modules, imported at test time (rdkit is in the base install)."""
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds
    from rdkit.Chem import rdForceFieldHelpers as helpers

    return SimpleNamespace(Chem=Chem, rdDetermineBonds=rdDetermineBonds, helpers=helpers)


def engine(method: str = "uff", **options: Any) -> RDKitFFEngine:
    """An rdkit_ff engine for ``method``."""
    stage = StageConfig(kind="single_point", engine="rdkit_ff", method=method, options=options)
    return RDKitFFEngine.from_stage(stage)


def state(
    symbols: list[str], coords: list[list[float]], charge: int = 0, mult: int = 1
) -> MolecularState:
    """A MolecularState from raw lists."""
    return MolecularState(
        symbols=symbols, coordinates=coords, charge=charge, spin_multiplicity=mult
    )


def reference_ff(rd: SimpleNamespace, mol_state: MolecularState, method: str) -> tuple[Any, Any]:
    """RDKit's own pipeline on the same input: XYZ block, DetermineBonds, then the force field.

    Returns ``(mol, ff)``: the force field points into the molecule's conformer, so the caller
    must keep ``mol`` alive while using ``ff`` (dropping it segfaults RDKit).
    """
    lines = [str(len(mol_state.symbols)), ""]
    lines += [
        f"{s} {x!r} {y!r} {z!r}"
        for s, (x, y, z) in zip(mol_state.symbols, mol_state.coordinates, strict=True)
    ]
    mol = rd.Chem.MolFromXYZBlock("\n".join(lines) + "\n")
    rd.rdDetermineBonds.DetermineBonds(mol, charge=0)
    if method == "uff":
        ff = rd.helpers.UFFGetMoleculeForceField(mol, ignoreInterfragInteractions=False)
    else:
        props = rd.helpers.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94")
        ff = rd.helpers.MMFFGetMoleculeForceField(mol, props, ignoreInterfragInteractions=False)
    ff.Initialize()
    return mol, ff


def rel(a: float, b: float) -> float:
    """Relative difference with an absolute floor for values near zero."""
    return abs(a - b) / max(abs(b), 1e-12)


# ---------------------------------------------------------------- references


@pytest.mark.parametrize("method", METHODS)
def test_energy_and_forces_match_rdkit(
    rd: SimpleNamespace, test_set: dict[str, MolecularState], method: str
) -> None:
    """Energy = ff.CalcEnergy() and forces = -ff.CalcGrad(), converted, to <= 1e-10 relative."""
    water = test_set["water"]
    result = engine(method).evaluate(water)
    mol, ff = reference_ff(rd, water, method)
    assert rel(result.energy_hartree, kcal_mol_to_hartree(ff.CalcEnergy())) <= 1e-10
    grad = list(ff.CalcGrad())
    expected = [-kcal_mol_per_angstrom_to_hartree_per_bohr(g) for g in grad]
    got = [v for row in result.forces_hartree_per_bohr or [] for v in row]
    assert len(got) == 9
    scale = max(abs(v) for v in expected)
    assert max(abs(g - e) for g, e in zip(got, expected, strict=True)) <= 1e-10 * scale
    assert result.device == "cpu" and result.engine.name == "rdkit_ff"
    assert mol.GetNumAtoms() == 3


@pytest.mark.parametrize("method", METHODS)
def test_forces_match_fd_of_energy(test_set: dict[str, MolecularState], method: str) -> None:
    """Forces equal the central FD of the engine energy at 1e-4 Angstrom, to <= 1e-5 Eh/Bohr."""
    water = test_set["water"]
    eng = engine(method)
    forces = eng.evaluate(water).forces_hartree_per_bohr
    assert forces is not None
    step = 1e-4
    for atom in range(3):
        for axis in range(3):
            energies = []
            for sign in (1, -1):
                coords = [row[:] for row in water.coordinates]
                coords[atom][axis] += sign * step
                energies.append(
                    eng.evaluate(state(water.symbols, coords), forces=False).energy_hartree
                )
            fd = -(energies[0] - energies[1]) / (2 * angstrom_to_bohr(step))
            assert abs(forces[atom][axis] - fd) <= 1e-5, (atom, axis, forces[atom][axis], fd)


@pytest.mark.parametrize("method", METHODS)
def test_fd_hessian(test_set: dict[str, MolecularState], method: str) -> None:
    """hessian=True gives a 9x9 finite-difference Hessian, exactly symmetric, asymmetry recorded."""
    result = engine(method).evaluate(test_set["water"], hessian=True)
    h = result.hessian_hartree_per_bohr2
    assert h is not None and len(h) == 9 and all(len(row) == 9 for row in h)
    assert result.hessian_method == "finite_difference"
    assert result.hessian_max_asymmetry is not None and result.hessian_max_asymmetry >= 0
    assert all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    assert all(h[i][i] > -1.0 for i in range(9))


def test_fd_hessian_matches_fd_of_forces(test_set: dict[str, MolecularState]) -> None:
    """A Hessian row equals the central difference of the engine's forces at the keyed step."""
    water = test_set["water"]
    eng = engine("uff")
    h = eng.evaluate(water, hessian=True).hessian_hartree_per_bohr2
    assert h is not None
    step_bohr = 0.005
    step_ang = step_bohr * 0.529177210903
    rows = []
    for sign in (1, -1):
        coords = [row[:] for row in water.coordinates]
        coords[0][2] += sign * step_ang
        f = eng.evaluate(state(water.symbols, coords)).forces_hartree_per_bohr
        assert f is not None
        rows.append([v for row in f for v in row])
    raw_row = [-(p - m) / (2 * step_bohr) for p, m in zip(rows[0], rows[1], strict=True)]
    assert max(abs(h[2][j] - raw_row[j]) for j in range(9)) <= 1e-6


@pytest.mark.parametrize("method", METHODS)
def test_fd_hessian_matches_energy_second_differences(
    test_set: dict[str, MolecularState], method: str
) -> None:
    """The Hessian agrees with second differences of the ENERGY alone (no gradients used).

    Guards the RDKit 2026.09.2 defect the engine works around: ``CalcGrad(positions)`` away from
    the force field's own conformer is not the gradient of ``CalcEnergy``, which made the
    first FD Hessian asymmetric by ~0.03 Eh/Bohr^2 and wrong in its elements.
    """
    water = test_set["water"]
    eng = engine(method)
    result = eng.evaluate(water, hessian=True)
    h = result.hessian_hartree_per_bohr2
    assert h is not None and result.hessian_max_asymmetry is not None
    assert result.hessian_max_asymmetry <= 1e-4
    step = 2e-3  # Angstrom
    bohr = angstrom_to_bohr(step)

    def energy(shifts: dict[int, float]) -> float:
        coords = [row[:] for row in water.coordinates]
        for index, delta in shifts.items():
            coords[index // 3][index % 3] += delta
        return eng.evaluate(state(water.symbols, coords), forces=False).energy_hartree

    for i, j in [(2, 2), (2, 4), (4, 5), (5, 8), (1, 7)]:
        if i == j:
            second = (energy({i: step}) - 2 * energy({}) + energy({i: -step})) / bohr**2
        else:
            second = (
                energy({i: step, j: step})
                - energy({i: step, j: -step})
                - energy({i: -step, j: step})
                + energy({i: -step, j: -step})
            ) / (4 * bohr**2)
        assert abs(h[i][j] - second) <= 2e-3 * max(1.0, abs(second)), (i, j, h[i][j], second)


def test_rdkit_calcgrad_positions_defect_is_avoided(rd: SimpleNamespace) -> None:
    """Documents the upstream behaviour the engine avoids (RDKit 2026.09.2).

    On one reused force field, ``CalcGrad(x)`` depends on earlier calls: after
    ``CalcEnergy(y)`` at another point it no longer equals a clean ``CalcGrad(x)``. The engine
    therefore builds a fresh force field per geometry and calls ``CalcEnergy()`` then
    ``CalcGrad()`` there only. If a future RDKit fixes this, the first assertion fails and the
    per-geometry rebuild can be revisited (it stays correct either way).
    """
    water = state(
        ["O", "H", "H"], [[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]]
    )
    mol_a, ff_a = reference_ff(rd, water, "uff")
    mol_b, ff_b = reference_ff(rd, water, "uff")
    x0 = list(ff_a.Positions())
    x = x0[:]
    x[2] += 1e-3
    y = x0[:]
    y[4] += 1e-3
    clean = list(ff_a.CalcGrad(x))
    ff_b.CalcEnergy(y)
    after = list(ff_b.CalcGrad(x))
    assert max(abs(a - b) for a, b in zip(clean, after, strict=True)) > 0.1
    # The engine's call pattern on a fresh force field is unaffected.
    mol_c, ff_c = reference_ff(rd, water, "uff")
    ff_c.CalcEnergy()
    mol_d, ff_d = reference_ff(rd, water, "uff")
    assert list(ff_c.CalcGrad()) == list(ff_d.CalcGrad())
    assert {mol_a.GetNumAtoms(), mol_b.GetNumAtoms(), mol_c.GetNumAtoms(), mol_d.GetNumAtoms()} == {
        3
    }


def test_methods_differ_and_are_case_insensitive(test_set: dict[str, MolecularState]) -> None:
    """UFF and MMFF94 give different energies; "UFF" keys and evaluates as "uff"."""
    water = test_set["water"]
    assert (
        engine("uff").evaluate(water).energy_hartree
        != engine("mmff94").evaluate(water).energy_hartree
    )
    upper = engine("UFF")
    assert upper.stage.method == "uff" and upper.stage == engine("uff").stage
    assert upper.evaluate(water).energy_hartree == engine("uff").evaluate(water).energy_hartree


# ---------------------------------------------------------------- refusals


@pytest.mark.parametrize("case", ["hydroxide", "hydronium", "hydroxyl", "pd_anion"])
@pytest.mark.parametrize("method", METHODS)
def test_charged_or_open_shell_refused(
    test_set: dict[str, MolecularState], case: str, method: str
) -> None:
    """The anion, cation, doublet and Pd anion are refused with the exact R35 message."""
    s = test_set[case]
    with pytest.raises(EngineInputError) as info:
        engine(method).evaluate(s)
    assert str(info.value) == (
        f"rdkit_ff: charge {s.charge}, multiplicity {s.spin_multiplicity}: {REFUSAL}"
    )


def test_water_geometry_with_charge_minus_two_refused(test_set: dict[str, MolecularState]) -> None:
    """The deliberate mismatch (water geometry, charge -2) is refused before any RDKit call."""
    water = test_set["water"]
    with pytest.raises(EngineInputError, match="rdkit_ff: charge -2, multiplicity 1: only neutral"):
        engine().evaluate(state(water.symbols, water.coordinates, charge=-2))


def test_same_geometry_doublet_is_refused(test_set: dict[str, MolecularState]) -> None:
    """R4: water evaluates at multiplicity 1; the same geometry as a doublet anion is refused."""
    water = test_set["water"]
    assert engine().evaluate(water).energy_hartree == engine().evaluate(water).energy_hartree
    with pytest.raises(EngineInputError, match="charge -1, multiplicity 2"):
        engine().evaluate(state(water.symbols, water.coordinates, charge=-1, mult=2))


def test_charge_check_runs_before_rdkit(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check (a) comes first: with DetermineBonds broken, a charged state still gets message (a)."""
    from rdkit.Chem import rdDetermineBonds

    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("RDKit was called")

    monkeypatch.setattr(rdDetermineBonds, "DetermineBonds", boom)
    with pytest.raises(EngineInputError, match=re.escape(REFUSAL)):
        engine().evaluate(test_set["hydroxide"])


@pytest.mark.parametrize(
    ("symbols", "coords", "fragment"),
    [
        (["H", "H"], [[0.0, 0.0, 0.0], [0.0, 0.0, 5.0]], "Final molecular charge"),
        (["N", "N"], [[0.0, 0.0, 0.0], [0.0, 0.0, 3.0]], "Unable to determine valence"),
    ],
    ids=["two-distant-h", "stretched-n2"],
)
def test_perception_failure_refused(
    symbols: list[str], coords: list[list[float]], fragment: str
) -> None:
    """Check (b): a ValueError from RDKit perception is refused, never swallowed."""
    with pytest.raises(
        EngineInputError, match="rdkit_ff: charge 0, multiplicity 1: RDKit bond perception failed"
    ) as info:
        engine().evaluate(state(symbols, coords))
    assert fragment in str(info.value)
    assert isinstance(info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("symbols", "coords", "fragment"),
    [
        (
            ["C", "H", "H"],
            [[0.0, 0.0, 0.0], [1.09, 0.0, 0.0], [-0.3, 1.05, 0.0]],
            "radical electrons 2",
        ),
        (["C"], [[0.0, 0.0, 0.0]], "implicit hydrogens 4"),
        (["O"], [[0.0, 0.0, 0.0]], "implicit hydrogens 2"),
    ],
    ids=["singlet-ch2-radicals", "lone-carbon-implicit-h", "lone-oxygen-implicit-h"],
)
def test_round_trip_mismatch_refused(
    symbols: list[str], coords: list[list[float]], fragment: str
) -> None:
    """Check (c): radicals or implicit hydrogens in the perceived molecule are refused."""
    with pytest.raises(EngineInputError, match="perception round-trip mismatch") as info:
        engine().evaluate(state(symbols, coords))
    assert fragment in str(info.value)


def test_round_trip_formal_charge_mismatch_refused(
    test_set: dict[str, MolecularState], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check (c): a perceived formal charge that differs from the state's charge is refused."""
    from rdkit.Chem import rdDetermineBonds

    real = rdDetermineBonds.DetermineBonds

    def shifted(mol: Any, **kwargs: Any) -> None:
        real(mol, **kwargs)
        mol.GetAtomWithIdx(0).SetFormalCharge(1)
        mol.GetAtomWithIdx(1).SetFormalCharge(1)

    monkeypatch.setattr(rdDetermineBonds, "DetermineBonds", shifted)
    with pytest.raises(EngineInputError, match="round-trip mismatch.*formal charge 2"):
        engine().evaluate(test_set["water"])


@pytest.mark.parametrize(
    ("symbols", "coords", "method"),
    [
        (["Pd"], [[0.0, 0.0, 0.0]], "uff"),
        (["Pd"], [[0.0, 0.0, 0.0]], "mmff94"),
        (
            ["S"] + ["F"] * 6,
            [
                [0, 0, 0],
                [1.56, 0, 0],
                [-1.56, 0, 0],
                [0, 1.56, 0],
                [0, -1.56, 0],
                [0, 0, 1.56],
                [0, 0, -1.56],
            ],
            "uff",
        ),
        (
            ["B", "H", "H", "H"],
            [[0, 0, 0], [1.19, 0, 0], [-0.595, 1.0306, 0], [-0.595, -1.0306, 0]],
            "mmff94",
        ),
    ],
    ids=["pd-atom-uff", "pd-atom-mmff94", "sf6-uff", "bh3-mmff94"],
)
def test_missing_parameters_refused(
    symbols: list[str], coords: list[list[float]], method: str
) -> None:
    """Check (d): no UFF / MMFF94 parameters for an atom type is refused (no partial terms)."""
    label = "UFF" if method == "uff" else "MMFF94"
    with pytest.raises(
        EngineInputError, match=f"rdkit_ff: charge 0, multiplicity 1: {label} has no parameters"
    ):
        engine(method).evaluate(state(symbols, [[float(v) for v in row] for row in coords]))


def test_bh3_has_uff_parameters() -> None:
    """The MMFF94 refusal for BH3 is a parameter gap, not perception: UFF evaluates it."""
    coords = [[0.0, 0.0, 0.0], [1.19, 0.0, 0.0], [-0.595, 1.0306, 0.0], [-0.595, -1.0306, 0.0]]
    assert engine("uff").evaluate(state(["B", "H", "H", "H"], coords)).forces_hartree_per_bohr


# ---------------------------------------------------------------- stage and identity


def test_resolved_options_and_identity() -> None:
    """No options resolve to fd_step_bohr 0.005 and engine_impl 1; the identity is RDKit's."""
    eng = engine()
    assert eng.stage.options == {"fd_step_bohr": 0.005, ENGINE_IMPL_KEY: 1}
    assert eng.identity.name == "rdkit_ff"
    assert eng.identity.version == library_version("rdkit") and eng.identity.model is None


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"options": {"gpu": True}}, "gpu"),
        ({"options": {"fd_step_bohr": 0.0}}, "fd_step_bohr"),
        ({"options": {"fd_step_bohr": -0.01}}, "fd_step_bohr"),
        ({"method": "gaff"}, "gaff"),
        ({"method": "mmff94s"}, "mmff94s"),
    ],
    ids=["unknown-option", "zero-step", "negative-step", "unknown-method", "mmff94s-not-offered"],
)
def test_bad_stage_refused(kwargs: dict[str, Any], match: str) -> None:
    """Unknown options, a non-positive FD step and other methods raise EngineInputError."""
    data: dict[str, Any] = {"kind": "single_point", "engine": "rdkit_ff", "method": "uff"}
    data.update(kwargs)
    with pytest.raises(EngineInputError, match=match):
        RDKitFFEngine.from_stage(StageConfig(**data))


def test_runtime_arguments_refused() -> None:
    """rdkit_ff takes no runtime arguments."""
    with pytest.raises(EngineInputError, match="threads"):
        RDKitFFEngine.from_stage(
            StageConfig(kind="single_point", engine="rdkit_ff", method="uff"), threads=2
        )


def test_result_lists_are_fresh(test_set: dict[str, MolecularState]) -> None:
    """Mutating one result's forces does not change the next result."""
    eng = engine()
    first = eng.evaluate(test_set["water"])
    assert first.forces_hartree_per_bohr is not None
    expected = first.forces_hartree_per_bohr[0][0]
    first.forces_hartree_per_bohr[0][0] = 123.0
    second = eng.evaluate(test_set["water"]).forces_hartree_per_bohr
    assert second is not None and second[0][0] == expected
