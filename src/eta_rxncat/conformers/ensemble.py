"""Boltzmann ensemble assembly from conformer records (with degeneracies)."""

from collections.abc import Sequence

from eta_rxncat.conformers.errors import EnsembleEmptyError
from eta_rxncat.core import ConformerEnsemble, ConformerRecord
from eta_rxncat.thermo import boltzmann


def build_ensemble(
    species_id: str, smiles: str, records: Sequence[ConformerRecord], temperature_k: float
) -> ConformerEnsemble:
    """Return the ensemble: weights proportional to g exp(-G/RT), log-sum-exp ``G_ens``.

    Raises:
        EnsembleEmptyError: If ``records`` is empty.
    """
    if not records:
        raise EnsembleEmptyError(())
    gibbs = [r.thermo.gibbs_free_energy_hartree for r in records]
    weights, g_ens = boltzmann(gibbs, [r.degeneracy for r in records], temperature_k)
    lowest = min(range(len(gibbs)), key=lambda i: (gibbs[i], i))
    return ConformerEnsemble(
        species_id=species_id,
        smiles=smiles,
        records=list(records),
        boltzmann_weights=weights,
        lowest_index=lowest,
        ensemble_gibbs_hartree=g_ens,
        temperature_k=temperature_k,
    )
