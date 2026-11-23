"""Frozen, strict contracts for a conserved-core graft: the request and its result (v0.4.0).

The models only validate; the graft itself lives in ``eta_rxncat.mapping``. Like every core
module this one imports neither numpy nor RDKit. Indices are 0-based. ``AtomMappingSpec``
(ADR-0005) describes the template side and is reused unchanged.
"""

from collections.abc import Sequence
from typing import Annotated, Any, Literal, Self

from pydantic import Field, FiniteFloat, StrictInt, model_validator

from eta_rxncat.core.models import (
    AtomMappingSpec,
    CoreModel,
    MolecularState,
    NonNegativeInt,
    PositiveFiniteFloat,
    PositiveInt,
    _duplicates,
)

NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]

IndexSource = Literal["template", "fragment"]
"""Which input a product atom came from."""


def _strictly_ascending(values: Sequence[Any]) -> bool:
    """Return True if each value is greater than the one before it."""
    return all(a < b for a, b in zip(values, values[1:], strict=False))


class GraftSpec(CoreModel):
    """A conserved-core graft request: which template atoms stay and which pairs align.

    Paired fragment atoms (``fragment_alignment``) are always dropped from the product; the
    appended atoms are the fragment atoms neither paired nor in ``fragment_delete``.

    Attributes:
        template: Keep/delete/alignment lists of the template (ADR-0005); ``anchors`` must be empty.
        fragment_alignment: Fragment atoms paired, in order, with ``template.alignment``.
        fragment_delete: Further fragment atoms to drop (unique, disjoint from the pairs).
        constrained_core: Kept template atoms frozen in the pre-relaxation.
        product_charge: Total formal charge of the product (explicit, never inferred).
        product_multiplicity: ``2S + 1`` of the product (explicit, never inferred).
        min_distance_angstrom: Overlap floor; a closer product pair is a clash.
        degenerate_tolerance_angstrom: RMS off-line deviation at or below which a pair set is
            degenerate.
        planar_tolerance_angstrom: RMS out-of-plane deviation at or below which a pair set is
            planar.
        junction_volume_tolerance_angstrom3: Signed volumes at or below this magnitude have sign 0.
    """

    template: AtomMappingSpec
    fragment_alignment: list[NonNegativeInt]
    fragment_delete: list[NonNegativeInt] = Field(default_factory=list)
    constrained_core: list[NonNegativeInt] = Field(default_factory=list)
    product_charge: StrictInt
    product_multiplicity: PositiveInt
    min_distance_angstrom: PositiveFiniteFloat = 0.5
    degenerate_tolerance_angstrom: PositiveFiniteFloat = 1e-3
    planar_tolerance_angstrom: PositiveFiniteFloat = 0.05
    junction_volume_tolerance_angstrom3: PositiveFiniteFloat = 0.05

    @model_validator(mode="after")
    def _check_spec(self) -> Self:
        if len(self.fragment_alignment) != len(self.template.alignment):
            raise ValueError(
                f"fragment_alignment has {len(self.fragment_alignment)} atoms but "
                f"template.alignment has {len(self.template.alignment)}"
            )
        for name, values in (
            ("template.alignment", self.template.alignment),
            ("fragment_alignment", self.fragment_alignment),
            ("fragment_delete", self.fragment_delete),
            ("constrained_core", self.constrained_core),
        ):
            dupes = _duplicates(values)
            if dupes:
                raise ValueError(f"{name} has duplicate indices: {dupes}")
        paired = sorted(set(self.fragment_delete) & set(self.fragment_alignment))
        if paired:
            raise ValueError(
                f"fragment_delete lists paired atoms {paired}: "
                "paired fragment atoms are always dropped"
            )
        keep = set(self.template.keep)
        not_kept = [i for i in self.constrained_core if i not in keep]
        if not_kept:
            raise ValueError(f"constrained_core indices {not_kept} are not in template.keep")
        if self.template.anchors:
            raise ValueError(
                f"template.anchors must be empty (the graft does not use anchors), "
                f"got {self.template.anchors}"
            )
        return self


class CloseContact(CoreModel):
    """A non-bonded product pair closer than the covalent-contact threshold (recorded only).

    Attributes:
        i: Lower product index.
        j: Higher product index.
        distance_angstrom: Interatomic distance.
    """

    i: NonNegativeInt
    j: NonNegativeInt
    distance_angstrom: PositiveFiniteFloat

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if not self.i < self.j:
            raise ValueError(f"close contact needs i < j, got ({self.i}, {self.j})")
        return self


class JunctionVolume(CoreModel):
    """Handedness of one junction bond (kept template atom, appended atom).

    The neighbours, the volume and the sign are all ``None`` when the template atom has fewer
    than two eligible reference neighbours, and all set otherwise.

    Attributes:
        template_atom: Product index of the kept template atom.
        appended_atom: Product index of the appended fragment atom.
        neighbour_a: Lower product index of the two reference neighbours.
        neighbour_b: Higher product index of the two reference neighbours.
        signed_volume_angstrom3: Triple product of the junction and reference bond vectors.
        sign: Sign of the volume, 0 within the junction volume tolerance.
    """

    template_atom: NonNegativeInt
    appended_atom: NonNegativeInt
    neighbour_a: NonNegativeInt | None
    neighbour_b: NonNegativeInt | None
    signed_volume_angstrom3: FiniteFloat | None
    sign: Literal[-1, 0, 1] | None

    @model_validator(mode="after")
    def _check_together(self) -> Self:
        parts = (self.neighbour_a, self.neighbour_b, self.signed_volume_angstrom3, self.sign)
        unset = [part is None for part in parts]
        if any(unset) and not all(unset):
            raise ValueError(
                "neighbour_a, neighbour_b, signed_volume_angstrom3 and sign must be all None "
                "or all set"
            )
        if self.neighbour_a is not None and self.neighbour_b is not None:
            if not self.neighbour_a < self.neighbour_b:
                raise ValueError(
                    f"junction needs neighbour_a < neighbour_b, "
                    f"got ({self.neighbour_a}, {self.neighbour_b})"
                )
        return self


class GraftResult(CoreModel):
    """The product of a conserved-core graft and everything measured about it.

    Attributes:
        product: The grafted structure (template-first atom order).
        index_map: Source of each product atom: ``("template" | "fragment", input index)``.
        alignment_rmsd_angstrom: Unrounded RMSD of the paired atoms after superposition.
        template_charge: Formal charge of the whole template input.
        fragment_charge: Formal charge of the whole fragment input.
        product_charge: Formal charge of the product (equals ``product.charge``).
        whole_input_charge_sum_holds_bool: product charge == template charge + fragment charge
            over the whole inputs, deleted atoms included. It is reported only, never used to
            infer, and it is False for a correct graft whose deleted atoms carry charge.
        constrained_core_product_indices: Product indices of the constrained core, ascending.
        active_product_indices: Product indices of the active atoms, ascending.
        min_interatomic_distance_angstrom: Shortest product pair distance.
        template_pair_planarity_rms_angstrom: RMS out-of-plane deviation of the template pairs.
        fragment_pair_planarity_rms_angstrom: RMS out-of-plane deviation of the fragment pairs.
        planar_pair_set_bool: True if either pair set is within the planar tolerance.
        source_bonds: Bonds of the graft's source graph as product index pairs, ascending.
        close_contacts: Recorded close contacts, ascending by ``(i, j)``.
        junctions: Junction handedness records, ascending by ``(template_atom, appended_atom)``.
    """

    product: MolecularState
    index_map: list[tuple[IndexSource, NonNegativeInt]]
    alignment_rmsd_angstrom: NonNegativeFiniteFloat
    template_charge: StrictInt
    fragment_charge: StrictInt
    product_charge: StrictInt
    whole_input_charge_sum_holds_bool: bool
    constrained_core_product_indices: list[NonNegativeInt]
    active_product_indices: list[NonNegativeInt]
    min_interatomic_distance_angstrom: PositiveFiniteFloat
    template_pair_planarity_rms_angstrom: NonNegativeFiniteFloat
    fragment_pair_planarity_rms_angstrom: NonNegativeFiniteFloat
    planar_pair_set_bool: bool
    source_bonds: list[tuple[NonNegativeInt, NonNegativeInt]]
    close_contacts: list[CloseContact]
    junctions: list[JunctionVolume]

    @model_validator(mode="after")
    def _check_result(self) -> Self:
        n_atoms = len(self.product.symbols)
        if len(self.index_map) != n_atoms:
            raise ValueError(f"index_map has {len(self.index_map)} entries for {n_atoms} atoms")
        referenced: list[int] = [
            *self.constrained_core_product_indices,
            *self.active_product_indices,
            *(i for bond in self.source_bonds for i in bond),
            *(i for contact in self.close_contacts for i in (contact.i, contact.j)),
            *(
                i
                for junction in self.junctions
                for i in (
                    junction.template_atom,
                    junction.appended_atom,
                    junction.neighbour_a,
                    junction.neighbour_b,
                )
                if i is not None
            ),
        ]
        out_of_range = sorted({i for i in referenced if i >= n_atoms})
        if out_of_range:
            raise ValueError(f"product indices {out_of_range} out of range for {n_atoms} atoms")
        for name, indices in (
            ("constrained_core_product_indices", self.constrained_core_product_indices),
            ("active_product_indices", self.active_product_indices),
        ):
            if not _strictly_ascending(indices):
                raise ValueError(f"{name} must be strictly ascending, got {indices}")
        reversed_bonds = [bond for bond in self.source_bonds if not bond[0] < bond[1]]
        if reversed_bonds:
            raise ValueError(f"source_bonds need i < j, got {reversed_bonds}")
        if not _strictly_ascending(self.source_bonds):
            raise ValueError("source_bonds must be strictly ascending")
        if not _strictly_ascending([(c.i, c.j) for c in self.close_contacts]):
            raise ValueError("close_contacts must be strictly ascending by (i, j)")
        junction_keys = [(j.template_atom, j.appended_atom) for j in self.junctions]
        if not _strictly_ascending(junction_keys):
            raise ValueError(
                "junctions must be strictly ascending by (template_atom, appended_atom)"
            )
        if self.product_charge != self.product.charge:
            raise ValueError(
                f"product_charge {self.product_charge} differs from product.charge "
                f"{self.product.charge}"
            )
        return self
