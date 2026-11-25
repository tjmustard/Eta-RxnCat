"""The selectivity scorer: Boltzmann-summed pathway free energies to ddG-dagger and selectivity.

Mission §5 "Selectivity" (v0.6.0, slice 04), pure and closed form. For each pathway the free energy
is ``G_p = -RT ln sum_i g_i exp(-G_i/RT)`` over the summed members, with the member degeneracy
``g_i`` (``G_i - RT ln g_i``, R8), computed against the lowest member so nothing overflows or is
clamped. Two pathways give ``ddG = G_minor - G_major >= 0``, ``r = exp(ddG/RT)`` and
``100 (r - 1)/(r + 1)``; with more, the shares are a softmax of ``-G_p/RT``.

No engine, RDKit, PySCF, torch or geomeTRIC is imported (G8): the constants are
``eta_rxncat.thermo.constants`` (ADR-0026, DV-03) and ``eta_rxncat.engines.units``.
"""

import math
from collections.abc import Mapping, Sequence

from eta_rxncat.core import PathwaySelectivity, SelectivityKind, SelectivityResult, TSEnsemble
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS

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
