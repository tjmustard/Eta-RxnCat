"""Tests for the ordered graft surgery (v0.4.0 slice 04; mission G1-G8, R14-R18, CR-02..CR-10)."""

import math

import numpy as np
import pytest
from cleanroom import TOLERANCE_ANGSTROM, Vector, Xyz, load_vector
from numpy.typing import NDArray
from pydantic import ValidationError

from eta_rxncat.core import ATOMIC_NUMBERS, AtomMappingSpec, GraftResult, GraftSpec, MolecularState
from eta_rxncat.mapping import (
    AlignmentError,
    GraftClashError,
    GraftInputError,
    covalent_radius_angstrom,
    graft,
)

FloatArray = NDArray[np.float64]

# Tetrahedral methyl: C at the origin, three H pointing to -z, the substituent site on +z.
C_H = 1.09
_COS = -1.0 / 3.0
_SIN = math.sqrt(1.0 - _COS * _COS)
METHYL = [[0.0, 0.0, 0.0]] + [
    [C_H * _SIN * math.cos(phi), C_H * _SIN * math.sin(phi), C_H * _COS]
    for phi in (0.0, 2.0 * math.pi / 3.0, 4.0 * math.pi / 3.0)
]


def multiplicity_for(symbols: list[str], charge: int = 0) -> int:
    """Return the lowest spin multiplicity compatible with the electron count."""
    electrons = sum(ATOMIC_NUMBERS[s] for s in symbols) - charge
    return 1 if electrons % 2 == 0 else 2


def state(
    symbols: list[str],
    coordinates: list[list[float]] | FloatArray,
    charge: int = 0,
    active: list[int] | None = None,
    name: str | None = None,
) -> MolecularState:
    """Build a MolecularState with a parity-correct multiplicity."""
    coords = np.asarray(coordinates, dtype=np.float64).tolist()
    return MolecularState(
        symbols=symbols,
        coordinates=coords,
        charge=charge,
        spin_multiplicity=multiplicity_for(symbols, charge),
        active_atom_indices=active or [],
        metadata={"name": name} if name else {},
    )


def rigid_motion(coords: list[list[float]]) -> FloatArray:
    """Apply a fixed proper rotation (0.9 rad about (1, -2, 0.5)) and translation."""
    axis = np.array([1.0, -2.0, 0.5])
    axis /= np.linalg.norm(axis)
    angle = 0.9
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    rotation = np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)
    return np.asarray(coords) @ rotation.T + np.array([4.0, -3.0, 2.5])


def assert_kept_bitwise(result: GraftResult, template: MolecularState, keep: list[int]) -> None:
    """Mini-requirement 10: kept coordinates equal the template floats element for element."""
    for k, i in enumerate(keep):
        assert result.product.coordinates[k] == template.coordinates[i]
        assert result.index_map[k] == ("template", i)


def ch3x(x: str, distance: float) -> tuple[list[str], list[list[float]]]:
    """Return CH3X with X on +z."""
    return ["C", "H", "H", "H", x], [*METHYL, [0.0, 0.0, distance]]


def methyl_spec(**overrides: object) -> GraftSpec:
    """Pairs C and the three H (template 0-3 <- fragment 0-3); template delete 4."""
    data: dict[str, object] = {
        "template": AtomMappingSpec(keep=[0, 1, 2, 3], delete=[4], alignment=[0, 1, 2, 3]),
        "fragment_alignment": [0, 1, 2, 3],
        "product_charge": 0,
        "product_multiplicity": 1,
    }
    data.update(overrides)
    return GraftSpec.model_validate(data)


# --- Mini-requirement 1: CH3Cl -> CH3F ------------------------------------------------------


def test_ch3cl_to_ch3f() -> None:
    """The F lands at its pre-motion position; kept template floats are unchanged."""
    template = state(*ch3x("Cl", 1.78), name="CH3Cl")
    symbols, frame = ch3x("F", 1.38)
    fragment = state(symbols, rigid_motion(frame), name="CH3F")
    result = graft(template, fragment, methyl_spec())
    assert result.product.symbols == ["C", "H", "H", "H", "F"]
    assert result.index_map == [
        ("template", 0),
        ("template", 1),
        ("template", 2),
        ("template", 3),
        ("fragment", 4),
    ]
    assert_kept_bitwise(result, template, [0, 1, 2, 3])
    assert math.dist(result.product.coordinates[4], frame[4]) <= 1e-10
    assert result.alignment_rmsd_angstrom <= 1e-10
    assert result.product.metadata == {
        "alignment_rmsd_angstrom": result.alignment_rmsd_angstrom,
        "template_name": "CH3Cl",
        "fragment_name": "CH3F",
    }
    # The C-F bond is a junction bond (in the source graph), never a close contact.
    assert (0, 4) in result.source_bonds
    assert result.close_contacts == []
    assert [(j.template_atom, j.appended_atom) for j in result.junctions] == [(0, 4)]
    assert result.junctions[0].sign == 1


# --- Mini-requirement 2: product order with fragment_delete ---------------------------------


def test_product_order_with_fragment_delete() -> None:
    """Appended atoms are the unpaired, undeleted fragment atoms in ascending index."""
    triangle = [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [0.0, 1.5, 0.0]]
    template = state(["C", "C", "C", "Cl"], [*triangle, [0.0, 0.0, 1.8]])
    frame = [
        triangle[2],
        [0.0, 0.0, -1.5],
        triangle[0],
        [1.5, 1.5, 0.0],
        triangle[1],
        [0.0, 0.0, 1.5],
    ]
    fragment = state(["C", "H", "C", "F", "C", "Br"], rigid_motion(frame))
    symbols = ["C", "C", "C", "F", "Br"]
    spec = GraftSpec(
        template=AtomMappingSpec(keep=[0, 1, 2], delete=[3], alignment=[0, 1, 2]),
        fragment_alignment=[2, 4, 0],
        fragment_delete=[1],
        product_charge=0,
        product_multiplicity=multiplicity_for(symbols),
    )
    result = graft(template, fragment, spec)
    assert result.product.symbols == symbols
    assert result.index_map == [
        ("template", 0),
        ("template", 1),
        ("template", 2),
        ("fragment", 3),
        ("fragment", 5),
    ]
    assert_kept_bitwise(result, template, [0, 1, 2])
    assert math.dist(result.product.coordinates[3], frame[3]) <= 1e-10
    assert math.dist(result.product.coordinates[4], frame[5]) <= 1e-10


def test_keep_list_order_is_product_order() -> None:
    """Kept template atoms follow keep-list order, not template order."""
    template = state(*ch3x("Cl", 1.78))
    spec = methyl_spec(
        template=AtomMappingSpec(keep=[3, 1, 0, 2], delete=[4], alignment=[0, 1, 2, 3])
    )
    symbols, frame = ch3x("F", 1.38)
    result = graft(template, state(symbols, frame), spec)
    assert_kept_bitwise(result, template, [3, 1, 0, 2])
    assert (2, 4) in result.source_bonds  # template C is product atom 2


# --- Mini-requirement 3: charge and multiplicity --------------------------------------------


def test_charge_and_multiplicity_come_from_the_spec() -> None:
    """The spec's charge and multiplicity land on the product; the sum is reported only."""
    template = state(*ch3x("Cl", 1.78))
    fragment = state(*ch3x("F", 1.38))
    neutral = graft(template, fragment, methyl_spec())
    assert (neutral.product.charge, neutral.product.spin_multiplicity) == (0, 1)
    assert neutral.whole_input_charge_sum_holds_bool is True
    assert neutral.product_charge == 0

    triplet = graft(template, fragment, methyl_spec(product_multiplicity=3))
    assert triplet.product.spin_multiplicity == 3

    charged = graft(
        state(*ch3x("Cl", 1.78), charge=1),
        state(*ch3x("F", 1.38), charge=-1),
        methyl_spec(product_charge=1, product_multiplicity=2),
    )
    assert (charged.template_charge, charged.fragment_charge) == (1, -1)
    assert (charged.product.charge, charged.product_charge) == (1, 1)
    assert charged.whole_input_charge_sum_holds_bool is False


def test_parity_violation_is_a_validation_error() -> None:
    """An odd-electron product with multiplicity 1 is refused by MolecularState."""
    with pytest.raises(ValidationError, match="impossible with 17 electrons"):
        graft(
            state(*ch3x("Cl", 1.78)),
            state(*ch3x("F", 1.38)),
            methyl_spec(product_charge=1, product_multiplicity=1),
        )


# --- Mini-requirement 4: input errors -------------------------------------------------------


def test_out_of_range_template_index_chains_value_error() -> None:
    """A template index beyond the template is GraftInputError from the ValueError (R14)."""
    spec = methyl_spec(
        template=AtomMappingSpec(keep=[0, 1, 2, 3], delete=[4, 9], alignment=[0, 1, 2, 3])
    )
    with pytest.raises(GraftInputError, match=r"\[9\] out of range") as caught:
        graft(state(*ch3x("Cl", 1.78)), state(*ch3x("F", 1.38)), spec)
    assert isinstance(caught.value.__cause__, ValueError)


def test_template_atoms_in_neither_list_refused() -> None:
    """A template atom in neither keep nor delete is refused (partition, DV-06)."""
    spec = methyl_spec(
        template=AtomMappingSpec(keep=[0, 1, 2, 3], delete=[], alignment=[0, 1, 2, 3])
    )
    with pytest.raises(GraftInputError, match=r"atoms \[4\] are in neither keep nor delete"):
        graft(state(*ch3x("Cl", 1.78)), state(*ch3x("F", 1.38)), spec)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"fragment_alignment": [0, 1, 2, 7]}, r"fragment_alignment indices \[7\] out of range"),
        ({"fragment_delete": [6]}, r"fragment_delete indices \[6\] out of range"),
    ],
)
def test_out_of_range_fragment_index(overrides: dict[str, object], message: str) -> None:
    """Fragment indices beyond the fragment raise GraftInputError."""
    with pytest.raises(GraftInputError, match=message):
        graft(state(*ch3x("Cl", 1.78)), state(*ch3x("F", 1.38)), methyl_spec(**overrides))


def test_deleted_active_atom_refused() -> None:
    """A template active atom in the delete list raises GraftInputError naming it."""
    template = state(*ch3x("Cl", 1.78), active=[0, 4])
    with pytest.raises(GraftInputError, match=r"template active atoms \[4\] are in template"):
        graft(template, state(*ch3x("F", 1.38)), methyl_spec())


def test_element_mismatch_in_pair_refused() -> None:
    """A pair joining different elements raises GraftInputError naming both (R17, CR-07)."""
    symbols, frame = ch3x("F", 1.38)
    fragment = state(["C", "H", "H", "F", "H"], [frame[0], frame[1], frame[2], frame[4], frame[3]])
    with pytest.raises(
        GraftInputError, match=r"pair \(template 3, fragment 3\) mismatches elements: H vs F"
    ):
        graft(state(*ch3x("Cl", 1.78)), fragment, methyl_spec())


def test_fragment_active_atoms_refused() -> None:
    """A non-empty fragment active_atom_indices raises GraftInputError naming them."""
    fragment = state(*ch3x("F", 1.38), active=[4])
    with pytest.raises(GraftInputError, match=r"fragment active_atom_indices \[4\]"):
        graft(state(*ch3x("Cl", 1.78)), fragment, methyl_spec())


def test_alignment_error_propagates() -> None:
    """A collinear pair set raises AlignmentError unchanged."""
    line = [[0.0, 0.0, 0.0], [1.5, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 1.5, 0.0]]
    template = state(["C", "C", "C", "Cl"], line)
    fragment = state(["C", "C", "C", "F"], line)
    spec = GraftSpec(
        template=AtomMappingSpec(keep=[0, 1, 2], delete=[3], alignment=[0, 1, 2]),
        fragment_alignment=[0, 1, 2],
        product_charge=0,
        product_multiplicity=multiplicity_for(["C", "C", "C", "F"]),
    )
    with pytest.raises(AlignmentError, match="collinear"):
        graft(template, fragment, spec)


# --- Mini-requirements 5 and 6: clash floor and close contacts ------------------------------

O_SITE = [1.2, 0.0, 1.6]


def contact_case(f_site: list[float]) -> tuple[MolecularState, MolecularState, GraftSpec]:
    """Template CH3 + kept, unpaired O; fragment CH3 + F at ``f_site`` (template frame)."""
    template = state(["C", "H", "H", "H", "O"], [*METHYL, O_SITE])
    f_frame = [*METHYL, f_site]
    fragment = state(["C", "H", "H", "H", "F"], rigid_motion(f_frame))
    spec = methyl_spec(
        template=AtomMappingSpec(keep=[0, 1, 2, 3, 4], delete=[], alignment=[0, 1, 2, 3]),
        product_multiplicity=multiplicity_for(["C", "H", "H", "H", "O", "F"]),
    )
    return template, fragment, spec


def test_clash_below_floor_raises() -> None:
    """An appended atom 0.3 A from a kept template atom raises GraftClashError(i, j, d)."""
    with pytest.raises(GraftClashError) as caught:
        graft(*contact_case([O_SITE[0], O_SITE[1], O_SITE[2] + 0.3]))
    assert (caught.value.i, caught.value.j) == (4, 5)
    assert caught.value.distance_angstrom == pytest.approx(0.3, abs=1e-9)


def test_close_pair_above_floor_is_recorded_not_raised() -> None:
    """At 0.6 A nothing is raised and the pair is a close contact."""
    template, fragment, spec = contact_case([O_SITE[0], O_SITE[1], O_SITE[2] + 0.6])
    result = graft(template, fragment, spec)
    assert [(c.i, c.j) for c in result.close_contacts] == [(4, 5)]
    assert result.close_contacts[0].distance_angstrom == pytest.approx(0.6, abs=1e-9)
    assert result.min_interatomic_distance_angstrom == pytest.approx(0.6, abs=1e-9)
    assert_kept_bitwise(result, template, [0, 1, 2, 3, 4])


def test_contacts_inside_threshold_only_and_never_source_bonds() -> None:
    """Only non-bonded (kept, appended) pairs under 1.3 x the radii sum are contacts."""
    template, fragment, spec = contact_case([0.0, 0.0, 1.38])  # C-F bond; O 1.22 A from F
    result = graft(template, fragment, spec)
    coords = result.product.coordinates
    symbols = result.product.symbols

    def threshold(i: int, j: int) -> float:
        return 1.3 * (covalent_radius_angstrom(symbols[i]) + covalent_radius_angstrom(symbols[j]))

    inside = [
        (i, j) for i in range(5) for j in (5,) if math.dist(coords[i], coords[j]) < threshold(i, j)
    ]
    assert (0, 5) in inside and (4, 5) in inside  # C-F (junction bond) and O-F
    assert (1, 5) not in inside  # an H-F pair outside the threshold
    assert (0, 5) in result.source_bonds
    assert [(c.i, c.j) for c in result.close_contacts] == [(4, 5)]


# --- Mini-requirement 8: clean-room vectors 04, 05, 07 --------------------------------------


def as_state(xyz: Xyz) -> MolecularState:
    """Wrap a vector structure as a neutral MolecularState with parity-correct multiplicity."""
    return state(xyz.symbols, xyz.coordinates)


def aryl_spec(vector: Vector) -> GraftSpec:
    """Build the 04/05 request: template delete, the pairs, fragment_delete = deletes - pairs."""
    n = len(vector.template.symbols)
    paired = [i for _, i in vector.pairs]
    return GraftSpec(
        template=AtomMappingSpec(
            keep=[i for i in range(n) if i not in vector.template_delete],
            delete=vector.template_delete,
            alignment=[t for t, _ in vector.pairs],
        ),
        fragment_alignment=paired,
        fragment_delete=[i for i in vector.incoming_delete if i not in paired],
        product_charge=0,
        product_multiplicity=1,
    )


def check_vector_product(vector: Vector, result: GraftResult) -> float:
    """Assert symbols and coordinates against the expected product; return the max deviation."""
    assert vector.expected_product is not None
    assert result.product.symbols == vector.expected_product.symbols
    deviation = float(
        np.max(np.abs(np.array(result.product.coordinates) - vector.expected_product.coordinates))
    )
    print(f"{vector.name}: max deviation {deviation:.3e} A")
    assert deviation <= TOLERANCE_ANGSTROM
    assert result.alignment_rmsd_angstrom <= TOLERANCE_ANGSTROM
    return deviation


@pytest.mark.parametrize("name", ["04_aryl_graft_para", "05_planar_reversed_order"])
def test_vectors_04_05(name: str) -> None:
    """04/05: the product matches; planar flag set; junction (C4, N) has sign 0."""
    vector = load_vector(name)
    spec = aryl_spec(vector)
    assert spec.template.delete == [8]
    assert spec.fragment_delete == [6, 7, 8, 9, 10]
    template = as_state(vector.template)
    result = graft(template, as_state(vector.incoming), spec)
    check_vector_product(vector, result)
    assert_kept_bitwise(result, template, spec.template.keep)
    c4 = spec.template.keep.index(3)
    n_index = result.product.symbols.index("N")
    assert math.dist(result.product.coordinates[c4], result.product.coordinates[n_index]) == (
        pytest.approx(1.40, abs=TOLERANCE_ANGSTROM)
    )
    assert result.planar_pair_set_bool is True
    junctions = [(j.template_atom, j.appended_atom, j.sign) for j in result.junctions]
    assert junctions == [(c4, n_index, 0)]


def test_vectors_04_05_amine_hydrogens_swap() -> None:
    """05's amine H are 04's exchanged (the planar reversed-sense case TJ R2 "A" flags)."""
    products = []
    for name in ("04_aryl_graft_para", "05_planar_reversed_order"):
        vector = load_vector(name)
        result = graft(as_state(vector.template), as_state(vector.incoming), aryl_spec(vector))
        products.append(np.array(result.product.coordinates))
    para, reversed_order = products
    # Each product is within 1e-6 A of its own six-decimal file, so they agree within 2e-6 A.
    both = 2 * TOLERANCE_ANGSTROM
    assert np.max(np.abs(para[:12] - reversed_order[:12])) <= both
    assert np.max(np.abs(para[12] - reversed_order[13])) <= both
    assert np.max(np.abs(para[13] - reversed_order[12])) <= both
    assert np.max(np.abs(para[12] - para[13])) > 1.0


def test_vector_07_literal_request_refused() -> None:
    """07(a): the literal request deletes paired template atom 5; ADR-0005 refuses it."""
    vector = load_vector("07_delete_lists_and_order")
    n = len(vector.template.symbols)
    assert vector.template_delete == [1, 2, 4]
    with pytest.raises(ValidationError, match=r"alignment indices \[4\] are not in keep"):
        GraftSpec(
            template=AtomMappingSpec(
                keep=[i for i in range(n) if i not in vector.template_delete],
                delete=vector.template_delete,
                alignment=[t for t, _ in vector.pairs],
            ),
            fragment_alignment=[i for _, i in vector.pairs],
            product_charge=0,
            product_multiplicity=1,
        )


def test_vector_07_eta_adapted() -> None:
    """07(b): template delete {2,3}, pairs (1,1),(4,2),(5,3) -> C, C, H, O, N, Cl.

    The vector's structures have odd electron counts (template 23, product 45), so they carry
    multiplicity 2 here; the vector's own "multiplicity 1" is not a valid MolecularState.
    """
    vector = load_vector("07_delete_lists_and_order")
    assert vector.pairs == [(0, 0), (3, 1), (4, 2)]
    spec = GraftSpec(
        template=AtomMappingSpec(keep=[0, 3, 4, 5], delete=[1, 2], alignment=[0, 3, 4]),
        fragment_alignment=[0, 1, 2],
        fragment_delete=[],
        product_charge=0,
        product_multiplicity=2,
    )
    template = as_state(vector.template)
    result = graft(template, as_state(vector.incoming), spec)
    assert result.product.symbols == ["C", "C", "H", "O", "N", "Cl"]
    expected = np.array(
        [[0, 0, 0], [0, 0, 1], [1, 1, 0], [0, 0, 2], [0, 1, 1], [1, 0, 1]], dtype=np.float64
    )
    deviation = float(np.max(np.abs(np.array(result.product.coordinates) - expected)))
    print(f"07_eta_adapted: max deviation {deviation:.3e} A")
    assert deviation <= TOLERANCE_ANGSTROM
    assert result.alignment_rmsd_angstrom <= TOLERANCE_ANGSTROM
    assert result.index_map == [
        ("template", 0),
        ("template", 3),
        ("template", 4),
        ("template", 5),
        ("fragment", 3),
        ("fragment", 4),
    ]
    assert_kept_bitwise(result, template, [0, 3, 4, 5])


# --- Re-indexing (G8) ------------------------------------------------------------------------


def test_active_atoms_and_core_are_reindexed() -> None:
    """Template actives and the constrained core land on product indices, sorted."""
    vector = load_vector("04_aryl_graft_para")
    base = aryl_spec(vector)
    spec = base.model_copy(update={"constrained_core": [9, 0, 3]})
    spec = GraftSpec.model_validate(spec.model_dump())
    template = state(vector.template.symbols, vector.template.coordinates, active=[11, 3])
    result = graft(template, as_state(vector.incoming), spec)
    assert result.constrained_core_product_indices == [0, 3, 8]
    assert result.active_product_indices == [3, 10]
    assert result.product.active_atom_indices == [3, 10]
