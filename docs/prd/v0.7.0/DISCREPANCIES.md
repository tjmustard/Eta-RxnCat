# v0.7.0 starter discrepancy register

**Purpose.** `PRDs/Eta-RxnCat-v0.7.0.zip` (sha256
`ad7b761635526395120d9369a4653c5a90005306ff96f6813bfa5cdc5f3f0b25`) ships a starter implementation,
unpacked here under `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/` (38 files, byte-identical to the zip, plus the
gate file `.ruff.toml`, which is not part of the starter and keeps the pre-commit lint off it). The
plan copy inside it, `Eta-RxnCat-v0.7.0/Eta-RxnCat_Living_Master_Plan.md`, has sha256
`ea483e29098fe9e327b71a6ae0f66ddbe4ff8c924e29e82b1bdf1148148e3cb6`, the same bytes as the authoritative
`PRDs/` plan. The starter is reference only: the code in `src/` and `tests/` is written fresh from the
mission's slice specs, and no code is copied from it. This register records every difference between the
starter and the rewrite, so each one can be reviewed and fixed if needed.

TJ, Q2 (v0.3.0, standing): "B use it as reference only. Keep a list of the discrepancies so that if
needed, we can go through each of them and fix any issues that arise."

**Clean room.** The starter's code was not read to write this register: the rows take their text from
mission §5 "Starter discrepancies" of `missions/release-0.7.0/SPEC.md`. (Slice 01's lint measurement
with the gate in the wrong place printed a few starter lines in ruff's diagnostics; nothing was copied.)

## Scope

The rows of mission `missions/release-0.7.0/SPEC.md` §5 "Starter discrepancies". Starter paths are
relative to `docs/prd/v0.7.0/Eta-RxnCat-v0.7.0/`. R-, Q- and G-numbers cite the mission SPEC.

**Status.** `open` means the row is logged and no audit has yet named it as satisfied. The Slice column
names the implementing slice or slices. An audit lists a row in its PASS handoff when its slice
satisfies it, and the scribe closes it at v0.7.0 docs time.

**Version strings.** Compared by sha256 with the v0.6.0 starter, five files differ or are new: the plan
copy, `pyproject.toml`, `src/eta_rxncat/__init__.py`, `src/eta_rxncat/mapping/enumerator.py` (new) and
`tests/unit/test_v070_enumerator.py` (new).

## Starter files (sha256, sorted by path)

```
be9a8b1192d13313be459dfc026e2119d60ade8e0d708080a999509792d8401b  Eta-RxnCat-v0.7.0/AGENTS.md
ea483e29098fe9e327b71a6ae0f66ddbe4ff8c924e29e82b1bdf1148148e3cb6  Eta-RxnCat-v0.7.0/Eta-RxnCat_Living_Master_Plan.md
0142d01d180d7682bb00d458f7320ca256152a2d3db06da53d6bbc37e718806a  Eta-RxnCat-v0.7.0/README.md
ea7562a29a654e221df2d193298c902425114690de111a97d77727c8fcc5276a  Eta-RxnCat-v0.7.0/pyproject.toml
0505f8713d77560b718d5371d1e12c4659eb3a7294f8e07771c8620c9140eba6  Eta-RxnCat-v0.7.0/src/eta_rxncat/__init__.py
4c1f0353223fb5d1e5bc2bfe7c473a5d4ae7f7d95a5748311e290ade62eaf89c  Eta-RxnCat-v0.7.0/src/eta_rxncat/cli.py
463b53ab83c27dd23d0df67693a8968fba186d38a911e99007e69532e388bd08  Eta-RxnCat-v0.7.0/src/eta_rxncat/conformers/__init__.py
d3d5fb49e23d28a98d93a5b26c58f3b78186a339b0e3ee259e78b62e5263eb72  Eta-RxnCat-v0.7.0/src/eta_rxncat/conformers/ensemble.py
71af842c0cc19380273a916c4e068ce23b7c48c83a7b86ebd1d5daaa709c4d93  Eta-RxnCat-v0.7.0/src/eta_rxncat/core/__init__.py
13634dec4b731c9d85e1c6865b45d2310e1bff1c9ecdb29b24590f8d862f9fd0  Eta-RxnCat-v0.7.0/src/eta_rxncat/core/models.py
6b2b85a536e58156e7e1bf005ebe86f52595d34d5b35f8fa1e463227924a25ae  Eta-RxnCat-v0.7.0/src/eta_rxncat/core/reaction_graph.py
1a7faff35ed4f5a8487241ac2b18914b7d7be5807dd97e0988bd3a8c81beb1ed  Eta-RxnCat-v0.7.0/src/eta_rxncat/core/thermo.py
472fcbd4d8da15105307aa9aabc774c5d8b13afb8c8c6cd1daca98a02d1e5e54  Eta-RxnCat-v0.7.0/src/eta_rxncat/engines/__init__.py
23177208c1770212f3c4b74538cb230cf766ad2fa170f2ebab663cadf4e738df  Eta-RxnCat-v0.7.0/src/eta_rxncat/engines/base.py
7651aec1a626da6abb4568833d97ad0c6836c7b22cff1801863afbb8ec320156  Eta-RxnCat-v0.7.0/src/eta_rxncat/engines/mlip.py
2b214584bc6adfe6704a654b9045965bcf968f18985d28186b2d53d59076faa7  Eta-RxnCat-v0.7.0/src/eta_rxncat/engines/pyscf_engine.py
fbd24e11b4c1269abddb2db9a378a32409e8c34c03cb8486592d6c2859d73a96  Eta-RxnCat-v0.7.0/src/eta_rxncat/engines/rdkit_xtb.py
8f7611a72f269f757fb8345851dd3357d51f857034ad3df36a54007994097071  Eta-RxnCat-v0.7.0/src/eta_rxncat/mapping/__init__.py
9fd962372458dc60998b86fa5730a6dc1e53df4b837c3bcb1362267c99a101ec  Eta-RxnCat-v0.7.0/src/eta_rxncat/mapping/core_mapper.py
a13bc8851d3f133ab3db41f02c51e0a3aef888d3c08454386871c6d993920735  Eta-RxnCat-v0.7.0/src/eta_rxncat/mapping/enumerator.py
acae51005256dfe263067472a1388d44a63af9a10ba3f3173575bf1f95b67c86  Eta-RxnCat-v0.7.0/src/eta_rxncat/optimize/__init__.py
6320acfa603878c6698bd931dfe706ae577c599320d30da5cad1d01a422f42e5  Eta-RxnCat-v0.7.0/src/eta_rxncat/optimize/gs_optimizer.py
da3ac514ecafbd1829cab3e93f44f3ae3a2fc97934faf626bb1149694edc99f1  Eta-RxnCat-v0.7.0/src/eta_rxncat/optimize/ts_optimizer.py
00a569d23af4560266bf0366132139c0d441c58af6cd17e4b38be9f582713814  Eta-RxnCat-v0.7.0/src/eta_rxncat/orchestrator/__init__.py
5ddd3aa41b9337d70ce25e64f035ccf174292522e89d5785aeb13bcb1b3a9c2b  Eta-RxnCat-v0.7.0/src/eta_rxncat/orchestrator/selectivity.py
54c757b6364550b5f5cf70d4609640067abed565b898170b229a0b595e2fdfb4  Eta-RxnCat-v0.7.0/src/eta_rxncat/store/__init__.py
893c7654b6842912c3bd6fc9e528def8ffc64623f606f03aad02f94b9d018486  Eta-RxnCat-v0.7.0/src/eta_rxncat/store/artifact_store.py
9d0cfcd002e95e69b35cb9dbbf828b18a05de0e963b7f6a22e3719d6a27ea14e  Eta-RxnCat-v0.7.0/src/eta_rxncat/utils/__init__.py
c7ff3b3fac91b73a9e5243d122ef21a3343e2ccb3687adc220b8453fae50fb0e  Eta-RxnCat-v0.7.0/src/eta_rxncat/utils/hw_probe.py
4905299ad38147ce2fc29527cd2812bf707f11187bb76bd01ac1e2830872a319  Eta-RxnCat-v0.7.0/tests/e2e/fixtures/example_reaction_graph.yaml
19daf6124b844070c4e6ad96a02dac7e17d5d89640b9b83a993708440aff02a7  Eta-RxnCat-v0.7.0/tests/unit/test_core_schemas.py
ad17d0bd4c47e724df63ad88cd62c9a5451723cef379d4411d8105d73a56ec78  Eta-RxnCat-v0.7.0/tests/unit/test_engines_v020.py
3a579cfbce91c86a4bb813ddd3a537b208d8fd77742a98e1f2c267256dcb8ca8  Eta-RxnCat-v0.7.0/tests/unit/test_hw_probe.py
1496c28244a0f8374bef60ab81328aa08c5c36190658f44a2e2c754c6fa29ef0  Eta-RxnCat-v0.7.0/tests/unit/test_v030_thermo_conformers.py
7091704036f57eb9705822095f4bbca8203d1c81c65bd6f764eb99bdd7c64107  Eta-RxnCat-v0.7.0/tests/unit/test_v040_core_mapper.py
0258f127b8059f74a49357f1270b260462d6f930ade98eb28494ed479c2f1ea8  Eta-RxnCat-v0.7.0/tests/unit/test_v050_ts_prfo.py
fff8b525139897cb6d84b8539093cb3d13de9fd8d6e9dad6630892d088455d3d  Eta-RxnCat-v0.7.0/tests/unit/test_v060_selectivity.py
177384780aa63dcb3a45498f7a26a17cbc2872271d3d38b7be7a1a67280fc7d6  Eta-RxnCat-v0.7.0/tests/unit/test_v070_enumerator.py
```

## Register

| Row | Starter | Starter does | eta v0.7.0 | Slice | Status |
|---|---|---|---|---|---|
| DV-01 | plan copy | equals the authoritative plan (sha256 `ea483e29…3cb6`) | PLAN_DISCREPANCIES: agrees; no new PD row | 01 | open |
| DV-02 | `SubstituentCandidate` | one fragment `AtomMappingSpec` | `LibraryEntry` + per-template `SiteTemplateMap` → `GraftSpec`, with `fragment_orders` | 02, 03 | open |
| DV-03 | `charge_delta` | `charge = template.charge + delta`; multiplicity copied | declared delta/multiplicity, parity refused, cross-node check | 02, 03 | open |
| DV-04 | `select_best_template` | reorders by lowest RMSD | declared rank; RMSD is a gate | 03 | open |
| DV-05 | after the graft | identity keep + alignment `[0, 1, 2]` | keeps `index_map` | 02, 03 | open |
| DV-06 | models | `template_id` / `priority_rank` / `structure` / `stoichiometry_multipliers` | schema 1 `id` / `rank` / `components` | 02 | open |
| DV-07 | template loop | silent `continue` on a count mismatch | recorded refusal | 03 | open |
| DV-08 | `target_node_ids=None` | grafts every node | only declared (node, template) pairs | 03 | open |
| DV-09 | — | no multi-site | Cartesian product with a cap | 04 | open |
| DV-10 | `pyproject.toml` | `version = "0.7.0"`, `ruff>=0.7.0` | bump in slice 14; ruff pin not adopted | 14 | done (v0.7.0 slice 14 set version 0.7.0; closed on TJ's choice, relay qitem-20261127204642-06c18509e72ce4bb) |
