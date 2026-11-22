"""Tests for safe concurrent first open and non-mutating schema rejection (slice 09)."""

import hashlib
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from eta_rxncat.store import ArtifactStore, StoreBusyError, StoreSchemaError


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


@contextmanager
def holder(path: Path, begin: str) -> Iterator[sqlite3.Connection]:
    """Hold a raw rollback-journal connection inside ``begin`` (BEGIN EXCLUSIVE / IMMEDIATE)."""
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute(begin)
    try:
        yield conn
    finally:
        if conn.in_transaction:
            conn.execute("COMMIT")
        conn.close()


HOLDERS = ["BEGIN EXCLUSIVE", "BEGIN IMMEDIATE"]


@pytest.mark.parametrize("begin", HOLDERS)
def test_open_waits_for_released_lock(tmp_path: Path, begin: str) -> None:
    """A holder releasing after 0.3 s: the store opens without error, after >= 0.3 s, in WAL."""
    path = tmp_path / "a.sqlite"
    outcome: dict[str, object] = {}
    with holder(path, begin) as conn:

        def opener() -> None:
            try:
                ArtifactStore(path, open_timeout_s=5.0).close()
            except BaseException as exc:  # asserted below
                outcome["error"] = exc
            outcome["seconds"] = time.monotonic() - start

        thread = threading.Thread(target=opener)
        start = time.monotonic()  # before the opener can run, so the 0.3 s bound is strict
        thread.start()
        time.sleep(0.3)
        conn.execute("COMMIT")
    thread.join()
    assert "error" not in outcome, outcome
    assert isinstance(outcome["seconds"], float) and outcome["seconds"] >= 0.3
    raw = sqlite3.connect(path)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 1
    assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    raw.close()


@pytest.mark.parametrize("begin", HOLDERS)
def test_open_deadline_raises_store_busy_error(tmp_path: Path, begin: str) -> None:
    """A holder keeping the lock: StoreBusyError (never a raw OperationalError) in [0.3, 1.0] s."""
    path = tmp_path / "a.sqlite"
    with holder(path, begin):
        start = time.monotonic()
        try:
            ArtifactStore(path, open_timeout_s=0.3)
        except StoreBusyError as exc:
            elapsed = time.monotonic() - start
            error: BaseException = exc
        else:
            pytest.fail("ArtifactStore opened while the file was locked")
    assert 0.3 <= elapsed <= 1.0, elapsed
    assert type(error) is StoreBusyError
    assert isinstance(error.__cause__, sqlite3.OperationalError)
    assert str(path) in str(error)


def test_busy_timeout_restored_after_open(tmp_path: Path) -> None:
    """After a successful open the store's connection has busy_timeout 5000 ms."""
    with ArtifactStore(tmp_path / "a.sqlite", open_timeout_s=0.5) as store:
        assert store._conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_foreign_file_under_exclusive_holder(tmp_path: Path) -> None:
    """A locked foreign file gives StoreBusyError and is unchanged once the holder releases."""
    path = tmp_path / "foreign.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.commit()
    conn.execute("PRAGMA user_version=7")
    conn.close()
    before = sha256(path)
    siblings = {p.name for p in tmp_path.iterdir()}
    with holder(path, "BEGIN EXCLUSIVE"):
        with pytest.raises(StoreBusyError):
            ArtifactStore(path, open_timeout_s=0.3)
    assert sha256(path) == before
    assert {p.name for p in tmp_path.iterdir()} == siblings
    raw = sqlite3.connect(path)
    assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 7
    raw.close()
