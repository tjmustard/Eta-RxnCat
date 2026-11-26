Decision (resolve, v0.2.0, R8/R18/R19; Red Team F8, F18, F19). Engine tests that need optional pieces are marked gpu, xtb, mlip_mace, mlip_uma, slow or acceptance, and are deselected by default.

Environments:
- `.venv` stays the base dev env for the required checks.
- Acceptance runs in named envs `.venv-accept-gpu`, `.venv-accept-mace` and `.venv-accept-uma` (UV_PROJECT_ENVIRONMENT).
- Only the build seat syncs them; the audit seat uses `uv run --no-sync`.

Behaviour:
- `ETA_RXNCAT_ACCEPTANCE=1` makes a conftest hook turn any skip into a failure, so a skipped acceptance run can never pass.
- Unit tests run with HF_HUB_OFFLINE=1 and never download. Provisioning is an explicit seat command.

Trade-off: extras in the shared `.venv` were rejected. `uv sync --locked` strips them, and two seats would thrash one env. The cost is three on-disk envs (hardlinked from the uv cache).
