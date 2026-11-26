"""The G15 gates on a built review bundle (slice 18; mission G15, R35).

Read from each sub-bundle's ``run_data.json`` and static ``index.html`` and compared with the run
record it was built from: every transition-state sample and every minimum row carries a disposition
(none ``not_recorded``), every frequency row sits in the "Used" or "Not used" group under a heading
that names its disposition, every transition-state block shows its identity numbers (with a banner
when the identity fails), and the two known answers of TJ's Phase 3 findings hold.
"""

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from eta_rxncat.review import RunRecord
from eta_rxncat.review.run_data import RecordRun

GROUP_TITLES = {
    "used": "Used in the result",
    "notused": "Not used (rejected, merged or superseded)",
}
BANNER = "Transition state identity check failed"

CLASH_ENGINE = "xtb_subprocess"
CLASH_CANDIDATE = ("ethyl", "endo")
CLASH_SAMPLE = 6
CLASH_PAIR = (4, 21)
CLASH_ANGSTROM = 0.438
SUPERSEDED_KEY = "071c077d750a"
SUPERSEDED_ENGINE = "uma_direct"
SUPERSEDED_CANDIDATE = "npropyl"


class G15Error(AssertionError):
    """A failed G15 gate."""


@dataclass
class Block:
    """One frequency block of a unit's static summary (an ``h5`` heading and what follows it)."""

    heading: str
    banner: str = ""
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class Group:
    """One of a unit's two static groups: its title, frequency blocks and rowless sample lines."""

    title: str = ""
    blocks: list[Block] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)


class _Page(HTMLParser):
    """Collect ``(candidate_id, unit heading) -> {"used": Group, "notused": Group}``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.units: dict[tuple[str, str], dict[str, Group]] = {}
        self.stray: list[str] = []
        self._candidate: str | None = None
        self._unit: str | None = None
        self._divs: list[str] = []
        self._capture: str | None = None
        self._text: list[str] = []

    def _group(self) -> Group | None:
        css = next((c for c in reversed(self._divs) if c in GROUP_TITLES), None)
        if css is None or self._candidate is None or self._unit is None:
            return None
        found = self.units.setdefault((self._candidate, self._unit), {})
        return found.setdefault(css, Group())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "section":
            self._candidate = (values.get("id") or "").removeprefix("c/")
            self._unit = None
        elif tag == "div":
            self._divs.append(values.get("class") or "")
            if self._divs[-1] == "banner":
                self._start("banner")
        elif tag in ("h3", "h4", "h5", "p"):
            self._start(tag)

    def _start(self, tag: str) -> None:
        self._capture, self._text = tag, []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self._candidate = None
        text = "".join(self._text)
        if tag == "div" and self._divs:
            if self._divs.pop() == "banner":
                self._finish("banner", text)
        elif tag == self._capture:
            self._finish(tag, text)

    def _finish(self, tag: str, text: str) -> None:
        self._capture = None
        if tag == "h3":
            self._unit = text
            return
        group = self._group()
        if group is None:
            if tag == "h5":
                self.stray.append(text)
        elif tag == "h4":
            group.title = text
        elif tag == "h5":
            group.blocks.append(Block(text))
        elif tag == "banner" and group.blocks:
            group.blocks[-1].banner += text
        elif tag == "p" and text.startswith("Sample "):
            group.lines.append(text)
        elif tag == "p" and group.blocks:
            group.blocks[-1].paragraphs.append(text)


def parse_page(html: str) -> dict[tuple[str, str], dict[str, Group]]:
    """Parse the static summaries of a sub-bundle's ``index.html``.

    Raises:
        G15Error: A frequency block outside both groups.
    """
    page = _Page()
    page.feed(html)
    page.close()
    if page.stray:
        raise G15Error(f"frequency block(s) outside the Used and Not used groups: {page.stray}")
    return page.units


def label_prefix(disposition: Mapping[str, Any], *, sample: bool) -> str:
    """The words a heading must start its disposition label with (written independently)."""
    kind = disposition["kind"]
    if sample:
        if kind == "member":
            return "member"
        if kind == "merged":
            return f"merged into sample {disposition['merged_into_index']}"
        word = {"excluded": "excluded", "fell_through": "fell through"}[kind]
        return f"{word}: {disposition['reason_code']}"
    if kind == "superseded_by_push":
        return "superseded by push"
    if kind == "dropped":
        return f"dropped: {disposition['reason_code']}"
    return str(kind)


def _record_run(record: RunRecord, data: Mapping[str, Any], candidate: Mapping[str, Any]) -> Any:
    engines = {e["engine_id"]: e["name"] for e in data["provenance"]["engines"]}
    (run,) = [
        r
        for r in record.runs
        if (r.candidate_id, r.pathway, r.engine.name)
        == (candidate["candidate_id"], candidate["pathway"], engines[candidate["engine_id"]])
    ]
    return run


def disposition_gate(name: str, data: Mapping[str, Any], record: RunRecord) -> None:
    """Every sample and every minimum row has a recorded disposition, as the record lists them.

    Raises:
        G15Error: Naming the sub-bundle, the candidate and what is missing.
    """
    problems: list[Any] = []
    for c in data["candidates"]:
        run: RecordRun = _record_run(record, data, c)
        where = (name, c["candidate_id"], c["pathway"])
        samples = [(d["template_id"], d["sample_index"]) for d in c.get("sample_dispositions", [])]
        wanted = [(s.template_id, s.sample_index) for s in run.samples]
        if sorted(samples) != sorted(wanted):
            problems.append((*where, "samples", sorted(set(wanted) ^ set(samples))))
        named = {d["frequency_id"] for d in c.get("sample_dispositions", [])}
        if set(c["frequency_ids"]) - named:
            problems.append((*where, "TS row without disposition"))
        ends = [d["frequency_id"] for d in c.get("endpoint_dispositions", [])]
        if sorted(ends) != sorted(set(c["endpoint_frequency_ids"])):
            problems.append((*where, "endpoint dispositions differ from the rows"))
        for d in c.get("sample_dispositions", []):
            if d["reason_code"] == "not_recorded" or d["kind"] == "not_recorded":
                problems.append((*where, d["sample_index"], "not_recorded"))
            if d["frequency_id"] is not None and d["identity"] is None:
                problems.append((*where, d["sample_index"], "no TSIdentity"))
        problems.extend(
            (*where, d["frequency_id"], "not_recorded")
            for d in c.get("endpoint_dispositions", [])
            if d["kind"] == "not_recorded"
        )
    if problems:
        raise G15Error(f"disposition gate: {problems}")


def _identity_problem(block: Block, identity: Mapping[str, Any]) -> str | None:
    text = next((p for p in block.paragraphs if p.startswith("Identity: imaginary")), None)
    if text is None:
        return "no identity paragraph"
    overlap = identity["forming_overlap"]
    shown = "none" if overlap is None else f"{overlap:.3f}"
    if f"forming-bond overlap {shown};" not in text:
        return f"overlap differs: {text}"
    failed = not identity["passed_bool"]
    verdict = "FAIL (" if failed else "; pass"
    if verdict not in text:
        return f"verdict differs: {text}"
    if (BANNER in block.banner) != failed:
        return f"banner differs: passed_bool {identity['passed_bool']}, banner {block.banner!r}"
    return None


def page_gate(name: str, data: Mapping[str, Any], html: str) -> dict[str, int]:
    """Every frequency row and rowless sample is in its group, headed by its disposition.

    Returns:
        Counts of the blocks seen: TS and minimum blocks per group, rowless lines and banners.

    Raises:
        G15Error: Naming the sub-bundle, the unit and the row.
    """
    units = parse_page(html)
    frequencies = {f["frequency_id"]: f for f in data["frequencies"]}
    counts: Counter[str] = Counter()
    problems: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for c in data["candidates"]:
        key = (c["candidate_id"], f"Pathway {c['pathway']}, engine {c['engine_id']}")
        seen.add(key)
        groups = units.get(key)
        if groups is None or set(groups) != set(GROUP_TITLES):
            raise G15Error(f"{name} {key}: the page has no Used and Not used groups")
        problems.extend(
            (name, key, "group title", groups[css].title)
            for css, title in GROUP_TITLES.items()
            if groups[css].title != title
        )
        unmatched = {css: list(g.blocks) for css, g in groups.items()}
        lines = {css: list(g.lines) for css, g in groups.items()}
        rows = [(True, d) for d in c.get("sample_dispositions", [])]
        rows += [(False, d) for d in c.get("endpoint_dispositions", [])]
        for sample, d in rows:
            css = "used" if d["kind"] in ("member", "kept") else "notused"
            prefix = label_prefix(d, sample=sample)
            if d["frequency_id"] is None:
                start = f"Sample {d['sample_index']} ({d['source']}, template {d['template_id']}): "
                found = [x for x in lines[css] if x.startswith(start + prefix)]
                if not found:
                    problems.append((name, key, css, start + prefix, "line missing"))
                    continue
                lines[css].remove(found[0])
                counts[f"{css}_lines"] += 1
                continue
            short = frequencies[d["frequency_id"]]["stage_key"][:12]
            role = "Transition state: " if sample else "Minimum: "
            found_blocks = [
                b
                for b in unmatched[css]
                if b.heading.startswith(role)
                and f"{short})" in b.heading
                and _label_of(b.heading).startswith(prefix)
            ]
            if not found_blocks:
                problems.append((name, key, css, role + short, prefix, "block missing"))
                continue
            block = found_blocks[0]
            unmatched[css].remove(block)
            counts[f"{css}_{'ts' if sample else 'minimum'}"] += 1
            if sample:
                problem = _identity_problem(block, d["identity"])
                if problem:
                    problems.append((name, key, short, problem))
                counts["ts_banners"] += BANNER in block.banner
        for css in GROUP_TITLES:
            problems.extend((name, key, css, b.heading, "unexpected") for b in unmatched[css])
            problems.extend((name, key, css, x, "unexpected") for x in lines[css])
    problems.extend((name, k, "unit not in run_data") for k in units if k not in seen)
    if problems:
        raise G15Error(f"page gate: {problems}")
    return dict(counts)


def _label_of(heading: str) -> str:
    return heading.rsplit(" — ", 1)[-1]


def _clash_answers(name: str, data: Mapping[str, Any], html: str) -> list[dict[str, Any]]:
    """Known answer 1: the clashing sample of ethyl endo on GFN2, rowless and not used."""
    engines = {e["engine_id"]: e["name"] for e in data["provenance"]["engines"]}
    found = []
    for c in data["candidates"]:
        unit = (c["candidate_id"], c["pathway"])
        if unit != CLASH_CANDIDATE or engines[c["engine_id"]] != CLASH_ENGINE:
            continue
        (d,) = [
            x
            for x in c["sample_dispositions"]
            if x["sample_index"] == CLASH_SAMPLE and x["template_id"] == c["chosen_template_id"]
        ]
        clash = d["clash"] or {}
        got = (
            d["kind"],
            d["reason_code"],
            (clash.get("i"), clash.get("j")),
            None if not clash else round(clash["distance_angstrom"], 3),
            d["frequency_id"],
        )
        want = ("excluded", "seed_clash", CLASH_PAIR, CLASH_ANGSTROM, None)
        if got != want:
            raise G15Error(f"{name} sample {CLASH_SAMPLE}: {got}, expected {want}")
        group = parse_page(html)[(unit[0], f"Pathway {unit[1]}, engine {c['engine_id']}")]
        shown = [
            x
            for x in group["notused"].lines
            if x.startswith(f"Sample {CLASH_SAMPLE} (") and "excluded: seed_clash" in x
        ]
        if len(shown) != 1 or f"{CLASH_ANGSTROM:.3f} Å" not in shown[0]:
            raise G15Error(f"{name}: the page does not show the clash of sample {CLASH_SAMPLE}")
        found.append({"sub_bundle": name, "line": shown[0], "clash": clash})
    return found


def _superseded_answers(
    name: str, data: Mapping[str, Any], record: RunRecord, html: str
) -> list[dict[str, Any]]:
    """Known answer 2: the pre-push minimum is not used; its successor has the recorded kind."""
    engines = {e["engine_id"]: e["name"] for e in data["provenance"]["engines"]}
    rows = {f["frequency_id"]: f for f in data["frequencies"]}
    found = []
    for c in data["candidates"]:
        engine = engines[c["engine_id"]]
        if c["candidate_id"] != SUPERSEDED_CANDIDATE or engine != SUPERSEDED_ENGINE:
            continue
        by_id = {d["frequency_id"]: d for d in c["endpoint_dispositions"]}
        matches = [i for i in by_id if rows[i]["stage_key"].startswith(SUPERSEDED_KEY)]
        if not matches:
            continue
        (row_id,) = matches
        d = by_id[row_id]
        if d["kind"] != "superseded_by_push" or d["superseded_by_frequency_id"] not in by_id:
            raise G15Error(f"{name} {SUPERSEDED_KEY}: {d}")
        successor = by_id[d["superseded_by_frequency_id"]]
        key = rows[successor["frequency_id"]]["stage_key"]
        run = _record_run(record, data, c)
        (recorded,) = {
            (x.kind, x.reason)
            for endpoint in run.endpoints
            for x in endpoint.frequency_dispositions or []
            if x.frequency_key == key
        }
        if (successor["kind"], successor["reason_code"]) != recorded:
            raise G15Error(f"{name} successor {key[:12]}: {successor} but recorded {recorded}")
        groups = parse_page(html)[
            (c["candidate_id"], f"Pathway {c['pathway']}, engine {c['engine_id']}")
        ]
        headings = [b.heading for b in groups["notused"].blocks]
        shown = [h for h in headings if f"{SUPERSEDED_KEY})" in h]
        if len(shown) != 1:
            raise G15Error(f"{name}: {SUPERSEDED_KEY} is not in the Not used group")
        found.append(
            {
                "sub_bundle": name,
                "pathway": c["pathway"],
                "heading": shown[0],
                "successor": key[:12],
                "successor_kind": successor["kind"],
                "successor_reason": successor["reason_code"],
            }
        )
    return found


def g15_gate(root: Path, records: Mapping[str, RunRecord]) -> dict[str, Any]:
    """Run every G15 gate over the sub-bundles ``records`` names (sub-bundle name -> its record).

    Returns:
        The block counts per sub-bundle and the known answers.

    Raises:
        G15Error: The first gate that fails, or a known answer that no sub-bundle shows.
    """
    report: dict[str, Any] = {"sub_bundles": {}, "known_clash": [], "known_superseded": []}
    for name, record in sorted(records.items()):
        data = json.loads((root / name / "run_data.json").read_bytes())
        html = (root / name / "index.html").read_text(encoding="utf-8")
        disposition_gate(name, data, record)
        report["sub_bundles"][name] = page_gate(name, data, html)
        report["known_clash"] += _clash_answers(name, data, html)
        report["known_superseded"] += _superseded_answers(name, data, record, html)
    missing = [k for k in ("known_clash", "known_superseded") if not report[k]]
    if missing:
        raise G15Error(f"known answer(s) shown by no sub-bundle: {missing}")
    return report
