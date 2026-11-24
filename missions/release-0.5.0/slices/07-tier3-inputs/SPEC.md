---
id: OPR.0.5.0.7
slice: 07-tier3-inputs
mission: release-0.5.0
status: active
stage: wip
verified: "2026-11-24 against scaffold (hyper_scope slice create)"
created: "2026-11-24"
intent: "Land the Tier 3 inputs: six XYZ files re-transcribed byte-equal to resolve's checked copies, SOURCES.md provenance with derived references, five provisional TS-fixture YAMLs and a loader, tier-D checks and the PySCF energy reproduction of the Liu files."
depends_on: [OPR.0.5.0.6, OPR.0.5.0.15]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_species_runner
parent: null
hacf_touches: ["tests/e2e/**", spec/compiled/architecture.yml]
hacf_oracle: [[uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/e2e/test_t3_inputs.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: v0.5.0 Tier 3 inputs — transcriptions, provenance, provisional YAMLs, energy check

## Intent

Land the Tier 3 inputs every E2E consumes — six XYZ files re-transcribed byte-equal to resolve's
checked copies, their `SOURCES.md` provenance with derived references and standard states, five
provisional TS-fixture YAMLs with a loader, tier-D checks, and a PySCF reproduction of Liu's
electronic energies — so a transcription error stops the build before any E2E.

Context the builder needs:
- **TJ A3, verbatim "Q3. A":** all four T3 fixtures; the team transcribes TS3a, TS4a,
  cyclobutenone and TS N4 from the attached SIs with checks and `SOURCES.md`; TJ confirms them at
  Phase 3. Q-E3: every fixture YAML is provisional.
- **Sources** (never committed; cite by DOI): `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/si/`
  — Liu, Paton, Kim, Liang, Houk, *JACS* 2013, 135, 15642, DOI 10.1021/ja408437u,
  `ja408437u_SI.pdf` sha256 `98f37dc41f252f4e031e750d9343c3c478d4e5651940c3d0ed54e587b476f6af`;
  Paton et al., *Angew. Chem. Int. Ed.* 2011, 50, 10366, DOI 10.1002/anie.201103998,
  `anie_201103998_SI_Paton2011.pdf` sha256 `a38b2362232940c05f20ae921cee6a04aef58d98811c066e1de003676f043af6`.
  TJ's builder `Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py` (sha256 `26e923529370687f78dffccbfa6f613f1e7391d50c425432c5f600ff86acc8e2`)
  — read with `ast.parse`; `XYZ_FILES` is an annotated assignment (`ast.AnnAssign`); never execute it (N16).
- **Procedure** (resolve's, in `~/.hacf/eta-rxncat-hacf/evidence/v050-resolve-f6/README.md` with
  its scripts; follow it independently in scratch, then compare):
  - Liu: `pdftotext -f <p> -l <p> -x <0|300> -y 0 -W 312 -H 792 -layout` per half page. TS3a = the
    17 atom lines after the `TS3a` label in page 15 left + the first 4 atom lines of page 15 right;
    TS4a = the 21 atom lines after `TS4a` on page 17 left.
  - Paton: `pdftotext -layout`; replace `"-­‐"` with `"-"`, then every other
    non-printable or non-ASCII character with a space. Cyclobutenone = 9 atom lines after
    `Cyclobutenone:` (page S3); N4 = 20 atom lines after `N4 (endo` (page S6).
  - Tetrazines 3 and 4: `XYZ_FILES["…3_dimethyltetrazine.xyz"]` and `["…4_bis_cf3_tetrazine.xyz"]`, byte-identical.
  - Atom regex `([A-Z][a-z]?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)`; coordinate strings
    verbatim; file = `f"{n}\n{header}\n"` + `f"{sym} {x} {y} {z}\n"` per atom. Headers, verbatim:
    - `TS3a.xyz`: `TS3a - Liu, Paton, Kim, Liang, Houk JACS 2013 SI S15 - M06-2X/6-31G(d) E = -491.366826 H = -491.187576 G = -491.232873 Hartree`
    - `TS4a.xyz`: `TS4a - Liu, Paton, Kim, Liang, Houk JACS 2013 SI S17 - M06-2X/6-31G(d) E = -1086.627595 H = -1086.490471 G = -1086.545437 Gsol = -1086.883262 Hartree`
    - `cyclobutenone.xyz`: `Cyclobutenone - Paton et al. ACIE 2011 SI S3 - M06-2X/6-31G(d) E(thermal) = -229.814586 H = -229.813642 G = -229.845861 Hartree`
    - `TS_N4.xyz`: `N4 (endo TS of cyclopentadiene+cyclobutenone) - Paton et al. ACIE 2011 SI S6 - M06-2X/6-31G(d) E(thermal) = -423.703397 H = -423.702453 G = -423.744120 Hartree`
  - **Expected sha256 (mission HF-1):** `TS3a.xyz` `6bf308b6846732718499d2370f355116a849a232f476c27a026dafb5ab1ea1b4`;
    `TS4a.xyz` `b00f6a874efd2b30112e34d2cb16892923f73b756e7bdbca4a2f6583b4bf008c`;
    `cyclobutenone.xyz` `c489e5124f42895bb0408f127aa10d51db70ccfbd72f4cf5c929c10052f4f30c`;
    `TS_N4.xyz` `cf7e45014bdab5971b2c993da3f2d5125ce744a8def5bda64998e047dc3dc46f`;
    `3_dimethyltetrazine.xyz` `e42ed53adaa7bc3a9fe542d88cafb632d4351c3e419e9b2b3b3b961744a7662d`;
    `4_bis_cf3_tetrazine.xyz` `174c23d2c794196f7d1fa5367529fe623e1529007bab76cb32b9139816e92f74`.
    Your independent output must be byte-equal; a difference is stop-and-report with the diff
    (never copy resolve's file over yours).
- **Destination:** `tests/e2e/data/e2e5/xyz/`; six rows added to `tests/e2e/data/e2e5/SOURCES.md`
  (file, SI page, energies as printed, sha256, transcriber "team (spec-resolve; slice 07
  re-transcription)", and for Paton "E(thermal) is the thermally corrected energy, not electronic").
  Add a **References** section to `SOURCES.md` with each ΔG‡ derived by header G arithmetic and
  its standard state (Gaussian, 1 atm; Paton's SI states no concentration correction and its Cp G
  −193.937243 equals Liu's −193.937241): TS1a_n 19.637 (1 M 17.742); TS1b_n 27.793 (25.899);
  TS3a 18.877 (16.983); TS4a 9.591 (7.697); N4 24.463 (22.569) kcal/mol (mission HF-9, R8).
- **Five provisional YAMLs** (Q-E3; new `schema: 1` TS form, loaded by a new
  `load_ts_fixture(path)` in `tests/e2e/fixtures.py`, `extra` keys refused like the existing loader):
  `t3_ts1a_n_unmapped.yaml`, `t3_ts1b_n_mapped.yaml`, `t3_ts3a_unmapped.yaml`,
  `t3_ts4a_mapped.yaml`, `t3_n4_unmapped.yaml`. Keys:
  - `schema: 1`, `fixture`, `species` (the reactants, v0.3.0 species blocks with `seed_xyz` and
    `conformer_options: {n_embed: 10, seed: 42}`; seeds are reordered by `conformers.generate`);
  - `ts`: `ts_id`, `charge: 0`, `spin_multiplicity: 1`, `active_atom_indices`, `forming_bonds`,
    and one start form: `start_xyz` (unmapped) | `start_from_fixture: {path_template,
    key: relaxed_product}` (TS1b_n; `{recipe}` ∈ xtb, uma) | `start_grafts` (TS4a: `template`,
    `fragment`, a list of two graft blocks with `keep`, `delete`, `alignment_pairs`,
    `fragment_delete`, `constrained_core`, and `pre_relax: {core, maxiter: 200}`);
  - `reference`: `xyz`, and `start_to_reference_map` (identity for unmapped; M1's
    `graft_to_ts1b_n_map`; HF-10's map for TS4a) with `map_rule`;
  - `barrier`: `reactants: [[id, 1], [id, 1]]`; `window_dG_dagger_1M_kcal_mol`;
  - `literature`: E/H/G per structure as printed, `dG_dagger_1atm_kcal_mol`, `dG_dagger_1M_kcal_mol`,
    `standard_state`, `source`.

  | YAML | Reactants (SMILES) | Start | Active | Forming bonds | Window (UMA, 1 M) |
  |---|---|---|---|---|---|
  | t3_ts1a_n_unmapped | Cp `C1=CCC=C1`, cyclopropene `C1=CC1` | `xyz/TS1a_n.xyz` | [0,1,2,3,4,5] | [[1,2],[3,5]] | [10.7, 24.7] |
  | t3_ts1b_n_mapped | Cp, cyclobutene `C1=CCC1` | `tests/fixtures/v0.4.0/m1_relaxed.{recipe}.json` `relaxed_product` (fields `symbols`, `coordinates_angstrom`, `charge`, `multiplicity`) | [0,1,2,3,4,5] | [[1,2],[3,5]] | [20.0, 34.0] |
  | t3_ts3a_unmapped | tetrazine 3 `Cc1nnc(C)nn1`, cyclopropene | `xyz/TS3a.xyz` | [0..7] | [[0,6],[3,7]] | [10.0, 24.0] |
  | t3_ts4a_mapped | tetrazine 4 `FC(F)(F)c1nnc(C(F)(F)F)nn1`, cyclopropene | two grafts on `xyz/TS3a.xyz` with fragment `xyz/4_bis_cf3_tetrazine.xyz` (mission R22 lists, below) | [0..7] | [[0,6],[3,7]] | [0.7, 14.7] |
  | t3_n4_unmapped | Cp, cyclobutenone `O=C1C=CC1` | `xyz/TS_N4.xyz` | [1,2,9,10,12,13] | [[1,9],[2,10]] | [15.6, 29.6] |

  **TS4a grafts (R22):** graft 1 on TS3a: keep all but `[15, 16, 17]`, delete `[15, 16, 17]`,
  pairs `[[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[10,10]]`, `fragment_delete [6, 7, 8, 9]`, core
  `[0, 3, 6, 7]`; graft 2 on graft 1's product: keep all but `[15, 16, 17]`, delete
  `[15, 16, 17]`, pairs `[[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[9,6]]`, `fragment_delete
  [10, 11, 12, 13]`, core `[0, 3, 6, 7]`. TS3a's active set `[0..7]` is set on the template.
  `start_to_reference_map` (stated rule: lexicographically smallest element-preserving isomorphism
  of graft 2's `source_bonds` graph onto TS4a's perceived graph, as v0.4.0 R2):
  `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 17, 18, 19, 20, 14, 15, 16, 10, 11, 12]` (HF-10).
- **R9 energy check** (PySCF, `.venv-accept-gpu`, eta's `pyscf_gpu_cpu` engine, M06-2X/6-31G(d)
  with stage options `cartesian_basis=True` (Gaussian's 6D d functions; mission R30, slice 15)
  and `grids_level=4` (mission R31),
  read `engines/pyscf_gpu_cpu/` for its other stage options; heavy-run gate; one structure at a time;
  `timeout 3600` each): controls TJ's `TS1a_n.xyz` (Liu E −310.559154) and `5_cyclopropene.xyz`
  (−116.562552); targets `TS3a.xyz` (−491.366826), `TS4a.xyz` (−1086.627595),
  `3_dimethyltetrazine.xyz` (−374.809570), `4_bis_cf3_tetrazine.xyz` (−970.056992). Bound
  \|E_pyscf − E_Liu\| ≤ 1e-4 Eh on every file. If a **control** misses, stop and report (the bound
  is TJ's to change, never yours). Record all six differences. Paton files: no electronic E;
  formula, connectivity, forming bonds and HF-4 stand.

**Seat rules for every v0.5.0 slice.** Self-contained. The mission SPEC is
`missions/release-0.5.0/SPEC.md`; its R-rows, HF-rows and N-constraints are cited by number.

- **Clean room, TS optimizers (TJ A1 "Q1. A", hard rule).** No seat reads the source of any TS
  optimizer: geomeTRIC's TS/step/transition code (any file of the installed `geometric` package),
  Sella, pysisyphus, Eta_Scripts, or the starter's `optimize/ts_optimizer.py` beyond naming it in a
  DV row. P-RFO comes only from Banerjee, Adams, Simons & Shepard, *J. Phys. Chem.* 1985, 89, 52;
  Baker, *J. Comput. Chem.* 1986, 7, 385; Bofill, *J. Comput. Chem.* 1994, 15, 1, and this SPEC.
  geomeTRIC may run only as a black box through `geometric-optimize` and its `--help` text.
- **Clean room, nMAP (v0.4.0 Q1).** TJ, verbatim: "There is some ownership by the university, my
  advisor and co-authors. They are copyrighted in the code, and that is why I'd like to build this
  clean room approach". Never open, clone, fetch or search Eta_Scripts or nMAP (GitHub,
  `~/PROJECTS/cleanroom-nmap`, a cache, a web or code search); only its `TRANSFER_LOG.md` may be
  read. Never message the clean-room seats.
- **Branch and commits.** Branch `feature/eta-rxncat-v0.5.0`, cut re-entrantly from Base (the
  mission commit on main, parent `0d2a8d3`). One code commit per slice unless the slice says
  otherwise. Record `Start` (HEAD when you begin) in your handoff. Every commit ends with exactly
  two footer lines, `Agentic-Assistant: OpenRig (Claude Code harness) · model <model-id>` and
  `Agentic-Framework: HACF v<version> (OpenRig)`, `<version>` read from
  `.agents/hacf-manifest.json` at commit time; no co-author or session trailer. Author "Thomas J.
  L. Mustard Ph.D." (repo-local git config). Never `--no-verify`, never rewrite history.
- **Code graph first.** The first command is `python3 .agents/scripts/hyper_codegraph.py index`;
  it must print `index: ok` (the red team saw `stale_index`). Anything else stops the slice. The
  graph only widens a blast radius.
- **Ledger.** Only through `hyper_ledger.py` / `hypergraph_updater.py`, never by hand. On an
  existing node, `ensure-node --id <node>` takes the **full** `--files` list (it replaces); count
  the node's globs before and after. No slice creates a node.
- **Scratch.** `TMPDIR=/home/tjmustard/.cache/eta-rxncat-tmp` (`/tmp` is a shared 16G tmpfs).
  Remove temp clones, venvs and scratch directories at the end of each step.
- **HACF v0.6.3.** No `HACF-install.sh` (never without `--ref`), no `HACF-uninstall.sh`, no
  `hyper_migrate.py apply`. On OpenRig 0.7.21, `hyper_spec.py`/`hyper_migrate.py` warn "outside
  the pinned contract", `hyper_spec.py proof` writes the proof natively and `hyper_migrate.py
  verify` skips `rig scope audit`: note it in the proof, not as a finding.
- **Firewall.** Never read `tests/candidate_outputs/` or `spec/archive/`, also not through git:
  every `git diff`, `git show` and `git log -p` over a range containing a candidates commit uses
  `-- . ':(exclude)tests/candidate_outputs'`; a candidates commit is checked by file names only.
  Never write `tests/fixtures/`. `PRDs/` is read-only.
- **Host (shared with the hacf and cleanroom rigs).** Before any E2E, GPU, engine or full-suite
  run: `free -g` and `ps` for other rigs' heavy python/pytest/engine processes; if one is active,
  wait (poll at most every 5 minutes with Monitor or a background wait, never a foreground sleep)
  for GPU/E2E work; the full CPU unit suite may run serially beside another rig's small batches
  only with ≥ 6 G available. Record the check in the proof. GPU/E2E runs one at a time. Never kill
  another rig's process. The check and the heavy command are separate calls (or the check exits
  non-zero), never echo-then-run.
- **Engines.** Every xtb command sets
  `ETA_RXNCAT_XTB=/home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb` (without it the
  xtb E2E skips with exit 0). UMA runs in `.venv-accept-uma` on CUDA. Every E2E command runs
  under coreutils `timeout 3600`; an expiry is stop-and-report with the output.
- **Lessons (mission R26):** unit-suffixed numeric keys (R54); no energy- or record-ordered list
  in a compared output (R55); one `gated_outcome` per test, `pending_*` fails under
  `ETA_RXNCAT_ACCEPTANCE=1` (R56); any reader of a store or runner payload checks `failed_reason`
  first (R50); re-dedup after any geometry change (v0.3.0 path unchanged); tolerances are measured
  before they are written, never guessed; the candidate rule (code commit C1 with a clean tree,
  E2E at C1, then a commit of only `tests/candidate_outputs/v0.5.0/*` as C2).
- **Required checks** (AGENTS.md), all exit 0 before each commit: `uv sync --locked`;
  `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy`; `uv run pytest`;
  `UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base`.
- **Licence.** TJ, verbatim: "I would prefer to keep ASE out as it would be a major core
  dependency. The core work this repo does needs to be purely MIT/BSD/equivalent. The engines for
  DFT, MLIP, conf search can be copy left. Because they can be replaced with a new engine later.
  But the core remains." No agent-made licence exception (N1).
- **Stop and report.** A host fact that does not hold, a failed engine run, or a bound that fails
  is stop-and-report to the lead with the output. Never work around it; never loosen a tolerance
  (TJ's or this SPEC's). Never use `AskUserQuestion`.
- **Never** push, tag or open a PR.

## 1. The Confidence Mandate

**Score: 9/10.** Procedure, bytes, lists and bounds are fixed and measured. Open: whether PySCF's
grid reproduces Gaussian's `fine` grid within 1e-4 Eh (the controls decide; a miss is a stop).

## Mini-requirements

1. The six files exist with the sha256s above; `SOURCES.md` has the six rows and the References
   section.
2. **Tier D** (`tests/e2e/test_t3_inputs.py`, default suite, no engine): for each file the formula
   (`C7H10N4`, `C7H4F6N4`, `C4H4O`, `C9H10O`, `C4H6N4`, `C4N4F6`); RDKit `DetermineConnectivity`
   gives 2 fragments for each TS and 1 for each minimum, every H/F degree 1, no C below degree 3;
   each YAML's forming bonds are inter-fragment and within 1.9–2.7 Å (HF-2 values ± 1e-3); each
   active set equals the R16 rule applied to the YAML's forming bonds (re-derived in the test).
3. **Tier D:** each YAML loads with `load_ts_fixture`; each reference ΔG‡ recomputed from the YAML
   literature G values equals the References section within 1e-3; the window is that 1 M value ± 7
   (TS1b_n: [20, 34]).
4. **Tier D (graft, no engine):** the two TS4a grafts with mapping's `graft()` give C7H4F6N4, no
   close contacts, alignment RMSDs 0.1462 ± 1e-3 Å and 0.1463 ± 1e-3 Å, and the stated-rule map
   above (re-derived), forming-core `[0, 3, 6, 7]` RMSD to Liu's TS4a 0.0599 ± 1e-3 Å.
5. **R9 (marker `gpu` + `acceptance`, run in the proof):** all six energy differences recorded;
   every one ≤ 1e-4 Eh.

## 3. Implementation Plan (Task List)

- [x] Task 1: codegraph index → `index: ok`; record Start; read `tests/e2e/fixtures.py`,
  `tests/e2e/m1.py` (map rule), `SOURCES.md`, the evidence README.
- [x] Task 2: re-transcribe in scratch; compare sha256 (stop on a difference); copy into the repo.
- [x] Task 3: `SOURCES.md`; five YAMLs; `load_ts_fixture`.
- [x] Task 4: tier-D tests; required checks.
- [x] Task 5: host check; R9 PySCF runs (separate calls); record.
- [x] Task 6: commit; updater for node `eta_rxncat_species_runner` (`tests/e2e/**` covers the files).

## 4. The Negative Space (Constraints)

- **DO NOT** commit the SI PDFs or any extracted SI text; **DO NOT** execute the builder.
- **DO NOT** take coordinates from Liu's TS4a for the graft (N13).
- **DO NOT** quote a reference without its derivation and standard state (N9).
- **DO NOT** raise the 1e-4 Eh bound; **DO NOT** gate on a Paton electronic energy.

## Proof contract

- [ ] `sha256sum` of the six files equals the list above (command and output).
- [ ] `uv run pytest tests/e2e/test_t3_inputs.py -q` passes.
- [ ] The R9 run records six differences, all ≤ 1e-4 Eh (with the host check).
- [ ] The required checks exit 0.

## Source material

- Mission R6, R8, R9, R16, R22, HF-1, HF-2, HF-9, HF-10; `~/.hacf/eta-rxncat-hacf/evidence/v050-resolve-f6/`.

## Intent visual

N/A: non-visual slice.

## Status

- compiled

## Dependencies

- OPR.0.5.0.6 (build order; its code and contracts are used here)
- OPR.0.5.0.15 (replan 2, R30: the `cartesian_basis` option R9 sets)
