Decision (resolve, replan 5, R42; amends ADR-0002; audit finding on slice 03, row qitem-20261122132213-82a94145). ArtifactStore opens a file in this order:
1. check the path;
2. connect;
3. set busy_timeout;
4. read user_version, and reject anything but 0 or 1 before any write;
5. switch to WAL with a bounded retry;
6. create or check the schema.

SQLite does not apply busy_timeout to the journal-mode switch, so concurrent first opens of a new file could raise "database is locked". The switch is retried on SQLITE_BUSY or SQLITE_LOCKED with exponential backoff (5 ms, doubling, capped at 100 ms) until `open_timeout_s` (default 5.0 s) has passed. After that it raises StoreBusyError, chained to the last OperationalError.

Trade-off:
- Rejected: an external lock file. It would break "create no file other than path".
- Rejected: failing fast. Openers would have to retry themselves.
- Rejected: creating the file in WAL from a single designated opener. That needs coordination the store cannot assume.

Chosen: a bounded retry inside the store. Callers see either success or one documented error. A foreign or too-new file is never modified.
