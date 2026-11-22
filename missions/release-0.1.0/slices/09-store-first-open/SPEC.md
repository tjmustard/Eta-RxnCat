---
id: OPR.0.1.0.9
slice: 09-store-first-open
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Make ArtifactStore safe to open concurrently on a new file (version check before any write, then a bounded WAL-switch retry that succeeds or raises StoreBusyError) and reject unsupported user_version files without modifying them."
depends_on: [OPR.0.1.0.3]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: blocked
node_id: eta_rxncat_store
parent: null
hacf_touches: ["src/eta_rxncat/store/**", tests/unit/store/test_first_open.py, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/store]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Artifact store — safe concurrent first open and non-mutating schema rejection

## Intent

Make `ArtifactStore.__init__` safe in two cases:
- When N instances open a **new** store file at the same moment, every one succeeds, or fails only
  with a documented error after a bounded retry.
- A file whose `user_version` this store does not support is rejected **without being modified**.

Context the builder needs (self-contained). Slice 03 (audited PASS, do not re-open its spec)
built `eta_rxncat.store`. `ArtifactStore(path)` currently does the following, in this order:
1. connects with `timeout=5.0`;
2. runs `PRAGMA busy_timeout=5000`;
3. runs `PRAGMA journal_mode=WAL`;
4. runs `_init_schema()`, which reads `user_version`, creates the schema under `BEGIN IMMEDIATE`
   when it is 0, and raises `StoreSchemaError` unless it is 1.

The audit found two defects outside slice 03's contract (row `qitem-20261122132213-82a94145`,
probe `~/.hacf/eta-rxncat-hacf/evidence/store-first-open-probe03b.py`):
1. Concurrent first open of a new file intermittently raises `sqlite3.OperationalError: database
   is locked` at `PRAGMA journal_mode=WAL`. SQLite does not apply `busy_timeout` to the
   journal-mode switch. It failed 3/30 trials with 2 openers and 4/30 with 6; existing files failed
   0/60. v0.8.0's parallel workers will open stores concurrently.
2. A foreign file with `user_version` 7 is converted to WAL before it is rejected.

The lead decided to fix this in v0.1.0. Node `eta_rxncat_store` already exists (slice 03), and
this slice changes only files it owns. Run `hyper_ledger.py ensure-node --from-spec <this SPEC.md>
--dimension Module` only to add this slice's `spec_refs`. Never hand-edit `architecture.yml`.

## 1. The Confidence Mandate

**Score: 9/10.** The order, the retry rule, the error type and the proofs are fixed. A
deterministic lock-holding test proves the retry path, and a heavily repeated race test proves the
real race. The residual is that a race test can only show absence across many trials; the
deterministic test carries the proof of the mechanism.

## Mini-requirements

1. New open order in `ArtifactStore.__init__`, replacing slice 03's order. Replan R52: **one deadline
   for the whole open**.
   1. Validate `open_timeout_s` (> 0, else `ValueError`, before anything else).
      `deadline = time.monotonic() + open_timeout_s`.
   2. Path check, unchanged (`FileNotFoundError` if `path.parent` is missing, nothing created).
   3. Connect (`sqlite3.connect(path, timeout=open_timeout_s, isolation_level=None, …)`).
   4. Read `PRAGMA user_version` through the busy step (Mini-requirement 2). If it is not 0 and
      not 1, close and raise `StoreSchemaError` **before any statement that writes**.
   5. `PRAGMA journal_mode=WAL` through the busy step. A returned mode other than `"wal"` raises
      `StoreSchemaError`.
   6. `_init_schema()`: `BEGIN IMMEDIATE` through the busy step. Then, if `user_version` is still
      0, create the schema and set it to 1, and `COMMIT`. Finally re-check that it equals 1.
   7. After a successful open, set `PRAGMA busy_timeout=5000` for normal operation (`put`/`get`/…
      keep slice 03's behaviour).
   
   On any exception, close the connection (as now).
2. The busy step (private helper, e.g. `_busy_step(conn, sql, deadline)`) is the only place an
   `OperationalError` is caught.
   - Before each attempt, set `PRAGMA busy_timeout = max(1, int(remaining_ms))`, where
     `remaining = deadline − time.monotonic()`. A step that blocks inside SQLite (e.g. the
     version read under an EXCLUSIVE holder) therefore can never wait past the deadline.
   - Run the statement. On `sqlite3.OperationalError` whose `sqlite_errorcode` is
     `sqlite3.SQLITE_BUSY` or `sqlite3.SQLITE_LOCKED`:
     - if time remains, sleep `min(delay, remaining)` and retry. `delay` starts at 0.005 s,
       doubles, and is capped at 0.1 s.
     - otherwise raise `StoreBusyError`. Its message names the path and the elapsed seconds, and
       it chains the last `OperationalError` (`raise … from`).
   - Any other `OperationalError` propagates unchanged, without a retry.
   - **Contract:** any BUSY/LOCKED condition during open, whether in the version read, the WAL
     switch or the schema transaction, and whether the other holder took a RESERVED, IMMEDIATE or
     EXCLUSIVE lock, surfaces only as `StoreBusyError`, after at most `open_timeout_s` plus one
     backoff step (≤ 0.1 s) plus statement overhead. A raw `OperationalError('database is
     locked')` never escapes `__init__`.
   
   Resolve prototyped this on this host (SQLite 3.46.1), under TMPDIR:
   - an EXCLUSIVE holder for 3 s with `open_timeout_s=0.3` → `StoreBusyError` after 0.300 s;
   - an IMMEDIATE holder, same timing → `StoreBusyError` after 0.300 s;
   - holders released after 0.3 s with a 5 s timeout → opened in WAL at about 0.33–0.36 s;
   - the barrier race at N = 2, 6, 16 → 0 errors in 300 trials.
3. API additions, both exported from `eta_rxncat.store`:
   - `ArtifactStore(path: Path, *, open_timeout_s: float = 5.0)`. It must be `> 0`, else
     `ValueError`.
   - `class StoreBusyError(Exception)`.
   
   Update the `__init__` docstring's `Raises:` section with `StoreBusyError`. Nothing else in
   the store's public API changes. `put`/`get`/`invalidate`/`query`/`status` are untouched.
4. No other mechanism. No lock files or sidecar files, and no change to `put` semantics or schema.
   Do not catch `OperationalError` anywhere outside the busy step, and use the busy step only
   during `__init__`.
5. US-011 (store area): `docs/prd/v0.1.0/DISCREPANCIES.md` `## Store` gains `added` rows for
   `StoreBusyError` and `open_timeout_s`, each with status `open`.

## 3. Implementation Plan (Task List)

- [ ] Task 1 — Reorder `__init__` (Mini-requirement 1), with the private busy-step helper
  (Mini-requirement 2) used for the version read, the WAL switch and `BEGIN IMMEDIATE`.
- [x] Task 2 — Add `StoreBusyError` and `open_timeout_s`, export them, and update docstrings.
- [ ] Task 3 — Tests in `tests/unit/store/test_first_open.py` (one per Proof contract bullet),
  using `tmp_path` and threads. Keep slice 03's tests unchanged and passing.
- [x] Task 4 — Run the audit probe (unchanged) and paste its output in your handoff.
- [x] Task 5 — Register rows; four gates exit 0.

## 4. The Negative Space (Constraints)

- **DO NOT** edit slice 03's SPEC, proof or tests (slice 03 is audited PASS). Changing
  `artifact_store.py` and `__init__.py` is this slice's job.
- **DO NOT** retry anything outside the open sequence's three busy steps, and never retry or block past the one `open_timeout_s` deadline.
- **DO NOT** write to a file before its `user_version` is known to be 0 or 1.
- **DO NOT** create any file other than `path` and SQLite's own `-wal`/`-shm` siblings.
- **DO NOT** swallow errors: any failure other than BUSY/LOCKED propagates unchanged.
- **DO NOT** import anything new beyond the stdlib (`time` is enough).
- **DO NOT** touch slices 04–08 or their files.

## Proof contract

- [ ] Race, repeated: for each N in (2, 6, 16), 100 trials. Each trial uses a fresh `tmp_path`
  file; N threads wait on one `threading.Barrier(N)`, then each opens `ArtifactStore(p)` and closes
  it. The expected result is **0 errors in 300 trials**. Afterwards, `PRAGMA user_version` is 1 and
  `PRAGMA journal_mode` is `wal` on each file.
- [ ] Retry path, deterministic, run **twice**: once with the holder using `BEGIN EXCLUSIVE`,
  once with `BEGIN IMMEDIATE` (parametrized).
  - A raw `sqlite3` connection makes a fresh file (rollback journal), runs the BEGIN and holds
    the lock.
  - `ArtifactStore(p, open_timeout_s=5.0)` starts in a thread.
  - The holder commits after 0.3 s.
  - Expected: the store opens without error, takes ≥ 0.3 s, and the file ends with
    `user_version` 1 and WAL.
- [ ] Deadline, deterministic, run **twice** (EXCLUSIVE and IMMEDIATE holders, each keeping the
  lock for the whole test). `ArtifactStore(p, open_timeout_s=0.3)` raises `StoreBusyError`, never
  a raw `OperationalError`. It raises within [0.3 s, 1.0 s], `__cause__` is an
  `sqlite3.OperationalError`, and the message contains the path.
- [ ] After a successful open, `PRAGMA busy_timeout` on the store's connection is `5000`.
- [ ] Foreign file untouched:
  - A raw `sqlite3` file is made with a table, `PRAGMA user_version=7` and the default journal
    mode, and its connection is closed.
  - Record its sha256 and the set of sibling file names, then call `ArtifactStore(p)`.
  - Expected: `StoreSchemaError`; the file's sha256 is unchanged; `PRAGMA journal_mode` (raw
    connection) is still `delete`; no `-wal`/`-shm` sibling exists.
  - `user_version` 2 behaves the same way.
  - Foreign file under an EXCLUSIVE holder: `ArtifactStore(p, open_timeout_s=0.3)` raises
    `StoreBusyError`, and after the holder releases, the file's sha256, its journal mode
    (`delete`) and its siblings are unchanged.
- [ ] `open_timeout_s=0` and `-1` → `ValueError`, and no file is created.
- [ ] Existing valid store (`user_version` 1, WAL) opens unchanged. Slice 03's tests all pass
  unmodified.
- [ ] The audit probe `~/.hacf/eta-rxncat-hacf/evidence/store-first-open-probe03b.py`, run as
  `uv run python <probe>` from the repo root, prints `0 errors` on all four lines.
- [ ] Four gates exit 0; the register rows from Mini-requirement 5 exist.

## Source material

- Audit finding on slice 03, row `qitem-20261122132213-82a94145` (quoted above), and its probe.
- `missions/release-0.1.0/slices/03-artifact-store/SPEC.md` and `proof/01-qa.md` (context only).
- ADR-0002 (store immutability, WAL, `user_version`); ADR-0012 (first amendment, PROPOSED); ADR-0015 (one-deadline open, PROPOSED to supersede ADR-0012).
- Mission `missions/release-0.1.0/SPEC.md` §5 Store contract and trade-off log R7, R42, R52.
- SQLite: `busy_timeout` is not honoured by the `journal_mode` change (the audit observed this).

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.3 (artifact store)
