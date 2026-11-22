"""Canonical, versioned per-stage cache keys (``key_schema = 1``).

A key covers everything that changes a stage's result (geometry, charge, multiplicity, active
atoms, stage settings, engine identity) and nothing that does not (``metadata``). Payloads are
built field by field, so a new model field changes keys only by a deliberate schema bump.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig

KEY_SCHEMA: Final = 1
"""Version of the key payloads; bumping it makes every old key miss."""

JsonScalar = str | int | float | bool | None


def canon(obj: object) -> str:
    """Return canonical JSON: sorted keys, no whitespace, ASCII only, NaN/inf rejected.

    Raises:
        ValueError: If ``obj`` contains a NaN or infinite float.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def h(obj: object) -> str:
    """Return the sha256 hex digest of ``canon(obj)``."""
    return hashlib.sha256(canon(obj).encode("ascii")).hexdigest()


def grid_coordinate(x: float) -> str:
    """Snap a coordinate to the 5-decimal grid as a fixed-point string; ``-0.0`` -> ``0.0``."""
    v = round(x, 5)
    if v == 0.0:
        v = 0.0
    return f"{v:.5f}"


def canonical_number(value: JsonScalar) -> JsonScalar:
    """Write an integral float as an int (``1.0`` -> ``1``); other values are unchanged."""
    if isinstance(value, float) and not isinstance(value, bool) and value.is_integer():
        return int(value)
    return value


def geometry_payload(state: MolecularState) -> dict[str, object]:
    """Return the keyed geometry fields of ``state`` (``metadata`` is deliberately excluded)."""
    return {
        "symbols": list(state.symbols),
        "coordinates": [[grid_coordinate(x) for x in row] for row in state.coordinates],
        "charge": state.charge,
        "spin_multiplicity": state.spin_multiplicity,
        "active_atom_indices": sorted(state.active_atom_indices),
    }


def stage_payload(stage: StageConfig, engine: EngineIdentity) -> dict[str, object]:
    """Return the keyed fields of a stage together with the engine that runs it."""
    return {
        "kind": stage.kind,
        "engine": stage.engine,
        "method": stage.method,
        "basis": stage.basis,
        "solvation": {
            "model": stage.solvation.model,
            "solvent": stage.solvation.solvent,
            "dielectric": canonical_number(stage.solvation.dielectric),
        },
        "frozen_atom_indices": sorted(stage.frozen_atom_indices),
        "options": {key: canonical_number(value) for key, value in stage.options.items()},
        "engine_identity": {"name": engine.name, "version": engine.version, "model": engine.model},
    }


@dataclass(frozen=True, slots=True)
class StageKey:
    """The cache key of one stage run on one geometry.

    Attributes:
        key_schema: Payload schema version (``KEY_SCHEMA``).
        geometry_hash: ``h(geometry_payload(state))``.
        stage_hash: ``h(stage_payload(stage, engine))``.
        key: ``h({"key_schema", "geometry_hash", "stage_hash"})``; the store's primary key.
        stage_kind: The stage kind.
        engine: The engine tag.
        engine_version: The engine version.
    """

    key_schema: int
    geometry_hash: str
    stage_hash: str
    key: str
    stage_kind: str
    engine: str
    engine_version: str


def build_stage_key(state: MolecularState, stage: StageConfig, engine: EngineIdentity) -> StageKey:
    """Build the cache key of running ``stage`` with ``engine`` on ``state``.

    Raises:
        ValueError: If ``engine.name`` is not the stage's engine tag.
    """
    if engine.name != stage.engine:
        raise ValueError(
            f"engine identity '{engine.name}' does not match stage engine '{stage.engine}'"
        )
    geometry_hash = h(geometry_payload(state))
    stage_hash = h(stage_payload(stage, engine))
    key = h({"key_schema": KEY_SCHEMA, "geometry_hash": geometry_hash, "stage_hash": stage_hash})
    return StageKey(
        key_schema=KEY_SCHEMA,
        geometry_hash=geometry_hash,
        stage_hash=stage_hash,
        key=key,
        stage_kind=stage.kind,
        engine=stage.engine,
        engine_version=engine.version,
    )
