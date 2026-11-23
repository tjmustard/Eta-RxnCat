"""Regression against a promoted candidate (Q5 "A"; R18): same device, class + RMSD matching.

Records are matched by class label and RMSD <= 0.125 Angstrom with H over graph automorphisms with
proper rotations only; an unmatched record on either side fails. sigma and g must be equal; |dE|
<= 1e-5 Eh; G and quantities <= 0.05 kcal/mol; weights within 0.02.
"""

from collections.abc import Mapping
from typing import Any

import numpy as np

from eta_rxncat.conformers._rmsd import atom_subset, graph_permutations, min_rmsds
from eta_rxncat.engines import HARTREE_KCAL_MOL

RMSD_MATCH_ANGSTROM = 0.125
E_TOL_HARTREE = 1e-5
G_TOL_KCAL_MOL = 0.05
WEIGHT_TOL = 0.02


def _match(
    new: list[dict[str, Any]], old: list[dict[str, Any]], smiles: str
) -> list[tuple[int, int | None]]:
    """Pair each new record with an unused old record of the same class within the RMSD."""
    perms = graph_permutations(smiles, 100000)
    atoms = atom_subset(smiles, True, 100000)
    used: set[int] = set()
    pairs: list[tuple[int, int | None]] = []
    for i, rec in enumerate(new):
        candidates = [
            j for j, o in enumerate(old) if j not in used and o.get("class") == rec.get("class")
        ]
        best = None
        if candidates:
            xyz = np.asarray(rec["xyz_angstrom"], dtype=np.float64)
            rmsd = min_rmsds(
                xyz,
                [np.asarray(old[j]["xyz_angstrom"], dtype=np.float64) for j in candidates],
                perms,
                atoms,
            )
            k = int(np.argmin(rmsd))
            if rmsd[k] <= RMSD_MATCH_ANGSTROM:
                best = candidates[k]
                used.add(best)
        pairs.append((i, best))
    return pairs


def compare(new: Mapping[str, Any], old: Mapping[str, Any]) -> dict[str, Any]:
    """Compare a fresh candidate payload with the promoted one; return status and the failures.

    Both payloads carry ``environment.device`` and ``species.<id>.records`` (with ``class``,
    ``xyz_angstrom``, ``rotational_symmetry_number``, ``degeneracy``,
    ``electronic_energy_hartree``, ``gibbs_free_energy_hartree``, ``boltzmann_weight``) and an
    optional ``derived`` block whose numeric entries (kcal/mol) are compared too.
    """
    failures: list[str] = []
    if new["environment"]["device"] != old["environment"]["device"]:
        return {
            "status": "fail",
            "failures": ["device differs; regression compares like with like"],
        }
    for species_id, sp_old in old["species"].items():
        sp_new = new["species"].get(species_id)
        if sp_new is None:
            failures.append(f"{species_id}: missing in the new run")
            continue
        pairs = _match(sp_new["records"], sp_old["records"], sp_new["smiles"])
        matched_old = {j for _, j in pairs if j is not None}
        for i, j in pairs:
            if j is None:
                failures.append(f"{species_id}: new record {i} has no match")
                continue
            a, b = sp_new["records"][i], sp_old["records"][j]
            for key in ("rotational_symmetry_number", "degeneracy"):
                if a[key] != b[key]:
                    failures.append(f"{species_id}: record {i} {key} {a[key]} != {b[key]}")
            if abs(a["electronic_energy_hartree"] - b["electronic_energy_hartree"]) > E_TOL_HARTREE:
                failures.append(f"{species_id}: record {i} |dE| > {E_TOL_HARTREE} Eh")
            dg = (
                a["gibbs_free_energy_hartree"] - b["gibbs_free_energy_hartree"]
            ) * HARTREE_KCAL_MOL
            if abs(dg) > G_TOL_KCAL_MOL:
                failures.append(f"{species_id}: record {i} |dG| {abs(dg):.4f} > {G_TOL_KCAL_MOL}")
            if abs(a["boltzmann_weight"] - b["boltzmann_weight"]) > WEIGHT_TOL:
                failures.append(f"{species_id}: record {i} weight differs by > {WEIGHT_TOL}")
        for j in range(len(sp_old["records"])):
            if j not in matched_old:
                failures.append(f"{species_id}: promoted record {j} has no match")
    failures.extend(compare_derived(old.get("derived", {}), new.get("derived", {})))
    return {"status": "fail" if failures else "pass", "failures": failures}


DERIVED_BOUNDS = {
    "_kcal_mol": G_TOL_KCAL_MOL,
    "_hartree": E_TOL_HARTREE,
    "_percent": 100.0 * WEIGHT_TOL,
}
"""R54: a leaf's tolerance by the nearest unit-suffixed key on its path (Q5 bounds by kind)."""


def _kind(path: tuple[str, ...]) -> str | None:
    """The unit suffix of the nearest key on ``path`` that has one."""
    for key in reversed(path):
        for suffix in DERIVED_BOUNDS:
            if key.endswith(suffix):
                return suffix
    return None


def compare_derived(old: Any, new: Any, path: tuple[str, ...] = ()) -> list[str]:
    """Recursively compare two ``derived`` blocks (R54); return the failures.

    Dicts by key (a key on one side only fails), lists by index (same length). Floats by the unit
    kind of their path (``_kcal_mol`` 0.05, ``_hartree`` 1e-5, ``_percent`` 2.0); a float with no
    unit on its path fails as unclassified. Non-bool ints, bools and strings must be equal.
    """
    where = "/".join(path) or "derived"
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for key in sorted(set(old) | set(new)):
            if key not in old or key not in new:
                side = "promoted" if key in old else "new"
                out.append(f"derived {where}/{key}: present only in the {side} payload")
                continue
            out.extend(compare_derived(old[key], new[key], (*path, str(key))))
        return out
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [f"derived {where}: length {len(new)} != {len(old)}"]
        out = []
        for i, (a, b) in enumerate(zip(old, new, strict=True)):
            out.extend(compare_derived(a, b, (*path, f"[{i}]")))
        return out
    if isinstance(old, float) or isinstance(new, float):
        if (
            isinstance(old, bool)
            or isinstance(new, bool)
            or not isinstance(old, int | float)
            or not isinstance(new, int | float)
        ):
            return [f"derived {where}: {new!r} vs {old!r} (type differs)"]
        kind = _kind(path)
        if kind is None:
            return [f"unclassified derived value {where}"]
        if abs(new - old) > DERIVED_BOUNDS[kind]:
            return [f"derived {where}: |{new} - {old}| > {DERIVED_BOUNDS[kind]}"]
        return []
    if type(old) is not type(new) or old != new:
        return [f"derived {where}: {new!r} != {old!r}"]
    return []
