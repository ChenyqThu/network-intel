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
from nintel.connectors.sentiment_monitor import map_reddit_row, map_youtube_row
from nintel.connectors.supabase import (
    map_blog_row,
    map_community_row,
    map_price_change,
    map_release_row,
    map_stock_change,
    map_upcoming_product,
)
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


def test_reddit_mapper():
    # real posts row shape (verified live)
    row = {"subreddit": "Ubiquiti", "title": "Troubleshooting UniFi Express 7",
           "permalink": "/r/Ubiquiti/comments/1t4t4qk/x/",
           "url": "https://www.reddit.com/r/Ubiquiti/comments/1t4t4qk/x/",
           "score": 12, "num_comments": 4, "created_utc": 1778016684.0,
           "ai_relevance_score": 0.45, "ai_sentiment_quick": "negative"}
    rr = map_reddit_row(row)
    assert rr.source == "reddit" and rr.provenance == "A"
    assert rr.url == "https://www.reddit.com/r/Ubiquiti/comments/1t4t4qk/x/"
    assert rr.raw["sentiment"] == "neg"
    assert rr.raw["metrics"]["likes"] == 12 and rr.raw["relevance"] == 0.45
    assert rr.published.startswith("2026-")
    assert content_hash(rr.source, rr.url, rr.title)


def test_youtube_mapper():
    row = {"channel_title": "Unified IT", "title": "UniFi Network Vulnerability",
           "url": "https://www.youtube.com/watch?v=NB5xpGjZcUA",
           "published_at": "2026-03-20T23:38:05Z", "view_count": 278, "like_count": 13,
           "comment_count": 1, "ai_relevance_score": 0.7, "ai_sentiment_quick": "negative"}
    rr = map_youtube_row(row)
    assert rr.source == "youtube" and rr.provenance == "A"
    assert rr.url == "https://www.youtube.com/watch?v=NB5xpGjZcUA"
    assert rr.published == "2026-03-20"
    assert rr.raw["metrics"]["views"] == 278 and rr.raw["sentiment"] == "neg"


def _notion_page(props: dict) -> dict:
    return {"properties": props}


def test_notion_reddit_mapper_omada_self():
    from nintel.connectors.sentiment_monitor import map_notion_reddit

    page = _notion_page({
        "标题": {"type": "title", "title": [{"plain_text": "ER707 M2 hijacking DNS"}]},
        "Reddit链接": {"type": "url", "url": "https://www.reddit.com/r/TPLINK/comments/abc/x/"},
        "发布时间": {"type": "date", "date": {"start": "2026-05-30T10:00:00Z"}},
        "情感倾向": {"type": "select", "select": {"name": "负面"}},
        "匹配关键词": {"type": "multi_select", "multi_select": [{"name": "Omada"}, {"name": "TP-Link"}]},
        "产品型号": {"type": "multi_select", "multi_select": []},
        "分数": {"type": "number", "number": 15},
        "评论数": {"type": "number", "number": 3},
        "相关性得分": {"type": "number", "number": 0.8},
        "切换意图": {"type": "checkbox", "checkbox": True},
        "AI摘要": {"type": "rich_text", "rich_text": [{"plain_text": "用户反映 ER707 DNS 问题"}]},
    })
    rr = map_notion_reddit(page)
    assert rr.source == "reddit" and rr.provenance == "A"
    assert rr.url.endswith("/abc/x/") and rr.published == "2026-05-30"
    assert rr.raw["subject"] == "omada_self"          # Omada/TP-Link tag -> our product
    assert rr.raw["omada_impact"] == "needs_fix"      # omada_self + negative
    assert rr.raw["sentiment"] == "neg" and rr.raw["switch_intent"] is True
    assert rr.raw["metrics"]["likes"] == 15 and rr.raw["summary"]
    assert content_hash(rr.source, rr.url, rr.title)


def test_notion_reddit_mapper_competitor():
    from nintel.connectors.sentiment_monitor import map_notion_reddit

    page = _notion_page({
        "标题": {"type": "title", "title": [{"plain_text": "First Ubiquiti Set Up"}]},
        "Reddit链接": {"type": "url", "url": "https://www.reddit.com/r/Ubiquiti/comments/def/x/"},
        "发布时间": {"type": "date", "date": {"start": "2026-06-01T10:00:00Z"}},
        "情感倾向": {"type": "select", "select": {"name": "中性"}},
        "匹配关键词": {"type": "multi_select", "multi_select": [{"name": "Competitor"}, {"name": "ubiquiti"}]},
        "切换意图": {"type": "checkbox", "checkbox": False},
    })
    rr = map_notion_reddit(page)
    assert rr.raw["subject"] == "competitor"          # no Omada marker
    assert rr.raw["omada_impact"] == "neutral"        # competitor + neutral
    assert rr.raw["switch_intent"] is False


def test_notion_youtube_mapper_brand_and_impact():
    from nintel.connectors.sentiment_monitor import map_notion_youtube

    page = _notion_page({
        "标题": {"type": "title", "title": [{"plain_text": "TP-Link Omada SDN review"}]},
        "视频链接": {"type": "url", "url": "https://www.youtube.com/watch?v=xyz"},
        "发布时间": {"type": "date", "date": {"start": "2026-05-29T00:00:00Z"}},
        "情感倾向": {"type": "select", "select": {"name": "正面"}},
        "播放量": {"type": "number", "number": 1000},
    })
    rr = map_notion_youtube(page)
    assert rr.source == "youtube" and rr.published == "2026-05-29"
    assert rr.raw["subject"] == "omada_self"
    assert rr.raw["omada_impact"] == "strength_confirm"   # omada_self + positive
    assert rr.raw["metrics"]["views"] == 1000


def test_rss_mapper_parity():
    c = _fixture_row(RssReader(), "rss")
    live = {"link": c.url, "title": c.title, "published": c.published, "summary": "x"}
    rr = map_rss_entry(live)
    assert rr.provenance == "C" and rr.source == "rss"
    assert content_hash(rr.source, rr.url, rr.title) == content_hash(c.source, c.url, c.title)


def test_store_price_change_mapper():
    # real store_recent_price_changes row shape (verified live)
    row = {"sku": "UACC-HDD-E-16TB", "store_region": "us", "previous_price": 609,
           "current_price": 719, "product_name": "UACC-HDD-E-16TB",
           "product_title": 'Enterprise 3.5" HDD, 16 TB', "category_slug": "cables-accessories"}
    m = map_price_change(row)
    # friendly product_title preferred over the SKU in product_name
    assert m["product"] == 'Enterprise 3.5" HDD, 16 TB' and m["cat"] == "cables accessories"
    assert m["from"] == 609 and m["to"] == 719
    assert m["dir"] == "up" and m["change"] == "+18%" and m["stock"] == "in"


def test_store_stock_change_mapper_out():
    row = {"sku": "U7-IW", "store_region": "us", "previous_stock": True,
           "current_stock": False, "product_name": "U7 In-Wall", "category_slug": "wifi"}
    m = map_stock_change(row)
    assert m["product"] == "U7 In-Wall" and m["stock"] == "out"
    assert m["dir"] == "down" and m["change"] == "缺货" and m["from"] is None


def test_store_upcoming_product_mapper():
    row = {"name": "UNVR-G2", "slug": "unvr-g2", "category_slug": "cameras-nvrs", "is_upcoming": True}
    m = map_upcoming_product(row)
    assert m["product"] == "UNVR-G2" and m["cat"] == "cameras nvrs"
    assert m["dir"] == "new" and m["change"] == "新品" and m["stock"] == "out"


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
