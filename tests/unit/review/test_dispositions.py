"""Dispositions and TS identity: the exporter, old inputs and the static summary (slice 16; R35)."""

import json
from pathlib import Path
from typing import Any

import pytest
from review_helpers import H2, key_of, put, stretch_hessian, stub_keys, stub_record
from test_bundle import page_of

from eta_rxncat.core import MolecularState, TSSearchResult
from eta_rxncat.review import (
    RunData,
    RunRecord,
    canonical_run_data_json,
    export_run_data,
    read_run_data,
    write_review_bundle,
)
from eta_rxncat.review.export import ExportError
from eta_rxncat.review.run_data import Candidate
from eta_rxncat.store import ArtifactStatus, ArtifactStore, geometry_payload

TEMPLATE = "t2__r=ethyl"


def ts_search(state: MolecularState = H2) -> dict[str, Any]:
    """A converged ``ts_opt`` row on ``state`` whose forming bond is 0-1."""
    return TSSearchResult.model_validate(
        {
            "final_state": state.model_dump(),
            "final_energy_hartree": -1.1,
            "converged": True,
            "n_steps": 1,
            "n_gradient_calls": 1,
            "n_hessian_calls": 1,
            "n_hessian_refreshes": 0,
            "n_rejected_steps": 0,
            "hessian_method": "analytic",
            "followed_eigenvalue_hartree_per_bohr2": -0.3,
            "final_max_gradient_hartree_per_bohr": 0.0,
            "final_rms_gradient_hartree_per_bohr": 0.0,
            "final_rigid_gradient_norm_hartree_per_bohr": 0.0,
            "forming_bonds": [{"i": 0, "j": 1}],
            "optimizer": {"name": "prfo", "version": "1"},
            "options": {},
            "history": [],
        }
    ).model_dump(mode="json")


def key_hex(name: str) -> str:
    """The stub store's key of one row."""
    return stub_keys()[name].key


def store_with(tmp_path: Path, extra: dict[str, dict[str, Any]] | None = None) -> Path:
    """The stub store with a converged ``ts_opt`` row and the given extra frequency rows."""
    path = tmp_path / "stub.sqlite"
    put(path, {"ts": ("ts", ts_search())})
    with ArtifactStore(path) as store:
        for tag, payload in (extra or {}).items():
            store.put(extra_key(tag), ArtifactStatus.COMPLETED, payload)
    return path


def extra_key(tag: str) -> Any:
    """The key of an extra frequency row."""
    return key_of(H2, "frequency", tag)


def minimum_row(constant: float) -> dict[str, Any]:
    """A frequency row; a negative ``constant`` gives one imaginary mode."""
    return {
        "energy_hartree": -1.1,
        "hessian_hartree_per_bohr2": stretch_hessian(constant),
        "hessian_method": "analytic",
        "geometry": geometry_payload(H2),
    }


def full_record(**changes: Any) -> RunRecord:
    """The stub record with one sample of every kind and one endpoint row of every kind."""
    data = stub_record().model_dump(mode="json")
    (run,) = data["runs"]
    keys = {name: key.key for name, key in stub_keys().items()}

    def sample(index: int, template: str = TEMPLATE, **extra: Any) -> dict[str, Any]:
        source = "seed" if index == 0 else f"perturb:{index}"
        return {
            "template_id": template,
            "sample_index": index,
            "source": source,
            "species_id": "ts",
            **extra,
        }

    rows = {"ts_opt_key": keys["ts"], "frequency_key": keys["freq"]}
    run["samples"] = [
        sample(0, **rows),
        sample(1, **rows),
        sample(2, **rows),
        sample(3),
        sample(4),
        sample(5),
        sample(0, "t1__r=ethyl"),
    ]
    run["fallback"]["attempts"].insert(
        0,
        {
            "template_id": "t1__r=ethyl",
            "rank": 1,
            "outcome": "fell_through",
            "reason": "seed:face_mismatch_pathway",
            "wall_time_s": 1.0,
        },
    )
    run["ensemble"]["excluded"] = [
        {
            "index": 2,
            "source": "perturb:2",
            "reason": "gate_failed:forming_overlap",
        },
        {
            "index": 3,
            "source": "perturb:3",
            "reason": "seed_clash",
            "detail": {
                "check": "clash",
                "pair": [0, 1],
                "distance_angstrom": 0.438,
                "ratio_to_covalent_sum": 0.7,
            },
        },
        {
            "index": 4,
            "source": "perturb:4",
            "reason": "bond_changed:ts",
            "detail": {"check": "bond_changed", "bonds_formed": [[0, 1]], "bonds_broken": []},
        },
    ]
    run["ensemble"]["merges"] = [
        {"kept_index": 0, "merged_index": 1, "dG_kcal_mol": 0.0, "rmsd_angstrom": 0.0}
    ]
    first, pushed, dropped = (extra_key(t).key for t in ("first", "pushed", "dropped"))
    run["endpoints"] = [
        {
            "species_id": "reactant",
            "opt_keys": [keys["end"]],
            "frequency_keys": [first, pushed, dropped],
            "frequency_dispositions": [
                {
                    "frequency_key": first,
                    "kind": "superseded_by_push",
                    "superseded_by_key": pushed,
                },
                {"frequency_key": pushed, "kind": "kept"},
                {"frequency_key": dropped, "kind": "dropped", "reason": "duplicate_after_push"},
            ],
        }
    ]
    run.update(changes)
    return RunRecord.model_validate(data)


ROWS = {"first": minimum_row(-0.3), "pushed": minimum_row(0.3), "dropped": minimum_row(0.4)}


def export(tmp_path: Path, record: RunRecord) -> RunData:
    """Export ``record`` from the store with the extra rows."""
    with ArtifactStore(store_with(tmp_path, ROWS)) as store:
        return export_run_data(record, store)


def unit(tmp_path: Path, record: RunRecord | None = None) -> Candidate:
    """The one candidate unit of an export."""
    (candidate,) = export(tmp_path, record or full_record()).candidates
    return candidate


def test_every_sample_has_its_disposition(tmp_path: Path) -> None:
    """Member, merged, excluded (with both seed findings), fell through and unjudged."""
    found = {(d.template_id, d.sample_index): d for d in unit(tmp_path).sample_dispositions}
    assert len(found) == 7
    member = found[TEMPLATE, 0]
    assert (member.kind, member.weight_fraction, member.reason_code) == ("member", 1.0, None)
    merged = found[TEMPLATE, 1]
    assert (merged.kind, merged.merged_into_index) == ("merged", 0)
    gate = found[TEMPLATE, 2]
    assert (gate.kind, gate.reason_code) == ("excluded", "gate_failed:forming_overlap")
    clash = found[TEMPLATE, 3]
    assert clash.clash is not None and clash.frequency_id is None and clash.identity is None
    assert (clash.clash.i, clash.clash.j, clash.clash.distance_angstrom) == (0, 1, 0.438)
    bonds = found[TEMPLATE, 4]
    assert bonds.reason_code == "bond_changed:ts" and bonds.bonds_formed == [(0, 1)]
    unjudged = found[TEMPLATE, 5]
    assert (unjudged.kind, unjudged.reason_code) == ("excluded", "not_recorded")
    fell = found["t1__r=ethyl", 0]
    assert (fell.kind, fell.reason_code) == ("fell_through", "seed:face_mismatch_pathway")


def test_identity_is_recomputed_from_the_stored_hessian(tmp_path: Path) -> None:
    """H2's one negative mode is the bond stretch; 1.2 A is below the default window."""
    (member, *_) = unit(tmp_path).sample_dispositions
    identity = member.identity
    assert identity is not None
    assert identity.n_imaginary == 1 and identity.imaginary_frequency_cm1 is not None
    assert identity.forming_overlap == pytest.approx(1.0)
    assert identity.active_core_ke_fraction == pytest.approx(1.0)
    assert [(d.i, d.j) for d in identity.forming_distances] == [(0, 1)]
    assert identity.forming_distances[0].distance_angstrom == pytest.approx(1.2000012345)
    assert identity.in_phase_bool is True and identity.passed_bool is False
    assert identity.reason_codes == ["forming_distance_out_of_window"]


def test_identity_uses_the_runs_validation_options(tmp_path: Path) -> None:
    """A wider window passes the same Hessian."""
    window = {"forming_distance_min_angstrom": 1.0, "forming_distance_max_angstrom": 1.5}
    (member, *_) = unit(tmp_path, full_record(validation=window)).sample_dispositions
    assert member.identity is not None and member.identity.passed_bool is True


def test_no_identity_without_a_converged_search(tmp_path: Path) -> None:
    """A failed ``ts_opt`` row gives no identity numbers."""
    path = tmp_path / "failed.sqlite"
    put(path, {})  # the default ts_opt row is a failure
    with ArtifactStore(path) as store:
        data = export_run_data(stub_record(), store)
    assert [d.identity for d in data.candidates[0].sample_dispositions] == [None, None]


def test_endpoint_dispositions(tmp_path: Path) -> None:
    """Kept, superseded and dropped rows reach the document."""
    candidate = unit(tmp_path)
    ids = candidate.endpoint_frequency_ids
    found = candidate.endpoint_dispositions
    assert [d.frequency_id for d in found] == ids
    assert [d.kind for d in found] == ["superseded_by_push", "kept", "dropped"]
    assert found[0].superseded_by_frequency_id == ids[1]
    assert found[2].reason_code == "duplicate_after_push"


def test_an_endpoint_without_dispositions_reads_not_recorded(tmp_path: Path) -> None:
    """An old record loads, serialises without the new keys and exports ``not_recorded``."""
    record = full_record()
    data = record.model_dump(mode="json")
    del data["runs"][0]["endpoints"][0]["frequency_dispositions"]
    old = RunRecord.model_validate(data)
    text = old.model_dump_json()
    assert "frequency_dispositions" not in text and '"validation":null' not in text
    assert RunRecord.model_validate_json(text) == old
    assert "validation" not in old.model_dump()["runs"][0]
    candidate = unit(tmp_path, old)
    assert {d.kind for d in candidate.endpoint_dispositions} == {"not_recorded"}


def test_a_disposition_naming_an_unlisted_row_is_refused(tmp_path: Path) -> None:
    """A disposition must name a listed row."""
    data = full_record().model_dump(mode="json")
    data["runs"][0]["endpoints"][0]["frequency_keys"].pop()
    with pytest.raises(ExportError, match="lists no frequency row"):
        unit(tmp_path, RunRecord.model_validate(data))


def test_a_document_without_the_new_keys_still_loads(tmp_path: Path) -> None:
    """Built with the pre-slice field set: no disposition list on any candidate."""
    document = json.loads(canonical_run_data_json(export(tmp_path, full_record())))
    for candidate in document["candidates"]:
        del candidate["sample_dispositions"], candidate["endpoint_dispositions"]
    loaded = read_run_data(json.dumps(document).encode())
    assert loaded.candidates[0].sample_dispositions == []
    assert json.loads(canonical_run_data_json(loaded)) == document
    html = (write_review_bundle(loaded, tmp_path / "old") / "index.html").read_text()
    assert "disposition not recorded" in html


def summary(tmp_path: Path, run_data: RunData) -> tuple[str, list[str]]:
    """The page text and, split at the not-used heading, its two groups."""
    page = page_of(write_review_bundle(run_data, tmp_path / "bundle"))
    text = "".join(page.text)
    used, notused = text.split("Not used (rejected, merged or superseded)")
    return text, [used.split("Used in the result", 1)[1], notused]


def test_the_summary_groups_used_rows_apart_and_names_each(tmp_path: Path) -> None:
    """Used rows come first; every other row is below, named."""
    _, (used, notused) = summary(tmp_path, export(tmp_path, full_record()))
    assert "member (weight 1.000)" in used and "— kept" in used
    for label in (
        "merged into sample 0",
        "excluded: gate_failed:forming_overlap",
        "excluded: seed_clash H0–H1 0.438 Å",
        "excluded: bond_changed:ts (formed H0–H1)",
        "excluded: not_recorded",
        "fell through: seed:face_mismatch_pathway",
        "superseded by push → frequency:reactant:",
        "dropped: duplicate_after_push",
    ):
        assert label in notused, label
        assert label not in used, label
    assert "Sample 3 (perturb:3, template t2__r=ethyl): excluded: seed_clash" in notused


def test_every_ts_block_shows_identity_and_banners_its_failure(tmp_path: Path) -> None:
    """Three TS blocks with one imaginary mode: the failed identity banners each of them."""
    data = export(tmp_path, full_record())
    page = page_of(write_review_bundle(data, tmp_path / "bundle"))
    text = "".join(page.text)
    assert text.count("Identity: imaginary frequency") == 3
    for part in (
        "forming-bond overlap 1.000",
        "active-core KE fraction 1.000",
        "forming distances H0–H1 1.200 Å",
        "in phase yes",
        "FAIL (forming_distance_out_of_window)",
    ):
        assert part in text
    identity = "Transition state identity check failed: forming_distance_out_of_window."
    assert text.count(identity) == 3
    # the superseded minimum keeps its count banner beside its label
    assert "Minimum has 1 imaginary mode(s); expected 0." in text
    assert len(page.banners()) == 4


def test_a_passing_identity_raises_no_banner(tmp_path: Path) -> None:
    """A passing TS raises no banner."""
    window = {"forming_distance_min_angstrom": 1.0, "forming_distance_max_angstrom": 1.5}
    record = full_record(validation=window, endpoints=[])
    page = page_of(write_review_bundle(export(tmp_path, record), tmp_path / "bundle"))
    assert not page.banners()
    assert "; pass" in "".join(page.text)
