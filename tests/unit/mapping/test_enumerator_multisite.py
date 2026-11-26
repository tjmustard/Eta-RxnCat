"""Multi-site product, cap, per-template remap and the entry multiset (v0.7.0 slice 04; R31).

The two-site toy puts site ``r`` (ethyl for H16, as HF-1) and site ``m`` (methyl for H14 on C6)
on the TS templates. Site ``m``'s fragment is propane from RDKit at a fixed seed: its C0, C1 and
one H of C1 pair with template C1, C6 and H15, and C2 with its three H is appended.

Hand-computed indices on a TS template (18 atoms): site ``r`` keeps ``0..15, 17`` and appends
seven atoms, so template 17 is index 16 and the product has 24 atoms. Site ``m`` deletes index
14, so template 15 is 14, template 17 is 15, the ethyl atoms are 16..22 and the methyl atoms
23..26.
"""

from typing import Any

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem
from test_enumerator_support import (
    MAX_RMSD,
    default_maps,
    default_nodes,
    entry,
    node,
    plan,
    selectivity_set,
    ts_map,
    ts_template,
    xyz_state,
)

from eta_rxncat.core import (
    AtomMappingSpec,
    EnumeratedCandidate,
    EnumerationPlan,
    EnumerationResult,
    EnumerationSite,
    GraftRecord,
    GraftResult,
    LibraryEntry,
    MolecularState,
    ReactionNode,
    SiteTemplateMap,
    StageConfig,
)
from eta_rxncat.mapping import enumerator as module
from eta_rxncat.mapping import graft
from eta_rxncat.mapping.enumerator import (
    EnumerationError,
    enumerate_candidates,
    map_template_indices,
)

# Site ``m`` on a TS template, in template indices: every atom surviving site ``r`` but H14.
M_KEEP = [*range(14), 15, 17]
M_ALIGNMENT = [1, 6, 15]
# Site ``m``'s fragment pairs and deletes (propane: C0, C1, H6 of C1 paired; C2 and H8..H10 stay).
M_ORDER = [0, 1, 6]
M_DELETE = [3, 4, 5, 7]


def run(built: EnumerationPlan) -> EnumerationResult:
    """Enumerate at the fixture's RMSD ceiling."""
    return enumerate_candidates(built, max_alignment_rmsd_angstrom=MAX_RMSD)


def one(built: EnumerationPlan) -> EnumeratedCandidate:
    """Return the single candidate of a plan."""
    (candidate,) = run(built).candidates
    return candidate


def propane() -> MolecularState:
    """Return RDKit propane embedded with a fixed seed."""
    molecule = Chem.AddHs(Chem.MolFromSmiles("CCC"))
    assert AllChem.EmbedMolecule(molecule, randomSeed=42) == 0
    positions = molecule.GetConformer().GetPositions()
    return MolecularState(
        symbols=[a.GetSymbol() for a in molecule.GetAtoms()],
        coordinates=positions.tolist(),
        charge=0,
        spin_multiplicity=1,
    )


def methyl(entry_id: str = "methyl", **overrides: Any) -> LibraryEntry:
    """Return site ``m``'s methyl entry."""
    data: dict[str, Any] = {
        "id": entry_id,
        "site_id": "m",
        "fragment": propane(),
        "fragment_orders": [M_ORDER],
        "fragment_delete": M_DELETE,
    }
    data.update(overrides)
    return LibraryEntry(**data)


def m_map(node_id: str, template_id: str = "t1", **overrides: Any) -> SiteTemplateMap:
    """Return site ``m``'s map of a TS template (H14 replaced), in template indices."""
    data: dict[str, Any] = {
        "node_id": node_id,
        "template_id": template_id,
        "template": AtomMappingSpec(
            keep=overrides.pop("keep", M_KEEP),
            delete=overrides.pop("delete", [14]),
            alignment=M_ALIGNMENT,
        ),
        "constrained_core": [0, 1, 2, 3, 4, 5],
        "forming_bonds": [(1, 2), (3, 5)],
    }
    data.update(overrides)
    return SiteTemplateMap(**data)


def cp_map() -> SiteTemplateMap:
    """Return site ``m``'s map of the cyclopentadiene reactant (one CH2 hydrogen replaced)."""
    return SiteTemplateMap(
        node_id="cp",
        template_id="t1",
        template=AtomMappingSpec(
            keep=[i for i in range(11) if i != 7], delete=[7], alignment=[0, 1, 6]
        ),
        constrained_core=[],
        forming_bonds=[],
    )


def two_sites(
    r_maps: list[SiteTemplateMap] | None = None, m_maps: list[SiteTemplateMap] | None = None
) -> list[EnumerationSite]:
    """Return sites ``r`` then ``m`` (defaults: the split-reactant plan)."""
    if r_maps is None:
        r_maps = default_maps()
    if m_maps is None:
        m_maps = [m_map("ts_endo"), m_map("ts_exo"), cp_map()]
    return [EnumerationSite(id="r", maps=r_maps), EnumerationSite(id="m", maps=m_maps)]


def endo_plan(**overrides: Any) -> EnumerationPlan:
    """Return a two-site plan on the endo TS template alone, without selectivity sets."""
    overrides.setdefault("sites", two_sites([ts_map("ts_endo")], [m_map("ts_endo")]))
    overrides.setdefault("library", [entry(), methyl()])
    overrides.setdefault("sets", [])
    return plan(**overrides)


def records_of(
    candidate: EnumeratedCandidate, node_id: str, template_id: str = "t1"
) -> list[GraftRecord]:
    """Return the records of one (node, template), in site order."""
    return [r for r in candidate.records if (r.node_id, r.template_id) == (node_id, template_id)]


def preopt(frozen: list[int]) -> StageConfig:
    """Return a toy constrained pre-optimisation stage."""
    return StageConfig(
        kind="constrained_preopt",
        engine="rdkit_ff",
        method="mmff94",
        frozen_atom_indices=frozen,
    )


def spy_graft(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record the site of every ``graft`` call, in order: ``"r"`` or ``"m"``."""
    calls: list[str] = []

    def spy(*args: Any) -> GraftResult:
        calls.append("m" if list(args[2].fragment_alignment) == M_ORDER else "r")
        return graft(*args)

    monkeypatch.setattr(module, "graft", spy)
    return calls


def test_two_by_two_product_order_and_ids() -> None:
    """Sites in plan order, entries in declared order, ids joined with ``+``."""
    library = [methyl("me2"), entry("npropyl"), methyl("me1"), entry("ethyl")]
    built = plan(sites=two_sites(), library=library)
    result = run(built)
    assert [c.candidate_id for c in result.candidates] == [
        "npropyl+me2",
        "npropyl+me1",
        "ethyl+me2",
        "ethyl+me1",
    ]
    assert result.candidates[1].entry_ids_by_site == {"r": "npropyl", "m": "me1"}
    assert [c.status for c in result.candidates] == ["ok"] * 4
    assert run(built).model_dump_json() == result.model_dump_json()


@pytest.mark.parametrize("bad", [False, True], ids=["ok", "unmappable_counts"])
def test_cap_is_refused_before_any_graft(bad: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """A product above the cap raises with both numbers, never calling graft."""
    calls = spy_graft(monkeypatch)
    second = entry("npropyl", fragment_orders=[[3, 4, 5]]) if bad else entry("npropyl")
    library = [entry(), second, methyl("me1"), methyl("me2")]
    built = plan(sites=two_sites(), library=library).model_copy(update={"max_candidates": 3})
    with pytest.raises(EnumerationError, match=r"4 candidates exceed max_candidates 3"):
        run(built)
    assert calls == []
    assert len(run(built.model_copy(update={"max_candidates": 4})).candidates) == 4


def test_two_site_plan_remaps_to_hand_computed_indices() -> None:
    """The split-reactant plan is ok; site ``m``'s record speaks its input's index space."""
    candidate = one(plan(sites=two_sites(), library=[entry(), methyl()]))
    assert (candidate.status, candidate.detail) == ("ok", None)
    assert [(r.node_id, r.site_id, r.status) for r in candidate.records] == [
        ("cp", "m", "ok"),
        ("cyclopropene", "r", "ok"),
        ("ts_endo", "r", "ok"),
        ("ts_endo", "m", "ok"),
        ("ts_exo", "r", "ok"),
        ("ts_exo", "m", "ok"),
    ]
    first, second = records_of(candidate, "ts_endo")
    assert first.index_map is not None and len(first.index_map) == 24
    assert second.index_map is not None and len(second.index_map) == 27
    # Site m's input is site r's product: its keep order, then the seven ethyl atoms 17..23.
    assert second.index_map[:23] == [("template", i) for i in [*range(14), 15, 16, *range(17, 24)]]
    assert [source for source, _ in second.index_map[23:]] == ["fragment"] * 4
    assert second.index_map[23:] == [("fragment", j) for j in [2, 8, 9, 10]]
    assert map_template_indices(first, [15, 17]) == [15, 16]
    assert map_template_indices(second, [15, 16, 17]) == [14, 15, 16]
    assert second.mapped_forming_bonds == [(1, 2), (3, 5)]
    assert second.constrained_core_product_indices == [0, 1, 2, 3, 4, 5]
    assert candidate.graph is not None
    nodes = {n.id: n for n in candidate.graph.nodes}
    (endo,) = nodes["ts_endo"].templates
    assert endo.id == "t1__ethyl+methyl"
    assert len(endo.components[0].state.symbols) == 27


def test_later_site_atoms_are_remapped_per_template() -> None:
    """Each template remaps through its own earlier graft, whose keep order differs."""
    swapped = [17, *range(16)]  # site r keeps template 17 first on t2
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1"), ts_template("t2", rank=2)])
    }
    sites = two_sites(
        [ts_map("ts_endo"), ts_map("ts_endo", "t2", keep=swapped)],
        [m_map("ts_endo"), m_map("ts_endo", "t2")],
    )
    candidate = one(endo_plan(nodes=nodes, sites=sites))
    assert candidate.status == "ok", candidate.detail
    r1, m1 = records_of(candidate, "ts_endo", "t1")
    r2, m2 = records_of(candidate, "ts_endo", "t2")
    assert map_template_indices(r1, [0, 17]) == [0, 16]
    assert map_template_indices(r2, [0, 17]) == [1, 0]
    # Site m keeps the same template atoms in the same order on both, from different inputs.
    assert m1.index_map is not None and m2.index_map is not None
    assert m1.index_map[:3] == [("template", 0), ("template", 1), ("template", 2)]
    assert m2.index_map[:3] == [("template", 1), ("template", 2), ("template", 3)]
    assert m2.index_map[15] == ("template", 0)  # template 17 (input 0) at product index 15
    assert m1.mapped_forming_bonds == m2.mapped_forming_bonds == [(1, 2), (3, 5)]


@pytest.mark.parametrize(
    "overrides",
    [
        {"delete": [14, 16]},
        {"keep": [*M_KEEP, 16]},
        {"constrained_core": [0, 1, 2, 3, 4, 5, 16]},
        {"forming_bonds": [(1, 2), (3, 16)]},
    ],
    ids=["delete", "keep", "core", "forming_bond"],
)
def test_atom_deleted_by_an_earlier_site(
    overrides: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Site m naming H16, which site r deleted, is refused ``site_atom_deleted`` ungrafted."""
    calls = spy_graft(monkeypatch)
    sites = two_sites([ts_map("ts_endo")], [m_map("ts_endo", **overrides)])
    candidate = one(endo_plan(sites=sites))
    first, second = records_of(candidate, "ts_endo")
    assert first.status == "ok"
    assert (second.status, second.reason) == ("refused", "site_atom_deleted")
    assert second.order_rmsds_angstrom == [] and second.index_map is None
    assert "m" not in calls
    assert (candidate.status, candidate.detail) == ("unmappable", "ts_endo")


def test_index_outside_the_template_at_a_later_site_is_graft_input() -> None:
    """An index that is no template atom was deleted by nobody: graft refuses it."""
    sites = two_sites([ts_map("ts_endo")], [m_map("ts_endo", delete=[14, 90])])
    found = records_of(one(endo_plan(sites=sites)), "ts_endo")[1]
    assert (found.status, found.reason) == ("refused", "graft_input")


def test_charge_adds_across_sites() -> None:
    """Σ charge_delta over the applied entries; the declared multiplicity carries on."""
    library = [entry(charge_delta=1, multiplicity=2), methyl(charge_delta=2)]
    candidate = one(endo_plan(library=library))
    assert candidate.status == "ok", [r.reason for r in candidate.records]
    first, second = records_of(candidate, "ts_endo")
    assert (first.product_charge, first.product_multiplicity) == (1, 2)
    assert (second.product_charge, second.product_multiplicity) == (3, 2)


def test_multiplicity_conflict_across_sites() -> None:
    """Two different declarations conflict at the site that introduces the second."""
    library = [
        entry(charge_delta=1, multiplicity=2),
        methyl(charge_delta=1, multiplicity=4),
    ]
    candidate = one(endo_plan(library=library))
    first, second = records_of(candidate, "ts_endo")
    assert first.status == "ok"
    assert (second.status, second.reason) == ("refused", "multiplicity_conflict")
    assert candidate.status == "unmappable"


def endo_nodes(stages: list[StageConfig], *templates: str) -> dict[str, ReactionNode]:
    """Return the default nodes with endo templates and node stages."""
    ranked = [ts_template(t, rank=k) for k, t in enumerate(templates or ("t1",), start=1)]
    return default_nodes() | {"ts_endo": node("ts_endo", ranked, stages=stages)}


def test_frozen_atoms_compose_through_both_sites() -> None:
    """R31.1: template atoms 17 and 15 sit at 15 and 14 after both grafts, list order kept."""
    candidate = one(endo_plan(nodes=endo_nodes([preopt([17, 0, 15])])))
    assert candidate.graph is not None, candidate.detail
    (endo,) = [n for n in candidate.graph.nodes if n.id == "ts_endo"]
    assert endo.stages is not None
    assert endo.stages[0].frozen_atom_indices == [15, 0, 14]


def test_frozen_atom_replaced_by_a_later_site_is_refused_before_graft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R31.1: freezing H14, which site m replaces, refuses m's graft without calling it."""
    calls = spy_graft(monkeypatch)
    candidate = one(endo_plan(nodes=endo_nodes([preopt([0, 14])])))
    first, second = records_of(candidate, "ts_endo")
    assert first.status == "ok"
    assert (second.status, second.reason) == ("refused", "graft_input")
    assert second.order_rmsds_angstrom == []
    assert calls and set(calls) == {"r"}
    assert (candidate.status, candidate.detail) == ("unmappable", "ts_endo")


def test_differing_composed_images_are_inconsistent() -> None:
    """R31.1: two eligible templates whose composed images differ."""
    reordered = [5, 4, 3, 2, 1, 0, *range(6, 14), 15, 17]
    sites = two_sites(
        [ts_map("ts_endo"), ts_map("ts_endo", "t2")],
        [m_map("ts_endo"), m_map("ts_endo", "t2", keep=reordered)],
    )
    built = endo_plan(nodes=endo_nodes([preopt([0])], "t1", "t2"), sites=sites)
    candidate = one(built)
    assert [r.status for r in candidate.records] == ["ok"] * 4
    assert (candidate.status, candidate.detail) == (
        "inconsistent",
        "frozen_index_mismatch:ts_endo",
    )


def hydrogen(site_id: str, entry_id: str) -> LibraryEntry:
    """Return an entry that puts a hydrogen back, so composition is unchanged.

    The fragment is the TS1a_n atoms 7, 2, 3, 17 (paired) and 16 (appended) for site ``r``.
    """
    source = xyz_state("TS1a_n")
    atoms = [7, 2, 3, 17, 16]
    fragment = MolecularState(
        symbols=[source.symbols[i] for i in atoms],
        coordinates=[source.coordinates[i] for i in atoms],
        charge=0,
        spin_multiplicity=1,
    )
    return LibraryEntry(
        id=entry_id,
        site_id=site_id,
        fragment=fragment,
        fragment_orders=[[0, 1, 2, 3], [0, 2, 1, 3]],
        fragment_delete=[],
    )


def test_site_on_both_ts_nodes_and_no_reactant_is_inconsistent() -> None:
    """R31.4: an empty reactant union against a TS entry is inconsistent.

    The hydrogen entry keeps every composition, so only the multiset check can fail.
    """
    built = plan(maps=[ts_map("ts_endo"), ts_map("ts_exo")], library=[hydrogen("r", "h")])
    candidate = one(built)
    assert [r.status for r in candidate.records] == ["ok", "ok"]
    assert (candidate.status, candidate.detail, candidate.graph) == (
        "inconsistent",
        "entry_multiset_mismatch:endo_exo",
        None,
    )


def test_site_on_two_reactant_nodes_is_inconsistent() -> None:
    """R31.4: one site on two reactants carries its entry twice against once on the TS.

    The cyclopentadiene fit of the hydrogen fragment is loose (about 0.40 A), so the RMSD
    ceiling is raised; the multiset rule, not the geometry, is under test.
    """
    cp = SiteTemplateMap(
        node_id="cp",
        template_id="t1",
        template=AtomMappingSpec(
            keep=[i for i in range(11) if i != 6], delete=[6], alignment=[1, 0, 2, 7]
        ),
        constrained_core=[],
        forming_bonds=[],
    )
    built = plan(maps=[*default_maps(), cp], library=[hydrogen("r", "h")])
    (candidate,) = enumerate_candidates(built, max_alignment_rmsd_angstrom=2.0).candidates
    assert [r.status for r in candidate.records] == ["ok"] * 4
    assert (candidate.status, candidate.detail) == (
        "inconsistent",
        "entry_multiset_mismatch:endo_exo",
    )


def test_split_reactants_pass_the_union_check() -> None:
    """Site r on the dienophile, site m on the diene, both on every TS node."""
    candidate = one(plan(sites=two_sites(), library=[entry(), methyl()], sets=[selectivity_set()]))
    assert (candidate.status, candidate.detail) == ("ok", None)


def test_partial_pathway_coverage_names_the_later_site() -> None:
    """A second site on one pathway node alone is inconsistent."""
    sites = two_sites(m_maps=[m_map("ts_endo"), cp_map()])
    candidate = one(plan(sites=sites, library=[entry(), methyl()]))
    assert (candidate.status, candidate.detail) == ("inconsistent", "partial_pathway_coverage:m")


def test_a_refused_site_stops_the_template(monkeypatch: pytest.MonkeyPatch) -> None:
    """R31.5: refused at site r means one record (r's) and no graft by site m."""
    calls = spy_graft(monkeypatch)
    library = [entry(fragment_orders=[[2, 3, 4]]), methyl()]
    candidate = one(endo_plan(library=library))
    (only,) = records_of(candidate, "ts_endo")
    assert (only.site_id, only.reason) == ("r", "graft_input")
    assert calls == []


def test_templates_not_listed_by_every_covering_site_are_dropped_once() -> None:
    """R31.5: dropped from either side, no record, sorted and named once."""
    nodes = default_nodes() | {
        "ts_endo": node(
            "ts_endo",
            [ts_template("t1"), ts_template("zz", rank=2), ts_template("aa", rank=3)],
        )
    }
    sites = two_sites(
        [ts_map("ts_endo"), ts_map("ts_endo", "zz")],  # r lists zz; aa is listed by m only
        [m_map("ts_endo"), m_map("ts_endo", "aa")],
    )
    candidate = one(endo_plan(nodes=nodes, sites=sites))
    assert candidate.status == "ok"
    assert candidate.detail == "dropped_unlisted:ts_endo/aa,ts_endo/zz"
    assert {r.template_id for r in candidate.records} == {"t1"}
    assert candidate.graph is not None
    (endo,) = [n for n in candidate.graph.nodes if n.id == "ts_endo"]
    assert [(t.id, t.rank) for t in endo.templates] == [("t1__ethyl+methyl", 1)]


def test_composition_is_compared_on_the_final_product() -> None:
    """A lower-ranked template whose final composition differs is refused at its last site."""
    nodes = default_nodes() | {
        "ts_endo": node("ts_endo", [ts_template("t1"), ts_template("t2", rank=2)])
    }
    fewer = m_map("ts_endo", "t2", keep=[i for i in M_KEEP if i not in (8, 9)], delete=[8, 9, 14])
    sites = two_sites([ts_map("ts_endo"), ts_map("ts_endo", "t2")], [m_map("ts_endo"), fewer])
    candidate = one(endo_plan(nodes=nodes, sites=sites))
    first, second = records_of(candidate, "ts_endo", "t2")
    assert (first.status, second.reason) == ("ok", "composition_mismatch")
    assert candidate.status == "ok"
