"""Reaction energies from species ensembles, at 1 atm and at the standard-state concentration."""

import math
from collections import Counter
from collections.abc import Mapping
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rdkit import Chem

from eta_rxncat.core import ConformerEnsemble, ThermoConfig
from eta_rxncat.core.models import PositiveInt
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.thermo.constants import ATM_PA, J_PER_MOL_TO_HARTREE, R_GAS


class ReactionSpec(BaseModel):
    """A balanced reaction between species.

    Attributes:
        reactants: ``(species_id, coefficient)`` pairs.
        products: ``(species_id, coefficient)`` pairs.
        smiles: SMILES of every species used, for the conservation check (formal charge from
            the SMILES).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reactants: tuple[tuple[str, PositiveInt], ...] = Field(min_length=1)
    products: tuple[tuple[str, PositiveInt], ...] = Field(min_length=1)
    smiles: dict[str, str]

    @model_validator(mode="after")
    def _conserved(self) -> Self:
        def side(pairs: tuple[tuple[str, int], ...]) -> tuple[Counter[str], int]:
            atoms: Counter[str] = Counter()
            charge = 0
            for species_id, coeff in pairs:
                if species_id not in self.smiles:
                    raise ValueError(f"species {species_id!r} has no SMILES")
                mol = Chem.MolFromSmiles(self.smiles[species_id])
                if mol is None:
                    raise ValueError(f"SMILES of {species_id!r} does not parse")
                mol = Chem.AddHs(mol)
                for atom in mol.GetAtoms():
                    atoms[atom.GetSymbol()] += coeff
                charge += coeff * Chem.GetFormalCharge(mol)
            return atoms, charge

        left, q_left = side(self.reactants)
        right, q_right = side(self.products)
        if left != right:
            raise ValueError(f"atoms not conserved: reactants {dict(left)}, products {dict(right)}")
        if q_left != q_right:
            raise ValueError(f"charge not conserved: reactants {q_left}, products {q_right}")
        return self

    @property
    def delta_n(self) -> int:
        """Moles of products minus moles of reactants."""
        return sum(c for _, c in self.products) - sum(c for _, c in self.reactants)


class ReactionEnergies(BaseModel):
    """Reaction energies in kcal/mol.

    ``dE`` and ``dH`` use each species' Boltzmann-weighted electronic energy and enthalpy;
    ``dG_1M`` uses the ensemble free energies (at the config's standard state) and ``dG_1atm``
    removes the standard-state correction: ``dG_1M - dG_1atm = delta_n RT ln(c RT / p)``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dE_kcal_mol: float
    dH_kcal_mol: float
    dG_1atm_kcal_mol: float
    dG_1M_kcal_mol: float
    delta_n: int


def standard_state_shift_kcal_mol(config: ThermoConfig) -> float:
    """Return RT ln(c RT / p) per mole of gas, in kcal/mol (1.8943 at 298.15 K, 1 M, 1 atm)."""
    t = config.temperature_k
    c = config.standard_state_mol_l * 1000.0  # mol/m^3
    p = config.pressure_atm * ATM_PA
    return R_GAS * t * math.log(c * R_GAS * t / p) * J_PER_MOL_TO_HARTREE * HARTREE_KCAL_MOL


def _weighted(ensemble: ConformerEnsemble, attr: str) -> float:
    """Return the Boltzmann-weighted mean of a per-record quantity (Eh)."""
    values = []
    for record, w in zip(ensemble.records, ensemble.boltzmann_weights, strict=True):
        e = record.thermo.electronic_energy_hartree
        value = e if attr == "E" else e + record.thermo.thermal_correction_enthalpy_hartree
        values.append(w * value)
    return math.fsum(values)


def reaction_free_energy(
    spec: ReactionSpec, ensembles: Mapping[str, ConformerEnsemble], config: ThermoConfig
) -> ReactionEnergies:
    """Return dE, dH, dG(1 atm) and dG(1 M) of ``spec`` from the species ensembles.

    Raises:
        KeyError: If an ensemble is missing.
        ValueError: If an ensemble's temperature differs from ``config``'s.
    """
    ids = [s for s, _ in spec.reactants] + [s for s, _ in spec.products]
    for species_id in ids:
        if ensembles[species_id].temperature_k != config.temperature_k:
            raise ValueError(f"ensemble {species_id!r} is not at {config.temperature_k} K")

    def total(fn: str) -> float:
        def value(species_id: str) -> float:
            ens = ensembles[species_id]
            return ens.ensemble_gibbs_hartree if fn == "G" else _weighted(ens, fn)

        prod = math.fsum(c * value(s) for s, c in spec.products)
        reac = math.fsum(c * value(s) for s, c in spec.reactants)
        return (prod - reac) * HARTREE_KCAL_MOL

    dg_1m = total("G")
    return ReactionEnergies(
        dE_kcal_mol=total("E"),
        dH_kcal_mol=total("H"),
        dG_1M_kcal_mol=dg_1m,
        dG_1atm_kcal_mol=dg_1m - spec.delta_n * standard_state_shift_kcal_mol(config),
        delta_n=spec.delta_n,
    )
