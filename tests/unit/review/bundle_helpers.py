"""Documents for the bundle tests: the stub export, edited to carry chosen imaginary counts."""

from pathlib import Path
from typing import Any

from review_helpers import HOSTILE, put, stub_record

from eta_rxncat.review import RunData, export_run_data
from eta_rxncat.store import ArtifactStore


def exported(tmp_path: Path, label: str = "endo TS", entry_id: str = "ethyl") -> RunData:
    """Return the ``RunData`` of the stub run (one TS frequency with one imaginary mode)."""
    path = tmp_path / "stub.sqlite"
    if not path.exists():
        put(path, {})
    with ArtifactStore(path) as store:
        return export_run_data(stub_record(label, entry_id), store)


def hostile(tmp_path: Path) -> RunData:
    """Return the stub document with hostile species, entry and provenance strings."""
    data = exported(tmp_path, label=HOSTILE, entry_id=HOSTILE).model_dump(mode="json")
    data["provenance"]["store_file_name"] = "<!--    -->.sqlite"
    return RunData.model_validate(data)


def with_modes(run_data: RunData, ts: int, minimum: int | None = None) -> RunData:
    """Return ``run_data`` whose TS frequency has ``ts`` imaginary modes.

    With ``minimum``, a copy of that frequency, with ``minimum`` imaginary modes, is added as the
    endpoint (minimum) frequency of the candidate.
    """
    data: dict[str, Any] = run_data.model_dump(mode="json")
    (entry,) = [f for f in data["frequencies"] if f["status"] == "completed"]

    def modes(item: dict[str, Any], n: int) -> None:
        item["frequencies_cm1"] = [-500.0 - k for k in range(n)] + [10.0, 1200.0]
        item["n_imaginary"] = n
        item["imaginary_modes"] = [
            {"frequency_cm1": -500.0 - k, "displacements_angstrom": [[0.0, 0.0, 0.0]] * 2}
            for k in range(n)
        ]

    modes(entry, ts)
    if minimum is not None:
        copy = {**entry, "frequency_id": "frequency:minimum"}
        modes(copy, minimum)
        data["frequencies"].append(copy)
        data["candidates"][0]["endpoint_frequency_ids"] = ["frequency:minimum"]
    return RunData.model_validate(data)
