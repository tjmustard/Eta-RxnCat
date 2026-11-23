"""Human Fixture 2: butadiene + ethylene -> cyclohexene at 1 M, with incremental solvation.

v0.3.0 slice 07; TJ Q4 "C" (the incremental-solvation test runs on the species runner), R13, R20,
R27, R47, R51. Every reaction free energy goes through ``checked_reaction_free_energy``.
"""

import math
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from candidates import candidate, environment, species_payload
from checks import assert_checks_pass, checks, write
from derived import (
    assert_no_duplicate_records,
    characterize,
    checked_reaction_free_energy,
    diene_class,
    failure_report,
    failure_rows,
    hf2_derived,
    hf2_lowest_records,
    near_degenerate_distinct,
    solvated_ensemble,
)
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import hf2

from eta_rxncat.core import Solvation, StageConfig
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import Recipe, SinglePoint, SpeciesResult, build_engine, run_species
from eta_rxncat.store import ArtifactStore

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

ALPB = StageConfig(
    kind="single_point",
    engine="xtb_subprocess",
    method="gfn2",
    solvation=Solvation(model="alpb", solvent="toluene"),
    options={"alpb_state": "gsolv"},
)
PCM = StageConfig(
    kind="single_point",
    engine="pyscf_gpu_cpu",
    method="pbe0",
    basis="def2-svp",
    solvation=Solvation(model="pcm", solvent="toluene"),
    options={"pcm_method": "C-PCM"},
)
UPSTREAM = ("conformer_search", "geometry_opt", "frequency")


def rows(path: Path) -> dict[str, tuple[str, str]]:
    """{key: (stage_kind, created_at_utc)} straight from the store file."""
    with sqlite3.connect(path) as conn:
        return {
            k: (kind, created)
            for k, kind, created in conn.execute(
                "SELECT key, stage_kind, created_at_utc FROM stage_artifacts"
            )
        }


def upstream_calls(result: SpeciesResult) -> int:
    """Engine calls spent on conformer search, optimization and frequencies."""
    return sum(result.metrics.stages[k].engine_calls for k in UPSTREAM)


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_hf2_diels_alder(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    candidate_dir: Path,
    commit_sha: str,
) -> None:
    """Gas run, per-conformer and ensemble dG_r, incremental ALPB/PCM reruns, candidate written."""
    recipe = recipes(recipe_name)
    fixture = hf2()
    assert fixture.reaction is not None
    store_path = tmp_path / "store.sqlite"
    gas: dict[str, SpeciesResult] = {}
    with ArtifactStore(store_path) as store:
        for spec in fixture.species:
            gas[spec.species_id] = run_species(spec, recipe, store)
    before = rows(store_path)
    ensembles = {k: v.ensemble for k, v in gas.items()}
    for spec in fixture.species:
        assert_no_duplicate_records(ensembles[spec.species_id], spec.smiles, spec.conformer_options)
    duplicates = {
        k: sum(reason == "duplicate_after_push" for _, reason in v.dropped) for k, v in gas.items()
    }
    cyclo = fixture.spec("cyclohexene")
    character = characterize(ensembles["cyclohexene"], cyclo.smiles, cyclo.conformer_options)
    print(f"\nHF2 {recipe_name} cyclohexene records (R53 characterization):")
    for row in character:
        print(f"  {row}")
    stop = near_degenerate_distinct(character, cyclo.conformer_options.rmsd_dedup_angstrom)
    assert not stop, f"STOP AND REPORT (R53): |dG| <= 0.01 kcal/mol above the RMSD threshold {stop}"

    # classes, sigma and degeneracy
    classes = [diene_class(r) for r in ensembles["butadiene"].records]
    assert "s-trans" in classes and "s-cis-side" in classes, classes
    lowest = hf2_lowest_records(ensembles)
    assert lowest["butadiene"].thermo.rotational_symmetry_number == 2
    assert lowest["ethylene"].thermo.rotational_symmetry_number == 4
    assert lowest["cyclohexene"].thermo.rotational_symmetry_number == 2
    assert lowest["cyclohexene"].degeneracy == 2

    config = recipe.thermo_config
    derived = hf2_derived(fixture.reaction, ensembles, config)
    gas_energies = derived["ensemble"]
    shift = gas_energies["dG_1M_kcal_mol"] - gas_energies["dG_1atm_kcal_mol"]
    assert shift == pytest.approx(-1.8943, abs=1e-4)

    # incremental: xtb ALPB(toluene) per kept record of every species (R13, R27)
    incremental: dict[str, object] = {}
    n_kept = {k: len(v.records) for k, v in ensembles.items()}
    if recipe_name == "xtb":
        solv: dict[str, SpeciesResult] = {}
        with ArtifactStore(store_path) as store:
            for spec in fixture.species:
                solv[spec.species_id] = run_species(
                    spec, recipe, store, single_points=[SinglePoint(ALPB)]
                )
        alpb_calls = sum(r.metrics.stages["single_point"].engine_calls for r in solv.values())
        assert sum(upstream_calls(r) for r in solv.values()) == 0
        assert alpb_calls == sum(n_kept.values())
        solvated = {
            k: solvated_ensemble(ensembles[k], solv[k].single_point_energies[0]) for k in ensembles
        }
        dg_solv = {
            k: (solvated[k].ensemble_gibbs_hartree - ensembles[k].ensemble_gibbs_hartree)
            * HARTREE_KCAL_MOL
            for k in ensembles
        }
        assert all(math.isfinite(v) for v in dg_solv.values())
        solv_energies = checked_reaction_free_energy(fixture.reaction, solvated, config)
        nu = {s: -c for s, c in fixture.reaction.reactants} | {
            s: c for s, c in fixture.reaction.products
        }
        additive = gas_energies["dG_1M_kcal_mol"] + sum(nu[k] * dg_solv[k] for k in nu)
        assert solv_energies.dG_1M_kcal_mol == pytest.approx(additive, abs=1e-9)
        assert abs(solv_energies.dG_1M_kcal_mol - gas_energies["dG_1M_kcal_mol"]) > 1e-6
        incremental["alpb_toluene"] = {
            "expected_calls": sum(n_kept.values()),
            "observed_calls": alpb_calls,
            "upstream_calls": 0,
            "dG_solv_kcal_mol": dg_solv,
            "dG_r_1M_solvated_kcal_mol": solv_energies.dG_1M_kcal_mol,
        }
    else:
        incremental["alpb_toluene"] = "n/a (UMA has no implicit solvation; dG_solv n/a)"

    # both recipes: one PySCF PCM(toluene, C-PCM) single point on ethylene's lowest record, CPU
    with ArtifactStore(store_path) as store:
        pcm = run_species(
            fixture.spec("ethylene"),
            recipe,
            store,
            single_points=[SinglePoint(PCM, only_lowest=True, engine_runtime={"device": "cpu"})],
        )
    assert pcm.metrics.stages["single_point"].engine_calls == 1
    assert upstream_calls(pcm) == 0
    incremental["pcm_toluene_ethylene_lowest"] = {
        "expected_calls": 1,
        "observed_calls": pcm.metrics.stages["single_point"].engine_calls,
        "upstream_calls": upstream_calls(pcm),
        "mechanism_only": True,
    }

    after = rows(store_path)
    for key, value in before.items():
        assert after[key] == value, key

    failures = []
    species = {}
    for spec in fixture.species:
        found = failure_report(spec.species_id, failure_rows(store_path, gas[spec.species_id].keys))
        failures.extend(found)
        classify = diene_class if spec.species_id == "butadiene" else None
        species[spec.species_id] = species_payload(spec, gas[spec.species_id], classify, found)
    observed = {
        "hf2.dE_r": derived["dE_r_lowest_records_kcal_mol"],
        "hf2.dH_r": derived["dH_r_lowest_records_kcal_mol"],
        "hf2.dG_r": derived["dG_r_lowest_records_kcal_mol"],
    }
    sigmas = {
        "butadiene_strans": lowest["butadiene"].thermo.rotational_symmetry_number,
        "ethylene": lowest["ethylene"].thermo.rotational_symmetry_number,
        "cyclohexene": lowest["cyclohexene"].thermo.rotational_symmetry_number,
    }
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = candidate(
        fixture=fixture.name,
        recipe=recipe_name,
        commit_sha=commit_sha,
        env=environment(identity, DEVICES[recipe_name]),
        thermo_config=config,
        species=species,
        derived={**derived, "incremental_solvation": incremental},
        checks={},
    )
    payload["checks"] = checks(fixture.name, recipe_name, payload, observed, sigmas)
    write(candidate_dir / f"{fixture.name}.{recipe_name}.json", payload)
    print(
        f"\nHF2 {recipe_name}: n_kept {n_kept}; duplicate_after_push {duplicates}; "
        f"dropped { {k: list(v.dropped) for k, v in gas.items()} }; "
        f"butadiene classes {classes}; failures {failures}; "
        f"incremental {incremental}; checks {payload['checks']['regression']['status']}/"
        f"{payload['checks']['accuracy']['status']}"
    )
    assert_checks_pass(payload["checks"])
