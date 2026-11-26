"""The review bundle writer: layout, manifest, embedded bytes, static summary and policy."""

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from bundle_helpers import exported, hostile, with_modes

from eta_rxncat.review import BundleError, canonical_run_data_json, write_review_bundle
from eta_rxncat.review.bundle import CONTENT_SECURITY_POLICY

LAYOUT = [
    "MANIFEST.sha256",
    "assets/3Dmol-min.js",
    "assets/LICENSE-3Dmol.txt",
    "assets/eta-view.js",
    "index.html",
    "run_data.json",
]


class Page(HTMLParser):
    """Collects the page's elements and the text of the embedded data element."""

    def __init__(self, html: str) -> None:
        """Parse ``html``."""
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.data = ""
        self.text: list[str] = []
        self._in_data = False
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record the element and whether it is the data element."""
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        self._in_data = tag == "script" and attributes.get("id") == "run-data"

    def handle_endtag(self, tag: str) -> None:
        """Leave the data element."""
        self._in_data = False

    def handle_data(self, data: str) -> None:
        """Collect data-element text apart from page text."""
        if self._in_data:
            self.data += data
        else:
            self.text.append(data)

    def of(self, tag: str) -> list[dict[str, str | None]]:
        """Return the attributes of every ``tag`` element."""
        return [a for t, a in self.elements if t == tag]

    def banners(self) -> list[str]:
        """Return one entry per banner element."""
        return [a.get("class") or "" for t, a in self.elements if a.get("class") == "banner"]


def files_of(root: Path) -> list[str]:
    """Return the files under ``root`` as sorted relative paths."""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def page_of(root: Path) -> Page:
    """Parse the bundle's page."""
    return Page((root / "index.html").read_text(encoding="utf-8"))


def test_layout_and_manifest(tmp_path: Path) -> None:
    """The bundle holds the stated files and its manifest verifies."""
    out = write_review_bundle(exported(tmp_path), tmp_path / "bundle")
    assert files_of(out) == LAYOUT
    lines = (out / "MANIFEST.sha256").read_text().splitlines()
    assert [line.split("  ", 1)[1] for line in lines] == LAYOUT[1:]
    for line in lines:
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest


def test_embedded_bytes_are_the_json_file(tmp_path: Path) -> None:
    """The embedded data is byte-equal to run_data.json."""
    run_data = exported(tmp_path)
    out = write_review_bundle(run_data, tmp_path / "bundle")
    html = (out / "index.html").read_bytes()
    opening = b'<script type="application/json" id="run-data">'
    assert html.count(opening) == 1
    embedded = html.split(opening, 1)[1].split(b"</script>", 1)[0]
    assert embedded == (out / "run_data.json").read_bytes() == canonical_run_data_json(run_data)


def test_scripts_are_classic_local_files_after_the_data(tmp_path: Path) -> None:
    """Only local classic scripts; no inline code or handlers."""
    page = page_of(write_review_bundle(exported(tmp_path), tmp_path / "bundle"))
    scripts = page.of("script")
    assert scripts == [
        {"type": "application/json", "id": "run-data"},
        {"src": "assets/3Dmol-min.js"},
        {"src": "assets/eta-view.js"},
    ]
    assert not [a for _, a in page.elements for name in a if name.startswith("on")]


def test_policy_is_the_stated_one_and_first(tmp_path: Path) -> None:
    """The policy meta carries the stated policy, before any content."""
    page = page_of(write_review_bundle(exported(tmp_path), tmp_path / "bundle"))
    policy = (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'none'"
    )
    assert CONTENT_SECURITY_POLICY == policy
    metas = page.of("meta")
    assert metas[1] == {"http-equiv": "Content-Security-Policy", "content": policy}


def test_hostile_strings_are_inert(tmp_path: Path) -> None:
    """Hostile strings add no element and show as text."""
    run_data = hostile(tmp_path)
    out = write_review_bundle(run_data, tmp_path / "bundle")
    html = (out / "index.html").read_bytes()
    assert b"<img" not in html
    assert b"<!--" not in html
    assert " ".encode() not in html.split(b'id="run-data">', 1)[1]
    page = page_of(out)
    assert len(page.of("script")) == 3 and not page.of("img")
    assert json.loads(page.data) == json.loads(canonical_run_data_json(run_data))
    ids = [a["id"] for a in page.of("section")]
    assert ids == [f"c/{c.candidate_id}" for c in run_data.candidates]
    assert any("onerror=alert(1)" in t for t in page.text)  # shown as text


def test_index_table_links_each_candidate_and_shows_gates(tmp_path: Path) -> None:
    """The index links the candidate section and shows its gates."""
    run_data = exported(tmp_path)
    page = page_of(write_review_bundle(run_data, tmp_path / "bundle"))
    assert {"href": "#c/r=ethyl"} in page.of("a")
    assert [a["id"] for a in page.of("section")] == ["c/r=ethyl"]
    text = "".join(page.text)
    assert "graft_rmsd: PASS value 0.05 threshold 0.15 angstrom" in text
    panels = [a for a in page.of("div") if a.get("class") == "eta-panels"]
    assert panels == [{"class": "eta-panels", "data-candidate": "r=ethyl"}]


def test_a_failed_gate_is_marked(tmp_path: Path) -> None:
    """A failed gate is marked as failed."""
    data = exported(tmp_path).model_dump(mode="json")
    data["gates"][0]["pass_bool"] = False
    run_data = type(exported(tmp_path)).model_validate(data)
    html = (write_review_bundle(run_data, tmp_path / "bundle") / "index.html").read_text()
    assert 'class="badge fail">graft_rmsd: FAIL' in html


def test_one_imaginary_ts_has_no_banner(tmp_path: Path) -> None:
    """A TS with one imaginary mode raises no banner."""
    run_data = with_modes(exported(tmp_path), ts=1)
    page = page_of(write_review_bundle(run_data, tmp_path / "bundle"))
    assert not page.banners()


@pytest.mark.parametrize("count", [0, 2])
def test_banner_on_a_ts_with_the_wrong_count(tmp_path: Path, count: int) -> None:
    """A TS with 0 or 2 imaginary modes raises the banner."""
    run_data = with_modes(exported(tmp_path), ts=count)
    out = write_review_bundle(run_data, tmp_path / "bundle")
    page = page_of(out)
    assert len(page.banners()) == 1
    text = "".join(page.text)
    assert f"Transition state has {count} imaginary mode(s); expected 1." in text
    assert f"n_imaginary = {count}" in text


def test_imaginary_frequencies_are_marked_red(tmp_path: Path) -> None:
    """Imaginary frequencies are listed in red."""
    run_data = with_modes(exported(tmp_path), ts=2)
    html = (write_review_bundle(run_data, tmp_path / "bundle") / "index.html").read_text()
    assert re.findall(r'<span class="imag">([^<]+)</span>', html) == ["-500.0", "-501.0"]
    assert ".imag { color: #c00000;" in html


@pytest.mark.parametrize(("count", "banners"), [(0, 0), (1, 1), (2, 1)])
def test_banner_on_a_minimum_with_an_imaginary_mode(
    tmp_path: Path, count: int, banners: int
) -> None:
    """A minimum raises the banner from one imaginary mode."""
    run_data = with_modes(exported(tmp_path), ts=1, minimum=count)
    page = page_of(write_review_bundle(run_data, tmp_path / "bundle"))
    assert len(page.banners()) == banners
    if banners:
        assert f"Minimum has {count} imaginary mode(s); expected 0." in "".join(page.text)


def test_missing_and_failed_frequencies_are_stated(tmp_path: Path) -> None:
    """Missing and failed frequencies are stated, not skipped."""
    data = exported(tmp_path).model_dump(mode="json")
    (missing,) = [f for f in data["frequencies"] if f["status"] == "missing"]
    html = (
        write_review_bundle(type(exported(tmp_path)).model_validate(data), tmp_path / "a")
        / "index.html"
    ).read_text()
    assert "Frequencies missing from the store" in html
    index = data["frequencies"].index(missing)
    data["frequencies"][index] = {**missing, "status": "failed", "failed_code": "scf_convergence"}
    run_data = type(exported(tmp_path)).model_validate(data)
    html = (write_review_bundle(run_data, tmp_path / "b") / "index.html").read_text()
    assert "Frequencies failed: scf_convergence" in html


def test_a_run_without_ts_frequencies_says_why(tmp_path: Path) -> None:
    """A run without TS frequencies shows its stop reason."""
    data = exported(tmp_path).model_dump(mode="json")
    unit = data["candidates"][0]
    unit["frequency_ids"] = []
    unit["stop_reason_code"] = "templates_exhausted"
    for member in unit["members"]:
        member["frequency_id"] = None
    run_data = type(exported(tmp_path)).model_validate(data)
    html = (write_review_bundle(run_data, tmp_path / "bundle") / "index.html").read_text()
    assert "No transition-state frequencies for this run: templates_exhausted" in html


def test_a_non_empty_directory_is_refused_and_untouched(tmp_path: Path) -> None:
    """A non-empty directory is refused and left alone."""
    out = tmp_path / "bundle"
    out.mkdir()
    (out / "keep.txt").write_text("mine")
    with pytest.raises(BundleError, match="not empty"):
        write_review_bundle(exported(tmp_path), out)
    assert files_of(out) == ["keep.txt"]


def test_a_file_as_the_output_is_refused(tmp_path: Path) -> None:
    """A file as the output path is refused."""
    (tmp_path / "f").write_text("x")
    with pytest.raises(BundleError):
        write_review_bundle(exported(tmp_path), tmp_path / "f")


def test_an_empty_directory_is_used(tmp_path: Path) -> None:
    """An existing empty directory is used."""
    (tmp_path / "empty").mkdir()
    assert files_of(write_review_bundle(exported(tmp_path), tmp_path / "empty")) == LAYOUT
