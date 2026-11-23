"""ETKDGv3 conformer generation, RMSD pruning, and Boltzmann ensemble thermodynamics."""

from __future__ import annotations

import math
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, rdDetermineBonds, rdMolAlign

from eta_rxncat.core.models import ConformerEnsemble, MolecularState

HARTREE_TO_J_MOL = 2625499.6394799
R_J_MOL_K = 8.314462618


def generate_conformers(
    state: MolecularState,
    num_confs: int = 25,
    rmsd_threshold_angstrom: float = 0.35,
    seed: int = 42,
) -> list[MolecularState]:
    """Generate deduplicated 3D conformers using RDKit ETKDGv3."""
    xyz_lines = [str(len(state.symbols)), state.name]
    for sym, (x, y, z) in zip(state.symbols, state.coordinates, strict=True):
        xyz_lines.append(f"{sym} {x:.8f} {y:.8f} {z:.8f}")
    raw = Chem.MolFromXYZBlock("\n".join(xyz_lines))
    if raw is None:
        return [state]
    mol = Chem.Mol(raw)
    try:
        rdDetermineBonds.DetermineConnectivity(mol)
    except Exception:
        return [state]

    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = rmsd_threshold_angstrom
    conf_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, params=params))
    if not conf_ids:
        return [state]

    # Align and prune close conformers
    kept_ids: list[int] = [conf_ids[0]]
    for cid in conf_ids[1:]:
        is_dup = False
        for k_id in kept_ids:
            rmsd = rdMolAlign.GetBestRMS(mol, mol, prbId=cid, refId=k_id)
            if rmsd < rmsd_threshold_angstrom:
                is_dup = True
                break
        if not is_dup:
            kept_ids.append(cid)

    results: list[MolecularState] = []
    for idx, cid in enumerate(kept_ids):
        conf = mol.GetConformer(cid)
        coords = [
            [float(conf.GetAtomPosition(a).x), float(conf.GetAtomPosition(a).y), float(conf.GetAtomPosition(a).z)]
            for a in range(mol.GetNumAtoms())
        ]
        results.append(
            state.model_copy(
                update={
                    "name": f"{state.name}_conf_{idx:03d}",
                    "coordinates": coords,
                }
            )
        )
    return results


def build_boltzmann_ensemble(
    species_name: str,
    conformers: list[MolecularState],
    gibbs_energies_hartree: list[float],
    temperature_k: float = 298.15,
) -> ConformerEnsemble:
    """Compute Boltzmann weights and Boltzmann-averaged Gibbs free energy G_BA."""
    g_arr = np.asarray(gibbs_energies_hartree, dtype=np.float64)
    g_min = float(np.min(g_arr))
    low_idx = int(np.argmin(g_arr))

    rel_j_mol = (g_arr - g_min) * HARTREE_TO_J_MOL
    rt = R_J_MOL_K * temperature_k
    boltz_factors = np.exp(-np.minimum(rel_j_mol / rt, 500.0))
    weights = boltz_factors / np.sum(boltz_factors)

    # Free energy of conformational ensemble: G_ens = G_min - RT ln(sum exp(-(G_i - G_min)/RT))
    g_ens_ha = g_min - (rt * math.log(float(np.sum(boltz_factors)))) / HARTREE_TO_J_MOL

    return ConformerEnsemble(
        species_name=species_name,
        conformers=conformers,
        gibbs_energies_hartree=g_arr.tolist(),
        boltzmann_weights=weights.tolist(),
        lowest_conformer_index=low_idx,
        boltzmann_averaged_gibbs_hartree=float(g_ens_ha),
    )
