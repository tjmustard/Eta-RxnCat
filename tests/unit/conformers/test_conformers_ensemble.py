"""Tests for dedup, the energy window, mirror degeneracy and ensembles (v0.3.0 slice 05).

R3, R9, R37; DV-11. Geometries are UFF-optimized with GeometricOptimizer (geomeTRIC is in the dev
group, so this runs in the default suite).
"""

import math
from dataclasses import dataclass

import pytest
from conformers_helpers import P1A_N, embedded, optimize, record

from eta_rxncat.conformers import (
    ConformerInputError,
    ConformerOptions,
    EnsembleEmptyError,
    Kept,
    assign_degeneracy,
    build_ensemble,
    conformer_chiral,
    dedup,
    dihedral_deg,
    drop_mirror_partners,
    energy_window,
    generate,
    graph_achiral,
)
from eta_rxncat.core import (
    ConformerRecord,
    MolecularState,
    OptimizationResult,
    ThermoAnalysisOptions,
)
from eta_rxncat.engines import kcal_mol_to_hartree
from eta_rxncat.thermo import rotational_symmetry_number

OPTIONS = ConformerOptions()
RT_298 = 6.02214076e23 * 1.380649e-23 * 298.15 / (4.3597447222071e-18 * 6.02214076e23)


@dataclass(frozen=True)
class Butane:
    """Every butane pool member (seed 42, defaults) UFF-optimized."""

    results: list[OptimizationResult]

    @property
    def states(self) -> list[MolecularState]:
        """Optimized states."""
        return [r.final_state for r in self.results]

    @property
    def energies(self) -> list[float]:
        """Optimized energies (Eh)."""
        return [r.final_energy_hartree for r in self.results]


@pytest.fixture(scope="module")
def butane() -> Butane:
    """Generate the butane pool and UFF-optimize every member (about 40 s)."""
    pool = generate("CCCC", charge=0, spin_multiplicity=1, options=OPTIONS)
    return Butane([optimize(m.state) for m in pool.members])


def classify(state: MolecularState) -> str:
    """Return 'anti' (|phi| > 120) or 'gauche' for butane's C-C-C-C dihedral."""
    return "anti" if abs(dihedral_deg(state, 0, 1, 2, 3)) > 120.0 else "gauche"


def records_for(b: Butane, indices: list[int]) -> list[ConformerRecord]:
    """Dedup, window, assign g and build records for the members at ``indices``."""
    states = [b.states[i] for i in indices]
    energies = [b.energies[i] for i in indices]
    kept, _ = energy_window(dedup(states, energies, OPTIONS, smiles="CCCC"), energies, OPTIONS)
    return [
        record(
            b.results[indices[k.index]],
            "CCCC",
            assign_degeneracy(states[k.index], "CCCC", OPTIONS),
            [indices[i] for i in k.source_ids],
        )
        for k in kept
    ]


def test_butane_one_anti_one_gauche(butane: Butane) -> None:
    """Dedup -> anti, g+, g-; mirror partners dropped -> one anti (g 1) and one gauche (g 2)."""
    records = records_for(butane, list(range(len(butane.results))))
    assert sorted(classify(r.state) for r in records) == ["anti", "gauche", "gauche"]
    kept, dropped = drop_mirror_partners(records, "CCCC", OPTIONS)
    assert len(dropped) == 1 and dropped[0][1] == "mirror_partner"
    by_class = {classify(r.state): r for r in kept}
    assert sorted(by_class) == ["anti", "gauche"] and len(kept) == 2
    assert by_class["anti"].degeneracy == 1
    assert by_class["gauche"].degeneracy == 2


def test_butane_gauche_g_survives_losing_one_enantiomer(butane: Butane) -> None:
    """With every g+ member removed before dedup, the gauche record still has g = 2 (R3)."""
    no_gplus = [
        i for i, s in enumerate(butane.states) if not 0.0 < dihedral_deg(s, 0, 1, 2, 3) < 120.0
    ]
    assert len(no_gplus) < len(butane.states)
    records = records_for(butane, no_gplus)
    kept, dropped = drop_mirror_partners(records, "CCCC", OPTIONS)
    assert dropped == []
    gauche = [r for r in kept if classify(r.state) == "gauche"]
    assert len(gauche) == 1 and gauche[0].degeneracy == 2
    assert [r.degeneracy for r in kept if classify(r.state) == "anti"] == [1]


def test_dedup_merges_into_lowest_energy(butane: Butane) -> None:
    """Representatives are ordered by energy; every input lands in exactly one group."""
    kept = dedup(butane.states, butane.energies, OPTIONS, smiles="CCCC")
    energies = [butane.energies[k.index] for k in kept]
    assert energies == sorted(energies)
    for k in kept:
        assert k.index == min(k.source_ids, key=lambda i: (butane.energies[i], i))
    merged = sorted(i for k in kept for i in k.source_ids)
    assert merged == list(range(len(butane.states)))


def test_dedup_ties_go_to_lower_index() -> None:
    """Two identical states with equal energy merge into the lower index."""
    st = embedded("O")
    assert dedup([st, st], [-1.0, -1.0], OPTIONS, smiles="O") == [Kept(index=0, source_ids=(0, 1))]


def test_dedup_rejects_mismatch() -> None:
    """Length mismatch and foreign atom order raise ConformerInputError."""
    st = embedded("O")
    with pytest.raises(ConformerInputError, match="2 states but 1"):
        dedup([st, st], [-1.0], OPTIONS, smiles="O")
    swapped = MolecularState(
        symbols=["H", "O", "H"], coordinates=st.coordinates, charge=0, spin_multiplicity=1
    )
    with pytest.raises(ConformerInputError, match="AddHs order"):
        dedup([swapped], [-1.0], OPTIONS, smiles="O")


def test_energy_window() -> None:
    """Inside: E - E_min <= window (kcal/mol); outside otherwise."""
    kept = [Kept(0, (0,)), Kept(1, (1,)), Kept(2, (2,))]
    window = kcal_mol_to_hartree(OPTIONS.energy_window_kcal_mol)
    energies = [0.0, window, window * 1.001]
    inside, outside = energy_window(kept, energies, OPTIONS)
    assert [k.index for k in inside] == [0, 1]
    assert [k.index for k in outside] == [2]
    assert energy_window([], [], OPTIONS) == ([], [])


# degeneracy


@pytest.mark.parametrize(
    ("smiles", "achiral"),
    [("CCCC", True), ("C[C@H](O)CC", False), (P1A_N, True), ("C/C=C/C", True)],
)
def test_graph_achiral(smiles: str, achiral: bool) -> None:
    """Butane and meso/Cs P1a_n are graph-achiral; a stereocentre is not (R37: E/Z ignored)."""
    assert graph_achiral(smiles) is achiral


def test_graph_achiral_rejects_bad_smiles() -> None:
    """An unparsable SMILES raises ConformerInputError."""
    with pytest.raises(ConformerInputError):
        graph_achiral("C(")


def test_p1a_n_cs_geometry_is_not_chiral() -> None:
    """P1a_n, UFF-optimized (Cs): conformer_chiral False, g = 1."""
    opt = optimize(embedded(P1A_N))
    assert not conformer_chiral(opt.final_state, P1A_N, OPTIONS)
    assert assign_degeneracy(opt.final_state, P1A_N, OPTIONS) == 1


def test_chiral_molecule_never_gets_g2(butane: Butane) -> None:
    """A conformer of a graph-chiral molecule has g = 1 even when the conformer is chiral."""
    st = optimize(embedded("C[C@H](O)CC")).final_state
    assert conformer_chiral(st, "C[C@H](O)CC", OPTIONS)
    assert assign_degeneracy(st, "C[C@H](O)CC", OPTIONS) == 1


# sigma on optimizer-converged geometries (R9)


@pytest.mark.parametrize(("smiles", "sigma"), [("O", 2), ("C=C", 4), ("c1ccccc1", 12)])
def test_sigma_on_uff_optimized_geometry(smiles: str, sigma: int) -> None:
    """GeometricOptimizer-converged water, ethylene, benzene give sigma 2, 4, 12."""
    st = optimize(embedded(smiles)).final_state
    assert rotational_symmetry_number(st, smiles, analysis=ThermoAnalysisOptions()) == sigma


# ensemble


def test_build_ensemble(butane: Butane) -> None:
    """Weights sum to 1 within 1e-12; G_ens <= G_min - RT ln g_lowest."""
    kept, _ = drop_mirror_partners(
        records_for(butane, list(range(len(butane.results)))), "CCCC", OPTIONS
    )
    ens = build_ensemble("n_butane", "CCCC", kept, 298.15)
    assert abs(math.fsum(ens.boltzmann_weights) - 1.0) <= 1e-12
    lowest = ens.records[ens.lowest_index]
    g_min = lowest.thermo.gibbs_free_energy_hartree
    assert ens.ensemble_gibbs_hartree <= g_min - RT_298 * math.log(lowest.degeneracy) + 1e-15
    assert classify(lowest.state) == "anti"


def test_build_ensemble_empty() -> None:
    """No records raises EnsembleEmptyError."""
    with pytest.raises(EnsembleEmptyError):
        build_ensemble("x", "C", [], 298.15)


def test_dihedral_deg_range() -> None:
    """dihedral_deg is in (-180, 180] and matches a hand-built trans/cis geometry."""
    trans = MolecularState(
        symbols=["H", "C", "C", "H"],
        coordinates=[[1, 1, 0], [0, 0, 0], [1.5, 0, 0], [0.5, -1, 0]],
        charge=0,
        spin_multiplicity=1,
    )
    assert dihedral_deg(trans, 0, 1, 2, 3) == 180.0
    cis = MolecularState(
        symbols=["H", "C", "C", "H"],
        coordinates=[[-1, 1, 0], [0, 0, 0], [1.5, 0, 0], [2.5, 1, 0]],
        charge=0,
        spin_multiplicity=1,
    )
    assert abs(dihedral_deg(cis, 0, 1, 2, 3)) < 1e-12
