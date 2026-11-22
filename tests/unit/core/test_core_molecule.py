"""Tests for MolecularState: required charge/multiplicity, strict ints, shapes, electrons."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import ATOMIC_NUMBERS, ELEMENT_SYMBOLS, MolecularState

WATER_COORDS = [[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]]


def water(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a neutral singlet water, with overrides applied."""
    data: dict[str, Any] = {
        "symbols": ["O", "H", "H"],
        "coordinates": WATER_COORDS,
        "charge": 0,
        "spin_multiplicity": 1,
    }
    data.update(overrides)
    return data


def test_element_table_covers_z_1_to_118() -> None:
    """The element table has 118 unique canonical symbols in Z order."""
    assert len(ELEMENT_SYMBOLS) == 118 == len(set(ELEMENT_SYMBOLS))
    assert ATOMIC_NUMBERS["H"] == 1 and ATOMIC_NUMBERS["Fe"] == 26 and ATOMIC_NUMBERS["Og"] == 118


@pytest.mark.parametrize("missing", ["charge", "spin_multiplicity"])
def test_charge_and_multiplicity_are_required(missing: str) -> None:
    """Omitting charge or spin multiplicity raises."""
    data = water()
    del data[missing]
    with pytest.raises(ValidationError, match=missing):
        MolecularState(**data)


@pytest.mark.parametrize("field", ["charge", "spin_multiplicity"])
@pytest.mark.parametrize("value", ["1", 1.0, True])
def test_charge_and_multiplicity_are_strict_ints(field: str, value: object) -> None:
    """A string, float or bool charge or multiplicity is rejected, not coerced."""
    with pytest.raises(ValidationError, match=field):
        MolecularState(**water(**{field: value}))


def test_multiplicity_zero_rejected() -> None:
    """Spin multiplicity must be at least 1."""
    with pytest.raises(ValidationError, match="spin_multiplicity"):
        MolecularState(**water(spin_multiplicity=0))


@pytest.mark.parametrize("symbol", ["fe", "FE", "Xx"])
def test_non_canonical_symbols_rejected(symbol: str) -> None:
    """Symbols must match the canonical case of a real element."""
    with pytest.raises(ValidationError, match="element symbol"):
        MolecularState(
            symbols=[symbol], coordinates=[[0.0, 0.0, 0.0]], charge=0, spin_multiplicity=1
        )


def test_canonical_two_letter_symbol_accepted() -> None:
    """``Fe`` is a valid symbol (neutral Fe atom, quintet)."""
    state = MolecularState(
        symbols=["Fe"], coordinates=[[0.0, 0.0, 0.0]], charge=0, spin_multiplicity=5
    )
    assert state.symbols == ["Fe"]


def test_symbol_and_coordinate_counts_must_match() -> None:
    """Two symbols with three coordinate rows raises."""
    with pytest.raises(ValidationError, match="coordinate rows"):
        MolecularState(**water(symbols=["H", "H"]))


def test_coordinate_rows_have_three_values() -> None:
    """A coordinate row of length 2 raises."""
    coords = [WATER_COORDS[0], WATER_COORDS[1], [0.0, 1.0]]
    with pytest.raises(ValidationError, match="coordinate row 2"):
        MolecularState(**water(coordinates=coords))


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_coordinates_must_be_finite(bad: float) -> None:
    """NaN or infinite coordinates raise."""
    coords = [WATER_COORDS[0], WATER_COORDS[1], [0.0, bad, 0.0]]
    with pytest.raises(ValidationError, match="finite"):
        MolecularState(**water(coordinates=coords))


@pytest.mark.parametrize(
    ("indices", "message"), [([-1], "out of range"), ([3], "out of range"), ([1, 1], "duplicate")]
)
def test_active_atom_indices_checked(indices: list[int], message: str) -> None:
    """Active indices must be unique and within ``0 <= i < N``."""
    with pytest.raises(ValidationError, match=message):
        MolecularState(**water(active_atom_indices=indices))


def test_unknown_key_rejected() -> None:
    """A misspelt key such as ``chrage`` is rejected."""
    with pytest.raises(ValidationError, match="chrage"):
        MolecularState(**water(chrage=0))


def test_neutral_water_doublet_rejected() -> None:
    """Neutral water has 10 electrons, so a doublet is impossible."""
    with pytest.raises(ValidationError, match="impossible"):
        MolecularState(**water(spin_multiplicity=2))


def test_neutral_water_singlet_accepted() -> None:
    """Neutral singlet water validates."""
    assert MolecularState(**water()).charge == 0


def test_water_cation_doublet_accepted() -> None:
    """H2O+ has 9 electrons, so a doublet validates."""
    assert MolecularState(**water(charge=1, spin_multiplicity=2)).spin_multiplicity == 2


def test_negative_electron_count_rejected() -> None:
    """An H atom with charge +2 would have -1 electrons."""
    with pytest.raises(ValidationError, match="electrons"):
        MolecularState(symbols=["H"], coordinates=[[0.0, 0.0, 0.0]], charge=2, spin_multiplicity=1)


def test_state_is_frozen() -> None:
    """States are immutable after construction."""
    state = MolecularState(**water())
    with pytest.raises(ValidationError):
        state.charge = 1  # type: ignore[misc]
