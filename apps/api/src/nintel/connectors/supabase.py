"""Source B — UNIFI_CHANNELS Supabase reader.

All UniFi channel data lives in the UNIFI_CHANNELS Supabase (verified live: 75
tables). This reader unions the three that map to intel items:

* ``product_releases``  → ``unifi_release``   (community.ui.com/releases/{slug}/{release_id})
* ``community_posts``   → ``unifi_community`` (community.ui.com/questions/{slug}/{post_id})
* ``blog_articles``     → ``blog``           (canonical_url)

Read over PostgREST with stdlib urllib (no supabase-py dependency). Offline
(default) it reconstructs provenance-``B`` rows from the seed reports.

(Store price/stock moves live in ``store_recent_*`` and feed the weekly ``store``
table, not the item stream — handled separately.)
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from .base import RawRow, connector_mode_guard, domain_of, seed_rows_for

_LIVE_HINT = (
    "A live reader queries the UNIFI_CHANNELS Supabase (SUPABASE_URL + "
    "SUPABASE_KEY) tables product_releases / community_posts / blog_articles."
)


# --- pure mappers (parity-tested against real row shapes) ------------------
def _iso_date(value: Any) -> str:
    return str(value or "")[:10]


def map_release_row(row: dict[str, Any]) -> RawRow:
    slug = row.get("slug") or ""
    rid = row.get("release_id") or ""
    url = (
        f"https://community.ui.com/releases/{slug}/{rid}"
        if slug and rid
        else (row.get("primary_download_url") or f"https://community.ui.com/releases/{slug}")
    )
    title = row.get("title") or ""
    published = _iso_date(row.get("release_date"))
    raw: dict[str, Any] = {
        "source": "unifi_release", "provenance": "B", "url": url, "title": title,
        "date": published, "source_domain": "community.ui.com", "source_tier": "official",
        "stage": row.get("stage"),
        "metrics": {"views": row.get("view_count"), "comments": row.get("comment_count")},
    }
    return RawRow(source="unifi_release", provenance="B", url=url, title=title, published=published, raw=raw)


def map_community_row(row: dict[str, Any]) -> RawRow:
    slug = row.get("slug") or ""
    pid = row.get("post_id") or ""
    url = f"https://community.ui.com/questions/{slug}/{pid}"
    title = row.get("title") or ""
    published = _iso_date(row.get("published_at"))
    raw: dict[str, Any] = {
        "source": "unifi_community", "provenance": "B", "url": url, "title": title,
        "date": published, "source_domain": "community.ui.com", "source_tier": "official",
        "metrics": {
            "views": row.get("view_count"),
            "comments": row.get("comment_count"),
            "likes": row.get("like_count"),
        },
    }
    return RawRow(source="unifi_community", provenance="B", url=url, title=title, published=published, raw=raw)


def map_blog_row(row: dict[str, Any]) -> RawRow:
    url = row.get("canonical_url") or f"https://blog.ui.com/article/{row.get('slug', '')}"
    title = row.get("title") or ""
    published = _iso_date(row.get("published_at"))
    raw: dict[str, Any] = {
        "source": "blog", "provenance": "B", "url": url, "title": title, "date": published,
        "source_domain": domain_of(url) or "blog.ui.com", "source_tier": "official",
        "metrics": {"views": row.get("view_count")},
    }
    return RawRow(source="blog", provenance="B", url=url, title=title, published=published, raw=raw)


_TABLES = (
    ("product_releases", "release_date", map_release_row),
    ("community_posts", "published_at", map_community_row),
    ("blog_articles", "published_at", map_blog_row),
)


class SupabaseReader:
    """Reader for the UniFi official channels (source B), Supabase-backed."""

    name = "supabase:unifi_channels"
    provenance = "B"

    def fetch(self, since: date) -> list[RawRow]:
        if connector_mode_guard(self.name, _LIVE_HINT, self.provenance):
            return [r for r in self._fetch_live(since) if r.date >= since]
        rows = seed_rows_for(provenances={"B"})
        return [r for r in rows if r.date >= since]

    def _fetch_live(self, since: date, *, limit: int = 200) -> list[RawRow]:  # pragma: no cover - network
        rows: list[RawRow] = []
        for table, date_col, mapper in _TABLES:
            for record in _pg_get(table, date_col=date_col, since=since, limit=limit):
                rows.append(mapper(record))
        return rows


def _pg_get(table: str, *, date_col: str, since: date, limit: int) -> list[dict[str, Any]]:  # pragma: no cover - network
    return _pg_query(
        table,
        {date_col: f"gte.{since.isoformat()}", "order": f"{date_col}.desc", "limit": limit},
    )


def _pg_query(table: str, params: dict[str, Any]) -> list[dict[str, Any]]:  # pragma: no cover - network
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_KEY"]
    q: dict[str, Any] = {"select": "*"}
    q.update(params)
    req = urllib.request.Request(
        f"{base}/rest/v1/{table}?{urllib.parse.urlencode(q)}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted host)
        return json.loads(resp.read().decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# Weekly store-moves block (new products / price / stock). These feed the
# report's tabular ``store`` block, NOT the item stream — they have no narrative
# and carry {product, cat, from, to, change, dir, stock} per the contract.
# ---------------------------------------------------------------------------
def _store_name(row: dict[str, Any]) -> str:
    # Prefer the friendly title ("Enterprise 3.5\" HDD, 8 TB"); product_name in
    # the store_recent_* tables is the SKU, so it's the last-resort fallback.
    return (
        row.get("product_title") or row.get("name") or row.get("title")
        or row.get("product_name") or row.get("sku") or "?"
    )


def _clean_cat(slug: Any) -> str:
    return str(slug or "").replace("-", " ").strip()


def map_price_change(row: dict[str, Any]) -> dict[str, Any]:
    """store_recent_price_changes row -> store move (pure; parity-tested)."""
    prev, curr = row.get("previous_price"), row.get("current_price")
    direction, change = "flat", ""
    if isinstance(prev, (int, float)) and isinstance(curr, (int, float)):
        direction = "up" if curr > prev else "down" if curr < prev else "flat"
        if prev:
            change = f"{(curr - prev) / prev * 100:+.0f}%"
    return {
        "product": _store_name(row), "cat": _clean_cat(row.get("category_slug")),
        "from": prev, "to": curr, "change": change, "dir": direction, "stock": "in",
    }


def map_stock_change(row: dict[str, Any]) -> dict[str, Any]:
    """store_recent_stock_changes row -> store move (pure; parity-tested)."""
    prev, curr = bool(row.get("previous_stock")), bool(row.get("current_stock"))
    change = "补货" if (curr and not prev) else "缺货" if (prev and not curr) else ""
    return {
        "product": _store_name(row), "cat": _clean_cat(row.get("category_slug")),
        "from": None, "to": None, "change": change,
        "dir": "up" if curr else "down", "stock": "in" if curr else "out",
    }


def map_upcoming_product(row: dict[str, Any]) -> dict[str, Any]:
    """techspecs_upcoming_products row -> store move (new product; parity-tested)."""
    return {
        "product": _store_name(row), "cat": _clean_cat(row.get("category_slug")),
        "from": None, "to": None, "change": "新品", "dir": "new", "stock": "out",
    }


def _dedupe_by_product(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["product"] in seen:
            continue
        seen.add(r["product"])
        out.append(r)
        if len(out) >= limit:
            break
    return out


def fetch_store_moves(  # pragma: no cover - network
    since: date, *, region: str = "us", new_n: int = 6, price_n: int = 6, stock_n: int = 6
) -> list[dict[str, Any]]:
    """Build the weekly ``store`` block: new products + price + stock changes.

    Upcoming products are global; price/stock changes are region-scoped (one
    region, default ``us``, to avoid the same SKU repeating across 8 locales).
    Deduped by product so one product shows once per category.
    """
    moves: list[dict[str, Any]] = []
    upcoming = _pg_query("techspecs_upcoming_products", {
        "is_upcoming": "is.true", "last_changed_at": f"gte.{since.isoformat()}",
        "order": "last_changed_at.desc", "limit": 40,
    })
    moves += _dedupe_by_product([map_upcoming_product(r) for r in upcoming], new_n)
    prices = _pg_query("store_recent_price_changes", {
        "store_region": f"eq.{region}", "change_time": f"gte.{since.isoformat()}",
        "order": "change_time.desc", "limit": 80,
    })
    moves += _dedupe_by_product([map_price_change(r) for r in prices], price_n)
    stocks = _pg_query("store_recent_stock_changes", {
        "store_region": f"eq.{region}", "change_time": f"gte.{since.isoformat()}",
        "order": "change_time.desc", "limit": 120,
    })
    moves += _dedupe_by_product([map_stock_change(r) for r in stocks], stock_n)
    return moves
