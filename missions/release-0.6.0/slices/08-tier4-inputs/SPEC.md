---
id: OPR.0.6.0.8
slice: 08-tier4-inputs
mission: release-0.6.0
status: active
stage: wip
verified: "2026-11-25 against scaffold (hyper_scope slice create)"
created: "2026-11-25"
intent: "Land TS1a_x, TS1b_x and P1b_x byte-equal to resolve's checked transcription, with SOURCES.md rows, the two provisional Tier 4 fixture YAMLs and offline input tests."
depends_on: [OPR.0.6.0.2, OPR.0.6.0.5]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_t4_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.6.0 Tier 4 inputs — TS1a_x, TS1b_x, P1b_x and the provisional fixtures

## Intent

Land Tier 4's inputs — TS1a_x from TJ's builder, TS1b_x and P1b_x transcribed from Liu 2013's SI —
byte-equal to resolve's checked transcription, with `SOURCES.md` rows, the two provisional schema-1
fixture YAMLs and input tests, so the E2E slices run on verified geometries.

Context the builder needs:
- **TJ, verbatim:** Q-E4 "Q4. A but the files attached can be used as reference." (forming carbons
  `[1, 2, 3, 5]`; P1b_x and TS1b_x transcribed from Liu's SI; TJ confirms at Phase 3); Q-E3 "Q3. B,
  but these may need updating as we define the YAML/JSON format." (team-drafted, provisional).
- Mission HF-1 (procedure and sha256), HF-2, HF-8. Resolve's procedure (re-run it; output must be
  byte-equal): `pdftotext -f <p> -l <p> -x <0|300> -y 0 -W <300|312> -H 792 -layout
  ja408437u_SI.pdf liu_p<p>_<L|R>.txt` for p = 9, 10, 20 (SI sha256 `98f37dc4…76f6af`, in
  `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/si/`). TS1b_x = 1 atom line after the
  "TS1b_x" label in `liu_p9_R.txt` + the first 20 atom lines of `liu_p10_L.txt`; P1b_x = 21 atom
  lines after "P1b_x" in `liu_p20_R.txt`. TS1a_x = the builder's `XYZ_FILES["…/TS1a_x.xyz"]` by
  `ast.parse` + `literal_eval` (never executed), byte-identical. Atom regex
  `([A-Z][a-z]?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)`; coordinates copied verbatim;
  written `"N\n<header>\n" + "S x y z\n"`. Headers (line 2):
  - `TS1b_x (exo Cp + cyclobutene) - Liu, Paton, Kim, Liang, Houk JACS 2013 SI S9-S10 - M06-2X/6-31G(d) E = -349.872275 H = -349.679329 G = -349.718879 Hartree`
  - `P1b_x (exo product Cp + cyclobutene) - Liu, Paton, Kim, Liang, Houk JACS 2013 SI S20 - M06-2X/6-31G(d) E = -349.957548 G = -349.797634 Hartree`
  Expected sha256: TS1a_x `ec319a528d3efd0d7c14fb1d018d31d57eae85e794df59761665ed4d0f684d60`,
  TS1b_x `2a0b8362cdd36464c5f3f7a196927005c1cc933f3fdc6a693ae0d56ff365fd82`,
  P1b_x `ca8706431f6e8b57662a3f65196a9ca3cba3288a4eda68308f7bc3c9699b5eec`.
- Files: `tests/e2e/data/e2e5/xyz/{TS1a_x,TS1b_x,P1b_x}.xyz`; `SOURCES.md` rows (file, sha256, SI page,
  header E/H/G, procedure); `tests/e2e/data/e2e5/t4_endo_exo_unmapped.yaml` and
  `t4_mapped_selectivity_pruned.yaml` (schema 1; the v0.5.0 `t3_*.yaml` style: species, two TS
  entries with `pathway: endo|exo`, `active_atom_indices [0..5]`, `forming_bonds [[1,2],[3,5]]`,
  starts (Liu xyz for unmapped; for mapped: TS1b_n from `tests/fixtures/v0.4.0/m1_relaxed.{recipe}.json`,
  TS1b_x from the graft block below), the pathway pruning rule `threshold_kcal_mol: 1.5` (mapped
  only), the priority-2 node `downstream_exo_minor` = P1b_x with `pathway: exo`, the literature
  header G values, ΔΔG‡ references (+4.3 / +1.8, with Liu's +4.273 / +1.849 recorded), UMA windows
  `[2.3, 6.3]` and `(0.5, 3.8]`, `kind: de`, `temperature_k: 298.15`). The mapped YAML's graft
  block reuses `m1_ts1a_n_to_ts1b_n.yaml`'s keep/delete/alignment/core lists with
  `template: xyz/TS1a_x.xyz` (HF-8: valid unchanged).
- Input tests (`tests/e2e/test_t4_inputs.py`, offline): sha256s; formula and atom counts; fragments
  (2/2/1); H degree 1, no C below degree 3; forming distances 2.353 (TS1a_x) and 2.266 Å (TS1b_x)
  to 0.001; header-G ΔΔG +4.273 and +1.849 to 0.005; YAMLs load through the fixture loader; the
  face tuples of Liu's files (endo (+1,+1), exo (−1,−1)) via slice 05's descriptor.
- **Seat rules (every slice):** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (never /tmp); every
  framework script with `python3`; Task 1 is `python3 .agents/scripts/hyper_codegraph.py index`
  (must print `index: ok`); run `hypergraph_updater.py --from-diff <Start> --apply` **once** after
  the commit (re-index first; a rerun needs `git restore spec/compiled/architecture.yml` first and a
  disclosure); never edit `spec/compiled/architecture.yml` by hand; never read `spec/archive/` or
  `tests/candidate_outputs/`; commits under this machine's git identity, ending with exactly
  `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)` (version from `.agents/hacf-manifest.json` at commit
  time), no co-author trailer, never `--no-verify`; stage named files only; no push, tag or promote.
- **Clean room (v0.4.0 Q1, v0.5.0 A1, hard rule):** never open, clone, fetch or search Eta_Scripts or
  nMAP; read no TS-optimizer or conformer-search source (installed `geometric` package internals,
  Sella, pysisyphus, the starter's code beyond naming it in a DV row); geomeTRIC runs only as a black
  box through eta's `GeometricOptimizer`. The mission SPEC is `missions/release-0.6.0/SPEC.md`; its
  R-, HF- and G-rows are cited by number.

## 1. The Confidence Mandate

**Score: 10/10.** Resolve already transcribed and checked these files (HF-1); this slice re-runs the
procedure and lands them with tests.

## Mini-requirements

1. US-009: the three xyz files are byte-equal to the expected sha256 values.
2. US-009: every input test above passes.
3. US-009: `SOURCES.md` rows complete; both YAMLs load and name P1b_x (not P1a_n) as
   `downstream_exo_minor`.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start.
- [x] Task 2: re-run the transcription in TMPDIR; compare sha256; copy.
- [x] Task 3: `SOURCES.md`, both YAMLs (fixture loader extension only if the loader needs the
      `pathway`/rule keys — keep it in `tests/e2e/fixtures.py`).
- [x] Task 4: `tests/e2e/test_t4_inputs.py`; required checks.
- [x] Task 5: commit; updater once (node `eta_rxncat_species_runner`).

## 4. The Negative Space (Constraints)

- **DO NOT** execute TJ's builder; **DO NOT** edit `PRDs/` or the SI PDFs.
- **DO NOT** hand-edit a coordinate; a mismatch is a stop-and-report.
- **DO NOT** run any engine in this slice.

## Proof contract

- [ ] The three sha256 values match (command + output).
- [ ] `uv run pytest tests/e2e/test_t4_inputs.py -q` passes; required checks exit 0.

## Source material

- Mission HF-1, HF-2, HF-8; `tests/e2e/data/e2e5/SOURCES.md`, `t3_*.yaml`, `m1_ts1a_n_to_ts1b_n.yaml`;
  `~/.hacf/eta-rxncat-hacf/evidence/v060-resolve/` (extract.py, liu_p*.txt).

## Intent visual

N/A (non-visual slice).

## Status

- compiled

## Dependencies

02 (the YAML's pathway and rule keys load through the slice 02 models), 05 (the face descriptor in the input test).
