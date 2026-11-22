"""Tests for safe concurrent first open and non-mutating schema rejection (slice 09)."""

import hashlib
import sqlite3
import threading
from pathlib import Path

import pytest

from eta_rxncat.store import ArtifactStore, StoreSchemaError


def open_and_close(path: Path, barrier: threading.Barrier, errors: list[BaseException]) -> None:
    """Wait on the barrier, then open and close a store at ``path``, recording any error."""
    barrier.wait()
    try:
        ArtifactStore(path).close()
    except BaseException as exc:  # recorded and asserted by the caller
        errors.append(exc)


@pytest.mark.parametrize("openers", [2, 6, 16])
def test_concurrent_first_open(tmp_path: Path, openers: int) -> None:
    """N barrier-synchronised openers of a new file all succeed, in each of 100 trials."""
    errors: list[BaseException] = []
    for trial in range(100):
        path = tmp_path / f"trial-{trial}.sqlite"
        barrier = threading.Barrier(openers)
        threads = [
            threading.Thread(target=open_and_close, args=(path, barrier, errors))
            for _ in range(openers)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        conn = sqlite3.connect(path)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        conn.close()
    assert errors == [], f"{len(errors)} errors in 100 trials of {openers} openers: {errors[:3]}"


def sha256(path: Path) -> str:
    """Return the sha256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("version", [7, 2])
def test_foreign_file_untouched(tmp_path: Path, version: int) -> None:
    """A file with an unsupported user_version is rejected byte-for-byte unmodified."""
    path = tmp_path / "foreign.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.execute(f"PRAGMA user_version={version}")
    conn.close()
    before = sha256(path)
    siblings = {p.name for p in tmp_path.iterdir()}
    with pytest.raises(StoreSchemaError, match=str(version)):
        ArtifactStore(path)
    assert sha256(path) == before
    assert {p.name for p in tmp_path.iterdir()} == siblings
    assert not (tmp_path / "foreign.sqlite-wal").exists()
    assert not (tmp_path / "foreign.sqlite-shm").exists()
    raw = sqlite3.connect(path)
    assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    raw.close()


@pytest.mark.parametrize("timeout", [0, -1, 0.0, float("nan")])
def test_open_timeout_must_be_positive(tmp_path: Path, timeout: float) -> None:
    """A non-positive (or NaN) open_timeout_s raises ValueError and creates nothing."""
    with pytest.raises(ValueError, match="open_timeout_s"):
        ArtifactStore(tmp_path / "a.sqlite", open_timeout_s=timeout)
    assert list(tmp_path.iterdir()) == []


def test_existing_valid_store_reopens(tmp_path: Path) -> None:
    """A user_version 1 WAL store opens unchanged (schema, version, mode) with a custom timeout."""
    path = tmp_path / "a.sqlite"
    ArtifactStore(path).close()
    raw = sqlite3.connect(path)
    tables_before = raw.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall()
    raw.close()
    with ArtifactStore(path, open_timeout_s=0.5) as store:
        assert store.query() == []
    raw = sqlite3.connect(path)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 1
    assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert raw.execute("SELECT sql FROM sqlite_master ORDER BY name").fetchall() == tables_before
    raw.close()


def test_non_busy_operational_error_propagates(tmp_path: Path) -> None:
    """A file that is not a database fails with SQLite's own error, not a retry or busy error."""
    path = tmp_path / "junk.sqlite"
    path.write_bytes(b"not a database, just some bytes" * 100)
    before = sha256(path)
    with pytest.raises(sqlite3.DatabaseError):
        ArtifactStore(path, open_timeout_s=0.2)
    assert sha256(path) == before
