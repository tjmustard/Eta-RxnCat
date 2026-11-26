---
slice: OPR.0.7.0.15
candidate_sha: 54e7e66
artifact_type: guard
verdict: CLEAR
money_evidence: sample 6 clash (4,21) 0.438 A ratio 0.409, member None; old
  fixtures byte-equal; ruff/mypy exit 0; full pytest 2642 passed
---


# Execute evidence: 15-seed-geometry-checks (OPR.0.7.0.15) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute`/`evidence` type.
This is builder evidence; the audit writes the QA verdict.

Start `493f40c`. Code commit `54e7e66`. No engine or GPU run, no store write, no `review/`,
`tests/e2e/` or fixture change (`git diff 493f40c 54e7e66 --stat` over those paths,
`orchestrator/__init__.py`, `test_ts_ensemble.py` and `test_ts_ensemble_guards.py` is empty).

## Known-answer clash numbers

`find_clash(start, perceive_bonds(TS1a_n__ethyl graft output) + [(1,2),(3,5)])`:

| geometry | result | sha256 of the XYZ |
|---|---|---|
| `v070_sample6_start.xyz` | clash, pair (4, 21), 0.438033 A, ratio 0.409376 | `c17a9133...0992183`, see below |
| `v070_member1_start.xyz` | `None` | `7788453d...16adc16` |

Full sha256: sample 6 `c17a91333b1daca851283c20fdbbe56939ff24516a56f1242dae78a040992183`;
member `7788453dd854aa95c83e72584448d19761cca3324c5ca2d98014d7d6a28adc16`.

Provenance: frame 0 (`coordinates_angstrom`) of `constrained_preopt` rows
`c50bc2b4e5cae37adb63adb30f4233588ecb8630af3690359fea0d9429beb1cc` (sample 6) and
`1e060de0dcbcc4d4411a53e8a4b0ccf6c0089713b612d3eef1a89b440641221e` (member), read with sqlite
`mode=ro` from `~/.hacf/eta-rxncat-hacf/evidence/v070-slice11/v070_enum.sqlite` (both rows also
exist in the two slice-12 xtb fallback stores). For both, eta's geometry hash of the frame equals
the row's `geometry_hash`. Symbols, charge and multiplicity come from the fixture
`v070_enum_ethyl_endo_xtb.runrecord.json`, species `TS1a_n__ethyl`. Coordinates are written with
10 decimals. Script: `~/.cache/eta-rxncat-tmp/s15_xyz.py` (removed after use).

## Fake-engine tests (`tests/unit/orchestrator/test_ts_fallback_seed_checks.py`, 19 passed)

| check | reason | detail asserted | calls asserted |
|---|---|---|---|
| clashing sample | `seed_clash`, no wall time | pair holds the moved H | pre-relax 0, TS searches 1 (seed), pre-relax rows 0 |
| clash, 20 samples | only index 1 excluded | - | pre-relax 19; indices 2-20 merge (slot kept) |
| pre-relax makes/breaks a bond | `bond_changed:pre_relax` | exact formed and broken lists | pre-relax 1, TS searches 1 (seed only) |
| TS makes/breaks a bond | `bond_changed:ts` | formed non-empty | gates judged the seed only |
| seed TS changes a bond | `seed:bond_changed:ts` | `failed_detail` both lists | pre-relax 0 |
| fallback, close contact 1, one template | `seed:seed_clash`, wall 0.0 | count 1 | pre-relax 0, engine 0 |
| fallback, close contact on rank 1 | falls through, rank 2 chosen | - | - |
| fallback pre-relax bond change | `seed:bond_changed:pre_relax`, rank 2 chosen | both lists | - |
| fallback seed TS bond change | `seed:bond_changed:ts`, rank 2 chosen | carried from `failed_detail` | - |
| `seed_checks=False` | `connectivity_changed` as before | no `detail` key | pre-relax 1 |

Also: the fallback passes `seed_checks=True`; `run_ts_ensemble` passes the keyword; only pairs
>= 3 bonds apart or unconnected are judged; forming pairs are ignored on both sides;
`SEED_CLASH_FACTOR is mapping.graft.CONTACT_FACTOR`. The allow-list test is extended in
`test_ts_fallback.py` (5 cases).

## Core and old records (`tests/unit/core/test_seed_check_models.py`, 10 passed)

- New reasons accepted, other spellings refused; `None` details omitted in `model_dump` and
  `model_dump_json`; set details round-trip.
- Byte equality, v0.6.0 and v0.7.0 fixtures: `*.runrecord.json` through
  `RunRecord.model_dump_json(indent=1)` (newline-terminated) equals the file; every other JSON,
  with each ensemble, exclusion and fallback record loaded and dumped again, re-serialised with
  its writer's `indent=2, sort_keys=True` plus newline, equals the file.
- `test_ts_ensemble.py` and `test_ts_ensemble_guards.py` are unchanged: 39 passed.
- `tests/unit/review/test_run_data.py` (schema drift) passes: `RunData` embeds none of the
  changed models.

## Commands

All from the repo root with `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp`, under `timeout 3600`.

| command | at | exit | seen |
|---|---|---|---|
| `python3 .agents/scripts/hyper_codegraph.py index` | 493f40c | 0 | `index: ok` |
| `uv run ruff check .` | 54e7e66 tree | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 54e7e66 tree | 0 | 749 files formatted |
| `uv run mypy` | 54e7e66 tree | 0 | 91 source files |
| `uv run pytest` (full; `ETA_RXNCAT_XTB` set) | 54e7e66 tree, pre-commit | 0 | 2642 passed, 196 deselected, 918.06 s |
| `uv run pytest tests/unit/orchestrator tests/unit/core` | 54e7e66 tree | 0 | 838 passed, 1 deselected |
| `pytest test_ts_ensemble.py test_ts_ensemble_guards.py` | 54e7e66 | 0 | 39 passed |
| `hyper_codegraph.py index --if-stale` | 54e7e66 | 0 | re-indexed |
| `hypergraph_updater.py --from-diff 493f40c --apply --slice OPR.0.7.0.15 --json` (once) | 54e7e66 | 0 | below |

The format check ran only in the excluding form, not the bare oracle form (seat rule: the bare
form prints `spec/archive` text).

Iteration runs with a non-zero exit, all fixed before the commit: `ruff check src` (one long
docstring line); the first new-test runs (2 test-side failures: stub samples flagged by the new
check, wrong seed tag); the first byte-equality test (compared dict order against key-sorted
files) and its format check.

Host before the full suite (07:43Z): 12 G available, 4 G free, load 10.8; other projects' CPU
jobs running; no eta engine or GPU process.

## Ledger

- `ensure-node --from-spec` on this SPEC: no change (it skipped the glob touches and the
  core-owned files). `ensure-node --id eta_rxncat_selectivity --description-file`: one sentence
  added, 1249 -> 1455 characters. Core description unchanged (1973). `validate: ok`.
- Updater marked dirty: cli, core, hw_probe, scaffold, selectivity, species_runner, store
  (`architecture.yml` is listed in several nodes' files). Seven further nodes `needs_review`.
- `unmapped`: the three mission files, plus untracked `spec/active/`, `spec/archive/` and
  `spec/process/` files (listed by name by the updater; none opened).

## For the auditor to rule on

1. The test file is named `test_ts_fallback_seed_checks.py` so the selectivity node's
   `test_ts_fallback*.py` glob owns it; it covers the ensemble too.
2. `close_contact_count` in the fallback detail is the sum over the template's `ok` graft
   records for the node (one record in every v0.7.0 run). Its `check` is `clash`, other fields
   `None`.
3. The `SeedCheckDetail` fields the SPEC leaves untyped are optional with default `None`
   (bond lists included). Inner `None` fields are serialised; only the outer `detail` /
   `failed_detail` key is omitted.
4. `find_clash` returns the `SeedCheckDetail` (not a bare tuple) and takes the topology with the
   forming bonds already in it. `bond_changes(state, intended, forming)` takes the forming bonds
   as a third argument.
5. `orchestrator/__init__.py` (in touches) is unchanged: the SPEC asks for no new lazy export.
