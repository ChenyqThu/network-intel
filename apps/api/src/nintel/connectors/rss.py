"""Source C — industry RSS reader.

Offline (default) it reconstructs provenance-``C`` rows from the weekly seed.
When ``NINTEL_CONNECTOR_MODE=live`` and ``C`` ∈ ``NINTEL_LIVE_SOURCES`` it polls
the feeds in ``NINTEL_RSS_FEEDS`` (comma-separated) with feedparser and maps
each entry via :func:`map_rss_entry`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for

_LIVE_HINT = (
    "A live reader polls the feeds in NINTEL_RSS_FEEDS (e.g. wi-fi.org, "
    "IEEE 802.11) with a feed parser."
)


def map_rss_entry(entry: dict[str, Any]) -> RawRow:
    """Map a normalized RSS entry ``{link,title,published,summary}`` -> RawRow."""

    url = entry.get("link") or entry["url"]
    title = entry.get("title") or ""
    published = str(entry.get("published") or "")[:10]
    raw: dict[str, Any] = {
        "source": "rss",
        "provenance": "C",
        "url": url,
        "title": title,
        "date": published,
        "source_domain": domain_of(url),
        "source_tier": "community",
    }
    if entry.get("summary"):
        raw["summary"] = entry["summary"]
    return RawRow(source="rss", provenance="C", url=url, title=title, published=published, raw=raw)


class RssReader:
    """Reader for industry RSS feeds (source C)."""

    name = "rss:industry"
    provenance = "C"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        rows = seed_rows_for(provenances={"C"})
        return [r for r in rows if r.date >= since]

    def _fetch_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        import os
        import time

        import feedparser  # optional [live] dependency

        feeds = [u.strip() for u in os.environ.get("NINTEL_RSS_FEEDS", "").split(",") if u.strip()]
        rows: list[RawRow] = []
        for feed_url in feeds:
            for e in feedparser.parse(feed_url).entries:
                pub = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                published = time.strftime("%Y-%m-%d", pub) if pub else ""
                rows.append(
                    map_rss_entry(
                        {
                            "link": e.get("link"),
                            "title": e.get("title"),
                            "published": published,
                            "summary": e.get("summary"),
                        }
                    )
                )
        return rows
