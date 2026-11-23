"""Independent test-local reference: SVD Kabsch with determinant correction (mission R5).

Written only for the tests and deliberately unlike ``eta_rxncat.mapping.align`` (SVD, not a
quaternion eigenproblem). Never imports ``eta_rxncat.thermo`` (N4).
"""

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def svd_kabsch(mobile: FloatArray, reference: FloatArray) -> tuple[FloatArray, float]:
    """Return the proper rotation mapping centred ``mobile`` onto centred ``reference``, and RMSD.

    The RMSD is computed from the residual coordinates after the motion.
    """
    m = np.asarray(mobile, dtype=np.float64)
    r = np.asarray(reference, dtype=np.float64)
    c_m = m.mean(axis=0)
    c_r = r.mean(axis=0)
    h = (m - c_m).T @ (r - c_r)
    u, _, vt = np.linalg.svd(h)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    correction = np.diag([1.0, 1.0, d if d != 0 else 1.0])
    rotation = vt.T @ correction @ u.T
    moved = (m - c_m) @ rotation.T + c_r
    rmsd = float(np.sqrt(((moved - r) ** 2).sum(axis=1).mean()))
    return rotation, rmsd
