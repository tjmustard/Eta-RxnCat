"""``v070.derive_samples`` and a clashed sample (v0.7.1, R37; v0.7.0's ``defd982``).

Offline: the ensemble run is synthetic and the store rows are planted, so no engine runs. A
registered stub engine only supplies the identity the planted pre-relax keys are built with.
"""

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from e2e_env import engine_for
from t3 import ts_recipe
from t4 import member_gates
from v070 import derive_samples, enumerate_one, pathway_spec

from eta_rxncat.conformers import sample_ts_conformers
from eta_rxncat.core import (
    EngineIdentity,
    MolecularState,
    TSEnsemble,
    TSEnsembleExclusion,
    TSEnsembleMember,
    TSEnsembleOptions,
)
from eta_rxncat.engines import Engine, OptionSpec, RawResult
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import (
    ENGINE_CLASSES,
    Recipe,
    SampleKeys,
    TSEnsembleRun,
    enumerated_pathway_inputs,
)
from eta_rxncat.orchestrator.ts_ensemble import _PreRelax
from eta_rxncat.store import ArtifactStatus, ArtifactStore, build_stage_key


class StubEngine(Engine):
    """An identity-only stand-in for the xtb engine; evaluating it is an error."""

    tag = "xtb_subprocess"
    ENGINE_IMPL: ClassVar[int] = 1
    OPTIONS: ClassVar[dict[str, OptionSpec]] = {"alpb_state": OptionSpec(str, "gsolv")}

    @property
    def identity(self) -> EngineIdentity:
        """A fixed stub identity."""
        return EngineIdentity(name="xtb_subprocess", version="stub-1")

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        raise AssertionError("derive_samples must not evaluate the engine")


def test_a_clashed_sample_has_no_keys_even_with_rows_in_the_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``seed_clash`` sample records only template, index, source and species.

    The store holds a pre-relax row for the clashed start, as a store copied from an earlier run
    does. This fails on ``bf7b949``'s ``derive_samples`` with its ``clashed`` branch removed: that
    logic redrew the starts, found the planted row and recorded its ``pre_relax_key``.
    """
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", StubEngine)
    inputs, candidate = enumerate_one("ethyl")
    spec = pathway_spec(inputs, "endo")
    assert candidate.graph is not None
    (node,) = [n for n in candidate.graph.nodes if n.id == spec.node_id]
    (template,) = node.templates
    stage, runtime = engine_for("xtb")
    recipe = Recipe("xtb", stage, GeometricOptimizer(), engine_runtime=runtime)
    ensemble_inputs = enumerated_pathway_inputs(
        candidate, spec.node_id, template.id, ts_recipe(recipe), member_gates("xtb")
    )
    seed = ensemble_inputs.seed.start
    bonds = perceive_bonds(seed)
    pairs = sorted((min(i, j), max(i, j)) for i, j in ensemble_inputs.seed.forming_bonds)
    clashed = sample_ts_conformers(
        seed, ensemble_inputs.core_indices, pairs, bonds, TSEnsembleOptions()
    )[0]

    with ArtifactStore(tmp_path / "s.sqlite") as store:
        pre = _PreRelax(
            ts_recipe(recipe), store, GeometricOptimizer(), ensemble_inputs.core_indices
        )
        planted = []
        for state in (seed, clashed.state):
            key = build_stage_key(state, pre.stage(), pre.engine.identity)
            store.put(key, ArtifactStatus.COMPLETED, {"failed_reason": "engine_error"})
            planted.append(key.key)
        member = TSEnsembleMember(
            index=0,
            source="seed",
            start_sha256="0" * 64,
            G_hartree=-1.0,
            degeneracy=1,
            rmsd_to_seed_angstrom=0.0,
            face=list(spec.expected_face),
            validation_passed_bool=True,
            weight=1.0,
        )
        ensemble = TSEnsemble(
            pathway="endo",
            temperature_k=298.15,
            reactant_key=ensemble_inputs.reactant_key,
            recipe_identity=pre.engine.identity,
            members=[member],
            excluded=[TSEnsembleExclusion(index=1, source=clashed.source, reason="seed_clash")],
            G_pathway_hartree=-1.0,
        )
        run = TSEnsembleRun(
            ensemble,
            {},
            SimpleNamespace(record=SimpleNamespace(state=seed), keys={}),  # type: ignore[arg-type]
            samples=(
                SampleKeys(0, "seed", planted[0], None, None),
                SampleKeys(1, clashed.source, None, None, None),
            ),
        )
        samples, timeouts = derive_samples(candidate, spec, run, template.id, recipe, "xtb", store)

    assert timeouts == []
    assert samples[0].pre_relax_key == planted[0]
    assert samples[1].model_dump(exclude_none=True) == {
        "template_id": template.id,
        "sample_index": 1,
        "source": clashed.source,
        "species_id": template.id,
    }
