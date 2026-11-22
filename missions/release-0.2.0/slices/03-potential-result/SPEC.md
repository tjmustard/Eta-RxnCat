---
id: OPR.0.2.0.3
slice: 03-potential-result
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Add the strict, frozen PotentialResult core data contract (energy, forces, exactly-symmetric Cartesian Hessian in atomic units, identity, device, recovery record)."
depends_on: [OPR.0.2.0.1]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_core
parent: null
hacf_touches: ["src/eta_rxncat/core/**", "tests/unit/core/**", docs/prd/v0.2.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/core/test_core_potential_result.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: `PotentialResult` core data contract

## Intent

Add `PotentialResult` to `eta_rxncat.core`. It is the strict, frozen data model every engine
returns: energy, forces and Hessian in atomic units, with the engine identity, device, timing and
SCF recovery record. It holds data only, with no engine imports.

Context the builder needs (self-contained).

ADR-0009 says result types "are defined by their consuming versions", and v0.2.0 is the first
consumer. Core models follow ADR-0003: Pydantic v2, `extra="forbid"`, `frozen=True`, finite
floats, StrictInt.

Existing core names you reuse: `CoreModel`, `FiniteFloat` (or the existing finite-float
annotation), and `EngineIdentity(name: EngineTag, version: str, model: str | None)`.

Conventions (mission §5 Contracts):
- forces = −∂E/∂x in Hartree/Bohr, N×3;
- the Hessian is Cartesian, Eh/Bohr², not mass-weighted, not projected, 3N×3N, and **exactly**
  symmetric (engines symmetrise and record the pre-symmetrisation maximum asymmetry, R15).

Node `eta_rxncat_core`.

## 1. The Confidence Mandate

**Score: 10/10.** Fields and validators are fully specified.

## Mini-requirements

1. `PotentialResult(CoreModel)` in `src/eta_rxncat/core/` (a new `results.py` or `models.py`),
   exported from `eta_rxncat.core`. Fields:

   | Field | Type |
   |---|---|
   | `energy_hartree` | finite float |
   | `forces_hartree_per_bohr` | `list[list[finite float]] \| None` |
   | `hessian_hartree_per_bohr2` | `list[list[finite float]] \| None` |
   | `hessian_method` | `Literal["analytic", "finite_difference"] \| None` |
   | `hessian_max_asymmetry` | finite float ≥ 0, or `None` |
   | `engine` | `EngineIdentity` |
   | `stage_engine_impl` | StrictInt ≥ 1 |
   | `device` | `Literal["cpu", "cuda"]` |
   | `device_reason` | `str \| None` (min length 1 when set) |
   | `wall_time_s` | finite float ≥ 0 |
   | `recovery_steps` | `list[str]`, default empty |

2. Validators, each raising `ValueError` with a message naming the field:
   - forces: every row has length 3, and there is at least 1 row;
   - Hessian: square, with side divisible by 3;
   - if both forces and Hessian are present, side = 3 × len(forces);
   - Hessian exactly symmetric (`H[i][j] == H[j][i]` for all i, j);
   - `hessian_method` and `hessian_max_asymmetry` are both set iff the Hessian is set;
   - no NaN or inf anywhere.
3. A docstring that states every unit and sign convention above.
4. Register rows in `docs/prd/v0.2.0/DISCREPANCIES.md` (status `open`): the starter's
   `PotentialResult` field names and units vs these (`changed` per field; `added` for
   `hessian_method`, `hessian_max_asymmetry`, `stage_engine_impl`, `device_reason`).

## 3. Implementation Plan (Task List)

- [ ] Task 1: the model and validators.
- [ ] Task 2: tests in `tests/unit/core/test_core_potential_result.py`, one per validator, each
  rejecting and accepting.
- [ ] Task 3: register rows; four gates.

## 4. The Negative Space (Constraints)

- **DO NOT** import anything from `eta_rxncat.engines`, numpy, torch or any extra in core. Plain
  lists only.
- **DO NOT** change any existing core model.
- **DO NOT** symmetrise inside the model. Engines do that, and the model only validates.

## Proof contract

- [ ] A valid result with N = 3 (forces 3×3, Hessian 9×9 symmetric, `hessian_method="analytic"`,
  `hessian_max_asymmetry=0.0`) constructs, and `model_dump()` round-trips through `model_validate`.
- [ ] Each of the following raises `ValidationError` naming the field:
  - a forces row of length 2;
  - an empty forces list;
  - an 8×8 Hessian;
  - a 9×9 Hessian with 4×3 forces;
  - `H[0][1] != H[1][0]` by 1e-15;
  - a Hessian without `hessian_method`;
  - `hessian_method` without a Hessian;
  - a NaN energy;
  - an inf force;
  - `device="gpu"`;
  - `stage_engine_impl=0`;
  - `wall_time_s=-1`;
  - an extra field.
- [ ] The frozen model rejects assignment.
- [ ] `python -c "import eta_rxncat.core, sys; assert not {'numpy','torch','pyscf','rdkit'} & set(sys.modules)"`
  (subprocess) → exit 0. numpy is not imported by core today: confirm, and if core already
  imports numpy, drop it from the set and say so.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0.

## Source material

- Mission §5 Contracts (`PotentialResult`, Hessian convention), R15; ADR-0003, ADR-0009;
  `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/src/eta_rxncat/engines/base.py` (reference only).

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.2.0.1 (v0.2.0 register)
