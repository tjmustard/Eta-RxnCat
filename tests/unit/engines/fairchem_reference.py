"""Shared real-weights checks for the fairchem engines (imported by test_esen.py / test_uma.py).

The reference is fairchem's own path: ``get_predict_unit(name, inference_settings=
"high-precision", device=...)`` plus ``FAIRChemCalculator`` on ``ase.Atoms`` with charge and spin
in ``atoms.info`` (ase is used here, in tests only, never in src/). Nothing here downloads:
``HF_HUB_OFFLINE=1`` is set by the suite conftest, and missing weights skip at fixture level.
"""

import hashlib
import importlib
import re
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, StageConfig
from eta_rxncat.engines import ev_per_angstrom_to_hartree_per_bohr, ev_to_hartree
from eta_rxncat.engines._fairchem_bridge import FairchemEngine, _cached, _registry

EV = 27.211386245988
BOHR = 0.529177210903
CASES = ("water", "hydroxide", "hydroxyl", "pd_anion")


def energy_tol(energy_ev: float) -> float:
    """max(1e-6 eV, 1e-10 |E|): fairchem's float32 accumulation noise is ~4e-11 relative (R48)."""
    return max(1e-6, 1e-10 * abs(energy_ev))


def stage(cls: type[FairchemEngine]) -> StageConfig:
    """The approved single-point stage for ``cls``."""
    return StageConfig(kind="single_point", engine=cls.tag, method=cls.METHOD)


def require_weights(cls: type[FairchemEngine]) -> None:
    """Skip (fixture level) when the checkpoint is not in fairchem's cache."""
    try:
        entry = _registry(cls.REGISTRY_NAME)
        _cached(entry, entry["subfolder"], entry["filename"])
    except (ImportError, FileNotFoundError) as exc:
        pytest.skip(f"{cls.tag} weights not provisioned: {exc}")


@cache
def engine(cls: type[FairchemEngine], device: str) -> FairchemEngine:
    """One engine per (class, device), built once per session."""
    return cls.from_stage(stage(cls), device=device)


@cache
def reference_calc(name: str, device: str) -> Any:
    """Fairchem's own predictor + calculator for ``name`` at high precision on ``device``."""
    pretrained = importlib.import_module("fairchem.core.calculate.pretrained_mlip")
    calc_mod = importlib.import_module("fairchem.core.calculate.ase_calculator")
    unit = pretrained.get_predict_unit(name, inference_settings="high-precision", device=device)
    return calc_mod.FAIRChemCalculator(unit, task_name="omol")


def reference(name: str, device: str, state: MolecularState) -> tuple[float, list[list[float]]]:
    """(energy eV, forces eV/A) from fairchem's calculator with explicit charge and spin."""
    ase = importlib.import_module("ase")
    atoms = ase.Atoms(state.symbols, positions=state.coordinates)
    atoms.info.update(charge=state.charge, spin=state.spin_multiplicity)
    atoms.calc = reference_calc(name, device)
    return float(atoms.get_potential_energy()), atoms.get_forces().tolist()


def check_reference(
    cls: type[FairchemEngine], device: str, test_set: dict[str, MolecularState]
) -> None:
    """All four cases: energy <= 1e-6 eV and forces <= 1e-5 eV/A vs fairchem's own predictor."""
    eng = engine(cls, device)
    for case in CASES:
        s = test_set[case]
        result = eng.evaluate(s)
        assert result.device == device
        assert result.recovery_steps == ["fairchem_dtype:float32"]
        e_ref, f_ref = reference(cls.REGISTRY_NAME, device, s)
        d_e = abs(result.energy_hartree * EV - e_ref)
        forces = result.forces_hartree_per_bohr
        assert forces is not None
        d_f = max(
            abs(f * EV / BOHR - r)
            for fr, rr in zip(forces, f_ref, strict=True)
            for f, r in zip(fr, rr, strict=True)
        )
        print(
            f"{cls.tag} {device} {case}: E {result.energy_hartree!r} Eh, "
            f"|dE| {d_e:.2e} eV, |dF| {d_f:.2e} eV/A"
        )
        assert d_e <= energy_tol(e_ref), (case, d_e, energy_tol(e_ref))
        assert d_f <= 1e-5, (case, d_f)
        assert abs(result.energy_hartree - ev_to_hartree(e_ref)) <= ev_to_hartree(energy_tol(e_ref))


def check_liveness(
    cls: type[FairchemEngine], device: str, test_set: dict[str, MolecularState]
) -> None:
    """Charge and spin are live: water q0 vs q-1 (same geometry) and hydroxyl m2 vs m4 differ."""
    eng = engine(cls, device)
    water = test_set["water"]
    hydroxyl = test_set["hydroxyl"]
    anion = MolecularState(
        symbols=water.symbols, coordinates=water.coordinates, charge=-1, spin_multiplicity=2
    )
    quartet = MolecularState(
        symbols=hydroxyl.symbols, coordinates=hydroxyl.coordinates, charge=0, spin_multiplicity=4
    )
    e_w0 = eng.evaluate(water, forces=False).energy_hartree
    e_wm = eng.evaluate(anion, forces=False).energy_hartree
    e_d = eng.evaluate(hydroxyl, forces=False).energy_hartree
    e_q = eng.evaluate(quartet, forces=False).energy_hartree
    print(
        f"{cls.tag} {device}: water q0 {e_w0!r} vs q-1 {e_wm!r}; OH m2 {e_d!r} vs m4 {e_q!r} (Eh)"
    )
    assert abs(e_w0 - e_wm) > 1e-5
    assert abs(e_d - e_q) > 1e-5


def check_fd_forces(
    cls: type[FairchemEngine], device: str, test_set: dict[str, MolecularState]
) -> None:
    """Forces vs central FD of the engine energy (step 1e-3 A) <= 1e-3 eV/A on water."""
    eng = engine(cls, device)
    water = test_set["water"]
    forces = eng.evaluate(water).forces_hartree_per_bohr
    assert forces is not None
    step = 1e-3
    for i in range(9):
        e = []
        for sign in (1, -1):
            c = [row[:] for row in water.coordinates]
            c[i // 3][i % 3] += sign * step
            moved = MolecularState(
                symbols=water.symbols, coordinates=c, charge=0, spin_multiplicity=1
            )
            e.append(eng.evaluate(moved, forces=False).energy_hartree * EV)
        fd = -(e[0] - e[1]) / (2 * step)
        assert abs(forces[i // 3][i % 3] * EV / BOHR - fd) <= 1e-3, (
            i,
            forces[i // 3][i % 3] * EV / BOHR,
            fd,
        )


def check_hessian(
    cls: type[FairchemEngine], device: str, test_set: dict[str, MolecularState]
) -> None:
    """hessian=True on water: 9x9, finite_difference, exactly symmetric."""
    result = engine(cls, device).evaluate(test_set["water"], hessian=True)
    h = result.hessian_hartree_per_bohr2
    assert h is not None and len(h) == 9 and all(len(row) == 9 for row in h)
    assert result.hessian_method == "finite_difference"
    assert all(h[i][j] == h[j][i] for i in range(9) for j in range(9))
    assert result.hessian_max_asymmetry is not None


def check_refs_and_identity(cls: type[FairchemEngine], device: str) -> None:
    """R40/ADR-0017: the derived ref hashes and the identity hash are those of the files used."""
    eng = engine(cls, device)
    entry = _registry(cls.REGISTRY_NAME)
    opts = eng.stage.options
    for key, option in (
        ("atom_refs", "atom_refs_sha256"),
        ("form_elem_refs", "form_elem_refs_sha256"),
    ):
        if entry[key] is None:
            assert opts[option] == "none"
        else:
            path = _cached(entry, entry[key]["subfolder"], entry[key]["filename"])
            assert opts[option] == hashlib.sha256(Path(path).read_bytes()).hexdigest()
    checkpoint = _cached(entry, entry["subfolder"], entry["filename"])
    digest = hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
    assert eng.identity.model == f"{cls.METHOD}@sha256:{digest}"
    assert re.fullmatch(rf"{re.escape(cls.METHOD)}@sha256:[0-9a-f]{{64}}", eng.identity.model)


def check_edited_refs_change_energy_and_key(
    cls: type[FairchemEngine], tmp_path: Path, test_set: dict[str, MolecularState]
) -> None:
    """A tmp copy of atom_refs with one value edited changes the derived sha and the key."""
    from eta_rxncat.store import build_stage_key

    entry = _registry(cls.REGISTRY_NAME)
    original = Path(_cached(entry, entry["atom_refs"]["subfolder"], entry["atom_refs"]["filename"]))
    text = original.read_text()
    match = re.search(r"^(\s*1\s*:\s*)(-?[0-9.eE+-]+)", text, flags=re.M) or re.search(
        r"^(\s*H\s*:\s*)(-?[0-9.eE+-]+)", text, flags=re.M
    )
    assert match, "no H/1 entry in the atom refs file"
    edited = tmp_path / original.name
    edited.write_text(
        text[: match.start(2)] + str(float(match.group(2)) + 0.5) + text[match.end(2) :]
    )
    base = engine(cls, "cpu")
    changed = cls.from_stage(stage(cls), device="cpu", atom_refs_path=edited)
    assert changed.stage.options["atom_refs_sha256"] != base.stage.options["atom_refs_sha256"]
    water = test_set["water"]
    assert (
        build_stage_key(water, base.stage, base.identity).key
        != build_stage_key(water, changed.stage, changed.identity).key
    )


def check_batch_matches_from_ase(
    cls: type[FairchemEngine], device: str, test_set: dict[str, MolecularState]
) -> None:
    """The engine's AtomicData equals fairchem's from_ase (as FAIRChemCalculator calls it)."""
    torch = importlib.import_module("torch")
    ase = importlib.import_module("ase")
    atomic_data = importlib.import_module("fairchem.core.datasets.atomic_data")
    eng = engine(cls, device)
    for case in CASES:
        s = test_set[case]
        mine = eng.batch(s, s.coordinates)
        atoms = ase.Atoms(s.symbols, positions=s.coordinates)
        atoms.info.update(charge=s.charge, spin=s.spin_multiplicity)
        theirs = atomic_data.AtomicData.from_ase(
            atoms,
            task_name="omol",
            r_edges=False,
            r_data_keys=["spin", "charge"],
            radius=6.0,
            target_dtype=eng.predict_unit.inference_settings.base_precision_dtype,
        )
        for key in (
            "pos",
            "atomic_numbers",
            "cell",
            "pbc",
            "natoms",
            "charge",
            "spin",
            "fixed",
            "tags",
            "edge_index",
            "nedges",
        ):
            assert torch.equal(getattr(mine, key), getattr(theirs, key)), (case, key)
        assert mine.dataset == theirs.dataset == ["omol"]
        assert int(mine.charge[0]) == s.charge and int(mine.spin[0]) == s.spin_multiplicity


def check_cpu_cuda_agree(cls: type[FairchemEngine], test_set: dict[str, MolecularState]) -> None:
    """R47: at high precision CPU and CUDA agree to <= 1e-6 eV and <= 1e-5 eV/A, all four cases."""
    cpu, cuda = engine(cls, "cpu"), engine(cls, "cuda")
    for case in CASES:
        a, b = cpu.evaluate(test_set[case]), cuda.evaluate(test_set[case])
        d_e = abs(a.energy_hartree - b.energy_hartree) * EV
        fa, fb = a.forces_hartree_per_bohr, b.forces_hartree_per_bohr
        assert fa is not None and fb is not None
        d_f = (
            max(
                abs(x - y)
                for ra, rb in zip(fa, fb, strict=True)
                for x, y in zip(ra, rb, strict=True)
            )
            * EV
            / BOHR
        )
        tol = energy_tol(a.energy_hartree * EV)
        print(
            f"{cls.tag} cpu vs cuda {case}: |dE| {d_e:.2e} eV (tol {tol:.1e}), |dF| {d_f:.2e} eV/A"
        )
        assert d_e <= tol and d_f <= 1e-5, (case, d_e, d_f)
        assert ev_per_angstrom_to_hartree_per_bohr(1.0) > 0
