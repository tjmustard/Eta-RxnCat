"""Tests for the Optimizer interface, options, constraints and errors (v0.3.0 slice 04, R42)."""

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import MolecularState, OptimizationResult, OptimizerIdentity
from eta_rxncat.engines import Engine, OptionSpec
from eta_rxncat.optimize import (
    DihedralConstraint,
    OptimizationFailedError,
    Optimizer,
    OptimizerError,
    OptimizerInputError,
    OptimizerUnavailableError,
    check_constraints,
    constraints_text,
)


def water() -> MolecularState:
    """Return a neutral singlet water molecule."""
    return MolecularState(
        symbols=["O", "H", "H"],
        coordinates=[[0.0, 0.0, 0.117], [0.0, 0.757, -0.467], [0.0, -0.757, -0.467]],
        charge=0,
        spin_multiplicity=1,
    )


class Toy(Optimizer):
    """A minimal concrete optimizer for the base-class behaviour."""

    OPTIONS: Mapping[str, OptionSpec] = {
        "mode": OptionSpec(str, "a", frozenset({"a", "b"})),
        "steps": OptionSpec(int, 3),
        "scale": OptionSpec(float, 0.5),
        "flag": OptionSpec(bool, False),
    }

    @property
    def identity(self) -> OptimizerIdentity:
        """Pretend to be geomeTRIC."""
        return OptimizerIdentity(name="geometric", version="0")

    def minimize(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        frozen_atom_indices: Sequence[int] = (),
        dihedral_constraints: Sequence[DihedralConstraint] = (),
        options: Mapping[str, Any] | None = None,
    ) -> OptimizationResult:
        """Not used."""
        raise NotImplementedError


def test_error_hierarchy() -> None:
    """Every optimizer error is an OptimizerError and none is a ValueError."""
    for cls in (OptimizerUnavailableError, OptimizerInputError, OptimizationFailedError):
        assert issubclass(cls, OptimizerError)
        assert not issubclass(cls, ValueError)


def test_failed_error_records_steps_and_energy() -> None:
    """OptimizationFailedError carries the steps tried and the last energy."""
    err = OptimizationFailedError("no", steps=("tric", "cartesian"), last_energy_hartree=-1.5)
    assert err.steps == ("tric", "cartesian")
    assert err.last_energy_hartree == -1.5
    assert "tric" in str(err)


def test_resolved_options_defaults_and_coercion() -> None:
    """Every option is filled; an int given for a float key becomes a float."""
    assert Toy().resolved_options(None) == {"flag": False, "mode": "a", "scale": 0.5, "steps": 3}
    resolved = Toy().resolved_options({"scale": 1, "mode": "b"})
    assert resolved["scale"] == 1.0 and isinstance(resolved["scale"], float)
    assert resolved["mode"] == "b"


def test_resolved_options_explicit_default_keys_the_same() -> None:
    """A default given explicitly resolves identically to leaving it out (ADR-0016)."""
    assert Toy().resolved_options({"steps": 3}) == Toy().resolved_options({})


@pytest.mark.parametrize(
    ("options", "fragment"),
    [
        ({"unknown": 1}, "unknown option"),
        ({"steps": 2.0}, "must be int"),
        ({"steps": True}, "must be int"),
        ({"flag": 1}, "must be bool"),
        ({"mode": "c"}, "not in"),
    ],
)
def test_resolved_options_rejects(options: dict[str, Any], fragment: str) -> None:
    """Unknown, mistyped and disallowed options raise OptimizerInputError."""
    with pytest.raises(OptimizerInputError, match=fragment):
        Toy().resolved_options(options)


def test_dihedral_constraint_valid() -> None:
    """Four distinct non-negative ints and a value in (-180, 180]."""
    c = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=180)
    assert c.atoms == (0, 1, 2, 3)
    assert c.value_deg == 180.0
    assert isinstance(c.value_deg, float)


@pytest.mark.parametrize(
    ("atoms", "value", "fragment"),
    [
        ((0, 1, 1, 3), 0.0, "distinct"),
        ((0, 1, 2), 0.0, "four ints"),
        ((0, 1, 2, 3, 4), 0.0, "four ints"),
        ((0, 1, 2, -1), 0.0, ">= 0"),
        ((0, 1, 2, True), 0.0, "four ints"),
        ((0, 1, 2, 3.0), 0.0, "four ints"),
        ((0, 1, 2, 3), 200.0, r"\(-180, 180\]"),
        ((0, 1, 2, 3), -180.0, r"\(-180, 180\]"),
        ((0, 1, 2, 3), float("nan"), r"\(-180, 180\]"),
        ((0, 1, 2, 3), "0", "must be a number"),
    ],
)
def test_dihedral_constraint_rejects(atoms: Any, value: Any, fragment: str) -> None:
    """Repeated, missing or negative indices and out-of-range values raise OptimizerInputError."""
    with pytest.raises(OptimizerInputError, match=fragment):
        DihedralConstraint(atoms=atoms, value_deg=value)


def test_dihedral_constraint_frozen_and_strict() -> None:
    """The model is frozen and rejects unknown fields."""
    c = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    with pytest.raises(ValidationError):
        c.value_deg = 1.0  # type: ignore[misc]
    with pytest.raises(ValidationError):
        DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0, unit="deg")  # type: ignore[call-arg]


def test_dihedral_index_beyond_state_rejected() -> None:
    """An index >= N raises OptimizerInputError when checked against the state."""
    c = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    with pytest.raises(OptimizerInputError, match="out of range for 3 atoms"):
        check_constraints(water(), (), [c])


@pytest.mark.parametrize(
    ("frozen", "fragment"),
    [([3], "out of range"), ([-1], "out of range"), ([0, 0], "duplicate"), ([True], "ints")],
)
def test_frozen_indices_rejected(frozen: list[Any], fragment: str) -> None:
    """Frozen atoms out of range, duplicated or non-int raise OptimizerInputError."""
    with pytest.raises(OptimizerInputError, match=fragment):
        check_constraints(water(), frozen, ())


def test_constraints_text_empty() -> None:
    """An unconstrained run has empty constraint text."""
    assert constraints_text((), ()) == ""


def test_constraints_text_canonical() -> None:
    """Frozen atoms sorted; dihedrals formatted %.6f; entries sorted and joined by ';'."""
    dihedrals = [
        DihedralConstraint(atoms=(3, 2, 1, 0), value_deg=-60.5),
        DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0),
    ]
    text = constraints_text([5, 2, 9], dihedrals)
    assert text == "dihedral:0,1,2,3:0.000000;dihedral:3,2,1,0:-60.500000;freeze:2,5,9"
    assert constraints_text([9, 2, 5], list(reversed(dihedrals))) == text


def test_constraints_text_single_dihedral() -> None:
    """The planar T1 constraint text (R42)."""
    c = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    assert constraints_text((), [c]) == "dihedral:0,1,2,3:0.000000"
