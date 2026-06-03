"""Trend / analytics stage.

Computes the ``stats`` block (and, for weekly, the ``dashboard`` payload) from
the curated items:

* ``total_items``         — count of items
* ``by_source``           — histogram over ``source``
* ``by_impact``           — histogram over ``omada_impact``
* ``top_hot``             — top items by a heat score (likes+comments or views)

The richer weekly dashboard (``sentimentTrend`` / ``vs`` / ``pains`` /
``topHeat`` plus week-over-week deltas) mixes per-report aggregates with
multi-week editorial series that cannot be derived from a single report's
items. Those editorial series are sourced from the curation manifest (seed);
the per-report aggregates (signals/threats/opps/source counts/topHeat) are
recomputed from the items so they stay consistent with the curated set.
"""

from __future__ import annotations

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
        doc["dashboard"] = normalize_dashboard(
            dict(seed_dashboard), items, doc.get("tally") or {}, live=live
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
) -> dict[str, Any]:
    """Coerce a weekly dashboard to contract-valid shapes from real item data.

    The LLM sometimes emits ``sources`` as a ``{source: count}`` dict (the
    frontend needs an array) or ``vs`` as a list (needs an object), which would
    crash ``ReportView``. Item-derived aggregates (sources / topHeat / signal
    counts / avgHeat / newCompetitor) are recomputed from the curated items.

    The multi-week editorial series (``sentimentTrend`` / ``vs`` / ``pains``) and
    week-over-week deltas need accumulated history and cannot be derived from a
    single report. On the ``live`` path they are emitted empty (never carry the
    seed's placeholder numbers into a real report — NO-FABRICATION); the frontend
    shows an honest empty-state until history accrues. Offline keeps the seed's
    series (type-guarded only) so the deterministic round-trip holds.
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
        # Single real report: emit only truthfully-derivable aggregates; the
        # multi-week series stay empty and the 环比 deltas stay null (no prior
        # week to compare). The frontend hides the delta and shows empty-states.
        dash["neutral"] = tally.get("neutral", 0)
        dash["avgHeat"] = _avg_heat(items)
        dash["newCompetitor"] = sum(1 for it in items if it.get("subject") == "competitor")
        dash["sentimentTrend"] = []
        dash["pains"] = []
        dash["vs"] = {"omada": 0, "unifi": 0}
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
