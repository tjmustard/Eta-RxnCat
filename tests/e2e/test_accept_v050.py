"""v0.5.0 acceptance driver: aggregate one recipe's Tier 3 fragments (slice 12; R56, v0.4.0 R27).

Runs last (``conftest.py`` orders every ``test_accept_v*.py`` driver last). It reads the fragments
the Tier 3 tests, the reproducibility runs and (UMA run) the cross-check wrote under
``$ETA_RXNCAT_ACCEPTANCE_OUT/fragments/`` in earlier invocations, and writes
``acceptance_<recipe>.json`` there with the commit, a clean-tree flag, hardware and the engine;
``acceptance_record_v050.py`` merges both recipes into ``docs/prd/v0.5.0/ACCEPTANCE_RESULT.json``.
A fragment that a test never wrote is ``missing`` (R56).
"""

import json
import platform
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from acceptance import out_dir
from acceptance_record_v050 import CASES
from e2e_env import DEVICES, RECIPE_PARAMS, REPO

from eta_rxncat.orchestrator import Recipe, build_engine, write_report

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]


def _fragment(path: Path) -> dict[str, Any]:
    """A fragment, or ``missing`` when its test raised before writing it (R56)."""
    if not path.exists():
        return {"test_outcome": "missing"}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_accept_v050(recipe_name: str, recipes: Callable[[str], Recipe], commit_sha: str) -> None:
    """The recipe's Tier 3 fragments are aggregated with hardware at a clean tree."""
    out = out_dir()
    if out is None:
        pytest.skip("ETA_RXNCAT_ACCEPTANCE_OUT is not set (acceptance record runs only)")
    recipe = recipes(recipe_name)
    fragments = out / "fragments"
    cases = {c: _fragment(fragments / f"t3_{c}.{recipe_name}.json") for c in CASES}
    repro = {c: _fragment(fragments / f"repro_{c}.{recipe_name}.json") for c in CASES}
    extra: dict[str, Any] = {}
    if recipe_name == "uma":  # the cross-check runs in the UMA env, for both recipes
        extra["cross_check"] = _fragment(fragments / "t3_cross_check.all.json")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    from eta_rxncat.utils.hw_probe import probe_hardware

    write_report(
        out / f"acceptance_{recipe_name}.json",
        {
            "recipe": recipe_name,
            "commit_sha": commit_sha,
            "tree_clean": status == "",
            "run_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "device": DEVICES[recipe_name],
            "engine": build_engine(
                recipe.engine_stage, recipe.engine_runtime
            ).identity.model_dump(),
            "python": platform.python_version(),
            "hardware": probe_hardware().model_dump(mode="json"),
            "cases": cases,
            "reproducibility": repro,
            **extra,
        },
    )
    assert status == "", "the acceptance record must be produced at a clean, committed tree"
