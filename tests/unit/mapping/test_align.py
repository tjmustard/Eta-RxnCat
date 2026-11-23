"""Tests for the Horn quaternion superposition (v0.4.0 slice 03; mission A1-A4, R5, R12, R18)."""

import ast
from pathlib import Path

import numpy as np
import pytest
from _svd_reference import svd_kabsch
from cleanroom import TOLERANCE_ANGSTROM, load_vector
from numpy.typing import NDArray

from eta_rxncat.mapping import (
    AlignmentError,
    CoreDisplacementError,
    GraftClashError,
    GraftInputError,
    MappingError,
    Superposition,
    pair_set_shape,
    superpose,
)
from eta_rxncat.mapping.align import _key_matrix

FloatArray = NDArray[np.float64]
MAPPING_SRC = Path(__file__).parents[3] / "src" / "eta_rxncat" / "mapping"


def random_rotation(rng: np.random.Generator) -> FloatArray:
    """Return a uniformly random proper rotation (det +1) via QR of a Gaussian matrix."""
    q, r = np.linalg.qr(rng.standard_normal((3, 3)))
    q = q * np.sign(np.diag(r))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def key_matrix_gap(mobile: FloatArray, reference: FloatArray) -> float:
    """Return the gap between the two largest eigenvalues of the unweighted key matrix."""
    dm = mobile - mobile.mean(axis=0)
    dr = reference - reference.mean(axis=0)
    eigenvalues = np.linalg.eigvalsh(_key_matrix(dm.T @ dr))
    return float(eigenvalues[-1] - eigenvalues[-2])


# --- Mini-requirement 1: known motion -------------------------------------------------------


def test_known_motion_is_recovered() -> None:
    """A random proper rotation plus translation is undone to 1e-10 Angstrom."""
    rng = np.random.default_rng(7)
    mobile = rng.uniform(-3.0, 3.0, size=(12, 3))
    rotation = random_rotation(rng)
    translation = np.array([5.0, -2.0, 1.0])
    reference = mobile @ rotation.T + translation
    fit = superpose(mobile, reference)
    assert np.max(np.abs(fit.apply(mobile) - reference)) <= 1e-10
    assert fit.rmsd_angstrom <= 1e-10
    assert np.max(np.abs(fit.rotation - rotation)) <= 1e-10


# --- Mini-requirement 2: 1000 random sets against the SVD reference -------------------------


def random_pair_sets(count: int) -> list[tuple[FloatArray, FloatArray]]:
    """Draw ``count`` independent (mobile, reference) pairs, redrawing degenerate ones (R5)."""
    rng = np.random.default_rng(20261123)
    sets: list[tuple[FloatArray, FloatArray]] = []
    while len(sets) < count:
        k = int(rng.integers(3, 30))
        mobile = rng.uniform(-3.0, 3.0, size=(k, 3))
        reference = rng.uniform(-3.0, 3.0, size=(k, 3))
        if min(pair_set_shape(mobile)[0], pair_set_shape(reference)[0]) < 0.1:
            continue
        if key_matrix_gap(mobile, reference) < 1e-6:
            continue
        sets.append((mobile, reference))
    return sets


def test_random_sets_match_svd_reference() -> None:
    """det(R) = +1, |dRMSD| <= 1e-10 Angstrom and max|dR| <= 1e-9 over 1000 random sets."""
    worst_rmsd = 0.0
    worst_rotation = 0.0
    worst_det = 0.0
    for mobile, reference in random_pair_sets(1000):
        fit = superpose(mobile, reference)
        rotation_svd, rmsd_svd = svd_kabsch(mobile, reference)
        worst_det = max(worst_det, abs(np.linalg.det(fit.rotation) - 1.0))
        worst_rmsd = max(worst_rmsd, abs(fit.rmsd_angstrom - rmsd_svd))
        worst_rotation = max(worst_rotation, float(np.max(np.abs(fit.rotation - rotation_svd))))
    print(f"max|ddet|={worst_det:.3e} max|dRMSD|={worst_rmsd:.3e} max|dR|={worst_rotation:.3e}")
    assert worst_det <= 1e-12
    assert worst_rmsd <= 1e-10
    assert worst_rotation <= 1e-9


# --- Mini-requirement 3: mirror images ------------------------------------------------------


def test_non_coplanar_mirror_is_not_reflected() -> None:
    """A non-coplanar set against its reflection keeps det +1 and a non-zero RMSD."""
    rng = np.random.default_rng(11)
    mobile = rng.uniform(-2.0, 2.0, size=(8, 3))
    assert pair_set_shape(mobile)[1] > 0.1
    reference = mobile * np.array([1.0, 1.0, -1.0])
    fit = superpose(mobile, reference)
    assert abs(np.linalg.det(fit.rotation) - 1.0) <= 1e-12
    assert fit.rmsd_angstrom > 1e-3


def test_vector_03_mirror_image() -> None:
    """Vector 03: RMSD 0.75 Angstrom; the moved incoming equals expected rows 5-8."""
    vector = load_vector("03_mirror_image")
    assert vector.expected_product is not None
    template_idx = [t for t, _ in vector.pairs]
    incoming_idx = [i for _, i in vector.pairs]
    assert template_idx == [0, 1, 2, 3] and incoming_idx == [0, 1, 2, 3]
    fit = superpose(
        vector.incoming.coordinates[incoming_idx], vector.template.coordinates[template_idx]
    )
    assert abs(fit.rmsd_angstrom - 0.75) <= TOLERANCE_ANGSTROM
    assert abs(np.linalg.det(fit.rotation) - 1.0) <= 1e-12
    moved = fit.apply(vector.incoming.coordinates)
    expected = vector.expected_product.coordinates[4:8]
    assert np.max(np.abs(moved - expected)) <= TOLERANCE_ANGSTROM
    assert vector.expected_product.symbols[4:8] == vector.incoming.symbols


# --- Mini-requirement 4: vectors 01 and 02 at alignment level -------------------------------


@pytest.mark.parametrize(
    ("name", "symbol", "position"),
    [
        ("01_rigid_recovery", "O", (1.0, 1.0, 1.0)),
        ("02_quarter_turn", "Cl", (0.0, 0.0, 1.0)),
    ],
)
def test_vectors_01_02_alignment(name: str, symbol: str, position: tuple[float, ...]) -> None:
    """The pairs fit exactly and the unpaired incoming atom lands on the expected last row."""
    vector = load_vector(name)
    assert vector.expected_product is not None
    template_idx = [t for t, _ in vector.pairs]
    incoming_idx = [i for _, i in vector.pairs]
    fit = superpose(
        vector.incoming.coordinates[incoming_idx], vector.template.coordinates[template_idx]
    )
    assert fit.rmsd_angstrom <= TOLERANCE_ANGSTROM
    unpaired = [i for i in range(len(vector.incoming.symbols)) if i not in incoming_idx]
    assert len(unpaired) == 1
    moved = fit.apply(vector.incoming.coordinates[unpaired])[0]
    assert vector.incoming.symbols[unpaired[0]] == symbol
    assert vector.expected_product.symbols[-1] == symbol
    assert np.max(np.abs(moved - vector.expected_product.coordinates[-1])) <= TOLERANCE_ANGSTROM
    assert np.max(np.abs(moved - np.array(position))) <= TOLERANCE_ANGSTROM


# --- Mini-requirement 5: refusals -----------------------------------------------------------


@pytest.mark.parametrize(
    ("n_pairs", "message"),
    [(1, "at least 3 pairs"), (2, "at least 3 pairs"), (3, "collinear or coincident")],
)
def test_vector_06_degenerate_pairs_refused(n_pairs: int, message: str) -> None:
    """Vector 06: 1 pair, 2 pairs and 3 collinear pairs raise AlignmentError (CR-05)."""
    vector = load_vector("06_degenerate_pairs")
    assert vector.expected_product is None and vector.pairs == []
    pairs = list(range(n_pairs))  # A: 1<-1; B: 1<-1, 2<-2; C: 1<-1, 2<-2, 3<-3 (0-based here)
    with pytest.raises(AlignmentError, match=message):
        superpose(vector.incoming.coordinates[pairs], vector.template.coordinates[pairs])


def test_refusals() -> None:
    """Two pairs, coincident points, shape mismatch, NaN and bad weights raise AlignmentError."""
    rng = np.random.default_rng(3)
    good = rng.uniform(-2.0, 2.0, size=(5, 3))
    two = rng.uniform(-2.0, 2.0, size=(2, 3))
    with pytest.raises(AlignmentError, match="at least 3 pairs"):
        superpose(two, two + 1.0)
    coincident = np.ones((4, 3))
    with pytest.raises(AlignmentError, match="mobile pair set is collinear or coincident"):
        superpose(coincident, good[:4])
    with pytest.raises(AlignmentError, match="reference pair set is collinear or coincident"):
        superpose(good[:4], coincident)
    with pytest.raises(AlignmentError, match="mobile has shape"):
        superpose(good, good[:4])
    with pytest.raises(AlignmentError, match=r"must have shape \(k, 3\)"):
        superpose(good[:, :2], good[:, :2])
    with_nan = good.copy()
    with_nan[2, 1] = np.nan
    with pytest.raises(AlignmentError, match="non-finite"):
        superpose(with_nan, good)
    with pytest.raises(AlignmentError, match="positive and finite"):
        superpose(good, good, weights=[1.0, 1.0, 0.0, 1.0, 1.0])
    with pytest.raises(AlignmentError, match="positive and finite"):
        superpose(good, good, weights=[1.0, -1.0, 1.0, 1.0, 1.0])
    with pytest.raises(AlignmentError, match="positive and finite"):
        superpose(good, good, weights=[1.0, np.inf, 1.0, 1.0, 1.0])
    with pytest.raises(AlignmentError, match="weights must have length 5"):
        superpose(good, good, weights=[1.0, 1.0])
    with pytest.raises(AlignmentError, match="not a numeric"):
        superpose([["a", "b", "c"]] * 3, good[:3])


def test_non_unique_rotation_refused() -> None:
    """A regular tetrahedron against its inversion has a triply degenerate top eigenvalue."""
    tetrahedron = np.array(
        [[1.0, 1.0, 1.0], [1.0, -1.0, -1.0], [-1.0, 1.0, -1.0], [-1.0, -1.0, 1.0]]
    )
    with pytest.raises(AlignmentError, match="rotation not unique"):
        superpose(tetrahedron, -tetrahedron)


def test_tolerance_is_keyword_and_applied() -> None:
    """A nearly collinear set passes the default tolerance and fails a looser one."""
    nearly = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.01, 0.0]])
    off_line = pair_set_shape(nearly)[0]
    assert 1e-3 < off_line < 0.1
    superpose(nearly, nearly + 1.0)
    with pytest.raises(AlignmentError, match="collinear or coincident"):
        superpose(nearly, nearly + 1.0, degenerate_tolerance_angstrom=0.1)


# --- Mini-requirement 6: weights ------------------------------------------------------------


def test_uniform_weights_equal_unweighted() -> None:
    """Weights all 2.0 give the unweighted result within 1e-12."""
    rng = np.random.default_rng(5)
    mobile = rng.uniform(-2.0, 2.0, size=(7, 3))
    reference = rng.uniform(-2.0, 2.0, size=(7, 3))
    plain = superpose(mobile, reference)
    doubled = superpose(mobile, reference, weights=[2.0] * 7)
    assert np.max(np.abs(plain.rotation - doubled.rotation)) <= 1e-12
    assert np.max(np.abs(plain.mobile_centroid - doubled.mobile_centroid)) <= 1e-12
    assert np.max(np.abs(plain.reference_centroid - doubled.reference_centroid)) <= 1e-12
    assert abs(plain.rmsd_angstrom - doubled.rmsd_angstrom) <= 1e-12


def test_weighted_centroid_and_rmsd_by_hand() -> None:
    """Weighted centroids and RMSD follow sum(w x)/sum(w) and sqrt(sum(w d^2)/sum(w))."""
    rng = np.random.default_rng(9)
    mobile = rng.uniform(-2.0, 2.0, size=(5, 3))
    reference = rng.uniform(-2.0, 2.0, size=(5, 3))
    weights = np.array([1.0, 2.0, 3.0, 0.5, 4.0])
    fit = superpose(mobile, reference, weights=weights)
    c_m = (weights[:, None] * mobile).sum(axis=0) / weights.sum()
    c_r = (weights[:, None] * reference).sum(axis=0) / weights.sum()
    assert np.max(np.abs(fit.mobile_centroid - c_m)) <= 1e-12
    assert np.max(np.abs(fit.reference_centroid - c_r)) <= 1e-12
    moved = (mobile - c_m) @ fit.rotation.T + c_r
    hand = np.sqrt((weights * ((moved - reference) ** 2).sum(axis=1)).sum() / weights.sum())
    assert abs(fit.rmsd_angstrom - hand) <= 1e-12
    assert abs(np.linalg.det(fit.rotation) - 1.0) <= 1e-12
    assert fit.rmsd_angstrom != pytest.approx(superpose(mobile, reference).rmsd_angstrom)


# --- Mini-requirement 7: determinism (H-M4) -------------------------------------------------


def test_identical_inputs_give_bitwise_identical_results() -> None:
    """Two calls on identical inputs give bitwise-identical rotation and RMSD."""
    mobile, reference = random_pair_sets(1)[0]
    first = superpose(mobile.copy(), reference.copy())
    second = superpose(mobile.copy(), reference.copy())
    assert np.array_equal(first.rotation, second.rotation)
    assert np.array_equal(np.array(first.rmsd_angstrom), np.array(second.rmsd_angstrom))


# --- Mini-requirement 8: pair_set_shape -----------------------------------------------------


def test_pair_set_shape_square_and_line() -> None:
    """A planar square has off-plane 0 and off-line > 0; a line has off-line 0."""
    square = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    off_line, off_plane = pair_set_shape(square)
    assert off_plane <= 1e-12
    assert off_line == pytest.approx(0.5)
    line = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0], [2.0, 2.0, 2.0], [5.0, 5.0, 5.0]])
    assert pair_set_shape(line)[0] <= 1e-12
    assert pair_set_shape(line)[1] <= 1e-12


def test_superposition_reports_shapes_and_is_frozen() -> None:
    """The fit carries both shapes, and the dataclass is frozen."""
    square = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    fit = superpose(square, square + 2.0)
    assert isinstance(fit, Superposition)
    assert fit.mobile_shape == pair_set_shape(square)
    assert fit.reference_shape == pair_set_shape(square + 2.0)
    with pytest.raises(AttributeError):
        fit.rmsd_angstrom = 1.0  # type: ignore[misc]


# --- Errors and the no-assert rule (Mini-requirement 10) ------------------------------------


def test_error_family_and_attributes() -> None:
    """Every mapping error is a MappingError; clash and displacement errors carry their data."""
    for error in (AlignmentError, GraftInputError, GraftClashError, CoreDisplacementError):
        assert issubclass(error, MappingError)
    clash = GraftClashError(3, 17, 0.4321)
    assert (clash.i, clash.j, clash.distance_angstrom) == (3, 17, 0.4321)
    assert "3" in str(clash) and "17" in str(clash) and "0.432100" in str(clash)
    moved = CoreDisplacementError(5, 2.5e-7)
    assert (moved.atom, moved.displacement_angstrom) == (5, 2.5e-7)
    assert "5" in str(moved) and "2.500e-07" in str(moved)


def test_no_assert_in_mapping_package() -> None:
    """The mapping package has no assert statement (mission R7)."""
    files = sorted(MAPPING_SRC.rglob("*.py"))
    assert files
    offenders = [
        f"{path.name}:{node.lineno}"
        for path in files
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Assert)
    ]
    assert offenders == []
