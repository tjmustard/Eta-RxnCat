"""Geometry measurements for class labels (torsion classes of HF1 and T1)."""

import math

from eta_rxncat.core import MolecularState


def dihedral_deg(state: MolecularState, i: int, j: int, k: int, l: int) -> float:  # noqa: E741
    """Return the dihedral angle i-j-k-l of ``state`` in degrees, in (-180, 180]."""
    p0, p1, p2, p3 = (state.coordinates[a] for a in (i, j, k, l))
    b0 = [p0[n] - p1[n] for n in range(3)]
    b1 = [p2[n] - p1[n] for n in range(3)]
    b2 = [p3[n] - p2[n] for n in range(3)]
    norm = math.sqrt(sum(x * x for x in b1))
    if norm == 0.0:
        raise ValueError(f"atoms {j} and {k} coincide")
    u = [x / norm for x in b1]
    v = [b0[n] - sum(b0[m] * u[m] for m in range(3)) * u[n] for n in range(3)]
    w = [b2[n] - sum(b2[m] * u[m] for m in range(3)) * u[n] for n in range(3)]
    x = sum(v[n] * w[n] for n in range(3))
    cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    y = sum(cross[n] * w[n] for n in range(3))
    angle = math.degrees(math.atan2(y, x))
    return 180.0 if angle == -180.0 else angle
