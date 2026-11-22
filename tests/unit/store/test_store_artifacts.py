"""Tests for the SQLite ArtifactStore: file handling, schema, write rules, concurrency."""

import sqlite3
import threading
from pathlib import Path

import pytest

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.store import (
    ArtifactConflictError,
    ArtifactStatus,
    ArtifactStore,
    StageKey,
    StoreSchemaError,
    build_stage_key,
)

WATER = MolecularState(
    symbols=["O", "H", "H"],
    coordinates=[[0.0, 0.0, 0.1173], [0.0, 0.7572, -0.4692], [0.0, -0.7572, -0.4692]],
    charge=0,
    spin_multiplicity=1,
)
PYSCF = EngineIdentity(name="pyscf_gpu_cpu", version="2.15.1")
P = {"energy_eh": -74.96, "converged": True, "steps": [1, 2, 3]}
P2 = {"energy_eh": -75.01, "converged": True}


def stage_key(kind: str = "single_point", method: str = "RHF") -> StageKey:
    """Return the key of a PySCF stage of ``kind`` on water."""
    stage = StageConfig(kind=kind, engine="pyscf_gpu_cpu", method=method, basis="STO-3G")
    return build_stage_key(WATER, stage, PYSCF)


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    """Return a new store in a temporary directory."""
    return ArtifactStore(tmp_path / "a.sqlite")


def test_missing_parent_directory(tmp_path: Path) -> None:
    """A missing parent raises FileNotFoundError and is not created."""
    with pytest.raises(FileNotFoundError):
        ArtifactStore(tmp_path / "missing" / "a.sqlite")
    assert not (tmp_path / "missing").exists()


def test_only_the_store_file_is_created(tmp_path: Path) -> None:
    """Opening creates the store file (and SQLite's own -wal/-shm siblings) only."""
    with ArtifactStore(tmp_path / "a.sqlite") as s:
        s.put(stage_key(), ArtifactStatus.COMPLETED, P)
        names = {p.name for p in tmp_path.iterdir()}
    assert names <= {"a.sqlite", "a.sqlite-wal", "a.sqlite-shm"} and "a.sqlite" in names


def test_new_store_pragmas(tmp_path: Path) -> None:
    """A new store is stamped user_version 1 and runs in WAL mode."""
    ArtifactStore(tmp_path / "a.sqlite").close()
    conn = sqlite3.connect(tmp_path / "a.sqlite")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    columns = [row[1] for row in conn.execute("PRAGMA table_info(stage_artifacts)")]
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(stage_artifacts)")}
    conn.close()
    assert columns == [
        "key",
        "key_schema",
        "geometry_hash",
        "stage_hash",
        "stage_kind",
        "engine",
        "engine_version",
        "status",
        "payload_json",
        "payload_sha256",
        "created_at_utc",
        "updated_at_utc",
    ]
    assert {"idx_stage_artifacts_geometry", "idx_stage_artifacts_kind_engine"} <= indexes


def test_reopen_existing_store(tmp_path: Path) -> None:
    """A version-1 file reopens and keeps its rows."""
    with ArtifactStore(tmp_path / "a.sqlite") as s:
        s.put(stage_key(), ArtifactStatus.COMPLETED, P)
    with ArtifactStore(tmp_path / "a.sqlite") as s:
        assert s.get(stage_key()) == P


def test_unknown_schema_version(tmp_path: Path) -> None:
    """A file with user_version 7 raises StoreSchemaError."""
    path = tmp_path / "a.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version=7")
    conn.close()
    with pytest.raises(StoreSchemaError, match="7"):
        ArtifactStore(path)


def test_completed_round_trip_and_idempotent_put(store: ArtifactStore) -> None:
    """Put/get round-trips; re-putting the same completed payload is a no-op."""
    k = stage_key()
    store.put(k, ArtifactStatus.COMPLETED, P)
    assert store.get(k) == P
    store.put(k, ArtifactStatus.COMPLETED, P)
    assert store.get(k) == P and store.status(k) == ArtifactStatus.COMPLETED


def test_completed_row_refuses_different_payload(store: ArtifactStore) -> None:
    """A different completed payload raises ArtifactConflictError and leaves the row unchanged."""
    k = stage_key()
    store.put(k, ArtifactStatus.COMPLETED, P)
    with pytest.raises(ArtifactConflictError):
        store.put(k, ArtifactStatus.COMPLETED, P2)
    assert store.get(k) == P


@pytest.mark.parametrize(
    "status", [ArtifactStatus.FAILED, ArtifactStatus.PENDING, ArtifactStatus.RUNNING]
)
def test_completed_row_refuses_status_change(store: ArtifactStore, status: ArtifactStatus) -> None:
    """Any non-completed write to a completed row raises, even with the same payload."""
    k = stage_key()
    store.put(k, ArtifactStatus.COMPLETED, P)
    with pytest.raises(ArtifactConflictError):
        store.put(k, status, P)
    assert store.get(k) == P and store.status(k) == ArtifactStatus.COMPLETED


def test_failed_then_completed(store: ArtifactStore) -> None:
    """A failed row hides its payload and may later complete."""
    k = stage_key()
    store.put(k, ArtifactStatus.FAILED, P)
    assert store.get(k) is None and store.status(k) == ArtifactStatus.FAILED
    store.put(k, ArtifactStatus.COMPLETED, P)
    assert store.get(k) == P


def test_pending_running_completed_lifecycle(store: ArtifactStore) -> None:
    """Pending and running rows update in place until completed."""
    k = stage_key()
    store.put(k, ArtifactStatus.PENDING, {})
    store.put(k, ArtifactStatus.RUNNING, {"step": 1})
    assert store.status(k) == ArtifactStatus.RUNNING and store.get(k) is None
    store.put(k, ArtifactStatus.COMPLETED, P2)
    assert store.get(k) == P2


def test_invalidate_allows_replacement(store: ArtifactStore) -> None:
    """Invalidate deletes a completed row, after which a new payload may be stored."""
    k = stage_key()
    store.put(k, ArtifactStatus.COMPLETED, P)
    assert store.invalidate(k) is True
    assert store.get(k) is None and store.status(k) is None
    store.put(k, ArtifactStatus.COMPLETED, P2)
    assert store.get(k) == P2
    assert store.invalidate(stage_key(method="B3LYP")) is False


def test_other_stage_misses_and_query_filters(store: ArtifactStore) -> None:
    """A different stage on the same geometry misses; query filters by kind and engine."""
    sp, freq = stage_key("single_point"), stage_key("frequency")
    store.put(freq, ArtifactStatus.COMPLETED, P)
    assert store.get(sp) is None
    store.put(sp, ArtifactStatus.PENDING, {})
    assert store.query(stage_kind="single_point") == [sp.key]
    assert store.query(stage_kind="frequency", engine="pyscf_gpu_cpu") == [freq.key]
    assert store.query(engine="mace") == []
    assert store.query() == sorted([sp.key, freq.key])


def test_nan_payload_rejected(store: ArtifactStore) -> None:
    """A payload containing NaN raises ValueError and writes nothing."""
    k = stage_key()
    with pytest.raises(ValueError):
        store.put(k, ArtifactStatus.COMPLETED, {"energy_eh": float("nan")})
    assert store.status(k) is None and store.query() == []


def test_unknown_status_rejected(store: ArtifactStore) -> None:
    """A status outside the enum raises ValueError and writes nothing."""
    with pytest.raises(ValueError):
        store.put(stage_key(), "done", P)  # type: ignore[arg-type]
    assert store.query() == []


def test_two_stores_two_threads(tmp_path: Path) -> None:
    """Two stores on one file, written from two threads, never hit 'database is locked'."""
    path = tmp_path / "a.sqlite"
    stores = [ArtifactStore(path), ArtifactStore(path)]
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def writer(index: int) -> None:
        """Write 50 artifacts through ``stores[index]``."""
        barrier.wait()
        try:
            for i in range(50):
                k = stage_key(method=f"M{index}-{i}")
                stores[index].put(k, ArtifactStatus.COMPLETED, {"i": i, "writer": index})
        except BaseException as exc:  # recorded and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert len(stores[0].query()) == 100
    for s in stores:
        s.close()
