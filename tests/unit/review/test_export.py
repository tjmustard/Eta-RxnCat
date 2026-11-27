"""``export_run_data`` (v0.7.0, slice 07; R12, R15, R18): stub rows and rows of the real runners."""

import getpass
import json
import math
import socket
from pathlib import Path

import pydantic
import pytest
from review_helpers import (
    ENGINE,
    H2,
    HOSTILE,
    SECRET,
    frames,
    put,
    stretch_hessian,
    stub_keys,
    stub_record,
)

from eta_rxncat.core import ThermoAnalysisOptions
from eta_rxncat.review import (
    RunData,
    RunRecord,
    canonical_run_data_json,
    export_run_data,
)
from eta_rxncat.review.export import ExportBudgetError, ExportError
from eta_rxncat.review.run_data import TrajectoryEntry
from eta_rxncat.store import ArtifactStore
from eta_rxncat.thermo import normal_modes


def export(path: Path, record: RunRecord | None = None, budget: int | None = None) -> RunData:
    """Export ``record`` from the store at ``path``."""
    with ArtifactStore(path) as store:
        return export_run_data(record or stub_record(), store, trajectory_byte_budget=budget)


@pytest.fixture
def path(tmp_path: Path) -> Path:
    """A stub store."""
    path = tmp_path / "stub.sqlite"
    put(path, {})
    return path


def by_kind(data: RunData, kind: str) -> TrajectoryEntry:
    """Return the one trajectory of ``kind``."""
    (entry,) = [t for t in data.trajectories if t.kind == kind]
    return entry


def test_two_exports_are_byte_identical(path: Path) -> None:
    """Requirement 4: the same record and store give the same bytes."""
    assert canonical_run_data_json(export(path)) == canonical_run_data_json(export(path))


def test_no_message_path_host_or_user_is_exported(path: Path, tmp_path: Path) -> None:
    """R15: no message, absolute path, host or user name leaves a row."""
    text = canonical_run_data_json(export(path)).decode("ascii")
    for secret in (SECRET, "failed in", str(tmp_path), str(Path.home()), "message"):
        assert secret not in text
    assert socket.gethostname() not in text
    assert f"/{getpass.getuser()}/" not in text
    assert '"store_file_name":"stub.sqlite"' in text


def test_missing_rows_are_exported_as_missing_and_never_computed(path: Path) -> None:
    """A row the store lacks is ``missing`` and stays absent."""
    data = export(path)
    gone = stub_keys()["gone"].key
    (missing,) = [f for f in data.frequencies if f.status == "missing"]
    assert missing.stage_key == gone
    assert set(missing.model_dump()) == {"status", "frequency_id", "species_id", "stage_key"}
    assert gone in {k.stage_key for k in data.provenance.stage_keys}
    with ArtifactStore(path) as store:
        assert len(store.query()) == 4  # the export wrote nothing


def test_an_empty_store_exports_every_row_as_missing(tmp_path: Path) -> None:
    """Nothing is computed from an empty store."""
    record = stub_record()
    data = export(tmp_path / "empty.sqlite", record)
    assert {t.status for t in data.trajectories} == {"missing"}
    assert {f.status for f in data.frequencies} == {"missing"}


def test_candidate_fields_come_from_the_record(path: Path) -> None:
    """The candidate entry carries the record's values and ids."""
    (candidate,) = export(path).candidates
    assert candidate.template_rank_used == 2
    assert candidate.graft_rmsd_angstrom == 0.05
    assert [(r.template_id, r.reason_code) for r in candidate.graft_refusals] == [
        ("t1", "alignment_rmsd")
    ]
    assert candidate.dG_dagger_kcal_mol == 12.5
    assert candidate.ddG_dagger_kcal_mol == 1.5
    assert (candidate.charge, candidate.spin_multiplicity) == (0, 1)
    (member,) = candidate.members
    assert member.weight_fraction == 1.0
    assert member.frequency_id in candidate.frequency_ids
    assert len(member.trajectory_ids) == 2
    assert len(candidate.frequency_ids) == 2
    assert len(candidate.endpoint_trajectory_ids) == 1


def test_a_stored_failure_keeps_its_code_and_frames(path: Path) -> None:
    """A failure row exports its code and frames."""
    search = by_kind(export(path), "ts_search")
    assert search.status == "stored"
    assert search.convergence.converged_bool is False
    assert search.convergence.failed_code == "ts_search_failed:max_steps"
    assert search.n_frames_total == len(search.frames) == 12


def test_a_converged_optimization_carries_its_convergence_data(path: Path) -> None:
    """A converged row exports its numbers."""
    relax = by_kind(export(path), "pre_relax")
    assert relax.status == "stored"
    assert relax.convergence.converged_bool is True
    assert relax.convergence.n_steps == 12
    assert relax.convergence.final_energy_hartree == -1.1
    assert [f.accepted_bool for f in relax.frames[:3]] == [True, False, True]


def test_a_known_imaginary_mode_is_counted_and_normalised(path: Path) -> None:
    """Requirement 5: one imaginary stretch, unit displacement."""
    (frequency,) = [f for f in export(path).frequencies if f.status == "completed"]
    expected = normal_modes(
        H2.symbols, H2.coordinates, stretch_hessian(), analysis=ThermoAnalysisOptions()
    )
    assert frequency.frequencies_cm1 == list(expected.frequencies_cm1)
    assert frequency.n_imaginary == 1
    assert frequency.imag_tol_cm1 == 20.0
    (mode,) = frequency.imaginary_modes
    assert mode.frequency_cm1 < -20.0
    first, second = mode.displacements_angstrom
    assert abs(first[0]) == pytest.approx(2**-0.5)
    assert second[0] == pytest.approx(-first[0])
    assert max((c for row in mode.displacements_angstrom for c in row), key=abs) > 0
    # The full-precision geometry of an optimization row would be used; here there is none, so
    # the row's own grid geometry is.
    assert frequency.coordinates_angstrom[1][0] == 1.2


def test_the_full_precision_geometry_of_the_optimization_is_used(path: Path) -> None:
    """The unrounded geometry of the matching row is used."""
    record = stub_record()
    endpoint = (
        record.runs[0].endpoints[0].model_copy(update={"frequency_keys": [stub_keys()["freq"].key]})
    )
    run = record.runs[0].model_copy(
        update={"endpoints": [endpoint], "samples": [], "ensemble": None}
    )
    data = export(path, record.model_copy(update={"runs": [run]}))
    (frequency,) = data.frequencies
    assert frequency.status == "completed"
    assert frequency.coordinates_angstrom == H2.coordinates


def test_decimation_keeps_the_count_and_respects_the_budget(tmp_path: Path) -> None:
    """Requirement 6: full count kept, bytes within the budget."""
    path = tmp_path / "long.sqlite"
    put(path, {}, n_frames=40)
    full = export(path)
    size = trajectories_size(full)
    assert {t.decimation_stride for t in full.trajectories} == {1}
    budget = size // 3
    data = export(path, budget=budget)
    assert trajectories_size(data) <= budget
    long = by_kind(data, "pre_relax")
    assert long.n_frames_total == 40
    assert long.decimation_stride > 1
    assert len(long.frames) < 40
    assert long.frames[-1] == by_kind(full, "pre_relax").frames[-1]
    assert long.frames[1] == by_kind(full, "pre_relax").frames[long.decimation_stride]
    # A trajectory too short to lose a frame is untouched.
    assert by_kind(data, "endpoint_opt").n_frames_total == 3
    # The budget is tight: the next smaller stride would not have fitted.
    looser = export(path, budget=size)
    assert {t.decimation_stride for t in looser.trajectories} == {1}


def trajectories_size(data: RunData) -> int:
    """The canonical bytes of the trajectories array."""
    document = canonical_run_data_json(data)
    start = document.index(b'"trajectories":') + len(b'"trajectories":')
    return len(document) - start - 1  # ``trajectories`` is the last key


def test_an_impossible_budget_is_refused(path: Path) -> None:
    """A budget below first-and-last frames is an error."""
    with pytest.raises(ExportBudgetError):
        export(path, budget=10)


def test_a_record_that_names_an_unknown_species_is_refused(path: Path) -> None:
    """An undeclared species is an error."""
    record = stub_record()
    run = record.runs[0].model_copy(update={"species_id": "nobody"})
    with pytest.raises(ExportError, match="nobody"):
        export(path, record.model_copy(update={"runs": [run]}))


def test_a_member_without_a_sample_is_refused(path: Path) -> None:
    """A summed member needs its rows in the record."""
    record = stub_record()
    run = record.runs[0].model_copy(update={"samples": []})
    with pytest.raises(ExportError, match="has no sample"):
        export(path, record.model_copy(update={"runs": [run]}))


def test_a_message_posing_as_a_reason_code_is_refused(tmp_path: Path) -> None:
    """Text with spaces or slashes cannot be a code."""
    path = tmp_path / "s.sqlite"
    put(path, {"ts": ("ts", {"failed_reason": f"boom in {SECRET}", "frames": frames(1)})})
    with pytest.raises(ValueError, match="pattern"):
        export(path)


def test_an_engine_model_that_is_a_path_is_refused(path: Path) -> None:
    """A model identity must not be a path."""
    record = stub_record()
    engine = ENGINE.model_copy(update={"model": SECRET})
    run = record.runs[0].model_copy(update={"engine": engine})
    with pytest.raises(ValueError, match="file path"):
        export(path, record.model_copy(update={"runs": [run], "gates": []}))


def test_a_row_shared_by_two_samples_is_one_entry(path: Path) -> None:
    """Two samples at one geometry share their rows without an error."""
    record = stub_record()
    run = record.runs[0]
    twin = run.samples[0].model_copy(update={"sample_index": 2, "source": "perturb:1"})
    run = run.model_copy(update={"samples": [*run.samples, twin]})
    data = export(path, record.model_copy(update={"runs": [run]}))
    assert len(data.trajectories) == 3
    assert by_kind(data, "ts_search").label.endswith(":seed")


def test_a_record_round_trips_through_json() -> None:
    """The record survives its JSON form."""
    record = stub_record(label=HOSTILE)
    assert RunRecord.model_validate_json(record.model_dump_json()) == record


def infinite_ratio_record() -> RunRecord:
    """The stub record with an infinite selectivity ratio."""
    data = stub_record().model_dump()
    data["selectivity"][0]["result"]["ratio"] = math.inf
    return RunRecord.model_validate(data)


@pytest.mark.parametrize("indent", [None, 1])
def test_an_infinite_ratio_round_trips_as_the_string_infinity(indent: int | None) -> None:
    """``ratio = inf`` is written as ``"Infinity"`` and read back as ``inf`` (v0.7.1 R38)."""
    record = infinite_ratio_record()
    text = record.model_dump_json(indent=indent)
    assert json.loads(text)["selectivity"][0]["result"]["ratio"] == "Infinity"
    read = RunRecord.model_validate_json(text)
    assert read == record
    assert read.selectivity[0].result.ratio == math.inf
    assert record.model_dump()["selectivity"][0]["result"]["ratio"] == math.inf


def float_paths(node: object, path: tuple[str | int, ...] = ()) -> list[tuple[str | int, ...]]:
    """The path of every float in a parsed JSON document."""
    if isinstance(node, float):
        return [path]
    items = (
        node.items()
        if isinstance(node, dict)
        else enumerate(node)
        if isinstance(node, list)
        else ()
    )
    return [found for key, child in items for found in float_paths(child, (*path, key))]


@pytest.mark.parametrize("bad", [math.nan, "NaN"], ids=["literal", "string"])
def test_a_nan_anywhere_in_a_record_is_refused(bad: float | str) -> None:
    """Every number of the record, the nested ratio included, refuses NaN."""
    text = infinite_ratio_record().model_dump_json()
    document = json.loads(text)
    paths = [("selectivity", 0, "result", "ratio"), *float_paths(document)]
    assert len(paths) > 10
    for path in paths:
        broken = json.loads(text)
        parent = broken
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = bad
        with pytest.raises(pydantic.ValidationError):
            RunRecord.model_validate_json(json.dumps(broken))


RECORDS_V070 = sorted(
    (Path(__file__).resolve().parents[2] / "fixtures" / "v0.7.0").glob("*.runrecord.json")
)


def test_the_committed_records_are_found() -> None:
    """The byte test below reads all 15 committed v0.7.0 records."""
    assert len(RECORDS_V070) == 15


@pytest.mark.parametrize("fixture", RECORDS_V070, ids=lambda p: p.name)
def test_a_finite_v070_record_reserialises_to_its_bytes(fixture: Path) -> None:
    """A committed record is written back byte for byte (the v0.7.0 writer's format)."""
    committed = fixture.read_bytes()
    record = RunRecord.model_validate_json(committed)
    assert (record.model_dump_json(indent=1) + "\n").encode() == committed


# --- Rows written by the real runners ---------------------------------------------------------

_ORCHESTRATOR = Path(__file__).resolve().parents[1] / "orchestrator"


def test_rows_of_the_real_runners_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback (stub surface) and species runner (UFF, geomeTRIC) rows resolve, with frames."""
    monkeypatch.syspath_prepend(str(_ORCHESTRATOR))
    monkeypatch.syspath_prepend(str(_ORCHESTRATOR.parent / "mapping"))
    import test_ts_ensemble as surface
    import test_ts_fallback as runner
    from orchestrator_helpers import uff_recipe, water

    from eta_rxncat.orchestrator import ENGINE_CLASSES, run_species

    path = tmp_path / "real.sqlite"
    with monkeypatch.context() as patch:
        patch.setitem(ENGINE_CLASSES, "xtb_subprocess", surface.TagEngine)
        runner.fallback(path, surface.TagRelax(["two_imag", "A", "B", "A"]))
    with ArtifactStore(path) as store:
        result = run_species(water(), uff_recipe(), store)
        relax_keys = store.query("constrained_preopt")
        ts_keys = store.query("ts_opt")
        frequency_keys = store.query("frequency", "xtb_subprocess")
    assert relax_keys and ts_keys and frequency_keys

    record = stub_record()
    surface_state = surface.SEED_STATE.model_copy(update={"metadata": {}})
    water_record = {
        "species_id": "water",
        "label": "water",
        "state": result.ensemble.records[0].state.model_dump(),
    }
    data = record.model_dump()
    data["species"] = [
        {"species_id": "ts", "label": "ts", "state": surface_state.model_dump()},
        water_record,
    ]
    samples = []
    for index, kind_key in enumerate(
        [("pre_relax_key", k) for k in relax_keys]
        + [("ts_opt_key", k) for k in ts_keys]
        + [("frequency_key", k) for k in frequency_keys]
    ):
        field, key = kind_key
        samples.append(
            {
                "template_id": "t",
                "sample_index": index,
                "source": "seed",
                "species_id": "ts",
                field: key,
            }
        )
    data["runs"][0].update(
        samples=samples,
        ensemble=None,
        endpoints=[
            {
                "species_id": "water",
                "opt_keys": list(result.keys["geometry_opt"]),
                "frequency_keys": list(result.keys["frequency"]),
            }
        ],
    )
    exported = export(path, RunRecord.model_validate(data))
    assert {t.status for t in exported.trajectories} == {"stored"}
    assert {t.kind for t in exported.trajectories} == {"pre_relax", "ts_search", "endpoint_opt"}
    # The stub minimizer records no frames; P-RFO steps and the real geomeTRIC run have them.
    assert all((t.n_frames_total > 0) == (t.kind != "pre_relax") for t in exported.trajectories)
    assert {f.status for f in exported.frequencies} <= {"completed", "failed"}
    completed = [f for f in exported.frequencies if f.status == "completed"]
    assert any(f.n_imaginary == 1 for f in completed)
    (water_frequency,) = [f for f in completed if f.species_id == "water"]
    assert water_frequency.n_imaginary == 0
    # The exact final geometry of the water optimization, not the 5-decimal grid.
    assert water_frequency.coordinates_angstrom == result.ensemble.records[0].state.coordinates
    assert water_frequency.frequencies_cm1 == list(
        result.ensemble.records[0].thermo.frequencies_cm1
    )
