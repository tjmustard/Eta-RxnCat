"""Re-dedup after the imaginary-mode push (v0.3.0 slice 11, mission R53).

Butane on rdkit_ff/uff: the first run gives an anti and a gauche record. The fake engine makes the
gauche record's first Hessian imaginary (Hessian call 2: frequencies run in energy order, anti
first), and the push directions are replaced to land where the test wants.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from orchestrator_helpers import ImaginaryUFF, butane, uff_recipe

import eta_rxncat.orchestrator.species as species
from eta_rxncat.conformers import dihedral_deg
from eta_rxncat.core import MolecularState
from eta_rxncat.orchestrator import ENGINE_CLASSES, SpeciesResult, run_species
from eta_rxncat.store import ArtifactStore


def classify(state: MolecularState) -> str:
    """Anti if |phi(C-C-C-C)| > 120 deg, else gauche."""
    return "anti" if abs(dihedral_deg(state, 0, 1, 2, 3)) > 120.0 else "gauche"


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory) -> SpeciesResult:
    """A normal butane run (no fake engine): one anti and one gauche record."""
    path = tmp_path_factory.mktemp("baseline") / "s.sqlite"
    with ArtifactStore(path) as store:
        result = run_species(butane(), uff_recipe(), store)
    assert sorted(classify(r.state) for r in result.ensemble.records) == ["anti", "gauche"]
    return result


def shifted(state: MolecularState, dx: float) -> MolecularState:
    """``state`` with every coordinate moved by ``dx`` Angstrom along a fixed direction."""
    xyz = np.asarray(state.coordinates) + dx * np.array([0.6, -0.3, 0.74])
    return state.model_copy(update={"coordinates": xyz.tolist()})


def mirrored(state: MolecularState) -> MolecularState:
    """``state`` reflected through the yz plane (the other gauche enantiomer)."""
    xyz = np.asarray(state.coordinates) * np.array([-1.0, 1.0, 1.0])
    return state.model_copy(update={"coordinates": xyz.tolist()})


def faked_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: MolecularState,
) -> SpeciesResult:
    """Run butane with gauche's first Hessian imaginary and the push sent towards ``target``."""
    ImaginaryUFF.hessian_calls = 0
    ImaginaryUFF.imaginary_calls = frozenset({2})
    monkeypatch.setitem(ENGINE_CLASSES, "rdkit_ff", ImaginaryUFF)
    monkeypatch.setattr(
        species,
        "_push_directions",
        lambda state, hessian, analysis: (shifted(target, 0.01), shifted(target, -0.01)),
    )
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        return run_species(butane(), uff_recipe(), store)


def test_push_onto_a_kept_conformer_is_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """Gauche pushed onto anti -> one record survives; one duplicate_after_push; G_ens = its G."""
    anti = next(r for r in baseline.ensemble.records if classify(r.state) == "anti")
    result = faked_run(tmp_path, monkeypatch, anti.state)
    records = result.ensemble.records
    assert [classify(r.state) for r in records] == ["anti"]
    reasons = [reason for _, reason in result.dropped]
    assert reasons.count("duplicate_after_push") == 1
    assert result.ensemble.ensemble_gibbs_hartree == pytest.approx(
        records[0].thermo.gibbs_free_energy_hartree, abs=1e-12
    )
    # whichever of the two anti records has the lower G survives, with its own ids (none merged)
    gauche = next(r for r in baseline.ensemble.records if classify(r.state) == "gauche")
    assert records[0].source_ids in (anti.source_ids, gauche.source_ids)
    dup = next(sid for sid, reason in result.dropped if reason == "duplicate_after_push")
    assert dup not in records[0].source_ids


def test_push_onto_a_new_minimum_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """Gauche pushed onto the other gauche enantiomer (not in the kept set) -> both kept."""
    gauche = next(r for r in baseline.ensemble.records if classify(r.state) == "gauche")
    result = faked_run(tmp_path, monkeypatch, mirrored(gauche.state))
    assert sorted(classify(r.state) for r in result.ensemble.records) == ["anti", "gauche"]
    assert "duplicate_after_push" not in [reason for _, reason in result.dropped]
    pushed = next(r for r in result.ensemble.records if classify(r.state) == "gauche")
    assert "imag_mode_push" in pushed.optimization.recovery_steps


def test_without_push_records_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """No push -> records and ensemble byte-identical to running without the re-dedup step."""
    monkeypatch.setattr(species, "_dedup_after_push", lambda records, spec, dropped: records)
    with ArtifactStore(tmp_path / "old.sqlite") as store:
        before = run_species(butane(), uff_recipe(), store)

    def dump(r: SpeciesResult) -> str:
        return json.dumps(r.ensemble.model_dump(), sort_keys=True) + json.dumps(r.dropped)

    assert dump(before) == dump(baseline)


def test_cached_rerun_still_free(tmp_path: Path) -> None:
    """The re-dedup makes no engine call and adds no row: a rerun is still 0 calls."""
    path = tmp_path / "s.sqlite"
    with ArtifactStore(path) as store:
        run_species(butane(), uff_recipe(), store)
    with ArtifactStore(path) as store:
        again = run_species(butane(), uff_recipe(), store)
    assert again.metrics.engine_calls == 0
    assert sum(m.rows_created for m in again.metrics.stages.values()) == 0
