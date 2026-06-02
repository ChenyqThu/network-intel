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


def apply_trends(report: Report, *, seed_dashboard: dict[str, Any] | None) -> Report:
    """Attach recomputed ``stats`` (and weekly ``dashboard``) to ``report``.

    The per-report aggregates are recomputed from items; the weekly dashboard's
    editorial multi-week series are carried from the seed manifest, with the
    item-derived aggregates (``topHeat``) refreshed so they match the curated
    set. Returns a new validated report.
    """

    items = [it.model_dump(by_alias=True, exclude_unset=True) for it in report.items]
    doc = report.dump()

    doc["stats"] = _merge_stats(doc.get("stats", {}), compute_stats(items))

    if report.type == "weekly" and seed_dashboard is not None:
        dashboard = dict(seed_dashboard)
        # Refresh the item-derived heat list; keep editorial series as-is.
        ranked = sorted(items, key=heat_score, reverse=True)[:5]
        dashboard["topHeat"] = [
            _heat_entry(it) for it in ranked
        ]
        doc["dashboard"] = dashboard

    from ..contract import load_report

    return load_report(doc)


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
