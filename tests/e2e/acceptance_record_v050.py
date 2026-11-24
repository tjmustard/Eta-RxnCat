r"""Merge the v0.5.0 Tier 3 acceptance files into docs/prd/v0.5.0/ACCEPTANCE_RESULT.json.

Usage::

    python3 tests/e2e/acceptance_record_v050.py suite <default_suite.log> <default_suite.json>
    python3 tests/e2e/acceptance_record_v050.py add-command <commands.json> <log> <exit_code> \\
        <wall_s> <env.json> -- <argv...>
    python3 tests/e2e/acceptance_record_v050.py merge <acceptance_xtb.json> \\
        <acceptance_uma.json> <commands.json> <default_suite.json> <out.json> [<prior_record.json>]

``add-command`` appends one run (argv, env, exit code, wall time, the pytest summary and the max
RSS read from its log) to ``commands.json``; ``suite`` derives the ``default_suite`` block from
the pytest log. Neither is typed by hand. Before TJ's Phase 3 the record has no ``verdict``
(slice 12). Once TJ's promoted fixtures are on disk and equal R33's sha256s and blob ids
(``promotion_evidence``), the merge writes ``verdict`` from ``record_verdict``: ``pass`` only with
every gated check ``pass``, a clean default suite and every command at exit 0 with no skip;
anything ``fail``, ``pending_*``, ``skipped`` or ``missing`` gives ``fail`` (R56, v0.4.0 R27). The
verdict run carries the slice 12 reproducibility measurement over from the prior record.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from acceptance_record_v040 import pytest_counts
from t3 import PROMOTED_V050, REGRESSION_BOUNDS

REPO = Path(__file__).resolve().parents[2]
CASES = ("ts1a_n", "ts1b_n", "ts3a", "ts4a", "n4")
RECIPES = ("xtb", "uma")
REPORT_ONLY = frozenset({("xtb", "ts4a")})
"""R32 (TJ Q-TJ4 A): GFN2 TS4a is report-only; nothing of it is gated."""
STATES = {"pass", "fail", "pending_promotion", "pending_confirmation", "skipped", "missing"}
"""A gated check's state (slice 12 SPEC); ``reported`` marks a value that is never gated."""
TEST_OUTCOMES = {"passed", "failed", "missing", "report_only"}
GFN2_IDENTITY_CORE = ("forming_overlap", "forming_in_phase", "active_core")
"""R32: the GFN2 identity core (overlap >= 0.50, in phase, KE >= 0.60) on every case but TS4a."""

HF1_SHA256 = {
    "TS3a.xyz": "6bf308b6846732718499d2370f355116a849a232f476c27a026dafb5ab1ea1b4",
    "TS4a.xyz": "b00f6a874efd2b30112e34d2cb16892923f73b756e7bdbca4a2f6583b4bf008c",
    "cyclobutenone.xyz": "c489e5124f42895bb0408f127aa10d51db70ccfbd72f4cf5c929c10052f4f30c",
    "TS_N4.xyz": "cf7e45014bdab5971b2c993da3f2d5125ce744a8def5bda64998e047dc3dc46f",
    "3_dimethyltetrazine.xyz": "e42ed53adaa7bc3a9fe542d88cafb632d4351c3e419e9b2b3b3b961744a7662d",
    "4_bis_cf3_tetrazine.xyz": "174c23d2c794196f7d1fa5367529fe623e1529007bab76cb32b9139816e92f74",
}
"""Mission HF-1: the six slice 07 transcriptions (the same values test_t3_inputs.py checks)."""
XYZ_DIR = REPO / "tests" / "e2e" / "data" / "e2e5" / "xyz"
R9_BOUND_HARTREE = 1e-4
R9_SOURCE = (
    "missions/release-0.5.0/slices/07-tier3-inputs/proof/01-qa.md, MR5 R9 table (auditor rerun "
    "through test_r9_pyscf_reproduces_liu_energy, cuda, M06-2X/6-31G(d) cartesian basis, R30)"
)
R9_PROOF = {
    "TS1a_n": (-310.5591789251, -2.493e-05),
    "5_cyclopropene": (-116.5625577450, -5.745e-06),
    "TS3a": (-491.3668527636, -2.676e-05),
    "TS4a": (-1086.6276171274, -2.213e-05),
    "3_dimethyltetrazine": (-374.8096524937, -8.249e-05),
    "4_bis_cf3_tetrazine": (-970.0570537571, -6.176e-05),
}
"""Slice 07 proof values (E_pyscf, E_pyscf - E_Liu in Eh), transcribed; R9 is not rerun here."""

TJ_BOUNDS = {
    "abs_delta_ts_energy_hartree": 1e-5,
    "heavy_rmsd_angstrom": 0.01,
    "abs_delta_dG_dagger_1M_kcal_mol": 0.01,
}
"""TJ's v0.4.0 Q6 numbers (|ΔE| <= 1e-5 Eh, heavy RMSD <= 0.01 Å) and |ΔΔG‡| <= 0.01 kcal/mol."""
BOUND_RULE = (
    "propose TJ's bound only if every measured difference of that recipe is <= 1/10 of it; "
    "otherwise propose 10x the measured maximum (slice 12 SPEC; the numeric bounds are TJ's, "
    "v0.3.0 R1 'R1. A')"
)
KNOWN_LIMITS = (
    "GFN2 TS4a is report-only (TJ Q-TJ4 A, mission R32): from the grafted, pre-relaxed start GFN2 "
    "finds no converged TS of this reaction; it is recorded as measured and never gated",
    "on GFN2 the forming-distance window of the identity check, ΔG‡ and the TS4a < TS3a ordering "
    "are reported, not gated (TJ Q-TJ3 A as amended by Q-TJ4 A, mission R4/R32)",
    "an xtb crash (exit 128) inside a TS search raises EngineError out of run_transition_state "
    "instead of a cached failed_reason; a v0.6.0+ robustness item (mission R32), not built",
)
REPORTED_NOTES = {
    "geometric_hessian_units": (
        "the cross-check seeds geometric-optimize with eta's Cartesian Hessian in Eh/Bohr^2; "
        "--help gives the file format but no units, so the units are an assumption (slice 11)"
    ),
    "geometric_licence": (
        "geomeTRIC 1.1.1 is 'BSD 3-clause Non-AI'; the licence question is open with TJ; it runs "
        "only as a CLI subprocess in .venv-accept-uma, nothing in src/ imports it (slice 11)"
    ),
    "gfn2_ts3a_cross_check": (
        "on GFN2 TS3a geomeTRIC converged to a soft saddle that is not the reaction's "
        "(about -37 cm^-1, forming overlap 0.0), while eta's GFN2 TS3a passes the identity "
        "core; reported, not gated (slice 11 audit)"
    ),
}
PROMOTION = {
    "source": "mission R33 (TJ's Phase 3; closes R28)",
    "commit": "ccacac5",
    "commit_subject": "Promote v0.5.0 Tier 3 fixtures (TJ's Phase 3 review)",
    "tj_answer_verbatim": "A: 0.75 all (Recommended)",
    "option_text_verbatim": (
        "UMA barrier tolerance 0.75 kcal/mol (10x the largest variation seen). Everything else "
        "stays at your v0.4.0 tolerances: energy 1e-5 Eh, geometry 0.01 Å, xtb barrier 0.01."
    ),
    "relayed_by": "operator-agent@kernel, qitem-20261124221114-efeccb6d9876cb00, 22:12Z",
    "scope_all": "every UMA case (operator-confirmed); xtb stays 0.01",
    "transcriptions_confirmed": (
        "option A: the six SI files (TS3a, TS4a, 3_dimethyltetrazine, 4_bis_cf3_tetrazine, "
        "cyclobutenone, TS_N4) and the five t3_*.yaml (TJ A3 / Q-E3)"
    ),
}
"""TJ's Phase 3 answer as the lead recorded it in mission R33 (never inferred from a status)."""
PROMOTED_FILES = {
    "t3_cross_check.json": (
        "c64465871b46fc31fcc63e074a907bb31a1e1a56c8486de3303b1a6d42077b8b",
        "55d0002c4a1c672f85b4b56e12a367a1a08556a4",
    ),
    "t3_n4.uma.json": (
        "965f2ff96cd6555a332b86232b22ab37c1c3f4106e29861607eab38e63918412",
        "2784a0b42ea6aefcbbad148c2c8a0a8b85f34e7a",
    ),
    "t3_n4.xtb.json": (
        "5ccb927814bdb6d5cac6542464452487858d83b711b98cfc5669d599087a1837",
        "209e9173b061c1f3e7094cb3b3f465e8daa515ef",
    ),
    "t3_ts1a_n.uma.json": (
        "00ed79b684cf016b949c426b632f72fea467090c0875527a0c12983cd339237e",
        "daa72d93980e9140df75834f0bb4487f7e8ddca2",
    ),
    "t3_ts1a_n.xtb.json": (
        "66ce057e26a6e0299c2717ba363395a4c58cdb866648f242bbbc9beaf6415691",
        "09cdd938e5e3f6bb7fa8d1dcc6f2e0ec2898f8c7",
    ),
    "t3_ts1b_n.uma.json": (
        "dfd0657cc94c12d63c6dc2140a183d4767f42c56ed9fdc8e82cc2d2c9e2d8f24",
        "856059550f74cdf90a7c51eea65b7a72d54a23bd",
    ),
    "t3_ts1b_n.xtb.json": (
        "80845cf09a1b122b22502a0072c525efcceda0bd37b18d70546e4adbf03d0add",
        "15463d0a0404465a173b2e515ad2d6eb45068aae",
    ),
    "t3_ts3a.uma.json": (
        "418a504e47eda5a8bc81a1fd6f4005024fd42a49ae888692e63e3b1f8b8e77d1",
        "5d10a2019d69786e4908d4748ec11e86fc0fa0a6",
    ),
    "t3_ts3a.xtb.json": (
        "0028815f265e2fca680cc46c4c4b41a50d82e268737612b9e23265abee11fc8c",
        "d223ea7f9924262b4791932fd893beb94b0352fc",
    ),
    "t3_ts4a.uma.json": (
        "50bd7126d6d57cba501a8611a545efba1ef90193fc37338f5466d4c40b30ab94",
        "d34adea8ddd5c9caeb9a6540d9a3f8e594be7b7a",
    ),
    "t3_ts4a.xtb.json": (
        "5697b52a2394e9097241fd50642685e5a6d39240e371cf042ebc7504e6aaab6f",
        "d37eae2f277869712f0dac7ac7d72ab4f4ae6807",
    ),
}
"""Mission R33's promoted files: (sha256, git blob id), re-verified at ``ccacac5``."""
TOP_KEYS = (
    "record_schema",
    "commit_sha",
    "run_at_utc",
    "hardware",
    "engines",
    "devices",
    "environment",
    "commands",
    "logs",
    "default_suite",
    "known_limits",
    "reported_notes",
    "evidence",
    "fixtures",
    "reproducibility",
    "proposed_regression_bounds",
)
VERDICT_KEYS = ("verdict", "verdict_reasons", "regression_bounds")
"""Required once the record states a verdict (slice 13)."""
FIXTURE_KEYS = {"t3", "cross_check", "transcriptions", "transcription_confirmation"}


# --- states and verdict ---------------------------------------------------------------------


def _status(value: Any) -> Any:
    return value.get("status") if isinstance(value, dict) else value


def entry_states(entry: dict[str, Any]) -> dict[str, Any]:
    """The gated states of one case x recipe entry (a report-only entry has none)."""
    if entry.get("report_only") is True:
        return {}
    outcome = entry.get("test_outcome")
    if outcome == "missing":
        return {"test_outcome": "missing"}
    states: dict[str, Any] = {} if outcome == "passed" else {"test_outcome": "fail"}
    for gate, value in sorted(entry.get("tier_gates", {}).items()):
        if _status(value) != "reported":
            states[f"tier_gates.{gate}"] = _status(value)
    states["regression"] = _status(entry.get("regression"))
    if "identity_core" in entry:
        states["identity_core"] = _status(entry["identity_core"])
    return states


def fixture_states(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Every gated state of the record's ``fixtures`` by dotted name."""
    states: dict[str, Any] = {}
    t3 = fixtures.get("t3", {})
    for case in CASES:
        for recipe in RECIPES:
            entry = t3.get(case, {}).get(recipe, {"test_outcome": "missing"})
            if (recipe, case) in REPORT_ONLY and entry.get("report_only") is not True:
                states[f"t3.{case}.{recipe}.report_only"] = "fail"
            for name, state in entry_states(entry).items():
                states[f"t3.{case}.{recipe}.{name}"] = state
    states["cross_check"] = _status(fixtures.get("cross_check", {"status": "missing"}))
    transcriptions = fixtures.get("transcriptions", {})
    for part in ("sha256", "r9"):
        states[f"transcriptions.{part}"] = _status(transcriptions.get(part, {"status": "missing"}))
    confirmation = _status(fixtures.get("transcription_confirmation", {"status": "missing"}))
    states["transcription_confirmation"] = "pass" if confirmation == "confirmed" else confirmation
    return states


def _suite_failures(block: dict[str, Any]) -> list[str]:
    code, failed, errors = block.get("exit_code"), block.get("failed", 0), block.get("errors", 0)
    if code != 0 or failed or errors:
        return [f"default_suite: exit_code {code}, failed {failed}, errors {errors}"]
    return []


def _command_failures(commands: list[dict[str, Any]]) -> list[str]:
    reasons = []
    for i, command in enumerate(commands):
        where = f"commands[{i}] {' '.join(command.get('argv', [])[-3:])}"
        if command.get("exit_code") != 0:
            reasons.append(f"{where}: exit_code {command.get('exit_code')}")
        skipped = pytest_counts(str(command.get("summary", "")))["skipped"]
        if skipped:
            reasons.append(f"{where}: {skipped} skipped")
    return reasons


def record_verdict(
    fixtures: dict[str, Any],
    default_suite: dict[str, Any] | None = None,
    commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The verdict rule (R56, v0.4.0 R27): ``pass`` or ``fail`` with the reasons.

    ``fail`` on a missing or failing default suite (non-zero exit, failures or errors), a command
    with a non-zero exit or a skip, no commands, or any gated check that is not ``pass``
    (``fail``, ``pending_*``, ``skipped``, ``missing`` or an unknown state). A report-only entry
    (GFN2 TS4a) never contributes.
    """
    reasons: list[str] = []
    if default_suite is None:
        reasons.append("default_suite: missing")
    else:
        reasons += _suite_failures(default_suite)
    if not commands:
        reasons.append("commands: none recorded")
    reasons += _command_failures(commands or [])
    for name, state in fixture_states(fixtures).items():
        if state != "pass":
            reasons.append(f"{name}: {state}")
    return {"verdict": "fail" if reasons else "pass", "verdict_reasons": reasons}


def check(record: dict[str, Any]) -> list[str]:
    """Schema problems of a record (empty when valid).

    A pre-promotion record has no ``verdict``; a stated verdict must equal ``record_verdict`` and
    needs TJ's regression bounds and a verified ``evidence.promotion``.
    """
    problems = [f"missing {key}" for key in TOP_KEYS if key not in record]
    if "verdict" in record or "verdict_reasons" in record:
        problems += [f"missing {key}" for key in VERDICT_KEYS if key not in record]
        promotion = record.get("evidence", {}).get("promotion", {})
        if promotion.get("status") != "verified":
            problems.append("a verdict needs evidence.promotion verified")
    if record.get("record_schema") != 1:
        problems.append("record_schema is not 1")
    fixtures = record.get("fixtures", {})
    if set(fixtures) != FIXTURE_KEYS:
        problems.append(f"fixtures keys {sorted(fixtures)} != {sorted(FIXTURE_KEYS)}")
    t3 = fixtures.get("t3", {})
    if set(t3) != set(CASES) or any(set(t3[c]) != set(RECIPES) for c in t3):
        problems.append("fixtures.t3 must be every case x recipe")
    for name, state in fixture_states(fixtures).items():
        if state not in STATES:
            problems.append(f"{name}: state {state!r} not in {sorted(STATES)}")
    for case in t3:
        for recipe, entry in t3[case].items():
            if entry.get("test_outcome") not in TEST_OUTCOMES:
                problems.append(f"t3.{case}.{recipe}: test_outcome {entry.get('test_outcome')!r}")
            if (recipe, case) not in REPORT_ONLY and entry.get("report_only"):
                problems.append(f"t3.{case}.{recipe}: only GFN2 TS4a may be report-only (R32)")
    if list(record.get("known_limits", [])) != list(KNOWN_LIMITS):
        problems.append("known_limits are not the fixed lines")
    for key in ("command", "exit_code", "passed", "failed"):
        if key not in record.get("default_suite", {}):
            problems.append(f"default_suite: missing {key}")
    if "verdict" in record or "verdict_reasons" in record:
        expected = record_verdict(fixtures, record.get("default_suite"), record.get("commands"))
        stated = {k: record.get(k) for k in expected}
        if stated != expected:
            problems.append(f"verdict {stated} is not the record's verdict {expected}")
    return problems


# --- entries from the fragments -------------------------------------------------------------


def identity_core(tier_gates: dict[str, Any]) -> dict[str, Any]:
    """R32: the GFN2 identity core from the gated overlap, in-phase and KE statuses."""
    parts = {g: _status(tier_gates.get(g, {"status": "missing"})) for g in GFN2_IDENTITY_CORE}
    if any(s == "missing" for s in parts.values()):
        return {"status": "missing", "parts": parts}
    return {"status": "pass" if set(parts.values()) == {"pass"} else "fail", "parts": parts}


def case_entry(
    fragment: dict[str, Any], case: str, recipe: str, promoted: bool = False
) -> dict[str, Any]:
    """The record entry of one case x recipe from its in-process fragment.

    Before the promotion the regression is ``pending_promotion``; after it, the fragment's own
    in-process comparison with the promoted fixture (``t3.regression_ts``), ``missing`` if absent.
    """
    if fragment.get("test_outcome") == "missing":
        return {"test_outcome": "missing"}
    gates = dict(fragment.get("checks", {}).get("tier_gates", {}))
    barrier = fragment.get("barrier")
    entry: dict[str, Any] = {
        "test_outcome": fragment.get("test_outcome"),
        "failed_checks": fragment.get("failed_checks", []),
        "tier_gates": gates,
        "window_dG_dagger_1M_kcal_mol": fragment.get("window_dG_dagger_1M_kcal_mol"),
        "dG_dagger_1M_kcal_mol": None if barrier is None else barrier["dG_dagger_1M_kcal_mol"],
        "reported": fragment.get("reported"),
        "second_run_cache": fragment.get("second_run_cache"),
    }
    if "graft_summary" in fragment:
        summary = dict(fragment["graft_summary"])
        summary.pop("pre_relaxed_start", None)
        entry["graft_summary"] = summary
    if (recipe, case) in REPORT_ONLY:
        for key in ("report_only", "reported_outcome", "failed_reason", "failed_checks"):
            entry[key] = fragment.get(key)
        if "engine_error_message" in fragment:
            entry["engine_error_message"] = fragment["engine_error_message"]
        regression = fragment.get("checks", {}).get("regression") if promoted else None
        entry["regression"] = {
            **(regression or {}),
            "status": "reported",
            "note": "report-only pair (R32)",
        }
        return entry
    if promoted:
        entry["regression"] = fragment.get("checks", {}).get("regression") or {"status": "missing"}
    else:
        entry["regression"] = {
            "status": "pending_promotion",
            "note": "the v0.5.0 candidates are not yet TJ's fixtures (Phase 3)",
        }
    if recipe == "xtb":
        entry["identity_core"] = identity_core(gates)
    return entry


def cross_check_block(fragment: dict[str, Any]) -> dict[str, Any]:
    """The cross-check (slice 11, R5): reported only; the gate is every run attempted+recorded."""
    if fragment.get("test_outcome") == "missing":
        return {"status": "missing"}
    records = fragment.get("records", {})
    expected = {f"{c}.{r}" for c in CASES for r in RECIPES}
    complete = set(records) == expected and all(
        "status" in v and "exit_code" in v for v in records.values()
    )
    keep = (
        "status",
        "exit_code",
        "wall_time_s",
        "converged_bool",
        "eta_failed_reason",
        "delta_e_geometric_minus_eta_kcal_mol",
        "heavy_atom_rmsd_angstrom",
        "validation_at_geometric_ts",
    )
    return {
        "status": "pass" if complete else "fail",
        "gate": "every case x recipe attempted and recorded (R5); the values are reported only",
        "geometric_version": fragment.get("geometric_version"),
        "hessian_units_assumption": fragment.get("hessian_units_assumption"),
        "licence_note": fragment.get("licence_note"),
        "records": {k: {f: v[f] for f in keep if f in v} for k, v in sorted(records.items())},
    }


def transcriptions_block(xyz_dir: Path = XYZ_DIR) -> dict[str, Any]:
    """HF-1 sha256s recomputed from the committed files; R9 transcribed from slice 07's proof."""
    files = {}
    for name, expected in sorted(HF1_SHA256.items()):
        path = xyz_dir / name
        observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        files[name] = {"expected": expected, "observed": observed}
    sha_ok = all(f["expected"] == f["observed"] for f in files.values())
    rows = {
        name: {"E_pyscf_hartree": e, "delta_vs_literature_hartree": d}
        for name, (e, d) in sorted(R9_PROOF.items())
    }
    r9_ok = all(abs(d) <= R9_BOUND_HARTREE for _, d in R9_PROOF.values())
    return {
        "sha256": {"status": "pass" if sha_ok else "fail", "files": files},
        "r9": {
            "status": "pass" if r9_ok else "fail",
            "bound_hartree": R9_BOUND_HARTREE,
            "source": R9_SOURCE,
            "transcribed": True,
            "rows": rows,
        },
    }


def git_blob_id(data: bytes) -> str:
    """Git's blob id of ``data`` (what ``git hash-object`` and ``git ls-tree`` print)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def promotion_evidence(promoted_dir: Path = PROMOTED_V050) -> dict[str, Any]:
    """TJ's promotion (R33): each promoted file's sha256 and blob id against R33's list.

    ``absent`` when no promoted file exists (pre-promotion); ``verified`` when all eleven equal
    R33; anything else raises, since a fixture that is not TJ's must never feed a verdict.
    """
    present = sorted(p.name for p in promoted_dir.glob("*.json")) if promoted_dir.is_dir() else []
    if not present:
        return {"status": "absent", "directory": "tests/fixtures/v0.5.0/"}
    files = {}
    for name, (sha, blob) in sorted(PROMOTED_FILES.items()):
        path = promoted_dir / name
        data = path.read_bytes() if path.is_file() else b""
        observed = (hashlib.sha256(data).hexdigest(), git_blob_id(data)) if data else (None, None)
        if observed != (sha, blob):
            raise ValueError(f"promoted {name} is not R33's: {observed} != {(sha, blob)}")
        files[name] = {"sha256": sha, "blob_id": blob}
    if present != sorted(PROMOTED_FILES):
        raise ValueError(f"promoted files {present} are not R33's {sorted(PROMOTED_FILES)}")
    return {
        "status": "verified",
        **PROMOTION,
        "directory": "tests/fixtures/v0.5.0/",
        "files": files,
    }


# --- reproducibility --------------------------------------------------------------------------


def heavy_rmsd_angstrom(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Heavy-atom RMSD (Angstrom) after Horn superposition, identity map (same atom order)."""
    from eta_rxncat.mapping import superpose

    if a["symbols"] != b["symbols"]:
        raise ValueError("the runs' TS geometries have different atom orders")
    heavy = [k for k, s in enumerate(a["symbols"]) if s != "H"]
    pa = np.asarray(a["coordinates"], dtype=float)[heavy]
    pb = np.asarray(b["coordinates"], dtype=float)[heavy]
    return float(superpose(pa, pb).rmsd_angstrom)


def _run_values(case_fragment: dict[str, Any]) -> dict[str, Any] | None:
    """The acceptance run's TS energy, ΔG‡ and TS geometry, or None without a converged TS."""
    ts = case_fragment.get("ts") or {}
    barrier = case_fragment.get("barrier")
    if ts.get("failed_reason") is not None or not ts.get("thermo") or barrier is None:
        return None
    return {
        "ts_energy_hartree": ts["thermo"]["electronic_energy_hartree"],
        "dG_dagger_1M_kcal_mol": barrier["dG_dagger_1M_kcal_mol"],
        "ts_state": ts["state"],
    }


def reproducibility_entry(
    case: str, recipe: str, case_fragment: dict[str, Any], repro_fragment: dict[str, Any]
) -> dict[str, Any]:
    """Max |ΔE_TS|, |ΔΔG‡| and heavy RMSD over every pair of the three fresh-store runs."""
    if (recipe, case) in REPORT_ONLY:
        return {
            "status": "n/a",
            "reason": "GFN2 TS4a is report-only (R32): no converged TS of this reaction to "
            "reproduce, so it was not rerun",
        }
    acceptance = _run_values(case_fragment)
    if acceptance is None or repro_fragment.get("test_outcome") == "missing":
        return {"status": "missing", "reason": "a run has no converged TS or no fragment"}
    runs = [acceptance, *repro_fragment["runs"]]
    labels = ["acceptance_run", *[f"fresh_store_{k + 1}" for k in range(len(runs) - 1)]]
    pairs = [(i, j) for i in range(len(runs)) for j in range(i + 1, len(runs))]
    de = [abs(runs[i]["ts_energy_hartree"] - runs[j]["ts_energy_hartree"]) for i, j in pairs]
    dg = [
        abs(runs[i]["dG_dagger_1M_kcal_mol"] - runs[j]["dG_dagger_1M_kcal_mol"]) for i, j in pairs
    ]
    rmsd = [heavy_rmsd_angstrom(runs[i]["ts_state"], runs[j]["ts_state"]) for i, j in pairs]
    return {
        "status": "measured",
        "n_runs": len(runs),
        "runs": {
            label: {
                "ts_energy_hartree": r["ts_energy_hartree"],
                "dG_dagger_1M_kcal_mol": r["dG_dagger_1M_kcal_mol"],
            }
            for label, r in zip(labels, runs, strict=True)
        },
        "max_abs_delta_ts_energy_hartree": max(de),
        "max_abs_delta_dG_dagger_1M_kcal_mol": max(dg),
        "max_heavy_rmsd_angstrom": max(rmsd),
    }


MEASURED_KEYS = {
    "abs_delta_ts_energy_hartree": "max_abs_delta_ts_energy_hartree",
    "heavy_rmsd_angstrom": "max_heavy_rmsd_angstrom",
    "abs_delta_dG_dagger_1M_kcal_mol": "max_abs_delta_dG_dagger_1M_kcal_mol",
}


def proposed_bounds(reproducibility: dict[str, Any]) -> dict[str, Any]:
    """Per recipe and quantity: TJ's bound if every measurement is <= 1/10 of it, else 10x max."""
    out: dict[str, Any] = {"rule": BOUND_RULE, "decided_by": "TJ at Phase 3", "recipes": {}}
    for recipe in RECIPES:
        entries = {c: e for c, e in reproducibility.get(recipe, {}).items()}
        measured = {c: e for c, e in entries.items() if e.get("status") == "measured"}
        missing = sorted(c for c, e in entries.items() if e.get("status") == "missing")
        block: dict[str, Any] = {
            "cases_measured": sorted(measured),
            "cases_not_measured": {
                c: e.get("reason") for c, e in sorted(entries.items()) if c not in measured
            },
        }
        for quantity, bound in TJ_BOUNDS.items():
            values = [e[MEASURED_KEYS[quantity]] for e in measured.values()]
            if missing or not values:
                block[quantity] = {"status": "missing", "tj_bound": bound}
                continue
            worst = max(values)
            worst_case = max(measured, key=lambda c: measured[c][MEASURED_KEYS[quantity]])
            if worst <= bound / 10:
                proposed, basis = bound, "tj_bound"
                statement = f"measured max {worst:.3g} <= 1/10 of TJ's {bound:g}: TJ's bound"
            else:
                proposed, basis = 10 * worst, "ten_times_measured_max"
                statement = (
                    f"measured max {worst:.3g} ({worst_case}) exceeds 1/10 of TJ's {bound:g}: "
                    f"proposing 10x the measured maximum, {proposed:.3g}, for TJ to decide"
                )
            block[quantity] = {
                "tj_bound": bound,
                "measured_max": worst,
                "measured_max_case": worst_case,
                "proposed": proposed,
                "basis": basis,
                "statement": statement,
            }
        out["recipes"][recipe] = block
    return out


# --- command and suite blocks ---------------------------------------------------------------

MAX_RSS = re.compile(r"Maximum resident set size \(kbytes\): (\d+)")


def command_entry(
    log: Path, exit_code: int, wall_s: float, env: dict[str, str], argv: list[str]
) -> dict[str, Any]:
    """One command from its log: the pytest summary line and /usr/bin/time's max RSS."""
    text = log.read_text(encoding="utf-8", errors="replace")
    summary = [ln for ln in text.splitlines() if re.match(r"^=+ .* in [\d.]+s", ln)]
    rss = MAX_RSS.search(text)
    return {
        "argv": argv,
        "env": env,
        "exit_code": exit_code,
        "wall_s": wall_s,
        "log": log.name,
        "summary": summary[-1].strip("= ") if summary else "",
        "max_rss_kbytes": int(rss.group(1)) if rss else None,
    }


def suite_block(suite_log: Path) -> dict[str, Any]:
    """The ``default_suite`` block from the pytest log (first line ``exit_code=<n>``)."""
    text = suite_log.read_text(encoding="utf-8")
    exit_code = int(re.search(r"exit_code=(\d+)", text).group(1))  # type: ignore[union-attr]
    return {"command": "uv run pytest", "exit_code": exit_code, **pytest_counts(text)}


# --- merge ----------------------------------------------------------------------------------


def merge_runs(
    runs: dict[str, dict[str, Any]],
    commands: list[dict[str, Any]],
    default_suite: dict[str, Any],
    xyz_dir: Path = XYZ_DIR,
    prior: dict[str, Any] | None = None,
    promoted_dir: Path = PROMOTED_V050,
) -> dict[str, Any]:
    """Build the record from the two per-recipe files.

    Without TJ's promoted fixtures: the pre-promotion record, no ``verdict`` (slice 12). With them
    (verified against R33): regression from the in-process comparisons, the transcriptions
    ``confirmed`` from TJ's recorded answer, TJ's bounds and the ``verdict`` (slice 13).
    ``prior`` is the slice 12 record, whose reproducibility measurement is carried over.
    """
    shas = {r["commit_sha"] for r in runs.values()}
    if len(shas) != 1 or not all(r["tree_clean"] for r in runs.values()):
        raise ValueError(f"recipes ran at different or unclean commits: {shas}")
    promotion = promotion_evidence(promoted_dir)
    promoted = promotion["status"] == "verified"
    t3 = {
        case: {
            recipe: case_entry(
                runs[recipe]["cases"].get(case, {"test_outcome": "missing"}), case, recipe, promoted
            )
            for recipe in RECIPES
        }
        for case in CASES
    }
    if prior is not None:
        reproducibility = prior["reproducibility"]
        proposed = prior["proposed_regression_bounds"]
    else:
        reproducibility = _reproducibility(runs)
        proposed = proposed_bounds(reproducibility)
    if promoted:
        confirmation = {
            "status": "confirmed",
            "source": PROMOTION["source"],
            "answer": PROMOTION["transcriptions_confirmed"],
        }
    else:
        confirmation = {
            "status": "pending_confirmation",
            "note": "TJ confirms the six transcriptions at Phase 3 (TJ A3)",
        }
    fixtures = {
        "t3": t3,
        "cross_check": cross_check_block(
            runs["uma"].get("cross_check", {"test_outcome": "missing"})
        ),
        "transcriptions": transcriptions_block(xyz_dir),
        "transcription_confirmation": confirmation,
    }
    evidence: dict[str, Any] = {
        "candidates_phase3_set": (
            "tests/candidate_outputs/v0.5.0/ (slices 08-11), committed for TJ's Phase 3 "
            "review; never read by this record"
        ),
        "record_run_candidates": "written to a scratch ETA_RXNCAT_CANDIDATE_DIR, not committed",
        "candidate_values": (
            "the acceptance run reruns slice 08-10 code in-process at this commit; its values "
            "stand for the candidates' (no candidate file is read, slice 12 firewall)"
        ),
        "promotion": promotion,
    }
    if prior is not None:
        evidence["reproducibility_source"] = (
            f"slice 12 record at {prior['commit_sha']}: three fresh-store runs per case x recipe; "
            "carried over, not rerun for the verdict"
        )
    record: dict[str, Any] = {
        "record_schema": 1,
        "commit_sha": shas.pop(),
        "run_at_utc": max(r["run_at_utc"] for r in runs.values()),
        "hardware": runs["uma"]["hardware"],
        "engines": {recipe: run["engine"] for recipe, run in sorted(runs.items())},
        "devices": {recipe: run["device"] for recipe, run in sorted(runs.items())},
        "environment": {recipe: {"python": run["python"]} for recipe, run in sorted(runs.items())},
        "commands": [{k: v for k, v in c.items() if k != "log"} for c in commands],
        "logs": {
            c["log"]: {"exit_code": c["exit_code"], "summary": c["summary"]} for c in commands
        },
        "default_suite": default_suite,
        "known_limits": list(KNOWN_LIMITS),
        "reported_notes": dict(REPORTED_NOTES),
        "evidence": evidence,
        "fixtures": fixtures,
        "reproducibility": reproducibility,
        "proposed_regression_bounds": proposed,
    }
    if promoted:
        record["regression_bounds"] = {
            "source": "mission R33 (TJ at Phase 3)",
            "recipes": {r: dict(b) for r, b in sorted(REGRESSION_BOUNDS.items())},
            "report_only": "GFN2 TS4a: compared and recorded, never gated (R32)",
            "excluded": "search_history (N11)",
        }
        record.update(record_verdict(fixtures, default_suite, record["commands"]))
    problems = check(record)
    if problems:
        raise ValueError(f"record invalid: {problems}")
    return record


def _reproducibility(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        recipe: {
            case: reproducibility_entry(
                case,
                recipe,
                runs[recipe]["cases"].get(case, {"test_outcome": "missing"}),
                runs[recipe]["reproducibility"].get(case, {"test_outcome": "missing"}),
            )
            for case in CASES
        }
        for recipe in RECIPES
    }


def _dump(path: Path, data: Any) -> None:
    text = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    """``suite``, ``add-command`` or ``merge`` (see the module docstring)."""
    if len(argv) == 3 and argv[0] == "suite":
        _dump(Path(argv[2]), suite_block(Path(argv[1])))
        print(f"wrote {argv[2]}")
        return 0
    if len(argv) >= 8 and argv[0] == "add-command" and argv[6] == "--":
        path = Path(argv[1])
        commands = _load(argv[1]) if path.exists() else []
        commands.append(
            command_entry(Path(argv[2]), int(argv[3]), float(argv[4]), _load(argv[5]), argv[7:])
        )
        _dump(path, commands)
        print(f"{path}: {len(commands)} commands; last {commands[-1]['summary']!r}")
        return 0
    if len(argv) in (6, 7) and argv[0] == "merge":
        runs = {"xtb": _load(argv[1]), "uma": _load(argv[2])}
        prior = _load(argv[6]) if len(argv) == 7 else None
        record = merge_runs(runs, _load(argv[3]), _load(argv[4]), prior=prior)
        _dump(Path(argv[5]), record)
        rule = record_verdict(record["fixtures"], record["default_suite"], record["commands"])
        stated = record.get("verdict", "none (pre-promotion)")
        print(f"wrote {argv[5]}; verdict {stated}; rule {rule}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
