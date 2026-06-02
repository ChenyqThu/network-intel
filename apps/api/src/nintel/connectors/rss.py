"""Source C — industry RSS reader.

Live behaviour
--------------
A live :class:`RssReader` would poll a configured set of industry feeds
(Wi-Fi Alliance newsroom, IEEE 802.11 working-group updates, trade press) with
an HTTP client + feed parser, e.g.::

    for feed_url in settings.rss_feeds:
        for entry in feedparser.parse(feed_url).entries:
            if parse_date(entry.published) >= since:
                yield RawRow(source="rss", provenance="C", url=entry.link, ...)

Offline (default) the reader reconstructs these rows from the provenance-``C``
items in the canonical weekly seed report.
"""

from __future__ import annotations

from datetime import date

from .base import RawRow, connector_mode_guard, seed_rows_for

_LIVE_HINT = (
    "A live reader would poll the configured industry RSS feeds "
    "(e.g. wi-fi.org, IEEE 802.11) with a feed parser."
)


class RssReader:
    """Fixture-backed reader for industry RSS feeds (source C)."""

    name = "rss:industry"
    provenance = "C"

    def fetch(self, since: date) -> list[RawRow]:
        connector_mode_guard(self.name, _LIVE_HINT)
        rows = seed_rows_for(provenances={"C"})
        return [r for r in rows if r.date >= since]
