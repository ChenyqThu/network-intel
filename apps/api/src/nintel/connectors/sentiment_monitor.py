"""Source A — omada-sentiment-monitor (Notion) reader.

Live behaviour
--------------
A live :class:`SentimentMonitorReader` would page the
``omada-sentiment-monitor`` Notion database (``NOTION_TOKEN`` +
``NOTION_DATABASE_ID``) where the monitor has already written Reddit / YouTube
posts annotated with ``sentiment`` (pos/neg/neu), ``relevance`` (0..1) and
``switch_intent`` (bool). i.e.::

    pages = notion.databases.query(database_id=..., filter={"date": {"on_or_after": since}})

and map each Notion page's properties onto :class:`RawRow` (carrying the
sentiment annotations in ``raw``). Sources emitted: ``reddit`` and ``youtube``.

Offline (default) the reader reconstructs these rows from the provenance-``A``
items in the canonical seed reports — which already carry the sentiment fields.
"""

from __future__ import annotations

from datetime import date

from .base import RawRow, connector_mode_guard, seed_rows_for

_LIVE_HINT = (
    "A live reader would query the omada-sentiment-monitor Notion database "
    "(NOTION_TOKEN + NOTION_DATABASE_ID) for Reddit/YouTube posts with "
    "sentiment / relevance / switch_intent annotations."
)


class SentimentMonitorReader:
    """Fixture-backed reader for the sentiment monitor (source A)."""

    name = "notion:sentiment_monitor"
    provenance = "A"

    def fetch(self, since: date) -> list[RawRow]:
        connector_mode_guard(self.name, _LIVE_HINT)
        rows = seed_rows_for(provenances={"A"})
        return [r for r in rows if r.date >= since]
