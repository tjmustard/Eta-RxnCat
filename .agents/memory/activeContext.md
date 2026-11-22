# Active Context

## Purpose
The "Now" of this project: what was just done, what is in progress, and any blockers or open questions.

## Usage
Agents read this file first to see where to pick up, and update it after each task.

## Current Sprint Goal
- [x] v0.1.0 foundation (mission `missions/release-0.1.0`, OPR.0.1.0): built, audited and
  accepted on this host on 2026-11-22. Next: v0.2.0 (potentials and engines), from
  `PRDs/Eta-RxnCat_Living_Master_Plan.md`.

## Session State
Updated 2026-11-22.
- Branch `feature/eta-rxncat-v0.1.0`, cut from `95734f7`. Not pushed, tagged or released.
- `v0.1.0` covers: strict Pydantic core models (`eta_rxncat.core`), the reaction-graph loader and
  validator, the stage cache key and SQLite artifact store (`eta_rxncat.store`), the hardware
  probe and GPU smoke test (`eta_rxncat.utils.hw_probe`), the CLI (`validate`, `hardware-check
  [--smoke]`), the optional extras `gpu`, `mlip-mace` and `mlip-uma` (mutually exclusive), the
  licence gate (`tools/licence_gate.py`), and the README, CHANGELOG and size-named WebP media.
  There is no engine code yet; `conformers/`, `engines/`, `mapping/`, `optimize/` and
  `orchestrator/` hold only a docstring.
- GPU acceptance passed on the RTX 5060 Ti at `ff3991e`:
  `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` (|ΔE| 9.95e-13 Eh, tolerance 1e-6).
- Gates (see `AGENTS.md`, "Required checks"): ruff check, ruff format, mypy, pytest and the
  `base` licence gate. CI also gates each extra.

## Recent Decisions
- Licence policy (TJ, 2026-11-22 14:57Z): the core (`src/eta_rxncat/` and the core install) is
  MIT/BSD or equivalent only and never imports `ase`. Copyleft engines (DFT, MLIP, conformer
  search) are allowed only behind the engine interface as optional extras or subprocesses,
  because they can be replaced. `ase` coming in through the MACE extra is fine (14:59Z).
- The `geometric` 1.1.1 licence-gate exception is narrow and documented (ADR-0011).
- Author form everywhere: "Thomas J. L. Mustard Ph.D." (`tests/unit/test_identity.py`).
- `PRDs/` is read-only. The living master plan in `PRDs/` governs over the copies in the zips.
- ADR-0001 to ADR-0015 are PROPOSED, not approved. ADR-0015 would supersede ADR-0012 and waits
  for TJ's lore approval.

## Next Steps
- Start the v0.2.0 architect stage once TJ has been told v0.1.0 is done.
- Carried forward, not v0.1.0 scope:
  - the store accepts `open_timeout_s=inf` and then hits `OverflowError`; reject non-finite
    values when the store is next touched;
  - opening an existing store waits behind an active writer (`BEGIN IMMEDIATE`), which matters
    for the v0.8.0 parallel workers;
  - licence-gate edge cases, and mapping "BSD License" to BSD-3-Clause;
  - CI disk space for the cu128 wheels.

## Field Notes (legacy)
`hyper_lore.py note --legacy` appends field notes below this line.
