"""Stage keys are byte-equal to v0.6.0's for the same inputs (v0.7.0 slice 06, ADR-0016).

``V060_KEYS`` were computed by ``stage_keys`` on the v0.6.0 tag's source. Frame capture adds
payload fields only, and ``optimize/prfo.py`` (whose bytes key ``ts_opt``) is not edited.
"""

from typing import ClassVar

from eta_rxncat.core import EngineIdentity, MolecularState, StageConfig
from eta_rxncat.engines import Engine, OptionSpec, RawResult
from eta_rxncat.optimize import GeometricOptimizer, PRFOOptimizer
from eta_rxncat.orchestrator import ENGINE_CLASSES, Recipe, TSRecipe, TSSpec
from eta_rxncat.orchestrator.species import _Runner, _with_kind
from eta_rxncat.orchestrator.ts import _TSRun
from eta_rxncat.orchestrator.ts_ensemble import _PreRelax
from eta_rxncat.store import ArtifactStore, build_stage_key

V060_PRFO_VERSION = "src-897c4e19cb4e738a"
V060_KEYS = {
    "geometry_opt": "49098c11962d275c2b2ac46c1c054f76ab90964bef45cabf10d138e76304b1d1",
    "geometry_opt_constrained": "159e30e59db9a57958e8f375181d7316cf9fa8c646a41969d370c0b772312d4f",
    "constrained_preopt": "0e7f97f0c7925e144d0618c157c9557cac842ef7914a89eeed5e151c9052153e",
    "ts_opt": "4a6d0dd6dfbe976e15b0fca9fdef96eddf261b979f51b033412fc5e6443d1756",
    "frequency": "2992429b3463346c71da04d3025e1ea8ba80cfcf2ac30304749558a3552dd3f8",
}

STAGE = StageConfig(kind="geometry_opt", engine="xtb_subprocess", method="gfn2")
STATE = MolecularState(
    symbols=["C", "O", "H", "N"],
    coordinates=[[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [-0.5, 0.9, 0.1], [0.4, 0.3, 2.2]],
    charge=0,
    spin_multiplicity=1,
    active_atom_indices=[0, 1, 3],
)


class KeyEngine(Engine):
    """A fixed-identity stand-in for xtb; it is never evaluated."""

    tag = "xtb_subprocess"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {"accuracy": OptionSpec(float, 1.0)}

    @property
    def identity(self) -> EngineIdentity:
        """A fixed fake identity."""
        return EngineIdentity(name="xtb_subprocess", version="fake-1")

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        raise AssertionError("key computation never evaluates")


def stage_keys(store: ArtifactStore) -> dict[str, str]:
    """Return the key of every stage kind whose payload this slice touches, and frequency."""
    optimizer = GeometricOptimizer()
    runner = _Runner.__new__(_Runner)
    runner.recipe = Recipe(name="k", engine_stage=STAGE, optimizer=optimizer)
    runner.engine = ENGINE_CLASSES["xtb_subprocess"](STAGE)  # type: ignore[assignment]
    ts_recipe = TSRecipe(name="k", engine_stage=STAGE, ts_optimizer=PRFOOptimizer())
    ts = _TSRun(TSSpec("t", STATE, ((0, 3),)), ts_recipe, store)
    pre = _PreRelax(ts_recipe, store, optimizer, [0, 1, 3])
    identity = runner.engine.identity
    stages = {
        "geometry_opt": runner.opt_stage(),
        "geometry_opt_constrained": runner.opt_stage("freeze:0,1"),
        "constrained_preopt": pre.stage(),
        "ts_opt": ts.ts_stage(),
        "frequency": _with_kind(ts.engine.stage, "frequency", ts.engine.stage.options),
    }
    return {name: build_stage_key(STATE, stage, identity).key for name, stage in stages.items()}


def test_stage_keys_equal_v060(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Every key equals the one v0.6.0 computes, ts_opt included."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", KeyEngine)
    assert PRFOOptimizer().identity.version == V060_PRFO_VERSION
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        assert stage_keys(store) == V060_KEYS
