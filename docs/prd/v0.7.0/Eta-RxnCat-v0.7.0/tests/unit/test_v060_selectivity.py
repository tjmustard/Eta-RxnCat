"""Unit tests for v0.6.0 selectivity calculations and priority-gate pruning rules."""

import pytest

from eta_rxncat.core.reaction_graph import PruningRule
from eta_rxncat.orchestrator.selectivity import (
    HARTREE_TO_KCAL_MOL,
    compute_selectivity_from_ts_pair,
    evaluate_pruning_rules,
)


def test_selectivity_ee_calculation() -> None:
    g_major = -100.0
    # 1.7 kcal/mol difference at 298.15 K gives ~89% ee (matches FLP paper benchmark)
    g_minor = g_major + (1.7 / HARTREE_TO_KCAL_MOL)
    ddg, ratio, ee = compute_selectivity_from_ts_pair(g_major, g_minor, temperature_k=298.15)
    assert ddg == pytest.approx(1.7, abs=1e-4)
    assert ratio > 15.0
    assert ee == pytest.approx(89.2, abs=0.5)


def test_pruning_rule_skips_remaining_nodes_on_low_ee() -> None:
    rule = PruningRule(
        rule_id="min_ee_80",
        metric="ee_percent",
        reference_node_id="ts_r",
        target_node_id="ts_s",
        operator="ge",
        threshold=80.0,
        on_fail="skip_remaining_nodes",
    )
    g_r = -100.0
    g_s = g_r + (0.4 / HARTREE_TO_KCAL_MOL)
    skip, msgs = evaluate_pruning_rules([rule], {"ts_r": g_r, "ts_s": g_s})
    assert skip is True
    assert len(msgs) == 1
