"""Offline tests of the flexible-ensemble inputs and helpers (slice 14); no engine is called."""

import math
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from fixtures import read_xyz
from t4_flexible import (
    DATA,
    MAX_ALIGNMENT_RMSD_ANGSTROM,
    SERIES,
    SMILES,
    TIMEOUT_REASON,
    bonds_of,
    build_fragment,
    fit_rmsd,
    flex,
    fragment_roles,
    gates,
    graft_series,
    guarded_graft_pre_relax,
    load_flex_fixture,
    lower_fit_order,
    non_decreasing_report,
    sha256_file,
    template_state,
)

from eta_rxncat.core import MolecularState, OptimizationResult, OptimizerIdentity
from eta_rxncat.mapping import perceive_bonds

SIZES = {"ethyl": 24, "npropyl": 27, "nbutyl": 30}


def test_the_fixture_lists_the_three_chains_in_order() -> None:
    """The series is ethyl, n-propyl, n-butyl, each with its stated expectation."""
    fixture = flex()
    assert [s.r_group for s in fixture.series] == list(SERIES)
    assert [s.smiles for s in fixture.series] == [SMILES[r] for r in SERIES]
    assert [s.expected_members for s in fixture.series] == [3, 4, 5]
    assert fixture.core == (0, 1, 2, 3, 4, 5) and fixture.forming_bonds == ((1, 2), (3, 5))
    assert fixture.pre_relax_maxiter == 200 and fixture.temperature_k == 298.15


@pytest.mark.parametrize("r_group", SERIES)
def test_fragment_sha256_matches_the_yaml_and_sources(r_group: str) -> None:
    """Requirement 2: each fragment's bytes equal the YAML's and the SOURCES.md row's sha256."""
    series = flex().get(r_group)
    digest = sha256_file(series.fragment)
    assert digest == series.sha256
    sources = (DATA / "SOURCES.md").read_text(encoding="utf-8")
    row = next(line for line in sources.splitlines() if f"xyz/r_{r_group}_cyclopropene.xyz" in line)
    assert digest in row


@pytest.mark.parametrize("r_group", SERIES)
def test_fragment_roles_equal_the_yaml_literals(r_group: str) -> None:
    """The stored ring, H and sp2-H indices are the SMILES topology's."""
    series = flex().get(r_group)
    roles = fragment_roles(series.smiles)
    assert series.ring_sp3 == roles["ring_sp3"]
    assert series.ring_h == roles["ring_h"]
    assert list(series.fragment_delete) == roles["sp2_h"]
    assert sorted(series.sp2_order) == roles["sp2"]
    assert len(read_xyz(series.fragment, 0, 1).symbols) == len(build_fragment(series.smiles)[0])


@pytest.mark.parametrize("r_group", SERIES)
def test_the_chain_is_all_anti(r_group: str) -> None:
    """HF-14: ring-H, ring C, C-alpha, C-beta and every C-C-C-C dihedral outward are 180 degrees."""
    series = flex().get(r_group)
    roles = fragment_roles(series.smiles)
    chain = roles["chain"]
    xyz = np.asarray(read_xyz(series.fragment, 0, 1).coordinates)

    def dihedral(a: int, b: int, c: int, d: int) -> float:
        b0, b1, b2 = xyz[a] - xyz[b], xyz[c] - xyz[b], xyz[d] - xyz[c]
        b1 = b1 / np.linalg.norm(b1)
        v, w = b0 - (b0 @ b1) * b1, b2 - (b2 @ b1) * b1
        return math.degrees(math.atan2(np.cross(b1, v) @ w, v @ w))

    for k in range(1, len(chain) - 1):
        first = roles["ring_h"] if k == 1 else chain[k - 2]
        angle = dihedral(first, chain[k - 1], chain[k], chain[k + 1])
        assert abs(abs(angle) - 180.0) < 0.5, (r_group, k, angle)


@pytest.mark.parametrize("r_group", SERIES)
def test_the_stored_sp2_order_is_the_lower_fit(r_group: str) -> None:
    """HF-14: the order is the lower-RMSD fit; the other is the mirror fit (about 0.49 Angstrom)."""
    fixture = flex()
    series = fixture.get(r_group)
    assert lower_fit_order(fixture, series) == series.sp2_order
    a, b = sorted(series.sp2_order)
    other = (b, a) if series.sp2_order == (a, b) else (a, b)
    assert fit_rmsd(fixture, series, series.sp2_order) <= MAX_ALIGNMENT_RMSD_ANGSTROM
    assert fit_rmsd(fixture, series, other) > 0.4


@pytest.mark.parametrize("r_group", SERIES)
def test_each_graft_fits_without_contacts_and_has_the_expected_bonds(r_group: str) -> None:
    """Requirement 2: RMSD <= 0.05, no close contacts, bonds = template - C7-H16 + the chain."""
    fixture = flex()
    series = fixture.get(r_group)
    result = graft_series(fixture, series)
    assert len(result.product.symbols) == SIZES[r_group]
    assert result.alignment_rmsd_angstrom <= MAX_ALIGNMENT_RMSD_ANGSTROM
    assert result.close_contacts == []
    to_product = {i: p for p, (src, i) in enumerate(result.index_map) if src == "template"}
    from_fragment = {i: p for p, (src, i) in enumerate(result.index_map) if src == "fragment"}
    template_bonds = {
        (min(to_product[i], to_product[j]), max(to_product[i], to_product[j]))
        for i, j in perceive_bonds(template_state(fixture))
        if 16 not in (i, j)
    }
    roles = fragment_roles(series.smiles)
    # The aligned fragment atoms take the template atoms' places (ring C(sp3) is C7).
    place = {**from_fragment, roles["ring_sp3"]: to_product[7]}
    from rdkit import Chem

    mol = Chem.AddHs(Chem.MolFromSmiles(series.smiles))
    dropped = set(roles["sp2"]) | set(roles["sp2_h"]) | {roles["ring_h"]}
    chain_bonds = {
        (
            min(place[b.GetBeginAtomIdx()], place[b.GetEndAtomIdx()]),
            max(place[b.GetBeginAtomIdx()], place[b.GetEndAtomIdx()]),
        )
        for b in mol.GetBonds()
        if not ({b.GetBeginAtomIdx(), b.GetEndAtomIdx()} & dropped)
    }
    assert bonds_of(result.product) == template_bonds | chain_bonds
    c7_alpha = (to_product[7], place[roles["chain"][1]])
    assert tuple(sorted(c7_alpha)) in bonds_of(result.product)


# --- The graft pre-relax guard (requirement 4) ------------------------------------------------


class LoopingOptimizer:
    """A stand-in minimizer that never returns: numpy linear algebra in a Python loop."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> OptimizationResult:
        """Spin forever (no engine call), as the HF-13 stall does."""
        a = np.random.default_rng(0).random((40, 40))
        while True:
            np.linalg.svd(a)
            np.linalg.eigh(a @ a.T)


class QuickOptimizer:
    """A stand-in minimizer that returns the start, with the core exactly where it was."""

    def minimize(self, state: MolecularState, engine: Any, **kwargs: Any) -> OptimizationResult:
        """Return the state unchanged."""
        return OptimizationResult(
            final_state=state,
            final_energy_hartree=-1.0,
            converged=True,
            n_steps=3,
            n_engine_calls=4,
            recovery_steps=[],
            optimizer=OptimizerIdentity(name="geometric", version="stub"),
            options={},
        )


def test_a_looping_pre_relax_becomes_graft_pre_relax_timeout() -> None:
    """Requirement 4: a stub that loops, under a 1 s budget, is a recorded failure, not a hang."""
    fixture = flex()
    product = graft_series(fixture, fixture.get("ethyl")).product
    start = time.perf_counter()
    result = guarded_graft_pre_relax(product, None, LoopingOptimizer(), fixture.core, 200, 1.0)  # type: ignore[arg-type]
    assert result.failed_reason == TIMEOUT_REASON == "graft_pre_relax_timeout"
    assert result.start is None
    assert 1.0 <= time.perf_counter() - start < 6.0


def test_a_finishing_pre_relax_keeps_the_core_and_reports_its_numbers() -> None:
    """No timeout: the relaxed state carries the active core and the optimizer's counts."""
    fixture = flex()
    product = graft_series(fixture, fixture.get("ethyl")).product
    result = guarded_graft_pre_relax(product, None, QuickOptimizer(), fixture.core, 200, 5.0)  # type: ignore[arg-type]
    assert result.failed_reason is None and result.start is not None
    assert list(result.start.active_atom_indices) == list(fixture.core)
    assert (result.n_steps, result.n_engine_calls, result.final_energy_hartree) == (3, 4, -1.0)


# --- Gates (a)-(f) on synthetic runs ----------------------------------------------------------


def metrics(rows: int = 0, calls: int = 0, hits: int = 5) -> dict[str, Any]:
    """Per stage metrics of a pass."""
    one = SimpleNamespace(wall_time_s=1.0, engine_calls=calls, cache_hits=hits, rows_created=rows)
    return {k: one for k in ("constrained_preopt", "ts_opt", "frequency")}


def species_hit() -> Any:
    """A reactant result whose every stage is all hits."""
    stage = SimpleNamespace(rows_created=0, cache_hits=2)
    return SimpleNamespace(
        metrics=SimpleNamespace(
            stages={k: stage for k in ("conformer_search", "geometry_opt", "frequency")}
        ),
        keys={k: [1, 2] for k in ("conformer_search", "geometry_opt", "frequency")},
    )


def member(index: int, source: str = "perturb:1", weight: float = 0.5, face: Any = (1, 1)) -> Any:
    """A member stub."""
    return SimpleNamespace(index=index, source=source, weight=weight, face=list(face))


def synthetic(
    members: list[Any] | None = None,
    excluded: list[str] | None = None,
    pre_reason: str | None = None,
    failed: str | None = None,
    second_rows: int = 0,
    same: bool = True,
) -> Any:
    """A FlexRun stand-in with the attributes ``gates`` reads."""
    members = members if members is not None else [member(0, "seed"), member(1)]

    def ensemble() -> Any:
        return SimpleNamespace(
            members=members,
            excluded=[SimpleNamespace(reason=r) for r in (excluded or [])],
            failed_reason=failed,
        )

    first = SimpleNamespace(ensemble=ensemble(), metrics=metrics())
    second = SimpleNamespace(
        ensemble=first.ensemble
        if same
        else SimpleNamespace(members=members, excluded=[], failed_reason="x"),
        metrics=metrics(rows=second_rows),
    )
    return SimpleNamespace(
        pre=SimpleNamespace(failed_reason=pre_reason),
        runs=(first, second),
        reactants=({"a": species_hit()}, {"a": species_hit()}),
    )


def statuses(run: Any) -> dict[str, str]:
    """The gate statuses of a synthetic run."""
    return {k: v["status"] for k, v in gates(run).items()}


def test_every_gate_passes_on_a_good_run() -> None:
    """Gates (a)-(f) all pass on two members of weight 1/2, equal faces and an all-hit rerun."""
    assert set(statuses(synthetic()).values()) == {"pass"}
    assert len(statuses(synthetic())) == 6


@pytest.mark.parametrize(
    ("run", "gate"),
    [
        (synthetic(members=[member(0, "seed", 1.0)]), "distinct_members_at_least_2"),
        (synthetic(members=[member(0, "seed", 0.5), member(1, weight=0.4)]), "weights_sum_to_one"),
        (
            synthetic(members=[member(0, "seed"), member(1, face=(1, -1))]),
            "faces_equal_the_seeds_no_face_or_engine_error",
        ),
        (synthetic(excluded=["face_mismatch"]), "faces_equal_the_seeds_no_face_or_engine_error"),
        (synthetic(excluded=["engine_error"]), "faces_equal_the_seeds_no_face_or_engine_error"),
        (synthetic(pre_reason="graft_pre_relax_timeout"), "graft_pre_relax_no_timeout"),
        (synthetic(failed="seed:ts_search_failed"), "ensemble_no_failed_reason"),
        (synthetic(second_rows=1), "second_pass_all_hits_equal_ensemble"),
        (synthetic(same=False), "second_pass_all_hits_equal_ensemble"),
    ],
)
def test_each_gate_fails_on_its_own_defect(run: Any, gate: str) -> None:
    """A defect fails the named gate."""
    assert statuses(run)[gate] == "fail"


def test_other_exclusions_do_not_gate() -> None:
    """outside_window, connectivity_changed and a search failure are reported, not gated."""
    run = synthetic(excluded=["outside_window", "connectivity_changed", "ts_search_failed:x"])
    assert set(statuses(run).values()) == {"pass"}


def test_a_missing_ensemble_fails_the_gates() -> None:
    """A graft pre-relax timeout leaves no ensemble; every ensemble gate fails (never a skip)."""
    run = SimpleNamespace(
        pre=SimpleNamespace(failed_reason=TIMEOUT_REASON),
        runs=(None, None),
        reactants=({}, {}),
    )
    got = statuses(run)
    assert got["graft_pre_relax_no_timeout"] == "fail"
    assert all(v == "fail" for v in got.values())


# --- The chain-length order (reported) and the loader -----------------------------------------


def test_non_decreasing_is_reported_over_the_r_groups_seen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The flag follows the counts seen so far; a decrease is reported, never gated."""
    monkeypatch.setenv("ETA_RXNCAT_FLEX_STATE", str(tmp_path))
    first = non_decreasing_report("xtb", "ethyl", 3)
    assert first["complete"] is False and first["non_decreasing"] is True
    non_decreasing_report("xtb", "npropyl", 4)
    last = non_decreasing_report("xtb", "nbutyl", 5)
    assert last["complete"] is True and last["non_decreasing"] is True
    assert last["counts_seen"] == {"ethyl": 3, "npropyl": 4, "nbutyl": 5}
    assert non_decreasing_report("xtb", "nbutyl", 2)["non_decreasing"] is False
    assert non_decreasing_report("uma", "ethyl", 3)["counts_seen"] == {"ethyl": 3}


def test_without_a_state_dir_only_this_r_is_known(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ETA_RXNCAT_FLEX_STATE: nothing is written and the report names only this R."""
    monkeypatch.delenv("ETA_RXNCAT_FLEX_STATE", raising=False)
    report = non_decreasing_report("xtb", "npropyl", 4)
    assert report["counts_seen"] == {"npropyl": 4} and report["complete"] is False


def test_the_loader_refuses_unknown_keys(tmp_path: Path) -> None:
    """A typo in the YAML is an error, not a silent default."""
    text = (DATA / "t4_flexible_alkyl.yaml").read_text(encoding="utf-8")
    bad = tmp_path / "bad.yaml"
    bad.write_text(re.sub(r"^core:", "kore:", text, flags=re.M), encoding="utf-8")
    with pytest.raises(ValueError, match="kore|core"):
        load_flex_fixture(bad)


def test_the_template_is_ts1a_n_with_its_core() -> None:
    """The graft template is TS1a_n (18 atoms) with active core 0-5."""
    state = template_state(flex())
    assert len(state.symbols) == 18 and list(state.active_atom_indices) == [0, 1, 2, 3, 4, 5]
