"""The v0.7.0 record writer on stub evidence in ``tmp_path`` (slices 13, 14, 18; no engine)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "unit" / "review"))

from acceptance_record_v070 import (  # noqa: E402
    PREVIOUS,
    RecordError,
    build_record,
    command_tag,
    differing_paths,
    main,
    record_verdict,
    refuse_candidates,
    volatile_reason,
)
from review_helpers import stub_record  # noqa: E402
from review_v070 import SOURCE_ROOT, sha256_of  # noqa: E402

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


STEMS = {
    "v070_enum_ethyl_exo_xtb": "exo",
    "v070_fallback_graft_time_xtb": "endo",
    "v070_fallback_run_time_xtb": "endo",
    "v070_fallback_run_time_uma": "endo",
}
SCORE = "v070_enum_ethyl_selectivity_xtb"


def proof_text(dg: float = 12.5, ddg: float = 1.5, stalls: int = 1) -> str:
    """Slice 17's proof: the ruling, the energy table and the clash table."""
    energies = [f"| {stem} | {path} | dG‡ | {dg} | {dg} | True |" for stem, path in STEMS.items()]
    energies += [
        f"| {SCORE} | exo | dG‡ | {dg} | {dg} | True |",
        f"| {SCORE} | endo/exo | ddG‡ | {ddg} | {ddg} | True |",
    ]
    clash = [f"| {stem} | [] | [] | 0 | {stalls if 'exo' in stem else 0} |" for stem in STEMS]
    return (
        "## Gate and rulings\n\n- TJ Q-R7a = A and Q-R7b = A, advisor relay\n"
        "  `qitem-20261126153756-49f5d76005956ea5`.\n\n"
        "## Energies against `tests/fixtures/v0.7.0/`\n\n"
        "| record | pathway | quantity | new | fixture | equal |\n|---|---|---|---|---|---|\n"
        + "\n".join(energies)
        + "\n\n## `seed_clash` against `cov_margin.out`\n\n"
        "| unit | seed_clash indices | measured | bond_changed | stalls |\n|---|---|---|---|---|\n"
        + "\n".join(clash)
        + "\n\n## Stores\n"
    )


def previous_record(units: list[str], manifest: str) -> dict[str, Any]:
    """Slice 13's record as far as the ``replan_7`` block reads it."""
    values = {
        "exclusions_by_reason": {"pre_relax_failed:PreRelaxTimeout": 1},
        "dG_dagger_kcal_mol": 12.5,
        "G_pathway_hartree": G_PATHWAY,
        "n_members": 1,
        "n_merges": 0,
    }
    entries = [{"record": f"{s}.runrecord.json", "values": values} for s in units]
    return {
        "g7_units": entries[:1],
        "g8_constructs": entries[1:],
        "g7_selectivity": [{"record": f"{SCORE}.runrecord.json", "ddG_dagger_kcal_mol": 1.5}],
        "stalls": {"count": 4, "time_lost_s": 2400.0, "graft_pre_relax_timeouts": 0},
        "bundle": {"root_manifest_sha256": manifest},
    }


def stub_evidence(tmp_path: Path) -> tuple[Path, Path, Path]:
    """The replan-7 evidence: one GFN2 unit with a stall, one score, three constructs."""
    ev = tmp_path / "evidence"
    root = ev / SOURCE_ROOT
    for folder in (root / "records", root / "proof"):
        folder.mkdir(parents=True)
    unit = unit_record("ethyl", "exo", "xtb", stall=True)
    score = (
        stub_record()
        .selectivity[0]
        .model_copy(update={"candidate_id": "ethyl", "engine": unit.runs[0].engine})
    )
    (root / "v070_enum.sqlite").write_bytes(b"")
    (root / "records" / "v070_enum_ethyl_exo_xtb.runrecord.json").write_text(unit.model_dump_json())
    (root / "records" / f"{SCORE}.runrecord.json").write_text(
        unit.model_copy(update={"selectivity": [score]}).model_dump_json()
    )
    put_command(root / "proof", "ethyl-exo-xtb")
    put_command(root / "proof", "score-ethyl-xtb")
    for construct, engine in (("graft_time", "xtb"), ("run_time", "xtb"), ("run_time", "uma")):
        stem = f"v070_fallback_{construct}_{engine}"
        (root / f"{stem}.sqlite").write_bytes(b"")
        record = unit_record("ethyl", "endo", engine, stall=False)
        (root / "records" / f"{stem}.runrecord.json").write_text(record.model_dump_json())
        put_command(root / "proof", f"{construct.replace('_', '-')}-{engine}")
    proof = tmp_path / "17-execute.md"
    proof.write_text(proof_text())
    (root / "proof" / PREVIOUS).write_text(json.dumps(previous_record(list(STEMS), "1" * 64)))
    (root / "review").mkdir()
    manifest = root / "review" / "MANIFEST.sha256"
    manifest.write_text("0" * 64 + "  index.html\n")
    report = {
        "engine_calls": 0,
        "stores": {"v070_enum.sqlite": {"rows_before": 3, "rows_after": 3}},
        "gate_counts": {},
        "g15": {"known_clash": [], "known_superseded": []},
        "gates": {
            "root_manifest_sha256": sha256_of(manifest),
            "sub_bundle_bytes": {"a": 1},
            "total_bytes": 2,
        },
    }
    (root / "review_report.json").write_text(json.dumps(report))
    log = tmp_path / "full.log"
    log.write_text("=== 10 passed, 2 deselected, 1 warning in 5.00s ===\n")
    return ev, proof, log


def test_the_record_is_derived_from_the_evidence(tmp_path: Path) -> None:
    """Gates, values, stalls, suite counts and the bundle come from the inputs."""
    ev, proof, log = stub_evidence(tmp_path)
    record = build_record(ev, proof, log, 0)
    (unit,) = record["g7_units"]
    assert unit["gates"] == {"G7.ok": "pass"} and unit["gated"] is True
    assert unit["values"]["stall_count"] == 1
    assert unit["values"]["seed_clash_count"] == 0
    assert unit["values"]["bond_changed_count"] == 0
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


def test_the_replan_block_states_what_changed(tmp_path: Path) -> None:
    """The clash rule, the changed exclusion reasons, the stalls and the manifests."""
    ev, proof, log = stub_evidence(tmp_path)
    block = build_record(ev, proof, log, 0)["replan_7"]
    assert block["clash_rule"]["q_r7a"] == "A" and block["clash_rule"]["q_r7b"] == "A"
    assert block["clash_rule"]["cut_covalent_sum_factor"] == 1.3
    assert block["clash_rule"]["rejected_ratio_min"] is None
    assert block["stalls"]["before"]["count"] == 4 and block["stalls"]["after"]["count"] == 1
    assert block["exclusion_reasons_changed"]["v070_fallback_run_time_xtb.runrecord.json"] == {
        "before": {"pre_relax_failed:PreRelaxTimeout": 1},
        "after": {},
    }
    assert block["units_or_scores_with_changed_values"] == []
    assert block["bundle_root_manifest_sha256"]["before"] == "1" * 64
    previous = ev / SOURCE_ROOT / "proof" / PREVIOUS
    assert block["previous_record_sha256"] == sha256_of(previous)
    old = json.loads(previous.read_text())
    old["g7_selectivity"][0]["ddG_dagger_kcal_mol"] = 2.0
    previous.write_text(json.dumps(old))
    changed = build_record(ev, proof, log, 0)["replan_7"]["units_or_scores_with_changed_values"]
    assert changed == [f"{SCORE}.runrecord.json: ddG_dagger_kcal_mol"]


@pytest.mark.parametrize(
    "text",
    [
        proof_text(dg=12.6),
        proof_text(ddg=1.6),
        proof_text(stalls=2),
        proof_text().replace("| [] | [] |", "| [3] | [3] |", 1),
        proof_text().replace("Q-R7a = A", "Q-R7a is open"),
    ],
)
def test_a_proof_that_disagrees_with_the_records_is_refused(tmp_path: Path, text: str) -> None:
    """Each changed value, or a proof without the ruling, fails the derivation."""
    ev, proof, log = stub_evidence(tmp_path)
    proof.write_text(text)
    with pytest.raises(RecordError, match="differs from the record|does not state"):
        build_record(ev, proof, log, 0)


def test_a_missing_proof_row_section_log_or_previous_is_refused(tmp_path: Path) -> None:
    """A missing table row, section, command log or previous record fails."""
    ev, proof, log = stub_evidence(tmp_path)
    proof.write_text(proof_text().replace("## Energies against", "## Energy"))
    with pytest.raises(RecordError, match="no section"):
        build_record(ev, proof, log, 0)
    proof.write_text(proof_text().replace("| v070_fallback_run_time_uma | endo | dG‡", "| x |", 1))
    with pytest.raises(RecordError, match="rows in slice 17"):
        build_record(ev, proof, log, 0)
    proof.write_text(proof_text())
    (ev / SOURCE_ROOT / "proof" / PREVIOUS).unlink()
    with pytest.raises(RecordError, match="no previous record"):
        build_record(ev, proof, log, 0)
    (ev / SOURCE_ROOT / "proof" / "run-time-uma.log").unlink()
    with pytest.raises(RecordError, match="no log"):
        build_record(ev, proof, log, 0)


def test_a_changed_manifest_or_candidate_input_is_refused(tmp_path: Path) -> None:
    """The manifest must be the one the build reported; candidates are never inputs."""
    ev, proof, log = stub_evidence(tmp_path)
    (ev / SOURCE_ROOT / "review" / "MANIFEST.sha256").write_text("changed\n")
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


# --- The verdict rerun (slice 14) -----------------------------------------------------------------


def stub_output(case: str, commit: str, wall: float, calls: int) -> dict[str, Any]:
    """A unit output holding the fields the verdict reads and one of each kind of field."""
    recipe = case.rsplit("_", 1)[1]
    return {
        "case": case,
        "recipe": recipe,
        "commit_sha": commit,
        "checks": {"tier_gates": {"candidate_ok": {"status": "pass"}}},
        "reported": {
            "G_pathway_hartree": G_PATHWAY,
            "first_pass_engine_calls": calls,
            "first_pass_new_rows": calls,
            "second_pass_engine_calls": 0,
            "second_pass_new_rows": 0,
            "first_pass_wall_time_s": wall,
        },
    }


def stub_verdict(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    """The stub evidence plus a fixtures directory and a rerun that matches it."""
    ev, proof, log = stub_evidence(tmp_path)
    fixtures = tmp_path / "fixtures"
    rerun = tmp_path / "rerun"
    for folder in (fixtures, rerun / "candidates", rerun / "proof"):
        folder.mkdir(parents=True)
    stems = ["v070_enum_ethyl_exo_xtb", "v070_enum_ethyl_selectivity_xtb"] + [
        f"v070_fallback_{c}" for c in ("graft_time_xtb", "run_time_xtb", "run_time_uma")
    ]
    for stem in stems:
        for folder, commit, wall, calls in (
            (fixtures, "a", 9.0, 7),
            (rerun / "candidates", "b", 1.0, 0),
        ):
            scored = "selectivity" in stem
            payload = (
                {"case": stem, "commit_sha": commit, "ddG": 1.5}
                if scored
                else stub_output(stem, commit, wall, calls)
            )
            (folder / f"{stem}.json").write_text(json.dumps(payload))
            record = {"runs": [{"fallback": {"attempts": [{"wall_time_s": wall}]}}]}
            (folder / f"{stem}.runrecord.json").write_text(json.dumps(record))
        put_command(rerun / "proof", command_tag(stem))
    return ev, proof, log, rerun, fixtures


def test_a_matching_rerun_passes_and_names_its_volatile_fields(tmp_path: Path) -> None:
    """Walls, commit and cache counts may differ; the verdict is the rule's own value."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    record = build_record(ev, proof, log, 0, rerun, fixtures)
    assert record["verdict"] == "pass" and record["verdict_reasons"] == []
    assert record_verdict(record) == {"verdict": "pass", "verdict_reasons": []}
    run = record["verdict_run"]
    assert len(run["commands"]) == 5 and len(run["units"]) == 4
    assert [u["gated"] for u in run["units"]] == [True, True, True, False]
    assert {u["first_pass_engine_calls"] for u in run["units"]} == {0}
    entry = run["regression"]["v070_enum_ethyl_exo_xtb.json"]
    assert entry["unexpected"] == [] and "reported.first_pass_wall_time_s" in entry["volatile"]
    assert all(volatile_reason(p) for e in run["regression"].values() for p in e["volatile"])


def test_a_changed_result_fails_the_verdict(tmp_path: Path) -> None:
    """One non-volatile difference is named and fails the comparison and the verdict."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    target = rerun / "candidates" / "v070_enum_ethyl_exo_xtb.json"
    payload = json.loads(target.read_text())
    payload["reported"]["G_pathway_hartree"] += 1e-12
    target.write_text(json.dumps(payload))
    record = build_record(ev, proof, log, 0, rerun, fixtures)
    entry = record["verdict_run"]["regression"][target.name]
    assert entry["unexpected"] == ["reported.G_pathway_hartree"]
    assert record["verdict"] == "fail"
    assert record["verdict_reasons"] == [f"regression {target.name}: fail"]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda r: r["suites"]["default_suite"].update(exit_code=1), "default_suite"),
        (lambda r: r["suites"]["default_suite"]["counts"].update(failed=1), "default_suite"),
        (lambda r: r["verdict_run"].update(commands=[]), "commands: none"),
        (lambda r: r["verdict_run"]["commands"][0].update(exit_code=1), "command "),
        (lambda r: r["verdict_run"]["commands"][0]["counts"].update(skipped=1), "command "),
        (lambda r: r["verdict_run"]["commands"][0]["counts"].update(passed=0), "command "),
        (lambda r: r["verdict_run"]["units"][0]["gates"].update(candidate_ok="fail"), ".candidate"),
        (lambda r: r["verdict_run"].update(units=[]), "units: no gated"),
        (lambda r: r["verdict_run"].update(regression={}), "regression: none"),
    ],
)
def test_the_verdict_rule_fails_on_suite_commands_gates_and_comparisons(
    tmp_path: Path, change: Any, reason: str
) -> None:
    """Every input of the rule can fail it, with a reason."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    record = build_record(ev, proof, log, 0, rerun, fixtures)
    change(record)
    got = record_verdict(record)
    assert got["verdict"] == "fail" and any(reason in r for r in got["verdict_reasons"])


def test_a_uma_gate_is_reported_not_gated(tmp_path: Path) -> None:
    """A failing gate of the UMA unit does not fail the verdict."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    record = build_record(ev, proof, log, 0, rerun, fixtures)
    record["verdict_run"]["units"][-1]["gates"]["candidate_ok"] = "fail"
    assert record_verdict(record)["verdict"] == "pass"


def test_missing_or_extra_files_and_half_the_inputs_are_refused(tmp_path: Path) -> None:
    """The fixtures and the rerun hold exactly the expected files; both inputs are needed."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    with pytest.raises(RecordError, match="both"):
        build_record(ev, proof, log, 0, rerun)
    extra = rerun / "candidates" / "other.json"
    extra.write_text("{}")
    with pytest.raises(RecordError, match="rerun outputs"):
        build_record(ev, proof, log, 0, rerun, fixtures)
    extra.unlink()
    (fixtures / "v070_enum_ethyl_exo_xtb.json").unlink()
    with pytest.raises(RecordError, match="fixtures"):
        build_record(ev, proof, log, 0, rerun, fixtures)


def test_differences_are_found_by_path_and_type() -> None:
    """Missing keys, shorter lists and a changed type are differences."""
    assert differing_paths({"a": [1, {"b": 2}]}, {"a": [1, {"b": 2}]}) == []
    assert differing_paths({"a": 1}, {"a": 1.0}) == ["a"]
    assert differing_paths({"a": 1}, {"a": True}) == ["a"]
    assert differing_paths({"a": [1]}, {"a": [1, 2]}) == ["a"]
    assert differing_paths({}, {"a": {"b": 1}}) == ["a.b"]
    assert volatile_reason("reported.members[0].G_hartree") is None
    assert volatile_reason("reported.excluded[0].pre_relax_wall_time_s") is None
    assert volatile_reason("runs[0].ensemble.members[0].weight") is None


def test_main_with_a_rerun_writes_the_verdict(tmp_path: Path) -> None:
    """Seven arguments add the verdict; six are a usage error."""
    ev, proof, log, rerun, fixtures = stub_verdict(tmp_path)
    out = tmp_path / "out.json"
    args = [str(ev), str(proof), str(log), "0", str(out), str(rerun), str(fixtures)]
    assert main(args) == 0
    assert json.loads(out.read_text())["verdict"] == "pass"
    assert main(args[:6]) == 2
