"""Core-frozen pre-relaxation of a grafted structure (mission X1-X4; TJ Q2 "(b)", R6, R7).

The conserved core is frozen, not restrained: it goes to ``Optimizer.minimize`` as
``frozen_atom_indices`` (geomeTRIC ``$freeze``). No dihedral constraint is ever passed, because
frozen atoms combined with a dihedral constraint can hang the optimizer (v0.3.0 audit 04).
"""

import math
from collections.abc import Mapping, Sequence

from eta_rxncat.core import MolecularState, OptimizationResult
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import Engine
from eta_rxncat.mapping.errors import CoreDisplacementError, MappingError
from eta_rxncat.optimize import Optimizer

CORE_FREEZE_TOLERANCE_ANGSTROM = 1e-6
"""Largest allowed movement of any core atom (max per-atom Euclidean, template frame; mission R26).

geomeTRIC ``$freeze`` with ``enforce`` 0.1 holds frozen atoms to about 1e-8 to 1e-7 Angstrom, not
exactly (measured: UFF up to 1.19e-7 Angstrom on n-butane, xtb 4.19e-8 Angstrom on the M1 graft).
The bound is 1e-6 Angstrom, the six-decimal precision of the inputs (replan 1). The core is never
snapped back or otherwise corrected.
"""


def relax_constrained_core(
    state: MolecularState,
    engine: Engine,
    optimizer: Optimizer,
    core_indices: Sequence[int],
    options: Mapping[str, ScalarValue] | None = None,
) -> OptimizationResult:
    """Pre-relax ``state`` with the atoms ``core_indices`` frozen.

    The result is a pre-relaxation of a transition-state guess, **not a minimum**: never pass it
    to ``eta_rxncat.thermo.check_ground_state``.

    Args:
        state: The grafted structure (template frame).
        engine: The potential.
        optimizer: The optimizer; called once with ``frozen_atom_indices`` and no dihedral
            constraints.
        core_indices: Atoms that must not move (non-empty, unique, in range).
        options: Optimizer options, passed through unchanged; a ``"constraints"`` key is refused.

    Returns:
        The optimizer's result, unchanged.

    Raises:
        MappingError: An empty, duplicated or out-of-range core, or an options key
            ``"constraints"``, before any engine call.
        CoreDisplacementError: A core atom moved more than ``CORE_FREEZE_TOLERANCE_ANGSTROM``
            (1e-6 Angstrom); the worst atom is named.
        eta_rxncat.optimize.OptimizerError: Raised by the optimizer; propagated unchanged.
        eta_rxncat.engines.EngineError: Raised by the engine; propagated unchanged.
    """
    core = list(core_indices)
    n_atoms = len(state.symbols)
    if not core:
        raise MappingError("core_indices is empty")
    if len(set(core)) != len(core):
        raise MappingError(f"core_indices has duplicates: {core}")
    out_of_range = sorted({i for i in core if not 0 <= i < n_atoms})
    if out_of_range:
        raise MappingError(f"core_indices {out_of_range} out of range for {n_atoms} atoms")
    if options is not None and "constraints" in options:
        raise MappingError(
            'options key "constraints" is refused: the core is frozen through '
            "frozen_atom_indices and no other constraint is ever applied"
        )

    result = optimizer.minimize(state, engine, frozen_atom_indices=tuple(core), options=options)

    worst_atom, worst = core[0], -1.0
    for k in core:
        moved = math.dist(result.final_state.coordinates[k], state.coordinates[k])
        if moved > worst:
            worst_atom, worst = k, moved
    if worst > CORE_FREEZE_TOLERANCE_ANGSTROM:
        raise CoreDisplacementError(worst_atom, worst)
    return result
