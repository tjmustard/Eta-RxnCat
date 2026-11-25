"""Tests for per-pathway pruning and the selectivity runner (v0.6.0, slice 07; R7, G2, US-006)."""

from pathlib import Path
from typing import Any

import pytest
from orchestrator_helpers import uff_recipe

import eta_rxncat.orchestrator.species as species
import eta_rxncat.orchestrator.ts_ensemble as ts_ensemble
from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import (
    PathwayPruningRule,
    ReactionGraph,
    SelectivityResult,
    TSEnsemble,
    TSEnsembleOptions,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import (
    DownstreamNode,
    PathwayInputs,
    SelectivityInputError,
    SpeciesSpec,
    TSEnsembleRun,
    evaluate_pathway_pruning,
    run_selectivity,
)
from eta_rxncat.store import ArtifactStore

HYDROGEN = {"symbols": ["H"], "coordinates": [[0.0, 0.0, 0.0]], "charge": 0, "spin_multiplicity": 2}
THRESHOLD = 1.5
T = 298.15
G0 = -1.234567891
SHA = "c" * 64


def node(node_id: str, priority: int, pathway: str | None, kind: str = "intermediate") -> dict:
    """Return a one-template node dict."""
    return {
        "id": node_id,
        "label": node_id,
        "kind": kind,
        "priority": priority,
        "templates": [{"id": "t1", "rank": 1, "components": [{"state": HYDROGEN, "count": 1}]}],
        "pathway": pathway,
    }


def rule_dict(pathways: tuple[str, str] = ("endo", "exo"), threshold: float = THRESHOLD) -> dict:
    """Return a pathway pruning rule dict."""
    return {
        "id": "endo_vs_exo",
        "metric": "ddG_dagger_kcal_mol",
        "pathways": list(pathways),
        "threshold_kcal_mol": threshold,
        "prune": "minor_pathway_priority_ge_2",
    }


def graph(rules: list[dict] | None = None, extra: list[dict] | None = None) -> ReactionGraph:
    """Two competing pathways with a downstream node each and one unlabelled node."""
    nodes = [
        node("TS_endo", 1, "endo", "transition_state"),
        node("TS_exo", 1, "exo", "transition_state"),
        node("after_endo", 2, "endo"),
        node("after_exo", 2, "exo"),
        node("free", 2, None),
        *(extra or []),
    ]
    return ReactionGraph.model_validate(
        {
            "schema_version": 1,
            "name": "competing",
            "nodes": nodes,
            "pathway_pruning_rules": [rule_dict()] if rules is None else rules,
        }
    )


def result(signed: dict[str, float], names: tuple[str, ...] = ("endo", "exo")) -> SelectivityResult:
    """Return a two-pathway (or more) result carrying the given signed gaps."""
    per = {
        n: {"G_pathway_hartree": G0 + 0.001 * k, "n_members": 1, "n_excluded": 0, "fraction": 0.5}
        for k, n in enumerate(names)
    }
    gap = max(abs(v) for v in signed.values())
    return SelectivityResult.model_validate(
        {
            "ddG_dagger_kcal_mol": gap,
            "signed_ddG_dagger_kcal_mol": signed,
            "ratio": 2.0,
            "selectivity_percent": 10.0,
            "kind": "de",
            "major_pathway": names[0],
            "temperature_k": T,
            "per_pathway": per,
        }
    )


# --- evaluate_pathway_pruning (pure) -------------------------------------------------------------


@pytest.mark.parametrize(
    ("gap", "pruned"),
    [(THRESHOLD - 0.01, False), (THRESHOLD, False), (THRESHOLD + 0.01, True)],
)
def test_prunes_only_above_the_threshold(gap: float, pruned: bool) -> None:
    """G2: strictly above the threshold prunes the minor's priority >= 2 nodes; at it, nothing."""
    g = graph()
    decision = evaluate_pathway_pruning(
        g.pathway_pruning_rules[0], result({"exo_vs_endo": gap}), g.nodes
    )
    assert decision.pruned_node_ids == (["after_exo"] if pruned else [])
    assert decision.ddG_dagger_kcal_mol == gap
    assert decision.threshold_kcal_mol == THRESHOLD
    assert decision.signed_ddG_dagger_kcal_mol == {"exo_vs_endo": gap}
    assert decision.rule_id == "endo_vs_exo" and decision.pathways == ("endo", "exo")
    assert ("> threshold" in decision.reason) == pruned
    assert "after_endo" not in decision.pruned_node_ids and "free" not in decision.pruned_node_ids


def test_the_computed_minor_is_pruned_not_the_expected_one() -> None:
    """G2: when the second pathway is the computed major, the first is pruned; sign recorded."""
    g = graph()
    decision = evaluate_pathway_pruning(
        g.pathway_pruning_rules[0], result({"exo_vs_endo": -2.0}), g.nodes
    )
    assert decision.pruned_node_ids == ["after_endo"]
    assert decision.ddG_dagger_kcal_mol == 2.0
    assert decision.signed_ddG_dagger_kcal_mol == {"exo_vs_endo": -2.0}


def test_signed_key_follows_rule_order() -> None:
    """R7: ``"<b>_vs_<a>"`` with (a, b) in rule order, whichever direction the scorer keyed."""
    g = graph(rules=[rule_dict(("exo", "endo"))])
    decision = evaluate_pathway_pruning(
        g.pathway_pruning_rules[0], result({"exo_vs_endo": 1.7}), g.nodes
    )
    assert decision.signed_ddG_dagger_kcal_mol == {"endo_vs_exo": -1.7}
    assert decision.pruned_node_ids == ["after_exo"]  # exo is still the one with the larger G


def test_never_prunes_unlabelled_or_first_tier_nodes() -> None:
    """A ``pathway=None`` node and the priority-1 TS nodes are never pruned; ids are sorted."""
    g = graph(extra=[node("z_exo", 3, "exo"), node("a_exo", 2, "exo"), node("lone", 5, None)])
    decision = evaluate_pathway_pruning(
        g.pathway_pruning_rules[0], result({"exo_vs_endo": 50.0}), g.nodes
    )
    assert decision.pruned_node_ids == ["a_exo", "after_exo", "z_exo"]
    assert {"free", "lone", "TS_exo", "TS_endo"}.isdisjoint(decision.pruned_node_ids)


def test_nothing_pruned_without_a_summed_member() -> None:
    """R7: no result, a missing pathway or an empty one prunes nothing and names the pathway."""
    g = graph()
    rule = g.pathway_pruning_rules[0]
    missing = evaluate_pathway_pruning(rule, None, g.nodes)
    assert missing.reason == "no_valid_member:endo"
    assert missing.pruned_node_ids == [] and missing.ddG_dagger_kcal_mol is None
    assert missing.signed_ddG_dagger_kcal_mol == {} and missing.threshold_kcal_mol == THRESHOLD
    three = result({"exo_vs_endo": 9.0, "meta_vs_endo": 9.5}, names=("endo", "exo", "meta"))
    absent = PathwayPruningRule.model_validate(rule_dict(("endo", "nope")))
    assert evaluate_pathway_pruning(absent, three, g.nodes).reason == "no_valid_member:nope"
    rule_nope = PathwayPruningRule.model_validate(rule_dict(("exo", "meta")))
    assert evaluate_pathway_pruning(rule_nope, three, g.nodes).pruned_node_ids == []
    zero = three.model_copy(
        update={
            "per_pathway": {
                **three.per_pathway,
                "exo": three.per_pathway["exo"].model_copy(update={"n_members": 0}),
            }
        }
    )
    assert evaluate_pathway_pruning(rule, zero, g.nodes).reason == "no_valid_member:exo"


def test_three_pathways_use_the_free_energies_for_a_non_major_pair() -> None:
    """With more than two pathways the pair's gap comes from the pathway free energies."""
    g = graph()
    three = result({"exo_vs_endo": 0.6, "meta_vs_endo": 1.2}, names=("endo", "exo", "meta"))
    rule = PathwayPruningRule.model_validate(rule_dict(("exo", "meta"), threshold=0.1))
    decision = evaluate_pathway_pruning(rule, three, g.nodes)
    expected = 0.001 * HARTREE_KCAL_MOL
    assert decision.ddG_dagger_kcal_mol == pytest.approx(expected, abs=1e-9)
    assert decision.signed_ddG_dagger_kcal_mol == {"meta_vs_exo": pytest.approx(expected, abs=1e-9)}


# --- run_selectivity (stub ensembles, recording species runner) ----------------------------------


def member(index: int, g: float) -> dict[str, Any]:
    """Return a one-member dict."""
    return {
        "index": index,
        "source": "seed",
        "start_sha256": SHA,
        "G_hartree": g,
        "degeneracy": 1,
        "rmsd_to_seed_angstrom": 0.0,
        "face": [1],
        "validation_passed_bool": True,
        "weight": 1.0,
    }


def ensemble(pathway: str, g: float | None, **overrides: Any) -> TSEnsemble:
    """Return a one-member ensemble (or a failed one for ``g=None``)."""
    data: dict[str, Any] = {
        "pathway": pathway,
        "temperature_k": T,
        "reactant_key": [["C=CC=C", 1], ["C=C", 1]],
        "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
    }
    if g is None:
        data["failed_reason"] = "seed:ts_search_failed:max_steps"
    else:
        data.update(members=[member(0, g)], G_pathway_hartree=g)
    data.update(overrides)
    return TSEnsemble.model_validate(data)


class Recorder:
    """Stands in for the ensemble runner and the species runner; records every call."""

    def __init__(self, g_by_pathway: dict[str, float | None]) -> None:
        """Keep each pathway's free energy (``None`` = a failed pathway)."""
        self.g = g_by_pathway
        self.ensembles: list[str] = []
        self.species: list[str] = []

    def run_ts_ensemble_detailed(self, seed: Any, recipe: Any, store: Any, **kw: Any) -> Any:
        """Record the pathway and return its canned ensemble."""
        self.ensembles.append(kw["pathway"])
        built = ensemble(kw["pathway"], self.g[kw["pathway"]])
        return TSEnsembleRun(built, {}, None)  # type: ignore[arg-type]

    def run_species(self, spec: Any, recipe: Any, store: Any, **kw: Any) -> str:
        """Record the species and return a marker."""
        self.species.append(spec.species_id)
        return f"ran:{spec.species_id}"


def downstream() -> dict[str, DownstreamNode]:
    """Inputs for the three priority-2 nodes (one butane-like species each)."""
    return {
        n: DownstreamNode(SpeciesSpec(n, "CCCC", 0, 1, ConformerOptions(n_embed=2)), uff_recipe())
        for n in ("after_endo", "after_exo", "free")
    }


def inputs() -> dict[str, PathwayInputs]:
    """Placeholder ensemble inputs; the stub ensemble runner ignores them."""
    return {
        p: PathwayInputs(
            seed=None,  # type: ignore[arg-type]
            recipe=None,  # type: ignore[arg-type]
            core_indices=(0,),
            reactant_key=(("C=CC=C", 1),),
            member_gates=lambda r: {},
        )
        for p in ("endo", "exo")
    }


def run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    recorder: Recorder,
    g: ReactionGraph | None = None,
):
    """Run ``run_selectivity`` with the recorder standing in for both runners."""
    monkeypatch.setattr(ts_ensemble, "run_ts_ensemble_detailed", recorder.run_ts_ensemble_detailed)
    monkeypatch.setattr(species, "run_species", recorder.run_species)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        return run_selectivity(
            g or graph(),
            store,
            pathways=inputs(),
            downstream=downstream(),
            optimizer=None,  # type: ignore[arg-type]
            options=TSEnsembleOptions(),
            kind="de",
        )


@pytest.mark.parametrize(
    ("gap", "pruned"),
    [(THRESHOLD - 0.01, False), (THRESHOLD + 0.01, True)],
)
def test_runner_prunes_on_the_boltzmann_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, gap: float, pruned: bool
) -> None:
    """Around the threshold: a pruned node has status ``pruned``; the species runner skips it."""
    recorder = Recorder({"endo": G0, "exo": G0 + gap / HARTREE_KCAL_MOL})
    outcome = run(tmp_path, monkeypatch, recorder)
    assert recorder.ensembles == ["endo", "exo"]
    assert outcome.nodes["after_exo"].status == ("pruned" if pruned else "computed")
    assert outcome.nodes["after_endo"].status == "computed"
    assert outcome.nodes["free"].status == "computed"
    assert ("after_exo" in recorder.species) == (not pruned)
    assert sorted(recorder.species) == sorted(
        n for n, o in outcome.nodes.items() if o.status == "computed"
    )
    (decision,) = outcome.decisions
    assert decision.ddG_dagger_kcal_mol == pytest.approx(gap, abs=1e-9)
    assert outcome.score is not None and outcome.score.pruning == decision
    assert outcome.nodes["after_exo"].pruned_by == (("endo_vs_exo",) if pruned else ())
    assert outcome.nodes["after_exo"].result == (None if pruned else "ran:after_exo")


def test_runner_prunes_the_computed_minor_whatever_the_caller_expects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first pathway of the rule is the high one here: it is the one pruned."""
    recorder = Recorder({"endo": G0 + 2.5 / HARTREE_KCAL_MOL, "exo": G0})
    outcome = run(tmp_path, monkeypatch, recorder)
    assert outcome.nodes["after_endo"].status == "pruned"
    assert outcome.nodes["after_exo"].status == "computed"
    assert outcome.decisions[0].signed_ddG_dagger_kcal_mol["exo_vs_endo"] == pytest.approx(-2.5)
    assert "after_endo" not in recorder.species


def test_runner_with_a_failed_pathway_prunes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pathway with no summed member: no score, no pruning, reason recorded, all nodes run."""
    recorder = Recorder({"endo": G0, "exo": None})
    outcome = run(tmp_path, monkeypatch, recorder)
    assert outcome.score is None
    assert outcome.decisions[0].reason == "no_valid_member:exo"
    assert outcome.decisions[0].pruned_node_ids == []
    assert {o.status for o in outcome.nodes.values()} == {"computed"}
    assert sorted(recorder.species) == ["after_endo", "after_exo", "free"]


def test_runner_without_rules_runs_everything(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No rule, no pruning (and there is no library default threshold)."""
    recorder = Recorder({"endo": G0, "exo": G0 + 9.0 / HARTREE_KCAL_MOL})
    outcome = run(tmp_path, monkeypatch, recorder, graph(rules=[]))
    assert outcome.decisions == ()
    assert {o.status for o in outcome.nodes.values()} == {"computed"}
    assert outcome.score is not None and outcome.score.pruning is None


def test_runner_refuses_missing_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Inputs must match the graph's priority-1 pathways and every unpruned downstream node."""
    recorder = Recorder({"endo": G0, "exo": G0})
    monkeypatch.setattr(ts_ensemble, "run_ts_ensemble_detailed", recorder.run_ts_ensemble_detailed)
    monkeypatch.setattr(species, "run_species", recorder.run_species)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(SelectivityInputError, match="pathways"):
            run_selectivity(
                graph(),
                store,
                pathways={"endo": inputs()["endo"]},
                downstream=downstream(),
                optimizer=None,  # type: ignore[arg-type]
                options=TSEnsembleOptions(),
                kind="de",
            )
        partial = {k: v for k, v in downstream().items() if k != "free"}
        with pytest.raises(SelectivityInputError, match="'free'"):
            run_selectivity(
                graph(),
                store,
                pathways=inputs(),
                downstream=partial,
                optimizer=None,  # type: ignore[arg-type]
                options=TSEnsembleOptions(),
                kind="de",
            )


def test_a_pruned_node_needs_no_inputs_and_makes_no_store_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the real species runner, a pruned node leaves no row and no engine work behind."""
    recorder = Recorder({"endo": G0, "exo": G0 + 3.0 / HARTREE_KCAL_MOL})
    monkeypatch.setattr(ts_ensemble, "run_ts_ensemble_detailed", recorder.run_ts_ensemble_detailed)
    path = tmp_path / "s.sqlite"
    nodes = {
        "after_endo": DownstreamNode(
            SpeciesSpec("after_endo", "CCCC", 0, 1, ConformerOptions(n_embed=2)), uff_recipe()
        ),
        "free": DownstreamNode(
            SpeciesSpec("free", "CC", 0, 1, ConformerOptions(n_embed=2)), uff_recipe()
        ),
    }  # no entry for the pruned ``after_exo``
    with ArtifactStore(path) as store:
        outcome = run_selectivity(
            graph(),
            store,
            pathways=inputs(),
            downstream=nodes,
            optimizer=None,  # type: ignore[arg-type]
            options=TSEnsembleOptions(),
            kind="de",
        )
        searches = store.query("conformer_search")
    assert (
        outcome.nodes["after_exo"].status == "pruned" and outcome.nodes["after_exo"].result is None
    )
    assert outcome.nodes["after_endo"].result is not None
    assert outcome.nodes["after_endo"].result.ensemble.records
    assert len(searches) == 2  # two computed species, none for the pruned node


def test_importing_the_module_stays_light() -> None:
    """The runner's heavy imports are inside the function: no RDKit at module import."""
    import subprocess
    import sys

    code = (
        "import sys; import eta_rxncat.orchestrator.selectivity as m; "
        "assert 'rdkit' not in sys.modules; assert m.run_selectivity"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
