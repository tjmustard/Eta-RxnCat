---
slice: OPR.0.7.1.2
candidate_sha: df4e674
artifact_type: guard
verdict: CLEAR
money_evidence: full pytest 2755 passed, 0 skipped; 8 Tier O ids pass; M2 added
  40.0 s (limit 60 s); 9/9 seam breaks fail
---

# Execute evidence: 02-tier-o-seams (OPR.0.7.1.2) - builder (not a QA verdict)

The artifact type is `guard` only because `hyper_spec.py proof` has no `execute` type; the audit
writes the QA verdict.

Start `16c7c86`. C1 `c3f548a` (the one test file). C2 `df4e674` (updater flags, progress, task
boxes, field note). Then this proof. No push, no tag.
`E` = `~/.hacf/eta-rxncat-hacf/evidence/v071-slice02`.

## Commands and exit codes

`TMPDIR=~/.cache/eta-rxncat-tmp`; `ETA_RXNCAT_XTB` set for the default-suite runs; uv commands
under `timeout 3600`.

| command | exit | seen |
|---|---|---|
| `hyper_codegraph.py index` (start, and again before the updater) | 0 | `index: ok` |
| `hyper_spec.py progress --event executing` / `executed` | 0 / 0 | |
| `uv run pytest tests/integration/test_seams_offline.py tests/integration/test_integration_policy.py -q --durations=8` | 0 | 65 passed |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run ruff format --check . --extend-exclude spec/archive --extend-exclude spec/process` | 0 | 862 files already formatted |
| `uv run mypy` | 0 | no issues, 91 source files |
| `uv run pytest -q --junitxml=E/m2_after2.xml` (the full check) | 0 | 2755 passed, 196 deselected, 0 skipped |
| `uv run pytest tests/integration -q --junitxml=E/integration.xml` | 0 | 65 passed |
| `hyper_ledger.py ensure-node --from-spec <SPEC>` | 0 | no change |
| `hypergraph_updater.py --from-diff 16c7c86 --apply --slice OPR.0.7.1.2 --json` (once) | 0 | below |
| `hyper_ledger.py validate` | 0 | ok |

During iteration one `ruff check` / `ruff format --check` on `tests/integration` failed (one long
line); fixed with `ruff format` before the runs above. The full check ran on the tree that became
C1; later changes are mission files and ledger flags.

## M2 (requirement 1)

`uv run pytest -q`, junit `time`, same host. Each measured run was preceded by a blocking host
check (no test or xtb process, load1 < 5); the runs marked "clean" were also sampled every 5 s for
other projects' test processes.

| run | tree | junit time | tests | other test processes | used |
|---|---|---|---|---|---|
| `m2_before` | Start | 301.881 s | 2747 | `hakf-v0.3.0-live` pytest seen running right after the run (no sampler yet) | no |
| `m2_before2` | Start | **210.117 s** | 2747 | 0 samples (clean) | **before** |
| `m2_after` | with the file | 290.105 s | 2755 | 41 samples, `hakf-v0.3.0-live` | no |
| `m2_after2` | with the file | **250.127 s** | 2755 | 0 samples (clean) | **after** |

**Added wall: 40.0 s (limit 60 s): within budget.** The 8 new cases take 11.2 s in `m2_after2`
(T-O1 to T-O3 are almost all of it; 19.9 s in the integration-only run). The rest of the 40 s is
the other 2747 tests running slower in that run (junit case sum 208.7 s before, 248.7 s after),
so run-to-run variation on this host is of the order of 30 s. The GPU was not checked; no GPU
test runs in the default suite.

## Tests by id (requirement 2; `E/integration.xml` and `E/m2_after2.xml`)

All `passed`, 0 skipped: `test_to1_species_runner_store_roundtrip`,
`test_to2_reaction_energies_replay_from_reopened_store`,
`test_to3_conformer_stage_stores_members`, `test_to4_enumerator_runs_the_real_graft`,
`test_to5_candidate_graph_file_roundtrip`, `test_to6_enumerated_seed_inputs[TS1a_n]`,
`test_to6_enumerated_seed_inputs[TS1a_x]`, `test_plan_loader_parity` (all in
`tests/integration/test_seams_offline.py`). The slice-01 policy test passes over the new file
(requirement 4).

## Seam breaks, builder's own check (requirement 3; the audit's R22 run is the record)

Throwaway worktree at Start plus the test file, R22 interpreter,
`PYTHONPATH=<worktree>/src`, import path confirmed under the worktree, no `uv` there, worktree
removed. The test file was the committed one. Log: `E/seam_breaks_builder.log`. Unbroken: 8
passed.

| break | edit | outcome |
|---|---|---|
| T-O1 identity | delete the `engine_identity` line of `stage_payload` | fail |
| T-O1 get | `ArtifactStore.get` returns `None` | fail |
| T-O2 | `reaction_free_energy` sums `spec.reactants[1:]` | fail |
| T-O3 | the conformer stage does not `_save` | fail |
| T-O4 bonds | `_graft_template` uses an identity `position` | fail |
| T-O4 stages | `_remap_stages` uses an identity `position` | fail |
| T-O5 | dump excludes node `priority` | fail |
| T-O6 | seed bonds mapped back to template indices | fail (both ids) |
| parity | conftest loader `base = ROOT` | fail |

Control (`E/seam_breaks_without_variant.log`): with the variant-plan assertions removed, both
T-O4 breaks and the T-O6 break **pass** (survive).

## Ledger

`eta_rxncat_integration` before and after `ensure-node`: `files ['tests/integration/**']`,
`spec_refs ['OPR.0.7.1.1']`, description 800 chars. No description words added anywhere, so no
compression. Updater: nodes `[eta_rxncat_integration]` (dirty), blast radius the same single node,
`lore_stale_candidates []`, no lore file changed. `unmapped` (104): the 3 mission files, the two
`.claude/*.bak-*`, and untracked `spec/archive/**` and `spec/process/**` paths (names only in the
updater output; no file there was opened or staged).

## For the audit to rule on

1. T-O4 and T-O6 assert more than the SPEC lists: a second plan built in the test
   (`_moved_atom_plan`) where each TS node's second forming bond names template atom 17 (product
   index 16) and its stage freezes atom 17. On the R21 plan the TS nodes name only atoms 0-5 and
   freeze nothing, so the listed index-remap and reference-bond breaks cannot fail the test there
   (control above). All SPEC assertions run on the unmodified plan; the variant is not chemistry
   and runs no engine. `find_clash` is asserted on the unmodified plan only.
2. Mission R36 also says the run-time fallback construct's rank 1 (TS1a_x geometry in the endo
   node) "gives the face mismatch before any search". The slice SPEC's T-O6 omits it, and it is
   **not built**: in `run_ts_with_fallback` the face check follows the pre-relaxation, which needs
   the engine this slice forbids. The lead or resolve may want to place or drop that gate.
3. `find_clash(seed)` is called as `find_clash(seed.start, [*perceive_bonds(seed.start),
   *seed.forming_bonds])`; the function takes a state and a topology.
4. T-O3 uses 1-propanol (`n_embed=3`, 3 records) so the weight sum covers more than one record;
   butane at `n_embed=3` keeps one. T-O1 and T-O2 use butane (T-O2: butane to isobutane).
5. T-O1 adds an assertion that a frequency row is not found under another engine version; without
   it the identity break leaves rerun and fresh-store keys equal. T-O1's `ThermoResult` round trip
   goes through a second store's `put`/`get` under that row's key (thermo itself is never stored
   by the runner). T-O2 also checks dG against the two ensembles' Gibbs energies of the same run;
   without it a dropped term replays equal.
6. Two of the four M2 runs are discarded for overlap (table above); both were kept in `E`.
7. `ensure-node` adds no `spec_refs` entry for this slice; the updater set
   `provenance.last_slice: OPR.0.7.1.2`.
8. Three commits (code; flags; proof), as slice 01.
