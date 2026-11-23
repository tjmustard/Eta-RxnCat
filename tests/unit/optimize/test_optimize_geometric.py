"""Tests for GeometricOptimizer: API path, sandbox, ladder and constraints (v0.3.0 slice 04).

geomeTRIC is in the dev group (R5), so these run in the default suite. Thresholds are read from
geomeTRIC at runtime, never hard-coded.
"""

import importlib.metadata
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem, rdForceFieldHelpers, rdMolTransforms
from rdkit.Geometry import Point3D

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.engines import (
    BOHR_ANGSTROM,
    Engine,
    EngineInputError,
    OptionSpec,
    RawResult,
    RDKitFFEngine,
    kcal_mol_to_hartree,
)
from eta_rxncat.optimize import (
    DihedralConstraint,
    GeometricOptimizer,
    OptimizationFailedError,
    OptimizerInputError,
    OptimizerUnavailableError,
)

UFF_STAGE = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
T1_SMILES = "C=C(/C=C/OC)OC"


def distorted_water() -> MolecularState:
    """Water with O-H 1.1 Angstrom and H-O-H 120 degrees."""
    a = math.radians(120.0)
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.0], [1.1, 0.0, 0.0], [1.1 * math.cos(a), 1.1 * math.sin(a), 0.0]],
        charge=0,
        spin_multiplicity=1,
    )


def gau_gmax() -> float:
    """GAU's gmax threshold (Eh/Bohr), read from geomeTRIC."""
    from geometric.params import OptParams

    return float(OptParams(convergence_set="GAU").Convergence_gmax)


class FlakyUFF(RDKitFFEngine):
    """rdkit_ff UFF that raises on chosen evaluation numbers (1-based) and counts calls.

    ``fail_with`` maps a call number to the exception raised there. A geomeTRIC
    ``GeomOptNotConvergedError`` raised from the engine stands in for an optimizer failure of the
    step that made the call: it propagates through geomeTRIC exactly as its own would.
    """

    def __init__(self, fail_with: dict[int, BaseException]) -> None:
        """Build on the UFF stage."""
        super().__init__(UFF_STAGE)
        self.fail_with = fail_with
        self.calls = 0

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self.calls += 1
        if self.calls in self.fail_with:
            raise self.fail_with[self.calls]
        return super()._evaluate(state, forces=forces, hessian=hessian)


def not_converged() -> BaseException:
    """Return geomeTRIC's own not-converged error."""
    from geometric.errors import GeomOptNotConvergedError

    return GeomOptNotConvergedError("fake engine: step fails")


class FixedTopologyUFF(Engine):
    """UFF on a fixed RDKit topology from a SMILES (no per-call bond perception).

    rdkit_ff re-perceives bonds at every geometry; rotating T1's diene 180 -> 0 degrees under TRIC
    makes that perception fail mid-run (measured, slice 04 H15), so the dihedral proof uses the
    route resolve measured H15 with: UFF on the SMILES topology.
    """

    tag = "rdkit_ff"
    ENGINE_IMPL = 1
    OPTIONS: dict[str, OptionSpec] = {}

    def __init__(self, mol: Any) -> None:
        """Keep a copy of the RDKit molecule (with H and a conformer)."""
        super().__init__(UFF_STAGE)
        self.mol = Chem.Mol(mol)
        self.calls = 0

    @property
    def identity(self) -> EngineIdentity:
        """rdkit_ff at the installed RDKit."""
        return EngineIdentity(name="rdkit_ff", version=importlib.metadata.version("rdkit"))

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        self.calls += 1
        mol = Chem.Mol(self.mol)
        conformer = mol.GetConformer()
        for i, (x, y, z) in enumerate(state.coordinates):
            conformer.SetAtomPosition(i, Point3D(x, y, z))
        ff = rdForceFieldHelpers.UFFGetMoleculeForceField(mol)
        ff.Initialize()
        energy = kcal_mol_to_hartree(ff.CalcEnergy())
        grad = np.asarray(ff.CalcGrad(), dtype=np.float64) * BOHR_ANGSTROM
        forces_eh_bohr = (-kcal_mol_to_hartree(1.0) * grad).reshape(-1, 3).tolist()
        return RawResult(
            energy_hartree=energy, device="cpu", forces_hartree_per_bohr=forces_eh_bohr
        )


def t1_embedded() -> tuple[Any, MolecularState]:
    """T1 with H, embedded by ETKDG at seed 42, and its state."""
    mol = Chem.AddHs(Chem.MolFromSmiles(T1_SMILES))
    assert AllChem.EmbedMolecule(mol, randomSeed=42) == 0
    st = MolecularState(
        symbols=[a.GetSymbol() for a in mol.GetAtoms()],
        coordinates=mol.GetConformer().GetPositions().tolist(),
        charge=0,
        spin_multiplicity=1,
    )
    return mol, st


def dihedral(mol: Any, coords: list[list[float]], atoms: tuple[int, int, int, int]) -> float:
    """RDKit's dihedral of ``atoms`` at ``coords`` (degrees)."""
    m = Chem.Mol(mol)
    conformer = m.GetConformer()
    for i, (x, y, z) in enumerate(coords):
        conformer.SetAtomPosition(i, Point3D(x, y, z))
    return float(rdMolTransforms.GetDihedralDeg(conformer, *atoms))


# availability and identity


def test_missing_geometric_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """With geometric not importable, construction names the install step."""
    monkeypatch.setitem(sys.modules, "geometric", None)
    with pytest.raises(OptimizerUnavailableError, match="uv sync --extra opt-geometric"):
        GeometricOptimizer()


def test_identity() -> None:
    """The identity is geometric at the installed version."""
    identity = GeometricOptimizer().identity
    assert identity.name == "geometric"
    assert identity.version == importlib.metadata.version("geometric") == "1.1.1"


def test_options_table() -> None:
    """Keyed options and defaults (mission §5 Contracts)."""
    resolved = GeometricOptimizer().resolved_options(None)
    assert resolved == {
        "convergence_set": "GAU",
        "coordsys": "tric",
        "hessian": "never",
        "maxiter": 300,
        "trust": 0.1,
    }


def test_convergence_sets_match_geometric() -> None:
    """The offered sets are exactly geomeTRIC's (read from a failing OptParams lookup)."""
    from geometric.params import OptParams

    spec = GeometricOptimizer.OPTIONS["convergence_set"]
    assert spec.allowed is not None
    for name in spec.allowed:
        OptParams(convergence_set=name)
    with pytest.raises(KeyError):
        OptParams(convergence_set="NOT_A_SET")


@pytest.mark.parametrize(
    "options", [{"coordsys": "prim"}, {"maxiter": 0}, {"trust": -0.1}, {"hessian": "each"}]
)
def test_bad_options_rejected(options: dict[str, Any]) -> None:
    """Disallowed coordsys/hessian and non-positive maxiter/trust raise before any call."""
    engine = FlakyUFF({})
    with pytest.raises(OptimizerInputError):
        GeometricOptimizer().minimize(distorted_water(), engine, options=options)
    assert engine.calls == 0


# convergence


def test_distorted_water_converges_like_rdkit() -> None:
    """UFF water converges; |F|max <= GAU gmax; E within 1e-5 Eh of RDKit's own tight UFF run."""
    engine = RDKitFFEngine(UFF_STAGE)
    result = GeometricOptimizer().minimize(distorted_water(), engine)
    assert result.converged is True
    assert result.recovery_steps == ["tric"]
    assert result.n_engine_calls >= result.n_steps >= 1
    forces = engine.evaluate(result.final_state, forces=True).forces_hartree_per_bohr
    assert forces is not None
    assert max(abs(f) for row in forces for f in row) <= gau_gmax()

    mol = Chem.AddHs(Chem.MolFromSmiles("O"))
    AllChem.EmbedMolecule(mol, randomSeed=1)
    conformer = mol.GetConformer()
    for i, (x, y, z) in enumerate(distorted_water().coordinates):
        conformer.SetAtomPosition(i, Point3D(x, y, z))
    assert rdForceFieldHelpers.UFFOptimizeMolecule(mol, maxIters=10000) == 0
    ff = rdForceFieldHelpers.UFFGetMoleculeForceField(mol)
    ff.Initialize()
    ff.Minimize(maxIts=10000, forceTol=1e-8, energyTol=1e-14)
    reference = kcal_mol_to_hartree(ff.CalcEnergy())
    assert abs(result.final_energy_hartree - reference) <= 1e-5
    assert result.final_state.charge == 0 and result.final_state.spin_multiplicity == 1
    assert result.options == GeometricOptimizer().resolved_options(None)
    assert "constraints" not in result.options


# sandbox


def test_sandbox_leaves_host_logging_and_cwd_alone(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    """No cwd files; root FileHandler and caplog still work; no geomeTRIC stderr; logger kept."""
    root = logging.getLogger()
    app_log = tmp_path / "app.log"
    handler = logging.FileHandler(app_log, mode="w", encoding="utf-8")
    root.addHandler(handler)
    geo = logging.getLogger("geometric")
    before = (list(geo.handlers), geo.level, geo.propagate)
    cwd_before = sorted(os.listdir(os.getcwd()))
    try:
        with caplog.at_level(logging.INFO):
            GeometricOptimizer().minimize(distorted_water(), RDKitFFEngine(UFF_STAGE))
            logging.getLogger("eta_rxncat.test").warning("after the optimization")
        handler.flush()
        assert "after the optimization" in app_log.read_text(encoding="utf-8")
        assert "after the optimization" in caplog.text
        assert not any(r.name.startswith("geometric") for r in caplog.records)
    finally:
        root.removeHandler(handler)
        handler.close()
    assert sorted(os.listdir(os.getcwd())) == cwd_before
    err = capfd.readouterr().err
    assert "geomeTRIC" not in err and "Step " not in err and "Converged" not in err
    assert (list(geo.handlers), geo.level, geo.propagate) == before


# ladder


def test_ladder_recovers_at_step_two() -> None:
    """TRIC failing -> recovery_steps == ['tric', 'tric_tight_trust'] on success at step 2."""
    engine = FlakyUFF({1: not_converged()})
    result = GeometricOptimizer().minimize(distorted_water(), engine)
    assert result.recovery_steps == ["tric", "tric_tight_trust"]
    assert result.n_engine_calls == engine.calls


def test_ladder_exhausted() -> None:
    """Every step failing -> OptimizationFailedError with the three unconstrained steps."""
    engine = FlakyUFF({1: not_converged(), 2: not_converged(), 3: not_converged()})
    with pytest.raises(OptimizationFailedError) as info:
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert info.value.steps == ("tric", "tric_tight_trust", "cartesian")


def test_engine_error_propagates_and_stops_the_ladder() -> None:
    """EngineInputError on call 3 propagates unchanged; no further step or call happens."""
    error = EngineInputError("fake engine refuses call 3")
    engine = FlakyUFF({3: error})
    with pytest.raises(EngineInputError) as info:
        GeometricOptimizer().minimize(distorted_water(), engine)
    assert info.value is error
    assert engine.calls == 3


def test_maxiter_exhaustion_moves_down_the_ladder() -> None:
    """Reaching maxiter raises GeomOptNotConvergedError: the ladder treats it as a failed step."""
    with pytest.raises(OptimizationFailedError) as info:
        GeometricOptimizer().minimize(
            distorted_water(), RDKitFFEngine(UFF_STAGE), options={"maxiter": 1}
        )
    assert info.value.steps == ("tric", "tric_tight_trust", "cartesian")
    assert info.value.last_energy_hartree is not None


def test_constrained_ladder_uses_hdlc_never_cartesian() -> None:
    """A constrained run failing steps 1-2 records step 3 as hdlc (R45; H15: hdlc accepts it)."""
    engine = FlakyUFF({1: not_converged(), 2: not_converged()})
    result = GeometricOptimizer().minimize(distorted_water(), engine, frozen_atom_indices=[0])
    assert result.recovery_steps == ["tric", "tric_tight_trust", "hdlc"]
    engine = FlakyUFF({1: not_converged(), 2: not_converged(), 3: not_converged()})
    with pytest.raises(OptimizationFailedError) as info:
        GeometricOptimizer().minimize(distorted_water(), engine, frozen_atom_indices=[0])
    assert info.value.steps == ("tric", "tric_tight_trust", "hdlc")


# constraints


def test_frozen_atoms_do_not_move() -> None:
    """Frozen atoms move <= 1e-8 Angstrom; the result records the constraint text."""
    start = distorted_water()
    result = GeometricOptimizer().minimize(
        start, RDKitFFEngine(UFF_STAGE), frozen_atom_indices=[0, 1]
    )
    moved = np.abs(
        np.asarray(result.final_state.coordinates[:2]) - np.asarray(start.coordinates[:2])
    )
    assert moved.max() <= 1e-8
    assert result.options["constraints"] == "freeze:0,1"


def test_frozen_index_out_of_range_rejected() -> None:
    """A frozen index >= N raises OptimizerInputError before any engine call."""
    engine = FlakyUFF({})
    with pytest.raises(OptimizerInputError):
        GeometricOptimizer().minimize(distorted_water(), engine, frozen_atom_indices=[3])
    assert engine.calls == 0


def test_planar_t1_dihedral_constraint() -> None:
    """T1 (seed 42) held at phi(0-1-2-3) = 0 converges within 0.1 degrees (R42, H15)."""
    mol, st = t1_embedded()
    assert abs(dihedral(mol, st.coordinates, (0, 1, 2, 3))) > 170.0
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    result = GeometricOptimizer().minimize(
        st, FixedTopologyUFF(mol), dihedral_constraints=[constraint]
    )
    assert abs(dihedral(mol, result.final_state.coordinates, (0, 1, 2, 3))) <= 0.1
    assert result.options["constraints"] == "dihedral:0,1,2,3:0.000000"
    assert result.recovery_steps == ["tric"]


def test_planar_t1_dihedral_on_hdlc() -> None:
    """H15: hdlc accepts the $set dihedral constraint and reaches the target."""
    mol, st = t1_embedded()
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    result = GeometricOptimizer().minimize(
        st,
        FixedTopologyUFF(mol),
        dihedral_constraints=[constraint],
        options={"coordsys": "hdlc"},
    )
    assert abs(dihedral(mol, result.final_state.coordinates, (0, 1, 2, 3))) <= 0.1


@pytest.mark.parametrize(
    ("frozen", "dihedrals"),
    [([0], []), ([], [DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)])],
)
def test_cartesian_with_constraint_rejected_before_any_call(
    frozen: list[int], dihedrals: list[DihedralConstraint]
) -> None:
    """coordsys='cart' plus any constraint raises OptimizerInputError with zero engine calls."""
    mol, st = t1_embedded()
    engine = FixedTopologyUFF(mol)
    with pytest.raises(OptimizerInputError, match="cart"):
        GeometricOptimizer().minimize(
            st,
            engine,
            frozen_atom_indices=frozen,
            dihedral_constraints=dihedrals,
            options={"coordsys": "cart"},
        )
    assert engine.calls == 0


def test_dihedral_index_beyond_state_rejected() -> None:
    """A dihedral index >= N raises OptimizerInputError before any engine call."""
    engine = FlakyUFF({})
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    with pytest.raises(OptimizerInputError, match="out of range"):
        GeometricOptimizer().minimize(distorted_water(), engine, dihedral_constraints=[constraint])
    assert engine.calls == 0


# reproducibility


def test_constrained_run_is_reproducible() -> None:
    """Two identical T1 constrained runs give bit-identical geometries, energies and step counts.

    geomeTRIC draws from numpy's global RNG; without seeding it, the same input converged to
    different structures (slice 04 measurement), so each run seeds it.
    """
    mol, st = t1_embedded()
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    runs = [
        GeometricOptimizer().minimize(st, FixedTopologyUFF(mol), dihedral_constraints=[constraint])
        for _ in range(2)
    ]
    assert runs[0].final_state.coordinates == runs[1].final_state.coordinates
    assert runs[0].final_energy_hartree == runs[1].final_energy_hartree
    assert runs[0].n_steps == runs[1].n_steps
    assert runs[0].n_engine_calls == runs[1].n_engine_calls


def test_host_rng_state_is_restored() -> None:
    """The caller's numpy global RNG stream continues as if no optimization had run."""
    np.random.seed(1234)
    expected = np.random.random(3)
    np.random.seed(1234)
    GeometricOptimizer().minimize(distorted_water(), RDKitFFEngine(UFF_STAGE))
    assert np.array_equal(np.random.random(3), expected)
