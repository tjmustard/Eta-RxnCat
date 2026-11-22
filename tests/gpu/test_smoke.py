"""GPU acceptance: the smoke test must pass on a CUDA host with the gpu extra (slice 07 runs it)."""

import pytest

from eta_rxncat.utils.hw_probe import run_smoke


@pytest.mark.gpu
def test_gpu_smoke_passes() -> None:
    """``run_smoke()`` passes every check on this host."""
    result = run_smoke()
    assert result.status == "pass", result.model_dump_json(indent=2)
