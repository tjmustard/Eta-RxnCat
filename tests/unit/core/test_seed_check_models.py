"""Tests for the seed check contracts (v0.7.0, slice 15): detail, reasons and old records."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from eta_rxncat.core import (
    FallbackAttempt,
    FallbackRecord,
    SeedCheckDetail,
    TSEnsemble,
    TSEnsembleExclusion,
)
from eta_rxncat.review.run_data import RunRecord

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
DETAIL = SeedCheckDetail(check="bond_changed", bonds_formed=[(0, 4)], bonds_broken=[])


def exclusion(reason: str, **extra: Any) -> dict[str, Any]:
    """A valid exclusion dict."""
    return {"index": 1, "source": "perturb:0", "reason": reason, **extra}


@pytest.mark.parametrize("reason", ["seed_clash", "bond_changed:pre_relax", "bond_changed:ts"])
def test_the_new_exclusion_reasons_are_accepted(reason: str) -> None:
    """The reason set gained three."""
    assert TSEnsembleExclusion.model_validate(exclusion(reason)).reason == reason


@pytest.mark.parametrize("reason", ["bond_changed", "bond_changed:frequency", "seed_clash:x"])
def test_other_spellings_are_refused(reason: str) -> None:
    """The set stays closed."""
    with pytest.raises(ValidationError, match="unknown exclusion reason"):
        TSEnsembleExclusion.model_validate(exclusion(reason))


def ensemble(**extra: Any) -> TSEnsemble:
    """A failed ensemble."""
    return TSEnsemble.model_validate(
        {
            "pathway": "endo",
            "temperature_k": 298.15,
            "reactant_key": [["C=C", 1]],
            "recipe_identity": {"name": "xtb_subprocess", "version": "6.8.0"},
            "failed_reason": "seed:bond_changed:ts",
            **extra,
        }
    )


def attempt(**extra: Any) -> FallbackAttempt:
    """A fallen-through attempt."""
    return FallbackAttempt.model_validate(
        {"template_id": "t", "rank": 1, "outcome": "fell_through", "wall_time_s": 0.0, **extra}
    )


def test_an_absent_detail_is_not_serialised() -> None:
    """``None`` details are left out, in both dump modes."""
    models = [
        (TSEnsembleExclusion.model_validate(exclusion("seed_clash")), "detail"),
        (ensemble(), "failed_detail"),
        (attempt(), "detail"),
    ]
    for model, key in models:
        assert key not in model.model_dump()
        assert key not in json.loads(model.model_dump_json())


def test_a_present_detail_round_trips() -> None:
    """A set detail is serialised and reads back equal, nested too."""
    models = [
        TSEnsembleExclusion.model_validate(exclusion("bond_changed:ts", detail=DETAIL)),
        ensemble(failed_detail=DETAIL),
        attempt(detail=DETAIL),
    ]
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model
    record = FallbackRecord(node_id="ts", attempts=[models[2]], stop_reason="x")
    assert record.model_dump(mode="json")["attempts"][0]["detail"]["bonds_formed"] == [[0, 4]]


def walk(value: Any) -> Iterator[dict[str, Any]]:
    """Every dict in a JSON document."""
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


KINDS: dict[type[Any], set[str]] = {
    TSEnsemble: {"pathway", "recipe_identity", "excluded"},
    TSEnsembleExclusion: {"index", "source", "reason", "pre_relax_wall_time_s"},
    FallbackRecord: {"node_id", "attempts", "stop_reason"},
}


def reserialised(value: Any, seen: dict[type[Any], int]) -> Any:
    """``value`` with every ensemble, exclusion and fallback record loaded and dumped again."""
    if isinstance(value, list):
        return [reserialised(item, seen) for item in value]
    if not isinstance(value, dict):
        return value
    for model, keys in KINDS.items():
        if keys <= value.keys():
            for nested in walk(value):
                for inner, inner_keys in KINDS.items():
                    seen[inner] += inner_keys <= nested.keys()
            return model.model_validate(value).model_dump(mode="json")
    return {key: reserialised(item, seen) for key, item in value.items()}


@pytest.mark.parametrize("version", ["v0.6.0", "v0.7.0"])
def test_old_records_reserialise_byte_equal(version: str) -> None:
    """Every stored ensemble, exclusion and fallback record loads and dumps unchanged."""
    seen = dict.fromkeys(KINDS, 0)
    for path in sorted((FIXTURES / version).rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        if path.name.endswith(".runrecord.json"):
            # The records' own writer: ``RunRecord.model_dump_json(indent=1)``.
            document = json.loads(text)
            reserialised(document, seen)
            again = RunRecord.model_validate_json(text).model_dump_json(indent=1)
            assert again == text.removesuffix("\n"), path.name
        else:
            document = reserialised(json.loads(text), seen)
            again = json.dumps(document, indent=2, sort_keys=True) + "\n"
            assert again == text, path.name
    assert seen[TSEnsemble] > 0 and seen[TSEnsembleExclusion] > 0
    if version == "v0.7.0":
        assert seen[FallbackRecord] > 0
