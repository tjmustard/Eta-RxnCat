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


PLAN_VERSIONS = tuple(f"0.{m}.0" for m in range(1, 10)) + ("1.0.0",)
"""Every version in the master plan's roadmap, in order (R50)."""


def project_version() -> str:
    """``[project].version`` from ``pyproject.toml``."""
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def readme_sections(version: str) -> list[str]:
    """The eight README section titles at ``version`` (the Features title carries the version)."""
    return [
        "What is Eta-RxnCat?",
        f"Features (v{version})",
        "Installation",
        "Usage",
        "Development",
        "Roadmap",
        "Acknowledgements",
        "License",
    ]


def _bold_versions(text: str) -> set[str]:
    """The ``**vX.Y.Z**`` versions named in ``text``."""
    return set(re.findall(r"\*\*v(\d+\.\d+\.\d+)\*\*", text))


def _section(text: str, start: str, end: str) -> str:
    """The text after ``start`` up to the next ``end`` ("" when ``start`` is absent)."""
    return text.split(start, 1)[1].split(end, 1)[0] if start in text else ""


def check_version_identity(readme_text: str, version: str) -> list[str]:
    """R50: the README's badge, Features heading and Roadmap match ``version``.

    The release badge is ``release-v<version>``; the Features heading is ``Features (v<version>)``;
    the Roadmap's ``### Built`` lists every plan version up to and including ``<version>``, and
    ``### Planned, not yet built`` lists every later one and no built one. Each problem names the
    part it is about (``badge``, ``heading``, ``roadmap``).
    """
    problems = []
    badge = f"https://img.shields.io/badge/release-v{version}-blue"
    if badge not in readme_text:
        problems.append(f"badge: no release-v{version} badge")
    headings = [line[3:] for line in readme_text.splitlines() if line.startswith("## ")]
    titles = [h.split(" ", 1)[1] for h in headings if " " in h]
    if f"Features (v{version})" not in titles:
        problems.append(f"heading: no 'Features (v{version})' section")
    roadmap = _section(readme_text, "## 🧭 Roadmap", "\n## ")
    built_text = _section(roadmap, "### Built", "\n### ")
    planned_text = _section(roadmap, "### Planned, not yet built", "\n### ")
    index = PLAN_VERSIONS.index(version) if version in PLAN_VERSIONS else -1
    built, later = set(PLAN_VERSIONS[: index + 1]), set(PLAN_VERSIONS[index + 1 :])
    if index < 0:
        problems.append(f"roadmap: {version} is not a plan version")
    if missing := sorted(built - _bold_versions(built_text)):
        problems.append(f"roadmap: '### Built' does not list {missing}")
    if missing := sorted(later - _bold_versions(planned_text)):
        problems.append(f"roadmap: '### Planned, not yet built' does not list {missing}")
    if wrong := sorted(built & _bold_versions(planned_text)):
        problems.append(f"roadmap: '### Planned, not yet built' lists built {wrong}")
    return problems


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
        f'href="https://github.com/{repo}/releases/latest"><img src="https://img.shields.io/badge/release-v',
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
    assert titles == readme_sections(project_version())
    assert all(not h[0].isascii() for h in headings[1:])  # emoji prefix
    anchors = {github_anchor(h) for h in re.findall(r"^#{2,6} (.+)$", text, flags=re.M)}
    toc = text.split("## Table of Contents", 1)[1].split("\n## ", 1)[0]
    links = re.findall(r"\]\((#[^)]+)\)", toc)
    assert len(links) == len(readme_sections(project_version()))
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
    assert check_version_identity(text, project_version()) == []


def synthetic_readme(version: str, built: tuple[str, ...], planned: tuple[str, ...]) -> str:
    """A minimal README with a badge, a Features heading and a Roadmap for the R50 checks."""
    lines = [
        f'<img src="https://img.shields.io/badge/release-v{version}-blue" alt="Latest Release"/>',
        "",
        f"## ✨ Features (v{version})",
        "",
        "## 🧭 Roadmap",
        "",
    ]
    if built:
        lines += ["### Built", "", *[f"- **v{v}**: done." for v in built], ""]
    lines += ["### Planned, not yet built", "", *[f"- **v{v}**: later." for v in planned], ""]
    lines += ["## 🙏 Acknowledgements", ""]
    return "\n".join(lines)


LATER_THAN_020 = PLAN_VERSIONS[2:]


def test_version_identity_v010_readme_fails_at_020() -> None:
    """A v0.1.0 README (badge, heading, roadmap) fails at 0.2.0, each part named."""
    old = synthetic_readme("0.1.0", (), PLAN_VERSIONS[1:])
    problems = check_version_identity(old, "0.2.0")
    for part in ("badge:", "heading:", "roadmap:"):
        assert any(p.startswith(part) for p in problems), (part, problems)


def test_version_identity_correct_020_readme_passes() -> None:
    """A correct v0.2.0 README passes."""
    good = synthetic_readme("0.2.0", ("0.1.0", "0.2.0"), LATER_THAN_020)
    assert check_version_identity(good, "0.2.0") == []


def test_version_identity_built_version_under_planned_fails() -> None:
    """v0.2.0 listed under Planned at version 0.2.0 fails."""
    text = synthetic_readme("0.2.0", ("0.1.0", "0.2.0"), ("0.2.0", *LATER_THAN_020))
    assert any("lists built ['0.2.0']" in p for p in check_version_identity(text, "0.2.0"))


def test_version_identity_missing_planned_version_fails() -> None:
    """v0.3.0 missing from Planned fails."""
    text = synthetic_readme("0.2.0", ("0.1.0", "0.2.0"), PLAN_VERSIONS[3:])
    assert any("does not list ['0.3.0']" in p for p in check_version_identity(text, "0.2.0"))


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
    # the GPU claim follows the newest GPU record at or below this version (v0.3.0 adds none)
    released = PLAN_VERSIONS[: PLAN_VERSIONS.index(version) + 1]
    recorded = [
        v for v in released if (REPO / "docs" / "prd" / f"v{v}" / "GPU_SMOKE_RESULT.json").is_file()
    ]
    gpu_version = recorded[-1] if recorded else version
    record_path = REPO / "docs" / "prd" / f"v{gpu_version}" / "GPU_SMOKE_RESULT.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else None
    assert check_gpu_claim(text, record, gpu_version) == []
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


# v0.3.0 claims derived from the acceptance record (slice 09) -----------------------------------

V030_RECORD = REPO / "docs" / "prd" / "v0.3.0" / "ACCEPTANCE_RESULT.json"
V030_FIXTURES = {"hf1_butane", "hf2_diels_alder", "e2e5_t1", "e2e5_t2"}


def _v030_entries(record: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [(n, r, e) for n, by in record["fixtures"].items() for r, e in by.items()]


def _v030_passed_everywhere(record: dict[str, Any]) -> bool:
    """Verdict pass; HF1, HF2, T1 and T2 each passed on both recipes and matched the fixtures."""
    fixtures = record["fixtures"]
    return (
        record["verdict"] == "pass"
        and set(fixtures) == V030_FIXTURES
        and all(set(by) == {"xtb", "uma"} for by in fixtures.values())
        and all(
            e["test_outcome"] == "passed" and e["regression"]["status"] == "pass"
            for _, _, e in _v030_entries(record)
        )
    )


def _v030_uma_accuracy(record: dict[str, Any]) -> bool:
    """HF1 and HF2: UMA accuracy gated and passed at TJ's gating level; xtb reported."""
    level = "wb97mv_def2tzvpd//b3lyp_631gss"
    return all(
        record["fixtures"][n]["uma"]["accuracy"]["verdict"] == "pass"
        and record["fixtures"][n]["xtb"]["accuracy"]["verdict"] == "reported"
        and all(
            record["fixtures"][n][r]["accuracy"]["gating_level"] == level for r in ("xtb", "uma")
        )
        for n in ("hf1_butane", "hf2_diels_alder")
    )


def _v030_smiles_confirmed(record: dict[str, Any]) -> bool:
    """T1 and T2 SMILES confirmed on both recipes (R58: the promotion)."""
    return all(
        e["smiles_confirmation"] == "confirmed"
        for n, _, e in _v030_entries(record)
        if n.startswith("e2e5")
    )


def _v030_window(record: dict[str, Any]) -> bool:
    """UMA's T2 dG_r(1 M) inside TJ's window (gated); GFN2's outside (reported, not gated)."""
    t2 = record["fixtures"]["e2e5_t2"]
    uma, xtb = t2["uma"]["window"], t2["xtb"]["window"]
    return (
        uma["inside"] is True
        and uma["gated"] is True
        and xtb["inside"] is False
        and xtb["gated"] is False
        and uma["bounds_kcal_mol"] == [-42.0, -20.0]
    )


V030_CLAIMS = (
    (
        "passed: conformer ensembles, quasi-RRHO 1 M thermochemistry and the cached single-species "
        "stage runner ran end to end on Human Fixtures 1 and 2 and TJ's Tiers 1 and 2, with both "
        "the xtb (GFN2) and UMA recipes, and every result matched the fixtures TJ promoted.",
        _v030_passed_everywhere,
    ),
    (
        "With UMA, the n-butane gauche–anti ΔG and the Diels–Alder ΔG_r agree with TJ's "
        "ωB97M-V/def2-TZVPD//B3LYP/6-31G** reference values within the gated bounds; GFN2's "
        "deviations are reported, not gated.",
        _v030_uma_accuracy,
    ),
    (
        "TJ confirmed the derived SMILES of the four Tier 1 and 2 species.",
        _v030_smiles_confirmed,
    ),
    (
        "UMA's Tier 2 ΔG_r(1 M) lies inside TJ's −42 to −20 kcal/mol window; GFN2's lies outside "
        "it and is reported, not gated.",
        _v030_window,
    ),
)


def _holds(holds: Any, record: dict[str, Any]) -> bool:
    """A claim holds; a record lacking the keys it needs (a missing fragment) does not."""
    try:
        return bool(holds(record))
    except (KeyError, TypeError):
        return False


def check_v030_claims(readme_text: str, record: dict[str, Any] | None) -> list[str]:
    """Each v0.3.0 README claim is present and true of the record; none without a passing record.

    R56: the claims need the record's top-level ``verdict`` present and ``"pass"``; a record
    without the key (slice 09's pre-promotion record) or with ``fail`` refuses every claim.
    """
    text = " ".join(readme_text.split())
    present = [phrase for phrase, _ in V030_CLAIMS if phrase in text]
    if record is None:
        return [f"README claims {p[:40]!r}… but there is no v0.3.0 record" for p in present]
    if record.get("verdict") != "pass":
        state = "has no verdict" if "verdict" not in record else "verdict is fail"
        return [f"README claims {p[:40]!r}… but the record {state}" for p in present] or [
            f"the v0.3.0 record {state}"
        ]
    problems = []
    for phrase, holds in V030_CLAIMS:
        if phrase not in text:
            problems.append(f"record present, README lacks the claim {phrase[:40]!r}…")
        elif not _holds(holds, record):
            problems.append(f"README claim {phrase[:40]!r}… is not what the record shows")
    if "](docs/prd/v0.3.0/ACCEPTANCE_RESULT.json)" not in text:
        problems.append(
            "record present, but no Markdown link to docs/prd/v0.3.0/ACCEPTANCE_RESULT.json"
        )
    return problems


def test_readme_v030_claims_match_record() -> None:
    """Every README v0.3.0 claim is derived from (and true of) ACCEPTANCE_RESULT.json."""
    record = json.loads(V030_RECORD.read_text(encoding="utf-8")) if V030_RECORD.is_file() else None
    assert check_v030_claims(readme(), record) == []


def test_v030_claim_check_catches_drift() -> None:
    """A record that no longer supports a claim, or a missing record, is caught."""
    record = json.loads(V030_RECORD.read_text(encoding="utf-8"))
    flipped = json.loads(json.dumps(record))
    flipped["fixtures"]["e2e5_t2"]["uma"]["window"]["inside"] = False
    assert any("not what the record shows" in p for p in check_v030_claims(readme(), flipped))
    unconfirmed = json.loads(json.dumps(record))
    unconfirmed["fixtures"]["e2e5_t1"]["xtb"]["smiles_confirmation"] = "pending_confirmation"
    assert any("not what the record shows" in p for p in check_v030_claims(readme(), unconfirmed))
    assert check_v030_claims(readme(), None) != []
    assert check_v030_claims("no claims here", None) == []


def test_v030_claims_refused_without_verdict() -> None:
    """R56 / slice 10 req 4: a record with no ``verdict`` key refuses every final claim."""
    record = json.loads(V030_RECORD.read_text(encoding="utf-8"))
    record.pop("verdict", None)
    problems = check_v030_claims(readme(), record)
    assert problems and all("has no verdict" in p for p in problems)
    assert len(problems) == len(V030_CLAIMS)


def _merged_with(entry_change: Any) -> dict[str, Any]:
    """The committed record re-merged (R56 merge) with one HF1 UMA fragment changed."""
    import sys

    sys.path.insert(0, str(REPO / "tests" / "e2e"))
    from acceptance_record import RECIPES, merge_runs

    record = json.loads(V030_RECORD.read_text(encoding="utf-8"))
    runs = {
        recipe: {
            "commit_sha": record["commit_sha"],
            "tree_clean": True,
            "run_at_utc": record["run_at_utc"],
            "hardware": record["hardware"],
            "engine": record["engines"][recipe],
            "device": record["devices"][recipe],
            "fixture_sha256": {"hf1_butane.uma.json": "0" * 64},
            "fixtures": {n: dict(by[recipe]) for n, by in record["fixtures"].items()},
        }
        for recipe in RECIPES
    }
    for run in runs.values():  # a verdict-run fragment records its T1/T2 tier gates
        for name in ("e2e5_t1", "e2e5_t2"):
            run["fixtures"][name]["tier_gates"] = {"gate": {"status": "pass"}}
    runs["uma"]["fixtures"]["hf1_butane"] = entry_change(runs["uma"]["fixtures"]["hf1_butane"])
    commands = [
        {"argv": [], "env": {}, "exit_code": 1, "wall_s": 0, "log": "x.log", "summary": "x"}
    ]
    return merge_runs(runs, commands)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (
            lambda e: {
                **e,
                "regression": {**e["regression"], "status": "fail"},
                "test_outcome": "failed",
                "failed_checks": ["regression"],
            },
            "hf1_butane.uma: test_outcome failed ['regression']",
        ),
        (lambda e: {"test_outcome": "missing"}, "hf1_butane.uma: test_outcome missing"),
    ],
)
def test_v030_claims_refused_for_failed_or_missing_fragment(change: Any, reason: str) -> None:
    """R56: a failed or missing fragment merges to verdict fail; the README claims are refused."""
    merged = _merged_with(change)
    assert merged["verdict"] == "fail"
    assert reason in merged["verdict_reasons"]
    problems = check_v030_claims(readme(), merged)
    assert any("verdict is fail" in p for p in problems), problems


# v0.4.0 claims derived from the pre-release acceptance record (slice 07) -----------------------

V040_RECORD = REPO / "docs" / "prd" / "v0.4.0" / "ACCEPTANCE_RESULT.json"


def _v040_m1(record: dict[str, Any]) -> dict[str, Any]:
    return dict(record["fixtures"]["m1"])


def _v040_gates_pass(record: dict[str, Any]) -> bool:
    """Graft forming core within 0.10 A; g1-g3 passed on xtb and UMA; every test passed."""
    m1 = _v040_m1(record)
    graft = m1["graft"]
    return (
        set(m1) == {"graft", "xtb", "uma"}
        and graft["test_outcome"] == "passed"
        and graft["forming_core_rmsd"]["status"] == "pass"
        and graft["forming_core_rmsd"]["bound_angstrom"] == 0.10
        and all(
            m1[r]["test_outcome"] == "passed"
            and m1[r]["relaxed_gates"]["status"] == "pass"
            and m1[r]["relaxed_gates"]["g2_connectivity_equals_ts1b_n"]["status"] == "pass"
            and m1[r]["relaxed_gates"]["g3_junction_signs_equal_ts1b_n"]["status"] == "pass"
            for r in ("xtb", "uma")
        )
    )


def _v040_pending_promotion(record: dict[str, Any]) -> bool:
    """Built and gated, with the M1 regression (and the map) still pending TJ's promotion."""
    m1 = _v040_m1(record)
    return (
        _v040_gates_pass(record)
        and record["verdict"] == "pending"
        and m1["graft"]["regression_graft"]["status"] == "pending_promotion"
        and m1["graft"]["map_confirmation"] == "pending_confirmation"
        and all(
            m1[r]["regression_relaxed"]["status"] == "pending_promotion" for r in ("xtb", "uma")
        )
    )


V040_CLAIMS = (
    (
        "conserved-core mapper: quaternion alignment, ordered graft surgery with explicit "
        "charge/spin, core-frozen pre-relaxation; M1 regression pending TJ promotion.",
        _v040_pending_promotion,
    ),
    (
        "TJ's Fixture M1 grafts within the 0.10 Å forming-core bound and pre-relaxes on the xtb "
        "(GFN2) and UMA recipes with TS1b_n's connectivity and junction handedness.",
        _v040_gates_pass,
    ),
    (
        "**v0.4.0**: the conserved-core structure mapper (a clean-room rewrite of `nMap`); M1 "
        "regression pending TJ promotion.",
        _v040_pending_promotion,
    ),
)


def check_v040_claims(readme_text: str, record: dict[str, Any] | None) -> list[str]:
    """Each v0.4.0 README claim is present and true of the record; none without a record.

    A ``fail`` verdict refuses every claim (R56); the version is not bumped here (slice 08).
    """
    text = " ".join(readme_text.split())
    present = [phrase for phrase, _ in V040_CLAIMS if phrase in text]
    if record is None:
        return [f"README claims {p[:40]!r}… but there is no v0.4.0 record" for p in present]
    if record.get("verdict") not in ("pass", "pending"):
        state = "has no verdict" if "verdict" not in record else "verdict is fail"
        return [f"README claims {p[:40]!r}… but the record {state}" for p in present] or [
            f"the v0.4.0 record {state}"
        ]
    problems = []
    for phrase, holds in V040_CLAIMS:
        if phrase not in text:
            problems.append(f"record present, README lacks the claim {phrase[:40]!r}…")
        elif not _holds(holds, record):
            problems.append(f"README claim {phrase[:40]!r}… is not what the record shows")
    if "](docs/prd/v0.4.0/ACCEPTANCE_RESULT.json)" not in text:
        problems.append(
            "record present, but no Markdown link to docs/prd/v0.4.0/ACCEPTANCE_RESULT.json"
        )
    return problems


def test_readme_v040_claims_match_record() -> None:
    """Every README v0.4.0 claim is derived from (and true of) the v0.4.0 record."""
    record = json.loads(V040_RECORD.read_text(encoding="utf-8")) if V040_RECORD.is_file() else None
    assert check_v040_claims(readme(), record) == []
    assert project_version() == "0.3.0"


def test_v040_claim_check_catches_drift() -> None:
    """A failed gate, a settled promotion, a fail verdict or a missing record is caught."""
    record = json.loads(V040_RECORD.read_text(encoding="utf-8"))
    gate = json.loads(json.dumps(record))
    gate["fixtures"]["m1"]["uma"]["relaxed_gates"]["g2_connectivity_equals_ts1b_n"]["status"] = (
        "fail"
    )
    assert any("not what the record shows" in p for p in check_v040_claims(readme(), gate))
    promoted = json.loads(json.dumps(record))
    promoted["fixtures"]["m1"]["xtb"]["regression_relaxed"]["status"] = "pass"
    assert any("not what the record shows" in p for p in check_v040_claims(readme(), promoted))
    failed = json.loads(json.dumps(record))
    failed["verdict"] = "fail"
    problems = check_v040_claims(readme(), failed)
    assert problems and all("verdict is fail" in p for p in problems)
    assert check_v040_claims(readme(), None) != []
    assert check_v040_claims("no claims here", None) == []


def _v040_recomputed(change: Any) -> dict[str, Any]:
    """The committed v0.4.0 record with one change and its verdict recomputed (mission R27)."""
    import sys

    sys.path.insert(0, str(REPO / "tests" / "e2e"))
    from acceptance_record_v040 import record_verdict

    record = json.loads(V040_RECORD.read_text(encoding="utf-8"))
    change(record)
    record.update(
        record_verdict(record["fixtures"], record.get("default_suite"), record.get("commands", []))
    )
    return record


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda r: r["default_suite"].update(failed=1), "default_suite: exit_code"),
        (
            lambda r: r["default_suite"]["cleanroom_vectors"].update(exit_code=1),
            "default_suite.cleanroom_vectors",
        ),
        (lambda r: r["commands"][0].update(exit_code=1), "exit_code 1"),
        (lambda r: r["commands"][1].update(summary="1 passed, 1 skipped in 3.0s"), "1 skipped"),
    ],
)
def test_v040_claims_refused_when_suite_vectors_commands_or_skips_fail(
    change: Any, reason: str
) -> None:
    """R27: a failing suite, vector run, command or a skip fails the record and every claim."""
    record = _v040_recomputed(change)
    assert record["verdict"] == "fail"
    assert any(reason in r for r in record["verdict_reasons"])
    problems = check_v040_claims(readme(), record)
    assert problems and all("verdict is fail" in p for p in problems)


def test_v040_claims_refused_without_verdict() -> None:
    """R27 (b) / v0.3.0 slice 10 req 4: no ``verdict`` key refuses every claim, never KeyError."""
    record = json.loads(V040_RECORD.read_text(encoding="utf-8"))
    record.pop("verdict", None)
    problems = check_v040_claims(readme(), record)
    assert problems and all("has no verdict" in p for p in problems)
    assert len(problems) == len(V040_CLAIMS)
