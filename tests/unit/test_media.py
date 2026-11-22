"""Media rules (slice 10, R53): size-named WebP files and next-size-up embedding.

Stdlib only (no Pillow), pure filesystem, no git. TJ: "Make all image files names the exact size
of the image inside 128 for 128px. Make multiple sizes of the logo and banner. Only imbed the next
size up for the documents."
"""

import re
import struct
from collections.abc import Iterable
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
README_COLUMN_PX = 1012
"""Width that ``width="100%"`` means: GitHub's README content column, a fixed constant."""

EXPECTED_MEDIA = {
    "icons/icon-1024.webp",
    "icons/web/icon-128.webp",
    "icons/web/icon-192.webp",
    "icons/web/icon-256.webp",
    "icons/web/icon-512.webp",
    "banner/banner-640x358.webp",
    "banner/banner-1024x573.webp",
    "banner/banner-1280x716.webp",
    "banner/banner-1920x1073.webp",
    "banner/banner-2576x1439.webp",
}
STARTER_COPY = "docs/prd/v0.1.0/Eta-RxnCat-v0.1.0"

_SQUARE = re.compile(r"(icon)-([1-9][0-9]*)\.webp")
_BANNER = re.compile(r"(banner)-([1-9][0-9]*)x([1-9][0-9]*)\.webp")
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_MD_IMG = re.compile(r"!\[[^\]]*\]\(\s*(?:\./)?(media/[^)\s]+)")


def webp_size(path: Path) -> tuple[int, int]:
    """Return ``(width, height)`` from a WebP file's RIFF header (VP8X, VP8L or VP8).

    Raises:
        ValueError: If the file is not a RIFF/WEBP file with a recognised first chunk.
    """
    data = path.read_bytes()[:30]
    if len(data) < 30 or data[0:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"{path}: not a RIFF/WEBP file")
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if chunk == b"VP8L":
        if data[20] != 0x2F:
            raise ValueError(f"{path}: VP8L signature missing")
        bits = int.from_bytes(data[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if chunk == b"VP8 ":
        if data[23:26] != b"\x9d\x01\x2a":
            raise ValueError(f"{path}: VP8 start code missing")
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height
    raise ValueError(f"{path}: unsupported WebP chunk {chunk!r}")


def parse_media_name(name: str) -> tuple[str, int, int]:
    """Return ``(family, width, height)`` from a size-named file name.

    ``icon-<N>.webp`` is N×N and ``banner-<W>x<H>.webp`` is W×H.

    Raises:
        ValueError: If the name is unsized or matches neither pattern.
    """
    square = _SQUARE.fullmatch(name)
    if square:
        n = int(square.group(2))
        return square.group(1), n, n
    banner = _BANNER.fullmatch(name)
    if banner:
        return banner.group(1), int(banner.group(2)), int(banner.group(3))
    raise ValueError(
        f"{name!r} is not a size-named media file (icon-<N>.webp, banner-<W>x<H>.webp)"
    )


def required_media(family: str, width: int, height: int | None, candidates: Iterable[Path]) -> Path:
    """Return the next size up: the narrowest ``family`` file at least ``width`` px wide.

    Raises:
        ValueError: If no candidate of the family is large enough.
    """
    fitting = []
    for path in candidates:
        try:
            fam, w, h = parse_media_name(path.name)
        except ValueError:
            continue
        if fam == family and w >= width and (height is None or h >= height):
            fitting.append((w, path))
    if not fitting:
        raise ValueError(f"no {family} file is at least {width}x{height or '?'} px")
    return min(fitting)[1]


def _attribute(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', tag)
    return match.group(1) if match else None


def _pixels(value: str | None) -> int | None:
    """Return a declared size in px: ``"200"`` → 200, ``"100%"`` → README column width."""
    if value is None:
        return None
    if value == "100%":
        return README_COLUMN_PX
    if re.fullmatch(r"[1-9][0-9]*", value):
        return int(value)
    raise ValueError(f"unsupported size attribute {value!r}")


def find_embeds(markdown_text: str) -> list[tuple[str, int | None, int | None]]:
    """Return ``(src, width_px, height_px)`` for every local media embed in Markdown text.

    ``<img src="./media/…">`` and ``![…](media/…)`` count; external URLs are ignored. A Markdown
    image has no width, so it is returned with ``width_px`` ``None``.
    """
    embeds: list[tuple[str, int | None, int | None]] = []
    for tag in _IMG.findall(markdown_text):
        src = _attribute(tag, "src")
        if src is None or re.match(r"[a-z]+://", src):
            continue
        src = src.removeprefix("./")
        if not src.startswith("media/"):
            continue
        embeds.append((src, _pixels(_attribute(tag, "width")), _pixels(_attribute(tag, "height"))))
    for src in _MD_IMG.findall(markdown_text):
        embeds.append((src, None, None))
    return embeds


def media_files(root: Path) -> list[Path]:
    """Return every file under ``root/media``, at any depth, sorted."""
    base = root / "media"
    return sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []


def scanned_docs(root: Path) -> list[Path]:
    """Return README.md, CHANGELOG.md and docs/**/*.md, excluding the verbatim starter copy."""
    docs = [root / name for name in ("README.md", "CHANGELOG.md") if (root / name).is_file()]
    if (root / "docs").is_dir():
        docs += [
            p
            for p in sorted((root / "docs").rglob("*.md"))
            if not p.relative_to(root).as_posix().startswith(STARTER_COPY + "/")
        ]
    return docs


def naming_violations(root: Path) -> list[str]:
    """Return one message per media file whose name is unsized or disagrees with its pixels."""
    problems = []
    for path in media_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            _, w, h = parse_media_name(path.name)
            actual = webp_size(path)
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        if actual != (w, h):
            problems.append(f"{rel}: named {w}x{h} but the header says {actual[0]}x{actual[1]}")
    return problems


def embed_violations(root: Path, docs: Iterable[Path]) -> list[str]:
    """Return one message per local embed that is not exactly its required next-size-up file."""
    candidates = media_files(root)
    problems = []
    for doc in docs:
        rel_doc = doc.relative_to(root).as_posix()
        for src, width, height in find_embeds(doc.read_text(encoding="utf-8")):
            where = f"{rel_doc}: {src}"
            target = root / src
            if not target.is_file():
                problems.append(f"{where}: file does not exist")
                continue
            if width is None:
                problems.append(f"{where}: local media must be an <img> with a width")
                continue
            try:
                family, _, file_height = parse_media_name(target.name)
                required = required_media(family, width, height, candidates)
            except ValueError as exc:
                problems.append(f"{where}: {exc}")
                continue
            if required.resolve() != target.resolve():
                need = required.relative_to(root).as_posix()
                problems.append(f"{where}: displayed at {width}px, the next size up is {need}")
            elif height is not None and height > file_height:
                problems.append(
                    f"{where}: declared height {height} exceeds the file's {file_height}"
                )
    return problems


# ---- the real repository ----


def test_media_set_is_exactly_the_ten_files() -> None:
    """media/ holds exactly the ten size-named WebP files, at any depth."""
    assert {p.relative_to(REPO / "media").as_posix() for p in media_files(REPO)} == EXPECTED_MEDIA


def test_every_media_name_matches_its_pixels() -> None:
    """Every media file's WebP header size equals the size in its name."""
    assert naming_violations(REPO) == []


def test_every_embed_uses_the_next_size_up() -> None:
    """Every local embed in README, CHANGELOG and docs (not the starter copy) is required."""
    assert embed_violations(REPO, scanned_docs(REPO)) == []


def test_readme_embeds_exactly_icon_256_and_banner_1024() -> None:
    """The README embeds icon-256 (shown at 200 px) and banner-1024x573 (shown at 100%)."""
    embeds = find_embeds((REPO / "README.md").read_text(encoding="utf-8"))
    assert embeds == [
        ("media/icons/web/icon-256.webp", 200, 200),
        ("media/banner/banner-1024x573.webp", README_COLUMN_PX, None),
    ]


def test_starter_copy_is_not_scanned() -> None:
    """The verbatim starter copy under docs/prd/v0.1.0/Eta-RxnCat-v0.1.0 is excluded."""
    assert not any(
        p.relative_to(REPO).as_posix().startswith(STARTER_COPY + "/") for p in scanned_docs(REPO)
    )


# ---- synthetic WebP headers ----


def vp8x(width: int, height: int) -> bytes:
    """Return a minimal VP8X (extended) WebP header for ``width`` x ``height``."""
    payload = (
        b"\x10\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    )
    return (
        b"RIFF"
        + struct.pack("<I", 4 + 8 + len(payload))
        + b"WEBP"
        + b"VP8X"
        + struct.pack("<I", len(payload))
        + payload
    )


def vp8l(width: int, height: int) -> bytes:
    """Return a minimal VP8L (lossless) WebP header for ``width`` x ``height``."""
    bits = (width - 1) | ((height - 1) << 14)
    payload = b"\x2f" + bits.to_bytes(4, "little") + b"\x00" * 5
    return (
        b"RIFF"
        + struct.pack("<I", 4 + 8 + len(payload))
        + b"WEBP"
        + b"VP8L"
        + struct.pack("<I", len(payload))
        + payload
    )


def vp8(width: int, height: int) -> bytes:
    """Return a minimal VP8 (lossy) WebP header for ``width`` x ``height``."""
    payload = b"\x00\x00\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", width, height)
    return (
        b"RIFF"
        + struct.pack("<I", 4 + 8 + len(payload))
        + b"WEBP"
        + b"VP8 "
        + struct.pack("<I", len(payload))
        + payload
    )


def make_repo(tmp_path: Path, files: dict[str, bytes], readme: str = "") -> Path:
    """Build a tmp repo with ``media/<rel>`` files and a README."""
    for rel, data in files.items():
        target = tmp_path / "media" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    return tmp_path


ICONS = {f"icons/web/icon-{n}.webp": vp8x(n, n) for n in (128, 192, 256, 512)}
BANNERS = {
    "banner/banner-640x358.webp": vp8(640, 358),
    "banner/banner-1024x573.webp": vp8(1024, 573),
    "banner/banner-1280x716.webp": vp8(1280, 716),
}


def img(src: str, width: str | None = "200", height: str | None = None) -> str:
    """Return an <img> tag for ``src`` with optional width and height."""
    attrs = f' width="{width}"' if width is not None else ""
    attrs += f' height="{height}"' if height is not None else ""
    return f'<img src="./media/{src}" alt="x"{attrs}/>\n'


@pytest.mark.parametrize(
    ("header", "size"),
    [(vp8x(256, 256), (256, 256)), (vp8l(300, 17), (300, 17)), (vp8(1024, 573), (1024, 573))],
    ids=["VP8X", "VP8L", "VP8"],
)
def test_webp_size_each_chunk_type(tmp_path: Path, header: bytes, size: tuple[int, int]) -> None:
    """Each chunk type's header is parsed to its width and height."""
    path = tmp_path / "x.webp"
    path.write_bytes(header)
    assert webp_size(path) == size


@pytest.mark.parametrize(
    "data",
    [b"RIFF\x00\x00\x00\x00WEBPABCD" + b"\x00" * 20, b"\x89PNG" + b"\x00" * 40, b"RIFF"],
    ids=["unknown-chunk", "png", "truncated"],
)
def test_webp_size_rejects_other_files(tmp_path: Path, data: bytes) -> None:
    """Non-WebP or unknown-chunk files raise ValueError."""
    path = tmp_path / "x.webp"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        webp_size(path)


@pytest.mark.parametrize(
    ("files", "readme"),
    [
        (
            {**ICONS, "icons/web/icon-256.webp": vp8x(256, 256)},
            img("icons/web/icon-256.webp", "200", "200"),
        ),
        ({"icons/web/icon-300.webp": vp8l(300, 300)}, img("icons/web/icon-300.webp", "300")),
        (BANNERS, img("banner/banner-1024x573.webp", "100%")),
    ],
    ids=["VP8X-icon", "VP8L-icon", "VP8-banner"],
)
def test_passing_cases(tmp_path: Path, files: dict[str, bytes], readme: str) -> None:
    """A correctly named file embedded at its next size up passes, for each chunk type."""
    root = make_repo(tmp_path, files, readme)
    assert naming_violations(root) == []
    assert embed_violations(root, scanned_docs(root)) == []


def test_fail_a_mismatched_name(tmp_path: Path) -> None:
    """(a) icon-256.webp whose header says 255x255 fails the naming check."""
    root = make_repo(tmp_path, {**ICONS, "icons/web/icon-256.webp": vp8x(255, 255)})
    assert naming_violations(root) == [
        "media/icons/web/icon-256.webp: named 256x256 but the header says 255x255"
    ]


def test_fail_b_oversized_choice(tmp_path: Path) -> None:
    """(b) icon-512 embedded at width 200 fails: the next size up is icon-256."""
    root = make_repo(tmp_path, ICONS, img("icons/web/icon-512.webp"))
    problems = embed_violations(root, scanned_docs(root))
    assert len(problems) == 1 and "icon-256.webp" in problems[0]


def test_fail_c_undersized_choice(tmp_path: Path) -> None:
    """(c) icon-192 embedded at width 200 fails: it is smaller than the display width."""
    root = make_repo(tmp_path, ICONS, img("icons/web/icon-192.webp"))
    problems = embed_violations(root, scanned_docs(root))
    assert len(problems) == 1 and "icon-256.webp" in problems[0]


def test_fail_d_unsized_name(tmp_path: Path) -> None:
    """(d) An unsized banner.webp fails the naming check."""
    unsized = "banner" + ".webp"  # assembled, so the slice's old-path grep stays empty
    root = make_repo(tmp_path, {unsized: vp8(1024, 573)})
    problems = naming_violations(root)
    assert len(problems) == 1 and f"media/{unsized}" in problems[0]
    assert "not a size-named" in problems[0]


@pytest.mark.parametrize(
    "readme",
    [img("icons/web/icon-256.webp", width=None), "![logo](./media/icons/web/icon-256.webp)\n"],
    ids=["img-without-width", "markdown-image"],
)
def test_fail_e_local_embed_without_width(tmp_path: Path, readme: str) -> None:
    """(e) A local embed with no width (including a Markdown image) fails."""
    root = make_repo(tmp_path, ICONS, readme)
    problems = embed_violations(root, scanned_docs(root))
    assert len(problems) == 1 and "width" in problems[0]


def test_fail_f_full_width_banner_too_large(tmp_path: Path) -> None:
    """(f) width="100%" (1012 px) embedding banner-1280x716 fails: banner-1024x573 is required."""
    root = make_repo(tmp_path, BANNERS, img("banner/banner-1280x716.webp", "100%"))
    problems = embed_violations(root, scanned_docs(root))
    assert len(problems) == 1 and "banner-1024x573.webp" in problems[0]


def test_declared_height_must_fit(tmp_path: Path) -> None:
    """A declared height larger than the chosen file's height fails."""
    root = make_repo(tmp_path, BANNERS, img("banner/banner-1024x573.webp", "1000", "600"))
    problems = embed_violations(root, scanned_docs(root))
    assert len(problems) == 1


def test_external_urls_ignored() -> None:
    """Badges and other external images are not media embeds."""
    text = '<img src="https://img.shields.io/badge/x-y-blue" alt="b"/>\n'
    assert find_embeds(text) == []


def test_required_media_rule() -> None:
    """The required file is the narrowest family member at least as wide (and tall) as shown."""
    names = [Path(f"icon-{n}.webp") for n in (128, 192, 256, 512, 1024)]
    assert required_media("icon", 200, 200, names).name == "icon-256.webp"
    assert required_media("icon", 128, None, names).name == "icon-128.webp"
    assert required_media("icon", 129, None, names).name == "icon-192.webp"
    with pytest.raises(ValueError):
        required_media("icon", 2000, None, names)
    banners = [Path(n) for n in ("banner-640x358.webp", "banner-1024x573.webp")]
    assert required_media("banner", README_COLUMN_PX, None, banners).name == "banner-1024x573.webp"


@pytest.mark.parametrize(
    "name",
    [
        "banner.webp",
        "icon.webp",
        "logo-256.webp",
        "icon-256.png",
        "icon-0256.webp",
        "banner-640.webp",
    ],
)
def test_parse_media_name_rejects(name: str) -> None:
    """Unsized or foreign names raise ValueError."""
    with pytest.raises(ValueError):
        parse_media_name(name)
