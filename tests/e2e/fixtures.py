"""Loader for the Human Fixture inputs (``tests/e2e/data/hf*.yaml``, provisional per TJ Q-E3)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.core import MolecularState
from eta_rxncat.orchestrator import ReactionSpec, SpeciesSpec

DATA = Path(__file__).parent / "data"


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
    species = []
    for raw in data["species"]:
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
