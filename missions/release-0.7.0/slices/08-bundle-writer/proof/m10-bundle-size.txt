# Slice 08 proof: 3Dmol integrity and M10

## 3Dmol.js 2.5.5 integrity (R20, HF-5; downloaded 2026-11-26 into a fresh dir under TMPDIR, never executed)

```
curl -sSfo 3dmol-2.5.5.tgz https://registry.npmjs.org/3dmol/-/3dmol-2.5.5.tgz        exit 0
npm view 3dmol@2.5.5 dist.integrity
  sha512-kqNHouGqq3YfW58174tdERvm0XYTmP0tavQKOqIw1ouc2OJ7epkXEFrtEkVXV0clBZT2Ze2xHRC/qxX0u0qCdw==
openssl dgst -sha512 -binary 3dmol-2.5.5.tgz | base64 -w0  (prefixed sha512-)
  sha512-kqNHouGqq3YfW58174tdERvm0XYTmP0tavQKOqIw1ouc2OJ7epkXEFrtEkVXV0clBZT2Ze2xHRC/qxX0u0qCdw==
sha256 3dmol-2.5.5.tgz              26d91c5036d4efe78fc032c22cb692fea92bbb3cb1e65d20bf3869673fb3d8f5
sha256 package/build/3Dmol-min.js   f7cc78921ae72e7623e89cdd111434f58c2efddd2ffda1cd212644b406fb8016  (537792 bytes)
sha256 package/LICENSE              4c6eaaed856f3f28a3b1a98e74f4a8a71618de7d51ea4155c29f6f793bcef861
```

The vendored copies under `src/eta_rxncat/review/assets/` have the same two sha256 values.

## M10: bundle size (stop-and-report gate: not triggered)

Raw files: `~/.hacf/eta-rxncat-hacf/evidence/v070-slice08/` (`run.sh`, `regen.py`, `extrap.py`,
`hostcheck.txt`, `time.txt`, `m10_smoke.json`, `m10_extrapolation.json`, `run_record.json`).

**Input.** Slice 06 kept no store, and its `smoke.py` writes none. `regen.py` repeats that smoke
(ethyl graft on TS1a_n, GFN2, geomeTRIC, `maxiter` 200) through the ensemble's cached
pre-relaxation (`_PreRelax`) into a scratch store, then runs `export_run_data` and
`write_review_bundle`. Command: `bash run.sh` (blocking host check
`v070-slice06/hostcheck.sh` in an exiting loop, scratch cwd, `timeout 600`,
`ETA_RXNCAT_XTB` set). Verdict `avail=12G gpu_apps=0 heavy=0 eta=0` at 10:10:35Z; another rig's
HACF pytest was listed but under the check's thresholds. Exit 0; scratch cwd left empty. Result:
24 atoms, 8 engine calls, 8 frames (the same counts as slice 06), 925-1133 bytes per frame
(at most 47.2 bytes per atom), bundle 568101 bytes (542319 of them assets). A first attempt
passed the check, ran the pre-relaxation and then failed building the record (my script:
neither `chosen_template_id` nor `stop_reason`); its store was removed and the run repeated.

**Extrapolation** (`extrap.py`, no engine): one smoke ensemble of one pre-relaxation does not
give a per-ensemble size, so frame counts come from resolve's four real HF-3 exo stores (copies;
v0.6.0 rows, so no stored frames): frames = pre-relax engine calls + P-RFO history lengths.
Non-trajectory and static-HTML bytes are measured by a real dry export and bundle write of
those rows.

| Ensemble (exo) | atoms | rows pre/ts/freq | frames | longest TS search | trajectory est. (B) | other run data (B) | static HTML (B) |
|---|---|---|---|---|---|---|---|
| ethyl GFN2 | 24 | 10/11/11 | 440 | 8 | 498 520 | 53 303 | 9 465 |
| ethyl UMA | 24 | 10/11/11 | 559 | 7 | 633 347 | 53 240 | 9 459 |
| n-propyl GFN2 | 27 | 10/11/11 | 547 | 14 | 697 220 | 57 139 | 10 243 |
| n-propyl UMA | 27 | 10/11/11 | 485 | 11 | 618 193 | 57 125 | 10 238 |

| E2E (11 ensembles: 8 G7 units, endo taken equal to exo, + 3 G8 at the largest) | bytes |
|---|---|
| ensemble trajectories | 6 986 220 |
| endpoint trajectories, **allowance, not measured** (7 x 20 rows x 60 frames x 16 atoms) | 6 344 800 |
| other run data (incl. 140 000 endpoint allowance) | 753 031 |
| static HTML | 109 539 |
| assets | 542 319 |
| **bundle, no decimation** (run data twice) | **28 820 960** |
| **bundle at the budget** (`TRAJECTORY_BYTE_BUDGET` = 10 000 000) | **<= 22 158 920** (2.8 MB under 25 000 000) |

- **Budget chosen:** 10 000 000 bytes of canonical `trajectories`, used by `review-bundle`.
- **Decimation:** at most stride 2 (every other frame, plus each last frame) with the endpoint
  allowance; none for the ensembles alone (about 7.5 MB). This is not below every-other frame on
  TS searches, so M10 does not stop. The stride is one common value (slice 07).
- **Limits of the estimate:** the endpoint rows and the G8 runs are assumptions, and bytes per
  frame come from one 8-frame trajectory. Slice 13 measures the real bundle against 25 MB.
