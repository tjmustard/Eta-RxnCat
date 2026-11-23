"""Reference values: format, loader and TJ's transcription (mission R43, R46-R48).

Format ``schema: 1``: ``reference_species`` (per species id: ``sigma``, ``conformer``,
``thermo_model``) and ``entries`` (``quantity``, ``level``, ``method``, ``value``, ``unit``,
``standard_state``, ``temperature_k``, ``provenance``, ``gate``). Only the ωB97M-V level may gate.

Entry point (writes the candidate; never read back)::

    python -m tests.e2e.reference_values transcribe <results.json> <out.json>
"""

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

QUANTITIES = frozenset(
    {
        "hf1.dE_gauche_anti",
        "hf1.dH_gauche_anti",
        "hf1.dG_gauche_anti",
        "hf1.gauche_population",
        "hf2.dE_r",
        "hf2.dH_r",
        "hf2.dG_r",
    }
)
GATING_LEVEL = "wb97mv_def2tzvpd//b3lyp_631gss"
LEVELS = frozenset({GATING_LEVEL, "b3lyp_631gss"})
UNITS = frozenset({"kcal/mol", "percent"})
STANDARD_STATES = frozenset({"1 atm", "1 bar", "1 M", "n/a"})
EXAMPLE_PROVENANCE = "EXAMPLE — not a reference"
ENTRY_KEYS = frozenset(
    {
        "quantity",
        "level",
        "method",
        "value",
        "unit",
        "standard_state",
        "temperature_k",
        "provenance",
        "gate",
    }
)
DELTA_N = {"hf2.dE_r": -1, "hf2.dH_r": -1, "hf2.dG_r": -1}
"""Moles of gas, products minus reactants, of each reaction quantity (others 0)."""

TJ_RESULTS_SHA256 = "40fe7c7f5ac697815b4e78e403ae1ec71731f7a82d925856b21597a59c97a35e"
TJ_SOURCE = Path(__file__).parent / "data" / "reference" / "tj-reference-b3lyp-20261123"

R_KCAL_MOL_K = 6.02214076e23 * 1.380649e-23 / 4184.0


class ReferenceError(ValueError):
    """A reference-values file breaks the format or the loader rules."""


def _check_entry(i: int, e: dict[str, Any], fixtures_mode: bool) -> None:
    where = f"entry {i}"
    if set(e) != ENTRY_KEYS:
        raise ReferenceError(f"{where}: keys {sorted(e)} != {sorted(ENTRY_KEYS)}")
    if e["quantity"] not in QUANTITIES:
        raise ReferenceError(f"{where}: unknown quantity {e['quantity']!r}")
    if e["level"] not in LEVELS:
        raise ReferenceError(f"{where}: unknown level {e['level']!r}")
    if e["unit"] not in UNITS:
        raise ReferenceError(f"{where}: unknown unit {e['unit']!r}")
    if e["standard_state"] not in STANDARD_STATES:
        raise ReferenceError(f"{where}: unknown standard_state {e['standard_state']!r}")
    if not isinstance(e["gate"], bool):
        raise ReferenceError(f"{where}: gate must be a bool")
    if e["gate"] and e["level"] != GATING_LEVEL:
        raise ReferenceError(f"{where}: gate true is allowed only at {GATING_LEVEL}")
    value = e["value"]
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ReferenceError(f"{where}: value must be a finite number")
    if not isinstance(e["provenance"], str) or not e["provenance"]:
        raise ReferenceError(f"{where}: provenance must be non-empty text")
    if fixtures_mode and e["provenance"] == EXAMPLE_PROVENANCE:
        raise ReferenceError(f"{where}: an EXAMPLE entry is not a reference")


def load_reference_values(data: dict[str, Any], *, fixtures_mode: bool) -> dict[str, Any]:
    """Validate reference values and return them unchanged.

    ``fixtures_mode`` is the mode for ``tests/fixtures/v0.3.0/reference_values.json``: it refuses
    any EXAMPLE entry.

    Raises:
        ReferenceError: On any format or rule violation.
    """
    if data.get("schema") != 1:
        raise ReferenceError("schema must be 1")
    if set(data) != {"schema", "reference_species", "entries"}:
        raise ReferenceError(f"top-level keys {sorted(data)} unexpected")
    for species_id, ref in data["reference_species"].items():
        if set(ref) != {"sigma", "conformer", "thermo_model"}:
            raise ReferenceError(f"reference_species {species_id!r}: keys {sorted(ref)}")
        if isinstance(ref["sigma"], bool) or not isinstance(ref["sigma"], int) or ref["sigma"] < 1:
            raise ReferenceError(f"reference_species {species_id!r}: sigma must be an int >= 1")
    seen: set[tuple[str, str]] = set()
    for i, entry in enumerate(data["entries"]):
        _check_entry(i, entry, fixtures_mode)
        pair = (entry["quantity"], entry["level"])
        if pair in seen:
            raise ReferenceError(f"entry {i}: a second entry for {pair}")
        seen.add(pair)
    return data


def load_reference_file(path: Path, *, fixtures_mode: bool) -> dict[str, Any]:
    """Load and validate a reference-values JSON file."""
    return load_reference_values(
        json.loads(Path(path).read_text(encoding="utf-8")), fixtures_mode=fixtures_mode
    )


def value_at_1m(entry: dict[str, Any]) -> float:
    """Return the entry's value converted to the 1 M standard state (kcal/mol).

    1 atm -> 1 M adds dn RT ln(c RT / p) (c = 1 mol/L, p = 101325 Pa); 1 bar -> 1 atm adds
    dn RT ln(1.01325). ``n/a`` and ``1 M`` values (and quantities with dn = 0) are unchanged.
    """
    dn = DELTA_N.get(entry["quantity"], 0)
    value = float(entry["value"])
    state = entry["standard_state"]
    if dn == 0 or state in ("1 M", "n/a"):
        return value
    rt = R_KCAL_MOL_K * float(entry["temperature_k"])
    if state == "1 bar":
        value += dn * rt * math.log(1.01325)
    vm_l = 1000.0 * (6.02214076e23 * 1.380649e-23) * float(entry["temperature_k"]) / 101325.0
    return value + dn * rt * math.log(vm_l)


def is_reported_only(entry: dict[str, Any]) -> bool:
    """``hf1.gauche_population`` is always reported, even with ``gate: true``."""
    return entry["quantity"] == "hf1.gauche_population" or not entry["gate"]


# TJ's results.json -> candidate reference values (R46) -------------------------------------

_BLOCKS = {"GATING REFERENCE": GATING_LEVEL, "B3LYP/6-31G** (RRHO)": "b3lyp_631gss"}
_KEYS: tuple[tuple[str, str, str, str], ...] = (
    # (path under the block, quantity, unit, standard_state)
    ("butane_gauche_minus_anti_kcal_mol/dE", "hf1.dE_gauche_anti", "kcal/mol", "n/a"),
    ("butane_gauche_minus_anti_kcal_mol/dH_298", "hf1.dH_gauche_anti", "kcal/mol", "n/a"),
    ("butane_gauche_minus_anti_kcal_mol/dG_298", "hf1.dG_gauche_anti", "kcal/mol", "n/a"),
    ("butane_gauche_population_percent_298K/from_dG", "hf1.gauche_population", "percent", "n/a"),
    ("diels_alder_kcal_mol/dE_r", "hf2.dE_r", "kcal/mol", "n/a"),
    ("diels_alder_kcal_mol/dH_r_298", "hf2.dH_r", "kcal/mol", "n/a"),
    ("diels_alder_kcal_mol/dG_r_298_1M", "hf2.dG_r", "kcal/mol", "1 M"),
)
_GATES = frozenset({("hf1.dG_gauche_anti", GATING_LEVEL), ("hf2.dG_r", GATING_LEVEL)})
_SPECIES = ("butane_anti", "butane_gauche", "butadiene_strans", "ethylene", "cyclohexene")


def transcribe_tj_results(path: Path) -> dict[str, Any]:
    """Return TJ's results.json as candidate reference values: a fixed key table, no arithmetic.

    Floats are copied as parsed. Only ``hf1.dG_gauche_anti`` and ``hf2.dG_r`` at the ωB97M-V
    level gate (R48).
    """
    raw = Path(path).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    entries = []
    for block, level in _BLOCKS.items():
        for key, quantity, unit, state in _KEYS:
            node: Any = data[block]
            for part in key.split("/"):
                node = node[part]
            entries.append(
                {
                    "quantity": quantity,
                    "level": level,
                    "method": data[block]["label"],
                    "value": node,
                    "unit": unit,
                    "standard_state": state,
                    "temperature_k": data["temperature_K"],
                    "provenance": (
                        "TJ-approved 2026-11-23 'Send as my reference'; advisor helper, PySCF "
                        f"2.15.1 / geomeTRIC 1.1.1; results.json sha256 {sha}; key {block}/{key}"
                    ),
                    "gate": (quantity, level) in _GATES,
                }
            )
    species = {
        name: {
            "sigma": data["symmetry_numbers_used"][name],
            "conformer": name,
            "thermo_model": "RRHO",
        }
        for name in _SPECIES
    }
    return {"schema": 1, "reference_species": species, "entries": entries}


def main(argv: list[str]) -> int:
    """``transcribe <results.json> <out.json>``: write the candidate reference values."""
    if len(argv) != 3 or argv[0] != "transcribe":
        print("usage: python -m tests.e2e.reference_values transcribe <results.json> <out.json>")
        return 2
    from eta_rxncat.orchestrator import write_report

    values = load_reference_values(transcribe_tj_results(Path(argv[1])), fixtures_mode=True)
    write_report(Path(argv[2]), values)
    print(f"wrote {argv[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
