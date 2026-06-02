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
from nintel.connectors.supabase import map_blog_row, map_community_row, map_release_row
from nintel.engine.ingest import content_hash

SINCE = date(2000, 1, 1)


def _fixture_row(reader, source: str) -> RawRow:
    rows = reader.fetch(SINCE)
    return next((r for r in rows if r.source == source), rows[0])


def test_supabase_release_mapper():
    # real product_releases row shape (verified live)
    row = {"release_id": "8485312c-c516-431b-9723-ee42ee71769a", "slug": "Site-Manager-5-7-1",
           "title": "Site Manager", "release_date": "2026-06-02T09:24:44Z",
           "stage": "GA", "view_count": 348, "comment_count": 2}
    rr = map_release_row(row)
    assert rr.source == "unifi_release" and rr.provenance == "B"
    assert rr.url == "https://community.ui.com/releases/Site-Manager-5-7-1/8485312c-c516-431b-9723-ee42ee71769a"
    assert rr.published == "2026-06-02"
    assert rr.raw["source_tier"] == "official"
    assert rr.raw["metrics"]["views"] == 348 and rr.raw["stage"] == "GA"
    assert content_hash(rr.source, rr.url, rr.title)  # computable/stable


def test_supabase_community_mapper():
    row = {"post_id": "02757b49-87a3-429e-b0eb-89db4ecab2a3", "post_type": "question",
           "slug": "Upgrade-AP-Pro-from-4-3-31", "title": "Upgrade AP Pro from 4.3.31",
           "published_at": "2026-06-02T12:37:42Z", "view_count": 1, "comment_count": 0, "like_count": 3}
    rr = map_community_row(row)
    assert rr.source == "unifi_community" and rr.provenance == "B"
    assert rr.url == "https://community.ui.com/questions/Upgrade-AP-Pro-from-4-3-31/02757b49-87a3-429e-b0eb-89db4ecab2a3"
    assert rr.raw["metrics"]["likes"] == 3


def test_supabase_blog_mapper():
    row = {"slug": "introducing-unifi-5g-backup",
           "canonical_url": "https://blog.ui.com/article/introducing-unifi-5g-backup",
           "title": "Introducing UniFi 5G Backup", "published_at": "2026-05-21T08:39:48Z",
           "view_count": 56683}
    rr = map_blog_row(row)
    assert rr.source == "blog" and rr.provenance == "B"
    assert rr.url == "https://blog.ui.com/article/introducing-unifi-5g-backup"
    assert rr.raw["source_domain"] == "blog.ui.com"
    assert rr.raw["metrics"]["views"] == 56683


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
