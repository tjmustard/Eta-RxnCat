"""Ordered conserved-core graft surgery (mission G1-G8; TJ R1 "B", Q5 "A", P1 "A", R2 "A").

The template never moves: kept template atoms come first, in keep-list order, with their input
floats copied unchanged. The fragment is superposed onto the template by its paired atoms; the
paired fragment atoms are always dropped, and the atoms that are neither paired nor in
``fragment_delete`` are appended in ascending fragment index. Charge and multiplicity come from
the spec, never from the inputs.
"""

import math
from typing import Literal

from eta_rxncat.core import CloseContact, GraftResult, GraftSpec, MolecularState
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.mapping.align import superpose
from eta_rxncat.mapping.errors import GraftClashError, GraftInputError
from eta_rxncat.mapping.report import covalent_radius_angstrom, junction_volumes, perceive_bonds

CONTACT_FACTOR = 1.3
"""Close-contact threshold factor on the sum of covalent radii (RDKit DetermineConnectivity's
default ``covFactor``)."""


def _check_inputs(template: MolecularState, fragment: MolecularState, spec: GraftSpec) -> None:
    """G1 and G2: index ranges, active and core atoms, and pair elements."""
    try:
        spec.template.check_atom_count(len(template.symbols))
    except ValueError as err:
        raise GraftInputError(f"template mapping does not fit the template: {err}") from err
    n_fragment = len(fragment.symbols)
    for name, values in (
        ("fragment_alignment", spec.fragment_alignment),
        ("fragment_delete", spec.fragment_delete),
    ):
        out_of_range = sorted({i for i in values if i >= n_fragment})
        if out_of_range:
            raise GraftInputError(
                f"{name} indices {out_of_range} out of range for a {n_fragment}-atom fragment"
            )
    deleted = set(spec.template.delete)
    for name, values in (
        ("template active atoms", template.active_atom_indices),
        ("constrained_core atoms", spec.constrained_core),
    ):
        lost = sorted(set(values) & deleted)
        if lost:
            raise GraftInputError(f"{name} {lost} are in template.delete")
    if fragment.active_atom_indices:
        raise GraftInputError(
            f"fragment active_atom_indices {sorted(fragment.active_atom_indices)} would be "
            "dropped; mark active atoms on the template"
        )
    for t, f in zip(spec.template.alignment, spec.fragment_alignment, strict=True):
        if template.symbols[t] != fragment.symbols[f]:
            raise GraftInputError(
                f"pair (template {t}, fragment {f}) mismatches elements: "
                f"{template.symbols[t]} vs {fragment.symbols[f]}"
            )


def graft(template: MolecularState, fragment: MolecularState, spec: GraftSpec) -> GraftResult:
    """Graft ``fragment`` onto ``template`` by the pairs and lists of ``spec``.

    Args:
        template: The structure whose kept atoms stay exactly where they are.
        fragment: The structure that moves; its unpaired, undeleted atoms are appended.
        spec: The request (template lists, fragment pairs and deletes, charge, multiplicity,
            tolerances).

    Returns:
        The product and everything measured about it.

    Raises:
        GraftInputError: If the spec does not fit the inputs (ranges, deleted active atoms,
            fragment active atoms, element mismatch in a pair).
        AlignmentError: If the pair sets cannot be superposed uniquely.
        GraftClashError: If two product atoms are closer than ``spec.min_distance_angstrom``.
        pydantic.ValidationError: If the product charge and multiplicity have the wrong parity.
    """
    _check_inputs(template, fragment, spec)

    # G3. Superpose the fragment's paired atoms onto the template's.
    fit = superpose(
        [fragment.coordinates[f] for f in spec.fragment_alignment],
        [template.coordinates[t] for t in spec.template.alignment],
        degenerate_tolerance_angstrom=spec.degenerate_tolerance_angstrom,
    )

    # G4. Assemble: kept template atoms (input floats, unchanged), then appended fragment atoms.
    keep = spec.template.keep
    dropped = set(spec.fragment_alignment) | set(spec.fragment_delete)
    appended = [j for j in range(len(fragment.symbols)) if j not in dropped]
    template_position = {i: k for k, i in enumerate(keep)}
    fragment_position = {j: len(keep) + k for k, j in enumerate(appended)}
    moved: list[list[float]] = (
        fit.apply([fragment.coordinates[j] for j in appended]).tolist() if appended else []
    )
    symbols = [template.symbols[i] for i in keep] + [fragment.symbols[j] for j in appended]
    coordinates: list[list[float]] = [list(template.coordinates[i]) for i in keep]
    coordinates += [[float(v) for v in row] for row in moved]
    index_map: list[tuple[Literal["template", "fragment"], int]] = [("template", i) for i in keep]
    index_map += [("fragment", j) for j in appended]
    n_atoms = len(symbols)

    # G5. Overlap floor.
    distances: dict[tuple[int, int], float] = {}
    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            d = math.dist(coordinates[i], coordinates[j])
            if d < spec.min_distance_angstrom:
                raise GraftClashError(i, j, d)
            distances[(i, j)] = d
    min_distance = min(distances.values())  # keep holds >= 3 alignment atoms, so n >= 3

    # G6. Source graph in product indices, then close contacts.
    bonds: set[tuple[int, int]] = set()

    def add_bond(i: int, j: int) -> None:
        bonds.add((min(i, j), max(i, j)))

    for a, b in perceive_bonds(template):
        if a in template_position and b in template_position:
            add_bond(template_position[a], template_position[b])
    paired_template = dict(zip(spec.fragment_alignment, spec.template.alignment, strict=True))
    for a, b in perceive_bonds(fragment):
        if a in fragment_position and b in fragment_position:
            add_bond(fragment_position[a], fragment_position[b])
        # Junction bonds: a paired fragment atom's bond to an appended atom lands on the paired
        # template atom.
        for f, other in ((a, b), (b, a)):
            if f in paired_template and other in fragment_position:
                add_bond(template_position[paired_template[f]], fragment_position[other])
    source_bonds = sorted(bonds)
    radius = {s: covalent_radius_angstrom(s) for s in set(symbols)}
    contacts = [
        CloseContact(i=i, j=j, distance_angstrom=distances[(i, j)])
        for i in range(len(keep))
        for j in range(len(keep), n_atoms)
        if (i, j) not in bonds
        and distances[(i, j)] < CONTACT_FACTOR * (radius[symbols[i]] + radius[symbols[j]])
    ]

    # G7. Planarity and junction handedness.
    template_planarity = fit.reference_shape[1]
    fragment_planarity = fit.mobile_shape[1]
    planar = min(template_planarity, fragment_planarity) <= spec.planar_tolerance_angstrom
    junctions = junction_volumes(
        coordinates, source_bonds, len(keep), spec.junction_volume_tolerance_angstrom3
    )

    # G8. Product and result.
    active = sorted(template_position[i] for i in template.active_atom_indices)
    core = sorted(template_position[i] for i in spec.constrained_core)
    metadata: dict[str, ScalarValue] = {"alignment_rmsd_angstrom": fit.rmsd_angstrom}
    for key, state in (("template_name", template), ("fragment_name", fragment)):
        if "name" in state.metadata:
            metadata[key] = state.metadata["name"]
    product = MolecularState(
        symbols=symbols,
        coordinates=coordinates,
        charge=spec.product_charge,
        spin_multiplicity=spec.product_multiplicity,
        active_atom_indices=active,
        metadata=metadata,
    )
    return GraftResult(
        product=product,
        index_map=index_map,
        alignment_rmsd_angstrom=fit.rmsd_angstrom,
        template_charge=template.charge,
        fragment_charge=fragment.charge,
        product_charge=spec.product_charge,
        whole_input_charge_sum_holds_bool=(
            spec.product_charge == template.charge + fragment.charge
        ),
        constrained_core_product_indices=core,
        active_product_indices=active,
        min_interatomic_distance_angstrom=min_distance,
        template_pair_planarity_rms_angstrom=template_planarity,
        fragment_pair_planarity_rms_angstrom=fragment_planarity,
        planar_pair_set_bool=planar,
        source_bonds=source_bonds,
        close_contacts=contacts,
        junctions=junctions,
    )
