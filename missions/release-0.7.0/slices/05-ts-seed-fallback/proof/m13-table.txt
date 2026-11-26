# M13: guarded pre-relax wall vs load, GFN2 TS1a_n, library default ensemble sizes

One `run_ts_ensemble_detailed` per window (`TSEnsembleOptions()`: n_embed 10, n_perturb 10, max_research 10), xtb 6.8.0,
scratch cwd and store. Instrument: wraps `relax_constrained_core` in `ts_ensemble` (scratch script, not committed).
CPU = self + reaped children (`os.times()`). `CPU/n_cpu` is the CPU normalised by 20 logical CPUs.
`R7 budget` = min(1200, 600 x max(1, load1_start / 20)), computed by the instrument before R7 was written.

## loaded

| # | outcome | wall s | load1 start | load1 end | n_cpu | CPU s | CPU/wall | CPU/n_cpu s | R7 budget s | wall/budget |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ok | 6.7 | 30.6 | 32.0 | 20 | 113 | 17.0 | 5.7 | 918 | 0.007 |
| 2 | ok | 15.8 | 30.9 | 33.9 | 20 | 271 | 17.1 | 13.6 | 928 | 0.017 |
| 3 | ok | 23.7 | 36.2 | 43.6 | 20 | 319 | 13.5 | 16.0 | 1085 | 0.022 |
| 4 | ok | 2.8 | 44.8 | 42.8 | 20 | 53 | 19.3 | 2.7 | 1200 | 0.002 |
| 5 | CoreDisplacementError | 169.3 | 39.5 | 25.0 | 20 | 3080 | 18.2 | 154.0 | 1186 | 0.143 |
| 6 | ok | 8.9 | 25.0 | 24.6 | 20 | 164 | 18.5 | 8.2 | 749 | 0.012 |
| 7 | ok | 12.1 | 24.5 | 24.0 | 20 | 233 | 19.2 | 11.6 | 736 | 0.016 |
| 8 | ok | 5.2 | 22.2 | 22.0 | 20 | 98 | 18.8 | 4.9 | 665 | 0.008 |
| 9 | ok | 6.7 | 20.3 | 20.8 | 20 | 127 | 18.9 | 6.4 | 609 | 0.011 |
| 10 | ok | 4.1 | 20.7 | 20.6 | 20 | 81 | 19.4 | 4.0 | 621 | 0.007 |

Ensemble line: `loaded ensemble wall 325.3782207201002 failed None members 1 excluded [(5, 'pre_relax_failed:CoreDisplacementError')] binary /home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`
Host check: `m13-loaded-hostcheck.txt`; env: `m13-loaded-env.txt`; `/usr/bin/time`: `m13-loaded-time.txt`.

## idle

| # | outcome | wall s | load1 start | load1 end | n_cpu | CPU s | CPU/wall | CPU/n_cpu s | R7 budget s | wall/budget |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ok | 4.2 | 2.3 | 2.3 | 20 | 76 | 18.2 | 3.8 | 600 | 0.007 |
| 2 | ok | 11.8 | 3.8 | 8.1 | 20 | 220 | 18.6 | 11.0 | 600 | 0.020 |
| 3 | ok | 10.3 | 8.1 | 11.5 | 20 | 191 | 18.5 | 9.6 | 600 | 0.017 |
| 4 | ok | 11.1 | 11.5 | 14.3 | 20 | 205 | 18.5 | 10.2 | 600 | 0.018 |
| 5 | CoreDisplacementError | 166.8 | 14.3 | 23.9 | 20 | 3117 | 18.7 | 155.8 | 600 | 0.278 |
| 6 | ok | 15.3 | 23.9 | 23.3 | 20 | 285 | 18.7 | 14.3 | 717 | 0.021 |
| 7 | ok | 24.9 | 23.5 | 23.0 | 20 | 466 | 18.7 | 23.3 | 704 | 0.035 |
| 8 | ok | 14.5 | 23.1 | 23.1 | 20 | 272 | 18.7 | 13.6 | 694 | 0.021 |
| 9 | ok | 17.5 | 21.5 | 21.6 | 20 | 324 | 18.6 | 16.2 | 644 | 0.027 |
| 10 | ok | 9.3 | 20.1 | 20.8 | 20 | 177 | 19.0 | 8.8 | 603 | 0.015 |

Ensemble line: `idle ensemble wall 326.84298736497294 failed None members 1 excluded [(5, 'pre_relax_failed:CoreDisplacementError')] binary /home/tjmustard/.local/share/eta-rxncat/xtb/6.8.0/stage/bin/xtb`
Host check: `m13-idle-hostcheck.txt`; env: `m13-idle-env.txt`; `/usr/bin/time`: `m13-idle-time.txt`.

## Reading
- No pre-relaxation timed out in either window; the largest wall/budget is below 0.29. The stop-and-report condition (a healthy
  pre-relaxation over the load-scaled budget) did not occur, so R7 was written.
- Sample 5 ends `CoreDisplacementError` at about 167-169 s in both windows: a template fault, not a timeout.
- Limits: the loaded window (lead-approved) was nice-19 load only, which a nice-0 job pre-empts, so it says little about
  contention at equal priority. The idle run raises load1 above 20 by its own CPU use (about 18 cores per wall second).
- The idle gate was fixed once on 11-26 to stop matching its own `ps`; a first idle launch was refused by the gate
  (a transient `python` process) and ran nothing.
