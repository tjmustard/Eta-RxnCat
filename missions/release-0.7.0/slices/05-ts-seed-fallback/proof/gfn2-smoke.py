# ruff: noqa: E402 - the sys.path lines must precede the test-helper imports
"""Requirement 15 smoke: run_ts_with_fallback on the enumerated ethyl/TS1a_n candidate (GFN2).

Run from a scratch cwd: python gfn2-smoke.py <store.sqlite> <result.json>
"""

import json
import sys
import time

REPO = "/home/tjmustard/PROJECTS/eta-rxncat"
sys.path[:0] = [f"{REPO}/tests/e2e", f"{REPO}/tests/unit/mapping"]

from e2e_env import recipe_for
from t3 import ts_recipe
from t4 import member_gates
from test_enumerator_support import MAX_RMSD, plan

from eta_rxncat.core import PathwaySpec, TSEnsembleOptions
from eta_rxncat.mapping.enumerator import enumerate_candidates
from eta_rxncat.optimize import GeometricOptimizer
from eta_rxncat.orchestrator import run_ts_with_fallback
from eta_rxncat.store import ArtifactStore

(candidate,) = enumerate_candidates(plan(), max_alignment_rmsd_angstrom=MAX_RMSD).candidates
node = next(n for n in candidate.graph.nodes if n.id == "ts_endo")
recipe = ts_recipe(recipe_for("xtb"))
passes = []
for number in (1, 2):
    t0 = time.perf_counter()
    with ArtifactStore(sys.argv[1]) as store:
        record, run = run_ts_with_fallback(
            candidate,
            "ts_endo",
            PathwaySpec(pathway="endo", node_id="ts_endo", expected_face=(1, 1)),
            recipe,
            store,
            optimizer=GeometricOptimizer(),
            options=TSEnsembleOptions(),
            member_gates=member_gates("xtb"),
        )
    passes.append((record, run))
    ensemble = None if run is None else run.ensemble
    out = {
        "pass": number,
        "wall_s": time.perf_counter() - t0,
        "templates": [(t.id, t.rank) for t in node.templates],
        "record": record.model_dump(mode="json"),
        "reactant_key": None if ensemble is None else ensemble.reactant_key,
        "members": None
        if ensemble is None
        else [(m.index, m.face, m.G_hartree, m.weight) for m in ensemble.members],
        "excluded": None if ensemble is None else [(e.index, e.reason) for e in ensemble.excluded],
        "stall_cap_reached": None if run is None else run.stall_cap_reached_bool,
        "metrics": None
        if run is None
        else {
            k: {"engine_calls": m.engine_calls, "rows": m.rows_created, "hits": m.cache_hits}
            for k, m in run.metrics.items()
        },
    }
    print(json.dumps(out), flush=True)
    with open(sys.argv[2], "a") as handle:
        handle.write(json.dumps(out) + "\n")
(first, a), (second, b) = passes
assert first.chosen_template_id == node.templates[0].id and node.templates[0].rank == 1
assert a is not None and a.ensemble.members
assert second == first and b.ensemble == a.ensemble
assert all(m.engine_calls == 0 and m.rows_created == 0 for m in b.metrics.values())
print("SMOKE PASS")
