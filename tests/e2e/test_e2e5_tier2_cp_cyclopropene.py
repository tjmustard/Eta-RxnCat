"""TJ Tier 2: cyclopentadiene + cyclopropene -> endo P1a_n at 1 M, with incremental ALPB(dioxane).

v0.3.0 slice 08; TJ Q-E2 "A", Q-E5 "C" (the -42..-20 kcal/mol window gates UMA only; GFN2 is
reported), R27, R51 (every dG_rxn through checked_reaction_free_energy), R53.
"""

import math
from collections.abc import Callable
from pathlib import Path

import pytest
from candidates import candidate, environment, species_payload
from checks import assert_checks_pass, checks, write
from derived import (
    assert_no_duplicate_records,
    checked_reaction_free_energy,
    failure_report,
    failure_rows,
    lowest,
    solvated_ensemble,
)
from e2e_env import DEVICES, RECIPE_PARAMS
from fixtures import t2

from eta_rxncat.core import Solvation, StageConfig
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import Recipe, SinglePoint, SpeciesResult, build_engine, run_species
from eta_rxncat.store import ArtifactStore

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

ALPB_DIOXANE = StageConfig(
    kind="single_point",
    engine="xtb_subprocess",
    method="gfn2",
    solvation=Solvation(model="alpb", solvent="dioxane"),
    options={"alpb_state": "gsolv"},
)
UPSTREAM = ("conformer_search", "geometry_opt", "frequency")


def all_hit(result: SpeciesResult, kind: str) -> bool:
    """A species is a hit for ``kind`` only if every one of its rows was served (R27)."""
    m = result.metrics.stages[kind]
    return m.rows_created == 0 and m.cache_hits == len(result.keys[kind]) > 0


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_e2e5_tier2_cp_cyclopropene(
    recipe_name: str,
    recipes: Callable[[str], Recipe],
    tmp_path: Path,
    candidate_dir: Path,
    commit_sha: str,
) -> None:
    """Gated: conservation, dG(1 M) < 0, 0 imaginary, P1a_n sigma 1 g 1, UMA window; caching."""
    recipe = recipes(recipe_name)
    fixture = t2()
    reaction = fixture.reaction
    assert reaction is not None and fixture.window_dG_r_1M_kcal_mol is not None
    store_path = tmp_path / "store.sqlite"
    gas: dict[str, SpeciesResult] = {}
    with ArtifactStore(store_path) as store:
        for spec in fixture.species:
            gas[spec.species_id] = run_species(spec, recipe, store)
    ensembles = {k: v.ensemble for k, v in gas.items()}
    for spec in fixture.species:
        assert_no_duplicate_records(ensembles[spec.species_id], spec.smiles, spec.conformer_options)
        lo = ensembles[spec.species_id].records[ensembles[spec.species_id].lowest_index]
        assert not lo.thermo.imaginary_frequencies_cm1, spec.species_id
    duplicates = {
        k: sum(reason == "duplicate_after_push" for _, reason in v.dropped) for k, v in gas.items()
    }
    p1 = lowest(ensembles["P1a_n"].records)
    assert p1.thermo.rotational_symmetry_number == 1 and p1.degeneracy == 1

    config = recipe.thermo_config
    energies = checked_reaction_free_energy(reaction, ensembles, config)
    dg = energies.dG_1M_kcal_mol
    assert dg < 0.0, dg
    low, high = fixture.window_dG_r_1M_kcal_mol
    inside = low < dg < high
    deviation = 0.0 if inside else (dg - high if dg >= high else dg - low)
    if recipe_name == "uma":
        assert inside, f"STOP AND REPORT (Q-E5): UMA dG_r(1 M) {dg:.3f} outside ({low}, {high})"

    incremental: dict[str, object] = {}
    n_kept = {k: len(v.records) for k, v in ensembles.items()}
    if recipe_name == "xtb":
        with ArtifactStore(store_path) as store:
            solv = {
                s.species_id: run_species(
                    s, recipe, store, single_points=[SinglePoint(ALPB_DIOXANE)]
                )
                for s in fixture.species
            }
        upstream = sum(r.metrics.stages[k].engine_calls for r in solv.values() for k in UPSTREAM)
        alpb_calls = sum(r.metrics.stages["single_point"].engine_calls for r in solv.values())
        cache = {
            kind: {
                "hits": sum(all_hit(r, kind) for r in solv.values()),
                "misses": sum(not all_hit(r, kind) for r in solv.values()),
            }
            for kind in ("geometry_opt", "frequency", "single_point")
        }
        assert upstream == 0
        assert cache["geometry_opt"] == {"hits": 3, "misses": 0}
        assert cache["frequency"] == {"hits": 3, "misses": 0}
        assert cache["single_point"] == {"hits": 0, "misses": 3}
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
        solv_energies = checked_reaction_free_energy(reaction, solvated, config)
        nu = {s: -c for s, c in reaction.reactants} | {s: c for s, c in reaction.products}
        additive = dg + sum(nu[k] * dg_solv[k] for k in nu)
        assert solv_energies.dG_1M_kcal_mol == pytest.approx(additive, abs=1e-9)
        assert abs(solv_energies.dG_1M_kcal_mol - dg) > 1e-6
        incremental = {
            "alpb_dioxane": {
                "expected_calls": sum(n_kept.values()),
                "observed_calls": alpb_calls,
                "upstream_calls": upstream,
                "species_stage_cache": cache,
                "dG_solv_kcal_mol": dg_solv,
                "dG_solv_sign": {
                    k: "negative" if v < 0 else "positive" for k, v in dg_solv.items()
                },
                "dG_r_1M_solvated_kcal_mol": solv_energies.dG_1M_kcal_mol,
            }
        }
    else:
        with ArtifactStore(store_path) as store:
            again = {s.species_id: run_species(s, recipe, store) for s in fixture.species}
        calls = sum(r.metrics.engine_calls for r in again.values())
        assert calls == 0
        incremental = {"plain_rerun": {"expected_calls": 0, "observed_calls": calls}}

    failures = []
    species = {}
    for spec in fixture.species:
        found = failure_report(spec.species_id, failure_rows(store_path, gas[spec.species_id].keys))
        failures.extend(found)
        species[spec.species_id] = species_payload(spec, gas[spec.species_id], None, found)
    derived = {
        "ensemble": energies.model_dump(),
        "window_dG_r_1M_kcal_mol": [low, high],
        "inside_window": inside,
        "window_gated": recipe_name == "uma",
        "window_deviation_kcal_mol": deviation,
        "literature": {
            "dE_r_kcal_mol": fixture.literature["dE_r_kcal_mol"] if fixture.literature else None,
            "dG_r_1M_kcal_mol": fixture.literature["dG_r_1M_kcal_mol"]
            if fixture.literature
            else None,
            "source": fixture.literature["source"] if fixture.literature else None,
            "delta_dG_r_1M_kcal_mol": dg - fixture.literature["dG_r_1M_kcal_mol"]
            if fixture.literature
            else None,
        },
        "incremental": incremental,
    }
    identity = build_engine(recipe.engine_stage, recipe.engine_runtime).identity
    payload = candidate(
        fixture=fixture.name,
        recipe=recipe_name,
        commit_sha=commit_sha,
        env=environment(identity, DEVICES[recipe_name]),
        thermo_config=config,
        species=species,
        derived=derived,
        checks={},
    )
    payload["checks"] = checks(fixture.name, recipe_name, payload, None, {})
    write(candidate_dir / f"{fixture.name}.{recipe_name}.json", payload)
    print(
        f"\nT2 {recipe_name}: n_kept {n_kept}; duplicate_after_push {duplicates}; "
        f"dropped { {k: list(v.dropped) for k, v in gas.items()} }; failures {failures}; "
        f"dE_r {energies.dE_kcal_mol:.3f} dG_r(1 atm) {energies.dG_1atm_kcal_mol:.3f} "
        f"dG_r(1 M) {dg:.3f} kcal/mol; window ({low}, {high}) inside {inside} "
        f"gated {recipe_name == 'uma'} deviation {deviation:.3f}; P1a_n sigma "
        f"{p1.thermo.rotational_symmetry_number} g {p1.degeneracy}; incremental {incremental}"
    )
    assert_checks_pass(payload["checks"])
