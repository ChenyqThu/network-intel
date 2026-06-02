"""Source A — omada-sentiment-monitor (Notion) reader.

Offline (default) it reconstructs provenance-``A`` rows from the seed reports
(which already carry sentiment / relevance / switch_intent). When
``NINTEL_CONNECTOR_MODE=live`` and ``A`` ∈ ``NINTEL_LIVE_SOURCES`` it pages the
omada-sentiment-monitor Notion database (``NOTION_TOKEN`` +
``NOTION_DATABASE_ID``) for Reddit / YouTube posts, flattens each page's
properties, and maps via :func:`map_notion_record`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for

_LIVE_HINT = (
    "A live reader queries the omada-sentiment-monitor Notion database "
    "(NOTION_TOKEN + NOTION_DATABASE_ID) for Reddit/YouTube posts with "
    "sentiment / relevance / switch_intent."
)


def map_notion_record(rec: dict[str, Any]) -> RawRow:
    """Map a flattened Notion record onto a :class:`RawRow` (pure; parity-tested).

    ``rec`` is the already-flattened page (``_flatten_page`` does the Notion
    property extraction): ``{source, url, title, date, sentiment, relevance,
    switch_intent, metrics, summary}``.
    """

    source = rec.get("source") or "reddit"
    url = rec["url"]
    title = rec.get("title") or ""
    published = str(rec.get("date") or "")[:10]
    raw: dict[str, Any] = {
        "source": source,
        "provenance": "A",
        "url": url,
        "title": title,
        "date": published,
        "source_domain": domain_of(url),
        "source_tier": "community",
    }
    for k in ("sentiment", "relevance", "switch_intent", "metrics", "summary"):
        if rec.get(k) is not None:
            raw[k] = rec[k]
    return RawRow(source=source, provenance="A", url=url, title=title, published=published, raw=raw)


class SentimentMonitorReader:
    """Reader for the sentiment monitor (source A)."""

    name = "notion:sentiment_monitor"
    provenance = "A"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        rows = seed_rows_for(provenances={"A"})
        return [r for r in rows if r.date >= since]

    def _fetch_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        import os

        from notion_client import Client  # optional [live] dependency

        notion = Client(auth=os.environ["NOTION_TOKEN"])
        db_id = os.environ["NOTION_DATABASE_ID"]
        pages = notion.databases.query(
            database_id=db_id,
            filter={
                "timestamp": "created_time",
                "created_time": {"on_or_after": since.isoformat()},
            },
        ).get("results", [])
        return [map_notion_record(_flatten_page(p)) for p in pages]


def _flatten_page(page: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover - network
    """Best-effort flattening of common Notion property types -> a flat record."""

    props = page.get("properties", {})

    def _val(name: str) -> Any:
        p = props.get(name) or {}
        kind = p.get("type")
        if kind in ("title", "rich_text"):
            return "".join(t.get("plain_text", "") for t in p.get(kind, []))
        if kind == "url":
            return p.get("url")
        if kind == "select":
            return (p.get("select") or {}).get("name")
        if kind == "number":
            return p.get("number")
        if kind == "checkbox":
            return p.get("checkbox")
        if kind == "date":
            return (p.get("date") or {}).get("start")
        return None

    return {
        "source": _val("source") or "reddit",
        "url": _val("url"),
        "title": _val("title") or _val("name"),
        "date": (_val("date") or page.get("created_time", ""))[:10],
        "sentiment": _val("sentiment"),
        "relevance": _val("relevance"),
        "switch_intent": _val("switch_intent"),
    }
