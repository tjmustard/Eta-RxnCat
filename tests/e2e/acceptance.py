"""Acceptance fragments: per fixture/recipe metrics and verdicts for the record (slice 09).

When ``ETA_RXNCAT_ACCEPTANCE_OUT`` is set, each E2E fixture test writes one fragment under
``$ETA_RXNCAT_ACCEPTANCE_OUT/fragments/``; ``test_accept_v030.py`` aggregates a recipe's fragments
and ``acceptance_record.py`` merges both recipes into ``docs/prd/v0.3.0/ACCEPTANCE_RESULT.json``.
Verdicts that need TJ (promoted fixtures, reference values, SMILES confirmation) stay
``pending_*`` here (R22).
"""

import os
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from eta_rxncat.orchestrator import SpeciesResult, write_report

OUT_ENV = "ETA_RXNCAT_ACCEPTANCE_OUT"
GATING_LEVEL = "wb97mv_def2tzvpd//b3lyp_631gss"
STAGES = ("conformer_search", "geometry_opt", "frequency", "single_point")


def out_dir() -> Path | None:
    """The acceptance output directory, or ``None`` when not recording."""
    value = os.environ.get(OUT_ENV)
    return Path(value) if value else None


def stage_metrics(results: Iterable[Any]) -> dict[str, Any]:
    """Per-stage wall time, engine calls and cache hits summed over runs, plus totals.

    Each item has ``.metrics`` (a ``RunMetrics``): species results and constrained points.
    """
    stages = {k: {"wall_time_s": 0.0, "engine_calls": 0, "cache_hits": 0} for k in STAGES}
    steps = 0
    recovery: Counter[str] = Counter()
    for r in results:
        for kind in STAGES:
            m = r.metrics.stages[kind]
            stages[kind]["wall_time_s"] += m.wall_time_s
            stages[kind]["engine_calls"] += m.engine_calls
            stages[kind]["cache_hits"] += m.cache_hits
        steps += r.metrics.optimizer_steps_total
        recovery.update(r.metrics.recovery_steps)
    return {
        "stages": stages,
        "optimizer_steps_total": steps,
        "recovery_steps": dict(sorted(recovery.items())),
    }


def failures_by_species(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    """R50 failure rows as {species: {stage: {reason: count}}}."""
    out: dict[str, dict[str, dict[str, int]]] = {}
    for row in rows:
        out.setdefault(row["species"], {}).setdefault(row["stage"], {})[row["reason"]] = row[
            "count"
        ]
    return out


def tj_reference() -> dict[str, Any]:
    """TJ's reference values transcribed in memory from the committed results.json (R46)."""
    import reference_values as rv

    return rv.load_reference_values(
        rv.transcribe_tj_results(rv.TJ_SOURCE / "results.json"), fixtures_mode=True
    )


def accuracy_block(
    checks: Mapping[str, Any],
    observed: Mapping[str, float] | None,
    sigmas: Mapping[str, int],
    recipe: str,
) -> dict[str, Any]:
    """The record's accuracy block (R46-R48).

    ``verdict`` is the check's own status (``pending_reference`` until TJ promotes, ``reported``
    for fixtures without reference entries). ``deltas`` compare like for like with TJ's values
    (both levels), read from the committed source in memory; ``status_against_tj_values`` says
    what the verdict would be against them, for information only.
    """
    from derived import accuracy

    block: dict[str, Any] = {"verdict": checks["accuracy"]["status"], "gating_level": GATING_LEVEL}
    if observed is None:
        block["deltas"] = []
        return block
    preview = accuracy(observed, sigmas, tj_reference(), recipe=recipe)
    block["deltas"] = preview["deltas"]
    block["status_against_tj_values"] = preview["status"]
    if "sigma_mismatch" in preview:
        block["sigma_mismatch"] = preview["sigma_mismatch"]
    return block


def write_fragment(fixture: str, recipe: str, data: Mapping[str, Any]) -> None:
    """Write one fixture/recipe fragment (no-op unless recording)."""
    out = out_dir()
    if out is None:
        return
    (out / "fragments").mkdir(parents=True, exist_ok=True)
    write_report(
        out / "fragments" / f"{fixture}.{recipe}.json",
        {"fixture": fixture, "recipe": recipe, **data},
    )


def species_stage_cache(reruns: Iterable[SpeciesResult]) -> dict[str, dict[str, int]]:
    """R27: per stage, species served wholly from cache (hit) versus not (miss), over a rerun."""
    out: dict[str, dict[str, int]] = {}
    runs = list(reruns)
    for kind in ("geometry_opt", "frequency", "single_point"):
        hits = 0
        for r in runs:
            m = r.metrics.stages[kind]
            hits += int(m.rows_created == 0 and m.cache_hits == len(r.keys[kind]) > 0)
        out[kind] = {"hits": hits, "misses": len(runs) - hits}
    return out


def species_counts(species: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """n_pool and n_kept per species, from the candidate's species entries (in memory)."""
    return {k: {"n_pool": v["n_pool"], "n_kept": v["n_kept"]} for k, v in species.items()}


def smiles_confirmation() -> str:
    """T1/T2 SMILES: ``pending_confirmation`` until TJ promotes e2e5_smiles.json (R22)."""
    import json

    from e2e_env import PROMOTED
    from fixtures import t1, t2
    from rdkit import Chem

    path = PROMOTED / "e2e5_smiles.json"
    if not path.exists():
        return "pending_confirmation"

    def canonical(s: str) -> str:
        return str(Chem.MolToSmiles(Chem.MolFromSmiles(s)))

    confirmed = json.loads(path.read_text(encoding="utf-8"))["species"]
    inputs = {s.species_id: s.smiles for f in (t1(), t2()) for s in f.species}
    same = all(canonical(confirmed[k]["derived_smiles"]) == canonical(v) for k, v in inputs.items())
    return "confirmed" if same else "fail"
