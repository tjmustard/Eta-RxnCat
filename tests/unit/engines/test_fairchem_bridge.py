"""Default-suite tests for the fairchem bridge (slice 10): no weights, no torch, fakes only."""

import logging
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from eta_rxncat.core import MolecularState, Solvation, StageConfig
from eta_rxncat.engines import (
    ENGINE_IMPL_KEY,
    EngineInputError,
    EngineUnavailableError,
    ESENOMol25Engine,
    UMADirectEngine,
)
from eta_rxncat.engines import _fairchem_bridge as bridge
from eta_rxncat.engines._fairchem_bridge import FairchemEngine

ENGINES = {"uma_direct": UMADirectEngine, "esen_omol25": ESENOMol25Engine}
METHODS = {"uma_direct": "uma-s-1p2p1", "esen_omol25": "esen-sm-conserving-all-omol"}
REPO = Path(__file__).resolve().parents[3]
SENTINEL = "hf_SENTINEL_do_not_print"


def stage(tag: str, **kwargs: Any) -> StageConfig:
    """A single point for ``tag`` with its approved method unless overridden."""
    data: dict[str, Any] = {"kind": "single_point", "engine": tag, "method": METHODS[tag]}
    data.update(kwargs)
    return StageConfig(**data)


class FakeUnit:
    """A predict unit that records the batch it receives and returns fixed values."""

    def __init__(self, direct: bool = False, tasks: tuple[str, ...] = ("omol",)) -> None:
        """Configure the direct-forces flag and the task list."""
        self.inference_settings = SimpleNamespace(base_precision_dtype="torch.float32")
        self.model = SimpleNamespace(
            module=SimpleNamespace(
                backbone=SimpleNamespace(regress_config=SimpleNamespace(direct_forces=direct))
            )
        )
        self.dataset_to_tasks = {t: [] for t in tasks}
        self.batches: list[dict[str, Any]] = []

    def predict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Record ``data`` and return energy -1 eV and zero forces."""
        self.batches.append(data)
        n = len(data["atomic_numbers"])
        energy = SimpleNamespace(
            detach=lambda: SimpleNamespace(
                cpu=lambda: SimpleNamespace(reshape=lambda *a: [SimpleNamespace(item=lambda: -1.0)])
            )
        )
        forces = SimpleNamespace(
            detach=lambda: SimpleNamespace(
                cpu=lambda: SimpleNamespace(tolist=lambda: [[0.0, 0.0, 0.0]] * n)
            )
        )
        return {"energy": energy, "forces": forces}


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """Weights and refs as tmp files; the loader returns a FakeUnit; AtomicData is the fields."""
    checkpoint = tmp_path / "model.pt"
    checkpoint.write_bytes(b"fake checkpoint")
    atom_refs = tmp_path / "iso_atom_elem_refs.yaml"
    atom_refs.write_text("H: -13.6\n")
    form_refs = tmp_path / "form_elem_refs.yaml"
    form_refs.write_text("refs:\n  H: -1.0\n")
    state: dict[str, Any] = {"unit": FakeUnit(), "loads": 0}

    def resolve(self: FairchemEngine, path: Any, a: Any, f: Any) -> tuple[Path, Path, Path | None]:
        return (
            Path(path) if path else checkpoint,
            Path(a) if a else atom_refs,
            (Path(f) if f else form_refs) if self.tag == "uma_direct" else None,
        )

    def load_unit(self: FairchemEngine, *args: Any) -> tuple[Any, str]:
        state["loads"] += 1
        return state["unit"], "cpu"

    monkeypatch.setattr(FairchemEngine, "_resolve", resolve)
    monkeypatch.setattr(FairchemEngine, "_load_unit", load_unit)
    monkeypatch.setattr(FairchemEngine, "_atomic_data", lambda self, fields: fields)
    monkeypatch.setattr(bridge, "library_version", lambda dist: "2.26.0")
    state.update(checkpoint=checkpoint, atom_refs=atom_refs, form_refs=form_refs)
    return state


# ---------------------------------------------------------------- methods and stages


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_unknown_method_refused(fake: dict[str, Any], tag: str) -> None:
    """Any method but the approved one is EngineInputError, per tag."""
    with pytest.raises(EngineInputError, match="is not"):
        ENGINES[tag].from_stage(stage(tag, method="uma-m-1p1"))


def test_uma_refuses_esen_method(fake: dict[str, Any]) -> None:
    """uma_direct never runs the eSEN checkpoint, and esen_omol25 never runs UMA."""
    with pytest.raises(EngineInputError, match="not 'uma-s-1p2p1'"):
        UMADirectEngine.from_stage(stage("uma_direct", method="esen-sm-conserving-all-omol"))
    with pytest.raises(EngineInputError, match="not 'esen-sm-conserving-all-omol'"):
        ESENOMol25Engine.from_stage(stage("esen_omol25", method="uma-s-1p2p1"))


@pytest.mark.parametrize(
    "method", ["esen-sm-direct-all-omol", "esen-md-direct-all-omol", "allscaip-md-direct-all-omol"]
)
def test_direct_force_names_refused(fake: dict[str, Any], method: str) -> None:
    """Direct-force OMol25 names are refused by name, before any load."""
    with pytest.raises(EngineInputError, match=f"{method}: direct-force checkpoint"):
        ESENOMol25Engine.from_stage(stage("esen_omol25", method=method))
    assert fake["loads"] == 0


def test_allscaip_conserving_not_approved(fake: dict[str, Any]) -> None:
    """allscaip-md-conserving-all-omol is refused as not approved."""
    with pytest.raises(
        EngineInputError,
        match=r"not approved \(TJ 16:52Z approved esen-sm-conserving-all-omol only\)",
    ):
        ESENOMol25Engine.from_stage(stage("esen_omol25", method="allscaip-md-conserving-all-omol"))


def test_foreign_tag_stage_refused(fake: dict[str, Any]) -> None:
    """ESEN given a uma_direct stage (and vice versa) is EngineInputError."""
    with pytest.raises(EngineInputError, match="runs engine 'esen_omol25', not 'uma_direct'"):
        ESENOMol25Engine.from_stage(stage("uma_direct"))
    with pytest.raises(EngineInputError, match="runs engine 'uma_direct', not 'esen_omol25'"):
        UMADirectEngine.from_stage(stage("esen_omol25"))


@pytest.mark.parametrize("tag", sorted(ENGINES))
@pytest.mark.parametrize(
    ("options", "match"),
    [
        ({"task": "omat"}, "task"),
        ({"inference_settings": "default"}, "inference_settings"),
        ({"inference_settings": "nitro"}, "inference_settings"),
        ({"fd_step_bohr": 0.0}, "fd_step_bohr"),
        ({"atom_refs_sha256": "0" * 64}, "derived"),
        ({"form_elem_refs_sha256": "none"}, "derived"),
        ({"nope": 1}, "nope"),
    ],
)
def test_bad_options_refused(
    fake: dict[str, Any], tag: str, options: dict[str, Any], match: str
) -> None:
    """Only task omol and high-precision; derived sha options cannot be set by the caller."""
    with pytest.raises(EngineInputError, match=match):
        ENGINES[tag].from_stage(stage(tag, options=options))


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_bad_runtime_refused(fake: dict[str, Any], tag: str) -> None:
    """An unknown device or runtime argument is EngineInputError."""
    with pytest.raises(EngineInputError, match="tpu"):
        ENGINES[tag].from_stage(stage(tag), device="tpu")
    with pytest.raises(EngineInputError, match="threads"):
        ENGINES[tag].from_stage(stage(tag), threads=2)


def test_solvation_rejected_by_core() -> None:
    """No implicit solvation reaches the fairchem engines (core pairs models with engines)."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="needs engine"):
        stage("uma_direct", solvation=Solvation(model="pcm", dielectric=10.0))


# ---------------------------------------------------------------- keys, identity, refs


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_resolved_options_and_identity(fake: dict[str, Any], tag: str) -> None:
    """Defaults plus the derived reference hashes; identity is <method>@sha256 of the file."""
    import hashlib

    eng = ENGINES[tag].from_stage(stage(tag))
    opts = eng.stage.options
    assert (
        opts["task"],
        opts["inference_settings"],
        opts["fd_step_bohr"],
        opts[ENGINE_IMPL_KEY],
    ) == ("omol", "high-precision", 0.005, 1)
    assert opts["atom_refs_sha256"] == hashlib.sha256(fake["atom_refs"].read_bytes()).hexdigest()
    expected_form = (
        hashlib.sha256(fake["form_refs"].read_bytes()).hexdigest()
        if tag == "uma_direct"
        else "none"
    )
    assert opts["form_elem_refs_sha256"] == expected_form
    digest = hashlib.sha256(fake["checkpoint"].read_bytes()).hexdigest()
    assert eng.identity.model == f"{METHODS[tag]}@sha256:{digest}"
    assert re.fullmatch(
        rf"{re.escape(METHODS[tag])}@sha256:[0-9a-f]{{64}}", eng.identity.model or ""
    )
    assert (eng.identity.name, eng.identity.version) == (tag, "2.26.0")


def test_refs_change_the_key(
    fake: dict[str, Any], tmp_path: Path, test_set: dict[str, MolecularState]
) -> None:
    """An edited atom_refs file (test hook) changes the derived sha and so the cache key."""
    from eta_rxncat.store import build_stage_key

    edited = tmp_path / "edited.yaml"
    edited.write_text("H: -13.5\n")
    base = UMADirectEngine.from_stage(stage("uma_direct"))
    changed = UMADirectEngine.from_stage(stage("uma_direct"), atom_refs_path=edited)
    water = test_set["water"]
    assert build_stage_key(water, base.stage, base.identity) != build_stage_key(
        water, changed.stage, changed.identity
    )


# ---------------------------------------------------------------- loading and batches


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_direct_force_unit_refused_after_load(fake: dict[str, Any], tag: str) -> None:
    """A loaded model whose regress_config.direct_forces is true is refused."""
    fake["unit"] = FakeUnit(direct=True)
    with pytest.raises(
        EngineInputError, match=f"{METHODS[tag]}: direct-force checkpoint; forces are not -dE/dx"
    ):
        ENGINES[tag].from_stage(stage(tag))


def test_missing_task_refused(fake: dict[str, Any]) -> None:
    """A loaded model without the omol task is refused."""
    fake["unit"] = FakeUnit(tasks=("omat",))
    with pytest.raises(EngineInputError, match="no 'omol' task"):
        UMADirectEngine.from_stage(stage("uma_direct"))


@pytest.mark.parametrize("tag", sorted(ENGINES))
@pytest.mark.parametrize(
    ("case", "charge", "spin"),
    [("water", 0, 1), ("hydroxide", -1, 1), ("hydroxyl", 0, 2), ("pd_anion", -1, 1)],
)
def test_batch_charge_and_spin(
    fake: dict[str, Any],
    test_set: dict[str, MolecularState],
    tag: str,
    case: str,
    charge: int,
    spin: int,
) -> None:
    """The batch carries charge = state.charge and spin = the multiplicity, task omol."""
    eng = ENGINES[tag].from_stage(stage(tag))
    result = eng.evaluate(test_set[case])
    batch = fake["unit"].batches[-1]
    assert (batch["charge"], batch["spin"], batch["dataset"]) == (charge, spin, "omol")
    assert batch["positions"] == test_set[case].coordinates
    assert result.recovery_steps == ["fairchem_dtype:float32"]
    assert result.device == "cpu"


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_no_weights(monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    """Neither cache nor checkpoint_path: EngineUnavailableError with the provisioning text."""

    def missing(entry: Any, subfolder: str, filename: str) -> Path:
        raise FileNotFoundError(filename)

    monkeypatch.setattr(
        bridge,
        "_registry",
        lambda name: {
            "subfolder": "checkpoints",
            "filename": "x.pt",
            "atom_refs": None,
            "form_elem_refs": None,
        },
    )
    monkeypatch.setattr(bridge, "_cached", missing)
    with pytest.raises(
        EngineUnavailableError,
        match=re.escape(
            f"no {tag} weights: provision via HF login (TJ Q3 A) or pass checkpoint_path (Q3 B)"
        ),
    ):
        ENGINES[tag].from_stage(stage(tag))
    with pytest.raises(EngineUnavailableError, match=f"no {tag} weights"):
        ENGINES[tag].from_stage(stage(tag), checkpoint_path="/nonexistent/model.pt")


@pytest.mark.parametrize("tag", sorted(ENGINES))
def test_token_never_appears(
    fake: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    test_set: dict[str, MolecularState],
    tag: str,
) -> None:
    """With HF_TOKEN set to a sentinel, no error, log or result repr contains it."""
    monkeypatch.setenv("HF_TOKEN", SENTINEL)
    caplog.set_level(logging.DEBUG)
    texts: list[str] = []
    eng = ENGINES[tag].from_stage(stage(tag))
    texts.append(repr(eng.evaluate(test_set["water"])))
    texts.append(repr(eng.identity) + repr(eng.stage))
    for bad in ({"method": "nope"}, {"options": {"task": "omat"}}):
        with pytest.raises(EngineInputError) as info:
            ENGINES[tag].from_stage(stage(tag, **bad))
        texts.append(str(info.value))
    texts.append(caplog.text)
    assert not any(SENTINEL in text for text in texts)


def test_committed_records_hold_no_token() -> None:
    """No committed evidence, inventory or test data contains an HF token (hf_ + 16+ chars)."""
    token = re.compile(r"hf_[A-Za-z0-9]{16,}")
    roots = [REPO / "docs", REPO / "tests/unit/engines/data"]
    hits = [
        str(path)
        for root in roots
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".json", ".log", ".txt", ".xyz", ".yaml"}
        and token.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert hits == []
