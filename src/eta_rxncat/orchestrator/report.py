"""Deterministic JSON reports (``schema: 1``): sorted keys, exact floats, LF, trailing newline."""

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from eta_rxncat.core import ConformerEnsemble

REPORT_SCHEMA = 1


def _check_floats(obj: Any, where: str = "$") -> None:
    """Reject NaN and infinity anywhere in ``obj``."""
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError(f"non-finite float at {where}")
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            _check_floats(v, f"{where}.{k}")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            _check_floats(v, f"{where}[{i}]")


def report_text(payload: Mapping[str, Any]) -> str:
    """Return the report text: ``{"schema": 1, **payload}`` as sorted, indented JSON.

    Floats are written with ``repr`` (Python's shortest round-trip form), so re-parsing gives the
    same floats exactly.

    Raises:
        ValueError: If ``payload`` sets another ``schema`` or holds NaN or infinity.
    """
    if payload.get("schema", REPORT_SCHEMA) != REPORT_SCHEMA:
        raise ValueError(f"report schema must be {REPORT_SCHEMA}, not {payload['schema']!r}")
    data = {**payload, "schema": REPORT_SCHEMA}
    _check_floats(data)
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"


def write_report(path: Path, payload: Mapping[str, Any]) -> None:
    """Write ``report_text(payload)`` to ``path`` (UTF-8, LF line endings)."""
    Path(path).write_text(report_text(payload), encoding="utf-8", newline="\n")


def ensemble_to_payload(ensemble: ConformerEnsemble) -> dict[str, Any]:
    """Return the report form of an ensemble, one entry per record in ensemble order."""
    records = []
    for i, (record, weight) in enumerate(
        zip(ensemble.records, ensemble.boltzmann_weights, strict=True)
    ):
        thermo = record.thermo
        records.append(
            {
                "index": i,
                "source_ids": list(record.source_ids),
                "electronic_energy_hartree": thermo.electronic_energy_hartree,
                "gibbs_free_energy_hartree": thermo.gibbs_free_energy_hartree,
                "zpe_hartree": thermo.zpe_hartree,
                "entropy_components_hartree_per_k": dict(thermo.entropy_components_hartree_per_k),
                "rotational_symmetry_number": thermo.rotational_symmetry_number,
                "degeneracy": record.degeneracy,
                "boltzmann_weight": weight,
                "lowest_frequencies_cm1": list(thermo.frequencies_cm1[:6]),
                "recovery_steps": list(record.optimization.recovery_steps),
                "symbols": list(record.state.symbols),
                "xyz_angstrom": [list(row) for row in record.state.coordinates],
            }
        )
    return {
        "species_id": ensemble.species_id,
        "smiles": ensemble.smiles,
        "temperature_k": ensemble.temperature_k,
        "ensemble_gibbs_hartree": ensemble.ensemble_gibbs_hartree,
        "lowest_index": ensemble.lowest_index,
        "records": records,
    }
