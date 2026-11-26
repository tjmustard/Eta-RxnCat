"""``SpeciesResult.frequency_dispositions`` (v0.7.0, slice 16; R35): every kind, fake engines.

Butane on rdkit_ff/uff: two records (anti, then gauche, in energy order), so the gauche record's
first frequency is Hessian call 2 and the pushed row's frequency is call 3.
"""

from pathlib import Path

import numpy as np
import pytest
from orchestrator_helpers import ImaginaryUFF, butane, uff_recipe
from test_push_rededup import classify, mirrored, shifted

import eta_rxncat.orchestrator.species as species
from eta_rxncat.core import MolecularState
from eta_rxncat.orchestrator import ENGINE_CLASSES, SpeciesResult, run_species
from eta_rxncat.orchestrator.species import FrequencyDisposition
from eta_rxncat.store import ArtifactStore


@pytest.fixture(scope="module")
def baseline(tmp_path_factory: pytest.TempPathFactory) -> SpeciesResult:
    """A normal butane run."""
    path = tmp_path_factory.mktemp("baseline") / "s.sqlite"
    with ArtifactStore(path) as store:
        return run_species(butane(), uff_recipe(), store)


def faked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    imaginary: set[int],
    target: MolecularState | None = None,
) -> SpeciesResult:
    """Run butane with the given Hessian calls imaginary and the push sent to ``target``."""
    ImaginaryUFF.hessian_calls = 0
    ImaginaryUFF.imaginary_calls = frozenset(imaginary)
    monkeypatch.setitem(ENGINE_CLASSES, "rdkit_ff", ImaginaryUFF)
    if target is not None:
        monkeypatch.setattr(
            species,
            "_push_directions",
            lambda state, hessian, analysis: (shifted(target, 0.01), shifted(target, -0.01)),
        )
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        return run_species(butane(), uff_recipe(), store)


def of_kind(result: SpeciesResult, kind: str) -> list[FrequencyDisposition]:
    """The dispositions of one kind."""
    return [d for d in result.frequency_dispositions if d.kind == kind]


def assert_one_per_row_in_visit_order(result: SpeciesResult) -> None:
    """One disposition per visited frequency row, in visit order."""
    visited = list(dict.fromkeys(result.keys["frequency"]))
    assert [d.frequency_key for d in result.frequency_dispositions] == visited


def test_a_clean_run_keeps_every_row(baseline: SpeciesResult) -> None:
    """Without a push or drop every row is kept."""
    assert_one_per_row_in_visit_order(baseline)
    assert {d.kind for d in baseline.frequency_dispositions} == {"kept"}
    assert all(d.reason is None and d.superseded_by_key is None for d in of_kind(baseline, "kept"))
    assert len(baseline.frequency_dispositions) == len(baseline.ensemble.records)


def test_push_chain_superseded_then_duplicate_after_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """Gauche pushed beside anti: its first row is superseded, the pushed row is a duplicate.

    The push returns anti's optimization shifted 0.01 A and not relaxed, so the pushed row has its
    own stage key while the re-dedup still matches it to anti.
    """
    anti = next(r for r in baseline.ensemble.records if classify(r.state) == "anti")
    near = anti.optimization.model_copy(
        update={
            "final_state": shifted(anti.state, 0.01),
            # slightly higher, so the re-dedup (lowest G first) keeps anti
            "final_energy_hartree": anti.optimization.final_energy_hartree + 1e-4,
        }
    )
    monkeypatch.setattr(species, "_push", lambda *args: near)
    result = faked(tmp_path, monkeypatch, {2})
    assert_one_per_row_in_visit_order(result)
    (old,) = of_kind(result, "superseded_by_push")
    assert old.reason is None
    by_key = {d.frequency_key: d for d in result.frequency_dispositions}
    new = by_key[str(old.superseded_by_key)]
    assert new.kind == "dropped"
    assert new.reason == "duplicate_after_push"
    (kept,) = of_kind(result, "kept")
    assert kept.frequency_key not in (old.frequency_key, new.frequency_key)


def test_push_onto_a_new_minimum_keeps_the_pushed_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """A push onto a new minimum keeps the pushed row."""
    gauche = next(r for r in baseline.ensemble.records if classify(r.state) == "gauche")
    result = faked(tmp_path, monkeypatch, {2}, mirrored(gauche.state))
    (old,) = of_kind(result, "superseded_by_push")
    new = next(d for d in result.frequency_dispositions if d.frequency_key == old.superseded_by_key)
    assert new.kind == "kept"
    assert len(of_kind(result, "kept")) == 2


def test_a_persistent_imaginary_mode_is_not_a_minimum(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """A pushed row that stays imaginary is dropped as not_a_minimum."""
    gauche = next(r for r in baseline.ensemble.records if classify(r.state) == "gauche")
    result = faked(tmp_path, monkeypatch, {2, 3}, mirrored(gauche.state))
    (old,) = of_kind(result, "superseded_by_push")
    (dropped,) = of_kind(result, "dropped")
    assert dropped.frequency_key == old.superseded_by_key
    assert dropped.reason == "not_a_minimum"
    assert ("not_a_minimum") in [reason for _, reason in result.dropped]


def test_a_push_that_fails_drops_the_first_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed push drops the first row as optimization_failed."""
    monkeypatch.setattr(species, "_push", lambda *args: None)
    result = faked(tmp_path, monkeypatch, {2})
    (dropped,) = of_kind(result, "dropped")
    assert dropped.reason == "optimization_failed"
    assert not of_kind(result, "superseded_by_push")


def test_a_mirror_reason_is_the_drop_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mirror drop carries its reason."""
    monkeypatch.setattr(
        species, "drop_mirror_partners", lambda records, *a: (records[:1], [(1, "mirror_partner")])
    )
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_species(butane(), uff_recipe(), store)
    (dropped,) = of_kind(result, "dropped")
    assert dropped.reason == "mirror_partner"
    assert dropped == result.frequency_dispositions[1]


def test_dispositions_add_no_call_row_or_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: SpeciesResult
) -> None:
    """The disposition record changes no stage key, result or engine call (a cached rerun)."""
    path = tmp_path / "s.sqlite"
    with ArtifactStore(path) as store:
        first = run_species(butane(), uff_recipe(), store)
    with ArtifactStore(path) as store:
        again = run_species(butane(), uff_recipe(), store)
        assert len(store.query()) == sum(m.rows_created for m in first.metrics.stages.values())
    assert again.metrics.engine_calls == 0
    assert again.keys == first.keys == baseline.keys
    assert again.frequency_dispositions == first.frequency_dispositions
    assert np.isclose(
        again.ensemble.ensemble_gibbs_hartree, baseline.ensemble.ensemble_gibbs_hartree
    )
