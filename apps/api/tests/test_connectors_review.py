"""Connector mode-switching, ingest dedupe, and the review gate."""

from __future__ import annotations

import os
from datetime import date

import pytest

from nintel.connectors import RssReader, SentimentMonitorReader, SupabaseReader
from nintel.engine.ingest import content_hash, ingest


def test_connectors_yield_expected_provenance():
    since = date(2000, 1, 1)
    assert all(r.provenance == "B" for r in SupabaseReader().fetch(since))
    assert all(r.provenance == "A" for r in SentimentMonitorReader().fetch(since))
    assert all(r.provenance == "C" for r in RssReader().fetch(since))
    # source C exists in the weekly seed (Wi-Fi Alliance RSS).
    assert RssReader().fetch(since)


def test_live_mode_raises(monkeypatch):
    monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "live")
    from nintel.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(NotImplementedError) as exc:
            SupabaseReader().fetch(date(2000, 1, 1))
        assert "live" in str(exc.value).lower()
    finally:
        monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "fixture")
        get_settings.cache_clear()


def test_ingest_dedupes_by_content_hash():
    items = ingest(persist=False)
    hashes = [content_hash(i["source"], i["url"], i["title"]) for i in items]
    assert len(hashes) == len(set(hashes)), "ingest produced duplicate content_hashes"
    # The EAP610 + SG2218 items appear in both seeds but should be deduped to one each.
    urls = [i["url"] for i in items]
    assert len(urls) == len(set(urls))


def test_ingest_persists_idempotently():
    from nintel.store.db import reset_db, session_scope
    from nintel.store.models import IntelItemRow

    reset_db()
    ingest(persist=True)
    with session_scope() as s:
        first = s.query(IntelItemRow).count()
    ingest(persist=True)  # second run must not duplicate
    with session_scope() as s:
        second = s.query(IntelItemRow).count()
    assert first == second and first > 0


def test_review_gate_pending_then_approve():
    from nintel.pipeline import build
    from nintel.review import approve, list_pending, list_published, submit

    report = build("daily", persist_items=False)
    path = submit(report)  # manual mode -> pending
    assert path.parent.name == "pending"
    assert report.report_id in list_pending()

    out = approve(report.report_id)
    assert out.parent.name == "published"
    assert report.report_id in list_published()
    assert report.report_id not in list_pending()


def test_review_auto_mode_publishes(monkeypatch):
    from nintel.config import get_settings
    from nintel.pipeline import build
    from nintel.review import list_published, submit

    monkeypatch.setenv("NINTEL_REVIEW_MODE", "auto")
    get_settings.cache_clear()
    try:
        report = build("weekly", persist_items=False)
        path = submit(report)
        assert path.parent.name == "published"
        assert report.report_id in list_published()
    finally:
        monkeypatch.setenv("NINTEL_REVIEW_MODE", "manual")
        get_settings.cache_clear()
