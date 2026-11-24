"""Activation energies from a TS record and its reactants' ensembles (v0.5.0, mission §5 "Barrier").

A TS has no SMILES (mission R1): atom and charge conservation are checked from the reactants'
SMILES against the TS geometry's symbols and charge, and a TS never passes through
``ReactionSpec``. The TS enters with its single ``ThermoResult`` and degeneracy 1 (TJ Q-TJ2 "A");
the reactants enter by v0.3.0's ensemble conventions (Boltzmann-weighted E and H,
``ensemble_gibbs_hartree``).

Energy source: the TS's E is ``ts.thermo.electronic_energy_hartree``, the energy of the frequency
stage at the TS geometry; a reactant record's E is its optimizer's final energy. Measured for
xtb at TS1a_n (slice 06): a gradient run and a Hessian run at one geometry give bitwise equal
energies, so both sides are the engine's energy at the stationary geometry.
"""

import math
from collections import Counter
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rdkit import Chem

from eta_rxncat.core import ConformerEnsemble, ThermoConfig, TransitionStateRecord
from eta_rxncat.core.models import PositiveInt
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator.reaction import _weighted, standard_state_shift_kcal_mol


class BarrierSpec(BaseModel):
    """The reactants of one transition state.

    Attributes:
        reactants: ``(species_id, coefficient)`` pairs.
        ts_id: The TS record's identifier.
        smiles: SMILES of every reactant (formal charge from the SMILES).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reactants: tuple[tuple[str, PositiveInt], ...] = Field(min_length=1)
    ts_id: str = Field(min_length=1)
    smiles: dict[str, str]

    @model_validator(mode="after")
    def _check_smiles(self) -> "BarrierSpec":
        for species_id, _ in self.reactants:
            if species_id not in self.smiles:
                raise ValueError(f"reactant {species_id!r} has no SMILES")
            if Chem.MolFromSmiles(self.smiles[species_id]) is None:
                raise ValueError(f"SMILES of {species_id!r} does not parse")
        return self

    @property
    def delta_n(self) -> int:
        """Moles of TS (one) minus moles of reactants."""
        return 1 - sum(c for _, c in self.reactants)

    def reactant_composition(self) -> tuple[Counter[str], int]:
        """Return the reactants' summed element counts (hydrogens added) and formal charge."""
        atoms: Counter[str] = Counter()
        charge = 0
        for species_id, coeff in self.reactants:
            mol = Chem.AddHs(Chem.MolFromSmiles(self.smiles[species_id]))
            for atom in mol.GetAtoms():
                atoms[atom.GetSymbol()] += coeff
            charge += coeff * Chem.GetFormalCharge(mol)
        return atoms, charge


class BarrierEnergies(BaseModel):
    """Activation energies in kcal/mol.

    ``dG_dagger_1M`` uses free energies at the config's standard state; ``dG_dagger_1atm``
    removes the standard-state correction: ``dG_1atm = dG_1M - delta_n RT ln(c RT / p)``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dE_dagger_kcal_mol: float
    dH_dagger_kcal_mol: float
    dG_dagger_1atm_kcal_mol: float
    dG_dagger_1M_kcal_mol: float
    delta_n: int


def activation_free_energy(
    spec: BarrierSpec,
    ensembles: Mapping[str, ConformerEnsemble],
    ts: TransitionStateRecord,
    config: ThermoConfig,
) -> BarrierEnergies:
    """Return dE, dH and dG (1 M and 1 atm) of activation from the reactants to ``ts``.

    Raises:
        KeyError: If a reactant's ensemble is missing.
        ValueError: The TS id differs; atoms or charge are not conserved (both sides named); a
            temperature differs from ``config``'s; or a record's or the TS's thermo config is
            not ``config`` (the v0.3.0 R51 standard-state check).
    """
    if ts.ts_id != spec.ts_id:
        raise ValueError(f"TS record {ts.ts_id!r} is not the spec's {spec.ts_id!r}")
    atoms, charge = spec.reactant_composition()
    ts_atoms = Counter(ts.state.symbols)
    if atoms != ts_atoms:
        raise ValueError(
            f"atoms not conserved: reactants {dict(sorted(atoms.items()))}, "
            f"TS {dict(sorted(ts_atoms.items()))}"
        )
    if charge != ts.state.charge:
        raise ValueError(f"charge not conserved: reactants {charge}, TS {ts.state.charge}")
    _check_configs(spec, ensembles, ts, config)

    def reactants(kind: str) -> float:
        def value(species_id: str) -> float:
            ensemble = ensembles[species_id]
            return ensemble.ensemble_gibbs_hartree if kind == "G" else _weighted(ensemble, kind)

        return math.fsum(c * value(s) for s, c in spec.reactants)

    thermo = ts.thermo
    ts_e = thermo.electronic_energy_hartree
    ts_h = ts_e + thermo.thermal_correction_enthalpy_hartree
    ts_g = thermo.gibbs_free_energy_hartree
    dg_1m = (ts_g - reactants("G")) * HARTREE_KCAL_MOL
    return BarrierEnergies(
        dE_dagger_kcal_mol=(ts_e - reactants("E")) * HARTREE_KCAL_MOL,
        dH_dagger_kcal_mol=(ts_h - reactants("H")) * HARTREE_KCAL_MOL,
        dG_dagger_1M_kcal_mol=dg_1m,
        dG_dagger_1atm_kcal_mol=dg_1m - spec.delta_n * standard_state_shift_kcal_mol(config),
        delta_n=spec.delta_n,
    )


def _check_configs(
    spec: BarrierSpec,
    ensembles: Mapping[str, ConformerEnsemble],
    ts: TransitionStateRecord,
    config: ThermoConfig,
) -> None:
    """Refuse a temperature or thermo config that differs from ``config`` (R51), by name."""
    if ts.thermo.config.temperature_k != config.temperature_k:
        raise ValueError(f"TS {ts.ts_id!r} thermo is not at {config.temperature_k} K")
    if ts.thermo.config != config:
        raise ValueError(
            f"TS {ts.ts_id!r}: thermo config {ts.thermo.config} != the barrier's {config}"
        )
    for species_id, _ in spec.reactants:
        ensemble = ensembles[species_id]
        if ensemble.temperature_k != config.temperature_k:
            raise ValueError(f"ensemble {species_id!r} is not at {config.temperature_k} K")
        for i, record in enumerate(ensemble.records):
            if record.thermo.config != config:
                raise ValueError(
                    f"species {species_id!r} record {i}: thermo config {record.thermo.config} "
                    f"!= the barrier's {config}"
                )
