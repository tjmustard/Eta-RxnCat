"""Tier O: every offline module seam with real modules on both sides (mission R7, R8, R21, R36).

No engine binary, no network, no stored reference number. Numbers are compared only between a
fresh result and its cache replay, or between two values of one run. Each test names the smallest
source edits (seam breaks, R4) that make it fail.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import (
    EnumeratedCandidate,
    EnumerationPlan,
    StageConfig,
    ThermoResult,
    dump_reaction_graph_json,
    load_reaction_graph,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.enumerator import enumerate_candidates
from eta_rxncat.optimize import PRFOOptimizer
from eta_rxncat.orchestrator import (
    ReactionSpec,
    SpeciesResult,
    SpeciesSpec,
    TSRecipe,
    build_engine,
    enumerated_pathway_inputs,
    reaction_free_energy,
    run_species,
)
from eta_rxncat.orchestrator.ts_ensemble import find_clash
from eta_rxncat.store import ArtifactStatus, ArtifactStore, build_stage_key

from .conftest import ROOT, V070_ENUMERATION_YAML, gfn2_stage, load_v070_plan, row_count, uff_recipe

pytestmark = pytest.mark.integration

WEIGHT_TOLERANCE = 1e-12
"""``weights_sum_tolerance`` of ``t4_flexible_alkyl.yaml`` (mission R7)."""

TS_NODES = ("TS1a_n", "TS1a_x")


def _species(species_id: str, smiles: str) -> SpeciesSpec:
    return SpeciesSpec(species_id, smiles, 0, 1, ConformerOptions(n_embed=3))


def _butane() -> SpeciesSpec:
    return _species("butane", "CCCC")


def _rows_created(result: SpeciesResult) -> int:
    return sum(stage.rows_created for stage in result.metrics.stages.values())


def _assert_replay(first: SpeciesResult, again: SpeciesResult) -> None:
    """``again`` is served entirely from the store and equals ``first``."""
    assert again.metrics.engine_calls == 0
    assert _rows_created(again) == 0
    for kind, keys in again.keys.items():
        assert again.metrics.stages[kind].cache_hits == len(keys), kind
    assert again.ensemble == first.ensemble
    assert again.dropped == first.dropped
    assert again.single_point_energies == first.single_point_energies
    assert again.keys == first.keys
    assert again.frequency_dispositions == first.frequency_dispositions


def _payload(store: ArtifactStore, key: str) -> dict[str, Any] | None:
    """Read one row's payload straight from the store file."""
    connection = sqlite3.connect(store.path)
    try:
        row = connection.execute(
            "SELECT payload_json FROM stage_artifacts WHERE key = ?", (key,)
        ).fetchone()
    finally:
        connection.close()
    return None if row is None else json.loads(row[0])


def test_to1_species_runner_store_roundtrip(store: ArtifactStore, tmp_path: Path) -> None:
    """T-O1: store, species runner, UFF, geomeTRIC and thermo.

    Seam breaks: drop ``engine_identity`` from ``stage_payload`` (``store/keys.py``);
    ``ArtifactStore.get`` returns ``None``.
    """
    recipe = uff_recipe()
    first = run_species(_butane(), recipe, store)
    rows = row_count(store)
    assert rows > 0
    assert rows == _rows_created(first)
    assert first.metrics.engine_calls > 0

    again = run_species(_butane(), recipe, store)
    _assert_replay(first, again)
    assert row_count(store) == rows

    with ArtifactStore(tmp_path / "fresh.db") as fresh:
        other = run_species(_butane(), recipe, fresh)
    assert other.keys == first.keys

    # The stored row is found by this engine's identity and by no other version of it.
    engine = build_engine(recipe.engine_stage, recipe.engine_runtime)
    stage = StageConfig.model_validate({**engine.stage.model_dump(), "kind": "frequency"})
    record = first.ensemble.records[0]
    key = build_stage_key(record.state, stage, engine.identity)
    assert key.key in first.keys["frequency"]
    assert store.get(key) is not None
    newer = engine.identity.model_copy(update={"version": "another-version"})
    assert store.get(build_stage_key(record.state, stage, newer)) is None

    thermo = record.thermo
    with ArtifactStore(tmp_path / "payload.db") as payloads:
        payloads.put(key, ArtifactStatus.COMPLETED, thermo.model_dump(mode="json"))
        stored = payloads.get(key)
    assert ThermoResult.model_validate(stored) == thermo


def test_to2_reaction_energies_replay_from_reopened_store(store: ArtifactStore) -> None:
    """T-O2: ``reaction_free_energy`` of two real runs equals its replay from a reopened store.

    Seam break: ``reaction_free_energy`` drops one species' term.
    """
    recipe = uff_recipe()
    species = [_butane(), _species("isobutane", "CC(C)C")]
    spec = ReactionSpec(
        reactants=(("butane", 1),),
        products=(("isobutane", 1),),
        smiles={s.species_id: s.smiles for s in species},
    )
    first = {s.species_id: run_species(s, recipe, store) for s in species}
    energies = reaction_free_energy(
        spec, {i: r.ensemble for i, r in first.items()}, recipe.thermo_config
    )
    gibbs = {i: r.ensemble.ensemble_gibbs_hartree for i, r in first.items()}
    assert energies.dG_1M_kcal_mol == (gibbs["isobutane"] - gibbs["butane"]) * HARTREE_KCAL_MOL
    store.close()

    with ArtifactStore(store.path) as reopened:
        again = {s.species_id: run_species(s, recipe, reopened) for s in species}
    for species_id, result in again.items():
        _assert_replay(first[species_id], result)
    replay = reaction_free_energy(
        spec, {i: r.ensemble for i, r in again.items()}, recipe.thermo_config
    )
    assert replay == energies


def test_to3_conformer_stage_stores_members(store: ArtifactStore) -> None:
    """T-O3: conformers, engine and store through ``run_species``.

    1-Propanol keeps several conformers, so the weight sum is over more than one record.

    Seam break: the conformer stage skips storing the members.
    """
    recipe = uff_recipe()
    spec = _species("propanol", "CCCO")
    first = run_species(spec, recipe, store)

    (key,) = first.keys["conformer_search"]
    pool = _payload(store, key)
    assert pool is not None
    n_atoms = len(first.ensemble.records[0].state.symbols)
    members = {m["id"]: m["xyz"] for m in pool["members"]}
    assert members and len(members) == len(pool["members"])
    assert all(len(xyz) == n_atoms for xyz in members.values())
    assert set(pool["pre_dedup_survivors"]) <= set(members)
    assert all(set(r.source_ids) <= set(members) for r in first.ensemble.records)

    weights = first.ensemble.boltzmann_weights
    assert len(weights) == len(first.ensemble.records) > 1
    assert abs(sum(weights) - 1) <= WEIGHT_TOLERANCE

    _assert_replay(first, run_species(spec, recipe, store))


def _enumerate(plan: EnumerationPlan, max_rmsd: float) -> list[EnumeratedCandidate]:
    return list(enumerate_candidates(plan, max_alignment_rmsd_angstrom=max_rmsd).candidates)


def _moved_atom_plan(plan: EnumerationPlan) -> EnumerationPlan:
    """The plan with each TS node naming template atom 17, which a graft moves to index 16.

    The v0.7.0 plan names only atoms 0-5 on its TS nodes, which no graft moves, and freezes
    nothing, so a lost index remap would not show on it. Atom 17 replaces atom 5 in the second
    forming bond and is frozen in the node's stage. The chemistry is not meaningful; nothing runs.
    """
    data = plan.model_dump()
    for node in data["reference_graph"]["nodes"]:
        if node["id"] in TS_NODES:
            node["stages"] = [
                StageConfig(
                    kind="geometry_opt", engine="rdkit_ff", method="uff", frozen_atom_indices=[17]
                ).model_dump()
            ]
    for site in data["sites"]:
        for site_map in site["maps"]:
            if site_map["node_id"] in TS_NODES:
                site_map["forming_bonds"] = [(1, 2), (3, 17)]
    return EnumerationPlan.model_validate(data)


def test_to4_enumerator_runs_the_real_graft() -> None:
    """T-O4: ``enumerate_candidates`` with the real ``graft`` on the v0.7.0 plan.

    Seam break: the enumerator skips the ``index_map`` remap (of the forming bonds or of the
    stages' frozen atoms).
    """
    loaded = load_v070_plan()
    assert loaded.max_alignment_rmsd_angstrom == 0.15
    results = [
        enumerate_candidates(
            loaded.plan, max_alignment_rmsd_angstrom=loaded.max_alignment_rmsd_angstrom
        )
        for _ in range(2)
    ]
    assert results[0].model_dump_json() == results[1].model_dump_json()
    candidates = results[0].candidates
    assert [c.status for c in candidates] == ["ok", "ok"]
    for candidate in candidates:
        assert candidate.records
        for record in candidate.records:
            assert record.status == "ok"
            assert record.close_contact_count == 0
            assert record.alignment_rmsd_angstrom is not None
            assert record.alignment_rmsd_angstrom <= loaded.max_alignment_rmsd_angstrom
        assert candidate.graph is not None
        for node in candidate.graph.nodes:
            for template in node.templates:
                for component in template.components:
                    assert (component.state.charge, component.state.spin_multiplicity) == (0, 1)

    # Template indices come out as product indices.
    moved = _moved_atom_plan(loaded.plan)
    for candidate in _enumerate(moved, loaded.max_alignment_rmsd_angstrom):
        assert candidate.status == "ok", candidate.detail
        assert candidate.graph is not None
        for record in candidate.records:
            if record.node_id not in TS_NODES:
                continue
            assert record.mapped_forming_bonds is not None
            assert [tuple(p) for p in record.mapped_forming_bonds] == [(1, 2), (3, 16)]
        for node in candidate.graph.nodes:
            if node.id in TS_NODES:
                assert node.stages is not None
                assert [s.frozen_atom_indices for s in node.stages] == [[16]]


def test_to5_candidate_graph_file_roundtrip(tmp_path: Path) -> None:
    """T-O5: an enumerated candidate graph through ``dump_reaction_graph_json`` and a file.

    The input graph is produced in this test: no committed standalone neutral ``ReactionGraph``
    file exists.

    Seam break: ``dump_reaction_graph_json`` omits one node field (for example ``priority``).
    """
    loaded = load_v070_plan()
    candidate = _enumerate(loaded.plan, loaded.max_alignment_rmsd_angstrom)[0]
    assert candidate.graph is not None
    path = tmp_path / "candidate.json"
    path.write_text(dump_reaction_graph_json(candidate.graph), encoding="utf-8")
    assert load_reaction_graph(path) == candidate.graph


def _ts_recipe() -> TSRecipe:
    return TSRecipe(name="xtb", engine_stage=gfn2_stage(), ts_optimizer=PRFOOptimizer())


def _ethyl(plan: EnumerationPlan, max_rmsd: float) -> EnumeratedCandidate:
    (ethyl,) = [c for c in _enumerate(plan, max_rmsd) if c.candidate_id == "ethyl"]
    return ethyl


@pytest.mark.parametrize("node_id", TS_NODES)
def test_to6_enumerated_seed_inputs(node_id: str) -> None:
    """T-O6: the ethyl candidate gives clean seed inputs for each TS node; no engine is built.

    Seam break: ``enumerated_pathway_inputs`` returns the reference (ungrafted) forming bonds.
    """
    loaded = load_v070_plan()
    template_id = f"{node_id}__ethyl"
    for plan, moved in ((loaded.plan, False), (_moved_atom_plan(loaded.plan), True)):
        candidate = _ethyl(plan, loaded.max_alignment_rmsd_angstrom)
        (record,) = [r for r in candidate.records if r.node_id == node_id]
        inputs = enumerated_pathway_inputs(
            candidate, node_id, template_id, _ts_recipe(), lambda _: {}
        )
        seed = inputs.seed
        assert record.mapped_forming_bonds is not None
        composed = {frozenset(p) for p in record.mapped_forming_bonds}
        assert {frozenset(p) for p in seed.forming_bonds} == composed
        assert list(inputs.core_indices) == seed.start.active_atom_indices
        if moved:
            assert composed == {frozenset((1, 2)), frozenset((3, 16))}
        else:
            assert (
                find_clash(seed.start, [*perceive_bonds(seed.start), *seed.forming_bonds]) is None
            )


def test_plan_loader_parity() -> None:
    """R21: the conftest plan loader equals ``tests/e2e/v070.py``'s, byte for byte.

    The E2E loader runs in a subprocess, because it imports its sibling modules by bare name.

    Seam break: the conftest loader resolves ``xyz`` against the repo root, not the YAML's
    directory.
    """
    script = (
        "import sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); import v070; "
        "sys.stdout.write(v070.load_enumeration(Path(sys.argv[2])).plan.model_dump_json())"
    )
    done = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "tests" / "e2e"), str(V070_ENUMERATION_YAML)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == load_v070_plan().plan.model_dump_json()
