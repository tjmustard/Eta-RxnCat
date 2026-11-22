---
id: OPR.0.1.0.5
slice: 05-cli
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Implement the eta-rxncat console script with hardware-check [--smoke] and validate, a fixed exit-code table and one-line stderr errors."
depends_on: [OPR.0.1.0.2, OPR.0.1.0.4]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_cli
parent: null
hacf_touches: [src/eta_rxncat/cli.py, src/eta_rxncat/__main__.py, "tests/unit/cli/**", pyproject.toml, uv.lock, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/cli], [uv, run, eta-rxncat, validate, tests/data/reaction_graphs/example_reaction_graph.yaml]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Minimal CLI — hardware-check and validate

## Intent

Implement the `eta-rxncat` console script with `hardware-check [--smoke]` and `validate <path>`,
a fixed exit-code table and one-line stderr errors with no traceback.

Context the builder needs (self-contained): v0.1.0 ships only these two commands; v1.0.0
finalises the full CLI. The commands wrap two existing modules:
- `eta_rxncat.utils.hw_probe` (slice 04): `probe_hardware() -> HardwareReport`, `run_smoke() ->
  SmokeResult`, `smoke_exit_code(result) -> int` (pass 0, fail 1, skipped 3). Both are pydantic
  models, serialised with `model_dump_json(indent=2)`.
- `eta_rxncat.core` (slice 02): `load_reaction_graph(path: Path) -> ReactionGraph` raising
  `GraphValidationError` with a message naming the offender; `ReactionGraph.nodes`, `.edges`,
  `.priority_order() -> list[str]`.
The starter `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py` is **reference only** (it
lets `validate` raise a traceback). Node `eta_rxncat_cli` (depends_on `eta_rxncat_core`,
`eta_rxncat_hw_probe`) is **not yet in the graph**: register it with `hyper_ledger.py ensure-node
--from-spec <this SPEC.md> --dimension Module`.

## 1. The Confidence Mandate

**Score: 10/10.** Commands, outputs and exit codes are fully specified and deterministic.

## Mini-requirements

1. Console script in `pyproject.toml`: `[project.scripts] eta-rxncat = "eta_rxncat.cli:main"`;
   `src/eta_rxncat/__main__.py` calls `main()` so `python -m eta_rxncat` works. `main(argv:
   Sequence[str] | None = None) -> int` built on stdlib `argparse` (no new dependency);
   `raise SystemExit(main())` only in `__main__`/the entry point.
2. US-003 `eta-rxncat hardware-check`: prints `probe_hardware().model_dump_json(indent=2)` to
   stdout, exit 0 (flags are inside the JSON).
3. US-004a `eta-rxncat hardware-check --smoke`: prints `run_smoke().model_dump_json(indent=2)` to
   stdout and exits `smoke_exit_code(result)` (0 pass, 1 fail, 3 skipped).
4. US-007 `eta-rxncat validate <path>`: on success prints exactly four lines to stdout —
   `OK <path as given>`, `nodes: <N>`, `edges: <M>`, `priority_order: <id>,<id>,…` — exit 0. On
   `GraphValidationError` (including missing file and unsupported extension): stderr is exactly
   one line `error: <message>`, stdout empty, exit 1, no traceback.
5. Usage errors (unknown command, missing argument) → argparse's message, exit 2.
6. `validate` never imports `torch`, `pyscf`, `gpu4pyscf`, `cupy`, `rdkit`, `mace`, `fairchem`
   (the CLI imports `hw_probe` functions lazily inside the `hardware-check` handler, or `hw_probe`
   itself imports them lazily).
7. US-011 (CLI area): `docs/prd/v0.1.0/DISCREPANCIES.md` `## CLI` gains a row for each starter
   subcommand, argument, output and exit behaviour, plus `added` rows (exit table, `__main__`,
   `--smoke`). Status `open`.

## 3. Implementation Plan (Task List)

- [ ] Task 1 — `cli.py`: parser with subcommands `hardware-check` (`--smoke` flag) and `validate`
  (`path`, `type=Path`); handlers return an int.
- [ ] Task 2 — `__main__.py`; `[project.scripts]` entry; `uv sync` so the script exists.
- [ ] Task 3 — Tests under `tests/unit/cli/`: call `main([...])` with `capsys`, and one subprocess
  test of the installed `eta-rxncat` script; write invalid graphs to `tmp_path` (never to
  `tests/fixtures/`).
- [ ] Task 4 — Register rows; four gates exit 0.

## 4. The Negative Space (Constraints)

- **DO NOT** add `typer`, `click` or any other dependency.
- **DO NOT** add commands beyond `hardware-check` and `validate`, or import `eta_rxncat.store`.
- **DO NOT** print a traceback for an invalid graph; **DO NOT** catch bare `Exception` to hide
  programming errors — catch `GraphValidationError` only.
- **DO NOT** call `sys.exit` inside `main`; return the code.
- **DO NOT** write to `tests/fixtures/`.

## Proof contract

- [ ] `uv run eta-rxncat validate tests/data/reaction_graphs/example_reaction_graph.yaml` → exit 0; stdout is exactly the four lines with the fixture's counts and priority order.
- [ ] `validate` on each of: duplicate node id, unknown edge endpoint, self-loop, duplicate edge, unknown pruning-rule ref, duplicate YAML key, `graph.toml`, missing file → exit 1, stdout empty, stderr exactly one line starting `error: ` that contains the offender, and no `Traceback`.
- [ ] `uv run eta-rxncat hardware-check` → exit 0, stdout parses as JSON with `report_schema == 1`.
- [ ] `uv run eta-rxncat hardware-check --smoke` on this environment (no torch) → exit 3, JSON `status == "skipped"`.
- [ ] `main(["hardware-check","--smoke"])` with `run_smoke` monkeypatched to pass / fail → 0 / 1.
- [ ] `uv run eta-rxncat` (no command) and `uv run eta-rxncat frobnicate` → exit 2.
- [ ] `uv run python -m eta_rxncat validate <fixture>` → exit 0.
- [ ] Subprocess test: after `main(["validate", <fixture>])`, none of `torch`, `pyscf`, `gpu4pyscf`, `cupy`, `rdkit` is in `sys.modules`.
- [ ] Four gates exit 0; DISCREPANCIES.md has a row for every CLI starter item.

## Source material

- `PRDs/Eta-RxnCat_Living_Master_Plan.md` (v1.0.0 PR #17 names the eventual CLI; v0.1.0 needs only these two).
- `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/src/eta_rxncat/cli.py` (reference only).
- Mission `missions/release-0.1.0/SPEC.md` §5 Contracts (CLI) and trade-off log R21.

## Intent visual

N/A — non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.2 (core loader), OPR.0.1.0.4 (hardware probe)
