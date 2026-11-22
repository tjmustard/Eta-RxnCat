"""Strict Pydantic v2 contracts for molecular states, stages, mapping and thermochemistry.

Every model forbids unknown keys and is frozen. Integers that carry chemistry are
``StrictInt``, so ``True``, ``"1"`` and ``1.0`` are rejected rather than coerced.
"""

import math
from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictInt, model_validator

from eta_rxncat.core.elements import ATOMIC_NUMBERS

StageKind = Literal[
    "conformer_search", "constrained_preopt", "geometry_opt", "frequency", "single_point"
]
"""The computational stages a node can run."""

EngineTag = Literal[
    "rdkit_ff", "mace", "uma_direct", "pyscf_gpu_cpu", "xtb_subprocess", "esen_omol25"
]
"""Frozen engine tags, one per model family (module-boundary names of the Master Plan).

``esen_omol25`` (v0.2.0, R31, ADR-0022 PROPOSED) is the OMol25 eSEN family, a model family of its
own rather than a UMA variant.
"""

SolvationModel = Literal["none", "ddcosmo", "pcm", "alpb"]
"""Implicit-solvation models."""

ScalarValue = str | int | float | bool
"""Value type allowed in free-form option and metadata maps."""

PositiveInt = Annotated[StrictInt, Field(ge=1)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class CoreModel(BaseModel):
    """Base for every core contract: unknown keys rejected, instances immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def _duplicates(values: Iterable[int]) -> list[int]:
    """Return the values that occur more than once, sorted."""
    seen: set[int] = set()
    dupes: set[int] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return sorted(dupes)


def _non_finite_keys(values: Mapping[str, ScalarValue]) -> list[str]:
    """Return the keys whose float values are NaN or infinite."""
    return sorted(
        key
        for key, value in values.items()
        if isinstance(value, float) and not math.isfinite(value)
    )


class MolecularState(CoreModel):
    """One molecular structure with explicit, never-defaulted charge and spin multiplicity.

    Attributes:
        symbols: Canonical element symbols (Z 1-118), one per atom.
        coordinates: Cartesian coordinates in Angstrom, one finite ``[x, y, z]`` row per atom.
        charge: Total formal charge.
        spin_multiplicity: ``2S + 1``.
        active_atom_indices: Unique 0-based indices of the reacting atoms.
        metadata: Free-form scalar annotations.
    """

    symbols: list[str] = Field(min_length=1)
    coordinates: list[list[FiniteFloat]]
    charge: StrictInt
    spin_multiplicity: PositiveInt
    active_atom_indices: list[StrictInt] = Field(default_factory=list)
    metadata: dict[str, ScalarValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_state(self) -> Self:
        unknown = [s for s in self.symbols if s not in ATOMIC_NUMBERS]
        if unknown:
            raise ValueError(f"unknown or non-canonical element symbol(s): {unknown}")
        n_atoms = len(self.symbols)
        if len(self.coordinates) != n_atoms:
            raise ValueError(f"{n_atoms} symbols but {len(self.coordinates)} coordinate rows")
        for row_index, row in enumerate(self.coordinates):
            if len(row) != 3:
                raise ValueError(f"coordinate row {row_index} has {len(row)} values, expected 3")
        out_of_range = [i for i in self.active_atom_indices if not 0 <= i < n_atoms]
        if out_of_range:
            raise ValueError(f"active_atom_indices {out_of_range} out of range for {n_atoms} atoms")
        dupes = _duplicates(self.active_atom_indices)
        if dupes:
            raise ValueError(f"duplicate active_atom_indices: {dupes}")
        self._check_electrons()
        return self

    def _check_electrons(self) -> None:
        """Check that charge and multiplicity are possible for this electron count."""
        n_electrons = sum(ATOMIC_NUMBERS[s] for s in self.symbols) - self.charge
        unpaired = self.spin_multiplicity - 1
        if n_electrons < 0:
            raise ValueError(f"charge {self.charge} leaves {n_electrons} electrons")
        if unpaired > n_electrons or (n_electrons - unpaired) % 2 != 0:
            raise ValueError(
                f"spin_multiplicity {self.spin_multiplicity} is impossible with "
                f"{n_electrons} electrons (charge {self.charge})"
            )


class Solvation(CoreModel):
    """Implicit-solvation settings of a stage.

    Attributes:
        model: Solvation model; ``none`` means gas phase.
        solvent: Solvent name, if the model takes one.
        dielectric: Dielectric constant (> 0), if the model takes one.
    """

    model: SolvationModel = "none"
    solvent: str | None = Field(default=None, min_length=1)
    dielectric: PositiveFiniteFloat | None = None

    @model_validator(mode="after")
    def _check_parameters(self) -> Self:
        given = self.solvent is not None or self.dielectric is not None
        if self.model == "none" and given:
            raise ValueError("solvation model 'none' takes neither solvent nor dielectric")
        if self.model != "none" and not given:
            raise ValueError(f"solvation model '{self.model}' needs a solvent or a dielectric")
        return self


_SOLVATION_ENGINES: Mapping[str, str] = MappingProxyType(
    {"ddcosmo": "pyscf_gpu_cpu", "pcm": "pyscf_gpu_cpu", "alpb": "xtb_subprocess"}
)
"""The only engine each non-trivial solvation model may run on."""


class StageConfig(CoreModel):
    """One computational stage: what to run, with which engine and settings.

    Attributes:
        kind: The stage kind.
        engine: The engine tag.
        method: Functional, force field or model name; never the placeholder ``default``.
        basis: Basis set; required for ``pyscf_gpu_cpu`` and forbidden otherwise.
        solvation: Implicit-solvation settings.
        frozen_atom_indices: Unique 0-based atoms held fixed; required for ``constrained_preopt``.
        options: Engine-specific scalar options (floats must be finite).
    """

    kind: StageKind
    engine: EngineTag
    method: str = Field(min_length=1)
    basis: str | None = None
    solvation: Solvation = Field(default_factory=Solvation)
    frozen_atom_indices: list[NonNegativeInt] = Field(default_factory=list)
    options: dict[str, ScalarValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_stage(self) -> Self:
        if not self.method.strip() or self.method.strip().lower() == "default":
            raise ValueError(f"method {self.method!r} is not a concrete method name")
        if self.engine == "pyscf_gpu_cpu":
            if not self.basis:
                raise ValueError("engine 'pyscf_gpu_cpu' requires a non-empty basis")
        elif self.basis is not None:
            raise ValueError(f"engine '{self.engine}' takes no basis")
        required_engine = _SOLVATION_ENGINES.get(self.solvation.model)
        if required_engine is not None and self.engine != required_engine:
            raise ValueError(
                f"solvation model '{self.solvation.model}' needs engine '{required_engine}', "
                f"not '{self.engine}'"
            )
        dupes = _duplicates(self.frozen_atom_indices)
        if dupes:
            raise ValueError(f"duplicate frozen_atom_indices: {dupes}")
        if self.kind == "constrained_preopt" and not self.frozen_atom_indices:
            raise ValueError("stage 'constrained_preopt' requires frozen_atom_indices")
        bad = _non_finite_keys(self.options)
        if bad:
            raise ValueError(f"options with non-finite values: {bad}")
        return self


class EngineIdentity(CoreModel):
    """The engine that produced a result: tag, version and optional model weights id.

    Attributes:
        name: Engine tag.
        version: Engine version string.
        model: Model weights identifier (e.g. ``uma-s-1.2.1``), if any.
    """

    name: EngineTag
    version: str = Field(min_length=1)
    model: str | None = None


class AtomMappingSpec(CoreModel):
    """Ordered atom-surgery lists of a template (0-based, order-sensitive).

    Attributes:
        keep: Atoms retained from the template.
        delete: Atoms removed from the template.
        alignment: Atoms used for alignment onto a reference core (at least 3, all kept).
        anchors: Kept atoms where substituents attach.
    """

    keep: list[StrictInt]
    delete: list[StrictInt]
    alignment: list[StrictInt]
    anchors: list[StrictInt] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_lists(self) -> Self:
        lists = {
            "keep": self.keep,
            "delete": self.delete,
            "alignment": self.alignment,
            "anchors": self.anchors,
        }
        for name, values in lists.items():
            negative = [i for i in values if i < 0]
            if negative:
                raise ValueError(f"{name} has negative indices: {negative}")
            dupes = _duplicates(values)
            if dupes:
                raise ValueError(f"{name} has duplicate indices: {dupes}")
        keep = set(self.keep)
        overlap = sorted(keep & set(self.delete))
        if overlap:
            raise ValueError(f"keep and delete overlap on {overlap}")
        not_kept = [i for i in self.alignment if i not in keep]
        if not_kept:
            raise ValueError(f"alignment indices {not_kept} are not in keep")
        if len(self.alignment) < 3:
            raise ValueError(f"alignment needs at least 3 atoms, got {len(self.alignment)}")
        loose = [i for i in self.anchors if i not in keep]
        if loose:
            raise ValueError(f"anchors {loose} are not in keep")
        return self

    def check_atom_count(self, n_atoms: int) -> None:
        """Check the lists against a template of ``n_atoms`` atoms.

        Args:
            n_atoms: Number of atoms in the template's index space.

        Raises:
            ValueError: If an index is ``>= n_atoms`` or keep and delete do not cover every atom.
        """
        everything = self.keep + self.delete + self.alignment + self.anchors
        too_big = sorted({i for i in everything if i >= n_atoms})
        if too_big:
            raise ValueError(f"mapping indices {too_big} out of range for {n_atoms} atoms")
        missing = sorted(set(range(n_atoms)) - set(self.keep) - set(self.delete))
        if missing:
            raise ValueError(f"atoms {missing} are in neither keep nor delete")


class ThermoConfig(CoreModel):
    """Thermochemistry settings: Grimme quasi-RRHO at a 1 M standard state by default.

    Attributes:
        entropy_model: Entropy treatment.
        temperature_k: Temperature in K.
        pressure_atm: Pressure in atm.
        standard_state_mol_l: Standard-state concentration in mol/L.
        qrrho_cutoff_cm1: Quasi-RRHO cutoff frequency omega_0 in cm^-1.
        qrrho_alpha: Quasi-RRHO damping exponent alpha.
        qrrho_rotor_moment_kg_m2: Average moment of inertia B_av in kg m^2.
    """

    entropy_model: Literal["grimme_qrrho"] = "grimme_qrrho"
    temperature_k: PositiveFiniteFloat = 298.15
    pressure_atm: PositiveFiniteFloat = 1.0
    standard_state_mol_l: PositiveFiniteFloat = 1.0
    qrrho_cutoff_cm1: PositiveFiniteFloat = 100.0
    qrrho_alpha: PositiveFiniteFloat = 4.0
    qrrho_rotor_moment_kg_m2: PositiveFiniteFloat = 1.0e-44
