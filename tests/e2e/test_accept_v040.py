"""v0.4.0 acceptance driver: aggregate one recipe's M1 fragments (slice 07; R22, R56, ADR-0027).

Runs last (tests/e2e/conftest.py orders every ``test_accept_v*.py`` driver last) in the same session
as ``test_m1_relax.py``. Needs ``ETA_RXNCAT_ACCEPTANCE_OUT`` (outside the repository) and writes
``acceptance_<recipe>.json`` there; ``acceptance_record_v040.py`` merges both recipes into
``docs/prd/v0.4.0/ACCEPTANCE_RESULT.json``. The xtb run also carries the recipe-independent graft
fragment.
"""

import hashlib
import json
import platform
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from acceptance import out_dir
from e2e_env import DEVICES, RECIPE_PARAMS, REPO
from m1 import PROMOTED_V040

from eta_rxncat.orchestrator import Recipe, build_engine, write_report

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]


def _fragment(path: Path) -> dict[str, Any]:
    """A fragment, or ``missing`` when its test raised before writing it (R56)."""
    if not path.exists():
        return {"test_outcome": "missing"}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_accept_v040(recipe_name: str, recipes: Callable[[str], Recipe], commit_sha: str) -> None:
    """M1 ran in this session; the recipe's fragments are aggregated with hardware."""
    out = out_dir()
    if out is None:
        pytest.skip("ETA_RXNCAT_ACCEPTANCE_OUT is not set (acceptance record runs only)")
    recipe = recipes(recipe_name)
    m1 = {recipe_name: _fragment(out / "fragments" / f"m1.{recipe_name}.json")}
    if recipe_name == "xtb":
        m1["graft"] = _fragment(out / "fragments" / "m1.graft.json")
    fixture_sha256 = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(PROMOTED_V040.glob("*.json"))
    }
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
            "fixture_sha256": fixture_sha256,
            "fixtures": {"m1": m1},
        },
    )
    assert status == "", "the acceptance record must be produced at a clean, committed tree"
