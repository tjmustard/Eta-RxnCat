---
id: OPR.0.1.0.11
slice: 11-readme-gpu-claim
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Make the README's GPU-acceptance statement derived from and tested against the committed acceptance record (docs/prd/v<version>/GPU_SMOKE_RESULT.json), and update it to the recorded v0.1.0 pass."
depends_on: [OPR.0.1.0.7, OPR.0.1.0.10]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [tests/unit/test_identity.py, README.md, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: README GPU-acceptance claim derived from the acceptance record

## Intent

Make the README's GPU-acceptance statement follow the committed acceptance record, and test it
against that record, so it can no longer go stale. Then update the statement to the v0.1.0 pass.

Context the builder needs (self-contained). Slice 07 (audited) recorded the v0.1.0 GPU acceptance
in `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`:
- `smoke.status` `"pass"`, run 2026-11-22T15:35:14Z against commit `ff3991ea5805…`;
- hardware: NVIDIA GeForce RTX 5060 Ti, compute capability 12.0;
- GPU4PySCF vs CPU PySCF `|ΔE|` 9.95e-13 Eh, MOs on device, torch device `cuda`, matmul max diff
  3.7e-13;
- `pytest -m gpu`: 1 passed.

Slice 08 (audited) wrote `tests/unit/test_identity.py::test_readme_claims_no_gpu_pass_and_no_pip_licenses`.
It asserts the README contains "GPU acceptance run has not been recorded yet" (`README.md` ~line
66). That was true at slice 08 and is false now, and the test blocks the scribe's README update.
This slice replaces that one hard-coded assertion with a record-derived check. Slice 08's SPEC is
not edited. Its test file is in this slice's touches, and this slice's audit judges the change.

Do not touch the scribe's uncommitted `CHANGELOG.md` or `.agents/memory/activeContext.md` edits.
Node `eta_rxncat_scaffold` already owns `README.md`, `docs/**` and `tests/unit/test_identity.py`.

## 1. The Confidence Mandate

**Score: 10/10.** One README sentence and one deterministic check, with explicit failing cases.

## Mini-requirements

1. Controlled vocabulary. The README states GPU acceptance with exactly one of two fixed phrases:
   - `GPU acceptance passed`, only when a passing record exists;
   - `GPU acceptance run has not been recorded yet`, only when it does not.
   
   The checker looks for these phrases after whitespace normalisation (`" ".join(text.split())`).
2. Checker: `check_gpu_claim(readme_text: str, record: dict | None, version: str) -> list[str]`,
   in `tests/unit/test_identity.py`, pure and stdlib only. It returns a list of violations.
   - "Passing record" means `record is not None and record.get("smoke", {}).get("status") == "pass"`.
   - The record link is a Markdown link whose target is `docs/prd/v<version>/GPU_SMOKE_RESULT.json`
     or `./docs/prd/v<version>/GPU_SMOKE_RESULT.json`.
   - With a passing record, the README must contain all of:
     - the pass phrase;
     - the record link;
     - the record's `hardware.gpu.name`, verbatim (e.g. `NVIDIA GeForce RTX 5060 Ti`);
     
     and must not contain the not-recorded phrase.
   - Without a passing record (the record is missing, or its status is not `pass`), the README
     must not contain the pass phrase.
3. The real-repo test replaces the hard-coded assertion in
   `test_readme_claims_no_gpu_pass_and_no_pip_licenses`. Rename the test
   `test_readme_gpu_claim_matches_record_and_no_pip_licenses`. It:
   - reads `version` from `pyproject.toml` `[project].version` with `tomllib`;
   - loads `docs/prd/v<version>/GPU_SMOKE_RESULT.json` if it exists (else `None`);
   - asserts `check_gpu_claim(...) == []`;
   - keeps its other two assertions unchanged: `"pip-licenses" not in text` and
     `"tools/licence_gate.py" in text`.
   
   Every other identity and media assertion stays untouched.
4. `README.md`: replace only the clause "the GPU acceptance run has not been recorded yet" in the
   "Hardware probe and GPU smoke test" bullet with a statement built from the record. It contains:
   - the pass phrase;
   - the GPU name and compute capability;
   - the date (from `run_at_utc`);
   - the two measured differences, rounded the way the record supports (e.g. `|ΔE| ≈ 1e-12 Eh`);
   - a link `[GPU_SMOKE_RESULT.json](docs/prd/v0.1.0/GPU_SMOKE_RESULT.json)`.
   
   Claim nothing the record does not show: no performance, no other GPUs, no MLIP engines. No
   other README line changes. Keep the line wrapping consistent with the surrounding bullet.
5. `docs/prd/v0.1.0/DISCREPANCIES.md` gains one `changed` row (status `open`): the README
   GPU-acceptance statement is now record-derived and tested (R54).

## 3. Implementation Plan (Task List)

- [ ] Task 1: write `check_gpu_claim` and its synthetic tests (Mini-requirements 1–2), and see the
  failing cases fail.
- [ ] Task 2: switch the real-repo test (Mini-requirement 3). It fails against the current README.
- [ ] Task 3: update the README clause (Mini-requirement 4); the real-repo test now passes.
- [ ] Task 4: register row; the four gates; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** edit slice 08's SPEC, proof or oracle, or any other identity/media assertion.
- **DO NOT** touch `CHANGELOG.md` or `.agents/memory/activeContext.md` (the scribe's work).
- **DO NOT** edit `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`.
- **DO NOT** hard-code the outcome. The expected README state comes from the record.
- **DO NOT** change any README text other than that clause.

## Proof contract

- [ ] Synthetic `check_gpu_claim` cases. Each of these returns ≥ 1 violation:
  - (a) the pass phrase with `record=None`;
  - (b) the pass phrase with `smoke.status == "fail"`;
  - (c) the not-recorded phrase with a passing record;
  - (d) the pass phrase and the GPU name with a passing record, but no record link;
  - (e) the pass phrase and the link with a passing record, but the wrong GPU name;
  - (f) a passing record whose README contains both phrases.
  
  These return `[]`:
  - (g) a passing record with a correct claim;
  - (h) `record=None` with the not-recorded phrase;
  - (i) a failing record with the not-recorded phrase.
- [ ] `uv run pytest tests/unit/test_identity.py` → exit 0 at this slice's HEAD. With the README
  clause temporarily reverted, the real-repo test fails (shown once in the handoff, not
  committed).
- [ ] `git diff <start> -- README.md` changes only the GPU-acceptance clause of that one bullet,
  and the new text contains `GPU acceptance passed`, `NVIDIA GeForce RTX 5060 Ti` and
  `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json`.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0.

## Source material

- `docs/prd/v0.1.0/GPU_SMOKE_RESULT.json` (slice 07's record).
- `tests/unit/test_identity.py` and `README.md` at the start commit; slice 08 SPEC (context only).
- Mission `missions/release-0.1.0/SPEC.md` trade-off log R34, R49, R54.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.1.0.7 (GPU acceptance record), OPR.0.1.0.10 (final README media lines)
