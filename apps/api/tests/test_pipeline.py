"""Pipeline build tests: schema-valid, correct sections, subject-aware impacts,
cite_id ↔ reference integrity, and resolvable {{cite:N}} refs."""

from __future__ import annotations

import re

import pytest

from nintel.contract import validate_against_schema
from nintel.engine.curate import IMPACT_VOCAB
from nintel.pipeline import build

_CITE_RE = re.compile(r"\{\{cite:(\d+)\}\}")

EXPECTED_SECTIONS = {
    "daily": ["omada_self", "competitor", "sentiment", "industry"],
    "weekly": ["omada_self", "competitor", "sentiment", "store", "industry", "dashboard"],
}


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_build_is_schema_valid(rtype):
    report = build(rtype, persist_items=False)
    validate_against_schema(report.dump())
    assert report.type == rtype


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_section_keys(rtype):
    report = build(rtype, persist_items=False)
    keys = [s.key for s in report.sections]
    assert keys == EXPECTED_SECTIONS[rtype]


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_subject_aware_impacts(rtype):
    report = build(rtype, persist_items=False)
    for item in report.items:
        allowed = IMPACT_VOCAB[item.subject] | {"unknown"}
        assert item.omada_impact in allowed, (
            f"{item.id}: {item.omada_impact} illegal for subject {item.subject}"
        )


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_cite_id_reference_integrity(rtype):
    report = build(rtype, persist_items=False)

    ref_ids = [r.cite_id for r in report.references]
    assert len(ref_ids) == len(set(ref_ids)), "duplicate cite_id in references"

    item_ids = {it.cite_id for it in report.items}
    assert item_ids == set(ref_ids), "item cite_id set != reference cite_id set"


@pytest.mark.parametrize("rtype", ["daily", "weekly"])
def test_all_cite_placeholders_resolvable(rtype):
    report = build(rtype, persist_items=False)
    ref_ids = {r.cite_id for r in report.references}

    used: set[int] = set(int(m) for m in _CITE_RE.findall(report.lead.text))
    if report.strategy:
        used |= {int(m) for m in _CITE_RE.findall(report.strategy.body)}
        for _label, body in report.strategy.paras or []:
            used |= {int(m) for m in _CITE_RE.findall(body)}

    assert used, "expected at least one {{cite:N}} in lead/strategy"
    assert used <= ref_ids, f"unresolvable refs: {sorted(used - ref_ids)}"


def test_weekly_has_strategy_daily_does_not():
    assert build("daily", persist_items=False).strategy is None
    weekly = build("weekly", persist_items=False)
    assert weekly.strategy is not None
    assert weekly.strategy.title


def test_weekly_store_and_dashboard_present():
    weekly = build("weekly", persist_items=False)
    assert weekly.store, "weekly should have store rows"
    assert weekly.dashboard, "weekly should have a dashboard payload"
    assert "sentimentTrend" in weekly.dashboard
    assert "topHeat" in weekly.dashboard


def test_stats_recomputed_consistently():
    """trend stage recomputes by_source/by_impact from items."""

    weekly = build("weekly", persist_items=False)
    stats = weekly.stats
    by_impact_sum = sum(stats.by_impact.values())
    assert stats.total_items == len(weekly.items) == by_impact_sum
    assert sum(stats.by_source.values()) == len(weekly.items)
