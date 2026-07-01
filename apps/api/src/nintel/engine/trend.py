"""Trend / analytics stage.

Computes the ``stats`` block (and, for weekly, the ``dashboard`` payload) from
the curated items:

* ``total_items``         — count of items
* ``by_source``           — histogram over ``source``
* ``by_impact``           — histogram over ``omada_impact``
* ``top_hot``             — top items by a heat score (likes+comments or views)

The richer weekly dashboard (``sentimentTrend`` / ``vs`` / ``pains`` /
``topHeat`` plus week-over-week deltas) mixes per-report aggregates with
multi-week series that cannot be derived from a single report's items. On the
**live** path the 口碑指数 series (``sentimentTrend`` / ``vs``) is aggregated from
the firehose's per-item sentiment (``intel_items``, bucketed by ISO week +
subject) — a truthful roll-up of really-ingested signals, never the seed's
placeholder numbers. ``pains`` needs named-theme clustering the firehose can't
provide mechanically, so it stays empty until a cite-anchored synthesis lands.
Offline replays the seed series verbatim so the deterministic round-trip holds;
the per-report aggregates (signals/threats/opps/source counts/topHeat) are
recomputed from the items so they stay consistent with the curated set.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from ..contract import Report


def heat_score(item: dict[str, Any]) -> float:
    """A simple, source-aware heat score used for ``top_hot`` / ``topHeat``."""

    metrics = item.get("metrics") or {}
    likes = metrics.get("likes") or 0
    comments = metrics.get("comments") or 0
    views = metrics.get("views") or 0
    if likes or comments:
        return float(likes + comments)
    return float(views)


def compute_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the ``stats`` block from curated items."""

    by_source: dict[str, int] = {}
    by_impact: dict[str, int] = {}
    for it in items:
        by_source[it["source"]] = by_source.get(it["source"], 0) + 1
        by_impact[it["omada_impact"]] = by_impact.get(it["omada_impact"], 0) + 1

    ranked = sorted(items, key=heat_score, reverse=True)[:5]
    top_hot = [
        {"id": it["id"], "title": it["title"], "score": heat_score(it)}
        for it in ranked
    ]
    return {
        "total_items": len(items),
        "by_source": by_source,
        "by_impact": by_impact,
        "top_hot": top_hot,
    }


def compute_tally(items: list[dict[str, Any]]) -> dict[str, int]:
    """Lead signal tally chips, recomputed from items."""

    threat = sum(1 for it in items if it["omada_impact"] == "threat")
    opp = sum(1 for it in items if it["omada_impact"] == "opportunity")
    neutral = sum(1 for it in items if it["omada_impact"] == "neutral")
    official = sum(1 for it in items if it.get("source_tier") == "official")
    return {
        "signals": len(items),
        "threat": threat,
        "opp": opp,
        "neutral": neutral,
        "official": official,
    }


def apply_trends(
    report: Report, *, seed_dashboard: dict[str, Any] | None, live: bool = False
) -> Report:
    """Attach recomputed ``stats`` (and weekly ``dashboard``) to ``report``.

    The per-report aggregates are recomputed from items; the weekly dashboard's
    editorial multi-week series are carried from the seed manifest, with the
    item-derived aggregates (``topHeat``) refreshed so they match the curated
    set. On the ``live`` path the seed's multi-week placeholders are dropped (a
    single real report cannot derive them — NO-FABRICATION); offline replays the
    seed verbatim so the deterministic round-trip holds. Returns a new validated
    report.
    """

    items = [it.model_dump(by_alias=True, exclude_unset=True) for it in report.items]
    doc = report.dump()

    doc["stats"] = _merge_stats(doc.get("stats", {}), compute_stats(items))
    # The engine owns the signal tally (counts), not the LLM — recompute it from
    # the curated items so daily and weekly are always consistent and correct.
    doc["tally"] = compute_tally(items)

    if report.type == "weekly" and seed_dashboard is not None:
        # The report date is the as-of for the live 口碑指数 roll-up (weekly live
        # builds set report.date == as_of). Guard the parse so a malformed date
        # just skips the firehose aggregation rather than failing the build.
        as_of: date | None = None
        if live:
            try:
                as_of = date.fromisoformat(report.date)
            except (ValueError, TypeError):
                as_of = None
        doc["dashboard"] = normalize_dashboard(
            dict(seed_dashboard), items, doc.get("tally") or {}, live=live, as_of=as_of
        )

    from ..contract import load_report

    return load_report(doc)


# Source key -> human label for the dashboard's source-mix chart.
_SOURCE_LABEL = {
    "unifi_release": "UniFi 发布", "unifi_community": "UniFi 社区", "blog": "UniFi 博客",
    "unifi_store": "UniFi Store", "unifi_product": "UniFi 产品",
    "reddit": "Reddit", "youtube": "YouTube", "rss": "行业 RSS", "omada_community": "Omada 社区",
}


def normalize_dashboard(
    dash: dict[str, Any],
    items: list[dict[str, Any]],
    tally: dict[str, int],
    *,
    live: bool = False,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Coerce a weekly dashboard to contract-valid shapes from real item data.

    The LLM sometimes emits ``sources`` as a ``{source: count}`` dict (the
    frontend needs an array) or ``vs`` as a list (needs an object), which would
    crash ``ReportView``. Item-derived aggregates (sources / topHeat / signal
    counts / avgHeat / newCompetitor) are recomputed from the curated items.

    The 口碑指数 series (``sentimentTrend`` / ``vs``) is multi-week and cannot come
    from a single report's ~12 curated items. On the ``live`` path it is
    aggregated from the firehose's per-item sentiment (see
    :func:`_weekly_sentiment_series`) — truthful, never the seed's placeholder
    numbers (NO-FABRICATION); thin history simply yields fewer points and the
    frontend shows an honest empty-state. ``pains`` stays empty (needs cite-anchored
    theme clustering the firehose can't provide mechanically). Offline keeps the
    seed's series (type-guarded only) so the deterministic round-trip holds.
    """
    by_source = compute_stats(items)["by_source"]
    dash["sources"] = [
        {"key": k, "label": _SOURCE_LABEL.get(k, k), "count": v}
        for k, v in sorted(by_source.items(), key=lambda kv: -kv[1])
    ]
    ranked = sorted(items, key=heat_score, reverse=True)[:5]
    dash["topHeat"] = [_heat_entry(it) for it in ranked]
    dash["signals"] = tally.get("signals", len(items))
    dash["threats"] = tally.get("threat", 0)
    dash["opps"] = tally.get("opp", 0)

    if live:
        # Single real report: emit only truthfully-derivable aggregates. The 口碑
        # 指数 series is rolled up from the firehose's per-item sentiment; the 环比
        # deltas stay null (no prior-week comparison yet). The frontend hides the
        # delta and shows an empty-state for any panel still short on data.
        dash["neutral"] = tally.get("neutral", 0)
        dash["avgHeat"] = _avg_heat(items)
        dash["newCompetitor"] = sum(1 for it in items if it.get("subject") == "competitor")
        trend, vs = _weekly_sentiment_series(as_of) if as_of else ([], {"omada": 0, "unifi": 0})
        dash["sentimentTrend"] = trend
        dash["vs"] = vs
        # 高频痛点 needs named-theme clustering (e.g. "6GHz 漫游/粘滞") anchored to
        # real items; the firehose lacks per-item categories (set only on the
        # curated subset), so a mechanical histogram would be misleading. Left
        # empty until a cite-anchored pains synthesis lands.
        dash["pains"] = []
        for key in ("signalsDelta", "newCompetitorDelta", "avgHeatDelta"):
            dash[key] = None
        return dash

    # Offline / fixture replay: keep the seed's editorial series verbatim
    # (type-guard only) so the deterministic round-trip holds.
    if not isinstance(dash.get("vs"), dict):
        dash["vs"] = {"omada": 0, "unifi": 0}
    for key in ("sentimentTrend", "pains"):
        if not isinstance(dash.get(key), list):
            dash[key] = []
    return dash


# 口碑指数 roll-up window (the frontend labels the panel "近 8 周") and the minimum
# per-(week, subject) sentiment sample below which a point is withheld as noise.
_SENTI_WEEKS = 8
_SENTI_MIN_SAMPLE = 3
# subject -> the sentimentTrend/vs line it feeds. competitor ≈ UniFi (the panel is
# literally "Omada vs UniFi"); industry carries no口碑 line and is excluded.
_SENTI_LINE = {"omada_self": "omada", "competitor": "unifi"}


def _sentiment_index(counts: dict[str, int]) -> int | None:
    """0–100 口碑指数 (positivity): pos=1, neu=0.5, neg=0. None below min sample.

    A sentiment-weighted positive share — all-positive → 100, all-neutral → 50,
    all-negative → 0 — matching the seed panel's semantics (``vs`` == the latest
    trend point). Returns ``None`` when the sample is too thin to be meaningful so
    the caller can withhold the point.
    """
    pos, neg, neu = counts.get("pos", 0), counts.get("neg", 0), counts.get("neu", 0)
    total = pos + neg + neu
    if total < _SENTI_MIN_SAMPLE:
        return None
    return round(100 * (pos + 0.5 * neu) / total)


def _weekly_sentiment_series(
    as_of: date, *, weeks: int = _SENTI_WEEKS
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """``(sentimentTrend, vs)`` from the firehose's per-item sentiment, by ISO week.

    Reads ``intel_items`` (the ~3k-row firehose) for omada_self/competitor rows
    carrying a sentiment (Source A tags every item pos/neg/neu), buckets them into
    the last ``weeks`` ISO weeks, and computes a 口碑指数 per (week, subject). A
    trend point is emitted only when *both* lines clear the min sample, so every
    emitted point renders as a full Omada-vs-UniFi pair; ``vs`` is the current ISO
    week's point (falling back to the latest complete week, then 0/0). Best-effort:
    any DB error yields an empty series and the frontend shows the empty-state.
    """
    from collections import defaultdict

    try:
        from sqlalchemy import select as sa_select

        from ..store.db import get_session
        from ..store.models import IntelItemRow

        earliest = (as_of - timedelta(weeks=weeks)).isoformat()
        session = get_session()
        try:
            rows = session.scalars(
                sa_select(IntelItemRow).where(
                    IntelItemRow.date >= earliest,
                    IntelItemRow.subject.in_(tuple(_SENTI_LINE)),
                )
            ).all()
            # Extract while the session is open; sentiment lives in the payload.
            records = [
                (r.date, r.subject, (r.payload or {}).get("sentiment")) for r in rows
            ]
        finally:
            session.close()
    except Exception:  # noqa: BLE001 - 口碑指数 is a nice-to-have, never fatal
        import logging

        logging.getLogger(__name__).warning(
            "weekly sentiment series unavailable; leaving 口碑指数 empty", exc_info=True
        )
        return [], {"omada": 0, "unifi": 0}

    # (iso_year, iso_week, line) -> {pos/neg/neu: count}
    buckets: dict[tuple[int, int, str], dict[str, int]] = defaultdict(
        lambda: {"pos": 0, "neg": 0, "neu": 0}
    )
    for d_str, subject, senti in records:
        line = _SENTI_LINE.get(subject)
        if line is None or senti not in ("pos", "neg", "neu"):
            continue
        try:
            iso = date.fromisoformat(d_str).isocalendar()
        except (ValueError, TypeError):
            continue
        buckets[(iso[0], iso[1], line)][senti] += 1

    def _pair(iso_year: int, iso_week: int) -> tuple[int | None, int | None]:
        return (
            _sentiment_index(buckets.get((iso_year, iso_week, "omada"), {})),
            _sentiment_index(buckets.get((iso_year, iso_week, "unifi"), {})),
        )

    # The last `weeks` ISO weeks up to as_of, oldest-first, deduped.
    trend: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for i in range(weeks - 1, -1, -1):
        iso = (as_of - timedelta(weeks=i)).isocalendar()
        key = (iso[0], iso[1])
        if key in seen:
            continue
        seen.add(key)
        omada, unifi = _pair(iso[0], iso[1])
        if omada is None or unifi is None:
            continue
        trend.append({"wk": f"W{iso[1]:02d}", "omada": omada, "unifi": unifi})

    cur = as_of.isocalendar()
    cur_omada, cur_unifi = _pair(cur[0], cur[1])
    if cur_omada is not None and cur_unifi is not None:
        vs = {"omada": cur_omada, "unifi": cur_unifi}
    elif trend:  # current week still thin — show the latest complete week
        vs = {"omada": trend[-1]["omada"], "unifi": trend[-1]["unifi"]}
    else:
        vs = {"omada": 0, "unifi": 0}
    return trend, vs


def _avg_heat(items: list[dict[str, Any]]) -> int:
    """Mean heat across the curated items (0 when empty)."""

    if not items:
        return 0
    return round(sum(heat_score(it) for it in items) / len(items))


def _heat_entry(item: dict[str, Any]) -> dict[str, Any]:
    metrics = item.get("metrics") or {}
    views = metrics.get("views") or 0
    likes = metrics.get("likes") or 0
    comments = metrics.get("comments") or 0
    if not (likes or comments) and views:
        return {"id": item["id"], "v": views, "fmt": "views"}
    return {"id": item["id"], "v": int(heat_score(item))}


def _merge_stats(seed_stats: dict[str, Any], computed: dict[str, Any]) -> dict[str, Any]:
    """Prefer computed aggregates; keep any extra editorial keys from the seed."""

    merged = dict(seed_stats)
    merged.update(computed)
    return merged
