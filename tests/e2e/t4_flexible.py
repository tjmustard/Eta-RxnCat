"""Tier 4 flexible-ensemble E2E helpers (v0.6.0 slice 14): an alkyl R-group series on TS1a_n.

TJ's amended Q-RES1 B: graft R = ethyl, n-propyl and n-butyl onto the cyclopropene CH2 of TS1a_n
with eta's graft, pre-relax each graft with the core frozen inside slice 13's wall-time guard, run
the v0.6.0 TS ensemble on one engine, and gate per R the ensemble (no failure, at least two
distinct members, unit weights, the seed's face, no ``face_mismatch``/``engine_error``) and the
second pass (all hits). Member counts, energies and the order of chain lengths are reported only.
Tests and inputs only: nothing here changes ``src/``.
"""

import hashlib
import json
import os
import platform
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from e2e_env import REPO
from fixtures import _exact_keys, _species, read_xyz
from rdkit import Chem, rdBase
from rdkit.Chem import AllChem
from rdkit.Chem import rdMolTransforms as transforms
from t3 import REACTANT_STAGES, all_hit, ts_recipe
from t4 import STAGE_KINDS, exclusions_by_reason, member_gates

from eta_rxncat.conformers import forming_bond_configuration
from eta_rxncat.core import (
    AtomMappingSpec,
    GraftResult,
    GraftSpec,
    MolecularState,
    TSEnsembleOptions,
)
from eta_rxncat.engines import HARTREE_KCAL_MOL
from eta_rxncat.mapping import graft, perceive_bonds, relax_constrained_core
from eta_rxncat.mapping.align import superpose
from eta_rxncat.optimize import GeometricOptimizer, Optimizer
from eta_rxncat.orchestrator import (
    Recipe,
    SpeciesResult,
    SpeciesSpec,
    TSEnsembleRun,
    TSSpec,
    build_engine,
    run_species,
    run_ts_ensemble_detailed,
)
from eta_rxncat.orchestrator._deadline import PreRelaxTimeout, deadline
from eta_rxncat.orchestrator.ts_ensemble import PRE_RELAX_BUDGET_S
from eta_rxncat.store import ArtifactStore

DATA = Path(__file__).resolve().parent / "data" / "e2e5"
FLEX_YAML = "t4_flexible_alkyl.yaml"
CANDIDATES_V060 = REPO / "tests" / "candidate_outputs" / "v0.6.0"
RECIPES = ("xtb", "uma")
SERIES = ("ethyl", "npropyl", "nbutyl")
SMILES = {"ethyl": "CCC1C=C1", "npropyl": "CCCC1C=C1", "nbutyl": "CCCCC1C=C1"}
TIMEOUT_REASON = "graft_pre_relax_timeout"
WEIGHT_TOLERANCE = 1e-12
MIN_DISTINCT_MEMBERS = 2
MAX_ALIGNMENT_RMSD_ANGSTROM = 0.05


# --- The fragments: 3-R-cyclopropenes with the chain all-anti ----------------------------------


def fragment_roles(smiles: str) -> dict[str, Any]:
    """The graft roles of a 3-R-cyclopropene by RDKit atom index (``AddHs`` order).

    ``ring_sp3`` is the ring sp3 carbon, ``sp2`` the two ring sp2 carbons (sorted), ``ring_h``
    the H on ``ring_sp3``, ``sp2_h`` the two sp2 hydrogens (sorted), ``chain`` the chain carbons
    from the ring outward.
    """
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    ring = [a for a in mol.GetAtoms() if a.IsInRing()]
    sp3 = next(a for a in ring if a.GetHybridization() == Chem.HybridizationType.SP3)
    sp2 = sorted(a.GetIdx() for a in ring if a.GetIdx() != sp3.GetIdx())
    ring_h = next(n.GetIdx() for n in sp3.GetNeighbors() if n.GetSymbol() == "H")
    sp2_h = sorted(
        n.GetIdx()
        for i in sp2
        for n in mol.GetAtomWithIdx(i).GetNeighbors()
        if n.GetSymbol() == "H"
    )
    chain = [sp3.GetIdx()]
    while True:
        nxt = [
            n.GetIdx()
            for n in mol.GetAtomWithIdx(chain[-1]).GetNeighbors()
            if n.GetSymbol() == "C" and not n.IsInRing() and n.GetIdx() not in chain
        ]
        if not nxt:
            break
        chain.append(nxt[0])
    return {"ring_sp3": sp3.GetIdx(), "sp2": sp2, "ring_h": ring_h, "sp2_h": sp2_h, "chain": chain}


def build_fragment(smiles: str) -> tuple[list[str], np.ndarray]:
    """ETKDGv3 (seed 42) + MMFF, then the chain all-anti (HF-14): the recipe of the committed files.

    The ring-H - ring C(sp3) - Calpha - Cbeta dihedral is set to 180 degrees, then every C-C-C-C
    dihedral outward. The plain ETKDG conformer of n-propyl folds the chain onto the ring and the
    graft refuses it.
    """
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    AllChem.EmbedMolecule(mol, params)
    AllChem.MMFFOptimizeMolecule(mol)
    roles = fragment_roles(smiles)
    chain, conf = roles["chain"], mol.GetConformer()
    for k in range(1, len(chain) - 1):
        first = roles["ring_h"] if k == 1 else chain[k - 2]
        transforms.SetDihedralDeg(conf, first, chain[k - 1], chain[k], chain[k + 1], 180.0)
    return [a.GetSymbol() for a in mol.GetAtoms()], np.asarray(conf.GetPositions())


def write_fragment_xyz(path: Path, smiles: str) -> str:
    """Write the fragment with 6 decimals and return its sha256 (done once, then committed)."""
    symbols, xyz = build_fragment(smiles)
    header = f"{smiles} ETKDGv3 seed 42 + MMFF, chain all-anti, RDKit {rdBase.rdkitVersion}"
    rows = "".join(
        f"{s} {x:.6f} {y:.6f} {z:.6f}\n" for s, (x, y, z) in zip(symbols, xyz, strict=True)
    )
    text = f"{len(symbols)}\n{header}\n{rows}"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- The fixture -------------------------------------------------------------------------------


@dataclass(frozen=True)
class FlexSeries:
    """One R of the series: its fragment file, graft lists and the stated member expectation."""

    r_group: str
    smiles: str
    fragment: Path
    sha256: str
    ring_sp3: int
    sp2_order: tuple[int, int]
    ring_h: int
    fragment_delete: tuple[int, ...]
    expected_members: int


@dataclass(frozen=True)
class FlexFixture:
    """The flexible-ensemble fixture: the template, the series and the shared settings."""

    name: str
    path: Path
    template: Path
    template_active: tuple[int, ...]
    keep: tuple[int, ...]
    delete: tuple[int, ...]
    alignment: tuple[int, ...]
    core: tuple[int, ...]
    forming_bonds: tuple[tuple[int, int], ...]
    pre_relax_maxiter: int
    temperature_k: float
    species: tuple[SpeciesSpec, ...]
    reactant_smiles: str
    series: tuple[FlexSeries, ...]

    def get(self, r_group: str) -> FlexSeries:
        """Return one R of the series."""
        return next(s for s in self.series if s.r_group == r_group)


def load_flex_fixture(path: Path | None = None) -> FlexFixture:
    """Load and validate ``t4_flexible_alkyl.yaml`` (unknown or missing keys are refused)."""
    path = Path(path) if path else DATA / FLEX_YAML
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise ValueError(f"{path}: schema must be 1")
    _exact_keys(
        path,
        "top-level",
        data,
        {"schema", "fixture", "template", "core", "forming_bonds", "pre_relax", "temperature_k"}
        | {"species", "series", "gates"},
    )
    template = data["template"]
    _exact_keys(
        path, "template", template, {"xyz", "active_atom_indices", "keep", "delete", "alignment"}
    )
    series = []
    for block in data["series"]:
        _exact_keys(
            path,
            "series[]",
            block,
            {"r_group", "smiles", "fragment_xyz", "sha256", "ring_sp3", "sp2_order", "ring_h"}
            | {"fragment_delete", "expected_members"},
        )
        series.append(
            FlexSeries(
                r_group=str(block["r_group"]),
                smiles=str(block["smiles"]),
                fragment=path.parent / str(block["fragment_xyz"]),
                sha256=str(block["sha256"]),
                ring_sp3=int(block["ring_sp3"]),
                sp2_order=(int(block["sp2_order"][0]), int(block["sp2_order"][1])),
                ring_h=int(block["ring_h"]),
                fragment_delete=tuple(int(i) for i in block["fragment_delete"]),
                expected_members=int(block["expected_members"]),
            )
        )
    species = _species(path, data["species"])
    return FlexFixture(
        name=str(data["fixture"]),
        path=path,
        template=path.parent / str(template["xyz"]),
        template_active=tuple(int(i) for i in template["active_atom_indices"]),
        keep=tuple(int(i) for i in template["keep"]),
        delete=tuple(int(i) for i in template["delete"]),
        alignment=tuple(int(i) for i in template["alignment"]),
        core=tuple(int(i) for i in data["core"]),
        forming_bonds=tuple((int(a), int(b)) for a, b in data["forming_bonds"]),
        pre_relax_maxiter=int(data["pre_relax"]["maxiter"]),
        temperature_k=float(data["temperature_k"]),
        species=tuple(species),
        reactant_smiles=str(species[0].smiles),
        series=tuple(series),
    )


def flex() -> FlexFixture:
    """The committed fixture."""
    return load_flex_fixture()


# --- The graft ---------------------------------------------------------------------------------


def template_state(fixture: FlexFixture) -> MolecularState:
    """TS1a_n with its active core."""
    state = read_xyz(fixture.template, 0, 1)
    return MolecularState.model_validate(
        {**state.model_dump(), "active_atom_indices": list(fixture.template_active)}
    )


def fit_rmsd(fixture: FlexFixture, series: FlexSeries, order: tuple[int, int]) -> float:
    """Alignment RMSD of the four pairs for one sp2 order (no product is built)."""
    template = np.asarray(template_state(fixture).coordinates)[list(fixture.alignment)]
    fragment = read_xyz(series.fragment, 0, 1)
    pairs = [series.ring_sp3, order[0], order[1], series.ring_h]
    return float(superpose(np.asarray(fragment.coordinates)[pairs], template).rmsd_angstrom)


def lower_fit_order(fixture: FlexFixture, series: FlexSeries) -> tuple[int, int]:
    """The sp2 pair order with the lower alignment RMSD (HF-14: never chosen any other way)."""
    a, b = sorted(series.sp2_order)
    orders = [(a, b), (b, a)]
    return min(orders, key=lambda o: fit_rmsd(fixture, series, o))


def graft_series(fixture: FlexFixture, series: FlexSeries) -> GraftResult:
    """Graft the R fragment onto TS1a_n at the stored sp2 order."""
    spec = GraftSpec(
        template=AtomMappingSpec(
            keep=list(fixture.keep), delete=list(fixture.delete), alignment=list(fixture.alignment)
        ),
        fragment_alignment=[series.ring_sp3, *series.sp2_order, series.ring_h],
        fragment_delete=list(series.fragment_delete),
        constrained_core=list(fixture.core),
        product_charge=0,
        product_multiplicity=1,
    )
    return graft(template_state(fixture), read_xyz(series.fragment, 0, 1), spec)


@dataclass(frozen=True)
class GraftPreRelax:
    """The guarded core-frozen pre-relaxation of one graft."""

    start: MolecularState | None
    failed_reason: str | None
    wall_time_s: float
    n_steps: int | None = None
    n_engine_calls: int | None = None
    final_energy_hartree: float | None = None


def guarded_graft_pre_relax(
    product: MolecularState,
    engine: Any,
    optimizer: Optimizer,
    core: Sequence[int],
    maxiter: int,
    budget_s: float = PRE_RELAX_BUDGET_S,
) -> GraftPreRelax:
    """Pre-relax a graft with the core frozen inside ``deadline(budget_s)`` (TJ's HF-13 guard).

    A ``PreRelaxTimeout`` gives ``failed_reason == "graft_pre_relax_timeout"`` (recorded, never a
    hang). The relaxed state keeps the product's active core.
    """
    start = time.perf_counter()
    try:
        with deadline(budget_s):
            relaxed = relax_constrained_core(
                product, engine, optimizer, list(core), options={"maxiter": maxiter}
            )
    except PreRelaxTimeout:
        return GraftPreRelax(None, TIMEOUT_REASON, time.perf_counter() - start)
    state = MolecularState.model_validate(
        {
            **relaxed.final_state.model_dump(),
            "active_atom_indices": list(core),
        }
    )
    return GraftPreRelax(
        state,
        None,
        time.perf_counter() - start,
        relaxed.n_steps,
        relaxed.n_engine_calls,
        relaxed.final_energy_hartree,
    )


# --- One R x recipe: reactants, the guarded graft pre-relax, the ensemble, twice ---------------


@dataclass(frozen=True)
class FlexRun:
    """One R on one recipe: the graft, its pre-relax, and two passes in one store."""

    series: FlexSeries
    graft: GraftResult
    pre: GraftPreRelax
    reactants: tuple[dict[str, SpeciesResult], dict[str, SpeciesResult]]
    runs: tuple[TSEnsembleRun | None, TSEnsembleRun | None]
    barrier: dict[str, float] | None = None
    barrier_error: str | None = None
    wall_time_s: tuple[float, float] = (0.0, 0.0)
    store_rows: dict[str, int] = field(default_factory=dict)
    seed_face: tuple[int, ...] | None = None


def reactant_specs(fixture: FlexFixture, series: FlexSeries) -> tuple[SpeciesSpec, ...]:
    """Cyclopentadiene (the fixture's species) and the 3-R-cyclopropene (n_embed 10, seed 42)."""
    from eta_rxncat.conformers import ConformerOptions

    rcp = SpeciesSpec(
        species_id=f"{series.r_group}_cyclopropene",
        smiles=series.smiles,
        charge=0,
        spin_multiplicity=1,
        conformer_options=ConformerOptions(n_embed=10, seed=42),
    )
    return (*fixture.species, rcp)


def reactant_key(fixture: FlexFixture, series: FlexSeries) -> tuple[tuple[str, int], ...]:
    """The sorted ``(SMILES, count)`` pairs of the two reactants."""
    return tuple(sorted((s.smiles, 1) for s in reactant_specs(fixture, series)))


def run_flexible(
    fixture: FlexFixture, series: FlexSeries, recipe: Recipe, recipe_name: str, store_path: Path
) -> FlexRun:
    """Graft, pre-relax inside the guard, then reactants and the ensemble twice in one store."""
    from eta_rxncat.orchestrator import BarrierSpec, activation_free_energy

    result = graft_series(fixture, series)
    engine = build_engine(recipe.engine_stage, recipe.engine_runtime)
    pre = guarded_graft_pre_relax(
        result.product, engine, GeometricOptimizer(), fixture.core, fixture.pre_relax_maxiter
    )
    specs = reactant_specs(fixture, series)
    reactants: list[dict[str, SpeciesResult]] = []
    runs: list[TSEnsembleRun | None] = []
    walls: list[float] = []
    for _ in range(2):
        t0 = time.perf_counter()
        run: TSEnsembleRun | None = None
        with ArtifactStore(store_path) as store:
            reactants.append({s.species_id: run_species(s, recipe, store) for s in specs})
            if pre.start is not None:
                seed = TSSpec(
                    ts_id=f"TS1a_n_{series.r_group}",
                    start=pre.start,
                    forming_bonds=fixture.forming_bonds,
                )
                run = run_ts_ensemble_detailed(
                    seed,
                    ts_recipe(recipe),
                    store,
                    optimizer=GeometricOptimizer(),
                    core_indices=list(fixture.core),
                    pathway="endo",
                    reactant_key=reactant_key(fixture, series),
                    options=TSEnsembleOptions(),
                    member_gates=member_gates(recipe_name),
                )
        runs.append(run)
        walls.append(time.perf_counter() - t0)
    with ArtifactStore(store_path) as store:
        rows = {k: len(store.query(k)) for k in (*STAGE_KINDS, "conformer_search")}
    barrier: dict[str, float] | None = None
    error: str | None = None
    first = runs[0]
    if first is not None and first.seed_result.record is not None:
        spec = BarrierSpec(
            reactants=tuple((s.species_id, 1) for s in specs),
            ts_id=f"TS1a_n_{series.r_group}",
            smiles={s.species_id: s.smiles for s in specs},
        )
        try:
            seed_barrier = activation_free_energy(
                spec,
                {k: v.ensemble for k, v in reactants[0].items()},
                first.seed_result.record,
                recipe.thermo_config,
            )
        except ValueError as exc:
            error = str(exc)
        else:
            g_path = first.ensemble.G_pathway_hartree
            shift = (
                0.0
                if g_path is None
                else (g_path - first.seed_result.record.thermo.gibbs_free_energy_hartree)
                * HARTREE_KCAL_MOL
            )
            barrier = {
                "seed_dG_dagger_1M_kcal_mol": seed_barrier.dG_dagger_1M_kcal_mol,
                "ensemble_dG_dagger_1M_kcal_mol": seed_barrier.dG_dagger_1M_kcal_mol + shift,
                "ensemble_correction_kcal_mol": shift,
            }
    seed_face = None
    if first is not None and first.seed_result.record is not None:
        final = first.seed_result.record.state
        pairs = sorted((min(i, j), max(i, j)) for i, j in fixture.forming_bonds)
        seed_face = forming_bond_configuration(final, pairs, perceive_bonds(final))
    return FlexRun(
        series,
        result,
        pre,
        (reactants[0], reactants[1]),
        (runs[0], runs[1]),
        barrier,
        error,
        (walls[0], walls[1]),
        rows,
        seed_face,
    )


# --- Gates -------------------------------------------------------------------------------------


def _status(ok: bool, gated: bool = True) -> dict[str, Any]:
    return {"status": ("pass" if ok else "fail") if gated else "reported"}


def second_pass_hits(run: FlexRun) -> bool:
    """Gate (e): the second pass made no engine call and wrote no row, and hit every stage."""
    first, second = run.runs
    if first is None or second is None:
        return False
    for kind in STAGE_KINDS:
        m = second.metrics[kind]
        if m.rows_created != 0 or m.engine_calls != 0:
            return False
    if second.metrics["ts_opt"].cache_hits == 0 or second.metrics["frequency"].cache_hits == 0:
        return False
    reactants_hit = all(all_hit(r, k) for r in run.reactants[1].values() for k in REACTANT_STAGES)
    return reactants_hit and first.ensemble == second.ensemble


def gates(run: FlexRun) -> dict[str, dict[str, Any]]:
    """Gates (a)-(f) of one R x recipe, each ``pass`` or ``fail``."""
    first = run.runs[0]
    ensemble = None if first is None else first.ensemble
    members = [] if ensemble is None else ensemble.members
    reasons = {} if ensemble is None else exclusions_by_reason(ensemble)
    weight_sum = sum(m.weight for m in members)
    seed_face = None if run.seed_face is None else list(run.seed_face)
    return {
        "graft_pre_relax_no_timeout": {
            **_status(run.pre.failed_reason is None),
            "failed_reason": run.pre.failed_reason,
        },
        "ensemble_no_failed_reason": {
            **_status(ensemble is not None and ensemble.failed_reason is None),
            "failed_reason": None if ensemble is None else ensemble.failed_reason,
        },
        "distinct_members_at_least_2": {
            **_status(len(members) >= MIN_DISTINCT_MEMBERS),
            "n_members": len(members),
        },
        "weights_sum_to_one": {
            **_status(bool(members) and abs(weight_sum - 1.0) <= WEIGHT_TOLERANCE),
            "weights_sum": weight_sum,
        },
        "faces_equal_the_seeds_no_face_or_engine_error": {
            **_status(
                bool(members)
                and seed_face is not None
                and all(m.face == seed_face for m in members)
                and "face_mismatch" not in reasons
                and "engine_error" not in reasons
            ),
            "seed_face": seed_face,
        },
        "second_pass_all_hits_equal_ensemble": _status(second_pass_hits(run)),
    }


# --- The candidate -----------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """The sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_totals(run: TSEnsembleRun) -> dict[str, dict[str, float]]:
    """Per stage kind: wall time, engine calls, cache hits and rows created."""
    return {
        kind: {
            "wall_time_s": run.metrics[kind].wall_time_s,
            "engine_calls": run.metrics[kind].engine_calls,
            "cache_hits": run.metrics[kind].cache_hits,
            "rows_created": run.metrics[kind].rows_created,
        }
        for kind in STAGE_KINDS
    }


def reported_block(fixture: FlexFixture, run: FlexRun) -> dict[str, Any]:
    """Everything reported and never gated: members, energies, exclusions, barriers, walls."""
    first = run.runs[0]
    block: dict[str, Any] = {
        "r_group": run.series.r_group,
        "expected_members": run.series.expected_members,
        "wall_time_s": {"first_pass": run.wall_time_s[0], "second_pass": run.wall_time_s[1]},
        "graft_pre_relax_wall_time_s": run.pre.wall_time_s,
        "barrier": run.barrier,
        "barrier_error": run.barrier_error,
        "store_rows": dict(run.store_rows),
    }
    if first is None:
        return block
    ensemble = first.ensemble
    lowest = min((m.G_hartree for m in ensemble.members), default=0.0)
    block.update(
        n_members=len(ensemble.members),
        members=[
            {
                "index": m.index,
                "source": m.source,
                "weight": m.weight,
                "G_hartree": m.G_hartree,
                "relative_G_kcal_mol": (m.G_hartree - lowest) * HARTREE_KCAL_MOL,
                "degeneracy": m.degeneracy,
                "rmsd_to_seed_angstrom": m.rmsd_to_seed_angstrom,
                "face": m.face,
                "pre_relax_wall_time_s": m.pre_relax_wall_time_s,
            }
            for m in ensemble.members
        ],
        exclusions_by_reason=exclusions_by_reason(ensemble),
        n_merges=len(ensemble.merges),
        n_flagged_merges=len(ensemble.flagged_merges),
        G_pathway_hartree=ensemble.G_pathway_hartree,
        max_pre_relax_wall_time_s=first.max_pre_relax_wall_time_s,
        stage_metrics=stage_totals(first),
        second_pass_stage_metrics=(None if run.runs[1] is None else stage_totals(run.runs[1])),
    )
    return block


def graft_block(fixture: FlexFixture, run: FlexRun) -> dict[str, Any]:
    """The graft: sizes, fit, contacts, the two sp2-order fits, and the pre-relax numbers."""
    a, b = sorted(run.series.sp2_order)
    return {
        "n_atoms": len(run.graft.product.symbols),
        "alignment_rmsd_angstrom": run.graft.alignment_rmsd_angstrom,
        "close_contacts": [c.model_dump(mode="json") for c in run.graft.close_contacts],
        "sp2_order": list(run.series.sp2_order),
        "sp2_order_fits_angstrom": {
            f"{a},{b}": fit_rmsd(fixture, run.series, (a, b)),
            f"{b},{a}": fit_rmsd(fixture, run.series, (b, a)),
        },
        "pre_relax": {
            "core": list(fixture.core),
            "maxiter": fixture.pre_relax_maxiter,
            "budget_s": PRE_RELAX_BUDGET_S,
            "failed_reason": run.pre.failed_reason,
            "wall_time_s": run.pre.wall_time_s,
            "n_steps": run.pre.n_steps,
            "n_engine_calls": run.pre.n_engine_calls,
            "final_energy_hartree": run.pre.final_energy_hartree,
        },
    }


def inputs_block(fixture: FlexFixture, series: FlexSeries) -> dict[str, str]:
    """The sha256 of the fragment, the template and the fixture YAML this run used."""
    return {
        "fragment": sha256_file(series.fragment),
        "template": sha256_file(fixture.template),
        "fixture_yaml": sha256_file(fixture.path),
    }


def run_environment(recipe_name: str) -> dict[str, Any]:
    """The environment variables the acceptance rules require (R9), as set."""
    env = {"ETA_RXNCAT_ACCEPTANCE": os.environ.get("ETA_RXNCAT_ACCEPTANCE", "")}
    if recipe_name == "xtb":
        env["ETA_RXNCAT_XTB"] = os.environ.get("ETA_RXNCAT_XTB", "")
    env["platform"] = platform.platform()
    env["rdkit"] = rdBase.rdkitVersion
    env["eta_rxncat"] = _version()
    return env


def _version() -> str:
    try:
        return metadata.version("eta-rxncat")
    except metadata.PackageNotFoundError:
        return "unknown"


def count_state_path(recipe_name: str) -> Path | None:
    """Scratch file holding the member counts seen so far on this recipe (never a candidate)."""
    base = os.environ.get("ETA_RXNCAT_FLEX_STATE")
    return Path(base) / f"flex_counts.{recipe_name}.json" if base else None


def non_decreasing_report(recipe_name: str, r_group: str, n_members: int) -> dict[str, Any]:
    """Whether the member count is non-decreasing over the R's seen so far (reported only).

    The counts of earlier R's come from a scratch file under ``ETA_RXNCAT_FLEX_STATE`` (written
    by this function, never a candidate); without it only this R is known.
    """
    path = count_state_path(recipe_name)
    seen: dict[str, int] = {}
    if path is not None and path.is_file():
        seen = {str(k): int(v) for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    seen[r_group] = n_members
    if path is not None:
        path.write_text(json.dumps(seen, sort_keys=True), encoding="utf-8")
    ordered = [seen[r] for r in SERIES if r in seen]
    return {
        "status": "reported",
        "counts_seen": {r: seen[r] for r in SERIES if r in seen},
        "complete": len(ordered) == len(SERIES),
        "non_decreasing": all(a <= b for a, b in zip(ordered, ordered[1:], strict=False)),
    }


def candidate_name(r_group: str, recipe_name: str) -> str:
    """``t4_flexible_<R>.<recipe>.json``."""
    return f"t4_flexible_{r_group}.{recipe_name}.json"


def bonds_of(state: MolecularState) -> set[tuple[int, int]]:
    """The perceived bonds of a state as a set of ascending pairs."""
    return {(min(i, j), max(i, j)) for i, j in perceive_bonds(state)}


def counted_reasons(run: TSEnsembleRun) -> Mapping[str, int]:
    """Exclusion reasons of a run's ensemble (a Counter, for tests)."""
    return Counter(e.reason for e in run.ensemble.excluded)
