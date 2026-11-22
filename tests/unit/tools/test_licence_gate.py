"""Tests for tools/licence_gate.py with synthetic *.dist-info folders (R45)."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).parents[3]
GATE = REPO / "tools" / "licence_gate.py"


def toml_value(value: Any) -> str:
    """Render a str, list of str or flat table of str as TOML."""
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(v) for v in value) + "]"
    raise TypeError(value)


def write_config(tmp_path: Path, exempt: list[dict[str, Any]], nvidia: bool = True) -> Path:
    """Write a config with the repo's allow-list, maps and NVIDIA rule plus ``exempt`` only."""
    gate = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["tool"][
        "eta-rxncat"
    ]["licence-gate"]
    lines = ["[tool.eta-rxncat.licence-gate]"]
    lines += [f"{k} = {toml_value(gate[k])}" for k in ("allowed", "allowed-exceptions")]
    for table in ("classifiers", "names"):
        lines.append(f"[tool.eta-rxncat.licence-gate.{table}]")
        lines += [f"{json.dumps(k)} = {json.dumps(v)}" for k, v in gate[table].items()]
    rule = dict(gate["nvidia-rule"])
    if not nvidia:
        rule["profiles"] = []
    lines.append("[tool.eta-rxncat.licence-gate.nvidia-rule]")
    lines += [f"{k} = {toml_value(v)}" for k, v in rule.items()]
    for entry in exempt:
        lines.append("[[tool.eta-rxncat.licence-gate.exempt]]")
        lines += [f"{k} = {toml_value(v)}" for k, v in entry.items()]
    path = tmp_path / "pyproject.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def dist(
    site: Path,
    name: str,
    version: str = "1.0",
    expression: str | None = None,
    classifiers: tuple[str, ...] = (),
    license_field: str | None = None,
) -> None:
    """Create ``<site>/<name>-<version>.dist-info/METADATA`` with the given licence metadata."""
    folder = site / f"{name.replace('-', '_')}-{version}.dist-info"
    folder.mkdir(parents=True)
    lines = ["Metadata-Version: 2.4", f"Name: {name}", f"Version: {version}"]
    if expression is not None:
        lines.append(f"License-Expression: {expression}")
    lines += [f"Classifier: {c}" for c in classifiers]
    if license_field is not None:
        body = license_field.replace("\n", "\n        ")  # RFC 822 continuation lines
        lines.append(f"License: {body}")
    (folder / "METADATA").write_text("\n".join(lines) + "\n", encoding="utf-8")


def gate(
    tmp_path: Path,
    profile: str = "base",
    exempt: list[dict[str, Any]] | None = None,
    nvidia: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run the gate over ``tmp_path / "site"`` with a test config."""
    config = write_config(tmp_path, exempt or [], nvidia)
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(GATE),
            "--profile",
            profile,
            "--path",
            str(tmp_path / "site"),
            "--config",
            str(config),
        ],
        capture_output=True,
        text=True,
    )


def fails(result: subprocess.CompletedProcess[str]) -> list[str]:
    """Return the FAIL lines of a gate run."""
    return [line for line in result.stdout.splitlines() if line.startswith("FAIL ")]


LGPL_FULL_TEXT = (
    "GNU LESSER GENERAL PUBLIC LICENSE\nVersion 2.1, February 1999\n\n"
    "BECAUSE THE LIBRARY IS LICENSED FREE OF CHARGE, THERE IS NO WARRANTY FOR THE LIBRARY,\n"
    "TO THE EXTENT PERMITTED BY APPLICABLE LAW. MIT BSD Apache ISC PSF"
)


@pytest.mark.parametrize(
    ("kwargs", "passes"),
    [
        ({"license_field": LGPL_FULL_TEXT}, False),
        ({"expression": "MPL-2.0 AND MIT"}, False),
        ({"expression": "MPL-2.0 AND (Apache-2.0 OR MIT)"}, False),
        ({"expression": "Apache-2.0 OR BSD-2-Clause"}, True),
        ({"expression": "BSD-2-Clause AND Apache-2.0 WITH LLVM-exception"}, True),
        ({"expression": "GPL-2.0 WITH LLVM-exception"}, False),
        ({"expression": "MIT AND (BSD-3-Clause"}, False),
        ({"classifiers": ("License :: OSI Approved :: MIT License",)}, True),
        (
            {"classifiers": ("License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",)},
            False,
        ),
        ({"license_field": "UNKNOWN"}, False),
        ({"license_field": "MIT License\n\nCopyright (c) 2020 Someone"}, False),
    ],
    ids=[
        "full-text-lgpl-with-PERMITTED",
        "mpl-and-mit",
        "mpl-and-apache-or-mit",
        "apache-or-bsd2",
        "bsd2-and-apache-with-llvm",
        "gpl-with-llvm",
        "spdx-parse-error",
        "classifier-mit",
        "classifier-mpl",
        "field-unknown",
        "field-multiline-mit",
    ],
)
def test_verdicts(tmp_path: Path, kwargs: dict[str, Any], passes: bool) -> None:
    """Each licence form gets the exact verdict: no substring or partial matching."""
    dist(tmp_path / "site", "pkg", **kwargs)
    result = gate(tmp_path)
    assert (result.returncode == 0) is passes, result.stdout
    assert (fails(result) == []) is passes
    if not passes:
        assert fails(result)[0].startswith("FAIL pkg:1.0 ")


def test_pinned_exemption_wrong_version(tmp_path: Path) -> None:
    """An exemption for pkg:1.0 does not cover pkg 1.1, and it is reported as stale."""
    dist(tmp_path / "site", "pkg", "1.1", license_field="UNKNOWN")
    exempt = [
        {
            "package": "pkg",
            "version": "1.0",
            "profiles": ["base"],
            "licence": "l",
            "pulled-in-by": "p",
            "reason": "r",
            "decision": "d",
        }
    ]
    result = gate(tmp_path, exempt=exempt)
    assert result.returncode == 1
    assert fails(result) == [
        "FAIL pkg:1.1 [license-field] UNKNOWN",
        "FAIL pkg:1.0 [stale exemption] not installed at this version or not failing (d)",
    ]


def test_exact_exemption_passes(tmp_path: Path) -> None:
    """An exemption pinned to the installed version covers the package."""
    dist(tmp_path / "site", "pkg", "1.1", license_field="UNKNOWN")
    exempt = [
        {
            "package": "pkg",
            "version": "1.1",
            "profiles": ["base"],
            "licence": "l",
            "pulled-in-by": "p",
            "reason": "r",
            "decision": "d",
        }
    ]
    result = gate(tmp_path, exempt=exempt)
    assert result.returncode == 0, result.stdout


def test_stale_exemption_for_absent_package(tmp_path: Path) -> None:
    """An exemption naming a package that is not installed fails as stale."""
    dist(tmp_path / "site", "ok", expression="MIT")
    exempt = [
        {
            "package": "gone",
            "version": "2.0",
            "profiles": ["base"],
            "licence": "l",
            "pulled-in-by": "p",
            "reason": "r",
            "decision": "d",
        }
    ]
    result = gate(tmp_path, exempt=exempt)
    assert result.returncode == 1 and fails(result)[0].startswith("FAIL gone:2.0 [stale exemption]")


def test_exemption_scoped_to_profile(tmp_path: Path) -> None:
    """An exemption listed for mlip-mace does not apply in base."""
    dist(tmp_path / "site", "pkg", license_field="UNKNOWN")
    exempt = [
        {
            "package": "pkg",
            "version": "1.0",
            "profiles": ["mlip-mace"],
            "licence": "l",
            "pulled-in-by": "p",
            "reason": "r",
            "decision": "d",
        }
    ]
    assert gate(tmp_path, "base", exempt).returncode == 1
    assert gate(tmp_path, "mlip-mace", exempt).returncode == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"classifiers": ("License :: Other/Proprietary License",)},
        {"license_field": "NVIDIA Proprietary Software"},
    ],
    ids=["classifier", "field"],
)
def test_nvidia_rule(tmp_path: Path, kwargs: dict[str, Any]) -> None:
    """A proprietary nvidia-* package passes in gpu, fails in base, and fails without the rule."""
    dist(tmp_path / "site", "nvidia-x-cu12", **kwargs)
    assert gate(tmp_path, "gpu").returncode == 0
    assert gate(tmp_path, "base").returncode == 1
    assert gate(tmp_path, "gpu", nvidia=False).returncode == 1


def test_nvidia_rule_needs_proprietary_licence(tmp_path: Path) -> None:
    """The NVIDIA rule does not cover an nvidia-* package under some other failing licence."""
    dist(tmp_path / "site", "nvidia-x-cu12", expression="GPL-3.0-only")
    assert gate(tmp_path, "gpu").returncode == 1


def test_nvidia_rule_needs_prefix(tmp_path: Path) -> None:
    """A proprietary package without the nvidia- prefix is not covered."""
    dist(tmp_path / "site", "vendor-x", classifiers=("License :: Other/Proprietary License",))
    assert gate(tmp_path, "gpu").returncode == 1


def test_exact_names_case_insensitive(tmp_path: Path) -> None:
    """Known short names match exactly, ignoring case; near-misses fail."""
    dist(tmp_path / "site", "a", license_field="mit license")
    dist(tmp_path / "site", "b", license_field="MIT Licence (see file)")
    result = gate(tmp_path)
    assert fails(result) == ["FAIL b:1.0 [license-field] MIT Licence (see file)"]


def test_field_spdx_expression(tmp_path: Path) -> None:
    """A single-line SPDX expression in the License field is evaluated exactly."""
    dist(tmp_path / "site", "a", license_field="BSD-3-Clause OR MIT")
    dist(tmp_path / "site", "b", license_field="OLDAP-2.8")
    assert fails(gate(tmp_path)) == ["FAIL b:1.0 [license-field] OLDAP-2.8"]


def test_expression_takes_precedence(tmp_path: Path) -> None:
    """License-Expression decides even when an allowed classifier is also present."""
    dist(
        tmp_path / "site",
        "pkg",
        expression="MPL-2.0",
        classifiers=("License :: OSI Approved :: MIT License",),
    )
    assert gate(tmp_path).returncode == 1


def test_several_classifiers_are_alternatives(tmp_path: Path) -> None:
    """With several licence classifiers one allowed classifier is enough."""
    dist(
        tmp_path / "site",
        "pkg",
        classifiers=(
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
            "License :: OSI Approved :: MIT License",
        ),
    )
    assert gate(tmp_path).returncode == 0


def test_project_and_pip_are_skipped(tmp_path: Path) -> None:
    """The project itself and pip are not judged."""
    dist(tmp_path / "site", "eta-rxncat", "0.1.0", license_field="UNKNOWN")
    dist(tmp_path / "site", "pip", "25.0", license_field="UNKNOWN")
    result = gate(tmp_path)
    assert result.returncode == 0 and "0 packages, 0 failures" in result.stdout


def test_usage_and_config_errors(tmp_path: Path) -> None:
    """An unknown profile or a config without the gate table exits 2."""
    bad = subprocess.run(
        [sys.executable, "-I", str(GATE), "--profile", "nope"], capture_output=True, text=True
    )
    assert bad.returncode == 2
    empty = tmp_path / "pyproject.toml"
    empty.write_text("[project]\nname = 'x'\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", str(GATE), "--profile", "base", "--config", str(empty)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and "licence-gate" in result.stderr


def repo_gate_table() -> dict[str, Any]:
    """Return the committed ``[tool.eta-rxncat.licence-gate]`` table."""
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    table: dict[str, Any] = data["tool"]["eta-rxncat"]["licence-gate"]
    return table


def test_repo_config_loads() -> None:
    """The committed config pins geometric 1.1.1 in every profile and has no pip-licenses table."""
    geometric = [e for e in repo_gate_table()["exempt"] if e["package"] == "geometric"]
    assert len(geometric) == 1
    assert geometric[0]["version"] == "1.1.1"
    assert geometric[0]["profiles"] == ["base", "gpu", "mlip-mace", "mlip-uma"]
    assert geometric[0]["decision"].startswith("R41")
    assert "pip-licenses" not in tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]


def test_exemptions_only_in_mlip_profiles() -> None:
    """Every exemption other than geometric lists only MLIP profiles, never base or gpu (R48)."""
    offenders = [
        f"{e['package']}:{e['version']} {e['profiles']}"
        for e in repo_gate_table()["exempt"]
        if e["package"] != "geometric"
        and (not e["profiles"] or not set(e["profiles"]) <= {"mlip-mace", "mlip-uma"})
    ]
    assert offenders == []


def test_exemption_entries_are_complete() -> None:
    """Every exemption records package, exact version, profiles, licence, parent and reasons."""
    required = {"package", "version", "profiles", "licence", "pulled-in-by", "reason", "decision"}
    for entry in repo_gate_table()["exempt"]:
        assert set(entry) == required, entry
        assert all(entry[k] for k in required), entry
        assert not any(c in entry["version"] for c in "<>=*~^,"), entry


def test_r48_lists() -> None:
    """The MLIP exemption lists are exactly R48's version-pinned sets."""
    table = repo_gate_table()["exempt"]

    def listed(profile: str) -> set[str]:
        return {
            f"{e['package']}:{e['version']}"
            for e in table
            if profile in e["profiles"] and e["package"] != "geometric"
        }

    assert listed("mlip-mace") == {
        "ase:3.29.0",
        "matscipy:1.3.1",
        "python-hostlist:2.3.0",
        "lmdb:1.7.3",
        "torch-ema:0.3",
        "tqdm:4.70.1",
        "orjson:3.13.0",
    }
    assert listed("mlip-uma") == {
        "ase:3.29.0",
        "psycopg2-binary:2.9.13",
        "ase_db_backends:0.11.0",
        "ray-haproxy:2.8.25",
        "lmdb:1.7.3",
        "certifi:2026.11.20",
        "tqdm:4.70.1",
        "orjson:3.13.0",
        "clusterscope:0.0.18",
    }
    assert all(
        e["decision"].startswith("R48 / ADR-0014") for e in table if e["package"] != "geometric"
    )
