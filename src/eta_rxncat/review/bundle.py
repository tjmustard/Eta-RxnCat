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
    FrequencyCompleted,
    FrequencyEntry,
    FrequencyFailed,
    Gate,
    RunData,
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


def _n_imaginary(candidate: Candidate, frequencies: dict[str, FrequencyEntry]) -> str:
    """Return the index cell of a unit's transition-state imaginary-mode counts."""
    cells = []
    for frequency_id in candidate.frequency_ids:
        entry = frequencies[frequency_id]
        if isinstance(entry, FrequencyCompleted):
            bad = ' class="fail"' if entry.n_imaginary != 1 else ""
            cells.append(f"<span{bad}>{entry.n_imaginary}</span>")
        else:
            cells.append(f'<span class="warn">{entry.status}</span>')
    return " ".join(cells) or "none"


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


def _frequency_block(
    entry: FrequencyEntry, *, role: str, expected: int, name: str, species: str
) -> str:
    """Return one frequency entry; a count other than ``expected`` raises the banner."""
    title = f"<h4>{_text(role)}: {_text(species)} ({_text(name)})</h4>"
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
    banner = ""
    if entry.n_imaginary != expected:
        banner = (
            f'<div class="banner">WARNING: {_text(role)} has {entry.n_imaginary} imaginary '
            f"mode(s); expected {expected}.</div>"
        )
    values = ", ".join(
        f'<span class="imag">{f:.1f}</span>' if f < -entry.imag_tol_cm1 else f"{f:.1f}"
        for f in entry.frequencies_cm1
    )
    return (
        f"{title}{banner}"
        f"<p>n_imaginary = {entry.n_imaginary} (below -{entry.imag_tol_cm1:g} cm<sup>-1</sup>)</p>"
        f"<p>Frequencies / cm<sup>-1</sup>: {values}</p>"
    )


def _unit_summary(run_data: RunData, candidate: Candidate) -> str:
    frequencies = {f.frequency_id: f for f in run_data.frequencies}
    species = {s.species_id: s.label for s in run_data.species}
    members = {m.frequency_id: m.member_index for m in candidate.members if m.frequency_id}
    gates = [g for g in run_data.gates if g.candidate_entry_id == candidate.candidate_entry_id]
    blocks = []
    for frequency_id in candidate.frequency_ids:
        entry = frequencies[frequency_id]
        name = (
            f"member {members[frequency_id]}"
            if frequency_id in members
            else f"sample {entry.stage_key[:12]}"
        )
        blocks.append(
            _frequency_block(
                entry,
                role="Transition state",
                expected=1,
                name=name,
                species=species[entry.species_id],
            )
        )
    if not candidate.frequency_ids:
        reason = candidate.stop_reason_code or "no reason recorded"
        blocks.append(
            f'<p class="warn">No transition-state frequencies for this run: {_text(reason)}</p>'
        )
    for frequency_id in candidate.endpoint_frequency_ids:
        entry = frequencies[frequency_id]
        blocks.append(
            _frequency_block(
                entry,
                role="Minimum",
                expected=0,
                name=f"sample {entry.stage_key[:12]}",
                species=species[entry.species_id],
            )
        )
    return (
        f"<h3>Pathway {_text(candidate.pathway)}, engine {_text(candidate.engine_id)}</h3>"
        f"<p>Charge {candidate.charge}, multiplicity {candidate.spin_multiplicity}</p>"
        f"<p>Gates: {_gates(gates)}</p>{''.join(blocks)}"
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
