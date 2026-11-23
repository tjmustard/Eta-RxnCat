"""Tests for ReactionSpec, reaction free energies and the JSON report writer (v0.3.0 slice 06)."""

import json
import math
from pathlib import Path

import pytest
from orchestrator_helpers import uff_recipe, water
from pydantic import ValidationError

from eta_rxncat.core import ThermoConfig
from eta_rxncat.orchestrator import (
    ReactionSpec,
    ensemble_to_payload,
    reaction_free_energy,
    report_text,
    run_species,
    standard_state_shift_kcal_mol,
    write_report,
)
from eta_rxncat.store import ArtifactStore

HF2 = ReactionSpec(
    reactants=(("butadiene", 1), ("ethylene", 1)),
    products=(("cyclohexene", 1),),
    smiles={"butadiene": "C=CC=C", "ethylene": "C=C", "cyclohexene": "C1=CCCCC1"},
)


def test_reaction_conserves_and_counts_moles() -> None:
    """A balanced Diels-Alder is accepted; delta_n = -1."""
    assert HF2.delta_n == -1


@pytest.mark.parametrize(
    ("reactants", "products", "smiles", "fragment"),
    [
        ((("a", 1),), (("b", 1),), {"a": "C=C", "b": "CC"}, "atoms not conserved"),
        ((("a", 2),), (("b", 1),), {"a": "[NH4+]", "b": "N"}, "not conserved"),
        ((("a", 1),), (("b", 1),), {"a": "[NH4+]", "b": "[NH3+]"}, "not conserved"),
        ((("a", 1),), (("b", 1),), {"a": "C"}, "no SMILES"),
        ((("a", 0),), (("b", 1),), {"a": "C", "b": "C"}, "greater than or equal to 1"),
    ],
)
def test_reaction_rejects(
    reactants: tuple[tuple[str, int], ...],
    products: tuple[tuple[str, int], ...],
    smiles: dict[str, str],
    fragment: str,
) -> None:
    """Non-conserving atoms or charge, a missing SMILES or a zero coefficient are rejected."""
    with pytest.raises(ValidationError, match=fragment):
        ReactionSpec(reactants=reactants, products=products, smiles=smiles)


def test_charge_conservation_rejected() -> None:
    """Same atoms, different charge -> rejected (charge from the SMILES' formal charge)."""
    with pytest.raises(ValidationError, match="charge not conserved"):
        ReactionSpec(
            reactants=(("a", 1),), products=(("b", 1),), smiles={"a": "[OH-]", "b": "[OH]"}
        )


def test_standard_state_shift() -> None:
    """RT ln(c RT/p) = 1.8943 kcal/mol at 298.15 K, 1 M, 1 atm."""
    assert standard_state_shift_kcal_mol(ThermoConfig()) == pytest.approx(1.8943, abs=1e-4)


def test_reaction_free_energy_delta_n(tmp_path: Path) -> None:
    """Delta_n = -1: dG(1 M) - dG(1 atm) = -1.8943 kcal/mol +- 1e-4 (water dimerisation toy)."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        ens = run_species(water(), uff_recipe(), store).ensemble
    dimer = ReactionSpec(
        reactants=(("w", 2),), products=(("w2", 1),), smiles={"w": "O", "w2": "O.O"}
    )
    w2 = ens.model_copy(update={"species_id": "w2"})
    energies = reaction_free_energy(dimer, {"w": ens, "w2": w2}, ThermoConfig())
    assert energies.delta_n == -1
    assert energies.dG_1M_kcal_mol - energies.dG_1atm_kcal_mol == pytest.approx(-1.8943, abs=1e-4)
    g = ens.ensemble_gibbs_hartree * 627.5094740631
    assert energies.dG_1M_kcal_mol == pytest.approx(g - 2 * g, rel=1e-12)


def test_reaction_temperature_mismatch(tmp_path: Path) -> None:
    """An ensemble at another temperature is refused."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        ens = run_species(water(), uff_recipe(), store).ensemble
    spec = ReactionSpec(reactants=(("w", 1),), products=(("x", 1),), smiles={"w": "O", "x": "O"})
    with pytest.raises(ValueError, match="K"):
        reaction_free_energy(spec, {"w": ens, "x": ens}, ThermoConfig(temperature_k=310.0))


# report


def test_report_round_trips_and_is_byte_identical(tmp_path: Path) -> None:
    """Floats re-parse exactly; two writes are byte-identical; sorted keys, LF, trailing newline."""
    payload = {"b": [0.1 + 0.2, 1e-300, -2.5e17, 1 / 3], "a": {"z": math.pi, "y": 7}}
    first, second = tmp_path / "one.json", tmp_path / "two.json"
    write_report(first, payload)
    write_report(second, payload)
    raw = first.read_bytes()
    assert raw == second.read_bytes()
    assert raw.endswith(b"\n") and b"\r" not in raw
    parsed = json.loads(raw)
    assert parsed["schema"] == 1
    assert parsed["b"] == payload["b"] and parsed["a"] == payload["a"]
    assert list(parsed) == sorted(parsed)


def test_report_rejects_nan_and_foreign_schema() -> None:
    """NaN anywhere, or another schema number, is refused."""
    with pytest.raises(ValueError, match="non-finite"):
        report_text({"x": [1.0, float("nan")]})
    with pytest.raises(ValueError, match="schema"):
        report_text({"schema": 2})


def test_ensemble_payload(tmp_path: Path) -> None:
    """Per record: E, G, ZPE, S components, sigma, g, weight, lowest 6 frequencies, xyz."""
    with ArtifactStore(tmp_path / "s.sqlite") as store:
        ens = run_species(water(), uff_recipe(), store).ensemble
    payload = ensemble_to_payload(ens)
    record = payload["records"][0]
    assert record["rotational_symmetry_number"] == 2 and record["degeneracy"] == 1
    assert len(record["lowest_frequencies_cm1"]) == 3
    assert set(record["entropy_components_hartree_per_k"]) == {
        "translational",
        "rotational",
        "vibrational",
        "electronic",
    }
    assert record["boltzmann_weight"] == 1.0
    assert len(record["xyz_angstrom"]) == 3
    text = report_text(payload)
    assert json.loads(text)["records"][0]["gibbs_free_energy_hartree"] == (
        ens.records[0].thermo.gibbs_free_energy_hartree
    )
