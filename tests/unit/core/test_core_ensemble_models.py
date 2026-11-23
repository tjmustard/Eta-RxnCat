"""Tests for ConformerRecord and ConformerEnsemble (v0.3.0 slice 02)."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    ConformerEnsemble,
    ConformerRecord,
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    ThermoAnalysisOptions,
    ThermoConfig,
    ThermoResult,
)


def state(symbols: tuple[str, ...] = ("O", "H", "H"), charge: int = 0, mult: int = 1) -> Any:
    """Return a three-atom state."""
    return MolecularState(
        symbols=list(symbols),
        coordinates=[[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
        charge=charge,
        spin_multiplicity=mult,
    )


def thermo(gibbs_offset: float = 0.0, n_atoms: int = 3, temperature_k: float = 298.15) -> Any:
    """Return a valid non-linear N = 3 ThermoResult with G = -76.396 + ``gibbs_offset``."""
    s = 8.1e-5
    return ThermoResult(
        n_atoms=n_atoms,
        electronic_energy_hartree=-76.4 + gibbs_offset,
        energy_source="optimization",
        zpe_hartree=0.021,
        thermal_correction_enthalpy_hartree=0.025,
        thermal_correction_gibbs_hartree=0.004,
        entropy_hartree_per_k=s,
        entropy_components_hartree_per_k={
            "translational": 5.0e-5,
            "rotational": 3.0e-5,
            "vibrational": 1.0e-6,
            "electronic": 0.0,
        },
        gibbs_free_energy_hartree=-76.4 + gibbs_offset + 0.004,
        standard_state_correction_hartree=0.003,
        frequencies_cm1=[1595.0, 3657.0, 3756.0][: 3 * n_atoms - 6] if n_atoms > 2 else [2100.0],
        imaginary_frequencies_cm1=[],
        soft_modes_cm1=[],
        rotational_symmetry_number=2,
        is_linear=n_atoms == 2,
        config=ThermoConfig(temperature_k=temperature_k),
        analysis=ThermoAnalysisOptions(),
        masses_source="rdkit",
    )


def record(
    gibbs_offset: float = 0.0,
    *,
    st: Any = None,
    th: Any = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Return keyword arguments for a valid ConformerRecord, with overrides applied."""
    st = st if st is not None else state()
    data: dict[str, Any] = {
        "state": st,
        "optimization": OptimizationResult(
            final_state=st,
            final_energy_hartree=-76.4 + gibbs_offset,
            converged=True,
            n_steps=5,
            n_engine_calls=6,
            recovery_steps=[],
            optimizer=OptimizerIdentity(name="geometric", version="1.1.1"),
            options={},
        ),
        "thermo": th if th is not None else thermo(gibbs_offset),
        "degeneracy": 1,
        "source_ids": [0],
    }
    data.update(overrides)
    return data


def ensemble(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid two-record ensemble, with overrides applied."""
    data: dict[str, Any] = {
        "species_id": "water",
        "smiles": "O",
        "records": [
            ConformerRecord(**record(0.0, source_ids=[0, 2])),
            ConformerRecord(**record(0.001, degeneracy=2, source_ids=[1])),
        ],
        "boltzmann_weights": [0.75, 0.25],
        "lowest_index": 0,
        "ensemble_gibbs_hartree": -76.3965,
        "temperature_k": 298.15,
    }
    data.update(overrides)
    return data


def ensemble_rejected(fragment: str, **overrides: Any) -> None:
    """Assert that ``overrides`` fail ensemble validation with a message containing ``fragment``."""
    with pytest.raises(ValidationError) as info:
        ConformerEnsemble(**ensemble(**overrides))
    assert fragment in str(info.value), str(info.value)


# ConformerRecord


def test_valid_record_round_trips() -> None:
    """A valid record constructs and round-trips through model_dump / model_validate."""
    value = ConformerRecord(**record())
    assert ConformerRecord.model_validate(value.model_dump()) == value


@pytest.mark.parametrize("degeneracy", [1, 2])
def test_degeneracy_one_or_two(degeneracy: int) -> None:
    """Degeneracy 1 and 2 are accepted."""
    assert ConformerRecord(**record(degeneracy=degeneracy)).degeneracy == degeneracy


@pytest.mark.parametrize("degeneracy", [0, 3, True, 2.0])
def test_degeneracy_rejected(degeneracy: object) -> None:
    """Any other degeneracy is rejected."""
    with pytest.raises(ValidationError):
        ConformerRecord(**record(degeneracy=degeneracy))


def test_source_ids_required() -> None:
    """source_ids needs at least one id."""
    with pytest.raises(ValidationError):
        ConformerRecord(**record(source_ids=[]))


def test_duplicate_source_ids_rejected() -> None:
    """source_ids must be unique."""
    with pytest.raises(ValidationError, match="duplicate source_ids"):
        ConformerRecord(**record(source_ids=[3, 1, 3]))


@pytest.mark.parametrize("bad", [-1, True])
def test_source_ids_non_negative_strict(bad: object) -> None:
    """source_ids are non-negative strict ints."""
    with pytest.raises(ValidationError):
        ConformerRecord(**record(source_ids=[bad]))


def test_thermo_atom_count_must_match_state() -> None:
    """thermo.n_atoms must equal the state's atom count."""
    with pytest.raises(ValidationError, match="thermo.n_atoms 2"):
        ConformerRecord(**record(th=thermo(n_atoms=2)))


# ConformerEnsemble


def test_valid_ensemble_round_trips() -> None:
    """A valid ensemble constructs and round-trips through model_dump / model_validate."""
    value = ConformerEnsemble(**ensemble())
    assert ConformerEnsemble.model_validate(value.model_dump()) == value


@pytest.mark.parametrize("field", ["species_id", "smiles"])
def test_identifiers_non_empty(field: str) -> None:
    """species_id and smiles must be non-empty."""
    with pytest.raises(ValidationError):
        ConformerEnsemble(**ensemble(**{field: ""}))


def test_records_required() -> None:
    """An ensemble needs at least one record."""
    with pytest.raises(ValidationError):
        ConformerEnsemble(**ensemble(records=[], boltzmann_weights=[]))


def test_single_record_ensemble() -> None:
    """A one-record ensemble with weight 1 is valid."""
    single = ensemble(records=[ConformerRecord(**record())], boltzmann_weights=[1.0])
    assert ConformerEnsemble(**single).lowest_index == 0


def test_weight_count_must_match() -> None:
    """One weight per record."""
    ensemble_rejected("3 boltzmann_weights for 2 records", boltzmann_weights=[0.5, 0.25, 0.25])


def test_negative_weight_rejected() -> None:
    """Weights are non-negative."""
    ensemble_rejected("negative boltzmann_weights at [1]", boltzmann_weights=[1.25, -0.25])


def test_weights_sum_within_tolerance_passes() -> None:
    """Weights summing to 1 within 1e-12 pass."""
    ConformerEnsemble(**ensemble(boltzmann_weights=[0.75 + 5e-13, 0.25]))


def test_weights_sum_off_rejected() -> None:
    """Weights summing to 1 + 1e-9 are rejected."""
    ensemble_rejected("sum to", boltzmann_weights=[0.75 + 1e-9, 0.25])


def test_lowest_index_must_be_argmin() -> None:
    """lowest_index must point at the lowest G."""
    ensemble_rejected("lowest_index 1 != argmin of G (0)", lowest_index=1)


def test_lowest_index_ties_pick_lowest() -> None:
    """With equal G, the lowest index wins; a later tied index is rejected."""
    tied = [ConformerRecord(**record(0.0)), ConformerRecord(**record(0.0, source_ids=[1]))]
    ConformerEnsemble(**ensemble(records=tied, boltzmann_weights=[0.5, 0.5], lowest_index=0))
    ensemble_rejected("argmin of G (0)", records=tied, boltzmann_weights=[0.5, 0.5], lowest_index=1)


def test_lowest_index_when_second_is_lower() -> None:
    """The argmin is found wherever it is."""
    records = [ConformerRecord(**record(0.002)), ConformerRecord(**record(0.0, source_ids=[1]))]
    ConformerEnsemble(**ensemble(records=records, boltzmann_weights=[0.2, 0.8], lowest_index=1))


def test_mixed_charge_rejected() -> None:
    """All records share the charge."""
    cation = state(charge=1, mult=2)
    records = [ConformerRecord(**record()), ConformerRecord(**record(0.001, st=cation))]
    ensemble_rejected("record 1 charge 1 != 0", records=records)


def test_mixed_multiplicity_rejected() -> None:
    """All records share the spin multiplicity."""
    triplet = state(mult=3)
    records = [ConformerRecord(**record()), ConformerRecord(**record(0.001, st=triplet))]
    ensemble_rejected("record 1 spin_multiplicity 3 != 1", records=records)


def test_mixed_symbols_rejected() -> None:
    """All records share the element symbols in order."""
    other = state(symbols=("S", "H", "H"))
    records = [ConformerRecord(**record()), ConformerRecord(**record(0.001, st=other))]
    ensemble_rejected("record 1 symbols differ", records=records)


def test_temperature_must_match_records() -> None:
    """Every record's thermo temperature equals the ensemble temperature."""
    hot = ConformerRecord(**record(0.001, th=thermo(0.001, temperature_k=310.0)))
    records = [ConformerRecord(**record()), hot]
    ensemble_rejected("records [1] have thermo temperature", records=records)
    ensemble_rejected(
        "records [0] have thermo temperature",
        temperature_k=310.0,
        records=[
            ConformerRecord(**record()),
            ConformerRecord(**record(0.001, th=thermo(0.001, temperature_k=310.0))),
        ],
    )


@pytest.mark.parametrize(
    ("cls", "kwargs", "field"),
    [
        (ConformerRecord, record(), "degeneracy"),
        (ConformerEnsemble, ensemble(), "lowest_index"),
    ],
)
def test_frozen_and_extra_forbidden(cls: type, kwargs: dict[str, Any], field: str) -> None:
    """Both models are frozen (assignment raises) and reject unknown fields."""
    value = cls(**kwargs)
    with pytest.raises(ValidationError):
        setattr(value, field, getattr(value, field))
    with pytest.raises(ValidationError):
        cls(**kwargs, unexpected=1)
