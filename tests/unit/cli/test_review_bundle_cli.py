"""``eta-rxncat review-bundle``: a stub record round trip and its one-line typed errors."""

import subprocess
import sys
from pathlib import Path

import pytest

from eta_rxncat import cli
from eta_rxncat.review import TRAJECTORY_BYTE_BUDGET, read_run_data

sys.path.insert(0, str(Path(__file__).parents[1] / "review"))

from review_helpers import put, stub_record  # noqa: E402


@pytest.fixture
def inputs(tmp_path: Path) -> tuple[Path, Path]:
    """Write the stub store and record; return their paths."""
    store = tmp_path / "run.sqlite"
    put(store, {})
    record = tmp_path / "run_record.json"
    record.write_text(stub_record().model_dump_json())
    return record, store


def arguments(record: Path, store: Path, out: Path) -> list[str]:
    """Return the ``review-bundle`` argument list."""
    return ["review-bundle", "--record", str(record), "--store", str(store), "--out", str(out)]


def test_round_trip(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A stub record exits 0 and writes a bundle that reads back."""
    out = tmp_path / "bundle"
    assert cli.main(arguments(*inputs, out)) == 0
    assert capsys.readouterr() == (f"OK {out}\n", "")
    run_data = read_run_data((out / "run_data.json").read_bytes())
    assert run_data.candidates[0].candidate_id == "r=ethyl"
    assert (out / "index.html").is_file() and (out / "MANIFEST.sha256").is_file()


def test_installed_script_round_trip(inputs: tuple[Path, Path], tmp_path: Path) -> None:
    """The installed console script writes the bundle too."""
    script = Path(sys.executable).parent / "eta-rxncat"
    result = subprocess.run(
        [str(script), *arguments(*inputs, tmp_path / "bundle")], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_the_exporter_budget_is_passed(
    inputs: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI exports with the bundle's trajectory budget."""
    seen = {}
    from eta_rxncat import review

    real = review.export_run_data

    def spy(*args: object, **kwargs: object) -> object:
        """Record the keywords, then export."""
        seen.update(kwargs)
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(review, "export_run_data", spy)
    assert cli.main(arguments(*inputs, tmp_path / "bundle")) == 0
    assert seen == {"trajectory_byte_budget": TRAJECTORY_BYTE_BUDGET}


def failing(
    argv: list[str], capsys: pytest.CaptureFixture[str], kind: str, out: Path | None = None
) -> str:
    """Assert exit 1 with one typed error line and no bundle; return stderr."""
    assert cli.main(argv) == 1
    stdout, stderr = capsys.readouterr()
    assert stdout == "" and stderr.count("\n") == 1
    assert stderr.startswith(f"error: {kind}: "), stderr
    if out is not None:
        assert not out.exists()
    return stderr


def test_missing_record(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing record file is a typed error."""
    out = tmp_path / "bundle"
    argv = arguments(tmp_path / "none.json", inputs[1], out)
    failing(argv, capsys, "FileNotFoundError", out)


def test_invalid_record(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A record that does not validate is a typed error."""
    inputs[0].write_text('{"species": 1}')
    out = tmp_path / "bundle"
    failing(arguments(*inputs, out), capsys, "ValidationError", out)


def test_missing_store_is_not_created(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing store is an error and stays missing."""
    store = tmp_path / "absent.sqlite"
    out = tmp_path / "bundle"
    failing(arguments(inputs[0], store, out), capsys, "FileNotFoundError", out)
    assert not store.exists()


def test_a_file_that_is_no_store(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file that is not a database is a typed error."""
    bad = tmp_path / "bad.sqlite"
    bad.write_bytes(b"this is not a database" * 100)
    out = tmp_path / "bundle"
    failing(arguments(inputs[0], bad, out), capsys, "DatabaseError", out)


def test_record_that_does_not_fit(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A record referring to undeclared species is an export error."""
    record = stub_record().model_copy(update={"species": []})
    inputs[0].write_text(record.model_dump_json())
    out = tmp_path / "bundle"
    failing(arguments(*inputs, out), capsys, "ExportError", out)


def test_non_empty_output(
    inputs: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-empty output directory is refused."""
    out = tmp_path / "bundle"
    out.mkdir()
    (out / "keep").write_text("x")
    failing(arguments(*inputs, out), capsys, "BundleError")


def test_missing_option_is_usage(capsys: pytest.CaptureFixture[str]) -> None:
    """A missing option is a usage error (exit 2)."""
    assert cli.main(["review-bundle", "--record", "r.json"]) == 2
    assert "--store" in capsys.readouterr().err
