"""Tier 4 inputs (v0.6.0 slice 08): transcriptions, provenance, provisional YAMLs, faces, exo graft.

Offline and engine-free. The three exo files are byte-equal to the mission's HF-1 sha256s; their
formulas, fragments, forming distances (HF-1), header-G references (HF-2), face descriptors
(R1/HF-3, slice 05) and the exo graft (HF-8) are checked; both provisional YAMLs load through the
fixture loader, with TJ's 1.5 kcal/mol threshold in the mapped one and no default anywhere.
"""

import hashlib
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from fixtures import DATA, T4_YAMLS, T4Fixture, load_t4_fixture, read_xyz, t4
from m1 import derive_map, forming_core_rmsd_angstrom
from rdkit import Chem
from rdkit.Chem import rdDetermineBonds
from test_t3_inputs import components, formula

from eta_rxncat.conformers import forming_bond_configuration
from eta_rxncat.core import AtomMappingSpec, GraftSpec, MolecularState
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import graft, perceive_bonds

E2E5 = DATA / "e2e5"
XYZ = E2E5 / "xyz"

# Mission HF-1: sha256, formula and fragment count of the three new files.
NEW_FILES = {
    "TS1a_x.xyz": ("ec319a528d3efd0d7c14fb1d018d31d57eae85e794df59761665ed4d0f684d60", "C8H10", 2),
    "TS1b_x.xyz": ("2a0b8362cdd36464c5f3f7a196927005c1cc933f3fdc6a693ae0d56ff365fd82", "C9H12", 2),
    "P1b_x.xyz": ("ca8706431f6e8b57662a3f65196a9ca3cba3288a4eda68308f7bc3c9699b5eec", "C9H12", 1),
}
FORMING = ((1, 2), (3, 5))


def header_g(name: str) -> float:
    """Return the Hartree G printed on line 2 of a Liu xyz file."""
    header = (XYZ / name).read_text(encoding="utf-8").splitlines()[1]
    match = re.search(r"G\s*=\s*(-\d+\.\d+)", header) or re.search(r"G=(-\d+\.\d+)", header)
    assert match, header
    return float(match.group(1))


def state(name: str) -> MolecularState:
    """Read a Tier 4 structure."""
    return read_xyz(XYZ / name, 0, 1)


# --- Files, provenance, connectivity -------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_file_sha256(name: str) -> None:
    """Each transcription is byte-equal to the mission's HF-1 sha256."""
    assert hashlib.sha256((XYZ / name).read_bytes()).hexdigest() == NEW_FILES[name][0]


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_sources_row(name: str) -> None:
    """SOURCES.md has a row with the file, its sha256 and its SI page."""
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| `xyz/{name}`"))
    assert NEW_FILES[name][0] in row
    assert re.search(r"\bS(9|10|20)\b", row)
    assert "Liu" in row


def test_sources_records_the_header_energies_and_procedure() -> None:
    """SOURCES.md has the printed E/H/G of the transcribed files and the pdftotext procedure."""
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8")
    for printed in ("−349.872275", "−349.679329", "−349.718879", "−349.957548", "−349.797634"):
        assert printed in text
    assert "pdftotext" in text and "ja408437u_SI.pdf" in text
    assert "98f37dc41f252f4e031e750d9343c3c478d4e5651940c3d0ed54e587b476f6af" in text


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_formula_and_connectivity(name: str) -> None:
    """Formula; 2 fragments for a TS, 1 for the product; every H degree 1, no C below degree 3."""
    mol = state(name)
    _, expected_formula, n_fragments = NEW_FILES[name]
    assert formula(mol.symbols) == expected_formula
    bonds = perceive_bonds(mol)
    _, parts = components(len(mol.symbols), bonds)
    assert len(parts) == n_fragments
    degree = Counter(a for bond in bonds for a in bond)
    assert all(degree[k] == 1 for k, s in enumerate(mol.symbols) if s == "H")
    assert all(degree[k] >= 3 for k, s in enumerate(mol.symbols) if s == "C")
    assert len(mol.symbols) == {"TS1a_x.xyz": 18, "TS1b_x.xyz": 21, "P1b_x.xyz": 21}[name]


@pytest.mark.parametrize(("name", "distance"), [("TS1a_x.xyz", 2.353), ("TS1b_x.xyz", 2.266)])
def test_forming_distances(name: str, distance: float) -> None:
    """HF-1: both forming pairs join the two fragments, at the measured distance (1e-3)."""
    mol = state(name)
    _, parts = components(len(mol.symbols), perceive_bonds(mol))
    coords = np.asarray(mol.coordinates)
    for i, j in FORMING:
        assert not any(i in part and j in part for part in parts)
        assert float(np.linalg.norm(coords[j] - coords[i])) == pytest.approx(distance, abs=1e-3)


def test_header_g_gives_liu_ddg() -> None:
    """HF-2: G(exo) - G(endo) from the xyz headers is +4.273 and +1.849 kcal/mol (0.005)."""
    unmapped = (header_g("TS1a_x.xyz") - header_g("TS1a_n.xyz")) * HARTREE_KCAL_MOL
    mapped = (header_g("TS1b_x.xyz") - header_g("TS1b_n.xyz")) * HARTREE_KCAL_MOL
    assert unmapped == pytest.approx(4.273, abs=0.005)
    assert mapped == pytest.approx(1.849, abs=0.005)
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8").split("## Tier 4 references")[1]
    assert "4.273" in text and "1.849" in text


def test_p1b_x_smiles_is_what_rdkit_derives() -> None:
    """The YAML's provisional SMILES is DetermineBonds + AssignStereochemistryFrom3D on P1b_x."""
    block = (XYZ / "P1b_x.xyz").read_text(encoding="utf-8")
    mol = Chem.MolFromXYZBlock(block)
    rdDetermineBonds.DetermineBonds(mol, charge=0)
    Chem.AssignStereochemistryFrom3D(mol)
    derived = Chem.MolToSmiles(Chem.RemoveHs(mol))
    assert t4("t4_mapped_selectivity_pruned.yaml").downstream is not None
    assert derived == t4("t4_mapped_selectivity_pruned.yaml").downstream.smiles  # type: ignore[union-attr]


# --- Faces (R1, HF-3; slice 05's descriptor on the seed graph) -------------------------------


@pytest.mark.parametrize(
    ("name", "face"),
    [
        ("TS1a_n.xyz", (1, 1)),
        ("TS1b_n.xyz", (1, 1)),
        ("TS1a_x.xyz", (-1, -1)),
        ("TS1b_x.xyz", (-1, -1)),
    ],
)
def test_face_of_liu_files(name: str, face: tuple[int, int]) -> None:
    """Endo is (+1, +1) and exo (-1, -1) on all four Liu TSs, with each file's own graph."""
    mol = state(name)
    assert forming_bond_configuration(mol, FORMING, perceive_bonds(mol)) == face


# --- YAMLs ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module", params=T4_YAMLS)
def fixture(request: pytest.FixtureRequest) -> T4Fixture:
    """Each Tier 4 fixture, loaded."""
    return t4(request.param)


def test_yaml_basics(fixture: T4Fixture) -> None:
    """Two labelled pathways, the active set, forming bonds, kind and temperature."""
    assert [p.pathway for p in fixture.pathways] == ["endo", "exo"]
    for p in fixture.pathways:
        assert p.active_atom_indices == (0, 1, 2, 3, 4, 5)
        assert p.forming_bonds == FORMING
    assert fixture.kind == "de" and fixture.temperature_k == 298.15
    assert fixture.gfn2_gate == {"endo_major": True, "ddG_dagger_greater_than_kcal_mol": 0.5}


def test_yaml_header_g_matches_the_xyz_files(fixture: T4Fixture) -> None:
    """The literature G values in the YAML equal the xyz headers, and give Liu's ddG."""
    for p in fixture.pathways:
        g = fixture.literature["structures"][p.ts_id]["G_hartree"]
        assert g == pytest.approx(header_g(f"{p.ts_id}.xyz"), abs=1e-9)
    endo, exo = (fixture.literature["structures"][p.ts_id]["G_hartree"] for p in fixture.pathways)
    assert (exo - endo) * HARTREE_KCAL_MOL == pytest.approx(
        fixture.liu_header_ddG_dagger_kcal_mol, abs=0.005
    )


def test_unmapped_yaml() -> None:
    """Unmapped: TS1a_n vs TS1a_x, +4.3 / +4.273, UMA window [2.3, 6.3], no rule or downstream."""
    f = t4("t4_endo_exo_unmapped.yaml")
    assert [p.ts_id for p in f.pathways] == ["TS1a_n", "TS1a_x"]
    assert f.reference_ddG_dagger_kcal_mol == 4.3 and f.liu_header_ddG_dagger_kcal_mol == 4.273
    assert f.uma_window.contains(2.3) and f.uma_window.contains(6.3)
    assert not f.uma_window.contains(2.29) and not f.uma_window.contains(6.31)
    assert f.pruning_rule is None and f.downstream is None
    assert all(p.start.form == "start_xyz" for p in f.pathways)
    assert {s.species_id for s in f.species} == {"cyclopentadiene", "cyclopropene"}


def test_mapped_yaml() -> None:
    """Mapped: TS1b_n vs TS1b_x, +1.8 / +1.849, UMA window (0.5, 3.8], TJ's 1.5 threshold."""
    f = t4("t4_mapped_selectivity_pruned.yaml")
    assert [p.ts_id for p in f.pathways] == ["TS1b_n", "TS1b_x"]
    assert f.reference_ddG_dagger_kcal_mol == 1.8 and f.liu_header_ddG_dagger_kcal_mol == 1.849
    assert not f.uma_window.contains(0.5) and f.uma_window.contains(0.51)
    assert f.uma_window.contains(3.8) and not f.uma_window.contains(3.81)
    assert [p.start.form for p in f.pathways] == ["start_from_fixture", "start_grafts"]
    rule = f.pruning_rule
    assert rule is not None and rule.threshold_kcal_mol == 1.5
    assert rule.pathways == ("endo", "exo") and rule.metric == "ddG_dagger_kcal_mol"
    assert rule.prune == "minor_pathway_priority_ge_2"
    node = f.downstream
    assert node is not None
    assert node.node_id == "downstream_exo_minor" and node.species_id == "P1b_x"
    assert node.pathway == "exo" and node.priority == 2
    assert node.xyz.name == "P1b_x.xyz" and "P1a_n" not in node.xyz.name
    assert hashlib.sha256(node.xyz.read_bytes()).hexdigest() == NEW_FILES["P1b_x.xyz"][0]


def test_mapped_endo_start_comes_from_the_promoted_m1_fixture() -> None:
    """The endo start is TS1b_n from the v0.4.0 relaxed M1 fixture, with the active set."""
    f = t4("t4_mapped_selectivity_pruned.yaml")
    start = f.pathway("endo").start_state("xtb")
    assert len(start.symbols) == 21 and start.active_atom_indices == [0, 1, 2, 3, 4, 5]
    with pytest.raises(ValueError, match="recipe"):
        f.pathway("endo").start_state()


# --- The loader refuses what it should -----------------------------------------------------------


def edited(tmp_path: Path, name: str, edit: Any) -> Path:
    """Copy the e2e5 data dir, apply ``edit(dict)`` to one YAML and return its path."""
    copy = tmp_path / "e2e5"
    shutil.copytree(E2E5, copy, ignore=shutil.ignore_patterns("*.sqlite"))
    path = copy / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


MAPPED = "t4_mapped_selectivity_pruned.yaml"
UNMAPPED = "t4_endo_exo_unmapped.yaml"


@pytest.mark.parametrize(
    ("name", "edit", "message"),
    [
        (MAPPED, lambda d: d["pruning_rule"].pop("threshold_kcal_mol"), "threshold_kcal_mol"),
        (MAPPED, lambda d: d["pruning_rule"].update(threshold_kcal_mol=0.0), "threshold"),
        (MAPPED, lambda d: d["pruning_rule"].update(pathways=["endo", "other"]), "pathways"),
        (MAPPED, lambda d: d["downstream_exo_minor"].update(pathway="nope"), "unknown"),
        (MAPPED, lambda d: d["downstream_exo_minor"].pop("smiles"), "downstream_exo_minor keys"),
        (UNMAPPED, lambda d: d.update(surprise=1), "unknown"),
        (UNMAPPED, lambda d: d.update(schema=2), "schema"),
        (UNMAPPED, lambda d: d["pathways"].pop(), "exactly two"),
        (UNMAPPED, lambda d: d["pathways"][1].update(pathway="endo"), "exactly two"),
        (UNMAPPED, lambda d: d["selectivity"]["uma_window_kcal_mol"].update(low=9.0), "low < high"),
        (
            UNMAPPED,
            lambda d: d["pathways"][0]["reference"].update(start_to_reference_map=[0]),
            "permutation",
        ),
    ],
)
def test_loader_refusals(tmp_path: Path, name: str, edit: Any, message: str) -> None:
    """Missing or unknown keys, a threshold without a value, and bad pathways are refused."""
    with pytest.raises(ValueError, match=message):
        load_t4_fixture(edited(tmp_path, name, edit))


# --- The exo graft (HF-8; no engine) -------------------------------------------------------------


def test_exo_graft_matches_the_m1_lists_and_reaches_ts1b_x() -> None:
    """Cyclobutene on TS1a_x with the M1 lists unchanged: valid, no contacts, 0.046 A to TS1b_x."""
    f = t4(MAPPED)
    exo = f.pathway("exo")
    block = exo.start.grafts
    assert block is not None
    (g,) = block["grafts"]
    m1 = yaml.safe_load((E2E5 / "m1_ts1a_n_to_ts1b_n.yaml").read_text(encoding="utf-8"))
    assert g["keep"] == m1["keep"] and g["delete"] == m1["delete"]
    assert g["alignment_pairs"] == m1["alignment_pairs"]
    assert g["fragment_delete"] == m1["fragment_delete"]
    assert g["constrained_core"] == m1["constrained_core"] == block["pre_relax"]["core"]
    template = read_xyz(E2E5 / block["template"], 0, 1)
    template = MolecularState.model_validate(
        {**template.model_dump(), "active_atom_indices": list(exo.active_atom_indices)}
    )
    spec = GraftSpec(
        template=AtomMappingSpec(
            keep=list(g["keep"]),
            delete=list(g["delete"]),
            alignment=[t for t, _ in g["alignment_pairs"]],
        ),
        fragment_alignment=[x for _, x in g["alignment_pairs"]],
        fragment_delete=list(g["fragment_delete"]),
        constrained_core=list(g["constrained_core"]),
        product_charge=0,
        product_multiplicity=1,
    )
    result = graft(template, read_xyz(E2E5 / block["fragment"], 0, 1), spec)
    assert formula(result.product.symbols) == "C9H12" and result.close_contacts == []
    assert result.constrained_core_product_indices == [1, 2, 3, 5]
    derived = derive_map(result, exo.reference)
    assert derived.graft_to_ts1b_n_map == list(exo.start_to_reference_map)
    rmsd = forming_core_rmsd_angstrom(
        result.product.coordinates, exo.reference, [1, 2, 3, 5], derived.graft_to_ts1b_n_map
    )
    assert rmsd == pytest.approx(0.046, abs=0.002) and rmsd < 0.10
