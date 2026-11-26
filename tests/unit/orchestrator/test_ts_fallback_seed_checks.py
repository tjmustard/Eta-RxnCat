"""Tests for the seed clash and unintended-bond checks (v0.7.0, slice 15; G14, R35).

Engine-free: the stub surface of ``test_ts_ensemble`` and the fallback helpers of
``test_ts_fallback``. The known-answer geometries are measured starts of the v0.7.0 ethyl endo
GFN2 run (see each XYZ comment line).
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from test_ts_ensemble import (
    CORE,
    FORMING,
    OPTIONS,
    REACTANTS,
    SEED_STATE,
    TagEngine,
    TagRelax,
    TagTS,
    gates,
    reasons,
    seed_spec,
    tag_engine,
    tag_of,
)
from test_ts_fallback import candidate, fallback, outcomes

import eta_rxncat.orchestrator.ts_ensemble as module
import eta_rxncat.orchestrator.ts_fallback as fallback_module
from eta_rxncat.core import (
    EnumeratedCandidate,
    MolecularState,
    OptimizationResult,
    TSEnsembleOptions,
)
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.graft import CONTACT_FACTOR
from eta_rxncat.orchestrator import TSRecipe, run_ts_ensemble, run_ts_ensemble_detailed
from eta_rxncat.orchestrator.ts_ensemble import SEED_CLASH_FACTOR, bond_changes, find_clash
from eta_rxncat.store import ArtifactStore

__all__ = ["tag_engine"]  # the autouse fixture that routes xtb_subprocess to the tag engine

DATA = Path(__file__).parent / "data"
RECORD = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "v0.7.0"
    / "v070_enum_ethyl_endo_xtb.runrecord.json"
)
ONE = TSEnsembleOptions(n_perturb=2, max_research=1)
# A hydrogen moved next to a far carbon: it breaks its bond and forms a new one.
H_ATOM, FAR_ATOM = 16, 0


def moved(state: MolecularState) -> MolecularState:
    """``state`` with ``H_ATOM`` placed 1.05 Angstrom from ``FAR_ATOM``, away from the rest."""
    xyz = np.asarray(state.coordinates)
    outward = xyz[FAR_ATOM] - xyz.mean(axis=0)
    xyz = xyz.copy()
    xyz[H_ATOM] = xyz[FAR_ATOM] + 1.05 * outward / np.linalg.norm(outward)
    return state.model_copy(update={"coordinates": xyz.tolist()})


def changed_bonds() -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """The bonds ``moved`` makes and breaks on the seed geometry."""
    detail = bond_changes(moved(SEED_STATE), perceive_bonds(SEED_STATE), FORMING)
    assert detail is not None and detail.bonds_formed and detail.bonds_broken
    return detail.bonds_formed, detail.bonds_broken


class MovingRelax(TagRelax):
    """A minimizer whose calls in ``on`` return the ``moved`` geometry."""

    def __init__(self, on: Sequence[int], script: Sequence[str] = ()) -> None:
        super().__init__(script)
        self.on = set(on)

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Minimize as ``TagRelax`` does, then move the hydrogen on a chosen call."""
        call = self.calls
        result: OptimizationResult = super().minimize(state, engine, **kwargs)
        if call not in self.on:
            return result
        return result.model_copy(update={"final_state": moved(result.final_state)})


class HealingRelax(TagRelax):
    """A minimizer that returns the seed's geometry, so no sample's noise changes a bond."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Minimize as ``TagRelax`` does, then restore the seed's coordinates."""
        result: OptimizationResult = super().minimize(state, engine, **kwargs)
        healed = result.final_state.model_copy(update={"coordinates": SEED_STATE.coordinates})
        return result.model_copy(update={"final_state": healed})


class CountingTS(TagTS):
    """Counts the TS searches."""

    calls = 0

    def find_saddle(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Count, then search."""
        type(self).calls += 1
        return super().find_saddle(state, engine, **kwargs)


class MovingTS(TagTS):
    """A search whose ``move``-tagged starts converge to the ``moved`` saddle."""

    def find_saddle(self, state: MolecularState, engine: Any, **kwargs: Any) -> Any:
        """Search as ``TagTS`` does, then move the hydrogen for a ``move`` tag."""
        move = tag_of(state) == "move"
        result = super().find_saddle(state, engine, **kwargs)
        if not move:
            return result
        return result.model_copy(update={"final_state": moved(result.final_state)})


def run(
    path: Path,
    relax: TagRelax,
    *,
    ts: type[TagTS] = CountingTS,
    options: TSEnsembleOptions = ONE,
    seed_tag: str = "seed",
    seed_checks: bool = True,
    member_gates: Any = gates,
) -> Any:
    """Run the detailed ensemble once, counting the TS searches."""
    from test_ts_ensemble import STAGE

    CountingTS.calls = 0
    with ArtifactStore(path) as store:
        return run_ts_ensemble_detailed(
            seed_spec(seed_tag),
            TSRecipe(name="stub", engine_stage=STAGE, ts_optimizer=ts()),
            store,
            optimizer=relax,
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=options,
            member_gates=member_gates,
            seed_checks=seed_checks,
        )


# --- The known-answer geometries ----------------------------------------------------------------


def topology() -> tuple[list[str], list[tuple[int, int]]]:
    """The seed's symbols and topology: the graft output's bonds plus the forming bonds."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    state = MolecularState.model_validate(
        next(s["state"] for s in record["species"] if s["species_id"] == "TS1a_n__ethyl")
    )
    return state.symbols, [*perceive_bonds(state), (1, 2), (3, 5)]


def read_start(name: str, symbols: list[str]) -> MolecularState:
    """Read a stored start geometry."""
    lines = (DATA / f"{name}.xyz").read_text(encoding="utf-8").splitlines()
    rows = [line.split() for line in lines[2 : 2 + int(lines[0])]]
    assert [r[0] for r in rows] == symbols
    return MolecularState(
        symbols=symbols,
        coordinates=[[float(x) for x in r[1:4]] for r in rows],
        charge=0,
        spin_multiplicity=1,
    )


def test_the_factor_is_the_grafts() -> None:
    """The clash factor is graft's contact factor."""
    assert SEED_CLASH_FACTOR is CONTACT_FACTOR


def test_sample_six_start_clashes() -> None:
    """Sample 6: ethyl H21 sits 0.438 Angstrom from diene C4."""
    symbols, bonds = topology()
    detail = find_clash(read_start("v070_sample6_start", symbols), bonds)
    assert detail is not None and detail.check == "clash"
    assert detail.pair == (4, 21)
    assert detail.distance_angstrom == pytest.approx(0.438, abs=0.001)
    assert detail.ratio_to_covalent_sum == pytest.approx(0.409, abs=0.001)


def test_a_member_start_does_not_clash() -> None:
    """The member of the same run passes."""
    symbols, bonds = topology()
    assert find_clash(read_start("v070_member1_start", symbols), bonds) is None


@pytest.mark.parametrize(
    "topology_bonds, clashes",
    [([(0, 1), (1, 2)], False), ([(0, 1)], True), ([(0, 1), (1, 3), (3, 2)], True)],
    ids=["one-three", "unconnected", "one-four"],
)
def test_only_pairs_three_bonds_apart_are_judged(
    topology_bonds: list[tuple[int, int]], clashes: bool
) -> None:
    """Pairs within two bonds are skipped; unconnected and 1-4 pairs are judged."""
    state = MolecularState(
        symbols=["C"] * 4,
        coordinates=[[0, 0, 0], [1.4, 0, 0], [0.4, 0.4, 0], [9, 9, 9]],
        charge=0,
        spin_multiplicity=1,
    )
    detail = find_clash(state, topology_bonds)
    assert (detail is not None and detail.pair == (0, 2)) is clashes


def test_forming_bonds_are_ignored_on_both_sides() -> None:
    """A forming pair is never a change, present or absent, in either order."""
    bonds = perceive_bonds(SEED_STATE)
    reversed_forming = [(j, i) for i, j in FORMING]
    assert bond_changes(SEED_STATE, [*bonds, *FORMING], reversed_forming) is None


# --- The ensemble -------------------------------------------------------------------------------


def clash_first_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sample 1's start clash."""
    real = module.sample_ts_conformers

    def sampler(*args: Any, **kwargs: Any) -> Any:
        first, *rest = real(*args, **kwargs)
        state = first.state
        xyz = np.asarray(state.coordinates).copy()
        xyz[H_ATOM] = xyz[FAR_ATOM] + np.array([0.0, 0.0, 0.4])
        clashing = state.model_copy(update={"coordinates": xyz.tolist()})
        assert find_clash(clashing, [*perceive_bonds(SEED_STATE), *FORMING]) is not None
        return [first.__class__(**{**vars(first), "state": clashing}), *rest]

    monkeypatch.setattr(module, "sample_ts_conformers", sampler)


def test_a_clashing_sample_reaches_no_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``seed_clash``: no pre-relax, no search, no wall time, the slot kept."""
    clash_first_sample(monkeypatch)
    relax = TagRelax()
    result = run(tmp_path / "s.sqlite", relax)
    (exclusion,) = result.ensemble.excluded
    assert (exclusion.index, exclusion.reason) == (1, "seed_clash")
    assert exclusion.pre_relax_wall_time_s is None
    assert exclusion.detail is not None and exclusion.detail.pair is not None
    assert H_ATOM in exclusion.detail.pair
    assert relax.calls == 0 and CountingTS.calls == 1
    assert result.metrics["constrained_preopt"].engine_calls == 0
    assert result.metrics["constrained_preopt"].rows_created == 0
    assert result.max_pre_relax_wall_time_s is None
    assert result.ensemble.failed_reason is None


def test_the_other_samples_keep_their_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is drawn in a clashing sample's place."""
    clash_first_sample(monkeypatch)
    relax = HealingRelax()
    result = run(tmp_path / "s.sqlite", relax, options=OPTIONS)
    assert reasons(result.ensemble) == {1: "seed_clash"}
    assert relax.calls == OPTIONS.max_research - 1
    assert sorted(m.merged_index for m in result.ensemble.merges) == list(
        range(2, OPTIONS.max_research + 1)
    )


def test_a_pre_relax_that_changes_a_bond_is_excluded_before_the_search(tmp_path: Path) -> None:
    """``bond_changed:pre_relax``: no ``ts_opt`` call for the sample."""
    relax = MovingRelax([0])
    result = run(tmp_path / "s.sqlite", relax)
    (exclusion,) = result.ensemble.excluded
    assert (exclusion.index, exclusion.reason) == (1, "bond_changed:pre_relax")
    assert exclusion.pre_relax_wall_time_s is not None
    formed, broken = changed_bonds()
    assert exclusion.detail is not None
    assert (exclusion.detail.bonds_formed, exclusion.detail.bonds_broken) == (formed, broken)
    assert relax.calls == 1 and CountingTS.calls == 1  # the seed's search only


def test_a_search_that_changes_a_bond_is_excluded_before_the_gates(tmp_path: Path) -> None:
    """``bond_changed:ts``: the member gates never see the sample."""
    judged: list[str] = []

    def spy(result: Any) -> dict[str, bool]:
        judged.append(tag_of(result.record.state))
        return gates(result)

    result = run(tmp_path / "s.sqlite", TagRelax(["move"]), ts=MovingTS, member_gates=spy)
    (exclusion,) = result.ensemble.excluded
    assert (exclusion.index, exclusion.reason) == (1, "bond_changed:ts")
    assert exclusion.detail is not None and exclusion.detail.bonds_formed
    assert judged == ["seed"]  # the seed only


def test_a_seed_search_that_changes_a_bond_fails_the_seed(tmp_path: Path) -> None:
    """``seed:bond_changed:ts`` before the gates; nothing sampled."""
    relax = TagRelax()
    result = run(tmp_path / "s.sqlite", relax, ts=MovingTS, seed_tag="move")
    assert result.ensemble.failed_reason == "seed:bond_changed:ts"
    detail = result.ensemble.failed_detail
    assert detail is not None and detail.check == "bond_changed"
    assert detail.bonds_formed and detail.bonds_broken
    assert result.ensemble.members == [] and relax.calls == 0


def test_without_seed_checks_nothing_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default is v0.6.0: the clashing start is relaxed; a changed TS is ``connectivity``."""
    clash_first_sample(monkeypatch)
    relax = TagRelax(["move"])
    result = run(tmp_path / "s.sqlite", relax, ts=MovingTS, seed_checks=False)
    assert relax.calls == 1
    assert reasons(result.ensemble) == {1: "connectivity_changed"}
    assert all("detail" not in e for e in result.ensemble.model_dump()["excluded"])


def test_the_plain_entry_point_passes_seed_checks(tmp_path: Path) -> None:
    """``run_ts_ensemble`` takes the keyword."""
    from test_ts_ensemble import recipe

    with ArtifactStore(tmp_path / "s.sqlite") as store:
        ensemble = run_ts_ensemble(
            seed_spec(),
            recipe(),
            store,
            optimizer=MovingRelax([0]),
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=ONE,
            member_gates=gates,
            seed_checks=True,
        )
    assert reasons(ensemble) == {1: "bond_changed:pre_relax"}


# --- The fallback -------------------------------------------------------------------------------


def with_contacts(built: EnumeratedCandidate, template_ref: str) -> EnumeratedCandidate:
    """``built`` with one close contact recorded on ``template_ref``'s graft record."""
    records = [
        r.model_copy(update={"close_contact_count": 1}) if r.template_id == template_ref else r
        for r in built.records
    ]
    return built.model_copy(update={"records": records})


def test_a_graft_with_close_contacts_is_never_seeded(tmp_path: Path) -> None:
    """``seed:seed_clash`` with no engine call."""
    relax = TagRelax()
    record, ran = fallback(tmp_path / "s.sqlite", relax, with_contacts(candidate(1), "t1"))
    assert outcomes(record) == [(1, "fell_through", "seed:seed_clash")]
    assert record.stop_reason == "all_templates_failed" and ran is None
    detail = record.attempts[0].detail
    assert detail is not None and detail.close_contact_count == 1
    assert record.attempts[0].wall_time_s == 0.0
    assert relax.calls == 0 and TagEngine.calls == 0


def test_close_contacts_fall_through_to_rank_two(tmp_path: Path) -> None:
    """Rank 2 is chosen."""
    record, ran = fallback(tmp_path / "s.sqlite", TagRelax(), with_contacts(candidate(), "t1"))
    assert record.chosen_template_id == "t2__c" and ran is not None
    assert outcomes(record) == [(1, "fell_through", "seed:seed_clash"), (2, "chosen", None)]
    assert record.attempts[1].detail is None


def test_a_graft_pre_relax_that_changes_a_bond_falls_through(tmp_path: Path) -> None:
    """``seed:bond_changed:pre_relax`` before the face check; rank 2 is chosen."""
    record, _ = fallback(tmp_path / "s.sqlite", MovingRelax([0]))
    assert outcomes(record) == [
        (1, "fell_through", "seed:bond_changed:pre_relax"),
        (2, "chosen", None),
    ]
    detail = record.attempts[0].detail
    assert detail is not None and detail.bonds_formed and detail.bonds_broken


def test_a_seed_search_that_changes_a_bond_falls_through(tmp_path: Path) -> None:
    """The ensemble's ``seed:bond_changed:ts`` carries its detail into the attempt."""
    record, _ = fallback(tmp_path / "s.sqlite", TagRelax(["move"]), ts=MovingTS)
    assert outcomes(record) == [
        (1, "fell_through", "seed:bond_changed:ts"),
        (2, "chosen", None),
    ]
    detail = record.attempts[0].detail
    assert detail is not None and detail.bonds_formed


def test_the_fallback_turns_seed_checks_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback's ensemble is run with ``seed_checks=True``."""
    seen: list[object] = []
    real = fallback_module.run_ts_ensemble_detailed

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen.append(kwargs.get("seed_checks"))
        return real(*args, **kwargs)

    monkeypatch.setattr(fallback_module, "run_ts_ensemble_detailed", spy)
    fallback(tmp_path / "s.sqlite", TagRelax())
    assert seen == [True]
