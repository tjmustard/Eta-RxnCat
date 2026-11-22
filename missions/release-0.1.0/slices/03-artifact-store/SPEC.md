---
id: OPR.0.1.0.3
slice: 03-artifact-store
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the canonical versioned per-stage cache key and a WAL-mode SQLite artifact store whose completed artifacts are never silently overwritten."
depends_on: [OPR.0.1.0.2]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_store
parent: null
hacf_touches: ["src/eta_rxncat/store/**", "tests/unit/store/**", docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/store]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Canonical stage cache key and SQLite artifact store

## Intent

Implement `eta_rxncat.store`: a canonical, versioned (`key_schema = 1`) per-stage cache key built
from a `MolecularState`, a `StageConfig` and an `EngineIdentity`, and a WAL-mode SQLite
`ArtifactStore` whose completed artifacts can never be silently overwritten.

Context the builder needs (self-contained): the plan's Hypothesis 4 rests on stage-decomposed,
content-addressed caching — a crashed run resumes from completed stages, and adding a solvation
single point reuses completed gas-phase optimizations. A wrong cache hit is a silent scientific
error, so the key must include everything that changes a stage's result and nothing that does not.
Models come from `eta_rxncat.core` (slice 02): `MolecularState(symbols, coordinates, charge,
spin_multiplicity, active_atom_indices, metadata)`, `StageConfig(kind, engine, method, basis,
solvation(model, solvent, dielectric), frozen_atom_indices, options)`, `EngineIdentity(name,
version, model)`. The starter `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/` is
**reference only**: its `INSERT OR REPLACE` and `sha256(model_dump())` are exactly what this slice
replaces. Node `eta_rxncat_store` (depends_on `eta_rxncat_core`) is **not yet in the graph**:
register it with `hyper_ledger.py ensure-node --from-spec <this SPEC.md> --dimension Module`.

## 1. The Confidence Mandate

**Score: 9/10.** Key payload, hashing, schema, pragmas and write rules are fully specified.
Residual: payload size for future Hessians (sidecar blobs) is deliberately deferred; this slice
stores canonical JSON text.

## Mini-requirements

1. US-009 key (`store/keys.py` or similar). `canon(obj) = json.dumps(obj, sort_keys=True,
   separators=(",", ":"), ensure_ascii=True, allow_nan=False)`; `h(obj) = sha256(canon(obj)
   .encode("ascii")).hexdigest()`. `KEY_SCHEMA: Final = 1`.
   - `geometry_payload(state)` = `{"symbols": [...], "coordinates": [[s, s, s], ...],
     "charge": int, "spin_multiplicity": int, "active_atom_indices": sorted}` where each coordinate
     is `v = round(x, 5)`; `if v == 0.0: v = 0.0` (drops `-0.0`); `s = f"{v:.5f}"`.
   - `stage_payload(stage, engine)` = `{"kind", "engine", "method", "basis", "solvation":
     {"model", "solvent", "dielectric"}, "frozen_atom_indices": sorted, "options": {...},
     "engine_identity": {"name", "version", "model"}}`; a float with `v.is_integer()` in `options`
     or `dielectric` is written as `int(v)`; bools stay bools.
   - `StageKey` (frozen model or dataclass) with `key_schema`, `geometry_hash =
     h(geometry_payload)`, `stage_hash = h(stage_payload)`, `key = h({"key_schema": 1,
     "geometry_hash": …, "stage_hash": …})`, `stage_kind`, `engine`, `engine_version`; built by
     `build_stage_key(state, stage, engine: EngineIdentity) -> StageKey`. `metadata` is not keyed.
     Raise `ValueError` if `engine.name != stage.engine`.
2. US-009a store (`store/artifact_store.py` or similar). `ArtifactStore(path: Path)`; `path` is
   the SQLite file; if `path.parent` does not exist → `FileNotFoundError`; nothing else is created.
   On open: `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`; `user_version` 0 on a new file →
   create schema and set 1; 1 → ok; anything else → `StoreSchemaError`. Schema:
   `stage_artifacts(key TEXT PRIMARY KEY, key_schema INTEGER NOT NULL, geometry_hash TEXT NOT NULL,
   stage_hash TEXT NOT NULL, stage_kind TEXT NOT NULL, engine TEXT NOT NULL, engine_version TEXT
   NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
   payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, created_at_utc TEXT NOT NULL,
   updated_at_utc TEXT NOT NULL)`; indexes on `geometry_hash` and `(stage_kind, engine)`.
3. Write rules: `put(key: StageKey, status: ArtifactStatus, payload: Mapping[str, object]) -> None`
   with `payload_json = canon(payload)`. New key → insert. Existing row not `completed` → update
   (status, payload, `updated_at_utc`). Existing `completed` row and the call is `status=completed`
   with the same `payload_sha256` → no-op. Any other write to a `completed` row →
   `ArtifactConflictError`, row unchanged. `invalidate(key) -> bool` deletes the row (True if one
   existed). `get(key) -> dict | None` returns the decoded payload only when `completed`.
   `status(key) -> ArtifactStatus | None`. `query(stage_kind: str | None = None, engine: str |
   None = None) -> list[str]` returns keys, sorted. Each write is one transaction
   (`BEGIN IMMEDIATE`).
4. US-011 (store area): `docs/prd/v0.1.0/DISCREPANCIES.md` `## Store` gains a row for every public
   name, field and method of the starter `store/*.py`, every starter SQL table, column and index,
   and `added` rows for every new column, method and error type. Known `changed` rows: key
   composition (`sha256(model_dump())` → canonical payload, R5/R6); `INSERT OR REPLACE` → immutable
   completed rows (R7); default path `.eta_cache/artifacts.sqlite` + `mkdir` → required path, no
   mkdir (R7). Status `open`.

## 3. Implementation Plan (Task List)

- [ ] Task 1 — `canon`, `h`, coordinate and option canonicalisation helpers (pure functions).
- [ ] Task 2 — `geometry_payload`, `stage_payload`, `StageKey`, `build_stage_key`.
- [ ] Task 3 — `ArtifactStatus` (`StrEnum`), `ArtifactConflictError`, `StoreSchemaError`.
- [ ] Task 4 — `ArtifactStore.__init__` (path check, pragmas, schema/user_version).
- [ ] Task 5 — `put`, `get`, `status`, `invalidate`, `query`, `close`/context manager.
- [ ] Task 6 — Tests under `tests/unit/store/` (one per Proof contract bullet), using `tmp_path`.
- [ ] Task 7 — Register rows (Mini-requirement 4).
- [ ] Task 8 — Four gates exit 0.

## 4. The Negative Space (Constraints)

- **DO NOT** hash `model_dump()`/`model_dump_json()` output directly; build the payloads field by field.
- **DO NOT** bundle multiple stages into one key.
- **DO NOT** use `INSERT OR REPLACE` or any path that overwrites a `completed` row except `invalidate`.
- **DO NOT** create directories or any file other than `path` (WAL `-wal`/`-shm` siblings are SQLite's own and allowed).
- **DO NOT** default the store path.
- **DO NOT** import from `eta_rxncat.utils`, `eta_rxncat.cli` or any engine library; `store` imports `eta_rxncat.core` and the stdlib only.
- **DO NOT** use `pickle`; payloads are JSON only (`allow_nan=False`).
- **DO NOT** implement crash-resume orchestration (v0.8.0); the store only stores.

## Proof contract

- [ ] Same state + stage + engine twice → identical `key`; a golden test pins the hex `key` for one fixed H₂O input, and recomputes it in the test from `canon`/`hashlib` directly.
- [ ] Coordinates `0.123454` vs `0.1234549` (same 5-decimal grid value) → same key; `0.12345` vs `0.12346` → different key; coordinate `-1e-6` vs `0.0` → same key.
- [ ] Changing each of charge, spin_multiplicity, one symbol, active_atom_indices, kind, engine (with matching identity), method, basis, solvation model, solvent, dielectric, frozen_atom_indices, an option value, engine version, engine model → different key (one assertion each).
- [ ] Changing only `metadata` → same key; options `{"x": 1}` vs `{"x": 1.0}` → same key; `{"x": True}` vs `{"x": 1}` → different key.
- [ ] `build_stage_key` with `engine.name != stage.engine` → `ValueError`.
- [ ] `ArtifactStore(tmp_path / "missing" / "a.sqlite")` → `FileNotFoundError`, and `tmp_path / "missing"` still does not exist.
- [ ] New store: `PRAGMA user_version` = 1, `PRAGMA journal_mode` = `wal`; a file with `user_version` 7 → `StoreSchemaError`.
- [ ] `put(k, completed, p)` then `get(k)` == `p`; `put(k, completed, p)` again → no error, row unchanged; `put(k, completed, p2)` → `ArtifactConflictError` and `get(k) == p`; `put(k, failed, p)` on the completed row → `ArtifactConflictError`.
- [ ] `put(k, failed, p)` then `get(k)` → `None`; then `put(k, completed, p)` → `get(k) == p` (failed → completed allowed).
- [ ] `invalidate(k)` → `True`, `get(k)` → `None`, `put(k, completed, p2)` → ok.
- [ ] A different stage on the same geometry → `get` misses; `query(stage_kind="single_point")` lists only matching keys.
- [ ] Two `ArtifactStore` instances on one file, alternating writes from two threads (50 puts each) → no `database is locked`, 100 rows.
- [ ] `put` with a payload containing `float("nan")` → `ValueError`, nothing written.
- [ ] Four gates exit 0; DISCREPANCIES.md has a row for every store starter item.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (Hypothesis 4; Module Boundary `store/`).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/store/{artifact_store,__init__}.py` (reference only).
- Mission `missions/release-0.1.0/SPEC.md` §5 Contracts (Cache key, Store) and trade-off log R5, R6, R7, R22, R25.

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.2 (core models)
