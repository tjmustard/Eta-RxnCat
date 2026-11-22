"""Tests for StageConfig, Solvation and EngineIdentity."""

from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import EngineIdentity, Solvation, StageConfig


def stage(**overrides: Any) -> dict[str, Any]:
    """Return keyword arguments for a valid PySCF single point, with overrides applied."""
    data: dict[str, Any] = {
        "kind": "single_point",
        "engine": "pyscf_gpu_cpu",
        "method": "wB97X-D3BJ",
        "basis": "def2-SVP",
    }
    data.update(overrides)
    return data


def test_valid_stage() -> None:
    """A complete PySCF stage validates with gas-phase solvation by default."""
    config = StageConfig(**stage())
    assert config.solvation == Solvation() and config.solvation.model == "none"


@pytest.mark.parametrize("method", ["default", "Default", "DEFAULT"])
def test_placeholder_method_rejected(method: str) -> None:
    """The literal ``default`` is not a method, in any case."""
    with pytest.raises(ValidationError, match="method"):
        StageConfig(**stage(method=method))


def test_empty_method_rejected() -> None:
    """The method must be non-empty."""
    with pytest.raises(ValidationError, match="method"):
        StageConfig(**stage(method=""))


def test_pyscf_requires_basis() -> None:
    """``pyscf_gpu_cpu`` without a basis raises."""
    with pytest.raises(ValidationError, match="basis"):
        StageConfig(**stage(basis=None))


def test_xtb_forbids_basis() -> None:
    """``xtb_subprocess`` with a basis raises."""
    with pytest.raises(ValidationError, match="basis"):
        StageConfig(**stage(engine="xtb_subprocess", method="GFN2-xTB"))


def test_ddcosmo_requires_pyscf() -> None:
    """The ddCOSMO model on the xTB engine raises."""
    with pytest.raises(ValidationError, match="ddcosmo"):
        StageConfig(
            kind="single_point",
            engine="xtb_subprocess",
            method="GFN2-xTB",
            solvation={"model": "ddcosmo", "solvent": "water"},
        )


def test_alpb_requires_xtb() -> None:
    """ALPB solvation on the PySCF engine raises."""
    with pytest.raises(ValidationError, match="alpb"):
        StageConfig(**stage(solvation={"model": "alpb", "solvent": "water"}))


def test_pcm_needs_solvent_or_dielectric() -> None:
    """PCM with neither solvent nor dielectric raises."""
    with pytest.raises(ValidationError, match="pcm"):
        StageConfig(**stage(solvation={"model": "pcm"}))


def test_pcm_with_dielectric_accepted() -> None:
    """PCM with only a dielectric validates."""
    config = StageConfig(**stage(solvation={"model": "pcm", "dielectric": 78.4}))
    assert config.solvation.dielectric == 78.4


def test_none_solvation_takes_no_parameters() -> None:
    """Model ``none`` with a solvent raises."""
    with pytest.raises(ValidationError, match="none"):
        Solvation(model="none", solvent="water")


def test_dielectric_must_be_positive() -> None:
    """A non-positive dielectric raises."""
    with pytest.raises(ValidationError, match="dielectric"):
        Solvation(model="pcm", dielectric=0.0)


def test_constrained_preopt_requires_frozen_atoms() -> None:
    """``constrained_preopt`` with no frozen atoms raises."""
    with pytest.raises(ValidationError, match="frozen_atom_indices"):
        StageConfig(kind="constrained_preopt", engine="rdkit_ff", method="UFF")


def test_constrained_preopt_with_frozen_atoms_accepted() -> None:
    """``constrained_preopt`` with frozen atoms validates."""
    config = StageConfig(
        kind="constrained_preopt", engine="rdkit_ff", method="UFF", frozen_atom_indices=[0, 2]
    )
    assert config.frozen_atom_indices == [0, 2]


@pytest.mark.parametrize(
    ("indices", "message"), [([-1], "frozen_atom_indices"), ([1, 1], "duplicate")]
)
def test_frozen_atom_indices_checked(indices: list[int], message: str) -> None:
    """Frozen atoms must be unique and non-negative."""
    with pytest.raises(ValidationError, match=message):
        StageConfig(**stage(frozen_atom_indices=indices))


def test_unknown_engine_tag_rejected() -> None:
    """The bare tag ``xtb`` is not an engine; ``xtb_subprocess`` is."""
    with pytest.raises(ValidationError, match="engine"):
        StageConfig(**stage(engine="xtb", basis=None))


def test_non_finite_option_rejected() -> None:
    """Float options must be finite."""
    with pytest.raises(ValidationError, match="non-finite"):
        StageConfig(**stage(options={"conv_tol": float("nan")}))


def test_engine_identity() -> None:
    """EngineIdentity needs a known tag and a non-empty version."""
    identity = EngineIdentity(name="uma_direct", version="1.0", model="uma-s-1.2.1")
    assert identity.model == "uma-s-1.2.1"
    with pytest.raises(ValidationError, match="version"):
        EngineIdentity(name="uma_direct", version="")
    with pytest.raises(ValidationError, match="name"):
        EngineIdentity(name="uma", version="1.0")
