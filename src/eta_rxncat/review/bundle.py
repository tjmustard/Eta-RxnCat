"""Write the static, offline review bundle from ``RunData`` (v0.7.0, slice 08).

The bundle is a folder opened by double-click: no server, no network (mission G11, G12, R14, R15,
R17, R20). ``index.html`` carries a Python-rendered static summary that needs no JavaScript, and
the same bytes as ``run_data.json`` in a data ``<script>`` element for the view components.
Every file is a function of ``RunData`` and the vendored assets alone, so two writes of one
document give the same bytes.
"""

import hashlib
from collections.abc import Iterable, Sequence
from html import escape
from pathlib import Path
from urllib.parse import quote

from eta_rxncat.review.export import canonical_run_data_json
from eta_rxncat.review.run_data import (
    Candidate,
    EndpointDisposition,
    FrequencyCompleted,
    FrequencyEntry,
    FrequencyFailed,
    Gate,
    RunData,
    SampleDisposition,
    TSIdentity,
)

ASSETS_PATH = Path(__file__).with_name("assets")
"""The asset files shipped with the package (see ``assets/SOURCES.md``)."""

BUNDLE_ASSETS: tuple[str, ...] = ("3Dmol-min.js", "LICENSE-3Dmol.txt", "eta-view.js")
"""The files copied into the bundle's ``assets/`` directory."""

CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'none'"
)
"""The page's policy (mission R14): local scripts only, and no connection of any kind."""

NOT_RECORDED = "disposition not recorded"
"""The label of a row the document says nothing about (an older record or document)."""

BUNDLE_BYTE_LIMIT = 25_000_000
"""The bundle's size ceiling in bytes (mission R18)."""

TRAJECTORY_BYTE_BUDGET = 10_000_000
"""The exporter's trajectory budget behind ``review-bundle``.

The bundle holds the canonical document twice (``run_data.json`` and the embedded copy), so the
trajectories take twice this budget, leaving about 5 MB of ``BUNDLE_BYTE_LIMIT`` for the rest of
the document, the static summary and 3Dmol.
"""

_STYLE = """
body { font-family: system-ui, sans-serif; margin: 1.5em; color: #111; background: #fff; }
table { border-collapse: collapse; margin: 0.5em 0 1em; }
th, td { border: 1px solid #999; padding: 0.25em 0.6em; text-align: left; vertical-align: top; }
section { border-top: 2px solid #333; margin-top: 2em; }
.pass { background: #d9f2d9; }
.fail { background: #ffd6d6; font-weight: bold; }
.badge { display: inline-block; border: 1px solid #666; padding: 0 0.4em; margin: 0 0.2em 0.2em 0; }
.imag { color: #c00000; font-weight: bold; }
h5 { font-size: 1em; margin: 1em 0 0.3em; overflow-wrap: anywhere; }
.notused { border-left: 6px solid #999; padding-left: 0.8em; margin-top: 1.5em; }
.banner { border: 4px solid #c00000; background: #ffd6d6; color: #700000; font-size: 1.2em;
  font-weight: bold; padding: 0.5em 1em; margin: 0.5em 0; }
.warn { border: 2px solid #b36b00; background: #fff0d6; padding: 0.3em 0.8em; margin: 0.5em 0; }
"""


class BundleError(ValueError):
    """The bundle cannot be written where it was asked for; nothing is written."""


def _text(value: object) -> str:
    """Return ``value`` as HTML text (every interpolated string goes through here)."""
    return escape(str(value), quote=True)


def _anchor(candidate_id: str) -> str:
    """Return the ``href`` of a candidate's section (route ``#c/<candidate_id>``)."""
    return f"#c/{quote(candidate_id, safe='=+._:-@,')}"


def _gate_badge(gate: Gate) -> str:
    verdict = "pass" if gate.pass_bool else "fail"
    detail = ""
    if gate.value is not None:
        detail += f" value {gate.value:g}"
    if gate.threshold is not None:
        detail += f" threshold {gate.threshold:g}"
    if gate.unit is not None:
        detail += f" {gate.unit}"
    if gate.detail_code is not None:
        detail += f" [{gate.detail_code}]"
    return (
        f'<span class="badge {verdict}">{_text(gate.gate_id)}: {verdict.upper()}'
        f"{_text(detail)}</span>"
    )


def _gates(gates: Iterable[Gate]) -> str:
    return "".join(_gate_badge(g) for g in gates) or "no gates"


def _atom(symbols: Sequence[str], i: int) -> str:
    """Return an atom's label: its element and 0-based index (the index alone if unknown)."""
    return f"{symbols[i]}{i}" if i < len(symbols) else str(i)


def _pair(symbols: Sequence[str], i: int, j: int) -> str:
    return f"{_atom(symbols, i)}\u2013{_atom(symbols, j)}"


def _sample_label(disposition: SampleDisposition, symbols: Sequence[str]) -> str:
    """Return what became of a transition-state sample, as its block heading names it."""
    if disposition.kind == "member":
        weight = disposition.weight_fraction
        return "member" if weight is None else f"member (weight {weight:.3f})"
    if disposition.kind == "merged":
        return f"merged into sample {disposition.merged_into_index}"
    prefix = "excluded" if disposition.kind == "excluded" else "fell through"
    reason = disposition.reason_code or "no reason recorded"
    clash = disposition.clash
    if clash is not None:
        reason += f" {_pair(symbols, clash.i, clash.j)} {clash.distance_angstrom:.3f} \u00c5"
    changes = [
        f"{verb} {', '.join(_pair(symbols, *bond) for bond in bonds)}"
        for verb, bonds in (
            ("formed", disposition.bonds_formed),
            ("broken", disposition.bonds_broken),
        )
        if bonds
    ]
    if changes:
        reason += f" ({'; '.join(changes)})"
    return f"{prefix}: {reason}"


def _endpoint_label(disposition: EndpointDisposition) -> str:
    """Return what became of a minimum's row, as its block heading names it."""
    if disposition.kind == "kept":
        return "kept"
    if disposition.kind == "superseded_by_push":
        pushed = disposition.superseded_by_frequency_id
        return "superseded by push" + ("" if pushed is None else f" \u2192 {pushed}")
    if disposition.kind == "dropped":
        return f"dropped: {disposition.reason_code or 'no reason recorded'}"
    return NOT_RECORDED


def _ts_rows(candidate: Candidate) -> list[tuple[bool, str | None, SampleDisposition | None]]:
    """Return ``(used, frequency_id, disposition)`` per TS sample, used ones first.

    A frequency id no disposition names (an older document) follows without one; it counts as
    used only when it is a member's.
    """
    rows: list[tuple[bool, str | None, SampleDisposition | None]] = [
        (d.kind == "member", d.frequency_id, d) for d in candidate.sample_dispositions
    ]
    named = {d.frequency_id for d in candidate.sample_dispositions}
    members = {m.frequency_id for m in candidate.members}
    rows += [(f in members, f, None) for f in candidate.frequency_ids if f not in named]
    return sorted(rows, key=lambda row: not row[0])


def _endpoint_rows(candidate: Candidate) -> list[tuple[bool, str, EndpointDisposition | None]]:
    """Return ``(used, frequency_id, disposition)`` per minimum row, used (``kept``) first."""
    rows: list[tuple[bool, str, EndpointDisposition | None]] = [
        (d.kind == "kept", d.frequency_id, d) for d in candidate.endpoint_dispositions
    ]
    named = {d.frequency_id for d in candidate.endpoint_dispositions}
    rows += [(False, f, None) for f in candidate.endpoint_frequency_ids if f not in named]
    return sorted(rows, key=lambda row: not row[0])


def _short_kind(used: bool, disposition: SampleDisposition | None) -> str:
    if disposition is not None:
        return disposition.kind.replace("_", " ")
    return "member" if used else "not recorded"


def _n_imaginary(candidate: Candidate, frequencies: dict[str, FrequencyEntry]) -> str:
    """Return the index cell of a unit's TS imaginary-mode counts, each with its disposition."""
    cells = []
    for used, frequency_id, disposition in _ts_rows(candidate):
        if frequency_id is None:
            continue
        entry = frequencies[frequency_id]
        kind = _text(_short_kind(used, disposition))
        if isinstance(entry, FrequencyCompleted):
            identity = None if disposition is None else disposition.identity
            failed = identity is not None and not identity.passed_bool
            bad = ' class="fail"' if entry.n_imaginary != 1 or failed else ""
            cells.append(f"<span{bad}>{entry.n_imaginary}</span> ({kind})")
        else:
            cells.append(f'<span class="warn">{entry.status}</span> ({kind})')
    return ", ".join(cells) or "none"


def _index_table(run_data: RunData) -> str:
    frequencies = {f.frequency_id: f for f in run_data.frequencies}
    rows = []
    for candidate in run_data.candidates:
        gates = [g for g in run_data.gates if g.candidate_entry_id == candidate.candidate_entry_id]
        rows.append(
            "<tr>"
            f'<td><a href="{_text(_anchor(candidate.candidate_id))}">'
            f"{_text(candidate.candidate_id)}</a></td>"
            f"<td>{_text(candidate.pathway)}</td>"
            f"<td>{_text(candidate.engine_id)}</td>"
            f"<td>{_n_imaginary(candidate, frequencies)}</td>"
            f"<td>{_gates(gates)}</td>"
            "</tr>"
        )
    run_gates = [g for g in run_data.gates if g.candidate_entry_id is None]
    return (
        "<table><thead><tr><th>Candidate</th><th>Pathway</th><th>Engine</th>"
        "<th>TS imaginary modes</th><th>Gates</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"<p>Gates over the whole record: {_gates(run_gates)}</p>"
    )


def _identity_text(identity: TSIdentity, symbols: Sequence[str]) -> str:
    """Return the identity numbers of a transition state as a paragraph."""

    def number(value: float | None, digits: int) -> str:
        return "none" if value is None else f"{value:.{digits}f}"

    distances = ", ".join(
        f"{_pair(symbols, d.i, d.j)} {d.distance_angstrom:.3f} \u00c5"
        for d in identity.forming_distances
    )
    phase = {True: "yes", False: "no", None: "not evaluated"}[identity.in_phase_bool]
    verdict = "pass" if identity.passed_bool else f"FAIL ({', '.join(identity.reason_codes)})"
    text = (
        f"Identity: imaginary frequency "
        f"{number(identity.imaginary_frequency_cm1, 1)} cm\u207b\u00b9; "
        f"forming-bond overlap {number(identity.forming_overlap, 3)}; "
        f"active-core KE fraction {number(identity.active_core_ke_fraction, 3)}; "
        f"forming distances {distances}; in phase {phase}; {verdict}"
    )
    return f"<p>{_text(text)}</p>"


def _frequency_block(
    entry: FrequencyEntry,
    *,
    role: str,
    expected: int,
    name: str,
    species: str,
    label: str,
    identity: TSIdentity | None = None,
    symbols: Sequence[str] = (),
) -> str:
    """Return one frequency entry, headed by its disposition.

    The banner is raised by a mode count other than ``expected`` or a failed identity.
    """
    title = f"<h5>{_text(role)}: {_text(species)} ({_text(name)}) \u2014 {_text(label)}</h5>"
    if isinstance(entry, FrequencyFailed):
        return (
            f'{title}<p class="warn">Frequencies failed: {_text(entry.failed_code)}. '
            "The imaginary-mode count is unknown.</p>"
        )
    if not isinstance(entry, FrequencyCompleted):
        return (
            f'{title}<p class="warn">Frequencies missing from the store. '
            "The imaginary-mode count is unknown.</p>"
        )
    problems = []
    if entry.n_imaginary != expected:
        problems.append(f"{role} has {entry.n_imaginary} imaginary mode(s); expected {expected}.")
    if identity is not None and not identity.passed_bool:
        problems.append(f"{role} identity check failed: {', '.join(identity.reason_codes)}.")
    banner = ""
    if problems:
        banner = f'<div class="banner">WARNING: {_text(" ".join(problems))}</div>'
    values = ", ".join(
        f'<span class="imag">{f:.1f}</span>' if f < -entry.imag_tol_cm1 else f"{f:.1f}"
        for f in entry.frequencies_cm1
    )
    checks = ""
    if identity is not None:
        checks = _identity_text(identity, symbols)
    elif expected == 1:
        checks = "<p>Identity numbers not available.</p>"
    return (
        f"{title}{banner}{checks}"
        f"<p>n_imaginary = {entry.n_imaginary} (below -{entry.imag_tol_cm1:g} cm<sup>-1</sup>)</p>"
        f"<p>Frequencies / cm<sup>-1</sup>: {values}</p>"
    )


def _unit_summary(run_data: RunData, candidate: Candidate) -> str:
    frequencies = {f.frequency_id: f for f in run_data.frequencies}
    species = {s.species_id: s for s in run_data.species}
    members = {m.frequency_id: m.member_index for m in candidate.members if m.frequency_id}
    gates = [g for g in run_data.gates if g.candidate_entry_id == candidate.candidate_entry_id]
    blocks: dict[bool, list[str]] = {True: [], False: []}
    for used, frequency_id, sample in _ts_rows(candidate):
        if frequency_id is None:
            assert sample is not None  # only a disposition lacks a frequency row
            symbols = species.get(sample.template_id, species[candidate.species_id]).symbols
            line = (
                f"Sample {sample.sample_index} ({sample.source}, template "
                f"{sample.template_id}): {_sample_label(sample, symbols)}"
            )
            blocks[used].append(f"<p>{_text(line)}</p>")
            continue
        entry = frequencies[frequency_id]
        unit_species = species[entry.species_id]
        index = members.get(frequency_id) if sample is None else sample.sample_index
        key = entry.stage_key[:12]
        if index is None:
            name = f"sample {key}"
        else:
            name = f"member {index}, sample {key}" if used else f"sample {index}, {key}"
        if sample is not None:
            label = _sample_label(sample, unit_species.symbols)
        else:
            label = "member" if used else NOT_RECORDED
        blocks[used].append(
            _frequency_block(
                entry,
                role="Transition state",
                expected=1,
                name=name,
                species=unit_species.label,
                label=label,
                identity=None if sample is None else sample.identity,
                symbols=unit_species.symbols,
            )
        )
    if not candidate.frequency_ids:
        reason = candidate.stop_reason_code or "no reason recorded"
        blocks[False].append(
            f'<p class="warn">No transition-state frequencies for this run: {_text(reason)}</p>'
        )
    for used, frequency_id, endpoint in _endpoint_rows(candidate):
        entry = frequencies[frequency_id]
        blocks[used].append(
            _frequency_block(
                entry,
                role="Minimum",
                expected=0,
                name=f"sample {entry.stage_key[:12]}",
                species=species[entry.species_id].label,
                label=NOT_RECORDED if endpoint is None else _endpoint_label(endpoint),
            )
        )
    groups = "".join(
        f'<div class="{css}"><h4>{title}</h4>{"".join(blocks[used]) or "<p>none</p>"}</div>'
        for used, css, title in (
            (True, "used", "Used in the result"),
            (False, "notused", "Not used (rejected, merged or superseded)"),
        )
    )
    return (
        f"<h3>Pathway {_text(candidate.pathway)}, engine {_text(candidate.engine_id)}</h3>"
        f"<p>Charge {candidate.charge}, multiplicity {candidate.spin_multiplicity}</p>"
        f"<p>Gates: {_gates(gates)}</p>{groups}"
    )


def _candidate_sections(run_data: RunData) -> str:
    """Return one section per candidate id, each with its static summary above its panels."""
    units: dict[str, list[Candidate]] = {}
    for candidate in run_data.candidates:
        units.setdefault(candidate.candidate_id, []).append(candidate)
    return "".join(
        f'<section id="c/{_text(candidate_id)}"><h2>Candidate {_text(candidate_id)}</h2>'
        f"{''.join(_unit_summary(run_data, c) for c in group)}"
        f'<div class="eta-panels" data-candidate="{_text(candidate_id)}"></div></section>'
        for candidate_id, group in units.items()
    )


def _index_html(run_data: RunData, data: bytes) -> bytes:
    provenance = run_data.provenance
    scripts: Sequence[str] = ("assets/3Dmol-min.js", "assets/eta-view.js")
    page = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f'<meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>eta-rxncat review bundle</title>\n<style>{_STYLE}</style>\n</head>\n<body>\n"
        "<h1>eta-rxncat review bundle</h1>\n"
        f"<p>eta {_text(provenance.eta_version)}, store "
        f"{_text(provenance.store_file_name)}, run-data schema "
        f"{run_data.schema_version}</p>\n"
        f"{_index_table(run_data)}\n"
        f"{_candidate_sections(run_data)}\n"
        # The canonical bytes escape <, > and &, so they cannot end this element.
        f'<script type="application/json" id="run-data">{data.decode("ascii")}</script>\n'
        + "".join(f'<script src="{src}"></script>\n' for src in scripts)
        + "</body>\n</html>\n"
    )
    return page.encode("utf-8")


def write_review_bundle(run_data: RunData, out_dir: str | Path) -> Path:
    """Write the review bundle of ``run_data`` into ``out_dir`` and return that directory.

    The bundle is ``index.html``, ``run_data.json``, ``assets/`` and ``MANIFEST.sha256`` (one
    ``<sha256>  <path>`` line per other file, sorted by path, as ``sha256sum -c`` reads it).

    Args:
        run_data: The document to render.
        out_dir: A directory that does not exist yet, or is empty.

    Raises:
        BundleError: ``out_dir`` is a file or a directory with something in it.
        OSError: The files cannot be written.
    """
    out = Path(out_dir)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise BundleError(f"the output directory is not empty: {out}")
    data = canonical_run_data_json(run_data)
    files = {
        "index.html": _index_html(run_data, data),
        "run_data.json": data,
        **{f"assets/{name}": (ASSETS_PATH / name).read_bytes() for name in BUNDLE_ASSETS},
    }
    manifest = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name}\n"
        for name, content in sorted(files.items())
    )
    (out / "assets").mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_bytes(content)
    (out / "MANIFEST.sha256").write_bytes(manifest.encode("ascii"))
    return out
