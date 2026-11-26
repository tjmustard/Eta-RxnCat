"""Unit tests for v0.4.0 clean-room quaternion/Kabsch alignment and atom surgery."""

import numpy as np

from eta_rxncat.core.models import AtomMappingSpec, MolecularState
from eta_rxncat.mapping.core_mapper import graft_substituent_onto_template, kabsch_align


def test_kabsch_align_recovers_known_rotation_translation() -> None:
    ref = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.5, 0.0, 0.0],
            [0.0, 1.5, 0.0],
            [0.0, 0.0, 1.5],
        ]
    )
    theta = 0.7
    rot = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta), np.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    mobile = ref @ rot.T + np.array([3.2, -1.5, 2.0])
    aligned, rmsd = kabsch_align(mobile, ref, [0, 1, 2, 3], [0, 1, 2, 3])
    assert rmsd < 1e-10
    assert np.allclose(aligned, ref, atol=1e-9)


def test_graft_substituent_preserves_order_and_active_atoms() -> None:
    # Template: CH3-Cl (delete Cl at index 4, keep C0 H1 H2 H3, align on C0 H1 H2)
    tmpl = MolecularState(
        name="core_ts",
        symbols=["C", "H", "H", "H", "Cl"],
        coordinates=[
            [0.0, 0.0, 0.0],
            [1.09, 0.0, 0.0],
            [-0.36, 1.03, 0.0],
            [-0.36, -0.51, 0.89],
            [0.0, 0.0, -1.78],
        ],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=[0, 1],
    )
    tmpl_spec = AtomMappingSpec(
        keep_atoms=[0, 1, 2, 3],
        delete_atoms=[4],
        alignment_atoms=[0, 1, 2],
    )

    # Substituent: CH3-F shifted in space (align C0 H1 H2, delete H3, keep F4)
    sub = MolecularState(
        name="fluoro_sub",
        symbols=["C", "H", "H", "H", "F"],
        coordinates=[
            [5.0, 2.0, 0.0],
            [6.09, 2.0, 0.0],
            [4.64, 3.03, 0.0],
            [4.64, 1.49, 0.89],
            [5.0, 2.0, -1.35],
        ],
        charge=0,
        spin_multiplicity=1,
    )
    sub_spec = AtomMappingSpec(
        keep_atoms=[4],
        delete_atoms=[0, 1, 2, 3],
        alignment_atoms=[0, 1, 2],
    )

    mapped, rmsd = graft_substituent_onto_template(tmpl, tmpl_spec, sub, sub_spec)
    assert rmsd < 1e-6
    assert mapped.symbols == ["C", "H", "H", "H", "F"]
    assert mapped.active_atom_indices == [0, 1]
    assert np.allclose(mapped.coords_array()[-1], [0.0, 0.0, -1.35], atol=1e-5)
