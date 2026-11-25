"""Clean-room quaternion/Kabsch alignment and ordered keep/delete/alignment atom surgery.

Inspired by nMap and Eta_Scripts (Mustard, Wender, & Cheong, ACS Catal. 2015).
"""

from __future__ import annotations

import numpy as np

from eta_rxncat.core.models import AtomMappingSpec, MolecularState


def kabsch_align(
    mobile_coords: np.ndarray,
    reference_coords: np.ndarray,
    mobile_align_indices: list[int],
    reference_align_indices: list[int],
) -> tuple[np.ndarray, float]:
    """Align mobile_coords onto reference_coords using ordered alignment atom indices via SVD/Kabsch."""
    if len(mobile_align_indices) != len(reference_align_indices) or len(mobile_align_indices) < 3:
        raise ValueError("Alignment index lists must have matching length >= 3.")

    p_sub = mobile_coords[mobile_align_indices]
    q_sub = reference_coords[reference_align_indices]

    p_centroid = np.mean(p_sub, axis=0)
    q_centroid = np.mean(q_sub, axis=0)

    p_centered = p_sub - p_centroid
    q_centered = q_sub - q_centroid

    h_mat = p_centered.T @ q_centered
    u_mat, _, vt_mat = np.linalg.svd(h_mat)
    d_sign = 1.0 if np.linalg.det(vt_mat.T @ u_mat.T) >= 0.0 else -1.0
    rot = vt_mat.T @ np.diag([1.0, 1.0, d_sign]) @ u_mat.T

    aligned_all = (mobile_coords - p_centroid) @ rot.T + q_centroid
    diff = aligned_all[mobile_align_indices] - q_sub
    rmsd = float(np.sqrt(np.mean(np.sum(diff**2, axis=1))))
    return aligned_all, rmsd


def graft_substituent_onto_template(
    template: MolecularState,
    template_spec: AtomMappingSpec,
    substituent: MolecularState,
    substituent_spec: AtomMappingSpec,
    *,
    charge_delta: int = 0,
    new_name: str | None = None,
) -> tuple[MolecularState, float]:
    """Perform ordered keep/delete atom surgery and Kabsch alignment to graft substituent onto template."""
    # Align substituent onto template using ordered alignment_atoms
    aligned_sub_coords, align_rmsd = kabsch_align(
        mobile_coords=substituent.coords_array(),
        reference_coords=template.coords_array(),
        mobile_align_indices=substituent_spec.alignment_atoms,
        reference_align_indices=template_spec.alignment_atoms,
    )

    tmpl_coords = template.coords_array()
    new_symbols: list[str] = []
    new_coords: list[list[float]] = []
    new_active: list[int] = []
    old_to_new: dict[int, int] = {}

    # Retain ordered keep_atoms from template (excluding any delete_atoms)
    delete_set = set(template_spec.delete_atoms)
    for old_idx in template_spec.keep_atoms:
        if old_idx in delete_set:
            continue
        new_idx = len(new_symbols)
        old_to_new[old_idx] = new_idx
        new_symbols.append(template.symbols[old_idx])
        new_coords.append(tmpl_coords[old_idx].tolist())
        if old_idx in template.active_atom_indices:
            new_active.append(new_idx)

    # Append ordered keep_atoms from aligned substituent
    sub_delete_set = set(substituent_spec.delete_atoms)
    for sub_old_idx in substituent_spec.keep_atoms:
        if sub_old_idx in sub_delete_set:
            continue
        new_symbols.append(substituent.symbols[sub_old_idx])
        new_coords.append(aligned_sub_coords[sub_old_idx].tolist())

    mapped = MolecularState(
        name=new_name or f"{template.name}_{substituent.name}",
        symbols=new_symbols,
        coordinates=new_coords,
        charge=template.charge + charge_delta,
        spin_multiplicity=template.spin_multiplicity,
        active_atom_indices=new_active,
        metadata={
            **template.metadata,
            "core_alignment_rmsd": round(align_rmsd, 6),
        },
    )
    return mapped, align_rmsd
