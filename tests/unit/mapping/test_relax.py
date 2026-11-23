"""Tests for the core-frozen pre-relaxation (v0.4.0 slice 05; mission X1-X4, R6, R7)."""

import ast
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolTransforms

from eta_rxncat.core import (
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    StageConfig,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import Engine, EngineRuntimeError, OptionSpec, RDKitFFEngine
from eta_rxncat.mapping import CoreDisplacementError, MappingError, relax_constrained_core
from eta_rxncat.mapping.relax import CORE_FREEZE_TOLERANCE_ANGSTROM
from eta_rxncat.optimize import GeometricOptimizer, OptimizationFailedError, Optimizer

UFF_STAGE = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
RELAX_SRC = Path(__file__).parents[3] / "src" / "eta_rxncat" / "mapping" / "relax.py"
CORE = (1, 2, 3, 5)


def six_atoms() -> MolecularState:
    """Return a six-atom singlet test structure (ethane-like C2H4 + 2 H = C2H6 positions)."""
    return MolecularState(
        symbols=["C", "C", "H", "H", "H", "H"],
        coordinates=[
            [0.0, 0.0, 0.0],
            [1.33, 0.0, 0.0],
            [-0.6, 0.93, 0.0],
            [-0.6, -0.93, 0.0],
            [1.93, 0.93, 0.0],
            [1.93, -0.93, 0.0],
        ],
        charge=0,
        spin_multiplicity=1,
    )


class RecordingOptimizer(Optimizer):
    """A test double: records each call and returns ``transform(state)`` as the final state."""

    OPTIONS: ClassVar[Mapping[str, OptionSpec]] = {}

    def __init__(
        self,
        move: dict[int, list[float]] | None = None,
        raises: BaseException | None = None,
    ) -> None:
        """Move the given atoms by the given vectors, or raise ``raises``, when called."""
        self.move = move or {}
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    @property
    def identity(self) -> OptimizerIdentity:
        """A fixed fake identity."""
        return OptimizerIdentity(name="geometric", version="0+recording-fake")

    def minimize(  # type: ignore[override]
        self, state: MolecularState, engine: Engine, **kwargs: Any
    ) -> OptimizationResult:
        """Record the call; raise or return the moved state."""
        self.calls.append({"state": state, "engine": engine, **kwargs})
        if self.raises is not None:
            raise self.raises
        coords = [list(row) for row in state.coordinates]
        for atom, shift in self.move.items():
            coords[atom] = [c + d for c, d in zip(coords[atom], shift, strict=True)]
        final = state.model_copy(update={"coordinates": coords})
        return OptimizationResult(
            final_state=final,
            final_energy_hartree=-1.0,
            converged=True,
            n_steps=3,
            n_engine_calls=4,
            recovery_steps=[],
            optimizer=self.identity,
            options={},
        )


def engine() -> RDKitFFEngine:
    """A real engine object; the recording fakes never call it."""
    return RDKitFFEngine(UFF_STAGE)


# --- Mini-requirement 1: the recording fake -------------------------------------------------


def test_minimize_called_with_frozen_core_and_no_dihedrals() -> None:
    """frozen_atom_indices == core, no dihedral_constraints passed, options passed through."""
    fake = RecordingOptimizer()
    options: dict[str, ScalarValue] = {"maxiter": 200}
    state = six_atoms()
    potential = engine()
    result = relax_constrained_core(state, potential, fake, list(CORE), options=options)
    (call,) = fake.calls
    assert call["frozen_atom_indices"] == (1, 2, 3, 5)
    assert "dihedral_constraints" not in call
    assert call.get("dihedral_constraints", ()) == ()
    assert call["options"] == {"maxiter": 200}
    assert call["state"] is state and call["engine"] is potential
    assert result.final_state.coordinates == state.coordinates
    assert result.n_steps == 3 and result.optimizer.version == "0+recording-fake"


def test_result_returned_unchanged() -> None:
    """The optimizer's result object is returned as is."""
    fake = RecordingOptimizer(move={0: [0.5, 0.0, 0.0]})
    original = fake.minimize
    returned: list[OptimizationResult] = []

    def spy(state: MolecularState, engine: Engine, **kwargs: Any) -> OptimizationResult:
        out = original(state, engine, **kwargs)
        returned.append(out)
        return out

    fake.minimize = spy  # type: ignore[method-assign]
    result = relax_constrained_core(six_atoms(), engine(), fake, CORE)
    assert result is returned[0]


# --- Mini-requirement 2: displacement guard -------------------------------------------------


def test_core_freeze_tolerance_is_1e_6() -> None:
    """The bound is the replan-1 constant, 1e-6 A (mission R26)."""
    assert CORE_FREEZE_TOLERANCE_ANGSTROM == 1e-6


def test_core_moved_beyond_limit_raises() -> None:
    """A core atom moved by 2e-6 A raises CoreDisplacementError naming it."""
    fake = RecordingOptimizer(move={3: [2e-6, 0.0, 0.0]})
    with pytest.raises(CoreDisplacementError) as caught:
        relax_constrained_core(six_atoms(), engine(), fake, CORE)
    assert caught.value.atom == 3
    assert caught.value.displacement_angstrom == pytest.approx(2e-6, rel=1e-6)


def test_worst_core_atom_is_named() -> None:
    """With two core atoms moved, the worst one is reported."""
    fake = RecordingOptimizer(move={1: [0.0, 3e-6, 0.0], 5: [0.0, 0.0, 5e-6]})
    with pytest.raises(CoreDisplacementError) as caught:
        relax_constrained_core(six_atoms(), engine(), fake, CORE)
    assert caught.value.atom == 5
    assert caught.value.displacement_angstrom == pytest.approx(5e-6, rel=1e-6)


def test_non_core_atoms_may_move() -> None:
    """Moving only non-core atoms by 1 A returns normally."""
    fake = RecordingOptimizer(move={0: [1.0, 0.0, 0.0], 4: [0.0, 1.0, 0.0]})
    result = relax_constrained_core(six_atoms(), engine(), fake, CORE)
    assert result.final_state.coordinates[0][0] == pytest.approx(1.0)


def test_core_within_limit_passes() -> None:
    """A core displacement of 5e-7 A is within the 1e-6 A limit."""
    fake = RecordingOptimizer(move={2: [5e-7, 0.0, 0.0]})
    relax_constrained_core(six_atoms(), engine(), fake, CORE)


# --- Mini-requirement 3: refusals before any call -------------------------------------------


@pytest.mark.parametrize(
    ("core", "options", "message"),
    [
        ([], None, "core_indices is empty"),
        ([1, 2, 2], None, r"duplicates: \[1, 2, 2\]"),
        ([1, 6], None, r"core_indices \[6\] out of range for 6 atoms"),
        ([1, -1], None, r"core_indices \[-1\] out of range"),
        ([1, 2, 3], {"constraints": "x"}, 'options key "constraints" is refused'),
    ],
)
def test_refusals_before_any_call(
    core: Sequence[int], options: dict[str, ScalarValue] | None, message: str
) -> None:
    """Each bad core or a "constraints" option raises MappingError with zero optimizer calls."""
    fake = RecordingOptimizer()
    with pytest.raises(MappingError, match=message):
        relax_constrained_core(six_atoms(), engine(), fake, core, options=options)
    assert fake.calls == []


# --- Mini-requirement 4: propagation --------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        OptimizationFailedError("ladder exhausted", steps=("tric",), last_energy_hartree=None),
        EngineRuntimeError("engine died"),
    ],
)
def test_errors_propagate_unchanged(error: Exception) -> None:
    """Optimizer and engine errors propagate as the same object."""
    fake = RecordingOptimizer(raises=error)
    with pytest.raises(type(error)) as caught:
        relax_constrained_core(six_atoms(), engine(), fake, CORE)
    assert caught.value is error


# --- Proof contract: minimize is never given dihedral_constraints ---------------------------


def test_relax_source_never_passes_dihedral_constraints() -> None:
    """Every minimize call in relax.py passes frozen_atom_indices and no dihedral_constraints."""
    tree = ast.parse(RELAX_SRC.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "minimize"
    ]
    assert len(calls) == 1
    keywords = {k.arg for k in calls[0].keywords}
    assert keywords == {"frozen_atom_indices", "options"}
    assert "check_ground_state" not in RELAX_SRC.read_text(encoding="utf-8").replace(
        "never pass it\n    to ``eta_rxncat.thermo.check_ground_state``", ""
    )


# --- Mini-requirement 5: UFF with geomeTRIC -------------------------------------------------


def distorted_butane() -> MolecularState:
    """n-Butane (UFF-embedded, seed 20261123) with one terminal C-H stretched to 1.3 A."""
    mol = Chem.AddHs(Chem.MolFromSmiles("CCCC"))
    assert AllChem.EmbedMolecule(mol, randomSeed=20261123) == 0
    conformer = mol.GetConformer()
    hydrogen = next(
        a.GetIdx() for a in mol.GetAtomWithIdx(0).GetNeighbors() if a.GetSymbol() == "H"
    )
    rdMolTransforms.SetBondLength(conformer, 0, hydrogen, 1.3)
    return MolecularState(
        symbols=[a.GetSymbol() for a in mol.GetAtoms()],
        coordinates=[list(conformer.GetAtomPosition(i)) for i in range(mol.GetNumAtoms())],
        charge=0,
        spin_multiplicity=1,
    )


def test_uff_core_frozen_relaxation() -> None:
    """GeometricOptimizer on UFF converges with the 3-carbon core held to <= 1e-6 A (R26)."""
    start = distorted_butane()
    core = [1, 2, 3]
    result = relax_constrained_core(
        start, RDKitFFEngine(UFF_STAGE), GeometricOptimizer(), core, options={"maxiter": 200}
    )
    moved = max(math.dist(result.final_state.coordinates[k], start.coordinates[k]) for k in core)
    print(f"UFF core max displacement {moved:.3e} A; n_steps {result.n_steps}")
    assert result.converged is True
    assert result.n_steps >= 1
    assert moved <= CORE_FREEZE_TOLERANCE_ANGSTROM
    stretched = np.linalg.norm(
        np.subtract(result.final_state.coordinates[0], result.final_state.coordinates[4])
    )
    assert stretched < 1.25  # the stretched C-H relaxed
    assert result.options["constraints"] == "freeze:1,2,3"
