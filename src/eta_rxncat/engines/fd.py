"""Central-difference Cartesian Hessian from forces (mission R15). Pure Python, no numpy."""

import math
from collections.abc import Callable, Sequence

ForceFn = Callable[[list[list[float]]], Sequence[Sequence[float]]]
"""Forces (Eh/Bohr, N x 3) at coordinates given in Bohr (N x 3)."""


def fd_hessian(
    force_fn: ForceFn, coords_bohr: Sequence[Sequence[float]], step_bohr: float
) -> tuple[list[list[float]], float]:
    """Return the symmetrised Hessian (Eh/Bohr^2, 3N x 3N) and the max pre-symmetrisation asymmetry.

    ``H[i][j] = -(F_j(x + h e_i) - F_j(x - h e_i)) / (2 h)``, with index ``3 * atom + axis``,
    from 6N calls of ``force_fn``. The result is ``(H + H^T) / 2``, exactly symmetric, and the
    second value is ``max |H[i][j] - H[j][i]|`` before symmetrising. ``coords_bohr`` and the
    lists ``force_fn`` returns are never modified.

    Raises:
        ValueError: a non-positive or non-finite step, coordinates that are not N x 3, or
            forces of the wrong shape.
    """
    if not (math.isfinite(step_bohr) and step_bohr > 0):
        raise ValueError(f"step_bohr must be finite and > 0, not {step_bohr!r}")
    base = [list(map(float, row)) for row in coords_bohr]
    if not base or any(len(row) != 3 for row in base):
        raise ValueError("coords_bohr must be N x 3 with N >= 1")
    dof = 3 * len(base)

    def flat_forces(coords: list[list[float]]) -> list[float]:
        forces = force_fn(coords)
        if len(forces) != len(base) or any(len(row) != 3 for row in forces):
            raise ValueError(f"force_fn returned forces not shaped {len(base)} x 3")
        return [float(value) for row in forces for value in row]

    raw: list[list[float]] = []
    for i in range(dof):
        atom, axis = divmod(i, 3)
        plus = [row[:] for row in base]
        minus = [row[:] for row in base]
        plus[atom][axis] += step_bohr
        minus[atom][axis] -= step_bohr
        f_plus = flat_forces(plus)
        f_minus = flat_forces(minus)
        raw.append([-(f_plus[j] - f_minus[j]) / (2.0 * step_bohr) for j in range(dof)])

    max_asym = 0.0
    hessian = [row[:] for row in raw]
    for i in range(dof):
        for j in range(i + 1, dof):
            max_asym = max(max_asym, abs(raw[i][j] - raw[j][i]))
            mean = (raw[i][j] + raw[j][i]) / 2.0
            hessian[i][j] = mean
            hessian[j][i] = mean
    return hessian, max_asym
