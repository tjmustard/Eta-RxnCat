Decision (resolve, v0.2.0, R6/R7; Red Team F6, F7). The cache key's stage is each engine's resolved stage. `Engine.from_stage(stage)` returns an engine whose `.stage` is a new StageConfig:
- every keyed option is filled with its default;
- the solvent name is normalised (lowercase);
- `engine_impl` (an int per engine, starting at 1) is added.
Keys are `build_stage_key(state, engine.stage, engine.identity)`.

Options are split by whether they change the result:
- keyed: options that change the result live in `StageConfig.options`, declared per engine;
- runtime: threads, timeouts, device preference and paths are constructor arguments and are never keyed;
- unknown keys raise EngineInputError.

Trade-off: implicit defaults inside engines were rejected. They make keys miss when a default changes, and collide when an implementation changes. Keying runtime knobs was rejected because they cause spurious misses. `engine_impl` is the explicit invalidation handle for behaviour changes in eta_rxncat's own engine code.
