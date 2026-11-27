"""TS seed fallback over an enumerated candidate's ranked templates (v0.7.0, slice 05).

Mission G6, R2-R7, R32. For one TS node of an ``ok`` candidate the eligible templates are tried in
rank order: a guarded, cached pre-relaxation, the pathway-face check, then the TS ensemble. Only a
seed that fails TS validation (the R4 allow-list) falls through to the next template; every other
reason stops the node, and a live ``EngineError`` propagates. This module writes no cache rows of
its own, so a rerun re-derives the same ``FallbackRecord`` from the cached rows.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from rdkit import Chem
from rdkit.Chem import rdDetermineBonds

from eta_rxncat.conformers import FaceDescriptorError, forming_bond_configuration
from eta_rxncat.core import (
    EnumeratedCandidate,
    FallbackAttempt,
    FallbackRecord,
    GraftRecord,
    MolecularState,
    PathwaySpec,
    ReactionGraph,
    ReactionNode,
    SeedCheckDetail,
    TemplateGeometry,
    TSEnsembleOptions,
)
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.enumerator import EnumerationError, map_template_indices
from eta_rxncat.optimize import Optimizer
from eta_rxncat.optimize.errors import TSSearchFailureReason
from eta_rxncat.orchestrator._deadline import PreRelaxTimeout
from eta_rxncat.orchestrator.selectivity import PathwayInputs
from eta_rxncat.orchestrator.ts import TSRecipe, TSSpec, _sorted_pairs
from eta_rxncat.orchestrator.ts_ensemble import (
    MemberGates,
    TSEnsembleRun,
    _PreRelax,
    bond_changes,
    run_ts_ensemble_detailed,
)
from eta_rxncat.store import ArtifactStore

FALLBACK_MAX_PRE_RELAX_TIMEOUTS = 2
"""The stall cap of the fallback's ensembles (mission R6)."""

FALL_THROUGH_TS_SEARCH: frozenset[TSSearchFailureReason] = frozenset(
    {"max_steps", "too_many_rejections", "mode_lost", "no_reaction_mode"}
)
"""TS-search failures that are the template's fault (mission R4)."""

STOP_TS_SEARCH: frozenset[TSSearchFailureReason] = frozenset({"wall_time_exceeded"})
"""TS-search failures that are not: a time fault stops the node (mission R4)."""

_FALL_THROUGH_REASONS = frozenset(
    {f"seed:ts_search_failed:{r}" for r in FALL_THROUGH_TS_SEARCH}
    | {"seed:ts_validation_failed", "seed:face_undetermined", "seed:face_mismatch_pathway"}
    | {"seed:seed_clash", "seed:bond_changed:pre_relax", "seed:bond_changed:ts"}
)
_GATE_PREFIX = "seed:gate_failed:"


class FallbackInputError(ValueError):
    """The candidate, node or template cannot be run; raised before any engine call."""


def falls_through(reason: str) -> bool:
    """Whether ``reason`` is on the R4 allow-list (the next template may be tried)."""
    if reason.startswith(_GATE_PREFIX):
        return len(reason) > len(_GATE_PREFIX)
    return reason in _FALL_THROUGH_REASONS


def _graph_node(candidate: EnumeratedCandidate, node_id: str) -> tuple[ReactionGraph, ReactionNode]:
    if candidate.status != "ok" or candidate.graph is None:
        raise FallbackInputError(
            f"candidate '{candidate.candidate_id}' is {candidate.status!r}, not 'ok': "
            f"{candidate.detail}"
        )
    for node in candidate.graph.nodes:
        if node.id == node_id:
            return candidate.graph, node
    raise FallbackInputError(f"candidate '{candidate.candidate_id}' has no node '{node_id}'")


def _check_neutral_closed_shell(graph: ReactionGraph) -> None:
    """Refuse any charged or open-shell species in the candidate (mission R5)."""
    for node in graph.nodes:
        for template in node.templates:
            for component in template.components:
                state = component.state
                if state.charge != 0 or state.spin_multiplicity != 1:
                    raise FallbackInputError(
                        f"charged_run_not_supported_v070: node '{node.id}', template "
                        f"'{template.id}' has charge {state.charge}, multiplicity "
                        f"{state.spin_multiplicity}"
                    )


def _check_competing_ts(graph: ReactionGraph, node: ReactionNode) -> None:
    """Refuse competing TS nodes whose rank-1 templates differ (mission G3, R3).

    The candidate carries no selectivity sets, so the competitors of ``node`` are the
    transition-state nodes of its priority.
    """

    def signature(template: TemplateGeometry) -> tuple[Counter[str], int, list[int]]:
        multiplicities = sorted(
            c.state.spin_multiplicity for c in template.components for _ in range(c.count)
        )
        return template.element_counts, template.total_charge, multiplicities

    competitors = [
        n for n in graph.nodes if n.kind == "transition_state" and n.priority == node.priority
    ]
    mine = signature(min(node.templates, key=lambda t: t.rank))
    for other in competitors:
        if signature(min(other.templates, key=lambda t: t.rank)) != mine:
            raise FallbackInputError(
                f"competing TS nodes '{node.id}' and '{other.id}' differ in composition, "
                "charge or multiplicity"
            )


def _canonical_smiles(state: MolecularState, node_id: str) -> str:
    """Return the canonical SMILES that RDKit ``DetermineBonds`` perceives for ``state``."""
    lines = [str(len(state.symbols)), ""]
    lines += [
        f"{s} {x:.10f} {y:.10f} {z:.10f}"
        for s, (x, y, z) in zip(state.symbols, state.coordinates, strict=True)
    ]
    molecule = Chem.MolFromXYZBlock("\n".join(lines) + "\n")
    if molecule is None:
        raise FallbackInputError(f"reactant node '{node_id}': RDKit cannot read the geometry")
    try:
        rdDetermineBonds.DetermineBonds(molecule, charge=state.charge)
        return str(Chem.MolToSmiles(Chem.RemoveHs(molecule)))
    except ValueError as exc:
        raise FallbackInputError(
            f"reactant node '{node_id}': bonds cannot be determined: {exc}"
        ) from exc


def _reactant_key(graph: ReactionGraph) -> tuple[tuple[str, int], ...]:
    """Sorted ``(SMILES, count)`` over every reactant node's rank-1 template (mission R3)."""
    counts: Counter[str] = Counter()
    for node in graph.nodes:
        if node.kind != "reactant":
            continue
        for component in min(node.templates, key=lambda t: t.rank).components:
            counts[_canonical_smiles(component.state, node.id)] += component.count
    if not counts:
        raise FallbackInputError(f"graph '{graph.name}' has no reactant node")
    return tuple(sorted(counts.items()))


def _compose_seed(
    records: Sequence[GraftRecord], node_id: str, ref: str
) -> tuple[list[tuple[int, int]], list[int]]:
    """Return the forming bonds and active core of the final product (mission R32).

    Record ``k``'s indices are in its own product space; each is carried into the last product
    through the later records. One record is returned verbatim.
    """

    def carry(k: int, index: int) -> int:
        for later in records[k + 1 :]:
            try:
                (index,) = map_template_indices(later, [index])
            except EnumerationError as exc:
                raise FallbackInputError(
                    f"multi_site_seed_atom_deleted: node '{node_id}', template '{ref}': atom "
                    f"{index} of site '{records[k].site_id}' is deleted by site "
                    f"'{later.site_id}'"
                ) from exc
        return index

    pairs: list[tuple[int, int]] = []
    core: list[int] = []
    for k, record in enumerate(records):
        bonds = record.mapped_forming_bonds
        record_core = record.constrained_core_product_indices
        if bonds is None or record_core is None:
            raise FallbackInputError(
                f"node '{node_id}', template '{ref}': the record of site '{record.site_id}' has "
                "no mapped forming bonds or core"
            )
        pairs.extend((carry(k, i), carry(k, j)) for i, j in bonds)
        core.extend(carry(k, i) for i in record_core)
    if len(records) == 1:
        return pairs, core
    unique: list[tuple[int, int]] = []
    seen: set[frozenset[int]] = set()
    for pair in pairs:
        if frozenset(pair) not in seen:
            seen.add(frozenset(pair))
            unique.append(pair)
    return unique, sorted(set(core))


def enumerated_pathway_inputs(
    candidate: EnumeratedCandidate,
    node_id: str,
    template_id: str,
    recipe: TSRecipe,
    member_gates: MemberGates,
) -> PathwayInputs:
    """Build one template's TS ensemble inputs from an enumerated candidate.

    Args:
        candidate: An ``ok`` candidate.
        node_id: The transition-state node.
        template_id: One of the node's templates (``<reference id>__<candidate id>``).
        recipe: The TS recipe.
        member_gates: The recipe's member gates.

    Returns:
        The seed TS (the grafted template with the composed forming bonds and active core), the
        core, and the ``reactant_key`` derived from the candidate's reactant nodes.

    Raises:
        FallbackInputError: The candidate is not ``ok``; the node or template is unknown or has no
            ``ok`` graft record; a species is charged or open-shell
            (``charged_run_not_supported_v070``); the competing TS templates differ; a reactant's
            bonds cannot be determined; or a later site deleted a seed atom
            (``multi_site_seed_atom_deleted``).
    """
    graph, node = _graph_node(candidate, node_id)
    _check_neutral_closed_shell(graph)
    _check_competing_ts(graph, node)
    template = next((t for t in node.templates if t.id == template_id), None)
    if template is None:
        raise FallbackInputError(f"node '{node_id}' has no template '{template_id}'")
    if len(template.components) != 1 or template.components[0].count != 1:
        raise FallbackInputError(f"template '{template_id}' is not a single species")
    suffix = f"__{candidate.candidate_id}"
    if not template_id.endswith(suffix):
        raise FallbackInputError(f"template '{template_id}' does not end in '{suffix}'")
    ref = template_id.removesuffix(suffix)
    records = [
        r
        for r in candidate.records
        if r.status == "ok" and r.node_id == node_id and r.template_id == ref
    ]
    if not records:
        raise FallbackInputError(f"node '{node_id}': no ok graft record of template '{ref}'")
    pairs, core = _compose_seed(records, node_id, ref)
    start = MolecularState.model_validate(
        {**template.components[0].state.model_dump(), "active_atom_indices": core}
    )
    return PathwayInputs(
        seed=TSSpec(ts_id=template_id, start=start, forming_bonds=tuple(pairs)),
        recipe=recipe,
        core_indices=core,
        reactant_key=_reactant_key(graph),
        member_gates=member_gates,
    )


def run_ts_with_fallback(
    candidate: EnumeratedCandidate,
    node_id: str,
    pathway: PathwaySpec,
    recipe: TSRecipe,
    store: ArtifactStore,
    *,
    optimizer: Optimizer,
    options: TSEnsembleOptions,
    member_gates: MemberGates,
    orientation_centers: Sequence[int] = (),
) -> tuple[FallbackRecord, TSEnsembleRun | None]:
    """Try a node's templates in rank order until one seeds a TS ensemble.

    Per template: a graft record with close contacts is ``seed:seed_clash`` with no engine call;
    then the cached core-frozen pre-relaxation (a timeout stops the node with
    ``graft_pre_relax_timeout``); a bond made or broken by it outside the forming bonds is
    ``seed:bond_changed:pre_relax``; the pre-relaxed start's face against the pathway's; then the
    ensemble, with the stall cap and ``seed_checks`` on. A reason on the R4 allow-list falls
    through to the next template; every other reason stops the node (``stopped:<reason>``). An
    attempt's ``wall_time_s`` is the sum of its pre-relaxation wall times as stored in the cache,
    so a rerun gives the same record.

    Args:
        candidate: An ``ok`` candidate.
        node_id: The transition-state node.
        pathway: The pathway (its node must be ``node_id``) with its expected face.
        recipe: The TS recipe.
        store: The artifact store.
        optimizer: The core-frozen minimizer.
        options: The keyed TS ensemble options.
        member_gates: The recipe's member gates.
        orientation_centers: Product indices whose orientation every member must keep (R24).

    Returns:
        The record, and the chosen template's ensemble run (``None`` if the node stopped or every
        template fell through, ``all_templates_failed``).

    Raises:
        FallbackInputError: As ``enumerated_pathway_inputs``, for any eligible template, before
            the first engine call; or the pathway names another node.
        eta_rxncat.engines.EngineError: A live engine error propagates unchanged.
    """
    if pathway.node_id != node_id:
        raise FallbackInputError(
            f"pathway '{pathway.pathway}' is on node '{pathway.node_id}', not '{node_id}'"
        )
    _, node = _graph_node(candidate, node_id)
    ranked = sorted(node.templates, key=lambda t: t.rank)
    derived = [
        (t, enumerated_pathway_inputs(candidate, node_id, t.id, recipe, member_gates))
        for t in ranked
    ]
    attempts: list[FallbackAttempt] = []

    def stopped(reason: str) -> tuple[FallbackRecord, None]:
        record = FallbackRecord(node_id=node_id, attempts=attempts, stop_reason=f"stopped:{reason}")
        return record, None

    for template, inputs in derived:

        def note(
            outcome: str,
            reason: str | None,
            wall: float,
            detail: SeedCheckDetail | None = None,
        ) -> None:
            attempts.append(
                FallbackAttempt.model_validate(
                    {
                        "template_id": template.id,
                        "rank": template.rank,
                        "outcome": outcome,
                        "reason": reason,
                        "wall_time_s": wall,
                        "detail": detail,
                    }
                )
            )

        ref = template.id.removesuffix(f"__{candidate.candidate_id}")
        contacts = sum(
            r.close_contact_count or 0
            for r in candidate.records
            if r.status == "ok" and r.node_id == node_id and r.template_id == ref
        )
        if contacts > 0:
            clash = SeedCheckDetail(check="clash", close_contact_count=contacts)
            note("fell_through", "seed:seed_clash", 0.0, clash)
            continue
        pre_relax = _PreRelax(recipe, store, optimizer, inputs.core_indices)
        relaxed, reason, wall = pre_relax.run(inputs.seed.start)
        seed_pre_relax_key = pre_relax.last_key
        if relaxed is None:
            if reason == f"pre_relax_failed:{PreRelaxTimeout.__name__}":
                reason = "graft_pre_relax_timeout"
            if falls_through(str(reason)):
                note("fell_through", reason, wall)
                continue
            note("stopped", reason, wall)
            return stopped(str(reason))
        start = MolecularState.model_validate(
            {**relaxed.model_dump(), "active_atom_indices": list(inputs.core_indices)}
        )
        pairs = _sorted_pairs(inputs.seed.forming_bonds)
        changed = bond_changes(start, perceive_bonds(inputs.seed.start), pairs)
        if changed is not None:
            note("fell_through", "seed:bond_changed:pre_relax", wall, changed)
            continue
        try:
            face = forming_bond_configuration(start, pairs, perceive_bonds(start))
        except FaceDescriptorError:
            note("fell_through", "seed:face_undetermined", wall)
            continue
        if face != pathway.expected_face:
            note("fell_through", "seed:face_mismatch_pathway", wall)
            continue
        run = run_ts_ensemble_detailed(
            TSSpec(ts_id=inputs.seed.ts_id, start=start, forming_bonds=inputs.seed.forming_bonds),
            recipe,
            store,
            optimizer=optimizer,
            core_indices=inputs.core_indices,
            pathway=pathway.pathway,
            reactant_key=inputs.reactant_key,
            options=options,
            member_gates=member_gates,
            expected_face=pathway.expected_face,
            max_pre_relax_timeouts=FALLBACK_MAX_PRE_RELAX_TIMEOUTS,
            orientation_centers=orientation_centers,
            seed_checks=True,
        )
        wall += run.total_pre_relax_wall_time_s
        failed = run.ensemble.failed_reason
        if failed is None and run.ensemble.members:
            note("chosen", None, wall)
            record = FallbackRecord(
                node_id=node_id, attempts=attempts, chosen_template_id=template.id
            )
            seed_keys = replace(run.samples[0], pre_relax_key=seed_pre_relax_key)
            return record, replace(run, samples=(seed_keys, *run.samples[1:]))
        reason = failed or "no_member"
        if falls_through(reason):
            note("fell_through", reason, wall, run.ensemble.failed_detail)
            continue
        note("stopped", reason, wall)
        return stopped(reason)
    return (
        FallbackRecord(node_id=node_id, attempts=attempts, stop_reason="all_templates_failed"),
        None,
    )


__all__ = [
    "FALLBACK_MAX_PRE_RELAX_TIMEOUTS",
    "FALL_THROUGH_TS_SEARCH",
    "STOP_TS_SEARCH",
    "FallbackInputError",
    "enumerated_pathway_inputs",
    "falls_through",
    "run_ts_with_fallback",
]
