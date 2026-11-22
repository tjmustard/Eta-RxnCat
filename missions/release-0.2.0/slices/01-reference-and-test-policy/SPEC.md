---
id: OPR.0.2.0.1
slice: 01-reference-and-test-policy
mission: release-0.2.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Unpack the v0.2.0 reference zip with its ruff gate file, seed the v0.2.0 discrepancy register, decide PD-006, and install the engine test policy (markers, acceptance envs, skip-to-fail switch, offline unit tests)."
depends_on: []
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executing
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["docs/prd/v0.2.0/**", docs/prd/PLAN_DISCREPANCIES.md, pyproject.toml, tests/conftest.py, tests/unit/test_test_policy.py, ".gitignore", AGENTS.md, spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_test_policy.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.2.0 reference copy, registers, and the engine test policy

## Intent

Unpack the v0.2.0 reference zip into the repo, seed the v0.2.0 discrepancy register, record
PD-006 as decided, and put the engine test policy in place before any engine exists:
- markers;
- acceptance environments;
- a switch that turns skips into failures;
- network-free unit tests.

Context the builder needs (self-contained).

TJ (v0.1.0): "Zips should be unpacked in repo as needed in appropriate sub directories." The zip
copies are reference only, plus a DISCREPANCIES register (v0.1.0 Q2 B).

v0.1.0 did this for its own zip at `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/`, using:
- root `[tool.ruff] force-exclude = true`;
- `extend-exclude = ["docs/prd", ".agents"]`;
- a declared two-line gate file `.ruff.toml` (`exclude = ["*"]`) inside the copy.

This is needed because the HACF pre-commit hook lints staged `.py` files by explicit path (v0.1.0
R38). Repeat that pattern exactly.

TJ's v0.2.0 Q1 was "C both", which decides PD-006 in `docs/prd/PLAN_DISCREPANCIES.md`.

Test policy decisions (mission R8, R18, R19):
- `.venv` stays the base dev env for the required checks.
- Acceptance runs use the named envs `.venv-accept-gpu`, `.venv-accept-mace` and
  `.venv-accept-uma`. Slice 11 creates them; this slice only ignores and documents them.
- `ETA_RXNCAT_ACCEPTANCE=1` turns any skip into a failure.
- Unit tests never reach the network.

Node `eta_rxncat_scaffold` owns `docs/**`, `pyproject.toml`, `tests/conftest.py`, `.gitignore`
and `AGENTS.md`.

## 1. The Confidence Mandate

**Score: 10/10.** Mechanical unpack (the v0.1.0 pattern), fixed register format, and a
deterministic conftest hook with explicit tests.

## Mini-requirements

1. `unzip -q PRDs/Eta-RxnCat-v0.2.0.zip -d docs/prd/v0.2.0/` gives
   `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/…`, 26 files.
   - Add exactly one gate file, `docs/prd/v0.2.0/Eta-RxnCat-v0.2.0/.ruff.toml`, with the same two
     lines as v0.1.0's (a comment that it is not part of the starter, then `exclude = ["*"]`).
   - The root ruff config already has `force-exclude` and `extend-exclude = ["docs/prd", …]`;
     change nothing there.
   - Commit all 27 files through the unmodified hook.
2. `docs/prd/v0.2.0/DISCREPANCIES.md` uses the v0.1.0 header and row format. It holds rows for:
   - the starter's version bump;
   - every public name in `engines/{__init__,base,rdkit_xtb,mlip,pyscf_engine}.py`;
   - every test in `tests/unit/test_engines_v020.py`;
   - the draft's known entries: solvent name ignored; swallowed perception errors; the GB VRAM
     formula; the per-evaluate probe; float32 UMA positions; `mace_mp` usage; engine names that
     differ from the frozen tags (`rdkit_uff`, `xtb_gfn2-xtb`, `mace_medium`,
     `pyscf_<xc>_<basis>`); FD MLIP Hessians; the `< −75.0` test.
   
   Disposition `pending` until the engine slices add `changed`/`dropped`/`added` rows.
   v0.1.0-identical modules (`core/`, `store/`, `utils/hw_probe.py`) are not re-registered;
   check with `cmp` against `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/` and state the result in the
   header.
3. `docs/prd/PLAN_DISCREPANCIES.md`:
   - PD-006 status → `decided`, quoting TJ "C both", and the row
     `qitem-20261122155050-b7431ecd1c462294`;
   - confirm the v0.2.0 zip-hash row against `unzip -p … | sha256sum`.
4. Test policy in `pyproject.toml` `[tool.pytest.ini_options]`:
   - `markers`: `gpu`, `xtb`, `mlip_mace`, `mlip_uma`, `slow`, `acceptance`, each with a one-line
     reason;
   - `addopts = "-m 'not gpu and not xtb and not mlip_mace and not mlip_uma and not slow and not acceptance'"`.
   
   Keep the existing `gpu` marker semantics.
5. `tests/conftest.py`:
   - (a) Autouse, session-scoped: set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
   - (b) A `pytest_runtest_makereport` hook. When `os.environ.get("ETA_RXNCAT_ACCEPTANCE") == "1"`,
     a report whose outcome is `skipped` (setup or call) becomes `failed`, with the skip reason in
     the longrepr. Without the variable, nothing changes.
6. `.gitignore` adds `.venv-accept-*/`.
7. `AGENTS.md` project section (after the HACF END marker) gains three short rules:
   - acceptance envs and the audit seat's `--no-sync`;
   - `ETA_RXNCAT_ACCEPTANCE=1`;
   - "unit tests never use the network; provisioning is a seat command".

## 3. Implementation Plan (Task List)

- [ ] Task 1: unpack, add the gate file, commit through the hook (Mini-requirement 1).
- [ ] Task 2: register and PD-006 (Mini-requirements 2–3).
- [ ] Task 3: markers, conftest, `.gitignore`, AGENTS.md (Mini-requirements 4–7).
- [ ] Task 4: tests in `tests/unit/test_test_policy.py`. Use pytester (`pytest_plugins =
  ["pytester"]`) to run an inner test that calls `pytest.skip("x")`, once with
  `ETA_RXNCAT_ACCEPTANCE=1` and once without.
- [ ] Task 5: four gates; `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** edit any of the 26 starter files, the HACF hook, or anything under `.agents/`. Never
  use `--no-verify`.
- **DO NOT** unpack any zip other than v0.2.0, or write outside `docs/prd/v0.2.0/`, except for
  the files named above.
- **DO NOT** touch `src/`.
- **DO NOT** make the default suite slower: no new default-selected test may take more than 1 s.

## Proof contract

- [ ] `git ls-files docs/prd/v0.2.0/Eta-RxnCat-v0.2.0 | wc -l` → 27. Each of the 26 files is
  byte-identical to `unzip -p PRDs/Eta-RxnCat-v0.2.0.zip <path>`.
- [ ] The hook-style re-check `bash -c 'mapfile -t F < <(git ls-files "docs/prd/v0.2.0/*.py"); .venv/bin/ruff check -- "${F[@]}" && .venv/bin/ruff format --check -- "${F[@]}"'`
  → exit 0.
- [ ] The register exists with every row in Mini-requirement 2, and its header states the `cmp`
  result. PD-006 is `decided`, with the quote.
- [ ] pytester proofs:
  - an inner skipping test → exit 0, `1 skipped` without the variable;
  - the same test → exit 1, `1 failed`, with the reason shown, under
    `ETA_RXNCAT_ACCEPTANCE=1`.
- [ ] `os.environ["HF_HUB_OFFLINE"] == "1"` inside a test.
- [ ] `uv run pytest --markers` lists the six markers. `uv run pytest -m acceptance --collect-only -q`
  collects 0 tests today.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0.

## Source material

- `PRDs/Eta-RxnCat-v0.2.0.zip` (reference only); `docs/prd/v0.1.0/` (the pattern).
- Mission `missions/release-0.2.0/SPEC.md` §5: R8, R18, R19; the discrepancy-register section.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- none (v0.1.0 complete at e8b16de)
