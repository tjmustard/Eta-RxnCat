"""The vendored assets: pinned hashes, licence rows, and presence in a built wheel."""

import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from eta_rxncat.review.bundle import ASSETS_PATH, BUNDLE_ASSETS

REPO = Path(__file__).parents[3]
MIN_JS_SHA256 = "f7cc78921ae72e7623e89cdd111434f58c2efddd2ffda1cd212644b406fb8016"
LICENSE_SHA256 = "4c6eaaed856f3f28a3b1a98e74f4a8a71618de7d51ea4155c29f6f793bcef861"
INTEGRITY = (
    "sha512-kqNHouGqq3YfW58174tdERvm0XYTmP0tavQKOqIw1ouc2OJ7epkXEFrtEkVXV0clBZT2Ze2xHRC/"
    "qxX0u0qCdw=="
)


def sha256(path: Path) -> str:
    """Return the sha256 of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_3dmol_build_is_the_pinned_one() -> None:
    """The vendored build has the pinned sha256."""
    assert sha256(ASSETS_PATH / "3Dmol-min.js") == MIN_JS_SHA256


def test_the_licence_file_is_the_packages_own() -> None:
    """The licence file is the package's, with every part."""
    licence = ASSETS_PATH / "LICENSE-3Dmol.txt"
    assert sha256(licence) == LICENSE_SHA256
    text = licence.read_text(encoding="utf-8")
    for part in ("BSD-3-Clause", "GLmol", "dual license of MIT or LGPL3", "Three.js", "jQuery"):
        assert part in text


def test_sources_records_the_pin_and_every_component() -> None:
    """SOURCES.md has the URL, hashes and licence rows."""
    sources = (ASSETS_PATH / "SOURCES.md").read_text(encoding="utf-8")
    for part in (
        "https://registry.npmjs.org/3dmol/-/3dmol-2.5.5.tgz",
        "2.5.5",
        "2026-11-26",
        INTEGRITY,
        MIN_JS_SHA256,
        "**eta elects MIT**",
    ):
        assert part in sources
    rows = {line.split("|")[1].strip(): line for line in sources.splitlines() if "| " in line}
    for name in ("GLmol", "three.js", "jQuery", "iobuffer", "netcdfjs", "upng-js"):
        assert "MIT" in rows[name]
    assert "MIT AND Zlib" in rows["pako"]
    assert "BSD-3-Clause" in rows["3Dmol.js"]


def test_the_wheel_ships_the_assets_and_the_schema(tmp_path: Path) -> None:
    """A built wheel lists each asset and the schema once."""
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not installed")
    built = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert built.returncode == 0, built.stderr
    (wheel,) = tmp_path.glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    expected = [f"eta_rxncat/review/assets/{n}" for n in (*BUNDLE_ASSETS, "SOURCES.md")]
    expected.append("eta_rxncat/review/schema/run_data.v1.schema.json")
    for name in expected:
        assert names.count(name) == 1, name
