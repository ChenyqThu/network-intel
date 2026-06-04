"""Recent-coverage digest for temporal de-duplication (B1).

Pulls the last few **published** reports and distills each into a compact record
— insight titles + 💡takeaways + cited item titles/urls — handed to the curator
as ``context.recent_coverage``. This lets Opus frame a recurring macro topic as
持续 / 升级 / 拐点 instead of re-reporting it as brand-new, **without** depending
on the (hash-embedder) vector ``history`` collection, which is unreliable for
topic-level matching.

Design notes:
* Small-N temporal recall — "what did we cover in the last week or two" — needs
  a direct recent-report digest, not semantic KNN. The corpus is tiny (a handful
  of reports × a few insights), so it fits the Opus context comfortably.
* Reference-only: like ``context.background``, it is never citeable. The prompt
  states this; the engine never turns these rows into ``items``/``references``.
* Best-effort: any repository hiccup returns ``None`` so a build never fails on
  the digest. Only runs on the live + LLM path (the caller gates on use_dynamic).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

_LOG = logging.getLogger(__name__)


def build_digest(
    report_type: str,
    as_of: date,
    *,
    lookback_days: int | None = None,
    max_reports: int = 6,
    max_insights: int = 6,
    max_items: int = 8,
) -> list[dict[str, Any]] | None:
    """Compact digest of recently-published reports for de-dup context.

    For a **weekly** build, only prior weeklies are considered (macro topics
    recur week-over-week); for a **daily**, any recent report counts (a daily can
    restate yesterday's daily or last week's weekly macro). Self / future-dated
    reports are skipped; the scan stops once it passes the lookback cutoff.
    """
    as_of_iso = as_of.isoformat()
    if lookback_days is None:
        lookback_days = 28 if report_type == "weekly" else 8
    cutoff = (as_of - timedelta(days=lookback_days)).isoformat()

    try:
        from ..api import repository

        index = repository.archive_index()  # newest-first, has id/date/type
    except Exception:  # noqa: BLE001 - digest is best-effort, never fatal
        _LOG.warning("recent_coverage: archive unavailable, skipping digest", exc_info=True)
        return None

    picked: list[dict[str, Any]] = []
    for entry in index:
        d = entry.get("date") or ""
        if not d or d >= as_of_iso:  # skip undated + self / future
            continue
        if d < cutoff:  # newest-first: nothing older qualifies
            break
        if report_type == "weekly" and entry.get("type") != "weekly":
            continue
        picked.append(entry)
        if len(picked) >= max_reports:
            break

    digests: list[dict[str, Any]] = []
    for entry in picked:
        try:
            doc = repository.get_report(entry["id"])
        except Exception:  # noqa: BLE001
            doc = None
        if not doc:
            continue
        insights = [
            {
                "subject": ins.get("subject"),
                "title": ins.get("title"),
                "takeaway": ins.get("takeaway"),
            }
            for ins in (doc.get("insights") or [])[:max_insights]
            if ins.get("title")
        ]
        items = [
            {"title": it.get("title"), "url": it.get("url")}
            for it in (doc.get("items") or [])[:max_items]
            if it.get("title")
        ]
        if not insights and not items:
            continue
        digests.append(
            {
                "report_id": entry.get("id"),
                "type": entry.get("type"),
                "date": entry.get("date"),
                "insights": insights,
                "items": items,
            }
        )

    return digests or None
