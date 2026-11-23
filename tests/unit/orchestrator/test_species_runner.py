"""Tests for the species runner: keys, push and drop paths, constrained points (v0.3.0 slice 06).

R7, R15, R18, R35, R42; DV-09, DV-15. Small molecules on rdkit_ff/uff and fake engines only.
"""

from pathlib import Path

import pytest
from orchestrator_helpers import (
    UFF,
    UFF_SP,
    ImaginaryUFF,
    RefusingUFF,
    butane,
    rows,
    uff_recipe,
    water,
    water_state,
)

from eta_rxncat.conformers import ConformerOptions, EnsembleEmptyError, dihedral_deg, generate
from eta_rxncat.core import StageConfig
from eta_rxncat.engines import EngineInputError, RDKitFFEngine
from eta_rxncat.optimize import DihedralConstraint, OptimizerInputError, constraints_text
from eta_rxncat.orchestrator import (
    ENGINE_CLASSES,
    CountingEngine,
    SinglePoint,
    run_constrained_point,
    run_species,
)
from eta_rxncat.orchestrator.species import _Runner
from eta_rxncat.store import ArtifactStore, build_stage_key
from eta_rxncat.thermo import ThermoInputError

# counting


def test_counting_engine_delegates_and_counts() -> None:
    """CountingEngine forwards stage/identity/evaluate and counts calls per kind."""
    inner = RDKitFFEngine(UFF)
    engine = CountingEngine(inner)
    assert engine.stage == inner.stage and engine.identity == inner.identity
    assert engine.wrapped is inner and engine.tag == "rdkit_ff"
    engine.kind = "frequency"
    engine.evaluate(water_state(), forces=True)
    engine.kind = "single_point"
    engine.evaluate(water_state(), forces=False)
    engine.evaluate(water_state(), forces=False)
    assert dict(engine.counts) == {"frequency": 1, "single_point": 2}
    assert engine.total == 3


# keys


def test_keys_byte_identical_across_fresh_stores(tmp_path: Path) -> None:
    """Two runs into fresh stores use byte-identical keys for every stage."""
    keys = []
    for name in ("a", "b"):
        with ArtifactStore(tmp_path / f"{name}.sqlite") as store:
            keys.append(run_species(butane(), uff_recipe(), store).keys)
    assert keys[0] == keys[1]
    assert all(keys[0][k] for k in ("conformer_search", "geometry_opt", "frequency"))


def test_geometry_opt_key_stage_options(tmp_path: Path) -> None:
    """The geometry_opt key holds engine options, opt.* resolved options, name and version."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        runner = _Runner(butane(), uff_recipe(), store)
        stage = runner.opt_stage()
    opts = stage.options
    assert stage.kind == "geometry_opt"
    assert opts["opt.name"] == "geometric" and opts["opt.version"] == "1.1.1"
    assert opts["opt.coordsys"] == "tric" and opts["opt.maxiter"] == 300
    assert "opt.constraints" not in opts
    assert opts["fd_step_bohr"] == 0.005 and opts["engine_impl"] == 1
    # the engine itself never sees opt.* keys
    assert not any(k.startswith("opt.") for k in runner.engine.stage.options)


def test_conformer_search_makes_no_engine_call(tmp_path: Path) -> None:
    """conformer_search is counted with 0 engine calls and stores one row."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_species(water(), uff_recipe(), store)
    m = result.metrics.stages["conformer_search"]
    assert m.engine_calls == 0 and m.rows_created == 1


def test_rows_created_equal_counted_misses(tmp_path: Path) -> None:
    """Every stage's rows_created equals its misses (keys visited minus hits)."""
    path = tmp_path / "s.sqlite"
    with ArtifactStore(path) as store:
        result = run_species(butane(), uff_recipe(), store)
    for kind, m in result.metrics.stages.items():
        assert m.rows_created == len(result.keys[kind]) - m.cache_hits, kind
    assert len(rows(path)) == sum(m.rows_created for m in result.metrics.stages.values())


# imaginary-mode push and drop paths


@pytest.fixture
def imaginary(monkeypatch: pytest.MonkeyPatch) -> type[ImaginaryUFF]:
    """Route rdkit_ff to ImaginaryUFF (call counter reset)."""
    ImaginaryUFF.hessian_calls = 0
    monkeypatch.setitem(ENGINE_CLASSES, "rdkit_ff", ImaginaryUFF)
    return ImaginaryUFF


def test_imag_mode_push_recorded(tmp_path: Path, imaginary: type[ImaginaryUFF]) -> None:
    """One imaginary mode at the first frequency -> push recorded, new geometry_opt rows."""
    imaginary.imaginary_calls = frozenset({1})
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_species(water(), uff_recipe(), store)
    record = result.ensemble.records[0]
    assert "imag_mode_push" in record.optimization.recovery_steps
    assert result.metrics.recovery_steps["imag_mode_push"] == 1
    opt_keys = result.keys["geometry_opt"]
    assert len(opt_keys) == len(set(opt_keys))
    spec = water()
    pool = generate(spec.smiles, charge=0, spin_multiplicity=1, options=spec.conformer_options)
    survivors = len(pool.pre_dedup_survivors)
    assert result.metrics.stages["geometry_opt"].rows_created == survivors + 2  # +/- displaced
    assert result.metrics.stages["frequency"].rows_created == 2
    assert not record.thermo.imaginary_frequencies_cm1


def test_persistent_imaginary_mode_drops(tmp_path: Path, imaginary: type[ImaginaryUFF]) -> None:
    """Imaginary after the push -> dropped not_a_minimum; all dropped -> EnsembleEmptyError."""
    imaginary.imaginary_calls = frozenset(range(1, 1000))
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(EnsembleEmptyError) as info:
            run_species(water(), uff_recipe(), store)
    reasons = {reason for _, reason in info.value.reasons}
    assert "not_a_minimum" in reasons


def test_engine_input_error_propagates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """EngineInputError from the engine propagates out of run_species."""
    monkeypatch.setitem(ENGINE_CLASSES, "rdkit_ff", RefusingUFF)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(EngineInputError, match="refuses"):
            run_species(water(), uff_recipe(), store)


# energy_source = single_point (R35)


def test_single_point_energy_source(tmp_path: Path) -> None:
    """With energy_source='single_point' every record's E is its SP energy."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        result = run_species(
            water(), uff_recipe(), store, single_points=[UFF_SP], energy_source="single_point"
        )
    for i, record in enumerate(result.ensemble.records):
        assert record.thermo.energy_source == "single_point"
        assert record.thermo.electronic_energy_hartree == result.single_point_energies[0][i]


def test_single_point_on_other_geometry_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An SP whose stored geometry differs from the frequency's -> ThermoInputError."""
    original = _Runner.single_point

    def shifted(self: _Runner, sp: SinglePoint, state: object) -> tuple[float, dict[str, object]]:
        energy, geometry = original(self, sp, state)  # type: ignore[arg-type]
        coords = [list(row) for row in geometry["coordinates"]]  # type: ignore[union-attr]
        coords[0][0] = "9.99999"
        return energy, {**geometry, "coordinates": coords}

    monkeypatch.setattr(_Runner, "single_point", shifted)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(ThermoInputError, match="R35"):
            run_species(
                water(), uff_recipe(), store, single_points=[UFF_SP], energy_source="single_point"
            )


def test_single_point_energy_source_needs_a_single_point(tmp_path: Path) -> None:
    """energy_source='single_point' without single points is refused."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(ThermoInputError):
            run_species(water(), uff_recipe(), store, energy_source="single_point")


# constrained point (R42)


def test_constrained_point(tmp_path: Path) -> None:
    """Butane held at phi = 0: |phi| <= 0.1 deg, own key, cached rerun, no frequency row."""
    path = tmp_path / "s.sqlite"
    spec, recipe = butane(), uff_recipe()
    start = (
        generate("CCCC", charge=0, spin_multiplicity=1, options=ConformerOptions(n_embed=1))
        .members[0]
        .state
    )
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    with ArtifactStore(path) as store:
        point = run_constrained_point(spec, recipe, store, start, dihedral_constraints=[constraint])
        runner = _Runner(spec, recipe, store)
        unconstrained = build_stage_key(start, runner.opt_stage(), runner.engine.identity).key
        constrained = build_stage_key(
            start, runner.opt_stage(constraints_text((), [constraint])), runner.engine.identity
        ).key
    assert abs(dihedral_deg(point.state, 0, 1, 2, 3)) <= 0.1
    assert not point.cache_hit and point.key == constrained != unconstrained
    assert point.optimization.options["constraints"] == "dihedral:0,1,2,3:0.000000"
    assert point.metrics.stages["geometry_opt"].engine_calls > 0
    assert {kind for kind, _ in rows(path).values()} == {"geometry_opt"}
    with ArtifactStore(path) as store:
        again = run_constrained_point(spec, recipe, store, start, dihedral_constraints=[constraint])
    assert again.cache_hit and again.metrics.engine_calls == 0
    assert again.metrics.stages["geometry_opt"].cache_hits == 1
    assert again.state == point.state


def test_constrained_point_refuses_frozen_plus_dihedral(tmp_path: Path) -> None:
    """Frozen atoms with a dihedral are refused up front; so is no constraint at all."""
    constraint = DihedralConstraint(atoms=(0, 1, 2, 3), value_deg=0.0)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        with pytest.raises(OptimizerInputError, match="refused"):
            run_constrained_point(
                butane(),
                uff_recipe(),
                store,
                water_state(),
                frozen_atom_indices=[0],
                dihedral_constraints=[constraint],
            )
        with pytest.raises(OptimizerInputError, match="at least one"):
            run_constrained_point(butane(), uff_recipe(), store, water_state())


def test_unknown_engine_tag_needs_registry() -> None:
    """build_engine uses ENGINE_CLASSES by tag."""
    from eta_rxncat.orchestrator import build_engine

    engine = build_engine(StageConfig(kind="single_point", engine="rdkit_ff", method="uff"), {})
    assert isinstance(engine, RDKitFFEngine)
