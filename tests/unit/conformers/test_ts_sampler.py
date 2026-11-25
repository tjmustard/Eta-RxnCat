"""Tests for the TS conformer sampler and the face descriptor (v0.6.0, slice 05; G4, R1, G8)."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from eta_rxncat.conformers._rmsd import min_rmsds
from eta_rxncat.conformers.errors import ConformerInputError
from eta_rxncat.conformers.ts_sampler import (
    FaceDescriptorError,
    TSSample,
    forming_bond_configuration,
    sample_ts_conformers,
)
from eta_rxncat.core import MolecularState, TSEnsembleOptions
from eta_rxncat.mapping import perceive_bonds

XYZ = Path(__file__).resolve().parents[2] / "e2e" / "data" / "e2e5" / "xyz"
FORMING = [(1, 2), (3, 5)]
CORE = [0, 1, 2, 3, 4, 5]
OPTIONS = TSEnsembleOptions()
Array = NDArray[np.float64]


def load(name: str, drop: tuple[int, ...] = ()) -> MolecularState:
    """Read a Tier 4 xyz file (Liu atom order), optionally dropping atoms."""
    lines = (XYZ / f"{name}.xyz").read_text(encoding="utf-8").split("\n")
    count = int(lines[0])
    rows = [line.split() for line in lines[2 : 2 + count]]
    kept = [r for k, r in enumerate(rows) if k not in drop]
    return MolecularState(
        symbols=[r[0] for r in kept],
        coordinates=[[float(x) for x in r[1:4]] for r in kept],
        charge=0,
        spin_multiplicity=1,
    )


def component(bonds: list[tuple[int, int]], start: int) -> set[int]:
    """Return the atoms connected to ``start`` by ``bonds``."""
    seen, stack = {start}, [start]
    while stack:
        atom = stack.pop()
        for i, j in bonds:
            for a, b in ((i, j), (j, i)):
                if a == atom and b not in seen:
                    seen.add(b)
                    stack.append(b)
    return seen


def with_coords(state: MolecularState, coords: Array) -> MolecularState:
    """Return ``state`` with new coordinates."""
    return state.model_copy(update={"coordinates": coords.tolist()})


def crossover(state: MolecularState) -> MolecularState:
    """Reflect the dienophile's non-core atoms through the plane of C2, C3 and the diene normal."""
    xyz = np.asarray(state.coordinates)
    bonds = perceive_bonds(state)
    moving = sorted(component(bonds, 2) - set(CORE))
    normal = np.cross(xyz[1] - xyz[0], xyz[4] - xyz[0])
    normal /= np.linalg.norm(normal)
    plane_normal = np.cross(xyz[3] - xyz[2], normal)
    plane_normal /= np.linalg.norm(plane_normal)
    origin = (xyz[2] + xyz[3]) / 2
    flipped = xyz.copy()
    for atom in moving:
        offset = (xyz[atom] - origin) @ plane_normal
        flipped[atom] = xyz[atom] - 2.0 * offset * plane_normal
    return with_coords(state, flipped)


SEEDS = {"TS1a_n": load("TS1a_n"), "TS1b_n": load("TS1b_n")}


# --- forming_bond_configuration -----------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_endo_is_plus_plus_and_the_crossover_is_minus_minus(name: str) -> None:
    """R1/HF-3: endo (+1, +1) and exo (-1, -1) on Liu's TSs, the exo built by the reflection."""
    seed = SEEDS[name]
    bonds = perceive_bonds(seed)
    assert forming_bond_configuration(seed, FORMING, bonds) == (1, 1)
    assert forming_bond_configuration(crossover(seed), FORMING, bonds) == (-1, -1)


def test_forming_bond_order_is_sorted() -> None:
    """The result follows the sorted forming-bond order, whatever order or direction is passed."""
    seed = SEEDS["TS1a_n"]
    bonds = perceive_bonds(seed)
    assert forming_bond_configuration(seed, [(5, 3), (2, 1)], bonds) == (1, 1)


def test_invariant_under_reflection_and_rigid_motion() -> None:
    """The descriptor is a relative configuration: mirror images and rotations keep it."""
    seed = SEEDS["TS1a_n"]
    bonds = perceive_bonds(seed)
    xyz = np.asarray(seed.coordinates)
    mirror = xyz * np.array([-1.0, 1.0, 1.0])
    angle = 0.7
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0, 0, 1.0]]
    )
    moved = xyz @ rotation.T + np.array([3.0, -2.0, 1.0])
    for coords in (mirror, moved, mirror @ rotation.T):
        assert forming_bond_configuration(with_coords(seed, coords), FORMING, bonds) == (1, 1)
    flipped = crossover(seed)
    mirrored_flip = with_coords(flipped, np.asarray(flipped.coordinates) * np.array([-1.0, 1.0, 1]))
    assert forming_bond_configuration(mirrored_flip, FORMING, bonds) == (-1, -1)


def _planar() -> MolecularState:
    coords = [[0, 0, 0], [3, 0, 0], [0, 1, 0], [-1, -1, 0], [3, 1, 0], [4, -1, 0]]
    return MolecularState(
        symbols=["C"] * 6, coordinates=[[float(x) for x in c] for c in coords],
        charge=0, spin_multiplicity=1,
    )  # fmt: skip


PLANAR_BONDS = [(0, 2), (0, 3), (1, 4), (1, 5)]


def test_zero_volume_is_refused() -> None:
    """A planar end (|V| < 1e-6) cannot be judged."""
    with pytest.raises(FaceDescriptorError, match="volume"):
        forming_bond_configuration(_planar(), [(0, 1)], PLANAR_BONDS)


def test_under_coordinated_end_is_refused() -> None:
    """An end with fewer than two neighbours besides its partner cannot be judged."""
    seed = SEEDS["TS1a_n"]
    bonds = [b for b in perceive_bonds(seed) if 2 not in b or 3 in b]
    with pytest.raises(FaceDescriptorError, match="need 2"):
        forming_bond_configuration(seed, FORMING, bonds)


# --- sample_ts_conformers -----------------------------------------------------------------------


def sample(name: str, options: TSEnsembleOptions = OPTIONS, seed: MolecularState | None = None):
    """Sample around a Tier 4 seed (or ``seed``) with the standard forming bonds and core."""
    state = SEEDS[name] if seed is None else seed
    return state, sample_ts_conformers(state, CORE, FORMING, perceive_bonds(state), options)


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_core_is_exactly_the_seeds_and_the_face_is_kept(name: str) -> None:
    """G4: every sample has the seed's core coordinates exactly and the seed's face."""
    seed, samples = sample(name)
    assert samples
    seed_xyz = np.asarray(seed.coordinates)
    for s in samples:
        assert isinstance(s, TSSample)
        assert np.array_equal(np.asarray(s.state.coordinates)[CORE], seed_xyz[CORE])
        assert s.face == (1, 1)
        assert s.state.symbols == seed.symbols
    assert any(s.source.startswith("fragment_embed:") for s in samples)
    assert any(s.source.startswith("perturb:") for s in samples)


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_exo_seed_stays_exo(name: str) -> None:
    """Sampling around the exo (crossover) seed never produces the endo face."""
    exo = crossover(SEEDS[name])
    _, samples = sample(name, seed=exo)
    assert samples
    assert {s.face for s in samples} == {(-1, -1)}


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_order_and_pre_dedup(name: str) -> None:
    """R11: embeds by index, then perturbations by index; no kept sample is close to another."""
    seed, samples = sample(name)
    kinds = [s.source.split(":")[0] for s in samples]
    assert kinds == sorted(kinds, key=["fragment_embed", "perturb"].index)
    for kind in ("fragment_embed", "perturb"):
        indices = [int(s.source.split(":")[1]) for s in samples if s.source.startswith(kind)]
        assert indices == sorted(indices)
    from eta_rxncat.conformers.ts_sampler import _automorphism_permutations

    bonds = perceive_bonds(seed)
    perms = _automorphism_permutations(seed.symbols, bonds, OPTIONS.max_automorphisms)
    everything = np.arange(len(seed.symbols), dtype=np.intp)
    arrays = [np.asarray(seed.coordinates)] + [np.asarray(s.state.coordinates) for s in samples]
    for k, coords in enumerate(arrays[1:], start=1):
        distances = min_rmsds(coords, arrays[:k], perms, everything)
        assert float(distances.min()) >= OPTIONS.pre_dedup_rmsd_angstrom


@pytest.mark.parametrize("name", sorted(SEEDS))
def test_deterministic_and_seed_dependent(name: str) -> None:
    """G4: equal inputs give byte-equal coordinates; another random_seed changes perturbations."""
    _, first = sample(name)
    _, second = sample(name)
    assert [s.state.coordinates for s in first] == [s.state.coordinates for s in second]
    assert [s.start_sha256 for s in first] == [s.start_sha256 for s in second]
    assert [s.source for s in first] == [s.source for s in second]
    other = TSEnsembleOptions(random_seed=7)
    _, third = sample(name, other)
    a = {s.source: s.state.coordinates for s in first if s.source.startswith("perturb")}
    b = {s.source: s.state.coordinates for s in third if s.source.startswith("perturb")}
    assert a and b and any(a[k] != b[k] for k in a.keys() & b.keys())


def test_digests_identify_geometries() -> None:
    """``start_sha256`` is 64 hex digits and distinct for distinct geometries."""
    _, samples = sample("TS1a_n")
    digests = [s.start_sha256 for s in samples]
    assert all(len(d) == 64 and set(d) <= set("0123456789abcdef") for d in digests)
    assert len(set(digests)) == len(digests)


def test_options_drive_the_count_and_the_dedup() -> None:
    """``n_perturb=0`` leaves only embeddings; a huge dedup radius drops every sample."""
    _, embeds = sample("TS1a_n", TSEnsembleOptions(n_perturb=1))
    only = TSEnsembleOptions(n_perturb=1, n_embed=1)
    _, one = sample("TS1a_n", only)
    assert len(one) <= 2 and len(one) <= len(embeds)
    _, none = sample("TS1a_n", TSEnsembleOptions(pre_dedup_rmsd_angstrom=50.0))
    assert none == []


def test_perturbations_move_only_non_core_atoms() -> None:
    """With a large sigma the non-core atoms move, the core does not."""
    seed, samples = sample("TS1a_n", TSEnsembleOptions(perturb_sigma_angstrom=0.5))
    seed_xyz = np.asarray(seed.coordinates)
    moved = [s for s in samples if s.source.startswith("perturb")]
    assert moved
    for s in moved:
        xyz = np.asarray(s.state.coordinates)
        assert np.array_equal(xyz[CORE], seed_xyz[CORE])
        assert np.abs(xyz[6:] - seed_xyz[6:]).max() > 0.05


def test_spectator_fragment_keeps_the_seeds_geometry() -> None:
    """A fragment with no core atoms is not embedded; embeddings keep it where the seed has it."""
    base = SEEDS["TS1a_n"]
    xyz = np.vstack([np.asarray(base.coordinates), [[10.0, 10.0, 10.0], [10.9, 10.0, 10.0]] ,
                     [[10.0, 10.9, 10.0]]])  # fmt: skip
    seed = MolecularState(
        symbols=[*base.symbols, "O", "H", "H"],
        coordinates=xyz.tolist(),
        charge=0,
        spin_multiplicity=1,
    )
    _, samples = sample("TS1a_n", seed=seed)
    embeds = [s for s in samples if s.source.startswith("fragment_embed")]
    assert embeds
    for s in embeds:
        assert np.array_equal(np.asarray(s.state.coordinates)[18:], xyz[18:])
        assert s.face == (1, 1)


def test_fragment_without_an_anchor_is_refused() -> None:
    """A fragment whose core atoms and heavy neighbours give fewer than three anchors is refused."""
    seed = load("TS1a_n", drop=(7, 16, 17))  # the cyclopropene CH2 and its hydrogens
    with pytest.raises(ConformerInputError, match="no usable anchor"):
        sample_ts_conformers(seed, CORE, FORMING, perceive_bonds(seed), OPTIONS)


def test_bond_order_provenance_is_recorded() -> None:
    """Embeddings record how bond orders were found; perturbations use none."""
    _, samples = sample("TS1a_n")
    for s in samples:
        if s.source.startswith("fragment_embed"):
            assert s.bond_orders in {"determined", "connectivity"}
        else:
            assert s.bond_orders == "none"


# --- G8 -----------------------------------------------------------------------------------------


def test_import_loads_no_engine_or_optimizer_stack() -> None:
    """G8: importing the sampler loads none of torch, pyscf, fairchem, geometric."""
    code = (
        "import sys; import eta_rxncat.conformers.ts_sampler; "
        "heavy = ('torch', 'pyscf', 'fairchem', 'geometric'); "
        "bad = [x for x in heavy if x in sys.modules]; assert not bad, bad"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
