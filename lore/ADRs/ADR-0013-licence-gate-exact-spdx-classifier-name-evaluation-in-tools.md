Decision (resolve, replan 7, R45). This supersedes the mechanism of ADR-0006 and ADR-0011; their policies stand (allow-list intent, the geometric 1.1.1 exception, TJ Q1 A exemptions).

The licence gate is `tools/licence_gate.py`, a stdlib-only script run by the target environment's interpreter. It is configured in `[tool.eta-rxncat.licence-gate]` and replaces `pip-licenses --partial-match --allow-only`.

Why the old mechanism was replaced: partial matching passed matscipy, whose LGPL full-text License field contains "MIT" inside "PERMITTED". It also hid MPL-2.0 inside SPDX `AND` expressions (tqdm, orjson). pip-licenses cannot evaluate `AND`.

Rules:
- Each package's verdict comes from the first source present:
  1. the SPDX `License-Expression`, with AND/OR/WITH/parentheses;
  2. otherwise the exact classifier map, where several classifiers are alternatives;
  3. otherwise an exact match of the `License` field against known names.
- Anything unrecognised fails, and there is no substring matching.
- Exemptions are version-pinned per profile (`base`, `gpu`, `mlip-mace`, `mlip-uma`).
- One NVIDIA name-plus-proprietary-licence rule applies in the torch profiles only.
- A stale exemption (package absent) fails.
- The allow-list in SPDX ids adds `Zlib` and `CC0-1.0`: permissive, carried by numpy in the core install, and already passing by substring before.

Trade-off:
- Rejected: keeping pip-licenses with exact matching. It cannot do SPDX `AND`, and its OR-over-names semantics would still pass "MPL-2.0 AND MIT"-style metadata wrongly or fail it for the wrong reason.
- Rejected: adding a third-party licence checker. It is a new dependency with its own semantics.
- Chosen: about 150 lines of tested project tooling with deterministic, documented semantics.

Cost: classifier and name maps need upkeep when a new package uses an unseen string. That fails closed, so it surfaces as a gate failure rather than a silent pass.
