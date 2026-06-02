"""Contract round-trip + schema validation tests."""

from __future__ import annotations

import json

import pytest

from nintel.contract import (
    Report,
    iter_schema_errors,
    load_report,
    validate_against_schema,
)

SEEDS = ["2026-06-01-daily", "2026-W22-weekly"]


@pytest.mark.parametrize("report_id", SEEDS)
def test_round_trip_lossless(contract_dir, report_id):
    """load → Pydantic → dump must equal the original seed and be schema-valid."""

    doc = json.loads((contract_dir / f"{report_id}.json").read_text(encoding="utf-8"))
    report = load_report(doc)
    out = report.dump()

    validate_against_schema(out)
    assert out == doc, f"round-trip mismatch for {report_id}"


@pytest.mark.parametrize("report_id", SEEDS)
def test_seed_is_schema_valid(contract_dir, report_id):
    doc = json.loads((contract_dir / f"{report_id}.json").read_text(encoding="utf-8"))
    # Should not raise.
    validate_against_schema(doc)
    assert not list(iter_schema_errors(doc))


def test_bad_doc_fails_schema(contract_dir):
    """A document missing required fields / using a bad enum must fail."""

    doc = json.loads((contract_dir / "2026-06-01-daily.json").read_text(encoding="utf-8"))

    # 1) Missing a required top-level field.
    broken = dict(doc)
    broken.pop("references")
    with pytest.raises(Exception):
        validate_against_schema(broken)

    # 2) Illegal omada_impact enum value on an item.
    broken2 = json.loads(json.dumps(doc))
    broken2["items"][0]["omada_impact"] = "totally_invalid"
    with pytest.raises(Exception):
        validate_against_schema(broken2)

    # 3) Pydantic also rejects the bad enum.
    with pytest.raises(Exception):
        Report.model_validate(broken2)


def test_subject_impact_vocab_enforced_in_code(contract_dir):
    """curate.validate_subject_impact rejects cross-subject impacts."""

    from nintel.engine.curate import validate_subject_impact

    # omada_self may not be a competitor impact.
    with pytest.raises(ValueError):
        validate_subject_impact({"id": "x", "subject": "omada_self", "omada_impact": "threat"})
    # competitor may not be a self impact.
    with pytest.raises(ValueError):
        validate_subject_impact({"id": "y", "subject": "competitor", "omada_impact": "needs_fix"})
    # legal combos pass.
    validate_subject_impact({"id": "z", "subject": "omada_self", "omada_impact": "needs_fix"})
    validate_subject_impact({"id": "w", "subject": "competitor", "omada_impact": "opportunity"})
