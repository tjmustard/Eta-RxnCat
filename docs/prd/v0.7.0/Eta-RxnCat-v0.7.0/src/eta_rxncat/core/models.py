"""Clean-room Pydantic v2 schemas for molecular states, mapping specs, and thermochemistry."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


class NodeKind(str, Enum):
    """Chemical classification of a stationary point or multi-species state."""

    REACTANT = "reactant"
    INTERMEDIATE = "intermediate"
    TRANSITION_STATE = "transition_state"
    PRODUCT = "product"
    OFF_CYCLE_SINK = "off_cycle_sink"


class StageKind(str, Enum):
    """Discrete computational stages cached independently by content hash."""

    CONFORMER_SEARCH = "conformer_search"
    CONSTRAINED_PREOPT = "constrained_preopt"
    GEOMETRY_OPT = "geometry_opt"
    FREQUENCY = "frequency"
    SINGLE_POINT = "single_point"


class SolvationSpec(BaseModel):
    """Implicit solvation specification."""

    model: Literal["none", "ddcosmo", "pcm", "alpb"] = "none"
    solvent: str | None = None
    dielectric: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def _validate_solvent(self) -> SolvationSpec:
        if self.model != "none" and not self.solvent and self.dielectric is None:
            raise ValueError(f"Solvation model '{self.model}' requires 'solvent' or 'dielectric'.")
        return self


class StageConfig(BaseModel):
    """Configuration for a single workflow stage (enables incremental stage appending)."""

    stage: StageKind
    engine: Literal["rdkit_ff", "xtb", "mace", "uma", "pyscf"]
    method: str = Field(
        default="default",
        description="Functional/force-field/model tag (e.g., 'UFF', 'GFN2-xTB', 'uma-s-1.2.1', 'wB97X-D3BJ').",
    )
    basis: str | None = Field(
        default=None,
        description="Basis set for QM engines (e.g., 'def2-SVP', 'def2-TZVPP').",
    )
    solvation: SolvationSpec = Field(default_factory=SolvationSpec)
    extra_options: dict[str, str | int | float | bool] = Field(default_factory=dict)

    def stage_hash(self) -> str:
        """Deterministic SHA-256 hash of stage settings."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ThermoConfig(BaseModel):
    """Thermochemistry settings defaulting to Grimme quasi-RRHO and 1 M standard state."""

    temperature_k: float = Field(default=298.15, gt=0.0)
    pressure_atm: float = Field(default=1.0, gt=0.0)
    concentration_mol_l: float | None = Field(
        default=1.0,
        gt=0.0,
        description="Standard-state concentration in mol/L (1.0 M applies +1.89 kcal/mol at 298.15 K).",
    )
    quasi_rrho_mode: Literal["grimme", "head_gordon", "none"] = "grimme"
    omega0_cm1: float = Field(
        default=100.0,
        gt=0.0,
        description="Cutoff frequency (cm^-1) for quasi-RRHO damping.",
    )


class MolecularState(BaseModel):
    """3D atomic structure with mandatory charge and spin multiplicity."""

    name: str
    symbols: list[str] = Field(..., min_length=1)
    coordinates: list[list[float]] = Field(..., min_length=1, description="Cartesian coordinates in Angstroms.")
    charge: int = Field(..., description="Total formal integer charge of the state.")
    spin_multiplicity: int = Field(..., ge=1, description="Spin multiplicity (2S + 1).")
    active_atom_indices: list[int] = Field(
        default_factory=list,
        description="0-based indices of atoms directly participating in bond-forming/breaking.",
    )
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_shapes_and_indices(self) -> MolecularState:
        n_atoms = len(self.symbols)
        if len(self.coordinates) != n_atoms:
            raise ValueError(f"symbols length ({n_atoms}) != coordinates length ({len(self.coordinates)}).")
        for idx, xyz in enumerate(self.coordinates):
            if len(xyz) != 3:
                raise ValueError(f"Atom {idx} coordinates must have length 3, got {len(xyz)}.")
        for a_idx in self.active_atom_indices:
            if a_idx < 0 or a_idx >= n_atoms:
                raise ValueError(f"active_atom_indices entry {a_idx} out of bounds for {n_atoms} atoms.")
        return self

    def coords_array(self) -> np.ndarray:
        return np.asarray(self.coordinates, dtype=np.float64)

    def geometry_hash(self, decimals: int = 5) -> str:
        """Content hash over elements, rounded coordinates, charge, and spin multiplicity."""
        rounded = np.round(self.coords_array(), decimals=decimals).tolist()
        payload = json.dumps(
            {
                "symbols": self.symbols,
                "coordinates": rounded,
                "charge": self.charge,
                "spin_multiplicity": self.spin_multiplicity,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AtomMappingSpec(BaseModel):
    """Ordered atom surgery specification inspired by nMap / Eta_Scripts.

    Indices are 0-based and order-sensitive:
    - keep_atoms: atoms retained from the template core/scaffold.
    - delete_atoms: leaving-group / dummy atoms stripped from the template prior to attachment.
    - alignment_atoms: ordered atom indices used for quaternion/Kabsch alignment onto reference core.
    - attachment_anchors: ordered atom indices where incoming R-groups/ligands connect.
    """

    keep_atoms: list[int] = Field(..., min_length=1)
    delete_atoms: list[int] = Field(default_factory=list)
    alignment_atoms: list[int] = Field(..., min_length=3)
    attachment_anchors: list[int] = Field(default_factory=list)

    @field_validator("alignment_atoms")
    @classmethod
    def _unique_alignment(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("alignment_atoms must not contain duplicate indices.")
        return v

    @model_validator(mode="after")
    def _check_disjoint_keep_delete(self) -> AtomMappingSpec:
        overlap = set(self.keep_atoms).intersection(self.delete_atoms)
        if overlap:
            raise ValueError(f"keep_atoms and delete_atoms overlap on indices: {sorted(overlap)}")
        if any(idx in self.delete_atoms for idx in self.alignment_atoms):
            raise ValueError("alignment_atoms cannot reference indices listed in delete_atoms.")
        return self


class VibrationalMode(BaseModel):
    """Single normal mode from harmonic vibrational analysis."""

    frequency_cm1: float
    displacement_vectors: list[list[float]]
    active_core_kinetic_fraction: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of mass-weighted mode kinetic energy localized on active_atom_indices.",
    )


class PotentialResult(BaseModel):
    """Standardized output returned by any Potential engine."""

    electronic_energy_hartree: float
    forces_hartree_per_bohr: list[list[float]] | None = None
    hessian_hartree_per_bohr2: list[list[float]] | None = None
    wall_time_seconds: float = 0.0
    backend_device: str = "cpu"
    recovery_steps_used: list[str] = Field(default_factory=list)


class ThermoResult(BaseModel):
    """Thermochemical corrections and Gibbs free energy for a stationary point."""

    electronic_energy_hartree: float
    zpe_hartree: float
    thermal_enthalpy_corr_hartree: float
    entropy_cal_per_mol_k: float
    gibbs_free_energy_hartree: float
    imaginary_frequencies_cm1: list[float] = Field(default_factory=list)
    is_valid_stationary_point: bool = True
    validation_notes: list[str] = Field(default_factory=list)


class ConformerEnsemble(BaseModel):
    """Collection of conformers for a single MolecularState with Boltzmann weights."""

    species_name: str
    conformers: list[MolecularState] = Field(..., min_length=1)
    gibbs_energies_hartree: list[float] = Field(..., min_length=1)
    boltzmann_weights: list[float] = Field(..., min_length=1)
    lowest_conformer_index: int = Field(..., ge=0)
    boltzmann_averaged_gibbs_hartree: float

    @model_validator(mode="after")
    def _check_lengths(self) -> ConformerEnsemble:
        n = len(self.conformers)
        if len(self.gibbs_energies_hartree) != n or len(self.boltzmann_weights) != n:
            raise ValueError("conformers, gibbs_energies_hartree, and boltzmann_weights must have equal length.")
        if not np.isclose(sum(self.boltzmann_weights), 1.0, atol=1e-4):
            raise ValueError(f"boltzmann_weights must sum to 1.0, got {sum(self.boltzmann_weights):.6f}.")
        return self
