## Context

TJ's Phase 3 audit needs every optimization's path (v0.7.0 Q-A3). eta's stage keys (ADR-0016) are
the cache contract, and geomeTRIC is a black box run in-process (ADR-0024). The clean room forbids
reading its source. geomeTRIC writes mode files (`HT.v_*.txt`) into the process cwd: 14 landed in
the repo root during the v0.6.0 verdict. ADR-0053 said a v0.6.0 reader refuses every v0.7.0 row.
A probe measured less: on a v0.7.0 replan-7 store copy, a v0.6.0 reader refused 87 of 87
successful `ts_opt` rows, because `TSStep` gained `coordinates_angstrom`, while its geometry_opt
rebuild picks known payload keys. TJ chose to narrow the claim to what was proved (v0.7.1 R45).

## Decision

- **Payload-only frames.** Optimization frames are additive, optional payload fields. `TSStep`
  gains `coordinates_angstrom` (eta's own P-RFO, every step). geomeTRIC runs gain
  `OptimizationFrame`s captured at eta's own `Bridge.calc_new` hook after each evaluation, in
  success **and** failure rows (a timed-out or failed pre-relax keeps its path). Accepted steps are
  labelled only from geomeTRIC's output file (`xyzout`); otherwise the list is labelled as engine
  evaluations including trial points.
- **Keys unchanged.** Stage keys are unchanged, and frames never alter a result.
- **Forward-only stores, as measured.** A v0.6.0 reader refuses v0.7.0 transition-state search
  (`ts_opt`) rows. Nothing is claimed for other v0.7.0 rows read by v0.6.0, so a v0.7.0 store is
  not supported under v0.6.0. A v0.6.0 row read by v0.7.0 shows "no trajectory stored".
- **Temp cwd.** Each geomeTRIC call runs with a per-run temporary directory as cwd, restored in
  `finally` under a lock.

## Consequences

- No recomputation and no cache invalidation. The cost is store size, which is measured and
  decimated in the run-data, never in the store.
- Using a v0.7.0 store under v0.6.0 is unsupported, and its TS-search rows fail loudly. The v0.7.0
  Phase 3 bundle gates that every trajectory has frames, so a reused old store cannot pass it.
- The repo and any caller's cwd stay clean of geomeTRIC files.
- Supersedes ADR-0053, whose reader claim was wider than its evidence.
