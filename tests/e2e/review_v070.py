"""The v0.7.0 review bundle over four stores (slice 13, mission G13, R15, R17, R18, R20, R34).

One bundle root: ``<root>/<sub>/`` is one sub-bundle per bundled (record, store) pair, written by
the unchanged ``eta-rxncat review-bundle``; ``<root>/index.html`` is a static page (no script) over
them and ``<root>/MANIFEST.sha256`` lists every other file of the tree. The build calls no engine
and writes to no store. Both output roots must be absent or empty; a non-empty one is refused, never
wiped. The tree is built and gated in scratch, then copied to the candidate root.

Network-reference scan (lead ruling A, ``qitem-20261126131940-8fe50cb7``): literal on every
eta-written file, ``eta-view.js`` included except the SVG namespace; the vendored 3Dmol and its
licence must equal the packaged bytes (their literal hits are counted, not gated); a network
``src``/``href`` fails anywhere.
"""

import getpass
import hashlib
import json
import re
import shutil
import socket
import subprocess
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from e2e_env import REPO
from v070 import counted_engine_calls

from eta_rxncat import cli
from eta_rxncat.review import RunRecord
from eta_rxncat.review.bundle import ASSETS_PATH, BUNDLE_BYTE_LIMIT, CONTENT_SECURITY_POLICY
from eta_rxncat.review.run_data import RecordRun
from eta_rxncat.store import ArtifactStore

SLICE11 = "11-enumeration-e2e"
SLICE12 = "12-fallback-e2e"
FALLBACK_STORES = ("graft_time_xtb", "run_time_xtb", "run_time_uma")
M10_MAX_TS_STRIDE = 2
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">'
VENDORED = ("3Dmol-min.js", "LICENSE-3Dmol.txt")
SVG_NAMESPACE = b"http://www.w3.org/2000/svg"
NETWORK_LITERALS = {
    "http:": re.compile(rb"(?i)\bhttp:"),
    "https:": re.compile(rb"(?i)\bhttps:"),
    "ws:": re.compile(rb"(?i)\bwss?:"),
    "//host": re.compile(rb"""(?<![:/\w])//[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"""),
}
NETWORK_REFERENCE = re.compile(
    rb"""(?i)\b(?:src|href)\s*=\s*\\?["']?\s*(?:(?:https?|wss?|ftp):|//)"""
)
SINKS = {
    "innerHTML": rb"innerHTML",
    "outerHTML": rb"outerHTML",
    "insertAdjacentHTML": rb"insertAdjacentHTML",
    "document.write": rb"document\s*\.\s*write",
    "eval": rb"\beval\s*\(",
    "Function": rb"\bFunction\s*\(",
    "string timer": rb"\bset(Timeout|Interval)\s*\(\s*[\"'`]",
}
"""Mission R14's sinks (the vendored 3Dmol is excluded, as in slice 08)."""
ABSOLUTE_PREFIXES = ("/home/", "/Users/", "/tmp/", "/root/")


class ReviewError(AssertionError):
    """A harness refusal or a failed gate."""


@dataclass(frozen=True)
class Source:
    """One store, its slice, and every run record written for it (by file name)."""

    slice_name: str
    store: Path
    records: Mapping[str, Path]


@dataclass(frozen=True)
class SubBundle:
    """One bundled (record, store) pair."""

    name: str
    slice_name: str
    record: Path
    store: Path


def sources(evidence: Path) -> list[Source]:
    """The four stores of slices 11 and 12 with their records, under ``evidence``.

    Raises:
        ReviewError: A store is missing, or a record of a slice belongs to no store.
    """
    first = evidence / "v070-slice11"
    second = evidence / "v070-slice12"
    found = [
        Source(
            SLICE11,
            first / "v070_enum.sqlite",
            {p.name: p for p in sorted((first / "records").glob("*.runrecord.json"))},
        )
    ]
    unassigned = {p.name for p in (second / "records").glob("*.runrecord.json")}
    for unit in FALLBACK_STORES:
        stem = f"v070_fallback_{unit}"
        name = f"{stem}.runrecord.json"
        if name not in unassigned:
            raise ReviewError(f"no run record {name} for store {stem}")
        unassigned.remove(name)
        found.append(Source(SLICE12, second / f"{stem}.sqlite", {name: second / "records" / name}))
    if unassigned:
        raise ReviewError(f"run record(s) of no store: {sorted(unassigned)}")
    missing = [s.store.name for s in found if not s.store.is_file() or not s.records]
    if missing:
        raise ReviewError(f"missing store or records: {missing}")
    return found


def read_records(source: Source) -> dict[str, RunRecord]:
    """Parse every record of the source."""
    return {n: RunRecord.model_validate_json(p.read_bytes()) for n, p in source.records.items()}


def _distinct(runs: Iterable[RecordRun]) -> list[RecordRun]:
    out: list[RecordRun] = []
    for run in runs:
        if run not in out:
            out.append(run)
    return out


def plan_store(records: Mapping[str, RunRecord]) -> tuple[list[str], list[str]]:
    """Choose the records to bundle (largest first); the rest are covered by ``==`` runs.

    Returns:
        ``(bundled, covered)`` record names, each sorted.
    """
    seen: list[RecordRun] = []
    bundled: list[str] = []
    covered: list[str] = []
    for name in sorted(records, key=lambda n: (-len(records[n].runs), n)):
        if records[name].runs and all(r in seen for r in records[name].runs):
            covered.append(name)
        else:
            bundled.append(name)
            seen.extend(records[name].runs)
    return sorted(bundled), sorted(covered)


def coverage_gate(records: Mapping[str, RunRecord], bundled: Sequence[str]) -> dict[str, int]:
    """The runs of the bundled records equal the runs of every record of the store.

    Raises:
        ReviewError: No bundled record, a run not covered, a run bundled twice in one record, or
            two different runs of one unit.
    """
    if not bundled:
        raise ReviewError("a store has no sub-bundle")
    every = _distinct(r for rec in records.values() for r in rec.runs)
    inside = _distinct(r for n in bundled for r in records[n].runs)
    missing = [r for r in every if r not in inside]
    if missing:
        raise ReviewError(f"runs not covered: {[_unit(r) for r in missing]}")
    for name in bundled:
        units = Counter(_unit(r) for r in records[name].runs)
        if max(units.values(), default=1) > 1:
            raise ReviewError(f"{name} holds a unit twice: {units}")
    keys = Counter(_unit(r) for r in every)
    if keys and max(keys.values()) > 1:
        raise ReviewError(
            f"two different runs of one unit: {[k for k, v in keys.items() if v > 1]}"
        )
    return {
        "records": len(records),
        "records_bundled": len(bundled),
        "runs": len(every),
        "runs_bundled": len(inside),
    }


def _unit(run: RecordRun) -> tuple[str, str, str]:
    return run.candidate_id, run.pathway, run.engine.name


def entry_gate(record: RunRecord, run_data: Mapping[str, Any]) -> int:
    """``run_data.json`` has one candidate entry per run of the record.

    Raises:
        ReviewError: The entries and the runs differ.
    """
    engines = {e["engine_id"]: e["name"] for e in run_data["provenance"]["engines"]}
    entries = Counter(
        (c["candidate_id"], c["pathway"], engines[c["engine_id"]]) for c in run_data["candidates"]
    )
    runs = Counter(_unit(r) for r in record.runs)
    if entries != runs:
        raise ReviewError(f"candidate entries {entries} are not the record's runs {runs}")
    return sum(entries.values())


def require_fresh(root: Path) -> None:
    """Refuse a root that exists and is not an empty directory (nothing is wiped).

    Raises:
        ReviewError: One line naming the root.
    """
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ReviewError(f"refusing a non-empty output root, nothing wiped: {root}")


def build_sub_bundles(
    stores: Sequence[Source],
    root: Path,
    on_record: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Plan, cover-gate and write every sub-bundle with the real CLI, counting engine calls.

    Returns:
        The report: coverage and row counts per store, engine calls, sub-bundles.

    Raises:
        ReviewError: A gate failed, the CLI refused, an engine was called or a store changed.
    """
    require_fresh(root)
    plan: list[tuple[Source, dict[str, RunRecord], list[str]]] = []
    report: dict[str, Any] = {"stores": {}, "sub_bundles": []}
    for source in stores:
        records = read_records(source)
        bundled, covered = plan_store(records)
        counts = coverage_gate(records, bundled)
        report["stores"][source.store.name] = {
            "slice": source.slice_name,
            "coverage": counts,
            "bundled": bundled,
            "covered": covered,
        }
        plan.append((source, records, bundled))
    root.mkdir(parents=True, exist_ok=True)
    with counted_engine_calls() as calls:
        for source, records, bundled in plan:
            before = _store_state(source.store)
            for name in bundled:
                sub = Path(name).stem
                start = time.perf_counter()
                code = cli.main(
                    [
                        "review-bundle",
                        "--record",
                        str(source.records[name]),
                        "--store",
                        str(source.store),
                        "--out",
                        str(root / sub),
                    ]
                )
                if code != 0:
                    raise ReviewError(f"review-bundle exit {code} for {name}")
                data = json.loads((root / sub / "run_data.json").read_bytes())
                report["sub_bundles"].append(
                    {
                        "name": sub,
                        "slice": source.slice_name,
                        "record": name,
                        "store": source.store.name,
                        "candidate_entries": entry_gate(records[name], data),
                        "trajectories": len(data["trajectories"]),
                        "frequencies": len(data["frequencies"]),
                        "wall_time_s": time.perf_counter() - start,
                    }
                )
                if on_record is not None:
                    on_record(sub)
            after = _store_state(source.store)
            report["stores"][source.store.name].update(
                rows_before=before[0],
                rows_after=after[0],
                sha256_before=before[1],
                sha256_after=after[1],
            )
            if before != after:
                raise ReviewError(f"store {source.store.name} changed: {before} -> {after}")
        report["engine_calls"] = calls["evaluate"]
    if report["engine_calls"]:
        raise ReviewError(f"the bundle made {report['engine_calls']} engine calls")
    return report


def _store_state(path: Path) -> tuple[int, str]:
    """Row count and file sha256 (the sha taken after the connection closed)."""
    with ArtifactStore(path) as store:
        rows = len(store.query())
    return rows, sha256_of(path)


def sha256_of(path: Path) -> str:
    """The file's sha256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(root: Path) -> list[Path]:
    return sorted(
        (p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()
    )


def bundle_bytes(directory: Path) -> int:
    """The total size of every file below ``directory``."""
    return sum(p.stat().st_size for p in _files(directory))


def gate_counts(run_data: Mapping[str, Any]) -> dict[str, list[int]]:
    """``{"gated": [pass, fail], "reported": [..], "record": [..]}``: UMA gates are reported."""
    engines = {e["engine_id"]: e["name"] for e in run_data["provenance"]["engines"]}
    by_entry = {c["candidate_entry_id"]: engines[c["engine_id"]] for c in run_data["candidates"]}
    counts = {"gated": [0, 0], "reported": [0, 0], "record": [0, 0]}
    for gate in run_data["gates"]:
        entry = gate["candidate_entry_id"]
        if entry is None:
            kind = "record"
        else:
            kind = "reported" if by_entry[entry].startswith("uma") else "gated"
        counts[kind][0 if gate["pass_bool"] else 1] += 1
    return counts


def stride_table(run_data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Per trajectory kind: count, strides seen, and the ``n_frames_total`` range and sum."""
    table: dict[str, list[Mapping[str, Any]]] = {}
    for t in run_data["trajectories"]:
        if t["status"] == "stored":
            table.setdefault(t["kind"], []).append(t)
    return {
        kind: {
            "trajectories": len(entries),
            "strides": sorted({t["decimation_stride"] for t in entries}),
            "n_frames_total_min": min(t["n_frames_total"] for t in entries),
            "n_frames_total_max": max(t["n_frames_total"] for t in entries),
            "n_frames_total_sum": sum(t["n_frames_total"] for t in entries),
        }
        for kind, entries in sorted(table.items())
    }


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _pair(counts: Sequence[int]) -> str:
    return f"{counts[0]} pass / {counts[1]} fail"


def _strides_cell(run_data: Mapping[str, Any]) -> str:
    summary = "".join(
        f"<p>{_text(kind)}: {v['trajectories']} trajectories, decimation_stride "
        f"{_text(', '.join(str(s) for s in v['strides']))}, n_frames_total "
        f"{v['n_frames_total_min']} to {v['n_frames_total_max']} "
        f"(sum {v['n_frames_total_sum']})</p>"
        for kind, v in stride_table(run_data).items()
    )
    rows = "".join(
        f"<tr><td>{_text(t['kind'])}</td><td>{_text(t['species_id'])}</td>"
        f"<td>{_text(t['stage_key'][:12])}</td><td>{t['decimation_stride']}</td>"
        f"<td>{t['n_frames_total']}</td></tr>"
        for t in run_data["trajectories"]
        if t["status"] == "stored"
    )
    return (
        f"{summary}<details><summary>every trajectory</summary><table><tr><th>Kind</th>"
        "<th>Species</th><th>Row</th><th>decimation_stride</th><th>n_frames_total</th></tr>"
        f"{rows}</table></details>"
    )


def write_root_index(root: Path, subs: Sequence[Mapping[str, str]]) -> None:
    """Write ``<root>/index.html``: static, no script, one row per sub-bundle, file names only.

    Each item of ``subs`` has ``name``, ``slice``, ``record`` and ``store`` (file names).
    """
    rows = []
    total = 0
    totals = {"gated": [0, 0], "reported": [0, 0], "record": [0, 0]}
    for sub in subs:
        data = json.loads((root / sub["name"] / "run_data.json").read_bytes())
        counts = gate_counts(data)
        for kind in totals:
            totals[kind] = [totals[kind][i] + counts[kind][i] for i in (0, 1)]
        size = bundle_bytes(root / sub["name"])
        total += size
        units = "".join(f"<p>{_text(c['candidate_entry_id'])}</p>" for c in data["candidates"])
        rows.append(
            "<tr>"
            f'<td><a href="{_text(sub["name"])}/index.html">{_text(sub["name"])}</a></td>'
            f"<td>{_text(sub['slice'])}</td>"
            f"<td>{_text(sub['record'])}</td>"
            f"<td>{_text(sub['store'])}</td>"
            f"<td>{units}</td>"
            f"<td>{_pair(counts['gated'])}</td>"
            f"<td>{_pair(counts['reported'])}</td>"
            f"<td>{_pair(counts['record'])}</td>"
            f"<td>{_strides_cell(data)}</td>"
            f"<td>{size}</td>"
            "</tr>"
        )
    page = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"{CSP_META}\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>eta-rxncat v0.7.0 review</title>\n<style>"
        "body{font-family:system-ui,sans-serif;margin:1.5em;color:#111;background:#fff}"
        "table{border-collapse:collapse;margin:0.5em 0}"
        "th,td{border:1px solid #999;padding:0.25em 0.6em;text-align:left;vertical-align:top}"
        "</style>\n</head>\n<body>\n<h1>eta-rxncat v0.7.0 review bundle</h1>\n"
        "<p>One row per sub-bundle; open a link to review its runs. Trajectories are decimated "
        "to fit the byte budget: a viewer shows every decimation_stride-th frame and the last of "
        "n_frames_total; the full trajectory stays in the store.</p>\n"
        "<p><b>Gates:</b> the mechanics gates count for gating on the GFN2 runs only. UMA gates "
        "are <b>reported, not gated</b>.</p>\n"
        "<table><thead><tr><th>Sub-bundle</th><th>Source slice</th><th>Run record</th>"
        "<th>Store</th><th>Unit ids</th><th>GFN2 mechanics gates (gated)</th>"
        "<th>UMA gates (reported, not gated)</th><th>Record-level gates</th>"
        "<th>Trajectories</th><th>Bytes</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>\n"
        f"<p>Total over {len(rows)} sub-bundles: {total} bytes. GFN2 mechanics gates (gated): "
        f"{_pair(totals['gated'])}. UMA gates (reported, not gated): "
        f"{_pair(totals['reported'])}. Record-level gates: {_pair(totals['record'])}.</p>\n"
        "</body>\n</html>\n"
    )
    (root / "index.html").write_bytes(page.encode("utf-8"))


def write_root_manifest(root: Path) -> str:
    """Write ``<root>/MANIFEST.sha256`` over every other file; return its own sha256."""
    manifest = "".join(
        f"{sha256_of(p)}  {p.relative_to(root).as_posix()}\n"
        for p in _files(root)
        if p != root / "MANIFEST.sha256"
    )
    (root / "MANIFEST.sha256").write_bytes(manifest.encode("utf-8"))
    return sha256_of(root / "MANIFEST.sha256")


# --- Gates on the files as written -----------------------------------------------------------


def m10_gate(root: Path, names: Sequence[str]) -> list[dict[str, Any]]:
    """Read each ``run_data.json`` file and stop on a ``ts_search`` stride above 2.

    Returns:
        Every trajectory's sub-bundle, id, kind, stride and ``n_frames_total``.

    Raises:
        ReviewError: Message starts ``STOP AND REPORT: M10``.
    """
    strides: list[dict[str, Any]] = []
    over = []
    for name in names:
        data = json.loads((root / name / "run_data.json").read_bytes())
        for t in data["trajectories"]:
            if t["status"] != "stored":
                continue
            row = {
                "sub_bundle": name,
                "trajectory_id": t["trajectory_id"],
                "kind": t["kind"],
                "decimation_stride": t["decimation_stride"],
                "n_frames_total": t["n_frames_total"],
            }
            strides.append(row)
            if t["kind"] == "ts_search" and t["decimation_stride"] > M10_MAX_TS_STRIDE:
                over.append(row)
    if over:
        raise ReviewError(
            "STOP AND REPORT: M10 "
            + "; ".join(
                f"sub-bundle {r['sub_bundle']} trajectory {r['trajectory_id']} stride "
                f"{r['decimation_stride']} n_frames_total {r['n_frames_total']}"
                for r in over
            )
        )
    return strides


def manifest_gate(directory: Path) -> int:
    """``sha256sum -c`` exits 0 and the manifest names every other file; return the count.

    Raises:
        ReviewError: A mismatch or an unlisted file.
    """
    run = subprocess.run(
        ["sha256sum", "-c", "--quiet", "MANIFEST.sha256"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        raise ReviewError(f"sha256sum -c exit {run.returncode} in {directory.name}: {run.stdout}")
    listed = {
        line.split("  ", 1)[1]
        for line in (directory / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    }
    present = {
        p.relative_to(directory).as_posix()
        for p in _files(directory)
        if p != directory / "MANIFEST.sha256"
    }
    if listed != present:
        raise ReviewError(
            f"manifest of {directory.name} does not list the files: {listed ^ present}"
        )
    return len(listed)


def host_strings(extra: Iterable[str] = ()) -> list[str]:
    """What no file may hold: path prefixes, ``$HOME``, user and host name, and ``extra``."""
    own = [str(Path.home()), str(REPO), getpass.getuser(), socket.gethostname()]
    return [*ABSOLUTE_PREFIXES, *own, *extra]


def host_data_gate(files: Mapping[str, bytes], forbidden: Sequence[str]) -> None:
    """No file holds an absolute path, ``$HOME``, the user name or the host name (R15).

    Raises:
        ReviewError: Naming the file and the kind of string found.
    """
    hits = [(name, s) for name, body in files.items() for s in forbidden if s.encode() in body]
    if hits:
        raise ReviewError(f"host data in the bundle: {hits}")


def network_hits(body: bytes) -> dict[str, int]:
    """The literal network strings of ``body``, counted per kind (non-zero only)."""
    counts = {k: len(p.findall(body)) for k, p in NETWORK_LITERALS.items()}
    return {k: v for k, v in counts.items() if v}


def network_gate(files: Mapping[str, bytes]) -> dict[str, dict[str, int]]:
    """Lead ruling A: vendored bytes pinned, literal scan on the rest, no network src/href.

    Returns:
        The literal hit counts of the vendored files (reported, not gated).

    Raises:
        ReviewError: A literal in an eta-written file, a vendored file that differs from the
            packaged bytes, or a network ``src``/``href`` anywhere.
    """
    vendored: dict[str, dict[str, int]] = {}
    problems = []
    for name, body in files.items():
        base = Path(name).name
        if NETWORK_REFERENCE.search(body):
            problems.append((name, "src/href"))
        if base in VENDORED:
            if body != (ASSETS_PATH / base).read_bytes():
                problems.append((name, "differs from the packaged asset"))
            vendored[name] = network_hits(body)
            continue
        if base == "eta-view.js":
            body = body.replace(SVG_NAMESPACE, b"")
        hits = network_hits(body)
        if hits:
            problems.append((name, f"network literal {hits}"))
    if problems:
        raise ReviewError(f"network reference in the bundle: {problems}")
    return vendored


def sink_gate(files: Mapping[str, bytes]) -> None:
    """No file but the vendored 3Dmol holds a script sink (R14).

    Raises:
        ReviewError: Naming the file and the sink.
    """
    hits = [
        (name, sink)
        for name, body in files.items()
        if Path(name).name != "3Dmol-min.js"
        for sink, pattern in SINKS.items()
        if re.search(pattern, body)
    ]
    if hits:
        raise ReviewError(f"script sink in the bundle: {hits}")


def csp_gate(files: Mapping[str, bytes]) -> int:
    """Every HTML page carries the one CSP meta (``connect-src 'none'``); return the page count.

    Raises:
        ReviewError: A page without it.
    """
    pages = [n for n in files if n.endswith(".html")]
    bad = [n for n in pages if CSP_META.encode() not in files[n]]
    if "connect-src 'none'" not in CONTENT_SECURITY_POLICY or bad or not pages:
        raise ReviewError(f"CSP meta missing or weak: {bad}")
    return len(pages)


def data_gate(root: Path, names: Sequence[str]) -> None:
    """Frames on every trajectory, nothing ``missing``, and embedded bytes equal the file.

    Raises:
        ReviewError: Naming the sub-bundle and the entry.
    """
    problems = []
    for name in names:
        raw = (root / name / "run_data.json").read_bytes()
        data = json.loads(raw)
        for t in data["trajectories"]:
            if t["status"] != "stored" or not t["frames"]:
                problems.append((name, t["trajectory_id"], t["status"], "no frames"))
        for f in data["frequencies"]:
            if f["status"] == "missing":
                problems.append((name, f["frequency_id"], "missing frequency"))
        species = {s["species_id"] for s in data["species"]}
        for entry in [*data["trajectories"], *data["frequencies"]]:
            if entry["species_id"] not in species:
                problems.append((name, entry["species_id"], "missing species"))
        page = (root / name / "index.html").read_bytes()
        match = re.search(
            rb'<script type="application/json" id="run-data">(.*?)</script>', page, re.DOTALL
        )
        if match is None or match.group(1) != raw:
            problems.append((name, "embedded run-data differs from run_data.json"))
    if problems:
        raise ReviewError(f"data gate: {problems}")


def size_gate(root: Path, names: Sequence[str], limit: int = BUNDLE_BYTE_LIMIT) -> dict[str, int]:
    """Each sub-bundle is at most ``limit`` bytes (R18).

    Raises:
        ReviewError: A sub-bundle above the limit.
    """
    sizes = {n: bundle_bytes(root / n) for n in names}
    over = {n: s for n, s in sizes.items() if s > limit}
    if over:
        raise ReviewError(f"sub-bundle above {limit} bytes: {over}")
    return sizes


def run_gates(root: Path, names: Sequence[str], extra_forbidden: Sequence[str]) -> dict[str, Any]:
    """Every real-bundle gate on the files as written (M10 first).

    Raises:
        ReviewError: The first gate that fails.
    """
    strides = m10_gate(root, names)
    listed = {n: manifest_gate(root / n) for n in names}
    listed["<root>"] = manifest_gate(root)
    sizes = size_gate(root, names)
    data_gate(root, names)
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in _files(root)}
    host_data_gate(files, host_strings(extra_forbidden))
    vendored = network_gate(files)
    sink_gate(files)
    pages = csp_gate(files)
    return {
        "manifest_files": listed,
        "sub_bundle_bytes": sizes,
        "total_bytes": bundle_bytes(root),
        "files_scanned": len(files),
        "vendored_network_literals": vendored,
        "html_pages_with_csp": pages,
        "strides": strides,
        "root_manifest_sha256": sha256_of(root / "MANIFEST.sha256"),
    }


def copy_tree_checked(source: Path, destination: Path) -> int:
    """Copy the gated tree byte for byte into a fresh ``destination``; return the file count.

    The bytes are checked against the source ``MANIFEST.sha256`` as they are written; files are
    created exclusively, nothing is overwritten, and the copy is never read back.

    Raises:
        ReviewError: The destination is not fresh, or a byte string differs from its manifest line.
    """
    require_fresh(destination)
    lines = (source / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    wanted = {name: digest for digest, name in (line.split("  ", 1) for line in lines)}
    wanted["MANIFEST.sha256"] = sha256_of(source / "MANIFEST.sha256")
    for name, digest in sorted(wanted.items()):
        body = (source / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != digest:
            raise ReviewError(f"{name} differs from the manifest")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "xb") as handle:
            if handle.write(body) != len(body):
                raise ReviewError(f"short write of {name}")
        shutil.copymode(source / name, target)
    return len(wanted)


def build_review(evidence: Path, scratch: Path, candidate: Path) -> dict[str, Any]:
    """Build in ``scratch``, gate, and only then copy to ``candidate``.

    Raises:
        ReviewError: A refused root or a failed gate; the candidate root is then untouched.
    """
    require_fresh(scratch)
    require_fresh(candidate)
    report = build_sub_bundles(sources(evidence), scratch)
    subs = report["sub_bundles"]
    names = [s["name"] for s in subs]
    write_root_index(scratch, subs)
    write_root_manifest(scratch)
    report["gates"] = run_gates(scratch, names, [str(evidence), str(scratch)])
    report["gate_counts"] = {
        n: gate_counts(json.loads((scratch / n / "run_data.json").read_bytes())) for n in names
    }
    report["copied_files"] = copy_tree_checked(scratch, candidate)
    return report
