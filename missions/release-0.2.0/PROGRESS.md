# Progress - release-0.2.0

> Durable acceptance state for this mission. `hyper_spec.py progress` regenerates the slice
> table below; in-process steps belong in the working agent's todo tool.

## Acceptance

- [ ] Scope complete
- [ ] Implementation in progress
- [ ] QA / review pass
- [ ] Merge / ship

<!-- BEGIN HACF GENERATED: slice-table -->
| id | slice | hacf_status | depends_on | last event |
|---|---|---|---|---|
| OPR.0.2.0.1 | 01-reference-and-test-policy | audited |  | 2026-11-22T16:58:12+00:00 audited |
| OPR.0.2.0.2 | 02-gpu-stack-cu129 | audited | OPR.0.2.0.1 | 2026-11-22T17:13:30+00:00 audited |
| OPR.0.2.0.3 | 03-potential-result | audited | OPR.0.2.0.1 | 2026-11-22T17:20:29+00:00 audited |
| OPR.0.2.0.4 | 04-engines-base | audited | OPR.0.2.0.3 | 2026-11-22T17:30:39+00:00 audited |
| OPR.0.2.0.5 | 05-rdkit-ff | compiled | OPR.0.2.0.4 | 2026-11-22T16:42:44+00:00 compiled |
| OPR.0.2.0.6 | 06-pyscf-cpu | compiled | OPR.0.2.0.4, OPR.0.2.0.5 | 2026-11-22T16:43:55+00:00 compiled |
| OPR.0.2.0.7 | 07-pyscf-gpu | compiled | OPR.0.2.0.6, OPR.0.2.0.2 | 2026-11-22T16:44:51+00:00 compiled |
| OPR.0.2.0.8 | 08-xtb-subprocess | compiled | OPR.0.2.0.4, OPR.0.2.0.5 | 2026-11-22T16:45:33+00:00 compiled |
| OPR.0.2.0.9 | 09-mace | compiled | OPR.0.2.0.4, OPR.0.2.0.5, OPR.0.2.0.2 | 2026-11-22T16:46:12+00:00 compiled |
| OPR.0.2.0.10 | 10-uma-direct | compiled | OPR.0.2.0.4, OPR.0.2.0.5, OPR.0.2.0.2, OPR.0.2.0.3 | 2026-11-22T16:47:04+00:00 compiled |
| OPR.0.2.0.11 | 11-acceptance | compiled | OPR.0.2.0.5, OPR.0.2.0.7, OPR.0.2.0.8, OPR.0.2.0.9, OPR.0.2.0.10 | 2026-11-22T16:48:00+00:00 compiled |
<!-- END HACF GENERATED: slice-table -->
