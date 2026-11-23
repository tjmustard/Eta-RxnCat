"""Tests for two-pass ETKDG pools, input checks and stereo-checked seeds (v0.3.0 slice 05).

R16, R21, R24, R28; DV-10, DV-21, DV-22.
"""

import hashlib

import pytest
from conformers_helpers import BUTADIENE, P1A_N, T1, embedded
from pydantic import ValidationError
from rdkit import Chem

from eta_rxncat.conformers import (
    ConformerInputError,
    ConformerOptions,
    EmbeddingFailedError,
    dihedral_deg,
    generate,
    seed_geometries_sha256,
)
from eta_rxncat.core import MolecularState

DEFAULT = ConformerOptions()


def s_cis_side(pool_members: list, origin: str) -> int:  # type: ignore[type-arg]
    """Count members of ``origin`` with |phi(0-1-2-3)| <= 90 degrees."""
    return sum(
        abs(dihedral_deg(m.state, 0, 1, 2, 3)) <= 90.0 for m in pool_members if m.origin == origin
    )


# options


def test_option_defaults_and_stage_options() -> None:
    """Defaults per mission §5; as_stage_options is sorted and complete."""
    stage = DEFAULT.as_stage_options()
    assert stage == {
        "energy_window_kcal_mol": 6.0,
        "include_h_in_rmsd": True,
        "max_automorphisms": 100000,
        "n_embed": 50,
        "pre_dedup_rmsd_angstrom": 0.125,
        "rmsd_dedup_angstrom": 0.125,
        "seed": 42,
        "torsion_free_pass": True,
    }
    assert list(stage) == sorted(stage)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_embed": 0},
        {"seed": True},
        {"torsion_free_pass": 1},
        {"rmsd_dedup_angstrom": 0.0},
        {"x": 1},
    ],
)
def test_options_rejected(kwargs: dict[str, object]) -> None:
    """Non-positive counts, non-strict types and unknown keys are rejected; the model is frozen."""
    with pytest.raises(ValidationError):
        ConformerOptions(**kwargs)  # type: ignore[arg-type]


def test_options_frozen() -> None:
    """ConformerOptions is immutable."""
    with pytest.raises(ValidationError):
        DEFAULT.seed = 1  # type: ignore[misc]


# input checks


@pytest.mark.parametrize(
    ("smiles", "charge", "mult", "fragment"),
    [
        ("CC", 1, 1, "formal charge 0, not 1"),
        ("[2H]C", 0, 1, "isotope"),
        ("C(", 0, 1, "does not parse"),
        ("CC", 0, 2, "impossible"),
    ],
)
def test_bad_inputs(smiles: str, charge: int, mult: int, fragment: str) -> None:
    """Charge mismatch, isotopes, unparsable SMILES and bad parity raise ConformerInputError."""
    with pytest.raises(ConformerInputError, match=fragment):
        generate(smiles, charge=charge, spin_multiplicity=mult, options=DEFAULT)


# F21: the s-cis-side class needs the torsion-free pass


@pytest.mark.parametrize(("smiles", "n", "pass2"), [(T1, 40, 24), (BUTADIENE, 50, 26)])
def test_torsion_free_pass_samples_s_cis_side(smiles: str, n: int, pass2: int) -> None:
    """Seed 42: pass 1 has 0 s-cis-side members, pass 2 the measured count (R21)."""
    pool = generate(smiles, charge=0, spin_multiplicity=1, options=ConformerOptions(n_embed=n))
    assert s_cis_side(list(pool.members), "etkdg") == 0
    assert s_cis_side(list(pool.members), "etkdg_free") == pass2
    ids = sorted(m.source_id for m in pool.members)
    assert ids == list(range(2 * n))


@pytest.mark.parametrize("smiles", [T1, BUTADIENE])
def test_without_torsion_free_pass_no_s_cis_side(smiles: str) -> None:
    """With torsion_free_pass=False the pool has no s-cis-side member (documents F21)."""
    pool = generate(
        smiles,
        charge=0,
        spin_multiplicity=1,
        options=ConformerOptions(torsion_free_pass=False),
    )
    assert all(m.origin == "etkdg" for m in pool.members)
    assert sum(abs(dihedral_deg(m.state, 0, 1, 2, 3)) <= 90.0 for m in pool.members) == 0
    assert "pass2" not in pool.failure_counts


@pytest.mark.parametrize("smiles", ["CCCC", T1, BUTADIENE])
def test_generation_is_deterministic(smiles: str) -> None:
    """H4: two calls give bit-identical coordinates for both passes."""
    a = generate(smiles, charge=0, spin_multiplicity=1, options=DEFAULT)
    b = generate(smiles, charge=0, spin_multiplicity=1, options=DEFAULT)
    assert [m.state.coordinates for m in a.members] == [m.state.coordinates for m in b.members]
    assert a.pre_dedup_survivors == b.pre_dedup_survivors


def test_members_in_smiles_atom_order() -> None:
    """Every member's symbols are the AddHs order of the SMILES."""
    pool = generate(T1, charge=0, spin_multiplicity=1, options=ConformerOptions(n_embed=5))
    order = [a.GetSymbol() for a in Chem.AddHs(Chem.MolFromSmiles(T1)).GetAtoms()]
    assert all(m.state.symbols == order for m in pool.members)
    assert set(pool.failure_counts) == {"pass1", "pass2"}


def test_embedding_failure_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zero embeddings in both passes raise EmbeddingFailedError with each pass's counts."""
    import sys

    gen = sys.modules[
        "eta_rxncat.conformers.generate"
    ]  # the package exports a function of that name
    monkeypatch.setattr(gen, "_embed", lambda mol_h, options, free: ([], (3, 1, 4)))
    with pytest.raises(EmbeddingFailedError) as info:
        generate("CCCC", charge=0, spin_multiplicity=1, options=DEFAULT)
    assert info.value.counts == {"pass1": (3, 1, 4), "pass2": (3, 1, 4)}


# pre-dedup


def test_pre_dedup_keeps_distinct_and_drops_duplicates() -> None:
    """Butane: survivors are a strict, ordered subset; no two survivors coincide."""
    pool = generate("CCCC", charge=0, spin_multiplicity=1, options=DEFAULT)
    survivors = pool.pre_dedup_survivors
    assert 0 < len(survivors) < len(pool.members)
    assert list(survivors) == sorted(survivors)


# seeds (R24, R28)


def seed_state(smiles: str, shuffle: bool = True) -> MolecularState:
    """An RDKit embedding of ``smiles`` with its atoms reversed (a foreign atom order)."""
    st = embedded(smiles)
    if not shuffle:
        return st
    return MolecularState(
        symbols=list(reversed(st.symbols)),
        coordinates=list(reversed(st.coordinates)),
        charge=0,
        spin_multiplicity=1,
    )


def test_seed_is_reordered_and_always_survives() -> None:
    """A valid seed in another atom order is reordered into SMILES order and survives pre-dedup."""
    seed = seed_state(T1)
    pool = generate(
        T1,
        charge=0,
        spin_multiplicity=1,
        options=ConformerOptions(n_embed=10),
        seed_geometries=[seed],
    )
    seeds = [m for m in pool.members if m.origin == "seed"]
    assert [m.source_id for m in seeds] == [20]
    assert pool.members[0].origin == "seed"
    assert 20 in pool.pre_dedup_survivors
    assert pool.pre_dedup_survivors[0] == 20
    order = [a.GetSymbol() for a in Chem.AddHs(Chem.MolFromSmiles(T1)).GetAtoms()]
    assert seeds[0].state.symbols == order
    assert sorted(map(tuple, seeds[0].state.coordinates)) == sorted(map(tuple, seed.coordinates))


def test_seed_survives_even_when_duplicating_an_embedding() -> None:
    """A seed equal to pass-1 embedding 0 is kept, and the embedding is the one dropped."""
    pool0 = generate(T1, charge=0, spin_multiplicity=1, options=ConformerOptions(n_embed=3))
    duplicate = pool0.member(0).state
    pool = generate(
        T1,
        charge=0,
        spin_multiplicity=1,
        options=ConformerOptions(n_embed=3),
        seed_geometries=[duplicate],
    )
    assert 6 in pool.pre_dedup_survivors
    assert 0 not in pool.pre_dedup_survivors


def test_seed_hash_text() -> None:
    """R28 hash: n, blank line, then one "sym x y z" row per atom (%.6f); sorted digests by ","."""
    a = embedded("O")
    b = embedded("O", seed=7)
    text = "3\n\n" + "".join(
        f"{s} {x:.6f} {y:.6f} {z:.6f}\n" for s, (x, y, z) in zip(a.symbols, a.coordinates)
    )
    digest = hashlib.sha256(text.encode()).hexdigest()
    assert seed_geometries_sha256([a]) == digest
    both = seed_geometries_sha256([a, b])
    assert both == ",".join(sorted(both.split(",")))
    assert seed_geometries_sha256([b, a]) == both
    assert seed_geometries_sha256([]) == ""
    pool = generate("O", charge=0, spin_multiplicity=1, options=DEFAULT, seed_geometries=[a])
    assert pool.seed_geometries_sha256 == digest


def test_z_seed_for_e_smiles_rejected() -> None:
    """F24: a Z-diene seed for the E SMILES of T1 is refused."""
    with pytest.raises(ConformerInputError, match="seed 0"):
        generate(
            T1,
            charge=0,
            spin_multiplicity=1,
            options=DEFAULT,
            seed_geometries=[seed_state("C=C(/C=C\\OC)OC")],
        )


def test_exo_seed_for_endo_smiles_rejected() -> None:
    """F24: an exo seed for the endo P1a_n SMILES is refused."""
    exo = "C1=C[C@H]2C[C@@H]1[C@@H]1C[C@@H]12"
    assert Chem.MolToSmiles(Chem.MolFromSmiles(exo)) != Chem.MolToSmiles(Chem.MolFromSmiles(P1A_N))
    generate(
        P1A_N,
        charge=0,
        spin_multiplicity=1,
        options=ConformerOptions(n_embed=2),
        seed_geometries=[seed_state(P1A_N)],
    )
    with pytest.raises(ConformerInputError, match="seed 0"):
        generate(
            P1A_N,
            charge=0,
            spin_multiplicity=1,
            options=ConformerOptions(n_embed=2),
            seed_geometries=[seed_state(exo)],
        )


@pytest.mark.parametrize(
    ("seed", "fragment"),
    [
        (
            MolecularState(
                symbols=["O", "H", "H"],
                coordinates=[[0, 0, 0], [0.96, 0, 0], [-0.24, 0.93, 0]],
                charge=0,
                spin_multiplicity=3,
            ),
            "multiplicity",
        ),
        (
            MolecularState(
                symbols=["O", "H", "H"],
                coordinates=[[0, 0, 0], [3.0, 0, 0], [-3.0, 0.0, 0]],
                charge=0,
                spin_multiplicity=1,
            ),
            "seed 0",
        ),
    ],
)
def test_bad_seed_rejected(seed: MolecularState, fragment: str) -> None:
    """A seed with another multiplicity or connectivity is refused, never dropped."""
    with pytest.raises(ConformerInputError, match=fragment):
        generate("O", charge=0, spin_multiplicity=1, options=DEFAULT, seed_geometries=[seed])


def test_wrong_element_seed_rejected() -> None:
    """A seed of another molecule is refused."""
    with pytest.raises(ConformerInputError, match="elements"):
        generate(
            "O", charge=0, spin_multiplicity=1, options=DEFAULT, seed_geometries=[embedded("N")]
        )


def test_caller_seed_not_modified() -> None:
    """The caller's seed state is unchanged."""
    seed = seed_state(T1)
    before = seed.model_dump()
    generate(
        T1,
        charge=0,
        spin_multiplicity=1,
        options=ConformerOptions(n_embed=2),
        seed_geometries=[seed],
    )
    assert seed.model_dump() == before
