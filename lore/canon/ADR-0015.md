Decision (resolve, replan 10, R52; slice 09). Proposed to supersede ADR-0012, which is still PROPOSED and unapproved; the supersession itself is left to the lore approval gate.

ArtifactStore's open sequence runs under ONE wall-clock deadline, `open_timeout_s` (default 5.0 s):
1. validate the timeout;
2. check the path;
3. connect;
4. read user_version, and reject anything other than 0/1 before any write;
5. switch to WAL;
6. BEGIN IMMEDIATE, create or check the schema, COMMIT;
7. restore busy_timeout to 5000 ms for normal use.

Steps 4, 5 and 6 each run through one busy step:
- before each attempt it sets busy_timeout to the remaining milliseconds;
- it retries only on SQLITE_BUSY or SQLITE_LOCKED, with backoff starting at 5 ms, doubling, capped at 100 ms;
- when time runs out it raises StoreBusyError, chained to the last OperationalError.
Everything else propagates.

Why ADR-0012 was not enough. It bounded only the WAL switch, after a version read governed by a separate 5 s busy_timeout. The build seat measured this: under an EXCLUSIVE holder, the read blocked 5.007 s and then raised a raw OperationalError('database is locked'). That contradicted the contract that openers either succeed or fail only with StoreBusyError after a bounded wait.

Verified by resolve with SQLite 3.46.1:
- EXCLUSIVE or IMMEDIATE holder past the deadline → StoreBusyError at 0.300 s (timeout 0.3);
- holder released after 0.3 s → WAL open in about 0.33 s;
- barrier race at N = 2, 6, 16 → 0 errors in 300 trials;
- foreign user_version-7 file under an EXCLUSIVE holder → StoreBusyError, file unchanged.

Trade-off:
- Rejected: weakening the proof to an IMMEDIATE-only holder. A real EXCLUSIVE holder would still have leaked a raw error after 5 s.
- Rejected: catching all OperationalErrors. That hides real faults.
- Chosen: one deadline and one documented error class, at the cost of a slightly more complex open path.
