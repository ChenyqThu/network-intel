"""Industry sources (C feeds + G Gemini-research + H scrape) — offline.

Covers the pure seams (tier classification, feed-list union, the research
mapper, the scrape parser) and per-source live gating, with no network and no
key — mirroring test_connectors_live.py.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from nintel.connectors import GeminiResearchReader, HtmlScrapeReader
from nintel.connectors.base import tier_for_domain
from nintel.connectors.gemini_research import map_research_item
from nintel.connectors.html_scrape import parse_listing
from nintel.connectors.rss import feed_urls
from nintel.contract import validate_against_schema
from nintel.engine.ingest import content_hash

SINCE = date(2000, 1, 1)


# --- shared tier helper ----------------------------------------------------
def test_tier_for_domain():
    assert tier_for_domain("blog.ui.com") == "official"      # subdomain of ui.com
    assert tier_for_domain("www.qualcomm.com") == "official"  # www stripped
    assert tier_for_domain("csa-iot.org") == "official"
    assert tier_for_domain("cnx-software.com") == "community"  # media, not first-party
    assert tier_for_domain("reddit.com") == "community"
    assert tier_for_domain("") == "community"


# --- source C: feed-list union (inline env + catalog file) -----------------
def test_feed_urls_unions_dedupes_and_skips_comments(tmp_path, monkeypatch):
    monkeypatch.setenv("NINTEL_RSS_FEEDS", "https://a.com/feed, https://b.com/feed")
    f = tmp_path / "feeds.txt"
    f.write_text("# a comment\nhttps://b.com/feed\nhttps://c.com/feed\n\n", encoding="utf-8")
    urls = feed_urls(SimpleNamespace(rss_feeds_file=str(f)))
    # order preserved, b.com deduped across inline+file, '#'/blank lines dropped
    assert urls == ["https://a.com/feed", "https://b.com/feed", "https://c.com/feed"]


def test_feed_urls_missing_file_is_ignored(monkeypatch):
    monkeypatch.setenv("NINTEL_RSS_FEEDS", "https://a.com/feed")
    urls = feed_urls(SimpleNamespace(rss_feeds_file="/no/such/file.txt"))
    assert urls == ["https://a.com/feed"]


# --- source G: Gemini research mapper --------------------------------------
def test_map_research_item():
    rr = map_research_item(
        {"title": "Wi-Fi 8 draft 2.0 approved", "url": "https://wifinowglobal.com/x",
         "source_domain": "wifinowglobal.com", "date": "2026-05-30", "summary": "..."},
        run_date="2026-06-01",
    )
    assert rr.provenance == "G" and rr.source == "rss"
    assert rr.raw["subject"] == "industry" and rr.raw["category"] == "industry_trend"
    assert rr.raw["source_tier"] == "community"
    assert rr.published == "2026-05-30"
    assert content_hash(rr.source, rr.url, rr.title)  # computable/stable


def test_map_research_item_bad_date_and_derived_domain():
    rr = map_research_item(
        {"title": "t", "url": "https://www.mediatek.com/a", "date": "last week"},
        run_date="2026-06-01",
    )
    assert rr.published == "2026-06-01"                      # unparseable -> run_date
    assert rr.raw["source_domain"] == "www.mediatek.com"     # derived from url
    assert rr.raw["source_tier"] == "official"               # mediatek.com is first-party


# --- source H: HTML scrape parser ------------------------------------------
def test_parse_listing_extracts_dedupes_and_routes():
    site = {"key": "t", "url": "https://blog.ui.com/", "link_pattern": r"/article/[^/]+/?$",
            "source": "blog", "subject": "competitor", "category": "new_product"}
    html = """
      <a href="/article/intro-5g-backup">Introducing UniFi 5G Backup</a>
      <a href="/about">About</a>
      <a href="https://blog.ui.com/article/intro-5g-backup">dup link</a>
      <a href="/article/another-post">  Another   Post  </a>
    """
    rows = parse_listing(html, site, run_date="2026-06-01")
    urls = [r.url for r in rows]
    assert "https://blog.ui.com/article/intro-5g-backup" in urls
    assert "https://blog.ui.com/article/another-post" in urls
    assert all("/about" not in u for u in urls)              # non-matching link skipped
    assert urls.count("https://blog.ui.com/article/intro-5g-backup") == 1  # rel+abs deduped
    first = next(r for r in rows if r.url.endswith("intro-5g-backup"))
    assert first.provenance == "H" and first.raw["subject"] == "competitor"
    assert first.title == "Introducing UniFi 5G Backup"
    assert next(r for r in rows if r.url.endswith("another-post")).title == "Another Post"  # ws collapsed


# --- gating: fixture is empty, live raises until opted in -------------------
def test_industry_sources_fixture_empty():
    # fixture mode (default): no network, no key — empty, no seed rows yet.
    assert GeminiResearchReader().fetch(SINCE) == []
    assert HtmlScrapeReader().fetch(SINCE) == []


def test_industry_sources_live_gating(monkeypatch):
    from nintel.config import get_settings

    monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "live")
    monkeypatch.setenv("NINTEL_LIVE_SOURCES", "B")  # G / H not enabled
    get_settings.cache_clear()
    try:
        with pytest.raises(NotImplementedError):
            GeminiResearchReader().fetch(SINCE)
        with pytest.raises(NotImplementedError):
            HtmlScrapeReader().fetch(SINCE)
    finally:
        monkeypatch.setenv("NINTEL_CONNECTOR_MODE", "fixture")
        monkeypatch.delenv("NINTEL_LIVE_SOURCES", raising=False)
        get_settings.cache_clear()


# --- contract: the new provenance letters validate -------------------------
def test_provenance_g_h_valid_in_schema():
    item = {
        "id": "g1", "cite_id": 1, "subject": "industry", "source": "rss",
        "source_domain": "wifinowglobal.com", "source_tier": "community",
        "provenance": "G", "title": "t", "summary": "s", "category": "industry_trend",
        "omada_impact": "neutral", "date": "2026-06-01", "url": "https://wifinowglobal.com/x",
    }
    doc = {
        "report_id": "t", "type": "daily", "date": "2026-06-01", "date_range": "2026-06-01",
        "generated_at": "2026-06-01T00:00:00-07:00",
        "lead": {"text": "x", "cite_refs": []}, "sections": [], "items": [item],
        "references": [{"cite_id": 1, "title": "t", "source_domain": "wifinowglobal.com",
                        "date": "2026-06-01", "url": "https://wifinowglobal.com/x"}],
        "stats": {},
    }
    validate_against_schema(doc)                       # G accepted
    doc["items"] = [{**item, "id": "h1", "provenance": "H"}]
    validate_against_schema(doc)                       # H accepted
