"""v0.7.0 review bundle E2E (slice 13, G13): the four real stores into one gated bundle.

Needs ``ETA_RXNCAT_V070_EVIDENCE`` (the directory that holds ``v070-slice11`` and
``v070-slice12``). The bundle is built and gated in ``<evidence>/v070-slice13/review`` and then
copied to ``tests/candidate_outputs/v0.7.0/review/`` (``ETA_RXNCAT_CANDIDATE_DIR`` redirects the
parent). Both roots must be fresh. No engine runs and no store changes. The report is written
beside the scratch tree, never read from the candidate directory.
"""

import json
import os
from pathlib import Path

import pytest
from e2e_env import acceptance
from review_v070 import build_review
from v070 import candidate_dir

pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.acceptance]

EXPECTED_RUNS = {
    "v070_enum.sqlite": 8,
    "v070_fallback_graft_time_xtb.sqlite": 1,
    "v070_fallback_run_time_xtb.sqlite": 1,
    "v070_fallback_run_time_uma.sqlite": 1,
}
EXPECTED_SUB_BUNDLES = 7


def test_v070_review_bundle() -> None:
    """Build, gate and copy the bundle of every slice 11 and 12 run."""
    base = os.environ.get("ETA_RXNCAT_V070_EVIDENCE")
    if not base:
        pytest.skip("ETA_RXNCAT_V070_EVIDENCE is not set (the slice 11 and 12 evidence directory)")
    if acceptance():
        assert os.environ.get("TMPDIR", "/tmp") != "/tmp"
    evidence = Path(base).resolve()
    out = evidence / "v070-slice13"
    out.mkdir(parents=True, exist_ok=True)
    report = build_review(evidence, out / "review", candidate_dir() / "review")
    (out / "review_report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    assert report["engine_calls"] == 0
    runs = {name: s["coverage"]["runs"] for name, s in report["stores"].items()}
    assert runs == EXPECTED_RUNS
    assert len(report["sub_bundles"]) == EXPECTED_SUB_BUNDLES
    print(
        f"\nreview bundle: {len(report['sub_bundles'])} sub-bundles, engine calls "
        f"{report['engine_calls']}, total bytes {report['gates']['total_bytes']}, root manifest "
        f"sha256 {report['gates']['root_manifest_sha256']}, copied {report['copied_files']} files"
    )
