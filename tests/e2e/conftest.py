"""E2E fixtures: recipes, fresh stores, the candidate directory and the run's commit (slice 07).

Every E2E test carries ``e2e`` and ``slow`` plus ``xtb`` or ``mlip_uma``; the default ``addopts``
deselects all of them. A missing binary or model skips with the reason, which fails an acceptance
run (``ETA_RXNCAT_ACCEPTANCE=1``).
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from e2e_env import CANDIDATES, REPO, recipe_for

from eta_rxncat.engines import EngineUnavailableError
from eta_rxncat.optimize import OptimizerUnavailableError
from eta_rxncat.orchestrator import Recipe, build_engine


@pytest.fixture(scope="session")
def recipes() -> Callable[[str], Recipe]:
    """Return a factory that builds a recipe and skips (with the reason) if it is unavailable."""
    built: dict[str, Recipe] = {}

    def get(name: str) -> Recipe:
        if name not in built:
            try:
                recipe = recipe_for(name)
                build_engine(recipe.engine_stage, recipe.engine_runtime)
            except (EngineUnavailableError, OptimizerUnavailableError) as exc:
                pytest.skip(f"recipe {name} unavailable: {exc}")
            built[name] = recipe
        return built[name]

    return get


@pytest.fixture
def candidate_dir() -> Path:
    """The candidate directory (write only; nothing reads a candidate back)."""
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    return CANDIDATES


@pytest.fixture(scope="session")
def commit_sha() -> str:
    """HEAD of the checkout the E2E run happens at (C1 of R23)."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()
