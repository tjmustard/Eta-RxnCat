"""Tests for the pure selectivity scorer (v0.6.0, slice 04): G1 closed forms, refusals and G8."""

import math
import subprocess
import sys
from decimal import Decimal, getcontext
from typing import Any

import pytest

from eta_rxncat.core import TSEnsemble
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import SelectivityInputError, score_selectivity
from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS

getcontext().prec = 60
SHA = "b" * 64
T = 298.15
G0 = -1.234567891  # small magnitude: ulp(G) * 627.5 stays below the 1e-12 kcal/mol tolerance


def rt_hartree(temperature_k: float = T) -> float:
    """Return RT in Eh from the project constants (the same ones the scorer must use)."""
    return R_GAS * temperature_k * J_PER_MOL_TO_HARTREE


def member(index: int, g_hartree: float, degeneracy: int = 1, n: int = 1) -> dict[str, Any]:
    """Return a member dict; weights are equal (the scorer sums energies, not stored weights)."""
    return {
        "index": index,
        "source": "seed" if index == 0 else f"perturb:{index}",
        "start_sha256": SHA,
        "G_hartree": g_hartree,
        "degeneracy": degeneracy,
        "rmsd_to_seed_angstrom": 0.0,
        "face": [1],
        "validation_passed_bool": True,
        "weight": 1.0 / n,
    }


def ensemble(
    pathway: str,
    energies: list[float],
    *,
    degeneracies: list[int] | None = None,
    temperature_k: float = T,
    **overrides: Any,
) -> TSEnsemble:
    """Return a valid ensemble of the given member energies."""
    degs = degeneracies or [1] * len(energies)
    members = [member(i, g, d, len(energies)) for i, (g, d) in enumerate(zip(energies, degs))]
    data: dict[str, Any] = {
        "pathway": pathway,
        "temperature_k": temperature_k,
        "reactant_key": [["C=CC=C", 1], ["C=CC=O", 1]],
        "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
        "members": members,
    }
    data.update(overrides)
    return TSEnsemble.model_validate(data)


def two(ga: float, gb: float, **kw: Any) -> dict[str, TSEnsemble]:
    """Return pathways ``a`` and ``b`` of one member each."""
    return {"a": ensemble("a", [ga], **kw), "b": ensemble("b", [gb], **kw)}


def reference_g(
    energies: list[float], degeneracies: list[int], temperature_k: float = T
) -> Decimal:
    """Return ``-RT ln sum g exp(-G/RT)`` (Eh) in 60-digit decimal arithmetic."""
    rt = Decimal(rt_hartree(temperature_k))
    total = sum(
        (Decimal(d) * (-Decimal(g) / rt).exp() for g, d in zip(energies, degeneracies)),
        Decimal(0),
    )
    return -rt * total.ln()


def gap(ddg_kcal: float, ga: float = G0) -> float:
    """Return the energy (Eh) that is ``ddg_kcal`` above ``ga``."""
    return ga + ddg_kcal / HARTREE_KCAL_MOL


# --- G1: closed forms ---------------------------------------------------------------------------


def test_two_single_member_pathways_closed_form() -> None:
    """ddG, ratio and percent equal the closed forms within 1e-12."""
    ga, gb = G0, gap(1.7)
    result = score_selectivity(two(ga, gb), kind="de", temperature_k=T)
    ddg = (Decimal(gb) - Decimal(ga)) * Decimal(HARTREE_KCAL_MOL)
    x = (Decimal(gb) - Decimal(ga)) / Decimal(rt_hartree())
    ratio = x.exp()
    assert result.major_pathway == "a"
    assert abs(Decimal(result.ddG_dagger_kcal_mol) - ddg) < Decimal("1e-12")
    assert abs(Decimal(result.ratio) / ratio - 1) < Decimal("1e-12")
    assert abs(Decimal(result.selectivity_percent) - 100 * (ratio - 1) / (ratio + 1)) < Decimal(
        "1e-12"
    )
    assert result.signed_ddG_dagger_kcal_mol == {"b_vs_a": pytest.approx(float(ddg), abs=1e-12)}
    assert result.kind == "de" and result.temperature_k == T
    assert result.pruning is None


@pytest.mark.parametrize(
    ("ddg", "percent", "tol"),
    [(1.7, 89.2, 0.5), (1.849, 91.5, 0.05), (4.273, 99.85, 0.05)],
)
def test_literature_checks(ddg: float, percent: float, tol: float) -> None:
    """The starter's check and the red team's two checks."""
    result = score_selectivity(two(G0, gap(ddg)), kind="de", temperature_k=T)
    assert result.selectivity_percent == pytest.approx(percent, abs=tol)


def test_multi_member_pathways_and_degeneracy() -> None:
    """Boltzmann sums over members, with the degeneracy in the sum (G_i - RT ln g_i)."""
    a = [G0, gap(0.4), gap(1.1)]
    b = [gap(0.9), gap(1.3)]
    degs_a, degs_b = [1, 2, 1], [1, 3]
    pathways = {
        "a": ensemble("a", a, degeneracies=degs_a),
        "b": ensemble("b", b, degeneracies=degs_b),
    }
    result = score_selectivity(pathways, kind="de", temperature_k=T)
    ga, gb = reference_g(a, degs_a), reference_g(b, degs_b)
    assert abs(Decimal(result.per_pathway["a"].G_pathway_hartree) - ga) < Decimal("1e-12")
    assert abs(Decimal(result.per_pathway["b"].G_pathway_hartree) - gb) < Decimal("1e-12")
    assert abs(Decimal(result.ddG_dagger_kcal_mol) - abs(gb - ga) * Decimal(HARTREE_KCAL_MOL)) < (
        Decimal("1e-12")
    )
    assert result.per_pathway["a"].n_members == 3 and result.per_pathway["b"].n_members == 2


def test_degeneracy_two_is_g_minus_rt_ln_two() -> None:
    """One member with g = 2 lowers its pathway by RT ln 2."""
    base = score_selectivity(two(G0, G0), kind="de", temperature_k=T)
    assert base.ddG_dagger_kcal_mol == 0.0
    pathways = {
        "a": ensemble("a", [G0], degeneracies=[2]),
        "b": ensemble("b", [G0]),
    }
    result = score_selectivity(pathways, kind="de", temperature_k=T)
    assert result.major_pathway == "a"
    expected = rt_hartree() * math.log(2.0) * HARTREE_KCAL_MOL
    assert result.ddG_dagger_kcal_mol == pytest.approx(expected, abs=1e-12)
    assert result.per_pathway["a"].G_pathway_hartree == pytest.approx(
        G0 - rt_hartree() * math.log(2.0), abs=1e-12
    )


def test_tie_is_fifty_fifty() -> None:
    """Equal pathways: ddG 0, ratio 1, selectivity 0 %, shares 0.5; the first name is the major."""
    result = score_selectivity(two(G0, G0), kind="de", temperature_k=T)
    assert result.ddG_dagger_kcal_mol == 0.0
    assert result.ratio == 1.0
    assert result.selectivity_percent == 0.0
    assert result.major_pathway == "a"
    assert result.per_pathway["a"].fraction == pytest.approx(0.5, abs=1e-15)
    assert result.per_pathway["b"].fraction == pytest.approx(0.5, abs=1e-15)


def test_large_gap_does_not_overflow_or_clamp() -> None:
    """DdG = 200 kcal/mol: the ratio is exp(ddG/RT) (about 1e146), the percent exactly 100."""
    ga, gb = G0, gap(200.0)
    result = score_selectivity(two(ga, gb), kind="de", temperature_k=T)
    x = (Decimal(gb) - Decimal(ga)) / Decimal(rt_hartree())
    assert math.isfinite(result.ratio) and result.ratio > 1e140
    assert abs(Decimal(result.ratio) / x.exp() - 1) < Decimal("1e-9")
    assert result.selectivity_percent == 100.0
    assert abs(result.ddG_dagger_kcal_mol - 200.0) < 1e-9


def test_overflowing_ratio_is_inf_and_percent_exactly_100() -> None:
    """If exp(ddG/RT) overflows a float: ratio inf and percent 100.0 exactly."""
    result = score_selectivity(two(G0, gap(1000.0)), kind="de", temperature_k=T)
    assert result.ratio == math.inf
    assert result.selectivity_percent == 100.0


def test_temperature_350() -> None:
    """At 350 K the same gap is less selective, by the closed form."""
    pathways = two(G0, gap(1.7), temperature_k=350.0)
    result = score_selectivity(pathways, kind="de", temperature_k=350.0)
    x = (Decimal(gap(1.7)) - Decimal(G0)) / Decimal(rt_hartree(350.0))
    expected = 100 * (x.exp() - 1) / (x.exp() + 1)
    assert abs(Decimal(result.selectivity_percent) - expected) < Decimal("1e-12")
    cold = score_selectivity(two(G0, gap(1.7)), kind="de", temperature_k=T)
    assert result.selectivity_percent < cold.selectivity_percent


def test_permutation_invariance_is_exact() -> None:
    """Pathway order and member order change nothing, bit for bit."""
    a = [G0, gap(0.4), gap(1.1), gap(0.05)]
    b = [gap(0.9), gap(1.3), gap(0.2)]
    forward = {"a": ensemble("a", a), "b": ensemble("b", b)}
    backward = {"b": ensemble("b", b[::-1]), "a": ensemble("a", [a[2], a[0], a[3], a[1]])}
    assert score_selectivity(forward, kind="de", temperature_k=T) == score_selectivity(
        backward, kind="de", temperature_k=T
    )


def test_three_pathways() -> None:
    """More than two: shares are a softmax, ddG is second minus major, percent the major's share."""
    energies = {"a": G0, "b": gap(0.8), "c": gap(2.5)}
    pathways = {n: ensemble(n, [g]) for n, g in energies.items()}
    result = score_selectivity(pathways, kind="regio", temperature_k=T)
    rt = Decimal(rt_hartree())
    weights = {n: (-(Decimal(g) - Decimal(G0)) / rt).exp() for n, g in energies.items()}
    total = sum(weights.values(), Decimal(0))
    assert result.major_pathway == "a"
    assert abs(Decimal(result.selectivity_percent) - 100 * weights["a"] / total) < Decimal("1e-12")
    for name, weight in weights.items():
        assert abs(Decimal(result.per_pathway[name].fraction) - weight / total) < Decimal("1e-12")
    assert result.ddG_dagger_kcal_mol == pytest.approx(0.8, abs=1e-9)
    assert set(result.signed_ddG_dagger_kcal_mol) == {"b_vs_a", "c_vs_a"}
    assert result.signed_ddG_dagger_kcal_mol["c_vs_a"] == pytest.approx(2.5, abs=1e-9)


def test_major_follows_the_computed_free_energy_not_the_name() -> None:
    """When ``b`` is lower, it is the major and the signed gap ``b_vs_a`` is negative."""
    result = score_selectivity(two(gap(1.0), G0), kind="de", temperature_k=T)
    assert result.major_pathway == "b"
    assert result.ddG_dagger_kcal_mol == pytest.approx(1.0, abs=1e-9)
    assert result.signed_ddG_dagger_kcal_mol["b_vs_a"] == pytest.approx(-1.0, abs=1e-9)


def test_ee_is_allowed_for_single_member_pathways() -> None:
    """kind='ee' over one-member pathways is accepted."""
    assert score_selectivity(two(G0, gap(1.0)), kind="ee", temperature_k=T).kind == "ee"


def test_counts_record_exclusions() -> None:
    """``n_excluded`` counts the ensemble's excluded samples."""
    excluded = [{"index": 5, "source": "perturb:5", "reason": "outside_window"}]
    pathways = {
        "a": ensemble("a", [G0], excluded=excluded),
        "b": ensemble("b", [gap(1.0)]),
    }
    result = score_selectivity(pathways, kind="de", temperature_k=T)
    assert result.per_pathway["a"].n_excluded == 1
    assert result.per_pathway["b"].n_excluded == 0


# --- Refusals name the offending field ----------------------------------------------------------


def test_fewer_than_two_pathways() -> None:
    """One pathway, or none, is refused."""
    with pytest.raises(SelectivityInputError, match="pathways"):
        score_selectivity({"a": ensemble("a", [G0])}, kind="de", temperature_k=T)
    with pytest.raises(SelectivityInputError, match="pathways"):
        score_selectivity({}, kind="de", temperature_k=T)


def test_pathway_without_a_summed_member() -> None:
    """A failed or empty pathway is refused, naming it."""
    failed = ensemble("b", [], failed_reason="no_valid_member")
    with pytest.raises(SelectivityInputError, match="pathway 'b'.*no_valid_member"):
        score_selectivity({"a": ensemble("a", [G0]), "b": failed}, kind="de", temperature_k=T)
    empty = ensemble("b", [])
    with pytest.raises(SelectivityInputError, match="pathway 'b'.*no summed member"):
        score_selectivity({"a": ensemble("a", [G0]), "b": empty}, kind="de", temperature_k=T)


def test_mixed_and_mismatched_temperatures() -> None:
    """Ensembles summed at different temperatures, or not at the call's, are refused."""
    mixed = {"a": ensemble("a", [G0]), "b": ensemble("b", [G0], temperature_k=350.0)}
    with pytest.raises(SelectivityInputError, match="temperature_k"):
        score_selectivity(mixed, kind="de", temperature_k=T)
    with pytest.raises(SelectivityInputError, match="temperature_k"):
        score_selectivity(two(G0, G0), kind="de", temperature_k=350.0)


@pytest.mark.parametrize("temperature_k", [0.0, -1.0, math.inf, math.nan])
def test_bad_call_temperature(temperature_k: float) -> None:
    """A non-positive or non-finite temperature is refused."""
    with pytest.raises(SelectivityInputError, match="temperature_k"):
        score_selectivity(two(G0, G0), kind="de", temperature_k=temperature_k)


def test_mixed_reactant_sets() -> None:
    """Pathways of different reactants are not comparable."""
    other = ensemble("b", [G0], reactant_key=[["C=CC=C", 1], ["C=CC=N", 1]])
    with pytest.raises(SelectivityInputError, match="reactant_key"):
        score_selectivity({"a": ensemble("a", [G0]), "b": other}, kind="de", temperature_k=T)


@pytest.mark.parametrize(
    "identity",
    [
        {"name": "xtb_subprocess", "version": "6.7.0"},
        {"name": "xtb_subprocess", "version": "6.8.0", "model": "m"},
        {"name": "mace", "version": "6.8.0"},
    ],
)
def test_mixed_recipe_identities(identity: dict[str, str]) -> None:
    """A different engine name, model or version is refused."""
    other = ensemble("b", [G0], recipe_identity=identity)
    with pytest.raises(SelectivityInputError, match="recipe_identity"):
        score_selectivity({"a": ensemble("a", [G0]), "b": other}, kind="de", temperature_k=T)


def test_ee_refused_over_multi_member_ensembles() -> None:
    """DV-08: kind='ee' with any pathway of more than one member."""
    pathways = {"a": ensemble("a", [G0, gap(0.1)]), "b": ensemble("b", [gap(1.0)])}
    with pytest.raises(SelectivityInputError, match="ee.*pathway 'a'.*DV-08"):
        score_selectivity(pathways, kind="ee", temperature_k=T)
    assert score_selectivity(pathways, kind="de", temperature_k=T).kind == "de"


def test_unknown_kind() -> None:
    """The kind is one of ee, de, regio."""
    with pytest.raises(SelectivityInputError, match="kind"):
        score_selectivity(two(G0, G0), kind="dr", temperature_k=T)  # type: ignore[arg-type]


def test_selectivity_input_error_is_a_value_error() -> None:
    """The refusal is a ValueError."""
    assert issubclass(SelectivityInputError, ValueError)


# --- G8: the import graph -----------------------------------------------------------------------


def test_selectivity_import_loads_no_heavy_module() -> None:
    """G8: importing the scorer loads none of torch, pyscf, fairchem, geometric, rdkit."""
    code = (
        "import sys; import eta_rxncat.orchestrator.selectivity as m; "
        "heavy = ('torch', 'pyscf', 'fairchem', 'geometric', 'rdkit'); "
        "bad = [x for x in heavy if x in sys.modules]; "
        "assert not bad, bad; "
        "assert m.score_selectivity"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_package_exports_resolve_lazily() -> None:
    """Every name in ``eta_rxncat.orchestrator.__all__`` still imports from the package."""
    code = (
        "import eta_rxncat.orchestrator as o; "
        "[getattr(o, n) for n in o.__all__]; "
        "from eta_rxncat.orchestrator import score_selectivity, SelectivityInputError"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
