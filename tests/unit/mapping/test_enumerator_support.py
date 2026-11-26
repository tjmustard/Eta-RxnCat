"""Plan builders for the enumerator tests (no tests here): HF-1's lists on the e2e5 XYZ files.

The fixtures are read only. Fragment orders are ``[ring sp3 C, sp2 C, sp2 C, ring H]``, paired with
the TS alignment ``[7, 2, 3, 17]``; the roles come from ``t4_flexible_alkyl.yaml``.
"""

from pathlib import Path
from typing import Any

from cleanroom import read_xyz

from eta_rxncat.core import (
    AtomMappingSpec,
    Component,
    EnumeratedCandidate,
    EnumerationPlan,
    EnumerationSite,
    GraftRecord,
    LibraryEntry,
    MolecularState,
    PathwaySpec,
    ReactionGraph,
    ReactionNode,
    SelectivitySet,
    SiteTemplateMap,
    StageConfig,
    TemplateGeometry,
)

XYZ = Path(__file__).parents[2] / "e2e" / "data" / "e2e5" / "xyz"
MAX_RMSD = 0.15
ACTIVE = [0, 1, 2, 3, 4, 5]
FORMING = [(1, 2), (3, 5)]
TS_KEEP = [*range(16), 17]
TS_ALIGNMENT = [7, 2, 3, 17]
ENDO_ORDER = [2, 3, 4, 10]  # sp2 order [3, 4]
EXO_ORDER = [2, 4, 3, 10]  # sp2 order [4, 3]


def xyz_state(name: str, **overrides: Any) -> MolecularState:
    """Read one e2e5 XYZ file as a neutral singlet, with overrides applied."""
    xyz = read_xyz(XYZ / f"{name}.xyz")
    data: dict[str, Any] = {
        "symbols": xyz.symbols,
        "coordinates": xyz.coordinates.tolist(),
        "charge": 0,
        "spin_multiplicity": 1,
    }
    data.update(overrides)
    return MolecularState(**data)


def template(
    template_id: str, state: MolecularState, rank: int = 1, count: int = 1
) -> TemplateGeometry:
    """Return a one-component template."""
    return TemplateGeometry(
        id=template_id, rank=rank, components=[Component(state=state, count=count, label=None)]
    )


def ts_template(
    template_id: str, name: str = "TS1a_n", rank: int = 1, **overrides: Any
) -> TemplateGeometry:
    """Return a TS template with the six reacting atoms marked active."""
    return template(
        template_id, xyz_state(name, active_atom_indices=ACTIVE, **overrides), rank=rank
    )


def ts_map(node_id: str, template_id: str = "t1", **overrides: Any) -> SiteTemplateMap:
    """Return HF-1's site map of a TS template (H16 replaced)."""
    keep = overrides.pop("keep", TS_KEEP)
    delete = overrides.pop("delete", [16])
    data: dict[str, Any] = {
        "node_id": node_id,
        "template_id": template_id,
        "template": AtomMappingSpec(keep=keep, delete=delete, alignment=TS_ALIGNMENT),
        "constrained_core": ACTIVE,
        "forming_bonds": FORMING,
    }
    data.update(overrides)
    return SiteTemplateMap(**data)


def reactant_map(node_id: str = "cyclopropene", template_id: str = "t1") -> SiteTemplateMap:
    """Return the site map of the cyclopropene reactant (one CH2 hydrogen replaced)."""
    return SiteTemplateMap(
        node_id=node_id,
        template_id=template_id,
        template=AtomMappingSpec(keep=[0, 1, 2, 4, 5, 6], delete=[3], alignment=[0, 1, 2, 4]),
        constrained_core=[],
        forming_bonds=[],
    )


def entry(entry_id: str = "ethyl", **overrides: Any) -> LibraryEntry:
    """Return the ethyl or n-propyl library entry with both fragment orders."""
    roles = {
        "ethyl": ("r_ethyl_cyclopropene", [ENDO_ORDER, EXO_ORDER], [11, 12]),
        "npropyl": ("r_npropyl_cyclopropene", [[3, 4, 5, 13], [3, 5, 4, 13]], [14, 15]),
    }
    name, orders, delete = roles[overrides.pop("fragment_name", entry_id)]
    data: dict[str, Any] = {
        "id": entry_id,
        "site_id": "r",
        "fragment": xyz_state(name),
        "fragment_orders": orders,
        "fragment_delete": delete,
    }
    data.update(overrides)
    return LibraryEntry(**data)


def node(node_id: str, templates: list[TemplateGeometry], **overrides: Any) -> ReactionNode:
    """Return a reaction node (a TS unless the kind is overridden)."""
    data: dict[str, Any] = {
        "id": node_id,
        "label": node_id,
        "kind": "transition_state",
        "priority": 1,
        "templates": templates,
    }
    data.update(overrides)
    return ReactionNode(**data)


def default_nodes() -> dict[str, ReactionNode]:
    """Return the two reactants and the endo and exo TS nodes."""
    return {
        "cp": node("cp", [template("t1", xyz_state("1_cyclopentadiene"))], kind="reactant"),
        "cyclopropene": node(
            "cyclopropene", [template("t1", xyz_state("5_cyclopropene"))], kind="reactant"
        ),
        "ts_endo": node("ts_endo", [ts_template("t1")]),
        "ts_exo": node("ts_exo", [ts_template("t1", "TS1a_x")]),
    }


def default_maps() -> list[SiteTemplateMap]:
    """Return the maps of both TS templates and the cyclopropene reactant."""
    return [ts_map("ts_endo"), ts_map("ts_exo"), reactant_map()]


def selectivity_set(set_id: str = "endo_exo") -> SelectivitySet:
    """Return the endo/exo set over both reactants."""
    return SelectivitySet(
        id=set_id,
        pathways=[
            PathwaySpec(pathway="endo", node_id="ts_endo", expected_face=(1, 1)),
            PathwaySpec(pathway="exo", node_id="ts_exo", expected_face=(-1, -1)),
        ],
        reactant_node_ids=["cp", "cyclopropene"],
    )


def plan(
    *,
    nodes: dict[str, ReactionNode] | None = None,
    maps: list[SiteTemplateMap] | None = None,
    library: list[LibraryEntry] | None = None,
    sets: list[SelectivitySet] | None = None,
    default_stages: list[StageConfig] | None = None,
    sites: list[EnumerationSite] | None = None,
) -> EnumerationPlan:
    """Return a one-site endo/exo plan, with parts replaced."""
    graph = ReactionGraph(
        schema_version=1,
        name="toy",
        nodes=list((nodes or default_nodes()).values()),
        default_stages=default_stages or [],
    )
    if sites is None:
        sites = [EnumerationSite(id="r", maps=default_maps() if maps is None else maps)]
    return EnumerationPlan(
        reference_graph=graph,
        sites=sites,
        library=[entry()] if library is None else library,
        selectivity_sets=[selectivity_set()] if sets is None else sets,
        max_candidates=8,
    )


def record(candidate: EnumeratedCandidate, node_id: str, template_id: str = "t1") -> GraftRecord:
    """Return the candidate's record of one (node, template)."""
    (found,) = [
        r for r in candidate.records if (r.node_id, r.template_id) == (node_id, template_id)
    ]
    return found
