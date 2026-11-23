"""Human Fixture 1: n-butane conformers on both recipes (v0.3.0 slice 07; TJ R2 "A", Q5 "A")."""

from collections.abc import Callable
from pathlib import Path

import pytest
from acceptance import (
    accuracy_block,
    failures_by_species,
    species_counts,
    stage_metrics,
    write_fragment,
)
from candidates import candidate, environment, species_payload
from checks import assert_checks_pass, checks, write
from derived import (
    assert_no_duplicate_records,
    butane_class,
    failure_report,
    failure_rows,
    hf1_derived,
)
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import hf1

from eta_rxncat.orchestrator import Recipe, build_engine, run_species
from eta_rxncat.store import ArtifactStore

pytestmark = [pytest.mark.e2e, pytest.mark.slow]


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_hf1_butane(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    candidate_dir: Path,
    commit_sha: str,
) -> None:
    """One anti (sigma 2, g 1) and one gauche (sigma 2, g 2) record; candidate written."""
    recipe = recipes(recipe_name)
    fixture = hf1()
    spec = fixture.spec("n_butane")
    store_path = tmp_path / "store.sqlite"
    with ArtifactStore(store_path) as store:
        result = run_species(spec, recipe, store)
    failures = failure_report(spec.species_id, failure_rows(store_path, result.keys))
    records = result.ensemble.records
    assert_no_duplicate_records(result.ensemble, spec.smiles, spec.conformer_options)
    duplicates = sum(reason == "duplicate_after_push" for _, reason in result.dropped)
    classes = [butane_class(r) for r in records]
    assert sorted(classes) == ["anti", "gauche"], classes
    by_class = dict(zip(classes, records, strict=True))
    assert by_class["anti"].thermo.rotational_symmetry_number == 2
    assert by_class["anti"].degeneracy == 1
    assert by_class["gauche"].thermo.rotational_symmetry_number == 2
    assert by_class["gauche"].degeneracy == 2
    assert not records[result.ensemble.lowest_index].thermo.imaginary_frequencies_cm1

    derived = hf1_derived(result.ensemble)
    observed = {
        "hf1.dE_gauche_anti": derived["dE_gauche_anti_kcal_mol"],
        "hf1.dH_gauche_anti": derived["dH_gauche_anti_kcal_mol"],
        "hf1.dG_gauche_anti": derived["dG_gauche_anti_kcal_mol"],
        "hf1.gauche_population": derived["gauche_population_percent"],
    }
    sigmas = {
        "butane_anti": by_class["anti"].thermo.rotational_symmetry_number,
        "butane_gauche": by_class["gauche"].thermo.rotational_symmetry_number,
    }
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = candidate(
        fixture=fixture.name,
        recipe=recipe_name,
        commit_sha=commit_sha,
        env=environment(identity, DEVICES[recipe_name]),
        thermo_config=recipe.thermo_config,
        species={spec.species_id: species_payload(spec, result, butane_class, failures)},
        derived={k: v for k, v in derived.items() if k != "classes"},
        checks={},
    )
    payload["checks"] = checks(fixture.name, recipe_name, payload, observed, sigmas)
    write(candidate_dir / f"{fixture.name}.{recipe_name}.json", payload)
    print(
        f"\nHF1 {recipe_name}: n_butane n_kept {len(records)} {classes}; "
        f"duplicate_after_push {duplicates}; dropped {list(result.dropped)}; "
        f"failures {failures}; engine calls {result.metrics.engine_calls}; "
        f"checks {payload['checks']['regression']['status']}/"
        f"{payload['checks']['accuracy']['status']}"
    )
    write_fragment(
        fixture.name,
        recipe_name,
        {
            "device": DEVICES[recipe_name],
            "species": species_counts(payload["species"]),
            **stage_metrics([result]),
            "regression": payload["checks"]["regression"],
            "accuracy": accuracy_block(payload["checks"], observed, sigmas, recipe_name),
            "failures": failures_by_species(failures),
            "test_outcome": "passed"
            if payload["checks"]["accuracy"]["status"] != "fail"
            else "failed",
        },
    )
    assert_checks_pass(payload["checks"])
