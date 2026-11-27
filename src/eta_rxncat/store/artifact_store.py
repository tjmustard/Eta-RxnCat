"""WAL-mode SQLite store of per-stage artifacts; completed artifacts are never silently replaced."""

import hashlib
import json
import numbers
import sqlite3
import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from eta_rxncat.store.keys import StageKey, canon

SCHEMA_VERSION = 1
"""``PRAGMA user_version`` of a store file this code can read and write."""

_OPEN_RETRY_FIRST_S = 0.005
_OPEN_RETRY_MAX_S = 0.1
_BUSY_TIMEOUT_MAX_MS = 2**31 - 1
"""Largest ``busy_timeout`` SQLite takes (a C int); longer or infinite waits are clamped to it."""
_RETRYABLE = frozenset({sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED})

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


class StoreBusyError(Exception):
    """Another connection kept the store file locked past ``open_timeout_s`` during open."""


def _now() -> str:
    """Return the current UTC time in ISO 8601."""
    return datetime.now(UTC).isoformat()


def _refuse_non_real(open_timeout_s: object) -> None:
    """Refuse an ``open_timeout_s`` that is a ``bool`` or not a real number.

    The parameter is ``object`` because type stubs do not register ``float`` as ``numbers.Real``.

    Raises:
        TypeError: If it is a ``bool`` or not a ``numbers.Real``.
    """
    if isinstance(open_timeout_s, bool) or not isinstance(open_timeout_s, numbers.Real):
        raise TypeError(f"open_timeout_s must be a real number, got {open_timeout_s!r}")


class ArtifactStore:
    """SQLite artifact store for stage-decomposed caching.

    Each write runs in its own ``BEGIN IMMEDIATE`` transaction. An instance may be shared by
    threads; its connection is guarded by a lock, and other connections to the same file wait
    up to ``busy_timeout`` (5 s) for the write lock.
    """

    def __init__(self, path: Path, *, open_timeout_s: float = 5.0) -> None:
        """Open or create the store file at ``path``, within one ``open_timeout_s`` deadline.

        The version read, the switch to WAL and the schema transaction each wait for other
        connections' locks only until the shared deadline (R52): any busy or locked condition
        during open surfaces as ``StoreBusyError``, never as a raw ``OperationalError``. The
        file's ``user_version`` is checked before anything is written, so an unsupported file
        is rejected untouched. After a successful open, ``busy_timeout`` is 5000 ms.

        Args:
            path: The SQLite file. Its parent directory must exist; nothing else is created.
            open_timeout_s: Deadline in seconds for the whole open; a real number > 0.
                ``math.inf`` means no deadline: a locked file is waited for without limit.
                Each single wait inside SQLite is capped at ``2**31 - 1`` ms.

        Raises:
            TypeError: If ``open_timeout_s`` is a ``bool`` or not a real number (nothing is
                created).
            ValueError: If ``open_timeout_s`` is NaN or not > 0 (nothing is created).
            FileNotFoundError: If ``path.parent`` is not an existing directory.
            StoreSchemaError: If the file's ``user_version`` is neither 0 (new) nor 1, or the
                file cannot be put in WAL mode.
            StoreBusyError: If another connection keeps the file locked past
                ``open_timeout_s``; chains the last ``OperationalError``.
        """
        _refuse_non_real(open_timeout_s)
        if not open_timeout_s > 0:
            raise ValueError(f"open_timeout_s must be > 0, got {open_timeout_s!r}")
        self._open_start = time.monotonic()
        self._deadline = self._open_start + open_timeout_s
        self.path = Path(path)
        if not self.path.parent.is_dir():
            raise FileNotFoundError(f"store directory does not exist: {self.path.parent}")
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self.path,
            timeout=min(open_timeout_s, _BUSY_TIMEOUT_MAX_MS / 1000),
            isolation_level=None,
            check_same_thread=False,
        )
        try:
            version = self._busy_step("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):  # before any statement that writes
                raise StoreSchemaError(
                    f"{self.path}: store schema version {version} is not supported "
                    f"(expected {SCHEMA_VERSION})"
                )
            row = self._busy_step("PRAGMA journal_mode=WAL").fetchone()
            mode = str(row[0]).lower() if row else ""
            if mode != "wal":
                raise StoreSchemaError(f"{self.path}: journal mode is {mode!r}, not 'wal'")
            self._init_schema()
            self._conn.execute("PRAGMA busy_timeout=5000")
        except BaseException:
            self._conn.close()
            raise

    def _busy_step(self, sql: str) -> sqlite3.Cursor:
        """Run one open statement, waiting for other connections' locks until the deadline.

        This is the only place an ``OperationalError`` is caught, and it is used only during
        ``__init__``. Before each attempt ``busy_timeout`` is set to the time remaining, so a
        statement that blocks inside SQLite cannot pass the deadline; BUSY/LOCKED is retried
        with backoff (5 ms doubling to 100 ms).

        Raises:
            StoreBusyError: When the deadline passes; chains the last ``OperationalError``.
        """
        delay = _OPEN_RETRY_FIRST_S
        while True:
            remaining = self._deadline - time.monotonic()
            wait_ms = max(1, int(min(remaining * 1000, _BUSY_TIMEOUT_MAX_MS)))
            self._conn.execute(f"PRAGMA busy_timeout={wait_ms}")
            try:
                return self._conn.execute(sql)
            except sqlite3.OperationalError as exc:
                if exc.sqlite_errorcode not in _RETRYABLE:
                    raise
                remaining = self._deadline - time.monotonic()
                if remaining <= 0:
                    elapsed = time.monotonic() - self._open_start
                    raise StoreBusyError(
                        f"{self.path}: still locked after {elapsed:.2f} s while opening ({sql!r})"
                    ) from exc
                time.sleep(min(delay, remaining))
                delay = min(delay * 2, _OPEN_RETRY_MAX_S)

    def _user_version(self) -> int:
        """Return the file's ``PRAGMA user_version``."""
        version: int = self._conn.execute("PRAGMA user_version").fetchone()[0]
        return version

    def _init_schema(self) -> None:
        """Create the schema on a new file under ``BEGIN IMMEDIATE``, then check the version."""
        self._busy_step("BEGIN IMMEDIATE")
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
