"""Tests for the PySCF engine's GPU path (slice 07).

Unmarked tests run in the default suite with fakes (no GPU needed). ``gpu`` tests run real
GPU4PySCF on the CUDA device in ``.venv-accept-gpu``:
``UV_PROJECT_ENVIRONMENT=.venv-accept-gpu ETA_RXNCAT_ACCEPTANCE=1 uv run --no-sync pytest -m gpu
tests/unit/engines/test_pyscf_gpu.py``.
"""

import json
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import EngineRuntimeError, EngineUnavailableError, PySCFEngine
from eta_rxncat.engines.pyscf_gpu_cpu import engine as engine_module
from eta_rxncat.engines.pyscf_gpu_cpu import gpu as gpu_module
from eta_rxncat.engines.pyscf_gpu_cpu.gpu import (
    CUBLAS_ALLOC_FAILED,
    CUDA_RUNTIME_ALLOC,
    CUSOLVER_ALLOC_FAILED,
    GPU_ANALYTIC_KS_HESSIAN_CLASSES,
    GPU_KS_HESSIAN_GRID_RESPONSE,
    GPU_STABILITY_CPU_COPY_STEP,
    GPU_STABILITY_MIN_ROTATIONS,
    VRAM_OVERHEAD_BYTES,
    VRAM_SAFETY,
    classes_from_record,
    estimate_bytes,
    is_gpu_oom,
    to_host,
)

REPO = Path(__file__).resolve().parents[3]
CALIBRATION = REPO / "docs/prd/v0.2.0/calibration/pyscf_vram.json"
GPU_SUPPORT = REPO / "docs/prd/v0.2.0/evidence/pyscf-gpu-support.json"


def stage(method: str = "hf", basis: str = "sto-3g", **kwargs: Any) -> StageConfig:
    """A PySCF single-point stage."""
    return StageConfig(
        kind="single_point", engine="pyscf_gpu_cpu", method=method, basis=basis, **kwargs
    )


# ---------------------------------------------------------------- fakes (default suite)


class FakeOOM(MemoryError):
    """Stands in for cupy.cuda.memory.OutOfMemoryError."""


class FakeStatusError(RuntimeError):
    """Stands in for CuPy's status-carrying CUDA / cuBLAS / cuSOLVER errors."""

    def __init__(self, status: int) -> None:
        """Carry ``status`` like the CuPy class does."""
        super().__init__(f"status {status}")
        self.status = status


class FakeRuntimeError(FakeStatusError):
    """cupy CUDARuntimeError."""


class FakeDriverError(FakeStatusError):
    """cupy CUDADriverError."""


class FakeCublasError(FakeStatusError):
    """cupy CUBLASError."""


class FakeCusolverError(FakeStatusError):
    """cupy CUSOLVERError."""


class FakePool:
    """A CuPy memory pool that counts free_all_blocks calls."""

    def __init__(self) -> None:
        """Start with no frees."""
        self.freed = 0

    def free_all_blocks(self) -> None:
        """Count the call."""
        self.freed += 1


def fake_gpu() -> SimpleNamespace:
    """A gpu_modules()-shaped namespace with fake error classes and counting pools."""
    device, pinned = FakePool(), FakePool()
    cupy = SimpleNamespace(
        get_default_memory_pool=lambda: device,
        get_default_pinned_memory_pool=lambda: pinned,
        cuda=SimpleNamespace(
            runtime=SimpleNamespace(memGetInfo=lambda: (7_000_000_000, 8_073_248_768))
        ),
    )
    return SimpleNamespace(
        cupy=cupy,
        scf=None,
        dft=None,
        version="1.9.2-fake",
        OutOfMemoryError=FakeOOM,
        CUDARuntimeError=FakeRuntimeError,
        CUDADriverError=FakeDriverError,
        CUBLASError=FakeCublasError,
        CUSOLVERError=FakeCusolverError,
        pools=(device, pinned),
    )


@pytest.fixture
def gpu_engine(monkeypatch: pytest.MonkeyPatch) -> tuple[PySCFEngine, SimpleNamespace, list[bool]]:
    """An HF/sto-3g engine whose GPU is a fake; ``_run`` on the 'GPU' raises what ``fail`` says."""
    fake = fake_gpu()
    monkeypatch.setattr(engine_module, "gpu_modules", lambda: fake)
    eng = PySCFEngine.from_stage(stage(), device="cuda")
    calls: list[bool] = []
    real = PySCFEngine._run

    def run(self: PySCFEngine, state: MolecularState, st: StageConfig, **kw: Any) -> Any:
        calls.append(self._on_gpu)
        if self._on_gpu:
            raise fake.raise_next
        return real(self, state, st, **kw)

    monkeypatch.setattr(PySCFEngine, "_run", run)
    return eng, fake, calls


def test_budget_read_once_at_construction(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ADR-0008 budget comes from memGetInfo at construction: min(6.5 GiB, total)."""
    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    eng = PySCFEngine.from_stage(stage(), device="auto")
    assert eng.vram_budget_bytes == 6_979_321_856


def test_budget_of_one_byte_runs_on_cpu(
    monkeypatch: pytest.MonkeyPatch, test_set: dict[str, MolecularState]
) -> None:
    """Estimate > budget: CPU, device_reason vram_estimate_over_budget, the step recorded."""
    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    eng = PySCFEngine.from_stage(stage(), device="auto")
    eng.vram_budget_bytes = 1
    result = eng.evaluate(test_set["water"], forces=False)
    assert result.device == "cpu"
    assert result.device_reason == "vram_estimate_over_budget"
    assert result.recovery_steps[0] == "vram_estimate>budget->cpu"
    assert result.recovery_steps[-1] == "stability:stable"


@pytest.mark.parametrize(
    "error",
    [
        FakeOOM("out of memory"),
        FakeCublasError(CUBLAS_ALLOC_FAILED),
        FakeCusolverError(CUSOLVER_ALLOC_FAILED),
        FakeRuntimeError(CUDA_RUNTIME_ALLOC),
    ],
    ids=[
        "OutOfMemoryError",
        "CUBLAS_ALLOC_FAILED",
        "CUSOLVER_ALLOC_FAILED",
        "cudaErrorMemoryAllocation",
    ],
)
def test_listed_oom_falls_back_once(
    gpu_engine: tuple[PySCFEngine, SimpleNamespace, list[bool]],
    test_set: dict[str, MolecularState],
    error: BaseException,
) -> None:
    """Each listed OOM: both pools freed once, one CPU run, gpu_oom recorded (never silent)."""
    eng, fake, calls = gpu_engine
    fake.raise_next = error
    result = eng.evaluate(test_set["water"], forces=False)
    assert calls == [True, False]
    assert result.device == "cpu" and result.device_reason == "gpu_oom"
    assert result.recovery_steps[0] == "gpu_oom->cpu"
    assert [pool.freed for pool in fake.pools] == [1, 1]


@pytest.mark.parametrize(
    "error",
    [
        FakeRuntimeError(700),
        FakeCublasError(13),
        FakeCusolverError(7),
        FakeDriverError(2),
    ],
    ids=["cuda-illegal-address", "cublas-execution-failed", "cusolver-internal", "driver-error"],
)
def test_other_gpu_errors_do_not_fall_back(
    gpu_engine: tuple[PySCFEngine, SimpleNamespace, list[bool]],
    test_set: dict[str, MolecularState],
    error: BaseException,
) -> None:
    """A CuPy/CUDA error that is not a listed allocation failure: EngineRuntimeError, no CPU run."""
    eng, fake, calls = gpu_engine
    fake.raise_next = error
    with pytest.raises(EngineRuntimeError, match="not an out-of-memory error") as info:
        eng.evaluate(test_set["water"], forces=False)
    assert calls == [True]
    assert info.value.__cause__ is error
    assert [pool.freed for pool in fake.pools] == [0, 0]


def test_is_gpu_oom_classification() -> None:
    """Exactly the four listed cases are OOM; other statuses and other types are not."""
    fake = fake_gpu()
    assert is_gpu_oom(fake, FakeOOM())
    assert is_gpu_oom(fake, FakeCublasError(CUBLAS_ALLOC_FAILED))
    assert is_gpu_oom(fake, FakeCusolverError(CUSOLVER_ALLOC_FAILED))
    assert is_gpu_oom(fake, FakeRuntimeError(CUDA_RUNTIME_ALLOC))
    for not_oom in (
        FakeCublasError(1),
        FakeCusolverError(3),
        FakeRuntimeError(700),
        FakeDriverError(2),
        MemoryError("host"),
        RuntimeError("other"),
    ):
        assert not is_gpu_oom(fake, not_oom), not_oom
    assert (CUDA_RUNTIME_ALLOC, CUBLAS_ALLOC_FAILED, CUSOLVER_ALLOC_FAILED) == (2, 3, 2)


@pytest.mark.parametrize(
    ("occ", "rotations"),
    [
        ([2.0, 0.0], 1),
        ([2.0, 2.0, 0.0, 0.0, 0.0], 6),
        ([[1.0, 0.0], [0.0, 0.0]], 1),
        ([[1.0, 1.0, 0.0], [1.0, 0.0, 0.0]], 2 + 2),
        ([2.0, 2.0, 2.0, 2.0, 2.0, 0.0, 0.0], 10),
    ],
    ids=["h2-rhf", "rhf-2x3", "h-atom-uhf", "uhf-2+2", "water-sto3g-rhf"],
)
def test_rotation_count(occ: Any, rotations: int) -> None:
    """n_rotations = nocc * nvir (RHF) or the per-spin sum (UHF), from mo_occ, before stability."""
    import numpy

    mf = SimpleNamespace(mo_occ=numpy.asarray(occ))
    assert PySCFEngine._rotation_count(mf) == rotations
    assert (rotations < GPU_STABILITY_MIN_ROTATIONS) is (rotations < 3)


def test_small_rotation_space_uses_cpu_copy_without_calling_gpu_stability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Below 3 rotations the GPU object's stability() is never called; a CPU copy's is."""
    import numpy

    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    eng = PySCFEngine.from_stage(stage(), device="cuda")
    calls: list[str] = []

    def gpu_stability(**kwargs: Any) -> Any:
        calls.append("gpu")
        raise AssertionError("nvar >= nroots")

    cpu_copy = SimpleNamespace(
        stability=lambda **kw: calls.append("cpu") or (None, None, True, None)
    )
    mf = SimpleNamespace(
        mo_occ=numpy.asarray([2.0, 0.0]), stability=gpu_stability, to_cpu=lambda: cpu_copy
    )
    steps: list[str] = ["diis"]
    eng._on_gpu = True
    try:
        eng._stability(mf, steps)
    finally:
        eng._on_gpu = False
    assert calls == ["cpu"]
    assert steps == ["diis", GPU_STABILITY_CPU_COPY_STEP, "stability:stable"]


def test_cuda_without_gpu_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """device='cuda' without GPU4PySCF / CuPy / a device names `uv sync --extra gpu`."""
    monkeypatch.setattr(engine_module, "gpu_modules", lambda: None)
    with pytest.raises(EngineUnavailableError, match=r"uv sync --extra gpu"):
        PySCFEngine.from_stage(stage(), device="cuda")


def test_auto_without_gpu_records_reason(
    monkeypatch: pytest.MonkeyPatch, test_set: dict[str, MolecularState]
) -> None:
    """device='auto' on a host without the GPU stack: CPU with gpu_unavailable; 'cpu': no reason."""
    monkeypatch.setattr(engine_module, "gpu_modules", lambda: None)
    auto = PySCFEngine.from_stage(stage(), device="auto").evaluate(test_set["water"], forces=False)
    assert auto.device == "cpu" and auto.device_reason == "gpu_unavailable"
    cpu = PySCFEngine.from_stage(stage(), device="cpu").evaluate(test_set["water"], forces=False)
    assert cpu.device == "cpu" and cpu.device_reason is None


def test_ddcosmo_always_cpu(
    monkeypatch: pytest.MonkeyPatch, test_set: dict[str, MolecularState]
) -> None:
    """DdCOSMO with a GPU present runs on CPU with ddcosmo_cpu_only (GPU never attempted)."""
    fake = fake_gpu()
    monkeypatch.setattr(engine_module, "gpu_modules", lambda: fake)
    real = PySCFEngine._run
    seen: list[bool] = []

    def run(self: PySCFEngine, state: MolecularState, st: StageConfig, **kw: Any) -> Any:
        seen.append(self._on_gpu)
        return real(self, state, st, **kw)

    monkeypatch.setattr(PySCFEngine, "_run", run)
    eng = PySCFEngine.from_stage(
        stage(solvation=Solvation(model="ddcosmo", solvent="water")), device="cuda"
    )
    result = eng.evaluate(test_set["water"], forces=False)
    assert result.device == "cpu" and result.device_reason == "ddcosmo_cpu_only"
    assert seen == [False]


def test_device_is_not_keyed(monkeypatch: pytest.MonkeyPatch) -> None:
    """cpu, auto and cuda engines have the same resolved stage."""
    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    stages = {
        PySCFEngine.from_stage(stage(), device=d).stage.model_dump_json()
        for d in ("cpu", "auto", "cuda")
    }
    assert len(stages) == 1


def test_engine_never_calls_probe_hardware(
    monkeypatch: pytest.MonkeyPatch, test_set: dict[str, MolecularState]
) -> None:
    """Neither construction nor evaluation calls probe_hardware (it would start a torch context)."""
    from eta_rxncat.utils import hw_probe

    def boom() -> None:
        raise AssertionError("probe_hardware called")

    monkeypatch.setattr(hw_probe, "probe_hardware", boom)
    monkeypatch.setattr(engine_module, "gpu_modules", fake_gpu)
    eng = PySCFEngine.from_stage(stage(), device="auto")
    eng.vram_budget_bytes = 1
    eng.evaluate(test_set["water"], forces=False)


def test_estimate_formula() -> None:
    """Estimate = f * 8 * (naux * nao(nao+1)/2 + 40 * nao^2) + overhead."""
    assert estimate_bytes(10, 50, safety=1.0, overhead=0) == 8 * (50 * 55 + 4000)
    assert estimate_bytes(24, 113) == int(VRAM_SAFETY * 8 * (113 * 300 + 40 * 576)) + (
        VRAM_OVERHEAD_BYTES
    )
    assert estimate_bytes(1, 0, safety=1.0, overhead=0) == 320


def test_calibration_record_matches_code() -> None:
    """Three entries; both constants equal the record's derived values; each estimate >= peak."""
    data = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert [e["system"] for e in data["entries"]] == ["water", "pd_anion", "decane"]
    assert data["VRAM_OVERHEAD_BYTES"] == VRAM_OVERHEAD_BYTES == 64 * 2**20
    worst = max(
        max(0.0, (e["measured_peak_bytes"] - VRAM_OVERHEAD_BYTES) / e["estimate_bytes_f1"])
        for e in data["entries"]
    )
    derived = max(1.0, math.ceil(worst * 1.25 * 100) / 100)
    assert data["VRAM_SAFETY"] == derived == VRAM_SAFETY
    for e in data["entries"]:
        assert e["estimate_bytes_f1"] == estimate_bytes(e["nao"], e["naux"], safety=1.0, overhead=0)
        assert estimate_bytes(e["nao"], e["naux"]) >= e["measured_peak_bytes"], e["system"]


def test_gpu_support_record_matches_code() -> None:
    """The record's analytic classes equal the classes it supports and the code constant (R44)."""
    data = json.loads(GPU_SUPPORT.read_text(encoding="utf-8"))
    ks_on = [r for r in data["rows"] if r["xc"] != "hf" and r["grid_response"]]
    ks_off = [r for r in data["rows"] if r["xc"] != "hf" and not r["grid_response"]]
    recorded = frozenset(tuple(c) for c in data["routing"]["analytic_classes"])
    assert recorded == classes_from_record(data["rows"]) == GPU_ANALYTIC_KS_HESSIAN_CLASSES
    assert GPU_KS_HESSIAN_GRID_RESPONSE is True
    assert data["verdict"]["GPU_KS_ANALYTIC_HESSIAN_OK"] is (
        all(r["max_abs_analytic_minus_fd"] <= 1e-4 for r in ks_on)
    )
    assert max(r["max_abs_analytic_minus_fd"] for r in ks_off) > 1e-2  # grid response off fails
    cases = {r["case"] for r in ks_on}
    assert {"water", "hcl", "hbr", "hi", "hydroxyl-uks", "water-pcm", "water-nodf"} <= cases
    assert {r["grid"] for r in ks_on if r["case"] in {"water", "hcl", "hbr", "hi"}} == {3, 9}


def test_decane_geometry() -> None:
    """The committed n-decane calibration geometry: C10H22, neutral singlet."""
    from collections import Counter

    from conftest import load_case

    decane = load_case("decane")
    assert Counter(decane.symbols) == {"C": 10, "H": 22}
    assert (decane.charge, decane.spin_multiplicity) == (0, 1)


# ---------------------------------------------------------------- real GPU


@pytest.fixture(scope="module")
def gpu() -> SimpleNamespace:
    """The real GPU modules; a gpu-marked test without them fails (no skip, R8/R32)."""
    found = gpu_module.gpu_modules()
    assert found is not None, "gpu tests need .venv-accept-gpu with a CUDA device"
    return found


def b3lyp(device: str, **kwargs: Any) -> PySCFEngine:
    """B3LYP/def2-SVP on ``device``."""
    return PySCFEngine.from_stage(stage("b3lyp", "def2-svp", **kwargs), device=device)


def converged_mf(eng: PySCFEngine, state: MolecularState, on_gpu: bool) -> Any:
    """Run the engine's own ladder + stability on one device and return the mean field."""
    st = eng.resolved_stage_for(state)
    eng._on_gpu = on_gpu
    try:
        mol = eng._build_mol(state, str(st.basis), str(st.options["ecp"]))
        mf, steps = eng._ladder(state, mol, st)
        return eng._stability(mf, steps), st, mol
    finally:
        eng._on_gpu = False


@pytest.mark.gpu
@pytest.mark.parametrize("case", ["water", "hydroxide", "hydroxyl", "pd_anion"])
def test_gpu_cpu_energy_agreement(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState], case: str
) -> None:
    """|E_gpu - E_cpu| <= 1e-6 Eh, both stable, GPU really on cuda; values recorded in output."""
    s = test_set[case]
    on_gpu = b3lyp("cuda").evaluate(s, forces=False)
    on_cpu = b3lyp("cpu").evaluate(s, forces=False)
    print(
        f"{case}: E_gpu {on_gpu.energy_hartree!r} E_cpu {on_cpu.energy_hartree!r} "
        f"|dE| {abs(on_gpu.energy_hartree - on_cpu.energy_hartree):.3e}"
    )
    assert on_gpu.device == "cuda" and on_gpu.device_reason == f"gpu4pyscf {gpu.version}"
    assert on_cpu.device == "cpu"
    assert "gpu_oom->cpu" not in on_gpu.recovery_steps
    assert on_gpu.recovery_steps[-1] == on_cpu.recovery_steps[-1] == "stability:stable"
    assert abs(on_gpu.energy_hartree - on_cpu.energy_hartree) <= 1e-6


@pytest.mark.gpu
@pytest.mark.parametrize("case", ["water", "hydroxide", "hydroxyl", "pd_anion"])
def test_cross_evaluation(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState], case: str
) -> None:
    """The CPU energy functional evaluated at the GPU density equals E_gpu within 1e-8 Eh."""
    s = test_set[case]
    eng = b3lyp("cuda")
    mf_gpu, st, mol = converged_mf(eng, s, on_gpu=True)
    assert type(mf_gpu).__module__.startswith("gpu4pyscf")
    dm = to_host(mf_gpu.make_rdm1())
    mf_cpu = eng._make_mf(mol, st)
    assert not type(mf_cpu).__module__.startswith("gpu4pyscf")
    e_cross = float(mf_cpu.energy_tot(dm=dm))
    print(f"{case}: E_gpu {float(mf_gpu.e_tot)!r} E_cpu(dm_gpu) {e_cross!r}")
    assert abs(e_cross - float(mf_gpu.e_tot)) <= 1e-8


@pytest.mark.gpu
@pytest.mark.parametrize("case", ["water", "hydroxyl"])
def test_gpu_cpu_gradient_agreement(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState], case: str
) -> None:
    """GPU forces equal CPU forces to <= 1e-6 Eh/Bohr."""
    s = test_set[case]
    f_gpu = b3lyp("cuda").evaluate(s).forces_hartree_per_bohr
    f_cpu = b3lyp("cpu").evaluate(s).forces_hartree_per_bohr
    assert f_gpu is not None and f_cpu is not None
    diff = max(
        abs(a - b) for ra, rb in zip(f_gpu, f_cpu, strict=True) for a, b in zip(ra, rb, strict=True)
    )
    print(f"{case}: max |F_gpu - F_cpu| = {diff:.3e}")
    assert diff <= 1e-6


@pytest.mark.gpu
def test_gpu_hessians(gpu: SimpleNamespace, test_set: dict[str, MolecularState]) -> None:
    """Water: HF analytic GPU vs CPU <= 1e-5; B3LYP GPU analytic vs CPU FD <= 1e-4."""
    water = test_set["water"]
    hf_gpu = PySCFEngine.from_stage(stage("hf", "def2-svp"), device="cuda").evaluate(
        water, hessian=True
    )
    hf_cpu = PySCFEngine.from_stage(stage("hf", "def2-svp"), device="cpu").evaluate(
        water, hessian=True
    )
    assert hf_gpu.device == "cuda" and hf_gpu.hessian_method == hf_cpu.hessian_method == "analytic"
    ks_gpu = b3lyp("cuda").evaluate(water, hessian=True)
    ks_cpu = b3lyp("cpu").evaluate(water, hessian=True)
    assert ks_gpu.device == "cuda"
    assert ks_gpu.hessian_method == "analytic" and ks_cpu.hessian_method == "finite_difference"

    def gap(a: Any, b: Any) -> float:
        return max(
            abs(x - y) for ra, rb in zip(a, b, strict=True) for x, y in zip(ra, rb, strict=True)
        )

    hf_gap = gap(hf_gpu.hessian_hartree_per_bohr2, hf_cpu.hessian_hartree_per_bohr2)
    ks_gap = gap(ks_gpu.hessian_hartree_per_bohr2, ks_cpu.hessian_hartree_per_bohr2)
    print(f"water Hessian GPU vs CPU: HF {hf_gap:.3e}, B3LYP {ks_gap:.3e}")
    assert hf_gap <= 1e-5 and ks_gap <= 1e-4
    h = ks_gpu.hessian_hartree_per_bohr2
    assert h is not None and all(h[i][j] == h[j][i] for i in range(9) for j in range(9))


@pytest.mark.gpu
@pytest.mark.parametrize("method", ["C-PCM", "IEF-PCM"])
def test_gpu_cpu_pcm_agreement(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState], method: str
) -> None:
    """Water C-PCM / IEF-PCM: GPU vs CPU <= 1e-6 Eh, the GPU run on cuda."""
    kwargs: dict[str, Any] = {
        "solvation": Solvation(model="pcm", solvent="water"),
        "options": {"pcm_method": method},
    }
    e_gpu = b3lyp("cuda", **kwargs).evaluate(test_set["water"], forces=False)
    e_cpu = b3lyp("cpu", **kwargs).evaluate(test_set["water"], forces=False)
    print(f"water {method}: |dE| {abs(e_gpu.energy_hartree - e_cpu.energy_hartree):.3e}")
    assert e_gpu.device == "cuda"
    assert abs(e_gpu.energy_hartree - e_cpu.energy_hartree) <= 1e-6


@pytest.mark.gpu
def test_gpu_ddcosmo_auto_runs_on_cpu(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState]
) -> None:
    """DdCOSMO with device='auto' on the GPU host -> cpu, ddcosmo_cpu_only."""
    eng = PySCFEngine.from_stage(
        stage(solvation=Solvation(model="ddcosmo", solvent="water")), device="auto"
    )
    result = eng.evaluate(test_set["water"], forces=False)
    assert result.device == "cpu" and result.device_reason == "ddcosmo_cpu_only"


@pytest.mark.gpu
def test_gpu_engine_imports_no_torch(gpu: SimpleNamespace) -> None:
    """Importing and running the GPU path loads no torch (subprocess, fresh interpreter)."""
    code = (
        "import sys\n"
        "import eta_rxncat.engines.pyscf_gpu_cpu\n"
        "assert 'torch' not in sys.modules, 'import'\n"
        "from eta_rxncat.core import MolecularState, StageConfig\n"
        "from eta_rxncat.engines import PySCFEngine\n"
        "s = MolecularState(symbols=['H', 'H'], coordinates=[[0, 0, 0], [0, 0, 0.74]],\n"
        "                   charge=0, spin_multiplicity=1)\n"
        "st = StageConfig(kind='single_point', engine='pyscf_gpu_cpu', method='hf',\n"
        "                 basis='sto-3g')\n"
        "r = PySCFEngine.from_stage(st, device='cuda').evaluate(s)\n"
        "assert r.device == 'cuda', r.device\n"
        "assert 'torch' not in sys.modules, 'evaluate'\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]


@pytest.mark.gpu
def test_gpu_decane_under_budget_runs_on_gpu(gpu: SimpleNamespace) -> None:
    """R42: decane's calibrated estimate is under the budget, so it really runs on cuda."""
    from conftest import load_case

    decane = load_case("decane")
    eng = b3lyp("cuda")
    st = eng.resolved_stage_for(decane)
    mol = eng._build_mol(decane, str(st.basis), str(st.options["ecp"]))
    estimate = eng.estimate_vram_bytes(mol, st)
    assert eng.vram_budget_bytes is not None and estimate < eng.vram_budget_bytes
    result = eng.evaluate(decane, forces=False)
    print(
        f"decane: estimate {estimate} B, budget {eng.vram_budget_bytes} B, "
        f"E {result.energy_hartree!r}"
    )
    assert result.device == "cuda" and "vram_estimate>budget->cpu" not in result.recovery_steps


@pytest.mark.gpu
@pytest.mark.parametrize("method", ["hf", "b3lyp"])
def test_gpu_tiny_system_stability(gpu: SimpleNamespace, method: str) -> None:
    """R43: H2/sto-3g on cuda -> stable, the cpu_copy record present, energy = CPU (<= 1e-6)."""
    h2 = MolecularState(
        symbols=["H", "H"],
        coordinates=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.74]],
        charge=0,
        spin_multiplicity=1,
    )
    on_gpu = PySCFEngine.from_stage(stage(method), device="cuda").evaluate(h2)
    on_cpu = PySCFEngine.from_stage(stage(method), device="cpu").evaluate(h2)
    assert on_gpu.device == "cuda"
    assert on_gpu.recovery_steps == ["diis", GPU_STABILITY_CPU_COPY_STEP, "stability:stable"]
    assert GPU_STABILITY_CPU_COPY_STEP not in on_cpu.recovery_steps
    print(f"H2 {method}: E_gpu {on_gpu.energy_hartree!r} E_cpu {on_cpu.energy_hartree!r}")
    assert abs(on_gpu.energy_hartree - on_cpu.energy_hartree) <= 1e-6


@pytest.mark.gpu
def test_gpu_water_has_no_cpu_copy(
    gpu: SimpleNamespace, test_set: dict[str, MolecularState]
) -> None:
    """Water has enough rotations: its GPU stability analysis runs on the GPU (no cpu_copy)."""
    result = PySCFEngine.from_stage(stage(), device="cuda").evaluate(test_set["water"])
    assert result.device == "cuda"
    assert result.recovery_steps == ["diis", "stability:stable"]
