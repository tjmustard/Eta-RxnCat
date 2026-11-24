"""SQLite + JSON content-addressed store keyed independently by computational stage.

Enables:
1. Crash-safe resubmission: completed nodes/stages are skipped automatically.
2. Incremental post-processing: appending a solvation single-point stage onto a completed
   gas-phase ReactionGraph hits cached geometries and frequencies and runs only the new stage.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from eta_rxncat.core.models import MolecularState, StageConfig


class StageCacheKey(BaseModel):
    """Canonical composite key for a single stage execution."""

    input_geometry_hash: str
    stage_config_hash: str
    composite_key: str

    @classmethod
    def build(cls, state: MolecularState, stage: StageConfig) -> StageCacheKey:
        g_hash = state.geometry_hash()
        s_hash = stage.stage_hash()
        combined = hashlib.sha256(f"{g_hash}:{s_hash}".encode("utf-8")).hexdigest()
        return cls(
            input_geometry_hash=g_hash,
            stage_config_hash=s_hash,
            composite_key=combined,
        )


class ArtifactStore:
    """Lightweight SQLite-backed artifact store for stage-decomposed caching."""

    def __init__(self, db_path: Path | str = ".eta_cache/artifacts.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stage_artifacts (
                    composite_key TEXT PRIMARY KEY,
                    input_geometry_hash TEXT NOT NULL,
                    stage_config_hash TEXT NOT NULL,
                    stage_kind TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_geom_hash ON stage_artifacts (input_geometry_hash)"
            )

    def get(self, key: StageCacheKey) -> dict[str, Any] | None:
        """Retrieve completed stage payload if present in cache."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM stage_artifacts WHERE composite_key = ? AND status = 'completed'",
                (key.composite_key,),
            ).fetchone()
        if row is None:
            return None
        loaded: dict[str, Any] = json.loads(row[0])
        return loaded

    def put(
        self,
        key: StageCacheKey,
        stage: StageConfig,
        payload: dict[str, Any],
        status: str = "completed",
    ) -> None:
        """Persist a stage execution result idempotently."""
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO stage_artifacts (
                    composite_key,
                    input_geometry_hash,
                    stage_config_hash,
                    stage_kind,
                    engine,
                    status,
                    payload_json,
                    created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key.composite_key,
                    key.input_geometry_hash,
                    key.stage_config_hash,
                    stage.stage.value,
                    stage.engine,
                    status,
                    json.dumps(payload, sort_keys=True),
                    now,
                ),
            )
