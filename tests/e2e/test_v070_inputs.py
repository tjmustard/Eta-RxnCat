"""v0.7.0 E2E inputs (slice 10): the plans load and resolve's measurements hold. Engine-free.

Pins mission HF-1 and HF-2 on the committed geometries: the anti-H site rule, the chosen fragment
orders and fits, the faces, the C7 orientation sign, the enumerator's two candidates, the two
fallback constructs and the SOURCES.md checksums.
"""

import hashlib
import re
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from fixtures import read_xyz
from v070 import (
    E2E5,
    ENUMERATION_YAML,
    FALLBACK_YAML,
    V070Inputs,
    load_enumeration,
    load_fallback,
)

from eta_rxncat.conformers import forming_bond_configuration
from eta_rxncat.core import EnumeratedCandidate, GraftRecord, MolecularState, TSEnsembleOptions
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.enumerator import enumerate_candidates

C7, SP2 = 7, (2, 3)
DIENE = [0, 1, 4, 5, 6]
FORMING = [(1, 2), (3, 5)]
FACE = {"TS1a_n": (1, 1), "TS1a_x": (-1, -1)}
ANTI_ANGLE_DEG = {"TS1a_n": 179.9, "TS1a_x": 163.5}
# Chosen sp2 pair per (entry, node), and the HF-1 fit ranges (Angstrom, 3 decimals).
ORDERS = {
    ("ethyl", "TS1a_n"): [3, 4],
    ("ethyl", "TS1a_x"): [4, 3],
    ("npropyl", "TS1a_n"): [5, 4],
    ("npropyl", "TS1a_x"): [4, 5],
}
FITS = {"TS1a_n": (0.033, 0.035), "TS1a_x": (0.046, 0.049)}
MIRROR_FITS = (0.491, 0.494)  # the endo mirror order grafts; the exo one clashes
REACTANT_FITS = {"ethyl": 0.0525, "npropyl": 0.0496}
ATOMS = {"ethyl": 24, "npropyl": 27}


def ts(name: str) -> MolecularState:
    """Read a Tier 4 TS."""
    return read_xyz(E2E5 / f"xyz/{name}.xyz", 0, 1)


def face(state: MolecularState) -> tuple[int, ...]:
    """The face descriptor over the two forming bonds."""
    return tuple(forming_bond_configuration(state, FORMING, perceive_bonds(state)))


def neighbours(state: MolecularState, atom: int) -> list[int]:
    """Atoms bonded to ``atom``."""
    return sorted({j for pair in perceive_bonds(state) if atom in pair for j in pair} - {atom})


def orientation_sign(state: MolecularState, substituent: int) -> float:
    """Sign of the signed volume at C7 over (C2, C3, substituent) (HF-2)."""
    x = np.asarray(state.coordinates)
    return float(np.sign(np.linalg.det(x[[*SP2, substituent]] - x[C7])))


def substituent(state: MolecularState, record: GraftRecord) -> int:
    """The fragment atom bonded to C7 in a grafted product."""
    assert record.index_map is not None
    (atom,) = [j for j in neighbours(state, C7) if record.index_map[j][0] == "fragment"]
    return atom


def run(inputs: V070Inputs) -> list[EnumeratedCandidate]:
    """Enumerate a loaded plan's candidates."""
    return enumerate_candidates(
        inputs.plan, max_alignment_rmsd_angstrom=inputs.max_alignment_rmsd_angstrom
    ).candidates


def record(candidate: EnumeratedCandidate, node: str, template: str) -> GraftRecord:
    """The graft record of one (node, template)."""
    (found,) = [r for r in candidate.records if (r.node_id, r.template_id) == (node, template)]
    return found


def product(candidate: EnumeratedCandidate, node: str, template: str) -> MolecularState:
    """The grafted state of one (node, template)."""
    assert candidate.graph is not None
    (graph_node,) = [n for n in candidate.graph.nodes if n.id == node]
    (found,) = [t for t in graph_node.templates if t.id == f"{template}__{candidate.candidate_id}"]
    return found.components[0].state


# --- The loaded plans ----------------------------------------------------------------------------


def test_enumeration_plan_declares_what_the_slice_states() -> None:
    """Graph, site maps, library, selectivity set and settings."""
    inputs = load_enumeration()
    plan = inputs.plan
    nodes = {n.id: (n.kind, n.priority, n.pathway) for n in plan.reference_graph.nodes}
    assert nodes == {
        "cyclopentadiene": ("reactant", 1, None),
        "cyclopropene": ("reactant", 1, None),
        "TS1a_n": ("transition_state", 2, "endo"),
        "TS1a_x": ("transition_state", 2, "exo"),
    }
    assert all(len(n.templates) == 1 for n in plan.reference_graph.nodes)
    assert [s.id for s in plan.sites] == ["c7"]
    assert [e.id for e in plan.library] == ["ethyl", "npropyl"]
    assert all(len(e.fragment_orders) == 2 for e in plan.library)
    maps = {m.node_id: m for m in plan.sites[0].maps}
    assert sorted(maps) == ["TS1a_n", "TS1a_x", "cyclopropene"]
    for node in FACE:
        assert maps[node].template.keep == [i for i in range(18) if i != 16]
        assert maps[node].template.delete == [16]
        assert maps[node].template.alignment == [7, 2, 3, 17]
        assert maps[node].constrained_core == [0, 1, 2, 3, 4, 5]
        assert maps[node].forming_bonds == FORMING
    (selectivity,) = plan.selectivity_sets
    assert selectivity.id == "endo_exo"
    assert selectivity.reactant_node_ids == ["cyclopentadiene", "cyclopropene"]
    assert {(p.pathway, p.node_id, p.expected_face) for p in selectivity.pathways} == {
        ("endo", "TS1a_n", (1, 1)),
        ("exo", "TS1a_x", (-1, -1)),
    }
    assert plan.max_candidates == 2
    assert inputs.max_alignment_rmsd_angstrom == 0.15
    assert inputs.orientation_centers == (C7,)


def test_loader_refuses_an_unknown_key(tmp_path: Path) -> None:
    """A key the loader does not know is refused."""
    data: dict[str, Any] = yaml.safe_load(ENUMERATION_YAML.read_text(encoding="utf-8"))
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump({**data, "temperature_k": 298.15}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown \\['temperature_k'\\]"):
        load_enumeration(path)


# --- Site rule, faces, orientation (HF-1, HF-2) ---------------------------------------------------


@pytest.mark.parametrize("name", sorted(FACE))
def test_site_rule_picks_h16(name: str) -> None:
    """The C7 H with the largest angle between C7->H and C7->diene centroid is H16."""
    state = ts(name)
    x = np.asarray(state.coordinates)
    to_diene = x[DIENE].mean(axis=0) - x[C7]
    angles = {}
    for h in (j for j in neighbours(state, C7) if state.symbols[j] == "H"):
        v = x[h] - x[C7]
        cosine = v @ to_diene / np.linalg.norm(v) / np.linalg.norm(to_diene)
        angles[h] = float(np.degrees(np.arccos(cosine)))
    assert sorted(angles) == [16, 17]
    assert max(angles, key=angles.__getitem__) == 16
    assert angles[16] == pytest.approx(ANTI_ANGLE_DEG[name], abs=0.05)


@pytest.mark.parametrize("name", sorted(FACE))
def test_template_face_and_orientation_flip(name: str) -> None:
    """HF-2: the face of each TS; the C7 sign flips between H16 and H17."""
    state = ts(name)
    assert face(state) == FACE[name]
    assert orientation_sign(state, 16) == -orientation_sign(state, 17) != 0


# --- The enumeration ------------------------------------------------------------------------------


def test_enumeration_gives_two_ok_candidates() -> None:
    """N = 2 ok candidates, neutral singlets, no contact, projected count."""
    inputs = load_enumeration()
    result = enumerate_candidates(
        inputs.plan, max_alignment_rmsd_angstrom=inputs.max_alignment_rmsd_angstrom
    )
    assert [(c.candidate_id, c.status) for c in result.candidates] == [
        ("ethyl", "ok"),
        ("npropyl", "ok"),
    ]
    # 2 candidates x 2 TS nodes x 1 template x (seed + re-searches).
    assert result.projected_ts_searches == 4 * (1 + TSEnsembleOptions().max_research)
    for candidate in result.candidates:
        assert candidate.detail is None
        assert len(candidate.records) == 3
        for r in candidate.records:
            assert (r.status, r.close_contact_count) == ("ok", 0)
            assert (r.product_charge, r.product_multiplicity) == (0, 1)
            assert r.alignment_rmsd_angstrom is not None
            assert r.alignment_rmsd_angstrom <= inputs.max_alignment_rmsd_angstrom


@pytest.mark.parametrize(("entry", "node"), sorted(ORDERS))
def test_ts_graft_order_fit_face_and_orientation(entry: str, node: str) -> None:
    """HF-1/HF-2 on every enumerated TS product."""
    inputs = load_enumeration()
    (candidate,) = [c for c in run(inputs) if c.candidate_id == entry]
    r = record(candidate, node, node)
    (library,) = [e for e in inputs.plan.library if e.id == entry]
    assert r.chosen_order_index is not None
    assert library.fragment_orders[r.chosen_order_index][1:3] == ORDERS[entry, node]

    assert r.alignment_rmsd_angstrom is not None
    low, high = FITS[node]
    assert low <= round(r.alignment_rmsd_angstrom, 3) <= high
    mirror = r.order_rmsds_angstrom[1 - r.chosen_order_index]
    if node == "TS1a_x":
        assert mirror == "graft_clash"
    else:
        assert isinstance(mirror, float)
        assert MIRROR_FITS[0] <= round(mirror, 3) <= MIRROR_FITS[1]
    assert r.min_interatomic_distance_angstrom == pytest.approx(1.078, abs=5e-4)

    state = product(candidate, node, node)
    assert len(state.symbols) == ATOMS[entry]
    assert state.symbols[C7] == "C"
    assert r.index_map is not None and r.index_map[C7] == ("template", C7)
    assert face(state) == FACE[node]
    # R takes the replaced H16's side of C7.
    assert orientation_sign(state, substituent(state, r)) == orientation_sign(ts(node), 16)


@pytest.mark.parametrize("entry", sorted(REACTANT_FITS))
def test_reactant_map_fit(entry: str) -> None:
    """The recorded cyclopropene map: one order fits within 0.15 A, with no contact."""
    (candidate,) = [c for c in run(load_enumeration()) if c.candidate_id == entry]
    r = record(candidate, "cyclopropene", "cyclopropene")
    assert r.alignment_rmsd_angstrom == pytest.approx(REACTANT_FITS[entry], abs=5e-5)
    assert r.close_contact_count == 0
    assert len(product(candidate, "cyclopropene", "cyclopropene").symbols) == ATOMS[entry] - 11


# --- The fallback constructs (G8) -----------------------------------------------------------------


@pytest.mark.parametrize("construct", ["graft_time", "run_time"])
def test_fallback_plan_shape(construct: str) -> None:
    """One entry, one TS node with two ranked templates, endo face expected."""
    inputs = load_fallback()[construct]
    plan = inputs.plan
    assert [e.id for e in plan.library] == ["ethyl"]
    (node,) = [n for n in plan.reference_graph.nodes if n.kind == "transition_state"]
    first = {"graft_time": "TS1a_n_cp_h", "run_time": "TS1a_x"}[construct]
    assert node.id == "TS1a_n"
    assert [(t.id, t.rank) for t in node.templates] == [(first, 1), ("TS1a_n", 2)]
    (selectivity,) = plan.selectivity_sets
    (pathway,) = selectivity.pathways
    assert (pathway.node_id, pathway.expected_face) == ("TS1a_n", (1, 1))
    assert inputs.orientation_centers == (C7,)


def test_graft_time_rank_1_is_refused_on_alignment() -> None:
    """Rank 1 is refused ``alignment_rmsd``; rank 2 remains."""
    inputs = load_fallback()["graft_time"]
    (candidate,) = run(inputs)
    assert candidate.status == "ok" and candidate.graph is not None
    refused = record(candidate, "TS1a_n", "TS1a_n_cp_h")
    assert (refused.status, refused.reason) == ("refused", "alignment_rmsd")
    assert refused.alignment_rmsd_angstrom == pytest.approx(0.888, abs=5e-4)
    assert record(candidate, "TS1a_n", "TS1a_n").status == "ok"
    (node,) = [n for n in candidate.graph.nodes if n.id == "TS1a_n"]
    assert [(t.id, t.rank) for t in node.templates] == [("TS1a_n__ethyl", 1)]
    assert face(product(candidate, "TS1a_n", "TS1a_n")) == (1, 1)


def test_run_time_rank_1_grafts_with_the_other_face() -> None:
    """Both templates graft; rank 1's start face is not the expected one."""
    inputs = load_fallback()["run_time"]
    (candidate,) = run(inputs)
    assert candidate.status == "ok" and candidate.graph is not None
    (node,) = [n for n in candidate.graph.nodes if n.id == "TS1a_n"]
    assert [(t.id, t.rank) for t in node.templates] == [
        ("TS1a_x__ethyl", 1),
        ("TS1a_n__ethyl", 2),
    ]
    assert all(r.status == "ok" and r.close_contact_count == 0 for r in candidate.records)
    expected = inputs.plan.selectivity_sets[0].pathways[0].expected_face
    start = face(product(candidate, "TS1a_n", "TS1a_x"))
    assert start == (-1, -1) != expected
    assert face(product(candidate, "TS1a_n", "TS1a_n")) == expected


# --- Provenance -----------------------------------------------------------------------------------


def referenced_xyz() -> list[str]:
    """Every xyz path the two YAMLs name."""
    text = ENUMERATION_YAML.read_text(encoding="utf-8") + FALLBACK_YAML.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"xyz: (xyz/[\w.]+\.xyz)", text)))


def test_sources_has_a_matching_row_for_every_input() -> None:
    """SOURCES.md lists each input with its current sha256."""
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8")
    section = text.split("## v0.7.0 E2E inputs", 1)[1]
    files = referenced_xyz()
    assert files == [
        "xyz/1_cyclopentadiene.xyz",
        "xyz/5_cyclopropene.xyz",
        "xyz/TS1a_n.xyz",
        "xyz/TS1a_x.xyz",
        "xyz/r_ethyl_cyclopropene.xyz",
        "xyz/r_npropyl_cyclopropene.xyz",
    ]
    for name in files:
        (row,) = [line for line in section.splitlines() if line.startswith(f"| `{name}`")]
        assert hashlib.sha256((E2E5 / name).read_bytes()).hexdigest() in row
