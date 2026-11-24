"""Loaders for the Human Fixture inputs and the Tier 3 TS fixtures (provisional per TJ Q-E3)."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import MolecularState
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
        if self.start.form == "start_xyz" and self.start.xyz is not None:
            state = read_xyz(self.start.xyz, self.charge, self.spin_multiplicity)
        elif self.start.form == "start_from_fixture" and self.start.path_template is not None:
            if recipe is None:
                raise ValueError(f"{self.name}: start_from_fixture needs a recipe")
            path = REPO / self.start.path_template.format(recipe=recipe)
            raw = json.loads(path.read_text(encoding="utf-8"))[str(self.start.key)]
            state = MolecularState(
                symbols=list(raw["symbols"]),
                coordinates=[list(row) for row in raw["coordinates_angstrom"]],
                charge=int(raw["charge"]),
                spin_multiplicity=int(raw["multiplicity"]),
            )
        else:
            raise ValueError(f"{self.name}: start form {self.start.form} has no direct geometry")
        return MolecularState.model_validate(
            {**state.model_dump(), "active_atom_indices": list(self.active_atom_indices)}
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
