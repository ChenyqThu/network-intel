"""Source C — industry RSS reader.

Offline (default) it reconstructs provenance-``C`` rows from the weekly seed.
When ``NINTEL_CONNECTOR_MODE=live`` and ``C`` ∈ ``NINTEL_LIVE_SOURCES`` it polls
the curated feed catalog with feedparser and maps each entry via
:func:`map_rss_entry`.

Feed URLs come from two places (unioned, deduped, order-preserving):

* ``NINTEL_RSS_FEEDS`` — comma-separated, inline.
* ``NINTEL_RSS_FEEDS_FILE`` — path to a newline-delimited file (``#`` comment
  lines ignored), so the curated catalog (see ``config/industry_feeds.txt``)
  lives in a committed file rather than one giant env var.

Robustness (lessons from verifying the catalog):

* a browser-like User-Agent is sent — several real feeds (SDxCentral, Qualcomm)
  reject the default urllib/feedparser UA with 403/404;
* each feed is fetched in its own try/except so one bad feed never kills the run;
* entries with no parseable date fall back to the run date, so freshly-seen
  items aren't silently dropped by the downstream freshness gate.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for, tier_for_domain

_LIVE_HINT = (
    "A live reader polls NINTEL_RSS_FEEDS / NINTEL_RSS_FEEDS_FILE (e.g. "
    "cnx-software.com, wifinowglobal.com, csa-iot.org) with a feed parser."
)

# Several real feeds reject the default urllib/feedparser UA — send a browser-like one.
_UA = "Mozilla/5.0 (compatible; NetworkIntelBot/1.0; +https://nintel.chenge.ink)"


def map_rss_entry(entry: dict[str, Any]) -> RawRow:
    """Map a normalized RSS entry ``{link,title,published,summary}`` -> RawRow."""

    url = entry.get("link") or entry["url"]
    title = entry.get("title") or ""
    published = str(entry.get("published") or "")[:10]
    domain = domain_of(url)
    raw: dict[str, Any] = {
        "source": "rss",
        "provenance": "C",
        "url": url,
        "title": title,
        "date": published,
        "source_domain": domain,
        "source_tier": tier_for_domain(domain),
        # Industry RSS feeds the `industry` section by default; the LLM curate
        # stage may re-home a clearly competitor-specific item.
        "subject": "industry",
        "category": "industry",
    }
    if entry.get("summary"):
        raw["summary"] = entry["summary"]
    return RawRow(source="rss", provenance="C", url=url, title=title, published=published, raw=raw)


def feed_urls(settings) -> list[str]:
    """Union of inline (``NINTEL_RSS_FEEDS``) + file (``NINTEL_RSS_FEEDS_FILE``)
    feed URLs, deduped, order-preserving. Blank and ``#`` lines are ignored.

    Pure (no network) — unit-tested directly.
    """

    import os
    from pathlib import Path

    urls: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        u = raw.strip()
        if not u or u.startswith("#"):
            return
        # Catalog lines carry an inline "# annotation" after the URL; keep only
        # the first whitespace-delimited token (a URL never contains spaces).
        u = u.split()[0]
        if u in seen:
            return
        seen.add(u)
        urls.append(u)

    for u in os.environ.get("NINTEL_RSS_FEEDS", "").split(","):
        _add(u)
    feeds_file = getattr(settings, "rss_feeds_file", None)
    if feeds_file:
        try:
            for line in Path(feeds_file).read_text(encoding="utf-8").splitlines():
                _add(line)
        except OSError:
            pass
    return urls


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
        import logging
        import time

        import feedparser  # optional [live] dependency

        from ..config import get_settings

        log = logging.getLogger(__name__)
        run_date = date.today().isoformat()
        rows: list[RawRow] = []
        for feed_url in feed_urls(get_settings()):
            try:
                parsed = feedparser.parse(feed_url, agent=_UA)
            except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the batch
                log.warning("rss feed failed %s: %s", feed_url, exc)
                continue
            for e in parsed.entries:
                pub = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
                published = time.strftime("%Y-%m-%d", pub) if pub else run_date
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
