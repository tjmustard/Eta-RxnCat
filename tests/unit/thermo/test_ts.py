"""Tests for the v0.5.0 TS validator, sigma from a bond graph and TS thermochemistry (slice 04)."""

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import thermo_geometries as g
from numpy.typing import NDArray
from rdkit import Chem

from eta_rxncat.core import (
    MolecularState,
    StageConfig,
    ThermoAnalysisOptions,
    ThermoConfig,
    TSValidationOptions,
)
from eta_rxncat.thermo import (
    ThermoInputError,
    TSValidationInputError,
    atomic_masses_amu,
    rotational_symmetry_number,
    rotational_symmetry_number_from_bonds,
    thermochemistry,
    ts_thermochemistry,
    validate_transition_state,
)
from eta_rxncat.thermo.rrho import _thermochemistry

Array = NDArray[np.float64]
ANALYSIS = ThermoAnalysisOptions()
REPO = Path(__file__).parents[3]
TS1A_N = REPO / "tests" / "e2e" / "data" / "e2e5" / "xyz" / "TS1a_n.xyz"
THERMO_SRC = REPO / "src" / "eta_rxncat" / "thermo"

# --- A hand-built 4-atom TS with unequal masses -------------------------------------------------

SYMBOLS = ["C", "O", "H", "N"]
COORDS = np.array([[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [-0.5, 0.9, 0.1], [0.4, 0.3, 2.2]])
VIBRATIONS = [300.0, 800.0, 1200.0, 1600.0, 3000.0]


def model_state(active: list[int] | None = None) -> MolecularState:
    """Return the 4-atom model (C, O, H, N), atoms 0, 1, 3 active unless given."""
    return MolecularState(
        symbols=SYMBOLS,
        coordinates=COORDS.tolist(),
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0, 1, 3] if active is None else active,
    )


def raw_stretch(bonds: list[tuple[int, int]], signs: list[float] | None = None) -> Array:
    """Return the summed (signed) forming stretch, flat, unnormalised (test-local)."""
    s = np.zeros_like(COORDS)
    for (i, j), sign in zip(bonds, signs or [1.0] * len(bonds), strict=True):
        u = (COORDS[j] - COORDS[i]) / np.linalg.norm(COORDS[j] - COORDS[i])
        s[i] -= sign * u
        s[j] += sign * u
    return s.ravel()


def vibrational_complement(masses: Array) -> Array:
    """Return an orthonormal basis of the mass-weighted vibrational space (test-local)."""
    rigid = g.rigid_basis(COORDS, masses, linear=False)
    u, _, _ = np.linalg.svd(rigid, full_matrices=True)
    return u[:, 6:]


def hessian_with_reaction_vector(
    q0_direction: Array, frequencies: list[float]
) -> tuple[Array, Array]:
    """Return a Cartesian Hessian whose lowest mode has mass-weighted vector q0 and q0 itself.

    ``q0_direction`` (mass-weighted, flat) is projected into the vibrational space and normalised;
    the other modes span the rest of it. ``frequencies`` (ascending) are assigned in order.
    """
    masses = atomic_masses_amu(SYMBOLS)
    comp = vibrational_complement(masses)
    q0 = comp @ (comp.T @ q0_direction)
    q0 /= np.linalg.norm(q0)
    rest, _ = np.linalg.qr(comp - np.outer(q0, q0 @ comp))
    rest = rest[:, : comp.shape[1] - 1]
    rest -= np.outer(q0, q0 @ rest)
    rest, _ = np.linalg.qr(rest)
    basis = np.column_stack([q0, rest])
    lam = np.array([g.cm1_to_eigenvalue(f) for f in frequencies])
    sqrt_m = np.repeat(np.sqrt(masses), 3)
    hessian = (basis @ np.diag(lam) @ basis.T) * np.outer(sqrt_m, sqrt_m)
    return 0.5 * (hessian + hessian.T), q0


def mass_weighted(cartesian: Array) -> Array:
    """Return M^(1/2) x for a flat Cartesian vector."""
    return np.repeat(np.sqrt(atomic_masses_amu(SYMBOLS)), 3) * cartesian


def stretch_hessian(
    frequencies: list[float], bonds: list[tuple[int, int]] | None = None
) -> tuple[Array, Array]:
    """Return a Hessian whose reaction mode follows the forming stretch of ``bonds``."""
    return hessian_with_reaction_vector(mass_weighted(raw_stretch(bonds or [(0, 3)])), frequencies)


def validate(hessian: Array, bonds: list[tuple[int, int]] | None = None, **kwargs: Any) -> Any:
    """Validate the model state with ``hessian`` and forming bonds (default (0, 3))."""
    state = kwargs.pop("state", model_state())
    return validate_transition_state(state, hessian, forming_bonds=bonds or [(0, 3)], **kwargs)


# --- G2: numbers equal independent computations ----------------------------------------------


def test_g2_numbers_equal_independent_values() -> None:
    """KE fraction, overlap and distances equal closed-form values within 1e-12."""
    hessian, q0 = stretch_hessian([-400.0, *VIBRATIONS])
    result = validate(hessian)
    masses = np.repeat(atomic_masses_amu(SYMBOLS), 3)
    # m_a |d_a|^2 is proportional to |q_a|^2 because d is proportional to M^(-1/2) q.
    q_atoms = (q0**2).reshape(-1, 3).sum(axis=1)
    expected_fraction = q_atoms[[0, 1, 3]].sum() / q_atoms.sum()
    d = q0 / np.sqrt(masses)
    d /= np.linalg.norm(d)
    s = raw_stretch([(0, 3)])
    s /= np.linalg.norm(s)
    assert result.n_imaginary == 1
    assert result.imaginary_frequency_cm1 == pytest.approx(-400.0, abs=1e-6)
    assert abs(result.active_core_ke_fraction - expected_fraction) <= 1e-12
    assert abs(result.forming_stretch_overlap - abs(float(s @ d))) <= 1e-12
    expected_distance = float(np.linalg.norm(COORDS[3] - COORDS[0]))
    assert abs(result.forming_distances_angstrom["0-3"] - expected_distance) <= 1e-12
    assert result.passed_bool
    assert result.reasons == []
    assert result.forming_bonds_in_phase_bool is True
    assert result.active_atom_indices == [0, 1, 3]
    assert result.options == TSValidationOptions()


def test_active_atoms_are_sorted_in_the_result() -> None:
    """The active set is reported sorted whatever order the state gives."""
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS])
    result = validate(hessian, state=model_state([3, 0, 1]))
    assert result.active_atom_indices == [0, 1, 3]


# --- One test per reason --------------------------------------------------------------------


def test_no_imaginary_mode() -> None:
    """A minimum: no imaginary mode, numbers None, all three checks false."""
    hessian, _ = stretch_hessian([200.0, *VIBRATIONS])
    result = validate(hessian)
    assert result.n_imaginary == 0
    assert result.reasons == ["no_imaginary_mode"]
    assert result.imaginary_frequency_cm1 is None
    assert result.active_core_ke_fraction is None
    assert result.forming_stretch_overlap is None
    assert result.forming_bonds_in_phase_bool is None
    assert not (
        result.mode_count_passed_bool
        or result.active_core_passed_bool
        or result.identity_passed_bool
    )
    assert not result.passed_bool


def test_soft_mode_above_tolerance_is_not_imaginary() -> None:
    """A mode at -15 cm^-1 is inside imag_tol (20): not counted as imaginary."""
    hessian, _ = stretch_hessian([-15.0, *VIBRATIONS])
    assert validate(hessian).reasons == ["no_imaginary_mode"]


def test_multiple_imaginary_modes() -> None:
    """Two modes below -20 cm^-1 fail the mode count."""
    hessian, _ = stretch_hessian([-400.0, -100.0, 800.0, 1200.0, 1600.0, 3000.0])
    result = validate(hessian)
    assert result.n_imaginary == 2
    assert "multiple_imaginary_modes" in result.reasons
    assert not result.mode_count_passed_bool
    assert not result.passed_bool


def test_imaginary_above_cutoff() -> None:
    """One imaginary mode at -30 cm^-1 is above the -50 cm^-1 cutoff."""
    hessian, _ = stretch_hessian([-30.0, *VIBRATIONS])
    result = validate(hessian)
    assert result.n_imaginary == 1
    assert result.reasons == ["imaginary_above_cutoff"]
    assert not result.mode_count_passed_bool


def test_active_core_fraction_below_threshold() -> None:
    """With only the hydrogen active, the reaction mode's KE fraction is far below 0.60."""
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS])
    result = validate(hessian, state=model_state([2]))
    assert result.active_core_ke_fraction is not None
    assert result.active_core_ke_fraction < 0.60
    assert result.reasons == ["active_core_fraction_below_threshold"]
    assert result.mode_count_passed_bool and result.identity_passed_bool
    assert not result.active_core_passed_bool


def test_forming_overlap_below_threshold() -> None:
    """A reaction mode mostly orthogonal to the forming stretch fails the overlap check."""
    s = mass_weighted(raw_stretch([(0, 3)]))
    other = mass_weighted(raw_stretch([(1, 2)]))
    hessian, _ = hessian_with_reaction_vector(other + 0.1 * s, [-400.0, *VIBRATIONS])
    result = validate(hessian)
    assert result.forming_stretch_overlap is not None
    assert result.forming_stretch_overlap < 0.50
    assert "forming_overlap_below_threshold" in result.reasons
    assert not result.identity_passed_bool


def test_forming_bonds_out_of_phase() -> None:
    """One bond stretching while the other shortens is out of phase."""
    bonds = [(0, 3), (2, 3)]
    signed = mass_weighted(raw_stretch(bonds, [1.0, -1.0]))
    hessian, _ = hessian_with_reaction_vector(signed, [-400.0, *VIBRATIONS])
    result = validate(hessian, bonds)
    assert result.forming_bonds_in_phase_bool is False
    assert "forming_bonds_out_of_phase" in result.reasons
    assert not result.identity_passed_bool


def test_forming_bonds_in_phase_with_two_bonds() -> None:
    """Two bonds moving together are in phase."""
    bonds = [(0, 3), (2, 3)]
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS], bonds)
    result = validate(hessian, bonds)
    assert result.forming_bonds_in_phase_bool is True
    assert "forming_bonds_out_of_phase" not in result.reasons


def test_forming_distance_out_of_window() -> None:
    """The C-O pair at 1.2 A is below the 1.90 A lower bound."""
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS], [(0, 1)])
    result = validate(hessian, [(0, 1)])
    assert result.forming_distances_angstrom == {"0-1": pytest.approx(1.2, abs=1e-12)}
    assert "forming_distance_out_of_window" in result.reasons
    assert not result.identity_passed_bool


def test_distance_window_bounds_are_inclusive_and_keyed() -> None:
    """A window that just includes or just excludes the 2.257 A forming distance decides it."""
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS])
    distance = float(np.linalg.norm(COORDS[3] - COORDS[0]))
    inside = TSValidationOptions(forming_distance_min_angstrom=distance)
    outside = TSValidationOptions(forming_distance_max_angstrom=distance - 1e-9)
    assert validate(hessian, options=inside).passed_bool
    assert validate(hessian, options=outside).reasons == ["forming_distance_out_of_window"]


def test_passed_only_without_reasons() -> None:
    """Every result here has passed_bool exactly when it has no reason."""
    cases = [[-400.0, *VIBRATIONS], [-30.0, *VIBRATIONS], [200.0, *VIBRATIONS]]
    for frequencies in cases:
        result = validate(stretch_hessian(frequencies)[0])
        assert result.passed_bool == (result.reasons == [])


# --- Refusals (R16) --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"state": model_state([])}, "active_atom_indices is empty"),
        ({"forming_bonds": []}, "no forming bonds"),
        ({"forming_bonds": [(1, 1)]}, "joins an atom to itself"),
        ({"forming_bonds": [(0, 3), (3, 0)]}, "duplicate forming bonds"),
        ({"forming_bonds": [(0, 4)]}, "out of range for 4 atoms"),
        ({"forming_bonds": [(-1, 2)]}, "out of range"),
        ({"forming_bonds": [(0, True)]}, "two ints"),
        (
            {"options": TSValidationOptions(imag_tol_cm1=25.0)},
            "options.imag_tol_cm1 25.0 != analysis.imag_tol_cm1 20.0",
        ),
        (
            {"analysis": ThermoAnalysisOptions(imag_tol_cm1=10.0)},
            "!= analysis.imag_tol_cm1 10.0",
        ),
    ],
)
def test_refusals(kwargs: dict[str, Any], fragment: str) -> None:
    """Bad inputs raise TSValidationInputError, a ThermoInputError."""
    hessian, _ = stretch_hessian([-400.0, *VIBRATIONS])
    state = kwargs.pop("state", model_state())
    bonds = kwargs.pop("forming_bonds", [(0, 3)])
    with pytest.raises(TSValidationInputError) as info:
        validate_transition_state(state, hessian, forming_bonds=bonds, **kwargs)
    assert isinstance(info.value, ThermoInputError)
    assert fragment in str(info.value), str(info.value)


# --- Sigma from a bond graph ------------------------------------------------------------------

SYMMETRY_CASES = [
    ("water", g.water(), "O"),
    ("ammonia", g.ammonia(), "N"),
    ("methane", g.methane(), "C"),
    ("ethylene", g.ethylene(), "C=C"),
    ("benzene", g.benzene(), "c1ccccc1"),
    ("CO2", g.co2(), "O=C=O"),
    ("bent CO2", g.co2(bend=1e-4), "O=C=O"),
    ("HCN", g.hcn(), "C#N"),
    ("n-butane anti", g.butane(180.0), "CCCC"),
    ("n-butane gauche", g.butane(60.0), "CCCC"),
    ("water, H moved 0.2 A", g.water(h_shift=0.2), "O"),
    ("neopentane", g.neopentane(), "CC(C)(C)C"),
    ("argon", g.state(["Ar"], [[0.0, 0.0, 0.0]]), "[Ar]"),
]


def smiles_bonds(smiles: str) -> list[tuple[int, int]]:
    """Return the bonds of ``Chem.AddHs(smiles)`` (the state atom order)."""
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    return [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]


@pytest.mark.parametrize(("name", "st", "smiles"), SYMMETRY_CASES)
def test_sigma_from_bonds_equals_sigma_from_smiles(
    name: str, st: MolecularState, smiles: str
) -> None:
    """On every molecule of the symmetry tests, sigma from the bonds equals sigma from SMILES."""
    from_smiles = rotational_symmetry_number(st, smiles, analysis=ANALYSIS)
    from_bonds = rotational_symmetry_number_from_bonds(st, smiles_bonds(smiles), analysis=ANALYSIS)
    assert from_bonds == from_smiles, name


@pytest.mark.parametrize(
    ("bonds", "fragment"),
    [([(0, 0)], "is not a pair"), ([(0, 9)], "is not a pair"), ([(0, 1), (1, 0)], "twice")],
)
def test_sigma_from_bonds_refuses_bad_bonds(bonds: list[tuple[int, int]], fragment: str) -> None:
    """Bonds out of range, to the same atom or repeated are refused."""
    with pytest.raises(ThermoInputError, match=fragment):
        rotational_symmetry_number_from_bonds(g.water(), bonds, analysis=ANALYSIS)


def read_xyz(path: Path) -> MolecularState:
    """Return the neutral singlet state of an XYZ file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0])
    rows = [line.split() for line in lines[2 : 2 + n]]
    return MolecularState(
        symbols=[r[0] for r in rows],
        coordinates=[[float(v) for v in r[1:4]] for r in rows],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0, 1, 2, 3, 4, 5],
    )


def test_ts1a_n_sigma_is_one() -> None:
    """TS1a_n with its perceived bonds has sigma 1 (mission HF-8)."""
    from eta_rxncat.mapping import perceive_bonds

    ts = read_xyz(TS1A_N)
    assert rotational_symmetry_number_from_bonds(ts, perceive_bonds(ts), analysis=ANALYSIS) == 1


# --- TS thermochemistry -----------------------------------------------------------------------


def butane_ts() -> tuple[MolecularState, Array, list[tuple[int, int]]]:
    """Return anti n-butane with one imaginary mode injected into a minimum's spectrum."""
    st = g.butane(180.0)
    n_modes = 3 * len(st.symbols) - 6
    frequencies = [-350.0] + [150.0 + 90.0 * k for k in range(n_modes - 1)]
    return st, g.hessian_with_modes(st, frequencies, linear=False), smiles_bonds("CCCC")


def butane_validation(st: MolecularState, hessian: Array) -> Any:
    """Validate the butane 'TS' (a C-C pair as the forming bond); only the mode count matters."""
    active = st.model_copy(update={"active_atom_indices": [0, 1, 2, 3]})
    return validate_transition_state(active, hessian, forming_bonds=[(0, 3)])


def test_ts_thermochemistry_equals_the_minimum_path_body() -> None:
    """ts_thermochemistry equals _thermochemistry with the same sigma (1e-12 Eh)."""
    st, hessian, bonds = butane_ts()
    validation = butane_validation(st, hessian)
    assert validation.mode_count_passed_bool
    result = ts_thermochemistry(
        st, hessian, -158.1, validation=validation, bonds=bonds, energy_source="optimization"
    )
    sigma = rotational_symmetry_number_from_bonds(st, bonds, analysis=ANALYSIS)
    reference = _thermochemistry(
        st,
        hessian,
        -158.1,
        sigma,
        energy_source="optimization",
        config=ThermoConfig(),
        analysis=ANALYSIS,
    )
    assert result.rotational_symmetry_number == sigma == 2
    assert result.imaginary_frequencies_cm1 == [pytest.approx(-350.0, abs=1e-6)]
    for field in (
        "gibbs_free_energy_hartree",
        "thermal_correction_enthalpy_hartree",
        "thermal_correction_gibbs_hartree",
        "zpe_hartree",
    ):
        assert abs(getattr(result, field) - getattr(reference, field)) <= 1e-12, field
    assert result == reference


def test_ts_thermochemistry_refuses_a_failed_mode_count() -> None:
    """A validation whose mode count failed is refused."""
    st, _, bonds = butane_ts()
    n_modes = 3 * len(st.symbols) - 6
    two = g.hessian_with_modes(
        st, [-350.0, -120.0] + [150.0 + 90.0 * k for k in range(n_modes - 2)], linear=False
    )
    validation = butane_validation(st, two)
    assert not validation.mode_count_passed_bool
    with pytest.raises(ThermoInputError, match="mode count passed"):
        ts_thermochemistry(
            st, two, -158.1, validation=validation, bonds=bonds, energy_source="optimization"
        )


def test_ts_thermochemistry_refuses_a_different_imaginary_mode() -> None:
    """A validation of another Hessian (imaginary -350 vs -500 cm^-1) is refused."""
    st, hessian, bonds = butane_ts()
    validation = butane_validation(st, hessian)
    n_modes = 3 * len(st.symbols) - 6
    other = g.hessian_with_modes(
        st, [-500.0] + [150.0 + 90.0 * k for k in range(n_modes - 1)], linear=False
    )
    with pytest.raises(ThermoInputError, match="do not match the validated"):
        ts_thermochemistry(
            st, other, -158.1, validation=validation, bonds=bonds, energy_source="optimization"
        )


# --- The minimum path is unchanged ---------------------------------------------------------------

# sha256 of thermochemistry(...).model_dump_json(), recorded by running the same inputs on the
# code at the slice's Start commit 4c4dfdf (before the _thermochemistry refactor).
START_RESULT_SHA256 = {
    "butane_anti": "0ca842484cb90cbf6c3b48d5788562073c880ffed69f2d8ebc6973fc55bdb0c0",
    "water": "5fa6819a6facc1edecbce13211f87f73c06a14109d41b82da07fe8a9529a78f2",
}
START_GIBBS_HARTREE = {"butane_anti": -157.97675644896748, "water": -158.1147545665069}


@pytest.mark.parametrize(
    ("name", "st", "smiles"), [("butane_anti", g.butane(180.0), "CCCC"), ("water", g.water(), "O")]
)
def test_minimum_path_output_unchanged_since_start(
    name: str, st: MolecularState, smiles: str
) -> None:
    """The minimum path returns byte-identical ThermoResult JSON to the pre-refactor code."""
    n_modes = 3 * len(st.symbols) - 6
    hessian = g.hessian_with_modes(st, [100.0 + 97.0 * k for k in range(n_modes)], linear=False)
    result = thermochemistry(st, hessian, -158.1, smiles=smiles, energy_source="optimization")
    assert result.gibbs_free_energy_hartree == START_GIBBS_HARTREE[name]
    digest = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
    assert digest == START_RESULT_SHA256[name]


# --- Real data: TJ's TS1a_n on GFN2 (marker xtb; deselected by default, never skipped) ----------


@pytest.mark.xtb
def test_ts1a_n_gfn2_passes_the_validator() -> None:
    """GFN2 Hessian of TS1a_n: one mode at -416 +/- 5 cm^-1, fraction >= 0.60, overlap >= 0.50."""
    from eta_rxncat.engines import XTBSubprocessEngine

    ts = read_xyz(TS1A_N)
    engine = XTBSubprocessEngine.from_stage(
        StageConfig(kind="frequency", engine="xtb_subprocess", method="gfn2"), threads=1
    )
    potential = engine.evaluate(ts, forces=True, hessian=True)
    result = validate_transition_state(
        ts, potential.hessian_hartree_per_bohr2, forming_bonds=[(1, 2), (3, 5)]
    )
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    assert result.n_imaginary == 1
    assert result.imaginary_frequency_cm1 == pytest.approx(-416.2, abs=5.0)
    assert result.active_core_ke_fraction is not None
    assert result.active_core_ke_fraction >= 0.60
    assert result.forming_stretch_overlap is not None
    assert result.forming_stretch_overlap >= 0.50
    assert result.passed_bool, result.reasons


# --- Imports ------------------------------------------------------------------------------------


def test_ts_module_loads_no_optimizer_or_engine_library() -> None:
    """Importing eta_rxncat.thermo.ts loads no geomeTRIC, torch, PySCF or fairchem."""
    heavy = ("geometric", "torch", "pyscf", "fairchem")
    code = (
        "import json, sys\n"
        "import eta_rxncat.thermo.ts\n"
        f"print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in {heavy!r})))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


def test_thermo_imports_neither_mapping_nor_orchestrator() -> None:
    """No module of thermo/ imports eta_rxncat.mapping or eta_rxncat.orchestrator."""
    hits = []
    for path in sorted(THERMO_SRC.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            hits += [
                f"{path.name}:{name}"
                for name in names
                if name.startswith(("eta_rxncat.mapping", "eta_rxncat.orchestrator"))
            ]
    assert hits == []
