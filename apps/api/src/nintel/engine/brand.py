"""Brand disambiguation for source-A (sentiment monitor) candidates.

The connector tags ``subject=omada_self`` by keyword (匹配关键词/title contains an
Omada/TP-Link marker). Keyword matching can't tell *TP-Link Omada networking*
from things merely **named** Omada — e.g. the "Omada E5" electric vehicle, which
even the monitor's own AI mis-scored as "an Omada EAP product, highly relevant".

This stage asks Haiku (real-world knowledge) to bucket each ``omada_self``
candidate into omada / competitor / other, then:

* ``other``      → dropped from the pool (noise; not networking at all),
* ``competitor`` → reclassified to ``subject=competitor`` (+ a valid impact),
* ``omada``      → kept as ``omada_self``.

It runs **before** selection so noise never takes an ``omada_self`` slot. It is a
no-op unless ``llm_enabled`` (offline/tests are unaffected), and best-effort: a
Haiku error keeps the keyword subjects rather than failing the build.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from ..config import get_settings


def _competitor_impact(sentiment: str | None) -> str:
    return {"neg": "opportunity", "pos": "threat"}.get(sentiment, "neutral")


def _recent(item_date: str | None, cutoff: date, as_of: date) -> bool:
    try:
        d = date.fromisoformat(str(item_date)[:10])
    except (ValueError, TypeError):
        return False
    return cutoff <= d <= as_of


def refine_omada_subjects(items: list[dict[str, Any]], *, as_of: date) -> list[dict[str, Any]]:
    """Verify keyword-tagged omada_self candidates with an LLM; drop/reclassify.

    Only candidates within ``weekly_window_days + 3`` of ``as_of`` are checked
    (the only ones that could be selected) to bound cost to one Haiku call.
    """

    settings = get_settings()
    if not settings.llm_enabled:
        return items

    cutoff = as_of - timedelta(days=settings.weekly_window_days + 3)
    idx = [
        i
        for i, it in enumerate(items)
        if it.get("subject") == "omada_self" and _recent(it.get("date"), cutoff, as_of)
    ]
    if not idx:
        return items

    from . import llm

    try:
        verdicts = llm.classify_brands([items[i] for i in idx])  # local index -> brand
    except Exception:  # noqa: BLE001 - best-effort; never fail the build on the filter
        logging.getLogger(__name__).warning(
            "brand filter unavailable; keeping keyword subjects", exc_info=True
        )
        return items

    drop: set[int] = set()
    to_competitor: set[int] = set()
    for local, i in enumerate(idx):
        verdict = verdicts.get(local, "omada")  # default to keep on a missing verdict
        if verdict == "other":
            drop.add(i)
        elif verdict == "competitor":
            to_competitor.add(i)

    if not drop and not to_competitor:
        return items

    out: list[dict[str, Any]] = []
    for i, it in enumerate(items):
        if i in drop:
            continue
        if i in to_competitor:
            it = dict(it)
            it["subject"] = "competitor"
            it["omada_impact"] = _competitor_impact(it.get("sentiment"))
        out.append(it)
    logging.getLogger(__name__).info(
        "brand filter: dropped %d, reclassified %d of %d omada_self candidates",
        len(drop), len(to_competitor), len(idx),
    )
    return out
