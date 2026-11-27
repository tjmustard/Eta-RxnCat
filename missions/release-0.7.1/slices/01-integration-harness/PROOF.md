# PROOF - OPR.0.7.1.1 Integration harness, marker split, mock policy, node and fixture ownership

> A slice is not done until this file maps every `## Proof contract` item of its SPEC.md to
> evidence under `proof/`. Add each C1 artifact with `hyper_spec.py proof`, which writes the
> artifact's header and lists it under "Artifacts"; never place evidence by hand.

## What this proves

- `pytest tests/integration tests/unit/test_test_policy.py` passes (requirements 1-4): proof/01-execute.md "Commands and exit codes" (83 passed) and "Requirement 4".
- `hyper_ledger.py validate` ok, `impact --files tests/integration/conftest.py` names `eta_rxncat_integration`, fixture counts (requirement 5): proof/01-execute.md "Ledger".
- Required checks exit 0 (requirement 6): proof/01-execute.md "Commands and exit codes".

## Artifacts

- proof/01-execute.md - guard CLEAR: full pytest 2747 passed, 0 skipped; 57 integration ids default-selected; ledger valid, 65/65 fixtures owned

## Residue / caveats

The scanner's uncaught forms and the other builder deviations are listed in proof/01-execute.md "For the audit to rule on". The loader's committed parity test is slice 02's. No engine ran.
