"""Loaders for the Human Fixture inputs and the Tier 3 TS fixtures (provisional per TJ Q-E3)."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import MolecularState, PathwayPruningRule
from eta_rxncat.orchestrator import BarrierSpec, ReactionSpec, SpeciesSpec

DATA = Path(__file__).parent / "data"
REPO = Path(__file__).parents[2]


@dataclass(frozen=True)
class Fixture:
    """A fixture: its species and, for a reaction fixture, the reaction."""

    name: str
    species: tuple[SpeciesSpec, ...]
    reaction: ReactionSpec | None
    literature: dict[str, Any] | None = None
    planar_point: dict[str, Any] | None = None
    window_dG_r_1M_kcal_mol: tuple[float, float] | None = None

    def spec(self, species_id: str) -> SpeciesSpec:
        """Return the species ``species_id``."""
        return next(s for s in self.species if s.species_id == species_id)


def load_fixture(path: Path) -> Fixture:
    """Load and validate a fixture YAML.

    Raises:
        ValueError: On a wrong schema, an unknown key, a duplicate species or a reaction that
            names an unknown species or does not conserve atoms and charge.
    """
    data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    top = {"schema", "fixture", "species", "reaction", "literature", "planar_point"}
    unknown = sorted(set(data) - top - {"window_dG_r_1M_kcal_mol"})
    if unknown:
        raise ValueError(f"{path}: unknown keys {unknown}")
    species = _species(path, data["species"])
    reaction = None
    if "reaction" in data:
        r = data["reaction"]
        reaction = ReactionSpec(
            reactants=tuple((str(a), int(b)) for a, b in r["reactants"]),
            products=tuple((str(a), int(b)) for a, b in r["products"]),
            smiles={s.species_id: s.smiles for s in species},
        )
    window = data.get("window_dG_r_1M_kcal_mol")
    if window is not None and (len(window) != 2 or not window[0] < window[1]):
        raise ValueError(f"{path}: window_dG_r_1M_kcal_mol must be [low, high] with low < high")
    return Fixture(
        name=str(data["fixture"]),
        species=tuple(species),
        reaction=reaction,
        literature=data.get("literature"),
        planar_point=data.get("planar_point"),
        window_dG_r_1M_kcal_mol=None if window is None else (float(window[0]), float(window[1])),
    )


def _species(path: Path, blocks: list[dict[str, Any]]) -> list[SpeciesSpec]:
    """Return the species blocks of a fixture YAML (unknown keys and duplicate ids refused)."""
    species = []
    for raw in blocks:
        keys = {"species_id", "smiles", "charge", "spin_multiplicity", "conformer_options"}
        extra = sorted(set(raw) - keys - {"seed_xyz"})
        if extra:
            raise ValueError(f"{path}: species keys {extra} unknown")
        species.append(
            SpeciesSpec(
                species_id=str(raw["species_id"]),
                smiles=str(raw["smiles"]),
                charge=int(raw["charge"]),
                spin_multiplicity=int(raw["spin_multiplicity"]),
                conformer_options=ConformerOptions(**raw.get("conformer_options", {})),
                seed_geometries=tuple(
                    read_xyz(
                        Path(path).parent / rel, int(raw["charge"]), int(raw["spin_multiplicity"])
                    )
                    for rel in raw.get("seed_xyz", [])
                ),
            )
        )
    ids = [s.species_id for s in species]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{path}: duplicate species ids {ids}")
    return species


def read_xyz(path: Path, charge: int, multiplicity: int) -> MolecularState:
    """Read an XYZ file (count line, comment, then ``symbol x y z`` rows) as a state."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    rows = [line.split() for line in lines[2 : 2 + n]]
    return MolecularState(
        symbols=[r[0] for r in rows],
        coordinates=[[float(x) for x in r[1:4]] for r in rows],
        charge=charge,
        spin_multiplicity=multiplicity,
    )


def hf1() -> Fixture:
    """Human Fixture 1 (n-butane)."""
    return load_fixture(DATA / "hf1_butane.yaml")


def hf2() -> Fixture:
    """Human Fixture 2 (butadiene + ethylene -> cyclohexene)."""
    return load_fixture(DATA / "hf2_diels_alder.yaml")


def t1() -> Fixture:
    """TJ Tier 1 (1,3-dimethoxybutadiene)."""
    return load_fixture(DATA / "e2e5" / "t1_dimethoxybutadiene.yaml")


def t2() -> Fixture:
    """TJ Tier 2 (Cp + cyclopropene -> endo P1a_n)."""
    return load_fixture(DATA / "e2e5" / "t2_cp_cyclopropene.yaml")


# --- Tier 3 TS fixtures (v0.5.0, provisional per TJ Q-E3) ----------------------------------------

TS_START_FORMS = ("start_xyz", "start_from_fixture", "start_grafts")
GRAFT_KEYS = {"keep", "delete", "alignment_pairs", "fragment_delete", "constrained_core"}


@dataclass(frozen=True)
class TSStart:
    """How the TS search starts: a geometry file, a promoted fixture's structure, or grafts.

    Attributes:
        form: ``start_xyz``, ``start_from_fixture`` or ``start_grafts``.
        xyz: The start geometry (``start_xyz``).
        path_template: Repository-relative path with ``{recipe}`` (``start_from_fixture``).
        key: The structure's key in that JSON (``start_from_fixture``).
        grafts: The ``start_grafts`` block as written (template, fragment, grafts, pre_relax).
    """

    form: str
    xyz: Path | None = None
    path_template: str | None = None
    key: str | None = None
    grafts: dict[str, Any] | None = None


@dataclass(frozen=True)
class TSFixture:
    """A Tier 3 TS fixture: reactant species, the TS request, its reference and the barrier."""

    name: str
    path: Path
    species: tuple[SpeciesSpec, ...]
    ts_id: str
    charge: int
    spin_multiplicity: int
    active_atom_indices: tuple[int, ...]
    forming_bonds: tuple[tuple[int, int], ...]
    start: TSStart
    reference: MolecularState
    start_to_reference_map: tuple[int, ...]
    map_rule: str
    barrier: BarrierSpec
    window_dG_dagger_1M_kcal_mol: tuple[float, float]
    literature: dict[str, Any]

    def spec(self, species_id: str) -> SpeciesSpec:
        """Return the species ``species_id``."""
        return next(s for s in self.species if s.species_id == species_id)

    def start_state(self, recipe: str | None = None) -> MolecularState:
        """Return the start geometry with the TS's charge, multiplicity and active set.

        Raises:
            ValueError: For ``start_grafts`` (built by the TS4a slice), or a missing recipe.
        """
        return _resolve_start(
            self.name,
            self.start,
            self.charge,
            self.spin_multiplicity,
            self.active_atom_indices,
            recipe,
        )


def _resolve_start(
    name: str,
    start: "TSStart",
    charge: int,
    spin_multiplicity: int,
    active_atom_indices: tuple[int, ...],
    recipe: str | None,
) -> MolecularState:
    """Return a start geometry (``start_xyz`` or ``start_from_fixture``) with its active set."""
    if start.form == "start_xyz" and start.xyz is not None:
        state = read_xyz(start.xyz, charge, spin_multiplicity)
    elif start.form == "start_from_fixture" and start.path_template is not None:
        if recipe is None:
            raise ValueError(f"{name}: start_from_fixture needs a recipe")
        path = REPO / start.path_template.format(recipe=recipe)
        raw = json.loads(path.read_text(encoding="utf-8"))[str(start.key)]
        state = MolecularState(
            symbols=list(raw["symbols"]),
            coordinates=[list(row) for row in raw["coordinates_angstrom"]],
            charge=int(raw["charge"]),
            spin_multiplicity=int(raw["multiplicity"]),
        )
    else:
        raise ValueError(f"{name}: start form {start.form} has no direct geometry")
    return MolecularState.model_validate(
        {**state.model_dump(), "active_atom_indices": list(active_atom_indices)}
    )


def _exact_keys(path: Path, where: str, block: dict[str, Any], keys: set[str]) -> None:
    """Refuse a block whose keys are not exactly ``keys``."""
    if not isinstance(block, dict):
        raise ValueError(f"{path}: {where} must be a mapping")
    missing, extra = sorted(keys - set(block)), sorted(set(block) - keys)
    if missing or extra:
        raise ValueError(f"{path}: {where} keys: missing {missing}, unknown {extra}")


def _pairs(path: Path, where: str, raw: Any) -> tuple[tuple[int, int], ...]:
    """Return a list of ``[i, j]`` int pairs."""
    pairs = []
    for pair in raw:
        if len(pair) != 2 or any(isinstance(v, bool) or not isinstance(v, int) for v in pair):
            raise ValueError(f"{path}: {where} entry {pair!r} is not two ints")
        pairs.append((int(pair[0]), int(pair[1])))
    return tuple(pairs)


def _ts_start(path: Path, ts: dict[str, Any]) -> TSStart:
    """Return the single start form of a ``ts`` block."""
    forms = [form for form in TS_START_FORMS if form in ts]
    if len(forms) != 1:
        raise ValueError(f"{path}: ts needs exactly one of {list(TS_START_FORMS)}, got {forms}")
    form = forms[0]
    if form == "start_xyz":
        return TSStart(form=form, xyz=Path(path).parent / str(ts[form]))
    if form == "start_from_fixture":
        block = ts[form]
        _exact_keys(path, "start_from_fixture", block, {"path_template", "key"})
        if "{recipe}" not in str(block["path_template"]):
            raise ValueError(f"{path}: start_from_fixture.path_template needs {{recipe}}")
        return TSStart(form=form, path_template=str(block["path_template"]), key=str(block["key"]))
    block = ts[form]
    _exact_keys(path, "start_grafts", block, {"template", "fragment", "grafts", "pre_relax"})
    if not block["grafts"]:
        raise ValueError(f"{path}: start_grafts.grafts is empty")
    for k, graft_block in enumerate(block["grafts"]):
        _exact_keys(path, f"start_grafts.grafts[{k}]", graft_block, GRAFT_KEYS)
        _pairs(path, f"start_grafts.grafts[{k}].alignment_pairs", graft_block["alignment_pairs"])
    _exact_keys(path, "start_grafts.pre_relax", block["pre_relax"], {"core", "maxiter"})
    return TSStart(form=form, grafts=block)


def load_ts_fixture(path: Path) -> TSFixture:
    """Load and validate a Tier 3 TS fixture YAML (``schema: 1``, TS form).

    Raises:
        ValueError: On a wrong schema; missing or unknown keys at any level; not exactly one start
            form; a reference map that is not a permutation of the reference's atoms; a barrier
            naming an unknown species; or a window that is not ``[low, high]`` with low < high.
    """
    path = Path(path)
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    top = {"schema", "fixture", "species", "ts", "reference", "barrier", "literature"}
    _exact_keys(path, "top-level", data, top)
    species = _species(path, data["species"])
    ts = data["ts"]
    base = {"ts_id", "charge", "spin_multiplicity", "active_atom_indices", "forming_bonds"}
    form_keys = set(ts) & set(TS_START_FORMS)
    _exact_keys(path, "ts", ts, base | form_keys)
    start = _ts_start(path, ts)
    ref = data["reference"]
    _exact_keys(path, "reference", ref, {"xyz", "start_to_reference_map", "map_rule"})
    reference = read_xyz(
        path.parent / str(ref["xyz"]), int(ts["charge"]), int(ts["spin_multiplicity"])
    )
    mapping = tuple(int(i) for i in ref["start_to_reference_map"])
    if sorted(mapping) != list(range(len(reference.symbols))):
        raise ValueError(f"{path}: start_to_reference_map is not a permutation of the reference")
    barrier = data["barrier"]
    _exact_keys(path, "barrier", barrier, {"reactants", "window_dG_dagger_1M_kcal_mol"})
    smiles = {s.species_id: s.smiles for s in species}
    reactants = tuple((str(a), int(b)) for a, b in barrier["reactants"])
    unknown = sorted({a for a, _ in reactants} - set(smiles))
    if unknown:
        raise ValueError(f"{path}: barrier reactants {unknown} are not species")
    window = barrier["window_dG_dagger_1M_kcal_mol"]
    if len(window) != 2 or not window[0] < window[1]:
        raise ValueError(f"{path}: window_dG_dagger_1M_kcal_mol must be [low, high], low < high")
    literature = data["literature"]
    _exact_keys(
        path,
        "literature",
        literature,
        {
            "structures",
            "dG_dagger_1atm_kcal_mol",
            "dG_dagger_1M_kcal_mol",
            "standard_state",
            "source",
        },
    )
    return TSFixture(
        name=str(data["fixture"]),
        path=path,
        species=tuple(species),
        ts_id=str(ts["ts_id"]),
        charge=int(ts["charge"]),
        spin_multiplicity=int(ts["spin_multiplicity"]),
        active_atom_indices=tuple(int(i) for i in ts["active_atom_indices"]),
        forming_bonds=_pairs(path, "ts.forming_bonds", ts["forming_bonds"]),
        start=start,
        reference=reference,
        start_to_reference_map=mapping,
        map_rule=str(ref["map_rule"]),
        barrier=BarrierSpec(
            reactants=reactants, ts_id=str(ts["ts_id"]), smiles={a: smiles[a] for a, _ in reactants}
        ),
        window_dG_dagger_1M_kcal_mol=(float(window[0]), float(window[1])),
        literature=literature,
    )


T3_YAMLS = (
    "t3_ts1a_n_unmapped.yaml",
    "t3_ts1b_n_mapped.yaml",
    "t3_ts3a_unmapped.yaml",
    "t3_ts4a_mapped.yaml",
    "t3_n4_unmapped.yaml",
)


def t3(name: str) -> TSFixture:
    """Load one Tier 3 TS fixture by file name."""
    return load_ts_fixture(DATA / "e2e5" / name)


# --- Tier 4 selectivity fixtures (v0.6.0, provisional per TJ Q-E3) --------------------------------


@dataclass(frozen=True)
class T4Pathway:
    """One competing pathway of a Tier 4 fixture: its TS request and reference."""

    pathway: str
    ts_id: str
    charge: int
    spin_multiplicity: int
    active_atom_indices: tuple[int, ...]
    forming_bonds: tuple[tuple[int, int], ...]
    start: TSStart
    reference: MolecularState
    start_to_reference_map: tuple[int, ...]
    map_rule: str

    def start_state(self, recipe: str | None = None) -> MolecularState:
        """Return the start geometry (``start_xyz`` or ``start_from_fixture``), active set set."""
        return _resolve_start(
            self.ts_id,
            self.start,
            self.charge,
            self.spin_multiplicity,
            self.active_atom_indices,
            recipe,
        )


@dataclass(frozen=True)
class T4Downstream:
    """The priority-2 node ``downstream_exo_minor`` of the mapped fixture."""

    node_id: str
    priority: int
    pathway: str
    species_id: str
    smiles: str
    charge: int
    spin_multiplicity: int
    xyz: Path


@dataclass(frozen=True)
class T4Window:
    """A window on the Boltzmann-summed ddG-dagger (kcal/mol) with its inclusive ends."""

    low: float
    high: float
    low_inclusive: bool
    high_inclusive: bool

    def contains(self, value: float) -> bool:
        """Return whether ``value`` is inside the window."""
        above = value >= self.low if self.low_inclusive else value > self.low
        below = value <= self.high if self.high_inclusive else value < self.high
        return above and below


@dataclass(frozen=True)
class T4Fixture:
    """A Tier 4 fixture: species, two competing pathways, the references and any pruning."""

    name: str
    path: Path
    species: tuple[SpeciesSpec, ...]
    pathways: tuple[T4Pathway, ...]
    kind: str
    temperature_k: float
    reference_ddG_dagger_kcal_mol: float
    liu_header_ddG_dagger_kcal_mol: float
    uma_window: T4Window
    gfn2_gate: dict[str, Any]
    literature: dict[str, Any]
    pruning_rule: PathwayPruningRule | None
    downstream: T4Downstream | None

    def pathway(self, label: str) -> T4Pathway:
        """Return the pathway ``label``."""
        return next(p for p in self.pathways if p.pathway == label)


T4_PATHWAY_KEYS = {"pathway", "ts_id", "charge", "spin_multiplicity", "active_atom_indices"}
T4_SELECTIVITY_KEYS = {
    "kind",
    "temperature_k",
    "reference_ddG_dagger_kcal_mol",
    "liu_header_ddG_dagger_kcal_mol",
    "uma_window_kcal_mol",
    "gfn2_gate",
}


def _t4_pathway(path: Path, block: dict[str, Any]) -> T4Pathway:
    forms = set(block) & set(TS_START_FORMS)
    _exact_keys(path, "pathways[]", block, T4_PATHWAY_KEYS | {"forming_bonds", "reference"} | forms)
    start = _ts_start(path, block)
    ref = block["reference"]
    _exact_keys(path, "pathways[].reference", ref, {"xyz", "start_to_reference_map", "map_rule"})
    reference = read_xyz(
        path.parent / str(ref["xyz"]), int(block["charge"]), int(block["spin_multiplicity"])
    )
    mapping = tuple(int(i) for i in ref["start_to_reference_map"])
    if sorted(mapping) != list(range(len(reference.symbols))):
        raise ValueError(f"{path}: start_to_reference_map is not a permutation of the reference")
    return T4Pathway(
        pathway=str(block["pathway"]),
        ts_id=str(block["ts_id"]),
        charge=int(block["charge"]),
        spin_multiplicity=int(block["spin_multiplicity"]),
        active_atom_indices=tuple(int(i) for i in block["active_atom_indices"]),
        forming_bonds=_pairs(path, "pathways[].forming_bonds", block["forming_bonds"]),
        start=start,
        reference=reference,
        start_to_reference_map=mapping,
        map_rule=str(ref["map_rule"]),
    )


def load_t4_fixture(path: Path) -> T4Fixture:
    """Load and validate a Tier 4 fixture YAML (``schema: 1``, two competing pathways).

    The optional ``pruning_rule`` goes through ``PathwayPruningRule`` (slice 02), so its threshold
    is required and has no default; ``downstream_exo_minor`` must name a pathway of the fixture.

    Raises:
        ValueError: On a wrong schema; missing or unknown keys at any level; not exactly two
            pathways with distinct labels; a window that is not ``low < high``; a pruning rule
            naming other pathways; or a downstream node on an unknown pathway.
    """
    path = Path(path)
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    optional = {"pruning_rule", "downstream_exo_minor"} & set(data)
    _exact_keys(
        path,
        "top-level",
        data,
        {"schema", "fixture", "species", "pathways", "selectivity", "literature"} | optional,
    )
    species = _species(path, data["species"])
    pathways = tuple(_t4_pathway(path, block) for block in data["pathways"])
    labels = [p.pathway for p in pathways]
    if len(pathways) != 2 or len(set(labels)) != 2:
        raise ValueError(f"{path}: need exactly two pathways with distinct labels, got {labels}")
    selectivity = data["selectivity"]
    _exact_keys(path, "selectivity", selectivity, T4_SELECTIVITY_KEYS)
    window_block = selectivity["uma_window_kcal_mol"]
    _exact_keys(
        path,
        "selectivity.uma_window_kcal_mol",
        window_block,
        {"low", "high", "low_inclusive", "high_inclusive"},
    )
    window = T4Window(
        low=float(window_block["low"]),
        high=float(window_block["high"]),
        low_inclusive=bool(window_block["low_inclusive"]),
        high_inclusive=bool(window_block["high_inclusive"]),
    )
    if not window.low < window.high:
        raise ValueError(f"{path}: uma_window_kcal_mol must have low < high")
    rule = None
    if "pruning_rule" in data:
        rule = PathwayPruningRule.model_validate(data["pruning_rule"])
        if sorted(rule.pathways) != sorted(labels):
            raise ValueError(f"{path}: pruning_rule pathways {rule.pathways} are not {labels}")
    downstream = None
    if "downstream_exo_minor" in data:
        block = data["downstream_exo_minor"]
        _exact_keys(
            path,
            "downstream_exo_minor",
            block,
            {
                "node_id",
                "priority",
                "pathway",
                "species_id",
                "smiles",
                "charge",
                "spin_multiplicity",
                "xyz",
            },
        )
        if block["pathway"] not in labels:
            raise ValueError(f"{path}: downstream_exo_minor pathway {block['pathway']!r} unknown")
        downstream = T4Downstream(
            node_id=str(block["node_id"]),
            priority=int(block["priority"]),
            pathway=str(block["pathway"]),
            species_id=str(block["species_id"]),
            smiles=str(block["smiles"]),
            charge=int(block["charge"]),
            spin_multiplicity=int(block["spin_multiplicity"]),
            xyz=path.parent / str(block["xyz"]),
        )
    return T4Fixture(
        name=str(data["fixture"]),
        path=path,
        species=tuple(species),
        pathways=pathways,
        kind=str(selectivity["kind"]),
        temperature_k=float(selectivity["temperature_k"]),
        reference_ddG_dagger_kcal_mol=float(selectivity["reference_ddG_dagger_kcal_mol"]),
        liu_header_ddG_dagger_kcal_mol=float(selectivity["liu_header_ddG_dagger_kcal_mol"]),
        uma_window=window,
        gfn2_gate=dict(selectivity["gfn2_gate"]),
        literature=data["literature"],
        pruning_rule=rule,
        downstream=downstream,
    )


T4_YAMLS = ("t4_endo_exo_unmapped.yaml", "t4_mapped_selectivity_pruned.yaml")


def t4(name: str) -> T4Fixture:
    """Load one Tier 4 fixture by file name."""
    return load_t4_fixture(DATA / "e2e5" / name)
