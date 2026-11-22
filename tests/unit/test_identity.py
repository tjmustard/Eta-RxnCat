"""Author-name guard: every author form this project writes is the canonical one (slice 08).

Pure filesystem: no git, no network. The pattern and the canonical string are assembled from
pieces, so this file never contains a literal author form and does not flag itself.
"""

import json
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).parents[2]
SURNAME = "Mus" + "tard"
CANONICAL = " ".join(["Thomas", "J.", "L.", SURNAME]) + " Ph.D."
AUTHOR = re.compile(
    r"(?:Thomas|Tom|TJ|T\.)(?:\s+[A-Z]\.)*\s+" + SURNAME + r"(?:,?\s*Ph\.?\s*D\.?)?"
)
HACF_END = "<!-- END HACF MANAGED BLOCK: hacf -->"

SCANNED_FILES = ("README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml", "AGENTS.md")
SCANNED_TREES = ("src", "tests", "docs", ".github")
EXCLUDED = (
    "PRDs",
    ".agents",
    ".claude",
    "CLAUDE.md",
    "HACF-uninstall.sh",
    "docs/prd",
    "missions",
    "lore",
    "spec",
)


def is_excluded(relative: Path) -> bool:
    """Return whether a repo-relative path lies under a path the guard must never read."""
    text = relative.as_posix()
    return any(text == ex or text.startswith(ex + "/") for ex in EXCLUDED)


def identity_paths(root: Path) -> list[Path]:
    """Return the files the guard scans under ``root``, never descending into excluded paths."""
    paths = [root / name for name in SCANNED_FILES if (root / name).is_file()]
    for tree in SCANNED_TREES:
        base = root / tree
        if not base.is_dir() or is_excluded(base.relative_to(root)):
            continue
        stack = [base]
        while stack:
            directory = stack.pop()
            for entry in sorted(directory.iterdir()):
                relative = entry.relative_to(root)
                if is_excluded(relative) or entry.name in {"__pycache__", ".pytest_cache"}:
                    continue
                if entry.is_dir():
                    stack.append(entry)
                elif entry.is_file():
                    paths.append(entry)
    return sorted(paths)


def _scan_text(path: Path, root: Path) -> tuple[int, str]:
    """Return ``(first line number, text)`` to scan; AGENTS.md only after the HACF END marker.

    A binary file (an image, a compiled cache) yields empty text.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return 1, ""
    if path.resolve() == (root / "AGENTS.md").resolve():
        lines = text.splitlines(keepends=True)
        end = next((i for i, line in enumerate(lines) if line.strip() == HACF_END), None)
        if end is not None:
            return end + 2, "".join(lines[end + 1 :])
    return 1, text


def find_author_violations(root: Path, paths: Iterable[Path]) -> list[str]:
    """Return ``path:line: text`` for every author form under ``root`` that is not canonical.

    The pattern runs over each file's whole text, so a form wrapped across lines is found; a
    match is judged with its whitespace collapsed (a canonical form wrapped at a space passes)
    and reported at the line where it starts. Excluded paths are skipped even if passed in, so
    the guard never reads them.
    """
    violations = []
    for path in paths:
        relative = path.relative_to(root) if path.is_absolute() else path
        if is_excluded(relative):
            continue
        first_line, text = _scan_text(root / relative, root)
        for match in AUTHOR.finditer(text):
            if " ".join(match.group(0).split()) != CANONICAL:
                number = first_line + text.count("\n", 0, match.start())
                violations.append(f"{relative.as_posix()}:{number}: {match.group(0)!r}")
    return violations


def test_repo_uses_only_the_canonical_author() -> None:
    """No scanned file in the repo writes the author any other way."""
    assert find_author_violations(REPO, identity_paths(REPO)) == []


@pytest.mark.parametrize("name", ["LICENSE", "README.md", "pyproject.toml"])
def test_canonical_form_present(name: str) -> None:
    """LICENSE, README.md and pyproject.toml each contain the canonical author at least once."""
    assert CANONICAL in (REPO / name).read_text(encoding="utf-8")


def test_license_line_three() -> None:
    """LICENSE line 3 is the copyright line in the canonical form."""
    assert (REPO / "LICENSE").read_text(encoding="utf-8").splitlines()[2] == (
        f"Copyright (c) 2026 {CANONICAL}"
    )


def test_scan_set_never_includes_excluded_paths() -> None:
    """The repo scan set holds the listed files and trees and nothing under an excluded path."""
    scanned = [p.relative_to(REPO) for p in identity_paths(REPO)]
    assert not [p for p in scanned if is_excluded(p)]
    names = {p.as_posix() for p in scanned}
    assert {"README.md", "CHANGELOG.md", "LICENSE", "pyproject.toml", "AGENTS.md"} <= names
    assert any(n.startswith("src/") for n in names) and any(n.startswith("tests/") for n in names)
    assert any(n.startswith(".github/") for n in names)


VARIANTS = [
    f"Thomas {SURNAME}",
    f"Thomas J. {SURNAME}",
    f"T. J. L. {SURNAME}",
    f"Thomas J. L. {SURNAME}, PhD",
    f"Thomas J. L. {SURNAME}",
    f"Thomas J. L. {SURNAME} PhD",
    f"Thomas J. L. {SURNAME} Ph.D",
    f"Tom {SURNAME}",
    f"TJ {SURNAME}",
]


@pytest.mark.parametrize("variant", VARIANTS)
def test_scanner_flags_variant(tmp_path: Path, variant: str) -> None:
    """Each non-canonical author form is reported with its file, line and text."""
    (tmp_path / "README.md").write_text(f"intro\nby {variant} here\n", encoding="utf-8")
    violations = find_author_violations(tmp_path, identity_paths(tmp_path))
    assert len(violations) == 1
    assert violations[0].startswith("README.md:2: ") and variant in violations[0]


@pytest.mark.parametrize(
    ("text", "line"),
    [
        (f"x\nby Thomas J. L.\n  {SURNAME}, PhD here\n", 2),
        (f"Thomas\n{SURNAME}\n", 1),
        (f"a\nb\nwritten by T. J.\nL. {SURNAME}\n", 3),
    ],
    ids=["initials-then-surname", "first-name-then-surname", "initials-split"],
)
def test_scanner_flags_wrapped_variant(tmp_path: Path, text: str, line: int) -> None:
    """A non-canonical form wrapped across lines is reported at the line where it starts."""
    (tmp_path / "README.md").write_text(text, encoding="utf-8")
    violations = find_author_violations(tmp_path, identity_paths(tmp_path))
    assert len(violations) == 1 and violations[0].startswith(f"README.md:{line}: ")


@pytest.mark.parametrize(
    "text",
    [
        f"Copyright Thomas J. L. {SURNAME}\nPh.D.\n",
        f"by Thomas J.\n   L. {SURNAME} Ph.D. and others\n",
    ],
    ids=["wrapped-before-suffix", "wrapped-inside-initials"],
)
def test_scanner_accepts_wrapped_canonical(tmp_path: Path, text: str) -> None:
    """The canonical form wrapped at a space is accepted (whitespace collapsed)."""
    (tmp_path / "LICENSE").write_text(text, encoding="utf-8")
    assert find_author_violations(tmp_path, identity_paths(tmp_path)) == []


def test_agents_md_wrapped_variant_reports_file_line(tmp_path: Path) -> None:
    """In AGENTS.md the reported line counts from the top of the file, after the HACF block."""
    agents = f"one\ntwo\n{HACF_END}\nrules\nby Tom\n{SURNAME}\n"
    (tmp_path / "AGENTS.md").write_text(agents, encoding="utf-8")
    violations = find_author_violations(tmp_path, identity_paths(tmp_path))
    assert len(violations) == 1 and violations[0].startswith("AGENTS.md:5: ")


def test_scanner_accepts_canonical_and_citation(tmp_path: Path) -> None:
    """The canonical form and a surname-first bibliographic citation pass."""
    text = (
        f"Copyright {CANONICAL}\n{SURNAME}, T. J. L.; Wender, P. A.; Cheong, P. H.-Y. ACS Catal.\n"
    )
    (tmp_path / "LICENSE").write_text(text, encoding="utf-8")
    assert find_author_violations(tmp_path, identity_paths(tmp_path)) == []


@pytest.mark.parametrize(
    "excluded", ["docs/prd/x.md", "PRDs/plan.md", "missions/m/SPEC.md", "spec/a.md"]
)
def test_scanner_skips_excluded_paths(tmp_path: Path, excluded: str) -> None:
    """A violation under an excluded path is neither collected nor reported."""
    target = tmp_path / excluded
    target.parent.mkdir(parents=True)
    target.write_text(f"Thomas {SURNAME}\n", encoding="utf-8")
    (tmp_path / "docs" / "ok.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "ok.md").write_text("fine\n", encoding="utf-8")
    assert target not in identity_paths(tmp_path)
    assert find_author_violations(tmp_path, [target]) == []


def test_scanner_reads_docs_outside_prd(tmp_path: Path) -> None:
    """docs/** outside docs/prd/** is scanned."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text(f"Thomas {SURNAME}\n", encoding="utf-8")
    assert find_author_violations(tmp_path, identity_paths(tmp_path)) == [
        f"docs/guide.md:1: 'Thomas {SURNAME}'"
    ]


def test_agents_md_scanned_only_after_hacf_block(tmp_path: Path) -> None:
    """In AGENTS.md only the text after the HACF END marker is scanned."""
    agents = f"inside block {'Thomas ' + SURNAME}\n{HACF_END}\nproject rules by Tom {SURNAME}\n"
    (tmp_path / "AGENTS.md").write_text(agents, encoding="utf-8")
    assert find_author_violations(tmp_path, identity_paths(tmp_path)) == [
        f"AGENTS.md:3: 'Tom {SURNAME}'"
    ]


def test_binary_files_are_skipped(tmp_path: Path) -> None:
    """Undecodable (binary) files are skipped rather than crashing the scan."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "blob.bin").write_bytes(b"\xff\xfe\x00" + f"Thomas {SURNAME}".encode())
    assert find_author_violations(tmp_path, identity_paths(tmp_path)) == []


README_SECTIONS = [
    "What is Eta-RxnCat?",
    "Features (v0.1.0)",
    "Installation",
    "Usage",
    "Development",
    "Roadmap",
    "Acknowledgements",
    "License",
]


def github_anchor(heading: str) -> str:
    """Return the GitHub anchor of a Markdown heading (lowercase, punctuation and emoji dropped)."""
    text = heading.strip().lower()
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return "#" + text.replace(" ", "-")


def readme() -> str:
    """Return the README text."""
    return (REPO / "README.md").read_text(encoding="utf-8")


def test_readme_header_and_banner() -> None:
    """Centered logo header with the Eta-RxnCat h1 and an italic tagline, then the banner."""
    lines = readme().splitlines()
    assert lines[0] == '<div align="center">'
    logo = "./media/icons/web/icon-256.webp"
    assert lines[1].strip() == f'<img src="{logo}" alt="Eta-RxnCat logo" width="200" height="200"/>'
    assert lines[2].strip() == "<h1>Eta-RxnCat</h1>"
    assert re.fullmatch(r"<h3><em>[^<]+</em></h3>", lines[3].strip())
    assert lines[4] == "</div>"
    following = [line for line in lines[5:] if line.strip()][0]
    banner = '<img src="./media/banner/banner-1024x573.webp" alt="Eta-RxnCat banner" width="100%"/>'
    assert following == f'<p align="center">{banner}</p>'


def test_readme_pitch_and_badges() -> None:
    """A bold centered pitch and the four badges for github.com/tjmustard/Eta-RxnCat."""
    text = readme()
    assert re.search(r'<p align="center">\s*<strong>[^<]+</strong>\s*</p>', text)
    repo = "tjmustard/Eta-RxnCat"
    for needle in (
        f'href="https://github.com/{repo}/releases/latest"><img src="https://img.shields.io/badge/release-v0.1.0-blue"',
        f'src="https://github.com/{repo}/actions/workflows/ci.yml/badge.svg"',
        f'src="https://img.shields.io/github/stars/{repo}?style=social"',
        f'src="https://img.shields.io/github/license/{repo}"',
    ):
        assert needle in text, needle


def test_readme_sections_and_toc() -> None:
    """The eight emoji-prefixed sections appear in order, and every TOC link hits a heading."""
    text = readme()
    headings = [line[3:] for line in text.splitlines() if line.startswith("## ")]
    assert headings[0] == "Table of Contents"
    titles = [h.split(" ", 1)[1] for h in headings[1:]]
    assert titles == README_SECTIONS
    assert all(not h[0].isascii() for h in headings[1:])  # emoji prefix
    anchors = {github_anchor(h) for h in re.findall(r"^#{2,6} (.+)$", text, flags=re.M)}
    toc = text.split("## Table of Contents", 1)[1].split("\n## ", 1)[0]
    links = re.findall(r"\]\((#[^)]+)\)", toc)
    assert len(links) == len(README_SECTIONS)
    assert [link for link in links if link not in anchors] == []
    body_links = re.findall(r"\]\((#[^)]+)\)", text)
    assert [link for link in body_links if link not in anchors] == []


def test_readme_slice01_requirements_kept() -> None:
    """The nMap DOI, Eta_Scripts credit, uv quickstart and licensing section survive."""
    text = readme()
    assert "10.1021/cs501828e" in text and "Eta_Scripts" in text
    assert "uv sync" in text and "uv run pytest" in text
    assert "## 📄 License" in text and "MIT" in text
    assert "### Planned, not yet built" in text
    for version in ("v0.2.0", "v0.5.0", "v1.0.0"):
        assert f"**{version}**" in text.split("## 🧭 Roadmap", 1)[1]


GPU_PASS_PHRASE = "GPU acceptance passed"
GPU_NOT_RECORDED_PHRASE = "GPU acceptance run has not been recorded yet"


def check_gpu_claim(readme_text: str, record: dict[str, Any] | None, version: str) -> list[str]:
    """Return violations of the README's GPU-acceptance claim against the acceptance record (R54).

    With a passing record (``smoke.status == "pass"``) the README must say the pass phrase, link
    ``docs/prd/v<version>/GPU_SMOKE_RESULT.json`` and name the record's GPU verbatim, and must not
    say the not-recorded phrase. Without one (no record, or not a pass) it must not say the pass
    phrase. Phrases are matched after whitespace normalisation.
    """
    text = " ".join(readme_text.split())
    passing = record is not None and record.get("smoke", {}).get("status") == "pass"
    problems = []
    if not passing:
        if GPU_PASS_PHRASE in text:
            state = "no record" if record is None else "a record that is not a pass"
            problems.append(f"README says {GPU_PASS_PHRASE!r} but there is {state}")
        return problems
    assert record is not None
    if GPU_PASS_PHRASE not in text:
        problems.append(f"passing record, but the README lacks {GPU_PASS_PHRASE!r}")
    if GPU_NOT_RECORDED_PHRASE in text:
        problems.append(f"passing record, but the README still says {GPU_NOT_RECORDED_PHRASE!r}")
    target = rf"(?:\./)?docs/prd/v{re.escape(version)}/GPU_SMOKE_RESULT\.json"
    if not re.search(rf"\]\(\s*{target}\s*\)", text):
        problems.append(
            f"passing record, but no Markdown link to docs/prd/v{version}/GPU_SMOKE_RESULT.json"
        )
    gpu_name = str(record.get("hardware", {}).get("gpu", {}).get("name", ""))
    if not gpu_name or gpu_name not in text:
        problems.append(f"passing record, but the README does not name the GPU {gpu_name!r}")
    return problems


def test_readme_gpu_claim_matches_record_and_no_pip_licenses() -> None:
    """The README GPU claim follows the acceptance record; the licence gate text is current."""
    text = readme()
    version = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    record_path = REPO / "docs" / "prd" / f"v{version}" / "GPU_SMOKE_RESULT.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else None
    assert check_gpu_claim(text, record, version) == []
    assert "pip-licenses" not in text
    assert "tools/licence_gate.py" in text


PASSING_RECORD: dict[str, Any] = {
    "smoke": {"status": "pass"},
    "hardware": {"gpu": {"name": "NVIDIA GeForce RTX 5060 Ti"}},
}
FAILING_RECORD: dict[str, Any] = {
    "smoke": {"status": "fail"},
    "hardware": {"gpu": {"name": "NVIDIA GeForce RTX 5060 Ti"}},
}
LINK = "[GPU_SMOKE_RESULT.json](docs/prd/v0.1.0/GPU_SMOKE_RESULT.json)"
GOOD_CLAIM = (
    f"{GPU_PASS_PHRASE} on an NVIDIA GeForce RTX 5060 Ti\n(compute capability 12.0); see {LINK}."
)


@pytest.mark.parametrize(
    ("readme_text", "record"),
    [
        (GOOD_CLAIM, None),
        (GOOD_CLAIM, FAILING_RECORD),
        (f"the {GPU_NOT_RECORDED_PHRASE}.", PASSING_RECORD),
        (f"{GPU_PASS_PHRASE} on an NVIDIA GeForce RTX 5060 Ti.", PASSING_RECORD),
        (f"{GPU_PASS_PHRASE} on an NVIDIA GeForce RTX 4090; see {LINK}.", PASSING_RECORD),
        (f"{GOOD_CLAIM} Also the {GPU_NOT_RECORDED_PHRASE}.", PASSING_RECORD),
    ],
    ids=[
        "a-pass-without-record",
        "b-pass-with-failing-record",
        "c-not-recorded-with-passing-record",
        "d-no-record-link",
        "e-wrong-gpu-name",
        "f-both-phrases",
    ],
)
def test_gpu_claim_violations(readme_text: str, record: dict[str, Any] | None) -> None:
    """Each wrong combination of README claim and record yields at least one violation."""
    assert len(check_gpu_claim(readme_text, record, "0.1.0")) >= 1


@pytest.mark.parametrize(
    ("readme_text", "record"),
    [
        (GOOD_CLAIM, PASSING_RECORD),
        (f"the {GPU_NOT_RECORDED_PHRASE}.", None),
        ("the GPU acceptance run has not\n  been recorded yet.", FAILING_RECORD),
    ],
    ids=["g-correct-claim", "h-no-record-not-recorded", "i-failing-record-not-recorded"],
)
def test_gpu_claim_consistent(readme_text: str, record: dict[str, Any] | None) -> None:
    """A claim that matches the record yields no violations (phrases match across line breaks)."""
    assert check_gpu_claim(readme_text, record, "0.1.0") == []


def test_gpu_claim_link_forms() -> None:
    """The link may be docs/... or ./docs/...; a link for another version does not count."""
    base = f"{GPU_PASS_PHRASE} on an NVIDIA GeForce RTX 5060 Ti; see [r]"
    assert (
        check_gpu_claim(
            base + "(./docs/prd/v0.1.0/GPU_SMOKE_RESULT.json).", PASSING_RECORD, "0.1.0"
        )
        == []
    )
    assert (
        check_gpu_claim(base + "(docs/prd/v0.2.0/GPU_SMOKE_RESULT.json).", PASSING_RECORD, "0.1.0")
        != []
    )
