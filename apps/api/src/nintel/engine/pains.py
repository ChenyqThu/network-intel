"""Weekly 高频痛点 (pain-point) synthesis — named themes from real complaints.

The dashboard's "高频痛点 Top 5 · UniFi 社区 · 本周" panel needs named pain themes
(e.g. "6GHz 漫游/粘滞") with real counts. The firehose carries UniFi-community
volume but no per-item categories (they're set only on the curated subset), so a
mechanical histogram can't name themes. This stage pulls the current week's
UniFi-community signals from the firehose and asks Sonnet to cluster the *real*
complaints into ≤5 named themes, assigning each item to a theme by index. The
engine then counts items per theme — so every number reflects real items
(NO-FABRICATION), each item counts once, and thin/unsupported themes are dropped.

Live + LLM only; best-effort (any hiccup → empty, frontend shows the empty-state).
Offline never reaches here (the pipeline gates on ``use_dynamic``).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

_LOG = logging.getLogger(__name__)

_MAX_SAMPLE = 120       # cap firehose items sent to the LLM (cost bound)
_MIN_SAMPLE = 5         # too few complaints to cluster meaningfully → empty
_MIN_THEME_COUNT = 3    # a theme needs this many real items to render
_MAX_THEMES = 5


def build_pains(as_of: date, *, settings: Any) -> list[dict[str, Any]]:
    """``[{name, count, of}]`` pain themes for the weekly dashboard (best-effort).

    Empty list on any of: LLM disabled, too few complaints, a fetch/clustering
    hiccup, or no theme clearing the min count — the frontend then shows an honest
    empty-state instead of a fabricated histogram.
    """
    if not getattr(settings, "llm_enabled", False):
        return []
    try:
        items = _fetch_unifi_community(as_of, window_days=settings.weekly_window_days)
    except Exception:  # noqa: BLE001 - pains is a nice-to-have, never fatal
        _LOG.warning("pains: firehose fetch failed; leaving pains empty", exc_info=True)
        return []
    if len(items) < _MIN_SAMPLE:
        return []

    from . import llm

    try:
        themes = llm.cluster_pains(items)
    except Exception:  # noqa: BLE001 - a Sonnet hiccup must not fail the weekly
        _LOG.warning("pains: clustering (Sonnet) failed; leaving pains empty", exc_info=True)
        return []

    return _tally_themes(themes, n_items=len(items))


def _fetch_unifi_community(as_of: date, *, window_days: int) -> list[dict[str, Any]]:
    """Current-window UniFi-community signals from the firehose (praise dropped).

    competitor(≈UniFi) + community tier, published within the weekly window. Clear
    praise (sentiment == pos) is excluded so the sample is complaint-weighted; the
    LLM still filters out any non-pain that slips through.
    """
    from sqlalchemy import select as sa_select

    from ..store.db import get_session
    from ..store.models import IntelItemRow

    since = (as_of - timedelta(days=window_days)).isoformat()
    session = get_session()
    try:
        rows = session.scalars(
            sa_select(IntelItemRow).where(
                IntelItemRow.date >= since,
                IntelItemRow.subject == "competitor",
                IntelItemRow.source_tier == "community",
            )
        ).all()
        items: list[dict[str, Any]] = []
        for r in rows:
            payload = r.payload or {}
            if payload.get("sentiment") == "pos" or not r.title:
                continue
            items.append(
                {
                    "title": r.title,
                    "summary": payload.get("summary"),
                    "sentiment": payload.get("sentiment"),
                }
            )
    finally:
        session.close()
    return items[:_MAX_SAMPLE]


def _tally_themes(
    themes: list[dict[str, Any]], *, n_items: int
) -> list[dict[str, Any]]:
    """Count real, unique member items per theme → contract ``pains`` rows.

    Each item is credited to at most one theme (first claim wins), indices are
    range-checked, themes below ``_MIN_THEME_COUNT`` are dropped, and the top
    ``_MAX_THEMES`` by count are kept. ``of`` is the largest count (bar-width
    denominator), matching the frontend's ``count / of`` render.
    """
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for theme in themes or []:
        name = (theme.get("name") or "").strip()
        members: list[int] = []
        for m in theme.get("members") or []:
            if isinstance(m, int) and 0 <= m < n_items and m not in seen:
                seen.add(m)
                members.append(m)
        if not name or len(members) < _MIN_THEME_COUNT:
            continue
        rows.append({"name": name, "count": len(members)})

    rows.sort(key=lambda r: -r["count"])
    rows = rows[:_MAX_THEMES]
    if not rows:
        return []
    of = rows[0]["count"]
    return [{"name": r["name"], "count": r["count"], "of": of} for r in rows]
