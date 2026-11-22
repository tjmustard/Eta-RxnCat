"""Exact licence gate for an installed environment (R45, ADR-0013).

Run with the interpreter of the environment to audit::

    <env>/bin/python -I tools/licence_gate.py --profile {base,gpu,mlip-mace,mlip-uma}

Each installed distribution (except the project itself and ``pip``) gets one verdict from the
first licence source present:

1. ``License-Expression``: parsed as SPDX. ``AND`` needs every term allowed, ``OR`` needs one,
   and ``WITH`` needs an allowed exception. A parse error fails.
2. ``License ::`` classifiers, each mapped exactly; several classifiers are alternatives.
3. The ``License`` field, matched exactly against the configured ``names``, the allowed ids, or a
   single-line SPDX expression of allowed ids.

Anything else (empty, ``UNKNOWN``, multi-line or full-text fields) is unrecognised and fails.
There is no substring matching. Exemptions are pinned to an exact package version and profile;
an exemption whose package is not installed at that version is stale and fails. The
configuration lives in ``pyproject.toml`` under ``[tool.eta-rxncat.licence-gate]``.

Exit status: 0 if every package passes or is exempt, 1 otherwise, 2 on a usage or config error.
"""

import argparse
import importlib.metadata as md
import re
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"
PROFILES = ("base", "gpu", "mlip-mace", "mlip-uma")
SKIPPED = frozenset({"eta-rxncat", "pip"})
_TOKEN = re.compile(r"\s*(\(|\)|[A-Za-z0-9.+:-]+)")


class SpdxError(ValueError):
    """An SPDX licence expression could not be parsed."""


class ConfigError(ValueError):
    """The ``[tool.eta-rxncat.licence-gate]`` table is missing or malformed."""


def normalise(name: str) -> str:
    """Return the PEP 503 normalised form of a distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def tokenize(expression: str) -> list[str]:
    """Split an SPDX expression into identifiers, operators and parentheses.

    Raises:
        SpdxError: If the expression contains a character outside the SPDX grammar.
    """
    tokens: list[str] = []
    pos = 0
    text = expression.rstrip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None:
            raise SpdxError(f"unexpected character {text[pos]!r} at {pos} in {expression!r}")
        tokens.append(match.group(1))
        pos = match.end()
    if not tokens:
        raise SpdxError("empty expression")
    return tokens


class _Parser:
    """Recursive-descent evaluator: ``or := and (OR and)*``, ``and := with (AND with)*``."""

    def __init__(self, tokens: list[str], allowed: frozenset[str], exceptions: frozenset[str]):
        self.tokens = tokens
        self.pos = 0
        self.allowed = allowed
        self.exceptions = exceptions

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise SpdxError("unexpected end of expression")
        self.pos += 1
        return token

    def parse(self) -> bool:
        value = self.or_expr()
        if self.peek() is not None:
            raise SpdxError(f"unexpected token {self.peek()!r}")
        return value

    def or_expr(self) -> bool:
        value = self.and_expr()
        while self.peek() == "OR":
            self.take()
            right = self.and_expr()
            value = value or right
        return value

    def and_expr(self) -> bool:
        value = self.with_expr()
        while self.peek() == "AND":
            self.take()
            right = self.with_expr()
            value = value and right
        return value

    def with_expr(self) -> bool:
        token = self.take()
        if token == "(":
            value = self.or_expr()
            if self.take() != ")":
                raise SpdxError("missing ')'")
            return value
        if token in {"AND", "OR", "WITH", ")"}:
            raise SpdxError(f"expected a licence id, got {token!r}")
        value = token.removesuffix("+") in self.allowed
        if self.peek() == "WITH":
            self.take()
            exception = self.take()
            if exception in {"AND", "OR", "WITH", "(", ")"}:
                raise SpdxError(f"expected an exception id after WITH, got {exception!r}")
            value = value and exception in self.exceptions
        return value


def spdx_allowed(expression: str, allowed: frozenset[str], exceptions: frozenset[str]) -> bool:
    """Return whether an SPDX expression is satisfied by the allowed ids and exceptions.

    Raises:
        SpdxError: If the expression does not parse.
    """
    return _Parser(tokenize(expression), allowed, exceptions).parse()


@dataclass(frozen=True)
class Exemption:
    """A version-pinned exemption of one package in some profiles."""

    package: str
    version: str
    profiles: tuple[str, ...]
    licence: str
    pulled_in_by: str
    reason: str
    decision: str


@dataclass(frozen=True)
class NvidiaRule:
    """The single prefix rule: NVIDIA CUDA wheels with a proprietary licence (TJ Q1 A)."""

    prefix: str
    licences: frozenset[str]
    profiles: tuple[str, ...]
    reason: str
    decision: str


@dataclass(frozen=True)
class Config:
    """The parsed ``[tool.eta-rxncat.licence-gate]`` table."""

    allowed: frozenset[str]
    exceptions: frozenset[str]
    classifiers: Mapping[str, str]
    names: Mapping[str, str]
    exemptions: tuple[Exemption, ...]
    nvidia: NvidiaRule


def _strings(table: Mapping[str, Any], key: str) -> list[str]:
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"'{key}' must be a list of strings")
    return list(value)


def _text(table: Mapping[str, Any], key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"'{key}' must be a non-empty string")
    return value


def _profiles(table: Mapping[str, Any]) -> tuple[str, ...]:
    profiles = _strings(table, "profiles")
    unknown = sorted(set(profiles) - set(PROFILES))
    if unknown:
        raise ConfigError(f"unknown profiles {unknown}")
    return tuple(profiles)


def _string_map(table: Mapping[str, Any], key: str) -> dict[str, str]:
    value = table.get(key)
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        raise ConfigError(f"'{key}' must be a table of strings")
    return dict(value)


def load_config(path: Path) -> Config:
    """Read the gate configuration from ``path`` (a ``pyproject.toml``).

    Raises:
        ConfigError: If the table is missing or malformed.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    table = data.get("tool", {}).get("eta-rxncat", {}).get("licence-gate")
    if not isinstance(table, dict):
        raise ConfigError(f"{path} has no [tool.eta-rxncat.licence-gate] table")
    rule = table.get("nvidia-rule")
    if not isinstance(rule, dict):
        raise ConfigError("missing [tool.eta-rxncat.licence-gate.nvidia-rule]")
    exempt = table.get("exempt", [])
    if not isinstance(exempt, list) or not all(isinstance(e, dict) for e in exempt):
        raise ConfigError("'exempt' must be an array of tables")
    return Config(
        allowed=frozenset(_strings(table, "allowed")),
        exceptions=frozenset(_strings(table, "allowed-exceptions")),
        classifiers=_string_map(table, "classifiers"),
        names={k.lower(): v for k, v in _string_map(table, "names").items()},
        exemptions=tuple(
            Exemption(
                package=_text(e, "package"),
                version=_text(e, "version"),
                profiles=_profiles(e),
                licence=_text(e, "licence"),
                pulled_in_by=_text(e, "pulled-in-by"),
                reason=_text(e, "reason"),
                decision=_text(e, "decision"),
            )
            for e in exempt
        ),
        nvidia=NvidiaRule(
            prefix=_text(rule, "prefix"),
            licences=frozenset(_strings(rule, "licences")),
            profiles=_profiles(rule),
            reason=_text(rule, "reason"),
            decision=_text(rule, "decision"),
        ),
    )


@dataclass(frozen=True)
class Verdict:
    """The licence verdict of one distribution."""

    name: str
    version: str
    source: str
    licence: str
    resolved: tuple[str, ...]
    allowed: bool


def _shown(text: str) -> str:
    """Return a one-line, bounded rendering of a licence string for the report."""
    flat = " ".join(text.split())
    return flat if len(flat) <= 60 else flat[:57] + "..."


def judge(name: str, version: str, metadata: Any, config: Config) -> Verdict:
    """Judge one distribution's metadata (an ``email.message.Message``-like object)."""
    expression = (metadata.get("License-Expression") or "").strip()
    if expression:
        try:
            ok = spdx_allowed(expression, config.allowed, config.exceptions)
        except SpdxError as exc:
            return Verdict(
                name, version, "expression", f"{expression} (parse error: {exc})", (), False
            )
        return Verdict(name, version, "expression", expression, (expression,), ok)
    classifiers = [
        c.split(" :: ")[-1]
        for c in (metadata.get_all("Classifier") or [])
        if c.startswith("License ::") and c.split(" :: ")[-1] != "OSI Approved"
    ]
    if classifiers:
        resolved = tuple(config.classifiers.get(c, "") for c in classifiers)
        ok = any(r in config.allowed for r in resolved)
        return Verdict(name, version, "classifier", "; ".join(classifiers), resolved, ok)
    field = metadata.get("License") or ""
    stripped = field.strip()
    shown = _shown(field) if stripped else "UNKNOWN"
    if not stripped or "\n" in stripped:  # empty, or a full licence text: unrecognised
        return Verdict(name, version, "license-field", shown, (), False)
    mapped = config.names.get(stripped.lower())
    if mapped is not None:  # an exact known short name
        return Verdict(name, version, "license-field", shown, (mapped,), mapped in config.allowed)
    try:  # an allowed id, or a single-line SPDX expression of allowed ids
        ok = spdx_allowed(stripped, config.allowed, config.exceptions)
    except SpdxError:
        return Verdict(name, version, "license-field", shown, (), False)
    return Verdict(name, version, "license-field", shown, (stripped,) if ok else (), ok)


def installed(path: Sequence[str] | None) -> list[tuple[str, str, Any]]:
    """Return ``(name, version, metadata)`` of each distribution, deduplicated by name."""
    dists: Iterable[md.Distribution] = (
        md.distributions(path=list(path)) if path is not None else md.distributions()
    )
    seen: dict[str, tuple[str, str, Any]] = {}
    for dist in dists:
        name = dist.metadata["Name"]
        if not name or normalise(name) in SKIPPED or normalise(name) in seen:
            continue
        seen[normalise(name)] = (name, dist.version, dist.metadata)
    return [seen[k] for k in sorted(seen)]


def run(profile: str, config: Config, path: Sequence[str] | None) -> tuple[list[str], list[str]]:
    """Evaluate the environment; return the table rows and the ``FAIL`` lines."""
    exemptions = [e for e in config.exemptions if profile in e.profiles]
    used: set[int] = set()
    rows: list[str] = []
    fails: list[str] = []
    for name, version, metadata in installed(path):
        verdict = judge(name, version, metadata, config)
        status = "pass" if verdict.allowed else "FAIL"
        if not verdict.allowed:
            for index, exemption in enumerate(exemptions):
                if normalise(exemption.package) == normalise(name) and exemption.version == version:
                    used.add(index)
                    status = f"exempt ({exemption.decision})"
                    break
            else:
                rule = config.nvidia
                if (
                    profile in rule.profiles
                    and normalise(name).startswith(rule.prefix)
                    and bool(verdict.resolved)
                    and all(r in rule.licences for r in verdict.resolved)
                ):
                    status = f"exempt ({rule.decision})"
        rows.append(f"{name:28} {version:22} {verdict.source:13} {verdict.licence:62} {status}")
        if status == "FAIL":
            fails.append(f"FAIL {name}:{version} [{verdict.source}] {verdict.licence}")
    for index, exemption in enumerate(exemptions):
        if index not in used:
            fails.append(
                f"FAIL {exemption.package}:{exemption.version} [stale exemption] "
                f"not installed at this version or not failing ({exemption.decision})"
            )
    return rows, fails


def main(argv: Sequence[str] | None = None) -> int:
    """Run the gate and return its exit status (0 pass, 1 fail, 2 usage or config error)."""
    parser = argparse.ArgumentParser(prog="licence_gate.py", description=__doc__.splitlines()[0])
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help=argparse.SUPPRESS)
    parser.add_argument(
        "--path", action="append", help="test hook: a directory of *.dist-info folders"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rows, fails = run(args.profile, config, args.path)
    print(f"licence gate, profile {args.profile}, python {sys.executable}")
    for row in rows:
        print(row)
    for line in fails:
        print(line)
    print(f"{len(rows)} packages, {len(fails)} failures")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
