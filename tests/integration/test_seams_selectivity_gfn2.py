"""Tier X: the selectivity chain and the review export on CPU GFN2 (mission R9, R35, R37, R42).

Real enumerator, graph file round trip, TS ensembles, scorer, store, exporter, reader and bundle
writer, with the ``xtb_subprocess`` engine. No stored reference number: values are compared only
between a fresh result and its cache replay, or between two writes of one document. Each test names
the smallest source edits (seam breaks, R4) that make it fail. T-X4 and T-X5 share one
module-scoped store; either test runs alone.

Deselected by default (``xtb``); run with the mission R2 Tier X command.
"""

import contextlib
import json
import re
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from eta_rxncat.core import (
    EnumeratedCandidate,
    EnumerationPlan,
    FallbackAttempt,
    FallbackRecord,
    ReactionGraph,
    TSEnsembleOptions,
    dump_reaction_graph_json,
    load_reaction_graph,
)
from eta_rxncat.mapping.enumerator import enumerate_candidates
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer
from eta_rxncat.orchestrator import (
    PathwayInputs,
    SelectivityRun,
    TSRunResult,
    enumerated_pathway_inputs,
    run_selectivity,
)
from eta_rxncat.review.bundle import write_review_bundle
from eta_rxncat.review.export import export_run_data
from eta_rxncat.review.run_data import (
    RecordCandidate,
    RecordRun,
    RecordSample,
    RecordSelectivity,
    RecordSpecies,
    RunRecord,
    read_run_data,
)
from eta_rxncat.review.schema import SCHEMA_PATH
from eta_rxncat.store import ArtifactStore

from .conftest import V070Plan, load_v070_plan, row_count
from .test_seams_ts_gfn2 import _assert_all_hits, _member_gates, _ts_recipe

pytestmark = [pytest.mark.integration, pytest.mark.xtb]

ENSEMBLE_OPTIONS = TSEnsembleOptions(n_embed=1, n_perturb=1, max_research=1)
WEIGHT_TOLERANCE = 1e-12
TS_NODES = ("TS1a_n", "TS1a_x")


@pytest.fixture(scope="module")
def chain_store(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ArtifactStore]:
    """One store for T-X4 and T-X5, with the module's working directory in a temporary one."""
    root = tmp_path_factory.mktemp("tx45")
    with contextlib.chdir(root):
        artifact_store = ArtifactStore(root / "store.db")
        yield artifact_store
        artifact_store.close()


class Chain(NamedTuple):
    """The enumerated candidate, its graph read back from a file, and the run on it."""

    candidate: EnumeratedCandidate
    loaded_graph: ReactionGraph
    run_graph: ReactionGraph
    pathways: dict[str, PathwayInputs]
    nodes: dict[str, str]  # pathway label -> TS node id
    result: SelectivityRun


def _ethyl(loaded: V070Plan, plan: EnumerationPlan) -> EnumeratedCandidate:
    result = enumerate_candidates(
        plan, max_alignment_rmsd_angstrom=loaded.max_alignment_rmsd_angstrom
    )
    (ethyl,) = [c for c in result.candidates if c.candidate_id == "ethyl"]
    assert ethyl.status == "ok", ethyl.detail
    return ethyl


def _through_file(graph: ReactionGraph, path: Path) -> ReactionGraph:
    path.write_text(dump_reaction_graph_json(graph), encoding="utf-8")
    return load_reaction_graph(path)


def _select(
    graph: ReactionGraph, store: ArtifactStore, pathways: dict[str, PathwayInputs]
) -> SelectivityRun:
    return run_selectivity(
        graph,
        store,
        pathways=pathways,
        downstream={},
        optimizer=GeometricOptimizer(),
        options=ENSEMBLE_OPTIONS,
        kind="de",
    )


def _run_chain(store: ArtifactStore, directory: Path) -> Chain:
    """Enumerate, write and read the graph, then run the selectivity runner on the file's graph.

    The run graph is the loaded graph with **only** the two TS nodes copied to priority 1:
    ``run_selectivity`` runs the priority-1 pathways, and the v0.7.0 plan keeps its TS nodes at
    priority 2 for the fallback runner (R35). The pathway inputs come from the unmodified
    candidate. A second call on the same store replays every row.
    """
    loaded = load_v070_plan()
    candidate = _ethyl(loaded, loaded.plan)
    assert candidate.graph is not None
    loaded_graph = _through_file(candidate.graph, directory / "graph.json")
    run_graph = loaded_graph.model_copy(
        update={
            "nodes": [
                n.model_copy(update={"priority": 1}) if n.id in TS_NODES else n
                for n in loaded_graph.nodes
            ]
        }
    )
    specs = [p for s in loaded.plan.selectivity_sets for p in s.pathways]
    nodes = {p.pathway: p.node_id for p in specs}
    recipe = _ts_recipe()
    pathways = {
        label: enumerated_pathway_inputs(
            candidate, node_id, f"{node_id}__ethyl", recipe, _member_gates
        )
        for label, node_id in nodes.items()
    }
    result = _select(run_graph, store, pathways)
    return Chain(candidate, loaded_graph, run_graph, pathways, nodes, result)


def _rule_variant(plan: EnumerationPlan) -> EnumerationPlan:
    """The R42 variant: the TS nodes at priority 1 and one pathway pruning rule."""
    data = plan.model_dump()
    graph = data["reference_graph"]
    for node in graph["nodes"]:
        if node["id"] in TS_NODES:
            node["priority"] = 1
    graph["pathway_pruning_rules"] = [
        {
            "id": "endo_exo_ddG",
            "metric": "ddG_dagger_kcal_mol",
            "pathways": ["endo", "exo"],
            "threshold_kcal_mol": 1.5,
            "prune": "minor_pathway_priority_ge_2",
        }
    ]
    return EnumerationPlan.model_validate(data)


def _all_fail(result: TSRunResult) -> dict[str, bool]:
    """Member gates that reject the seed, so no pathway is summed or scored."""
    return {"rejected": False}


def test_tx4_graph_file_to_selectivity_and_replay(
    chain_store: ArtifactStore, tmp_path: Path
) -> None:
    """T-X4: enumerated graph -> file -> ``load_reaction_graph`` -> ``run_selectivity`` -> score.

    The gates run on the unmodified v0.7.0 plan; the one change to its graph is the TS-node
    priority copy of ``_run_chain``. Two variants then cover breaks the unmodified inputs cannot
    show:

    1. (R42, engine-free) the plan with the TS nodes at priority 1 and one
       ``pathway_pruning_rules`` entry (the plan has none), its graph round-tripped through a file.
    2. (run inputs, not the plan) each pathway's ``reactant_key`` replaced by a distinct marker
       and member gates that reject every seed. Both pathways share their reactants, so the plan
       cannot give them different keys, and different keys are not scorable; with no summed
       member nothing is scored. Every row replays from the store.

    Seam breaks: ``run_selectivity`` passes the wrong pathway's ``reactant_key``;
    ``load_reaction_graph`` drops ``pathway_pruning_rules`` or a node's ``pathway``.
    """
    chain = _run_chain(chain_store, tmp_path)
    assert chain.loaded_graph == chain.candidate.graph
    assert [n.id for n in chain.run_graph.nodes if n.priority == 1 and n.pathway] == list(TS_NODES)

    result = chain.result
    assert sorted(result.ensembles) == ["endo", "exo"]
    for label, run in result.ensembles.items():
        assert run.ensemble.failed_reason is None, (label, run.ensemble.failed_reason)
        assert run.ensemble.members, label
        assert abs(sum(m.weight for m in run.ensemble.members) - 1) <= WEIGHT_TOLERANCE, label
        assert run.ensemble.reactant_key == tuple(chain.pathways[label].reactant_key), label
    assert result.score is not None
    assert result.nodes == {} and result.decisions == ()

    count = row_count(chain_store)
    again = _select(chain.run_graph, chain_store, chain.pathways)
    for run in again.ensembles.values():
        _assert_all_hits(run)
    assert row_count(chain_store) == count
    assert again.score == result.score

    loaded = load_v070_plan()
    variant = _ethyl(loaded, _rule_variant(loaded.plan)).graph
    assert variant is not None and variant.pathway_pruning_rules
    assert _through_file(variant, tmp_path / "variant.json") == variant

    marked = {
        label: replace(
            inputs,
            reactant_key=((f"[{label}]", 1),),
            member_gates=_all_fail,
        )
        for label, inputs in chain.pathways.items()
    }
    rejected = _select(chain.run_graph, chain_store, marked)
    assert rejected.score is None
    for label, run in rejected.ensembles.items():
        assert run.ensemble.failed_reason == "seed:gate_failed:rejected", label
        assert run.ensemble.reactant_key == marked[label].reactant_key, label
        assert all(m.engine_calls == 0 for m in run.metrics.values()), label
    assert row_count(chain_store) == count


def _run_record(chain: Chain) -> RunRecord:
    """The ``RunRecord`` of a chain: only values the run and the candidate hold.

    ``run_selectivity`` runs no fallback, so each pathway's fallback record states what did
    happen: the node's one template (its rank) was tried and seeded the ensemble, with the
    ensemble's stored pre-relaxation wall time. No barrier, endpoint or gate is claimed.
    """
    candidate, score = chain.candidate, chain.result.score
    assert candidate.graph is not None and score is not None
    nodes = {n.id: n for n in candidate.graph.nodes}
    species: list[RecordSpecies] = []
    runs: list[RecordRun] = []
    for label, run in chain.result.ensembles.items():
        node_id = chain.nodes[label]
        template_id = chain.pathways[label].seed.ts_id
        (template,) = [t for t in nodes[node_id].templates if t.id == template_id]
        state = template.components[0].state
        species.append(RecordSpecies(species_id=template_id, label=template_id, state=state))
        recipe = chain.pathways[label].recipe
        fallback = FallbackRecord(
            node_id=node_id,
            attempts=[
                FallbackAttempt(
                    template_id=template_id,
                    rank=template.rank,
                    outcome="chosen",
                    wall_time_s=run.total_pre_relax_wall_time_s,
                )
            ],
            chosen_template_id=template_id,
        )
        runs.append(
            RecordRun(
                candidate_id=candidate.candidate_id,
                pathway=label,
                engine=run.ensemble.recipe_identity,
                optimizers=[GeometricOptimizer().identity, PRFOOptimizer().identity],
                species_id=template_id,
                analysis=recipe.analysis,
                fallback=fallback,
                ensemble=run.ensemble,
                stall_cap_reached_bool=run.stall_cap_reached_bool,
                samples=[
                    RecordSample(
                        template_id=template_id,
                        sample_index=keys.index,
                        source=keys.source,
                        species_id=template_id,
                        pre_relax_key=keys.pre_relax_key,
                        ts_opt_key=keys.ts_opt_key,
                        frequency_key=keys.frequency_key,
                    )
                    for keys in run.samples
                ],
                validation=recipe.validation_options,
            )
        )
    return RunRecord(
        species=species,
        candidates=[
            RecordCandidate(
                candidate_id=candidate.candidate_id,
                entry_ids_by_site=candidate.entry_ids_by_site,
                records=candidate.records,
            )
        ],
        runs=runs,
        selectivity=[
            RecordSelectivity(
                candidate_id=candidate.candidate_id,
                engine=runs[0].engine,
                result=score,
            )
        ],
    )


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}
_ANNOTATIONS = {"$defs", "default", "description", "discriminator", "title"}


def _schema_errors(value: Any, schema: dict[str, Any], root: dict[str, Any], at: str) -> list[str]:
    """Check ``value`` against the JSON Schema keywords the committed schema uses.

    The project has no schema validator dependency. An unknown keyword raises, so the check
    cannot pass by ignoring part of the schema.
    """
    errors: list[str] = []
    for keyword, rule in schema.items():
        bad = False
        if keyword in _ANNOTATIONS:
            continue
        if keyword == "$ref":
            target = root["$defs"][rule.removeprefix("#/$defs/")]
            errors += _schema_errors(value, target, root, at)
        elif keyword == "type":
            bad = not isinstance(value, _JSON_TYPES[rule]) or (
                isinstance(value, bool) and rule != "boolean"
            )
        elif keyword in ("anyOf", "oneOf"):
            matches = sum(not _schema_errors(value, option, root, at) for option in rule)
            bad = matches == 0 if keyword == "anyOf" else matches != 1
        elif keyword == "const":
            bad = value != rule
        elif keyword == "enum":
            bad = value not in rule
        elif keyword == "required":
            bad = isinstance(value, dict) and not set(rule) <= set(value)
        elif keyword == "properties":
            if isinstance(value, dict):
                for name, sub in rule.items():
                    if name in value:
                        errors += _schema_errors(value[name], sub, root, f"{at}.{name}")
        elif keyword == "additionalProperties":
            if isinstance(value, dict):
                extra = set(value) - set(schema.get("properties", {}))
                if rule is False:
                    bad = bool(extra)
                else:
                    for name in sorted(extra):
                        errors += _schema_errors(value[name], rule, root, f"{at}.{name}")
        elif keyword == "prefixItems":
            if isinstance(value, list):
                for i, (item, sub) in enumerate(zip(value, rule, strict=False)):
                    errors += _schema_errors(item, sub, root, f"{at}[{i}]")
        elif keyword == "items":
            if isinstance(value, list):
                start = len(schema.get("prefixItems", []))
                for i, item in enumerate(value[start:], start=start):
                    errors += _schema_errors(item, rule, root, f"{at}[{i}]")
        elif keyword == "minItems":
            bad = isinstance(value, list) and len(value) < rule
        elif keyword == "maxItems":
            bad = isinstance(value, list) and len(value) > rule
        elif keyword == "minLength":
            bad = isinstance(value, str) and len(value) < rule
        elif keyword == "pattern":
            bad = isinstance(value, str) and re.search(rule, value) is None
        elif keyword == "minimum":
            bad = isinstance(value, int | float) and value < rule
        elif keyword == "maximum":
            bad = isinstance(value, int | float) and value > rule
        else:
            raise AssertionError(f"unchecked schema keyword {keyword!r} at {at}")
        if bad:
            errors.append(f"{at}: {keyword}")
    return errors


def _unsorted_objects(data: bytes) -> list[list[str]]:
    """The key lists of every JSON object of ``data`` that is not in sorted order."""
    found: list[list[str]] = []

    def check(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        keys = [key for key, _ in pairs]
        if keys != sorted(keys):
            found.append(keys)
        return dict(pairs)

    json.loads(data, object_pairs_hook=check)
    return found


def _files(directory: Path) -> dict[str, bytes]:
    return {
        p.relative_to(directory).as_posix(): p.read_bytes()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def test_tx5_review_export_round_trip(chain_store: ArtifactStore, tmp_path: Path) -> None:
    """T-X5: T-X4's run -> ``RunRecord`` -> export -> schema -> lenient reader -> bundle bytes.

    The run comes from the shared store, so after T-X4 it is a replay of T-X4's rows.

    Seam breaks: the ``RunData`` serialiser writes keys out of sorted order;
    ``export_run_data`` skips a sample's ``ts_opt`` row.
    """
    chain = _run_chain(chain_store, tmp_path)
    record = _run_record(chain)
    count = row_count(chain_store)
    export = export_run_data(record, chain_store)
    assert row_count(chain_store) == count

    # Every row a sample names is in the document, and nothing else is.
    samples = [s for run in record.runs for s in run.samples]
    expected = {("pre_relax", s.pre_relax_key) for s in samples if s.pre_relax_key} | {
        ("ts_search", s.ts_opt_key) for s in samples if s.ts_opt_key
    }
    assert {kind for kind, _ in expected} == {"pre_relax", "ts_search"}
    assert {(t.kind, t.stage_key) for t in export.trajectories} == expected
    assert all(t.status == "stored" for t in export.trajectories)
    frequency_keys = {s.frequency_key for s in samples if s.frequency_key}
    assert frequency_keys
    assert {f.stage_key for f in export.frequencies} == frequency_keys
    assert all(f.status == "completed" for f in export.frequencies)
    assert sorted(c.pathway for c in export.candidates) == ["endo", "exo"]
    for candidate in export.candidates:
        assert candidate.members, candidate.pathway
        assert candidate.ddG_dagger_kcal_mol == record.selectivity[0].result.ddG_dagger_kcal_mol

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert _schema_errors({"schema_version": 1}, schema, schema, "$")
    document = export.model_dump_json().encode()
    assert _schema_errors(json.loads(document), schema, schema, "$") == []
    assert read_run_data(document) == export

    first = _files(write_review_bundle(export, tmp_path / "a"))
    second = _files(write_review_bundle(export, tmp_path / "b"))
    assert {"index.html", "run_data.json", "MANIFEST.sha256"} <= set(first)
    assert first == second
    written = first["run_data.json"]
    assert _unsorted_objects(written) == []
    assert _schema_errors(json.loads(written), schema, schema, "$") == []
    assert read_run_data(written).candidates
