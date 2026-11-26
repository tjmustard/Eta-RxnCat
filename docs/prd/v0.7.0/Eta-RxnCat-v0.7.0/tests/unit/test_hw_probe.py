"""Unit test for hardware probe diagnostic report."""

from eta_rxncat.utils.hw_probe import probe_hardware


def test_probe_hardware_returns_valid_report() -> None:
    report = probe_hardware()
    assert isinstance(report.torch_installed, bool)
    assert isinstance(report.cuda_available, bool)
    if report.cuda_available:
        assert report.total_vram_gb is not None and report.total_vram_gb > 0
        assert report.recommended_vram_budget_gb is not None
