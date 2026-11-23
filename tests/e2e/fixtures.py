"""Loader for the Human Fixture inputs (``tests/e2e/data/hf*.yaml``, provisional per TJ Q-E3)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from eta_rxncat.conformers import ConformerOptions
from eta_rxncat.orchestrator import ReactionSpec, SpeciesSpec

DATA = Path(__file__).parent / "data"


@dataclass(frozen=True)
class Fixture:
    """A fixture: its species and, for a reaction fixture, the reaction."""

    name: str
    species: tuple[SpeciesSpec, ...]
    reaction: ReactionSpec | None

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
    unknown = sorted(set(data) - {"schema", "fixture", "species", "reaction"})
    if unknown:
        raise ValueError(f"{path}: unknown keys {unknown}")
    species = []
    for raw in data["species"]:
        extra = sorted(
            set(raw) - {"species_id", "smiles", "charge", "spin_multiplicity", "conformer_options"}
        )
        if extra:
            raise ValueError(f"{path}: species keys {extra} unknown")
        species.append(
            SpeciesSpec(
                species_id=str(raw["species_id"]),
                smiles=str(raw["smiles"]),
                charge=int(raw["charge"]),
                spin_multiplicity=int(raw["spin_multiplicity"]),
                conformer_options=ConformerOptions(**raw.get("conformer_options", {})),
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
    return Fixture(name=str(data["fixture"]), species=tuple(species), reaction=reaction)


def hf1() -> Fixture:
    """Human Fixture 1 (n-butane)."""
    return load_fixture(DATA / "hf1_butane.yaml")


def hf2() -> Fixture:
    """Human Fixture 2 (butadiene + ethylene -> cyclohexene)."""
    return load_fixture(DATA / "hf2_diels_alder.yaml")
