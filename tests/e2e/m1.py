"""Fixture M1 (v0.4.0): loader, the stated atom-map rule and the measurements both M1 tests share.

Graft cyclobutene onto TS1a_n by the provisional YAML, then compare with Liu's TS1b_n. The atom map
from the graft to TS1b_n is chosen by a coordinate-free rule (mission R2, TJ "P2 A"): the
lexicographically smallest element-preserving isomorphism of the graft's source graph onto
TS1b_n's perceived graph. No RMSD ever takes part in the choice (N2).
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from e2e_env import REPO
from fixtures import read_xyz

from eta_rxncat.core import AtomMappingSpec, GraftResult, GraftSpec, MolecularState
from eta_rxncat.mapping import core_rmsd_angstrom, junction_volumes, perceive_bonds, superpose

DATA = REPO / "tests" / "e2e" / "data" / "e2e5"
YAML_PATH = DATA / "m1_ts1a_n_to_ts1b_n.yaml"
CANDIDATES_V040 = REPO / "tests" / "candidate_outputs" / "v0.4.0"
FORMING_CORE_BOUND_ANGSTROM = 0.10
"""TJ "Q6. A": forming-core RMSD of the pure graft to TS1b_n."""


@dataclass(frozen=True)
class M1:
    """The M1 inputs: the YAML, the three structures and the graft request."""

    config: dict[str, Any]
    template: MolecularState
    fragment: MolecularState
    reference: MolecularState
    spec: GraftSpec
    input_sha256: dict[str, str]


def load_m1() -> M1:
    """Read the M1 YAML, its three XYZ files and build the GraftSpec."""
    config: dict[str, Any] = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    template = read_xyz(
        DATA / config["template"], config["template_charge"], config["template_multiplicity"]
    )
    template = template.model_copy(
        update={"active_atom_indices": list(config["active_atom_indices"])}
    )
    template = MolecularState.model_validate(template.model_dump())
    fragment = read_xyz(
        DATA / config["fragment"], config["fragment_charge"], config["fragment_multiplicity"]
    )
    reference = read_xyz(
        DATA / config["reference"], config["product_charge"], config["product_multiplicity"]
    )
    pairs = config["alignment_pairs"]
    spec = GraftSpec(
        template=AtomMappingSpec(
            keep=list(config["keep"]),
            delete=list(config["delete"]),
            alignment=[t for t, _ in pairs],
        ),
        fragment_alignment=[f for _, f in pairs],
        fragment_delete=list(config["fragment_delete"]),
        constrained_core=list(config["constrained_core"]),
        product_charge=config["product_charge"],
        product_multiplicity=config["product_multiplicity"],
    )
    sha = {
        name: hashlib.sha256((DATA / config[name]).read_bytes()).hexdigest()
        for name in ("template", "fragment", "reference")
    }
    sha["yaml"] = hashlib.sha256(YAML_PATH.read_bytes()).hexdigest()
    return M1(config, template, fragment, reference, spec, sha)


def _graph_mol(symbols: list[str], bonds: list[tuple[int, int]]) -> Any:
    """An RDKit mol of element atoms, all bonds single, no implicit hydrogens."""
    from rdkit import Chem

    mol = Chem.RWMol()
    for symbol in symbols:
        atom = Chem.Atom(symbol)
        atom.SetNoImplicit(True)
        mol.AddAtom(atom)
    for i, j in bonds:
        mol.AddBond(i, j, Chem.BondType.SINGLE)
    return mol.GetMol()


@dataclass(frozen=True)
class AtomMap:
    """The stated-rule map and what the rule saw."""

    graft_to_ts1b_n_map: list[int]
    n_isomorphisms: int
    matches: list[tuple[int, ...]]


class MapRuleError(RuntimeError):
    """The map rule cannot apply (unequal bond counts or zero isomorphisms): stop and report."""


def derive_map(result: GraftResult, reference: MolecularState) -> AtomMap:
    """Mission R2: the lexicographically smallest isomorphism, source graph -> TS1b_n graph."""
    reference_bonds = perceive_bonds(reference)
    if len(reference_bonds) != len(result.source_bonds):
        raise MapRuleError(
            f"bond counts differ: graft source graph {len(result.source_bonds)}, "
            f"TS1b_n {len(reference_bonds)}"
        )
    source = _graph_mol(result.product.symbols, list(result.source_bonds))
    target = _graph_mol(reference.symbols, reference_bonds)
    matches = list(
        target.GetSubstructMatches(source, uniquify=False, useChirality=False, maxMatches=100000)
    )
    if not matches:
        raise MapRuleError("no element-preserving isomorphism of the source graph onto TS1b_n")
    return AtomMap(list(min(matches)), len(matches), sorted(matches))


def heavy_maps(result: GraftResult, atom_map: AtomMap) -> list[tuple[int, ...]]:
    """The distinct heavy-atom restrictions of every isomorphism, sorted."""
    heavy = [k for k, s in enumerate(result.product.symbols) if s != "H"]
    return sorted({tuple(m[k] for k in heavy) for m in atom_map.matches})


def forming_core_rmsd_angstrom(
    product_coords: Any, reference: MolecularState, core: list[int], mapping: list[int]
) -> float:
    """RMSD of the product's core onto TS1b_n's mapped atoms (Horn, unweighted)."""
    return core_rmsd_angstrom(
        reference.coordinates, product_coords, [mapping[k] for k in core], core
    )


def heavy_map_rmsds(
    result: GraftResult, reference: MolecularState, atom_map: AtomMap
) -> list[dict[str, Any]]:
    """Forming-core RMSD under each distinct heavy-atom map, sorted by the heavy-map tuple.

    Reported so TJ sees the stated rule did not pick by RMSD (mission R2).
    """
    heavy = [k for k, s in enumerate(result.product.symbols) if s != "H"]
    core = result.constrained_core_product_indices
    rows = []
    for heavy_map in heavy_maps(result, atom_map):
        partial = dict(zip(heavy, heavy_map, strict=True))
        rows.append(
            {
                "heavy_map": list(heavy_map),
                "forming_core_rmsd_angstrom": core_rmsd_angstrom(
                    reference.coordinates,
                    result.product.coordinates,
                    [partial[k] for k in core],
                    core,
                ),
            }
        )
    return rows


def rmsds_to_reference(
    coords: Any, reference: MolecularState, result: GraftResult, mapping: list[int]
) -> dict[str, float]:
    """Full, active and forming-core RMSD of ``coords`` to TS1b_n under ``mapping``."""
    n = len(mapping)
    active = result.active_product_indices
    core = result.constrained_core_product_indices
    return {
        "full_rmsd_angstrom": core_rmsd_angstrom(
            reference.coordinates, coords, mapping, list(range(n))
        ),
        "active_rmsd_angstrom": core_rmsd_angstrom(
            reference.coordinates, coords, [mapping[k] for k in active], active
        ),
        "forming_core_rmsd_angstrom": forming_core_rmsd_angstrom(coords, reference, core, mapping),
    }


def appended_heavy_rmsd_angstrom(
    coords: Any, reference: MolecularState, result: GraftResult, mapping: list[int]
) -> float:
    """Appended heavy atoms vs their TS1b_n partners after forming-core superposition (no refit)."""
    core = result.constrained_core_product_indices
    points = np.asarray(coords, dtype=np.float64)
    ref = np.asarray(reference.coordinates, dtype=np.float64)
    fit = superpose(points[core], ref[[mapping[k] for k in core]])
    appended = [
        k
        for k, (source, _) in enumerate(result.index_map)
        if source == "fragment" and result.product.symbols[k] != "H"
    ]
    moved = fit.apply(points[appended])
    diff = moved - ref[[mapping[k] for k in appended]]
    return float(np.sqrt((diff * diff).sum(axis=1).mean()))


def mapped_bonds(bonds: list[tuple[int, int]], mapping: list[int]) -> set[tuple[int, int]]:
    """Bonds re-indexed through ``mapping`` as a set of sorted pairs."""
    return {(min(mapping[i], mapping[j]), max(mapping[i], mapping[j])) for i, j in bonds}


def reference_junction_signs(
    result: GraftResult, reference: MolecularState, mapping: list[int], tolerance: float
) -> list[dict[str, Any]]:
    """TS1b_n's junction volumes at the mapped positions, with the graft's source bonds."""
    coords = [reference.coordinates[mapping[k]] for k in range(len(mapping))]
    n_kept = sum(1 for source, _ in result.index_map if source == "template")
    return [
        j.model_dump() for j in junction_volumes(coords, result.source_bonds, n_kept, tolerance)
    ]


def candidate_dir() -> Path:
    """``ETA_RXNCAT_CANDIDATE_DIR`` if set, else ``tests/candidate_outputs/v0.4.0`` (write only)."""
    override = os.environ.get("ETA_RXNCAT_CANDIDATE_DIR")
    path = Path(override) if override else CANDIDATES_V040
    path.mkdir(parents=True, exist_ok=True)
    return path


def spec_payload(m1: M1) -> dict[str, Any]:
    """The graft request as written in a candidate."""
    return m1.spec.model_dump()


def product_payload(state: MolecularState) -> dict[str, Any]:
    """Symbols, coordinates (Angstrom), charge and multiplicity of a structure."""
    return {
        "symbols": list(state.symbols),
        "coordinates_angstrom": [list(row) for row in state.coordinates],
        "charge": state.charge,
        "multiplicity": state.spin_multiplicity,
    }


# --- Acceptance: regression against promoted fixtures and map confirmation (slice 07) --------

PROMOTED_V040 = REPO / "tests" / "fixtures" / "v0.4.0"
GRAFT_COORD_TOL_ANGSTROM = 1e-10
"""TJ "Q6. A": graft regression, coordinate RMSD with no superposition."""
RELAXED_E_TOL_HARTREE = 1e-5
RELAXED_HEAVY_RMSD_TOL_ANGSTROM = 0.01
"""TJ "Q6. A": relaxed regression, |dE| and heavy-atom RMSD after Horn superposition (R20(d))."""


def _load(path: Path) -> dict[str, Any] | None:
    import json

    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _plain_rmsd(a: Any, b: Any) -> float:
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    return float(np.sqrt((diff * diff).sum(axis=1).mean()))


def regression_graft(
    graft_payload: dict[str, Any], promoted_dir: Path = PROMOTED_V040
) -> dict[str, Any]:
    """Compare the graft with the promoted ``m1_graft.json``; ``pending_promotion`` if absent.

    Coordinates with no superposition (RMSD <= 1e-10 Angstrom, symbols equal); ``index_map``,
    ``graft_to_ts1b_n_map``, close-contact pairs and junction signs exact.
    """
    old = _load(promoted_dir / "m1_graft.json")
    if old is None:
        return {"status": "pending_promotion"}
    new_product, old_product = graft_payload["product"], old["product"]
    problems = []
    if new_product["symbols"] != old_product["symbols"]:
        problems.append("symbols")
        rmsd = None
    else:
        rmsd = _plain_rmsd(new_product["coordinates_angstrom"], old_product["coordinates_angstrom"])
        if rmsd > GRAFT_COORD_TOL_ANGSTROM:
            problems.append("coordinates")
    for key in ("index_map", "graft_to_ts1b_n_map"):
        if graft_payload[key] != old[key]:
            problems.append(key)
    pairs = [[c["i"], c["j"]] for c in graft_payload["close_contacts"]]
    if pairs != [[c["i"], c["j"]] for c in old["close_contacts"]]:
        problems.append("close_contacts")
    signs = [
        [j["template_atom"], j["appended_atom"], j["sign"]] for j in graft_payload["junctions"]
    ]
    if signs != [[j["template_atom"], j["appended_atom"], j["sign"]] for j in old["junctions"]]:
        problems.append("junction_signs")
    return {
        "status": "fail" if problems else "pass",
        "coordinate_rmsd_angstrom": rmsd,
        "bound_angstrom": GRAFT_COORD_TOL_ANGSTROM,
        "mismatches": problems,
    }


def regression_relaxed(
    relaxed_payload: dict[str, Any], recipe: str, promoted_dir: Path = PROMOTED_V040
) -> dict[str, Any]:
    """Compare a relaxed graft with the promoted ``m1_relaxed.<recipe>.json``.

    |dE| <= 1e-5 Eh and heavy-atom RMSD <= 0.01 Angstrom after Horn superposition over the heavy
    atoms; ``pending_promotion`` if the fixture is absent.
    """
    old = _load(promoted_dir / f"m1_relaxed.{recipe}.json")
    if old is None:
        return {"status": "pending_promotion"}
    new_product, old_product = relaxed_payload["relaxed_product"], old["relaxed_product"]
    if new_product["symbols"] != old_product["symbols"]:
        return {"status": "fail", "mismatches": ["symbols"]}
    heavy = [k for k, s in enumerate(new_product["symbols"]) if s != "H"]
    new_xyz = np.asarray(new_product["coordinates_angstrom"], dtype=np.float64)[heavy]
    old_xyz = np.asarray(old_product["coordinates_angstrom"], dtype=np.float64)[heavy]
    rmsd = superpose(new_xyz, old_xyz).rmsd_angstrom
    delta_e = abs(relaxed_payload["final_energy_hartree"] - old["final_energy_hartree"])
    problems = []
    if delta_e > RELAXED_E_TOL_HARTREE:
        problems.append("energy")
    if rmsd > RELAXED_HEAVY_RMSD_TOL_ANGSTROM:
        problems.append("heavy_atom_rmsd")
    return {
        "status": "fail" if problems else "pass",
        "abs_delta_energy_hartree": delta_e,
        "energy_bound_hartree": RELAXED_E_TOL_HARTREE,
        "heavy_atom_rmsd_angstrom": rmsd,
        "heavy_atom_rmsd_bound_angstrom": RELAXED_HEAVY_RMSD_TOL_ANGSTROM,
        "mismatches": problems,
    }


def map_confirmation(yaml_map: list[int], promoted_dir: Path = PROMOTED_V040) -> str:
    """TJ's promotion of ``m1_graft.json`` confirms the map (TJ P2 "A", R2, R25).

    ``confirmed`` if the promoted file's ``graft_to_ts1b_n_map`` equals the YAML's, ``fail`` if it
    differs, ``pending_confirmation`` if nothing is promoted. No status field is read.
    """
    old = _load(promoted_dir / "m1_graft.json")
    if old is None:
        return "pending_confirmation"
    return "confirmed" if old["graft_to_ts1b_n_map"] == list(yaml_map) else "fail"
