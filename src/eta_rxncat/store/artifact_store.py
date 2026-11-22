"""WAL-mode SQLite store of per-stage artifacts; completed artifacts are never silently replaced."""

import hashlib
import json
import sqlite3
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from eta_rxncat.store.keys import StageKey, canon

SCHEMA_VERSION = 1
"""``PRAGMA user_version`` of a store file this code can read and write."""

_SCHEMA = (
    """
    CREATE TABLE stage_artifacts (
        key TEXT PRIMARY KEY,
        key_schema INTEGER NOT NULL,
        geometry_hash TEXT NOT NULL,
        stage_hash TEXT NOT NULL,
        stage_kind TEXT NOT NULL,
        engine TEXT NOT NULL,
        engine_version TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
        payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL
    )
    """,
    "CREATE INDEX idx_stage_artifacts_geometry ON stage_artifacts (geometry_hash)",
    "CREATE INDEX idx_stage_artifacts_kind_engine ON stage_artifacts (stage_kind, engine)",
)


class ArtifactStatus(StrEnum):
    """Lifecycle state of a stage artifact."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactConflictError(Exception):
    """A write would change a completed artifact; only ``invalidate`` may replace one."""


class StoreSchemaError(Exception):
    """The store file has a ``user_version`` this code does not understand."""


def _now() -> str:
    """Return the current UTC time in ISO 8601."""
    return datetime.now(UTC).isoformat()


class ArtifactStore:
    """SQLite artifact store for stage-decomposed caching.

    Each write runs in its own ``BEGIN IMMEDIATE`` transaction. An instance may be shared by
    threads; its connection is guarded by a lock, and other connections to the same file wait
    up to ``busy_timeout`` (5 s) for the write lock.
    """

    def __init__(self, path: Path) -> None:
        """Open or create the store file at ``path``.

        Args:
            path: The SQLite file. Its parent directory must exist; nothing else is created.

        Raises:
            FileNotFoundError: If ``path.parent`` is not an existing directory.
            StoreSchemaError: If the file's ``user_version`` is neither 0 (new) nor 1.
        """
        self.path = Path(path)
        if not self.path.parent.is_dir():
            raise FileNotFoundError(f"store directory does not exist: {self.path.parent}")
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.path, timeout=5.0, isolation_level=None, check_same_thread=False
        )
        try:
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._init_schema()
        except BaseException:
            self._conn.close()
            raise

    def _user_version(self) -> int:
        """Return the file's ``PRAGMA user_version``."""
        version: int = self._conn.execute("PRAGMA user_version").fetchone()[0]
        return version

    def _init_schema(self) -> None:
        """Create the schema on a new file, or check the version of an existing one."""
        version = self._user_version()
        if version == 0:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                if self._user_version() == 0:  # another connection may have just created it
                    for statement in _SCHEMA:
                        self._conn.execute(statement)
                    self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            version = self._user_version()
        if version != SCHEMA_VERSION:
            raise StoreSchemaError(
                f"{self.path}: store schema version {version} is not supported "
                f"(expected {SCHEMA_VERSION})"
            )

    def put(self, key: StageKey, status: ArtifactStatus, payload: Mapping[str, object]) -> None:
        """Insert or update the artifact for ``key``.

        A new key is inserted. A row that is not completed is updated. Re-putting a completed
        row with ``status=completed`` and the identical payload is a no-op.

        Args:
            key: The stage key.
            status: The artifact's status.
            payload: JSON-serialisable result data (no NaN or infinite floats).

        Raises:
            ValueError: If the payload contains NaN or infinity; nothing is written.
            ArtifactConflictError: On any other write to a completed row; the row is unchanged.
        """
        status = ArtifactStatus(status)
        payload_json = canon(dict(payload))
        payload_sha256 = hashlib.sha256(payload_json.encode("ascii")).hexdigest()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT status, payload_sha256 FROM stage_artifacts WHERE key = ?", (key.key,)
                ).fetchone()
                now = _now()
                if row is None:
                    self._conn.execute(
                        "INSERT INTO stage_artifacts (key, key_schema, geometry_hash, "
                        "stage_hash, stage_kind, engine, engine_version, status, payload_json, "
                        "payload_sha256, created_at_utc, updated_at_utc) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            key.key,
                            key.key_schema,
                            key.geometry_hash,
                            key.stage_hash,
                            key.stage_kind,
                            key.engine,
                            key.engine_version,
                            status.value,
                            payload_json,
                            payload_sha256,
                            now,
                            now,
                        ),
                    )
                elif row[0] == ArtifactStatus.COMPLETED:
                    if status != ArtifactStatus.COMPLETED or row[1] != payload_sha256:
                        raise ArtifactConflictError(
                            f"artifact {key.key} is completed; write with status '{status.value}' "
                            "and a different payload refused (invalidate it first)"
                        )
                else:
                    self._conn.execute(
                        "UPDATE stage_artifacts SET status = ?, payload_json = ?, "
                        "payload_sha256 = ?, updated_at_utc = ? WHERE key = ?",
                        (status.value, payload_json, payload_sha256, now, key.key),
                    )
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise

    def get(self, key: StageKey) -> dict[str, Any] | None:
        """Return the payload of a completed artifact, or ``None`` (missing or not completed)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT payload_json FROM stage_artifacts WHERE key = ? AND status = ?",
                (key.key, ArtifactStatus.COMPLETED.value),
            ).fetchone()
        if row is None:
            return None
        payload: dict[str, Any] = json.loads(row[0])
        return payload

    def status(self, key: StageKey) -> ArtifactStatus | None:
        """Return the artifact's status, or ``None`` if there is no row for ``key``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT status FROM stage_artifacts WHERE key = ?", (key.key,)
            ).fetchone()
        return None if row is None else ArtifactStatus(row[0])

    def invalidate(self, key: StageKey) -> bool:
        """Delete the artifact for ``key``; the only way to replace a completed one.

        Returns:
            ``True`` if a row existed and was deleted.
        """
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                deleted = self._conn.execute(
                    "DELETE FROM stage_artifacts WHERE key = ?", (key.key,)
                ).rowcount
                self._conn.execute("COMMIT")
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
        return deleted > 0

    def query(self, stage_kind: str | None = None, engine: str | None = None) -> list[str]:
        """Return the sorted keys whose stage kind and engine match the given filters."""
        sql = "SELECT key FROM stage_artifacts WHERE 1 = 1"
        params: list[str] = []
        if stage_kind is not None:
            sql += " AND stage_kind = ?"
            params.append(stage_kind)
        if engine is not None:
            sql += " AND engine = ?"
            params.append(engine)
        with self._lock:
            rows = self._conn.execute(sql + " ORDER BY key", params).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> Self:
        """Return the store for use in a ``with`` block."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the store."""
        self.close()
