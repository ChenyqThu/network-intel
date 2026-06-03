"""Source H — generic HTML-scrape reader (no-feed official sources).

For high-value sources that have **no usable RSS** but a stable listing page —
UniFi blog, Netgear blog, MediaTek/Realtek newsrooms, Reyee news. Unlike the
Google-News query feeds (which yield redirect URLs), this collects the
publisher's **real article URLs** directly, so the citation line stays truthful
(PRD §7.8.6).

Design
------
* :data:`SITES` lists each source: a listing URL + a ``link_pattern`` regex that
  matches its article hrefs + the routing fields (source/subject/category).
* :func:`parse_listing` is a **pure**, stdlib-only (``html.parser``) extractor:
  HTML + site config -> deduped ``RawRow`` list. Unit-tested against a synthetic
  page, so the extraction engine is proven offline with no dependency.
* The live path just fetches each listing with a browser UA and runs the parser.

⚠️ The per-site ``link_pattern`` values are **templates**: validate each against
the live page's real HTML before enabling that site (DOM changes / SPA shells
can need tuning). Listing pages rarely expose reliable per-article dates, so
scraped items are stamped with the run date (good enough for the weekly window;
the LLM curate stage can refine).
"""

from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .base import RawRow, connector_mode_guard, domain_of, tier_for_domain

_LIVE_HINT = "A live reader fetches the SITES listing pages and extracts article links."

_UA = "Mozilla/5.0 (compatible; NetworkIntelBot/1.0; +https://nintel.chenge.ink)"

# Each site: listing page + an href regex for its articles + routing fields.
# link_pattern is a TEMPLATE — validate against the live page before enabling.
SITES: tuple[dict[str, Any], ...] = (
    {"key": "unifi_blog", "url": "https://blog.ui.com/", "link_pattern": r"/article/[^/]+/?$",
     "source": "blog", "subject": "competitor", "category": "new_product"},
    {"key": "netgear_blog", "url": "https://www.netgear.com/blog/", "link_pattern": r"/blog/[^/]+/.+",
     "source": "rss", "subject": "competitor", "category": "competitor"},
    {"key": "mediatek_blog", "url": "https://www.mediatek.com/tek-talk-blogs", "link_pattern": r"/tek-talk-blogs/[^/]+",
     "source": "rss", "subject": "industry", "category": "industry"},
    {"key": "realtek_news", "url": "https://www.realtek.com/en/press-room/news-releases", "link_pattern": r"/press-room/news-releases/[^/]+",
     "source": "rss", "subject": "industry", "category": "industry"},
    {"key": "reyee_news", "url": "https://reyee.ruijie.com/en-global/about/news/", "link_pattern": r"/about/news/.+",
     "source": "rss", "subject": "competitor", "category": "competitor"},
)


class _AnchorExtractor(HTMLParser):
    """Collect ``(href, text)`` for anchors whose href matches ``pattern``."""

    def __init__(self, pattern: re.Pattern[str]) -> None:
        super().__init__()
        self._pat = pattern
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        if href and self._pat.search(href):
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


def parse_listing(html: str, site: dict[str, Any], *, run_date: str) -> list[RawRow]:
    """Pure: listing HTML + site config -> deduped RawRow list (provenance ``H``)."""

    parser = _AnchorExtractor(re.compile(site["link_pattern"]))
    parser.feed(html)
    rows: list[RawRow] = []
    seen: set[str] = set()
    for href, title in parser.links:
        url = urljoin(site["url"], href)
        if not title or url in seen:
            continue
        seen.add(url)
        domain = domain_of(url)
        raw: dict[str, Any] = {
            "source": site["source"], "provenance": "H", "url": url, "title": title,
            "date": run_date, "source_domain": domain, "source_tier": tier_for_domain(domain),
            "subject": site["subject"], "category": site["category"],
        }
        rows.append(RawRow(source=site["source"], provenance="H", url=url, title=title, published=run_date, raw=raw))
    return rows


class HtmlScrapeReader:
    """Reader for no-feed official sources via listing-page scrape (source H)."""

    name = "html:scrape"
    provenance = "H"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        return []  # no offline fixture — scrape is a live-only source

    def _fetch_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        import logging
        import urllib.request

        log = logging.getLogger(__name__)
        run_date = date.today().isoformat()
        rows: list[RawRow] = []
        for site in SITES:
            try:
                req = urllib.request.Request(site["url"], headers={"User-Agent": _UA})
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted host)
                    html = resp.read().decode("utf-8", "replace")
            except Exception as exc:  # noqa: BLE001 - one bad site must not kill the run
                log.warning("scrape failed %s: %s", site["key"], exc)
                continue
            rows.extend(parse_listing(html, site, run_date=run_date))
        return rows
