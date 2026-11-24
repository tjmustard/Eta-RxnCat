"""Tier 3 inputs (v0.5.0 slice 07): transcriptions, provenance, provisional YAMLs, graft, energies.

Tier D (default suite, no engine): sha256, formula and connectivity of the six new files; each
YAML's forming bonds, R16 active set, references and window; the TS4a dual graft and its map.
R9 (``gpu`` + ``acceptance``): PySCF M06-2X/6-31G(d) single points against Liu's electronic
energies, |dE| <= 1e-4 Eh on every Liu file (two of TJ's committed files are the controls).
"""

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml
from fixtures import DATA, T3_YAMLS, TSFixture, load_ts_fixture, read_xyz, t3
from m1 import _graph_mol, forming_core_rmsd_angstrom

from eta_rxncat.core import AtomMappingSpec, GraftResult, GraftSpec, MolecularState, ThermoConfig
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import graft, perceive_bonds
from eta_rxncat.orchestrator import standard_state_shift_kcal_mol

E2E5 = DATA / "e2e5"
XYZ = E2E5 / "xyz"

# Mission HF-1 sha256s and formulas of the six slice-07 files.
NEW_FILES = {
    "TS3a.xyz": ("6bf308b6846732718499d2370f355116a849a232f476c27a026dafb5ab1ea1b4", "C7H10N4", 2),
    "TS4a.xyz": ("b00f6a874efd2b30112e34d2cb16892923f73b756e7bdbca4a2f6583b4bf008c", "C7H4F6N4", 2),
    "cyclobutenone.xyz": (
        "c489e5124f42895bb0408f127aa10d51db70ccfbd72f4cf5c929c10052f4f30c",
        "C4H4O",
        1,
    ),
    "TS_N4.xyz": ("cf7e45014bdab5971b2c993da3f2d5125ce744a8def5bda64998e047dc3dc46f", "C9H10O", 2),
    "3_dimethyltetrazine.xyz": (
        "e42ed53adaa7bc3a9fe542d88cafb632d4351c3e419e9b2b3b3b961744a7662d",
        "C4H6N4",
        1,
    ),
    "4_bis_cf3_tetrazine.xyz": (
        "174c23d2c794196f7d1fa5367529fe623e1529007bab76cb32b9139816e92f74",
        "C4N4F6",
        1,
    ),
}

# Mission HF-2: forming distances (Angstrom) at the literature TSs, per YAML.
HF2_DISTANCES = {
    "t3_ts1a_n_unmapped.yaml": [2.336, 2.336],
    "t3_ts1b_n_mapped.yaml": [2.241, 2.241],
    "t3_ts3a_unmapped.yaml": [2.274, 2.274],
    "t3_ts4a_mapped.yaml": [2.378, 2.378],
    "t3_n4_unmapped.yaml": [2.166, 2.309],
}


def formula(symbols: list[str]) -> str:
    """Return a formula in the order the slice spec writes them (C, H, then the rest by name)."""
    counts = Counter(symbols)
    order = ["C", "H"] + sorted(s for s in counts if s not in ("C", "H"))
    if "H" not in counts:  # C4N4F6 is written C, N, F in the spec
        order = ["C", "N", "F"] + sorted(s for s in counts if s not in ("C", "N", "F"))
    return "".join(f"{s}{counts[s] if counts[s] > 1 else ''}" for s in order if s in counts)


def components(
    n_atoms: int, bonds: list[tuple[int, int]]
) -> tuple[dict[int, set[int]], list[set[int]]]:
    """Return the adjacency and the connected components of a bond graph."""
    adjacency: dict[int, set[int]] = {i: set() for i in range(n_atoms)}
    for i, j in bonds:
        adjacency[i].add(j)
        adjacency[j].add(i)
    seen: set[int] = set()
    parts = []
    for start in range(n_atoms):
        if start in seen:
            continue
        part: set[int] = set()
        stack = [start]
        while stack:
            atom = stack.pop()
            if atom not in part:
                part.add(atom)
                stack.extend(adjacency[atom] - part)
        seen |= part
        parts.append(part)
    return adjacency, parts


def r16_active_set(state: MolecularState, forming: tuple[tuple[int, int], ...]) -> list[int]:
    """Mission R16: forming atoms plus every heavy atom on a 4-atom path between the diene termini.

    The diene fragment is the one whose two forming atoms are not bonded to each other (the
    dienophile's are); every 4-atom path counts, so a symmetric ring contributes both sides.
    """
    adjacency, parts = components(len(state.symbols), perceive_bonds(state))
    part_of = {a: next(k for k, part in enumerate(parts) if a in part) for b in forming for a in b}
    active = {a for b in forming for a in b}
    for k in set(part_of.values()):
        u, v = (a for a in part_of if part_of[a] == k)
        if v in adjacency[u]:
            continue
        for x in adjacency[u]:
            for y in adjacency[x] - {u, v}:
                if v in adjacency[y] and state.symbols[x] != "H" and state.symbols[y] != "H":
                    active |= {x, y}
    return sorted(active)


# --- Files, provenance, connectivity ---------------------------------------------------------


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_file_sha256(name: str) -> None:
    """Each re-transcribed file is byte-equal to the mission's HF-1 sha256."""
    assert hashlib.sha256((XYZ / name).read_bytes()).hexdigest() == NEW_FILES[name][0]


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_sources_row(name: str) -> None:
    """SOURCES.md has a row with the file and its sha256."""
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith(f"| `xyz/{name}`"))
    assert NEW_FILES[name][0] in row


@pytest.mark.parametrize("name", sorted(NEW_FILES))
def test_formula_and_connectivity(name: str) -> None:
    """Formula; 2 fragments for a TS, 1 for a minimum; H/F degree 1; no C below degree 3."""
    state = read_xyz(XYZ / name, 0, 1)
    _, expected_formula, n_fragments = NEW_FILES[name]
    assert formula(state.symbols) == expected_formula
    bonds = perceive_bonds(state)
    _, parts = components(len(state.symbols), bonds)
    assert len(parts) == n_fragments
    degree = Counter(a for bond in bonds for a in bond)
    assert all(degree[k] == 1 for k, s in enumerate(state.symbols) if s in ("H", "F"))
    assert all(degree[k] >= 3 for k, s in enumerate(state.symbols) if s == "C")


# --- YAMLs ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module", params=T3_YAMLS)
def fixture(request: pytest.FixtureRequest) -> TSFixture:
    """Each Tier 3 TS fixture, loaded."""
    return t3(request.param)


def test_forming_bonds_inter_fragment_within_window(fixture: TSFixture) -> None:
    """Forming bonds join the two fragments of the reference TS at 1.9-2.7 A (HF-2 +- 1e-3)."""
    ref = fixture.reference
    _, parts = components(len(ref.symbols), perceive_bonds(ref))
    assert len(parts) == 2
    coords = np.asarray(ref.coordinates)
    distances = []
    for i, j in fixture.forming_bonds:
        assert not any(i in part and j in part for part in parts), (i, j)
        distances.append(float(np.linalg.norm(coords[j] - coords[i])))
    assert all(1.9 <= d <= 2.7 for d in distances)
    expected = HF2_DISTANCES[fixture.path.name]
    assert distances == pytest.approx(expected, abs=1e-3)


def test_active_set_follows_r16(fixture: TSFixture) -> None:
    """The YAML's active set equals R16 re-derived from its forming bonds on the reference TS."""
    assert list(fixture.active_atom_indices) == r16_active_set(
        fixture.reference, fixture.forming_bonds
    )


def references() -> dict[str, tuple[float, float]]:
    """Read SOURCES.md's References table: TS -> (dG 1 atm, dG 1 M), kcal/mol."""
    text = (E2E5 / "SOURCES.md").read_text(encoding="utf-8").split("## References", 1)[1]
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"-?\d+\.\d+", cells[3]):
            rows[cells[0]] = (float(cells[3]), float(cells[4]))
    return rows


def test_reference_barrier_from_literature_g(fixture: TSFixture) -> None:
    """dG(1 atm) from the YAML's literature G values equals SOURCES.md and the YAML (1e-3)."""
    structures = fixture.literature["structures"]
    g_ts = structures[fixture.ts_id]["G_hartree"]
    g_reactants = sum(structures[s]["G_hartree"] * c for s, c in fixture.barrier.reactants)
    dg_1atm = (g_ts - g_reactants) * HARTREE_KCAL_MOL
    shift = standard_state_shift_kcal_mol(ThermoConfig())
    dg_1m = dg_1atm + fixture.barrier.delta_n * shift
    name = "N4" if fixture.ts_id == "TS_N4" else fixture.ts_id
    sources_1atm, sources_1m = references()[name]
    assert dg_1atm == pytest.approx(sources_1atm, abs=1e-3)
    assert dg_1m == pytest.approx(sources_1m, abs=1e-3)
    assert fixture.literature["dG_dagger_1atm_kcal_mol"] == pytest.approx(dg_1atm, abs=1e-3)
    assert fixture.literature["dG_dagger_1M_kcal_mol"] == pytest.approx(dg_1m, abs=1e-3)


def test_window_is_the_1m_reference_plus_minus_7(fixture: TSFixture) -> None:
    """The window is the 1 M reference +- 7 kcal/mol (to 0.1), TS1b_n TJ's [20, 34]."""
    low, high = fixture.window_dG_dagger_1M_kcal_mol
    if fixture.ts_id == "TS1b_n":
        assert (low, high) == (20.0, 34.0)
        return
    centre = fixture.literature["dG_dagger_1M_kcal_mol"]
    assert low == pytest.approx(centre - 7.0, abs=0.05)
    assert high == pytest.approx(centre + 7.0, abs=0.05)


def test_barrier_conserves_atoms_against_the_reference(fixture: TSFixture) -> None:
    """The reactants' SMILES conserve atoms and charge against the reference TS (R1)."""
    atoms, charge = fixture.barrier.reactant_composition()
    assert atoms == Counter(fixture.reference.symbols)
    assert charge == fixture.reference.charge == fixture.charge


def test_unmapped_start_is_the_reference() -> None:
    """For the unmapped fixtures the start geometry is the reference and the map the identity."""
    for name in ("t3_ts1a_n_unmapped.yaml", "t3_ts3a_unmapped.yaml", "t3_n4_unmapped.yaml"):
        f = t3(name)
        assert f.start.form == "start_xyz"
        assert f.start_state().coordinates == f.reference.coordinates
        assert list(f.start_to_reference_map) == list(range(len(f.reference.symbols)))


@pytest.mark.parametrize("recipe", ["xtb", "uma"])
def test_ts1b_n_start_from_the_promoted_m1_fixture(recipe: str) -> None:
    """TS1b_n starts from M1's promoted relaxed product; it has TS1b_n's formula."""
    f = t3("t3_ts1b_n_mapped.yaml")
    start = f.start_state(recipe)
    assert Counter(start.symbols) == Counter(f.reference.symbols)
    assert start.active_atom_indices == [0, 1, 2, 3, 4, 5]
    mapped = [f.reference.symbols[f.start_to_reference_map[k]] for k in range(len(start.symbols))]
    assert mapped == start.symbols


@pytest.mark.parametrize(
    ("edit", "fragment"),
    [
        (lambda d: d.update(extra=1), "unknown ['extra']"),
        (lambda d: d["ts"].update(start_xyz="xyz/TS3a.xyz"), "exactly one of"),
        (lambda d: d["ts"].update(colour="red"), "unknown ['colour']"),
        (lambda d: d["barrier"].update(reactants=[["nobody", 1]]), "are not species"),
        (lambda d: d["barrier"].update(window_dG_dagger_1M_kcal_mol=[5.0, 1.0]), "low < high"),
        (lambda d: d["reference"].update(start_to_reference_map=[0, 0]), "not a permutation"),
        (
            lambda d: d["ts"]["start_grafts"]["grafts"][0].update(keep_all=True),
            "unknown ['keep_all']",
        ),
        (lambda d: d.update(schema=2), "schema must be 1"),
    ],
)
def test_loader_refusals(tmp_path: Path, edit: Any, fragment: str) -> None:
    """Unknown keys, two start forms, unknown reactants, bad windows and maps are refused."""
    data = yaml.safe_load((E2E5 / "t3_ts4a_mapped.yaml").read_text(encoding="utf-8"))
    edit(data)
    path = tmp_path / "t3.yaml"
    (tmp_path / "xyz").symlink_to(XYZ)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(fragment)):
        load_ts_fixture(path)


# --- TS4a: two single CF3 grafts on TS3a (mission R22, HF-10; no engine) ------------------------


def ts4a_grafts() -> tuple[GraftResult, GraftResult]:
    """Run the two grafts of t3_ts4a_mapped.yaml; Liu's TS4a is never a donor (N13)."""
    f = t3("t3_ts4a_mapped.yaml")
    block = f.start.grafts
    assert block is not None
    template = read_xyz(E2E5 / block["template"], 0, 1)
    template = MolecularState.model_validate(
        {**template.model_dump(), "active_atom_indices": list(f.active_atom_indices)}
    )
    fragment = read_xyz(E2E5 / block["fragment"], 0, 1)
    results = []
    for g in block["grafts"]:
        spec = GraftSpec(
            template=AtomMappingSpec(
                keep=list(g["keep"]),
                delete=list(g["delete"]),
                alignment=[t for t, _ in g["alignment_pairs"]],
            ),
            fragment_alignment=[fr for _, fr in g["alignment_pairs"]],
            fragment_delete=list(g["fragment_delete"]),
            constrained_core=list(g["constrained_core"]),
            product_charge=0,
            product_multiplicity=1,
        )
        result = graft(template, fragment, spec)
        results.append(result)
        template = result.product
    return results[0], results[1]


def test_ts4a_dual_graft() -> None:
    """C7H4F6N4, no close contacts, alignment RMSDs 0.1462 / 0.1463 A (HF-10)."""
    first, second = ts4a_grafts()
    assert formula(second.product.symbols) == "C7H4F6N4"
    assert first.close_contacts == [] and second.close_contacts == []
    assert first.alignment_rmsd_angstrom == pytest.approx(0.1462, abs=1e-3)
    assert second.alignment_rmsd_angstrom == pytest.approx(0.1463, abs=1e-3)
    assert second.constrained_core_product_indices == [0, 3, 6, 7]
    assert second.active_product_indices == list(range(8))


def test_ts4a_map_and_forming_core_rmsd() -> None:
    """The stated-rule map re-derived equals the YAML's; forming-core RMSD 0.0599 A (HF-10)."""
    _, second = ts4a_grafts()
    f = t3("t3_ts4a_mapped.yaml")
    reference = f.reference
    source = _graph_mol(second.product.symbols, list(second.source_bonds))
    target = _graph_mol(reference.symbols, perceive_bonds(reference))
    matches = target.GetSubstructMatches(
        source, uniquify=False, useChirality=False, maxMatches=100000
    )
    assert len(matches) == 576
    derived = list(min(matches))
    assert derived == list(f.start_to_reference_map)
    rmsd = forming_core_rmsd_angstrom(second.product.coordinates, reference, [0, 3, 6, 7], derived)
    assert rmsd == pytest.approx(0.0599, abs=1e-3)


# --- R9: PySCF reproduction of Liu's electronic energies (gpu + acceptance) ----------------------

R9_CASES = {
    "TS1a_n.xyz": (-310.559154, "control"),
    "5_cyclopropene.xyz": (-116.562552, "control"),
    "TS3a.xyz": (-491.366826, "target"),
    "TS4a.xyz": (-1086.627595, "target"),
    "3_dimethyltetrazine.xyz": (-374.809570, "target"),
    "4_bis_cf3_tetrazine.xyz": (-970.056992, "target"),
}
R9_BOUND_HARTREE = 1e-4
"""Mission R9: |E_pyscf - E_Liu| on every Liu file; never raised by a seat."""


@pytest.mark.gpu
@pytest.mark.acceptance
@pytest.mark.parametrize("name", list(R9_CASES))
def test_r9_pyscf_reproduces_liu_energy(name: str) -> None:
    """M06-2X/6-31G(d), Cartesian d (Gaussian 6D, R30), no DF, grid level 4 (R31), vs Liu's E."""
    from eta_rxncat.core import StageConfig
    from eta_rxncat.engines import PySCFEngine

    liu, role = R9_CASES[name]
    engine = PySCFEngine.from_stage(
        StageConfig(
            kind="single_point",
            engine="pyscf_gpu_cpu",
            method="m062x",
            basis="6-31g*",
            options={"cartesian_basis": True, "density_fit": False, "grids_level": 4},
        ),
        device="cuda",
    )
    state = read_xyz(XYZ / name, 0, 1)
    result = engine.evaluate(state, forces=False, hessian=False)
    delta = result.energy_hartree - liu
    print(
        json.dumps(
            {
                "file": name,
                "n_ao": int(engine._build_mol(state, "6-31g*", "none").nao),
                "role": role,
                "energy_pyscf_hartree": result.energy_hartree,
                "energy_liu_hartree": liu,
                "delta_hartree": delta,
                "delta_kcal_mol": delta * HARTREE_KCAL_MOL,
                "device": result.device,
                "wall_time_s": result.wall_time_s,
            },
            sort_keys=True,
        )
    )
    assert math.isfinite(delta)
    assert abs(delta) <= R9_BOUND_HARTREE
