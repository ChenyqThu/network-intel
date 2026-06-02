"""Source B — UNIFI_CHANNELS Supabase reader.

Offline (default) it reconstructs provenance-``B`` rows from the seed reports.
When ``NINTEL_CONNECTOR_MODE=live`` and ``B`` is in ``NINTEL_LIVE_SOURCES`` it
queries the UNIFI_CHANNELS Supabase project (``SUPABASE_URL`` + ``SUPABASE_KEY``)
and unions four tables, mapping each row via :func:`map_supabase_row`:

* ``product_releases`` → ``unifi_release`` (community.ui.com/releases)
* ``blog``             → ``blog``          (blog.ui.com)
* ``community``        → ``unifi_community`` (community.ui.com questions)
* ``store``            → ``unifi_store``    (store.ui.com)

URL integrity (PRD §7.8.6) is preserved — full UUIDs, never truncated.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for

_LIVE_HINT = (
    "A live reader queries the UNIFI_CHANNELS Supabase tables "
    "(product_releases / blog / community / store) via SUPABASE_URL + SUPABASE_KEY."
)

_TABLE_SOURCE = {
    "product_releases": "unifi_release",
    "blog": "blog",
    "community": "unifi_community",
    "store": "unifi_store",
}


def map_supabase_row(table: str, row: dict[str, Any]) -> RawRow:
    """Map one Supabase row onto a :class:`RawRow` (pure; parity-tested)."""

    source = _TABLE_SOURCE.get(table, "unifi_community")
    url = row["url"]
    title = row.get("title") or row.get("name") or ""
    published = str(row.get("published_at") or row.get("created_at") or "")[:10]
    raw: dict[str, Any] = {
        "source": source,
        "provenance": "B",
        "url": url,
        "title": title,
        "date": published,
        "source_domain": domain_of(url),
        "source_tier": "official" if source in ("unifi_release", "blog") else "community",
    }
    metrics = {k: row[k] for k in ("likes", "comments", "views") if row.get(k) is not None}
    if metrics:
        raw["metrics"] = metrics
    for k in ("stage", "badges", "sentiment"):
        if row.get(k) is not None:
            raw[k] = row[k]
    return RawRow(source=source, provenance="B", url=url, title=title, published=published, raw=raw)


class SupabaseReader:
    """Reader for the UniFi official channels (source B)."""

    name = "supabase:unifi_channels"
    provenance = "B"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        rows = seed_rows_for(provenances={"B"})
        return [r for r in rows if r.date >= since]

    def _fetch_live(self, since: date) -> list[RawRow]:  # pragma: no cover - network
        import os

        from supabase import create_client  # optional [live] dependency

        client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
        rows: list[RawRow] = []
        for table in _TABLE_SOURCE:
            data = (
                client.table(table)
                .select("*")
                .gte("published_at", since.isoformat())
                .execute()
                .data
            )
            rows.extend(map_supabase_row(table, r) for r in data)
        return rows
