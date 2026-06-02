"""WS2: live connector mappers + per-source gating (no network).

Proves the live mapping is shape-compatible with the fixture path (same
content_hash -> ingest dedupe treats live + fixture as the same item) and that
sources can be enabled one at a time via NINTEL_LIVE_SOURCES.
"""

from __future__ import annotations

from datetime import date

import pytest

from nintel.connectors import RssReader, SentimentMonitorReader, SupabaseReader
from nintel.connectors.base import RawRow
from nintel.connectors.rss import map_rss_entry
from nintel.connectors.sentiment_monitor import map_notion_record
from nintel.connectors.supabase import map_supabase_row
from nintel.engine.ingest import content_hash

SINCE = date(2000, 1, 1)


def _fixture_row(reader, source: str) -> RawRow:
    rows = reader.fetch(SINCE)
    return next((r for r in rows if r.source == source), rows[0])


def test_supabase_mapper_parity():
    rel = _fixture_row(SupabaseReader(), "unifi_release")
    live = {"url": rel.url, "title": rel.title, "published_at": rel.published + "T00:00:00Z", "likes": 10}
    rr = map_supabase_row("product_releases", live)
    assert rr.provenance == "B" and rr.source == "unifi_release"
    assert rr.url == rel.url  # full UUID preserved, never truncated
    # Same identity as the fixture row -> ingest would dedupe them together.
    assert content_hash(rr.source, rr.url, rr.title) == content_hash(rel.source, rel.url, rel.title)
    assert rr.raw["metrics"]["likes"] == 10
    assert rr.raw["source_tier"] == "official"


def test_notion_mapper_parity():
    a = _fixture_row(SentimentMonitorReader(), "reddit")
    live = {"source": a.source, "url": a.url, "title": a.title, "date": a.published,
            "sentiment": "neg", "relevance": 0.9, "switch_intent": True}
    rr = map_notion_record(live)
    assert rr.provenance == "A"
    assert content_hash(rr.source, rr.url, rr.title) == content_hash(a.source, a.url, a.title)
    assert rr.raw["sentiment"] == "neg" and rr.raw["switch_intent"] is True


def test_rss_mapper_parity():
    c = _fixture_row(RssReader(), "rss")
    live = {"link": c.url, "title": c.title, "published": c.published, "summary": "x"}
    rr = map_rss_entry(live)
    assert rr.provenance == "C" and rr.source == "rss"
    assert content_hash(rr.source, rr.url, rr.title) == content_hash(c.source, c.url, c.title)


def test_per_source_live_gating_routes_one_at_a_time(monkeypatch):
    from nintel.config import get_settings

    monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "live")
    monkeypatch.setenv("NINTEL_LIVE_SOURCES", "B")  # enable only source B
    get_settings.cache_clear()
    sentinel = RawRow(source="unifi_release", provenance="B", url="http://x",
                      title="T", published="2026-06-01", raw={})
    monkeypatch.setattr(SupabaseReader, "_fetch_live", lambda self, since: [sentinel])
    try:
        # B enabled -> live path used.
        assert SupabaseReader().fetch(SINCE) == [sentinel]
        # A not enabled -> loud NotImplementedError (not a silent fixture fallback).
        with pytest.raises(NotImplementedError):
            SentimentMonitorReader().fetch(SINCE)
    finally:
        monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "fixture")
        monkeypatch.delenv("NINTEL_LIVE_SOURCES", raising=False)
        get_settings.cache_clear()
