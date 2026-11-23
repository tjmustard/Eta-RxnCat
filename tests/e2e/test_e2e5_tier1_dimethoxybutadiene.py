"""TJ Tier 1: 1,3-dimethoxybutadiene classes, ordering and the planar s-cis point (slice 08).

TJ Q-E2 "A", Q-E5 "C"; R21, R25 (H12: the ordering gate holds on both recipes), R42 (F32 "A the
planar geometry": a constrained point, reported only; its gate is |phi| <= 0.1 deg).
"""

import math
from collections.abc import Callable
from pathlib import Path

import pytest
from acceptance import (
    accuracy_block,
    failures_by_species,
    smiles_confirmation,
    species_counts,
    stage_metrics,
    write_fragment,
)
from candidates import candidate, environment, species_payload
from checks import assert_checks_pass, checks, write
from derived import (
    assert_no_duplicate_records,
    diene_class,
    failure_report,
    failure_rows,
    lowest,
    reperceived_smiles,
)
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import t1
from rdkit import Chem

from eta_rxncat.conformers import dihedral_deg
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.optimize import DihedralConstraint
from eta_rxncat.orchestrator import Recipe, build_engine, run_constrained_point, run_species
from eta_rxncat.store import ArtifactStore

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_e2e5_tier1_dimethoxybutadiene(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    candidate_dir: Path,
    commit_sha: str,
) -> None:
    """Both diene classes kept, s-trans lowest, planar point within 0.1 deg; candidate written."""
    recipe = recipes(recipe_name)
    fixture = t1()
    spec = fixture.species[0]
    assert fixture.literature is not None and fixture.planar_point is not None
    store_path = tmp_path / "store.sqlite"
    with ArtifactStore(store_path) as store:
        result = run_species(spec, recipe, store)
    ens = result.ensemble
    assert_no_duplicate_records(ens, spec.smiles, spec.conformer_options)
    duplicates = sum(reason == "duplicate_after_push" for _, reason in result.dropped)
    records = ens.records
    classes = [diene_class(r) for r in records]

    # gated (both recipes)
    assert len(records) >= 2, classes
    assert not records[ens.lowest_index].thermo.imaginary_frequencies_cm1
    assert abs(math.fsum(ens.boltzmann_weights) - 1.0) <= 1e-12
    assert ens.ensemble_gibbs_hartree <= records[ens.lowest_index].thermo.gibbs_free_energy_hartree
    strans = [r for r, c in zip(records, classes, strict=True) if c == "s-trans"]
    scis = [r for r, c in zip(records, classes, strict=True) if c == "s-cis-side"]
    assert strans and scis, f"STOP AND REPORT: a diene class is missing {classes}"
    low_t, low_c = lowest(strans), lowest(scis)
    ordering = low_t.thermo.gibbs_free_energy_hartree < low_c.thermo.gibbs_free_energy_hartree
    dg_ct = (low_c.thermo.gibbs_free_energy_hartree - low_t.thermo.gibbs_free_energy_hartree) * (
        HARTREE_KCAL_MOL
    )
    assert ordering, f"STOP AND REPORT (H12): lowest s-cis-side G is below s-trans by {-dg_ct}"

    # planar s-cis point (R42), from the lowest-G kept s-cis-side record
    atoms = tuple(fixture.planar_point["dihedral_atoms"])
    constraint = DihedralConstraint(atoms=atoms, value_deg=fixture.planar_point["value_deg"])
    with ArtifactStore(store_path) as store:
        planar = run_constrained_point(
            spec, recipe, store, low_c.state, dihedral_constraints=[constraint]
        )
    phi = dihedral_deg(planar.state, *atoms)
    assert abs(phi - constraint.value_deg) <= 0.1, phi
    de_planar = (planar.energy_hartree - low_t.thermo.electronic_energy_hartree) * HARTREE_KCAL_MOL

    smiles = [reperceived_smiles(r) for r in records]
    canonical_input = Chem.MolToSmiles(Chem.MolFromSmiles(spec.smiles))
    for i, s in enumerate(smiles):
        assert Chem.MolToSmiles(Chem.MolFromSmiles(s)) == canonical_input, (i, s)
    weights = dict.fromkeys(("s-trans", "s-cis-side"), 0.0)
    for w, c in zip(ens.boltzmann_weights, classes, strict=True):
        weights[c] += w
    derived = {
        # R55: order-free; per-record classes and SMILES live on the record entries
        "class_counts": {c: classes.count(c) for c in ("s-trans", "s-cis-side")},
        "dE_scis_strans_kcal_mol": (
            low_c.thermo.electronic_energy_hartree - low_t.thermo.electronic_energy_hartree
        )
        * HARTREE_KCAL_MOL,
        "dG_scis_strans_kcal_mol": dg_ct,
        "population_strans_percent": 100.0 * weights["s-trans"],
        "population_scis_side_percent": 100.0 * weights["s-cis-side"],
        "reperceived_smiles_unique": sorted(set(smiles)),
        "dE_planar_scis_strans_kcal_mol": de_planar,
        "planar_point_energy_hartree": planar.energy_hartree,
        "literature": {
            "quantity": fixture.literature["quantity"],
            "value_kcal_mol": fixture.literature["value_kcal_mol"],
            "source": fixture.literature["source"],
            "label": fixture.literature["label"],
            "delta_kcal_mol": de_planar - fixture.literature["value_kcal_mol"],
        },
    }
    failures = failure_report(spec.species_id, failure_rows(store_path, result.keys))
    species_entry = species_payload(spec, result, diene_class, failures)
    for entry, s in zip(species_entry["records"], smiles, strict=True):
        entry["reperceived_smiles"] = s
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = candidate(
        fixture=fixture.name,
        recipe=recipe_name,
        commit_sha=commit_sha,
        env=environment(identity, DEVICES[recipe_name]),
        thermo_config=recipe.thermo_config,
        species={spec.species_id: species_entry},
        derived=derived,
        checks={},
    )
    payload["planar_point"] = {
        "label": fixture.literature["label"],
        "dihedral_atoms": list(atoms),
        "phi_deg": phi,
        "cache_hit": planar.cache_hit,
        "symbols": list(planar.state.symbols),
        "xyz_angstrom": [list(row) for row in planar.state.coordinates],
        "recovery_steps": list(planar.optimization.recovery_steps),
    }
    payload["checks"] = checks(fixture.name, recipe_name, payload, None, {})
    write(candidate_dir / f"{fixture.name}.{recipe_name}.json", payload)
    print(
        f"\nT1 {recipe_name}: n_kept {len(records)} class_counts {derived['class_counts']}; "
        f"reperceived_smiles_unique {derived['reperceived_smiles_unique']}; duplicate_after_push "
        f"{duplicates}; dropped {list(result.dropped)}; failures {failures}; "
        f"H12 ordering s-trans<s-cis-side {ordering} "
        f"(dG s-cis-side - s-trans {dg_ct:.3f} kcal/mol, "
        f"dE {derived['dE_scis_strans_kcal_mol']:.3f}); planar phi {phi:.4f} deg, "
        f"dE_planar_scis_strans {de_planar:.3f} kcal/mol vs literature "
        f"{fixture.literature['value_kcal_mol']}; populations s-trans "
        f"{derived['population_strans_percent']:.1f}% s-cis-side "
        f"{derived['population_scis_side_percent']:.1f}%; checks "
        f"{payload['checks']['regression']['status']}/{payload['checks']['accuracy']['status']}"
    )
    write_fragment(
        fixture.name,
        recipe_name,
        {
            "device": DEVICES[recipe_name],
            "species": species_counts(payload["species"]),
            **stage_metrics([result, planar]),
            "regression": payload["checks"]["regression"],
            "accuracy": accuracy_block(payload["checks"], None, {}, recipe_name),
            "smiles_confirmation": smiles_confirmation(),
            "class_counts": derived["class_counts"],
            "ordering_strans_below_scis": ordering,
            "planar_point": {"phi_deg": phi, "dE_planar_scis_strans_kcal_mol": de_planar},
            "failures": failures_by_species(failures),
            "test_outcome": "passed",
        },
    )
    assert_checks_pass(payload["checks"])
