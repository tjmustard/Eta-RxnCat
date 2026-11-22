"""Real-weights tests for the UMA (uma-s-1p2p1) engine (slice 10), marked mlip_uma.

Run in .venv-accept-uma: `UV_PROJECT_ENVIRONMENT=.venv-accept-uma ETA_RXNCAT_ACCEPTANCE=1 uv run
--no-sync pytest -m mlip_uma tests/unit/engines/`. CUDA cases are also marked gpu.
"""

from pathlib import Path

import fairchem_reference as ref
import pytest

from eta_rxncat.core import MolecularState
from eta_rxncat.engines import UMADirectEngine

CLS = UMADirectEngine


@pytest.fixture(scope="module", autouse=True)
def weights() -> None:
    """Skip at fixture level (never module level) without the provisioned checkpoint."""
    ref.require_weights(CLS)


@pytest.mark.mlip_uma
def test_cpu_reference(test_set: dict[str, MolecularState]) -> None:
    """All four cases on CPU match fairchem's own high-precision predictor."""
    ref.check_reference(CLS, "cpu", test_set)


@pytest.mark.mlip_uma
@pytest.mark.gpu
def test_cuda_reference(test_set: dict[str, MolecularState]) -> None:
    """All four cases on CUDA match fairchem's own high-precision predictor."""
    ref.check_reference(CLS, "cuda", test_set)


@pytest.mark.mlip_uma
@pytest.mark.parametrize("device", ["cpu", pytest.param("cuda", marks=pytest.mark.gpu)])
def test_liveness(test_set: dict[str, MolecularState], device: str) -> None:
    """Charge and spin are live (Mini-requirement 3)."""
    ref.check_liveness(CLS, device, test_set)


@pytest.mark.mlip_uma
@pytest.mark.parametrize("device", ["cpu", pytest.param("cuda", marks=pytest.mark.gpu)])
def test_fd_forces(test_set: dict[str, MolecularState], device: str) -> None:
    """Forces equal -FD of the energy (conserving model)."""
    ref.check_fd_forces(CLS, device, test_set)


@pytest.mark.mlip_uma
def test_hessian(test_set: dict[str, MolecularState]) -> None:
    """The water Hessian is a symmetric 9x9 FD Hessian."""
    ref.check_hessian(CLS, "cpu", test_set)


@pytest.mark.mlip_uma
@pytest.mark.parametrize("device", ["cpu", pytest.param("cuda", marks=pytest.mark.gpu)])
def test_refs_and_identity(device: str) -> None:
    """Derived reference hashes and the content-pinned identity are those of the files used."""
    ref.check_refs_and_identity(CLS, device)


@pytest.mark.mlip_uma
def test_edited_refs_change_key(tmp_path: Path, test_set: dict[str, MolecularState]) -> None:
    """An edited reference file changes the derived hash and the cache key (R40)."""
    ref.check_edited_refs_change_energy_and_key(CLS, tmp_path, test_set)


@pytest.mark.mlip_uma
@pytest.mark.parametrize("device", ["cpu", pytest.param("cuda", marks=pytest.mark.gpu)])
def test_batch_matches_from_ase(test_set: dict[str, MolecularState], device: str) -> None:
    """The engine's batch is exactly what FAIRChemCalculator would build (literal charge/spin)."""
    ref.check_batch_matches_from_ase(CLS, device, test_set)


@pytest.mark.mlip_uma
@pytest.mark.gpu
def test_cpu_cuda_agree(test_set: dict[str, MolecularState]) -> None:
    """R47: CPU and CUDA agree at high precision."""
    ref.check_cpu_cuda_agree(CLS, test_set)
