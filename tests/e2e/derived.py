"""Fixture-derived quantities, the standard-state check and the accuracy helper (R2, R6, R47-R51).

Every quantity compared with TJ's reference is per conformer (R47): HF1 lowest gauche - lowest anti
record; HF2 lowest-G records of cyclohexene, s-trans butadiene and ethylene. Ensemble quantities
are reported beside them, never compared.
"""

import json
import math
import sqlite3
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from eta_rxncat.conformers import dihedral_deg
from eta_rxncat.core import ConformerEnsemble, ConformerRecord, ThermoConfig
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import ReactionEnergies, ReactionSpec, reaction_free_energy

R_KCAL_MOL_K = 6.02214076e23 * 1.380649e-23 / 4184.0


# torsion classes -----------------------------------------------------------------------------


def butane_class(record: ConformerRecord) -> str:
    """HF1: ``anti`` if |phi(C1-C2-C3-C4)| > 120 deg, else ``gauche``."""
    return "anti" if abs(dihedral_deg(record.state, 0, 1, 2, 3)) > 120.0 else "gauche"


def diene_class(record: ConformerRecord) -> str:
    """Butadiene/T1: ``s-trans`` if |phi(0-1-2-3)| > 90 deg, else ``s-cis-side`` (not "planar")."""
    return "s-trans" if abs(dihedral_deg(record.state, 0, 1, 2, 3)) > 90.0 else "s-cis-side"


def lowest(records: Sequence[ConformerRecord]) -> ConformerRecord:
    """The lowest-G record (ties to the lower index)."""
    return min(records, key=lambda r: r.thermo.gibbs_free_energy_hartree)


def _h(record: ConformerRecord) -> float:
    return (
        record.thermo.electronic_energy_hartree + record.thermo.thermal_correction_enthalpy_hartree
    )


def _x(record: ConformerRecord, x: str) -> float:
    if x == "E":
        return record.thermo.electronic_energy_hartree
    if x == "H":
        return _h(record)
    return record.thermo.gibbs_free_energy_hartree


# HF1 -----------------------------------------------------------------------------------------


def hf1_derived(ensemble: ConformerEnsemble) -> dict[str, Any]:
    """Return HF1's per-conformer gauche - anti quantities, population and class dG (kcal/mol)."""
    classes = [butane_class(r) for r in ensemble.records]
    anti = [r for r, c in zip(ensemble.records, classes, strict=True) if c == "anti"]
    gauche = [r for r, c in zip(ensemble.records, classes, strict=True) if c == "gauche"]
    if not anti or not gauche:
        raise ValueError(f"HF1 needs anti and gauche records, got {classes}")
    a, g = lowest(anti), lowest(gauche)
    p_g = math.fsum(
        w for w, c in zip(ensemble.boltzmann_weights, classes, strict=True) if c == "gauche"
    )
    p_a = 1.0 - p_g
    rt = R_KCAL_MOL_K * ensemble.temperature_k
    return {
        "dE_gauche_anti_kcal_mol": (_x(g, "E") - _x(a, "E")) * HARTREE_KCAL_MOL,
        "dH_gauche_anti_kcal_mol": (_x(g, "H") - _x(a, "H")) * HARTREE_KCAL_MOL,
        "dG_gauche_anti_kcal_mol": (_x(g, "G") - _x(a, "G")) * HARTREE_KCAL_MOL,
        "gauche_population_percent": 100.0 * p_g,
        "class_dG_gauche_anti_kcal_mol": -rt * math.log(p_g / p_a),
        "classes": classes,
    }


# HF2 -----------------------------------------------------------------------------------------


def checked_reaction_free_energy(
    spec: ReactionSpec, ensembles: Mapping[str, ConformerEnsemble], config: ThermoConfig
) -> ReactionEnergies:
    """``reaction_free_energy`` after checking every record's thermo config equals ``config`` (R51).

    Raises:
        ValueError: A record of some species has another ThermoConfig (temperature, pressure,
            standard state or quasi-RRHO settings); the message names the species.
    """
    ids = [s for s, _ in spec.reactants] + [s for s, _ in spec.products]
    for species_id in ids:
        for i, record in enumerate(ensembles[species_id].records):
            if record.thermo.config != config:
                raise ValueError(
                    f"species {species_id!r} record {i}: thermo config {record.thermo.config} "
                    f"!= the reaction's {config}"
                )
    return reaction_free_energy(spec, ensembles, config)


def hf2_lowest_records(ensembles: Mapping[str, ConformerEnsemble]) -> dict[str, ConformerRecord]:
    """The per-conformer HF2 records: lowest-G cyclohexene, s-trans butadiene and ethylene."""
    strans = [r for r in ensembles["butadiene"].records if diene_class(r) == "s-trans"]
    if not strans:
        raise ValueError("butadiene has no s-trans record")
    return {
        "cyclohexene": lowest(ensembles["cyclohexene"].records),
        "butadiene": lowest(strans),
        "ethylene": lowest(ensembles["ethylene"].records),
    }


def hf2_derived(
    spec: ReactionSpec, ensembles: Mapping[str, ConformerEnsemble], config: ThermoConfig
) -> dict[str, Any]:
    """Return ensemble dX_r, per-conformer dX_r_lowest_records (G at 1 M) and their G difference."""
    energies = checked_reaction_free_energy(spec, ensembles, config)
    recs = hf2_lowest_records(ensembles)
    per = {
        f"d{x}_r_lowest_records_kcal_mol": (
            _x(recs["cyclohexene"], x) - _x(recs["butadiene"], x) - _x(recs["ethylene"], x)
        )
        * HARTREE_KCAL_MOL
        for x in ("E", "H", "G")
    }
    return {
        "ensemble": energies.model_dump(),
        **per,
        "dG_r_ensemble_minus_lowest_kcal_mol": energies.dG_1M_kcal_mol
        - per["dG_r_lowest_records_kcal_mol"],
        "lowest_records_sigma": {k: r.thermo.rotational_symmetry_number for k, r in recs.items()},
    }


def solvated_ensemble(
    ensemble: ConformerEnsemble, sp_energies: Mapping[int, float]
) -> ConformerEnsemble:
    """Rebase each record on its solvated single-point energy (R27).

    G_solv,i = G_i + (E_sp,i - E_i).

    The Boltzmann sum is redone over the solvated G with the same degeneracies.
    """
    from eta_rxncat.conformers import build_ensemble

    records = []
    for i, record in enumerate(ensemble.records):
        t = record.thermo
        data = t.model_dump()
        data["electronic_energy_hartree"] = sp_energies[i]
        data["energy_source"] = "single_point"
        data["gibbs_free_energy_hartree"] = sp_energies[i] + t.thermal_correction_gibbs_hartree
        records.append(record.model_copy(update={"thermo": type(t).model_validate(data)}))
    return build_ensemble(ensemble.species_id, ensemble.smiles, records, ensemble.temperature_k)


# R50: failures are completed rows carrying failed_reason --------------------------------------


def failure_rows(
    store_path: Path, keys_by_kind: Mapping[str, Sequence[str]]
) -> Counter[tuple[str, str]]:
    """Count ``(stage, failed_reason)`` over the rows a run used (checked before any use, R50)."""
    counts: Counter[tuple[str, str]] = Counter()
    with sqlite3.connect(store_path) as conn:
        for kind, keys in keys_by_kind.items():
            for key in set(keys):
                row = conn.execute(
                    "SELECT payload_json FROM stage_artifacts "
                    "WHERE key = ? AND status = 'completed'",
                    (key,),
                ).fetchone()
                if row is None:
                    continue
                payload = json.loads(row[0])
                if "failed_reason" in payload:
                    counts[(kind, str(payload["failed_reason"]))] += 1
    return counts


def failure_report(species_id: str, counts: Counter[tuple[str, str]]) -> list[dict[str, Any]]:
    """Failure rows as report entries: species, stage, reason, count (sorted)."""
    return [
        {"species": species_id, "stage": stage, "reason": reason, "count": n}
        for (stage, reason), n in sorted(counts.items())
    ]


# accuracy (R47, R48) -------------------------------------------------------------------------

GATE_BOUNDS_KCAL_MOL = {"hf1.dG_gauche_anti": 0.5, "hf2.dG_r": 2.0}
"""Q5 "A" bounds for the UMA recipe; xtb is never gated."""


def accuracy(
    observed: Mapping[str, float],
    sigmas: Mapping[str, int],
    reference: Mapping[str, Any] | None,
    *,
    recipe: str,
) -> dict[str, Any]:
    """Compare per-conformer quantities with every reference entry of the same quantity.

    Args:
        observed: quantity -> our value (kcal/mol or percent; hf2.dG_r at 1 M).
        sigmas: reference species id -> sigma of the record we compared.
        reference: Validated reference values, or ``None`` (then ``pending_reference``).
        recipe: ``uma`` (gated) or ``xtb`` (never gated).

    Returns:
        ``status`` (``pass``|``fail``|``reported``|``pending_reference``) and per-entry deltas.
        A sigma mismatch fails UMA and is flagged ``sigma_mismatch`` beside xtb's delta.
    """
    from reference_values import is_reported_only, value_at_1m

    if reference is None:
        return {"status": "pending_reference", "deltas": []}
    mismatched = sorted(
        name
        for name, ref in reference["reference_species"].items()
        if name in sigmas and sigmas[name] != ref["sigma"]
    )
    deltas = []
    gated_fail = False
    gated_any = False
    for entry in reference["entries"]:
        q = entry["quantity"]
        if q not in observed:
            continue
        delta = observed[q] - value_at_1m(entry)
        gated = recipe == "uma" and not is_reported_only(entry) and q in GATE_BOUNDS_KCAL_MOL
        within = abs(delta) <= GATE_BOUNDS_KCAL_MOL.get(q, math.inf)
        if gated:
            gated_any = True
            gated_fail |= (not within) or bool(mismatched)
        deltas.append(
            {
                "quantity": q,
                "level": entry["level"],
                "observed": observed[q],
                "reference_1m": value_at_1m(entry),
                "delta": delta,
                "gated": gated,
                **({"within_bound": within, "bound": GATE_BOUNDS_KCAL_MOL[q]} if gated else {}),
            }
        )
    status = "reported" if not gated_any else ("fail" if gated_fail else "pass")
    result: dict[str, Any] = {"status": status, "deltas": deltas}
    if mismatched:
        result["sigma_mismatch"] = mismatched
    return result


# R53: no duplicate records; per-record characterization ---------------------------------------


def _pairwise(
    ensemble: ConformerEnsemble, smiles: str, options: Any, mirror: bool
) -> list[list[float]]:
    """Least proper-rotation RMSD (with H, over automorphisms) between every pair of records."""
    import numpy as np

    from eta_rxncat.conformers._rmsd import atom_subset, graph_permutations, min_rmsds

    perms = graph_permutations(smiles, options.max_automorphisms)
    atoms = atom_subset(smiles, True, options.max_automorphisms)
    xyz = [np.asarray(r.state.coordinates, dtype=np.float64) for r in ensemble.records]
    flip = np.array([-1.0, 1.0, 1.0]) if mirror else np.ones(3)
    return [[float(min_rmsds(a, [b * flip], perms, atoms)[0]) for b in xyz] for a in xyz]


def assert_no_duplicate_records(ensemble: ConformerEnsemble, smiles: str, options: Any) -> None:
    """No two kept records within ``rmsd_dedup_angstrom`` (proper rotation, with H; R53).

    Raises:
        AssertionError: naming the pair and its RMSD.
    """
    rmsd = _pairwise(ensemble, smiles, options, mirror=False)
    n = len(ensemble.records)
    pairs = [
        (i, j, rmsd[i][j])
        for i in range(n)
        for j in range(i + 1, n)
        if rmsd[i][j] <= options.rmsd_dedup_angstrom
    ]
    assert not pairs, f"{ensemble.species_id}: duplicate records (i, j, rmsd) {pairs}"


RING_TORSIONS = ((5, 0, 1, 2), (0, 1, 2, 3), (1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 0), (4, 5, 0, 1))
"""Cyclohexene ``C1CC=CCC1``: the six ring torsions in SMILES atom order."""


def characterize(ensemble: ConformerEnsemble, smiles: str, options: Any) -> list[dict[str, Any]]:
    """Characterize each kept record (R53).

    Per record: dG and dE to the lowest (kcal/mol), ring torsions, lowest two frequencies,
    recovery steps, and the least RMSD to every other record (proper rotation, and mirror).
    """
    recs = ensemble.records
    g0 = min(r.thermo.gibbs_free_energy_hartree for r in recs)
    e0 = min(r.thermo.electronic_energy_hartree for r in recs)
    proper = _pairwise(ensemble, smiles, options, mirror=False)
    mirror = _pairwise(ensemble, smiles, options, mirror=True)
    rows = []
    for i, r in enumerate(recs):
        rows.append(
            {
                "index": i,
                "source_ids": list(r.source_ids),
                "degeneracy": r.degeneracy,
                "sigma": r.thermo.rotational_symmetry_number,
                "dG_to_lowest_kcal_mol": (r.thermo.gibbs_free_energy_hartree - g0)
                * HARTREE_KCAL_MOL,
                "dE_to_lowest_kcal_mol": (r.thermo.electronic_energy_hartree - e0)
                * HARTREE_KCAL_MOL,
                "ring_torsions_deg": [round(dihedral_deg(r.state, *t), 1) for t in RING_TORSIONS],
                "lowest_two_cm1": [round(f, 1) for f in r.thermo.frequencies_cm1[:2]],
                "recovery_steps": list(r.optimization.recovery_steps),
                "min_rmsd_proper": [round(x, 3) for x in proper[i]],
                "min_rmsd_mirror": [round(x, 3) for x in mirror[i]],
            }
        )
    return rows


def near_degenerate_distinct(rows: list[dict[str, Any]], threshold: float) -> list[tuple[int, int]]:
    """Pairs with |dG| <= 0.01 kcal/mol but proper RMSD above the dedup threshold (stop rule)."""
    out = []
    for a in rows:
        for b in rows:
            close = abs(a["dG_to_lowest_kcal_mol"] - b["dG_to_lowest_kcal_mol"]) <= 0.01
            distinct = a["min_rmsd_proper"][b["index"]] > threshold
            if a["index"] < b["index"] and close and distinct:
                out.append((a["index"], b["index"]))
    return out


def reperceived_smiles(record: ConformerRecord) -> str:
    """Canonical isomeric SMILES re-perceived from the record's geometry (bonds + 3D stereo)."""
    from rdkit import Chem
    from rdkit.Chem import rdDetermineBonds

    rw = Chem.RWMol()
    for symbol in record.state.symbols:
        rw.AddAtom(Chem.Atom(symbol))
    conformer = Chem.Conformer(len(record.state.symbols))
    for i, (x, y, z) in enumerate(record.state.coordinates):
        conformer.SetAtomPosition(i, (x, y, z))
    rw.AddConformer(conformer, assignId=True)
    mol = rw.GetMol()
    rdDetermineBonds.DetermineBonds(mol, charge=record.state.charge)
    Chem.AssignStereochemistryFrom3D(mol)
    return str(Chem.MolToSmiles(Chem.RemoveHs(mol)))
