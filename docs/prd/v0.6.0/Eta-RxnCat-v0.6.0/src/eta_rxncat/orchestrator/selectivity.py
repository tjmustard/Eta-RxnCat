"""Boltzmann-weighted selectivity (% ee / d.r.) and priority-gate pruning evaluator."""

from __future__ import annotations

import math

from eta_rxncat.core.reaction_graph import PruningRule

HARTREE_TO_KCAL_MOL = 627.5094740631
R_KCAL_MOL_K = 0.00198720425864083


def compute_selectivity_from_ts_pair(
    g_major_hartree: float,
    g_minor_hartree: float,
    temperature_k: float = 298.15,
) -> tuple[float, float, float]:
    """Return (ddG_dagger_kcal, major_minor_ratio, ee_percent) from two competing TS Gibbs energies."""
    ddg_kcal = (g_minor_hartree - g_major_hartree) * HARTREE_TO_KCAL_MOL
    rt = R_KCAL_MOL_K * temperature_k
    ratio = math.exp(min(ddg_kcal / rt, 500.0))
    ee_percent = 100.0 * (ratio - 1.0) / (ratio + 1.0)
    return ddg_kcal, ratio, ee_percent


def evaluate_pruning_rules(
    rules: list[PruningRule],
    node_gibbs_hartree: dict[str, float],
    temperature_k: float = 298.15,
    computed_tof_s_inv: float | None = None,
) -> tuple[bool, list[str]]:
    """Evaluate priority-gate rules; returns (should_skip_remaining, triggered_messages)."""
    skip = False
    messages: list[str] = []

    for rule in rules:
        if rule.reference_node_id not in node_gibbs_hartree:
            continue
        if rule.target_node_id is not None and rule.target_node_id not in node_gibbs_hartree:
            continue

        val: float
        if rule.metric == "delta_g_dagger_kcal":
            assert rule.target_node_id is not None
            val = (
                node_gibbs_hartree[rule.target_node_id] - node_gibbs_hartree[rule.reference_node_id]
            ) * HARTREE_TO_KCAL_MOL
        elif rule.metric == "delta_delta_g_dagger_kcal":
            assert rule.target_node_id is not None
            val, _, _ = compute_selectivity_from_ts_pair(
                node_gibbs_hartree[rule.reference_node_id],
                node_gibbs_hartree[rule.target_node_id],
                temperature_k=temperature_k,
            )
        elif rule.metric == "ee_percent":
            assert rule.target_node_id is not None
            _, _, val = compute_selectivity_from_ts_pair(
                node_gibbs_hartree[rule.reference_node_id],
                node_gibbs_hartree[rule.target_node_id],
                temperature_k=temperature_k,
            )
        elif rule.metric == "tof_s_inv":
            if computed_tof_s_inv is None:
                continue
            val = computed_tof_s_inv
        else:
            continue

        passed = (
            (rule.operator == "lt" and val < rule.threshold)
            or (rule.operator == "le" and val <= rule.threshold)
            or (rule.operator == "gt" and val > rule.threshold)
            or (rule.operator == "ge" and val >= rule.threshold)
        )
        if not passed:
            msg = (
                f"Rule '{rule.rule_id}' failed: {rule.metric}={val:.2f} "
                f"did not satisfy {rule.operator} {rule.threshold:.2f}."
            )
            messages.append(msg)
            if rule.on_fail == "skip_remaining_nodes":
                skip = True

    return skip, messages
