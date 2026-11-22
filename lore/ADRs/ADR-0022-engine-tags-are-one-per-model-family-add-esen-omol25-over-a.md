Decision (resolve, v0.2.0 replan 1, R31; TJ 16:52Z "A - Ship it as a second model", with the lead's condition, accepted by TJ, that the engine tag be honest because it is in the cache key). This amends ADR-0001's frozen EngineTag set, which is still PROPOSED.

Engine tags are one per model family, and the set gains `esen_omol25`. A fairchem-based family gets its own tag over a shared private bridge module (`engines/_fairchem_bridge.py`):
- `uma_direct` accepts exactly `uma-s-1p2p1`;
- `esen_omol25` accepts exactly `esen-sm-conserving-all-omol` (facebook/OMol25 esen_sm_conserving_all.pt).

Direct-force checkpoints are refused by name and by the loaded config's direct-forces flag, because their forces are not -dE/dx. Other conserving checkpoints that TJ did not name, such as allscaip-md-conserving-all-omol, are refused. Identity stays per ADR-0017: `<model>@sha256:<hex>`.

Trade-off:
- Rejected: running eSEN under `uma_direct`. A result's tag would name a model that did not produce it, even though identity.model would differ.
- Rejected: one generic `fairchem` tag with model-qualified identity. It renames the plan's `uma_direct` module boundary and the v0.1.0 frozen tag.
- Rejected: model-qualified tags (`fairchem:<model>`). These break the Literal-typed tag contract.

Chosen: a small core Literal change (slice 03), with existing tags and keys unchanged. The cost is one tag per future model family.
