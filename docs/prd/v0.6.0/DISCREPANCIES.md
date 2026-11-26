# v0.6.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.6.0.zip` (sha256
`0c1b1f6ebf810c8bab904f018d816bbd0d561f6055d7130aaad36509d78a88b7`) ships a starter implementation,
unpacked here under `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/` (36 files, byte-identical to the zip, plus the
gate file `.ruff.toml`, which is not part of the starter and keeps the pre-commit lint off it). The
plan copy inside it, `Eta-RxnCat-v0.6.0/Eta-RxnCat_Living_Master_Plan.md`, has sha256
`ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438`, the same bytes as the v0.4.0 and
v0.5.0 plan copies. The starter is reference only: the code in `src/` and `tests/` is written fresh from
the mission's slice specs, and no code is copied from it. This register records every difference between
the starter and the rewrite, so each one can be reviewed and fixed if needed.

TJ, Q2 (v0.3.0, standing): "B use it as reference only. Keep a list of the discrepancies so that if
needed, we can go through each of them and fix any issues that arise."

**Clean room.** The starter's code was not opened for this register (it is named only). Rows DV-02…DV-09
take their text from mission §5 "Starter discrepancies" of `missions/release-0.6.0/SPEC.md`.

## Scope

The rows of mission `missions/release-0.6.0/SPEC.md` §5 "Starter discrepancies". Starter paths are
relative to `docs/prd/v0.6.0/Eta-RxnCat-v0.6.0/`. R-, Q- and HF-numbers cite the mission SPEC.

**Status.** `closed (audits NN, …)` means each listed audit handoff named the row as satisfied; the scribe closed it at v0.6.0 docs time. `open` means the row is logged and its v0.6.0 decision is not yet built. The Slice column
names the implementing slice or slices from the mission's execution checklist. An audit lists a row in its
PASS handoff when its slice satisfies it, and the scribe closes it at v0.6.0 docs time.

**Version strings.** Compared by sha256 with the v0.5.0 starter, 32 of the 36 files are byte-identical,
including the plan copy, `AGENTS.md` and `README.md`. Four differ: `src/eta_rxncat/orchestrator/selectivity.py`
(new) and `tests/unit/test_v060_selectivity.py` (new), whose rows are below, and `pyproject.toml` and
`src/eta_rxncat/__init__.py`, which differ only in the version string (`0.5.0` → `0.6.0`). eta's own version
stays `0.5.0` until the acceptance verdict passes; slice 12 bumps it on pass (mission execution checklist).

## Starter files (sha256, sorted by path)

```
be9a8b1192d13313be459dfc026e2119d60ade8e0d708080a999509792d8401b  Eta-RxnCat-v0.6.0/AGENTS.md
ad092dff7de6f43791b9dbb2a6cc9c6ac4a636c7c8acf9afc71db30488366438  Eta-RxnCat-v0.6.0/Eta-RxnCat_Living_Master_Plan.md
20d940c99526bf765ba48db1b00603cc4e939a7d3973dbc93ba835d0bc1a5013  Eta-RxnCat-v0.6.0/pyproject.toml
0142d01d180d7682bb00d458f7320ca256152a2d3db06da53d6bbc37e718806a  Eta-RxnCat-v0.6.0/README.md
4c1f0353223fb5d1e5bc2bfe7c473a5d4ae7f7d95a5748311e290ade62eaf89c  Eta-RxnCat-v0.6.0/src/eta_rxncat/cli.py
d3d5fb49e23d28a98d93a5b26c58f3b78186a339b0e3ee259e78b62e5263eb72  Eta-RxnCat-v0.6.0/src/eta_rxncat/conformers/ensemble.py
463b53ab83c27dd23d0df67693a8968fba186d38a911e99007e69532e388bd08  Eta-RxnCat-v0.6.0/src/eta_rxncat/conformers/__init__.py
71af842c0cc19380273a916c4e068ce23b7c48c83a7b86ebd1d5daaa709c4d93  Eta-RxnCat-v0.6.0/src/eta_rxncat/core/__init__.py
13634dec4b731c9d85e1c6865b45d2310e1bff1c9ecdb29b24590f8d862f9fd0  Eta-RxnCat-v0.6.0/src/eta_rxncat/core/models.py
6b2b85a536e58156e7e1bf005ebe86f52595d34d5b35f8fa1e463227924a25ae  Eta-RxnCat-v0.6.0/src/eta_rxncat/core/reaction_graph.py
1a7faff35ed4f5a8487241ac2b18914b7d7be5807dd97e0988bd3a8c81beb1ed  Eta-RxnCat-v0.6.0/src/eta_rxncat/core/thermo.py
23177208c1770212f3c4b74538cb230cf766ad2fa170f2ebab663cadf4e738df  Eta-RxnCat-v0.6.0/src/eta_rxncat/engines/base.py
472fcbd4d8da15105307aa9aabc774c5d8b13afb8c8c6cd1daca98a02d1e5e54  Eta-RxnCat-v0.6.0/src/eta_rxncat/engines/__init__.py
7651aec1a626da6abb4568833d97ad0c6836c7b22cff1801863afbb8ec320156  Eta-RxnCat-v0.6.0/src/eta_rxncat/engines/mlip.py
2b214584bc6adfe6704a654b9045965bcf968f18985d28186b2d53d59076faa7  Eta-RxnCat-v0.6.0/src/eta_rxncat/engines/pyscf_engine.py
fbd24e11b4c1269abddb2db9a378a32409e8c34c03cb8486592d6c2859d73a96  Eta-RxnCat-v0.6.0/src/eta_rxncat/engines/rdkit_xtb.py
eaeb5a1f57dc37b0a39db9dfbfcd88672b978a0c44eec7f9f715e28dac24785c  Eta-RxnCat-v0.6.0/src/eta_rxncat/__init__.py
9fd962372458dc60998b86fa5730a6dc1e53df4b837c3bcb1362267c99a101ec  Eta-RxnCat-v0.6.0/src/eta_rxncat/mapping/core_mapper.py
8f7611a72f269f757fb8345851dd3357d51f857034ad3df36a54007994097071  Eta-RxnCat-v0.6.0/src/eta_rxncat/mapping/__init__.py
6320acfa603878c6698bd931dfe706ae577c599320d30da5cad1d01a422f42e5  Eta-RxnCat-v0.6.0/src/eta_rxncat/optimize/gs_optimizer.py
acae51005256dfe263067472a1388d44a63af9a10ba3f3173575bf1f95b67c86  Eta-RxnCat-v0.6.0/src/eta_rxncat/optimize/__init__.py
da3ac514ecafbd1829cab3e93f44f3ae3a2fc97934faf626bb1149694edc99f1  Eta-RxnCat-v0.6.0/src/eta_rxncat/optimize/ts_optimizer.py
00a569d23af4560266bf0366132139c0d441c58af6cd17e4b38be9f582713814  Eta-RxnCat-v0.6.0/src/eta_rxncat/orchestrator/__init__.py
5ddd3aa41b9337d70ce25e64f035ccf174292522e89d5785aeb13bcb1b3a9c2b  Eta-RxnCat-v0.6.0/src/eta_rxncat/orchestrator/selectivity.py
893c7654b6842912c3bd6fc9e528def8ffc64623f606f03aad02f94b9d018486  Eta-RxnCat-v0.6.0/src/eta_rxncat/store/artifact_store.py
54c757b6364550b5f5cf70d4609640067abed565b898170b229a0b595e2fdfb4  Eta-RxnCat-v0.6.0/src/eta_rxncat/store/__init__.py
c7ff3b3fac91b73a9e5243d122ef21a3343e2ccb3687adc220b8453fae50fb0e  Eta-RxnCat-v0.6.0/src/eta_rxncat/utils/hw_probe.py
9d0cfcd002e95e69b35cb9dbbf828b18a05de0e963b7f6a22e3719d6a27ea14e  Eta-RxnCat-v0.6.0/src/eta_rxncat/utils/__init__.py
4905299ad38147ce2fc29527cd2812bf707f11187bb76bd01ac1e2830872a319  Eta-RxnCat-v0.6.0/tests/e2e/fixtures/example_reaction_graph.yaml
19daf6124b844070c4e6ad96a02dac7e17d5d89640b9b83a993708440aff02a7  Eta-RxnCat-v0.6.0/tests/unit/test_core_schemas.py
ad17d0bd4c47e724df63ad88cd62c9a5451723cef379d4411d8105d73a56ec78  Eta-RxnCat-v0.6.0/tests/unit/test_engines_v020.py
3a579cfbce91c86a4bb813ddd3a537b208d8fd77742a98e1f2c267256dcb8ca8  Eta-RxnCat-v0.6.0/tests/unit/test_hw_probe.py
1496c28244a0f8374bef60ab81328aa08c5c36190658f44a2e2c754c6fa29ef0  Eta-RxnCat-v0.6.0/tests/unit/test_v030_thermo_conformers.py
7091704036f57eb9705822095f4bbca8203d1c81c65bd6f764eb99bdd7c64107  Eta-RxnCat-v0.6.0/tests/unit/test_v040_core_mapper.py
0258f127b8059f74a49357f1270b260462d6f930ade98eb28494ed479c2f1ea8  Eta-RxnCat-v0.6.0/tests/unit/test_v050_ts_prfo.py
fff8b525139897cb6d84b8539093cb3d13de9fd8d6e9dad6630892d088455d3d  Eta-RxnCat-v0.6.0/tests/unit/test_v060_selectivity.py
```

## Register

| ID | Source | Behaviour there | v0.6.0 decision | Slice | Status |
|---|---|---|---|---|---|
| DV-01 / PD-010 | starter plan vs zip, PR #12, #13 | plan: "% ee / regioselectivity"; zip adds "*(Done when unit tests verify selectivity math and branch pruning.)*" | the `PRDs/` plan governs (TJ Q1 "A"); the zip's added done-criterion is logged, not followed. PD-010 status set to `logged as DV-01` in slice 01. | 01, 04, 07 | closed (audit 07) |
| DV-02 | starter `core.reaction_graph` (mission §5) | `core.reaction_graph.PruningRule(rule_id, metric, reference_node_id, target_node_id, operator, threshold, on_fail)` | eta's `core.graph.PruningRule(id, description, parameters)` stays as it is; a new `PathwayPruningRule` sits beside it (R7, R23). | 02, 07 | closed (audit 07) |
| DV-03 | `src/eta_rxncat/orchestrator/selectivity.py` in the starter (mission §5; file not opened) | own physical constants, and an exponent clamp at 500 | `eta_rxncat.thermo` constants and log-sum-exp, no clamp. | 04 | closed (audit 04) |
| DV-04 | `src/eta_rxncat/orchestrator/selectivity.py` in the starter (mission §5; file not opened) | compares two TSs; plan says "Boltzmann-weighted" | TJ Q1 B: each pathway's G is a Boltzmann sum over its validated, deduplicated TS ensemble. | 04, 06 | closed (audits 04, 06; lead ruling) |
| DV-05 | `src/eta_rxncat/orchestrator/selectivity.py` in the starter (mission §5; file not opened) | a global `skip_remaining_nodes` | per-pathway pruning of the computed minor pathway's priority ≥ 2 nodes (TJ Q2 A, R7). | 07 | closed (audit 07) |
| DV-06 | TJ's Tier 4 YAMLs | forming-bond indices `[0,2,3,4]`, product label `P1a_n`; "% ee" for a diastereomeric pair | schema 1; indices `[1,2,3,5]`; `P1a_n` → `P1b_x` (Q-E4); the quantity is reported as % de. | 08 | closed (audit 08; TJ Phase 3, R31) |
| DV-07 | starter overall | no TS conformer search | added per TJ Q1 B (sampler and ensemble runner). | 05, 06 | closed (audit 06) |
| DV-08 | `src/eta_rxncat/orchestrator/selectivity.py` in the starter (mission §5; file not opened) | `kind="ee"` accepted over any pathway | `kind="ee"` is refused over multi-member ensembles (R8, `SelectivityInputError`). | 04 | closed (audit 04) |
| DV-09 | draft TS sampler in mission §5 (R16, HF-4; not in the starter, which has no TS sampler, DV-07) | ETKDG with a coordMap over the two-fragment TS graph | per-fragment ETKDGv3 embedding plus a seeded non-core perturbation (R16; the draft fails by measurement, HF-4). | 05 | closed (audit 05) |
