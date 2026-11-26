Decision (TJ, 12:49Z, verbatim "B", row qitem-20261122123511-7102e97b507c86d4; resolve R41; amends ADR-0006, which said there are no exceptions). geomeTRIC 1.1.1 stays a v0.1.0 runtime dependency under one documented licence-gate exception.

Facts as TJ phrased them:
- Licence: BSD 3-clause Non-AI.
- Clause 4 restricts use in AI-training datasets. It reads: "The source code and the binary form, and any modifications made to them may not be included in training datasets for improving machine learning algorithms, including but not limited to artificial intelligence, natural language processing, or data mining". It applies to derivatives.
- pip-licenses reports the metadata as UNKNOWN.

How the exception is scoped:
- The single licence-gate config is `[tool.pip-licenses]` in `pyproject.toml`: `partial-match = true`, the ADR-0006 allow-list, and `ignore-packages = ["geometric:1.1.1"]`. pip-licenses 5.5.5 reads it from the working directory. The `ci.yml` and `AGENTS.md` gate commands both use it.
- The exception is pinned to the version. An upgrade or downgrade of geometric no longer matches, so the gate fails and the licence comes back for review.
- Any other UNKNOWN or disallowed package still fails. Verified by resolve in a scratch env.
- A CLI `--ignore-packages` replaces the config list rather than extending it. Every per-extra command (ADR-0010) therefore repeats `geometric:1.1.1` in its own list.

Eta-RxnCat does not vendor or redistribute geomeTRIC. Clause 4 travels with any environment or dataset that bundles it. Nothing in v0.1.0 imports it; v0.3.0 is its first use.
