"""The review bundle harness on stub stores and records in ``tmp_path`` (slices 13, 18; no engine).

Every check has a failing case: coverage, M10, fresh output, the root index, the manifest and the
other real-bundle gates.
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import review_g15

sys.path.append(str(Path(__file__).resolve().parents[1] / "unit" / "review"))

from review_helpers import put, stub_record  # noqa: E402
from review_v070 import (  # noqa: E402
    CSP_META,
    ENUMERATION,
    FALLBACK,
    SOURCE_ROOT,
    ReviewError,
    Source,
    build_sub_bundles,
    copy_tree_checked,
    coverage_gate,
    csp_gate,
    data_gate,
    gate_counts,
    host_data_gate,
    host_strings,
    intro_gate,
    m10_gate,
    manifest_gate,
    network_gate,
    plan_store,
    require_fresh,
    run_gates,
    sink_gate,
    size_gate,
    sources,
    write_root_index,
    write_root_manifest,
)
from test_dispositions import export, extra_key, full_record  # noqa: E402

from eta_rxncat.review.bundle import ASSETS_PATH, BundleError, write_review_bundle  # noqa: E402
from eta_rxncat.review.run_data import RunRecord  # noqa: E402


def stub_source(tmp_path: Path, labels: tuple[str, ...] = ("endo TS",)) -> Source:
    """A stub store and one record file per label (different species labels, same run)."""
    store = tmp_path / "stub.sqlite"
    put(store, {})
    records = {}
    for index, label in enumerate(labels):
        path = tmp_path / f"stub_{index}.runrecord.json"
        path.write_text(stub_record(label).model_dump_json(), encoding="utf-8")
        records[path.name] = path
    return Source(ENUMERATION, store, records)


def built(tmp_path: Path) -> tuple[Path, dict[str, Any], list[str]]:
    """A built root from the stub store, with the index and manifest."""
    root = tmp_path / "review"
    report = build_sub_bundles([stub_source(tmp_path)], root)
    names = [s["name"] for s in report["sub_bundles"]]
    write_root_index(root, report["sub_bundles"])
    write_root_manifest(root)
    return root, report, names


def edit_data(root: Path, name: str, change: Any) -> None:
    """Rewrite one sub-bundle's run_data.json."""
    path = root / name / "run_data.json"
    data = json.loads(path.read_bytes())
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def two_runs() -> tuple[RunRecord, RunRecord, RunRecord]:
    """A record of two units, and one record per unit."""
    base = stub_record().runs[0]
    exo = base.model_copy(update={"pathway": "exo"})
    both = stub_record().model_copy(update={"runs": [base, exo]})
    one = stub_record().model_copy(update={"runs": [base]})
    other = stub_record().model_copy(update={"runs": [exo]})
    return both, one, other


def test_plan_bundles_the_covering_record_and_lists_the_rest() -> None:
    """The larger record is bundled; equal-run records are covered."""
    both, one, other = two_runs()
    records = {"b.json": both, "a.json": one, "c.json": other}
    assert plan_store(records) == (["b.json"], ["a.json", "c.json"])
    assert coverage_gate(records, ["b.json"]) == {
        "records": 3,
        "records_bundled": 1,
        "runs": 2,
        "runs_bundled": 2,
    }


def test_coverage_fails_on_a_missing_run_no_bundle_or_a_different_run() -> None:
    """Coverage fails on each way a run can be lost or doubled."""
    both, one, other = two_runs()
    with pytest.raises(ReviewError, match="not covered"):
        coverage_gate({"a.json": one, "c.json": other}, ["a.json"])
    with pytest.raises(ReviewError, match="no sub-bundle"):
        coverage_gate({"a.json": one}, [])
    twice = both.model_copy(update={"runs": [one.runs[0], one.runs[0]]})
    with pytest.raises(ReviewError, match="twice"):
        coverage_gate({"t.json": twice}, ["t.json"])
    changed = one.model_copy(
        update={"runs": [one.runs[0].model_copy(update={"dG_dagger_kcal_mol": 1.0})]}
    )
    records = {"b.json": both, "d.json": changed}
    assert plan_store(records) == (["b.json", "d.json"], [])
    with pytest.raises(ReviewError, match="two different runs"):
        coverage_gate(records, ["b.json", "d.json"])


def test_sources_refuse_a_missing_or_unassigned_record(tmp_path: Path) -> None:
    """Every store of the named source root has its records and no record is unassigned."""
    records = tmp_path / SOURCE_ROOT / "records"
    records.mkdir(parents=True)
    (tmp_path / SOURCE_ROOT / "v070_enum.sqlite").write_bytes(b"")
    with pytest.raises(ReviewError, match="no run record"):
        sources(tmp_path)
    for unit in ("graft_time_xtb", "run_time_xtb", "run_time_uma"):
        (records / f"v070_fallback_{unit}.runrecord.json").write_text("{}")
    (records / "stray.runrecord.json").write_text("{}")
    with pytest.raises(ReviewError, match="of no store"):
        sources(tmp_path)
    (records / "stray.runrecord.json").unlink()
    with pytest.raises(ReviewError, match="missing store"):
        sources(tmp_path)
    for unit in ("graft_time_xtb", "run_time_xtb", "run_time_uma"):
        (tmp_path / SOURCE_ROOT / f"v070_fallback_{unit}.sqlite").write_bytes(b"")
    with pytest.raises(ReviewError, match="missing store"):
        sources(tmp_path)
    (records / "v070_enum_ethyl_endo_xtb.runrecord.json").write_text("{}")
    found = sources(tmp_path)
    assert [s.group for s in found] == [ENUMERATION, FALLBACK, FALLBACK, FALLBACK]
    assert list(found[0].records) == ["v070_enum_ethyl_endo_xtb.runrecord.json"]


def test_fresh_root_refused_and_nothing_wiped(tmp_path: Path) -> None:
    """A non-empty root is refused in one line and left alone."""
    require_fresh(tmp_path / "absent")
    (tmp_path / "empty").mkdir()
    require_fresh(tmp_path / "empty")
    full = tmp_path / "full"
    full.mkdir()
    (full / "keep").write_text("x")
    for bad in (full, full / "keep"):
        with pytest.raises(ReviewError, match="non-empty") as info:
            require_fresh(bad)
        assert "\n" not in str(info.value)
    source = stub_source(tmp_path)
    with pytest.raises(ReviewError, match="non-empty"):
        build_sub_bundles([source], full)
    assert (full / "keep").read_text() == "x"


def test_the_cli_refuses_a_non_empty_out(tmp_path: Path) -> None:
    """The writer behind each sub-bundle refuses a non-empty ``--out`` (``BundleError``)."""
    from review_helpers import stub_record as record

    from eta_rxncat import cli
    from eta_rxncat.review import export_run_data
    from eta_rxncat.store import ArtifactStore

    source = stub_source(tmp_path)
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "keep").write_text("x")
    with ArtifactStore(source.store) as store:
        data = export_run_data(record(), store)
    with pytest.raises(BundleError):
        write_review_bundle(data, tmp_path / "out")
    (path,) = source.records.values()
    argv = ["review-bundle", "--record", str(path), "--store", str(source.store)]
    assert cli.main([*argv, "--out", str(tmp_path / "out")]) == 1


def test_build_counts_calls_rows_and_entries(tmp_path: Path) -> None:
    """The build makes no engine call, changes no store and has one entry per run."""
    _, report, names = built(tmp_path)
    assert names == ["stub_0.runrecord"]
    assert report["engine_calls"] == 0
    (store,) = report["stores"].values()
    assert store["rows_before"] == store["rows_after"] == 4
    assert store["sha256_before"] == store["sha256_after"]
    assert report["sub_bundles"][0]["candidate_entries"] == 1


def test_gates_fail_on_the_stub_row_without_frames_or_missing(tmp_path: Path) -> None:
    """The stub record names a row the store lacks, so the data gate refuses it."""
    root, _, names = built(tmp_path)
    with pytest.raises(ReviewError, match="missing frequency"):
        data_gate(root, names)


def clean_root(tmp_path: Path) -> tuple[Path, list[str]]:
    """A built root whose data gate passes: the missing stub sample is removed."""
    store = tmp_path / "stub.sqlite"
    put(store, {})
    record = stub_record()
    run = record.runs[0].model_copy(update={"samples": record.runs[0].samples[:1]})
    path = tmp_path / "ok.runrecord.json"
    path.write_text(record.model_copy(update={"runs": [run]}).model_dump_json(), encoding="utf-8")
    root = tmp_path / "review"
    report = build_sub_bundles([Source(FALLBACK, store, {path.name: path})], root)
    names = [s["name"] for s in report["sub_bundles"]]
    write_root_index(root, report["sub_bundles"])
    write_root_manifest(root)
    return root, names


def test_every_gate_passes_on_a_clean_root_and_copy_is_byte_checked(tmp_path: Path) -> None:
    """All gates pass and the copy checks bytes and refuses to overwrite."""
    root, names = clean_root(tmp_path)
    gates = run_gates(root, names, [str(tmp_path)])
    assert gates["html_pages_with_csp"] == 2
    assert gates["vendored_network_literals"]
    destination = tmp_path / "candidate" / "review"
    n = copy_tree_checked(root, destination)
    assert n == gates["manifest_files"]["<root>"] + 1
    assert (destination / "index.html").read_bytes() == (root / "index.html").read_bytes()
    with pytest.raises(ReviewError, match="non-empty"):
        copy_tree_checked(root, destination)
    (root / "index.html").write_bytes(b"changed")
    with pytest.raises(ReviewError, match="differs"):
        copy_tree_checked(root, tmp_path / "other")


def test_m10_stops_on_stride_3_and_passes_stride_2(tmp_path: Path) -> None:
    """A ts_search stride of 3 stops the run; 2 passes."""
    root, names = clean_root(tmp_path)

    def stride(value: int) -> Any:
        def change(data: dict[str, Any]) -> None:
            for t in data["trajectories"]:
                if t["kind"] == "ts_search":
                    t["decimation_stride"] = value

        return change

    edit_data(root, names[0], stride(2))
    assert {r["decimation_stride"] for r in m10_gate(root, names) if r["kind"] == "ts_search"} == {
        2
    }
    edit_data(root, names[0], stride(3))
    with pytest.raises(ReviewError, match="^STOP AND REPORT: M10") as info:
        m10_gate(root, names)
    assert names[0] in str(info.value) and "stride 3" in str(info.value)


def test_root_index_is_static_linked_and_names_files_only(tmp_path: Path) -> None:
    """The root page is script-free, linked, and names files only."""
    root, names = clean_root(tmp_path)
    html = (root / "index.html").read_text(encoding="utf-8")
    assert CSP_META in html and "<script" not in html
    assert f'href="{names[0]}/index.html"' in html
    assert "ok.runrecord.json" in html and "stub.sqlite" in html
    assert "decimation_stride" in html and "n_frames_total" in html
    assert "reported, not gated" in html
    assert str(tmp_path) not in html


def set_stride(root: Path, name: str, kind: str, stride: int) -> None:
    """Set the stride of every trajectory of one kind in a sub-bundle's data."""

    def change(data: dict[str, Any]) -> None:
        for t in data["trajectories"]:
            if t["kind"] == kind:
                t["decimation_stride"] = stride

    edit_data(root, name, change)


def reindex(root: Path, names: list[str]) -> str:
    """Rewrite the root page from the files and return it."""
    subs = [
        {"name": n, "group": "g", "record": "ok.runrecord.json", "store": "stub.sqlite"}
        for n in names
    ]
    write_root_index(root, subs)
    return (root / "index.html").read_text(encoding="utf-8")


def test_intro_says_no_decimation_when_every_stride_is_one(tmp_path: Path) -> None:
    """All strides 1: the page says none is decimated; a later stride above 1 fails the gate."""
    root, names = clean_root(tmp_path)
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "No trajectory is decimated" in html and "Some trajectories are decimated" not in html
    assert intro_gate(root, names).startswith("No trajectory is decimated")
    set_stride(root, names[0], "pre_relax", 2)
    with pytest.raises(ReviewError, match="does not state the decimation"):
        intro_gate(root, names)


def test_intro_states_the_kinds_and_strides_above_one(tmp_path: Path) -> None:
    """A stride above 1 is named by kind; the page then fails once the data is at stride 1."""
    root, names = clean_root(tmp_path)
    set_stride(root, names[0], "pre_relax", 4)
    set_stride(root, names[0], "ts_search", 2)
    html = reindex(root, names)
    assert "No trajectory is decimated" not in html
    assert "pre_relax at decimation_stride 4; ts_search at decimation_stride 2" in html
    assert "endpoint_opt at" not in html
    assert intro_gate(root, names).startswith("Some trajectories are decimated")
    set_stride(root, names[0], "pre_relax", 1)
    set_stride(root, names[0], "ts_search", 1)
    with pytest.raises(ReviewError, match="does not state the decimation"):
        intro_gate(root, names)


def test_uma_gates_are_counted_as_reported() -> None:
    """UMA gates are counted as reported, GFN2 as gated."""
    data = {
        "provenance": {"engines": [{"engine_id": "e", "name": "uma_direct"}]},
        "candidates": [{"candidate_entry_id": "c", "engine_id": "e"}],
        "gates": [
            {"candidate_entry_id": "c", "pass_bool": True},
            {"candidate_entry_id": None, "pass_bool": False},
        ],
    }
    assert gate_counts(data) == {"gated": [0, 0], "reported": [1, 0], "record": [0, 1]}
    data["provenance"]["engines"][0]["name"] = "xtb_subprocess"  # type: ignore[index]
    assert gate_counts(data)["gated"] == [1, 0]


def test_manifest_gate_fails_on_a_changed_or_unlisted_file(tmp_path: Path) -> None:
    """A changed or unlisted file fails the manifest gate."""
    root, names = clean_root(tmp_path)
    assert manifest_gate(root / names[0]) == 5
    manifest_gate(root)
    (root / "extra.txt").write_text("x")
    with pytest.raises(ReviewError, match="does not list"):
        manifest_gate(root)
    (root / "extra.txt").unlink()
    (root / names[0] / "run_data.json").write_text("{}")
    with pytest.raises(ReviewError, match="sha256sum"):
        manifest_gate(root)


def test_data_gate_fails_on_unequal_embedded_bytes_and_empty_frames(tmp_path: Path) -> None:
    """Empty frames and unequal embedded bytes fail."""
    root, names = clean_root(tmp_path)
    data_gate(root, names)
    edit_data(root, names[0], lambda d: d["trajectories"][0].update(frames=[]))
    with pytest.raises(ReviewError, match="no frames"):
        data_gate(root, names)
    with pytest.raises(ReviewError, match="embedded"):
        data_gate(root, names)


def test_size_gate_fails_above_the_limit(tmp_path: Path) -> None:
    """A sub-bundle above the limit fails."""
    root, names = clean_root(tmp_path)
    assert size_gate(root, names)
    with pytest.raises(ReviewError, match="above"):
        size_gate(root, names, limit=10)


@pytest.mark.parametrize(
    "body",
    [b"see http://a.example/x", b"wss://a.example", b'"//cdn.example.com/x.js"', b"<img src=//x>"],
)
def test_network_gate_fails_on_an_eta_file(body: bytes) -> None:
    """Each network literal fails an eta-written file."""
    with pytest.raises(ReviewError, match="network"):
        network_gate({"index.html": body})


def test_network_gate_ruling_a() -> None:
    """Vendored bytes are pinned, the SVG namespace is the one exemption."""
    view = (ASSETS_PATH / "eta-view.js").read_bytes()
    vendored = {n: (ASSETS_PATH / n).read_bytes() for n in ("3Dmol-min.js", "LICENSE-3Dmol.txt")}
    counts = network_gate({"assets/eta-view.js": view, **vendored})
    assert counts["3Dmol-min.js"]
    with pytest.raises(ReviewError, match="differs"):
        network_gate({"assets/3Dmol-min.js": vendored["3Dmol-min.js"] + b" "})
    with pytest.raises(ReviewError, match="src/href"):
        network_gate({"assets/LICENSE-3Dmol.txt": b'<a href="https://x.example">'})
    with pytest.raises(ReviewError, match="network literal"):
        network_gate({"assets/eta-view.js": view + b" 'http://x.example'"})


@pytest.mark.parametrize("body", [b"/home/someone/x", b"C /tmp/y", b"user " + b"zz-host"])
def test_host_data_gate_fails(body: bytes) -> None:
    """A path, temp dir or host name fails."""
    with pytest.raises(ReviewError, match="host data"):
        host_data_gate({"f": body}, host_strings(["zz-host"]))


def test_sink_and_csp_gates_fail() -> None:
    """A script sink or a page without the CSP fails."""
    sink_gate({"assets/3Dmol-min.js": b"a.innerHTML = b"})
    with pytest.raises(ReviewError, match="sink"):
        sink_gate({"index.html": b"a.innerHTML = b"})
    with pytest.raises(ReviewError, match="CSP"):
        csp_gate({"index.html": b"<html></html>"})
    with pytest.raises(ReviewError, match="CSP"):
        csp_gate({})


# --- The G15 gates (slice 18) -----------------------------------------------------------------


def dispositions_bundle(tmp_path: Path, drop: int | None = 5) -> tuple[dict[str, Any], str, Any]:
    """A written bundle of the stub record with every disposition kind (``drop`` removes one)."""
    record = full_record()
    run = record.runs[0]
    kept = [s for s in run.samples if s.sample_index != drop]
    record = record.model_copy(update={"runs": [run.model_copy(update={"samples": kept})]})
    out = write_review_bundle(export(tmp_path, record), tmp_path / "bundle")
    data = json.loads((out / "run_data.json").read_bytes())
    return data, (out / "index.html").read_text(encoding="utf-8"), record


def test_g15_gates_pass_on_a_recorded_bundle(tmp_path: Path) -> None:
    """Every row is recorded, grouped and headed; identity and banners show."""
    data, html, record = dispositions_bundle(tmp_path)
    review_g15.disposition_gate("s", data, record)
    counts = review_g15.page_gate("s", data, html)
    assert counts["used_ts"] == 1 and counts["used_minimum"] == 1
    assert counts["notused_ts"] == 2 and counts["notused_minimum"] == 2
    assert counts["notused_lines"] == 3 and counts["ts_banners"] >= 1


def test_g15_refuses_a_not_recorded_or_missing_disposition(tmp_path: Path) -> None:
    """The unjudged sample, a dropped disposition and a missing endpoint row each fail."""
    data, _, record = dispositions_bundle(tmp_path, drop=None)
    with pytest.raises(review_g15.G15Error, match="not_recorded"):
        review_g15.disposition_gate("s", data, record)
    shorter = tmp_path / "short"
    shorter.mkdir()
    data, _, record = dispositions_bundle(shorter)
    data["candidates"][0]["sample_dispositions"].pop()
    with pytest.raises(review_g15.G15Error, match="samples"):
        review_g15.disposition_gate("s", data, record)
    again = tmp_path / "ends"
    again.mkdir()
    data, _, record = dispositions_bundle(again)
    data["candidates"][0]["endpoint_dispositions"].pop()
    with pytest.raises(review_g15.G15Error, match="endpoint dispositions"):
        review_g15.disposition_gate("s", data, record)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("— member (weight 1.000)", "— something else", "block missing"),
        ('<div class="notused">', '<div class="other">', "outside the Used"),
        ("Identity: imaginary frequency", "Numbers: imaginary frequency", "no identity"),
        ("Transition state identity check failed", "Check passed", "banner differs"),
        ("forming-bond overlap", "forming overlap", "overlap differs"),
        ("excluded: seed_clash", "excluded: other", "line missing"),
    ],
)
def test_g15_page_gate_fails_on_a_changed_page(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    """Each way the static page can lose a disposition fails the gate."""
    data, html, _ = dispositions_bundle(tmp_path)
    assert old in html
    with pytest.raises(review_g15.G15Error, match=message):
        review_g15.page_gate("s", data, html.replace(old, new))


def test_g15_known_answers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The clash and superseded answers hold on matching constants and fail on others."""
    data, html, record = dispositions_bundle(tmp_path)
    engine = data["provenance"]["engines"][0]["name"]
    candidate = data["candidates"][0]["candidate_id"]
    for name, value in (
        ("CLASH_ENGINE", engine),
        ("CLASH_CANDIDATE", (candidate, "endo")),
        ("CLASH_SAMPLE", 3),
        ("CLASH_PAIR", (0, 1)),
        ("SUPERSEDED_ENGINE", engine),
        ("SUPERSEDED_CANDIDATE", candidate),
        ("SUPERSEDED_KEY", extra_key("first").key[:12]),
    ):
        monkeypatch.setattr(review_g15, name, value)
    (clash,) = review_g15._clash_answers("s", data, html)
    assert "excluded: seed_clash" in clash["line"]
    (pushed,) = review_g15._superseded_answers("s", data, record, html)
    assert (pushed["successor_kind"], pushed["successor_reason"]) == ("kept", None)
    monkeypatch.setattr(review_g15, "CLASH_ANGSTROM", 0.5)
    with pytest.raises(review_g15.G15Error, match="expected"):
        review_g15._clash_answers("s", data, html)
    changed = data["candidates"][0]["endpoint_dispositions"]
    changed[1].update(kind="dropped", reason_code="x")
    with pytest.raises(review_g15.G15Error, match="recorded"):
        review_g15._superseded_answers("s", data, record, html)
