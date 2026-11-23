"""v0.3.0 acceptance driver: aggregate one recipe's fixture fragments (slice 09; R4, R22, Q4 C).

Runs last (tests/e2e/conftest.py orders it) in the same session as HF1, HF2, T1 and T2. Needs
``ETA_RXNCAT_ACCEPTANCE_OUT`` (outside the repository); writes ``acceptance_<recipe>.json`` there.
``tests/e2e/acceptance_record.py`` merges both recipes into
``docs/prd/v0.3.0/ACCEPTANCE_RESULT.json``.
"""

import json
import platform
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from acceptance import out_dir
from e2e_env import DEVICES, RECIPE_PARAMS, REPO

from eta_rxncat.orchestrator import Recipe, build_engine, write_report

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]

FIXTURES = ("hf1_butane", "hf2_diels_alder", "e2e5_t1", "e2e5_t2")


@pytest.mark.parametrize("recipe_name", RECIPE_PARAMS)
def test_accept_v030(recipe_name: str, recipes: Callable[[str], Recipe], commit_sha: str) -> None:
    """Every fixture ran in this session; the recipe's fragments are aggregated with hardware."""
    out = out_dir()
    if out is None:
        pytest.skip("ETA_RXNCAT_ACCEPTANCE_OUT is not set (acceptance record runs only)")
    recipe = recipes(recipe_name)
    fixtures = {}
    for name in FIXTURES:
        path = out / "fragments" / f"{name}.{recipe_name}.json"
        assert path.exists(), f"{name}.{recipe_name}: no fragment (did the fixture test run?)"
        fixtures[name] = json.loads(path.read_text(encoding="utf-8"))
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
            "fixtures": fixtures,
        },
    )
    assert status == "", "the acceptance record must be produced at a clean, committed tree"
