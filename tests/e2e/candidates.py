"""Candidate output payloads (mission §5 "Candidate output", ``schema: 1``).

Written once per fixture and recipe into ``tests/candidate_outputs/v0.3.0/`` and committed in a
candidates-only commit (R23). Nothing in the suite reads a candidate back.
"""

import platform
from collections.abc import Callable, Mapping, Sequence
from importlib import metadata
from typing import Any

from eta_rxncat.conformers import generate
from eta_rxncat.core import ConformerRecord, EngineIdentity, ThermoConfig
from eta_rxncat.orchestrator import SpeciesResult, SpeciesSpec, ensemble_to_payload


def environment(identity: EngineIdentity, device: str) -> dict[str, Any]:
    """Versions, engine identity and device of a run."""
    versions = {"python": platform.python_version()}
    for dist in ("rdkit", "geometric", "fairchem-core", "torch"):
        try:
            versions[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            continue
    return {"versions": versions, "engine": identity.model_dump(), "device": device}


def species_payload(
    spec: SpeciesSpec,
    result: SpeciesResult,
    classify: Callable[[ConformerRecord], str] | None,
    failures: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """One species: inputs, pool and kept counts, dropped (with reasons), records, failures."""
    pool = generate(
        spec.smiles,
        charge=spec.charge,
        spin_multiplicity=spec.spin_multiplicity,
        options=spec.conformer_options,
        seed_geometries=spec.seed_geometries,
    )
    payload = ensemble_to_payload(result.ensemble)
    for record, entry in zip(result.ensemble.records, payload["records"], strict=True):
        if classify is not None:
            entry["class"] = classify(record)
    return {
        "smiles": spec.smiles,
        "charge": spec.charge,
        "multiplicity": spec.spin_multiplicity,
        "n_pool": len(pool.members),
        "n_kept": len(result.ensemble.records),
        "dropped": [{"source_id": sid, "reason": reason} for sid, reason in result.dropped],
        "failures": list(failures),
        **payload,
    }


def candidate(
    *,
    fixture: str,
    recipe: str,
    commit_sha: str,
    env: Mapping[str, Any],
    thermo_config: ThermoConfig,
    species: Mapping[str, Mapping[str, Any]],
    derived: Mapping[str, Any],
    checks: Mapping[str, Any],
) -> dict[str, Any]:
    """The full candidate payload (``write_report`` adds ``schema: 1``)."""
    return {
        "fixture": fixture,
        "recipe": recipe,
        "commit_sha": commit_sha,
        "environment": dict(env),
        "thermo_config": thermo_config.model_dump(),
        "species": {k: dict(v) for k, v in species.items()},
        "derived": dict(derived),
        "checks": dict(checks),
    }
