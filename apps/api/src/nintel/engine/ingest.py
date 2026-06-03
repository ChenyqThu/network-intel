"""Ingest stage: raw source rows → normalized IntelItem dicts → SQLite.

Responsibilities (SOLUTION §8, ARCHITECTURE §3):

* Pull :class:`~nintel.connectors.base.RawRow` from every connector.
* Normalize each onto the contract item shape (the fixture rows already carry
  the curated fields; a live ingest would do the field mapping + light
  enrichment here).
* Dedupe by ``content_hash`` = sha256(source | url | title).
* Persist to the ``intel_items`` table (idempotent on ``content_hash``).

The function returns the deduped, normalized item dicts so the downstream
classify/curate stages can run on them directly without a DB round-trip.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Iterable

from sqlalchemy import select

from ..connectors import all_connectors
from ..connectors.base import Connector, RawRow
from ..store.db import session_scope
from ..store.models import IntelItemRow

# A long lookback so the fixture seeds (late May 2026) are always in range.
DEFAULT_SINCE = date(2000, 1, 1)


def content_hash(source: str, url: str, title: str) -> str:
    """Stable dedupe key: sha256 of ``source | url | title``."""

    h = hashlib.sha256()
    h.update(f"{source}|{url}|{title}".encode("utf-8"))
    return h.hexdigest()


def normalize(row: RawRow) -> dict[str, Any]:
    """Map a raw row onto the contract item shape.

    For the fixture connectors the raw payload *is* the curated item, so we
    pass it through (a defensive copy). A live ingest would build the dict from
    the source-native fields, deriving ``source_domain`` from the URL, mapping
    Notion/Supabase columns to ``metrics``/``sentiment``, etc. The
    ``content_hash`` is attached for persistence/dedupe but is not part of the
    contract item.
    """

    item = dict(row.raw)
    item.setdefault("source", row.source)
    item.setdefault("url", row.url)
    item.setdefault("title", row.title)
    item.setdefault("date", row.published)
    return item


def _dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        ch = content_hash(item["source"], item["url"], item["title"])
        if ch in seen:
            continue
        seen.add(ch)
        out.append(item)
    return out


def ingest(
    connectors: list[Connector] | None = None,
    *,
    since: date = DEFAULT_SINCE,
    persist: bool = True,
    report_type: str | None = None,
) -> list[dict[str, Any]]:
    """Run every connector, normalize + dedupe, optionally persist.

    Returns the normalized, deduped item dicts (the raw material for classify).
    When ``report_type`` is a non-weekly cadence, connectors declaring
    ``cadence == "weekly"`` (e.g. the Gemini deep-research source) are skipped.
    """

    if connectors is None:
        connectors = all_connectors()
        if report_type is not None and report_type != "weekly":
            connectors = [c for c in connectors if getattr(c, "cadence", "both") != "weekly"]

    raw: list[dict[str, Any]] = []
    for conn in connectors:
        try:
            rows = conn.fetch(since)
        except Exception as exc:  # noqa: BLE001 - one bad source must not kill the report
            import logging

            logging.getLogger(__name__).warning(
                "connector %s failed, skipping: %s", getattr(conn, "name", conn), exc
            )
            continue
        for row in rows:
            raw.append(normalize(row))

    items = _dedupe(raw)

    if persist:
        _persist(items)

    return items


def _persist(items: list[dict[str, Any]]) -> None:
    """Upsert items into ``intel_items`` keyed on ``content_hash`` (idempotent)."""

    with session_scope() as session:
        existing = set(session.scalars(select(IntelItemRow.content_hash)).all())
        for item in items:
            ch = content_hash(item["source"], item["url"], item["title"])
            if ch in existing:
                continue
            existing.add(ch)
            session.add(
                IntelItemRow(
                    content_hash=ch,
                    item_id=item.get("id", ch[:8]),
                    subject=item.get("subject", ""),
                    source=item["source"],
                    source_tier=item.get("source_tier", ""),
                    category=item.get("category", ""),
                    omada_impact=item.get("omada_impact", "unknown"),
                    title=item["title"],
                    url=item["url"],
                    date=item["date"],
                    payload=item,
                )
            )
