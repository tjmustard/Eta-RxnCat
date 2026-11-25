"""The selectivity scorer: Boltzmann-summed pathway free energies to ddG-dagger and selectivity.

Mission §5 "Selectivity" (v0.6.0, slice 04), pure and closed form. For each pathway the free energy
is ``G_p = -RT ln sum_i g_i exp(-G_i/RT)`` over the summed members, with the member degeneracy
``g_i`` (``G_i - RT ln g_i``, R8), computed against the lowest member so nothing overflows or is
clamped. Two pathways give ``ddG = G_minor - G_major >= 0``, ``r = exp(ddG/RT)`` and
``100 (r - 1)/(r + 1)``; with more, the shares are a softmax of ``-G_p/RT``.

No engine, RDKit, PySCF, torch or geomeTRIC is imported at module level (G8): the constants are
``eta_rxncat.thermo.constants`` (ADR-0026, DV-03) and ``eta_rxncat.engines.units``.

Slice 07 adds the pure ``evaluate_pathway_pruning`` (mission R7) and ``run_selectivity``, which
composes the TS ensembles (slice 06) and the species runner. Those need RDKit, so
``run_selectivity`` imports them inside the function: importing this module stays light.
"""

import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from eta_rxncat.core import (
    PathwayPruningRule,
    PathwaySelectivity,
    PruningDecision,
    ReactionGraph,
    ReactionNode,
    SelectivityKind,
    SelectivityResult,
    TSEnsemble,
    TSEnsembleOptions,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS

if TYPE_CHECKING:
    from eta_rxncat.optimize import Optimizer
    from eta_rxncat.orchestrator.species import Recipe, SpeciesResult, SpeciesSpec
    from eta_rxncat.orchestrator.ts import TSRecipe, TSSpec
    from eta_rxncat.orchestrator.ts_ensemble import MemberGates, TSEnsembleRun
    from eta_rxncat.store import ArtifactStore

_KINDS: tuple[str, ...] = ("ee", "de", "regio")


class SelectivityInputError(ValueError):
    """The pathways cannot be compared; the message names the offending field."""


def _rt_hartree(temperature_k: float) -> float:
    return R_GAS * temperature_k * J_PER_MOL_TO_HARTREE


def _pathway_free_energy_hartree(ensemble: TSEnsemble, rt: float) -> float:
    """Return ``-RT ln sum g_i exp(-G_i/RT)`` (Eh), order-free (``fsum``) and overflow-free."""
    lowest = min(m.G_hartree for m in ensemble.members)
    total = math.fsum(
        m.degeneracy * math.exp(-(m.G_hartree - lowest) / rt) for m in ensemble.members
    )
    return lowest - rt * math.log(total)


def _check_inputs(pathways: Mapping[str, TSEnsemble], kind: str, temperature_k: float) -> list[str]:
    """Raise ``SelectivityInputError`` unless the pathways are comparable; return sorted names."""
    if kind not in _KINDS:
        raise SelectivityInputError(f"kind must be one of {_KINDS}, got {kind!r}")
    if not (isinstance(temperature_k, int | float) and math.isfinite(temperature_k)) or (
        temperature_k <= 0
    ):
        raise SelectivityInputError(
            f"temperature_k must be positive and finite, got {temperature_k!r}"
        )
    names = sorted(pathways)
    if len(names) < 2:
        raise SelectivityInputError(f"pathways: need at least two, got {names}")
    first = pathways[names[0]]
    for name in names:
        ensemble = pathways[name]
        if ensemble.failed_reason is not None or not ensemble.members:
            reason = ensemble.failed_reason or "no summed member"
            raise SelectivityInputError(f"pathway {name!r} has no summed member: {reason}")
        if ensemble.temperature_k != temperature_k:
            raise SelectivityInputError(
                f"temperature_k: pathway {name!r} was summed at {ensemble.temperature_k} K, "
                f"the call asks {temperature_k} K"
            )
        if ensemble.reactant_key != first.reactant_key:
            raise SelectivityInputError(f"reactant_key: pathway {name!r} differs from {names[0]!r}")
        if ensemble.recipe_identity != first.recipe_identity:
            raise SelectivityInputError(
                f"recipe_identity: pathway {name!r} differs from {names[0]!r} "
                "(engine name, model or version)"
            )
        if kind == "ee" and len(ensemble.members) > 1:
            raise SelectivityInputError(
                f"kind='ee' is refused over multi-member ensembles: pathway {name!r} has "
                f"{len(ensemble.members)} members (DV-08)"
            )
    return names


def _softmax_fractions(free_energies: Sequence[float], rt: float) -> list[float]:
    """Return the shares ``exp(-G_p/RT) / sum`` (stable, order-free)."""
    lowest = min(free_energies)
    terms = [math.exp(-(g - lowest) / rt) for g in free_energies]
    total = math.fsum(terms)
    return [t / total for t in terms]


def score_selectivity(
    pathways: Mapping[str, TSEnsemble], *, kind: SelectivityKind, temperature_k: float
) -> SelectivityResult:
    """Score competing pathways from their TS ensembles.

    Args:
        pathways: Pathway label -> its TS ensemble; at least two, each with a summed member.
        kind: ``ee``, ``de`` or ``regio`` (a label; ``ee`` needs single-member pathways, DV-08).
        temperature_k: Temperature (K); every ensemble must have been summed at it.

    Returns:
        ddG-dagger (minor minus major, or second minus major for more than two pathways), the
        signed gaps keyed ``"<b>_vs_<a>"`` (``G_b - G_a``; two pathways: sorted-name order, more:
        each other pathway against the major), the ratio, the selectivity percent (two pathways:
        ``100 (r - 1)/(r + 1)``; more: the major's share), the major pathway and each pathway's
        free energy, counts and share. ``ratio`` is ``inf`` and the percent ``100.0`` if
        ``exp(ddG/RT)`` overflows a float.

    Raises:
        SelectivityInputError: Fewer than two pathways, a pathway with no summed member, mixed
            temperature, reactants or recipe identity, or ``kind="ee"`` over a multi-member
            ensemble.
    """
    names = _check_inputs(pathways, kind, temperature_k)
    rt = _rt_hartree(temperature_k)
    free_energy = {n: _pathway_free_energy_hartree(pathways[n], rt) for n in names}
    ranked = sorted(names, key=lambda n: (free_energy[n], n))
    major, second = ranked[0], ranked[1]
    ddg = (free_energy[second] - free_energy[major]) * HARTREE_KCAL_MOL
    x = (free_energy[second] - free_energy[major]) / rt
    try:
        ratio = math.exp(x)
    except OverflowError:
        ratio = math.inf
    shares = dict(zip(names, _softmax_fractions([free_energy[n] for n in names], rt), strict=True))
    if len(names) == 2:
        percent = 100.0 * math.tanh(x / 2.0)
        low, high = names
        signed = {f"{high}_vs_{low}": (free_energy[high] - free_energy[low]) * HARTREE_KCAL_MOL}
    else:
        percent = 100.0 * shares[major]
        signed = {
            f"{n}_vs_{major}": (free_energy[n] - free_energy[major]) * HARTREE_KCAL_MOL
            for n in names
            if n != major
        }
    return SelectivityResult(
        ddG_dagger_kcal_mol=ddg,
        signed_ddG_dagger_kcal_mol=signed,
        ratio=ratio,
        selectivity_percent=percent,
        kind=kind,
        major_pathway=major,
        temperature_k=temperature_k,
        per_pathway={
            n: PathwaySelectivity(
                G_pathway_hartree=free_energy[n],
                n_members=len(pathways[n].members),
                n_excluded=len(pathways[n].excluded),
                fraction=shares[n],
            )
            for n in names
        },
    )


# --- Per-pathway pruning (slice 07, mission R7, G2) ----------------------------------------------


def _signed_gap_kcal_mol(result: SelectivityResult, a: str, b: str) -> float:
    """Return ``G_b - G_a`` (kcal/mol): the scorer's own signed gap when it has one."""
    direct = result.signed_ddG_dagger_kcal_mol.get(f"{b}_vs_{a}")
    if direct is not None:
        return direct
    reverse = result.signed_ddG_dagger_kcal_mol.get(f"{a}_vs_{b}")
    if reverse is not None:
        return -reverse
    gap = result.per_pathway[b].G_pathway_hartree - result.per_pathway[a].G_pathway_hartree
    return gap * HARTREE_KCAL_MOL


def evaluate_pathway_pruning(
    rule: PathwayPruningRule,
    result: SelectivityResult | None,
    nodes: Sequence[ReactionNode],
    *,
    without_member: Collection[str] = (),
) -> PruningDecision:
    """Evaluate one ``PathwayPruningRule`` against a selectivity result (pure).

    The computed minor pathway is the one of ``rule.pathways`` with the larger free energy. If the
    gap exceeds ``rule.threshold_kcal_mol`` (strictly), the nodes with ``priority >= 2`` and
    ``pathway == minor`` are pruned; nothing at or below the threshold, and never a node whose
    ``pathway`` is ``None``. The caller's expectation of which pathway is minor plays no part.

    Args:
        rule: The rule (its threshold has no default).
        result: The score; ``None``, or a result without a summed member for one of the rule's
            pathways, prunes nothing and says why (``no_valid_member:<pathway>``).
        nodes: The graph's nodes.
        without_member: Pathways known to have no summed member (the runner passes the failed
            ones, so the reason names the right pathway).

    Returns:
        The decision: rule id, pathways, unsigned gap, ``"<b>_vs_<a>"`` signed gap in rule order,
        threshold, sorted pruned ids and the reason.
    """
    first, second = rule.pathways
    per_pathway = {} if result is None else result.per_pathway

    def has_member(name: str) -> bool:
        entry = per_pathway.get(name)
        return entry is not None and entry.n_members > 0 and name not in without_member

    if result is None or not (has_member(first) and has_member(second)):
        # name the pathway known to lack a member, else the first of the rule that the result misses
        known = [n for n in rule.pathways if n in without_member]
        name = known[0] if known else next((n for n in rule.pathways if not has_member(n)), first)
        return PruningDecision(
            rule_id=rule.id,
            pathways=rule.pathways,
            ddG_dagger_kcal_mol=None,
            signed_ddG_dagger_kcal_mol={},
            threshold_kcal_mol=rule.threshold_kcal_mol,
            pruned_node_ids=[],
            reason=f"no_valid_member:{name}",
        )
    assert result is not None
    signed = _signed_gap_kcal_mol(result, first, second)
    gap = abs(signed)
    minor = second if signed > 0 else first
    base = {
        "rule_id": rule.id,
        "pathways": rule.pathways,
        "ddG_dagger_kcal_mol": gap,
        "signed_ddG_dagger_kcal_mol": {f"{second}_vs_{first}": signed},
        "threshold_kcal_mol": rule.threshold_kcal_mol,
    }
    if gap > rule.threshold_kcal_mol:
        pruned = sorted(n.id for n in nodes if n.priority >= 2 and n.pathway == minor)
        return PruningDecision(
            **base,
            pruned_node_ids=pruned,
            reason=(
                f"ddG_dagger {gap:.6g} > threshold {rule.threshold_kcal_mol:.6g} kcal/mol: "
                f"pruned the {len(pruned)} priority>=2 node(s) of minor pathway {minor}"
            ),
        )
    return PruningDecision(
        **base,
        pruned_node_ids=[],
        reason=(
            f"ddG_dagger {gap:.6g} <= threshold {rule.threshold_kcal_mol:.6g} kcal/mol: "
            "nothing pruned"
        ),
    )


@dataclass(frozen=True)
class PathwayInputs:
    """What one priority-1 pathway needs to build its TS ensemble.

    Attributes:
        seed: The verified seed TS.
        recipe: The TS recipe (shared by the seed and every member).
        core_indices: Atoms that never move.
        reactant_key: Sorted ``(SMILES, count)`` pairs of the reactants.
        member_gates: The recipe's member gates.
    """

    seed: "TSSpec"
    recipe: "TSRecipe"
    core_indices: Sequence[int]
    reactant_key: Sequence[tuple[str, int]]
    member_gates: "MemberGates"


@dataclass(frozen=True)
class DownstreamNode:
    """How to run one priority >= 2 node through the species runner.

    Attributes:
        spec: The species.
        recipe: Engine, optimizer and thermochemistry settings.
    """

    spec: "SpeciesSpec"
    recipe: "Recipe"


@dataclass(frozen=True)
class NodeOutcome:
    """What happened to one priority >= 2 node.

    Attributes:
        node_id: The node.
        pathway: The node's pathway label, if any.
        status: ``computed`` (it ran through the species runner) or ``pruned`` (no engine call).
        pruned_by: Ids of the rules that pruned it (empty when computed).
        result: The species result when computed.
    """

    node_id: str
    pathway: str | None
    status: Literal["computed", "pruned"]
    pruned_by: tuple[str, ...] = ()
    result: "SpeciesResult | None" = None


@dataclass(frozen=True)
class SelectivityRun:
    """The outcome of ``run_selectivity``: what slice 10's candidate serialises.

    Attributes:
        ensembles: Each priority-1 pathway's TS ensemble run, by pathway label.
        score: The score over the pathways with a summed member (``None`` with fewer than two);
            with exactly one rule its decision is also ``score.pruning``.
        decisions: One decision per rule, in graph order.
        nodes: One outcome per priority >= 2 node, by node id.
    """

    ensembles: "dict[str, TSEnsembleRun]"
    score: SelectivityResult | None
    decisions: tuple[PruningDecision, ...]
    nodes: dict[str, NodeOutcome] = field(default_factory=dict)


def run_selectivity(
    graph: ReactionGraph,
    store: "ArtifactStore",
    *,
    pathways: Mapping[str, PathwayInputs],
    downstream: Mapping[str, DownstreamNode],
    optimizer: "Optimizer",
    options: TSEnsembleOptions,
    kind: SelectivityKind,
) -> SelectivityRun:
    """Run the competing pathways, score them, evaluate each pruning rule once, run the rest.

    Order (mission §5 "Selectivity", R7): every priority-1 pathway's TS ensemble (slice 06), then
    ``score_selectivity`` over the pathways that have a summed member (slice 04), then each
    ``PathwayPruningRule`` once, then every priority >= 2 node that no rule pruned through
    ``run_species``. A pruned node gets status ``pruned`` and no engine call. There is no scheduler
    and no resume here (v0.8.0). The inputs are explicit: v0.6.0 has no graph-to-TS loader.

    Args:
        graph: The reaction graph (nodes carry ``pathway``; rules in ``pathway_pruning_rules``).
        store: The artifact store.
        pathways: Per priority-1 pathway label, the ensemble inputs.
        downstream: Per priority >= 2 node id, how to run it (needed for every unpruned node).
        optimizer: The core-frozen minimizer for the ensembles' pre-relaxation.
        options: The keyed TS ensemble options.
        kind: The selectivity kind to report.

    Raises:
        SelectivityInputError: A priority-1 pathway has no inputs (or an input names no pathway),
            or an unpruned priority >= 2 node has no ``DownstreamNode``.
    """
    from eta_rxncat.orchestrator.species import run_species
    from eta_rxncat.orchestrator.ts_ensemble import run_ts_ensemble_detailed

    labels = sorted({n.pathway for n in graph.nodes if n.priority == 1 and n.pathway is not None})
    if sorted(pathways) != labels:
        raise SelectivityInputError(
            f"pathways: inputs for {sorted(pathways)} but the graph's priority-1 pathways "
            f"are {labels}"
        )
    runs = {
        label: run_ts_ensemble_detailed(
            pathways[label].seed,
            pathways[label].recipe,
            store,
            optimizer=optimizer,
            core_indices=pathways[label].core_indices,
            pathway=label,
            reactant_key=pathways[label].reactant_key,
            options=options,
            member_gates=pathways[label].member_gates,
        )
        for label in labels
    }
    valid = {
        label: run.ensemble
        for label, run in runs.items()
        if run.ensemble.failed_reason is None and run.ensemble.members
    }
    score: SelectivityResult | None = None
    if len(valid) >= 2:
        temperature_k = next(iter(valid.values())).temperature_k
        score = score_selectivity(valid, kind=kind, temperature_k=temperature_k)
    failed = sorted(set(labels) - set(valid))
    decisions = tuple(
        evaluate_pathway_pruning(rule, score, graph.nodes, without_member=failed)
        for rule in graph.pathway_pruning_rules
    )
    if score is not None and len(decisions) == 1:
        score = score.model_copy(update={"pruning": decisions[0]})
    pruned_by: dict[str, list[str]] = {}
    for decision in decisions:
        for node_id in decision.pruned_node_ids:
            pruned_by.setdefault(node_id, []).append(decision.rule_id)
    outcomes: dict[str, NodeOutcome] = {}
    later = sorted((n for n in graph.nodes if n.priority >= 2), key=lambda n: (n.priority, n.id))
    for node in later:
        if node.id in pruned_by:
            outcomes[node.id] = NodeOutcome(
                node.id, node.pathway, "pruned", pruned_by=tuple(pruned_by[node.id])
            )
            continue
        inputs = downstream.get(node.id)
        if inputs is None:
            raise SelectivityInputError(
                f"downstream: node {node.id!r} is not pruned and has no inputs"
            )
        outcomes[node.id] = NodeOutcome(
            node.id,
            node.pathway,
            "computed",
            result=run_species(inputs.spec, inputs.recipe, store),
        )
    return SelectivityRun(ensembles=runs, score=score, decisions=decisions, nodes=outcomes)
