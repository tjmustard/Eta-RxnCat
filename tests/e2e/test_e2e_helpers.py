"""Default-suite tests for the E2E loaders, derived quantities, regression and writer (slice 07).

No engine runs here: records are synthetic (RDKit geometries, hand-made thermochemistry).
"""

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import pytest
import reference_values as rv
from derived import (
    accuracy,
    butane_class,
    checked_reaction_free_energy,
    diene_class,
    failure_report,
    failure_rows,
    hf1_derived,
    hf2_derived,
    solvated_ensemble,
)
from fixtures import DATA, hf1, hf2, load_fixture
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolTransforms
from regression import compare

from eta_rxncat.conformers import build_ensemble
from eta_rxncat.core import (
    ConformerEnsemble,
    ConformerRecord,
    MolecularState,
    OptimizationResult,
    OptimizerIdentity,
    StageConfig,
    ThermoAnalysisOptions,
    ThermoConfig,
    ThermoResult,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.orchestrator import ReactionSpec, ensemble_to_payload, write_report
from eta_rxncat.store import ArtifactStatus, ArtifactStore, build_stage_key

RT = 6.02214076e23 * 1.380649e-23 / 4184.0 * 298.15  # kcal/mol
TJ_RESULTS = rv.TJ_SOURCE / "results.json"

# synthetic records -------------------------------------------------------------------------


def state(smiles: str, dihedral: float | None = None) -> MolecularState:
    """An RDKit geometry of ``smiles`` (AddHs order), optionally with phi(0-1-2-3) set."""
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    assert AllChem.EmbedMolecule(mol, randomSeed=7) == 0
    if dihedral is not None:
        rdMolTransforms.SetDihedralDeg(mol.GetConformer(), 0, 1, 2, 3, dihedral)
    return MolecularState(
        symbols=[a.GetSymbol() for a in mol.GetAtoms()],
        coordinates=mol.GetConformer().GetPositions().tolist(),
        charge=0,
        spin_multiplicity=1,
    )


def record(
    st: MolecularState,
    g_hartree: float,
    *,
    degeneracy: int = 1,
    sigma: int = 2,
    config: ThermoConfig | None = None,
) -> ConformerRecord:
    """A record with energy g - 0.1, G = g, and placeholder but valid thermochemistry."""
    n = len(st.symbols)
    e = g_hartree - 0.1
    comps = {"translational": 5e-5, "rotational": 3e-5, "vibrational": 2e-5, "electronic": 0.0}
    thermo = ThermoResult(
        n_atoms=n,
        electronic_energy_hartree=e,
        energy_source="optimization",
        zpe_hartree=0.05,
        thermal_correction_enthalpy_hartree=0.11,
        thermal_correction_gibbs_hartree=0.1,
        entropy_hartree_per_k=math.fsum(comps.values()),
        entropy_components_hartree_per_k=comps,
        gibbs_free_energy_hartree=g_hartree,
        standard_state_correction_hartree=0.003,
        frequencies_cm1=[100.0 + 10.0 * i for i in range(3 * n - 6)],
        imaginary_frequencies_cm1=[],
        soft_modes_cm1=[],
        rotational_symmetry_number=sigma,
        is_linear=False,
        config=config or ThermoConfig(),
        analysis=ThermoAnalysisOptions(),
        masses_source="synthetic",
    )
    opt = OptimizationResult(
        final_state=st,
        final_energy_hartree=e,
        converged=True,
        n_steps=1,
        n_engine_calls=1,
        recovery_steps=["tric"],
        optimizer=OptimizerIdentity(name="geometric", version="1.1.1"),
        options={},
    )
    return ConformerRecord(
        state=st, optimization=opt, thermo=thermo, degeneracy=degeneracy, source_ids=[0]
    )  # type: ignore[arg-type]


def ensemble(species_id: str, smiles: str, records: list[ConformerRecord]) -> ConformerEnsemble:
    """build_ensemble at 298.15 K."""
    return build_ensemble(species_id, smiles, records, 298.15)


def hf2_ensembles(
    config: ThermoConfig | None = None, cyclo_g: int = 2
) -> dict[str, ConformerEnsemble]:
    """Synthetic HF2 ensembles: s-trans butadiene, ethylene, cyclohexene with degeneracy cyclo_g."""
    return {
        "butadiene": ensemble(
            "butadiene", "C=CC=C", [record(state("C=CC=C", 180.0), -156.0, config=config)]
        ),
        "ethylene": ensemble(
            "ethylene", "C=C", [record(state("C=C"), -78.5, sigma=4, config=config)]
        ),
        "cyclohexene": ensemble(
            "cyclohexene",
            "C1CC=CCC1",
            [record(state("C1CC=CCC1"), -234.55, degeneracy=cyclo_g, config=config)],
        ),
    }


# fixtures --------------------------------------------------------------------------------------


def test_fixture_inputs_load() -> None:
    """HF1 is CCCC (n_embed 50, seed 42); HF2 is butadiene + ethylene -> cyclohexene."""
    one = hf1()
    assert [s.smiles for s in one.species] == ["CCCC"] and one.reaction is None
    assert one.species[0].conformer_options.n_embed == 50
    assert one.species[0].conformer_options.seed == 42
    two = hf2()
    assert [s.species_id for s in two.species] == ["butadiene", "ethylene", "cyclohexene"]
    assert two.reaction is not None and two.reaction.delta_n == -1


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("schema: 2\nfixture: x\nspecies: []\n", "schema"),
        ("schema: 1\nfixture: x\nspecies: []\nextra: 1\n", "unknown keys"),
        (
            "schema: 1\nfixture: x\nspecies:\n  - {species_id: a, smiles: C, charge: 0, "
            "spin_multiplicity: 1}\nreaction: {reactants: [[a, 1]], products: [[a, 2]]}\n",
            "not conserved",
        ),
    ],
)
def test_fixture_loader_rejects(tmp_path: Path, text: str, fragment: str) -> None:
    """Wrong schema, unknown keys and non-conserving reactions are refused."""
    path = tmp_path / "f.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=fragment):
        load_fixture(path)


# reference values ------------------------------------------------------------------------------


def example() -> dict[str, Any]:
    """The committed example file."""
    return json.loads((DATA / "reference_values.example.json").read_text(encoding="utf-8"))


def test_example_loads_but_never_as_fixture() -> None:
    """One entry per level per quantity; fixtures mode refuses EXAMPLE provenance."""
    data = rv.load_reference_values(example(), fixtures_mode=False)
    assert len(data["entries"]) == 14
    with pytest.raises(rv.ReferenceError, match="EXAMPLE"):
        rv.load_reference_values(example(), fixtures_mode=True)


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda d: d["entries"][7].update(gate=True), "only at"),
        (lambda d: d["entries"].append(dict(d["entries"][0])), "second entry"),
        (lambda d: d["entries"][0].update(quantity="hf3.x"), "unknown quantity"),
        (lambda d: d["entries"][0].update(standard_state="2 M"), "standard_state"),
        (lambda d: d["entries"][0].update(value=float("nan")), "finite"),
        (lambda d: d["entries"][0].pop("gate"), "keys"),
        (lambda d: d["reference_species"]["ethylene"].update(sigma=0), "sigma"),
    ],
)
def test_reference_loader_rejects(mutate: Any, fragment: str) -> None:
    """B3LYP gates, duplicates, unknown names, non-finite values and bad sigma are refused."""
    data = example()
    mutate(data)
    with pytest.raises(rv.ReferenceError, match=fragment):
        rv.load_reference_values(data, fixtures_mode=False)


def test_value_at_1m() -> None:
    """hf2.dG_r: 1 atm -> 1 M adds -RT ln(24.4654); 1 bar adds -RT ln 1.01325; others unchanged."""
    base = {"quantity": "hf2.dG_r", "value": -29.0, "temperature_k": 298.15}
    at_1m = rv.value_at_1m({**base, "standard_state": "1 M"})
    at_atm = rv.value_at_1m({**base, "standard_state": "1 atm"})
    at_bar = rv.value_at_1m({**base, "standard_state": "1 bar"})
    assert at_1m == -29.0
    assert at_atm - at_1m == pytest.approx(-1.8943, abs=1e-4)
    assert at_bar - at_atm == pytest.approx(-RT * math.log(1.01325), rel=1e-9)
    hf1_entry = {"quantity": "hf1.dG_gauche_anti", "value": 0.7, "temperature_k": 298.15}
    assert rv.value_at_1m({**hf1_entry, "standard_state": "1 atm"}) == 0.7


# R46: TJ's reference as a candidate ------------------------------------------------------------


def test_tj_results_committed_byte_identical() -> None:
    """The committed results.json has R46's sha256."""
    assert hashlib.sha256(TJ_RESULTS.read_bytes()).hexdigest() == rv.TJ_RESULTS_SHA256


def test_tj_transcription() -> None:
    """Passes the fixtures-mode loader; every value is its key's float exactly; rounded figures."""
    values = rv.load_reference_values(rv.transcribe_tj_results(TJ_RESULTS), fixtures_mode=True)
    raw = json.loads(TJ_RESULTS.read_text(encoding="utf-8"))
    entries = {(e["quantity"], e["level"]): e for e in values["entries"]}
    assert len(entries) == 14
    for (quantity, level), e in entries.items():
        key = e["provenance"].split("; key ", 1)[1]
        block = next(
            b for b in ("GATING REFERENCE", "B3LYP/6-31G** (RRHO)") if key.startswith(b + "/")
        )
        path = key[len(block) + 1 :]
        node: Any = raw[block]
        for part in path.split("/"):
            node = node[part]
        assert e["value"] == node and type(e["value"]) is float, (quantity, level)
        assert rv.TJ_RESULTS_SHA256 in e["provenance"]
        assert e["temperature_k"] == 298.15
    gating = {k for k, e in entries.items() if e["gate"]}
    assert gating == {("hf1.dG_gauche_anti", rv.GATING_LEVEL), ("hf2.dG_r", rv.GATING_LEVEL)}

    def r(q: str, level: str, nd: int = 3) -> float:
        return round(entries[(q, level)]["value"], nd)

    w, b = rv.GATING_LEVEL, "b3lyp_631gss"
    assert r("hf1.dE_gauche_anti", w) == 0.609
    assert r("hf1.dH_gauche_anti", w) == 0.658
    assert r("hf1.dG_gauche_anti", w) == 0.685
    assert r("hf1.gauche_population", w, 1) == 38.6
    assert r("hf2.dE_r", w) == -47.055
    assert r("hf2.dH_r", w) == -42.712
    assert r("hf2.dG_r", w) == -30.922
    assert r("hf1.dH_gauche_anti", b) == 0.870
    assert r("hf1.dG_gauche_anti", b) == 0.897
    assert r("hf2.dH_r", b) == -38.311
    assert r("hf2.dG_r", b) == -26.522
    assert entries[("hf2.dG_r", w)]["standard_state"] == "1 M"
    assert entries[("hf1.gauche_population", w)]["unit"] == "percent"
    assert {k: v["sigma"] for k, v in values["reference_species"].items()} == {
        "butane_anti": 2,
        "butane_gauche": 2,
        "butadiene_strans": 2,
        "ethylene": 4,
        "cyclohexene": 2,
    }


def test_transcription_entry_point(tmp_path: Path) -> None:
    """The entry point writes the transcription (into tmp_path here, never the candidate dir)."""
    out = tmp_path / "reference_values.json"
    assert rv.main(["transcribe", str(TJ_RESULTS), str(out)]) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == rv.transcribe_tj_results(TJ_RESULTS)
    assert rv.main(["nope"]) == 2


# derived quantities ---------------------------------------------------------------------------


def test_hf1_derived_per_conformer_and_class() -> None:
    """Per-conformer dG has no RT ln 2; class dG = per-conformer dG - RT ln 2 (g = 2 gauche)."""
    anti = record(state("CCCC", 180.0), -158.30)
    gauche = record(state("CCCC", 65.0), -158.30 + 0.7 / HARTREE_KCAL_MOL, degeneracy=2)
    assert butane_class(anti) == "anti" and butane_class(gauche) == "gauche"
    d = hf1_derived(ensemble("n_butane", "CCCC", [anti, gauche]))
    assert d["dG_gauche_anti_kcal_mol"] == pytest.approx(0.7, abs=1e-9)
    assert d["class_dG_gauche_anti_kcal_mol"] == pytest.approx(0.7 - RT * math.log(2), abs=1e-9)
    p = 2 * math.exp(-0.7 / RT) / (1 + 2 * math.exp(-0.7 / RT))
    assert d["gauche_population_percent"] == pytest.approx(100 * p, abs=1e-9)


def test_hf2_ensemble_vs_lowest_records_differ_by_rt_ln2() -> None:
    """Synthetic cyclohexene, g = 2: ensemble and per-conformer dG_r differ by exactly -RT ln 2."""
    ens = hf2_ensembles()
    spec = hf2().reaction
    assert spec is not None
    d = hf2_derived(spec, ens, ThermoConfig())
    assert d["dG_r_ensemble_minus_lowest_kcal_mol"] == pytest.approx(-RT * math.log(2), abs=1e-9)
    expected = (-234.55 + 156.0 + 78.5) * HARTREE_KCAL_MOL
    assert d["dG_r_lowest_records_kcal_mol"] == pytest.approx(expected, abs=1e-9)
    assert diene_class(ens["butadiene"].records[0]) == "s-trans"


@pytest.mark.parametrize(
    "other", [ThermoConfig(standard_state_mol_l=2.0), ThermoConfig(pressure_atm=2.0)]
)
def test_checked_reaction_free_energy_refuses_mixed_config(other: ThermoConfig) -> None:
    """R51: a species run at another standard state or pressure is refused, by name."""
    ens = hf2_ensembles()
    ens["ethylene"] = ensemble(
        "ethylene", "C=C", [record(state("C=C"), -78.5, sigma=4, config=other)]
    )
    spec = hf2().reaction
    assert spec is not None
    with pytest.raises(ValueError, match="ethylene"):
        checked_reaction_free_energy(spec, ens, ThermoConfig())
    checked_reaction_free_energy(spec, hf2_ensembles(), ThermoConfig())


def test_solvated_ensemble_shifts_g_by_delta_e() -> None:
    """R27: G_solv = G_gas + (E_sp - E_gas) per record; same degeneracies."""
    ens = hf2_ensembles()["cyclohexene"]
    rec = ens.records[0]
    shifted = solvated_ensemble(ens, {0: rec.thermo.electronic_energy_hartree - 0.002})
    assert shifted.records[0].thermo.gibbs_free_energy_hartree == pytest.approx(
        rec.thermo.gibbs_free_energy_hartree - 0.002, abs=1e-12
    )
    assert shifted.records[0].degeneracy == 2
    assert shifted.ensemble_gibbs_hartree - ens.ensemble_gibbs_hartree == pytest.approx(
        -0.002, abs=1e-12
    )


# accuracy ------------------------------------------------------------------------------------


def reference_for_tests() -> dict[str, Any]:
    """TJ's transcription, validated."""
    return rv.load_reference_values(rv.transcribe_tj_results(TJ_RESULTS), fixtures_mode=True)


def test_accuracy_pending_without_reference() -> None:
    """No promoted reference -> pending_reference."""
    assert (
        accuracy({"hf1.dG_gauche_anti": 0.7}, {}, None, recipe="uma")["status"]
        == "pending_reference"
    )


def test_accuracy_gates_uma_only() -> None:
    """UMA within 0.5 passes, beyond fails; xtb is reported, never gated; both levels listed."""
    ref = reference_for_tests()
    sig = {"butane_anti": 2, "butane_gauche": 2}
    ok = accuracy({"hf1.dG_gauche_anti": 0.685 + 0.4}, sig, ref, recipe="uma")
    bad = accuracy({"hf1.dG_gauche_anti": 0.685 + 0.6}, sig, ref, recipe="uma")
    xtb = accuracy({"hf1.dG_gauche_anti": 5.0}, sig, ref, recipe="xtb")
    assert ok["status"] == "pass" and bad["status"] == "fail" and xtb["status"] == "reported"
    assert {d["level"] for d in xtb["deltas"]} == {rv.GATING_LEVEL, "b3lyp_631gss"}
    assert not any(d["gated"] for d in xtb["deltas"])


def test_accuracy_population_and_sigma_mismatch() -> None:
    """Population is always reported; a sigma mismatch fails UMA and is flagged for xtb."""
    ref = reference_for_tests()
    pop = accuracy({"hf1.gauche_population": 99.0}, {}, ref, recipe="uma")
    assert pop["status"] == "reported"
    wrong = {"butane_anti": 1, "butane_gauche": 2}
    uma = accuracy({"hf1.dG_gauche_anti": 0.685}, wrong, ref, recipe="uma")
    xtb = accuracy({"hf1.dG_gauche_anti": 0.685}, wrong, ref, recipe="xtb")
    assert uma["status"] == "fail" and uma["sigma_mismatch"] == ["butane_anti"]
    assert xtb["status"] == "reported" and xtb["sigma_mismatch"] == ["butane_anti"]


def test_hf2_accuracy_uses_1m_value() -> None:
    """The gated HF2 entry compares at 1 M (-30.922) with a 2.0 kcal/mol bound."""
    ref = reference_for_tests()
    sig = {"butadiene_strans": 2, "ethylene": 4, "cyclohexene": 2}
    assert accuracy({"hf2.dG_r": -30.922 + 1.9}, sig, ref, recipe="uma")["status"] == "pass"
    assert accuracy({"hf2.dG_r": -30.922 - 2.1}, sig, ref, recipe="uma")["status"] == "fail"


# R50 failure rows ------------------------------------------------------------------------------


def test_failure_rows_counted_before_use(tmp_path: Path) -> None:
    """A completed row carrying failed_reason is counted as a failure, by stage and reason."""
    path = tmp_path / "s.sqlite"
    st = state("O")
    stage = StageConfig(kind="geometry_opt", engine="rdkit_ff", method="uff")
    from eta_rxncat.core import EngineIdentity

    identity = EngineIdentity(name="rdkit_ff", version="x")
    bad = build_stage_key(st, stage, identity)
    good = build_stage_key(
        state("O").model_copy(update={"coordinates": [[0, 0, 0], [0, 0, 1], [0, 1, 0]]}),
        stage,
        identity,
    )
    with ArtifactStore(path) as store:
        store.put(
            bad, ArtifactStatus.COMPLETED, {"failed_reason": "optimization_failed", "message": "m"}
        )
        store.put(good, ArtifactStatus.COMPLETED, {"final_energy_hartree": -1.0})
    counts = failure_rows(path, {"geometry_opt": [bad.key, good.key, bad.key]})
    assert dict(counts) == {("geometry_opt", "optimization_failed"): 1}
    assert failure_report("water", counts) == [
        {"species": "water", "stage": "geometry_opt", "reason": "optimization_failed", "count": 1}
    ]
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM stage_artifacts").fetchone()[0] == 2


# regression -----------------------------------------------------------------------------------


def payload(
    device: str = "cpu", shift: float = 0.0, weight: float = 1.0, cls: str = "anti"
) -> dict[str, Any]:
    """A synthetic candidate payload with one butane record."""
    ens = ensemble("n_butane", "CCCC", [record(state("CCCC", 180.0), -158.3 + shift)])
    sp = ensemble_to_payload(ens)
    sp["smiles"] = "CCCC"
    sp["records"][0]["class"] = cls
    sp["records"][0]["boltzmann_weight"] = weight
    return {
        "environment": {"device": device},
        "species": {"n_butane": sp},
        "derived": {"dG_kcal_mol": 0.7},
    }


def test_regression_pass_and_failures() -> None:
    """Same -> pass; energy, weight, class, device or derived drift -> fail."""
    assert compare(payload(), payload())["status"] == "pass"
    assert compare(payload(shift=2e-5), payload())["status"] == "fail"
    assert compare(payload(weight=0.97), payload())["status"] == "fail"
    assert compare(payload(cls="gauche"), payload())["status"] == "fail"
    assert compare(payload(device="cuda"), payload())["status"] == "fail"
    drifted = payload()
    drifted["derived"]["dG_kcal_mol"] = 0.8
    assert compare(drifted, payload())["status"] == "fail"


def test_report_round_trip(tmp_path: Path) -> None:
    """The candidate writer is deterministic and float-exact (tmp_path, never the candidate dir)."""
    p = payload()
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    write_report(a, p)
    write_report(b, p)
    assert a.read_bytes() == b.read_bytes()
    assert (
        json.loads(a.read_text())["species"]["n_butane"]["records"][0]["gibbs_free_energy_hartree"]
        == (p["species"]["n_butane"]["records"][0]["gibbs_free_energy_hartree"])
    )


def test_reaction_spec_in_fixture_conserves() -> None:
    """HF2's reaction is ReactionSpec-valid (atoms and charge)."""
    spec = hf2().reaction
    assert isinstance(spec, ReactionSpec)


# R54: recursive derived regression ---------------------------------------------------------------


def hf2_derived_block() -> dict[str, Any]:
    """A nested derived block shaped like HF2's."""
    return {
        "ensemble": {"dG_1M_kcal_mol": -30.0, "dE_kcal_mol": -45.0, "delta_n": -1},
        "dG_r_lowest_records_kcal_mol": -29.6,
        "lowest_records_sigma": {"ethylene": 4},
        "incremental_solvation": {
            "alpb_toluene": {
                "observed_calls": 5,
                "dG_solv_kcal_mol": {"cyclohexene": -4.1, "ethylene": -1.4},
            },
            "pcm_toluene_ethylene_lowest": {"mechanism_only": True, "observed_calls": 1},
        },
        "note": "x",
        "energy_hartree": -1.0,
        "gauche_population_percent": 38.0,
    }


def nested_set(d: dict[str, Any], path: tuple[str, ...], value: Any) -> dict[str, Any]:
    """Return a deep copy of ``d`` with the leaf at ``path`` replaced."""
    out = json.loads(json.dumps(d))
    node = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return out


@pytest.mark.parametrize(
    ("path", "value", "fails"),
    [
        (("ensemble", "dG_1M_kcal_mol"), -30.06, True),
        (("ensemble", "dG_1M_kcal_mol"), -30.04, False),
        (("incremental_solvation", "alpb_toluene", "dG_solv_kcal_mol", "cyclohexene"), -4.16, True),
        (
            ("incremental_solvation", "alpb_toluene", "dG_solv_kcal_mol", "cyclohexene"),
            -4.14,
            False,
        ),
        (("energy_hartree",), -1.0 + 2e-5, True),
        (("energy_hartree",), -1.0 + 5e-6, False),
        (("gauche_population_percent",), 40.5, True),
        (("gauche_population_percent",), 39.5, False),
        (("incremental_solvation", "alpb_toluene", "observed_calls"), 6, True),
        (("ensemble", "delta_n"), -2, True),
        (("incremental_solvation", "pcm_toluene_ethylene_lowest", "mechanism_only"), False, True),
        (("note",), "y", True),
    ],
    ids=[
        "kcal_mol 0.06 fails",
        "kcal_mol 0.04 passes",
        "nested dG_solv 0.06 fails",
        "nested dG_solv 0.04 passes",
        "hartree 2e-5 fails",
        "hartree 5e-6 passes",
        "percent 2.5 fails",
        "percent 1.5 passes",
        "count changed fails",
        "delta_n changed fails",
        "bool changed fails",
        "string changed fails",
    ],
)
def test_derived_regression_by_unit(path: tuple[str, ...], value: Any, fails: bool) -> None:
    """R54: each leaf compared by the unit of its path; counts, bools and strings exact."""
    from regression import compare_derived

    old = hf2_derived_block()
    assert bool(compare_derived(old, nested_set(old, path, value))) is fails


def test_derived_regression_missing_keys_and_unclassified() -> None:
    """A key on one side only fails (either side); a float with no unit fails as unclassified."""
    from regression import compare_derived

    old = hf2_derived_block()
    new = json.loads(json.dumps(old))
    del new["incremental_solvation"]["alpb_toluene"]["dG_solv_kcal_mol"]["ethylene"]
    assert any("present only in the promoted" in f for f in compare_derived(old, new))
    assert any("present only in the new" in f for f in compare_derived(new, old))
    unclassified = {"block": {"ratio": 0.5}}
    assert compare_derived(unclassified, unclassified) == ["unclassified derived value block/ratio"]
    assert compare_derived(old, json.loads(json.dumps(old))) == []


# R55: T1 derived values are order-free ------------------------------------------------------------


def t1_derived(records: list[tuple[str, str]]) -> dict[str, Any]:
    """Build T1's order-free derived entries from (class, reperceived SMILES) per record."""
    classes = [c for c, _ in records]
    return {
        "class_counts": {c: classes.count(c) for c in ("s-trans", "s-cis-side")},
        "reperceived_smiles_unique": sorted({s for _, s in records}),
        "dG_scis_strans_kcal_mol": 1.147,
    }


def test_t1_derived_is_order_free() -> None:
    """The same records in a swapped (energy) order compare equal; a changed count fails."""
    from regression import compare_derived

    a = [
        ("s-trans", "C=C(/C=C/OC)OC"),
        ("s-cis-side", "C=C(/C=C/OC)OC"),
        ("s-trans", "C=C(/C=C/OC)OC"),
    ]
    swapped = [a[1], a[2], a[0]]
    assert compare_derived(t1_derived(a), t1_derived(swapped)) == []
    changed = t1_derived(a)
    changed["class_counts"]["s-trans"] = 3
    assert compare_derived(t1_derived(a), changed) != []
    # the old energy-ordered list form would have failed on the same swap
    old = {"classes": [c for c, _ in a]}
    new = {"classes": [c for c, _ in swapped]}
    assert compare_derived(old, new) != []
