"""Tests for GraftSpec, GraftResult, CloseContact and JunctionVolume (v0.4.0 slice 02)."""

import json
import subprocess
import sys
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    AtomMappingSpec,
    CloseContact,
    GraftResult,
    GraftSpec,
    JunctionVolume,
    MolecularState,
    NonNegativeFiniteFloat,
)

# --- GraftSpec ------------------------------------------------------------------------------


def m1_template() -> AtomMappingSpec:
    """Return the template lists of the M1 mapping (TS1a_n, 18 atoms)."""
    return AtomMappingSpec(
        keep=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15],
        delete=[7, 16, 17],
        alignment=[2, 3, 10, 11],
    )


def spec(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for the valid M1-shaped GraftSpec, with overrides applied."""
    data: dict[str, Any] = {
        "template": m1_template(),
        "fragment_alignment": [0, 3, 4, 9],
        "constrained_core": [1, 2, 3, 5],
        "product_charge": 0,
        "product_multiplicity": 1,
    }
    data.update(overrides)
    return data


def test_graft_spec_m1_round_trips_json() -> None:
    """The M1-shaped spec round-trips through JSON unchanged, defaults included."""
    value = GraftSpec(**spec())
    assert GraftSpec.model_validate_json(value.model_dump_json()) == value
    assert value.fragment_delete == []
    assert value.min_distance_angstrom == 0.5
    assert value.degenerate_tolerance_angstrom == 1e-3
    assert value.planar_tolerance_angstrom == 0.05
    assert value.junction_volume_tolerance_angstrom3 == 0.05


def test_graft_spec_pair_count_must_match() -> None:
    """Validator 1: the fragment pairs one atom per template alignment atom."""
    GraftSpec(**spec(fragment_alignment=[0, 3, 4, 9]))
    with pytest.raises(ValidationError, match="fragment_alignment has 3 atoms but"):
        GraftSpec(**spec(fragment_alignment=[0, 3, 4]))


def test_graft_spec_fragment_alignment_unique() -> None:
    """Validator 2 (fragment side): fragment_alignment has no duplicates (CR-08)."""
    GraftSpec(**spec(fragment_alignment=[0, 3, 4, 8]))
    with pytest.raises(ValidationError, match=r"fragment_alignment has duplicate indices: \[3\]"):
        GraftSpec(**spec(fragment_alignment=[0, 3, 3, 9]))


def test_graft_spec_template_alignment_unique() -> None:
    """Validator 2 (template side): a duplicated template alignment atom is refused.

    GraftSpec re-validates its template, so the reused ``AtomMappingSpec`` validator refuses the
    duplicate first, even for an instance built without validation.
    """
    GraftSpec(**spec(template=m1_template()))
    unchecked = AtomMappingSpec.model_construct(
        keep=[0, 1, 2], delete=[], alignment=[0, 1, 1, 2], anchors=[]
    )
    with pytest.raises(ValidationError, match=r"alignment has duplicate indices: \[1\]"):
        GraftSpec(**spec(template=unchecked, fragment_alignment=[0, 1, 2, 3]))
    with pytest.raises(ValidationError, match=r"alignment has duplicate indices: \[1\]"):
        GraftSpec(
            **spec(
                template={"keep": [0, 1, 2], "delete": [], "alignment": [0, 1, 1, 2]},
                fragment_alignment=[0, 1, 2, 3],
            )
        )


def test_graft_spec_fragment_delete_unique() -> None:
    """Validator 3: fragment_delete has no duplicates."""
    GraftSpec(**spec(fragment_delete=[1, 2]))
    with pytest.raises(ValidationError, match=r"fragment_delete has duplicate indices: \[2\]"):
        GraftSpec(**spec(fragment_delete=[2, 2]))


def test_graft_spec_fragment_delete_disjoint_from_pairs() -> None:
    """Validator 3: a paired fragment atom in fragment_delete is refused (TJ R1 "B")."""
    GraftSpec(**spec(fragment_delete=[1]))
    with pytest.raises(ValidationError, match="paired fragment atoms are always dropped"):
        GraftSpec(**spec(fragment_delete=[1, 3]))


def test_graft_spec_constrained_core_unique() -> None:
    """Validator 4: constrained_core has no duplicates."""
    GraftSpec(**spec(constrained_core=[1, 2]))
    with pytest.raises(ValidationError, match=r"constrained_core has duplicate indices: \[2\]"):
        GraftSpec(**spec(constrained_core=[1, 2, 2]))


def test_graft_spec_constrained_core_kept() -> None:
    """Validator 4: constrained_core is a subset of template.keep."""
    GraftSpec(**spec(constrained_core=[0, 15]))
    with pytest.raises(ValidationError, match=r"constrained_core indices \[7\] are not in"):
        GraftSpec(**spec(constrained_core=[1, 7]))


def test_graft_spec_anchors_refused() -> None:
    """Validator 5: non-empty template.anchors is refused, never ignored (R11)."""
    GraftSpec(**spec(template=m1_template()))
    anchored = AtomMappingSpec(
        keep=[0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15],
        delete=[7, 16, 17],
        alignment=[2, 3, 10, 11],
        anchors=[2],
    )
    with pytest.raises(ValidationError, match="template.anchors must be empty"):
        GraftSpec(**spec(template=anchored))


@pytest.mark.parametrize(
    "field",
    [
        "min_distance_angstrom",
        "degenerate_tolerance_angstrom",
        "planar_tolerance_angstrom",
        "junction_volume_tolerance_angstrom3",
    ],
)
@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_graft_spec_tolerances_positive_finite(field: str, bad: float) -> None:
    """Tolerances are positive and finite."""
    GraftSpec(**spec(**{field: 0.2}))
    with pytest.raises(ValidationError, match=field):
        GraftSpec(**spec(**{field: bad}))


@pytest.mark.parametrize("field", ["fragment_alignment", "fragment_delete", "constrained_core"])
def test_graft_spec_negative_index_refused(field: str) -> None:
    """Fragment and core indices are non-negative (CR-09)."""
    values = {
        "fragment_alignment": [0, 3, 4, -1],
        "fragment_delete": [-2],
        "constrained_core": [-1],
    }[field]
    with pytest.raises(ValidationError, match=field):
        GraftSpec(**spec(**{field: values}))


def test_graft_spec_multiplicity_positive() -> None:
    """product_multiplicity is at least 1."""
    GraftSpec(**spec(product_multiplicity=2))
    with pytest.raises(ValidationError, match="product_multiplicity"):
        GraftSpec(**spec(product_multiplicity=0))


@pytest.mark.parametrize("bad", [True, "0", 0.0])
def test_graft_spec_strict_charge(bad: object) -> None:
    """product_charge is a strict int: True, "0" and 0.0 are refused (ADR-0003)."""
    with pytest.raises(ValidationError, match="product_charge"):
        GraftSpec(**spec(product_charge=bad))


@pytest.mark.parametrize("bad", [True, "1"])
def test_graft_spec_strict_multiplicity(bad: object) -> None:
    """product_multiplicity is a strict int."""
    with pytest.raises(ValidationError, match="product_multiplicity"):
        GraftSpec(**spec(product_multiplicity=bad))


def test_graft_spec_frozen() -> None:
    """Assignment raises."""
    value = GraftSpec(**spec())
    with pytest.raises(ValidationError, match="frozen"):
        value.product_charge = 1  # type: ignore[misc]


def test_graft_spec_extra_forbidden() -> None:
    """An unknown field raises."""
    with pytest.raises(ValidationError, match="extra_forbidden"):
        GraftSpec(**spec(anchors=[]))


# --- CloseContact ---------------------------------------------------------------------------


def test_close_contact_order() -> None:
    """CloseContact needs i < j."""
    assert CloseContact(i=0, j=17, distance_angstrom=1.1218).j == 17
    with pytest.raises(ValidationError, match=r"close contact needs i < j, got \(17, 0\)"):
        CloseContact(i=17, j=0, distance_angstrom=1.1218)
    with pytest.raises(ValidationError, match=r"close contact needs i < j, got \(3, 3\)"):
        CloseContact(i=3, j=3, distance_angstrom=1.0)


def test_close_contact_distance_positive_finite() -> None:
    """distance_angstrom is positive and finite."""
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValidationError, match="distance_angstrom"):
            CloseContact(i=0, j=1, distance_angstrom=bad)


def test_close_contact_frozen_strict_extra() -> None:
    """Frozen, strict and extra-forbidding."""
    value = CloseContact(i=0, j=1, distance_angstrom=1.0)
    with pytest.raises(ValidationError, match="frozen"):
        value.i = 2  # type: ignore[misc]
    with pytest.raises(ValidationError, match="i"):
        CloseContact(i=True, j=1, distance_angstrom=1.0)
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CloseContact(i=0, j=1, distance_angstrom=1.0, kind="h")  # type: ignore[call-arg]


# --- JunctionVolume -------------------------------------------------------------------------


def junction(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a set JunctionVolume, with overrides applied."""
    data: dict[str, Any] = {
        "template_atom": 0,
        "appended_atom": 15,
        "neighbour_a": 1,
        "neighbour_b": 4,
        "signed_volume_angstrom3": -0.8,
        "sign": -1,
    }
    data.update(overrides)
    return data


def test_junction_all_set_or_all_none() -> None:
    """The neighbours, volume and sign are all None together or all set."""
    assert JunctionVolume(**junction()).sign == -1
    unset = JunctionVolume(
        **junction(neighbour_a=None, neighbour_b=None, signed_volume_angstrom3=None, sign=None)
    )
    assert unset.signed_volume_angstrom3 is None
    for field in ("neighbour_a", "neighbour_b", "signed_volume_angstrom3", "sign"):
        with pytest.raises(ValidationError, match="must be all None or all set"):
            JunctionVolume(**junction(**{field: None}))


def test_junction_neighbour_order() -> None:
    """neighbour_a < neighbour_b when set."""
    JunctionVolume(**junction(neighbour_a=1, neighbour_b=4))
    with pytest.raises(ValidationError, match=r"neighbour_a < neighbour_b, got \(4, 1\)"):
        JunctionVolume(**junction(neighbour_a=4, neighbour_b=1))
    with pytest.raises(ValidationError, match=r"neighbour_a < neighbour_b, got \(2, 2\)"):
        JunctionVolume(**junction(neighbour_a=2, neighbour_b=2))


def test_junction_sign_values() -> None:
    """The sign is -1, 0 or 1; the volume is finite."""
    for sign in (-1, 0, 1):
        assert JunctionVolume(**junction(sign=sign)).sign == sign
    with pytest.raises(ValidationError, match="sign"):
        JunctionVolume(**junction(sign=2))
    with pytest.raises(ValidationError, match="signed_volume_angstrom3"):
        JunctionVolume(**junction(signed_volume_angstrom3=float("nan")))


def test_junction_frozen_extra() -> None:
    """Frozen and extra-forbidding."""
    value = JunctionVolume(**junction())
    with pytest.raises(ValidationError, match="frozen"):
        value.sign = 1  # type: ignore[misc]
    with pytest.raises(ValidationError, match="extra_forbidden"):
        JunctionVolume(**junction(volume=1.0))


# --- GraftResult ----------------------------------------------------------------------------


def product(charge: int = 0, multiplicity: int = 1) -> MolecularState:
    """Return a five-atom CH3F-like product (template C, H, H, H then fragment F)."""
    return MolecularState(
        symbols=["C", "H", "H", "H", "F"],
        coordinates=[
            [0.0, 0.0, 0.0],
            [1.09, 0.0, 0.0],
            [-0.36, 1.03, 0.0],
            [-0.36, -0.51, 0.89],
            [-0.47, -0.67, -1.16],
        ],
        charge=charge,
        spin_multiplicity=multiplicity,
    )


def result(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid GraftResult, with overrides applied."""
    data: dict[str, Any] = {
        "product": product(),
        "index_map": [
            ("template", 0),
            ("template", 1),
            ("template", 2),
            ("template", 3),
            ("fragment", 1),
        ],
        "alignment_rmsd_angstrom": 0.0123,
        "template_charge": 0,
        "fragment_charge": 0,
        "product_charge": 0,
        "whole_input_charge_sum_holds_bool": True,
        "constrained_core_product_indices": [0, 1],
        "active_product_indices": [0, 4],
        "min_interatomic_distance_angstrom": 1.03,
        "template_pair_planarity_rms_angstrom": 0.0,
        "fragment_pair_planarity_rms_angstrom": 0.01,
        "planar_pair_set_bool": True,
        "source_bonds": [(0, 1), (0, 2), (0, 3), (0, 4)],
        "close_contacts": [
            CloseContact(i=1, j=4, distance_angstrom=1.9),
            CloseContact(i=2, j=4, distance_angstrom=1.95),
        ],
        "junctions": [JunctionVolume(**junction(template_atom=0, appended_atom=4))],
    }
    data.update(overrides)
    return data


def test_graft_result_round_trips_json() -> None:
    """A valid result round-trips through JSON (tuples restored)."""
    value = GraftResult(**result())
    assert GraftResult.model_validate_json(value.model_dump_json()) == value
    assert value.index_map[4] == ("fragment", 1)


def test_graft_result_charge_sum_docstring() -> None:
    """The charge-sum field documents that it is report-only (R10)."""
    description = GraftResult.__doc__ or ""
    assert "over the whole inputs, deleted atoms included" in description
    assert "reported only, never used to" in description


def test_graft_result_charge_sum_false_allowed() -> None:
    """A False sum is a valid report (a charged leaving group), not an error."""
    value = GraftResult(**result(template_charge=1, whole_input_charge_sum_holds_bool=False))
    assert value.whole_input_charge_sum_holds_bool is False


def test_graft_result_index_map_length() -> None:
    """Validator 1: one index_map entry per product atom."""
    with pytest.raises(ValidationError, match="index_map has 4 entries for 5 atoms"):
        GraftResult(**result(index_map=result()["index_map"][:4]))


def test_graft_result_index_map_source() -> None:
    """index_map sources are "template" or "fragment"."""
    bad = [*result()["index_map"][:4], ("substituent", 1)]
    with pytest.raises(ValidationError, match="index_map"):
        GraftResult(**result(index_map=bad))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("constrained_core_product_indices", [0, 5]),
        ("active_product_indices", [7]),
        ("source_bonds", [(0, 1), (0, 5)]),
        ("close_contacts", [CloseContact(i=1, j=5, distance_angstrom=1.9)]),
        ("junctions", [JunctionVolume(**junction(template_atom=0, appended_atom=5))]),
        ("junctions", [JunctionVolume(**junction(appended_atom=4, neighbour_b=9))]),
    ],
)
def test_graft_result_indices_in_range(field: str, value: object) -> None:
    """Validator 2: every referenced product index is below the atom count."""
    with pytest.raises(ValidationError, match="out of range for 5 atoms"):
        GraftResult(**result(**{field: value}))


@pytest.mark.parametrize("field", ["constrained_core_product_indices", "active_product_indices"])
@pytest.mark.parametrize("bad", [[1, 0], [0, 0]])
def test_graft_result_index_lists_strictly_ascending(field: str, bad: list[int]) -> None:
    """Validator 3: core and active product indices are strictly ascending."""
    GraftResult(**result(**{field: [0, 1, 4]}))
    with pytest.raises(ValidationError, match=f"{field} must be strictly ascending"):
        GraftResult(**result(**{field: bad}))


def test_graft_result_source_bond_pairs_ordered() -> None:
    """Validator 4: each source bond has i < j."""
    with pytest.raises(ValidationError, match=r"source_bonds need i < j, got \[\(4, 0\)\]"):
        GraftResult(**result(source_bonds=[(0, 1), (4, 0)]))


@pytest.mark.parametrize("bad", [[(0, 2), (0, 1)], [(0, 1), (0, 1)]])
def test_graft_result_source_bonds_ascending(bad: list[tuple[int, int]]) -> None:
    """Validator 4: the bond list is strictly ascending."""
    with pytest.raises(ValidationError, match="source_bonds must be strictly ascending"):
        GraftResult(**result(source_bonds=bad))


def test_graft_result_close_contacts_ascending() -> None:
    """Validator 5: close contacts are strictly ascending by (i, j)."""
    swapped = list(reversed(result()["close_contacts"]))
    with pytest.raises(ValidationError, match=r"close_contacts must be strictly ascending"):
        GraftResult(**result(close_contacts=swapped))


def test_graft_result_junctions_ascending() -> None:
    """Validator 5: junctions are strictly ascending by (template_atom, appended_atom)."""
    first = JunctionVolume(**junction(template_atom=0, appended_atom=4))
    second = JunctionVolume(**junction(template_atom=1, appended_atom=4))
    GraftResult(**result(junctions=[first, second]))
    with pytest.raises(ValidationError, match="junctions must be strictly ascending"):
        GraftResult(**result(junctions=[second, first]))
    with pytest.raises(ValidationError, match="junctions must be strictly ascending"):
        GraftResult(**result(junctions=[first, first]))


def test_graft_result_product_charge_matches_state() -> None:
    """Validator 6: product_charge equals product.charge."""
    GraftResult(**result(product=product(charge=1, multiplicity=2), product_charge=1))
    with pytest.raises(ValidationError, match="product_charge -1 differs from product.charge 0"):
        GraftResult(**result(product_charge=-1))


@pytest.mark.parametrize(
    "field",
    [
        "alignment_rmsd_angstrom",
        "template_pair_planarity_rms_angstrom",
        "fragment_pair_planarity_rms_angstrom",
    ],
)
@pytest.mark.parametrize("bad", [-1e-9, float("nan"), float("inf")])
def test_graft_result_non_negative_finite(field: str, bad: float) -> None:
    """RMSD and planarity values are non-negative and finite (zero allowed)."""
    GraftResult(**result(**{field: 0.0}))
    with pytest.raises(ValidationError, match=field):
        GraftResult(**result(**{field: bad}))


def test_graft_result_min_distance_positive() -> None:
    """min_interatomic_distance_angstrom is positive."""
    with pytest.raises(ValidationError, match="min_interatomic_distance_angstrom"):
        GraftResult(**result(min_interatomic_distance_angstrom=0.0))


@pytest.mark.parametrize("field", ["template_charge", "fragment_charge", "product_charge"])
@pytest.mark.parametrize("bad", [True, "0"])
def test_graft_result_strict_charges(field: str, bad: object) -> None:
    """Charges are strict ints."""
    with pytest.raises(ValidationError, match=field):
        GraftResult(**result(**{field: bad}))


def test_graft_result_frozen_extra() -> None:
    """Frozen and extra-forbidding."""
    value = GraftResult(**result())
    with pytest.raises(ValidationError, match="frozen"):
        value.product_charge = 1  # type: ignore[misc]
    with pytest.raises(ValidationError, match="extra_forbidden"):
        GraftResult(**result(name="graft"))


# --- NonNegativeFiniteFloat and the import boundary -----------------------------------------


def test_non_negative_finite_float_exported() -> None:
    """NonNegativeFiniteFloat is exported from eta_rxncat.core."""
    assert NonNegativeFiniteFloat is not None


def test_core_import_loads_no_numpy_or_rdkit() -> None:
    """Importing eta_rxncat.core and the mapping models loads neither numpy nor RDKit."""
    code = (
        "import json, sys\n"
        "import eta_rxncat.core\n"
        "import eta_rxncat.core.mapping_models\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in ('numpy', 'rdkit'))\n"
        "print(json.dumps(loaded))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == []
