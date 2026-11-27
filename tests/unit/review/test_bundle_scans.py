"""Scans of a written bundle: no network reference, no host data, no script sink; stable bytes."""

import getpass
import hashlib
import re
import socket
from pathlib import Path

import pytest
from bundle_helpers import exported, hostile
from review_helpers import SECRET
from test_assets import LICENSE_SHA256, MIN_JS_SHA256

from eta_rxncat.review import RunData, write_review_bundle
from eta_rxncat.review.bundle import ASSETS_PATH

REPO = Path(__file__).parents[3]
VENDORED = {"3Dmol-min.js"}
PINNED_SHA256 = frozenset({MIN_JS_SHA256, LICENSE_SHA256})
"""The pin source: the vendored assets' sha256 in ``test_assets.py`` (as in ``assets/SOURCES.md``).

A file with these exact bytes is third-party text eta cannot have written host data into, and a
short user or host name can match inside it by chance (R40).
"""
IN_PINNED_ONLY = "Float32Array"
"""A word of the pinned 3Dmol build that no other bundle file holds."""
SINKS = {
    "innerHTML": r"innerHTML",
    "outerHTML": r"outerHTML",
    "insertAdjacentHTML": r"insertAdjacentHTML",
    "document.write": r"document\s*\.\s*write",
    "eval": r"\beval\s*\(",
    "Function": r"\bFunction\s*\(",
    "string timer": r"\bset(Timeout|Interval)\s*\(\s*[\"'`]",
    "fetch": r"\bfetch\s*\(",
    "module": r"^\s*(import|export)\b",
}


@pytest.fixture(params=["plain", "hostile"])
def bundle(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """Write the plain and the hostile bundle."""
    run_data: RunData = exported(tmp_path) if request.param == "plain" else hostile(tmp_path)
    return write_review_bundle(run_data, tmp_path / "bundle")


def contents(root: Path) -> dict[str, bytes]:
    """Return every file of the bundle by relative path."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def sinks_in(source: str) -> list[str]:
    """Return the names of the script sinks found in ``source``."""
    return [name for name, pattern in SINKS.items() if re.search(pattern, source, re.MULTILINE)]


def test_no_network_reference_in_any_src_or_href(bundle: Path) -> None:
    """No ``src`` or ``href`` points at the network."""
    pattern = re.compile(rb"""\b(?:src|href)\s*=\s*["']?\s*(?:https?:)?//""", re.IGNORECASE)
    for name, content in contents(bundle).items():
        assert not pattern.search(content), name


def test_every_reference_is_a_vendored_file_or_an_anchor(bundle: Path) -> None:
    """Every reference is a bundled file or an anchor."""
    html = (bundle / "index.html").read_text(encoding="utf-8")
    references = re.findall(r'<(?:script|a|link|img)[^>]*?\s(?:src|href)="([^"]*)"', html)
    assert references
    for reference in references:
        assert reference.startswith("#") or (bundle / reference).is_file(), reference


def test_no_host_data_in_any_file(bundle: Path, tmp_path: Path) -> None:
    """No file eta wrote holds a local path, the user name or the host name."""
    forbidden = {
        str(tmp_path),
        str(REPO),
        str(Path.home()),
        "/home/",
        "/Users/",
        "/tmp/",
        SECRET,
        getpass.getuser(),
        socket.gethostname(),
    }
    for name, content in contents(bundle).items():
        if hashlib.sha256(content).hexdigest() in PINNED_SHA256:
            continue
        for item in forbidden:
            assert item.encode() not in content, (name, item)


def stand_in(monkeypatch: pytest.MonkeyPatch, kind: str, name: str) -> None:
    """Make ``name`` the user name or the host name the scan looks for."""
    if kind == "user":
        monkeypatch.setattr(getpass, "getuser", lambda: name)
    else:
        monkeypatch.setattr(socket, "gethostname", lambda: name)


@pytest.mark.parametrize("kind", ["user", "host"])
def test_the_host_data_scan_skips_the_pinned_3dmol_file(
    bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A name that only the pinned 3Dmol build happens to contain is not a finding (R40)."""
    holders = [n for n, c in contents(bundle).items() if IN_PINNED_ONLY.encode() in c]
    assert holders == ["assets/3Dmol-min.js"]
    stand_in(monkeypatch, kind, IN_PINNED_ONLY)
    test_no_host_data_in_any_file(bundle, tmp_path)


@pytest.mark.parametrize("name", ["assets/eta-view.js", "index.html", "assets/3Dmol-min.js"])
@pytest.mark.parametrize("kind", ["user", "host"])
def test_the_host_data_scan_finds_a_planted_name(
    bundle: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, name: str
) -> None:
    """A name planted in any file is found, the 3Dmol build too once its bytes leave the pin."""
    planted = "planted-name-r40"
    stand_in(monkeypatch, kind, planted)
    with (bundle / name).open("ab") as handle:
        handle.write(planted.encode())
    with pytest.raises(AssertionError, match=planted):
        test_no_host_data_in_any_file(bundle, tmp_path)


def test_eta_scripts_use_no_sink(bundle: Path) -> None:
    """Every script eta wrote passes the sink scan."""
    scripts = [p for p in bundle.rglob("*.js") if p.name not in VENDORED]
    assert [p.name for p in scripts] == ["eta-view.js"]
    for script in scripts:
        assert sinks_in(script.read_text(encoding="utf-8")) == []
    shipped = [p for p in ASSETS_PATH.glob("*.js") if p.name not in VENDORED]
    assert [p.name for p in shipped] == ["eta-view.js"]


@pytest.mark.parametrize(
    "source",
    [
        "a.innerHTML = b",
        "a.outerHTML = b",
        "a.insertAdjacentHTML('beforeend', b)",
        "document.write(b)",
        "eval(b)",
        "new Function(b)",
        "setTimeout('f()', 1)",
        "setInterval( `f()`, 1)",
        "fetch('x')",
        "import x from 'y';",
    ],
)
def test_the_sink_scan_finds_each_sink(source: str) -> None:
    """The scan catches each forbidden sink."""
    assert sinks_in(source)


def test_the_sink_scan_allows_safe_calls() -> None:
    """The scan accepts safe DOM calls."""
    assert sinks_in("el.textContent = v; el.setAttribute('a', v); setTimeout(step, 10);") == []


def test_two_writes_are_byte_identical(tmp_path: Path) -> None:
    """Two writes of one document give the same bytes."""
    first = write_review_bundle(exported(tmp_path), tmp_path / "one")
    second = write_review_bundle(exported(tmp_path), tmp_path / "two")
    assert contents(first) == contents(second)
