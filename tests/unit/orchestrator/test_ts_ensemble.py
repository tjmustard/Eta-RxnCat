"""Tests for the TS ensemble runner on stub surfaces (v0.6.0, slice 06; G4, G7, G8, R1-R3, R19).

The surface is TS1a_n (18 atoms, forming bonds (1, 2) and (3, 5), core 0-5). A stub core-frozen
minimizer and a stub P-RFO decide each sample's fate from a *script* of tags: the tag travels in
``MolecularState.metadata`` (not keyed), and picks the saddle geometry, its energy offset and any
failure. Tag ``A`` is the seed's own saddle.
"""

import json
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest
from numpy.typing import NDArray
from test_ts_runner import STAGE, FakeEngine, FakeTS

from eta_rxncat.conformers import forming_bond_configuration
from eta_rxncat.core import (
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    TSEnsemble,
    TSEnsembleOptions,
    TSSearchResult,
)
from eta_rxncat.core.models import ScalarValue
from eta_rxncat.engines import (
    HARTREE_KCAL_MOL,
    Engine,
    EngineRuntimeError,
    EngineUnavailableError,
    OptionSpec,
    RawResult,
    ScfConvergenceError,
)
from eta_rxncat.mapping import perceive_bonds
from eta_rxncat.mapping.relax import CORE_FREEZE_TOLERANCE_ANGSTROM
from eta_rxncat.optimize import OptimizationFailedError, Optimizer, TSSearchFailedError
from eta_rxncat.orchestrator import (
    ENGINE_CLASSES,
    TSRecipe,
    TSRunResult,
    TSSpec,
    run_ts_ensemble,
    run_ts_ensemble_detailed,
)
from eta_rxncat.orchestrator.ts_ensemble import PRE_RELAX_BUDGET_S
from eta_rxncat.store import ArtifactStore
from eta_rxncat.thermo import atomic_masses_amu
from eta_rxncat.thermo.constants import J_PER_MOL_TO_HARTREE, R_GAS

Array = NDArray[np.float64]
XYZ = Path(__file__).resolve().parents[2] / "e2e" / "data" / "e2e5" / "xyz" / "TS1a_n.xyz"
FORMING = ((1, 2), (3, 5))
CORE = [0, 1, 2, 3, 4, 5]
REACTANTS = (("C1C=CC=C1", 1), ("C1=C1", 1))
BASE_G = -100.0
OPTIONS = TSEnsembleOptions(n_perturb=20, max_research=20)

DE_KCAL = {"lowdg": 0.03, "highdg": 0.2, "B": 0.4, "far": 4.0}
"""Energy offsets (kcal/mol) of the tags; the rest are at 0."""

# --- The surface ---------------------------------------------------------------------------------


def _load() -> MolecularState:
    lines = XYZ.read_text(encoding="utf-8").split("\n")
    rows = [line.split() for line in lines[2 : 2 + int(lines[0])]]
    return MolecularState(
        symbols=[r[0] for r in rows],
        coordinates=[[float(x) for x in r[1:4]] for r in rows],
        charge=0,
        spin_multiplicity=1,
        active_atom_indices=CORE,
    )


SEED_STATE = _load()
SEED_XYZ = np.asarray(SEED_STATE.coordinates)
N_ATOMS = len(SEED_STATE.symbols)
BONDS = perceive_bonds(SEED_STATE)
SHIFT_ORDER = ["A", "lowdg", "highdg", "gate", "two_imag", "undet"]


def _crossover(xyz: Array) -> Array:
    """Reflect the dienophile's non-core atoms through the plane of C2, C3 and the diene normal."""
    seen, stack = {2}, [2]
    while stack:
        atom = stack.pop()
        for i, j in BONDS:
            for a, b in ((i, j), (j, i)):
                if a == atom and b not in seen:
                    seen.add(b)
                    stack.append(b)
    normal = np.cross(xyz[1] - xyz[0], xyz[4] - xyz[0])
    normal /= np.linalg.norm(normal)
    plane_normal = np.cross(xyz[3] - xyz[2], normal)
    plane_normal /= np.linalg.norm(plane_normal)
    origin = (xyz[2] + xyz[3]) / 2
    out = xyz.copy()
    for atom in sorted(seen - set(CORE)):
        out[atom] = xyz[atom] - 2.0 * ((xyz[atom] - origin) @ plane_normal) * plane_normal
    return out


def _group(carbon: int) -> list[int]:
    """Return a CH2 carbon and its hydrogens (they move together, so no bond breaks)."""
    hydrogens = [
        b if a == carbon else a
        for a, b in BONDS
        if carbon in (a, b) and SEED_STATE.symbols[b if a == carbon else a] == "H"
    ]
    return [carbon, *hydrogens]


def saddle_coordinates(tag: str) -> Array:
    """Return the saddle geometry a tag converges to."""
    xyz = SEED_XYZ.copy()
    tag = "A" if tag == "seed" else tag
    if tag == "X":
        return _crossover(xyz)
    if tag == "conn":
        xyz[16] += np.array([0.0, 0.0, 3.0])
        return xyz
    if tag == "B":
        xyz[_group(6)] += np.array([0.35, 0.0, 0.1])
        xyz[_group(7)] += np.array([0.0, 0.3, 0.1])
        return xyz
    if tag == "far":
        xyz[_group(6)] += np.array([-0.35, 0.3, 0.0])
        xyz[_group(7)] += np.array([0.3, -0.3, 0.2])
        return xyz
    k = SHIFT_ORDER.index(tag) if tag in SHIFT_ORDER else len(SHIFT_ORDER)
    xyz[6:] += np.array([1.0e-3 * k, 0.0, 0.0])
    return xyz


def _energy(tag: str) -> float:
    return BASE_G + DE_KCAL.get(tag, 0.0) / HARTREE_KCAL_MOL


def stub_hessian(coords: Array, frequencies: Sequence[float]) -> list[list[float]]:
    """Return a Hessian whose lowest mode is the in-phase stretch of both forming bonds."""
    hartree_j, bohr_m, amu_kg, c_cm = (
        4.3597447222071e-18,
        0.529177210903e-10,
        1.66053906660e-27,
        2.99792458e10,
    )

    def eigenvalue(w: float) -> float:
        omega = 2.0 * np.pi * c_cm * abs(w)
        return float(np.copysign(omega**2 * bohr_m**2 * amu_kg / hartree_j, w))

    masses = atomic_masses_amu(SEED_STATE.symbols)
    sqrt_m = np.repeat(np.sqrt(masses), 3)
    r = coords - (masses[:, None] * coords).sum(axis=0) / masses.sum()
    rigid = []
    for axis in range(3):
        t = np.zeros_like(coords)
        t[:, axis] = 1.0
        rigid.append(t.ravel() * sqrt_m)
        unit = np.zeros(3)
        unit[axis] = 1.0
        rigid.append(np.cross(unit, r).ravel() * sqrt_m)
    u, _, _ = np.linalg.svd(np.column_stack(rigid), full_matrices=True)
    comp = u[:, 6:]
    stretch = np.zeros_like(coords)
    for i, j in FORMING:
        bond = (coords[j] - coords[i]) / np.linalg.norm(coords[j] - coords[i])
        stretch[i] -= bond
        stretch[j] += bond
    q0 = comp @ (comp.T @ (sqrt_m * stretch.ravel()))
    q0 /= np.linalg.norm(q0)
    rest = np.linalg.qr(comp - np.outer(q0, q0 @ comp))[0][:, : comp.shape[1] - 1]
    basis = np.column_stack([q0, rest])
    hessian = (basis @ np.diag([eigenvalue(f) for f in frequencies]) @ basis.T) * np.outer(
        sqrt_m, sqrt_m
    )
    return (0.5 * (hessian + hessian.T)).tolist()


_POSITIVE = list(np.linspace(300.0, 3200.0, 3 * N_ATOMS - 6 - 1))
ONE_IMAGINARY = [-400.0, *_POSITIVE]
TWO_IMAGINARY = [-400.0, -100.0, *_POSITIVE[1:]]


def tag_of(state: MolecularState) -> str:
    """Return the scripted tag a state carries (``A`` when none)."""
    return str(state.metadata.get("tag", "A"))


class TagEngine(FakeEngine):
    """The fake xtb engine on the TS1a_n surface: energy and Hessian follow the state's tag."""

    def _evaluate(self, state: MolecularState, *, forces: bool, hessian: bool) -> RawResult:
        type(self).calls += 1
        coords = np.asarray(state.coordinates)
        tag = tag_of(state)
        frequencies = TWO_IMAGINARY if tag == "two_imag" else ONE_IMAGINARY
        return RawResult(
            energy_hartree=_energy(tag),
            device="cpu",
            forces_hartree_per_bohr=np.zeros_like(coords).tolist() if forces else None,
            hessian_hartree_per_bohr2=stub_hessian(coords, frequencies) if hessian else None,
            hessian_method="analytic" if hessian else None,
            hessian_max_asymmetry=0.0 if hessian else None,
        )


class TagTS(FakeTS):
    """A P-RFO stand-in: converges any start to the saddle its tag names, or fails as scripted."""

    def find_saddle(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        forming_bonds: Sequence[tuple[int, int]] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> TSSearchResult:
        """Evaluate once, then return the tag's saddle (or raise the tag's failure)."""
        tag = tag_of(state)
        engine.evaluate(state, forces=True)
        if tag == "fail":
            raise TSSearchFailedError(
                "stub", reason="max_steps", steps=("0",), last_energy_hartree=-1.0
            )
        if tag == "scf":
            raise ScfConvergenceError("stub SCF failure", steps=("diis",))
        if tag == "engine":
            raise EngineRuntimeError("stub engine crash")
        if tag == "unavail":
            raise EngineUnavailableError("stub: no engine on this host")
        saddle = state.model_copy(
            update={"coordinates": saddle_coordinates(tag).tolist(), "metadata": {"tag": tag}}
        )
        return super().find_saddle(saddle, engine, forming_bonds=forming_bonds, options=options)


class TagRelax(Optimizer):
    """A core-frozen minimizer stand-in: tags each call from a script and counts the calls."""

    OPTIONS: ClassVar[Mapping[str, OptionSpec]] = {"maxiter": OptionSpec(int, 300)}

    def __init__(self, script: Sequence[str] = ()) -> None:
        """``script[k]`` is the tag of the ``k``-th call; later calls get ``A``."""
        self.script = list(script)
        self.calls = 0
        self.frozen_seen: list[tuple[int, ...]] = []
        self.core_moves: list[float] = []

    @property
    def identity(self) -> OptimizerIdentity:
        """A fixed stub identity."""
        return OptimizerIdentity(name="geometric", version="stub-1")

    def minimize(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        frozen_atom_indices: Sequence[int] = (),
        dihedral_constraints: Sequence[Any] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> OptimizationResult:
        """Evaluate once and return the state, tagged, with the core nudged by 5e-8 Angstrom."""
        tag = self.script[self.calls] if self.calls < len(self.script) else "A"
        self.calls += 1
        self.frozen_seen.append(tuple(frozen_atom_indices))
        engine.evaluate(state, forces=True)
        if tag == "pre_fail":
            raise OptimizationFailedError("stub", steps=(), last_energy_hartree=None)
        if tag == "pre_scf":
            raise ScfConvergenceError("stub pre-relax SCF failure", steps=("diis",))
        if tag == "pre_engine":
            raise EngineRuntimeError("stub pre-relax crash")
        coords = np.asarray(state.coordinates).copy()
        move = 1.0e-3 if tag == "pre_core" else 5.0e-8
        coords[frozen_atom_indices[0]] += np.array([move, 0.0, 0.0])
        self.core_moves.append(move)
        return OptimizationResult(
            final_state=state.model_copy(
                update={"coordinates": coords.tolist(), "metadata": {"tag": tag}}
            ),
            final_energy_hartree=BASE_G,
            converged=True,
            n_steps=1,
            n_engine_calls=1,
            recovery_steps=[],
            optimizer=self.identity,
            options=self.resolved_options(options),
        )


def gates(result: TSRunResult) -> dict[str, bool]:
    """Stub member gates: the ``gate`` tag fails the active-core check."""
    assert result.record is not None
    return {"mode_count": True, "active_core": tag_of(result.record.state) != "gate"}


@pytest.fixture(autouse=True)
def idle_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hold the load average at zero, so the load-scaled budget (R7) is the base budget."""
    monkeypatch.setattr("os.getloadavg", lambda: (0.0, 0.0, 0.0))


@pytest.fixture(autouse=True)
def tag_engine(monkeypatch: pytest.MonkeyPatch) -> type[TagEngine]:
    """Route xtb_subprocess to the tag engine."""
    monkeypatch.setitem(ENGINE_CLASSES, "xtb_subprocess", TagEngine)
    monkeypatch.setattr(TagEngine, "calls", 0)
    monkeypatch.setattr(TagEngine, "scf_failure", False)
    return TagEngine


def recipe() -> TSRecipe:
    """The TS recipe on the stub surface."""
    return TSRecipe(name="stub", engine_stage=STAGE, ts_optimizer=TagTS())


def seed_spec(tag: str = "seed") -> TSSpec:
    """The seed TS spec; its tag decides which saddle it converges to."""
    return TSSpec(
        ts_id="TS1a_n",
        start=SEED_STATE.model_copy(update={"metadata": {"tag": tag}}),
        forming_bonds=FORMING,
    )


def ensemble(
    store_path: Path,
    script: Sequence[str] = (),
    *,
    seed_tag: str = "seed",
    relax: TagRelax | None = None,
    options: TSEnsembleOptions = OPTIONS,
):
    """Run the ensemble once and return (run, relax stub)."""
    relax = relax if relax is not None else TagRelax(script)
    with ArtifactStore(store_path) as store:
        run = run_ts_ensemble_detailed(
            seed_spec(seed_tag),
            recipe(),
            store,
            optimizer=relax,
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=options,
            member_gates=gates,
        )
    return run, relax


def reasons(result: TSEnsemble) -> dict[int, str]:
    """Map each excluded index to its reason."""
    return {e.index: e.reason for e in result.excluded}


# --- The seed ------------------------------------------------------------------------------------


def test_seed_only_ensemble(tmp_path: Path) -> None:
    """With every sample re-converging onto the seed's saddle, the ensemble is one member."""
    run, relax = ensemble(tmp_path / "s.sqlite")
    result = run.ensemble
    assert result.failed_reason is None
    assert [m.index for m in result.members] == [0]
    assert result.members[0].source == "seed"
    assert result.members[0].weight == 1.0
    assert result.members[0].pre_relax_wall_time_s is None
    assert result.G_pathway_hartree == pytest.approx(result.members[0].G_hartree, abs=1e-15)
    assert relax.calls == 20 and len(result.merges) == relax.calls  # every sample merged
    assert result.excluded == []
    assert result.temperature_k == 298.15 and result.pathway == "endo"


def test_failing_seed_stops_sampling(tmp_path: Path) -> None:
    """A seed whose search fails: ``seed:<reason>``, nothing sampled, no pre-relax."""
    run, relax = ensemble(tmp_path / "s.sqlite", seed_tag="fail")
    assert run.ensemble.failed_reason == "seed:ts_search_failed:max_steps"
    assert run.ensemble.members == [] and run.ensemble.G_pathway_hartree is None
    assert relax.calls == 0
    assert run.metrics["constrained_preopt"].engine_calls == 0


def test_seed_that_fails_a_gate_stops_sampling(tmp_path: Path) -> None:
    """A seed that fails its gates: ``seed:gate_failed:<check>``."""
    run, relax = ensemble(tmp_path / "s.sqlite", seed_tag="gate")
    assert run.ensemble.failed_reason == "seed:gate_failed:active_core"
    assert relax.calls == 0


def test_seed_with_two_imaginary_modes(tmp_path: Path) -> None:
    """A seed that fails validation: ``seed:ts_validation_failed``."""
    run, relax = ensemble(tmp_path / "s.sqlite", seed_tag="two_imag")
    assert run.ensemble.failed_reason == "seed:ts_validation_failed"
    assert relax.calls == 0


# --- Merging and weights (G4, US-005) -----------------------------------------------------------


SCRIPT_TWO_SADDLES = ["A", "lowdg", "highdg", "B", "A", "B", "lowdg", "A", "B", "highdg"]


def test_two_saddles_merge_copies(tmp_path: Path) -> None:
    """Exactly two saddles survive; re-converged copies merge, large dG ones are flagged."""
    run, relax = ensemble(tmp_path / "s.sqlite", SCRIPT_TWO_SADDLES)
    result = run.ensemble
    # sample k has index k + 1; the first B is script position 3 -> index 4
    assert [m.index for m in result.members] == [0, 4]
    assert result.excluded == []
    assert len(result.merges) == relax.calls + 1 - 2  # every candidate but the two kept
    kept_for = {m.merged_index: m.kept_index for m in result.merges}
    b_class = {4, 6, 9}
    assert all(kept_for[i] == 0 for i in range(1, relax.calls + 1) if i not in b_class)
    assert all(kept_for[i] == 4 for i in (6, 9))  # B-class into the first B
    flagged = {m.merged_index for m in result.flagged_merges}
    assert flagged == {3, 10}  # the two highdg (0.2 kcal/mol)
    by_index = {m.merged_index: m for m in result.merges}
    assert abs(by_index[2].dG_kcal_mol) < 0.05  # lowdg is merged and not flagged
    assert by_index[2].dG_kcal_mol == pytest.approx(0.03, abs=1e-3)
    assert 2 not in flagged and all(
        m.rmsd_angstrom < OPTIONS.rmsd_dedup_angstrom for m in result.merges
    )


def test_weights_and_free_energy_closed_form(tmp_path: Path) -> None:
    """Weights sum to 1 within 1e-12; G_pathway is the log-sum-exp; merged copies count once."""
    run, _ = ensemble(tmp_path / "s.sqlite", SCRIPT_TWO_SADDLES)
    result = run.ensemble
    assert abs(sum(m.weight for m in result.members) - 1.0) < 1e-12
    rt_eh = R_GAS * 298.15 * J_PER_MOL_TO_HARTREE
    gs = [m.G_hartree for m in result.members]
    lowest = min(gs)
    total = sum(m.degeneracy * np.exp(-(m.G_hartree - lowest) / rt_eh) for m in result.members)
    assert result.G_pathway_hartree == pytest.approx(lowest - rt_eh * np.log(total), abs=1e-12)
    for m in result.members:
        expected = m.degeneracy * np.exp(-(m.G_hartree - lowest) / rt_eh) / total
        assert m.weight == pytest.approx(expected, abs=1e-12)
    assert all(m.degeneracy == 1 and m.validation_passed_bool for m in result.members)
    assert all(m.face == [1, 1] for m in result.members)
    seed_m, b_m = result.members
    assert seed_m.rmsd_to_seed_angstrom == 0.0 and b_m.rmsd_to_seed_angstrom > 0.125
    assert (b_m.G_hartree - seed_m.G_hartree) * HARTREE_KCAL_MOL > 0.3


# --- Exclusions (R19) ---------------------------------------------------------------------------

SCRIPT_REASONS = [
    "fail",  # 1  ts_search_failed:max_steps
    "scf",  # 2  scf_convergence
    "engine",  # 3  engine_error (cached)
    "two_imag",  # 4  ts_validation_failed
    "gate",  # 5  gate_failed:active_core
    "X",  # 6  face_mismatch
    "conn",  # 7  connectivity_changed
    "far",  # 8  outside_window
    "pre_core",  # 9  pre_relax_failed:CoreDisplacementError
    "pre_fail",  # 10 pre_relax_failed:OptimizationFailedError
    "pre_scf",  # 11 scf_convergence (pre-relax)
    "pre_engine",  # 12 engine_error (pre-relax)
    "B",  # 13 a valid distinct saddle
]
EXPECTED = {
    1: "ts_search_failed:max_steps",
    2: "scf_convergence",
    3: "engine_error",
    4: "ts_validation_failed",
    5: "gate_failed:active_core",
    6: "face_mismatch",
    7: "connectivity_changed",
    8: "outside_window",
    9: "pre_relax_failed:CoreDisplacementError",
    10: "pre_relax_failed:OptimizationFailedError",
    11: "scf_convergence",
    12: "engine_error",
}


def test_every_exclusion_reason_is_recorded(tmp_path: Path) -> None:
    """R19: each failure is excluded with its reason, source and index; the rest is summed."""
    run, _ = ensemble(tmp_path / "s.sqlite", SCRIPT_REASONS)
    result = run.ensemble
    assert reasons(result) == EXPECTED
    assert [m.index for m in result.members] == [0, 13]
    assert result.failed_reason is None
    samples = {e.index: e for e in result.excluded}
    assert all(e.source.startswith(("fragment_embed:", "perturb:")) for e in samples.values())
    assert all(e.pre_relax_wall_time_s is not None for e in samples.values())
    assert all(m.pre_relax_wall_time_s is not None for m in result.members[1:])


def test_face_undetermined_is_excluded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A member whose face cannot be judged is excluded ``face_undetermined``."""
    import eta_rxncat.orchestrator.ts_ensemble as module

    real = module.forming_bond_configuration

    def judge(state: MolecularState, forming: Any, bonds: Any) -> tuple[int, ...]:
        if tag_of(state) == "undet":
            raise module.FaceDescriptorError("stub: zero volume")
        return real(state, forming, bonds)

    monkeypatch.setattr(module, "forming_bond_configuration", judge)
    run, _ = ensemble(tmp_path / "s.sqlite", ["undet"])
    assert reasons(run.ensemble) == {1: "face_undetermined"}
    assert [m.index for m in run.ensemble.members] == [0]


def test_a_face_flip_is_the_descriptor_not_the_geometry_label(tmp_path: Path) -> None:
    """The crossover saddle really has the other face (the test surface is honest)."""
    flipped = SEED_STATE.model_copy(update={"coordinates": saddle_coordinates("X").tolist()})
    assert forming_bond_configuration(SEED_STATE, FORMING, BONDS) == (1, 1)
    assert forming_bond_configuration(flipped, FORMING, BONDS) == (-1, -1)


def test_host_errors_propagate(tmp_path: Path) -> None:
    """EngineUnavailableError is not a member failure: it raises and nothing is cached for it."""
    with pytest.raises(EngineUnavailableError):
        ensemble(tmp_path / "s.sqlite", ["unavail"])


def test_pathway_fails_only_with_no_summed_member(tmp_path: Path) -> None:
    """Even with every sample excluded the seed is a member, so the pathway does not fail."""
    run, _ = ensemble(tmp_path / "s.sqlite", ["fail"] * 10 + ["engine"] * 10)
    assert run.ensemble.failed_reason is None
    assert [m.index for m in run.ensemble.members] == [0]
    assert len(run.ensemble.excluded) == 20


# --- Cache (G7), pre-relax (G4, R5, R24) ---------------------------------------------------------


def test_second_call_is_all_cache_hits(tmp_path: Path) -> None:
    """G7: a second call makes zero engine calls and writes no rows, and returns an equal result."""
    path = tmp_path / "s.sqlite"
    first, relax = ensemble(path, SCRIPT_REASONS)
    calls = (TagEngine.calls, relax.calls)
    second, relax_again = ensemble(path, SCRIPT_REASONS)
    assert second.ensemble == first.ensemble
    assert (TagEngine.calls, relax_again.calls) == (calls[0], 0)
    for kind in ("constrained_preopt", "ts_opt", "frequency"):
        assert second.metrics[kind].engine_calls == 0, kind
        assert second.metrics[kind].rows_created == 0, kind
        assert second.metrics[kind].cache_hits > 0, kind
    assert first.metrics["constrained_preopt"].rows_created == relax.calls == 20
    assert first.metrics["constrained_preopt"].engine_calls == relax.calls


def test_pre_relax_freezes_the_core_within_the_bound(tmp_path: Path) -> None:
    """G4: the minimizer gets exactly the sorted core; accepted moves are within ADR-0032."""
    run, relax = ensemble(tmp_path / "s.sqlite", ["A", "pre_core", "B"])
    assert set(relax.frozen_seen) == {tuple(CORE)}
    accepted = [m for m in relax.core_moves if m != 1.0e-3]
    assert accepted and max(accepted) <= CORE_FREEZE_TOLERANCE_ANGSTROM
    assert reasons(run.ensemble) == {2: "pre_relax_failed:CoreDisplacementError"}


def test_only_the_three_stage_kinds_are_cached(tmp_path: Path) -> None:
    """R24: no new stage kind; the pre-relax rows are ``constrained_preopt``."""
    path = tmp_path / "s.sqlite"
    _, relax = ensemble(path, SCRIPT_TWO_SADDLES)
    with ArtifactStore(path) as store:
        assert len(store.query("constrained_preopt")) == relax.calls == 20
        assert store.query("ts_opt") and store.query("frequency")
        for kind in ("geometry_opt", "single_point", "conformer_search"):
            assert store.query(kind) == []


def test_detailed_run_reports_the_longest_pre_relax(tmp_path: Path) -> None:
    """R25: the run reports the maximum pre-relax wall time over the samples."""
    run, _ = ensemble(tmp_path / "s.sqlite", SCRIPT_TWO_SADDLES)
    walls = [m.pre_relax_wall_time_s for m in run.ensemble.members[1:]]
    assert run.max_pre_relax_wall_time_s is not None
    assert run.max_pre_relax_wall_time_s >= max(w for w in walls if w is not None)


def test_run_ts_ensemble_returns_the_ensemble(tmp_path: Path) -> None:
    """The plain entry point returns the same ensemble the detailed one carries."""
    detailed, _ = ensemble(tmp_path / "s.sqlite", SCRIPT_TWO_SADDLES)
    relax = TagRelax(SCRIPT_TWO_SADDLES)
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        plain = run_ts_ensemble(
            seed_spec(),
            recipe(),
            store,
            optimizer=relax,
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=OPTIONS,
            member_gates=gates,
        )
    assert relax.calls == 0  # served from the same store
    assert isinstance(plain, TSEnsemble)
    assert plain == detailed.ensemble


# --- The pre-relax wall budget (slice 13; R28) -------------------------------------------------


class SpinRelax(TagRelax):
    """A stalled core-frozen minimizer: the listed calls loop on numpy, with no engine call."""

    def __init__(self, script: Sequence[str], spin_calls: Sequence[int]) -> None:
        """``spin_calls`` are the zero-based call numbers that never return."""
        super().__init__(script)
        self.spin_calls = set(spin_calls)

    def minimize(
        self,
        state: MolecularState,
        engine: Engine,
        *,
        frozen_atom_indices: Sequence[int] = (),
        dihedral_constraints: Sequence[Any] = (),
        options: Mapping[str, ScalarValue] | None = None,
    ) -> OptimizationResult:
        """Spin on svd/eigh when this call is scripted to stall, else behave as ``TagRelax``."""
        if self.calls in self.spin_calls:
            self.calls += 1
            a = np.random.default_rng(1).random((40, 40))
            while True:
                np.linalg.svd(a)
                np.linalg.eigh(a @ a.T)
        return super().minimize(
            state,
            engine,
            frozen_atom_indices=frozen_atom_indices,
            dihedral_constraints=dihedral_constraints,
            options=options,
        )


TWO_SAMPLES = TSEnsembleOptions(n_perturb=20, max_research=2)
BUDGET_S = 2.0


def _budgeted(path: Path, relax: TagRelax, budget: float | None) -> Any:
    with ArtifactStore(path) as store:
        return run_ts_ensemble_detailed(
            seed_spec(),
            recipe(),
            store,
            optimizer=relax,
            core_indices=CORE,
            pathway="endo",
            reactant_key=REACTANTS,
            options=TWO_SAMPLES,
            member_gates=gates,
            pre_relax_budget_s=budget,
        )


def test_a_stalled_pre_relax_is_excluded_and_the_ensemble_continues(tmp_path: Path) -> None:
    """R28 requirements 1, 2, 6: the stall is cut and recorded, the next sample still counts."""
    start = time.perf_counter()
    run = _budgeted(tmp_path / "s.sqlite", SpinRelax(["spin", "B"], [0]), BUDGET_S)
    assert time.perf_counter() - start < BUDGET_S + 8.0
    assert run.ensemble.failed_reason is None
    assert reasons(run.ensemble) == {1: "pre_relax_failed:PreRelaxTimeout"}
    stalled = run.ensemble.excluded[0]
    assert stalled.pre_relax_wall_time_s is not None
    assert BUDGET_S <= stalled.pre_relax_wall_time_s <= BUDGET_S + 4.0
    assert run.max_pre_relax_wall_time_s == stalled.pre_relax_wall_time_s
    baseline, _ = ensemble(tmp_path / "base.sqlite", ["A", "B"], options=TWO_SAMPLES)
    good = [m for m in run.ensemble.members if m.index == 2]
    ref = [m for m in baseline.ensemble.members if m.index == 2]
    assert good and ref
    assert good[0].G_hartree == ref[0].G_hartree  # the engine still evaluates correctly


def test_the_cached_timeout_is_a_cache_hit(tmp_path: Path) -> None:
    """G7, R28 requirement 5: a second call re-runs nothing; the row holds the budget."""
    path = tmp_path / "s.sqlite"
    first = _budgeted(path, SpinRelax(["spin", "B"], [0]), BUDGET_S)
    calls = TagEngine.calls
    relax = SpinRelax(["spin", "B"], [0])
    second = _budgeted(path, relax, BUDGET_S)
    assert relax.calls == 0
    assert TagEngine.calls == calls
    assert second.ensemble == first.ensemble
    assert second.metrics["constrained_preopt"].rows_created == 0
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT payload_json FROM stage_artifacts WHERE stage_kind = ?", ("constrained_preopt",)
        ).fetchall()
    payloads = [json.loads(r[0]) for r in rows]
    timed = [p for p in payloads if p.get("failed_reason") == "pre_relax_failed:PreRelaxTimeout"]
    assert len(timed) == 1
    assert timed[0]["budget_s"] == BUDGET_S
    assert timed[0]["load1"] == 0.0
    assert timed[0]["budget_kind"] == "load_scaled_wall"


def test_a_loaded_host_records_the_effective_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R7: at 1.5 loads per CPU the row stores the scaled budget and the load it read."""
    monkeypatch.setattr("os.getloadavg", lambda: (30.0, 0.0, 0.0))
    monkeypatch.setattr("os.cpu_count", lambda: 20)
    path = tmp_path / "s.sqlite"
    _budgeted(path, SpinRelax(["spin", "B"], [0]), 1.0)
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT payload_json FROM stage_artifacts WHERE stage_kind = ?", ("constrained_preopt",)
        ).fetchall()
    (timed,) = [p for r in rows if "budget_s" in (p := json.loads(r[0]))]
    assert (timed["budget_s"], timed["load1"]) == (1.5, 30.0)
    assert timed["wall_time_s"] >= 1.5


def test_the_budget_is_not_part_of_the_stage_key(tmp_path: Path) -> None:
    """A run with another budget (or none) reuses the rows of the first."""
    path = tmp_path / "s.sqlite"
    first, relax = ensemble(path, ["A", "B"], options=TWO_SAMPLES)
    relax_again = TagRelax(["A", "B"])
    again = _budgeted(path, relax_again, 123.0)
    assert relax_again.calls == 0
    assert again.ensemble == first.ensemble


def test_the_default_budget_and_a_none_budget(tmp_path: Path) -> None:
    """R28 requirement 7: the default is 600 s; ``None`` starts no watchdog thread."""
    assert PRE_RELAX_BUDGET_S == 600.0
    before = threading.active_count()
    run = _budgeted(tmp_path / "s.sqlite", TagRelax(["A", "B"]), None)
    assert threading.active_count() == before
    assert run.ensemble.failed_reason is None


@pytest.mark.parametrize("budget", [0.0, -2.0, float("nan"), float("inf")])
def test_an_invalid_budget_raises_before_any_engine_call(tmp_path: Path, budget: float) -> None:
    """R28 requirement 7: a bad budget is refused before the seed or any pre-relax runs."""
    calls = TagEngine.calls
    relax = TagRelax()
    with pytest.raises(ValueError, match="budget"):
        _budgeted(tmp_path / "s.sqlite", relax, budget)
    assert TagEngine.calls == calls
    assert relax.calls == 0


# --- G8 -----------------------------------------------------------------------------------------


def test_import_loads_no_optimizer_stack() -> None:
    """G8: importing the runner loads none of torch, pyscf, fairchem, geometric."""
    code = (
        "import sys; import eta_rxncat.orchestrator.ts_ensemble; "
        "heavy = ('torch', 'pyscf', 'fairchem', 'geometric'); "
        "bad = [x for x in heavy if x in sys.modules]; assert not bad, bad"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
