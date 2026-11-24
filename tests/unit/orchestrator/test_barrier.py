"""Tests for the v0.5.0 activation barrier (slice 06): sums, standard state, conservation, Liu."""

import ast
import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from rdkit import Chem

from eta_rxncat.core import (
    ConformerEnsemble,
    ConformerRecord,
    FormingBond,
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    StageConfig,
    ThermoAnalysisOptions,
    ThermoConfig,
    ThermoResult,
    TransitionStateRecord,
    TSSearchResult,
    TSValidation,
    TSValidationOptions,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import (
    BarrierEnergies,
    BarrierSpec,
    activation_free_energy,
    standard_state_shift_kcal_mol,
)

REPO = Path(__file__).parents[3]
XYZ = REPO / "tests" / "e2e" / "data" / "e2e5" / "xyz"
BARRIER_SRC = REPO / "src" / "eta_rxncat" / "orchestrator" / "barrier.py"
CONFIG = ThermoConfig()
SHIFT = standard_state_shift_kcal_mol(CONFIG)
CP, CPE = "C1=CCC=C1", "C1=CC1"
COMPONENTS = {
    "translational": 5.0e-5,
    "rotational": 3.0e-5,
    "vibrational": 2.0e-5,
    "electronic": 0.0,
}


def read_xyz(name: str, charge: int = 0, multiplicity: int = 1) -> MolecularState:
    """Return the state of one of TJ's committed XYZ files."""
    lines = (XYZ / name).read_text(encoding="utf-8").splitlines()
    rows = [line.split() for line in lines[2 : 2 + int(lines[0])]]
    return MolecularState(
        symbols=[r[0] for r in rows],
        coordinates=[[float(v) for v in r[1:4]] for r in rows],
        charge=charge,
        spin_multiplicity=multiplicity,
    )


def thermo(
    n_atoms: int,
    energy: float,
    h_corr: float,
    g_corr: float,
    *,
    imaginary: float | None = None,
    config: ThermoConfig = CONFIG,
) -> ThermoResult:
    """Return a self-consistent ThermoResult with chosen E, H - E and G - E (Eh)."""
    n_modes = 3 * n_atoms - 6
    positive = [100.0 + 50.0 * k for k in range(n_modes - (imaginary is not None))]
    frequencies = ([imaginary] if imaginary is not None else []) + positive
    return ThermoResult(
        n_atoms=n_atoms,
        electronic_energy_hartree=energy,
        energy_source="optimization",
        zpe_hartree=0.1,
        thermal_correction_enthalpy_hartree=h_corr,
        thermal_correction_gibbs_hartree=g_corr,
        entropy_hartree_per_k=math.fsum(COMPONENTS.values()),
        entropy_components_hartree_per_k=dict(COMPONENTS),
        gibbs_free_energy_hartree=energy + g_corr,
        standard_state_correction_hartree=0.003,
        frequencies_cm1=frequencies,
        imaginary_frequencies_cm1=[] if imaginary is None else [imaginary],
        soft_modes_cm1=[],
        rotational_symmetry_number=1,
        is_linear=False,
        config=config,
        analysis=ThermoAnalysisOptions(),
        masses_source="test",
    )


def record(state: MolecularState, t: ThermoResult) -> ConformerRecord:
    """Return a conformer record of ``state`` with thermo ``t``."""
    optimization = OptimizationResult(
        final_state=state,
        final_energy_hartree=t.electronic_energy_hartree,
        converged=True,
        n_steps=1,
        n_engine_calls=1,
        recovery_steps=[],
        optimizer=OptimizerIdentity(name="geometric", version="1.1.1"),
        options={},
    )
    return ConformerRecord(
        state=state, optimization=optimization, thermo=t, degeneracy=1, source_ids=[0]
    )


def ensemble(
    species_id: str, smiles: str, records: list[ConformerRecord], weights: list[float], g: float
) -> ConformerEnsemble:
    """Return an ensemble of ``records`` with the given weights and ensemble G (Eh)."""
    gibbs = [r.thermo.gibbs_free_energy_hartree for r in records]
    return ConformerEnsemble(
        species_id=species_id,
        smiles=smiles,
        records=records,
        boltzmann_weights=weights,
        lowest_index=min(range(len(gibbs)), key=lambda i: (gibbs[i], i)),
        ensemble_gibbs_hartree=g,
        temperature_k=records[0].thermo.config.temperature_k,
    )


def ts_record(
    state: MolecularState, t: ThermoResult, ts_id: str = "TS1a_n"
) -> TransitionStateRecord:
    """Return a TS record of ``state`` with thermo ``t`` (one imaginary mode)."""
    search = TSSearchResult(
        final_state=state,
        final_energy_hartree=t.electronic_energy_hartree,
        converged=True,
        n_steps=1,
        n_gradient_calls=1,
        n_hessian_calls=1,
        n_hessian_refreshes=0,
        n_rejected_steps=0,
        hessian_method="analytic",
        followed_eigenvalue_hartree_per_bohr2=-0.05,
        final_max_gradient_hartree_per_bohr=0.0,
        final_rms_gradient_hartree_per_bohr=0.0,
        final_rigid_gradient_norm_hartree_per_bohr=0.0,
        forming_bonds=[FormingBond(i=1, j=2), FormingBond(i=3, j=5)],
        optimizer=OptimizerIdentity(name="prfo", version="src-0123456789abcdef"),
        options={},
        history=[],
    )
    validation = TSValidation(
        n_imaginary=1,
        imaginary_frequency_cm1=t.imaginary_frequencies_cm1[0],
        active_core_ke_fraction=0.93,
        forming_stretch_overlap=0.8,
        forming_bonds_in_phase_bool=True,
        forming_distances_angstrom={"1-2": 2.3, "3-5": 2.3},
        options=TSValidationOptions(),
        active_atom_indices=[0, 1, 2, 3, 4, 5],
        mode_count_passed_bool=True,
        active_core_passed_bool=True,
        identity_passed_bool=True,
        passed_bool=True,
        reasons=[],
    )
    return TransitionStateRecord(
        ts_id=ts_id, state=state, search=search, validation=validation, thermo=t, degeneracy=1
    )


def spec(**overrides: Any) -> BarrierSpec:
    """Return the Cp + cyclopropene barrier spec of TS1a_n."""
    values: dict[str, Any] = {
        "reactants": (("cp", 1), ("cpe", 1)),
        "ts_id": "TS1a_n",
        "smiles": {"cp": CP, "cpe": CPE},
    }
    values.update(overrides)
    return BarrierSpec(**values)


# --- Hand-built bimolecular case (Δn = -1) -------------------------------------------------------

CP_STATE, CPE_STATE, TS_STATE = (
    read_xyz("1_cyclopentadiene.xyz"),
    read_xyz("5_cyclopropene.xyz"),
    read_xyz("TS1a_n.xyz"),
)
CP_RECORDS = [
    record(CP_STATE, thermo(11, -194.000, 0.090, 0.060)),
    record(CP_STATE, thermo(11, -193.998, 0.091, 0.059)),
]
CP_WEIGHTS = [0.7, 0.3]
CP_G = -193.9405
CPE_RECORDS = [record(CPE_STATE, thermo(7, -116.560, 0.060, 0.035))]
CPE_G = -116.525
TS_THERMO = thermo(18, -310.540, 0.150, 0.105, imaginary=-450.0)


def bimolecular() -> tuple[dict[str, ConformerEnsemble], TransitionStateRecord]:
    """Return the hand-built reactant ensembles and TS record."""
    ensembles = {
        "cp": ensemble("cp", CP, CP_RECORDS, CP_WEIGHTS, CP_G),
        "cpe": ensemble("cpe", CPE, CPE_RECORDS, [1.0], CPE_G),
    }
    return ensembles, ts_record(TS_STATE, TS_THERMO)


def test_bimolecular_equals_hand_sums() -> None:
    """dE, dH, dG(1 M) equal the hand sums; dG(1 atm) - dG(1 M) = +RT ln(cRT/p) for Δn = -1."""
    ensembles, ts = bimolecular()
    result = activation_free_energy(spec(), ensembles, ts, CONFIG)
    cp_e = 0.7 * -194.000 + 0.3 * -193.998
    cp_h = 0.7 * (-194.000 + 0.090) + 0.3 * (-193.998 + 0.091)
    cpe_e, cpe_h = -116.560, -116.560 + 0.060
    expected_e = (-310.540 - (cp_e + cpe_e)) * HARTREE_KCAL_MOL
    expected_h = (-310.540 + 0.150 - (cp_h + cpe_h)) * HARTREE_KCAL_MOL
    expected_g = (-310.540 + 0.105 - (CP_G + CPE_G)) * HARTREE_KCAL_MOL
    assert result.delta_n == -1
    assert abs(result.dE_dagger_kcal_mol - expected_e) <= 1e-9
    assert abs(result.dH_dagger_kcal_mol - expected_h) <= 1e-9
    assert abs(result.dG_dagger_1M_kcal_mol - expected_g) <= 1e-9
    shift = result.dG_dagger_1atm_kcal_mol - result.dG_dagger_1M_kcal_mol
    assert abs(shift - SHIFT) <= 1e-9
    assert SHIFT == pytest.approx(1.8943, abs=1e-4)


def butadiene_state(charge: int = 0, multiplicity: int = 1) -> MolecularState:
    """Return a C4H6 state in AddHs(C=CC=C) atom order (coordinates are placeholders)."""
    mol = Chem.AddHs(Chem.MolFromSmiles("C=CC=C"))
    symbols = [a.GetSymbol() for a in mol.GetAtoms()]
    return MolecularState(
        symbols=symbols,
        coordinates=[[1.1 * i, 0.3 * (i % 2), 0.1 * (i % 3)] for i in range(len(symbols))],
        charge=charge,
        spin_multiplicity=multiplicity,
    )


def test_unimolecular_has_no_standard_state_shift() -> None:
    """Δn = 0 (a rotation TS of butadiene): dG(1 atm) equals dG(1 M)."""
    state = butadiene_state()
    reactant = ensemble(
        "bd", "C=CC=C", [record(state, thermo(10, -155.0, 0.09, 0.06))], [1.0], -154.94
    )
    ts = ts_record(state, thermo(10, -154.99, 0.089, 0.061, imaginary=-200.0), ts_id="TS-rot")
    result = activation_free_energy(
        BarrierSpec(reactants=(("bd", 1),), ts_id="TS-rot", smiles={"bd": "C=CC=C"}),
        {"bd": reactant},
        ts,
        CONFIG,
    )
    assert result.delta_n == 0
    assert abs(result.dG_dagger_1atm_kcal_mol - result.dG_dagger_1M_kcal_mol) <= 1e-9
    assert (
        abs(result.dG_dagger_1M_kcal_mol - ((-154.99 + 0.061) - -154.94) * HARTREE_KCAL_MOL) <= 1e-9
    )


# --- Liu check (tier D, mission HF-9) ------------------------------------------------------------

# Header energies of TJ's SOURCES.md (Liu & Houk JACS 2013 SI; Gaussian, 1 atm): E and G in Eh.
LIU = {
    "cp": (-194.004692, -193.937241),
    "cpe": (-116.562552, -116.529371),
    "ts": (-310.559154, -310.435319),
}


def test_liu_ts1a_n_barrier() -> None:
    """Liu's 1 atm G values, moved to eta's 1 M standard state, give 19.637 (1 atm), 17.742 (1 M).

    Each species' 1 atm G is shifted by +RT ln(cRT/p) to the 1 M G that eta's records carry.
    """
    to_1m = SHIFT / HARTREE_KCAL_MOL

    def species(key: str, state: MolecularState, smiles: str) -> ConformerEnsemble:
        e, g = LIU[key]
        t = thermo(len(state.symbols), e, 0.1, g + to_1m - e)
        return ensemble(key, smiles, [record(state, t)], [1.0], g + to_1m)

    e_ts, g_ts = LIU["ts"]
    ts = ts_record(TS_STATE, thermo(18, e_ts, 0.15, g_ts + to_1m - e_ts, imaginary=-416.2))
    ensembles = {"cp": species("cp", CP_STATE, CP), "cpe": species("cpe", CPE_STATE, CPE)}
    result = activation_free_energy(spec(), ensembles, ts, CONFIG)
    assert result.dG_dagger_1atm_kcal_mol == pytest.approx(19.637, abs=1e-3)
    assert result.dG_dagger_1M_kcal_mol == pytest.approx(17.742, abs=1e-3)
    assert result.dE_dagger_kcal_mol == pytest.approx(
        (e_ts - LIU["cp"][0] - LIU["cpe"][0]) * HARTREE_KCAL_MOL, abs=1e-9
    )


# --- Refusals ------------------------------------------------------------------------------------


def test_reactants_short_by_one_hydrogen() -> None:
    """A cyclopentadienyl radical (C5H5) instead of Cp leaves the TS one H over."""
    ensembles, ts = bimolecular()
    short = spec(smiles={"cp": "[CH]1C=CC=C1", "cpe": CPE})
    with pytest.raises(
        ValueError,
        match=r"atoms not conserved: reactants \{'C': 8, 'H': 9\}, TS \{'C': 8, 'H': 10\}",
    ):
        activation_free_energy(short, ensembles, ts, CONFIG)


def test_wrong_charge() -> None:
    """A cationic TS (same atoms) is not conserved against neutral reactants."""
    ensembles, _ = bimolecular()
    cation = read_xyz("TS1a_n.xyz", charge=1, multiplicity=2)
    ts = ts_record(cation, TS_THERMO)
    with pytest.raises(ValueError, match="charge not conserved: reactants 0, TS 1"):
        activation_free_energy(spec(), ensembles, ts, CONFIG)


def test_mismatched_ts_id() -> None:
    """A TS record of another id is refused."""
    ensembles, _ = bimolecular()
    with pytest.raises(ValueError, match="'TS1b_n' is not the spec's 'TS1a_n'"):
        activation_free_energy(spec(), ensembles, ts_record(TS_STATE, TS_THERMO, "TS1b_n"), CONFIG)


def test_reactant_temperature_mismatch() -> None:
    """An ensemble at 300 K is refused for a 298.15 K barrier."""
    ensembles, ts = bimolecular()
    hot = ThermoConfig(temperature_k=300.0)
    ensembles["cpe"] = ensemble(
        "cpe", CPE, [record(CPE_STATE, thermo(7, -116.56, 0.06, 0.035, config=hot))], [1.0], CPE_G
    )
    with pytest.raises(ValueError, match="ensemble 'cpe' is not at 298.15 K"):
        activation_free_energy(spec(), ensembles, ts, CONFIG)


def test_ts_temperature_mismatch() -> None:
    """A TS thermo at 300 K is refused for a 298.15 K barrier."""
    ensembles, _ = bimolecular()
    hot = thermo(
        18, -310.54, 0.15, 0.105, imaginary=-450.0, config=ThermoConfig(temperature_k=300.0)
    )
    with pytest.raises(ValueError, match="TS 'TS1a_n' thermo is not at 298.15 K"):
        activation_free_energy(spec(), ensembles, ts_record(TS_STATE, hot), CONFIG)


@pytest.mark.parametrize(
    "other", [ThermoConfig(standard_state_mol_l=0.0409), ThermoConfig(pressure_atm=2.0)]
)
def test_mixed_standard_state_refused(other: ThermoConfig) -> None:
    """R51: a reactant or the TS at another standard state or pressure is refused, by name."""
    ensembles, ts = bimolecular()
    mixed = dict(ensembles)
    mixed["cpe"] = ensemble(
        "cpe", CPE, [record(CPE_STATE, thermo(7, -116.56, 0.06, 0.035, config=other))], [1.0], CPE_G
    )
    with pytest.raises(ValueError, match="species 'cpe' record 0: thermo config"):
        activation_free_energy(spec(), mixed, ts, CONFIG)
    ts_other = ts_record(TS_STATE, thermo(18, -310.54, 0.15, 0.105, imaginary=-450.0, config=other))
    with pytest.raises(ValueError, match="TS 'TS1a_n': thermo config"):
        activation_free_energy(spec(), ensembles, ts_other, CONFIG)


def test_missing_ensemble_is_a_key_error() -> None:
    """A reactant without an ensemble raises KeyError."""
    ensembles, ts = bimolecular()
    del ensembles["cpe"]
    with pytest.raises(KeyError):
        activation_free_energy(spec(), ensembles, ts, CONFIG)


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"smiles": {"cp": CP}}, "reactant 'cpe' has no SMILES"),
        ({"smiles": {"cp": CP, "cpe": "C1=C("}}, "SMILES of 'cpe' does not parse"),
        ({"reactants": ()}, "at least 1 item"),
        ({"ts_id": ""}, "at least 1 character"),
        ({"reactants": (("cp", 0),)}, "greater than or equal to 1"),
    ],
)
def test_barrier_spec_refusals(overrides: dict[str, Any], fragment: str) -> None:
    """BarrierSpec needs SMILES for every reactant, parsable, and positive coefficients."""
    with pytest.raises(ValidationError, match=fragment):
        spec(**overrides)


def test_energies_model_is_strict() -> None:
    """BarrierEnergies forbids extra keys and is frozen."""
    value = BarrierEnergies(
        dE_dagger_kcal_mol=1.0,
        dH_dagger_kcal_mol=1.0,
        dG_dagger_1atm_kcal_mol=1.0,
        dG_dagger_1M_kcal_mol=1.0,
        delta_n=0,
    )
    with pytest.raises(ValidationError):
        BarrierEnergies(**value.model_dump(), extra=1)
    with pytest.raises(ValidationError):
        value.delta_n = 1  # type: ignore[misc]


def test_no_reaction_spec_for_a_ts() -> None:
    """The barrier code never uses ReactionSpec or reaction_free_energy (R1); docstrings aside."""
    tree = ast.parse(BARRIER_SRC.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    names |= {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert {"ReactionSpec", "reaction_free_energy"} & names == set()


# --- Energy source (audit 05 note): frequency-run E equals gradient-run E on xtb -----------------


@pytest.mark.xtb
def test_xtb_hessian_run_energy_equals_gradient_run_energy() -> None:
    """At TS1a_n, xtb's Hessian-run energy equals its gradient-run energy (measured: exactly).

    The TS runner gives ts_thermochemistry the frequency stage's energy; ground-state records
    carry the optimizer's final energy. This pins them as the same engine energy at one geometry.
    """
    from eta_rxncat.engines import XTBSubprocessEngine

    engine = XTBSubprocessEngine.from_stage(
        StageConfig(kind="frequency", engine="xtb_subprocess", method="gfn2"), threads=1
    )
    gradient_run = engine.evaluate(TS_STATE, forces=True, hessian=False).energy_hartree
    hessian_run = engine.evaluate(TS_STATE, forces=False, hessian=True).energy_hartree
    print(f"gradient {gradient_run!r} hessian {hessian_run!r} diff {hessian_run - gradient_run!r}")
    assert hessian_run == gradient_run
