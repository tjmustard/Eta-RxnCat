"""Horn unit-quaternion superposition of ordered point pairs (mission A1-A4, ADR-0029).

The rotation is the eigenvector of the largest eigenvalue of Horn's 4x4 key matrix (Horn,
J. Opt. Soc. Am. A 1987, 4, 629), so it is a proper rotation by construction: there is no
reflection fix-up and no SVD. Degenerate pair sets are refused rather than given an arbitrary
spin, and the RMSD is computed from residual coordinates, never from eigenvalues.
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from eta_rxncat.mapping.errors import AlignmentError

FloatArray = NDArray[np.float64]

_EIGEN_GAP_RELATIVE = 1e-10
"""lambda_max - lambda_second at or below this times max(1, |lambda_max|) is not unique."""


def _points(values: ArrayLike, name: str) -> FloatArray:
    """Return ``values`` as a finite float64 (k, 3) array, else raise ``AlignmentError``."""
    try:
        points = np.array(values, dtype=np.float64)
    except (TypeError, ValueError) as err:
        raise AlignmentError(f"{name} is not a numeric (k, 3) array") from err
    if points.ndim != 2 or points.shape[1] != 3:
        raise AlignmentError(f"{name} must have shape (k, 3), got {points.shape}")
    if not np.all(np.isfinite(points)):
        raise AlignmentError(f"{name} has non-finite coordinates")
    return points


def pair_set_shape(points: ArrayLike) -> tuple[float, float]:
    """Measure how close a point set is to a line and to a plane.

    For the centred (k, 3) set with singular values s1 >= s2 >= s3, the RMS off-line deviation is
    ``sqrt((s2**2 + s3**2) / k)`` and the RMS off-plane deviation is ``s3 / sqrt(k)``.

    Args:
        points: A (k, 3) array of coordinates in Angstrom, k >= 1.

    Returns:
        ``(rms_off_line_angstrom, rms_off_plane_angstrom)``.

    Raises:
        AlignmentError: If ``points`` is not a finite, non-empty (k, 3) array.
    """
    coords = _points(points, "points")
    k = coords.shape[0]
    if k == 0:
        raise AlignmentError("points is empty")
    centred = coords - coords.mean(axis=0)
    singular = np.zeros(3)
    computed = np.linalg.svd(centred, compute_uv=False)
    singular[: computed.shape[0]] = computed
    s2, s3 = float(singular[1]), float(singular[2])
    return float(np.sqrt((s2 * s2 + s3 * s3) / k)), float(s3 / np.sqrt(k))


def _key_matrix(correlation: FloatArray) -> FloatArray:
    """Return Horn's symmetric 4x4 key matrix for the correlation M = sum w (m - c_m)(r - c_r)^T."""
    (sxx, sxy, sxz), (syx, syy, syz), (szx, szy, szz) = correlation
    return np.array(
        [
            [sxx + syy + szz, syz - szy, szx - sxz, sxy - syx],
            [syz - szy, sxx - syy - szz, sxy + syx, szx + sxz],
            [szx - sxz, sxy + syx, -sxx + syy - szz, syz + szy],
            [sxy - syx, szx + sxz, syz + szy, -sxx - syy + szz],
        ],
        dtype=np.float64,
    )


def _rotation_from_quaternion(q: FloatArray) -> FloatArray:
    """Return the rotation matrix of the unit quaternion ``q = (w, x, y, z)``."""
    w, x, y, z = q / np.linalg.norm(q)
    return np.array(
        [
            [w * w + x * x - y * y - z * z, 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), w * w - x * x + y * y - z * z, 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), w * w - x * x - y * y + z * z],
        ],
        dtype=np.float64,
    )


@dataclass(frozen=True)
class Superposition:
    """The rigid motion that best maps a mobile pair set onto a reference pair set.

    Attributes:
        rotation: Proper 3x3 rotation matrix (det +1).
        mobile_centroid: (Weighted) centroid of the mobile pair set, Angstrom.
        reference_centroid: (Weighted) centroid of the reference pair set, Angstrom.
        rmsd_angstrom: (Weighted) RMSD of the moved mobile pairs from the reference pairs.
        mobile_shape: ``pair_set_shape`` of the mobile pair set.
        reference_shape: ``pair_set_shape`` of the reference pair set.
    """

    rotation: FloatArray
    mobile_centroid: FloatArray
    reference_centroid: FloatArray
    rmsd_angstrom: float
    mobile_shape: tuple[float, float]
    reference_shape: tuple[float, float]

    def apply(self, coords: ArrayLike) -> FloatArray:
        """Move coordinates with the fitted motion: x' = R (x - c_m) + c_r.

        Args:
            coords: A (n, 3) array of coordinates in the mobile frame, Angstrom.

        Returns:
            The moved (n, 3) float64 array.

        Raises:
            AlignmentError: If ``coords`` is not a finite (n, 3) array.
        """
        points = _points(coords, "coords")
        moved: FloatArray = (points - self.mobile_centroid) @ self.rotation.T
        return moved + self.reference_centroid


def superpose(
    mobile: ArrayLike,
    reference: ArrayLike,
    weights: Sequence[float] | ArrayLike | None = None,
    *,
    degenerate_tolerance_angstrom: float = 1e-3,
) -> Superposition:
    """Fit the proper rotation and translation that best map ``mobile`` onto ``reference``.

    Row j of ``mobile`` is paired with row j of ``reference``.

    Args:
        mobile: (k, 3) coordinates that move, Angstrom.
        reference: (k, 3) coordinates that stay, Angstrom.
        weights: Optional positive, finite weight per pair (plain means when omitted).
        degenerate_tolerance_angstrom: A set whose RMS off-line deviation is at or below this is
            collinear or coincident and refused.

    Returns:
        The fitted ``Superposition``.

    Raises:
        AlignmentError: On a shape mismatch, fewer than 3 pairs, non-finite values, bad weights,
            a collinear or coincident set, or a non-unique rotation.
    """
    m = _points(mobile, "mobile")
    r = _points(reference, "reference")
    if m.shape != r.shape:
        raise AlignmentError(f"mobile has shape {m.shape} but reference has {r.shape}")
    k = m.shape[0]
    if k < 3:
        raise AlignmentError(f"superposition needs at least 3 pairs, got {k}")
    if weights is None:
        w = np.ones(k, dtype=np.float64)
    else:
        try:
            w = np.array(weights, dtype=np.float64)
        except (TypeError, ValueError) as err:
            raise AlignmentError("weights are not numeric") from err
        if w.shape != (k,):
            raise AlignmentError(f"weights must have length {k}, got shape {w.shape}")
        if not (np.all(np.isfinite(w)) and np.all(w > 0)):
            raise AlignmentError("weights must be positive and finite")

    mobile_shape = pair_set_shape(m)
    reference_shape = pair_set_shape(r)
    for name, (off_line, _) in (("mobile", mobile_shape), ("reference", reference_shape)):
        if off_line <= degenerate_tolerance_angstrom:
            raise AlignmentError(
                f"{name} pair set is collinear or coincident: RMS off-line deviation "
                f"{off_line:.3e} <= {degenerate_tolerance_angstrom:.3e} angstrom"
            )

    total = float(w.sum())
    c_m = (w[:, None] * m).sum(axis=0) / total
    c_r = (w[:, None] * r).sum(axis=0) / total
    dm = m - c_m
    dr = r - c_r
    correlation = (w[:, None] * dm).T @ dr
    eigenvalues, eigenvectors = np.linalg.eigh(_key_matrix(correlation))
    top, second = float(eigenvalues[-1]), float(eigenvalues[-2])
    if top - second <= _EIGEN_GAP_RELATIVE * max(1.0, abs(top)):
        raise AlignmentError("rotation not unique")
    rotation = _rotation_from_quaternion(eigenvectors[:, -1])

    residual = dm @ rotation.T + c_r - r
    rmsd = float(np.sqrt((w * (residual * residual).sum(axis=1)).sum() / total))
    return Superposition(
        rotation=rotation,
        mobile_centroid=c_m,
        reference_centroid=c_r,
        rmsd_angstrom=rmsd,
        mobile_shape=mobile_shape,
        reference_shape=reference_shape,
    )
