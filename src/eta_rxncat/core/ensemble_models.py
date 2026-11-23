"""Conformer-ensemble contracts: one conformer record and a Boltzmann ensemble (v0.3.0).

Data only: pydantic and the standard library, no numpy and no RDKit. ``eta_rxncat.conformers``
and ``eta_rxncat.thermo`` compute the weights and free energies; these models check them.
"""

from typing import Literal, Self

from pydantic import Field, FiniteFloat, field_validator, model_validator

from eta_rxncat.core.models import (
    CoreModel,
    MolecularState,
    NonNegativeInt,
    PositiveFiniteFloat,
    _duplicates,
)
from eta_rxncat.core.optimization_models import OptimizationResult
from eta_rxncat.core.thermo_models import ThermoResult

_WEIGHT_SUM_TOL = 1e-12


class ConformerRecord(CoreModel):
    """One optimized conformer with its thermochemistry.

    Attributes:
        state: The optimized structure.
        optimization: The optimization that produced it.
        thermo: Its thermochemistry.
        degeneracy: 2 for a chiral conformer of a graph-achiral molecule (its mirror image is
            the same energy), else 1.
        source_ids: Unique ids of the pool members that converged to this conformer (>= 1).
    """

    state: MolecularState
    optimization: OptimizationResult
    thermo: ThermoResult
    degeneracy: Literal[1, 2]
    source_ids: list[NonNegativeInt] = Field(min_length=1)

    @field_validator("degeneracy", mode="before")
    @classmethod
    def _strict_degeneracy(cls, value: object) -> object:
        # Literal[1, 2] alone accepts True and 2.0 (they compare equal); ADR-0003 wants ints.
        if type(value) is not int:
            raise ValueError(f"degeneracy must be the int 1 or 2, not {value!r}")
        return value

    @model_validator(mode="after")
    def _check_record(self) -> Self:
        dupes = _duplicates(self.source_ids)
        if dupes:
            raise ValueError(f"duplicate source_ids: {dupes}")
        if self.thermo.n_atoms != len(self.state.symbols):
            raise ValueError(
                f"thermo.n_atoms {self.thermo.n_atoms} != {len(self.state.symbols)} atoms in state"
            )
        return self


class ConformerEnsemble(CoreModel):
    """The Boltzmann ensemble of one species' conformers at one temperature.

    Attributes:
        species_id: Species identifier.
        smiles: Input SMILES.
        records: The kept conformers (>= 1), all with the same symbols, charge and multiplicity.
        boltzmann_weights: One weight per record (degeneracy included), >= 0, summing to 1.
        lowest_index: Index of the record with the lowest G (ties go to the lowest index).
        ensemble_gibbs_hartree: Ensemble free energy (Eh).
        temperature_k: Temperature (K); equal to every record's ``thermo.config.temperature_k``.
    """

    species_id: str = Field(min_length=1)
    smiles: str = Field(min_length=1)
    records: list[ConformerRecord] = Field(min_length=1)
    boltzmann_weights: list[FiniteFloat]
    lowest_index: NonNegativeInt
    ensemble_gibbs_hartree: FiniteFloat
    temperature_k: PositiveFiniteFloat

    @model_validator(mode="after")
    def _check_ensemble(self) -> Self:
        records = self.records
        weights = self.boltzmann_weights
        if len(weights) != len(records):
            raise ValueError(f"{len(weights)} boltzmann_weights for {len(records)} records")
        negative = [i for i, w in enumerate(weights) if w < 0]
        if negative:
            raise ValueError(f"negative boltzmann_weights at {negative}")
        total = sum(weights)
        if abs(total - 1.0) > _WEIGHT_SUM_TOL:
            raise ValueError(f"boltzmann_weights sum to {total!r}, not 1")
        gibbs = [r.thermo.gibbs_free_energy_hartree for r in records]
        lowest = min(range(len(gibbs)), key=lambda i: (gibbs[i], i))
        if self.lowest_index != lowest:
            raise ValueError(f"lowest_index {self.lowest_index} != argmin of G ({lowest})")
        first = records[0].state
        for i, record in enumerate(records[1:], start=1):
            state = record.state
            if state.symbols != first.symbols:
                raise ValueError(f"record {i} symbols differ from record 0")
            if state.charge != first.charge:
                raise ValueError(f"record {i} charge {state.charge} != {first.charge}")
            if state.spin_multiplicity != first.spin_multiplicity:
                raise ValueError(
                    f"record {i} spin_multiplicity {state.spin_multiplicity} != "
                    f"{first.spin_multiplicity}"
                )
        bad_t = [
            i for i, r in enumerate(records) if r.thermo.config.temperature_k != self.temperature_k
        ]
        if bad_t:
            raise ValueError(f"records {bad_t} have thermo temperature != {self.temperature_k} K")
        return self
