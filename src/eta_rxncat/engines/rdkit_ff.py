"""RDKit UFF / MMFF94 engine (tag ``rdkit_ff``): energies, analytic forces, FD Hessian.

Only neutral closed-shell states are represented (TJ v0.2.0 Q2 "A"; lead decision on slice 05):
charge 0 and multiplicity 1. Bonds are perceived with ``rdDetermineBonds.DetermineBonds`` at
charge 0, and the perceived molecule must round-trip (R14): the same element multiset, total
formal charge 0, no radical electrons and no implicit hydrogens. Anything else, a perception
failure or missing force field parameters is refused with ``EngineInputError``; there is no
coordinates-only fallback.

Remaining risk (R14): perception can choose a different resonance or bond-order assignment with
the same formula and charge; the force field then types those bonds.

RDKit is BSD-3-Clause and is imported lazily, inside this module's methods only.
"""

from collections import Counter
from typing import Any, ClassVar

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.engines.base import Engine, RawResult
from eta_rxncat.engines.errors import EngineInputError
from eta_rxncat.engines.fd import fd_hessian
from eta_rxncat.engines.identity import library_version
from eta_rxncat.engines.options import OptionSpec, normalise_solvent
from eta_rxncat.engines.units import (
    angstrom_to_bohr,
    bohr_to_angstrom,
    kcal_mol_per_angstrom_to_hartree_per_bohr,
    kcal_mol_to_hartree,
)

METHODS = ("uff", "mmff94")
"""Accepted ``StageConfig.method`` values (case-insensitive; keyed lowercase)."""


class RDKitFFEngine(Engine):
    """UFF or MMFF94 single points with analytic forces and a central-difference Hessian.

    ``stage.method`` is ``uff`` or ``mmff94``. Keyed options: ``fd_step_bohr`` (0.005) and
    ``engine_impl`` (1). No runtime arguments.
    """

    tag = "rdkit_ff"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {"fd_step_bohr": OptionSpec(float, 0.005)}

    def __init__(self, stage: StageConfig, **runtime: Any) -> None:
        """Resolve the stage and check the method.

        Raises:
            EngineInputError: a method other than ``uff``/``mmff94``, a non-positive
                ``fd_step_bohr``, an unknown option or a runtime argument.
        """
        super().__init__(stage, **runtime)
        if self.stage.method not in METHODS:
            raise EngineInputError(
                f"rdkit_ff: method {stage.method!r} is not one of {list(METHODS)}"
            )
        step = self.stage.options["fd_step_bohr"]
        if not isinstance(step, float) or not step > 0:
            raise EngineInputError(f"rdkit_ff: option 'fd_step_bohr' must be > 0, not {step!r}")
        self._step_bohr = step

    @classmethod
    def normalise_stage(cls, stage: StageConfig) -> StageConfig:
        """Lowercase the solvent and the method, so ``UFF`` and ``uff`` key the same."""
        stage = normalise_solvent(stage)
        if stage.method == stage.method.lower():
            return stage
        data = stage.model_dump()
        data["method"] = stage.method.lower()
        return StageConfig.model_validate(data)

    @property
    def identity(self) -> EngineIdentity:
        """``rdkit_ff`` at the installed RDKit version; no model weights."""
        return EngineIdentity(name="rdkit_ff", version=library_version("rdkit"), model=None)

    def _refuse(self, state: MolecularState, why: str) -> EngineInputError:
        return EngineInputError(
            f"rdkit_ff: charge {state.charge}, multiplicity {state.spin_multiplicity}: {why}"
        )

    def _perceive(self, state: MolecularState) -> Any:
        """Return the bond-perceived RDKit molecule for ``state`` (charge 0), or refuse."""
        if state.charge != 0 or state.spin_multiplicity != 1:
            raise self._refuse(
                state,
                "only neutral closed-shell states (charge 0, multiplicity 1) are supported",
            )
        from rdkit import Chem
        from rdkit.Chem import rdDetermineBonds
        from rdkit.Geometry import Point3D

        rw = Chem.RWMol()
        for symbol in state.symbols:
            rw.AddAtom(Chem.Atom(symbol))
        conformer = Chem.Conformer(len(state.symbols))
        for index, (x, y, z) in enumerate(state.coordinates):
            conformer.SetAtomPosition(index, Point3D(x, y, z))
        rw.AddConformer(conformer, assignId=True)
        mol = rw.GetMol()
        try:
            rdDetermineBonds.DetermineBonds(mol, charge=state.charge)
            # Sanitising sets valences and hybridisation; without it the force-field typers hit
            # RDKit invariant violations (seen for a lone Pd atom).
            Chem.SanitizeMol(mol)
        except ValueError as exc:
            # RDKit 2026.09: DetermineBonds raises ValueError for unassignable bond orders and
            # for elements without defined valences (e.g. Pd with ligands); SanitizeMol raises
            # MolSanitizeException, a ValueError subclass.
            raise self._refuse(state, f"RDKit bond perception failed: {exc}") from exc
        perceived = Counter(atom.GetSymbol() for atom in mol.GetAtoms())
        formal = sum(atom.GetFormalCharge() for atom in mol.GetAtoms())
        radicals = sum(atom.GetNumRadicalElectrons() for atom in mol.GetAtoms())
        # Implicit hydrogens would make the force field see atoms the state does not have
        # (RDKit gives a lone C atom four), so the round-trip requires none.
        implicit_h = sum(atom.GetNumImplicitHs() for atom in mol.GetAtoms())
        if perceived != Counter(state.symbols) or formal != state.charge or radicals or implicit_h:
            raise self._refuse(
                state,
                f"perception round-trip mismatch (elements {dict(perceived)}, formal charge "
                f"{formal}, radical electrons {radicals}, implicit hydrogens {implicit_h})",
            )
        return mol

    def _force_field(self, state: MolecularState, mol: Any) -> Any:
        """Return the initialised UFF or MMFF94 force field for ``mol``, or refuse."""
        from rdkit.Chem import rdForceFieldHelpers as helpers

        if self.stage.method == "uff":
            if not helpers.UFFHasAllMoleculeParams(mol):
                raise self._refuse(state, "UFF has no parameters for some atom types")
            ff = helpers.UFFGetMoleculeForceField(mol, ignoreInterfragInteractions=False)
        else:
            if not helpers.MMFFHasAllMoleculeParams(mol):
                raise self._refuse(state, "MMFF94 has no parameters for some atom types")
            props = helpers.MMFFGetMoleculeProperties(mol, mmffVariant="MMFF94")
            ff = helpers.MMFFGetMoleculeForceField(mol, props, ignoreInterfragInteractions=False)
        if ff is None:
            raise self._refuse(state, f"RDKit could not set up {self.stage.method}")
        ff.Initialize()
        return ff

    def _energy_and_gradient(
        self, state: MolecularState, mol: Any, positions_ang: list[float]
    ) -> tuple[float, list[float]]:
        """Return (kcal/mol, kcal/mol/A gradient) of a force field built AT ``positions_ang``.

        RDKit 2026.09.2's ``CalcGrad(positions)`` is wrong away from the force field's own
        conformer (its gradient no longer matches ``CalcEnergy``; measured up to ~45
        kcal/mol/A on water), so every geometry gets a fresh force field on a copy of the
        already-perceived ``mol``, with its conformer moved there. Topology and atom typing are
        fixed by the one perception; the gradient is only ever taken at the force field's own
        coordinates, where it matches the energy to ~1e-8.
        """
        from rdkit import Chem
        from rdkit.Geometry import Point3D

        copy = Chem.Mol(mol)
        conformer = copy.GetConformer()
        for index in range(copy.GetNumAtoms()):
            x, y, z = positions_ang[3 * index : 3 * index + 3]
            conformer.SetAtomPosition(index, Point3D(x, y, z))
        ff = self._force_field(state, copy)
        # Read both values while ``copy`` is alive: the force field points into its conformer.
        energy = float(ff.CalcEnergy())
        gradient = [float(g) for g in ff.CalcGrad()]
        return energy, gradient

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        mol = self._perceive(state)
        n_atoms = len(state.symbols)

        def forces_at(coords_bohr: list[list[float]]) -> list[list[float]]:
            positions = [bohr_to_angstrom(v) for row in coords_bohr for v in row]
            _, grad = self._energy_and_gradient(state, mol, positions)
            flat = [-kcal_mol_per_angstrom_to_hartree_per_bohr(g) for g in grad]
            return [flat[3 * a : 3 * a + 3] for a in range(n_atoms)]

        positions = [v for row in state.coordinates for v in row]
        energy, grad = self._energy_and_gradient(state, mol, positions)
        result = RawResult(energy_hartree=kcal_mol_to_hartree(energy), device="cpu")
        if forces or hessian:
            flat = [-kcal_mol_per_angstrom_to_hartree_per_bohr(g) for g in grad]
            result.forces_hartree_per_bohr = [flat[3 * a : 3 * a + 3] for a in range(n_atoms)]
        if hessian:
            coords_bohr = [[angstrom_to_bohr(v) for v in row] for row in state.coordinates]
            matrix, asym = fd_hessian(forces_at, coords_bohr, self._step_bohr)
            result.hessian_hartree_per_bohr2 = matrix
            result.hessian_method = "finite_difference"
            result.hessian_max_asymmetry = asym
        return result
