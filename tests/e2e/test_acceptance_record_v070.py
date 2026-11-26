"""The v0.7.0 acceptance record writer on stub evidence in ``tmp_path`` (slice 13; no engine)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "unit" / "review"))

from acceptance_record_v070 import (  # noqa: E402
    RecordError,
    build_record,
    main,
    refuse_candidates,
)
from review_helpers import stub_record  # noqa: E402
from review_v070 import sha256_of  # noqa: E402

ENGINES = {"xtb": "xtb_subprocess", "uma": "uma_direct"}
G_PATHWAY = -1.05


def unit_record(candidate: str, pathway: str, engine: str, stall: bool) -> Any:
    """A one-unit record with one member and, optionally, one 600 s stall."""
    base = stub_record()
    run = base.runs[0]
    assert run.ensemble is not None
    identity = run.engine.model_copy(update={"name": ENGINES[engine]})
    excluded = (
        [
            {
                "index": 1,
                "source": "perturb:0",
                "reason": "pre_relax_failed:PreRelaxTimeout",
                "pre_relax_wall_time_s": 600.004,
            }
        ]
        if stall
        else []
    )
    data = run.ensemble.model_dump()
    data.update(pathway=pathway, excluded=excluded)
    run = run.model_validate(
        {
            **run.model_dump(),
            "candidate_id": candidate,
            "pathway": pathway,
            "engine": identity.model_dump(),
            "ensemble": data,
        }
    )
    gate = base.gates[0].model_copy(
        update={
            "gate_id": "G7.ok",
            "unit_ref": base.gates[0].unit_ref.model_copy(  # type: ignore[union-attr]
                update={"candidate_id": candidate, "pathway": pathway, "engine": identity}
            ),
        }
    )
    return base.model_copy(
        update={
            "runs": [run],
            "gates": [gate],
            "selectivity": [],
            "candidates": [base.candidates[0].model_copy(update={"candidate_id": candidate})],
        }
    )


def put_command(proof: Path, tag: str, code: int = 0) -> None:
    """The log and time files of one command."""
    (proof / f"{tag}.log").write_text("=== 1 passed, 3 warnings in 5.00s ===\n")
    (proof / f"{tag}.time").write_text(f"\tExit status: {code}\n")


def stub_evidence(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Slices 11, 12 and 13 evidence: one GFN2 unit with a stall, one score, three constructs."""
    ev = tmp_path / "evidence"
    first = ev / "v070-slice11"
    second = ev / "v070-slice12"
    for folder in (first / "records", first / "proof", second / "records", second / "proof"):
        folder.mkdir(parents=True)
    (first / "v070_enum.sqlite").write_bytes(b"")
    unit = unit_record("ethyl", "exo", "xtb", stall=True)
    (first / "records" / "v070_enum_ethyl_exo_xtb.runrecord.json").write_text(
        unit.model_dump_json()
    )
    scored = stub_record()
    score = scored.selectivity[0].model_copy(
        update={
            "candidate_id": "ethyl",
            "engine": unit.runs[0].engine,
        }
    )
    merged = unit.model_copy(update={"selectivity": [score]})
    (first / "records" / "v070_enum_ethyl_selectivity_xtb.runrecord.json").write_text(
        merged.model_dump_json()
    )
    put_command(first / "proof", "ethyl-exo-xtb")
    put_command(first / "proof", "score-ethyl-xtb")
    (first / "proof" / "table.md").write_text(
        "| ethyl exo xtb | exit 0 | 1 | x | 1 / 600 / False | 12.500 | a |\n"
    )
    proof_rows = []
    for construct, engine in (("graft_time", "xtb"), ("run_time", "xtb"), ("run_time", "uma")):
        stem = f"v070_fallback_{construct}_{engine}"
        (second / f"{stem}.sqlite").write_bytes(b"")
        record = unit_record("ethyl", "endo", engine, stall=False)
        (second / "records" / f"{stem}.runrecord.json").write_text(record.model_dump_json())
        put_command(second / "proof", f"{construct.replace('_', '-')}-{engine}")
        name = {"xtb": "GFN2", "uma": "UMA"}[engine]
        proof_rows.append(f"| {construct} {name} | m | x | 0 | 1 | no | {G_PATHWAY} | 1 / 1 |")
    slice12 = tmp_path / "12-execute.md"
    slice12.write_text(
        "### Ensemble gates and values\n\n| unit | a |\n|---|---|\n"
        + "\n".join(proof_rows)
        + "\n\n## Stores\n"
    )
    out = ev / "v070-slice13"
    (out / "review").mkdir(parents=True)
    manifest = out / "review" / "MANIFEST.sha256"
    manifest.write_text("0" * 64 + "  index.html\n")
    report = {
        "engine_calls": 0,
        "stores": {"v070_enum.sqlite": {"rows_before": 3, "rows_after": 3}},
        "gate_counts": {},
        "gates": {
            "root_manifest_sha256": sha256_of(manifest),
            "sub_bundle_bytes": {"a": 1},
            "total_bytes": 2,
        },
    }
    (out / "review_report.json").write_text(json.dumps(report))
    log = tmp_path / "full.log"
    log.write_text("=== 10 passed, 2 deselected, 1 warning in 5.00s ===\n")
    return ev, slice12, log


def test_the_record_is_derived_from_the_evidence(tmp_path: Path) -> None:
    """Gates, values, stalls, suite counts and the bundle come from the inputs."""
    ev, proof, log = stub_evidence(tmp_path)
    record = build_record(ev, proof, log, 0)
    (unit,) = record["g7_units"]
    assert unit["gates"] == {"G7.ok": "pass"} and unit["gated"] is True
    assert unit["values"]["stall_count"] == 1
    assert record["stalls"]["time_lost_s"] == pytest.approx(600.004)
    assert [u["construct"] for u in record["g8_constructs"]] == [
        "graft_time",
        "run_time",
        "run_time",
    ]
    assert [u["gated"] for u in record["g8_constructs"]] == [True, True, False]
    assert record["g7_selectivity"][0]["ddG_dagger_kcal_mol"] == 1.5
    assert record["suites"]["default_suite"]["counts"]["passed"] == 10
    assert all(c["counts"]["skipped"] == 0 for c in record["suites"]["engine_commands"])
    bundle = record["bundle"]
    assert bundle["path"] == "tests/candidate_outputs/v0.7.0/review/"
    assert bundle["rows_per_store"]["v070_enum.sqlite"] == {"before": 3, "after": 3}
    assert "verdict" not in record


def test_a_table_that_disagrees_with_the_record_is_refused(tmp_path: Path) -> None:
    """A proof table with another stall count fails the derivation."""
    ev, proof, log = stub_evidence(tmp_path)
    table = ev / "v070-slice11" / "proof" / "table.md"
    table.write_text(table.read_text().replace("1 / 600", "0 / 0"))
    with pytest.raises(RecordError, match="differs from the record"):
        build_record(ev, proof, log, 0)


def test_a_slice12_disagreement_or_missing_log_is_refused(tmp_path: Path) -> None:
    """A different ``G_pathway`` or a missing command log fails."""
    ev, proof, log = stub_evidence(tmp_path)
    text = proof.read_text()
    proof.write_text(text.replace(str(G_PATHWAY), "-1.06", 1))
    with pytest.raises(RecordError, match="differs from the record"):
        build_record(ev, proof, log, 0)
    proof.write_text(text)
    (ev / "v070-slice12" / "proof" / "run-time-uma.log").unlink()
    with pytest.raises(RecordError, match="no log"):
        build_record(ev, proof, log, 0)


def test_a_changed_manifest_or_candidate_input_is_refused(tmp_path: Path) -> None:
    """The manifest must be the one the build reported; candidates are never inputs."""
    ev, proof, log = stub_evidence(tmp_path)
    (ev / "v070-slice13" / "review" / "MANIFEST.sha256").write_text("changed\n")
    with pytest.raises(RecordError, match="differs from the build report"):
        build_record(ev, proof, log, 0)
    with pytest.raises(RecordError, match="candidate"):
        refuse_candidates(Path("tests/candidate_outputs/v0.7.0/review"))


def test_main_writes_the_record_and_rejects_bad_usage(tmp_path: Path) -> None:
    """The command writes JSON; a wrong argument count is a usage error."""
    ev, proof, log = stub_evidence(tmp_path)
    out = tmp_path / "out.json"
    assert main([str(ev), str(proof), str(log), "0", str(out)]) == 0
    assert json.loads(out.read_text())["version"] == "0.7.0"
    assert main([]) == 2
